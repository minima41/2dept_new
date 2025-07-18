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