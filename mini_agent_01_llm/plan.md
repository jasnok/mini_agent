# 브라우저 영상 분석·음성 안내 및 음성 영어 번역 통합 개발 계획

> 작성 기준: 현재 프로젝트의 Streamlit → FastAPI → OpenAI 연결 구조와 수업 코드 스타일을 유지한다.  
> 현재 단계에서는 계획만 수립하며, 아래 기능 코드는 아직 구현하지 않는다.

## 통합 목표

이 계획은 다음 두 기능을 하나의 멀티모달 프로젝트에 통합한다.

1. **영상 프레임 분석·음성 안내**: 브라우저에서 동영상 파일 또는 카메라 영상을 표시하고, 사용자가 선택한 순간의 프레임을 캡처해 백엔드에서 이미지 분석한 뒤 한국어 음성으로 안내한다.
2. **음성 영어 번역**: 브라우저에서 한국어 음성을 녹음해 백엔드로 전송하고, STT → 영어 번역 → 영어 TTS를 수행해 원문·번역문·합성 음성을 제공한다.

```text
[영상 기능]
브라우저 영상/카메라 → 현재 프레임 캡처 → 이미지 분석 → 한국어 TTS → 음성 재생

[음성 기능]
브라우저 마이크 → 음성 녹음 → STT → 영어 번역 → 영어 TTS → 텍스트 표시·음성 재생
```

두 기능은 기존 `media_router.py`, `media_service.py`, `api_client.py`, OpenAI 설정과 TTS 구현을 공유한다. 영상 원본과 음성 원본은 영구 저장하지 않는 것을 기본 원칙으로 한다.

## 1. 프로젝트 분석

### 1.1 현재 기술 스택

- Python 기반 단일 저장소
- 프론트엔드: Streamlit (`frontend/app.py`, `frontend/app_pages/`)
- 백엔드: FastAPI + Uvicorn (`backend/app/main.py`)
- HTTP 클라이언트: HTTPX (`frontend/core/api_client.py`)
- 요청·응답 검증: Pydantic (`backend/app/schemas.py`)
- 파일 업로드: FastAPI `UploadFile` + `python-multipart`
- 외부 AI 서비스: OpenAI, Gemini, Ollama
- 현재 멀티모달 기능: OpenAI 이미지 분석 및 OpenAI TTS
- 설정 관리: `python-dotenv`, 프로젝트 루트 `.env`, `backend/app/config.py`
- 테스트: Pytest + FastAPI `TestClient` (`backend/tests/test_api.py`)
- 패키지 관리: 루트 `requirements.txt`를 사용하는 pip 방식

### 1.2 기존 폴더 구조 요약

```text
mini_agent_01_llm/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI 생성 및 라우터 등록
│  │  ├─ config.py               # .env 로드 및 Settings
│  │  ├─ schemas.py              # Pydantic 요청·응답 모델
│  │  ├─ providers.py            # LLM Provider 호출
│  │  ├─ routers/
│  │  │  ├─ agent_router.py
│  │  │  └─ media_router.py      # 이미지 분석 및 TTS API
│  │  └─ services/
│  │     └─ media_service.py     # 이미지 검증·분석 및 TTS
│  └─ tests/
│     └─ test_api.py
├─ frontend/
│  ├─ app.py                     # Streamlit 페이지 등록 및 내비게이션
│  ├─ app_pages/
│  │  ├─ 07_image_analysis.py    # 파일 업로드 UI 참고 대상
│  │  └─ 08_tts.py               # 음성 출력 UI 참고 대상
│  ├─ clients/
│  │  └─ agent_client.py
│  └─ core/
│     └─ api_client.py           # 공통 백엔드 HTTP 호출
├─ learning_unit/
│  └─ 06_openai_tts.py           # OpenAI TTS 학습 예제
├─ .env                          # 실제 설정값(내용은 분석하지 않음)
├─ .env.example                  # 공개 가능한 환경변수 예시
├─ requirements.txt
└─ README.md
```

### 1.3 재사용할 기존 코드와 작성 방식

- [ ] `frontend/app_pages/07_image_analysis.py`의 업로드·spinner·오류 표시 흐름을 재사용한다.
- [ ] `frontend/app_pages/08_tts.py`의 `st.audio` 출력과 합성 음성 고지를 재사용한다.
- [ ] `frontend/core/api_client.py`의 `BackendAPIError`, HTTPX 예외 변환 방식을 유지한다.
- [ ] `backend/app/routers/media_router.py`에 음성 번역 엔드포인트를 추가하여 멀티모달 API를 한 라우터에 모은다.
- [ ] `backend/app/services/media_service.py`의 API 키 검사, 입력 검증, OpenAI 클라이언트 호출 방식을 확장한다.
- [ ] `backend/app/schemas.py`에 결과 모델을 추가하고 Pydantic 검증 방식을 유지한다.
- [ ] `backend/tests/test_api.py`의 monkeypatch 기반 외부 API 격리 방식을 유지한다.
- [ ] `backend/app/config.py`의 불변 `Settings` dataclass와 루트 `.env` 로드 방식을 유지한다.

### 1.4 추가·변경 범위

- 음성 번역용 Streamlit 페이지 `frontend/app_pages/09_voice_translation.py`를 추가한다.
- 영상 기능은 현재 프레임을 브라우저에서 `canvas`로 캡처해야 하므로 `frontend/video_app/`에 최소 React/Vite 화면을 두는 방식을 기본안으로 한다. Streamlit 커스텀 컴포넌트를 채택할 경우에는 이 폴더 대신 컴포넌트 폴더 하나만 추가한다.
- 기존 `media_router.py`, `media_service.py`, `schemas.py`, `config.py`, `api_client.py`, `app.py`, `test_api.py`, `.env.example`, `README.md`를 최소 수정한다.
- 현재 루트에 `.gitignore`가 확인되지 않았으므로 새로 만들고 `.env`, `.venv/`, `__pycache__/`, 테스트 캐시를 제외한다.
- 기존 파일을 삭제할 필요는 없다. 저장소에 있는 `__pycache__`는 소스가 아니므로 Git 추적 여부를 확인한 뒤 추적 중이면 별도 정리한다.

## 2. 요구사항 정리

### 2.1 핵심 기능과 사용자 흐름

#### A. 영상 프레임 분석·음성 안내

