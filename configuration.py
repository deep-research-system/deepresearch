"""프로젝트 설정과 환경 변수 로딩.

이 모듈은 API 키와 모델 파라미터와 같은 설정 값을 중앙 집중화한다.
python-dotenv를 사용하여 환경 변수에서 값을 읽으므로 프로젝트 루트의 ``.env`` 파일에 비밀값을 저장할 수 있다.
"""

import os
from dataclasses import dataclass

try:
    # ``python-dotenv`` may not always be installed in minimal environments. Attempt
    # to import it; if unavailable, loading .env files will be skipped silently.
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    load_dotenv = lambda *_, **__: None


# Load variables from a .env file if present. This call is idempotent.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """연구 시스템을 위한 불변 설정 값."""

    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    max_subqueries: int = int(os.getenv("MAX_SUBQUERIES", "5"))
    max_results_per_query: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "5"))

    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")


# Export a singleton settings instance
settings = Settings()