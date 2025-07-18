from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.shared.database import init_db
from app.shared.websocket import websocket_manager, start_websocket_ping_task
from app.modules.dart.router import router as dart_router
from app.modules.dart.monitor import start_dart_monitoring, stop_dart_monitoring
from app.modules.stocks.router import router as stocks_router
from app.modules.stocks.monitor import start_stock_monitoring, stop_stock_monitoring

# 로깅 설정
import os
import pathlib

# 로그 디렉토리 생성
log_dir = pathlib.Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 이벤트"""
    # 시작 시
    logger.info("FastAPI 애플리케이션 시작")
    await init_db()
    
    # WebSocket ping 태스크 시작
    import asyncio
    ping_task = asyncio.create_task(start_websocket_ping_task())
    
    # DART 모니터링 시작
    await start_dart_monitoring()
    
    # 주가 모니터링 시작
    await start_stock_monitoring()
    
    yield
    
    # 종료 시
    ping_task.cancel()
    await stop_dart_monitoring()
    await stop_stock_monitoring()
    logger.info("FastAPI 애플리케이션 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="투자본부 모니터링 시스템",
    description="DART 공시 및 주가 모니터링 웹 애플리케이션",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.*.*:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """기본 엔드포인트"""
    return {"message": "투자본부 모니터링 시스템 API"}


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "version": "1.0.0"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결 엔드포인트"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신 (연결 유지용)
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# 라우터 등록
app.include_router(dart_router, prefix="/api/dart", tags=["dart"])
app.include_router(stocks_router, prefix="/api/stocks", tags=["stocks"])
# app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )