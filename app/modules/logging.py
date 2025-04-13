"""
UTF-8 지원 로깅 서비스 (logging_service.py)

주요 개선사항:
1. 모든 로그 파일을 UTF-8로 작성하도록 개선
2. 파일 핸들러에 인코딩 설정 추가
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any
import codecs

from app.settings import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel( SRC_LOG_LEVELS["MODULE"] )

class TranslationLogger:
    @staticmethod
    def log_translation(source_lang: str, target_lang: str, source_text: str, translated_text: str) -> None:
        """
        번역 요청과 결과를 로그에 기록합니다.
        
        Args:
            source_lang: 원본 언어 코드
            target_lang: 대상 언어 코드
            source_text: 원본 텍스트
            translated_text: 번역된 텍스트
        """
        # logger.debug(f"번역 요청: {source_lang} -> {target_lang}, 원본: '{source_text}', 번역: '{translated_text}'")
        # 빈 텍스트 처리
        if source_text is None:
            source_text = ""
        if translated_text is None:
            translated_text = ""
            
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "source_language": source_lang,
            "target_language": target_lang,
            "source_text": source_text,
            "translated_text": translated_text,
            "characters": len(source_text) if source_text else 0
        }
        
        # 콘솔에 로그 출력
        logger.debug(f"번역: {source_lang} -> {target_lang}, 원본: '{source_text}', 번역: '{translated_text}'")
        
        # JSON 형식으로 로그 파일에 저장 (UTF-8 인코딩)
        try:
            with codecs.open("logs/translations.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"로그 파일 쓰기 오류: {str(e)}")
    
    @staticmethod
    def log_evaluation(source_text: str, translated_text: str, score: int, feedback: str) -> None:
        """
        번역 품질 평가 결과를 로그에 기록합니다.
        
        Args:
            source_text: 원본 텍스트
            translated_text: 번역된 텍스트
            score: 품질 점수 (0-100)
            feedback: 평가 피드백
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "source_text": source_text,
            "translated_text": translated_text,
            "quality_score": score,
            "feedback": feedback
        }
        
        # 콘솔에 로그 출력
        logger.info(f"번역 품질 평가: 점수={score}, 피드백: '{feedback}'")
        
        # JSON 형식으로 로그 파일에 저장 (UTF-8 인코딩)
        try:
            with codecs.open("logs/evaluations.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"평가 로그 파일 쓰기 오류: {str(e)}")
            
    @staticmethod
    def log_error(error_type: str, details: Dict[str, Any]) -> None:
        """
        오류를 로그에 기록합니다.
        
        Args:
            error_type: 오류 유형
            details: 오류 관련 세부 정보
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "details": details
        }
        
        logger.error(f"오류: {error_type} - {json.dumps(details, ensure_ascii=False)}")
        
        try:
            with codecs.open("logs/errors.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"오류 로그 파일 쓰기 오류: {str(e)}")

