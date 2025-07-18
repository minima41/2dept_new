# 투자본부 React + FastAPI 웹 애플리케이션 개발 가이드라인

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