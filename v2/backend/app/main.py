"""
V2 Investment Monitor - FastAPI 메인 애플리케이션
투자본부 웹 애플리케이션 (DART + 주식 모니터링)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging
from typing import List, Dict
import json
from pathlib import Path

from app.core.config import settings
from app.core.database import init_database, close_database, check_database_health
from app.routers import dart_router, stock_router, notification_router, system_router
from app.services.dart_service import dart_service
from app.services.stock_service import stock_service
from app.services.websocket_service import WebSocketManager
from app.utils.logger import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# WebSocket 매니저
websocket_manager = WebSocketManager()

# 백그라운드 task 스케줄러
background_tasks = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # starting 시
    logger.info(f"{settings.app_name} v{settings.version} starting")
    
    # 데이터베이스  seconds기화
    await init_database()
    
    # 백그라운드 task starting
    await start_background_tasks()
    
    yield
    
    # stopping 시
    logger.info("Application shutting down...")
    
    # 백그라운드 task stopped
    await stop_background_tasks()
    
    # 데이터베이스 connected stopping
    await close_database()
    
    logger.info("Application shutdown complete")

# FastAPI 앱 creating
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="투자본부 DART 공시 및 주식 모니터링 시스템",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(dart_router.router, prefix="/api/dart", tags=["DART"])
app.include_router(stock_router.router, prefix="/api/stocks", tags=["Stock"])
app.include_router(notification_router.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(system_router.router, prefix="/api/system", tags=["System"])

# 정적 파일 서빙 ( items발용)
if settings.debug:
    static_path = Path(__file__).parent / "static"
    static_path.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# === 메인 엔드포인트 ===

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지"""
    return f"""
    <html>
        <head><title>{settings.app_name}</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>🏢 {settings.app_name}</h1>
            <p>투자본부 DART 공시 및 주식 모니터링 시스템 v{settings.version}</p>
            
            <h2>[DART] API 엔드포인트</h2>
            <ul>
                <li><a href="/docs">/docs</a> - API 문서 (Swagger)</li>
                <li><a href="/redoc">/redoc</a> - API 문서 (ReDoc)</li>
                <li><a href="/api/system/health">/api/system/health</a> - 헬스체크</li>
                <li><a href="/api/system/status">/api/system/status</a> - 시스템 상태</li>
            </ul>
            
            <h2>🔧  items발 info</h2>
            <ul>
                <li>Debug 모드: {"ON" if settings.debug else "OFF"}</li>
                <li>Database: {settings.database_url}</li>
                <li>DART API: {"Connected" if settings.dart_api_key else "Not configured"}</li>
            </ul>
            
            <h2>[WEB] WebSocket</h2>
            <p>실 hours updating를 위해 <code>ws://localhost:{settings.port}/ws</code>로 connected하세요.</p>
            
            <div style="margin-top: 30px; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                <p><strong>투자본부 내부 시스템</strong></p>
                <p>DART 공시 모니터링, 주식 가격 추적, 실 hours 알림 기능 제공</p>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "version": settings.version,
        "timestamp": asyncio.get_event_loop().time()
    }

# === WebSocket 엔드포인트 ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """실 hours updating를 위한 WebSocket"""
    client_id = await websocket_manager.connect(websocket)
    logger.info(f"[CONNECTION] WebSocket 클라이언트 connected: {client_id}")
    
    try:
        # connected checking message
        await websocket_manager.send_personal_message({
            "type": "connection",
            "message": "WebSocket connected success",
            "client_id": client_id
        }, websocket)
        
        #  seconds기 데이터 전송
        await send_initial_data(websocket)
        
        # message 수신 대기
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 클라이언트 message processing
            await handle_websocket_message(websocket, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"[CONNECTION] WebSocket 클라이언트 connected disconnected: {client_id}")
    except Exception as e:
        logger.error(f"[ERROR] WebSocket error: {e}")
        websocket_manager.disconnect(client_id)

async def send_initial_data(websocket: WebSocket):
    """새 클라이언트에게  seconds기 데이터 전송"""
    try:
        # DART 통계
        dart_stats = await dart_service.get_statistics()
        await websocket_manager.send_personal_message({
            "type": "dart_statistics", 
            "data": dart_stats
        }, websocket)
        
        # 주식 통계  
        stock_stats = await stock_service.get_statistics()
        await websocket_manager.send_personal_message({
            "type": "stock_statistics",
            "data": stock_stats
        }, websocket)
        
        # 모니터링 주식 목록
        stocks = await stock_service.get_monitoring_stocks()
        await websocket_manager.send_personal_message({
            "type": "stock_list",
            "data": stocks
        }, websocket)
        
    except Exception as e:
        logger.error(f"[ERROR]  seconds기 데이터 전송 failed: {e}")

async def handle_websocket_message(websocket: WebSocket, message: Dict):
    """클라이언트 message processing"""
    try:
        msg_type = message.get("type")
        
        if msg_type == "ping":
            await websocket_manager.send_personal_message({
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
        
        elif msg_type == "get_status":
            # 시스템 상태 요청
            db_health = await check_database_health()
            await websocket_manager.send_personal_message({
                "type": "system_status",
                "data": {
                    "database": db_health,
                    "dart_service": True,
                    "stock_service": True,
                    "connected_clients": websocket_manager.get_connection_count()
                }
            }, websocket)
            
    except Exception as e:
        logger.error(f"[ERROR] WebSocket message processing failed: {e}")

# === 백그라운드 task 관리 ===

async def start_background_tasks():
    """백그라운드 모니터링 task starting"""
    logger.info("Background tasks starting")
    
    # DART 모니터링 task
    background_tasks["dart_monitor"] = asyncio.create_task(dart_monitoring_task())
    
    # 주식 모니터링 task  
    background_tasks["stock_monitor"] = asyncio.create_task(stock_monitoring_task())
    
    # 시스템 상태 broadcast
    background_tasks["status_broadcast"] = asyncio.create_task(status_broadcast_task())

async def stop_background_tasks():
    """백그라운드 task stopped"""
    logger.info("Background tasks stopping")
    
    for task_name, task in background_tasks.items():
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"{task_name} task stopped")

async def dart_monitoring_task():
    """DART 공시 모니터링 백그라운드 task"""
    while True:
        try:
            logger.info("[DART] DART 공시 checking in progress...")
            new_disclosures = await dart_service.process_new_disclosures()
            
            if new_disclosures:
                # 새 공시가 있으면 WebSocket으로 broadcast
                await websocket_manager.broadcast({
                    "type": "dart_update",
                    "data": new_disclosures,
                    "count": len(new_disclosures)
                })
                logger.info(f"[NOTIFICATION] 새 공시 {len(new_disclosures)} records broadcast")
            
            await asyncio.sleep(settings.dart_check_interval)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[ERROR] DART 모니터링 error: {e}")
            await asyncio.sleep(60)  # error 시 1 minutes 대기

async def stock_monitoring_task():
    """주식 가격 모니터링 백그라운드 task"""
    while True:
        try:
            # 장  hours에만 실행
            if stock_service.is_market_open():
                logger.info("[STOCK] 주가 updating in progress...")
                result = await stock_service.update_all_prices()
                
                if result["updated_count"] > 0:
                    # updating된 주가 info broadcast
                    stocks = await stock_service.get_monitoring_stocks()
                    await websocket_manager.broadcast({
                        "type": "stock_update",
                        "data": stocks,
                        "updated_count": result["updated_count"],
                        "alert_count": result["alert_count"]
                    })
                
                await asyncio.sleep(settings.stock_update_interval)
            else:
                # 장 마감  hours에는 30 minutes 대기
                await asyncio.sleep(30 * 60)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[ERROR] 주식 모니터링 error: {e}")
            await asyncio.sleep(60)

async def status_broadcast_task():
    """시스템 상태 주기적 broadcast"""
    while True:
        try:
            # 5 minutes마다 시스템 상태 전송
            await asyncio.sleep(5 * 60)
            
            if websocket_manager.get_connection_count() > 0:
                db_health = await check_database_health()
                
                await websocket_manager.broadcast({
                    "type": "system_status",
                    "data": {
                        "database": db_health,
                        "dart_service": True,
                        "stock_service": True,
                        "connected_clients": websocket_manager.get_connection_count(),
                        "market_open": stock_service.is_market_open()
                    }
                })
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[ERROR] 상태 broadcast error: {e}")

# ===  items발용 실행 (python app/main.py) ===
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"[START] {settings.app_name}  items발 서버 starting")
    logger.info(f"[WEB] URL: http://{settings.host}:{settings.port}")
    logger.info(f"📖 API 문서: http://{settings.host}:{settings.port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info" if not settings.debug else "debug"
    )