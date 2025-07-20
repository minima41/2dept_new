from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.shared.database import init_db
from app.shared.websocket import websocket_manager, start_websocket_ping_task
from app.shared.websocket_log_handler import setup_websocket_logging, get_websocket_log_handler
from app.modules.dart.router import router as dart_router
from app.modules.dart.monitor import start_dart_monitoring, stop_dart_monitoring
from app.modules.stocks.router import router as stocks_router
from app.modules.stocks.monitor import start_stock_monitoring, stop_stock_monitoring

# 통합 로깅 시스템 사용
from app.utils.logger import app_logger as logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 이벤트"""
    # 시작 시
    logger.info("FastAPI 애플리케이션 시작")
    
    # WebSocket 로그 핸들러 설정
    setup_websocket_logging(level=logging.INFO)
    logger.info("WebSocket 로그 스트리밍 설정 완료")
    
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


@app.get("/api/logs/recent")
async def get_recent_logs(count: int = 100):
    """최근 로그 메시지들을 조회"""
    log_handler = get_websocket_log_handler()
    logs = log_handler.get_recent_logs(count)
    return {"logs": logs, "count": len(logs)}


@app.post("/api/logs/clear")
async def clear_logs():
    """저장된 로그 메시지들을 클리어"""
    log_handler = get_websocket_log_handler()
    log_handler.clear_logs()
    logger.info("로그 메시지가 클리어되었습니다")
    return {"message": "로그가 클리어되었습니다"}


@app.post("/api/logs/test")
async def test_log_message(level: str = "info", message: str = "테스트 로그 메시지"):
    """테스트용 로그 메시지 생성"""
    level = level.upper()
    if level == "DEBUG":
        logger.debug(message)
    elif level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    else:
        logger.info(message)
    
    return {"message": f"{level} 레벨 로그가 생성되었습니다: {message}"}


@app.post("/api/email/test-daily-summary")
async def test_daily_summary_email():
    """테스트용 일일 마감 요약 이메일 발송"""
    try:
        from app.modules.stocks.service import stock_service
        from app.shared.email import send_daily_summary_email
        
        # 현재 모니터링 데이터 및 통계 수집
        monitoring_data = stock_service.get_monitoring_data()
        statistics = stock_service.get_statistics()
        
        # 이메일 데이터 구성
        email_data = {
            "stocks": monitoring_data.stocks,
            "statistics": statistics
        }
        
        # 이메일 발송
        success = await send_daily_summary_email(email_data)
        
        if success:
            logger.info("테스트 일일 마감 요약 이메일 발송 성공")
            return {"message": "일일 마감 요약 이메일이 성공적으로 발송되었습니다.", "success": True}
        else:
            logger.error("테스트 일일 마감 요약 이메일 발송 실패")
            return {"message": "일일 마감 요약 이메일 발송에 실패했습니다.", "success": False}
            
    except Exception as e:
        logger.error(f"테스트 일일 마감 요약 이메일 오류: {e}")
        return {"message": f"오류가 발생했습니다: {e}", "success": False}


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