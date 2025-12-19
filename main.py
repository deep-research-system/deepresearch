"""딥리서치 시스템의 진입점.

이 스크립트는 연구 그래프를 연결하고 커맨드 라인에서 실행한다.

그래프 구현은 ``src`` 패키지에 있으며, 런타임에 ``src`` 디렉터리를 Python 경로에 추가하여
패키지 구조와 상관없이 상대 import가 동작하도록 한다.

이 파일을 직접 실행하려면 다음과 같이 입력한다:
    python main.py
"""

import sys
from pathlib import Path

# Ensure that the ``src`` directory is on the Python path.  This allows
# ``main.py`` to import from ``src`` without installing the package first.
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from configuration import settings  # noqa: E402  # import after sys.path modification
from src.graph import build_graph  # noqa: E402


def main() -> None:
    """딥리서치 파이프라인을 실행한다.

    사용자에게 질문을 입력받고 연구 그래프를 실행한 후,
    생성된 마크다운 보고서를 표준 출력에 표시한다.
    현재 구현은 정보 수집과 편집에 집중하며, PDF 생성은 향후 선택적 확장으로 남겨둔다.
    """
    graph = build_graph()
    question = input("딥리서치 질문을 입력하세요:\n> ").strip()
    if not question:
        print("질문이 비어 있습니다.")
        return
    # Invoke the graph with the initial state containing the question
    out = graph.invoke({"question": question})
    print("\n" + "=" * 60)
    print(out.get("report_markdown", "보고서 생성 실패"))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()