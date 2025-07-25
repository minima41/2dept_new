"""
V2 Investment Monitor - WebSocket connected 관리
실 hours 데이터 updating를 위한 WebSocket 서비스
"""
from fastapi import WebSocket
from typing import List, Dict, Set
import json
import asyncio
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """ items별 WebSocket connected 관리"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscriptions: Set[str] = set()  # 구독 중인 이벤트 타입
        
    async def send_message(self, message: Dict) -> bool:
        """메시지 전송"""
        try:
            await self.websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
            return True
        except Exception as e:
            logger.error(f"[ERROR] message 전송 failed ({self.client_id}): {e}")
            return False
    
    def update_ping(self):
        """핑  hours updating"""
        self.last_ping = datetime.now()
    
    def subscribe(self, event_type: str):
        """이벤트 타입 구독"""
        self.subscriptions.add(event_type)
    
    def unsubscribe(self, event_type: str):
        """이벤트 타입 구독 disconnected"""
        self.subscriptions.discard(event_type)
    
    def is_subscribed(self, event_type: str) -> bool:
        """특정 이벤트 타입 구독 여부 checking"""
        return event_type in self.subscriptions


class WebSocketManager:
    """WebSocket connected 관리자"""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionManager] = {}
        self.heartbeat_task: asyncio.Task = None
        
    async def connect(self, websocket: WebSocket) -> str:
        """새 WebSocket connected"""
        await websocket.accept()
        
        client_id = str(uuid.uuid4())
        connection = ConnectionManager(websocket, client_id)
        self.connections[client_id] = connection
        
        logger.info(f"[CONNECTION] WebSocket connected: {client_id} (총 {len(self.connections)} items)")
        
        # 하트비트 task이 없으면 starting
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        return client_id
    
    def disconnect(self, client_id: str):
        """WebSocket connected disconnected"""
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"[CONNECTION] WebSocket connected disconnected: {client_id} (총 {len(self.connections)} items)")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket) -> bool:
        """ items별 message 전송"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
            return True
        except Exception as e:
            logger.error(f"[ERROR]  items별 message 전송 failed: {e}")
            return False
    
    async def send_to_client(self, client_id: str, message: Dict) -> bool:
        """특정 클라이언트에게 message 전송"""
        if client_id in self.connections:
            return await self.connections[client_id].send_message(message)
        return False
    
    async def broadcast(self, message: Dict, event_type: str = None) -> int:
        """모든 connected된 클라이언트에게 message broadcast"""
        if not self.connections:
            return 0
        
        sent_count = 0
        failed_connections = []
        
        for client_id, connection in self.connections.items():
            # 이벤트 타입 구독 checking
            if event_type and not connection.is_subscribed(event_type):
                continue
                
            success = await connection.send_message(message)
            if success:
                sent_count += 1
            else:
                failed_connections.append(client_id)
        
        # failed한 connected 정리
        for client_id in failed_connections:
            self.disconnect(client_id)
        
        if sent_count > 0:
            logger.info(f"[BROADCAST] broadcast: {sent_count} items 클라이언트에게 전송")
        
        return sent_count
    
    async def broadcast_dart_update(self, disclosures: List[Dict]) -> int:
        """DART 공시 updating broadcast"""
        message = {
            "type": "dart_update",
            "data": disclosures,
            "count": len(disclosures),
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message, "dart")
    
    async def broadcast_stock_update(self, stocks: List[Dict]) -> int:
        """주식 가격 updating broadcast"""
        message = {
            "type": "stock_update", 
            "data": stocks,
            "count": len(stocks),
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message, "stock")
    
    async def broadcast_alert(self, alert_data: Dict) -> int:
        """알림 broadcast"""
        message = {
            "type": "alert",
            "data": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message, "alert")
    
    async def broadcast_system_status(self, status_data: Dict) -> int:
        """시스템 상태 broadcast"""
        message = {
            "type": "system_status",
            "data": status_data,
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message, "system")
    
    def get_connection_count(self) -> int:
        """현재 connected 수 querying"""
        return len(self.connections)
    
    def get_connection_info(self) -> List[Dict]:
        """연결 info querying"""
        return [
            {
                "client_id": client_id,
                "connected_at": connection.connected_at.isoformat(),
                "last_ping": connection.last_ping.isoformat(),
                "subscriptions": list(connection.subscriptions)
            }
            for client_id, connection in self.connections.items()
        ]
    
    async def handle_client_message(self, client_id: str, message: Dict):
        """클라이언트 message processing"""
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        msg_type = message.get("type")
        
        try:
            if msg_type == "ping":
                connection.update_ping()
                await connection.send_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif msg_type == "subscribe":
                # 이벤트 구독
                event_types = message.get("events", [])
                for event_type in event_types:
                    connection.subscribe(event_type)
                
                await connection.send_message({
                    "type": "subscribed",
                    "events": event_types
                })
                logger.info(f"[BROADCAST] 클라이언트 {client_id} 구독: {event_types}")
            
            elif msg_type == "unsubscribe":
                # 이벤트 구독 disconnected
                event_types = message.get("events", [])
                for event_type in event_types:
                    connection.unsubscribe(event_type)
                
                await connection.send_message({
                    "type": "unsubscribed", 
                    "events": event_types
                })
                logger.info(f"[BROADCAST] 클라이언트 {client_id} 구독 disconnected: {event_types}")
            
            elif msg_type == "get_status":
                # 현재 상태 요청
                await connection.send_message({
                    "type": "status_response",
                    "data": {
                        "client_id": client_id,
                        "connected_at": connection.connected_at.isoformat(),
                        "subscriptions": list(connection.subscriptions),
                        "total_connections": len(self.connections)
                    }
                })
                
        except Exception as e:
            logger.error(f"[ERROR] 클라이언트 message processing failed ({client_id}): {e}")
    
    async def heartbeat_loop(self):
        """하트비트 루프 (연결 상태 checking)"""
        while self.connections:
            try:
                await asyncio.sleep(30)  # 30 seconds마다 checking
                
                current_time = datetime.now()
                stale_connections = []
                
                # 5 minutes 이상 응답 없는 connected 찾기
                for client_id, connection in self.connections.items():
                    if (current_time - connection.last_ping).seconds > 300:  # 5 minutes
                        stale_connections.append(client_id)
                
                # 오래된 connected 정리
                for client_id in stale_connections:
                    logger.info(f"🧹 비활성 connected 제거: {client_id}")
                    self.disconnect(client_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ERROR] 하트비트 루프 error: {e}")
    
    async def cleanup(self):
        """정리 task"""
        # 모든 connected에 stopping message 전송
        if self.connections:
            await self.broadcast({
                "type": "server_shutdown",
                "message": "서버가 stopping됩니다."
            })
        
        # 하트비트 task stopped
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 모든 connected 정리
        self.connections.clear()
        logger.info("🧹 WebSocket 매니저 정리 completed")


# === 전역 WebSocket 매니저 ===
websocket_manager = WebSocketManager()


# === 유틸리티 함수 ===

async def notify_dart_update(disclosures: List[Dict]):
    """DART 공시 updating 알림"""
    return await websocket_manager.broadcast_dart_update(disclosures)

async def notify_stock_update(stocks: List[Dict]): 
    """주식 가격 updating 알림"""
    return await websocket_manager.broadcast_stock_update(stocks)

async def notify_alert(alert_type: str, message: str, data: Dict = None):
    """알림 전송"""
    alert_data = {
        "alert_type": alert_type,
        "message": message,
        "data": data or {}
    }
    return await websocket_manager.broadcast_alert(alert_data)

async def notify_system_status(status_data: Dict):
    """시스템 상태 알림"""
    return await websocket_manager.broadcast_system_status(status_data)