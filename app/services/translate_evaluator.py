"""
개선된 번역 품질 평가 서비스 (app/services/translation_evaluator.py)

주요 개선사항:
1. 외국어 혼합 감지 로직 강화
2. 특수문자 처리 로직 개선
3. 반복 학습형 피드백 시스템
"""
import json
import re
import logging
from typing import Dict, Any, Tuple, List

from app.modules.llm import ollamac
from app.models.llm import Message
from app.models.llm import EvaluationReseponse
from app.models.llm import TranslateReseponse
from app.models.llm import SystemPrompt
from app.models.llm import ImprovePrompt

from app.modules.logging import TranslationLogger
from app.utils.language_utils import get_language_name
from app.utils.string_utils import parse_llm_json_response
from app.settings import SRC_LOG_LEVELS, settings

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["SERVICE"])

class TranslationEvaluator:
    # 평가 이력을 저장하기 위한 클래스 변수
    _evaluation_history = {}  # 키: source_text, 값: [평가 이력 리스트]
    
    def clean_special_chars(self, text: str) -> str:
        """
        LLM에 전달하기 전에 허용된 특수문자만 남기고 제거합니다.
        
        Args:
            text: 처리할 텍스트
            
        Returns:
            str: 특수문자가 제거된 텍스트
        """
        if not text:
            return ""
        
        # 허용할 특수문자 목록: 마침표, 쉼표, 느낌표, 물음표, 싱글쿼터, 괄호, 기타 문장 부호
        allowed_special_chars = ['.', ',', '!', '?' ]
        
        # 정규식을 사용하여 허용된 특수문자와 일반 문자(알파벳, 숫자, 공백)만 유지
        pattern = r'[^\w\s' + re.escape(''.join(allowed_special_chars)) + ']'
        cleaned_text = re.sub(pattern, ' ', text)
        
        # 연속된 공백을 하나로 치환
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    def store_evaluation_history(self, source_text: str, evaluation: Dict[str, Any]) -> None:
        """
        번역 평가 이력을 저장합니다.
        
        Args:
            source_text: 원본 텍스트
            evaluation: 평가 정보 (점수, 피드백 등)
        """
        if source_text not in TranslationEvaluator._evaluation_history:
            TranslationEvaluator._evaluation_history[source_text] = []
        
        # 최대 5개까지만 저장
        if len(TranslationEvaluator._evaluation_history[source_text]) >= 5:
            TranslationEvaluator._evaluation_history[source_text].pop(0)
        
        TranslationEvaluator._evaluation_history[source_text].append(evaluation)
    
    def get_evaluation_history(self, source_text: str) -> List[Dict[str, Any]]:
        """
        특정 원본 텍스트에 대한 평가 이력을 반환합니다.
        
        Args:
            source_text: 원본 텍스트
            
        Returns:
            List[Dict[str, Any]]: 평가 이력 리스트
        """
        return TranslationEvaluator._evaluation_history.get(source_text, [])
    
    async def evaluate_translation(
        self, 
        source_text: str, 
        translated_text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Tuple[int, str]:
        """
        번역 품질을 평가하고 점수를 반환합니다.
        
        Args:
            source_text: 원본 텍스트
            translated_text: 번역된 텍스트
            source_lang: 원본 언어 코드
            target_lang: 대상 언어 코드
            
        Returns:
            Tuple[int, str]: (품질 점수 0-100, 평가 설명)
        """
        # 매우 짧은 텍스트는 평가가 어려우므로 기본 점수 반환
        if len(source_text) < 3 or len(translated_text) < 3:
            return 95, "매우 짧은 텍스트로 평가가 제한됨"
            
        # 동일한 텍스트인 경우 (번역이 필요 없는 숫자, 기호 등)
        if source_text == translated_text:
            return 100, "번역이 필요 없는 텍스트"
        
        # 평가 이력 가져오기
        evaluation_history = self.get_evaluation_history(source_text)
        
        prompt = ImprovePrompt(source_lang=source_lang, target_lang=target_lang)

        # 이전 평가 이력이 있으면 프롬프트에 추가
        if evaluation_history:
            history_text = "\n\nPrevious evaluation history:\n"
            for i, eval_item in enumerate(evaluation_history):
                history_text += f"{i+1}. Score: {eval_item.get('score', 'N/A')}, "
                history_text += f"Feedback: {eval_item.get('feedback', 'N/A')}\n"
            # system_prompt += history_text
            prompt.CUSTOM(history_text)

        system_prompt = prompt.build()

        normalize_source_lang = get_language_name(source_lang)
        normalize_target_lang = get_language_name(target_lang)

        user_prompt = f"""Source ({normalize_source_lang}): {source_text}
Translation ({normalize_target_lang}): {translated_text}

Evaluate this translation and provide a score and brief feedback in JSON format."""

        try:
            messages = []
            messages.append(  Message( role="system", content=system_prompt ) )
            messages.append(  Message( role="user", content=user_prompt ) )

            response = await ollamac.chat(
                messages=messages,
                format=EvaluationReseponse.model_json_schema(),
                timeout=settings.OLLAMA_TIMEOUT,
            )
            # logger.debug(f"Evaluation response: {response}")
            
            content = response.get("message", {}).get("content", "").strip()
            # logger.debug(f"Evaluation text: {content}")
            
            # JSON 추출 시도
            try:
                evaluation = parse_llm_json_response(content=content)
                
                # evaluation = json.loads(evaluation_text)
                score = int(evaluation.get("score", 0))
                feedback = evaluation.get("feedback", "평가 정보 없음")
                
                # 점수 범위 제한
                score = max(0, min(score, 100))
                
                # 평가 이력 저장
                self.store_evaluation_history(
                    source_text, 
                    {"score": score, "feedback": feedback, "translated_text": translated_text}
                )
                
                return score, feedback
            except (json.JSONDecodeError, ValueError) as e:
                # JSON 파싱 실패 시 기본값 반환
                error_msg = f"평가 결과 파싱 실패: {str(e)}, 받은 데이터: {content}"
                TranslationLogger.log_error("json_parse_error", {
                    "error": str(e),
                    "received_data": content,
                    "source_text": source_text
                })
                return 70, error_msg
                
        except Exception as e:
            error_msg = f"평가 프로세스 오류: {str(e)}"
            TranslationLogger.log_error("evaluation_error", {
                "error": str(e),
                "source_text": source_text,
                "translated_text": translated_text
            })
            return 70, error_msg

    async def improve_translation(
        self, 
        source_text: str, 
        previous_translation: str, 
        source_lang: str, 
        target_lang: str,
        feedback: str,
        word_mapping: Dict[str, str]
    ) -> str:
        """
        이전 번역을 개선합니다.
        
        Args:
            source_text: 원본 텍스트
            previous_translation: 이전 번역 텍스트
            source_lang: 원본 언어 코드
            target_lang: 대상 언어 코드
            feedback: 이전 번역에 대한 피드백
            
        Returns:
            str: 개선된 번역
        """
        # 특수문자 제거
        cleaned_source_text = self.clean_special_chars(source_text)
        cleaned_previous_translation = self.clean_special_chars(previous_translation)
        cleaned_feedback = self.clean_special_chars(feedback)
        
        # 평가 이력 가져오기
        evaluation_history = self.get_evaluation_history(source_text)

        # 번역 프롬프트 구성
        prompt = SystemPrompt(source_lang=source_lang, target_lang=target_lang)\
                .CRITICAL()\
                .WORD_MAPPING()\
                .RESPONSE_FORMAT()

        # 이전 평가 이력이 있으면 프롬프트에 추가
        if evaluation_history:
            history_text = "\n\nPrevious translation attempts:\n"
            for i, eval_item in enumerate(evaluation_history):
                history_text += f"{i+1}. Translation: {eval_item.get('translated_text', 'N/A')}\n"
                history_text += f"   Score: {eval_item.get('score', 'N/A')}, "
                history_text += f"Feedback: {eval_item.get('feedback', 'N/A')}\n"
            prompt.CUSTOM(history_text)

        system_prompt = prompt.build()

        nomalize_source_lang = get_language_name(source_lang)
        nomalize_target_lang = get_language_name(target_lang)

        user_prompt = f"""Source ({nomalize_source_lang}): {cleaned_source_text}
Previous Translation ({nomalize_target_lang}): {cleaned_previous_translation}
Feedback: {cleaned_feedback}

Provide an improved translation."""
        
        try:
            messages = []
            messages.append(  Message( role="system", content=system_prompt ) )
            messages.append(  Message( role="user", content=user_prompt ) )

            response = await ollamac.chat(
                messages=messages,
                format=TranslateReseponse.model_json_schema(),
                timeout=settings.OLLAMA_TIMEOUT,
            )
            
            content = response.get("message", {}).get("content", "").strip()
        
            # JSON 형식 추출 시도
            try:
                evaluation = parse_llm_json_response(content=content)
                
                improved_translation = evaluation.get("translation", "")
                word_mapping = evaluation.get("word_mapping", "")
                
                # 결과가 없는 경우 원래 번역 반환
                if not improved_translation:
                    return previous_translation, None
                
                return improved_translation, word_mapping
                
            except (json.JSONDecodeError, ValueError):
                # JSON 파싱 실패 시 원래 응답 텍스트를 사용
                # 따옴표 제거 등 후처리
                improved_translation = content.strip()
                if not improved_translation:
                    return previous_translation
                
                return improved_translation, word_mapping
                
        except Exception as e:
            # 예외 발생 시 원래 번역 반환
            TranslationLogger.log_error("improvement_error", {
                "error": str(e),
                "source_lang": source_lang,
                "target_lang": target_lang,
                "text": source_text
            })
            return previous_translation, word_mapping
        
EVALUATOR = TranslationEvaluator()