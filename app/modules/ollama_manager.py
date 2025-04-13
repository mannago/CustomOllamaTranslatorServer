import logging

import asyncio
import time

from app.modules.llm import ollamac

from app.settings import SRC_LOG_LEVELS, settings

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MODULE"])

class OllamaManager:
    """
    Ollama 모델 관리 및 다운로드를 위한 클래스입니다.
    Ollama API를 사용하여 모델을 다운로드하고 로드하며, 모델이 VRAM에서 제거되지 않도록 핑을 보냅니다.
    """

    def __init__(self):
        self.client = ollamac.get_client()
        self.ping_task = None
        self._shutdown_event = asyncio.Event()

    async def check_server(self, max_retries=10, retry_delay=5):
        """Ollama 서버가 실행 중인지 확인합니다."""
        for attempt in range(max_retries):
            if self._shutdown_event.is_set():
                logger.info("서버 확인 작업이 취소되었습니다.")
                return False
            else:
                try:
                    # 올라마 서버 상태 확인
                    health_response = await self.client.ps()
                    logger.debug(f"올라마 서버 준비 완료: {health_response}")
                    return True
                except Exception as e:
                    logger.warning(f"올라마 서버 준비 중... 재시도 {attempt+1}/{max_retries}: {str(e)}")
                    await asyncio.sleep(retry_delay)
        
        raise RuntimeError("올라마 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")

    async def check_model_availability(self, model_name, max_retries=5, retry_delay=2):
        """모델이 이미 로드되어 있는지 확인합니다."""
        for attempt in range(max_retries):
            try:
                response = await self.client.list()
                available_models = [m.model for m in response.models]
                logger.debug(f"사용 가능한 모델: {available_models}")
                
                # 정확히 일치하는지 확인
                if model_name in available_models:
                    logger.info(f"모델 '{model_name}'이(가) 이미 로드되었습니다.")
                    return True
                    
                # 태그가 없는 기본 이름이 포함되어 있는지 확인
                base_model_name = model_name.split(':')[0]  # ':' 이전의 기본 모델 이름만 추출
                matching_models = [m for m in available_models if m.startswith(base_model_name)]
                
                if matching_models:
                    logger.info(f"모델 기본 이름 '{base_model_name}'이(가) 일치하는 모델 발견: {matching_models}")
                    return True
                
                # 모델이 없음
                return False
            except Exception as e:
                logger.warning(f"모델 목록 조회 실패, 재시도 {attempt+1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)

    async def download_model(self, model_name, max_retries=10, retry_delay=5):
        """Ollama 모델을 다운로드합니다."""
        # 서버 상태 확인
        await self.check_server(max_retries, retry_delay)
        
        # 모델이 이미 있는지 확인
        if await self.check_model_availability(model_name, max_retries, retry_delay):
            return True
        
        # 모델 다운로드 시작
        start_time = time.time()
        logger.info(f"모델 '{model_name}'을(를) 다운로드합니다...")
        print(f"모델 '{model_name}'을(를) 다운로드합니다...")
        
        try:
            # 진행 상태 변수 초기화
            current_status = ""
            last_status_update = ""
            download_started = time.time()
            
            async for progress in await self.client.pull(model=model_name, stream=True):
                # 진행 상황 출력
                current_time = time.time()
                elapsed = current_time - download_started
                elapsed_str = f"{int(elapsed // 60)}분 {int(elapsed % 60)}초"
                
                if 'status' in progress:
                    status = progress.get('status', '')
                    
                    # 상태가 변경된 경우 새 줄에 출력
                    if current_status != status:
                        if current_status:  # 이전 상태가 있었으면 줄바꿈
                            print()
                        current_status = status
                        print(f"상태: {status}", end="")
                    
                    status_update = ""
                    if 'download' in progress:
                        download_info = progress.get('download', {})
                        completed = download_info.get('completed', 0)
                        total = download_info.get('total', 0)
                        
                        if total > 0:
                            percent = (completed / total) * 100
                            status_update = f" - {completed}/{total} ({percent:.2f}%) - 경과: {elapsed_str}"
                    elif 'digest' in progress:
                        digest = progress.get('digest', '')
                        status_update = f" - 다이제스트: {digest[:10]}... - 경과: {elapsed_str}"
                    else:
                        status_update = f" - 경과: {elapsed_str}"
                    
                    # 상태 업데이트가 변경된 경우만 갱신
                    if status_update != last_status_update:
                        last_status_update = status_update
                        print(f"\r상태: {status}{status_update}", end="")
            
            # 총 소요 시간 계산
            end_time = time.time()
            total_time = end_time - start_time
            total_time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
            
            print(f"\n\n모델 다운로드가 완료되었습니다!")
            print(f"총 소요 시간: {total_time_str}")
            logger.info(f"모델 '{model_name}' 다운로드 완료 (소요 시간: {total_time_str})")
            
            return True

        except Exception as e:
            # 소요 시간 포함하여 오류 로깅
            end_time = time.time()
            total_time = end_time - start_time
            total_time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
            
            error_msg = f"모델 '{model_name}' 다운로드 실패 (시도 시간: {total_time_str}): {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def wait_for_model_loading(self, model_name, max_retries=30, retry_delay=5):
        """모델이 완전히 로드될 때까지 기다립니다."""
        logger.info(f"모델 '{model_name}' 로드 대기 중...")
        print(f"모델 '{model_name}' 로드 대기 중...")
        
        start_time = time.time()
        model_loaded = False
        
        for attempt in range(max_retries):
            try:
                # 모델이 사용 가능한지 확인
                if await self.check_model_availability(model_name):
                    # 간단한 모델 쿼리를 시도하여 실제 사용 가능한지 확인
                    try:
                        test_response = await self.client.generate(
                            model=model_name,
                            prompt="test",
                            options={"num_predict": 1}  # 최소한의 토큰만 생성
                        )
                        model_loaded = True
                        break
                    except Exception as e:
                        logger.debug(f"모델이 아직 쿼리에 응답할 준비가 되지 않았습니다: {str(e)}")
                
                # 아직 로드되지 않음
                elapsed = time.time() - start_time
                elapsed_str = f"{int(elapsed // 60)}분 {int(elapsed % 60)}초"
                print(f"\r모델 로드 대기 중... (경과: {elapsed_str}) {attempt+1}/{max_retries}", end="")
                await asyncio.sleep(retry_delay)
                
            except Exception as e:
                logger.warning(f"모델 로드 확인 실패, 재시도 {attempt+1}/{max_retries}: {str(e)}")
                await asyncio.sleep(retry_delay)
        
        print()  # 줄바꿈
        
        if not model_loaded:
            raise RuntimeError(f"모델 '{model_name}'이(가) 로드되지 않았습니다. 시간 초과.")
        
        # 총 소요 시간 계산
        end_time = time.time()
        total_time = end_time - start_time
        total_time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
        
        logger.info(f"모델 '{model_name}' 로드 완료 (소요 시간: {total_time_str})")
        print(f"모델 '{model_name}' 로드 완료 (소요 시간: {total_time_str})")
        
        return True

    async def ping_model(self, model_name, interval=60):
        """모델이 VRAM에서 제거되지 않도록 주기적으로 핑을 보냅니다."""
        logger.info(f"모델 '{model_name}' 핑 시작 (간격: {interval}초)")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # 가벼운 쿼리 실행
                    test_response = await self.client.generate(
                        model=model_name,
                        prompt="ping",
                        options={"num_predict": 1}  # 최소한의 토큰만 생성
                    )
                    logger.debug(f"모델 '{model_name}' 핑 성공")
                except Exception as e:
                    logger.warning(f"모델 '{model_name}' 핑 실패: {str(e)}")
                
                # wait_for을 사용하여 shutdown_event를 감지하면서 대기
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=interval
                    )
                except asyncio.TimeoutError:
                    # 타임아웃은 정상적인 상황이므로 무시
                    pass
        except asyncio.CancelledError:
            logger.info(f"모델 '{model_name}' 핑 작업이 취소되었습니다.")
        except Exception as e:
            logger.error(f"모델 '{model_name}' 핑 작업 중 오류 발생: {str(e)}")
        finally:
            logger.info(f"모델 '{model_name}' 핑 작업 종료")

    async def load(self, model_name: str, max_retries=1, retry_delay=1, keep_alive=False, ping_interval=60):
        """Ollama 모델을 다운로드하고 로드합니다. 선택적으로 핑을 유지합니다."""
        model = model_name or self.model
        logger.debug(f"OLLAMA 호스트: {settings.OLLAMA_BASE_URL}, 모델 로드: {model}")

        if settings.OLLAMA_SERVER_CHECK_ENABLE:
            logger.info("서버 체크 활성화")
            max_retries = 10  # 서버 체크를 활성화합니다.
            retry_delay = 5
        
        if settings.OLLAMA_HEALTH_CHECK_ENABLE:
            logger.info("헬스 체크 활성화")
            keep_alive = True  # 헬스 체크를 활성화합니다.
        
        # 1. 모델 다운로드
        await self.download_model(model, max_retries, retry_delay)
        
        # 2. 모델 로드 대기
        await self.wait_for_model_loading(model, max_retries, retry_delay)
        
        # 3. 필요한 경우 핑 작업 시작
        if keep_alive:
            # 백그라운드 태스크로 핑 시작
            self.ping_task = asyncio.create_task(self.ping_model(model, ping_interval))
            logger.info(f"모델 '{model}' 핑 작업이 백그라운드에서 실행 중입니다.")
        
        return None
    
    async def shutdown(self):
        """모든 백그라운드 작업을 정상적으로 종료합니다."""
        logger.info("Ollama 관리자 종료 중...")
        
        # 종료 이벤트 설정
        self._shutdown_event.set()
        
        # ping_task가 있으면 취소
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
            
        logger.info("Ollama 관리자 종료 완료")
    
MANAGER = OllamaManager()