- [ ] 사용자가 동영상 파일을 선택하거나 카메라 사용 권한을 허용한다.
- [ ] 브라우저의 `<video>` 요소에서 영상을 표시한다.
- [ ] 사용자가 원하는 시점에 현재 프레임을 JPEG로 한 번 캡처한다.
- [ ] 캡처 이미지를 기존 이미지 분석 API로 보내고 분석 결과를 화면에 표시한다.
- [ ] 분석 결과의 `summary`를 기존 TTS API로 보내 한국어 MP3를 생성한다.
- [ ] 이전 음성을 정리한 뒤 최신 안내 음성을 한 번 재생한다.

#### B. 음성 영어 번역

- [ ] 사용자가 음성 처리 및 합성 음성 사용 안내를 확인한다.
- [ ] Streamlit 페이지가 브라우저의 마이크 권한을 요청한다.
- [ ] 사용자가 한국어 음성을 녹음하고 녹음 결과를 미리 듣는다.
- [ ] 사용자가 전송 버튼을 누르면 오디오를 `multipart/form-data`로 백엔드에 전송한다.
- [ ] 백엔드는 파일을 검증한 뒤 STT → 영어 번역 → 영어 TTS를 순서대로 수행한다.
- [ ] 프론트엔드는 인식된 한국어 원문, 영어 번역문, 영어 합성 음성을 표시한다.
- [ ] 사용자는 결과 음성을 재생하거나 다시 녹음할 수 있다.

### 2.2 정상 처리 흐름

영상 기능:

```text
브라우저 video
→ canvas.drawImage로 현재 프레임 캡처
→ JPEG Blob 생성 및 multipart 업로드
→ 기존 image-analysis API
→ 분석 summary 반환
→ 기존 TTS API
→ 한국어 MP3 재생
```

음성 기능:

```text
브라우저 마이크
→ Streamlit st.audio_input이 녹음 데이터를 수신
→ frontend/core/api_client.py가 FastAPI에 multipart 업로드
→ media_router가 파일 수신
→ media_service가 형식·크기·내용 검증
→ OpenAI STT로 한국어 텍스트 생성
→ 기존 OpenAI Responses 연결 방식으로 영어 번역
→ 기존 OpenAI TTS로 영어 MP3 생성
→ JSON(원문, 번역문, Base64 MP3, 메타데이터) 응답
→ Streamlit이 텍스트 표시 및 st.audio로 재생
```

Streamlit을 유지하므로 네트워크 관점의 정확한 경로는 `브라우저 → Streamlit 프로세스 → FastAPI → 외부 AI 서비스`이다. 브라우저가 FastAPI를 직접 호출하는 커스텀 JavaScript 방식은 현재 수업 구조를 벗어나므로 1차 구현 범위에서 제외한다.

### 2.3 오류 처리 흐름

- [ ] 마이크 미지원 또는 권한 거부 시 브라우저 설정 안내를 보여 준다.
- [ ] 녹음이 없거나 빈 파일이면 전송 버튼을 비활성화하거나 422 응답을 보여 준다.
- [ ] MIME 타입, 파일 시그니처 또는 크기가 허용 범위를 벗어나면 413/415/422로 구분한다.
- [ ] STT 결과가 비어 있으면 번역과 TTS를 호출하지 않고 422로 종료한다.
- [ ] API 키·설정 누락은 422, 외부 서비스 실패·타임아웃은 502/504로 변환한다.
- [ ] 프론트엔드는 상태 코드와 안전한 오류 메시지만 표시하고 내부 예외·키는 노출하지 않는다.
- [ ] 실패 후 사용자가 같은 녹음을 다시 전송하거나 새로 녹음할 수 있게 한다.

### 2.4 기능적 요구사항

- [ ] 입력 언어의 기본값은 한국어(`ko`)로 고정하되 향후 확장 가능한 서비스 함수 인자를 둔다.
- [ ] 출력 언어는 영어(`en`)로 고정한다.
- [ ] 한 번의 사용자 요청으로 STT·번역·TTS 결과를 받는다.
- [ ] 결과에 `transcript`, `translation`, `audio_base64`, `audio_mime_type`, `synthetic_voice`를 포함한다.
- [ ] 처리 중 중복 버튼 클릭을 막는다.
- [ ] 결과 오디오에는 “AI 합성 음성” 고지를 표시한다.

### 2.5 비기능 요구사항

- [ ] 1차 교육용 범위에서는 최대 10MB, 최대 녹음 길이 60초를 기본 제한으로 삼는다.
- [ ] 전체 요청 제한 시간은 음성 처리 특성을 고려해 90초를 기본값으로 설정한다.
- [ ] 원본 음성과 생성 음성을 디스크에 영구 저장하지 않는다.
- [ ] 외부 API 키와 사용자 음성·변환 텍스트를 로그에 남기지 않는다.
- [ ] 외부 서비스 호출 실패가 서버 프로세스를 중단시키지 않아야 한다.
- [ ] 테스트에서는 실제 유료 API를 호출하지 않는다.

## 3. 전체 시스템 구조

### 3.1 구성요소별 역할

| 구성요소 | 역할 |
|---|---|
| 브라우저/Streamlit UI | 마이크 권한, 녹음, 미리 듣기, 전송, 상태 및 결과 표시 |
| Streamlit 프론트엔드 프로세스 | 녹음 bytes를 multipart로 FastAPI에 전달하고 응답을 UI 형식으로 변환 |
| FastAPI 라우터 | HTTP 입력 수신, 오류를 HTTP 상태 코드로 변환, 응답 모델 적용 |
| 미디어 서비스 | 오디오 검증, STT → 번역 → TTS 오케스트레이션 |
| OpenAI STT | 한국어 음성을 한국어 텍스트로 변환 |
| OpenAI Responses | 한국어 텍스트를 영어 텍스트로 번역 |
| OpenAI TTS | 영어 번역문을 MP3 합성 음성으로 생성 |
| 영상 캡처 UI | 동영상/카메라 표시, canvas 프레임 캡처, 분석 요청, 한국어 안내 재생 |
| OpenAI 이미지 분석 | 캡처된 단일 프레임을 분석하고 구조화된 설명을 반환 |

### 3.2 데이터 흐름

영상 분석·음성 안내:

```text
[Video file 또는 Browser camera]
        ↓ 사용자가 분석 버튼 클릭
[video current frame → canvas]
        ↓ canvas.toBlob(image/jpeg, 0.8)
[POST /api/media/image-analysis]
        ↓
[구조화된 이미지 분석 결과 summary]
        ↓
[POST /api/media/tts]
        ↓ audio/mpeg
[브라우저 화면 표시 및 한국어 음성 재생]
```

음성 영어 번역:

```text
[Browser microphone]
        ↓ audio recording
[Streamlit st.audio_input]
        ↓ multipart/form-data (audio)
[POST /api/media/voice-translation]
        ↓ validate MIME, signature, size
[STT: audio → Korean transcript]
        ↓
[Translation: Korean transcript → English text]
        ↓
[TTS: English text → MP3 bytes]
        ↓ JSON + Base64 encoded MP3
[Streamlit transcript/translation/st.audio]
```

Base64는 JSON 응답을 단순화하지만 바이너리보다 약 33% 커진다. 60초 교육용 입력에는 구현 단순성이 이점이다. 운영 규모로 확장하면 작업 ID와 인증된 일회성 오디오 다운로드 URL 방식으로 변경한다.

## 4. 폴더 및 파일 설계

### 4.1 목표 폴더 트리

```text
mini_agent_01_llm/
├─ backend/
│  ├─ app/
│  │  ├─ config.py                         # 음성 제한·STT 설정 추가
│  │  ├─ schemas.py                        # VoiceTranslationResult 추가
│  │  ├─ routers/media_router.py           # 통합 음성 번역 API 추가
│  │  └─ services/media_service.py         # 검증·STT·번역·TTS 추가
│  └─ tests/test_api.py                     # 음성 API 테스트 추가
├─ frontend/
│  ├─ app.py                               # 1-7 페이지 등록
│  ├─ app_pages/
│  │  └─ 09_voice_translation.py           # 새 마이크·결과 UI
│  ├─ video_app/                            # 브라우저 영상·canvas 캡처 UI
│  │  └─ (React/Vite 최소 구성)             # 구현 방식 확정 후 상세 파일 결정
│  └─ core/api_client.py                   # upload_voice_translation 추가
├─ .env.example                            # 공개 음성 설정 이름 추가
├─ .gitignore                              # 새로 추가
├─ requirements.txt                        # 필요 시 Streamlit 최소 버전 명시
├─ README.md                               # 실행·기능 설명 갱신
└─ plan.md
```

### 4.2 파일별 계획

- [ ] `frontend/video_app/`: 동영상 파일/카메라 입력, `<video>`, `<canvas>`, 프레임 캡처, 분석 결과 및 MP3 재생을 담당한다.
- [ ] `frontend/app_pages/09_voice_translation.py`: `st.audio_input` 기반 녹음, 동의 안내, 전송, 결과 표시를 담당한다.
- [ ] `frontend/app.py`: “1-7. 음성 영어 번역” 페이지와 사이드바 링크를 등록한다.
- [ ] `frontend/core/api_client.py`: 오디오 multipart 업로드, JSON 파싱, Base64 디코딩, HTTP 오류 변환 함수를 추가한다.
- [ ] `backend/app/routers/media_router.py`: `POST /api/media/voice-translation` 엔드포인트와 상태 코드 매핑을 추가한다.
- [ ] `backend/app/services/media_service.py`: `validate_audio`, `transcribe_audio`, `translate_to_english`, 통합 오케스트레이션 함수를 추가하고 기존 `create_speech`를 재사용·일반화한다.
- [ ] `backend/app/schemas.py`: `VoiceTranslationResult`와 필요한 메타데이터 모델을 추가한다.
- [ ] `backend/app/config.py`: STT 모델, 오디오 제한, 타임아웃 설정을 추가한다.
- [ ] `backend/tests/test_api.py`: 성공, 검증 실패, 외부 API 실패, 키 비노출 테스트를 추가한다.
- [ ] `.env.example`: 실제 비밀값 없이 새 설정명과 안전한 기본값을 기록한다.
- [ ] `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`를 추가한다.
- [ ] `README.md`: 기능, 마이크 요구사항, 실행 및 검증 절차를 추가한다.
- [ ] 삭제 파일: 없음.

## 5. API 설계

### 5.1 영상 프레임 분석 및 안내 API

첫 구현은 기존 API 두 개를 순서대로 재사용한다.

1. `POST /api/media/image-analysis`
   - `multipart/form-data`
   - 필드: `image`(JPEG 캡처), `question`
   - 기존 `TravelImageAnalysis`를 반환하며 `summary`를 음성 안내 입력으로 사용한다.
2. `POST /api/media/tts`
   - JSON: `text`, `voice`, `instructions`
   - `audio/mpeg` bytes를 반환한다.

영상 기능을 독립적으로 추적해야 할 때만 `POST /api/media/video-frame-analysis`를 추가한다. 이 경우 `image`, `question`, 선택적 `session_id`, `captured_at`을 받고 내부에서 기존 `analyze_image()`를 호출한다.

```json
{
  "captured_at": "2026-08-18T12:00:00Z",
  "summary": "횡단보도 앞에 사람이 서 있습니다.",
  "should_speak": true
}
```

- [ ] 원본 동영상 전체는 서버에 전송하지 않고 캡처한 단일 JPEG만 전송한다.
- [ ] 캡처 폭은 최대 1280px, JPEG 품질은 약 0.8을 기본값으로 한다.
- [ ] 기존 `MAX_IMAGE_SIZE_MB`, MIME 및 파일 시그니처 검증을 그대로 적용한다.
- [ ] 단발 캡처에서는 `should_speak=true`를 기본으로 하되 사용자가 음성을 끌 수 있게 한다.

### 5.2 권장 음성 번역 통합 API

**`POST /api/media/voice-translation`**

- Content-Type: `multipart/form-data`
- 필드: `audio`(필수 파일), `source_language`(선택, 기본 `ko`), `target_language`(선택, 기본 `en`), `voice`(선택)
- 기본 파일 제한: 10MB
- 허용 MIME 후보: `audio/wav`, `audio/x-wav`, `audio/webm`, `audio/ogg`, `audio/mpeg`, `audio/mp4`
- 실제 허용 목록은 대상 브라우저에서 `st.audio_input`이 만드는 형식을 확인해 확정한다.
- 확장자나 클라이언트 MIME만 신뢰하지 않고 magic bytes/컨테이너 헤더도 함께 검사한다.
- 언어는 1차 범위에서 `ko` → `en`만 허용하며 다른 값은 422를 반환한다.
- `voice`는 기존 `TtsRequest` 허용 목록과 일치시킨다.

