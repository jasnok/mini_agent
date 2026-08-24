# Mini Agent 03 · Tool Use — Master Plan

## 1. 프로젝트 개요

이 프로젝트는 LLM이 Tool을 선택하고, Python Backend가 입력을 검증한 뒤 안전하게 실행하며, Tool Result를 최종 답변으로 변환하는 과정을 학습하는 누적형 예제다.

Mini Agent 01·02의 LLM 기초, Provider 비교, Prompt, Pydantic, Structured Output 기능을 유지하면서 다음 내용을 추가한다.

- Tool Schema와 Tool Call의 관계
- `auto`·`none`·`required` Tool Choice 비교
- 누락된 인자를 추측하지 않는 재질문
- Pydantic 기반 Tool arguments 검증
- Allowlist 기반 Tool 실행
- Tool 오류의 공통 형식
- Tool 선택 → 실행 → 최종 답변으로 이어지는 단일 Agent Cycle
- Workflow와 Agent를 비교하는 7개 Tool Use Lab

현재 범위는 교육용 애플리케이션이다. 실제 예약·결제·환불·삭제, 실제 주차 차단기나 에어컨 같은 장치 제어, 운영 DB 연동은 포함하지 않는다.

---

## 2. 실제 시스템 구조

```text
Streamlit Frontend
  frontend/app.py
  frontend/app_pages/*.py
        │
        ▼
Frontend API Client
  frontend/clients/agent_client.py
        │ HTTP
        ▼
FastAPI Backend
  backend/app/main.py
  backend/app/routers/
        │
        ├─ services/       유스케이스·정책·Workflow
        ├─ agents/         LLM 판단·인자 추출·Agent Loop
        ├─ tools/          Tool 명세·검증·실행
        ├─ providers/      OpenAI·Gemini·Ollama·Mock 연결
        ├─ schemas/        요청·응답 Pydantic 계약
        └─ repositories/   교육용 In-memory Mock 상태
```

핵심 경계는 다음과 같다.

```text
LLM/Agent = Tool 또는 다음 행동을 제안
Backend   = Schema·Allowlist·업무 정책으로 제안을 검증
Tool      = 검증된 하나의 작업만 수행
```

Agent의 출력은 신뢰 경계 밖의 입력으로 취급한다. LLM이 만든 Tool 이름과 arguments도 일반 사용자 입력과 동일하게 검증한 뒤 실행한다.

---

## 3. 폴더 구조와 책임

```text
mini_agent_03_tool/
├─ backend/
│  ├─ app/
│  │  ├─ agents/          Agent 정의, Routing, 실행 Cycle
│  │  ├─ core/            환경 설정
│  │  ├─ providers/       LLM·Media Provider 구현
│  │  ├─ repositories/    Lab용 In-memory Mock 저장소
│  │  ├─ routers/         FastAPI HTTP 진입점
│  │  ├─ schemas/         Pydantic 요청·응답 모델
│  │  ├─ services/        Workflow·정책·유스케이스
│  │  ├─ tools/           Tool Registry·Executor·Tool 함수
│  │  └─ main.py          FastAPI 앱과 Router 등록
│  └─ tests/              API·Lab·Open-Meteo 테스트
├─ frontend/
│  ├─ app_pages/          01~18 학습 화면
│  ├─ clients/            Backend 호출 Client
│  ├─ core/               Frontend 공통 API 설정
│  └─ app.py              Streamlit 진입점·Navigation
├─ learning_unit/         단계별 독립 학습 예제와 실습
│  ├─ 10_labs/            7개 Tool Use Lab 예제
│  └─ 20_assignments/     과제 안내
├─ starter/               학습자 시작 코드
├─ solution/              해설 안내
├─ docs/                  통합 Lab 설계 문서
├─ .env.example           공통 환경변수 예시
├─ requirements.txt       Python 의존성
├─ README.md              실행·기능 요약
└─ master.md              본 문서
```

별도의 `/database`, `/workflow`, `/agent`, `/tools` 최상위 폴더를 만들지 않는다. 현재 구현은 `backend/app` 아래에서 계층별로 분리한다.

`.venv`, `__pycache__`, `.pytest_cache`, `.env`는 소스 구조나 협업 대상에 포함하지 않는다.

---

## 4. Frontend

Frontend는 Streamlit을 사용하며 기본 포트는 `8501`이다. `frontend/app.py`가 18개 페이지를 등록한다.

주요 화면 그룹:

1. LLM에서 Agent로: 개념 비교, 여행 분류, LLM 호출, Provider 비교, 이미지 분석, TTS
2. Prompt와 구조화 출력: Prompt 구성, Pydantic 검증, Structured Output
3. Tool Use: Tool Schema, 선택, 입력 검증, 안전 실행, 오류 처리, Agent Cycle, 통합 Labs

