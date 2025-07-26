# 투자본부 모니터링 시스템 v3

Flask 기반 웹 애플리케이션으로 DART 공시 모니터링과 주식 가격 추적을 통합 제공합니다.

## 프로젝트 구조

```
v3/
├── app.py              # Flask 백엔드 서버
├── modules/            # 비즈니스 로직 모듈
│   ├── dart_monitor.py # DART 공시 모니터링
│   ├── stock_monitor.py # 주식 가격 모니터링
│   ├── email_utils.py  # 이메일 발송 유틸리티
│   └── config.py       # 통합 설정 관리
├── static/             # 프론트엔드 파일
│   ├── index.html      # 메인 대시보드
│   ├── script.js       # JavaScript 로직
│   └── style.css       # CSS 스타일
├── data/               # 데이터 파일 저장소
├── logs/               # 로그 파일 저장소
└── requirements.txt    # Python 의존성
```

## 설치 및 실행

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. 서버 실행:
```bash
python app.py
```

3. 브라우저에서 접속:
```
http://localhost:5000
```

## 주요 기능

- **DART 공시 모니터링**: 관심 기업의 공시를 실시간 모니터링
- **주식 가격 추적**: 설정된 종목의 가격 변동 알림
- **이메일 알림**: 중요 이벤트 발생 시 자동 이메일 발송
- **웹 대시보드**: 실시간 데이터 확인 및 설정 관리