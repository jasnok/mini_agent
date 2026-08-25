# 담당자 2 — Backend / API

## 1. 문서 목적과 적용 기준

이 문서는 Mini Agent 03의 기존 Backend를 기반으로 주차장 출입 관리 시스템의 HTTP API 계층을 통합하기 위한 담당자 2의 구현 명세다.

문서가 충돌하면 다음 순서로 적용한다.

1. `TEAM_INTEGRATION_CONTRACT.md`
2. 본 문서 `02_backend_api.md`
3. `master.md`

`master.md`의 기존 Stage 01~03 기능은 유지할 수 있지만, 이번 팀 통합의 필수 범위는 `TEAM_INTEGRATION_CONTRACT.md`의 주차장 API 계약이다. 기존 여행 Agent, 7개 Lab과 `/api/labs/run`은 이번 통합의 필수 API로 사용하지 않는다.

다음 안전 원칙은 기존 프로젝트와 팀 통합에서 공통으로 유지한다.

- LLM이 만든 Tool 이름과 arguments를 신뢰하지 않는다.
- Tool 이름은 Allowlist, arguments는 Pydantic Schema로 검증한다.
- DB·Tool·Provider 오류를 정상적인 미등록 차량 결과로 바꾸지 않는다.
- Router에는 승인 정책, Tool 실행 순서와 Agent Prompt를 구현하지 않는다.
- Workflow와 Agent는 담당자 3이 제공하는 동일한 공통 Tool을 사용한다.
- Prompt만으로 안전을 보장하지 않고 Backend에서도 요청과 결과 계약을 검증한다.

## 2. 담당 목표

Frontend의 번호판 이미지 요청을 검증하고 번호판 인식기에 연결하며, Workflow와 AI Agent 실행 함수를 안정적인 공통 HTTP API로 제공한다.

Backend 담당자는 다음을 구현한다.

- FastAPI 앱, Router와 Swagger
- 요청·응답 Pydantic Schema
- 이미지 형식·내용·크기 검증
- 번호판 인식 컴포넌트 연결
- Workflow·Agent 실행 함수 연결
- 외부 결과의 공통 응답 Schema 검증
- HTTP 오류와 timeout 변환
- Backend 단위·API 테스트

## 3. 담당 범위와 경계

Backend 담당자의 기본 작업 범위는 다음과 같다.

```text
/backend
```

권장 구조:

```text
backend/
├─ app/
│  ├─ core/             환경 설정
│  ├─ recognizers/      번호판 인식 인터페이스와 Mock 연결
│  ├─ routers/          FastAPI HTTP 진입점
│  ├─ schemas/          요청·응답 Pydantic 계약
│  ├─ services/         이미지 검증·인식 연결
│  ├─ errors.py         공개 가능한 Backend 예외
│  └─ main.py           FastAPI 앱과 Router 등록
└─ tests/               Backend API 테스트
```

다음 범위는 직접 수정하지 않는다.

- `/frontend`: 화면과 API Client
- `/database`: DB Schema, migration과 Repository
- `/tools`: 공통 Tool, Registry, Executor와 arguments Schema
- `/workflow`: 차량 승인·거부 Workflow
- `/agent`: System Prompt, LLM 판단과 Agent Loop
- `/tests`: 최상위 통합 테스트
- `.env.example`, `requirements.txt`, `TEAM_INTEGRATION_CONTRACT.md`: 통합 담당자 관리 파일

공통 파일 변경이 필요하면 변경 이유와 정확한 항목을 통합 담당자에게 먼저 공유한다. 다른 담당자의 실제 구현을 `/backend`에 복사하지 않는다. 구현이 아직 없으면 공개 계약과 일치하는 Fake 또는 Mock을 Backend 테스트에서 주입한다.

## 4. 책임 구조

```text
Frontend
  ↓ HTTP
Backend Router
  ↓ 요청 Schema 검증
Backend 연결 계층
  ├─ 번호판 인식 Service → Recognizer
  ├─ Parking Workflow → 공통 Tool Executor
  └─ Parking Agent    → 공통 Tool Executor
        ↓
공통 실행 결과 Schema 검증
  ↓
HTTP 응답
```

