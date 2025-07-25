# V2 Investment Monitor - Backend

투자본부 DART 공시 및 주식 모니터링 시스템의 FastAPI 백엔드입니다.

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 값 입력
```

### 3. 서버 실행
```bash
# 방법 1: Python 스크립트
python run_server.py

# 방법 2: uvicorn 직접 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 방법 3: 메인 모듈 실행
python app/main.py
```

### 4. API 접근
- **메인 페이지**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **헬스체크**: http://localhost:8000/health

## 🏗️ 아키텍처

### 디렉터리 구조
```
backend/
├── app/
│   ├── main.py              # FastAPI 메인 앱
│   ├── core/                # 핵심 설정
│   │   ├── config.py        # 설정 관리
│   │   └── database.py      # DB 연결
│   ├── services/            # 비즈니스 로직
│   │   ├── dart_service.py  # DART 모니터링
│   │   ├── stock_service.py # 주식 모니터링
│   │   ├── notification_service.py # 알림 처리
│   │   └── websocket_service.py    # 실시간 통신
│   ├── routers/             # API 라우터
│   │   ├── dart_router.py   # DART API
│   │   ├── stock_router.py  # 주식 API
│   │   ├── notification_router.py # 알림 API
│   │   └── system_router.py # 시스템 API
│   ├── models/              # Pydantic 모델
│   │   ├── dart_models.py   # DART 모델
│   │   └── stock_models.py  # 주식 모델
│   └── utils/               # 유틸리티
│       └── logger.py        # 로깅 시스템
├── data/                    # 데이터 파일
├── logs/                    # 로그 파일
└── requirements.txt         # Python 의존성
```

### 핵심 기능

#### 1. DART 공시 모니터링
- **30분 간격** 자동 공시 확인
- **키워드 매칭** 및 중요도 점수 계산
- **관심 기업** 별도 모니터링
- **이메일 알림** 자동 발송

#### 2. 주식 가격 모니터링
- **실시간 주가** 업데이트 (PyKrx + 웹 스크래핑)
- **목표가/손절가** 알림
- **시장 시간** 자동 감지
- **WebSocket** 실시간 전송

#### 3. 통합 알림 시스템
- **이메일 발송** (SMTP)
- **WebSocket 브로드캐스트**
- **알림 히스토리** 관리
- **우선순위** 기반 처리

#### 4. 실시간 통신
- **WebSocket** 연결 관리
- **이벤트 구독** 시스템
- **하트비트** 체크
- **자동 재연결**

## 📊 API 엔드포인트

### DART API (`/api/dart/`)
```
GET  /disclosures          # 공시 목록 조회
GET  /disclosures/latest   # 최신 공시
GET  /disclosures/{id}     # 공시 상세
GET  /statistics           # 통계 정보
POST /check-now            # 수동 확인
PUT  /keywords             # 키워드 설정
```

### 주식 API (`/api/stocks/`)
```
GET  /monitoring           # 모니터링 주식 목록
POST /monitoring           # 주식 추가
PUT  /monitoring/{code}    # 주식 설정 수정
GET  /price/{code}         # 현재가 조회
POST /update-prices        # 수동 주가 업데이트
```

### 알림 API (`/api/notifications/`)
```
GET  /                     # 알림 목록
GET  /unread               # 읽지 않은 알림
POST /mark-read            # 읽음 표시
GET  /statistics           # 알림 통계
POST /test                 # 테스트 알림
```

### 시스템 API (`/api/system/`)
```
GET  /health              # 헬스체크
GET  /status              # 시스템 상태
GET  /diagnostics         # 시스템 진단
GET  /logs                # 로그 파일 목록
POST /maintenance/cleanup # 시스템 정리
```

## 🔧 설정

### 환경 변수
주요 환경 변수는 `.env` 파일에서 설정:

```env
# DART API
DART_API_KEY=your-dart-api-key
DART_CHECK_INTERVAL=1800

# 이메일
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECEIVER=recipient@company.com

# 주식 모니터링
STOCK_UPDATE_INTERVAL=10
MARKET_OPEN_TIME=09:00
MARKET_CLOSE_TIME=15:35
```

### 키워드 및 기업 설정
`app/core/config.py`에서 직접 수정하거나 API를 통해 동적 변경:

```python
DART_KEYWORDS = ["합병", "분할", "매각", ...]
MONITORING_COMPANIES = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    ...
}
```

## 🐳 Docker 실행

### Docker Compose 사용
```bash
# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 단독 Docker 실행
```bash
# 이미지 빌드
docker build -t investment-monitor-backend .

# 컨테이너 실행
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  investment-monitor-backend
```

## 📝 로깅

로그 파일은 `logs/` 디렉터리에 저장:

- `app.log` - 일반 애플리케이션 로그
- `dart_monitor.log` - DART 모니터링 로그
- `stock_monitor.log` - 주식 모니터링 로그
- `notifications.log` - 알림 발송 로그
- `websocket.log` - WebSocket 연결 로그
- `error.log` - 에러 전용 로그

## 🧪 테스트

### API 테스트
```bash
# 헬스체크
curl http://localhost:8000/health

# DART 수동 확인
curl -X POST http://localhost:8000/api/dart/check-now

# 주가 수동 업데이트
curl -X POST http://localhost:8000/api/stocks/update-prices

# 테스트 알림 발송
curl -X POST "http://localhost:8000/api/notifications/test?notification_type=system"
```

### 시스템 진단
```bash
curl http://localhost:8000/api/system/diagnostics
```

## 🛠️ 개발

### 코드 구조
- **서비스 계층**: 비즈니스 로직 분리
- **라우터 계층**: API 엔드포인트 정의
- **모델 계층**: 데이터 검증 (Pydantic)
- **유틸리티**: 공통 기능 (로깅 등)

### 개발 모드 실행
```bash
python run_server.py
# 또는
uvicorn app.main:app --reload --log-level debug
```

### 새 기능 추가 시
1. `models/`에 Pydantic 모델 정의
2. `services/`에 비즈니스 로직 구현
3. `routers/`에 API 엔드포인트 추가
4. `main.py`에 라우터 등록

## ⚠️ 주의사항

### 보안
- 프로덕션에서는 `SECRET_KEY` 변경 필수
- 이메일 비밀번호는 **앱 비밀번호** 사용
- DART API 키는 환경 변수로만 설정

### 성능
- 시장 시간 외에는 주식 업데이트 중단
- WebSocket 연결 수 제한 (기본 100개)
- 로그 파일 자동 로테이션 (5MB, 3개 백업)

### 데이터
- SQLite (개발용) / PostgreSQL (프로덕션) 지원
- 데이터 파일은 `data/` 디렉터리에 저장
- 정기적인 데이터베이스 정리 권장

## 📞 지원

시스템 관련 문의는 투자본부 내부 채널을 이용해 주세요.

---

**V2 Investment Monitor** - 2024 투자본부 웹 애플리케이션