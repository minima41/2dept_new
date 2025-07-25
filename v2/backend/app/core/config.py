"""
V2 Investment Monitor - 통합 설정 관리
2025년 최신 Pydantic v2 + 환경변수 기반
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 통합 설정"""
    
    # === 기본 설정 ===
    app_name: str = "Investment Monitor V2"
    debug: bool = True
    version: str = "2.0.0"
    
    # === 서버 설정 ===
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # === 데이터베이스 ===
    database_url: str = "sqlite:///./investment_monitor.db"
    
    # === Redis (캐싱) ===
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  #  items발 시 선택적
    
    # === JWT 보안 ===
    secret_key: str = "your-super-secret-key-change-in-production-v2"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1주일
    
    # === DART API (기존 dart_monitor.py 설정) ===
    dart_api_key: str = "d63d0566355b527123f1d14cf438c84041534b2b"
    dart_base_url: str = "https://opendart.fss.or.kr/api"
    dart_check_interval: int = 30 * 60  # 30 minutes ( seconds 단위)
    
    # === 이메일 설정 (기존 설정 이전) ===
    email_sender: str = "dlwlrma401@gmail.com"
    email_password: str = "byvu_dkyn_qfyz_lwji" 
    email_receiver: str = "ljm@inveski.com"
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    
    # === 주식 모니터링 ===
    stock_update_interval: int = 10  # 10 seconds
    market_open_time: str = "09:00"
    market_close_time: str = "15:35"
    
    # === WebSocket ===
    max_websocket_connections: int = 100
    websocket_heartbeat_interval: int = 30
    
    # === 파일 경로 (OS 호환) ===
    @property
    def data_dir(self) -> Path:
        """데이터 파일 디렉터리 (v2 백엔드 전용)"""
        return Path(__file__).parent.parent.parent / "data"
    
    @property  
    def logs_dir(self) -> Path:
        """로그 파일 디렉터리 (v2 백엔드 전용)"""
        return Path(__file__).parent.parent.parent / "logs"
    
    # === 모니터링 설정 ===
    max_processed_ids: int = 1000
    notification_batch_size: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        

# === DART 키워드 (기존 config.py에서 이전) ===
DART_KEYWORDS = [
    "합병", " minutes할", "매각", "취득", "투자", "지 minutes", "출자", "신주", "유상증자", 
    "무상증자", "주식매수", "자기주식", "배당", "이익잉여금", "자본준비금",
    "특별관계자", "주요주주", "경영권", "대주주", "소송", " minutes쟁", "손해배상",
    "회생절차", "파산", "청산", "해산", "영업양도", "영업양수", "자산양도",
    "자산양수", "계약해지", "계약해제", "특허", "라이선스", "기술이전",
    "연구 items발", "신제품", "신기술", "FDA", "임상", "치료제", "신약",
    "백신", "진단", "의료기기", "허가", "승인", "인증", "수주", "계약",
    "MOU", "LOI", "협약", "제휴", "파트너십", "조인트벤처", "공동투자",
    "공동 items발", "공동출자", "증설", "확장", "신규사업", "사업다각화",
    "구조조정", "인수", "피인수", "상장", "상장폐지", "관리종목", "투자주의",
    "투자경고", "신용등급", "채권", "회사채", "전환사채", "신주인수권부사채",
    "워런트", "옵션", "스톡옵션", "주식선택권", "임원변경", "대표이사",
    "신임", "사임", "해임", "선임", "감사", "감사위원", "사외이사",
    "공시", "정정", "첨부", "취소", "철회", "연기", "변경", "수정"
]

# === 관심 기업 (기존 config.py에서 이전) ===  
MONITORING_COMPANIES = {
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
    "066570": "LG전자"
}

# === 전역 설정 인스턴스 ===
settings = Settings()

# === 디렉터리 자동 creating ===
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)