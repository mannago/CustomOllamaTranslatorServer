from abc import ABC
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.utils.language_utils import get_language_name

class Message(BaseModel):
    """채팅 메시지 모델"""
    role: str = Field(..., description="메시지 역할 (예: system, user, assistant)")
    content: str = Field(..., description="메시지 내용")
    
    @field_validator('role')
    def validate_role(cls, v):
        allowed_roles = ['system', 'user', 'assistant', 'tool', 'function']
        if v not in allowed_roles:
            raise ValueError(f"허용되지 않는 역할입니다. 허용 역할: {', '.join(allowed_roles)}")
        return v

class WordMapping(BaseModel):
    word: str = Field(..., description="단어")
    translation: str = Field(..., description="번역")
    category: str = Field(..., description="카테고리 (예: character_names, place_names)")
    
class TranslateReseponse(BaseModel):
    """API 응답 모델"""
    translation: str = Field(..., description="번역된 텍스트")
    word_mapping: List[WordMapping] = Field(default_factory=list, description="단어 매핑 정보")

class EvaluationReseponse(BaseModel):
    """API 응답 모델"""
    score: int = Field(..., description="점수 (0-100)")
    feedback: str = Field(..., description="피드백 내용 (예: '문법 오류', '자연스러운 번역')")


class Prompt(ABC):
    """프롬프트 모델"""

    def __init__(self,source_lang: str, target_lang: str):
        self.source_lang = get_language_name(source_lang)
        self.target_lang = get_language_name(target_lang)
        self._parts = []

    def _add_part(self, text):
        """내부적으로 프롬프트 부분을 추가"""
        self._parts.append(text)
        return self
    
    def CUSTOM(self, text):
        """사용자 정의 프롬프트 부분 추가"""
        self._add_part(text)
        return self
    
    def build(self):
        """최종 프롬프트 문자열 반환"""
        return "\n\n".join(self._parts)