Router는 HTTP 요청·응답 변환에 집중한다. 다음 로직을 Router에 넣지 않는다.

- 차량 승인·거부 판단
- `check_vehicle`, `open_gate`, `deny_gate` 실행 순서
- 차량 번호 정규화의 최종 업무 규칙
- DB 조회와 연결 정책
- Agent System Prompt와 Tool 선택 방식
- Agent 반복 호출과 종료 조건

## 5. 차량 번호와 상태 계약

시스템 내부와 HTTP API의 차량 번호 필드명은 모두 `vehicle_number`를 사용한다.

```text
12가3456
```

최종 정규화와 유효성 규칙은 Database / Tool 담당자가 제공한다. Backend는 API 요청 형식과 필수값을 검증하되, 다른 계층의 최종 규칙을 중복 구현하지 않는다.

허용 차량 상태:

| 값 | 의미 |
|---|---|
| `APPROVED` | 등록되어 있고 출입 허용 |
| `BLOCKED` | 등록되어 있지만 출입 차단 |
| `NOT_FOUND` | 등록되지 않음 |

DB 연결 실패, timeout과 Tool 예외는 `NOT_FOUND`가 아니다.

## 6. 공통 Tool 연결 계약

Workflow와 Agent가 사용하는 공통 Tool은 담당자 3의 `/tools`에서 제공한다.

```text
check_vehicle(vehicle_number: str)
open_gate(vehicle_number: str)
deny_gate(vehicle_number: str, reason: str)
```

허용 Tool은 `check_vehicle`, `open_gate`, `deny_gate`뿐이다. Backend는 Tool을 직접 구현하거나 Router에서 직접 호출하지 않는다.

Backend가 기대하는 안전 규칙:

- 모든 Tool 실행은 공통 Registry와 Executor를 통과한다.
- Agent arguments도 사용자 입력과 동일하게 검증한다.
- `check_vehicle` 성공 전에 Gate Tool을 실행하지 않는다.
- 한 요청에서 `open_gate`와 `deny_gate`를 모두 실행하지 않는다.
- DB·Tool 오류 후 다른 Gate Tool로 임의 전환하지 않는다.

공통 Tool 오류 코드:

| 코드 | 의미 |
|---|---|
| `TOOL_NOT_ALLOWED` | Allowlist에 없는 Tool |
| `TOOL_VALIDATION_ERROR` | arguments 검증 실패 |
| `TOOL_EXECUTION_ERROR` | Tool 실행 예외 |
| `DATABASE_UNAVAILABLE` | DB 연결 또는 조회 불가 |

## 7. 외부 실행 함수 계약

### 7.1 Workflow

담당자 4가 다음 동기 함수를 제공한다.

```python
def run_parking_workflow(vehicle_number: str) -> dict:
    ...
```

Backend는 요청을 검증하고 이 함수를 호출한 뒤 반환값을 공통 실행 결과 Schema로 검증한다. Backend가 차량 상태에 따라 Gate Tool을 추가로 호출하거나 결과를 재판단하지 않는다.

### 7.2 AI Agent

담당자 5가 다음 비동기 함수를 제공한다.

```python
async def run_parking_agent(
    message: str,
    vehicle_number: str | None = None,
) -> dict:
    ...
```

Backend는 `message`와 구조화된 `vehicle_number`를 전달하고, timeout과 Provider 오류를 HTTP 오류로 변환한다. Tool 선택, 반복 호출 감지, 최대 3회 제한과 종료 판단은 Agent 담당 범위다.

외부 구현이 준비되지 않은 동안에는 Backend 테스트에서 같은 Signature의 Fake를 주입한다. Import 실패를 `NOT_FOUND`나 정상 업무 결과로 변환하지 않는다.

## 8. HTTP API 계약

### 8.1 상태 확인

```http
GET /health
```