Frontend의 책임은 입력 수집, API 호출, 결과·Trace 표시다. Tool 실행, 승인 정책, Lab Routing을 UI에 구현하지 않는다.

---

## 5. Backend와 API

Backend는 FastAPI를 사용하며 기본 주소는 `http://127.0.0.1:8000`이다. Swagger 문서는 `http://127.0.0.1:8000/docs`에서 확인한다.

### Stage 01 · LLM 기초

| Method | Endpoint | 역할 |
|---|---|---|
| GET | `/health` | Backend·기본 Provider 상태 |
| GET | `/api/providers` | Provider 설정 상태 |
| POST | `/api/concepts/compare` | LLM·Workflow·Agent 판단 비교 |
| POST | `/api/travel/classify` | 여행 요청 분류 |
| POST | `/api/generate` | 단일 Provider 생성 |
| POST | `/api/providers/compare` | Provider 응답 비교 |
| POST | `/api/media/image-analysis` | 이미지 분석 |
| POST | `/api/media/tts` | 음성 생성 |

### Stage 02 · Prompt와 구조화 출력

| Method | Endpoint | 역할 |
|---|---|---|
| POST | `/api/prompts/preview` | Prompt 조합 결과 확인 |
| POST | `/api/structured/validate` | Pydantic 검증 |
| POST | `/api/structured/travel-plan` | 구조화 여행 계획 생성 |
| POST | `/api/structured/compare` | Provider별 구조화 출력 비교 |

### Stage 03 · Tool과 Agent

| Method | Endpoint | 역할 |
|---|---|---|
| GET | `/api/tools` | 허용된 Tool 명세 조회 |
| POST | `/api/tools/select` | LLM이 Tool과 arguments만 선택 |
| POST | `/api/tools/run` | 지정한 Tool을 Backend가 직접 검증·실행 |
| POST | `/api/tools/complete` | Tool 선택·실행·최종 답변의 단일 Cycle |

### Tool Use Labs

| Method | Endpoint | 역할 |
|---|---|---|
| POST | `/api/labs/run` | 7개 Lab의 공통 실행 진입점 |
| POST | `/api/labs/reset` | In-memory Mock 상태 초기화 |

기존 코드에 없는 `/api/vehicle/recognize`, `/api/workflow/parking`, `/api/agent/parking` Endpoint는 본 프로젝트의 계약으로 사용하지 않는다. 주차장 실습도 `/api/labs/run`을 사용한다.

---

## 6. Tool 구조와 안전 실행

일반 Stage 03 Tool은 `backend/app/tools/registry.py`의 `ToolSpec`으로 등록한다.

```text
ToolSpec
├─ name
├─ description
├─ Pydantic arguments model
└─ Python execute function
```

같은 Pydantic 모델에서 LLM에 전달할 JSON Schema와 실행 직전 Backend 검증을 생성한다. `backend/app/tools/executor.py`는 Registry에 없는 이름을 거부하고 오류를 공통 형식으로 반환한다.

등록 Tool:

- `get_current_weather`
- `get_weather_forecast`
- `search_hotels`
- `search_attractions`

Lab Tool은 `backend/app/tools/lab_tools.py`의 별도 Allowlist를 사용한다. Tool은 전체 흐름을 결정하지 않고 조회 또는 상태 변경 하나만 담당한다.

공통 오류 코드:

- `TOOL_NOT_ALLOWED`
- `TOOL_VALIDATION_ERROR`
- `TOOL_EXECUTION_ERROR`

---

## 7. Agent Cycle

Stage 03의 여행 Agent는 다음 흐름을 최대 한 번 수행한다.

```text
사용자 메시지
  ↓
OpenAI가 Tool과 arguments 선택
  ↓
필수 인자 검사
  ├─ 누락 → 사용자에게 추가 질문
  └─ 충족
       ↓
Backend Allowlist·Pydantic 검증
       ↓
Tool 실행
       ↓
Tool Result를 이용한 최종 답변 생성
```

- 도메인 역할과 Tool 구성: `backend/app/agents/travel_agent.py`
- 공통 실행 방식: `backend/app/agents/runtime.py`
- 안전 실행: `backend/app/tools/executor.py`

현재 Stage 03 기본 Cycle은 여러 Tool을 무제한 반복하는 범용 Agent Loop가 아니다. 통합 Labs의 일부 시나리오만 명시적인 최대 단계와 종료 조건을 가진다.

---

## 8. Tool Use Labs

`POST /api/labs/run`은 모든 Lab이 공유하는 진입점이다.

```text
요청
  ↓
lab_id=auto ? Ollama Routing Agent : 명시적 Lab 선택
  ↓
Routing Service의 Handler Allowlist
  ↓
Agent-assisted Workflow 또는 Agent-controlled Loop
  ↓
Tool → In-memory Mock Repository
  ↓
공통 결과·Tool Calls·Trace
```

