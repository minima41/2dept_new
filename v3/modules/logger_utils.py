"""
고급 로깅 유틸리티 모듈
성능 모니터링, 구조화된 로깅, 로그 로테이션 등 제공
"""
import logging
import logging.handlers
import os
import time
import functools
import json
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager

from .config import (
    LOGS_DIR, LOG_FILES, LOG_FORMAT, LOG_DATE_FORMAT,
    LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_LEVEL,
    PERFORMANCE_LOGGING_ENABLED, SLOW_QUERY_THRESHOLD,
    API_RESPONSE_TIME_THRESHOLD
)

class StructuredLogger:
    """구조화된 로깅을 위한 클래스"""
    
    def __init__(self, name: str, log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # 중복 핸들러 방지
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: str = None):
        """로그 핸들러 설정"""
        # 로그 디렉토리 생성
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        # 파일 핸들러 (로테이션 포함)
        if log_file:
            file_path = os.path.join(LOGS_DIR, log_file)
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                LOG_FORMAT, datefmt=LOG_DATE_FORMAT
            ))
            self.logger.addHandler(file_handler)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_handler.setFormatter(logging.Formatter(
            LOG_FORMAT, datefmt=LOG_DATE_FORMAT
        ))
        self.logger.addHandler(console_handler)
    
    def structured_log(self, level: str, message: str, **kwargs):
        """구조화된 로그 메시지 생성"""
        log_data = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        formatted_message = f"{message} | " + " | ".join(
            f"{k}={v}" for k, v in kwargs.items()
        )
        
        getattr(self.logger, level.lower())(formatted_message)
    
    def debug(self, message: str, **kwargs):
        self.structured_log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.structured_log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.structured_log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.structured_log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.structured_log('CRITICAL', message, **kwargs)

class PerformanceLogger:
    """성능 모니터링 로거"""
    
    def __init__(self):
        self.logger = StructuredLogger('performance', LOG_FILES['performance'])
        self.enabled = PERFORMANCE_LOGGING_ENABLED
    
    @contextmanager
    def measure_time(self, operation: str, **context):
        """실행 시간 측정 컨텍스트 매니저"""
        if not self.enabled:
            yield
            return
        
        start_time = time.time()
        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            self.log_performance(operation, elapsed_time, **context)
    
    def log_performance(self, operation: str, elapsed_time: float, **context):
        """성능 로그 기록"""
        if not self.enabled:
            return
        
        level = 'WARNING' if elapsed_time > SLOW_QUERY_THRESHOLD else 'INFO'
        
        self.logger.structured_log(
            level,
            f"Performance: {operation}",
            operation=operation,
            elapsed_time=f"{elapsed_time:.3f}s",
            is_slow=elapsed_time > SLOW_QUERY_THRESHOLD,
            **context
        )

def performance_monitor(operation_name: str = None):
    """성능 모니터링 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = PerformanceLogger()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with perf_logger.measure_time(op_name, function=func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def api_request_logger(func: Callable) -> Callable:
    """API 요청 로깅 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        api_logger = StructuredLogger('api', LOG_FILES['api'])
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            level = 'WARNING' if elapsed_time > API_RESPONSE_TIME_THRESHOLD else 'INFO'
            
            api_logger.structured_log(
                level,
                f"API Request: {func.__name__}",
                function=func.__name__,
                elapsed_time=f"{elapsed_time:.3f}s",
                success=True,
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            api_logger.structured_log(
                'ERROR',
                f"API Request Failed: {func.__name__}",
                function=func.__name__,
                elapsed_time=f"{elapsed_time:.3f}s",
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            
            raise
    
    return wrapper

# 전역 로거 인스턴스들
loggers = {
    'app': StructuredLogger('app', LOG_FILES['app']),
    'dart': StructuredLogger('dart_monitor', LOG_FILES['dart']),
    'stock': StructuredLogger('stock_monitor', LOG_FILES['stock']),
    'email': StructuredLogger('email', LOG_FILES['email']),
    'websocket': StructuredLogger('websocket', LOG_FILES['websocket']),
    'error': StructuredLogger('error', LOG_FILES['error']),
    'performance': PerformanceLogger()
}

def get_logger(name: str) -> StructuredLogger:
    """로거 인스턴스 반환"""
    if name in loggers:
        return loggers[name]
    else:
        return StructuredLogger(name)

def log_exception(logger_name: str = 'error'):
    """예외 로깅 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger(logger_name)
                logger.error(
                    f"Exception in {func.__name__}",
                    function=func.__name__,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    module=func.__module__
                )
                raise
        return wrapper
    return decorator

def setup_logging():
    """로깅 시스템 초기화"""
    # 로그 디렉토리 생성
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # 로그 파일들이 존재하는지 확인하고 권한 설정
    for log_file in LOG_FILES.values():
        log_path = os.path.join(LOGS_DIR, log_file)
        if not os.path.exists(log_path):
            # 빈 로그 파일 생성
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"# {log_file} - Created at {datetime.now().isoformat()}\n")
    
    # 시스템 시작 로그
    app_logger = get_logger('app')
    app_logger.info(
        "로깅 시스템 초기화 완료",
        log_level=LOG_LEVEL,
        log_files=list(LOG_FILES.keys()),
        performance_enabled=PERFORMANCE_LOGGING_ENABLED
    )

# 모듈 로드 시 자동 초기화
setup_logging()