Backend 실행 상태와 필요한 기본 설정 상태를 반환한다. API Key, DB 접속정보와 같은 민감정보는 반환하지 않는다.

### 8.2 번호판 이미지 인식

```http
POST /api/vehicle/recognize
Content-Type: multipart/form-data
```

입력:

```text
image: 번호판 이미지 파일
```

성공 응답:

```json
{
  "success": true,
  "vehicle_number": "12가3456",
  "message": "차량 번호를 인식했습니다."
}
```

인식 실패 응답 예시:

```json
{
  "success": false,
  "vehicle_number": null,
  "message": "차량 번호를 인식하지 못했습니다."
}
```

번호판 인식은 Tool, Workflow와 Agent에 포함하지 않는다. 초기 통합에서는 파일명, 고정 샘플 또는 Mock 인식기를 사용할 수 있다. 실제 OCR이나 Vision Provider를 추가해도 HTTP 계약은 유지한다.

### 8.3 Workflow 실행

```http
POST /api/workflow/parking
Content-Type: application/json
```

요청:

```json
{
  "vehicle_number": "12가3456"
}
```

Backend는 `run_parking_workflow(vehicle_number)`를 호출하고 공통 실행 결과를 반환한다.

### 8.4 AI Agent 실행

```http
POST /api/agent/parking
Content-Type: application/json
```

요청:

```json
{
  "message": "12가3456 차량이 들어가려고 합니다.",
  "vehicle_number": "12가3456"
}
```

`message`와 `vehicle_number` 중 하나 이상을 포함해야 한다. 이미지 인식을 거친 요청은 가능한 경우 구조화된 `vehicle_number`를 함께 전달한다.

Backend는 `await run_parking_agent(...)`를 호출하고 공통 실행 결과를 반환한다.

### 8.5 기존 API와의 관계

`master.md`의 Stage 01~03 API와 `/api/labs/run`은 기존 학습 기능으로 남아 있을 수 있다. 그러나 이번 주차장 팀 통합의 필수 계약은 다음 세 Endpoint다.

```text
/api/vehicle/recognize
/api/workflow/parking
/api/agent/parking
```

기존 `/api/labs/run` 응답을 새 주차장 API 응답으로 임의 변환해 사용하지 않는다.

## 9. 이미지 검증

Backend는 번호판 인식기를 호출하기 전에 다음을 검증한다.

1. 파일이 비어 있지 않은지 확인한다.
2. 허용된 MIME 형식인지 확인한다.
3. MIME과 실제 파일 Signature가 일치하는지 확인한다.
4. 파일 크기가 제한을 넘지 않는지 확인한다.
5. 검증된 파일만 번호판 인식기에 전달한다.

기본 최대 크기는 `5MB`다. 지원 형식은 `.env.example`과 Swagger에 명시한다. 크기 초과와 형식 오류를 구분할 수 있도록 별도의 Backend 예외를 사용한다.

| 상황 | HTTP 상태 |
|---|---:|
| 빈 파일·지원하지 않는 형식·Signature 불일치 | `422` |
| 이미지 크기 초과 | `413` |
| 인식 Provider 또는 의존성 오류 | `502` |
| 인식 처리 timeout | `504` |

## 10. 요청·응답 Schema

### 10.1 Workflow 요청

```text
vehicle_number: 필수 문자열
```

### 10.2 Agent 요청

```text
message: 선택 문자열
vehicle_number: 선택 문자열
```

Pydantic 모델 검증으로 두 필드 중 하나 이상을 요구한다.

### 10.3 공통 실행 결과

Workflow와 Agent는 다음 핵심 필드를 동일하게 반환한다.

```json
{
  "success": true,
  "vehicle_number": "12가3456",
  "registered": true,
  "vehicle_status": "APPROVED",
  "gate_opened": true,
  "message": "문이 열렸습니다.",
  "execution_type": "workflow",
  "status": "completed",
  "trace": [],
  "termination_reason": "completed",
  "error": null
}
```

