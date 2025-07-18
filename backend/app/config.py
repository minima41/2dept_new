from pydantic_settings import BaseSettings
from typing import List, Dict
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "투자본부 모니터링 시스템"
    DEBUG: bool = True
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # DART API 설정
    DART_API_KEY: str = "d63d0566355b527123f1d14cf438c84041534b2b"
    DART_BASE_URL: str = "https://opendart.fss.or.kr/api"
    DART_CHECK_INTERVAL: int = 1800  # 30분 (초 단위)
    
    # 이메일 설정
    EMAIL_SENDER: str = "dlwlrma401@gmail.com"
    EMAIL_PASSWORD: str = "byvu_dkyn_qfyz_lwji"
    EMAIL_RECEIVER: str = "ljm@inveski.com"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    
    # 주가 모니터링 설정
    STOCK_UPDATE_INTERVAL: int = 10  # 10초 (초 단위)
    MARKET_OPEN_TIME: str = "09:00"
    MARKET_CLOSE_TIME: str = "15:35"
    
    # WebSocket 설정
    MAX_WEBSOCKET_CONNECTIONS: int = 50
    
    # 파일 경로 설정
    DATA_DIR: str = "/mnt/c/2dept/backend/app/data"
    LOGS_DIR: str = "/mnt/c/2dept/logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 관심 기업 목록 (기존 config.py에서 가져옴)
COMPANIES = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "005380": "현대차",
    "000270": "기아",
    "005490": "POSCO홀딩스",
    "035720": "카카오",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "012330": "현대모비스",
    "028260": "삼성물산",
    "066570": "LG전자",
    "034020": "두산에너빌리티",
    "003670": "포스코퓨처엠",
    "096770": "SK이노베이션",
    "018260": "삼성에스디에스",
    "086790": "하나금융지주",
    "316140": "우리금융지주",
    "055550": "신한지주",
    "105560": "KB금융",
    "017670": "SK텔레콤",
    "030200": "KT",
    "032640": "LG유플러스"
}

# 키워드 목록 (기존 config.py에서 가져옴)
KEYWORDS = [
    "합병", "분할", "매각", "취득", "투자", "지분", "출자", "신주", "유상증자", 
    "무상증자", "주식매수", "자기주식", "배당", "이익잉여금", "자본준비금",
    "특별관계자", "주요주주", "경영권", "대주주", "소송", "분쟁", "손해배상",
    "회생절차", "파산", "청산", "해산", "영업양도", "영업양수", "자산양도",
    "자산양수", "계약해지", "계약해제", "특허", "라이선스", "기술이전",
    "연구개발", "신제품", "신기술", "FDA", "임상", "치료제", "신약",
    "백신", "진단", "의료기기", "허가", "승인", "인증", "수주", "계약",
    "MOU", "LOI", "협약", "제휴", "파트너십", "조인트벤처", "공동투자",
    "공동개발", "공동출자", "증설", "확장", "신규사업", "사업다각화",
    "구조조정", "인수", "피인수", "상장", "상장폐지", "관리종목", "투자주의",
    "투자경고", "신용등급", "채권", "회사채", "전환사채", "신주인수권부사채",
    "워런트", "옵션", "스톡옵션", "주식선택권", "임원변경", "대표이사",
    "신임", "사임", "해임", "선임", "감사", "감사위원", "사외이사",
    "공시", "정정", "첨부", "취소", "철회", "연기", "변경", "수정"
]

# 설정 인스턴스
settings = Settings()