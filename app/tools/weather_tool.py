# app/tools/weather_tool.py

import os
import requests
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

#  init_chat_model + model_provider="groq"
llm = init_chat_model(
    "llama-3.1-8b-instant",   # ← 여기에는 모델 이름만
    model_provider="groq",    # ← provider를 명시
    temperature=0.7,
    max_tokens=1000,
)


@tool("weather")
def weather(city: str) -> str:
    """
    주어진 도시(city)의 날씨를 조회하고,
    LLM을 통해 한국어로 자연스럽게 요약하여 제공하는 도구입니다.
    """

    # 1) 날씨 API 호출 (지금은 서울 위도/경도 고정 데모)
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=37.5665&longitude=126.9780&current_weather=true"
        )
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        weather_json = res.json()
    except Exception as e:
        return f"날씨 API 호출 오류: {e}"

    # 2) LLM에게 요약 요청
    prompt = f"""
너는 친절하고 정확한 한국어 날씨 비서야.
아래 날씨 데이터를 바탕으로 도시의 현재 날씨를 자연스럽게 설명해줘.

도시: {city}
날씨 데이터(JSON): {weather_json}
"""

    try:
        result = llm.invoke(prompt)
        return result
    except Exception as e:
        return f"날씨 요약 중 오류: {e}"