| 필드 | 형식 | 의미 |
|---|---|---|
| `success` | boolean | 시스템 오류 없이 처리되었는지 여부 |
| `vehicle_number` | string 또는 null | 정규화된 차량 번호 |
| `registered` | boolean | 등록 여부 |
| `vehicle_status` | 차량 상태 또는 null | `APPROVED`, `BLOCKED`, `NOT_FOUND` |
| `gate_opened` | boolean | Gate 개방 여부 |
| `message` | string | 사용자 안내 문구 |
| `execution_type` | string | `workflow` 또는 `agent` |
| `status` | string | 공통 처리 상태 |
| `trace` | array | 단계별 실행 기록 |
| `termination_reason` | string | 종료 이유 |
| `error` | object 또는 null | 시스템 오류 정보 |

출입 거부는 정상 업무 결과이므로 `success=true`다. 입력·DB·Tool·Provider 오류는 `success=false`다.

처리 상태:

```text
completed
needs_clarification
rejected
error
```

종료 이유:

```text
completed
needs_clarification
tool_not_allowed
tool_validation_error
tool_execution_error
database_unavailable
provider_timeout
provider_error
invalid_provider_response
repeated_tool_call
max_steps_exceeded
policy_rejected
```

오류 객체:

```json
{
  "code": "TOOL_EXECUTION_ERROR",
  "message": "차량 조회 중 오류가 발생했습니다."
}
```

Backend는 Workflow와 Agent 반환값을 Pydantic 공통 응답 모델로 검증한다. 필드명을 임의 변환해 다른 담당자의 계약 불일치를 숨기지 않는다.

## 11. Trace 계약

Trace 항목 예시:

```json
{
  "step": 1,
  "stage": "vehicle_check",
  "status": "completed",
  "tool_name": "check_vehicle",
  "arguments": {"vehicle_number": "12가3456"},
  "result": {"status": "APPROVED"},
  "error_code": null,
  "elapsed_ms": 15
}
```

권장 `stage`:

```text
input_validation
vehicle_check
policy_decision
tool_selection
tool_validation
tool_execution
final_answer
terminated
```

Backend는 Trace를 재판단하거나 Tool 실행을 추가하지 않고 공통 Schema로 검증해 전달한다. Trace에는 비밀번호, API Key, 전체 Prompt, DB 접속정보와 불필요한 개인정보를 기록하지 않는다.

## 12. 오류와 HTTP 상태 코드

HTTP 상태 코드와 응답 의미를 다음과 같이 일치시킨다.

| 상황 | 상태 코드 |
|---|---:|
| 잘못된 요청·이미지 형식 | `422` |
| 이미지 크기 초과 | `413` |
| DB·Tool·Provider 의존성 오류 | `502` |
| LLM·외부 처리 timeout | `504` |
| 예상하지 못한 내부 오류 | `500` |
| `BLOCKED`, `NOT_FOUND` | `200` |
| `needs_clarification` | `200` |

다음 규칙을 적용한다.

- `BLOCKED`와 `NOT_FOUND`는 정상적으로 완료된 업무상 거부다.
- DB 연결 실패를 `NOT_FOUND`로 바꾸지 않는다.
- Tool·Provider 오류 후 Backend가 Gate Tool을 추가 호출하지 않는다.
- 내부 예외 메시지를 HTTP 응답에 그대로 포함하지 않는다.
- Stack Trace, DB 접속정보, SQL, API Key와 Provider의 민감한 원문을 노출하지 않는다.
- 공개 오류에는 안정적인 `code`와 사용자 안내용 `message`만 포함한다.

## 13. 환경변수

공통 설정은 환경변수로 주입하고 비밀번호와 API Key를 코드에 하드코딩하지 않는다.

```text
DATABASE_URL
LLM_PROVIDER
OPENAI_API_KEY
OPENAI_MODEL
OLLAMA_BASE_URL
OLLAMA_MODEL
BACKEND_API_URL
REQUEST_TIMEOUT_SECONDS
MAX_IMAGE_SIZE_MB
```

권장 기본값:

