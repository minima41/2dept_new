"""
V2 Investment Monitor - 로깅 설정
통합 로깅 시스템 (파일 로테이션 + 콘솔 출력)
"""
import logging
import logging.handlers
from pathlib import Path
import sys
from datetime import datetime

from ..core.config import settings


def setup_logging():
    """통합 로깅 설정"""
    
    # 로그 디렉터리 creating
    log_dir = settings.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # === 콘솔 핸들러 ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
    
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # === 파일 핸들러들 ===
    
    # 1. 메인 앱 로그
    setup_file_handler(
        logger_name="app",
        filename=log_dir / "app.log",
        level=logging.INFO
    )
    
    # 2. DART 모니터링 로그
    setup_file_handler(
        logger_name="app.services.dart_service",
        filename=log_dir / "dart_monitor.log", 
        level=logging.INFO
    )
    
    # 3. 주식 모니터링 로그
    setup_file_handler(
        logger_name="app.services.stock_service",
        filename=log_dir / "stock_monitor.log",
        level=logging.INFO
    )
    
    # 4. 알림 서비스 로그
    setup_file_handler(
        logger_name="app.services.notification_service",
        filename=log_dir / "notifications.log",
        level=logging.INFO
    )
    
    # 5. WebSocket 로그
    setup_file_handler(
        logger_name="app.services.websocket_service",
        filename=log_dir / "websocket.log",
        level=logging.INFO
    )
    
    # 6. 에러 전용 로그 (모든 에러)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # === 외부 라이브러리 로그 레벨 조정 ===
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("databases").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # starting 로그
    logger = logging.getLogger("app.utils.logger")
    logger.info(f"Logging system initialized - log directory: {log_dir}")


def setup_file_handler(logger_name: str, filename: Path, level: int = logging.INFO):
    """ items별 파일 핸들러 설정"""
    logger = logging.getLogger(logger_name)
    
    # 파일 로테이션 핸들러
    file_handler = logging.handlers.RotatingFileHandler(
        filename=filename,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 파일용 포매터
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(file_handler)
    logger.setLevel(level)


class ColoredFormatter(logging.Formatter):
    """컬러 출력을 위한 커스텀 포매터"""
    
    # ANSI 컬러 코드
    COLORS = {
        'DEBUG': '\033[36m',    # 청록색
        'INFO': '\033[32m',     #  seconds록색  
        'WARNING': '\033[33m',  # 노란색
        'ERROR': '\033[31m',    # 빨간색
        'CRITICAL': '\033[35m', # 마젠타색
        'RESET': '\033[0m'      # 리셋
    }
    
    def format(self, record):
        # 로그 레벨에 따라 컬러 적용
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        
        # message 컬러 적용 (이모지 제외)
        message = record.getMessage()
        record.msg = message
        
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)


def log_function_call(func_name: str, args: dict = None, result: any = None):
    """함수 호출 로깅 유틸리티"""
    logger = logging.getLogger("app.function_calls")
    
    if args:
        logger.debug(f"🔧 {func_name} 호출 - 인자: {args}")
    
    if result is not None:
        logger.debug(f"[SUCCESS] {func_name} completed - 결과: {result}")


def log_api_request(method: str, path: str, client_ip: str = None, user_id: str = None):
    """API 요청 로깅"""
    logger = logging.getLogger("app.api_requests")
    
    extras = []
    if client_ip:
        extras.append(f"IP: {client_ip}")
    if user_id:
        extras.append(f"User: {user_id}")
    
    extra_info = " | " + " | ".join(extras) if extras else ""
    logger.info(f"[WEB] {method} {path}{extra_info}")


def log_websocket_event(event_type: str, client_count: int, data_size: int = None):
    """WebSocket 이벤트 로깅"""
    logger = logging.getLogger("app.websocket_events")
    
    size_info = f" | 데이터 크기: {data_size}B" if data_size else ""
    logger.info(f"[BROADCAST] WebSocket {event_type} | 클라이언트: {client_count} items{size_info}")


def log_monitoring_cycle(service: str, processed: int, alerts: int, duration: float):
    """모니터링 cycle 로깅"""
    logger = logging.getLogger(f"app.monitoring.{service}")
    
    logger.info(f"[PROCESS] {service} cycle completed - processing: {processed} items | 알림: {alerts} items | 소요: {duration:.2f} seconds")


def log_email_notification(recipient: str, subject: str, success: bool):
    """이메일 sending 로깅"""
    logger = logging.getLogger("app.email_notifications")
    
    status = "[SUCCESS] success" if success else "[ERROR] failed"
    logger.info(f"[EMAIL] 이메일 sending {status} | 수신자: {recipient} | 제목: {subject}")


def log_database_operation(operation: str, table: str, affected_rows: int = None):
    """데이터베이스 task 로깅"""
    logger = logging.getLogger("app.database_operations")
    
    row_info = f" | 영향 받은 행: {affected_rows} items" if affected_rows is not None else ""
    logger.debug(f"[DATABASE] DB {operation} | 테이블: {table}{row_info}")


def log_external_api_call(api_name: str, endpoint: str, status_code: int, duration: float):
    """외부 API 호출 로깅"""
    logger = logging.getLogger("app.external_apis")
    
    status = "[SUCCESS]" if 200 <= status_code < 300 else "[ERROR]"
    logger.info(f"[WEB] {api_name} API {status} | {endpoint} | {status_code} | {duration:.2f} seconds")


# ===  items발용 테스트 ===
if __name__ == "__main__":
    setup_logging()
    logger = get_logger("test")
    
    logger.debug("🔧 디버그 message")
    logger.info("[SUCCESS] info message") 
    logger.warning("[WARNING] warning message")
    logger.error("[ERROR] 에러 message")
    logger.critical("[CRITICAL] critical error")
    
    print("로그 테스트 completed!")