응답 예시:

```json
{
  "transcript": "안녕하세요. 서울역은 어디에 있나요?",
  "translation": "Hello. Where is Seoul Station?",
  "source_language": "ko",
  "target_language": "en",
  "audio_base64": "SUQz...",
  "audio_mime_type": "audio/mpeg",
  "synthetic_voice": true
}
```

상태 코드:

| 코드 | 의미 |
|---|---|
| 200 | STT·번역·TTS 완료 |
| 413 | 최대 업로드 크기 초과 |
| 415 | 지원하지 않는 MIME/오디오 형식 |
| 422 | 빈 파일, 무음·인식 결과 없음, 잘못된 언어·voice, 설정 누락 |
| 502 | 외부 AI 서비스 오류 또는 잘못된 외부 응답 |
| 504 | 외부 AI 서비스 제한 시간 초과 |
| 500 | 예상하지 못한 내부 오류(일반 메시지만 반환) |

### 5.3 음성 번역 통합 API와 단계별 API 비교

| 방식 | 장점 | 단점 | 판단 |
|---|---|---|---|
| 통합 API | UI 호출 1회, 수업 흐름이 단순, 중간 데이터 관리 불필요 | 전체 시간이 길고 어느 단계가 실패했는지 별도 분류 필요 | **1차 구현 권장** |
| STT/번역/TTS 분리 | 단계별 재시도·재사용·관찰이 쉬움 | 프론트 로직, API 수, 개인정보 보관 지점 증가 | 운영 확장 시 고려 |

현재 프로젝트는 작은 학습용 동기식 API이며 기존 TTS도 동기식이므로 통합 API가 적합하다. 서비스 내부 함수는 세 단계로 분리하여 단위 테스트와 향후 API 분리가 가능하게 한다.

## 6. 프론트엔드 구현 계획

### 6.1 영상 프레임 분석 화면

- [ ] 1차 개발 단위는 동영상 파일 한 개를 선택하고 현재 프레임 한 장을 분석하는 기능으로 제한한다.
- [ ] 2차로 `navigator.mediaDevices.getUserMedia()` 기반 실시간 카메라 입력을 추가한다.
- [ ] `<input type="file" accept="video/*">` 또는 카메라 stream을 `<video>`에 연결한다.
- [ ] `video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA`일 때만 캡처 버튼을 활성화한다.
- [ ] 원본 비율을 유지해 최대 폭 1280px로 축소한 뒤 `canvas.drawImage()`를 실행한다.
- [ ] `canvas.toBlob(..., "image/jpeg", 0.8)`로 Blob을 만들고 `FormData`로 전송한다.
- [ ] `isAnalyzing` 상태 동안 캡처 버튼을 비활성화해 중복 요청과 비용을 막는다.
- [ ] 최신 캡처 이미지, 분석 결과, 음성 재생 상태와 오류를 표시한다.
- [ ] 분석 `summary`를 `/api/media/tts`로 보내고 MP3 Blob URL을 `<audio>` 또는 `Audio`로 재생한다.
- [ ] 새 결과가 오면 이전 재생을 중지하고 `URL.revokeObjectURL()`로 이전 URL을 해제한다.
- [ ] 브라우저 자동 재생 정책을 고려해 사용자 클릭 이벤트에서 분석·재생 흐름을 시작한다.
- [ ] 카메라 stream의 모든 track을 중지하는 “카메라 중지” 동작을 제공한다.
- [ ] 카메라 권한 거부, 지원하지 않는 영상, 캡처 실패, 분석/TTS 실패를 각각 안내한다.

영상 캡처에는 브라우저 JavaScript의 `video`, `canvas`, `MediaDevices`가 필요하다. 따라서 1차 선택지는 최소 React/Vite 화면이며, 프로젝트를 하나의 Streamlit 앱으로 유지해야 한다면 Streamlit 커스텀 컴포넌트로 같은 JavaScript를 감싼다. 방식은 구현 전에 사용자에게 확인한다.

### 6.2 음성 영어 번역 화면

- [ ] 페이지 상단에 “마이크 음성은 외부 AI 서비스로 전송되며 영구 저장하지 않는다”는 안내와 합성 음성 고지를 표시한다.
- [ ] Streamlit 버전이 지원하면 `st.audio_input("한국어로 말해 주세요")`를 사용한다. 이는 브라우저 마이크 권한과 녹음을 처리하며 현재 Python 중심 수업 구조를 유지한다.
- [ ] 지원 버전이 낮으면 `requirements.txt`에 호환되는 Streamlit 최소 버전을 명시한다.
- [ ] 녹음 객체가 없을 때 번역 버튼을 비활성화한다.
- [ ] 녹음 객체의 `name`, `type`, `getvalue()`를 이용해 기존 이미지 업로드 패턴처럼 백엔드로 보낸다.
- [ ] 녹음 완료 후 원본 오디오 미리 듣기를 제공한다.
- [ ] `st.button` + `st.spinner`로 처리 중 상태를 표시하며 처리 중 동일 요청을 중복 실행하지 않도록 session state 상태값을 둔다.
- [ ] 필요한 상태값은 `voice_translation_processing`, `voice_translation_result`, 필요 시 `voice_translation_error`로 제한한다.
- [ ] 응답의 원문과 번역문을 서로 구분된 영역에 표시한다.
- [ ] Base64 MP3를 bytes로 변환하고 `st.audio(..., format="audio/mpeg")`로 재생한다.
- [ ] 합성 음성임을 음성 플레이어 바로 위에 다시 고지한다.
- [ ] 권한 거부 시 HTTPS/localhost 조건, 브라우저 주소창의 마이크 권한 재설정 방법을 안내한다.
- [ ] API 오류는 `BackendAPIError`를 통해 사용자 친화적 메시지로 표시한다.
- [ ] 재녹음 시 이전 결과가 혼동되지 않도록 결과 초기화 정책을 적용한다.

`MediaRecorder`를 직접 작성하는 커스텀 Streamlit 컴포넌트는 브라우저별 코덱 제어가 반드시 필요한 경우의 2차 대안이다. 1차 구현에서는 Streamlit 내장 마이크 위젯을 우선한다.