```env
LLM_PROVIDER=mock
BACKEND_API_URL=http://127.0.0.1:8000
REQUEST_TIMEOUT_SECONDS=60
MAX_IMAGE_SIZE_MB=5
```

`.env`는 Git에 커밋하지 않는다. `.env.example`과 `requirements.txt` 변경은 통합 담당자에게 필요한 항목과 이유를 전달한다.

## 14. 다른 담당자와의 연결

| 협업 대상 | 합의할 내용 |
|---|---|
| Frontend | 세 Endpoint, 이미지 제한과 공통 응답 Schema |
| Database / Tool | Tool 오류 형식, 차량 번호 규칙과 DB 오류 전달 방식 |
| Workflow | `run_parking_workflow()` Signature, 결과와 예외 계약 |
| AI Agent | `run_parking_agent()` Signature, timeout, 결과와 예외 계약 |
| 통합 담당자 | `.env.example`, 의존성, 최상위 통합 테스트와 계약 변경 |

통합은 다음 순서를 따른다.

```text
Tool → Workflow/Agent → Backend → Frontend
```

다른 구현이 준비되지 않은 동안에는 계약과 일치하는 Fake 또는 Mock으로 Backend API를 테스트한다. 다른 담당자의 실제 코드를 Backend 디렉터리에 복사하지 않는다.

## 15. Backend 테스트 기준

- [ ] `/health`가 정상 응답한다.
- [ ] 지원하지 않는 이미지와 Signature 불일치가 `422`로 거부된다.
- [ ] 5MB를 초과한 이미지가 `413`으로 거부된다.
- [ ] 번호판 인식 성공·실패가 공통 형식으로 반환된다.
- [ ] `/api/workflow/parking`이 Workflow 실행 함수를 호출한다.
- [ ] `/api/agent/parking`이 비동기 Agent 실행 함수를 호출한다.
- [ ] Agent 요청에 `message`와 `vehicle_number` 중 하나 이상이 필요하다.
- [ ] Workflow와 Agent 응답이 동일한 공통 Schema를 사용한다.
- [ ] `BLOCKED`와 `NOT_FOUND`가 HTTP `200`의 정상 업무 결과로 반환된다.
- [ ] DB 오류가 `NOT_FOUND`로 변환되지 않는다.
- [ ] DB·Tool·Provider 오류가 `502`로 변환된다.
- [ ] LLM과 외부 처리 timeout이 `504`로 변환된다.
- [ ] 예상하지 못한 내부 오류가 `500`으로 변환된다.
- [ ] 내부 예외와 민감정보가 응답에 노출되지 않는다.
- [ ] Trace의 구조와 종료 이유가 공통 Schema로 검증된다.
- [ ] Swagger에서 세 주차장 API 계약을 확인할 수 있다.
- [ ] Router에 차량 정책, Tool 순서와 Agent Prompt가 포함되지 않는다.

## 16. 완료 기준

- [ ] 번호판 이미지 업로드와 검증이 동작한다.
- [ ] 번호판 인식 성공·실패를 공통 형식으로 반환한다.
- [ ] Workflow 실행 API가 구현되어 있다.
- [ ] AI Agent 실행 API가 구현되어 있다.
- [ ] Workflow와 Agent의 핵심 응답 형식이 일치한다.
- [ ] 세 차량 상태가 공통 계약에 맞게 전달된다.
- [ ] 출입 거부와 시스템 오류가 구분된다.
- [ ] 오류와 timeout이 올바른 HTTP 상태로 변환된다.
- [ ] Workflow와 Agent가 반환한 Trace를 안전하게 전달한다.
- [ ] Swagger에 요청·응답 및 오류 계약이 표시된다.
- [ ] Router에 DB·Workflow·Tool·Agent 내부 정책이 섞이지 않는다.
- [ ] Backend 단위·API 테스트가 통과한다.

이번 Backend 통합의 목표는 Agent나 Router에 출입 권한을 몰아주는 것이 아니라, 각 담당자의 구현을 명확한 HTTP 계약과 검증 경계로 안전하게 연결하는 것이다.
