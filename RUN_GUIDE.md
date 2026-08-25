# 팀 로컬 실행 가이드

이 문서는 각 팀원이 자신의 Windows PC에서 PostgreSQL, Backend, Frontend를 실행하고
주차 Workflow와 AI Agent가 정상 동작하는지 확인하는 절차입니다.

## 1. 사전 준비

다음 프로그램이 필요합니다.

- Git
- Python 3.12
- Docker Desktop
- OpenAI API Key(실제 사진 번호판 인식 시 필요)

Docker Desktop은 PostgreSQL 컨테이너를 실행하기 전에 먼저 시작합니다.

## 2. 최신 코드 준비

새로 받는 경우:

```powershell
cd C:\mini
git clone https://github.com/jasnok/team2_miniproject2.git
cd .\team2_miniproject2
git switch develop
```

기존 저장소가 있는 경우 Backend와 Frontend를 먼저 종료한 뒤:

```powershell
cd C:\mini\team2_miniproject2
git switch develop
git pull origin develop
```

이전 버전에서 `.venv`가 Git에 추적되어 pull이 실패하면 기존 가상환경을 저장소 밖으로
옮긴 뒤 pull하고 새로 만드는 방법이 가장 안전합니다.

```powershell
cd C:\mini\team2_miniproject2
Move-Item .venv ..\team2_miniproject2_venv_backup
git pull origin develop
python -m venv .venv
```

새 환경이 정상 동작하는 것을 확인한 후 백업 가상환경은 직접 정리합니다.

## 3. Python 가상환경과 패키지 설치

```powershell
cd C:\mini\team2_miniproject2
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell 프롬프트 앞에 `(.venv)`가 표시되면 활성화된 상태입니다.

## 4. 환경변수 설정

```powershell
Copy-Item .env.example .env
notepad .env
```

실제 이미지에서 차량번호를 인식하면서 Agent 판단은 재현 가능한 Mock으로 확인하는 권장
설정은 다음과 같습니다.

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=본인의_OpenAI_API_Key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
VEHICLE_RECOGNIZER=openai
BACKEND_API_URL=http://127.0.0.1:8000
DATABASE_URL=postgresql://agent_user:agent_password@localhost:5433/agent_db
```

AI Agent의 Tool 선택까지 OpenAI로 실행하려면 다음 값도 변경합니다.

```env
LLM_PROVIDER=openai
```

API 비용 없이 화면과 DB 흐름만 확인하려면 다음처럼 설정합니다. 이때 번호판은 이미지
내용이 아니라 업로드 파일명(예: `12가3456.jpg`)에서 추출합니다.

```env
LLM_PROVIDER=mock
VEHICLE_RECOGNIZER=mock
OPENAI_API_KEY=
```

`.env`에는 실제 비밀값이 들어가므로 Git에 commit하지 않습니다.

## 5. PostgreSQL 실행 및 데이터 준비

### 기존 컨테이너 확인

```powershell
docker ps -a --filter "name=aidevs-pgvector"
```

컨테이너가 있지만 중지 상태이면:

```powershell
docker start aidevs-pgvector
```

컨테이너가 없으면 최초 한 번 생성합니다.

```powershell
docker run --name aidevs-pgvector `
  -e POSTGRES_USER=agent_user `
  -e POSTGRES_PASSWORD=agent_password `
  -e POSTGRES_DB=agent_db `
  -p 5433:5432 `
  -d pgvector/pgvector:pg16
