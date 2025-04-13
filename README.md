# 🌐 Ollama 기반 번역 서비스 API

FastAPI와 Ollama를 활용한 번역 서비스 API 서버입니다. 이 프로젝트는 대규모 언어 모델(LLM)을 사용하여 텍스트 번역을 제공하고, 번역 품질을 평가하며, 외부 번역 사전을 관리하는 기능을 포함하고 있습니다.

## ✨ 주요 기능

- ✅ 언어 간 텍스트 번역 (LLM이 처리할 수 있는 언어)
- ✅ REST API 인터페이스 (FastAPI)
- ✅ 번역 품질 평가 및 개선 시스템 (선택 사항)
- ✅ 외부 JSON 파일을 통한 번역 사전 관리
- ✅ 번역 요청 및 결과 로깅
- ✅ 캐싱 시스템으로 중복 요청 최적화

## 📋 요구사항

- Python 3.12 이상 권장 (3.12로 개발되었음)
- [Ollama](https://github.com/ollama/ollama) 설치 및 실행
- Ollama 지원 LLM 모델
- Docker Desktop (Docker 사용 시)

## 🎯 주 사용처

본 프로젝트는 [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator/releases)의 Custom 서버 역할 용도로 작성되었습니다.

## 🚀 설치 방법

### Docker 사용 (권장)

1. **저장소 클론:**
   ```bash
   git clone https://github.com/mannago/CustomOllamaTranslatorServer.git
   cd CustomOllamaTranslatorServer
   ```

2. **환경 변수 설정:**
   `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 다음 값들을 설정하세요:
   ```
   OLLAMA_MODEL="huihui_ai/kanana-nano-abliterated"
   ```

3. **Docker Compose 실행:**
   ```bash
   docker compose up
   ```

4. 서버 빌드 및 모델 다운로드 대기 (모델 구성에 시간이 소요될 수 있습니다)

### 직접 구동

1. **Ollama 설치 및 모델 다운로드:**
   - Ollama 공식 사이트: https://ollama.com/
   ```bash
   ollama pull huihui_ai/kanana-nano-abliterated
   ```

2. **저장소 클론:**
   ```bash
   git clone https://github.com/mannago/CustomOllamaTranslatorServer.git
   cd CustomOllamaTranslatorServer
   ```

3. **가상 환경 생성 및 활성화:**
   ```bash
   python -m pip install virtualenv
   python -m virtualenv .venv
   
   # Linux/Mac
   source .venv/bin/activate
   
   # Windows
   .venv\Scripts\activate
   ```

4. **의존성 설치:**
   ```bash
   pip install -r requirements.txt
   ```

5. **환경 변수 설정:**
   `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 다음 값들을 설정하세요:
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL="huihui_ai/kanana-nano-abliterated"
   ```

## ▶️ 실행 방법

```bash
python run.py
```

서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

## 🧪 테스트 방법

```bash
curl -G "http://localhost:8000/translate?from=en&to=ko&text=Hello%20World"
```

예상 응답:
```
안녕하세요 세계
```

## 📚 API 사용 방법

### 번역 엔드포인트

```
GET http://localhost:8000/translate?from=en&to=ko&text=hello
```

응답:
```
안녕하세요
```

## 📘 번역 사전 관리

외부 JSON 파일을 통해 번역 사전을 관리할 수 있습니다. 기본 경로는 `resources/dictionaries/` 폴더입니다.

### 사전 파일 구조

- `resources/dictionaries/ko_dictionary.json`: 한국어 번역 사전
- `resources/dictionaries/ja_dictionary.json`: 일본어 번역 사전
- `resources/dictionaries/en_dictionary.json`: 영어 번역 사전
- `resources/dictionaries/lang_dictionary.json.example`: 번역 사전 예제 파일

번역 사전 JSON 파일 구조:
```json
{
  "ui": {
    "NEW GAME": "새 게임",
    "CONTINUE": "계속하기"
  },
  "legal": {
    "All Rights Reserved": "모든 권리 보유",
    "Version": "버전"
  }
}
```

## 🔍 번역 품질 평가 및 개선

번역 품질을 자동으로 평가하고 개선하는 기능이 구현되어 있습니다:

- 번역 결과를 0-100 점수로 평가
- 평가 기준:
  - 정확성: 40%
  - 유창성: 30%
  - 용어: 20%
  - 완전성: 10%
- 설정된 품질 기준(기본값: 90점) 미달 시 자동 재번역
- 최대 개선 시도 횟수 제한으로 무한 루프 방지
- 평가 결과 로깅 (`logs/evaluations.jsonl`)

## 📊 로깅 시스템

다양한 형태의 로그를 기록합니다:

| 로그 유형 | 파일 경로 |
|----------|---------|
| 일반 로그 | `logs/translation.log` |
| 번역 요청/결과 로그 | `logs/translations.jsonl` |
| 번역 평가 로그 | `logs/evaluations.jsonl` |
| 오류 로그 | `logs/errors.jsonl` |

## ⚙️ 환경 변수 설정

`.env` 파일이나 Docker 환경 변수를 통해 다음 설정을 조정할 수 있습니다:

### Ollama 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `OLLAMA_BASE_URL` | Ollama 호스트 URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | 사용할 Ollama 모델 | `huihui_ai/kanana-nano-abliterated` |
| `OLLAMA_TIMEOUT` | Ollama 요청 Timeout 시간 설정 (초) | `300` |
| `OLLAMA_SERVER_CHECK_ENABLE` | Ollama 서버확인 반복 실행 여부 | `False` |
| `OLLAMA_HEALTH_CHECK_ENABLE` | Ollama 주기적인 상태확인 실행 여부 | `False` |

### 성능 최적화 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `PRELOAD_MODEL` | 번역 요청 전 Ollama 모델 로드할지 여부 | `True` |

### 지원 언어 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `SUPPORTED_LANGUAGES` | 지원되는 언어 목록 (쉼표로 구분) | `en,ko` |

### 캐싱 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `ENABLE_CACHE` | 캐싱 활성화 여부 | `True` |
| `CACHE_EXPIRATION` | 캐시 만료 시간 (초) | `3600` |

### 사전 번역 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `ENABLE_DICTIONARY` | 사전 기반 번역 활성화 여부 | `True` |

### 번역 품질 평가 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `ENABLE_EVALUATION` | 번역 품질 평가 활성화 여부 | `False` |
| `QUALITY_THRESHOLD` | 번역 개선 재시도 품질 점수 기준치 (0-100) | `90` |
| `MAX_IMPROVEMENT_ATTEMPTS` | 최대 개선 시도 횟수 | `3` |

### 평가 제외 조건
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `MIN_TEXT_LENGTH_FOR_EVALUATION` | 평가에 필요한 최소 텍스트 길이 | `8` |
| `MAX_TEXT_LENGTH_FOR_EVALUATION` | 평가에 필요한 최대 텍스트 길이 | `1000` |

### 이력 관리 설정
| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `MAX_HISTORY_PER_LANG_PAIR` | 언어 쌍별 최대 이력 수 | `10` |

## 💡 번역 품질 개선 방안

1. **더 강력한 LLM 사용하기:**
   번역 품질은 LLM의 성능에 크게 의존합니다. OpenAI, Google Gemini, Anthropic Claude와 같은 더 강력한 LLM을 사용하여 품질을 향상시킬 수 있습니다.

2. **사전 개선 작업 적용하기:**
   번역 후 생성된 사전을 대형 모델(OpenAI, Gemini, Claude 등)에 제공하여 개선된 버전으로 변경하고 재번역을 시도합니다.

3. **수동 검수 및 피드백 반영하기:**
   번역 사전을 검수하여 원하는 형태로 변경 후 재번역합니다.

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)로 배포됩니다.