### 공통 요청

```json
{
  "message": "12가3456 차량으로 들어가고 싶어요",
  "session_id": "demo-session",
  "lab_id": "parking",
  "arguments": {},
  "confirmed": false,
  "action_id": null
}
```

`lab_id`는 `auto`, `parking`, `air_conditioner`, `parcel_locker`, `cafe`, `library`, `inventory`, `travel` 중 하나다.

### 공통 응답 핵심 필드

```json
{
  "lab_id": "parking",
  "execution_type": "workflow",
  "status": "confirmation_required",
  "final_answer": "등록 차량입니다. 주차장 문 열기를 확인해 주세요.",
  "state": {},
  "tool_calls": [],
  "trace": [],
  "termination_reason": "confirmation_required",
  "routing": null
}
```

`status`는 `completed`, `needs_clarification`, `confirmation_required`, `rejected`, `error` 중 하나다.

### 일곱 가지 시나리오

| Lab | 실행 형태 | 핵심 흐름 |
|---|---|---|
| 주차장 | Workflow | 번호 추출 → 차량 조회 → 등록·활성 정책 → 확인 → Mock 문 열기 |
| 에어컨 | Workflow | 온도 추출 → 히스테리시스 정책 → 확인 → Mock 제어 |
| 택배함 | Workflow | ID·코드 추출 → 만료·재사용 검사 → 확인 → Mock 열기 |
| 재고 | Workflow | 재고 조회 → 수량·Version 검사 → 확인 → 조건부 예약 |
| 카페 | Agent | 세션 입력 병합 → 누락값 재질문 → Mock 주문 |
| 도서 | Agent | 회원·도서·대출 근거 수집 → Backend 정책 판정 |
| 여행 | Agent | 도시·날짜 확인 → 현재 날씨/예보 선택 → 관광지 조회 → 종료 |

주차장 Lab은 이미지 인식이나 PostgreSQL을 사용하지 않는다. 자연어 또는 `arguments.plate_number`로 받은 번호판과 In-memory Mock 차량 데이터를 사용한다.

---

## 9. Workflow와 Agent 비교

| 항목 | Workflow | Agent |
|---|---|---|
| 흐름 | 코드로 미리 정의 | 관찰 결과에 따라 다음 행동 선택 |
| 정책 | Backend가 결정 | Agent가 제안하되 Backend가 검증 |
| 예측 가능성 | 높음 | 상대적으로 낮음 |
| 유연성 | 정해진 시나리오에 강함 | 다양한 자연어·다단계 탐색에 강함 |
| 상태 변경 | 확인 후 실행 | 확인·Allowlist 없이 실행 불가 |

```text
Workflow = 정해진 절차를 안정적으로 실행
Agent    = 상황에 따라 필요한 Tool과 다음 행동을 선택
```

Agent 사용 여부와 관계없이 보안·승인·재고·인증 같은 최종 정책은 Backend가 소유한다.

---

## 10. 상태 변경과 확인

주차장, 에어컨, 택배함, 재고처럼 상태를 변경하는 Lab은 `confirmed=true`만으로 즉시 실행하지 않는다.

1. Backend가 입력과 정책을 검증한다.
2. 만료 시간이 있는 `pending_action`과 `action_id`를 발급한다.
3. 사용자가 해당 `action_id`로 확인한다.
4. Backend가 action, 만료, 현재 상태를 다시 검증한다.
5. 검증된 Tool만 한 번 실행한다.

확인 단계에서는 Ollama에 같은 요청을 다시 판단시키지 않는다. 택배함 일회성 코드와 재고 Version처럼 실행 사이에 바뀔 수 있는 값은 실행 직전에 다시 검사한다.

---

## 11. Provider와 환경변수

프로젝트 루트의 `.env.example`을 복사해 `.env`를 만들고 개인 설정을 입력한다. `.env`와 API Key는 Git에 커밋하지 않는다.

| 변수 | 기본값/역할 |
|---|---|
| `LLM_PROVIDER` | 기본 Provider, 기본값 `mock` |
| `OPENAI_API_KEY` | OpenAI 생성·Media·Stage 03 Tool Calling |
| `OPENAI_MODEL` | OpenAI 일반·Tool 모델 |
| `OPENAI_VISION_MODEL` | 이미지 분석 모델 |
| `OPENAI_TTS_MODEL` | TTS 모델 |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini 연결 |
| `OLLAMA_BASE_URL` | 기본값 `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Lab Routing·도메인 추출 모델 |
| `BACKEND_API_URL` | 기본값 `http://127.0.0.1:8000` |
| `REQUEST_TIMEOUT_SECONDS` | 외부·Backend 요청 제한 시간 |
| `WEATHER_MODE` | `mock` 또는 `open_meteo` |
| `OPEN_METEO_BASE_URL` | 예보 API 주소 |
| `OPEN_METEO_GEOCODING_URL` | 도시 검색 API 주소 |
| `MAX_IMAGE_SIZE_MB` | 이미지 업로드 제한 |