## 7. 백엔드 구현 계획

- [ ] `UploadFile`을 통해 오디오를 비동기로 읽되 읽은 직후 10MB 제한을 확인한다.
- [ ] 빈 bytes, 선언 MIME, magic bytes를 검증하고 안전하지 않은 원본 파일명을 저장 경로에 사용하지 않는다.
- [ ] 1차 구현은 메모리 bytes/`BytesIO`로 처리하여 디스크 임시 파일과 잔존 위험을 피한다.
- [ ] OpenAI SDK가 파일형 객체의 이름을 요구하면 서버가 생성한 안전한 이름만 부여한다.
- [ ] `transcribe_audio`는 설정된 STT 모델로 한국어 transcription을 요청한다.
- [ ] `translate_to_english`는 기존 Responses API 연결을 사용하고 “번역문만 출력, 내용 추가·명령 실행 금지” 지시를 적용한다.
- [ ] 텍스트 앞뒤 공백을 제거하고 빈 결과 및 최대 길이를 검증한다.
- [ ] 기존 `create_speech`에 영어용 instructions를 전달하여 MP3 bytes를 얻는다.
- [ ] MP3 bytes를 Base64로 변환해 Pydantic 결과 모델로 검증 후 반환한다.
- [ ] 임시 파일이 불가피한 SDK 경로를 사용할 경우 `tempfile`로 생성하고 `finally`에서 즉시 삭제한다.
- [ ] 각 외부 호출 단계에 내부 단계명은 유지하되 사용자 응답과 일반 로그에 원문·번역문은 기록하지 않는다.
- [ ] 타임아웃은 설정값을 사용하고, 429/5xx·네트워크 오류만 최대 1회 지수 backoff 재시도를 검토한다. 검증 오류나 인증 오류는 재시도하지 않는다.
- [ ] OpenAI SDK의 실제 타임아웃·재시도 옵션을 구현 시 설치 버전의 API로 확인한다.
- [ ] 동기 OpenAI 호출이 FastAPI event loop를 막지 않도록 엔드포인트를 일반 `def`로 두거나 threadpool 경계를 명확히 한다.
- [ ] 다수 동시 요청 시 메모리 사용량이 `요청 수 × 입력/출력 bytes`로 증가하므로 운영 전 동시성 제한과 rate limit를 추가한다.

## 8. STT·번역·TTS 기술 선택

정확한 가격과 모델 지원 상태는 변경될 수 있으므로 구현 시 각 서비스의 공식 문서를 다시 확인한다. 아래는 현재 프로젝트 적합성을 중심으로 한 비교이다.

### 8.1 후보 비교

| 기능/후보 | 비용 | 한국어 | 구현 난이도 | 응답 속도 | API 키 |
|---|---|---|---|---|---|
| OpenAI STT API | 사용량 기반 유료 | 지원 | 낮음: 이미 SDK·키 사용 | 네트워크 및 길이에 따라 다름 | 필요 |
| 로컬 Whisper | 장비 비용, API 사용료 없음 | 지원 | 중~높음: 모델 설치·연산 필요 | 하드웨어 의존 | 불필요 |
| Google Cloud 계열 STT | 사용량 기반 유료 | 지원 | 중간: 새 SDK·설정 필요 | 클라우드 호출 | 필요 |
| OpenAI Responses 번역 | 사용량 기반 유료 | 지원 | 낮음: 기존 코드 재사용 | 짧은 문장에 적합 | 필요 |
| Gemini 번역 | 사용량/정책에 따름 | 지원 | 중간: 기존 SDK는 있으나 모델 설정 필요 | 클라우드 호출 | 필요 |
| 규칙/사전 번역 | 낮음 | 제한적 | 중간 | 빠름 | 불필요 |
| OpenAI TTS | 사용량 기반 유료 | 영어 지원 | 낮음: 기존 구현 존재 | 클라우드 호출 | 필요 |
| 브라우저 SpeechSynthesis | 대체로 무료 | 환경 의존 | 낮음 | 빠름 | 불필요 |
| 로컬 TTS | 장비 비용 | 모델 의존 | 높음 | 하드웨어 의존 | 불필요 |

### 8.2 권장 조합

**OpenAI STT + OpenAI Responses 번역 + 기존 OpenAI TTS**를 기본안으로 권장한다.

이유:

- 프로젝트에 `openai` 패키지, `OPENAI_API_KEY`, Responses 호출, TTS 호출이 이미 있다.
- 새 클라우드 계정·SDK·인증 방식을 추가하지 않아 수업의 기존 구조를 가장 잘 유지한다.
- STT·번역·TTS의 오류 처리와 설정을 한 Provider 경계에서 통일할 수 있다.
- 브라우저 TTS가 아니라 백엔드 TTS라는 요구사항을 만족한다.

로컬 전용 요구나 비용 제한이 확정되면 2차안으로 로컬 Whisper를 STT에 적용할 수 있으나 모델 파일, CPU/GPU 성능, 배포 용량 검증이 먼저 필요하다.

## 9. 보안 및 개인정보 보호

- [ ] `OPENAI_API_KEY`는 `.env`에만 두고 코드, 응답, 로그에 포함하지 않는다.
- [ ] `.env.example`에는 빈 키와 설정 이름만 기록한다.
- [ ] 새 `.gitignore`에 `.env`를 포함하고 이미 Git에 추적 중인지 `git ls-files .env`로 확인한다.
- [ ] 원본 및 합성 오디오를 기본적으로 메모리에서만 처리하고 영구 저장하지 않는다.
- [ ] 임시 파일 사용 시 무작위 서버 파일명과 `finally` 정리를 적용한다.
- [ ] MIME, magic bytes, 빈 파일, 크기, 언어·voice allowlist를 검증한다.
- [ ] 클라이언트 원본 파일명을 파일 시스템 경로나 외부 서비스 메타데이터로 그대로 사용하지 않는다.
- [ ] 현재 Streamlit 서버가 FastAPI를 호출하는 구조에서는 브라우저 CORS가 필요하지 않다.
- [ ] 향후 브라우저가 FastAPI를 직접 호출하면 명시적인 프론트엔드 origin만 CORS allowlist에 추가하고 `*`와 credential 조합을 사용하지 않는다.
- [ ] 애플리케이션 10MB 제한과 함께 운영 프록시의 body size 제한도 맞춘다.
- [ ] 로그에는 요청 ID, 단계, 소요 시간, 상태만 남기고 음성 bytes·원문·번역문은 제외한다.
- [ ] 사용자에게 녹음 전 마이크 사용, 외부 AI 전송, 미보관 정책, 합성 음성임을 명확히 알린다.
- [ ] 공개 배포 전 HTTPS를 적용한다. 브라우저 마이크 기능은 일반적으로 secure context 또는 localhost가 필요하다.

