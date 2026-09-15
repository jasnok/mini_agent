# Mini Agent MCP Docker 실행 안내

Docker Hub는 이미지 저장소입니다. 실제 프로그램은 Docker Desktop 또는 서버에서 실행됩니다.
Compose 프로젝트 이름은 `mini-agent-mcp-app`이며 Frontend, Backend, Travel, Policy 총 4개입니다.
두 MCP 서버는 Docker에서 Streamable HTTP를 사용합니다.

## 서비스별 설정

| 파일 | 용도 |
| --- | --- |
| `frontend/.env` | Backend 주소 |
| `backend/.env` | OpenAI API 키·모델, Travel·Policy 주소 |
| `mcp_server/travel/.env` | Travel의 실행 주소와 포트 8010 |
| `mcp_server/policy/.env` | Policy의 HTTP 실행 모드와 포트 8011 |

Compose의 `env_file`이 각 파일을 해당 컨테이너에 전달합니다. API 키는 Backend에만 전달합니다.
루트의 기존 `.env`는 로컬 Python 실행용으로 보존했으며 Docker 서비스의 설정 파일이 아닙니다.
Docker용 키를 수정할 때는 `backend/.env`를 수정하세요.
실제 `.env`는 Git과 Docker 이미지에서 제외합니다. 전달용 예시는 각 `.env.example`입니다.

## 이 PC에서 실행·확인

PowerShell에서:

```powershell
cd C:\mini_agent\mini_agent_03_mcp
docker compose config --quiet
docker compose ps
```

네 서비스가 모두 `healthy`이면 정상입니다. 일반 `docker compose config`는 키까지 출력할 수 있으므로 검사에는 `--quiet`을 사용하세요.

- 앱: http://localhost:8501
- API 문서: http://localhost:8000/docs
- MCP 연결 상태: http://localhost:8000/api/mcp/status

```powershell
Invoke-RestMethod http://localhost:8000/api/mcp/status
Invoke-RestMethod http://localhost:8000/api/mcp/tools | ConvertTo-Json -Depth 10
Invoke-RestMethod http://localhost:8000/api/mcp/baggage-policy
docker compose logs --tail 50 backend
```

연결 상태는 `connected`, 도구 수는 3개이며 두 서버의 transport는 `streamable-http`입니다.
앱에서 `MCP Tool 발견`, `수하물 정책 읽기`를 확인하세요.
`MCP Agent 실행`은 유효한 OpenAI 키가 필요하며 API 사용 비용이 발생합니다.
교육용 날씨·호텔·정책 데이터는 코드에 정의된 예제 데이터입니다.

## 다른 PC에서 Docker Hub 이미지로 실행

Docker Desktop의 Linux 컨테이너 환경을 준비합니다. 현재 배포 이미지는 linux/amd64용입니다.
`compose.release.yml`과 다음 네 `.env.example`을 같은 상대 폴더 구조로 전달하세요.
소스 코드나 Dockerfile은 필요하지 않습니다.

```text
배포폴더/
├─ compose.release.yml
├─ frontend/.env.example
├─ backend/.env.example
└─ mcp_server/
   ├─ travel/.env.example
   └─ policy/.env.example
```

배포폴더에서 최초 한 번 실행합니다. 기존 `.env`가 있다면 덮어쓰지 마세요.

```powershell
Copy-Item frontend/.env.example frontend/.env
Copy-Item backend/.env.example backend/.env
Copy-Item mcp_server/travel/.env.example mcp_server/travel/.env
Copy-Item mcp_server/policy/.env.example mcp_server/policy/.env
```

`backend/.env`의 `OPENAI_API_KEY`를 입력하고 실행합니다.
저장소 접근에 인증이 필요한 경우 먼저 `docker login`을 실행하세요.

```powershell
docker compose -f compose.release.yml pull
docker compose -f compose.release.yml up -d --wait
docker compose -f compose.release.yml ps
```

Frontend와 Backend는 PC의 localhost에만 공개됩니다. 두 MCP 포트는 Docker 내부 전용입니다.
Redis·PostgreSQL·Ollama는 이 앱의 의존성이 아닙니다.

## 설정 변경과 코드 변경

`.env`만 바꾼 경우 컨테이너를 다시 생성합니다. 단순 restart는 변경된 환경변수를 반영하지 않습니다.

```powershell
docker compose up -d --force-recreate --wait
```

코드를 바꾼 경우 이미지를 다시 빌드합니다.

```powershell
docker compose up -d --build --wait
```

Docker Hub 업로드는 별도 동작입니다. 다음 명령은 Compose에 지정된 이미지 4개를 올립니다.

```powershell
docker compose push
```

이번 버전은 `jso4603/mini-agent-mcp-frontend:1.0.0`, `mini-agent-mcp-backend:1.0.0`,
`mini-agent-mcp-travel:1.0.0`, `mini-agent-mcp-policy:1.0.0`입니다(모두 `jso4603/` 아래).
다음 배포는 두 Compose의 이미지 버전을 함께 올려 기존 배포본과 구분하세요.

## 종료

```powershell
docker compose down
```

이번 앱의 컨테이너와 네트워크만 제거하며 공용 Redis·PostgreSQL·Ollama는 유지합니다.
