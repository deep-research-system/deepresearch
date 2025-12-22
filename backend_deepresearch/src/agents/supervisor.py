"""
현재 딥리서치 기능만 들어있기 때문에 supervisor의 역할이 없는 상태
clarify로부터 받은 내용을 그대로 subquery로 전달하는 역할만 일단 수행
"""


from __future__ import annotations
from src.state import ResearchState

def supervise(state: ResearchState) -> ResearchState:
    return state
