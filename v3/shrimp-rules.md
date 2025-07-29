# 투자본부 모니터링 시스템 v3 - AI Agent 개발 규칙

## 프로젝트 개요

### 시스템 정보
- **이름**: D2 Dash - 투자 모니터링 대시보드
- **기술 스택**: Python Flask + JavaScript + HTML/CSS
- **주요 기능**: DART 공시 모니터링 + 주식 가격 추적 + 이메일 알림
- **데이터 저장**: JSON 파일 기반 (FileLock 동시성 제어)
- **프로젝트 루트**: C:\2dept\v3
- **웹 접속**: http://localhost
- **로그 저장**: C:\2dept\logs

### 핵심 모듈
- **app.py**: Flask 메인 서버
- **modules/**: 백엔드 로직 (config.py, dart_monitor.py, stock_monitor.py, auth.py, logger_utils.py, email_utils.py)
- **static/**: 프론트엔드 파일 (index.html, dart.html, script.js, dart.js, style.css)
- **data/**: JSON 데이터 파일 저장소
- **logs/**: 시스템 로그 파일

## 아키텍처 및 디렉터리 구조

### 필수 준수 구조
```
C:\2dept\v3\
├── app.py                    # Flask 메인 서버
├── modules/                  # 백엔드 모듈 (모든 로직은 여기)
│   ├── config.py            # 중앙 설정 관리
│   ├── dart_monitor.py      # DART 공시 모니터링
│   ├── stock_monitor.py     # 주식 가격 모니터링
│   ├── auth.py              # 인증 시스템
│   ├── logger_utils.py      # 로깅 시스템
│   └── email_utils.py       # 이메일 알림
├── static/                   # 프론트엔드 파일
│   ├── index.html           # 메인 대시보드
│   ├── dart.html            # DART 공시 페이지
│   ├── script.js            # 메인 대시보드 JS
│   ├── dart.js              # DART 페이지 JS
│   └── style.css            # 공통 스타일시트
├── data/                     # JSON 데이터 저장
├── logs/                     # 시스템 로그
├── .env                      # 환경변수
└── requirements.txt          # Python 의존성
```

### 모듈별 책임 분리
- **config.py**: 모든 설정값 중앙 관리 (API 키, 이메일, 모니터링 간격 등)
- **dart_monitor.py**: DART API 연동, 공시 데이터 처리, 알림 발송
- **stock_monitor.py**: 주식 API 연동, 가격 추적, 알림 조건 처리
- **auth.py**: 사용자 인증, 세션 관리
- **logger_utils.py**: 통합 로깅 시스템
- **email_utils.py**: 이메일 알림 발송

## 코드 작업 표준

### 코딩 스타일
- **주석**: 한글 주석과 docstring 사용 필수
- **모듈 임포트**: 명확한 분리 (외부 라이브러리 → 내부 모듈)
- **로깅**: 모든 함수에서 logger_utils.py의 get_logger() 사용
- **예외 처리**: log_exception() 함수로 에러 로깅
- **환경 설정**: .env 파일과 config.py를 통한 중앙 관리

### 백엔드 개발 규칙
- **새 기능 추가**: modules/ 폴더에 모듈 생성 또는 기존 모듈 확장
- **API 엔드포인트**: app.py에 라우트 추가, 실제 로직은 modules/에서 구현
- **데이터 저장**: JSON 파일 + FileLock 사용 (동시성 제어 필수)
- **설정 변경**: config.py 수정 후 관련 모듈들에서 참조

### 프론트엔드 개발 규칙
- **HTML 구조**: 기존 레이아웃과 일관성 유지
- **JavaScript**: 백엔드 API와 연동하는 비동기 함수 구현
- **CSS**: style.css에서 공통 스타일 관리
- **아이콘**: Font Awesome 6.0.0 사용

## 파일 작업 안전 규칙

### edit-file-lines 필수 규칙
- **⚠️ 중요**: 모든 edit-file-lines 호출 시 반드시 `"dryRun": true` 설정
- **사전 확인**: 수정 전 get_file_lines로 정확한 라인 내용 확인
- **라인 번호**: 파일 수정 후 라인 번호 변경됨을 고려하여 재확인
- **섹션 분할**: 대용량 파일은 3-5개 섹션으로 나누어 순차 처리
- **approve_edit**: dryRun 확인 후 stateId로 실제 적용

### 파일 작업 순서
1. **확인**: `get_file_lines`로 수정할 부분의 현재 내용 확인
2. **계획**: 수정 범위와 내용 명확히 정의
3. **Dry Run**: `edit_file_lines`를 `dryRun: true`로 실행
4. **검토**: 반환된 diff 내용 확인
5. **적용**: `approve_edit`로 실제 수정 실행
6. **검증**: 수정 결과 확인

### 금지 작업
- **라인 번호 추측**: 반드시 실제 파일 내용 확인 후 작업
- **일괄 수정**: 한 번에 여러 파일 수정 금지 (순차 처리)
- **백업 없는 수정**: Git commit 없이 중요 파일 수정 금지

## Git 워크플로우 규칙

### 필수 Git 작업
- **저장소 초기화**: .git이 없으면 `git init` 실행
- **파일 수정 후**: 반드시 `git add`와 `git commit` 수행
- **커밋 메시지**: 컨벤셔널 커밋 형식 사용
  - `feat:` 새 기능 추가
  - `fix:` 버그 수정
  - `chore:` 설정 변경
  - `style:` UI/레이아웃 수정
  - `refactor:` 코드 리팩토링

### GitHub 연동
- **원격 저장소**: https://github.com/minima41/dash
- **CLI 사용**: GitHub CLI (gh) 명령어 우선 사용
- **브랜치 전략**: test 브랜치에서 검증 후 master로 PR 머지
- **푸시 전략**: HTTP 버퍼 크기 증가, 작은 단위로 분할 푸시
- **.gitignore**: 로그 파일, 임시 파일, __pycache__ 등 제외

### 커밋 예시
```bash
git add v3/modules/dart_monitor.py
git commit -m "fix: DART API 연동 오류 수정"
```

## 테스트 및 검증 규칙

### 기능 테스트 필수 사항
- **웹 접속**: http://localhost로 접속 테스트
- **로그 확인**: C:\2dept\logs에서 오류 로그 점검
- **API 상태**: DART API 연동 상태 확인
- **알림 시간**: 주가 알림은 9시-15시30분으로 제한
- **중복 방지**: 당일 동일 알림 내용 반복 금지

### 검증 절차
1. **기능 수정 후**: 해당 기능 동작 테스트
2. **로그 점검**: 에러 로그 발생 여부 확인
3. **연동 테스트**: 관련된 다른 기능들과의 연동 확인
4. **사용자 승인**: 테스트 완료 후 사용자에게 결과 보고

### 오류 처리
- **로그 우선**: 오류 발생 시 logs/ 폴더의 로그 파일 먼저 확인
- **API 오류**: DART API나 주식 API 연동 문제 시 대체 방안 검토
- **데이터 오류**: JSON 파일 손상 시 백업 파일 활용

## 다중 파일 연동 규칙

### DART 공시 관리 연동
**수정 시 함께 고려해야 할 파일들:**
- `modules/dart_monitor.py` ↔ `static/dart.html` ↔ `static/dart.js` ↔ `static/style.css`
- **백엔드 수정 시**: API 응답 형식 변경 → 프론트엔드 JS 수정 필요
- **레이아웃 수정 시**: HTML 구조 변경 → CSS 스타일 + JS 이벤트 핸들러 수정
- **설정 변경 시**: config.py → dart_monitor.py → 프론트엔드 반영

### 주식 모니터링 연동
**수정 시 함께 고려해야 할 파일들:**
- `modules/stock_monitor.py` ↔ `static/index.html` ↔ `static/script.js` ↔ `static/style.css`
- **종목 추가/수정**: 백엔드 데이터 구조 → 프론트엔드 UI 표시
- **알림 로직**: stock_monitor.py → email_utils.py → 프론트엔드 상태 표시
- **수익률 계산**: 백엔드 계산 로직 → 프론트엔드 UI 표시

### 공통 설정 연동
**설정 변경 시 연쇄 수정 필요:**
- `config.py` → `app.py` → 관련 모듈들 → 프론트엔드 설정
- `.env` → `config.py` → 모든 관련 모듈
- `requirements.txt` → Python 환경 → 관련 import 문

## AI 의사결정 표준

### 작업 우선순위
1. **사용자 안전**: 데이터 손실 방지, 백업 확인
2. **기능 안정성**: 기존 기능 영향 최소화
3. **코드 품질**: 기존 스타일과 일관성 유지
4. **테스트 완료**: 수정 후 반드시 동작 확인

### 불확실한 상황 처리
- **파일 내용 불명**: 추측하지 말고 실제 파일 내용 확인
- **API 변경 필요**: 백엔드와 프론트엔드 동시 수정 계획 수립
- **설정값 변경**: config.py에서 중앙 관리, 하드코딩 금지
- **에러 발생**: 로그 파일 확인 후 근본 원인 파악

### 의사결정 트리
```
수정 요청 받음
├── 단일 파일 수정?
│   ├── Yes → 파일 확인 → dryRun → 수정 → 테스트
│   └── No → 연관 파일 식별 → 순차 수정 계획
├── 설정 변경?
│   ├── Yes → config.py 우선 → 관련 모듈 확인
│   └── No → 기능별 모듈에서 처리
└── 테스트 필요?
    ├── 항상 Yes → 기능 테스트 → 로그 확인 → 보고
```

## 금지 사항 및 주의사항

### 절대 금지 사항
- **⚠️ 사용자 승인 없는 작업 진행 금지**
- **⚠️ Shrimp 작업 임의 삭제 금지**
- **⚠️ 기존 개발 규모 확장 금지** (테스트 및 오류 수정에 집중)
- **⚠️ MySQL 관련 코드 추가 금지** (파일 기반 저장소 사용)
- **⚠️ 하드코딩된 설정값 사용 금지** (config.py 활용)

### 주의 사항
- **파일 동시성**: JSON 파일 수정 시 FileLock 사용 확인
- **로그 확인**: 모든 작업 후 C:\2dept\logs에서 오류 로그 확인
- **백업 유지**: 중요 파일 수정 전 Git commit으로 백업
- **테스트 환경**: http://localhost 접속 확인
- **API 제한**: DART API 호출 제한, 주가 알림 시간 제한 준수

### 에러 시 대응
- **파일 읽기 실패**: 파일 경로와 권한 확인
- **API 연동 실패**: 네트워크 상태와 API 키 확인
- **Git 오류**: GitHub 토큰과 권한 확인
- **실행 오류**: Python 환경과 의존성 확인

## v3 보완사항 특별 규칙

### DART 공시관리 페이지 레이아웃 수정
- **참조 사이트**: https://dart.fss.or.kr/dsac001/mainY.do
- **수정 파일**: `static/dart.html` + `static/dart.js` + `static/style.css`
- **데이터 연동**: 10분마다 업데이트, 등록 종목 + 보고서명 매칭

### 주식 모니터링 구분 수정
- **현재**: 전체/메자닌/주식 구분 → 실제 데이터는 기타
- **수정**: 실제 등록된 종목의 구분에 맞춰 표시 정렬
- **수정 파일**: `modules/stock_monitor.py` + `static/index.html` + `static/script.js`

### 수익률 표시 기능
- **계산 기준**: 취득가 대비 현재가 수익률
- **표시 위치**: 주식 모니터링 테이블에 수익률 컬럼 추가
- **수정 파일**: 백엔드 계산 로직 + 프론트엔드 UI 표시

### 종목 추가 자동화
- **기능**: 종목코드 입력 → 종목명, 전일가 자동 조회
- **API 연동**: 주식 정보 API 활용
- **수정 파일**: `modules/stock_monitor.py` + 종목 추가 UI

### 손절가 설정 개선
- **선택지**: -5%, -10%, 직접입력
- **기본값**: -5%
- **계산**: 취득가 기준 자동 계산
- **수정 파일**: 종목 추가/수정 UI + 백엔드 계산 로직

### 주가 알림 제한
- **시간 제한**: 9시-15시30분만 알림
- **중복 방지**: 당일 동일 알림 반복 금지
- **수정 파일**: `modules/stock_monitor.py` + `modules/email_utils.py`

### DART API 연동 점검
- **확인 사항**: 데이터 수신 상태, API 응답 검증
- **오류 시**: 로그 확인 후 API 키, 네트워크 상태 점검
- **수정 파일**: `modules/dart_monitor.py`

---

**🔥 핵심 원칙: 모든 작업은 사용자 승인 후 진행, 테스트 완료 후 보고 필수**


## 프로젝트 개요

### 기술 스택
- Flask 백엔드 (Python)
- JavaScript 프론트엔드
- HTML/CSS UI
- JSON 데이터 저장
- 로그 기반 모니터링

### 핵심 기능
- DART 공시 모니터링 시스템
- 주식 가격 추적
- 실시간 알림 시스템
- 웹 대시보드 인터페이스

## 프로젝트 아키텍처

### 디렉토리 구조
```
v3/
├── app.py                 # Flask 메인 서버
├── modules/              # 백엔드 모듈
│   ├── auth.py          # 인증 시스템
│   ├── config.py        # 설정 관리
│   ├── dart_monitor.py  # DART 모니터링
│   ├── stock_monitor.py # 주식 모니터링
│   ├── logger_utils.py  # 로깅 시스템
│   └── email_utils.py   # 이메일 기능
├── static/              # 프론트엔드 자원
│   ├── index.html       # 메인 대시보드
│   ├── dart.html        # DART 관리 페이지
│   ├── script.js        # 메인 JavaScript
│   ├── dart.js          # DART JavaScript
│   └── style.css        # 스타일시트
├── data/                # 데이터 저장소
├── logs/                # 로그 파일
└── requirements.txt     # Python 의존성
```

## 코드 표준

### JavaScript 구문 규칙
- 객체 리터럴에서 메서드 간 **반드시 쉼표(,) 추가**
- async/await 함수는 적절한 컨텍스트 내에서만 사용
- 모든 DOM 요소 참조 전 존재 여부 확인 필수

### Python 코딩 규칙
- 모듈별 기능 분리 원칙 준수
- 모든 함수에 로깅 추가
- 예외 처리 시 logger_utils.log_exception 사용

### HTML 구조 규칙
- ID 속성은 kebab-case 사용 (예: refresh-companies)
- JavaScript에서 참조하는 모든 요소 ID 정의 필수

## 기능 구현 표준

### JavaScript 파일 수정 시
1. **구문 검증 필수**: 객체 메서드 간 쉼표 누락 확인
2. **DOM 요소 존재 확인**: HTML 파일에서 참조 요소 검증
3. **API 엔드포인트 일치 확인**: Flask 라우트와 fetch URL 동기화
4. **오류 처리 추가**: try-catch 블록과 로깅 포함

### HTML 파일 수정 시
1. **JavaScript 연동 확인**: 모든 ID가 JavaScript에서 사용되는지 검증
2. **CSS 클래스 일치**: style.css에 정의된 클래스만 사용
3. **반응형 구조 유지**: 기존 그리드 시스템 준수

### Python 모듈 수정 시
1. **로깅 시스템 활용**: get_logger() 사용
2. **설정 파일 참조**: config.py에서 상수 가져오기
3. **예외 처리 표준화**: log_exception() 함수 활용
4. **모듈 간 의존성 최소화**: 순환 import 방지

## 프레임워크 사용 표준

### Flask 라우트 관리
- API 엔드포인트는 `/api/v1/` 접두사 사용
- 모든 라우트에 로깅 미들웨어 적용
- JSON 응답은 `{"success": true/false, "data": {}, "message": ""}` 형식 준수

### JavaScript API 호출
- fetch() 사용 시 적절한 에러 처리 필수
- API_BASE 상수 활용하여 엔드포인트 구성
- 응답 데이터 구조 검증 후 사용

## 워크플로우 표준

### 파일 수정 워크플로우
1. **현재 코드 분석**: 수정 대상 파일의 기존 구조 파악
2. **관련 파일 확인**: 연동되는 파일들의 영향 범위 검토
3. **수정 계획 수립**: 변경사항이 미치는 영향 분석
4. **단계별 수정**: 3-5개 섹션으로 나누어 순차 진행
5. **Git 커밋**: 각 의미있는 변경 후 즉시 커밋

### 디버깅 워크플로우
1. **로그 확인**: `logs/` 폴더에서 오류 로그 분석
2. **콘솔 오류 추적**: 브라우저 개발자 도구 활용
3. **단계별 격리**: 문제 범위를 점진적으로 축소
4. **수정 후 검증**: 전체 시스템 동작 확인

## 핵심 파일 상호작용 표준

### JavaScript ↔ HTML 동기화
- **script.js 수정 시**: index.html의 DOM 요소 ID 확인 필수
- **dart.js 수정 시**: dart.html의 DOM 요소 ID 확인 필수
- **새 DOM 요소 추가 시**: JavaScript elements 객체 동시 업데이트

### Frontend ↔ Backend API 동기화
- **Flask 라우트 변경 시**: JavaScript API 호출부분 동시 수정
- **데이터 구조 변경 시**: 프론트엔드 파싱 로직 동시 업데이트
- **새 API 추가 시**: 프론트엔드 함수와 UI 요소 동시 생성

### 모듈 간 의존성 관리
- **config.py 수정 시**: 관련 모듈의 import문 확인
- **새 로거 추가 시**: logger_utils.py와 사용 모듈 동시 수정
- **모니터링 로직 변경 시**: app.py의 스케줄러 부분 검토

## AI 의사결정 표준

### 우선순위 판단 기준
1. **보안 취약점 > 기능 오류 > 성능 개선 > 코드 정리**
2. **백엔드 안정성 > 프론트엔드 UX > 로깅/모니터링**
3. **기존 기능 보존 > 새 기능 추가**

### 모호한 상황 처리
- **DOM 요소 누락 발견 시**: HTML에 요소 추가 후 JavaScript 수정
- **API 불일치 발견 시**: 백엔드 라우트 기준으로 프론트엔드 수정
- **로그 오류 발견 시**: logger_utils 설정 우선 확인

### 파일 수정 범위 결정
- **3줄 미만 변경**: 단일 edit 작업
- **3-10줄 변경**: 섹션별 분할 edit
- **10줄 초과 변경**: 5개 이하 섹션으로 분할

## 금지 사항

### 절대 금지
- **MetaMask 관련 코드 수정**: 기존 MetaMask 충돌 방지 코드 변경 금지
- **프로젝트 루트 구조 변경**: v3/ 폴더 구조 임의 변경 금지
- **핵심 모듈 삭제**: modules/ 폴더 내 파일 삭제 금지
- **설정 파일 임의 수정**: config.py 값 변경 시 전체 영향 검토 필수

### 주의 사항
- **JavaScript 구문 오류 유발 패턴**: 객체 메서드 간 쉼표 누락 방지
- **DOM 요소 참조 실수**: 존재하지 않는 ID 참조 방지
- **순환 import**: Python 모듈 간 순환 의존성 생성 방지
- **로그 파일 직접 수정**: logs/ 폴더 내 파일 직접 편집 금지

### 확인 필수 사항
- **edit-file-lines 사용 전**: 반드시 dryRun: true로 미리보기 확인
- **여러 파일 수정 시**: 파일 간 의존성 사전 검토
- **Git 커밋 전**: 전체 시스템 동작 테스트 수행
- **JavaScript 수정 후**: 브라우저 콘솔 오류 확인

## 예시

### ✅ 올바른 JavaScript 객체 메서드 구문
```javascript
const alertManager = {
    async updateTotalUnreadCount() {
        // 구현 코드
    },  // 쉼표 필수!
    
    async markAlertRead(alertId) {
        // 구현 코드
    }   // 마지막 메서드는 쉼표 선택사항
};
```

### ❌ 잘못된 JavaScript 객체 메서드 구문
```javascript
const alertManager = {
    async updateTotalUnreadCount() {
        // 구현 코드
    }   // 쉼표 누락!
    
    async markAlertRead(alertId) {  // SyntaxError 발생
        // 구현 코드
    }
};
```

### ✅ 올바른 DOM 요소 참조 패턴
```javascript
// dart.js에서 요소 참조 시
const elements = {
    refreshCompanies: document.getElementById('refresh-companies')
};

// dart.html에서 해당 요소 정의
<button id="refresh-companies" class="btn btn-primary">새로고침</button>
```

### ✅ 올바른 파일 수정 순서
1. 기존 코드 구조 분석
2. 관련 파일들 동시 확인
3. dryRun으로 변경사항 미리보기
4. 단계별 수정 실행
5. Git 커밋 수행

## 프로젝트 개요

### 기술 스택
- **백엔드**: Flask 3.x + Python 3.9+
- **프론트엔드**: Vanilla JavaScript + Bootstrap CSS
- **데이터 저장**: JSON 파일 기반 시스템
- **모니터링**: 실시간 주식/DART 공시 추적
- **인증**: Flask-Session 기반 세션 관리

### 핵심 기능
- 실시간 주식 가격 모니터링 및 알림
- DART 공시 모니터링 및 키워드 필터링
- 통합 알림 시스템
- 사용자 인증 및 권한 관리
- 성능 모니터링 및 로깅

## 프로젝트 아키텍처

### 디렉토리 구조
```
v3/
├── app.py              # Flask 메인 애플리케이션
├── modules/            # 백엔드 모듈들
│   ├── config.py       # 설정 관리
│   ├── stock_monitor.py # 주식 모니터링
│   ├── dart_monitor.py  # DART 공시 모니터링
│   ├── auth.py         # 인증 시스템
│   ├── logger_utils.py # 로깅 시스템
│   └── email_utils.py  # 이메일 발송
├── static/             # 프론트엔드 파일들
│   ├── index.html      # 메인 대시보드
│   ├── dart.html       # DART 관리 페이지
│   ├── script.js       # 메인 JavaScript
│   ├── dart.js         # DART 전용 JavaScript
│   └── style.css       # 스타일시트
├── data/               # JSON 데이터 파일들
│   ├── monitoring_stocks.json
│   ├── dart_companies.json
│   ├── dart_keywords.json
│   ├── daily_history.json
│   └── users.json
└── logs/               # 로그 파일들
```

### 모듈 의존성 체인
- **app.py** → modules/* (모든 모듈 의존)
- **stock_monitor.py** → config.py, logger_utils.py
- **dart_monitor.py** → config.py, logger_utils.py, email_utils.py
- **auth.py** → config.py, logger_utils.py

## 코딩 표준

### Python 코딩 규칙
- **함수명**: snake_case 사용 필수
- **클래스명**: PascalCase 사용 필수
- **상수명**: UPPER_CASE 사용 필수
- **타입 힌트**: 모든 함수에 반드시 타입 힌트 작성
- **Docstring**: 모든 함수/클래스에 구글 스타일 docstring 작성
- **에러 처리**: try-except 블록으로 모든 예외 상황 처리
- **로깅**: logger_utils.get_logger() 사용하여 모듈별 로거 생성

### JavaScript 코딩 규칙
- **함수명**: camelCase 사용 필수
- **상수명**: UPPER_CASE 사용 필수
- **변수명**: camelCase 사용 필수
- **API 호출**: async/await 패턴 사용 필수
- **에러 처리**: try-catch 블록으로 모든 API 호출 보호
- **DOM 조작**: 요소 존재 확인 후 조작 (null 체크 필수)

### CSS 규칙
- **클래스명**: kebab-case 사용 필수
- **Bootstrap 우선**: 기본 Bootstrap 클래스 최대한 활용
- **커스텀 CSS**: 꼭 필요한 경우만 style.css에 추가

## 기능 구현 표준

### API 엔드포인트 구현 규칙
- **URL 패턴**: `/api/v1/{resource}/{action}` 형식 준수
- **HTTP 메서드**: RESTful 원칙 준수 (GET, POST, PUT, DELETE)
- **인증 데코레이터**: @login_required 또는 @admin_required 필수 적용
- **성능 모니터링**: @performance_monitor() 데코레이터 필수 적용
- **요청 로깅**: @api_request_logger 데코레이터 필수 적용
- **에러 응답**: create_error_response() 함수 사용 필수
- **JSON 응답**: jsonify() 사용하여 일관된 응답 형식 유지

### 데이터 처리 규칙
- **JSON 파일 읽기**: 항상 파일 존재 확인 후 처리
- **JSON 파일 쓰기**: 백업 생성 후 원자적 쓰기 수행
- **데이터 검증**: 모든 입력 데이터 타입 및 형식 검증 필수
- **기본값 설정**: 누락된 필드에 대한 기본값 정의 필수

### 프론트엔드 구현 규칙
- **API 호출**: fetch() 사용하여 RESTful API 호출
- **로딩 상태**: API 호출 중 로딩 인디케이터 표시 필수
- **에러 표시**: API 오류 시 사용자 친화적 메시지 표시
- **데이터 검증**: 서버 응답 데이터 구조 검증 후 사용
- **실시간 업데이트**: setInterval을 사용한 주기적 데이터 갱신

## 프레임워크/라이브러리 사용 표준

### Flask 사용 규칙
- **라우트 정의**: 함수별로 명확한 단일 책임 유지
- **요청 처리**: request 객체 사용 시 항상 유효성 검증
- **세션 관리**: Flask-Session을 통한 서버 사이드 세션 사용
- **CORS 설정**: 개발 환경에서만 CORS 허용

### Bootstrap 사용 규칙
- **그리드 시스템**: 반응형 디자인을 위한 Bootstrap Grid 사용
- **컴포넌트**: 버튼, 카드, 모달 등 Bootstrap 컴포넌트 적극 활용
- **유틸리티 클래스**: 간단한 스타일링은 Bootstrap 유틸리티 클래스 사용

### 제3자 라이브러리 제약
- **새 라이브러리 추가 금지**: 기존 requirements.txt에 없는 라이브러리 추가 불가
- **CDN 사용 금지**: 프론트엔드에서 외부 CDN 의존성 추가 불가
- **jQuery 사용 금지**: Vanilla JavaScript만 사용

## 워크플로우 표준

### 개발 워크플로우
1. **코드 수정 전**: 관련 파일들의 현재 상태 확인
2. **수정 계획 수립**: 변경 영향도 분석 및 수정 순서 결정
3. **단위 수정**: 한 번에 하나의 기능만 수정
4. **테스트 실행**: 수정 후 관련 기능 동작 확인
5. **Git 커밋**: 의미 있는 단위로 커밋 수행

### 데이터 플로우
```
클라이언트 요청 → Flask 라우트 → 모듈 함수 → JSON 파일 I/O → 응답 반환
```

### 실시간 모니터링 플로우
```
백그라운드 스레드 → 외부 API 호출 → 데이터 처리 → JSON 파일 업데이트 → 알림 발송
```

## 핵심 파일 상호작용 표준

### 동시 수정 필수 파일 그룹

#### API 엔드포인트 추가 시
- **app.py**: 새 라우트 추가
- **해당 모듈**: 비즈니스 로직 구현
- **static/script.js** 또는 **static/dart.js**: 클라이언트 API 호출 추가

#### 새 설정 추가 시
- **modules/config.py**: 설정 상수 정의
- **사용하는 모든 모듈**: 새 설정 참조 추가

#### 데이터 모델 변경 시
- **해당 JSON 파일**: 데이터 구조 변경
- **관련 모든 모듈**: 읽기/쓰기 로직 업데이트
- **프론트엔드**: 데이터 처리 로직 업데이트

### 스크립트 파일 충돌 방지 규칙
- **API_BASE 상수**: script.js에서만 정의, dart.js에서는 사용만
- **전역 변수**: 파일별로 unique한 prefix 사용
- **함수명**: 파일별로 고유한 네임스페이스 패턴 사용

### 로깅 시스템 통합 규칙
- **모듈별 로거**: get_logger(module_name) 패턴 사용
- **로그 레벨**: DEBUG < INFO < WARNING < ERROR 순서 준수
- **성능 로깅**: @performance_monitor 데코레이터 사용
- **에러 로깅**: log_exception() 함수 사용하여 스택트레이스 포함

## AI 의사결정 표준

### 우선순위 판단 기준
1. **보안 관련**: 인증/권한 문제가 최우선
2. **데이터 무결성**: JSON 파일 손상 방지가 2순위
3. **시스템 안정성**: 서버 크래시 방지가 3순위
4. **사용자 경험**: UI/UX 개선이 4순위
5. **성능 최적화**: 속도 개선이 5순위

### 파일 수정 순서 결정 트리
```
백엔드 API 변경 필요?
├─ YES → app.py → modules → 프론트엔드 → 테스트
└─ NO → 프론트엔드만 수정 → 테스트

데이터 모델 변경 필요?
├─ YES → JSON 구조 설계 → 백엔드 → 프론트엔드 → 마이그레이션
└─ NO → 기존 구조 유지하며 수정

설정 변경 필요?
├─ YES → config.py → 관련 모듈들 → 재시작 필요 알림
└─ NO → 런타임 수정 가능
```

### 에러 처리 결정 기준
- **복구 가능한 에러**: 로그 기록 후 기본값으로 계속 진행
- **복구 불가능한 에러**: 즉시 중단하고 상세 에러 메시지 반환
- **외부 API 오류**: 재시도 로직 구현 (최대 3회)
- **JSON 파일 오류**: 백업에서 복구 시도

### 성능 최적화 결정 기준
- **API 응답 시간**: 500ms 이하 유지
- **파일 I/O**: 필요 시에만 수행, 캐싱 고려
- **메모리 사용**: 대용량 데이터는 스트리밍 처리
- **프론트엔드**: DOM 조작 최소화, 이벤트 위임 사용

## 금지 사항

### 절대 금지 사항
- **requirements.txt 수정 금지**: 새 라이브러리 추가 절대 불가
- **v3 외부 폴더 수정 금지**: v2나 루트 폴더 파일 수정 불가
- **동기 I/O 사용 금지**: 파일 읽기/쓰기 시 비동기 패턴 권장
- **하드코딩 금지**: 모든 설정값은 config.py에서 관리
- **직접 HTML 수정 금지**: 동적 콘텐츠는 JavaScript로 생성

### 코드 품질 금지 사항
- **중복 코드 작성 금지**: 기존 함수 재사용 필수
- **매직 넘버 사용 금지**: 모든 숫자는 명명된 상수로 정의
- **전역 상태 변경 금지**: 함수는 부작용 없이 작성
- **console.log 남기기 금지**: 디버깅 코드는 제거 후 커밋

### 보안 관련 금지 사항
- **인증 우회 금지**: @login_required 데코레이터 제거 불가
- **SQL 인젝션 위험 코드 금지**: 동적 쿼리 생성 불가
- **XSS 위험 코드 금지**: 사용자 입력 직접 HTML 삽입 불가
- **비밀번호 평문 저장 금지**: 해시화 필수

### 데이터 처리 금지 사항
- **JSON 파일 직접 덮어쓰기 금지**: 항상 백업 생성 후 처리
- **대용량 데이터 메모리 로드 금지**: 스트리밍 처리 사용
- **동시성 제어 없는 파일 쓰기 금지**: 파일 락 사용 필수
- **데이터 검증 생략 금지**: 모든 입력 데이터 검증 필수

## 특수 처리 지침

### API_BASE 상수 충돌 해결
- **문제**: script.js와 dart.js에서 동일한 상수명 사용
- **해결책**: dart.js에서 API_BASE 선언 제거, window.API_BASE 참조 사용
- **수정 순서**: 
  1. dart.js에서 `const API_BASE = '';` 라인 제거
  2. dart.js의 API 호출에서 `window.API_BASE` 사용
  3. 브라우저 콘솔 오류 해결 확인

### DART 공시 연동 강화
- **현재 상태**: dart_monitor.py가 독립적으로 동작
- **개선 방향**: 웹 시스템과 데이터 공유 강화
- **구현 방법**: 
  1. dart_monitor.py가 JSON 파일에 결과 저장
  2. Flask API가 해당 파일 읽어서 제공
  3. 프론트엔드에서 실시간 업데이트 표시

### Python-Flask 데이터 동기화
- **파일 기반 공유**: JSON 파일을 통한 데이터 교환
- **동기화 주기**: 최소 60초 간격으로 파일 업데이트
- **충돌 방지**: 파일 락과 원자적 쓰기 사용
- **백업 전략**: 수정 전 자동 백업 파일 생성

### 실시간 로그 시스템
- **로그 레벨별 파일 분리**: debug.log, info.log, error.log
- **로그 로테이션**: 일별 로그 파일 생성
- **웹 인터페이스**: /api/v1/stocks/logs API로 실시간 조회
- **성능 고려**: 로그 파일 크기 제한 및 압축

## 테스트 및 검증 표준

### 필수 테스트 항목
- **API 엔드포인트**: 모든 HTTP 메서드와 상태 코드 확인
- **인증 시스템**: 로그인/로그아웃/권한 검증
- **데이터 무결성**: JSON 파일 읽기/쓰기 검증
- **에러 처리**: 예외 상황에서의 시스템 안정성
- **프론트엔드**: UI 컴포넌트 동작 및 API 연동

### 성능 검증 기준
- **API 응답 시간**: 평균 200ms 이하
- **메모리 사용량**: 500MB 이하 유지
- **파일 I/O**: 동시 요청 처리 가능
- **프론트엔드**: 페이지 로드 시간 3초 이하

### 배포 전 체크리스트
- [ ] 모든 API 엔드포인트 정상 동작
- [ ] 인증 시스템 보안 검증
- [ ] 로그 파일 정리 및 권한 설정
- [ ] JSON 데이터 파일 백업 확인
- [ ] 프론트엔드 브라우저 호환성 확인
- [ ] 성능 모니터링 대시보드 확인

## 프로젝트 개요

**프로젝트명:** D2 Dash v3 - 투자 모니터링 대시보드  
**기술스택:** Flask, Python, HTML/CSS/JavaScript, JSON 데이터 저장  
**핵심기능:** DART 공시 모니터링, 주식 가격 추적, 이메일 알림 시스템  
**배포환경:** 로컬 웹서버 (http://localhost)  

## 프로젝트 아키텍처

### 디렉토리 구조
- `/` - 프로젝트 루트 (C:\2dept\v3)
- `app.py` - Flask 메인 애플리케이션
- `modules/` - 백엔드 모듈 (dart_monitor.py, stock_monitor.py, email_utils.py, config.py)
- `static/` - 프론트엔드 파일 (HTML, CSS, JS)
- `data/` - JSON 데이터 저장소
- `logs/` - 로그 파일 저장
- `.env` - 환경변수 설정

### 모듈 분할
- **dart_monitor.py**: DART OpenAPI 연동, 공시 데이터 수집
- **stock_monitor.py**: 주식 가격 추적, PyKrx/네이버 크롤링
- **email_utils.py**: 이메일 알림 발송
- **logger_utils.py**: 통합 로깅 시스템
- **config.py**: 설정값 관리

## 핵심 개발 규칙

### 파일 상호작용 규칙

**⚠️ 필수 준수사항:**
- `modules/` 폴더의 파이썬 모듈 수정시 `app.py`의 import와 라우트 함께 확인/수정할 것
- `static/` 폴더의 HTML 수정시 관련 JS 파일도 함께 수정할 것
- 새로운 API 엔드포인트 추가시 프론트엔드 JS에서 호출 코드도 추가할 것
- `config.py` 수정시 관련 모듈들의 변수명 일치 확인할 것
- 데이터 스키마 변경시 모든 관련 모듈의 데이터 처리 로직 동기화할 것

### 데이터 관리 표준

**JSON 파일 기반 저장:**
- 모든 영구 데이터는 `data/` 폴더의 JSON 파일로 저장할 것
- 주식 데이터: `data/monitoring_stocks.json`
- DART 데이터: `data/dart_companies.json`, `data/processed_ids.json`
- 사용자 데이터: `data/users.json`
- 설정 데이터: `data/settings.json`

**파일 동시 접근 방지:**
- JSON 파일 수정시 반드시 `FileLock` 사용할 것
- 백업 파일 생성 후 원본 파일 수정할 것
- 데이터 무결성 검증 로직 포함할 것

### 기능 구현 표준

**이메일 알림 시스템:**
- 모든 이메일 발송은 `email_utils.py`의 함수 사용할 것
- 주식 알림과 DART 알림은 별도 템플릿 사용할 것
- 발송 실패시 재시도 로직 포함할 것
- 이메일 설정은 `.env` 파일에서 관리할 것

**로깅 시스템:**
- 모든 로깅은 `logger_utils.py`의 `get_logger()` 사용할 것
- 모듈별 로거 인스턴스 분리 관리할 것
- 에러 로그는 스택트레이스 포함할 것
- 로그 파일은 `logs/` 폴더에 저장할 것

**실시간 모니터링:**
- 백그라운드 작업은 `threading` 모듈 사용할 것
- 주식 가격 체크는 10초 간격으로 실행할 것
- 시장 시간(09:00-15:30) 외에는 모니터링 중단할 것
- WebSocket 연결로 실시간 업데이트 제공할 것

### UI/UX 개발 표준

**반응형 디자인:**
- 모든 페이지는 모바일 환경 지원할 것
- CSS Grid/Flexbox 사용하여 레이아웃 구성할 것
- 최소 해상도 320px 지원할 것

**사용자 인터랙션:**
- 모든 사용자 액션에 로딩 상태 표시할 것
- 에러 발생시 명확한 에러 메시지 표시할 것
- 성공적인 액션에 대한 피드백 제공할 것
- 폼 입력시 실시간 유효성 검증 제공할 것

## 코딩 표준

### 명명 규칙
- **Python**: snake_case (함수, 변수, 모듈)
- **Python**: PascalCase (클래스명)
- **JavaScript**: camelCase (함수, 변수)
- **CSS**: kebab-case (클래스명)
- **파일명**: snake_case (Python), kebab-case (HTML/CSS/JS)

### 주석 규칙
- 모든 함수에 docstring 작성할 것
- 복잡한 로직에는 인라인 주석 추가할 것
- TODO/FIXME 주석 사용하여 개선점 표시할 것
- API 엔드포인트에는 입력/출력 스키마 문서화할 것

### 에러 처리
- 모든 외부 API 호출에 try-catch 블록 적용할 것
- 사용자 입력 검증 로직 포함할 것
- 에러 메시지는 사용자 친화적으로 작성할 것
- 치명적 에러는 관리자에게 이메일 알림 발송할 것

## 특정 기능 구현 가이드

### 주식 모니터링 구현
- **카테고리 분류**: 메자닌/주식 2개 카테고리로 구분할 것
- **종목 관리**: 추가/삭제/편집 기능 제공할 것
- **가격 모니터링**: PyKrx 우선, 실패시 네이버 크롤링 사용할 것
- **알림 조건**: 상한/하한 임계값 설정 기능 제공할 것
- **장종료 보고서**: 15:30 이후 하루 결과 이메일 발송할 것

### DART 공시 모니터링 구현
- **종목 관리**: 관심 종목 추가/삭제 기능 제공할 것
- **보고서 키워드**: 특정 보고서명 필터링 기능 제공할 것
- **AND 조건**: 종목 + 키워드 모두 일치시 알림 발송할 것
- **중복 방지**: 처리된 공시 ID 저장하여 중복 알림 방지할 것

### 로그인 시스템 구현
- **사용자 관리**: JSON 파일 기반 사용자 데이터 저장할 것
- **세션 관리**: Flask-Session 사용하여 로그인 상태 관리할 것
- **권한 관리**: 일반 사용자/관리자 권한 구분할 것
- **승인 시스템**: 신규 가입시 관리자 승인 필요하게 할 것

## 의존성 관리

### 필수 라이브러리
- **Flask**: 웹 프레임워크
- **requests**: HTTP 클라이언트
- **beautifulsoup4**: 웹 스크래핑
- **pykrx**: 주식 데이터 (선택적)
- **filelock**: 파일 동시 접근 방지
- **python-dotenv**: 환경변수 관리

### 외부 API
- **DART OpenAPI**: 공시 데이터 수집
- **네이버 금융**: 주식 가격 크롤링 (백업용)
- **SendGrid/SMTP**: 이메일 발송

## 워크플로우 표준

### 개발 프로세스
1. 기능 요구사항 분석
2. 관련 모듈/파일 식별
3. 백엔드 API 구현
4. 프론트엔드 UI 구현
5. 통합 테스트 수행
6. 에러 처리 검증
7. 문서화 업데이트

### 테스트 절차
- 단위 테스트: 각 모듈별 기능 검증
- 통합 테스트: API 엔드포인트 동작 확인
- UI 테스트: 브라우저에서 사용자 시나리오 테스트
- 부하 테스트: 동시 사용자 환경 시뮬레이션

## AI 의사결정 기준

### 우선순위 판단
1. **보안** > 기능 > 성능
2. **데이터 안정성** > 사용자 편의성
3. **기존 시스템 호환성** > 새로운 기능

### 모호한 상황 처리
- 기존 코드 패턴 분석하여 일관성 유지할 것
- 불확실한 요구사항은 보수적으로 접근할 것
- 중요한 변경사항은 백업 생성 후 진행할 것

## 금지 사항

### ❌ 절대 금지
- 기존 JSON 데이터 파일의 스키마를 임의 변경하지 말 것
- 보안에 민감한 정보를 평문으로 저장하지 말 것
- 동기화되지 않은 멀티스레딩 코드를 작성하지 말 것
- 사용자 입력을 검증 없이 처리하지 말 것
- 외부 의존성 없이 작동해야 하는 핵심 기능을 외부 라이브러리에 의존시키지 말 것

### ⚠️ 주의 사항
- PyKrx 라이브러리는 선택적 의존성으로 처리할 것
- 이메일 발송 실패가 전체 시스템을 중단시키지 않도록 할 것
- 대량의 로그 파일이 디스크 공간을 고갈시키지 않도록 로테이션 설정할 것

## 예시

### ✅ 올바른 구현
```python
# 데이터 파일 수정시
with FileLock(f"{data_file}.lock"):
    with open(data_file, 'r') as f:
        data = json.load(f)
    # 데이터 수정
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)
```

### ❌ 잘못된 구현
```python
# 동시 접근 제어 없이 파일 수정
with open(data_file, 'w') as f:
    json.dump(data, f)
```

---

**최종 업데이트:** 2025-07-27  
**문서 버전:** v3.0  

## 프로젝트 개요

투자본부 모니터링 시스템 v3 - Flask 백엔드와 JavaScript SPA 프론트엔드로 구성된 DART 공시 모니터링 및 주식 가격 추적 웹 애플리케이션

- **프로젝트 루트**: C:\2dept\v3
- **서빙 URL**: http://localhost
- **기술 스택**: Flask + JavaScript SPA + MySQL
- **주요 기능**: DART 공시 모니터링, 주식 투자 모니터링, 통합 알림 시스템

## 프로젝트 아키텍처

### 디렉토리 구조 규칙

- **백엔드**: app.py (메인 Flask 서버)
- **모듈**: modules/ (config.py, dart_monitor.py, stock_monitor.py, email_utils.py)
- **프론트엔드**: static/ (index.html, dart.html, script.js, dart.js, style.css)
- **로그**: logs/ (app.log, error.log 등)
- **데이터**: data/ (JSON 파일, 임시 데이터)

### 모듈화 원칙

- **절대 금지**: app.py에 모든 로직을 작성하는 것
- **필수 준수**: 기능별로 modules/ 폴더의 해당 파일에 구현
- **의존성 관리**: modules/__init__.py 파일 유지

## SPA 라우팅 규칙

### Flask Catch-All 라우트 구현

**필수 구현**: app.py에 다음 패턴으로 catch-all 라우트 추가

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    # API 요청은 제외
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # 정적 파일 요청 처리
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    
    # SPA 라우트는 index.html 반환
    return send_from_directory(app.static_folder, 'index.html')
```

### 라우트 우선순위

1. **API 라우트**: /api/v1/* (최우선)
2. **정적 파일**: /static/* (두 번째)
3. **SPA 라우트**: 나머지 모든 경로 (마지막)

## API 표준

### URL 패턴

- **필수 사용**: 모든 API는 `/api/v1/` prefix 사용
- **금지**: `/api/` 단독 사용 (버전 관리 불가)

### API 응답 형식 표준

**성공 응답**:
```json
{
    "status": "success",
    "data": {...},
    "message": "Optional success message"
}
```

**에러 응답**:
```json
{
    "status": "error",
    "error": "Error description",
    "code": "ERROR_CODE"
}
```

### DART API 특수 규칙

- **날짜 형식**: 반드시 YYYYMMDD 사용 (예: "20241201")
- **기본 날짜 범위**: 미지정 시 최근 12개월
- **최대 조회 기간**: 한 번에 1년 이내로 제한

## 파일 수정 연계 규칙

### Flask 백엔드 수정 시

**app.py 수정 시 필수 확인**:
- modules/config.py (설정 변경 영향)
- modules/dart_monitor.py (DART 관련 수정 시)
- modules/stock_monitor.py (주식 관련 수정 시)
- requirements.txt (새 패키지 추가 시)

### JavaScript 프론트엔드 수정 시

## 주식 모니터링 UI 표준

### 탭 구조 구현 규칙

**필수 구현**: 주식 모니터링 페이지는 다음 3개 탭으로 구성할 것
- **전체**: 모든 모니터링 종목 표시 (종목 수 실시간 업데이트)
- **매수만**: category가 '매수'인 종목만 필터링
- **기타**: category가 '기타'인 종목만 필터링

**탭 표시 형식**: "탭명 (종목수)" 형태로 표시 (예: "전체 (29)", "매수만 (15)")

### 종목 테이블 컬럼 표준

**필수 컬럼 순서**:
1. **종목코드** (6자리) - 클릭 시 종목 수정 모달
2. **종목명** - 한글명 표시
3. **현재가** - 실시간 업데이트, 천 단위 콤마
4. **등락률** - 색상 구분 (상승: 빨강, 하락: 파랑)
5. **목표가(TP)** - Target Price
6. **손절가(SL)** - Stop Loss  
7. **마지막 체크** - 마지막 가격 업데이트 시간
8. **상태** - 모니터링 중/off
9. **알람설정** - on/off

**색상 규칙**:
- 상승: #f44336 (빨강)
- 하락: #2196f3 (파랑)
- 보합: #757575 (회색)

### 실시간 업데이트 규칙

**업데이트 주기**: 10초마다 전체 종목 가격 갱신
**장시간 제한**: 09:00-15:30 시간대만 활성화
**UI 반영**: 가격 변경 시 1초간 하이라이트 효과

## 모달 팝업 구현 표준

### 종목 추가/수정 모달 필수 요소

**라디오 버튼**: 매수/기타 선택 (필수)
**입력 필드**:
- 종목코드 (6자리, 숫자만)
- 목표가(TP) (숫자, 천 단위 콤마)
- 손절가(SL) (숫자, 천 단위 콤마)  
- 전일가 (참고용, 자동 입력)
- 전일가(floor) (하한선)
- 취득가 (매수 카테고리만)

**알림 설정**:
- 일일 급등 알림 활성화 (체크박스)
- 급등 임계값 (기본값: 5%)
- 급락 임계값 (기본값: 5%)
- 메모 (선택사항)
- 패리티 알림 퍼센트 설정

**버튼**: 저장/취소

### 유효성 검사 규칙

- **종목코드**: 6자리 숫자, 실제 존재하는 종목인지 API로 검증
- **목표가**: 현재가보다 높아야 함 (매수 카테고리)
- **손절가**: 현재가보다 낮아야 함 (매수 카테고리)
- **임계값**: 1-50% 범위 내 숫자

## 데이터 분류 시스템

### 카테고리 관리 규칙

**매수 카테고리**:
- 실제 보유 종목
- 목표가/손절가 필수 설정
- 취득가 입력 필수
- 수익률 계산 표시

**기타 카테고리**:
- 관심 종목, 분석 대상
- 목표가/손절가 선택사항
- 취득가 불필요
- 등락률만 표시

### 데이터 저장 형식

```json
{
  "code": "005930",
  "name": "삼성전자",
  "category": "매수|기타",
  "target_price": 85000,
  "stop_loss": 75000,
  "acquisition_price": 80000,
  "alert_settings": {
    "daily_alert": true,
    "rise_threshold": 5,
    "fall_threshold": 5,
    "parity_percent": 80
  },
  "memo": "선택사항",
  "created_at": "2025-07-27T10:30:00Z",
  "updated_at": "2025-07-27T10:30:00Z"
}
```

## 알림 시스템 세부 규칙

### 패리티 알림

**발동 조건**: 설정한 퍼센트에 도달 시
**계산 공식**: (현재가 / 목표가) * 100
**예시**: 목표가 100,000원, 패리티 80% 설정 → 80,000원 도달시 알림

### 급등급락 알림

**일일 기준**: 전일 종가 대비 설정 임계값 초과시
**실시간 기준**: 최근 1시간 내 설정 임계값 초과시
**중복 방지**: 동일 조건으로 1일 1회만 알림

### 목표가/손절가 알림

**목표가 도달**: 현재가 >= 목표가
**손절가 도달**: 현재가 <= 손절가
**즉시 알림**: 조건 달성 즉시 이메일 발송

## 실시간 로그 시스템

### 일일 내역 표시 규칙

**컬럼 구성**:
- 시간 (HH:MM:SS)
- 종목코드
- 동작 (급등/급락/목표가/손절가)
- 알림 유형 (독과 투웹↑/독과 투웹↓)
- 현재가
- 기준가

**정렬**: 시간 역순 (최신이 위)
**보관 기간**: 당일만 표시, 자정에 초기화

### 실시간 로그 표시 규칙

**로그 내용**:
- 수동 새로고침 실행 시간
- 데이터 모드 업뎃 완료 로그
- UI 데이터 로드 완료 로그
- 종목 수: 총 119개 등 정보

**표시 형식**: "YYYY-MM-DD HH:MM:SS,mmm - INFO - 메시지"
**자동 스크롤**: 새 로그 추가시 하단으로 자동 이동
**새로고침 주기**: 60초마다 로그 갱신

## 특수 UI 컴포넌트 규칙

### 새로고침 주기 설정

**위치**: 우측 하단
**옵션**: 60초 선택 드롭다운
**동작**: 설정 변경시 즉시 적용

### 모니터링 상태 표시

**아이콘**: 녹색 원 (정상), 빨간 원 (오류)
**위치**: 각 종목 행의 상태 컬럼
**클릭 동작**: 모니터링 on/off 토글

### 반응형 레이아웃

**데스크톱**: 전체 테이블 표시
**태블릿**: 일부 컬럼 숨김 (메모, 마지막체크)
**모바일**: 카드 형태로 변경, 필수 정보만 표시

**최종 업데이트:** 2025-07-27  
**문서 버전:** v3.1 (주식 모니터링 시스템 특화)
**script.js 수정 시 필수 확인**:
- index.html (DOM 요소 변경 확인)
- style.css (새 스타일 클래스 추가 시)
- dart.js (공통 함수 수정 시)

**dart.js 수정 시 필수 확인**:
- dart.html (DART 페이지 관련 수정)
- script.js (공통 API 호출 함수 수정 시)

### 데이터베이스 연관 파일

**MySQL 스키마 변경 시 필수 확인**:
- modules/config.py (DB 설정)
- modules/stock_monitor.py (주식 데이터 테이블 관련)
- modules/dart_monitor.py (DART 데이터 테이블 관련)

## 로깅 및 디버깅 규칙

### 로그 파일 규칙

- **app.log**: 모든 일반 로그
- **error.log**: 에러 전용 로그
- **debug.log**: 개발 시 디버그 로그

### 로깅 레벨 사용

- **ERROR**: 시스템 중단 수준 오류
- **WARNING**: 기능 영향을 주는 문제
- **INFO**: 정상 동작 기록
- **DEBUG**: 개발/테스트 정보

### 필수 로깅 위치

- **API 요청/응답**: 모든 API 호출 시작과 종료
- **DART API 호출**: 외부 API 호출 시작, 종료, 에러
- **데이터베이스 작업**: CRUD 작업 전후
- **에러 발생**: 모든 try-catch 블록에서 exception 로깅

## Git 워크플로우 규칙

### 커밋 메시지 형식

```
<type>: <description>

<body>
```

**타입 종류**:
- feat: 새 기능 추가
- fix: 버그 수정
- refactor: 코드 리팩토링
- docs: 문서 변경
- test: 테스트 코드
- style: 코드 스타일 변경

### 브랜치 관리

- **main**: 운영 브랜치
- **test**: 테스트 브랜치
- **feature/***: 기능 개발 브랜치

### 필수 Git 작업 순서

1. 파일 수정 후 즉시: `git add .`
2. 의미있는 단위로: `git commit -m "type: description"`
3. 테스트 완료 후: `git push origin test`
4. 검증 완료 후: PR로 main 병합

## 에러 처리 표준

### 프론트엔드 에러 처리

**필수 구현**: 모든 fetch 호출에 try-catch
```javascript
try {
    const response = await fetch('/api/v1/endpoint');
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    // 정상 처리
} catch (error) {
    console.error('API 호출 실패:', error);
    // 사용자에게 에러 표시
}
```

### 백엔드 에러 처리

**필수 구현**: 모든 API 엔드포인트에 try-except
```python
@app.route('/api/v1/endpoint')
def api_endpoint():
    try:
        # 로직 구현
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"API 에러: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500
```

## 데이터 형식 규칙

### 날짜/시간 형식

- **DART API**: YYYYMMDD (예: "20241201")
- **내부 저장**: ISO 8601 (예: "2024-12-01T10:30:00Z")
- **화면 표시**: YYYY-MM-DD HH:MM (예: "2024-12-01 10:30")

### 통화 표시

- **원화**: 천 단위 콤마, "원" 단위 (예: "1,234,567원")
- **달러**: 소수점 2자리, "$" 기호 (예: "$1,234.56")

## 성능 최적화 규칙

### API 응답 최적화

- **페이징**: 목록 조회 시 limit/offset 파라미터 필수
- **필드 선택**: 필요한 필드만 반환
- **캐싱**: 동일 요청은 5분간 캐시

### 프론트엔드 최적화

- **지연 로딩**: 초기 로드 시 필수 데이터만
- **배치 요청**: 여러 API 호출을 하나로 통합
- **에러 재시도**: 네트워크 에러 시 3회까지 자동 재시도

## 보안 규칙

### API 보안

- **입력 검증**: 모든 파라미터 검증 필수
- **SQL 인젝션 방지**: ORM 사용 또는 파라미터 바인딩
- **로그 민감정보**: 비밀번호, API 키 로깅 금지

### 설정 파일 관리

- **.env**: 민감한 설정 정보 (Git 추적 제외)
- **.env.example**: 설정 템플릿 (Git 포함)
- **config.py**: 환경변수 로드 및 기본값 설정

## 금지 사항

### 절대 금지 사항

- **하드코딩**: API 키, 비밀번호, DB 연결 정보
- **전역 변수**: 스레드 안전하지 않은 전역 상태
- **블로킹 호출**: 메인 스레드에서 긴 작업 수행
- **에러 무시**: try-except에서 pass 사용

### 코드 품질 금지

- **거대 함수**: 50줄 이상 함수 작성
- **깊은 중첩**: 4단계 이상 if/for 중첩
- **매직 넘버**: 의미 없는 숫자 하드코딩
- **중복 코드**: 동일 로직 3회 이상 반복

### 파일 수정 금지

- **프로덕션 로그**: 운영 중 로그 파일 직접 수정
- **Git 히스토리**: 이미 푸시된 커밋 수정
- **node_modules**: npm 패키지 직접 수정
- **__pycache__**: Python 캐시 파일 수동 수정

## 테스트 규칙

### 단위 테스트

- **모든 API**: 정상/에러 케이스 테스트
- **모든 함수**: 입력/출력 검증
- **커버리지**: 최소 80% 이상

### 통합 테스트

- **API 플로우**: 전체 사용자 시나리오
- **데이터베이스**: 실제 DB 연동 테스트
- **외부 API**: DART API 연동 테스트

### 성능 테스트

- **응답 시간**: API 3초 이내 응답
- **동시 접속**: 10명 동시 사용 가능
- **메모리 사용량**: 500MB 이내 유지