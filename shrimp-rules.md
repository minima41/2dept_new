# Development Guidelines for 2dept Investment Platform

## Project Overview

### Mission
- **Primary Goal**: 100% restore all features from `simple_stock_manager_integrated.py` and `dart_monitor.py` to React + FastAPI web application
- **Technology Stack**: React + TypeScript + FastAPI + WebSocket + TailwindCSS
- **Architecture**: Modular Monolith with real-time monitoring capabilities
- **Target Users**: Investment team (10 members max) for local network usage

### Current Status
- **Backend**: Fully implemented with complete monitoring, service, and router layers
- **Frontend**: Basic implementation exists but missing critical features from original tkinter GUI
- **Priority**: Frontend feature completion to match original functionality
- **Critical Gap**: Mezzanine investment features (conversion price, parity calculation) and complex alert system missing

## Project Architecture
### Directory Structure Rules
- **Backend Modules**: `backend/app/modules/{dart,stocks,funds,keywords,portfolio}/`
- **Each Module Contains**: `router.py`, `service.py`, `models.py`, `monitor.py`
- **Frontend Pages**: `frontend/src/pages/` with PascalCase naming (e.g., `StocksPage.tsx`)
- **Frontend Components**: `frontend/src/components/` organized by feature
- **Shared Utilities**: `frontend/src/services/apiClient.ts` for centralized API calls

### Module Interaction Rules
- **Backend services** already implemented - DO NOT modify core logic
- **WebSocket events** managed through `shared/websocket.py`
- **Real-time updates** must use WebSocket subscription pattern
- **API calls** must go through service layer, never direct database access

## Code Standards

### Naming Conventions
- **React Components**: PascalCase with `.tsx` extension
- **API Methods**: camelCase in `apiClient.ts`
- **Backend Files**: snake_case for Python modules
- **WebSocket Events**: snake_case for event names
- **CSS Classes**: TailwindCSS utility classes only

### TypeScript Requirements
- **All components** must be TypeScript with proper interface definitions
- **Props interfaces** must be defined for reusable components
- **API response types** must be defined in `src/types/`
- **No `any` types** - use proper type definitions

### Styling Standards
- **Primary Framework**: TailwindCSS utility classes
- **Theme Support**: Must support light/dark/prompt themes
- **Responsive Design**: Mobile-first approach with responsive utilities
- **NO external UI libraries** - use existing `src/components/ui/` components

## Functionality Implementation Standards

### Critical Missing Features (Priority Order)

#### Phase 1: Data Model & Mezzanine Features (HIGH PRIORITY)
1. **Database Schema Extension** 
   - Add `conversion_price`, `conversion_price_floor`, `category`, `acquisition_price` fields
   - Migrate existing data without loss
2. **Parity Calculation Engine**
   - Formula: `(current_price / conversion_price) * 100`
   - Floor parity: `(current_price / conversion_price_floor) * 100`
   - Color coding: Green if >= 100%, Red if < 100%
3. **Stock Category System**
   - Categories: "메자닌" (mezzanine) / "기타" (other)
   - UI filtering by category
   - Different alert rules per category

#### Phase 2: Complex Alert System (HIGH PRIORITY)
1. **Multi-condition Alert Engine**
   - TP/SL price alerts
   - Parity percentage alerts (80%, 100%, 120%)
   - Daily fluctuation alerts (configurable thresholds)
   - Duplicate prevention using `triggered_alerts` set
2. **Alert Tracking System**
   - Track triggered alerts by ID
   - Daily reset logic for fluctuation alerts
   - Alert history persistence

#### Phase 3: UI Enhancement (MEDIUM PRIORITY)
1. **Real-time Log Display Component** (LogTextHandler web equivalent)
2. **Theme Toggle System** (light/dark/prompt themes)
3. **Advanced Stock Settings Modal** 
   - All fields from original: conversion prices, acquisition price
   - Auto-calculation for TP/SL based on acquisition price
4. **Mezzanine-specific UI Components**
   - Parity percentage display with color coding
   - Conversion price input with floor option
   - Separate email templates for mezzanine/other

#### Phase 4: Automation (MEDIUM PRIORITY)
1. **End-of-day Summary Email** (15:35-15:40 auto-send)
   - Separate emails for mezzanine/other stocks
   - HTML tables with proper formatting
   - Profit/loss calculations
2. **Refresh Interval Controls** (30s/60s/300s options)
3. **Alert History Page** (notifications.json display)
### Feature Implementation Rules
- **Preserve Original Logic**: Copy exact calculations from `simple_stock_manager_integrated.py`
- **Web Adaptation**: Adapt tkinter UI patterns to React components
- **Real-time Updates**: Every feature must support WebSocket real-time updates
- **Error Handling**: Include loading states, error states, and retry mechanisms

### Parity Calculation Requirements
- **Formula**: `(current_price / conversion_price) * 100`
- **Display**: Show percentage with 2 decimal places
- **Color Coding**: Green if >= 100%, Red if < 100%
- **Floor Calculation**: Support conversion_price_floor for alternative calculation

## Framework Usage Standards

### React Query Implementation
- **Data Fetching**: Use `useQuery` for GET operations
- **Mutations**: Use `useMutation` for POST/PUT/DELETE operations
- **Refetch Intervals**: Configure based on data type (10s for stocks, 30s for other)
- **Cache Management**: Implement proper cache invalidation on mutations

### WebSocket Integration
- **Connection Management**: Single WebSocket connection per client
- **Event Subscription**: Component-level subscription to relevant events
- **Reconnection Logic**: Automatic reconnection with exponential backoff
- **Event Types**: `stock_price_update`, `dart_alert`, `system_status`, `log_message`

