import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    llm_model: str
    tavily_api_key: str | None
    temperature: float
    max_subqueries: int

    @staticmethod
    def load() -> "Settings":
        load_dotenv()
        return Settings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            temperature=0.2,
            max_subqueries=10,
        )

settings = Settings.load()
