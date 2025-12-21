"""딥리서치를 위한 크롤링 유틸리티.

이 모듈은 웹 페이지에서 HTML/텍스트를 추출하기 위한 기본 틀이다.
예를 들어 readability-lxml이나 newspaper3k를 사용하여 기사 내용을 추출할 수 있다.
현재는 시연을 위해 빈 문자열을 반환한다.
"""

from typing import Any


def extract_text(url: str) -> str:
    """URL에서 읽을 수 있는 텍스트를 추출하기 위한 임시 함수.

    Args:
        url: 콘텐츠를 가져와 추출할 URL.

    Returns:
        추출된 텍스트를 포함하는 문자열을 반환한다. 현재는 빈 문자열을 반환하며, 이후 실제 추출 로직으로 교체한다.
    """
    # TODO: implement crawling and readability extraction
    return ""


__all__ = ["extract_text"]