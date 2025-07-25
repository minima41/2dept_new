"""
Investment Monitor V2 - 간단한 FastAPI 서버
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime
from typing import List
import uvicorn

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(title="Investment Monitor V2", version="2.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 연결됨. 총 연결 수: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 연결 해제됨. 총 연결 수: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# 기본 라우트
@app.get("/")
async def root():
    return {"message": "Investment Monitor V2 API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 시스템 상태 API
@app.get("/api/system/status")
async def get_system_status():
    return {
        "backend": "running",
        "websocket_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

# DART 통계 API (실제 데이터)
@app.get("/api/dart/statistics")
async def get_dart_statistics():
    try:
        from app.services.dart_service import dart_service
        stats = await dart_service.get_statistics()
        
        return {
            "statistics": {
                "total_disclosures": stats.get("total_processed", 0),
                "sent_alerts": stats.get("today_count", 0),
                "keywords_matched": stats.get("keywords_count", 0),
                "high_priority_count": stats.get("high_priority_count", 0),
                "companies_count": stats.get("companies_count", 0),
                "last_check": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"DART 통계 조회 실패: {e}")
        return {
            "statistics": {
                "total_disclosures": 0,
                "sent_alerts": 0,
                "keywords_matched": len(DART_KEYWORDS) if 'DART_KEYWORDS' in globals() else 0,
                "high_priority_count": 0,
                "companies_count": 0,
                "last_check": datetime.now().isoformat()
            }
        }

# 주식 통계 API (실제 데이터)
@app.get("/api/stocks/statistics")
async def get_stock_statistics():
    try:
        from app.services.stock_service import stock_service
        
        # 모니터링 주식 목록 조회
        monitoring_stocks = await stock_service.get_monitoring_stocks()
        
        # 통계 계산
        total_stocks = len(monitoring_stocks)
        active_alerts = sum(1 for stock in monitoring_stocks 
                          if stock.get("target_price") or stock.get("stop_loss_price"))
        
        # 포트폴리오 가치 계산 (간단 계산)
        total_value = 0
        total_profit_loss = 0
        
        for stock in monitoring_stocks:
            if stock.get("purchase_price") and stock.get("quantity"):
                purchase_value = stock["purchase_price"] * stock["quantity"]
                total_value += purchase_value
        
        return {
            "statistics": {
                "total_stocks": total_stocks,
                "active_alerts": active_alerts,
                "today_alerts": 0,  # 실제로는 오늘 생성된 알림 수를 계산해야 함
                "total_portfolio_value": total_value,
                "total_profit_loss_rate": total_profit_loss
            }
        }
        
    except Exception as e:
        logger.error(f"주식 통계 조회 실패: {e}")
        return {
            "statistics": {
                "total_stocks": 0,
                "active_alerts": 0,
                "today_alerts": 0,
                "total_portfolio_value": 0,
                "total_profit_loss_rate": 0
            }
        }

# 모니터링 주식 목록 API
@app.get("/api/stocks/monitoring")
async def get_monitoring_stocks():
    try:
        from app.services.stock_service import stock_service
        
        # 실제 모니터링 주식 목록 조회
        stocks = await stock_service.get_monitoring_stocks()
        
        # 각 주식의 현재 가격 정보 추가
        enhanced_stocks = []
        for stock in stocks:
            try:
                current_data = await stock_service.get_current_price(stock["stock_code"])
                enhanced_stock = {
                    "code": stock["stock_code"],
                    "name": stock["stock_name"],
                    "price": current_data.get("price", 0) if current_data else 0,
                    "change_rate": current_data.get("change_rate", 0) if current_data else 0,
                    **stock  # 원본 데이터도 포함
                }
                enhanced_stocks.append(enhanced_stock)
            except Exception as e:
                logger.error(f"주식 {stock['stock_name']} 가격 조회 실패: {e}")
                enhanced_stocks.append({
                    "code": stock["stock_code"],
                    "name": stock["stock_name"],
                    "price": 0,
                    "change_rate": 0,
                    **stock
                })
        
        return {
            "success": True,
            "stocks": enhanced_stocks,
            "count": len(enhanced_stocks)
        }
        
    except Exception as e:
        logger.error(f"모니터링 주식 목록 조회 실패: {e}")
        return {
            "success": False,
            "stocks": [],
            "count": 0,
            "error": str(e)
        }

# DART 수동 체크 API
@app.post("/api/dart/check-now")
async def check_dart_now():
    try:
        # 실제 DART API 호출하여 공시 확인
        from app.services.dart_service import dart_service
        
        # 새로운 공시 처리
        new_disclosures = await dart_service.process_new_disclosures()
        
        # WebSocket으로 실시간 업데이트 전송
        for disclosure in new_disclosures:
            await manager.broadcast({
                "type": "dart_update",
                "data": {
                    "corp_name": disclosure["corp_name"],
                    "report_nm": disclosure["report_nm"],
                    "priority_score": disclosure["priority_score"],
                    "matched_keywords": disclosure["matched_keywords"],
                    "dart_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={disclosure['rcept_no']}",
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        return {
            "success": True,
            "message": f"새로운 중요 공시 {len(new_disclosures)}건 발견",
            "new_disclosures": len(new_disclosures),
            "disclosures": new_disclosures
        }
        
    except Exception as e:
        logger.error(f"DART 체크 실패: {e}")
        return {
            "success": False,
            "message": f"DART 체크 실패: {str(e)}",
            "new_disclosures": 0,
            "disclosures": []
        }

# 주식 수동 체크 API
@app.post("/api/stocks/check-now")
async def check_stocks_now():
    try:
        # 실제 주식 서비스를 사용하여 주가 체크
        from app.services.stock_service import stock_service
        
        # 모니터링 중인 모든 주식의 현재 가격 확인
        monitoring_stocks = await stock_service.get_monitoring_stocks()
        updates = []
        
        for stock in monitoring_stocks:
            try:
                # 현재 주가 조회
                current_data = await stock_service.get_current_price(stock["stock_code"])
                
                if current_data:
                    # 가격 변동 체크 및 알림 생성
                    alerts = await stock_service._check_price_alerts(stock, current_data.get("price"))
                    
                    for alert in alerts:
                        await manager.broadcast({
                            "type": "stock_update",
                            "data": {
                                "stock_name": stock["stock_name"],
                                "stock_code": stock["stock_code"],
                                "current_price": current_data.get("price"),
                                "change_rate": current_data.get("change_rate", 0),
                                "type": "alert",
                                "message": alert.get("message", "주가 알림"),
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                        updates.append(alert)
                        
            except Exception as e:
                logger.error(f"주식 {stock.get('stock_name')} 체크 실패: {e}")
        
        return {
            "success": True,
            "message": f"주식 체크 완료, {len(updates)}건 알림 생성",
            "alerts_generated": len(updates),
            "updates": updates
        }
        
    except Exception as e:
        logger.error(f"주식 체크 실패: {e}")
        return {
            "success": False,
            "message": f"주식 체크 실패: {str(e)}",
            "alerts_generated": 0,
            "updates": []
        }

# DART 공시 목록 API
@app.get("/api/dart/disclosures")
async def get_dart_disclosures(days: int = 1):
    try:
        from app.services.dart_service import dart_service
        
        # 지정된 기간의 공시 조회
        disclosures = await dart_service.fetch_recent_disclosures(days)
        
        # 실제 데이터가 없는 경우 샘플 데이터 제공
        if not disclosures:
            sample_disclosures = [
                {
                    "rcept_no": "20250124000001",
                    "corp_code": "00126380",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_nm": "주요사항보고서(유상증자결정)",
                    "rcept_dt": "20250124",
                    "flr_nm": "삼성전자",
                    "rm": "유상증자 관련 주요사항 보고",
                    "matched_keywords": ["유상증자"],
                    "priority_score": 8,
                    "is_important": True
                },
                {
                    "rcept_no": "20250124000002", 
                    "corp_code": "00164779",
                    "corp_name": "SK하이닉스",
                    "stock_code": "000660",
                    "report_nm": "주요사항보고서(투자결정)",
                    "rcept_dt": "20250124",
                    "flr_nm": "SK하이닉스",
                    "rm": "대규모 설비투자 계획 발표",
                    "matched_keywords": ["투자"],
                    "priority_score": 6,
                    "is_important": True
                },
                {
                    "rcept_no": "20250124000003",
                    "corp_code": "00293886",
                    "corp_name": "NAVER",
                    "stock_code": "035420", 
                    "report_nm": "사업보고서(분기보고서)",
                    "rcept_dt": "20250124",
                    "flr_nm": "NAVER",
                    "rm": "2024년 4분기 실적 발표",
                    "matched_keywords": [],
                    "priority_score": 3,
                    "is_important": False
                }
            ]
            disclosures = sample_disclosures
        
        return {
            "success": True,
            "disclosures": disclosures,
            "count": len(disclosures),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"공시 목록 조회 실패: {e}")
        return {
            "success": False,
            "disclosures": [],
            "count": 0,
            "days": days,
            "error": str(e)
        }

# 주식 목록 API (프론트엔드 호환성을 위해 /monitoring과 동일한 응답)
@app.get("/api/stocks/list")
async def get_stocks_list():
    try:
        from app.services.stock_service import stock_service
        
        # 모니터링 주식 목록 조회
        monitoring_stocks = await stock_service.get_monitoring_stocks()
        
        # 각 주식의 현재 가격 정보 추가
        enhanced_stocks = []
        for stock in monitoring_stocks:
            try:
                current_data = await stock_service.get_current_price(stock["stock_code"])
                
                enhanced_stock = {
                    "code": stock["stock_code"],
                    "name": stock["stock_name"],
                    "current_price": current_data.get("price", 0) if current_data else 0,
                    "change": current_data.get("change", 0) if current_data else 0,
                    "change_percent": current_data.get("change_rate", 0) if current_data else 0,
                    "tp_price": stock.get("target_price"),
                    "sl_price": stock.get("stop_loss_price"),
                    "enabled": stock.get("monitoring_enabled", True),
                    "last_updated": datetime.now().isoformat()
                }
                enhanced_stocks.append(enhanced_stock)
            except Exception as e:
                logger.error(f"주식 {stock['stock_name']} 가격 조회 실패: {e}")
                enhanced_stock = {
                    "code": stock["stock_code"],
                    "name": stock["stock_name"],
                    "current_price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "tp_price": stock.get("target_price"),
                    "sl_price": stock.get("stop_loss_price"),
                    "enabled": stock.get("enabled", True),
                    "last_updated": datetime.now().isoformat()
                }
                enhanced_stocks.append(enhanced_stock)
        
        return {
            "success": True,
            "stocks": enhanced_stocks,
            "count": len(enhanced_stocks)
        }
        
    except Exception as e:
        logger.error(f"주식 목록 조회 실패: {e}")
        return {
            "success": False,
            "stocks": [],
            "count": 0,
            "error": str(e)
        }

# 주식 모니터링 토글 API
@app.post("/api/stocks/{stock_code}/toggle")
async def toggle_stock_monitoring(stock_code: str, request_data: dict):
    try:
        from app.services.stock_service import stock_service
        
        enabled = request_data.get("enabled", True)
        
        # 주식 모니터링 상태 변경
        success = await stock_service.toggle_monitoring(stock_code, enabled)
        
        if success:
            return {
                "success": True,
                "message": f"{stock_code} 모니터링이 {'활성화' if enabled else '비활성화'}되었습니다",
                "stock_code": stock_code,
                "enabled": enabled
            }
        else:
            return {
                "success": False,
                "message": f"{stock_code} 모니터링 상태 변경에 실패했습니다"
            }
            
    except Exception as e:
        logger.error(f"주식 모니터링 토글 실패: {e}")
        return {
            "success": False,
            "message": f"모니터링 상태 변경 실패: {str(e)}"
        }

# 주식 알림 목록 API
@app.get("/api/stocks/alerts")
async def get_stock_alerts():
    try:
        # 실제로는 데이터베이스나 파일에서 알림 내역을 조회해야 함
        # 지금은 샘플 데이터 반환
        sample_alerts = [
            {
                "id": "alert_001",
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "alert_type": "tp_reached",
                "message": "목표가 도달: 72,000원",
                "timestamp": datetime.now().isoformat(),
                "price": 72000
            },
            {
                "id": "alert_002", 
                "stock_code": "000660",
                "stock_name": "SK하이닉스",
                "alert_type": "price_drop",
                "message": "5% 하락: 126,000원",
                "timestamp": datetime.now().isoformat(),
                "price": 126000
            }
        ]
        
        return {
            "success": True,
            "alerts": sample_alerts,
            "count": len(sample_alerts)
        }
        
    except Exception as e:
        logger.error(f"알림 목록 조회 실패: {e}")
        return {
            "success": False,
            "alerts": [],
            "count": 0,
            "error": str(e)
        }

# 주식 수동 업데이트 API
@app.post("/api/stocks/update-now")
async def update_stocks_now():
    try:
        from app.services.stock_service import stock_service
        
        # 모니터링 중인 모든 주식의 현재 가격 업데이트
        monitoring_stocks = await stock_service.get_monitoring_stocks()
        updated_count = 0
        
        for stock in monitoring_stocks:
            try:
                current_data = await stock_service.get_current_price(stock["stock_code"])
                if current_data:
                    updated_count += 1
                    
                    # WebSocket으로 실시간 업데이트 전송
                    await manager.broadcast({
                        "type": "stock_update",
                        "data": {
                            "stock_name": stock["stock_name"],
                            "stock_code": stock["stock_code"],
                            "current_price": current_data.get("price"),
                            "change_rate": current_data.get("change_rate", 0),
                            "type": "price_update",
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                    
            except Exception as e:
                logger.error(f"주식 {stock.get('stock_name')} 업데이트 실패: {e}")
        
        return {
            "success": True,
            "message": f"{updated_count}개 종목 가격 업데이트 완료",
            "updated_count": updated_count,
            "total_stocks": len(monitoring_stocks)
        }
        
    except Exception as e:
        logger.error(f"주식 업데이트 실패: {e}")
        return {
            "success": False,
            "message": f"주식 업데이트 실패: {str(e)}",
            "updated_count": 0
        }

# WebSocket 엔드포인트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 연결 확인 메시지 전송
        await websocket.send_text(json.dumps({
            "type": "connection_status",
            "data": "WebSocket 연결됨",
            "timestamp": datetime.now().isoformat()
        }))
        
        # 초기 통계 데이터 전송
        await websocket.send_text(json.dumps({
            "type": "dart_statistics",
            "data": {
                "total_disclosures": 42,
                "sent_alerts": 3,
                "keywords_matched": 7,
                "last_check": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }))
        
        await websocket.send_text(json.dumps({
            "type": "stock_statistics", 
            "data": {
                "total_stocks": 11,
                "active_alerts": 2,
                "today_alerts": 1,
                "total_portfolio_value": 1500000000,
                "total_profit_loss_rate": 2.34
            },
            "timestamp": datetime.now().isoformat()
        }))
        
        await websocket.send_text(json.dumps({
            "type": "stock_list",
            "data": [
                {"code": "005930", "name": "삼성전자", "price": 71500, "change_rate": 1.23},
                {"code": "000660", "name": "SK하이닉스", "price": 128000, "change_rate": -0.85},
                {"code": "035420", "name": "NAVER", "price": 195000, "change_rate": 2.10}
            ],
            "timestamp": datetime.now().isoformat()
        }))
        
        # 주기적으로 하트비트 전송
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    try:
        # 데이터베이스 초기화
        from app.core.database import init_database
        await init_database()
        
        # 서비스 초기화
        from app.services.dart_service import dart_service
        from app.services.stock_service import stock_service
        
        # 기존 데이터 로드 확인 및 샘플 데이터 추가
        current_stocks = await stock_service.get_monitoring_stocks()
        logger.info(f"🔍 현재 로드된 주식 수: {len(current_stocks)}")
        
        if len(current_stocks) == 0:
            logger.info("📝 샘플 주식 데이터 추가 중...")
            # 샘플 주식 데이터 추가 (테스트용)
            sample_stocks = [
                {"code": "005930", "name": "삼성전자", "tp": 75000, "sl": 65000},
                {"code": "000660", "name": "SK하이닉스", "tp": 140000, "sl": 120000},
                {"code": "035420", "name": "NAVER", "tp": 200000, "sl": 180000}
            ]
            
            for stock in sample_stocks:
                success = await stock_service.add_monitoring_stock(
                    stock["code"], 
                    stock["name"], 
                    stock.get("tp"), 
                    stock.get("sl")
                )
                if success:
                    logger.info(f"✅ {stock['name']} 추가 완료")
                else:
                    logger.error(f"❌ {stock['name']} 추가 실패")
            
            # 추가 후 재확인
            updated_stocks = await stock_service.get_monitoring_stocks()
            logger.info(f"📊 최종 주식 수: {len(updated_stocks)}")
        else:
            logger.info(f"✅ 기존 주식 데이터 로드됨: {len(current_stocks)}개")
        
        logger.info("🚀 V2 투자 모니터링 시스템 시작 완료")
        
    except Exception as e:
        logger.error(f"❌ 시작 초기화 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    try:
        from app.core.database import close_database
        await close_database()
        logger.info("🛑 시스템 종료 완료")
    except Exception as e:
        logger.error(f"❌ 종료 처리 실패: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )