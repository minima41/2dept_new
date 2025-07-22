# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a React + FastAPI investment monitoring web application (투자본부 웹 애플리케이션) designed for a team of ~10 people. The project integrates existing Python scripts for DART disclosure monitoring and stock price tracking into a unified real-time web platform.

## Architecture

### Modular Monolith Structure
```
C:\2dept\
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Configuration management
│   │   ├── modules/           # Business modules
│   │   │   ├── dart/          # DART disclosure monitoring
│   │   │   ├── stocks/        # Stock price monitoring
│   │   │   ├── portfolio/     # Portfolio management
│   │   │   ├── funds/         # Fund management
│   │   │   └── keywords/      # Keyword management
│   │   ├── shared/            # Common modules
│   │   │   ├── database.py    # DB connection
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── email.py       # Email notifications
│   │   │   └── websocket.py   # WebSocket manager
│   │   └── data/              # Data files
│   │       ├── monitoring_stocks.json
│   │       ├── notifications.json
│   │       └── processed_ids.txt
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   ├── services/          # API calls
│   │   ├── stores/            # Zustand stores
│   │   ├── hooks/             # Custom hooks
│   │   └── types/             # TypeScript types
└── logs/                       # Log files
```

### Module Structure Pattern
Each module follows this pattern:
- `router.py` - FastAPI router with endpoints
- `service.py` - Business logic
- `models.py` - Pydantic models
- `monitor.py` - Background tasks (optional)

## Technology Stack

### Backend (FastAPI)
- **Framework**: FastAPI + Python 3.9+
- **Database**: SQLite (development) → PostgreSQL (production)
- **Real-time**: WebSocket (FastAPI built-in)
- **Scheduling**: APScheduler
- **Authentication**: JWT tokens

### Frontend (React)
- **Framework**: React 18 + TypeScript + Vite
- **State Management**: Zustand + React Query
- **UI Framework**: Tailwind CSS + Recharts
- **Real-time**: WebSocket client hooks

## Key Configuration

### Environment Variables (.env)
```env
# DART API
DART_API_KEY=d63d0566355b527123f1d14cf438c84041534b2b

# Email Settings
EMAIL_SENDER=dlwlrma401@gmail.com
EMAIL_PASSWORD=byvu_dkyn_qfyz_lwji
EMAIL_RECEIVER=ljm@inveski.com

# Database
DATABASE_URL=sqlite:///./app.db

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### DART Module Configuration
- **API Key**: `d63d0566355b527123f1d14cf438c84041534b2b`
- **Check Interval**: 30 minutes (1800 seconds)
- **Companies**: Defined in `config.py` COMPANIES dictionary
- **Keywords**: Defined in `config.py` KEYWORDS list
- **Processed IDs**: Tracked in `processed_ids.txt`

### Stock Monitoring Configuration
- **Update Interval**: 5-10 seconds during market hours (09:00-15:35)
- **Data Source**: PyKrx API (primary) → Naver crawling (fallback)
- **Alert Types**: TP/SL prices, daily surge/drop thresholds
- **Data Storage**: `monitoring_stocks.json`

## Common Development Tasks

### Running the Application
```bash
# Backend
cd backend
pip install -r requirements.txt
python app/main.py

# Frontend
cd frontend
npm install
npm run dev

