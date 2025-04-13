"""
개선된 언어 일관성 번역 서비스 (app/services/consistent_translator.py)

- 사용자 사전을 참조 프롬프트로 제공하도록 개선
- 긴 문장을 직접 대체하지 않고 LLM에 정보 제공
"""
import logging

from app.services.dictionary_manager import DICTIONARY
from app.services.translate_service import translate_text
from app.models.llm import SystemPrompt

from app.settings import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["SERVICE"])

class ConsistentTranslator:
    """
    언어 일관성을 보장하는 번역 서비스
    """
    @classmethod
    async def translate(
        cls,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        사전 참조 정보를 활용하여 텍스트를 번역합니다.
        
        Args:
            text: 번역할 텍스트
            source_lang: 원본 언어 코드
            target_lang: 대상 언어 코드
            
        Returns:
            str: 번역된 텍스트
        """
        # init
        if not source_lang:
            raise Exception("source_lang is required")
        
        if source_lang == target_lang:
            return text
        
        # 빈 텍스트 처리
        if not text or text.strip() == "":
            return ""

        # logger.debug(f"사전 참조 번역 요청: {text} (from {source_lang} to {target_lang})")
        # 사전에서 참조 정보 가져오기
        references = DICTIONARY.get_prompt_references(text, target_lang)
        
        # 참조 정보가 없으면 기본 번역 사용
        if not references:
            logger.debug("사전 참조 정보 없음, 기본 번역 사용")
            return await translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
    
        # 프롬프트 생성
        prompt = SystemPrompt(source_lang=source_lang, target_lang=target_lang)\
            .CRITICAL()\
            .WORD_MAPPING()\
            .RESPONSE_FORMAT()

        logger.debug(f"사전 참조 정보")
        # 참조 정보 추가        
        for i, ref in enumerate(references):
            prompt.CUSTOM(
                f"- \"{ref['term']}\" -> \"{ref['translation']}\"\n"
            )
            logger.debug(f"- \"{ref['term']}\" -> \"{ref['translation']}\"")
            
        system_prompt = prompt.RESPONSE_FORMAT().build()

        return await translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            system_prompt=system_prompt
        )
        