## 10. 구현 단계

### 단계 0. 통합 UI 방식과 개발 순서 확정

- [ ] 목적: Streamlit 음성 화면과 JavaScript 영상 화면의 경계를 확정한다.
- [ ] 대상 파일: `README.md`, 이후 선택에 따라 `frontend/video_app/` 또는 Streamlit 컴포넌트 폴더
- [ ] 작업: 영상 화면을 React/Vite로 둘지 Streamlit 커스텀 컴포넌트로 둘지 결정하고, 동영상 파일 입력을 먼저 구현한 뒤 카메라 입력을 추가한다.
- [ ] 완료 조건: 실행 포트, CORS 필요 여부, 프론트엔드 폴더 구조가 확정된다.
- [ ] 확인: 선택한 구조에서 브라우저가 샘플 동영상을 표시할 수 있다.

### 단계 1. 환경 및 계약 확정

- [ ] 목적: 지원 브라우저, 실제 녹음 MIME, 설치된 SDK API를 확인한다.
- [ ] 대상 파일: `requirements.txt`, `.env.example`, `backend/app/config.py`
- [ ] 작업: Streamlit `st.audio_input` 지원 여부, OpenAI STT 메서드, 모델명, timeout 옵션을 공식 문서 및 로컬 설치 버전으로 검증한다.
- [ ] 완료 조건: 입력 MIME·최대 크기·STT 모델·응답 계약이 확정된다.
- [ ] 확인: 최소 녹음 샘플의 파일명, MIME, bytes 헤더를 민감정보 없이 개발 환경에서 확인한다.

### 단계 2. 설정과 응답 스키마 추가

- [ ] 목적: 하드코딩 없이 제한과 모델을 관리한다.
- [ ] 대상 파일: `.env.example`, `.gitignore`, `backend/app/config.py`, `backend/app/schemas.py`
- [ ] 작업: STT 모델, 최대 오디오 크기, 음성 처리 timeout과 `VoiceTranslationResult`를 추가한다.
- [ ] 완료 조건: 설정 기본값이 로드되고 결과 예시가 Pydantic 검증을 통과한다.
- [ ] 확인: Python import 검사 및 스키마 단위 테스트를 실행한다.

### 단계 3. 오디오 검증 구현

- [ ] 목적: 잘못되거나 과도한 업로드를 외부 API 호출 전에 차단한다.
- [ ] 대상 파일: `backend/app/services/media_service.py`, `backend/tests/test_api.py`
- [ ] 작업: MIME allowlist, magic bytes, 빈 파일, 10MB 제한 검사를 분리 함수로 구현한다.
- [ ] 완료 조건: 정상 샘플은 통과하고 빈 파일·위장 파일·초과 파일은 명확한 예외를 낸다.
- [ ] 확인: 매개변수화된 Pytest 단위 테스트를 실행한다.

### 단계 4. STT·번역·TTS 서비스 구현

- [ ] 목적: 세 AI 처리 단계를 각각 테스트 가능한 함수로 만든다.
- [ ] 대상 파일: `backend/app/services/media_service.py`
- [ ] 작업: transcription, 영어 번역, 기존 TTS 재사용, 통합 orchestration 함수를 구현한다.
- [ ] 완료 조건: mock된 각 단계로 원문·번역문·MP3 결과가 생성된다.
- [ ] 확인: 외부 API를 monkeypatch한 서비스 테스트를 실행한다.

### 단계 5. FastAPI 통합 엔드포인트 구현

- [ ] 목적: 프론트엔드가 한 번의 요청으로 전체 결과를 받게 한다.
- [ ] 대상 파일: `backend/app/routers/media_router.py`, `backend/tests/test_api.py`
- [ ] 작업: multipart 수신, 서비스 호출, Base64 응답, 413/415/422/502/504 매핑을 구현한다.
- [ ] 완료 조건: 정상 mock 요청은 200과 스키마를 반환하고 오류별 상태 코드가 구분된다.
- [ ] 확인: `TestClient` 통합 테스트 및 FastAPI `/docs` 수동 호출을 수행한다.

### 단계 6. 프론트엔드 API 클라이언트 구현

- [ ] 목적: 오디오 업로드와 결과 디코딩을 공통 계층에 둔다.
- [ ] 대상 파일: `frontend/core/api_client.py`
- [ ] 작업: multipart 업로드, timeout, 오류 메시지, JSON 필드 검사, Base64 디코딩 함수를 추가한다.
- [ ] 완료 조건: mock 백엔드 응답을 텍스트와 MP3 bytes로 변환한다.
- [ ] 확인: 로컬 FastAPI를 대상으로 정상/오류 호출을 확인한다.

### 단계 7. Streamlit 음성 번역 페이지 구현

- [ ] 목적: 녹음부터 결과 재생까지 완성한다.
- [ ] 대상 파일: `frontend/app_pages/09_voice_translation.py`, `frontend/app.py`
- [ ] 작업: 안내, `st.audio_input`, 미리 듣기, 전송 버튼, spinner, 원문/번역문, `st.audio`, 재시도 UI를 추가한다.
- [ ] 완료 조건: 브라우저에서 녹음한 한국어가 영어 텍스트와 영어 음성으로 표시된다.
- [ ] 확인: Chrome/Edge의 localhost에서 권한 허용·거부 두 경우를 수동 테스트한다.

### 단계 8. 문서화와 전체 회귀 검증

- [ ] 목적: 초보자가 동일 환경에서 실행하고 기존 기능도 유지되는지 확인한다.
- [ ] 대상 파일: `README.md`, 필요 시 `BEGINNER_GUIDE.md`
- [ ] 작업: 설정, 실행, 개인정보 안내, 제한, 문제 해결 방법을 기록한다.
- [ ] 완료 조건: 새 환경에서 문서만 보고 실행할 수 있고 기존 이미지/TTS 테스트가 통과한다.
- [ ] 확인: 전체 Pytest, import/compile 검사, 수동 E2E 체크리스트를 수행한다.

