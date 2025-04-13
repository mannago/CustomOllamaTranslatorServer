import time
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List
from datetime import datetime

from ollama import AsyncClient
from pydantic import BaseModel

from app.models.llm import Message
from app.settings import settings, SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MODULE"])

class BaseLLM(ABC):
    """
    대형 언어 모델(LLM)을 위한 기본 추상 클래스
    
    모든 LLM 구현체는 이 클래스를 상속받아 공통 인터페이스를 구현해야 합니다.
    """
    
    @abstractmethod
    async def chat(self, 
                  messages: List[Message],
                  **kwargs ) -> Message:
        """
        채팅 메시지 생성
        
        Args:
            messages: 채팅 히스토리 메시지 목록
            options: 생성 옵션
            
        Returns:
            Message: 생성된 응답 메시지
        """
        pass

# ===== Ollama LLM 클라이언트 =====

class OllamaLLM(BaseLLM):
    """
    Ollama 대형 언어 모델 클라이언트
    
    자체 호스팅 LLM인 Ollama API를 사용하여 상호작용하기 위한 클라이언트 구현
    """
    
    def __init__(self,
                 api_base: str = settings.OLLAMA_BASE_URL,
                 model: str = settings.OLLAMA_MODEL ):
        """
        Ollama LLM 초기화
        
        Args:
            api_base (str, 선택): Ollama API 기본 URL
            model (str, 선택): 사용할 Ollama 모델 이름
        """
        self.client = AsyncClient( host=api_base )
        self.model = model
        self.timeout = settings.OLLAMA_TIMEOUT # 기본 타임아웃 설정 (초 단위)

    def get_client(self):
        """Ollama API 클라이언트를 반환합니다."""
        return self.client

    # async def load(self, model_name: str, max_retries=10, retry_delay=5):
    #     """Ollama 모델을 로드합니다."""
    #     model = model_name or self.model
    #     logger.debug(f"OLLAMA 호스트: {settings.OLLAMA_BASE_URL}, 모델 로드: {model}")
        
    #     # 올라마 서버 준비 확인
    #     server_ready = False
    #     for attempt in range(max_retries):
    #         try:
    #             # 올라마 서버 상태 확인
    #             health_response = await self.client.ps()
    #             server_ready = True
    #             logger.debug(f"올라마 서버 준비 완료: {health_response}")
    #             break
    #         except Exception as e:
    #             logger.warning(f"올라마 서버 준비 중... 재시도 {attempt+1}/{max_retries}: {str(e)}")
    #             await asyncio.sleep(retry_delay)
        
    #     if not server_ready:
    #         raise RuntimeError("올라마 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        
    #     start_time = time.time()
        
    #     try:
    #         # 사용 가능한 모델 확인
    #         for attempt in range(max_retries):
    #             try:
    #                 response = await self.client.list()
    #                 available_models = [m.model for m in response.models]
    #                 logger.debug(f"사용 가능한 모델: {available_models}")
                    
    #                 # 정확히 일치하는지 확인
    #                 if model in available_models:
    #                     logger.info(f"모델 '{model}'이(가) 이미 로드되었습니다.")
    #                     return None
                        
    #                 # 태그가 없는 기본 이름이 포함되어 있는지 확인
    #                 base_model_name = model.split(':')[0]  # ':' 이전의 기본 모델 이름만 추출
    #                 matching_models = [m for m in available_models if m.startswith(base_model_name)]
                    
    #                 if matching_models:
    #                     logger.info(f"모델 기본 이름 '{base_model_name}'이(가) 일치하는 모델 발견: {matching_models}")
    #                     return None
                    
    #                 # 모델이 없으면 다운로드 진행
    #                 break
    #             except Exception as e:
    #                 logger.warning(f"모델 목록 조회 실패, 재시도 {attempt+1}/{max_retries}: {str(e)}")
    #                 if attempt == max_retries - 1:
    #                     raise
    #                 await asyncio.sleep(retry_delay)
                    
    #         # 모델 다운로드 시작
    #         logger.info(f"모델 '{model}'을(를) 다운로드합니다...")
    #         print(f"모델 '{model}'을(를) 다운로드합니다...")
            
    #         # 진행 상태 변수 초기화
    #         current_status = ""
    #         last_status_update = ""
    #         download_started = time.time()
            
    #         async for progress in await self.client.pull(model=model, stream=True):
    #             # 진행 상황 출력
    #             current_time = time.time()
    #             elapsed = current_time - download_started
    #             elapsed_str = f"{int(elapsed // 60)}분 {int(elapsed % 60)}초"
                
    #             if 'status' in progress:
    #                 status = progress.get('status', '')
                    
    #                 # 상태가 변경된 경우 새 줄에 출력
    #                 if current_status != status:
    #                     if current_status:  # 이전 상태가 있었으면 줄바꿈
    #                         print()
    #                     current_status = status
    #                     print(f"상태: {status}", end="")
                    
    #                 status_update = ""
    #                 if 'download' in progress:
    #                     download_info = progress.get('download', {})
    #                     completed = download_info.get('completed', 0)
    #                     total = download_info.get('total', 0)
                        
    #                     if total > 0:
    #                         percent = (completed / total) * 100
    #                         status_update = f" - {completed}/{total} ({percent:.2f}%) - 경과: {elapsed_str}"
    #                 elif 'digest' in progress:
    #                     digest = progress.get('digest', '')
    #                     status_update = f" - 다이제스트: {digest[:10]}... - 경과: {elapsed_str}"
    #                 else:
    #                     status_update = f" - 경과: {elapsed_str}"
                    
    #                 # 상태 업데이트가 변경된 경우만 갱신
    #                 if status_update != last_status_update:
    #                     last_status_update = status_update
    #                     print(f"\r상태: {status}{status_update}", end="")
            
    #         # 다운로드 완료 후 모델 로드 확인
    #         logger.info("모델 다운로드 완료, 모델 로드 확인 중...")
            
    #         # 모델 로드 확인 및 대기
    #         model_loaded = False
    #         for attempt in range(max_retries):
    #             try:
    #                 # 모델 로드 확인
    #                 response = await self.client.list()
    #                 available_models = [m.model for m in response.models]
                    
    #                 if model in available_models:
    #                     model_loaded = True
    #                     break
                        
    #                 logger.debug(f"모델 로드 대기 중... {attempt+1}/{max_retries}")
    #                 await asyncio.sleep(retry_delay)
    #             except Exception as e:
    #                 logger.warning(f"모델 로드 확인 실패, 재시도 {attempt+1}/{max_retries}: {str(e)}")
    #                 await asyncio.sleep(retry_delay)
            
    #         if not model_loaded:
    #             raise RuntimeError(f"모델 '{model}'이(가) 다운로드 후 로드되지 않았습니다.")
            
    #         # 총 소요 시간 계산
    #         end_time = time.time()
    #         total_time = end_time - start_time
    #         total_time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
            
    #         print(f"\n\n모델 다운로드 및 로드가 완료되었습니다!")
    #         print(f"총 소요 시간: {total_time_str}")
    #         logger.info(f"모델 '{model}' 다운로드 및 로드 완료 (소요 시간: {total_time_str})")
            
    #         return None

    #     except Exception as e:
    #         # 소요 시간 포함하여 오류 로깅
    #         end_time = time.time()
    #         total_time = end_time - start_time
    #         total_time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
            
    #         error_msg = f"모델 '{model}' 로드 실패 (시도 시간: {total_time_str}): {str(e)}"
    #         logger.error(error_msg)
    #         raise RuntimeError(error_msg) from e

    async def ping(self, timeout:int = settings.OLLAMA_TIMEOUT):
        """Ollama API에 연결합니다."""
        logger.debug(f"OLLAMA 호스트: {settings.OLLAMA_BASE_URL}, 모델 핑: {self.model}, 타임아웃: {timeout}초, content: just only say pong")
        async with asyncio.timeout(timeout):
            try:
                response = await self.client.chat(model=self.model, messages=[{'role': 'user', 'content': 'just only say pong'}])
                return response
            except Exception as e:
                logger.error(f"모델 핑 실패: {str(e)}")
                raise RuntimeError(f"모델 핑 실패: {str(e)}") from e
    
    async def chat(self, messages: List[Message], model: str = None, format: BaseModel = None, **kwargs):

        if model is None:
            model = self.model
    
        payload = {
            "model": model,
            "messages": messages,
            "format": format,
            "stream": False,
            "options": {}
        }

        options_item = ["temperature", "max_tokens", "top_p", "timeout", "stop"]

        # 기본 옵션 설정
        for key in options_item:
            if key in kwargs:
                payload["options"][key] = kwargs[key]

        timeout = self.timeout
        if payload["options"].get("timeout"):
            self.timeout = payload["options"]["timeout"]            

        # 타임아웃 컨텍스트 매니저 사용
        async with asyncio.timeout(timeout):
            # 나머지 코드는 동일...
            response = await self.client.chat(
                **payload
            )

        return response    

ollamac = OllamaLLM()