"""
개선된 main.py 파일 (일관성 있는 번역 서비스 통합)
"""

import time
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.modules.llm import ollamac
from app.modules.ollama_manager import MANAGER
from app.services.dictionary_manager import DICTIONARY
from app.services.translate_service import HISTORY
from app.api.v1.endpoint import api_router
from app.utils.logger import start_logger

from app.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

logger.debug("디버그 메시지가 보입니다")

# 응답 시간 측정 미들웨어
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 로거 초기화
    start_logger()
    
    # 시작 시 경로 설정 및 초기화
    DICTIONARY.initialize_dictionaries()
    
    # 번역 이력 초기화    
    HISTORY.initialize()
    
    # 모델 사전 로드
    if settings.PRELOAD_MODEL:
        try:
            await MANAGER.load(settings.OLLAMA_MODEL)            
            response = await ollamac.ping()
            result = response.get("message", {}).get("content", "").strip()
            print(f"모델 사전 로드 완료: {settings.OLLAMA_MODEL} : {result}")
        except Exception as e:
            raise RuntimeError(f"모델 사전 로드 실패: {str(e)}") from e
    
    yield  # 애플리케이션 실행 부분
    
    # 종료 시 정리 작업 (필요한 경우)    
    logger.info("애플리케이션이 종료됩니다...")    

    if MANAGER:
        await MANAGER.shutdown()

# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# 타이밍 미들웨어 추가
app.add_middleware(TimingMiddleware)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 허용할 도메인만 지정해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router)
app.include_router(api_router, prefix="/api/v1beta", tags=["v1beta"])

# 기본 엔드포인트
@app.get("/")
async def root():
    return {"message": "Translation Service API with Consistency"}
