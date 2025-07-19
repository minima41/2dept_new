"""
통합 로깅 시스템 모듈
- RotatingFileHandler 지원
- 구조화된 로그 레벨별 출력
- 자동 재시도 로직 포함
"""
import logging
import logging.handlers
import os
import pathlib
import sys
from datetime import datetime
from functools import wraps
from typing import Optional

# 로그 디렉토리 경로
LOG_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

class CustomFormatter(logging.Formatter):
    """색상 코드를 포함한 커스텀 포매터"""
    
    COLORS = {
        logging.DEBUG: '\033[36m',    # 청록색
        logging.INFO: '\033[32m',     # 녹색  
        logging.WARNING: '\033[33m',  # 노란색
        logging.ERROR: '\033[31m',    # 빨간색
        logging.CRITICAL: '\033[35m', # 자주색
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelno, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3,
    console_output: bool = True
) -> logging.Logger:
    """
    통합 로거 설정
    
    RotatingFileHandler와 콘솔 핸들러를 포함한 로거를 생성합니다.
    파일 로그는 지정된 크기에 도달하면 자동으로 로테이션됩니다.
    
    Args:
        name: 로거 이름 (모듈명 또는 기능명)
        log_file: 로그 파일명 (None이면 "{name}.log" 사용)
        level: 로그 레벨 (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: 로그 파일 최대 크기 (바이트 단위, 기본 5MB)
        backup_count: 로테이션할 백업 파일 개수 (기본 3개)
        console_output: 콘솔 출력 활성화 여부 (기본 True)
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
        
    Example:
        >>> logger = setup_logger("my_module", level=logging.DEBUG)
        >>> logger.info("로거 설정 완료")
        
    Note:
        WSL 환경에서 권한 문제 발생 시 일반 FileHandler로 fallback됩니다.
    """
    logger = logging.getLogger(name)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(level)
    
    # 파일 핸들러 설정
    if log_file is None:
        log_file = f"{name}.log"
    
    file_path = LOG_DIR / log_file
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    except (PermissionError, OSError):
        # WSL 환경에서 권한 문제 시 일반 파일 핸들러 사용
        file_handler = logging.FileHandler(
            file_path,
            encoding='utf-8'
        )
    file_handler.setLevel(level)
    
    # 파일용 포매터 (색상 없음)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러 설정
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # 콘솔용 포매터 (색상 포함)
        console_formatter = CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

def auto_retry(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    자동 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 재시도 간격 (초)
        exceptions: 재시도할 예외 타입들
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 최종 실패 (시도 {attempt + 1}/{max_retries + 1}): {e}")
                        raise
                    else:
                        logger.warning(f"{func.__name__} 재시도 {attempt + 1}/{max_retries + 1}: {e}")
                        import time
                        time.sleep(delay)
        return wrapper
    return decorator

def log_function_call(logger: Optional[logging.Logger] = None):
    """
    함수 호출 로그 데코레이터
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # 함수 시작 로그
            logger.debug(f"{func.__name__} 시작 - args: {args}, kwargs: {kwargs}")
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                # 함수 성공 로그
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"{func.__name__} 완료 - 소요시간: {duration:.3f}초")
                return result
            except Exception as e:
                # 함수 실패 로그
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"{func.__name__} 실패 - 소요시간: {duration:.3f}초, 오류: {e}")
                raise
        return wrapper
    return decorator

# 기본 로거들 설정
app_logger = setup_logger("app", "app.log")
dart_logger = setup_logger("dart_monitor", "dart_monitor.log")
stock_logger = setup_logger("stock_manager", "stock_manager.log")
email_logger = setup_logger("email", "email.log")
error_logger = setup_logger("error", "error.log", level=logging.ERROR)

# 모듈에서 직접 사용할 수 있는 로거들
__all__ = [
    'setup_logger',
    'auto_retry', 
    'log_function_call',
    'app_logger',
    'dart_logger',
    'stock_logger',
    'email_logger',
    'error_logger'
]