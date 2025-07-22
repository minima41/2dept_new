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
    except (PermissionError, OSError) as e:
        # WSL 환경에서 권한 문제 시 대체 방안 시도
        print(f"RotatingFileHandler 생성 실패: {e}")
        
        try:
            # 먼저 로그 디렉토리 권한 확인 및 생성
            LOG_DIR.chmod(0o755)
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            print(f"권한 조정 후 RotatingFileHandler 생성 성공: {file_path}")
        except (PermissionError, OSError) as e2:
            print(f"권한 조정 후에도 RotatingFileHandler 실패: {e2}")
            # 최종 fallback: 일반 FileHandler 사용
            try:
                file_handler = logging.FileHandler(
                    file_path,
                    encoding='utf-8'
                )
                print(f"FileHandler로 fallback 성공: {file_path}")
            except Exception as e3:
                print(f"모든 핸들러 생성 실패: {e3}")
                # 콘솔 전용으로 동작
                file_handler = None
    # 파일 핸들러가 성공적으로 생성된 경우에만 추가
    if file_handler is not None:
        file_handler.setLevel(level)
        
        # 파일용 포매터 (색상 없음)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    else:
        print(f"파일 핸들러 생성 실패 - {name} 로거는 콘솔 출력만 사용합니다")
    
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


def manual_log_rotation(log_file: str, max_size_mb: int = 10, keep_files: int = 3):
    """
    WSL2 환경에서 RotatingFileHandler가 실패할 경우를 대비한 수동 로그 로테이션
    
    Args:
        log_file: 로그 파일명 (확장자 포함)
        max_size_mb: 최대 파일 크기 (MB)
        keep_files: 보관할 백업 파일 수
    """
    log_path = LOG_DIR / log_file
    
    # 파일이 존재하지 않으면 무시
    if not log_path.exists():
        return
    
    # 파일 크기 확인
    file_size_mb = log_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        print(f"로그 파일 크기 초과 ({file_size_mb:.1f}MB > {max_size_mb}MB) - 수동 로테이션 시작")
        
        try:
            # WSL2에서 rename 실패 시 복사 후 삭제 방식 사용
            import shutil
            import tempfile
            
            # 기존 백업 파일들 순환
            for i in range(keep_files - 1, 0, -1):
                old_backup = LOG_DIR / f"{log_file}.{i}"
                new_backup = LOG_DIR / f"{log_file}.{i + 1}"
                
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()  # 기존 파일 삭제
                    shutil.move(str(old_backup), str(new_backup))
            
            # 현재 로그 파일을 .1으로 백업
            backup_file = LOG_DIR / f"{log_file}.1"
            if backup_file.exists():
                backup_file.unlink()
            
            # 원본 파일의 마지막 몇 줄만 보관하고 나머지는 백업으로 이동
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 마지막 1000줄만 보관
            keep_lines = 1000
            if len(lines) > keep_lines:
                # 오래된 줄들을 백업에 저장
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines[:-keep_lines])
                
                # 최근 줄들만 원본에 유지
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-keep_lines:])
            
            print(f"수동 로그 로테이션 완료: {log_file}")
            
        except Exception as e:
            print(f"수동 로그 로테이션 실패 ({log_file}): {e}")
            # 최후의 방법: 파일 내용을 간단히 자르기
            try:
                with open(log_path, 'r+', encoding='utf-8', errors='ignore') as f:
                    f.seek(0)
                    lines = f.readlines()
                    if len(lines) > 1000:
                        f.seek(0)
                        f.writelines(lines[-1000:])
                        f.truncate()
                print(f"로그 파일 내용 축소 완료: {log_file}")
            except Exception as e2:
                print(f"로그 파일 축소도 실패: {e2}")


def cleanup_oversized_logs():
    """
    크기가 큰 로그 파일들을 자동으로 로테이션
    """
    log_files = ["app.log", "dart_monitor.log", "stock_manager.log", "email.log", "error.log"]
    
    for log_file in log_files:
        manual_log_rotation(log_file, max_size_mb=10, keep_files=3)

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
    'manual_log_rotation',
    'cleanup_oversized_logs',
    'app_logger',
    'dart_logger',
    'stock_logger',
    'email_logger',
    'error_logger'
]