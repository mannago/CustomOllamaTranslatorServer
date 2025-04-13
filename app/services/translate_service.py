"""
개선된 Ollama 번역 서비스 (app/services/ollama_service.py)

주요 개선사항:
1. 외국어 혼합 방지 로직 강화
2. 특수문자 보존 로직 개선
3. 번역 품질 평가 시스템 강화
4. 번역 이력 관리 기능 최적화
"""

import httpx
import json
import re
import asyncio
import logging
from typing import List
from fastapi import HTTPException

from app.modules.llm import ollamac
from app.models.llm import Message
from app.models.llm import TranslateReseponse
from app.models.llm import SystemPrompt
from app.models.llm import WordMapping

from app.modules.logging import TranslationLogger
from app.services.dictionary_manager import DICTIONARY
from app.services.translate_history import HISTORY
from app.services.translate_evaluator import EVALUATOR
from app.utils.string_utils import parse_llm_json_response

from app.settings import settings
from app.settings import SRC_LOG_LEVELS


logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["SERVICE"])

# 간단한 인메모리 캐시 시스템
translation_cache = {}

def clean_special_chars(text: str) -> str:
    """
    LLM에 전달하기 전에 특수문자를 처리합니다.
    마침표, 쉼표, 따옴표 등 문장 부호는 보존합니다.
    
    Args:
        text: 처리할 텍스트
        
    Returns:
        str: 처리된 텍스트
    """
    if not text:
        return ""
        
    allowed_special_chars = ['!', '?', '.', ',', '\'', '"']
    
    # 정규식을 사용하여 허용된 특수문자와 일반 문자(알파벳, 숫자, 공백)만 유지
    pattern = r'[^\w\s' + re.escape(''.join(allowed_special_chars)) + ']'
    cleaned_text = re.sub(pattern, ' ', text)
    
    # 연속된 공백을 하나로 치환
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text