### 단계 9. 영상 파일 프레임 분석·TTS 구현

- [ ] 목적: 동영상 파일의 원하는 한 장면을 분석하고 음성으로 안내한다.
- [ ] 대상 파일: 선택한 영상 프론트엔드 파일, `frontend/core/api_client.py` 또는 전용 브라우저 API 모듈
- [ ] 작업: video 표시, canvas 캡처, JPEG 축소, 기존 이미지 분석 API 호출, summary 표시, 기존 TTS 호출 및 재생을 구현한다.
- [ ] 완료 조건: 동영상 전체가 아닌 현재 프레임 한 장만 서버로 전송되고 한국어 안내가 한 번 재생된다.
- [ ] 확인: 서로 다른 시점에서 캡처해 분석 결과와 최신 음성이 바뀌는지 검증한다.

### 단계 10. 카메라 입력과 개인정보 UI 추가

- [ ] 목적: 실시간 카메라에서도 같은 단발 캡처 흐름을 제공한다.
- [ ] 대상 파일: 선택한 영상 프론트엔드 파일, `README.md`
- [ ] 작업: `getUserMedia`, 권한 오류, 카메라 중지, stream track 정리, 외부 AI 전송 안내를 추가한다.
- [ ] 완료 조건: 사용자가 카메라를 시작·캡처·분석·중지할 수 있고 페이지 종료 시 stream이 정리된다.
- [ ] 확인: 권한 허용·거부·재허용과 카메라 중지를 Chrome/Edge에서 테스트한다.

## 11. 테스트 계획

### 11.1 백엔드 단위·통합 테스트

- [ ] 정상 WAV/WebM 샘플 검증 테스트
- [ ] 빈 오디오와 STT 빈 결과 테스트
- [ ] 허용되지 않은 MIME 및 확장자 위장 테스트
- [ ] 파일 시그니처 불일치 테스트
- [ ] 정확히 제한 크기와 제한 초과 크기 경계 테스트
- [ ] source/target language 및 voice allowlist 테스트
- [ ] STT 성공·실패·timeout 테스트
- [ ] 번역 성공·실패·빈 결과 테스트
- [ ] TTS 성공·실패 테스트
- [ ] 각 외부 호출을 monkeypatch하여 실제 과금 없는 통합 테스트
- [ ] 응답에 API 키, 파일 bytes 원문, 내부 traceback이 노출되지 않는지 테스트
- [ ] 기존 `/health`, Provider, 이미지 분석, TTS API 회귀 테스트

예상 명령:

```powershell
cd C:\mini_agent\mini_agent_01_llm
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
pytest .\backend\tests -q
python -m compileall .\backend .\frontend
```

### 11.2 프론트엔드 및 브라우저 테스트

- [ ] 동영상 파일이 재생되고 서로 다른 재생 시점의 프레임이 올바르게 캡처되는지 확인한다.
- [ ] 영상이 아직 준비되지 않았을 때 캡처가 차단되는지 확인한다.
- [ ] 최대 폭 축소와 JPEG Blob MIME/크기를 확인한다.
- [ ] 분석 버튼 연속 클릭 시 영상 분석 요청이 중복되지 않는지 확인한다.
- [ ] 새 분석이 시작되면 이전 음성이 중지되고 이전 Blob URL이 해제되는지 확인한다.
- [ ] 카메라 권한 허용·거부·중지 및 stream track 정리를 확인한다.
- [ ] 원본 동영상 전체가 네트워크로 전송되지 않는지 개발자 도구에서 확인한다.
- [ ] Chrome과 Edge에서 마이크 권한 허용 후 녹음한다.
- [ ] 마이크 권한을 거부했을 때 복구 안내가 보이는지 확인한다.
- [ ] 1~2초 짧은 음성, 30~60초 긴 음성, 무음, 배경 잡음을 테스트한다.
- [ ] 버튼 연속 클릭 시 중복 요청이 발생하지 않는지 확인한다.
- [ ] 백엔드 중지, timeout, 4xx/5xx 응답 시 UI가 복구되는지 확인한다.
- [ ] 같은 녹음 재전송과 새 녹음 시 결과 상태가 올바른지 확인한다.
- [ ] 영어 MP3가 재생되고 합성 음성 안내가 인접 표시되는지 확인한다.

### 11.3 전체 E2E 시나리오

- [ ] 동영상 파일을 선택하고 원하는 장면에서 분석 버튼을 누른다.
- [ ] 현재 프레임 JPEG만 전송되고 분석 summary가 표시되는지 확인한다.
- [ ] summary가 한국어 합성 음성으로 한 번 재생되는지 확인한다.
- [ ] “안녕하세요. 서울역은 어디에 있나요?”라고 한국어로 녹음한다.
- [ ] 원문이 의미를 보존한 한국어 텍스트로 표시되는지 확인한다.
- [ ] 영어 번역문이 의미를 보존하는지 사람이 확인한다.
- [ ] 생성 음성이 영어로 재생되고 번역문과 대체로 일치하는지 확인한다.
- [ ] 서버 로그에 음성 데이터·인식문·번역문·API 키가 남지 않는지 확인한다.

## 12. 실행 및 검증 방법

### 12.1 설치 및 환경변수