### State Management Rules
- **Server State**: React Query for API data
- **WebSocket State**: Context API for real-time data
- **UI State**: Local component state with useState
- **Global Settings**: Context API for theme, user preferences

## Workflow Standards

### Development Process
1. **Analyze Original Feature**: Study `simple_stock_manager_integrated.py` implementation
2. **Check Backend API**: Verify required endpoints exist in backend services
3. **Create Component**: Build React component with TypeScript
4. **Add API Integration**: Connect to backend through `apiClient.ts`
5. **Implement WebSocket**: Add real-time updates if needed
6. **Test Functionality**: Verify feature works identically to original
7. **Update Routes**: Add to `App.tsx` routing if new page

### Testing Requirements
- **TypeScript Compilation**: Must pass without errors
- **Browser Testing**: Test in Chrome/Firefox development mode
- **WebSocket Verification**: Check connection in browser dev tools
- **API Testing**: Verify endpoints respond correctly
- **Cross-component Testing**: Ensure features work together

## File Interaction Standards

### Multi-file Coordination Requirements
- **New Component** → Update `src/components/index.ts` with export
- **New Page** → Update `App.tsx` routing configuration
- **API Changes** → Synchronize `apiClient.ts` with backend router changes
- **Theme Changes** → Update `tailwind.config.js` + `index.css` + theme context
- **Type Definitions** → Update all related files in `src/types/`

### Dependency Chain Management
- **Real-time Logs**: WebSocket → Log Context → Log Component → All Pages
- **Stock Data**: Backend Service → API Client → React Query → Components
- **Theme System**: Context Provider → All Pages/Components → CSS Variables
- **Alert System**: Backend Monitor → WebSocket → Alert Context → UI Notifications

### Critical File Relationships
- **StocksPage.tsx** ↔ **apiClient.ts** (stocks methods)
- **Theme Provider** ↔ **All Page Components** (theme consumption)
- **WebSocket Hook** ↔ **Backend websocket.py** (event synchronization)
- **Log Component** ↔ **Backend logging system** (real-time log streaming)

## Database Migration Standards

### Schema Extension for Mezzanine Features
```sql
-- Required fields for mezzanine investment tracking
ALTER TABLE monitoring_stocks ADD COLUMN conversion_price REAL DEFAULT NULL;
ALTER TABLE monitoring_stocks ADD COLUMN conversion_price_floor REAL DEFAULT NULL;
ALTER TABLE monitoring_stocks ADD COLUMN category TEXT DEFAULT 'basic';
ALTER TABLE monitoring_stocks ADD COLUMN acquisition_price REAL DEFAULT NULL;

-- Index for performance
CREATE INDEX idx_stock_category ON monitoring_stocks(category);
```

### Data Migration Rules
- **Backward Compatibility**: Existing stocks default to category 'basic' (기타)
- **Null Handling**: conversion_price NULL means non-mezzanine stock
- **Alert Migration**: Existing alerts preserved, new parity alerts added only for mezzanine
- **Triggered Alerts**: Convert from list to set structure in migration script

### Migration Script Location
- **Path**: `backend/migrations/001_add_mezzanine_fields.py`
- **Execution**: Run before server start if schema version mismatch
- **Rollback**: Include rollback function for safety
## AI Decision-making Standards

### Priority Matrix
1. **Highest**: Restore original `simple_stock_manager_integrated.py` features
2. **High**: Fix critical bugs preventing basic functionality
3. **Medium**: Improve user experience and web-specific enhancements
4. **Low**: Add new features not in original application

### Conflict Resolution Rules
- **Original vs Web-friendly**: Adapt to web but preserve functionality
- **Performance vs Completeness**: Prioritize feature completeness first
- **Backend vs Frontend**: Make frontend changes, avoid backend modifications
- **Simple vs Complex**: Choose simpler implementation if functionality identical

### Decision Trees
- **Missing Feature**: Check backend API → Create frontend component → Add WebSocket if needed
- **Bug Found**: Check if backend issue → Fix in frontend if possible → Report if backend fix needed
- **Performance Issue**: Profile first → Optimize frontend → Consider backend only if critical

## Prohibited Actions

### Backend Restrictions
- **NEVER modify** existing `service.py`, `monitor.py`, `models.py` core logic
- **NEVER add** direct database queries in frontend
- **NEVER bypass** service layer for data access
- **NEVER change** existing API endpoint behavior

### Frontend Restrictions
- **NEVER add** new UI component libraries
- **NEVER use** inline styles - only TailwindCSS classes
- **NEVER ignore** TypeScript errors
- **NEVER create** components without proper interfaces

### Dependency Restrictions
- **NEVER add** new npm packages without checking existing alternatives
- **NEVER modify** existing package.json dependencies
- **NEVER use** browser-specific APIs without polyfills
- **NEVER implement** features that require server-side changes

### Code Quality Restrictions
- **NEVER commit** code with TypeScript compilation errors
- **NEVER push** untested features
- **NEVER create** components without loading/error states
- **NEVER hardcode** values that should be configurable

## Feature Completion Checklist

### 100% Restoration Goal
- [ ] Real-time log display with auto-scroll and level filtering
- [ ] Theme toggle: light/dark/prompt with persistence
- [ ] Stock category system: mezzanine/other with filtering
- [ ] Parity calculation: conversion_price vs current_price with color coding
- [ ] Daily alert settings: enable/disable, up/down thresholds
- [ ] Complete stock modal: all fields from original GUI
- [ ] Alert history: chronological list with filtering
- [ ] Refresh intervals: user-configurable update rates
- [ ] End-of-day email: automated summary at market close
- [ ] Profit/loss tracking: acquisition_price based calculations