async def translate_text(source_lang: str, target_lang: str, text: str, system_prompt:str = None) -> str:
    """
    Ollama를 사용하여 텍스트를 번역합니다.
    
    Args:
        source_lang: 원본 언어 코드 (없으면 자동 감지)
        target_lang: 대상 언어 코드
        text: 번역할 텍스트
    
    Returns:
        str: 번역된 텍스트
    """
    # 초기화
    if not source_lang:
        source_lang = "auto"

    # 빈 텍스트 처리
    if not text or text.strip() == "":
        return ""
        
    # 캐시 확인
    cache_key = f"{source_lang}:{target_lang}:{text}"
    if settings.ENABLE_CACHE and cache_key in translation_cache:
        cached_result = translation_cache[cache_key]
        # 캐시된 결과를 로그에 기록 (캐시 히트 표시)
        TranslationLogger.log_translation(
            source_lang=source_lang, 
            target_lang=target_lang, 
            source_text=text, 
            translated_text=f"{cached_result} (cache)"
        )
        return cached_result
    
    # UI 번역 사전에서 먼저 확인 (전체 텍스트 일치)
    if settings.ENABLE_DICTIONARY:
        dictionary_translation = DICTIONARY.get_translation(text, target_lang)
        if dictionary_translation is not None:  # None이 아닌 경우만 처리
            # 사전에서 찾은 번역 결과를 로그에 기록
            TranslationLogger.log_translation(
                source_lang=source_lang, 
                target_lang=target_lang, 
                source_text=text, 
                translated_text=f"{dictionary_translation} (dictionary)"
            )
            
            # 번역 이력에 추가
            HISTORY.add_history(
                source_lang=source_lang,
                target_lang=target_lang,
                source_text=text,
                translated_text=dictionary_translation,
                quality_score=100  # 사전 번역은 최고 품질로 간주
            )
            
            # 캐시 저장
            if settings.ENABLE_CACHE:
                translation_cache[cache_key] = dictionary_translation
            
            return dictionary_translation
    
    # 알려진 용어 또는 구문 매핑을 찾아 프롬프트에 포함
    dictionary_mappings = {}
    found_terms = []
    
    if settings.ENABLE_DICTIONARY:
                
        # 사전 객체 가져오기
        dictionary = DICTIONARY.get_dictionary(target_lang)
        if dictionary:
            # 알려진 용어 또는 구문 (UI 요소, 버튼 등)이 전체 텍스트에 포함되어 있는지 확인
            for category, translations in dictionary.items():
                for source_term, target_term in translations.items():
                    # 빈 문자열 건너뛰기
                    if not source_term.strip():
                        continue
                        
                    # 대소문자 구분 없이 검색 (소문자로 통일)
                    source_term_lower = source_term.lower()
                    text_lower = text.lower()
                    
                    # 독립된 단어나 구문으로 존재하는지 확인 (단어 경계 확인)
                    if (f" {source_term_lower} " in f" {text_lower} " or 
                        text_lower == source_term_lower or
                        text_lower.startswith(f"{source_term_lower} ") or
                        text_lower.endswith(f" {source_term_lower}")):
                        
                        # 알려진 용어를 프롬프트에 추가할 매핑에 포함
                        dictionary_mappings[source_term] = target_term
                        found_terms.append(source_term)
    
    # 이전 번역 이력 가져오기
    previous_translations = HISTORY.get_history(
        source_lang=source_lang,
        target_lang=target_lang
    )
    
    # 특수문자 처리
    cleaned_text = clean_special_chars(text)
    # cleaned_text = text

    if system_prompt is None:
        prompt = SystemPrompt(source_lang=source_lang, target_lang=target_lang)\
                .CRITICAL()\
                .WORD_MAPPING()\
                .RESPONSE_FORMAT()

        # 사전에서 발견된 용어 매핑이 있으면 프롬프트에 추가
        if dictionary_mappings:
            prompt.REFERENCES(references=dictionary_mappings)

        # 이전 번역 이력이 있으면 프롬프트에 추가 (최대 5개)
        if previous_translations:
            history_prompt = "\nPREVIOUS TRANSLATIONS (for reference):\n"
            for i, item in enumerate(previous_translations[-5:]):
                history_prompt += f"{i+1}. Source: \"{item['source_text']}\"\n"
                history_prompt += f"   Translation: \"{item['translated_text']}\"\n"
            prompt.CUSTOM(history_prompt)

        system_prompt = prompt.build()
        # logger.debug(f"시스템 프롬프트: {system_prompt}")
    
    prompt = f"Translate: {cleaned_text}"
    
    try:
        messages = []
        messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))


        translation_response = await ollamac.chat(
            messages=messages,
            stream=False,
            format=TranslateReseponse.model_json_schema(),
            timout=settings.OLLAMA_TIMEOUT
        )
        contents = translation_response.get("message", {}).get("content", "").strip()

        # JSON 파싱 시도
        try:
            response_content = parse_llm_json_response(content=contents)
            translated_text = response_content.get("translation", "")
            word_mapping = response_content.get("word_mapping", "")
            
            # JSON에서 번역 결과를 얻지 못한 경우 원본 응답 사용
            if not translated_text:
                translated_text = response_content
        except (json.JSONDecodeError, ValueError):
            # JSON 파싱 실패 시 전체 응답 텍스트 사용
            translated_text = response_content
        
        # 결과가 없는 경우
        if not translated_text:
            error_detail = "번역 결과를 얻지 못했습니다."
            TranslationLogger.log_error("empty_response", {
                "source_lang": source_lang,
                "target_lang": target_lang,
                "text": text
            })
            raise HTTPException(
                status_code=500,
                detail=error_detail
            )
            
        # 번역이 완료되면 품질 평가 시작 (짧은 텍스트는 평가 제외)
        quality_score = None
        feedback = None
        
        if (settings.ENABLE_EVALUATION and 
            len(text) >= settings.MIN_TEXT_LENGTH_FOR_EVALUATION and
            len(text) <= settings.MAX_TEXT_LENGTH_FOR_EVALUATION and
            len(translated_text) >= 2):

            translated_text, word_mapping = await translate_evaluator(
                text=text, 
                translated_text=translated_text, 
                source_lang=source_lang, 
                target_lang=target_lang, 
                word_mapping=word_mapping
            )

        # 번역 결과 로깅
        TranslationLogger.log_translation(
            source_lang=source_lang, 
            target_lang=target_lang, 
            source_text=text, 
            translated_text=translated_text
        )
        
        # 번역 이력에 추가
        HISTORY.add_history(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=text,
            translated_text=translated_text,
            quality_score=quality_score,
            feedback=feedback
        )

        # 캐시 저장
        if settings.ENABLE_CACHE:
            translation_cache[cache_key] = translated_text
            
            # 캐시 크기 제한 (간단한 구현)
            if len(translation_cache) > 1000:
                # 캐시의 가장 오래된 항목 10% 제거
                keys_to_remove = list(translation_cache.keys())[:100]
                for k in keys_to_remove:
                    translation_cache.pop(k, None)
        
        try:
            # 번역 매핑에 추가
            logger.debug(f"사전 매핑 처리: {word_mapping}")
            DICTIONARY.process_word_mapping(word_mapping, target_lang )
        except Exception as e:
            logger.debug(f"사전 매핑 처리 오류: {str(e)}")
        
        return translated_text
    
    except httpx.RequestError as e:
        error_detail = f"Ollama 서비스 연결 오류: {str(e)}"
        TranslationLogger.log_error("connection_error", {
            "error": str(e),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "text": text
        })
        raise HTTPException(
            status_code=503,
            detail=error_detail
        )


