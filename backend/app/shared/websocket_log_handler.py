import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from threading import Lock

from .websocket import websocket_manager


class WebSocketLogHandler(logging.Handler):
    """WebSocket을 통해 로그를 실시간으로 스트리밍하는 핸들러"""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.loop = None
        self.lock = Lock()
        
        # 로그 메시지 큐 (비동기 처리를 위해)
        self.log_queue = []
        self.max_queue_size = 1000
        
    def emit(self, record: logging.LogRecord):
        """로그 레코드를 WebSocket으로 전송"""
        try:
            # 로그 데이터 구성
            log_data = self._format_log_record(record)
            
            # 큐에 추가 (스레드 안전)
            with self.lock:
                if len(self.log_queue) >= self.max_queue_size:
                    # 큐가 가득 차면 오래된 로그 제거
                    self.log_queue.pop(0)
                self.log_queue.append(log_data)
            
            # 비동기로 전송 (현재 실행 중인 이벤트 루프가 있는 경우에만)
            try:
                loop = asyncio.get_running_loop()
                if loop:
                    loop.create_task(self._send_log_async(log_data))
            except RuntimeError:
                # 이벤트 루프가 없거나 다른 스레드에서 실행 중인 경우 무시
                pass
                
        except Exception:
            # 로그 핸들러에서 예외가 발생하면 조용히 무시
            # (로그 자체가 문제를 일으키면 안 됨)
            pass
    
    def _format_log_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """로그 레코드를 WebSocket 전송용 형태로 변환"""
        # 예외 정보 처리
        exc_text = None
        if record.exc_info:
            exc_text = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info[1])
        
        return {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
            "thread_id": record.thread,
            "process_id": record.process,
            "exception": exc_text,
            "pathname": record.pathname,
            "filename": record.filename
        }
    
    async def _send_log_async(self, log_data: Dict[str, Any]):
        """비동기로 로그 메시지를 WebSocket으로 전송"""
        try:
            await websocket_manager.send_log_message(log_data)
        except Exception:
            # WebSocket 전송 실패 시 조용히 무시
            pass
    
    def get_recent_logs(self, count: int = 100) -> list:
        """최근 로그 메시지들을 반환"""
        with self.lock:
            return self.log_queue[-count:] if count <= len(self.log_queue) else self.log_queue.copy()
    
    def clear_logs(self):
        """저장된 로그 메시지들을 클리어"""
        with self.lock:
            self.log_queue.clear()


# 전역 WebSocket 로그 핸들러 인스턴스
websocket_log_handler = WebSocketLogHandler()

def setup_websocket_logging(level: int = logging.INFO):
    """WebSocket 로그 핸들러를 설정"""
    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    websocket_log_handler.setFormatter(formatter)
    websocket_log_handler.setLevel(level)
    
    # 루트 로거에 핸들러 추가
    root_logger = logging.getLogger()
    root_logger.addHandler(websocket_log_handler)
    
    return websocket_log_handler

def get_websocket_log_handler() -> WebSocketLogHandler:
    """WebSocket 로그 핸들러 인스턴스 반환"""
    return websocket_log_handler