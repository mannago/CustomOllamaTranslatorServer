"""
번역 엔드포인트 수정 예제 (app/api/v1/endpoints/translation.py)

- 언어 일관성 번역 서비스 통합
- 세션 관리 기능 추가
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.services.consistent_translator import ConsistentTranslator
from app.settings import settings
from app.settings import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["ROUTER"])

router = APIRouter()

@router.get("/translate", response_class=PlainTextResponse)
async def translate_get(
    from_lang: str = Query(None, alias="from", description="원본 언어 코드"),
    to: str = Query(..., description="대상 언어 코드"),
    text: str = Query(..., description="번역할 텍스트")
):
    """
    텍스트를 지정된 언어로 번역합니다.
    
    - **source_lang**: 원본 텍스트의 언어 코드 (비워두면 자동 감지)
    - **target_lang**: 번역할 대상 언어 코드
    - **text**: 번역할 텍스트 내용
    """
    logger.debug(f"원본 언어: {from_lang}, 대상 언어: {to}, 텍스트: {text}")
    # 지원되는 언어인지 확인
    if to not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원되지 않는 대상 언어: {to}. 지원되는 언어: {', '.join(settings.SUPPORTED_LANGUAGES)}"
        )
    
    # 일관성 보장 번역 적용
    translated_text = await ConsistentTranslator.translate(
        text=text,
        source_lang=from_lang,
        target_lang=to
    )
    logger.debug(f"번역 결과: {translated_text}")
    # PlainTextResponse로 직접 텍스트 반환 (따옴표 없음)
    return translated_text
