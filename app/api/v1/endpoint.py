"""
API 라우터 업데이트 (app/api/v1/router.py)

주요 변경사항:
1. 번역 이력 라우터 추가
"""

from fastapi import APIRouter
from app.routers import translation

api_router = APIRouter()

# 번역 관련 엔드포인트 등록
api_router.include_router(
    translation.router,
    tags=["translation"]
)