```

### 차량 테이블과 Mock 데이터 생성

테이블이 아직 없을 때만 실행합니다.

```powershell
docker cp .\backend\sql\car_plate.sql aidevs-pgvector:/tmp/car_plate.sql
docker exec -it aidevs-pgvector psql -U agent_user -d agent_db -f /tmp/car_plate.sql
```

`CREATE TABLE`과 `INSERT 0 3`이 출력되면 정상입니다. 이미 테이블이 있다는 오류가 나오면
SQL을 다시 실행하지 않고 아래 조회 명령으로 확인합니다.

```powershell
docker exec aidevs-pgvector psql -U agent_user -d agent_db -c "SELECT * FROM parking_vehicles;"
```

기본 테스트 데이터:

| 차량번호 | DB 상태 | 예상 출입 결과 |
|---|---|---|
| `12가3456` | active | APPROVED, 문 열림 |
| `34나7890` | inactive | BLOCKED, 문 닫힘 |
| `56다1111` | active이지만 만료 | BLOCKED, 문 닫힘 |
| `99가9999` | 미등록 | NOT_FOUND, 문 닫힘 |

## 6. Backend 실행

첫 번째 PowerShell에서 실행합니다.

```powershell
cd C:\mini\team2_miniproject2
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

다음 메시지가 나오면 정상입니다.

```text
Application startup complete.
```

API 문서: <http://127.0.0.1:8000/docs>

`workflow`, `agent`, `tools` 폴더의 변경은 Backend의 자동 reload 대상에 포함되지 않을 수
있습니다. 해당 파일을 수정했다면 `Ctrl+C`로 종료한 뒤 Backend를 다시 실행합니다.

## 7. Frontend 실행

두 번째 PowerShell을 열고 실행합니다.

```powershell
cd C:\mini\team2_miniproject2
.\.venv\Scripts\Activate.ps1
python -m streamlit run .\frontend\app.py
```

자동으로 열리지 않으면 <http://localhost:8501>에 접속합니다.

## 8. 사이트 동작 확인

### Workflow

1. 왼쪽 메뉴에서 `02. Prompt와 구조화 출력`을 펼칩니다.
2. `2-4. Workflow`를 선택합니다.
3. `Backend API`를 선택합니다.
4. 번호판 사진을 촬영하거나 업로드합니다.
5. `Workflow로 출입 확인`을 누릅니다.

### AI Agent

1. `2-5. AI Agent`를 선택합니다.
2. `Backend API`를 선택합니다.
3. 번호판 사진을 촬영하거나 업로드합니다.
4. `AI Agent로 출입 확인`을 누릅니다.

실제 번호판은 화면을 충분히 크게 채우고 정면에서 밝고 선명하게 촬영합니다. 손글씨,
흐린 사진, 가려진 번호판은 Vision 모델이 오인식할 수 있으므로 화면에 표시되는 인식
차량번호를 함께 확인합니다.

## 9. API만 직접 확인하기

Workflow:

```powershell
$body = @{ vehicle_number = "34나7890" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/workflow/parking" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

AI Agent:

```powershell
$body = @{
  message = "34나7890 차량이 들어가려고 합니다."
  vehicle_number = "34나7890"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/agent/parking" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

`34나7890`은 `vehicle_status=BLOCKED`, `gate_opened=false`가 정상입니다.

## 10. 자주 발생하는 문제

### `ModuleNotFoundError: No module named 'app'`

Backend 명령은 반드시 `backend` 폴더에서 실행합니다.

```powershell
cd C:\mini\team2_miniproject2\backend
python -m uvicorn app.main:app --reload --port 8000
```

### Backend 502 오류

- Backend 터미널의 traceback을 먼저 확인합니다.
- `.env`의 `OPENAI_API_KEY`, `VEHICLE_RECOGNIZER`, `DATABASE_URL`을 확인합니다.
- Docker 컨테이너가 실행 중인지 `docker ps`로 확인합니다.
- Backend를 완전히 종료하고 다시 실행합니다.

### DB 연결 실패

```powershell
docker ps --filter "name=aidevs-pgvector"
docker exec aidevs-pgvector pg_isready -U agent_user -d agent_db
```

### PowerShell에서 가상환경 실행이 차단됨

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 11. 종료

Backend와 Frontend 터미널에서 각각 `Ctrl+C`를 누릅니다. PostgreSQL도 종료하려면:

```powershell
docker stop aidevs-pgvector
```