async def translate_evaluator(text: str, translated_text:str , source_lang: str, target_lang: str, word_mapping: List[WordMapping]) -> str:
    """
    번역 품질 평가를 위한 텍스트 변환
    """
    try:
        # 평가 수행 - 시간 제한 설정 (최대 5초)
        quality_score, feedback = await asyncio.wait_for(
            EVALUATOR.evaluate_translation(
                source_text=text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang
            ),
            timeout=5.0
        )
        
        # 로그에 평가 결과 기록
        TranslationLogger.log_evaluation(
            source_text=text,
            translated_text=translated_text,
            score=quality_score,
            feedback=feedback
        )
        
        # 외국어 혼합이 감지되었거나 품질 기준 미달 시 재시도
        if quality_score < settings.QUALITY_THRESHOLD:
            print(f"번역 품질 점수({quality_score})가 기준({settings.QUALITY_THRESHOLD})에 미달, 재시도합니다.")
            
            # 최대 개선 시도 횟수만큼 반복
            attempts = 0
            current_translation = translated_text
            best_score = quality_score
            best_translation = translated_text
            best_feedback = feedback
            
            while attempts < settings.MAX_IMPROVEMENT_ATTEMPTS:
                try:
                    print(f"번역 개선 시도 {attempts+1}/{settings.MAX_IMPROVEMENT_ATTEMPTS}")                                
                
                    enhancement_feedback = feedback
                    
                    # 번역 개선 시도
                    improved_translation, word_mapping = await asyncio.wait_for(
                        EVALUATOR.improve_translation(
                            source_text=text,
                            previous_translation=current_translation,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            feedback=enhancement_feedback,
                            word_mapping=word_mapping
                        ),
                        timeout=settings.OLLAMA_TIMEOUT  # 개선에는 더 많은 시간 허용
                    )
                    
                    # 개선된 번역이 이전과 동일하면 더 이상 시도하지 않음
                    if improved_translation == current_translation:
                        print("번역 개선 없음, 종료합니다.")
                        break
                    
                    # 개선된 번역 평가
                    improved_score, improved_feedback = await asyncio.wait_for(
                        EVALUATOR.evaluate_translation(
                            source_text=text,
                            translated_text=improved_translation,
                            source_lang=source_lang,
                            target_lang=target_lang
                        ),
                        timeout=settings.OLLAMA_TIMEOUT
                    )
                    
                    print(f"개선된 번역 품질 점수: {improved_score} (이전: {best_score})")
                    
                    # 로그에 평가 결과 기록
                    TranslationLogger.log_evaluation(
                        source_text=text,
                        translated_text=improved_translation,
                        score=improved_score,
                        feedback=improved_feedback
                    )
                    
                    # 더 나은 점수면 업데이트
                    if improved_score > best_score:
                        best_score = improved_score
                        best_translation = improved_translation
                        best_feedback = improved_feedback
                        print(f"더 나은 번역 발견: 점수 {best_score}")
                    
                    # 품질 기준 충족 시 종료
                    if improved_score >= settings.QUALITY_THRESHOLD:
                        print(f"품질 기준 충족: {improved_score} >= {settings.QUALITY_THRESHOLD}")
                        break
                    
                    # 다음 시도를 위해 현재 번역 업데이트
                    current_translation = improved_translation
                    feedback = improved_feedback
                    
                except asyncio.TimeoutError:
                    print(f"번역 개선 시도 {attempts+1} 시간 초과")
                except Exception as e:
                    print(f"번역 개선 오류: {str(e)}")
                
                attempts += 1
            
            # 최종 결과 사용
            translated_text = best_translation
            quality_score = best_score
            feedback = best_feedback
            print(f"최종 번역 품질 점수: {quality_score}")
            
    except asyncio.TimeoutError:
        # 평가 시간 초과 시 기본값 사용
        quality_score = 80
        feedback = "평가 시간 초과"
        TranslationLogger.log_error("evaluation_timeout", {
            "source_text": text,
            "translated_text": translated_text
        })
    except Exception as e:
        # 평가 실패 시 기본값 사용
        quality_score = 80
        feedback = f"평가 오류: {str(e)}"
        TranslationLogger.log_error("evaluation_error", {
            "error": str(e),
            "source_text": text,
            "translated_text": translated_text
        })
    
    return translated_text, word_mapping