현재 구현에는 PostgreSQL, Docker Compose, SSE, 별도 Frontend CORS Origin 설정이 필요하지 않다. 해당 기능을 실제로 추가할 때 코드, `.env.example`, README, 본 문서를 함께 갱신한다.

---

## 12. 로컬 실행

PowerShell 기준:

```powershell
cd C:\mini_agent\mini_agent_03_tool
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Backend:

```powershell
cd C:\mini_agent\mini_agent_03_tool\backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Frontend는 새 터미널에서 실행한다.

```powershell
cd C:\mini_agent\mini_agent_03_tool
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py
```

기본 접속 주소:

- Frontend: `http://localhost:8501`
- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Ollama: `http://127.0.0.1:11434`

`LLM_PROVIDER=mock`과 `WEATHER_MODE=mock`에서는 해당 기능을 결정적으로 실습할 수 있다. OpenAI Tool 선택·Agent Cycle과 Media 기능은 유효한 `OPENAI_API_KEY`가 필요하다. `lab_id=auto` 및 Lab의 자연어 인자 추출은 Ollama가 실행 중이어야 한다.

---

## 13. 테스트 기준

```powershell
cd C:\mini_agent\mini_agent_03_tool
.\.venv\Scripts\Activate.ps1
pytest backend\tests
```

필수 확인 항목:

- [ ] `/health`가 정상 응답한다.
- [ ] Frontend가 Backend API에 연결된다.
- [ ] Tool 목록이 Registry와 일치한다.
- [ ] 허용되지 않은 Tool이 실행되지 않는다.
- [ ] 잘못된 arguments가 Pydantic 검증에서 거부된다.
- [ ] 필수 인자가 없으면 Tool을 실행하지 않고 재질문한다.
- [ ] Tool 오류가 공통 오류 코드로 반환된다.
- [ ] Agent Cycle Trace에 선택·실행·최종 답변 단계가 기록된다.
- [ ] 7개 Lab이 올바른 Workflow/Agent Handler로 연결된다.
- [ ] 상태 변경 Lab이 확인 전에는 Tool을 실행하지 않는다.
- [ ] 만료·재사용·Version 충돌이 안전하게 거부된다.
- [ ] Lab reset이 교육용 In-memory 상태만 초기화한다.
- [ ] `WEATHER_MODE=open_meteo`의 외부 오류를 Mock 값으로 숨기지 않는다.

---

## 14. 변경 규칙

- Router는 HTTP 변환만 담당하고 업무 정책을 넣지 않는다.
- 요청·응답 변경은 해당 `schemas/` 모델, Frontend Client, 테스트, 문서를 함께 수정한다.
- Tool을 추가할 때 함수만 만들지 말고 Registry/Allowlist, arguments Schema, 오류 처리, 테스트를 함께 추가한다.
- LLM이 Handler 이름이나 Python 경로를 직접 결정하게 하지 않는다.
- 상태 변경은 pending action과 사용자 확인 절차를 우회하지 않는다.
- Mock 데이터를 실제 운영 데이터처럼 설명하지 않는다.
- 공통 파일(`master.md`, `.env.example`, `requirements.txt`, Router·Schema·Tool Registry)은 변경 영향을 먼저 확인한다.
- 기존 학습 단계의 API와 화면을 불필요하게 깨뜨리지 않는다.

---

## 15. 완료 기준

- [ ] Stage 01·02의 기존 화면과 API가 유지된다.
- [ ] Tool Schema, 선택, 검증, 실행, 오류 처리를 각각 관찰할 수 있다.
- [ ] OpenAI 기반 단일 Agent Cycle이 Tool Result로 최종 답변을 생성한다.
- [ ] Workflow와 Agent의 책임 차이가 Trace에서 드러난다.
- [ ] 모든 Tool은 Allowlist와 Pydantic 검증을 통과해야 실행된다.
- [ ] 중요한 상태 변경은 사용자의 명시적 확인 후 한 번만 실행된다.
- [ ] 7개 Lab이 공통 API와 공통 응답 계약을 사용한다.
- [ ] 단위·API 테스트가 통과한다.
- [ ] README, `.env.example`, Swagger, 본 문서의 실행 정보가 실제 코드와 일치한다.

이 프로젝트의 최종 목표는 Agent에게 모든 권한을 넘기는 것이 아니라, LLM의 유연한 판단을 예측 가능한 Backend 경계 안에서 안전하게 사용하는 방법을 이해하는 것이다.
