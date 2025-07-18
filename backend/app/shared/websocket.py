from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime
import logging
from enum import Enum

from app.config import settings

logger = logging.getLogger(__name__)


class WebSocketEventType(str, Enum):
    """WebSocket 이벤트 타입"""
    DART_UPDATE = "dart_update"
    STOCK_UPDATE = "stock_update"
    ALERT_TRIGGERED = "alert_triggered"
    SYSTEM_STATUS = "system_status"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"
    ERROR = "error"


class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> [connection_id]
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.max_connections = settings.MAX_WEBSOCKET_CONNECTIONS
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """WebSocket 연결 수락"""
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Maximum connections exceeded")
            raise Exception("Maximum WebSocket connections exceeded")
        
        await websocket.accept()
        
        # 고유한 연결 ID 생성
        connection_id = f"conn_{len(self.active_connections)}_{datetime.now().timestamp()}"
        
        # 연결 저장
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }
        
        # 사용자별 연결 목록 업데이트
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(connection_id)
        
        logger.info(f"WebSocket 연결 수락: {connection_id} (사용자: {user_id})")
        
        # 연결 성공 메시지 전송
        await self.send_to_connection(connection_id, {
            "type": WebSocketEventType.USER_CONNECTED,
            "data": {
                "connection_id": connection_id,
                "connected_at": datetime.now().isoformat(),
                "message": "WebSocket 연결이 성공적으로 설정되었습니다."
            }
        })
        
        return connection_id
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        connection_id = None
        
        # 연결 ID 찾기
        for conn_id, conn in self.active_connections.items():
            if conn == websocket:
                connection_id = conn_id
                break
        
        if connection_id:
            # 연결 정보 가져오기
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            
            # 연결 제거
            self.active_connections.pop(connection_id, None)
            self.connection_metadata.pop(connection_id, None)
            
            # 사용자별 연결 목록에서 제거
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id] = [
                    conn_id for conn_id in self.user_connections[user_id] 
                    if conn_id != connection_id
                ]
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            logger.info(f"WebSocket 연결 해제: {connection_id} (사용자: {user_id})")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """특정 연결에 메시지 전송"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"메시지 전송 실패 ({connection_id}): {e}")
                # 연결이 끊어진 경우 정리
                self.disconnect(self.active_connections[connection_id])
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """특정 사용자의 모든 연결에 메시지 전송"""
        if user_id in self.user_connections:
            connection_ids = self.user_connections[user_id].copy()
            for connection_id in connection_ids:
                await self.send_to_connection(connection_id, message)
    
    async def broadcast(self, message: Dict[str, Any], exclude_connections: Optional[List[str]] = None):
        """모든 연결에 메시지 브로드캐스트"""
        exclude_connections = exclude_connections or []
        
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            if connection_id not in exclude_connections:
                await self.send_to_connection(connection_id, message)
    
    async def send_dart_update(self, disclosure_data: Dict[str, Any]):
        """DART 공시 업데이트 브로드캐스트"""
        message = {
            "type": WebSocketEventType.DART_UPDATE,
            "data": disclosure_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        logger.info(f"DART 업데이트 브로드캐스트: {disclosure_data.get('corp_name', 'Unknown')}")
    
    async def send_stock_update(self, stock_data: Dict[str, Any]):
        """주가 업데이트 브로드캐스트"""
        message = {
            "type": WebSocketEventType.STOCK_UPDATE,
            "data": stock_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_alert(self, alert_data: Dict[str, Any], user_id: Optional[str] = None):
        """알림 전송"""
        message = {
            "type": WebSocketEventType.ALERT_TRIGGERED,
            "data": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_id:
            await self.send_to_user(user_id, message)
        else:
            await self.broadcast(message)
        
        logger.info(f"알림 전송: {alert_data.get('title', 'Unknown')} (사용자: {user_id or 'All'})")
    
    async def send_system_status(self, status_data: Dict[str, Any]):
        """시스템 상태 업데이트 브로드캐스트"""
        message = {
            "type": WebSocketEventType.SYSTEM_STATUS,
            "data": status_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        logger.info(f"시스템 상태 업데이트: {status_data.get('status', 'Unknown')}")
    
    async def send_error(self, error_message: str, connection_id: Optional[str] = None):
        """에러 메시지 전송"""
        message = {
            "type": WebSocketEventType.ERROR,
            "data": {
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if connection_id:
            await self.send_to_connection(connection_id, message)
        else:
            await self.broadcast(message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계 정보 조회"""
        return {
            "total_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "connected_users": len(self.user_connections),
            "connections_per_user": {
                user_id: len(connections) 
                for user_id, connections in self.user_connections.items()
            }
        }
    
    async def ping_all_connections(self):
        """모든 연결에 ping 메시지 전송 (연결 상태 확인)"""
        message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            try:
                await self.send_to_connection(connection_id, message)
                # 마지막 ping 시간 업데이트
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_ping"] = datetime.now()
            except Exception as e:
                logger.error(f"Ping 전송 실패 ({connection_id}): {e}")
    
    async def cleanup_dead_connections(self):
        """죽은 연결 정리"""
        current_time = datetime.now()
        dead_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            last_ping = metadata.get("last_ping", metadata.get("connected_at"))
            if (current_time - last_ping).total_seconds() > 300:  # 5분 이상 응답 없음
                dead_connections.append(connection_id)
        
        for connection_id in dead_connections:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                self.disconnect(websocket)
                logger.info(f"죽은 연결 정리: {connection_id}")


# 전역 WebSocket 매니저 인스턴스
websocket_manager = WebSocketManager()


async def start_websocket_ping_task():
    """WebSocket 연결 상태 확인 백그라운드 태스크"""
    while True:
        try:
            await websocket_manager.ping_all_connections()
            await websocket_manager.cleanup_dead_connections()
            await asyncio.sleep(60)  # 1분마다 ping
        except Exception as e:
            logger.error(f"WebSocket ping 태스크 오류: {e}")
            await asyncio.sleep(60)