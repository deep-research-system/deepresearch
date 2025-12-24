from __future__ import annotations

import re
from typing import List

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from configuration import settings
from src.prompts.prompts import clarify_question_prompt, finalize_question_prompt
from src.state import ResearchState

_Q_RE = re.compile(r"\s*(?:\d+)[.)]\s*(.+)")
_NOQ = "NO_QUESTION"


def _llm():
    return init_chat_model(settings.llm_model, api_key=settings.openai_api_key)


def _parse_questions(text: str) -> List[str]:
    t = text.strip()
    if t == _NOQ:
        return []
    qs: List[str] = []
    for line in t.splitlines():
        m = _Q_RE.match(line)
        if m:
            q = m.group(1).strip()
            if q.endswith("?") and q:
                qs.append(q)
    return qs[:3]


def clarify(state: ResearchState):
    if state.final_question:
        yield {
            "need_clarification": False,
            "final_question": state.final_question,
            "clarifying_questions": state.clarifying_questions,
        }
        return

    if state.clarifying_questions and state.clarifying_answers:
        buf: List[str] = []
        for chunk in _llm().stream(
            [
                SystemMessage(content=finalize_question_prompt),
                HumanMessage(
                    content=(
                        "원 질문:\n"
                        f"{state.question}\n\n"
                        "추가 Q/A:\n"
                        + "\n".join(
                            f"Q: {q}\nA: {a}"
                            for q, a in zip(state.clarifying_questions, state.clarifying_answers)
                        )
                    )
                ),
            ]
        ):
            if chunk.content:
                buf.append(chunk.content)
                yield {"type": "assistant_text", "content": chunk.content}

        state.need_clarification = False
        state.final_question = "".join(buf).strip() or state.question

        yield {
            "need_clarification": False,
            "final_question": state.final_question,
            "clarifying_questions": state.clarifying_questions,
        }
        return

    buf: List[str] = []
    for chunk in _llm().stream(
        [
            SystemMessage(content=clarify_question_prompt),
            HumanMessage(content=f"사용자 질문:\n{state.question}"),
        ]
    ):
        if chunk.content:
            buf.append(chunk.content)
            yield {"type": "assistant_text", "content": chunk.content}

    full = "".join(buf)
    qs = _parse_questions(full)

    state.clarifying_questions = qs
    state.need_clarification = bool(qs)

    if not qs:
        state.final_question = state.question
        yield {
            "need_clarification": False,
            "final_question": state.final_question,
            "clarifying_questions": [],
        }
    else:
        yield {
            "need_clarification": True,
            "clarifying_questions": qs,
        }
