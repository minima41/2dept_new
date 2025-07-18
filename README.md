# 투자본부 모니터링 시스템

React + FastAPI 기반 투자 모니터링 웹 애플리케이션

## 🏗️ 프로젝트 구조

```
C:\2dept\
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py            # 메인 서버
│   │   ├── config.py          # 환경설정
│   │   ├── modules/           # 비즈니스 모듈
│   │   │   ├── dart/          # DART 공시 모니터링
│   │   │   └── stocks/        # 주가 모니터링
│   │   ├── shared/            # 공통 모듈
│   │   │   ├── database.py    # 데이터베이스
│   │   │   └── websocket.py   # WebSocket 관리
│   │   └── data/              # 데이터 파일
│   └── requirements.txt
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── components/       # 재사용 컴포넌트
│   │   ├── hooks/            # 커스텀 훅
│   │   ├── stores/           # 상태 관리
│   │   └── services/         # API 클라이언트
│   └── package.json
└── logs/                      # 로그 파일
```

## 🚀 시스템 실행 방법

### 1. Python 백엔드 실행 (WSL 환경)

```bash
# 백엔드 디렉토리로 이동
cd /mnt/c/2dept/backend

# Python 가상환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate

# 의존성 설치 (pip가 없는 경우)
# Ubuntu/Debian: sudo apt update && sudo apt install python3-pip
# 또는 패키지 매니저를 통해 설치

# 서버 실행
python3 app/main.py
```

**백엔드 실행 시 주의사항:**
- Python 3.9+ 필요
- pip 모듈이 설치되어 있어야 함
- 환경 변수 파일 (.env) 생성 필요

### 2. React 프론트엔드 실행

```bash
# 프론트엔드 디렉토리로 이동
cd /mnt/c/2dept/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 또는 빌드 후 실행
npm run build
npm run preview
```

### 3. 접속 정보

- **백엔드**: http://localhost:8000
- **프론트엔드**: http://localhost:3000
- **WebSocket**: ws://localhost:8000/ws

## 🔧 현재 구현 상태

### ✅ 완료된 기능
1. **프로젝트 구조 설정**
   - FastAPI 백엔드 기본 구조
   - React 프론트엔드 기본 구조
   - 모듈형 아키텍처

2. **백엔드 핵심 모듈**
   - WebSocket 실시간 통신
   - DART 공시 모니터링 서비스
   - 주가 모니터링 서비스
   - 데이터베이스 연결 (SQLite)

3. **프론트엔드 UI**
   - 대시보드 페이지
   - DART 모니터링 페이지
   - 주가 모니터링 페이지
   - 실시간 알림 시스템
   - 반응형 레이아웃

4. **상태 관리**
   - Zustand 스토어
   - React Query API 클라이언트
   - WebSocket 연결 관리

### ⚠️ 현재 제한사항

1. **백엔드 의존성**
   - Python pip 모듈 미설치로 인한 패키지 설치 불가
   - 수동 설치 필요: `sudo apt install python3-pip python3-venv`

2. **실시간 기능**
   - WebSocket 연결 테스트 필요
   - 실제 DART API 연동 확인 필요

3. **데이터베이스**
   - SQLite 초기 데이터 설정 필요
   - 마이그레이션 스크립트 실행 필요

## 🔄 다음 단계

1. **Python 환경 설정**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```

2. **백엔드 의존성 설치**
   ```bash
   cd /mnt/c/2dept/backend
   pip3 install -r requirements.txt
   ```

3. **시스템 테스트**
   - 백엔드 서버 실행 확인
   - 프론트엔드 연결 확인  
   - WebSocket 통신 테스트

4. **추가 구현 단계**
   - 6단계: DART 프론트엔드 세부 구현
   - 7단계: 주가 모니터링 프론트엔드 구현
   - 8단계: 포트폴리오 관리 통합
   - 9단계: 시스템 통합 테스트

## 🛠️ 기술 스택

- **백엔드**: FastAPI, SQLAlchemy, APScheduler, WebSocket
- **프론트엔드**: React 18, TypeScript, Tailwind CSS, Zustand
- **실시간 통신**: WebSocket
- **데이터베이스**: SQLite (개발) → PostgreSQL (프로덕션)
- **API 연동**: DART OpenAPI, PyKrx, Naver 증권

## 📊 모니터링 기능

1. **DART 공시 모니터링**
   - 30분 간격 자동 체크
   - 키워드 기반 필터링
   - 실시간 알림

2. **주가 모니터링**
   - 5-10초 간격 실시간 업데이트
   - TP/SL 알림
   - 포트폴리오 손익 계산

3. **이메일 알림**
   - 중요 공시 즉시 알림
   - 주가 임계값 도달 시 알림