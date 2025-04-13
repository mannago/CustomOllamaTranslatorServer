"""
개선된 사용자 정의 단어 사전 관리 (app/services/dictionary_manager.py)

- 긴 문장과 짧은 문장 처리 방식 구분
- 사전 용어를 LLM 프롬프트 참조 자료로 제공
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional

from app.models.llm import WordMapping 
from app.settings import settings, DICTIONARIES_PATH
from app.settings import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["SERVICE"])

class DictionaryManager:
    """
    동적 사용자 정의 단어 사전 관리 클래스
    """
    # 기본 사전 저장 경로
    _base_path = DICTIONARIES_PATH
    
    # 사전 캐시
    _dictionaries = {}
    
    # 커스텀 항목 우선 순위 카테고리
    _priority_categories = ["character_names", "place_names", "custom_terms", "ui", "general"]
    
    # 직접 대체 최대 길이 (이보다 긴 문장은 참조용으로만 사용)
    MAX_DIRECT_REPLACEMENT_LENGTH = 30
    
    def initialize_dictionaries(self) -> None:
        """
        애플리케이션 시작 시 모든 지원 언어에 대한 사전을 미리 로드합니다.
        이 메서드는 애플리케이션 시작 시 한 번 호출되어야 합니다.
        """
        logger.info("사전 초기화 시작")
        logger.info(f"사전 경로: {self._base_path}")
        
        # 사전 디렉토리 확인 및 생성
        if not os.path.exists(self._base_path):
            os.makedirs(self._base_path, exist_ok=True)
            logger.info(f"사전 디렉토리 생성: {self._base_path}")
        
        # 지원되는 모든 언어의 사전 파일 확인 및 로드
        for lang in settings.SUPPORTED_LANGUAGES:
            filepath = os.path.join(self._base_path, f"{lang}_dictionary.json")
            
            # 파일이 존재하는지 확인
            if os.path.exists(filepath):
                # 사전 로드
                self.get_dictionary(lang)
        
        logger.info(f"사전 초기화 완료: {len(self._dictionaries)}개 언어 로드됨")
    
    def _create_default_dictionary(self, lang_code: str) -> None:
        """
        언어 코드에 대한 기본 사전 파일을 생성합니다.
        
        Args:
            lang_code: 언어 코드
        """
        # base_dict = self._system_dictionary.get(lang_code, {})
        base_dict = {
            "character_names": {},
            "place_names": {},
            "custom_terms": {},
            "ui": {}
        }
            
        # 파일에 저장
        filepath = os.path.join(self._base_path, f"{lang_code}_dictionary.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(base_dict, f, ensure_ascii=False, indent=2)
                logger.info(f"기본 사전 파일 생성: {filepath}")
        except Exception as e:
            logger.error(f"사전 파일 저장 오류: {filepath}, {str(e)}")
    
    def get_dictionary(self, lang_code: str) -> Dict[str, Dict[str, str]]:
        """
        지정된 언어 코드에 대한 단어 사전을 가져옵니다.
        사전이 아직 로드되지 않았으면 로드합니다.
        
        Args:
            lang_code: 언어 코드 (예: "ko", "ja", "en")
            
        Returns:
            Dict[str, Dict[str, str]]: 카테고리별 단어 사전
        """
        # 이미 로드된 사전이 있으면 반환
        if lang_code in self._dictionaries:
            return self._dictionaries[lang_code]
        
        # 파일 경로 생성
        filepath = os.path.join(self._base_path, f"{lang_code}_dictionary.json")
        
        # 파일이 존재하는지 확인
        if not os.path.exists(filepath):
            # 기본 사전 생성
            self._create_default_dictionary(lang_code)
        
        # 파일에서 사전 로드
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                self._dictionaries[lang_code] = translations
                
                logger.info(f"사전 로드 완료: {lang_code}, 항목 수: {sum(len(v) for v in translations.values())}")
                return translations
        except Exception as e:
            logger.error(f"사전 파일 로드 오류: {filepath}, {str(e)}")
            return self._dictionaries[lang_code]
    
    def get_translation(self, text: str, target_lang: str) -> Optional[str]:
        """
        특정 텍스트에 대한 번역을 사전에서 찾습니다.
        짧은 문장은 직접 대체, 긴 문장은 None 반환 (참조용으로만 사용).
        
        Args:
            text: 번역할 텍스트
            target_lang: 대상 언어 코드
            
        Returns:
            Optional[str]: 번역이 있으면 번역된 텍스트, 없으면 None
        """
        # logger.debug(f"get_translation called with text: {text}, target_lang: {target_lang}")
        if not text or not text.strip():
            return text
            
        # 긴 문장 처리 방식 변경
        if len(text) > self.MAX_DIRECT_REPLACEMENT_LENGTH and " " in text:
            # 긴 문장은 None 반환 (직접 대체하지 않고 참조용으로만 사용)
            return None
            
        # 사전 가져오기
        dictionary = self.get_dictionary(target_lang)
        if not dictionary:
            return None
            
        # 정확한 매치 확인
        for category in self._priority_categories:
            if category in dictionary:
                if text in dictionary[category]:
                    return dictionary[category][text]
                    
                # 대소문자 구분 없이 확인
                text_lower = text.lower()
                for source, translation in dictionary[category].items():
                    if source.lower() == text_lower:
                        return translation
        
        # 부분 매치 (고유명사 등 포함된 경우)
        result = text
        replacements_made = False
        original_words = text.split()
        
        # 우선순위가 높은 카테고리부터 처리
        for category in self._priority_categories:
            if category in dictionary:
                for source, translation in dictionary[category].items():
                    if len(source) > 2:  # 최소 길이 제한 (너무 짧은 단어는 제외)
                        # 단어 경계 확인 (온전한 단어 대체)
                        pattern = r'\b' + re.escape(source) + r'\b'
                        if re.search(pattern, result, re.IGNORECASE):
                            result = re.sub(pattern, translation, result, flags=re.IGNORECASE)
                            replacements_made = True
        
        if replacements_made:
            # 혼합 언어 검사: 결과에 단어가 남아있는지 확인
            # 1. 원문의 모든 단어가 번역되었는지 확인
            result_words = result.split()
            
            # 2. 원문에 있는 영어 단어가 결과에도 그대로 있는지 확인 (대소문자 무시)
            contains_untranslated = False
            for orig_word in original_words:
                # 단순 구두점이나 숫자는 건너뛰기
                if len(orig_word) <= 1 or orig_word.isdigit():
                    continue
                    
                # 영어 알파벳으로만 구성된 단어가 결과에 그대로 남아있는지 확인
                if re.match(r'^[a-zA-Z]+$', orig_word):
                    if any(res_word.lower() == orig_word.lower() for res_word in result_words):
                        contains_untranslated = True
                        break
            
            # 3. 번역되지 않은 단어가 있다면 부분 번역 결과를 사용하지 않음
            if contains_untranslated:
                return None
                
            return result
            
        return None
    
    def get_prompt_references(self, text: str, target_lang: str) -> List[Dict[str, str]]:
        """
        텍스트에 포함된 용어들의 사전 참조 정보를 가져옵니다.
        긴 문장에서 LLM 프롬프트에 추가할 참조 자료로 사용됩니다.
        
        Args:
            text: 번역할 텍스트
            target_lang: 대상 언어 코드
            
        Returns:
            List[Dict[str, str]]: 참조 정보 목록 [{"term": "원본", "translation": "번역"}]
        """
        if not text or not text.strip():
            return []
            
        # 사전 가져오기
        dictionary = self.get_dictionary(target_lang)
        if not dictionary:
            return []
            
        references = []
        
        # 텍스트에서 사전 용어 찾기
        for category in self._priority_categories:
            if category in dictionary:
                for source, translation in dictionary[category].items():
                    if len(source) > 2:  # 최소 길이 제한
                        # 단어 경계 또는 공백 확인
                        pattern = r'\b' + re.escape(source) + r'\b'
                        if re.search(pattern, text, re.IGNORECASE) or f" {source} " in f" {text} ":
                            references.append({
                                "term": source,
                                "translation": translation
                            })
        
        return references
    
    def process_word_mapping(self, word_mapping: List[WordMapping], target_lang: str) -> None:
        """
        LLM 응답에서 반환된 word_mapping을 처리하여 사전에 추가합니다.
        
        Args:
            word_mapping: LLM에서 반환한 단어 매핑 딕셔너리
            target_lang: 대상 언어 코드
        """
        for item in word_mapping:

            category: str = item["category"]
            original: str = item["word"]
            translated: str = item["translation"]

            if category is None or "" == category.strip():
                # 카테고리 자동 결정
                category = "custom_terms"  # 기본값

            # 단어 후처리
            category = category.strip()
            original = original.strip()
            translated = translated.strip()
                
            # 번역 사전에 추가
            self.add_translation(
                text=original,
                translation=translated,
                target_lang=target_lang,
                category=category,
                confidence=0.9  # LLM의 번역은 신뢰도가 높다고 가정
            )


    def add_translation(self, text: str, translation: str, target_lang: str, category: str = "custom_terms", confidence: float = 0.8) -> bool:
        """
        번역 사전에 새 항목을 추가하고 파일에 저장합니다.
        
        Args:
            text: 원본 텍스트
            translation: 번역된 텍스트
            target_lang: 대상 언어 코드
            category: 번역 카테고리
            confidence: 신뢰도 점수 (0.0~1.0)
            
        Returns:
            bool: 성공 여부
        """
        # 빈 텍스트 처리
        if not text or not text.strip() or not translation or not translation.strip():
            return False
            
        # 신뢰도가 낮으면 무시
        if confidence < 0.5:
            return False
            
        # 너무 긴 텍스트는 사전에 추가하지 않음
        if len(text) > self.MAX_DIRECT_REPLACEMENT_LENGTH:
            return False
            
        # 숫자나 특수문자만 있는 경우 제외
        if re.match(r'^[\d\W]+$', text):
            return False
            
        # 사전 가져오기 (없으면 생성)
        if target_lang not in self._dictionaries:
            self._dictionaries[target_lang] = {}
        
        dictionary = self._dictionaries[target_lang]
        
        # 카테고리 확인 (없으면 생성)
        if category not in dictionary:
            dictionary[category] = {}
        
        # 번역 추가
        dictionary[category][text] = translation
        
        # 파일에 저장
        filepath = os.path.join(self._base_path, f"{target_lang}_dictionary.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=2)
            logger.info(f"사전에 단어 추가: {text} -> {translation} ({category})")
            return True
        except Exception as e:
            logger.error(f"사전 파일 저장 오류: {filepath}, {str(e)}")
            return False
    
    def reload_dictionary(self, lang_code: str) -> bool:
        """
        특정 언어의 사전을 다시 로드합니다.
        
        Args:
            lang_code: 언어 코드
            
        Returns:
            bool: 성공 여부
        """
        # 캐시에서 제거
        if lang_code in self._dictionaries:
            del self._dictionaries[lang_code]
        
        # 다시 로드
        dictionary = self.get_dictionary(lang_code)
        return bool(dictionary)

DICTIONARY = DictionaryManager()