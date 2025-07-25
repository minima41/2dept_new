# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

V2 Investment Monitor는 투자본부를 위한 **DART 공시 및 주식 모니터링 웹 애플리케이션**입니다. 기존 Python 스크립트(`dart_monitor.py`, `simple_stock_manager_integrated.py`)의 핵심 기능을 현대적인 웹 스택으로 재구축한 프로젝트입니다.

## Architecture

### Modern Tech Stack (2025)
```
v2/
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py            # FastAPI 앱 진입점
│   │   ├── core/              # 핵심 설정
│   │   │   ├── config.py      # 통합 설정 관리
│   │   │   └── database.py    # SQLite/PostgreSQL 연결
│   │   ├── services/          # 비즈니스 로직 (기존 .py 이전)
│   │   │   ├── dart_service.py      # dart_monitor.py 로직
│   │   │   ├── stock_service.py     # stock_manager 로직
│   │   │   ├── notification_service.py # 통합 알림
│   │   │   └── websocket_service.py # 실시간 통신
│   │   ├── routers/           # API 엔드포인트
│   │   │   ├── dart_router.py
│   │   │   ├── stock_router.py
│   │   │   ├── notification_router.py
│   │   │   └── system_router.py
│   │   ├── models/            # Pydantic 모델
│   │   │   ├── dart_models.py
│   │   │   └── stock_models.py
│   │   └── utils/
│   │       └── logger.py      # 로깅 시스템
│   ├── data/                  # 데이터 파일
│   ├── logs/                  # 로그 파일
│   └── requirements.txt       # Python 의존성
└── frontend/                  # Next.js 프론트엔드
    ├── src/
    │   ├── app/              # Next.js 14 App Router
    │   │   ├── layout.tsx    # 루트 레이아웃
    │   │   ├── page.tsx      # 메인 대시보드
    │   │   └── globals.css   # 글로벌 스타일
    │   ├── components/       # React 컴포넌트
    │   │   ├── dashboard/    # 대시보드 컴포넌트들
    │   │   └── ui/          # 재사용 UI 컴포넌트
    │   ├── providers/       # Context Providers
    │   ├── services/        # API 클라이언트
    │   ├── hooks/           # 커스텀 훅
    │   ├── types/           # TypeScript 타입
    │   └── utils/           # 유틸리티
    └── package.json         # Node.js 의존성
```

## Technology Stack

### Backend (FastAPI)
- **Framework**: FastAPI 0.109.0 + Python 3.9+
- **Database**: SQLite (개발) → PostgreSQL (프로덕션)
- **Real-time**: WebSocket + Redis PubSub (선택적)
- **Scheduling**: APScheduler 3.10.4
- **External APIs**: DART OpenAPI, PyKrx, 웹 스크래핑
- **Authentication**: JWT tokens

### Frontend (Next.js)
- **Framework**: Next.js 14.1.0 + TypeScript 5.8.3
- **State Management**: Zustand 4.5.0 + TanStack Query 5.20.1
- **UI Framework**: Tailwind CSS 3.4.1 + Headless UI
- **Charts**: Tremor 3.15.0 + Recharts 2.11.0
- **Real-time**: WebSocket client + React Context

## Common Development Tasks

### Running the Application

```bash
# Backend (FastAPI)
cd v2/backend
pip install -r requirements.txt
python run_server.py
# 또는
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Next.js)
cd v2/frontend
npm install
npm run dev

# Full stack with Docker
cd v2
docker-compose up -d
```

### Development Commands

```bash
# Backend
python run_server.py        # 개발 서버 시작
pytest tests/              # 테스트 실행
black . && ruff .          # 코드 포맷팅 + 린팅

# Frontend  
npm run dev                # 개발 서버 시작
npm run build              # 프로덕션 빌드
npm run lint               # ESLint 실행
npm run type-check         # TypeScript 검사
npm run format             # Prettier 포맷팅
```

### Development Servers
- **Backend**: http://localhost:8000 (API 문서: /docs)
- **Frontend**: http://localhost:3000
- **WebSocket**: ws://localhost:8000/ws

### Key API Endpoints
```
GET  /api/dart/disclosures        # DART 공시 목록
POST /api/dart/check-now          # 수동 공시 확인
GET  /api/stocks/monitoring       # 모니터링 주식 목록
POST /api/stocks/update-prices    # 수동 주가 업데이트
GET  /api/notifications/          # 알림 목록
GET  /api/system/health           # 헬스체크
```

## Environment Configuration

### Backend (.env)
```env
# 기본 설정
DEBUG=true
APP_NAME="Investment Monitor V2"

# 데이터베이스  
DATABASE_URL="sqlite:///./investment_monitor.db"

# DART API (실제 키로 교체 필요)
DART_API_KEY="your-dart-api-key-here"
DART_CHECK_INTERVAL=1800

# 이메일 (실제 정보로 교체 필요)
EMAIL_SENDER="your-email@gmail.com"
EMAIL_PASSWORD="your-app-password"
EMAIL_RECEIVER="recipient@company.com"

# 보안
SECRET_KEY="your-super-secret-key-change-in-production"
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
NEXT_PUBLIC_WS_URL="ws://localhost:8000/ws"
NEXT_PUBLIC_DEBUG=true
```

## Core Business Logic

### DART Monitoring (기존 dart_monitor.py 로직)
- **30분 간격** 자동 공시 체크
- **키워드 매칭** 및 중요도 점수 계산
- **관심 기업** 별도 모니터링
- **이메일 알림** 자동 발송
- **WebSocket** 실시간 브로드캐스트