### Verification Standards
- **Visual Comparison**: Web UI matches original tkinter functionality
- **Feature Parity**: Every setting/option available in web version
- **Real-time Performance**: Updates at same frequency as original
- **Email Integration**: Alerts sent with identical triggers and content
- **Data Accuracy**: Calculations match original implementation exactly

## Implementation Checklist by Phase

### Phase 1: Data Model Extension (Days 1-2)
- [ ] Create database migration script for new fields
- [ ] Update SQLite schema with mezzanine fields
- [ ] Modify stocks models.py to include new fields
- [ ] Update stocks service.py with parity calculation logic
- [ ] Test data migration with existing stocks data
- [ ] Implement category filtering in backend API

### Phase 2: Alert System Enhancement (Days 3-5)
- [ ] Implement triggered_alerts tracking system
- [ ] Add multi-condition alert evaluation logic
- [ ] Create daily reset scheduler for fluctuation alerts
- [ ] Update notification service with deduplication
- [ ] Test complex alert scenarios
- [ ] Ensure email alerts work for all conditions

### Phase 3: Frontend UI Updates (Days 6-8)
- [ ] Create MezzanineStockCard component with parity display
- [ ] Update StocksPage with category filter tabs
- [ ] Implement advanced stock settings modal
- [ ] Add real-time log viewer component
- [ ] Create theme toggle system
- [ ] Update stock table to show all new fields

### Phase 4: Automation Features (Days 9-10)
- [ ] Implement end-of-day email scheduler
- [ ] Create HTML email templates for mezzanine/other
- [ ] Add refresh interval selector component
- [ ] Build alert history page
- [ ] Test automated workflows
- [ ] Performance optimization and final testing

---

**THIS DOCUMENT IS FOR AI AGENT USE ONLY**
**Follow these rules strictly to ensure consistent, complete feature restoration**

## 프로젝트 개요

### 핵심 정보
- **프로젝트 루트**: C:\2dept (절대 변경 금지)
- **접속 URL**: http://localhost (WSL2 환경)
- **아키텍처**: 모듈러 모놀리스 (FastAPI + React)
- **대상 사용자**: 10명 내외 팀
- **배포 환경**: 로컬 네트워크
- **GitHub 저장소**: https://github.com/minima41/dash

### 기술 스택
- **백엔드**: Python 3.9+, FastAPI, SQLite, Redis
- **프론트엔드**: React 18+, TypeScript, Tailwind CSS
- **실시간 통신**: Server-Sent Events (SSE) 우선, WebSocket 보조
- **데이터베이스**: SQLite + JSON 파일 조합
- **환경**: WSL2, Windows 11

## 디렉터리 구조 규칙

### 필수 디렉터리 구조
```
C:\2dept/
├── backend/
│   ├── routes/          # API 엔드포인트 모듈
│   ├── services/        # 비즈니스 로직 (dart_monitor, stock_monitor)
│   ├── models/          # 데이터 모델
│   ├── utils/           # 공통 유틸리티
│   ├── main.py          # FastAPI 앱 진입점
│   └── config.py        # 설정 파일
├── frontend/
│   ├── src/
│   │   ├── pages/       # 페이지 컴포넌트
│   │   ├── components/  # 재사용 컴포넌트
│   │   ├── hooks/       # 커스텀 훅
│   │   └── utils/       # 프론트엔드 유틸리티
│   ├── public/
│   └── package.json
├── data/                # 데이터 파일 (JSON, SQLite)
├── logs/                # 로그 파일 (필수 위치)
├── .env                 # 환경변수 (Git 제외)
├── .gitignore
└── README.md
```

### 디렉터리 생성 규칙
- **새 디렉터리 생성 시**: filesystem:create_directory 도구 사용
- **로그 디렉터리**: C:\2dept\logs 반드시 생성
- **데이터 디렉터리**: C:\2dept\data 반드시 생성
- **백엔드/프론트엔드**: 각각 독립적인 패키지 관리

## 기존 코드 통합 규칙

### 파일 마이그레이션 규칙
- **simple_stock_manager_integrated.py** → **backend/services/stock_monitor.py**
  - 클래스 기반으로 리팩터링
  - FastAPI 의존성 주입 패턴 적용
  - 기존 JSON 데이터 파일 형식 유지
- **dart_monitor.py** → **backend/services/dart_monitor.py**
  - 백그라운드 태스크로 변환
  - DART API 키 환경변수로 분리
  - 이메일 설정 통합 모듈 활용
- **config.py** → **.env + backend/config.py**
  - 민감 정보 .env로 분리
  - 공개 설정 config.py에 유지

### 데이터 파일 처리 규칙
- **기존 파일 형식 유지**: monitoring_stocks.json, notifications.json, processed_ids.txt
- **위치 변경**: C:\2dept\data\ 하위로 이동
- **백업 전략**: 변경 전 반드시 백업 생성

## 파일 수정 규칙

### edit-file-lines 사용 규칙
- **모든 파일 수정 시 필수**: edit-file-lines 도구만 사용
- **dryRun 필수**: 항상 "dryRun": true로 먼저 실행
- **라인 번호 재확인**: 파일 수정 전 get_file_lines로 현재 상태 확인
- **섹션별 분할**: 3-5개 섹션으로 나누어 순차적 수정

### 파일 생성 규칙
- **대용량 파일**: 3-5개 섹션으로 분할하여 write → edit 순서
- **소용량 파일**: filesystem:write_file 일괄 생성
- **템플릿 활용**: 기존 유사 파일 구조 참조

## Git 워크플로우 규칙

### 필수 Git 규칙
- **.git 없는 경우**: 즉시 git init 실행
- **파일 변경 후**: 반드시 git add && git commit
- **파일 삭제 시**: git rm 사용
- **브랜치 전략**: test 브랜치 → PR → master 병합

