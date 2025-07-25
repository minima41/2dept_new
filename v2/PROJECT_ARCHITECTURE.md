# Investment Monitoring V2 - 프로젝트 아키텍처

## 🎯 프로젝트 목표

기존 `dart_monitor.py` (414줄)와 `simple_stock_manager_integrated.py` (1676줄)의 **핵심 기능만 추출**하여 **현대적인 웹 애플리케이션**으로 재구축

## 🏗️ **2025년 최신 기술 스택**

### Backend (Python)
```
FastAPI (초고속 API, 자동 문서화)
├── Pydantic v2 (데이터 검증)  
├── SQLite → PostgreSQL (점진적 전환)
├── Redis (캐싱, 세션 관리)
├── WebSocket (실시간 통신)
└── APScheduler (백그라운드 작업)
```

### Frontend (React)
```  
Next.js 15 + TypeScript
├── TailwindCSS (스타일링)
├── Tremor/Recharts (차트)
├── Zustand (상태관리) 
├── React Query v5 (서버상태)
└── Framer Motion (애니메이션)
```

### 실시간 데이터
```
WebSocket (양방향 통신)
├── Server-Sent Events (일방향 스트림)
├── Redis PubSub (메시지 브로커)
└── Background Workers (모니터링)
```

## 📐 **단순화된 아키텍처**

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Frontend      │◄───────────────►│   Backend       │
│   (Next.js)     │                 │   (FastAPI)     │
└─────────────────┘                 └─────────────────┘
                                            │
                ┌───────────────────────────┼───────────────────────────┐
                │                           │                           │
        ┌───────▼────────┐       ┌─────────▼────────┐       ┌─────────▼────────┐
        │ DART Monitor   │       │  Stock Monitor   │       │   Notification   │
        │ (Background)   │       │  (Background)    │       │    System        │
        └────────────────┘       └──────────────────┘       └──────────────────┘
                │                           │                           │
        ┌───────▼────────┐       ┌─────────▼────────┐       ┌─────────▼────────┐
        │   DART API     │       │   PyKrx/Naver   │       │      Email       │
        │  (공시정보)      │       │   (주가정보)      │       │   (Gmail SMTP)   │
        └────────────────┘       └──────────────────┘       └──────────────────┘
```

## 🎨 **UI/UX 설계 컨셉**

### 통합 대시보드 
```
┌─────────────────────────────────────────────────────────────┐
│  Investment Monitor V2          🔔 3   👤 Admin   ⚙️        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 실시간 현황                    📈 오늘의 요약               │
│  ┌─────────────┐ ┌─────────────┐  ┌─────────────────────────┐│
│  │ DART 공시   │ │ 주가 모니터 │  │ • 새 공시: 5건           ││
│  │ ✅ 정상     │ │ ✅ 정상     │  │ • 가격 알림: 2건         ││
│  │ 마지막: 2분전│ │ 마지막: 5초전│  │ • 시스템: 정상          ││
│  └─────────────┘ └─────────────┘  └─────────────────────────┘│
│                                                             │
│  📋 최근 알림                      ⚡ 실시간 업데이트          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [DART] 삼성전자 - 정기주주총회 개최 공고     2분전     🔴 │││
│  │ [주가] 카카오 - 목표가 도달 (45,000원)      5분전     🟡 │││  
│  │ [DART] NAVER - 유상증자 결정                7분전     🔴 │││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  🎯 모니터링 설정                  📊 통계 & 차트             │
│  [+ DART 키워드]  [+ 관심 종목]    [차트 영역]              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 **핵심 기능 명세**

### 1. DART 모니터링
- **기존**: `dart_monitor.py`의 핵심 로직
- **신규**: 
  - 실시간 WebSocket 알림
  - 키워드 관리 UI  
  - 공시 상세보기 모달

### 2. 주가 모니터링  
- **기존**: `simple_stock_manager_integrated.py`의 GUI → 웹 UI
- **신규**:
  - 종목 추가/삭제 웹 인터페이스
  - 실시간 가격 차트
  - 목표가/손절가 설정

### 3. 통합 알림 시스템
- **기존**: 개별 이메일 발송
- **신규**: 
  - 브라우저 푸시 알림
  - 알림 히스토리 관리
  - 중요도별 필터링

## 📁 **디렉터리 구조**

```
v2/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py         # FastAPI 앱 진입점
│   │   ├── core/           # 핵심 설정
│   │   │   ├── config.py   # 환경설정
│   │   │   └── database.py # DB 설정
│   │   ├── services/       # 비즈니스 로직 (기존 .py 로직 이전)
│   │   │   ├── dart_service.py      # dart_monitor.py 로직
│   │   │   ├── stock_service.py     # stock_manager 로직  
│   │   │   └── notification_service.py # 알림 통합
│   │   ├── api/            # API 엔드포인트  
│   │   │   ├── dart.py
│   │   │   ├── stocks.py
│   │   │   └── notifications.py
│   │   └── models/         # Pydantic 모델
│   └── requirements.txt
├── frontend/               # Next.js 프론트엔드
│   ├── app/               # App Router (Next.js 13+)
│   │   ├── layout.tsx
│   │   ├── page.tsx       # 메인 대시보드
│   │   ├── dart/          # DART 관련 페이지
│   │   └── stocks/        # 주식 관련 페이지
│   ├── components/        # 재사용 컴포넌트
│   ├── lib/              # 유틸리티 & API 클라이언트
│   └── package.json
├── docker-compose.yml     # 통합 개발환경
└── README.md             # 프로젝트 가이드
```

## ⚡ **개발 우선순위**

### Phase 1 (핵심 기능) - 2-3시간
1. FastAPI + SQLite 기본 설정 
2. 기존 파이썬 로직 → 서비스 클래스로 이전
3. Next.js 기본 대시보드 UI
4. WebSocket 실시간 통신 구현

### Phase 2 (통합 & 테스트) - 1-2시간  
1. DART + 주식 모니터링 통합
2. 알림 시스템 구현
3. 데이터 지속성 및 안정성 테스트
4. UI/UX 최적화

### Phase 3 (배포 & 운영) - 1시간
1. Docker 컨테이너화
2. 프로덕션 설정 분리
3. 모니터링 & 로깅 시스템  
4. 문서화 완료

## 💡 **기술적 혁신 포인트**

1. **Zero-Config 개발환경**: `docker-compose up` 한 방에 개발환경 실행
2. **Type-Safe 전체 스택**: Python Pydantic ↔ TypeScript 자동 동기화  
3. **실시간 Everything**: WebSocket으로 모든 업데이트 실시간 반영
4. **Modern UI**: TailwindCSS + Headless UI로 2025년 스타일 구현
5. **자동화된 테스팅**: API 자동 테스트 + E2E 테스트 포함

---
**목표**: 기존 2000줄 복잡한 코드 → **500줄 내외 깔끔한 웹앱**으로 재탄생! 🚀