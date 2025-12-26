from __future__ import annotations

import json
import re
from typing import Any, Dict, Generator, List, Tuple

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from configuration import settings
from src.prompts.prompts import (
    clarify_question_prompt,
    judge_clarify_answers_prompt,
    finalize_question_prompt,
)
from src.state import ResearchState

Event = Dict[str, Any]
_NOQ = "NO_QUESTION"
_Q_LINE_RE = re.compile(r"^\s*(\d+)[.)]\s*(.+?)\s*$")


def _llm():
    return init_chat_model(
        settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=settings.temperature,
    )

# 첫 질문에 대한 LLM 실행 (파싱 안되어있음)
def run_clarify_llm(human_prompt: str) -> Generator[Event, None, str]:
    llm = _llm()
    full: List[str] = []


    for chunk in llm.stream(
        [SystemMessage(content=clarify_question_prompt), HumanMessage(content=human_prompt)]
    ):
        c = getattr(chunk, "content", "") or ""
        if not c:
            continue
        full.append(c)
        yield {"type": "assistant_text", "content": c}

    return "".join(full).strip()

def extract_context_from_qa_blocks(qa_blocks: List[str]) -> Dict[str, str]:
    context = {}
    for block in qa_blocks:
        lines = block.splitlines()
        for i in range(len(lines) - 1):
            line_q = lines[i].strip()
            line_a = lines[i + 1].strip()
            if line_q.startswith("Q:") and line_a.startswith("A:"):
                q = line_q[2:].strip()
                a = line_a[2:].strip()
                if q and a and not a.lower() in ("", "몰라", "모름", "잘 모르겠어요", "알아서"):
                    context[q] = a
    return context

# run_clarify_llm에서 생긴 LLM 답변을 파성 + 추가 질문 완성
def make_clarify_questions(
    question: str,
    qa_blocks: List[str],
) -> Generator[Event, None, Tuple[bool, List[str]]]:
    context_dict = extract_context_from_qa_blocks(qa_blocks)
    context_str = "\n".join(f"- {k}: {v}" for k, v in context_dict.items())
    
    base = f"사용자 질문:\n{question}\n"
    if qa_blocks:
        base += "\n추가 Q/A:\n" + "\n\n".join(qa_blocks) + "\n"
    if context_dict:
        base += f"\n\n이미 확보된 정보(context):\n{context_str}\n\n위 항목은 이미 답변 받은 것이므로, 어떤 형태로든 다시 묻지 마라.\n"

    for attempt in range(2):
        human = base if attempt == 0 else base + "\n출력 형식을 반드시 지켜라: NO_QUESTION 또는 1) ...? 형식만.\n"
        raw = (yield from run_clarify_llm(human)).strip()

        if raw == _NOQ:
            if len(question.strip()) < 8 and attempt == 0:
                base += "\n입력이 매우 짧고 추상적이다. 리서치가 흔들리지 않도록 필수 정보만 묻는 추가 질문을 만들어라.\n"
                continue
            return (False, [])

        qs: List[str] = []
        for line in raw.splitlines():
            m = _Q_LINE_RE.match(line)
            if not m:
                continue
            q = m.group(2).strip()
            if not q:
                continue
            if not q.endswith("?"):
                q = q.rstrip(".") + "?"
            qs.append(q)

        if qs:
            return (True, qs[:5])

    return (False, [])

# 추가질문에 대한 답변 충분함 확인
def judge_clarify_answer(
    question: str,
    clarifying_questions: List[str],
    user_answer_text: str,
) -> Tuple[bool, List[str]]:
    llm = _llm()

    human = (
        f"원 질문:\n{question}\n\n"
        + "Clarify 질문 목록:\n"
        + "\n".join(f"- {q}" for q in clarifying_questions)
        + "\n\n"
        + f"사용자 답변:\n{user_answer_text}"
    )

    resp = llm.invoke([
        SystemMessage(content=judge_clarify_answers_prompt),
        HumanMessage(content=human),
    ])

    t = (getattr(resp, "content", "") or "").strip()
    try:
        obj = json.loads(t)
        ok = bool(obj.get("answers_sufficient", False))
        followups = obj.get("unanswered_questions", [])
        return ok, followups
    except Exception:
        return False, clarifying_questions  # fallback: 전부 불충분 처리


def build_final_question(
    question: str,
    qa_blocks: List[str],
) -> str:
    llm = _llm()

    context_dict = extract_context_from_qa_blocks(qa_blocks)
    context_str = "\n".join(f"- {k}: {v}" for k, v in context_dict.items())
    human = f"원 질문:\n{question}\n\n"
    human += "추가 Q/A:\n" + "\n\n".join(qa_blocks) if qa_blocks else "추가 Q/A: 없음"
    if context_dict:
        human += f"\n\n※ 아래 정보는 이미 사용자로부터 확인된 항목이므로, 반드시 그대로 반영해야 한다:\n{context_str}"

    resp = llm.invoke(
        [
            SystemMessage(content=finalize_question_prompt),
            HumanMessage(content=human),
        ]
    )

    t = (getattr(resp, "content", "") or "").strip()
    if not t:
        return ""

    try:
        obj = json.loads(t)
        fq = obj.get("final_question")
        return fq.strip() if isinstance(fq, str) and fq.strip() else t
    except Exception:
        return t


def clarify(state: ResearchState) -> Generator[Event, None, None]:
    if getattr(state, "final_question", None):
        state.need_clarification = False
        yield {"need_clarification": False, "final_question": state.final_question}
        return

    msgs = getattr(state, "messages", None) or []
    qa_blocks = [
        str(m.get("content", "")).strip()
        for m in msgs
        if isinstance(m, dict) and m.get("type") == "clarify_qa" and str(m.get("content", "")).strip()
    ]

    def _append_qa(block: str):
        if not block:
            return
        if getattr(state, "messages", None) is None:
            state.messages = []
        if state.messages and isinstance(state.messages[-1], dict) and state.messages[-1].get("type") == "clarify_qa":
            if state.messages[-1].get("content") == block:
                return
        state.messages.append({"type": "clarify_qa", "content": block})

    if state.clarifying_questions and state.clarifying_answers:
        user_answer_text = "\n".join(state.clarifying_answers).strip()
        cur_block = ""
        if user_answer_text:
            cur_block = (
                "Q/A:\n"
                + "\n".join(f"Q: {q}" for q in state.clarifying_questions)
                + "\n"
                + f"A: {user_answer_text}"
            )

        ok, followups = judge_clarify_answer(
            state.question,
            state.clarifying_questions,
            user_answer_text,
        )

        if not ok:
            if cur_block:
                _append_qa(cur_block)
                qa_blocks = qa_blocks + [cur_block]
            if followups:
                state.need_clarification = True
                state.clarifying_questions = followups
                state.clarifying_answers = []
                yield {"need_clarification": True, "clarifying_questions": followups}
            return

        if cur_block:
            _append_qa(cur_block)
            qa_blocks = qa_blocks + [cur_block]

        fq = build_final_question(state.question, qa_blocks) or state.question
        state.final_question = fq
        state.need_clarification = False
        yield {"need_clarification": False, "final_question": fq}
        return

    need, qs = yield from make_clarify_questions(state.question, qa_blocks)

    if not need:
        fq = build_final_question(state.question, qa_blocks) or state.question
        state.final_question = fq
        state.need_clarification = False
        yield {"need_clarification": False, "final_question": fq}
        return

    state.need_clarification = True
    state.clarifying_questions = qs
    state.clarifying_answers = []
    yield {"need_clarification": True, "clarifying_questions": qs}