### 커밋 메시지 규칙
- **feat**: 새로운 기능 추가
- **fix**: 버그 수정
- **refactor**: 코드 리팩터링
- **chore**: 설정, 빌드 관련
- **docs**: 문서 수정

### GitHub 연동 규칙
- **저장소**: https://github.com/minima41/dash
- **인증**: Personal Access Token 사용
- **푸시 전략**: HTTP 버퍼 크기 증가, 분할 푸시
- **충돌 처리**: 작은 변경사항 단위로 새 커밋 생성

## 데이터베이스 연결 규칙

### MySQL 연결 설정
- **HOST**: localhost
- **사용자**: root
- **패스워드**: 공백 (XAMPP 기본 설정)
- **명령어 형식**: mysql -u root -e "QUERY;" [database]
- **쿼리 인용부호**: 반드시 양쪽 따옴표로 감싸기

### SQLite 규칙
- **위치**: C:\2dept\data\*.sqlite3
- **백업**: 스키마 변경 전 백업 생성
- **마이그레이션**: 스키마 변경 시 마이그레이션 스크립트 작성

## 실시간 데이터 처리 규칙

### 통신 방식 우선순위
1. **Server-Sent Events (SSE)**: 주가, 공시 데이터
2. **WebSocket**: 복잡한 양방향 통신 필요 시만
3. **Polling**: 마지막 수단

### 업데이트 주기 규칙
- **주가 데이터**: 5-10초 간격
- **공시 데이터**: 30분 간격
- **뉴스 데이터**: 10분 간격
- **펀드 데이터**: 수동 업데이트

### 캐싱 전략
- **메모리 캐시**: Redis (실시간 데이터)
- **파일 캐시**: JSON (백업 및 영속성)
- **브라우저 캐시**: 정적 리소스 24시간

## 성능 및 확장성 규칙

### 성능 기준
- **동시 사용자**: 10명 기준 최적화
- **API 응답시간**: 200ms 이내
- **메모리 사용량**: 2GB 이하
- **CPU 사용률**: 50% 이하

### 로깅 규칙
- **위치**: C:\2dept\logs
- **파일 크기**: 최대 5MB
- **백업 개수**: 3개
- **로테이션**: 자동 (RotatingFileHandler)
- **레벨**: INFO 이상 파일 저장, DEBUG 콘솔만

## 보안 및 환경변수 규칙

### .env 파일 규칙
- **위치**: C:\2dept\.env
- **Git 제외**: .gitignore에 반드시 추가
- **필수 변수**:
  ```
  DART_API_KEY=
  EMAIL_SENDER=
  EMAIL_PASSWORD=
  EMAIL_RECEIVER=
  OPENAI_API_KEY=
  ```

### API 키 관리
- **절대 금지**: API 키를 소스코드에 하드코딩
- **환경변수 사용**: os.getenv() 또는 python-dotenv
- **예외 처리**: API 키 없을 시 적절한 에러 메시지

## 테스팅 규칙

### 필수 테스트
- **API 엔드포인트**: 모든 routes에 대한 단위 테스트
- **실시간 기능**: SSE/WebSocket 통합 테스트
- **데이터 처리**: 주가/공시 데이터 파싱 테스트
- **에러 처리**: 예외 상황 처리 테스트

### 테스트 실행 규칙
- **새 기능 추가 시**: 기존 테스트 전체 실행
- **테스트 실패 시**: 수정 후 재실행 확인
- **테스트 위치**: backend/tests/, frontend/src/__tests__/

## AI Agent 작업 규칙

### 파일 수정 전 필수 확인사항
1. **라인 번호 재확인**: get_file_lines로 현재 상태 확인
2. **영향 범위 분석**: 수정이 다른 파일에 미치는 영향 확인
3. **백업 확인**: 중요 파일은 Git 커밋 상태 확인
4. **권한 확인**: 사용자 동의 없이 임의 작업 금지

### 작업 진행 규칙
- **한 번에 하나씩**: 여러 작업 동시 진행 금지
- **사용자 동의**: 작업 전 반드시 사용자 승인
- **상태 보고**: 작업 진행 상황 실시간 보고
- **에러 처리**: 오류 발생 시 즉시 중단 및 보고

### 금지 사항
- **.env 파일 Git 커밋**: 절대 금지
- **임의 디렉터리 변경**: 프로젝트 구조 임의 변경 금지
- **대용량 파일 일괄 수정**: 섹션별 분할 수정 필수
- **테스트 생략**: 기능 변경 시 테스트 실행 생략 금지

## WSL2 환경 특별 규칙

### 네트워크 설정
- **Mirrored Mode 필수**: Windows 11 22H2+ 환경
- **포트 포워딩**: 이전 버전에서 자동 스크립트 사용
- **방화벽 설정**: localhost 접근 허용 확인

### 파일 시스템
- **경로 구분자**: Windows 스타일 역슬래시 사용
- **권한 설정**: WSL2 내 파일 권한 확인
- **동기화**: Windows-WSL2 간 파일 동기화 주의

## 통합 및 배포 규칙

### 기존 시스템 통합
- **점진적 마이그레이션**: 기능별로 단계적 통합
- **데이터 무결성**: 기존 데이터 형식 유지
- **백워드 호환성**: 기존 기능 동작 보장

### 배포 전 체크리스트
- [ ] 모든 테스트 통과
- [ ] 로그 파일 정상 생성
- [ ] 환경변수 설정 완료
- [ ] Git 커밋 및 푸시 완료
- [ ] 성능 기준 충족 확인

---

**경고**: 이 문서는 AI Agent 전용입니다. 모든 규칙을 엄격히 준수하며, 불확실한 경우 반드시 사용자에게 확인 요청하세요.