# Full stack with Docker
docker-compose up
```

### Development Servers
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Network Access**: http://192.168.x.x:3000

### WebSocket Events
- `dart_update` - New DART disclosure
- `stock_update` - Real-time stock price update
- `alert_triggered` - Price alert notification
- `system_status` - System status change

## Coding Standards

### Backend (FastAPI)
- Use async/await pattern throughout
- All API responses must use Pydantic models
- Environment variables for sensitive data
- Standard error handling with proper HTTP status codes

### Frontend (React)
- Functional components + hooks only
- TypeScript strict mode enabled
- Tailwind CSS utility classes only
- React Query for server state management
- Zustand for client state management

### File Operations
- Use FileLock for concurrent JSON file access
- Automatic daily backup of data files
- File size limit: 10MB

## Logging

### Log Directory Structure
```
C:\2dept\logs\
├── app.log              # General application logs
├── dart_monitor.log     # DART monitoring logs
├── stock_manager.log    # Stock monitoring logs
├── email.log           # Email sending logs
└── error.log           # Error logs
```

### Log Rotation
- Max file size: 5MB
- Keep 3 backup files
- UTF-8 encoding

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
Focus on:
- WebSocket connection stability
- Real-time data flow
- External API failure scenarios
- Concurrent user access (10 users)

## Performance Requirements

### Concurrent Users
- Support 10 simultaneous users
- WebSocket connection limit: 50 connections
- Memory usage monitoring required

### Real-time Updates
- DART: 30-minute intervals
- Stock prices: 5-10 seconds during market hours
- WebSocket message broadcasting

## Security Considerations

### API Keys
- Never hardcode API keys in source code
- Use environment variables exclusively
- Keep .env files out of version control

### Authentication
- JWT token-based authentication
- 30-minute token expiration
- CORS settings appropriately restricted

## Data Management

### File-based Data (Legacy Support)
- `monitoring_stocks.json` - Stock watchlist
- `notifications.json` - Alert history
- `processed_ids.txt` - Processed DART disclosure IDs
- Located in `C:\2dept\backend\app\data\`

### Database Schema
- **users** table - User information
- **funds** table - Fund information
- **alert_history** table - Alert tracking

## Project Tasks

The repository contains a comprehensive task list in `shrimp/tasks.json` with 9 main development phases:

1. **Project Structure & Environment Setup**
2. **Shared Modules & WebSocket Communication**
3. **DART Disclosure Monitoring Module**
4. **Stock Price Monitoring Module**
5. **React Dashboard & Basic UI**
6. **DART Frontend Implementation**
7. **Stock Monitoring Frontend**
8. **Portfolio Management Integration**
9. **System Integration Testing & Deployment**

Each task includes detailed implementation guides, verification criteria, and file dependencies.

## Important Notes

### Prohibited Practices
- No browser storage (localStorage, sessionStorage)
- No Django framework usage
- No microservices architecture
- No real-time polling (use WebSocket instead)
- No hardcoded sensitive information
- No synchronous file I/O operations

### Development Priorities
1. User experience first
2. System stability second
3. Development productivity third
4. Code quality fourth

### External Dependencies
- **DART OpenAPI**: Government disclosure API
- **PyKrx**: Korean stock market data
- **Naver Finance**: Fallback for stock prices
- **Email SMTP**: Gmail for notifications

This project aims to modernize existing Python monitoring scripts into a professional web application while maintaining the proven monitoring logic and data structures.


## 한국어 Claude 지침 및 MCP 활용 가이드

**기본 지침**: 모든 응답은 한국어로 제공하며, MCP(Model Context Protocol) 도구를 적극 활용합니다.

### Playwright MCP Server 사용 예시
```json
// 페이지 열기
{ "tool":"playwright","parameters":{"action":"goto","url":"https://example.com"}}

// 로그인 버튼 클릭
{ "tool":"playwright","parameters":{"action":"click","selector":"#login-button"}}

// 검색어 입력 후 엔터
{ "tool":"playwright","parameters":{"action":"fill","selector":"input[name='q']","text":"MCP Server"}}
{ "tool":"playwright","parameters":{"action":"press","selector":"input[name='q']","key":"Enter"}}

// 페이지 스크린샷 저장
{ "tool":"playwright","parameters":{"action":"screenshot","path":"search-results.png"}}

// 콘솔 에러 로그 수집
{ "tool":"playwright","parameters":{"action":"getConsoleLogs"}}

// 네트워크 요청 내역 수집
{ "tool":"playwright","parameters":{"action":"getNetworkRequests"}}

// JS 평가(페이지 타이틀 가져오기)
{ "tool":"playwright","parameters":{"action":"evaluate","expression":"document.title"}}

// 접근성 스냅샷(구조화된 DOM)
{ "tool":"playwright","parameters":{"action":"accessibilitySnapshot"}}
```

### Context7 라이브러리 조회
```json
// 라이브러리 버전 조회
{ "tool": "context7", "parameters": {"query": "axios 최신 버전 알려줘"}}