class SystemPrompt(Prompt):
    """
    번역 시스템 프롬프트를 구성하는 함수입니다.
    각 섹션별로 메서드를 제공하여 필요에 따라 프롬프트를 구성할 수 있습니다.
    
    Args:
        source_lang: 원본 언어
        target_lang: 대상 언어
        
    Returns:
        SystemPrompt 객체: 프롬프트 구성을 위한 메서드를 포함하는 객체
    """
    def __init__(self, source_lang, target_lang):
        super().__init__(source_lang, target_lang)

        # 기본 소개 부분 추가
        prompt = f"""You are a professional translator from '{self.source_lang}' to '{self.target_lang}'.
Translate the text exactly as provided, maintaining the original meaning, tone, nuance, and punctuation."""
        
        self._add_part(prompt)
    
    def CRITICAL(self):
        """중요 번역 규칙 추가"""
        #- Translate EVERYTHING - do not omit any part of the original text
        prompt = f"""CRITICAL TRANSLATION RULES:
- Use ONLY '{self.target_lang}' language in your translation - NO foreign words, NO mixing languages
- If there is no corresponding translation, write it as it is pronounced in '{self.target_lang}'.
- Preserve ALL punctuation including periods, commas, ellipses (...), exclamation marks, etc.
- Maintain the intensity and emotion of the original text
- Translate idioms and expressions naturally into '{self.target_lang}' culture
- Provide ONLY the translated text with no explanations or notes        
- Return only translated results
- DO NOT USE md5 format
- If there is a previous translation history, the tone should be the same.
- PRIORITIZE CONSISTENCY: If provided with previous translation terms in 'references', use these translations for consistency unless they significantly distort the meaning in the current context
- Mistakes decrease trustworthiness. Verify and answer accurately to avoid mistakes."""
        
        self._add_part(prompt)
        return self
    
    def WORD_MAPPING(self):
        """단어 매핑 지침 추가"""

        prompt = f"""## TRANSLATION DICTIONARY USAGE:
When translating, use the provided translation dictionary to ensure consistency with previously translated terms. The dictionary is organized by categories to help you find relevant translations quickly.

### Dictionary Categories:
1. **Part of Speech Categories**
   - `nouns`: General nouns (people, places, things, concepts)
   - `verbs`: Action words in their base form
   - `adjectives`: Words that describe nouns
   - `adverbs`: Words that modify verbs, adjectives, or other adverbs
   - `pronouns`: Words that replace nouns
   - `prepositions`: Words that show relationships between other words
   - `conjunctions`: Words that connect clauses or sentences
   - `interjections`: Exclamatory words

2. **Special Vocabulary Categories**
   - `proper_nouns`: Names of specific people, places, characters, or entities
   - `technical_terms`: Specialized vocabulary related to specific fields
   - `game_ui`: Terms related to user interface elements in games
   - `idioms`: Expressions with meanings different from their individual words
   - `phrases`: Common multi-word expressions

3. **Thematic Categories**
   - `body_parts`: Terms for parts of the human/creature body
   - `emotions`: Words describing feelings and emotional states
   - `actions`: Specific types of activities or behaviors
   - `objects`: Physical items and artifacts
   - `settings`: Environmental and location descriptions
   
### Translation Process:
1. When you encounter a word or phrase for translation, first check if it exists in any of the dictionary categories.
2. If found, use the provided '{self.target_lang}' translation to maintain consistency.
3. If a word appears in multiple categories with different translations, consider the context to choose the appropriate translation.
4. If not found, translate it appropriately and remember your translation for future consistency.
5. For phrases and sentences, try to identify individual terms that have existing translations and integrate them into your complete translation.

## IMPORTANT ABOUT WORD MAPPING:
1. The "word_mapping" field should ONLY include:
   - Proper nouns (names of people, places, organizations, brands)
   - Cultural terms and concepts that require specific translation
   - Technical terms, specialized vocabulary, and jargon
   - Idiomatic expressions and phrases with non-literal meanings
   - Terms that appear multiple times and require consistent translation
2. Do NOT include common grammatical elements:
   - Example In English: articles (the, a, an), basic prepositions (of, to, in), common pronouns (I, you, he)
   - Example In Korean: 조사 (은/는/이/가), 일반 접속사, 기본 대명사
3. Focus on 5-15 key terms that truly need special attention for consistency
4. Verify that each term you include has a genuine translation (not identical to source)
5. Use the appropriate category from the dictionary structure above for each word_mapping entry"""

        self._add_part(prompt)
        return self
    
    def REFERENCES(self, references=None):
        """이전 번역 참조 정보 추가"""
        if not references:
            return self
            
        ref_text = "PREVIOUS TRANSLATION REFERENCES:\nTo ensure consistency, prioritize these translations for recurring terms:\n"
        ref_items = []
        
        for ref in references:
            if "term" in ref and "translation" in ref:
                ref_items.append(f"- \"{ref['term']}\" → \"{ref['translation']}\"")
        
        if ref_items:
            ref_text += "\n".join(ref_items)
            self._add_part(ref_text)
        
        return self

    def RESPONSE_FORMAT(self):
        """응답 형식 추가"""
        format_text = '''## RESPONSE RULE:
- The translation field should contain the full translated text.
- The word_mapping field must be a list of key phrases or proper nouns in the original text, each with its translation and a category (e.g., "character_names", "place_names").
- Return only the JSON response without additional explanation or formatting.
- DO NOT USE md5 format
- All values must be in valid JSON syntax.

## RESPONSE FORMAT:
{ 
  "translation": "your translation here", 
  "word_mapping": [
    { "word": "Sara", "translation": "사라", "category": "proper_nouns" },
    { "word": "Willsdrey Village", "translation": "윌스드레이 마을", "category": "place_names" },
    { "word": "examine", "translation": "살펴보다", "category": "verbs" }
  ]
}'''
        self._add_part(format_text)
        return self

class ImprovePrompt(Prompt):
    """
    번역 품질 개선 프롬프트를 구성하는 함수입니다.
    
    Args:
        source_lang: 원본 언어
        target_lang: 대상 언어
        
    Returns:
        ImprovePrompt 객체: 프롬프트 구성을 위한 메서드를 포함하는 객체
    """
    def __init__(self, source_lang, target_lang):
        super().__init__(source_lang, target_lang)

        # 기본 소개 부분 추가
        # 번역 프롬프트 구성
        prompt = f"""You are a professional translation quality evaluator.
Your task is to evaluate the quality of translation from {self.source_lang} to {self.target_lang}.

Evaluate based on these criteria:
1. Accuracy (40%): Does the translation convey the original meaning correctly?
2. Fluency (30%): Does the translation sound natural in {self.target_lang}?
3. Terminology (20%): Are domain-specific terms correctly translated?
4. Completeness (10%): Is all content from the source text included?

Score Guidelines:
90-100: Excellent, professional quality
80-89: Good, minor issues
70-79: Acceptable, some errors
60-69: Poor, significant issues
Below 60: Unacceptable, major errors

CRITICAL: If the translation contains mixed languages (words from languages other than {self.target_lang}), score it below 50.
For example, if translating to Korean and you see Spanish words like "alguien" or Japanese characters like "かの", score it below 50.

YOU MUST RETURN ONLY A VALID JSON OBJECT with this exact format:
{{
  "score": <integer between 0-100>,
  "feedback": "<brief explanation of issues or why it's good>"
}}

No additional text before or after the JSON. Only the JSON object.
NOT USE md5 format."""
        self._add_part(prompt)