## 프로젝트 개요

- **프로젝트명**: 투자본부 React 기반 로컬 웹 애플리케이션
- **기술 스택**: FastAPI (백엔드) + React (프론트엔드)
- **아키텍처**: 모듈러 모놀리스 패턴
- **주요 기능**: 주식/공시/뉴스 모니터링, 펀드 관리, 실시간 알림
- **프로젝트 루트**: C:\2dept

## 프로젝트 아키텍처

### 디렉토리 구조

```
C:\2dept
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI 애플리케이션 진입점)
│   │   ├── config.py (환경 설정)
│   │   ├── modules/
│   │   │   ├── dart/ (공시 모니터링)
│   │   │   ├── stocks/ (주가 모니터링)
│   │   │   └── shared/ (공통 모듈)
│   │   └── data/ (데이터 파일)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
│   └── package.json
├── logs/ (로그 파일 저장)
└── .git/
```

### 모듈 구조 규칙

- **절대 경로 import 사용**: `from app.modules.dart import monitor`
- **모듈러 모놀리스 패턴**: 기능별 모듈로 분리하되 단일 애플리케이션으로 배포
- **공통 모듈**: `app/modules/shared/`에 데이터베이스, WebSocket 등 공통 기능 배치

## 실행 및 환경 설정 규칙

### **⚠️ 중요: 올바른 실행 방법**

- **금지**: `python app/main.py` 직접 실행 (ModuleNotFoundError 발생)
- **필수**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` 사용
- **실행 디렉토리**: 반드시 `C:\2dept\backend` 에서 실행

### 패키지 관리

- **의존성 설치**: `pip install -r requirements.txt`
- **가상환경 권장**: `python -m venv venv` 후 활성화
- **버전 호환성**: FastAPI 0.104.1, Starlette 0.27.0, AnyIO 3.7+ 조합 유지

### 환경 설정 개선 규칙

- **경로 설정 유연화**: config.py의 DATA_DIR, LOGS_DIR을 환경변수 기반으로 변경
  ```python
  DATA_DIR: str = os.getenv("DATA_DIR", "C:\\2dept\\data")
  LOGS_DIR: str = os.getenv("LOGS_DIR", "C:\\2dept\\logs")
  ```
- **WSL2와 Windows 호환**: /mnt/c/ 경로 사용 금지, Windows 경로 사용
- **네트워크 바인딩**: WSL2 환경에서는 반드시 --host 0.0.0.0 설정

## 코드 수정 규칙

### **⚠️ 필수: edit-file-lines 사용법**

- **반드시 dryRun: true로 먼저 검증**
- **파일 수정 전 해당 부분 확인**: `get_file_lines` 또는 `search_file` 사용
- **3-5개 섹션으로 나누어 수정**: 한 번에 큰 파일 전체 수정 금지

### 파일 수정 워크플로우

1. **파일 내용 확인**: 수정할 부분 주변 라인 확인
2. **dryRun 검증**: `"dryRun": true`로 변경사항 미리보기
3. **승인 후 적용**: `approve_edit` 도구로 실제 적용
4. **결과 검증**: 수정 후 해당 라인 재확인

## 기존 코드 통합 규칙

### dart_monitor.py 통합

- **위치**: `backend/app/modules/dart/monitor.py`로 이동
- **구조 변경**: 함수 기반으로 리팩토링 (클래스 생성 권장)
- **설정 분리**: `config.py`에서 DART_API_KEY, COMPANIES 등 관리
- **WebSocket 통합**: 새로운 공시 발견 시 실시간 알림

### simple_stock_manager_integrated.py 통합

- **위치**: `backend/app/modules/stocks/manager.py`로 이동
- **GUI 제거**: tkinter 관련 코드 제거, API 엔드포인트로 대체
- **상태 관리**: 웹 애플리케이션 상태 관리로 변경
- **실시간 업데이트**: WebSocket으로 주가 변동 실시간 전송

### 통합 시 주의사항

- **로그 경로**: `C:\2dept\logs`에 저장
- **데이터 파일**: `backend/app/data/`에 JSON 파일 저장
- **이메일 설정**: 통합 알림 모듈로 관리
- **스케줄러**: APScheduler 사용하여 백그라운드 작업 관리

## Git 워크플로우 규칙

### **⚠️ 필수: Git 작업 절차**

1. **Git 저장소 확인**: `.git` 폴더 없으면 `git init` 실행
2. **브랜치 생성**: `git checkout -b test` (테스트 브랜치)
3. **파일 수정 후**: `git add .` 및 `git commit -m "설명"`
4. **테스트 검증**: test 브랜치에서 충분한 테스트
5. **master 병합**: `git checkout master` → `git merge test`

### 커밋 메시지 규칙

- **feat**: 새로운 기능 추가
- **fix**: 버그 수정
- **refactor**: 코드 리팩토링
- **test**: 테스트 추가/수정
- **docs**: 문서 수정

## 테스트 및 검증 규칙

### 백엔드 테스트

- **서버 실행**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **API 테스트**: `curl http://localhost:8000/health`
- **로그 확인**: `C:\2dept\logs\app.log` 에러 확인

### 프론트엔드 테스트

- **개발 서버**: `npm start` (포트 3000)
- **빌드 테스트**: `npm run build`
- **CORS 확인**: 백엔드 API 호출 정상 여부 확인

## 금지사항 및 제한사항

### **⚠️ 절대 금지**

- **직접 실행 금지**: `python app/main.py` 사용 금지
- **dryRun 없이 수정 금지**: `edit-file-lines` 사용 시 반드시 dryRun 먼저
- **Git 작업 생략 금지**: 모든 파일 수정 후 반드시 commit
- **테스트 생략 금지**: 코드 수정 후 반드시 실행 테스트
- **임의 삭제 금지**: shrimp 작업 삭제 시 반드시 사용자 동의

