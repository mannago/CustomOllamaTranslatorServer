import json
import os
from datetime import datetime

from app.settings import settings, HISTORY_FILE

# 번역 이력 관리를 위한 클래스
class TranslationHistory:
    _history = {}  # 언어 쌍별 이력 저장 (source_lang:target_lang -> [번역 이력])
    _history_file = HISTORY_FILE
    _max_history_per_lang_pair = 10
    
    def initialize(self):
        """번역 이력을 파일에서 로드합니다."""
        if os.path.exists(self._history_file):
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except Exception as e:
                print(f"번역 이력 로드 실패: {str(e)}")
                self._history = {}
    
    def add_history(self, source_lang: str, target_lang: str, source_text: str, translated_text: str, 
                    quality_score: int = None, feedback: str = None):
        """번역 이력을 추가합니다."""
        key = f"{source_lang}:{target_lang}"
        
        if key not in self._history:
            self._history[key] = []
        
        # 중복 제거 (동일한 원본 텍스트가 있으면 제거)
        self._history[key] = [item for item in self._history[key] if item.get('source_text') != source_text]
        
        # 새 이력 추가 (피드백 정보도 포함)
        self._history[key].append({
            'source_text': source_text,
            'translated_text': translated_text,
            'quality_score': quality_score,
            'feedback': feedback,  # 피드백 정보 추가
            'timestamp': datetime.now().isoformat()
        })
        
        # 최대 개수 유지
        if len(self._history[key]) > self._max_history_per_lang_pair:
            self._history[key] = self._history[key][-self._max_history_per_lang_pair:]
        
        # 파일에 저장
        self._save_history()
    
    def get_history(self, source_lang: str, target_lang: str) -> list:
        """특정 언어 쌍에 대한 번역 이력을 반환합니다."""
        key = f"{source_lang}:{target_lang}"
        return self._history.get(key, [])
    
    def _save_history(self):
        """번역 이력을 파일에 저장합니다."""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"번역 이력 저장 실패: {str(e)}")

HISTORY = TranslationHistory()