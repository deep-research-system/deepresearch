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
        yield {"assistant_text" : c}

    return "".join(full).strip()


def extract_context_from_qa_blocks(qa_blocks: List[str]) -> Dict[str, str]:
    """
    qa_blocks 예: "Q: ...\nA: ..." 형태에서 Q/A를 추출해 컨텍스트로 정리
    """
    context: Dict[str, str] = {}
    for block in qa_blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        q, a = "", ""
        for line in lines:
            if line.lower().startswith("q:"):
                q = line[2:].strip()
            elif line.lower().startswith("a:"):
                a = line[2:].strip()
        if q and a and a.lower() not in ("", "몰라", "모름", "잘 모르겠어요", "알아서"):
            context[q] = a
    return context


def _append_qa(block: str) -> str:
    return block.strip()


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
        base += (
            "\n이미 확보된 정보(context):\n"
            f"{context_str}\n"
            "위 항목은 이미 답변 받은 것이므로, 어떤 형태로든 다시 묻지 마라.\n"
        )

    full = yield from run_clarify_llm(base)

    # NO_QUESTION이면 추가질문 없음
    if _NOQ in full:
        return (False, [])

    qs: List[str] = []
    for line in full.splitlines():
        m = _Q_LINE_RE.match(line)
        if not m:
            continue
        q = m.group(2).strip()
        if not q.endswith("?"):
            q = q.rstrip(".") + "?"
        qs.append(q)

    if qs:
        return (True, qs[:3])

    return (False, [])


def judge_clarify_answer(
    question: str,
    clarifying_questions: List[str],
    user_answer_text: str,
) -> Tuple[bool, List[str]]:
    """
    - ok=True: 충분함
    - ok=False: 불충분, followups(재질문 리스트) 반환
    """
    llm = _llm()
    human = (
        f"원 질문:\n{question}\n\n"
        + "Clarify 질문 목록:\n"
        + "\n".join(f"- {q}" for q in (clarifying_questions or []))
        + "\n\n"
        + f"사용자 답변:\n{user_answer_text}\n"
    )

    out = llm.invoke([SystemMessage(content=judge_clarify_answers_prompt), HumanMessage(content=human)])
    t = (getattr(out, "content", "") or "").strip()

    try:
        obj = json.loads(t)
        ok = bool(obj.get("answers_sufficient"))
        followups = obj.get("unanswered_questions") or []
        if not isinstance(followups, list):
            followups = []
        followups = [str(x).strip() for x in followups if str(x).strip()]
        return ok, followups
    except Exception:
        # 파싱 실패 시 보수적으로 "불충분" 처리하지 않고, 통과(서비스 안정)
        return True, []


def build_final_question(question: str, qa_blocks: List[str]) -> str:
    llm = _llm()
    human = f"원 질문:\n{question}\n\n"
    if qa_blocks:
        human += "추가 Q/A:\n" + "\n\n".join(qa_blocks) + "\n"

    out = llm.invoke([SystemMessage(content=finalize_question_prompt), HumanMessage(content=human)])
    t = (getattr(out, "content", "") or "").strip()

    # finalize는 JSON을 기대하지만, 실패 시 원문 리턴
    try:
        obj = json.loads(t)
        fq = obj.get("final_question")
        if isinstance(fq, str) and fq.strip():
            return fq.strip()
        return t
    except Exception:
        return t


def _format_followups_text(followups: List[str]) -> str:
    intro = "답변이 부족해 추가로 몇 가지 확인할게요."
    lines = [intro]
    for i, q in enumerate(followups[:3], start=1):
        lines.append(f"{i}) {q}")
    return "\n".join(lines)


def clarify(state: ResearchState) -> Generator[Event, None, None]:
    # 이미 final_question이 있으면 그대로 반환
    if getattr(state, "final_question", None):
        state.need_clarification = False
        yield {"need_clarification": False, "final_question": state.final_question}
        return

    msgs = getattr(state, "messages", None) or []
    qa_blocks = [
        str(m.get("content", "")).strip()
        for m in msgs
        if isinstance(m, dict) and m.get("role") == "assistant" and str(m.get("content", "")).strip().startswith("Q:")
    ]

    # 2번째 요청: 사용자가 추가질문 답변을 제출한 경우
    if getattr(state, "clarifying_answers", None):
        # 사용자가 제출한 답변을 하나의 텍스트로 합쳐서 judge에 전달
        user_answer_text = "\n".join([str(x).strip() for x in (state.clarifying_answers or []) if str(x).strip()])

        # QA 블록 누적(선택): 현재 질문/답변을 기록
        cur_block = ""
        if state.clarifying_questions:
            q_lines = "\n".join(f"Q: {q}" for q in state.clarifying_questions)
            a_lines = "\n".join(f"A: {a}" for a in (state.clarifying_answers or []))
            cur_block = f"{q_lines}\n{a_lines}".strip()

        ok, followups = judge_clarify_answer(
            state.question,
            state.clarifying_questions or [],
            user_answer_text,
        )

        if not ok:
            if cur_block:
                qa_blocks = qa_blocks + [_append_qa(cur_block)]

            # followups 중복 제거(“이전에 물었던 질문 문장”과 완전 동일한 것 제거)
            asked_set = set([q.strip() for q in (state.clarifying_questions or []) if q.strip()])
            followups = [q for q in followups if q and q not in asked_set]

            if followups:
                state.need_clarification = True
                state.clarifying_questions = followups[:3]
                state.clarifying_answers = []

                # 재질문은 화면에 assistant_text로 1회 출력(줄바꿈 포함)
                yield {"assistant_text" : _format_followups_text(state.clarifying_questions)}

                # 프론트가 다음 요청에 질문 리스트를 다시 실어보낼 수 있도록 전달(저장용)
                yield {
                    "need_clarification": True,
                    "clarifying_questions": state.clarifying_questions,
                }
            else:
                # followups가 비었으면 그냥 최종질문 생성으로 진행
                fq = build_final_question(state.question, qa_blocks) or state.question
                state.final_question = fq
                state.need_clarification = False
                yield {"need_clarification": False, "final_question": fq}
            return

        # 충분하면 최종질문 생성
        if cur_block:
            qa_blocks = qa_blocks + [_append_qa(cur_block)]

        fq = build_final_question(state.question, qa_blocks) or state.question
        state.final_question = fq
        state.need_clarification = False
        yield {"need_clarification": False, "final_question": fq}
        return

    # 1번째 요청: 추가질문 생성 여부 판단 + (있으면) assistant_text 스트리밍 출력
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

    # 프론트가 “저장용”으로 질문 리스트를 받도록 전달 (UI 출력은 이미 assistant_text로 끝남)
    yield {
        "need_clarification": True,
        "clarifying_questions": state.clarifying_questions,
    }
