import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List

# .env 파일 로드
load_dotenv()

#####################################
## logging
#####################################

BASEPATH = Path(__file__).resolve().parent

GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL == "":   
    GLOBAL_LOG_LEVEL = "INFO"

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

log_sources = [
    "MAIN",
    "CONFIG",
    "MODULE",
    "SERVICE",
    "MODEL",
    "ROUTER",    
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in logging.getLevelNamesMapping():
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    logger.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

logger.setLevel(SRC_LOG_LEVELS["CONFIG"])

#####################################
## PATHS
#####################################

# 리소스 경로
RESOURCES_PATH = Path( BASEPATH.parent / os.getenv("RESOURCES_PATH", "resources") ).resolve()  # 리소스 파일 경로
_DICTIONARIES_PATH = RESOURCES_PATH / Path( "dictionaries" ) # 번역 파일 경로

DICTIONARIES_PATH: str = str( _DICTIONARIES_PATH )
HISTORY_FILE: str = str( Path( RESOURCES_PATH / "translation_history.json" ).resolve() ) # 번역 이력 파일 경로 )

logger.debug(f"리소스 경로: {RESOURCES_PATH}")
logger.debug(f"사전 경로: {_DICTIONARIES_PATH}")

# 로그 경로
LOG_PATH = os.environ.get("LOG_PATH", "logs").upper()
LOG_FILE: str= str(  Path( Path(LOG_PATH) / "translation.log" ).resolve() ) # 번역 이력 파일 경로

# 폴더 생성
PATHS : List[Path] = [ Path(LOG_PATH), _DICTIONARIES_PATH ]

try:
    for path in PATHS:
        path.exists() or os.makedirs(path, exist_ok=True )  # 디렉토리 생성
except Exception as e:
    raise RuntimeError(f"폴더 생성 실패: {e}") from e

# 파일 로깅을 위한 설정 (UTF-8 인코딩 적용)
class UTF8FileHandler(logging.FileHandler):
    """UTF-8 인코딩을 사용하는 파일 핸들러"""
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

# # TimedRotatingFileHandler 추가
# log_file_path = os.path.join(LOG_PATH, "translation.log")
# file_handler = TimedRotatingFileHandler(
#     log_file_path,
#     when='midnight',  # 매일 자정에 로테이션
#     interval=1,       # 1일마다
#     backupCount=30,   # 30일분 보관
#     encoding='utf-8'
# )
# file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# logger.addHandler(file_handler)

#####################################
## Settings
#####################################

class Settings(BaseSettings):
    # 애플리케이션 설정
    APP_NAME: str = "Translation Service API"
    
    # Ollama 설정
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "huihui_ai/kanana-nano-abliterated")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 초 단위 (기본값: 300초)
    OLLAMA_SERVER_CHECK_ENABLE: bool = os.getenv("OLLAMA_SERVER_CHECK_ENABLE", "False").lower() in ["true", "1", "yes"]
    OLLAMA_HEALTH_CHECK_ENABLE: bool = os.getenv("OLLAMA_HEALTH_CHECK_ENABLE", "False").lower() in ["true", "1", "yes"]
    
    
    # 성능 최적화 설정
    PRELOAD_MODEL: bool = os.getenv("PRELOAD_MODEL", "True").lower() in ["true", "1", "yes"]
    
    # 지원하는 언어 코드 목록
    # SUPPORTED_LANGUAGES: list = ["en", "ko", "ja", "zh", "es", "fr", "de", "ru", "pt", "ar"]
    SUPPORTED_LANGUAGES: list = os.getenv("SUPPORTED_LANGUAGES", "en,ko").split(",")
    
    # 캐싱 설정
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() in ["true", "1", "yes"]
    CACHE_EXPIRATION: int = int(os.getenv("CACHE_EXPIRATION", "3600"))  # 초 단위 (1시간)

    # 사전 번역 설정
    ENABLE_DICTIONARY: bool = os.getenv("ENABLE_DICTIONARY", "True").lower() in ["true", "1", "yes"]
    
    # 번역 품질 평가 설정 (.env 파일에서 조정 가능)
    ENABLE_EVALUATION: bool = os.getenv("ENABLE_EVALUATION", "False").lower() in ["true", "1", "yes"]
    QUALITY_THRESHOLD: int = int(os.getenv("QUALITY_THRESHOLD", "90"))  # 품질 점수 기준치 (0-100)
    MAX_IMPROVEMENT_ATTEMPTS: int = int(os.getenv("MAX_IMPROVEMENT_ATTEMPTS", "3"))  # 최대 개선 시도 횟수
    
    # 평가 제외 조건 (.env 파일에서 조정 가능)
    MIN_TEXT_LENGTH_FOR_EVALUATION: int = int(os.getenv("MIN_TEXT_LENGTH_FOR_EVALUATION", "8"))  # 평가에 필요한 최소 텍스트 길이
    MAX_TEXT_LENGTH_FOR_EVALUATION: int = int(os.getenv("MAX_TEXT_LENGTH_FOR_EVALUATION", "1000"))  # 평가에 필요한 최대 텍스트 길이
    
    # 이력 관리 설정
    MAX_HISTORY_PER_LANG_PAIR: int = int(os.getenv("MAX_HISTORY_PER_LANG_PAIR", "10"))  # 언어 쌍별 최대 이력 수
    
settings = Settings()