### **⚠️ 주의사항**

- **경로 문제**: WSL 경로(`/mnt/c/`) 사용 금지, Windows 경로(`C:\`) 사용
- **의존성 충돌**: requirements.txt 버전 임의 변경 금지
- **포트 충돌**: 백엔드 8000, 프론트엔드 3000 포트 사용
- **로그 용량**: 로그 파일 크기 5MB 초과 시 로테이션 적용

## AI 결정 기준

### 우선순위

1. **안정성**: 기존 동작 중인 코드 영향 최소화
2. **호환성**: Windows 환경 호환성 우선
3. **모듈성**: 모듈러 모놀리스 구조 유지
4. **테스트 가능성**: 검증 가능한 단위로 작업 분할

### 의사결정 트리

```
문제 발생
├── 실행 오류 → uvicorn 사용법 확인
├── 모듈 오류 → import 경로 확인
├── 파일 수정 → dryRun 검증
└── 기능 추가 → 모듈러 구조 적용
```

## 주요 파일 상호작용 규칙

### 동시 수정 필요 파일

- **config.py 수정 시**: `main.py`에서 import 확인
- **모듈 추가 시**: `__init__.py` 파일 생성
- **API 엔드포인트 추가 시**: `main.py`에 라우터 등록
- **데이터 모델 변경 시**: 관련 모든 모듈 확인
- **실행 방법 변경 시**: `EXECUTION_GUIDE.md` 함께 업데이트

### 파일 간 의존성

- **main.py** → 모든 라우터 및 모듈 import
- **config.py** → 환경설정 (API 키, 데이터베이스 설정)
- **modules/shared/** → 공통 기능 (데이터베이스, WebSocket)
- **modules/dart/**, **modules/stocks/** → 각 도메인별 기능

---

**이 규칙 문서는 AI Agent 전용으로 작성되었으며, 모든 개발 작업은 이 규칙을 준수해야 합니다.**

## 프로젝트 개요

### 목적
- 투자본부 10명 내외 팀용 로컬 웹 애플리케이션 구축
- DART 공시, 주가 모니터링, 포트폴리오 관리, 펀드/조합 관리, 키워드 관리 통합
- 기존 Python 스크립트(dart_monitor.py, simple_stock_manager.py) 웹화
- AI 코딩 도구 활용으로 개발 생산성 55% 향상 목표

### 기술 스택 (필수 준수)
- **백엔드**: FastAPI + Python 3.9+
- **프론트엔드**: React 18 + TypeScript + Vite
- **상태 관리**: Zustand + React Query
- **데이터베이스**: SQLite (개발) → PostgreSQL (운영)
- **실시간 통신**: WebSocket (FastAPI 내장)
- **UI 프레임워크**: Tailwind CSS + Recharts
- **스케줄링**: APScheduler

## 아키텍처 표준

### 모듈러 모놀리스 구조 (필수)
```
C:\2dept\
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py            # FastAPI 앱 진입점
│   │   ├── config.py          # 설정 관리
│   │   ├── modules/           # 비즈니스 모듈들
│   │   │   ├── dart/          # 공시 모니터링
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py  # FastAPI 라우터
│   │   │   │   ├── service.py # 비즈니스 로직
│   │   │   │   ├── models.py  # Pydantic 모델
│   │   │   │   └── monitor.py # 백그라운드 모니터
│   │   │   ├── stocks/        # 주가 모니터링
│   │   │   ├── portfolio/     # 포트폴리오 관리
│   │   │   ├── funds/         # 펀드 관리
│   │   │   └── keywords/      # 키워드 관리
│   │   ├── shared/            # 공통 모듈
│   │   │   ├── database.py    # DB 연결
│   │   │   ├── auth.py        # 인증
│   │   │   ├── email.py       # 이메일 발송
│   │   │   └── websocket.py   # WebSocket 관리
│   │   └── data/              # 데이터 파일
│   │       ├── monitoring_stocks.json
│   │       ├── notifications.json
│   │       └── processed_ids.txt
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── pages/             # 페이지 컴포넌트
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DartPage.tsx
│   │   │   ├── StocksPage.tsx
│   │   │   ├── PortfolioPage.tsx
│   │   │   ├── FundsPage.tsx
│   │   │   └── KeywordsPage.tsx
│   │   ├── components/        # 재사용 컴포넌트
│   │   ├── services/          # API 호출
│   │   ├── stores/            # Zustand 스토어
│   │   ├── hooks/             # 커스텀 훅
│   │   └── types/             # TypeScript 타입
│   ├── package.json
│   └── vite.config.ts
├── logs/                       # 로그 파일 (필수)
├── docker-compose.yml
└── README.md
```

## 모듈별 구현 규칙

### DART 모듈 (기존 dart_monitor.py 기반)
**필수 구현 사항:**
- DART OpenAPI 키: `d63d0566355b527123f1d14cf438c84041534b2b` 사용
- 관심 기업 목록: config.py COMPANIES 딕셔너리 활용
- 관심 키워드: KEYWORDS 리스트 기반 필터링
- 처리된 공시 ID 추적: processed_ids.txt 파일 관리
- 30분 간격 모니터링 (CHECK_INTERVAL = 1800초)

**API 엔드포인트:**
- `GET /api/dart/disclosures` - 최신 공시 목록
- `POST /api/dart/keywords` - 키워드 추가/삭제
- `WebSocket /ws/dart` - 실시간 공시 알림

**백그라운드 작업:**
- APScheduler로 30분마다 DART API 호출
- 새 공시 발견 시 WebSocket으로 브로드캐스트
- 이메일 알림 및 로그 기록

### Stocks 모듈 (기존 simple_stock_manager.py 기반)
**필수 구현 사항:**
- PyKrx API 우선, 실패 시 네이버 크롤링
- 종목 데이터: monitoring_stocks.json 파일 관리
- 알림 조건: TP/SL 가격, 일일 급등락 임계값
- 트리거된 알림 추적: triggered_alerts set 활용

**API 엔드포인트:**
- `GET /api/stocks` - 관심 종목 목록
- `POST /api/stocks` - 종목 추가
- `PUT /api/stocks/{code}/alerts` - 알림 설정
- `WebSocket /ws/stocks` - 실시간 주가 업데이트

**실시간 처리:**
- 5-10초 간격 주가 업데이트 (장중 09:00-15:35)
- 가격 변동 시 WebSocket 브로드캐스트
- 알림 조건 충족 시 이메일 발송

### Portfolio 모듈
**기능:**
- 관심 종목 통합 관리
- DART/주가 알림 ON/OFF 토글
- 실시간 시세 모니터링 대시보드

### Funds/Keywords 모듈
**구현 우선순위:** 낮음 (페이지만 준비, 추후 상세 개발)

## 코딩 표준

### FastAPI 백엔드 규칙
**파일 구조 패턴:**
```python
# router.py - FastAPI 라우터
from fastapi import APIRouter, WebSocket
from .service import DartService
from .models import DartDisclosure

router = APIRouter(prefix="/api/dart", tags=["dart"])

@router.get("/disclosures")
async def get_disclosures():
    return await DartService.get_latest_disclosures()

# service.py - 비즈니스 로직
class DartService:
    @staticmethod
    async def get_latest_disclosures():
        # 구현

# models.py - Pydantic 모델
from pydantic import BaseModel
from datetime import datetime

class DartDisclosure(BaseModel):
    corp_code: str
    corp_name: str
    report_nm: str
    rcept_dt: datetime
```

**필수 준수 사항:**
- 모든 API 응답은 Pydantic 모델 사용
- async/await 패턴 강제 적용
- 환경변수로 민감 정보 관리
- 에러 핸들링 표준화

### React 프론트엔드 규칙
**컴포넌트 패턴:**
```typescript
// 페이지 컴포넌트
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { dartApi } from '../services/dartApi';

export const DartPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['dart-disclosures'],
    queryFn: dartApi.getDisclosures,
    refetchInterval: 30000
  });

  return (
    <div className="p-6">
      {/* UI 구현 */}
    </div>
  );
};