```powershell
cd C:\mini_agent\mini_agent_01_llm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env.example`에 계획할 항목:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_STT_MODEL=<구현 시 지원 모델 확인 후 확정>
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
MAX_AUDIO_SIZE_MB=10
VOICE_REQUEST_TIMEOUT_SECONDS=90
BACKEND_API_URL=http://127.0.0.1:8000
```

모델명은 구현 시 설치된 SDK와 공식 문서에서 실제 지원 여부를 확인한 후 확정하며, 실제 키는 `.env`에만 입력한다.

### 12.2 서버 실행

터미널 1:

```powershell
cd C:\mini_agent\mini_agent_01_llm
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000
```

터미널 2:

```powershell
cd C:\mini_agent\mini_agent_01_llm
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py
```

### 12.3 예상 검증 결과

- [ ] Streamlit 사이드바에 “1-7. 음성 영어 번역”이 표시된다.
- [ ] localhost 페이지에서 마이크 권한 요청과 녹음 위젯이 동작한다.
- [ ] 한국어 녹음 전송 후 원문과 영어 번역문이 표시된다.
- [ ] 영어 MP3 플레이어가 표시되고 재생된다.
- [ ] 무음·잘못된 파일·초과 크기·외부 API 실패가 구분된 메시지로 표시된다.
- [ ] 기존 페이지와 전체 자동화 테스트가 계속 통과한다.

## 13. 가정 사항

- 현재 프론트엔드는 일반 HTML/React가 아니라 Streamlit이며 이 구조를 유지한다.
- 영상의 현재 프레임을 임의 시점에 캡처하는 부분만 브라우저 JavaScript가 필요하므로 최소 React/Vite 화면 또는 Streamlit 커스텀 컴포넌트 사용을 허용한다고 가정한다.
- 영상 기능은 동영상 파일 입력을 먼저 완성한 후 카메라 입력을 추가한다.
- 영상 분석 결과는 한국어로 안내하고, 음성 번역 결과는 영어로 안내한다.
- 1차 지원 브라우저는 최신 Chrome과 Edge, 실행 환경은 localhost이다.
- 입력은 한국어, 번역과 합성 음성은 영어로 고정한다.
- 한 번의 녹음은 최대 60초·10MB인 교육용 단일 사용자 프로토타입이다.
- 기존에 설정된 OpenAI 연결을 사용하며 음성 처리에 따른 API 비용 사용이 허용된다.
- 사용자 계정, 로그인, 음성 이력 저장, 실시간 스트리밍 번역은 범위에 포함하지 않는다.
- Streamlit `st.audio_input`이 현재 프로젝트 환경에서 사용 가능하다고 가정하되 단계 1에서 검증한다.
- `.env`의 실제 내용은 분석하지 않았으며, 공개 가능한 `.env.example`과 소스 코드만 근거로 기존 Provider를 판단했다.

## 14. 사용자에게 추가로 확인할 사항

- [ ] 영상 화면을 별도 React/Vite 앱으로 둘지 Streamlit 커스텀 컴포넌트로 통합할지 확인한다.
- [ ] 영상 입력이 동영상 파일만 필요한지, 실시간 카메라까지 필요한지 확정한다.
- [ ] 이미지 분석 질문과 한국어 안내문의 길이·말투를 확정한다.
- [ ] 입력 언어가 항상 한국어인지, 자동 언어 감지가 필요한지 확인한다.
- [ ] 목표 브라우저와 모바일 브라우저 지원 여부를 확인한다.
- [ ] 최대 녹음 시간과 허용 파일 크기를 확정한다.
- [ ] OpenAI 사용 비용과 음성 외부 전송에 대한 정책상 허용 여부를 확인한다.
- [ ] 영어 음성의 voice, 억양, 말하기 속도 요구를 확정한다.
- [ ] 결과 다운로드, 이력 저장, 재번역 기능이 필요한지 확인한다.
- [ ] 실제 배포가 필요한 경우 HTTPS, 인증, rate limit, 보관·삭제 정책을 확정한다.

## 15. 예상 위험 요소

- React/Vite 화면을 추가하면 Streamlit과 개발 서버가 분리되어 실행·CORS 설정이 늘어날 수 있다.
- Streamlit 커스텀 컴포넌트는 별도 JavaScript 빌드와 양방향 데이터 전달 학습이 필요하다.
- 카메라와 마이크는 HTTPS 또는 localhost, 사용자 권한, 브라우저 정책에 영향을 받는다.
- 큰 영상의 원본 프레임은 이미지 제한을 초과할 수 있으므로 브라우저 축소가 필요하다.
- 브라우저 자동 재생 정책으로 인해 사용자 클릭 없이 TTS를 바로 재생하지 못할 수 있다.
- 브라우저 또는 Streamlit 버전에 따라 마이크 위젯과 생성 MIME이 다를 수 있다.
- WebM/Ogg 컨테이너와 코덱 조합을 외부 STT가 모두 받지 못할 수 있다.
- 세 번의 외부 AI 호출로 지연 시간과 비용이 누적된다.
- Base64 오디오 응답은 바이너리보다 메모리와 전송량이 증가한다.
- 무음, 잡음, 억양, 마이크 품질에 따라 STT와 번역 품질이 달라진다.
- SDK/모델명/가격/지원 형식은 변경될 수 있어 구현 시 공식 문서 재확인이 필요하다.
- 동시 사용자가 늘면 메모리, API rate limit, timeout 문제가 발생할 수 있다.
- 음성은 개인정보가 될 수 있으므로 공개 배포 전에 동의·보관·삭제 정책 검토가 필요하다.

## 16. 완료 기준(Definition of Done)

- [ ] 기존 수업 폴더 구조와 `app_pages → api_client → router → service/schema` 흐름을 유지한다.
- [ ] 사용자가 동영상 파일을 재생하고 원하는 시점의 현재 프레임 한 장을 캡처할 수 있다.
- [ ] 선택 범위에 카메라가 포함되면 사용자가 카메라를 시작·캡처·중지할 수 있다.
- [ ] 원본 동영상 전체가 아닌 축소된 단일 JPEG 프레임만 백엔드로 전송된다.
- [ ] 캡처 분석 결과가 화면에 표시되고 한국어 합성 음성으로 한 번 재생된다.
- [ ] 영상 분석 중 중복 요청, 이전 음성, Blob URL 및 카메라 stream이 안전하게 관리된다.
- [ ] 브라우저에서 한국어 음성을 녹음하고 FastAPI 처리 흐름으로 전송할 수 있다.
- [ ] 백엔드가 STT → 영어 번역 → 영어 TTS를 한 요청에서 수행한다.
- [ ] UI에 한국어 원문, 영어 번역문, 재생 가능한 영어 합성 음성이 표시된다.
- [ ] 마이크 거부, 빈/무음, 잘못된 형식, 초과 크기, timeout, 외부 API 실패를 처리한다.
- [ ] `.env.example`과 `.gitignore`가 준비되고 비밀키가 코드·응답·로그에 노출되지 않는다.
- [ ] 원본 및 합성 음성을 기본적으로 영구 저장하지 않는다.
- [ ] 외부 API를 mock한 자동화 테스트와 기존 회귀 테스트가 모두 통과한다.
- [ ] Chrome/Edge localhost E2E 시나리오가 통과한다.
- [ ] README만 보고 설치, 설정, 백엔드·프론트엔드 실행 및 기능 확인이 가능하다.
