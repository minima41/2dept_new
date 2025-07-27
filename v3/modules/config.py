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

# === 기본 DART 키워드 목록 ===
DEFAULT_DART_KEYWORDS: List[str] = [
    "합병", "분할", "매각", "취득", "투자", "지분", "출자", 
    "신주", "유상증자", "무상증자", "주식매수", "자기주식", 
    "배당", "이익잉여금", "자본준비금", "특별관계자", 
    "주요주주", "경영권", "대주주", "전환사채", "감자"
]

# === 키워드 필터링 설정 ===
# AND 조건 키워드 세트 (모든 키워드가 포함되어야 함)
# 예: ["투자", "지분"] - 투자 AND 지분이 모두 포함된 공시만 필터링
KEYWORD_AND_CONDITIONS: List[List[str]] = [
    # 예시: 투자 관련 AND 조건들
    # ["투자", "지분"],        # 투자 AND 지분 
    # ["합병", "취득"],        # 합병 AND 취득
    # ["유상증자", "신주"]     # 유상증자 AND 신주
]

# 키워드 필터링 모드
KEYWORD_FILTER_MODE = os.getenv('KEYWORD_FILTER_MODE', 'OR')  # 'OR' 또는 'AND' 또는 'MIXED'

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

# === 로깅 시스템 설정 ===
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(5 * 1024 * 1024)))  # 5MB
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '3'))

# 로그 파일 이름 설정
LOG_FILES = {
    'app': 'app.log',                    # 일반 애플리케이션 로그
    'error': 'error.log',                # 에러 전용 로그
    'dart': 'dart_monitor.log',          # DART 모니터링 로그
    'stock': 'stock_monitor.log',        # 주식 모니터링 로그
    'email': 'email.log',                # 이메일 발송 로그
    'websocket': 'websocket.log',        # WebSocket 연결 로그
    'api': 'api_requests.log',           # API 요청/응답 로그
    'performance': 'performance.log'      # 성능 모니터링 로그
}

# 로그 포맷 설정
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 개발/프로덕션 환경별 로깅 레벨
LOG_LEVELS = {
    'DEBUG': ['dart_monitor', 'stock_monitor', 'email_utils'],
    'INFO': ['app', 'api_requests'],
    'WARNING': ['websocket'],
    'ERROR': ['error']
}

# 성능 로깅 설정
PERFORMANCE_LOGGING_ENABLED = os.getenv('PERFORMANCE_LOGGING_ENABLED', 'True').lower() == 'true'
SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))  # 초
API_RESPONSE_TIME_THRESHOLD = float(os.getenv('API_RESPONSE_TIME_THRESHOLD', '2.0'))  # 초

# === 데이터 파일 경로 ===
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')

# 파일 경로들
PROCESSED_IDS_FILE = os.path.join(DATA_DIR, 'processed_ids.txt')
MONITORING_STOCKS_FILE = os.path.join(DATA_DIR, 'monitoring_stocks.json')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')

# DART 데이터 파일 경로들
DART_COMPANIES_FILE = os.path.join(DATA_DIR, 'dart_companies.json')
DART_KEYWORDS_FILE = os.path.join(DATA_DIR, 'dart_keywords.json')
DAILY_HISTORY_FILE = os.path.join(DATA_DIR, 'daily_history.json')

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

# === 확장된 주식 데이터 스키마 ===
STOCK_DATA_SCHEMA = {
    "code": str,            # 종목코드 (필수)
    "name": str,            # 종목명 (필수)
    "category": str,        # 카테고리: "매수" | "기타" (기본값: "기타")
    "target_price": float,  # 목표가 (필수)
    "stop_loss": float,     # 손절가 (필수)
    "acquisition_price": float,  # 취득가 (선택, 수익률 계산용)
    "alert_settings": dict,      # 알림 설정 (선택)
    "memo": str,                # 메모 (선택)
    "current_price": float,     # 현재가 (시스템 업데이트)
    "change_percent": float,    # 등락률 (시스템 업데이트)
    "last_updated": str,        # 마지막 업데이트 시간 (시스템 업데이트)
    "enabled": bool,            # 모니터링 활성화 (기본값: True)
    "triggered_alerts": list,   # 발생한 알림 기록 (시스템 관리)
    "alert_prices": list,       # 알림 가격 목록 (시스템 관리)
    "error": str                # 오류 정보 (시스템 관리)
}

# === 주식 카테고리 정의 ===
STOCK_CATEGORIES = ["매수", "기타"]
DEFAULT_STOCK_CATEGORY = "기타"

# === 기본 알림 설정 ===
DEFAULT_ALERT_SETTINGS = {
    "daily_alert": True,        # 일일 알림 활성화
    "rise_threshold": 5.0,      # 상승률 알림 임계값 (%)
    "fall_threshold": 5.0,      # 하락률 알림 임계값 (%)
    "parity_percent": 80.0,     # 패리티 알림 임계값 (%)
    "target_alert": True,       # 목표가 도달 알림
    "stop_loss_alert": True     # 손절가 도달 알림
}

# === 데이터 마이그레이션 설정 ===
MIGRATION_VERSION = "1.1"  # 현재 데이터 스키마 버전
BACKUP_ENABLED = True      # 마이그레이션 시 백업 생성 여부

# === 동적 기업 관리 함수 ===

def add_monitoring_company(company_code: str, company_name: str) -> bool:
    """
    모니터링 기업 추가
    
    Args:
        company_code: 기업코드
        company_name: 기업명
        
    Returns:
        bool: 성공 여부
    """
    global COMPANIES
    
    try:
        if company_code in COMPANIES:
            return False  # 이미 존재하는 기업
        
        COMPANIES[company_code] = company_name
        
        # TODO: 향후 파일 저장 기능 추가 가능
        # save_companies_to_file()
        
        return True
        
    except Exception as e:
        print(f"기업 추가 오류: {e}")
        return False

def remove_monitoring_company(company_code: str) -> bool:
    """
    모니터링 기업 삭제
    
    Args:
        company_code: 삭제할 기업코드
        
    Returns:
        bool: 성공 여부
    """
    global COMPANIES
    
    try:
        if company_code not in COMPANIES:
            return False  # 존재하지 않는 기업
        
        del COMPANIES[company_code]
        
        # TODO: 향후 파일 저장 기능 추가 가능
        # save_companies_to_file()
        
        return True
        
    except Exception as e:
        print(f"기업 삭제 오류: {e}")
        return False

def get_monitoring_companies() -> Dict[str, str]:
    """
    현재 모니터링 기업 목록 반환
    
    Returns:
        Dict[str, str]: 기업코드 -> 기업명 매핑
    """
    return COMPANIES.copy()