// API 서비스
export const dartApi = {
  getDisclosures: () => 
    fetch('/api/dart/disclosures').then(res => res.json()),
};
```

**필수 준수 사항:**
- 함수형 컴포넌트 + 훅스만 사용
- TypeScript strict 모드 활성화
- Tailwind CSS 유틸리티 클래스만 사용
- React Query로 서버 상태 관리

## 데이터 관리 표준

### 파일 기반 데이터 (기존 방식 유지)
**위치:** `C:\2dept\backend\app\data\`
- `monitoring_stocks.json` - 관심 종목 데이터
- `notifications.json` - 알림 내역
- `processed_ids.txt` - 처리된 공시 ID
- `dart_monitor.log` - DART 모니터링 로그

**관리 규칙:**
- JSON 파일 변경 시 FileLock 사용
- 자동 백업 (일일 1회)
- 파일 크기 제한 (10MB)

### 데이터베이스 설계
**SQLite 테이블 (개발용):**
```sql
-- 사용자 정보
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 펀드 정보
CREATE TABLE funds (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    inception_date DATE,
    total_assets DECIMAL(15,2),
    performance DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 실시간 통신 표준

### WebSocket 구현 규칙
**백엔드 WebSocket 매니저:**
```python
# shared/websocket.py
from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()
```

**프론트엔드 WebSocket 훅:**
```typescript
// hooks/useWebSocket.ts
import { useEffect, useState } from 'react';

export const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<any>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      setLastMessage(JSON.parse(event.data));
    };
    setSocket(ws);
    return () => ws.close();
  }, [url]);

  return { socket, lastMessage };
};
```

### 실시간 이벤트 타입
**필수 정의:**
- `dart_new_disclosure` - 새 공시 발생
- `stock_price_update` - 주가 업데이트
- `alert_triggered` - 알림 발생
- `system_status` - 시스템 상태 변경

## 보안 및 설정 관리

### 환경변수 표준 (.env)
```env
# DART API
DART_API_KEY=d63d0566355b527123f1d14cf438c84041534b2b

# 이메일 설정
EMAIL_SENDER=dlwlrma401@gmail.com
EMAIL_PASSWORD=byvu_dkyn_qfyz_lwji
EMAIL_RECEIVER=ljm@inveski.com

# 데이터베이스
DATABASE_URL=sqlite:///./app.db

# JWT 토큰
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**보안 규칙:**
- .env 파일 절대 Git 커밋 금지
- API 키 하드코딩 금지
- JWT 토큰 만료 시간 설정
- CORS 설정 제한적 적용

## 로깅 및 모니터링

### 로그 디렉토리 구조
```
C:\2dept\logs\
├── app.log              # 일반 애플리케이션 로그
├── dart_monitor.log     # DART 모니터링 로그
├── stock_manager.log    # 주가 모니터링 로그
├── email.log           # 이메일 발송 로그
└── error.log           # 에러 로그
```

### 로깅 설정
```python
# 백엔드 로깅 설정
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'C:/2dept/logs/app.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
```

## Git 워크플로우 표준

### 브랜치 전략
- **main**: 운영 브랜치
- **test**: 테스트 브랜치
- **feature/***: 기능 개발 브랜치

### 커밋 규칙
**커밋 메시지 형식:**
```
<type>(<scope>): <subject>

[optional body]
```

**타입:**
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 코드 리팩토링
- `style`: 코드 포맷팅
- `docs`: 문서 수정
- `test`: 테스트 추가/수정

**예시:**
```bash
feat(dart): DART API 통합 및 실시간 알림 구현
fix(stocks): PyKrx API 호출 실패 시 네이버 크롤링 폴백 수정
refactor(websocket): WebSocket 연결 관리 로직 개선
```

## 파일 작업 규칙

### 동시 수정 필요 파일들

#### 새 모듈 추가 시
1. `backend/app/modules/{module_name}/` 폴더 생성
2. `backend/app/main.py`에 라우터 등록
3. `frontend/src/pages/{ModuleName}Page.tsx` 생성
4. `frontend/src/services/{module}Api.ts` 생성
5. `frontend/src/types/{module}.ts` 타입 정의

#### API 엔드포인트 추가 시
1. 백엔드 `router.py`에 엔드포인트 추가
2. `service.py`에 비즈니스 로직 구현
3. `models.py`에 Pydantic 모델 정의
4. 프론트엔드 API 서비스 함수 추가
5. TypeScript 타입 정의 업데이트

#### WebSocket 이벤트 추가 시
1. 백엔드 WebSocket 핸들러 구현
2. 프론트엔드 WebSocket 훅 업데이트
3. 이벤트 타입 정의 추가
4. 관련 컴포넌트에서 이벤트 구독

## 테스트 전략

### 백엔드 테스트
```python
# tests/test_dart.py
import pytest
from app.modules.dart.service import DartService

@pytest.mark.asyncio
async def test_get_latest_disclosures():
    disclosures = await DartService.get_latest_disclosures()
    assert len(disclosures) >= 0
    # 추가 검증 로직
```

### 프론트엔드 테스트
```typescript
// src/pages/__tests__/DartPage.test.tsx
import { render, screen } from '@testing-library/react';
import { DartPage } from '../DartPage';

test('renders dart disclosures page', () => {
  render(<DartPage />);
  expect(screen.getByText('DART 공시 모니터링')).toBeInTheDocument();
});
```

## 성능 최적화 규칙

### 백엔드 최적화
- **데이터베이스**: 연결 풀링 사용 (max 20 connections)
- **캐싱**: 메모리 캐시 5분 TTL
- **API 호출**: 비동기 처리 및 타임아웃 설정
- **로그**: 로테이션 및 압축

### 프론트엔드 최적화
- **코드 분할**: React.lazy로 페이지별 분할
- **메모이제이션**: React.memo, useMemo, useCallback 활용
- **가상 스크롤링**: 대용량 데이터 테이블
- **이미지**: WebP 포맷 및 지연 로딩

## AI 의사결정 표준

### 우선순위 규칙
1. **사용자 경험** 최우선
2. **시스템 안정성** 두 번째
3. **개발 생산성** 세 번째
4. **코드 품질** 네 번째

### 기술 선택 기준
**모듈러 모놀리스 vs 마이크로서비스**
→ 10명 규모이므로 모놈리스 선택

**SQLite vs PostgreSQL**
→ 개발: SQLite, 운영: PostgreSQL

**WebSocket vs 폴링**
→ 실시간성 중요한 주가/공시는 WebSocket

**상태 관리 라이브러리**
→ Zustand (단순) + React Query (서버 상태)

### 에러 처리 우선순위
1. **사용자 친화적 메시지** 표시
2. **상세 에러 로그** 기록
3. **자동 복구** 시도
4. **알림 발송** (심각한 오류 시)

## 금지 사항

### 절대 금지
- **브라우저 스토리지 사용** (localStorage, sessionStorage)
- **Django 프레임워크** 사용 (복잡도 과다)
- **마이크로서비스 아키텍처** 도입
- **실시간 데이터 폴링** (WebSocket 대신)
- **하드코딩된 API 키** 또는 민감 정보
- **동기식 파일 I/O** 작업
- **전역 상태** 남용 (prop drilling 과도한 방지만)

### 주의 사항
- **API 호출 빈도** 제한 (DART: 30분, 주가: 5-10초)
- **메모리 사용량** 모니터링 (10명 동시 접속 대응)
- **로그 파일 크기** 관리 (5MB 로테이션)
- **외부 API 의존성** 최소화

## 배포 및 운영

### Docker 설정
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
    volumes:
      - ./logs:/app/logs
      - ./backend/app/data:/app/data
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

### 로컬 서버 운영
- **백엔드**: http://localhost:8000
- **프론트엔드**: http://localhost:3000
- **네트워크 접속**: http://192.168.x.x:3000
- **모니터링**: 대시보드에서 시스템 상태 확인

### 백업 및 복구
- **데이터 파일**: 일일 자동 백업
- **데이터베이스**: SQLite 파일 복사
- **로그 파일**: 주간 아카이브
- **설정 파일**: Git 버전 관리

## 개발 체크리스트

### 새 기능 개발 시
- [ ] 모듈 구조 준수
- [ ] API 문서화
- [ ] TypeScript 타입 정의
- [ ] 에러 핸들링 구현
- [ ] 로깅 설정
- [ ] 테스트 작성
- [ ] Git 커밋 규칙 준수

### 코드 리뷰 기준
- [ ] 보안 취약점 확인
- [ ] 성능 영향 검토
- [ ] 코드 표준 준수
- [ ] 테스트 커버리지
- [ ] 문서 업데이트

이 가이드라인을 준수하여 안정적이고 확장 가능한 투자본부 웹 애플리케이션을 구축하시기 바랍니다.