// 패키지 사용법 검색
{ "tool": "context7", "parameters": {"query": "lodash 사용법 예시"}}
```


### Git MCP 사용법 

**.gitignore 설정**: 먼저 .gitignore 파일을 프로젝트 루트에 만들고 IDE 설정 파일, 빌드 산출물, 로그, node_modules/, vendor/ 등 불필요한 항목을 명시합니다.

```json
// 1. 초기화 & 커밋
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": [
      "/c",
      "git init && echo IDE/.vs/ > .gitignore && git add . && git commit -m \"chore: initial project baseline\""
    ]
  }
}

// 2. 파일 수정 후 커밋 플로우
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": [
      "/c",
      "git add SHORTS_REAL/script_result.php && git commit -m \"feat: change button label\""
    ]
  }
}
```


```json
// 3. 파일 목록 조회
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "dir /S"]
  }
}

// 4. 패턴 검색
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "findstr /S /I /R \"console\\.log\" *.js"]
  }
}

// 5. 테스트 실행 후 자동 커밋
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "npm test -- --verbose && git add . && git commit -m \"test: auto commit\""]
  }
}

// 6. 파일 생성 + 커밋
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "echo DB_HOST=... > .env.example && git add .env.example && git commit -m \"chore: add env template\""]
  }
}

// 7. 파일 삭제 + 커밋
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "git rm debug.log && git commit -m \"build: drop debug log\""]
  }
}

