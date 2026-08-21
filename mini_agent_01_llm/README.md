# Mini Agent 01 · LLM 판단에서 서비스 연결까지

`01_llm-to-agent`의 단위 Python 예제를 FastAPI Endpoint와 Streamlit 메뉴로
하나씩 연결합니다. 첫 단계에서는 로그인과 Agent Workflow를 넣지 않습니다.

```text
Python 판단 함수
→ FastAPI
→ Streamlit 메뉴
→ Mock
→ Gemini
→ OpenAI GPT
→ Docker Ollama/Llama
→ 이미지 분석
→ 음성 생성
```

## 이번 단계에서 구현

- LLM·Workflow·Agent 비교
- 여행 요청 분류
- 낮은 confidence와 추가 질문
- Mock Provider로 연결 확인
- Gemini·GPT·Ollama/Llama 선택
- 동일 Prompt의 모델·응답 시간·실패 비교
- GPT 이미지 분석과 업로드 검증
- 여행 안내문 MP3 합성 음성 생성
- 한국어 음성의 영어 텍스트·영어 합성 음성 변환
- 동영상/카메라 현재 프레임 분석 및 한국어 음성 안내

## 아직 구현하지 않음

- Structured Output
- LangChain
- Tool
- RAG와 Memory
- Agent Workflow와 LangGraph
- 로그인

## 실행

```powershell
cd C:\mini_agent_st\mini_agent_01_llm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

터미널 1:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

터미널 2:

```powershell
cd C:\mini_agent_st\mini_agent_01_llm
streamlit run .\frontend\app.py
```

Ollama는 `C:\mini_agent_st\infra`에서 먼저 실행하고 모델을 내려받아야 합니다.
Cloud Provider는 `.env`에 해당 API Key와 모델을 설정한 경우에만 호출합니다.

## 확인 순서

1. LLM·Workflow·Agent 메뉴에서 두 판단 결과를 비교합니다.
2. 여행 요청 분류에서 `confidence`와 추가 질문을 확인합니다.
3. 환경 상태에서 Backend와 Provider 설정을 확인합니다.
4. 기본 Provider인 Mock으로 Frontend·Backend 연결을 확인합니다.
5. 이전 과정에서 사용한 Gemini를 연결합니다.
6. GPT와 Ollama/Llama를 추가해 같은 질문을 비교합니다.
7. Ollama Container를 중지하고 실패가 비교 결과에 남는지 확인합니다.
8. 이미지 분석에서 업로드 형식과 구조화된 결과를 확인합니다.
9. 음성 생성에서 안내문을 MP3로 변환하고 합성 음성 고지를 확인합니다.
10. 음성 영어 번역에서 60초 이내 한국어를 녹음해 영어 텍스트와 음성을 확인합니다.
11. 영상 분석 음성 안내에서 전용 화면을 열어 동영상 또는 카메라의 현재 장면을 분석합니다.

Provider 비교는 `Gemini → GPT → Ollama/Llama` 순서로 진행합니다. Cloud Provider는
호출량과 비용을 확인하고, Ollama는 Docker와 모델 준비 상태를 먼저 확인합니다.

이미지 분석과 음성 생성은 01 단원의 `1-5`, `1-6` 메뉴에서 진행합니다.

## 멀티모달 통합 기능

### 음성 영어 번역

Streamlit의 `1-7. 음성 영어 번역`에서 마이크로 한국어를 녹음합니다. 프론트엔드는
녹음 파일을 `POST /api/media/voice-translation`에 전송하고, 백엔드는 STT → 영어
번역 → 영어 TTS를 수행합니다. 원본 음성과 생성 음성은 서버에 영구 저장하지 않습니다.

### 영상 분석 음성 안내

Streamlit의 `1-8. 영상 분석 음성 안내`에서 전용 화면을 열거나 다음 주소로 직접
접속합니다.

```text
http://127.0.0.1:8000/video/
```

전용 화면은 동영상 파일 또는 카메라를 브라우저에서 재생하고, 사용자가 버튼을 누른
순간의 현재 프레임만 최대 폭 1280px JPEG로 만들어 기존 이미지 분석 API에 보냅니다.
분석 요약은 기존 TTS API를 통해 한국어 합성 음성으로 재생됩니다. 원본 동영상 전체는
서버로 전송하지 않습니다.

마이크와 카메라는 `localhost` 또는 HTTPS 환경에서 사용하고 브라우저 권한을 허용해야
합니다. 외부 AI 호출에는 사용량에 따른 비용이 발생할 수 있습니다.

추가 환경변수:

```dotenv
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
MAX_AUDIO_SIZE_MB=10
VOICE_REQUEST_TIMEOUT_SECONDS=90
```

자동화 테스트는 실제 OpenAI 호출을 막기 위해 빈 키로 실행할 수 있습니다.

```powershell
$env:PYTHONPATH = "$PWD\backend"
$env:OPENAI_API_KEY = ""
pytest .\backend\tests -q
```
