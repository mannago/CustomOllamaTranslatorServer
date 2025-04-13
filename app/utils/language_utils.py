def normalize_language_code(lang_code: str) -> str:
    """
    언어 코드를 정규화합니다. (e.g., 'korean' -> 'ko', 'eng' -> 'en')

    Args:
        lang_code: 정규화할 언어 코드

    Returns:
        str: 정규화된 언어 코드 (2자리 ISO 639-1) 또는 실패 시 원본 소문자 반환
    """
    # 대체 언어 코드 매핑
    code_mapping = {
        "korean": "ko",
        "english": "en",
        "japanese": "ja",
        "chinese": "zh",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "russian": "ru",
        "portuguese": "pt",
        "arabic": "ar",
        # 일반적인 코드 변환
        "kor": "ko",
        "eng": "en",
        "jpn": "ja",
        "chn": "zh",
        "esp": "es",
        "fra": "fr",
        "deu": "de",
        "rus": "ru",
        "por": "pt",
        "ara": "ar"
        # 필요시 더 많은 매핑 추가
    }

    if not lang_code:
        return ""

    # 소문자로 변환
    normalized = lang_code.lower().strip() # 양쪽 공백 제거 추가

    # 매핑된 코드가 있으면 반환
    if normalized in code_mapping:
        return code_mapping[normalized]

    # 이미 2자리 코드면 그대로 반환 (단, 알파벳인지 확인)
    if len(normalized) == 2 and normalized.isalpha():
        return normalized

    # 3자리 코드 등 다른 형식일 경우, 매핑에 없으면 일단 원본 소문자 반환
    # 또는 여기서 오류를 발생시키거나 None을 반환하는 정책을 사용할 수도 있습니다.
    return normalized # 또는 "" 또는 None 반환 고려

def get_language_name(lang_code: str) -> str:
    """
    언어 코드에 해당하는 언어 이름을 반환합니다.

    Args:
        lang_code: 언어 코드 (정규화 전/후 모두 가능)

    Returns:
        str: 언어 이름 또는 "Unknown"
    """
    # 정규화된 코드 사용
    normalized_code = normalize_language_code(lang_code)
    language_names = {
        "en": "English",
        "ko": "Korean",
        "ja": "Japanese",
        "zh": "Chinese",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ru": "Russian",
        "pt": "Portuguese",
        "ar": "Arabic",
        # 설정 파일의 SUPPORTED_LANGUAGES 외의 언어 이름도 정의해 둘 수 있음
        "hi": "Hindi",
        "it": "Italian",
        "nl": "Dutch",
        "pl": "Polish",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "th": "Thai"
    }

    return language_names.get(normalized_code, "Unknown")