### Stock Monitoring (기존 stock_manager 로직)
- **10초 간격** 실시간 주가 업데이트
- **PyKrx API** (1차) + 웹 스크래핑 (fallback)
- **목표가/손절가** 알림 시스템
- **시장 시간** 자동 감지 (09:00-15:35)
- **포트폴리오** 손익 계산

### Real-time Communication
- **WebSocket** 연결 관리 및 하트비트
- **이벤트 기반** 업데이트 시스템
- **자동 재연결** 처리
- **연결 상태** 실시간 표시

## Coding Standards

### Backend (FastAPI)
- **비즈니스 로직**: `services/` 계층에 분리
- **API 엔드포인트**: `routers/` 계층에 정의
- **데이터 모델**: Pydantic v2 모델 사용
- **에러 처리**: HTTP 상태 코드 준수
- **로깅**: 구조화된 로깅 (`loguru` 사용)

### Frontend (Next.js)
- **App Router**: Next.js 14 App Router 사용
- **컴포넌트**: 기능별 디렉터리 구조
- **상태 관리**: TanStack Query (서버) + Zustand (클라이언트)
- **스타일링**: Tailwind CSS utility-first
- **타입 안전성**: TypeScript strict 모드

### File Operations
- **동시 접근 제어**: FileLock 사용
- **로그 로테이션**: 5MB 제한, 3개 백업 유지
- **데이터 백업**: 자동 일일 백업

## Logging System

### Log Files (logs/)
- `app.log` - 일반 애플리케이션 로그
- `dart_monitor.log` - DART 모니터링 전용
- `stock_monitor.log` - 주식 모니터링 전용
- `notifications.log` - 알림 발송 기록
- `websocket.log` - WebSocket 연결 로그
- `error.log` - 에러 전용 로그

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
pytest tests/services/ -k dart_service
```

### Frontend Tests  
```bash
cd frontend
npm test
npm run test:watch
```

## Performance & Scalability

### System Requirements
- **동시 사용자**: 최대 50명 (WebSocket 연결)
- **메모리 사용**: 모니터링 및 최적화 필요
- **응답 시간**: API < 100ms, WebSocket < 50ms

### Background Tasks
- **DART 모니터링**: 30분 간격 (사용자 설정 가능)
- **주식 업데이트**: 시장 시간 내 10초 간격
- **로그 정리**: 일일 자동 실행

## Security Best Practices

### API Keys & Secrets
- 환경 변수로만 관리 (`.env` 파일)
- 프로덕션에서는 시크릿 관리 서비스 사용
- `.env.example` 파일로 템플릿 제공

### Data Protection
- JWT 토큰 기반 인증 (선택적)
- CORS 설정으로 도메인 제한
- 입력 데이터 검증 (Pydantic 모델)

## Docker Deployment

### Development
```bash
cd v2
docker-compose up -d
```

### Production
```bash
# 개별 컨테이너 빌드
docker build -t investment-monitor-backend ./backend
docker build -t investment-monitor-frontend ./frontend

# 프로덕션 실행
docker-compose -f docker-compose.prod.yml up -d
```

## Migration from Legacy Code

### 기존 코드 이전 현황
- ✅ **DART 모니터링**: `dart_monitor.py` → `services/dart_service.py`
- ✅ **주식 관리**: `stock_manager.py` → `services/stock_service.py`  
- ✅ **웹 인터페이스**: Tkinter GUI → Next.js 웹 대시보드
- ✅ **실시간 통신**: 개별 알림 → WebSocket 통합

### 유지된 핵심 기능
1. **DART API 키**: `d63d0566355b527123f1d14cf438c84041534b2b`
2. **모니터링 로직**: 기존 키워드 매칭 및 점수 계산
3. **이메일 설정**: 기존 SMTP 설정 유지
4. **데이터 형식**: JSON 파일 호환성 유지

## Development Priorities

### Current Status (Phase 1 완료)
1. ✅ **Backend**: FastAPI + SQLite + 서비스 계층
2. ✅ **Frontend**: Next.js + 대시보드 UI
3. ✅ **WebSocket**: 실시간 통신 구현
4. ✅ **Integration**: 기존 로직 이전 완료

### Next Steps (Phase 2)
1. 🔄 **DART 상세 페이지**: 공시 내용 및 관리 기능
2. 🔄 **주식 관리 UI**: 종목 추가/수정/삭제 인터페이스  
3. 🔄 **알림 센터**: 히스토리 및 설정 관리
4. 🔄 **시스템 설정**: 키워드, 간격 등 동적 설정

## Important Notes

### Prohibited Practices
- 하드코딩된 API 키나 비밀번호 금지
- 동기식 파일 I/O 사용 금지 (async/await 사용)
- 프론트엔드에서 민감 정보 저장 금지
- 무제한 WebSocket 연결 허용 금지

### Development Environment
- **주 개발 환경**: Windows + WSL2 또는 네이티브
- **Python 버전**: 3.9+ (FastAPI 호환성)
- **Node.js 버전**: 18.0+ (Next.js 14 요구사항)
- **패키지 관리**: pip (Python) + npm (Node.js)

### External Dependencies
- **DART OpenAPI**: 한국 금융감독원 공시 API
- **PyKrx**: 한국거래소 주가 데이터
- **웹 스크래핑**: Naver Finance (PyKrx 실패 시 fallback)
- **이메일**: Gmail SMTP (앱 비밀번호 사용)

이 프로젝트는 기존 2000줄 규모의 복잡한 Python 스크립트를 500줄 내외의 깔끔한 웹 애플리케이션으로 재탄생시키는 것을 목표로 합니다.