// 8. 특정 파일 내용 읽기
{
  "tool": "git",
  "parameters": {
    "subtool": "RunCommand",
    "path": "/mnt/c/2dept",
    "command": "cmd",
    "args": ["/c", "git show HEAD:SHORTS_REAL/script_result.php"]
  }
}
```


---

## 프로젝트별 특화 지침 (Project-Specific Guidelines)

### 웹사이트 및 경로 설정
1. **루트 경로**: `/mnt/c/2dept` → http://localhost
2. **메인 페이지**: http://localhost 접속 시 `index.php` 페이지 표시
3. **URL 접근**: http://localhost/site가 아닌 http://localhost로 접근
4. **로그 위치**: `/mnt/c/2dept/logs` - 모든 실행 오류 기록

### 웹 테스트 및 브라우징
- **Playwright 사용법**: DOM 구조 먼저 확인 → 요소 클릭/내용 확인
- **테스트 순서**: 텍스트 박스, 버튼, 링크 확인 → 필요시 상호작용
- **웹 자료 검색**: Google Search 후 Playwright 브라우징

### 데이터베이스 설정
```bash
# MySQL 접속 정보
HOST: localhost
USER: root
PASSWORD: (공백)
DATABASE: mydb
```

### 테스트 사용자 계정
```
아이디: newuser@example.com
비밀번호: Test12345
```

### Git 워크플로우
- **브랜치 구조**: test (개발) → master (메인)
- **파일 삭제**: `git rm` 및 commit 사용
- **PR 프로세스**: test 브랜치 검증 → master 병합
- **GitHub CLI**: `gh` 명령어 활용

### 작업 진행 원칙
- **사전 승인**: 모든 작업 전 사용자 동의 획득
- **단계별 진행**: 작업을 임의로 진행하지 않음
- **안전한 배포**: HTTP 버퍼 크기 조정, 작은 커밋 단위로 푸시

## 클로드 코드에서의 mcp-installer를 사용한 MCP (Model Context Protocol) 설치 및 설정 가이드 
공통 주의사항
1. 현재 사용 환경을 확인할 것. 모르면 사용자에게 물어볼 것. 
2. OS(윈도우,리눅스,맥) 및 환경들(WSL,파워셀,명령프롬프트등)을 파악해서 그에 맞게 세팅할 것. 모르면 사용자에게 물어볼 것.
3. mcp-installer을 이용해 필요한 MCP들을 설치할 것
   (user 스코프로 설치 및 적용할것)
4. 특정 MCP 설치시, 바로 설치하지 말고, WebSearch 도구로 해당 MCP의 공식 사이트 확인하고 현재 OS 및 환경 매치하여, 공식 설치법부터 확인할 것
5. 공식 사이트 확인 후에는 context7 MCP 존재하는 경우, context7으로 다시 한번 확인할 것
6. MCP 설치 후, task를 통해 디버그 모드로 서브 에이전트 구동한 후, /mcp 를 통해 실제 작동여부를 반드시 확인할 것 
7. 설정 시, API KEY 환경 변수 설정이 필요한 경우, 가상의 API 키로 디폴트로 설치 및 설정 후, 올바른 API 키 정보를 입력해야 함을 사용자에게 알릴 것
8. Mysql MCP와 같이 특정 서버가 구동중 상태여만 정상 작동한 것은 에러가 나도 재설치하지 말고, 정상 구동을 위한 조건을 사용자에게 알릴 것
9. 현재 클로드 코드가 실행되는 환경이야.
10. 설치 요청 받은 MCP만 설치하면 돼. 혹시 이미 설치된 다른 MCP 에러 있어도, 그냥 둘 것
11. 일단, 터미널에서 설치하려는 MCP 작동 성공한 경우, 성공 시의 인자 및 환경 변수 이름을 활용해, 올바른 위치의 json 파일에 MCP 설정을 직접할 것
12. WSL sudo 패스워드: qsc1445!   

*윈도우에서의 주의사항*
1. 설정 파일 직접 세팅시, Windows 경로 구분자는 백슬래시(\)이며, JSON 내에서는 반드시 이스케이프 처리(\\\\)해야 해.
** OS 공통 주의사항**
1. Node.js가 %PATH%에 등록되어 있는지, 버전이 최소 v18 이상인지 확인할 것
2. npx -y 옵션을 추가하면 버전 호환성 문제를 줄일 수 있음

### MCP 서버 설치 순서

1. 기본 설치
	mcp-installer를 사용해 설치할 것

2. 설치 후 정상 설치 여부 확인하기	
	claude mcp list 으로 설치 목록에 포함되는지 내용 확인한 후,
	task를 통해 디버그 모드로 서브 에이전트 구동한 후 (claude --debug), 최대 2분 동안 관찰한 후, 그 동안의 디버그 메시지(에러 시 관련 내용이 출력됨)를 확인하고 /mcp 를 통해(Bash(echo "/mcp" | claude --debug)) 실제 작동여부를 반드시 확인할 것

3. 문제 있을때 다음을 통해 직접 설치할 것

	*User 스코프로 claude mcp add 명령어를 통한 설정 파일 세팅 예시*
	예시1:
	claude mcp add --scope user youtube-mcp \
	  -e YOUTUBE_API_KEY=$YOUR_YT_API_KEY \

	  -e YOUTUBE_TRANSCRIPT_LANG=ko \
	  -- npx -y youtube-data-mcp-server


4. 정상 설치 여부 확인 하기
	claude mcp list 으로 설치 목록에 포함되는지 내용 확인한 후,
	task를 통해 디버그 모드로 서브 에이전트 구동한 후 (claude --debug), 최대 2분 동안 관찰한 후, 그 동안의 디버그 메시지(에러 시 관련 내용이 출력됨)를 확인하고, /mcp 를 통해(Bash(echo "/mcp" | claude --debug)) 실제 작동여부를 반드시 확인할 것


5. 문제 있을때 공식 사이트 다시 확인후 권장되는 방법으로 설치 및 설정할 것
	(npm/npx 패키지를 찾을 수 없는 경우) pm 전역 설치 경로 확인 : npm config get prefix
	권장되는 방법을 확인한 후, npm, pip, uvx, pip 등으로 직접 설치할 것

	#### uvx 명령어를 찾을 수 없는 경우
	# uv 설치 (Python 패키지 관리자)
	curl -LsSf https://astral.sh/uv/install.sh | sh

	#### npm/npx 패키지를 찾을 수 없는 경우
	# npm 전역 설치 경로 확인
	npm config get prefix


	#### uvx 명령어를 찾을 수 없는 경우
	# uv 설치 (Python 패키지 관리자)
	curl -LsSf https://astral.sh/uv/install.sh | sh


	## 설치 후 터미널 상에서 작동 여부 점검할 것 ##
	
	## 위 방법으로, 터미널에서 작동 성공한 경우, 성공 시의 인자 및 환경 변수 이름을 활용해서, 클로드 코드의 올바른 위치의 json 설정 파일에 MCP를 직접 설정할 것 ##


	설정 예시
		(설정 파일 위치)
		**리눅스, macOS 또는 윈도우 WSL 기반의 클로드 코드인 경우**
		- **User 설정**: `~/.claude/` 디렉토리
		- **Project 설정**: 프로젝트 루트/.claude

		**윈도우 네이티브 클로드 코드인 경우**
		- **User 설정**: `C:\2dept\.claude` 디렉토리
		- *User 설정파일*  C:\2dept\.claude.json
		- **Project 설정**: 2dept\.claude

		1. npx 사용

		{
		  "youtube-mcp": {
		    "type": "stdio",
		    "command": "npx",
		    "args": ["-y", "youtube-data-mcp-server"],
		    "env": {
		      "YOUTUBE_API_KEY": "YOUR_API_KEY_HERE",
		      "YOUTUBE_TRANSCRIPT_LANG": "ko"
		    }
		  }
		}


		2. cmd.exe 래퍼 + 자동 동의)
		{
		  "mcpServers": {
		    "mcp-installer": {
		      "command": "cmd.exe",
		      "args": ["/c", "npx", "-y", "@anaisbetts/mcp-installer"],
		      "type": "stdio"
		    }
		  }
		}

		3. 파워셀예시
		{
		  "command": "powershell.exe",
		  "args": [
		    "-NoLogo", "-NoProfile",
		    "-Command", "npx -y @anaisbetts/mcp-installer"
		  ]
		}

		4. npx 대신 node 지정
		{
		  "command": "node",
		  "args": [
		    "%APPDATA%\\npm\\node_modules\\@anaisbetts\\mcp-installer\\dist\\index.js"
		  ]
		}

		5. args 배열 설계 시 체크리스트
		토큰 단위 분리: "args": ["/c","npx","-y","pkg"] 와
			"args": ["/c","npx -y pkg"] 는 동일해보여도 cmd.exe 내부에서 따옴표 처리 방식이 달라질 수 있음. 분리가 안전.
		경로 포함 시: JSON에서는 \\ 두 번. 예) "C:\\tools\\mcp\\server.js".
		환경변수 전달:
			"env": { "UV_DEPS_CACHE": "%TEMP%\\uvcache" }
		타임아웃 조정: 느린 PC라면 MCP_TIMEOUT 환경변수로 부팅 최대 시간을 늘릴 수 있음 (예: 10000 = 10 초) 

**중요사항**
	윈도우 네이티브 환경이고 MCP 설정에 어려움이 있는데 npx 환경이라면, cmd나 node 등으로 다음과 같이 대체해 볼것:
	{
	"mcpServers": {
	      "context7": {
		 "command": "cmd",
		 "args": ["/c", "npx", "-y", "@upstash/context7-mcp@latest"]
	      }
	   }
	}

	claude mcp add-json context7 -s user '{"type":"stdio","command":"cmd","args": ["/c", "npx", "-y", "@upstash/context7-mcp@latest"]}'

(설치 및 설정한 후는 항상 아래 내용으로 검증할 것)
	claude mcp list 으로 설치 목록에 포함되는지 내용 확인한 후,
	task를 통해 디버그 모드로 서브 에이전트 구동한 후 (claude --debug), 최대 2분 동안 관찰한 후, 그 동안의 디버그 메시지(에러 시 관련 내용이 출력됨)를 확인하고 /mcp 를 통해 실제 작동여부를 반드시 확인할 것

ㅊㅇ 
		
** MCP 서버 제거가 필요할 때 예시: **
claude mcp remove youtube-mcp


## 윈도우 네이티브 클로드 코드에서 클로드 데스크탑의 MCP 가져오는 방법 ###
"C:\Users\<사용자이름>\AppData\Roaming\Claude\claude_desktop_config.json" 이 파일이 존재한다면 클로드 데스크탑이 설치된 상태야.
이 파일의 mcpServers 내용을 클로드 코드 설정 파일(C:\Users\{사용자명}\.claude.json)의 user 스코프 위치(projects 항목에 속하지 않은 mcpServers가 user 스코프에 해당)로 그대로 가지고 오면 돼.
가지고 온 후, task를 통해 디버그 모드로 서브 에이전트 구동하여 (claude --debug) 클로드 코드에 문제가 없는지 확인할 것