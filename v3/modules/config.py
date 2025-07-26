"""
투자본부 모니터링 시스템 v3 - 통합 설정 관리
기존 dart_monitor.py의 설정을 환경변수와 함께 중앙 관리
"""
import os
from typing import Dict, List
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# === DART API 설정 ===
DART_API_KEY = os.getenv('DART_API_KEY', 'd63d0566355b527123f1d14cf438c84041534b2b')

# === 이메일 설정 ===
EMAIL_SENDER = os.getenv('EMAIL_SENDER', 'dlwlrma401@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'byvu dkyn qfyz lwji')
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER', 'ljm@inveski.com')

# SendGrid 설정 (선택사항)
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', EMAIL_SENDER)

# === 모니터링 간격 설정 (초) ===
DART_CHECK_INTERVAL = int(os.getenv('DART_CHECK_INTERVAL', '1800'))  # 30분
STOCK_CHECK_INTERVAL = int(os.getenv('STOCK_CHECK_INTERVAL', '10'))   # 10초

# === DART 관심 기업 설정 ===
COMPANIES: Dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스", 
    "035420": "NAVER",
    "035720": "카카오",
    "207940": "삼성바이오로직스",
    "006400": "삼성SDI",
    "051910": "LG화학",
    "068270": "셀트리온",
    "005490": "POSCO홀딩스",
    "105560": "KB금융",
    "055550": "신한지주",
    "096770": "SK이노베이션",
    "012330": "현대모비스",
    "028260": "삼성물산",
    "066570": "LG전자",
    "003550": "LG",
    "017670": "SK텔레콤",
    "030200": "KT",
    "018260": "삼성에스디에스"
}

# === DART 키워드 필터링 ===
KEYWORDS: List[str] = [
    "합병", "분할", "매각", "취득", "투자", "지분", "출자", "신주", "유상증자", 
    "무상증자", "주식매수", "자기주식", "배당", "이익잉여금", "자본준비금",
    "특별관계자", "주요주주", "경영권", "대주주", "소송", "분쟁", "손해배상",
    "부채비율", "유동비율", "당기순이익", "매출액", "영업이익", "자산총계",
    "부채총계", "자본총계", "현금", "차입금", "신용등급", "회계감사",
    "내부회계관리제도", "공시", "정정", "취소", "연기", "철회"
]

# === 중요 공시 구분 ===
IMPORTANT_SECTIONS: List[str] = [
    "주요사항보고서", "증권발행실무준칙", "기업결합", "분할", "합병", 
    "주식의매수", "자기주식", "유상증자", "무상증자", "주식매수선택권",
    "전환사채", "신주인수권부사채", "교환사채", "감자", "주식분할", "주식병합"
]

# === 문맥 윈도우 설정 ===
CONTEXT_WINDOW = 150  # 키워드 주변 문자 수

# === Flask 서버 설정 ===
APP_NAME = "D2 Dash"
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# === 주식 모니터링 설정 ===
STOCK_MARKET_OPEN_TIME = "09:00"
STOCK_MARKET_CLOSE_TIME = "15:30"

# 주식 알림 임계값 (%)
STOCK_ALERT_THRESHOLD_HIGH = 5.0  # 상승 알림
STOCK_ALERT_THRESHOLD_LOW = -3.0  # 하락 알림

# === 로그 설정 ===
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3

# === 데이터 파일 경로 ===
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')

# 파일 경로들
PROCESSED_IDS_FILE = os.path.join(DATA_DIR, 'processed_ids.txt')
MONITORING_STOCKS_FILE = os.path.join(DATA_DIR, 'monitoring_stocks.json')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')

# === 외부 API 설정 ===
DART_API_URL = "https://opendart.fss.or.kr/api"
NAVER_FINANCE_URL = "https://finance.naver.com"

# 요청 타임아웃 (초)
REQUEST_TIMEOUT = 30

# === 기본 모니터링 주식 ===
DEFAULT_MONITORING_STOCKS = [
    {
        "code": "005930",
        "name": "삼성전자",
        "target_price": 80000,
        "stop_loss": 65000,
        "enabled": True
    },
    {
        "code": "000660", 
        "name": "SK하이닉스",
        "target_price": 150000,
        "stop_loss": 120000,
        "enabled": True
    },
    {
        "code": "035420",
        "name": "NAVER",
        "target_price": 200000,
        "stop_loss": 160000,
        "enabled": True
    }
]