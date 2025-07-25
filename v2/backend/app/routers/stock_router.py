"""
V2 Investment Monitor - 주식 모니터링 API 라우터
주식 가격 모니터링 관련 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
import logging

from ..services.stock_service import stock_service
from ..models.stock_models import (
    StockAddRequest, StockUpdateRequest, StockResponse, 
    StockPriceResponse, StockAlertResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

# === 모니터링 주식 관리 ===

@router.get("/monitoring")
async def get_monitoring_stocks():
    """모니터링 중인 주식 목록 querying"""
    try:
        stocks = await stock_service.get_monitoring_stocks()
        
        # 프론트엔드 호환성을 위해 각 주식에 필요한 필드 추가
        enhanced_stocks = []
        for stock in stocks:
            try:
                # 현재가 querying 시도
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
                    "last_updated": stock.get("last_updated"),
                    **stock  # 원본 데이터도 포함
                }
                enhanced_stocks.append(enhanced_stock)
            except Exception as e:
                logger.warning(f"주가 querying failed ({stock['stock_name']}): {e}")
                # 주가 querying failed해도 기본 info는 반환
                enhanced_stock = {
                    "code": stock["stock_code"],
                    "name": stock["stock_name"],
                    "current_price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "tp_price": stock.get("target_price"),
                    "sl_price": stock.get("stop_loss_price"),
                    "enabled": stock.get("monitoring_enabled", True),
                    "last_updated": stock.get("last_updated"),
                    **stock
                }
                enhanced_stocks.append(enhanced_stock)
        
        return {
            "success": True,
            "stocks": enhanced_stocks,
            "count": len(enhanced_stocks)
        }
    except Exception as e:
        logger.error(f"[ERROR] 모니터링 주식 querying failed: {e}")
        return {
            "success": False,
            "stocks": [],
            "count": 0,
            "error": str(e)
        }

@router.post("/monitoring", response_model=Dict[str, Any])
async def add_monitoring_stock(stock_request: StockAddRequest):
    """모니터링 주식 추가"""
    try:
        success = await stock_service.add_monitoring_stock(
            stock_code=stock_request.stock_code,
            stock_name=stock_request.stock_name,
            target_price=stock_request.target_price,
            stop_loss_price=stock_request.stop_loss_price
        )
        
        if success:
            return {
                "success": True,
                "message": f"{stock_request.stock_name} ({stock_request.stock_code}) 모니터링 추가 completed",
                "stock_code": stock_request.stock_code
            }
        else:
            raise HTTPException(status_code=500, detail="주식 추가 failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 주식 추가 failed: {e}")
        raise HTTPException(status_code=500, detail="주식 추가 중 error가 발생했습니다.")

@router.post("/add", response_model=Dict[str, Any])
async def add_stock_alias(stock_request: StockAddRequest):
    """모니터링 주식 추가 (별칭 엔드포인트)"""
    return await add_monitoring_stock(stock_request)

@router.put("/monitoring/{stock_code}")
async def update_monitoring_stock(stock_code: str, stock_update: StockUpdateRequest):
    """모니터링 주식 설정 updating"""
    try:
        # 기존 주식 checking
        stocks = await stock_service.get_monitoring_stocks()
        stock_info = next((s for s in stocks if s["stock_code"] == stock_code), None)
        
        if not stock_info:
            raise HTTPException(status_code=404, detail="해당 주식을 찾을 수 없습니다.")
        
        # 설정 updating
        if hasattr(stock_update, 'target_price') and stock_update.target_price is not None:
            stock_info["target_price"] = stock_update.target_price
        if hasattr(stock_update, 'stop_loss_price') and stock_update.stop_loss_price is not None:
            stock_info["stop_loss_price"] = stock_update.stop_loss_price
        if hasattr(stock_update, 'monitoring_enabled') and stock_update.monitoring_enabled is not None:
            stock_info["monitoring_enabled"] = stock_update.monitoring_enabled
        
        # 저장
        stock_service.monitoring_stocks[stock_code] = stock_info
        stock_service._save_monitoring_stocks()
        
        # DB updating
        await stock_service._save_stock_to_db(stock_info)
        
        return {
            "success": True,
            "message": f"{stock_info['stock_name']} 설정 updating completed",
            "stock_info": stock_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 주식 설정 updating failed ({stock_code}): {e}")
        raise HTTPException(status_code=500, detail="주식 설정 updating 중 error가 발생했습니다.")

@router.delete("/monitoring/{stock_code}")
async def remove_monitoring_stock(stock_code: str):
    """모니터링 주식 제거"""
    try:
        success = await stock_service.remove_monitoring_stock(stock_code)
        
        if success:
            return {
                "success": True,
                "message": f"주식 {stock_code} 모니터링 disconnected completed"
            }
        else:
            raise HTTPException(status_code=404, detail="해당 주식을 찾을 수 없습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 주식 제거 failed ({stock_code}): {e}")
        raise HTTPException(status_code=500, detail="주식 제거 중 error가 발생했습니다.")

# === 주식 가격 querying ===

@router.get("/price/{stock_code}", response_model=StockPriceResponse)
async def get_stock_price(stock_code: str):
    """특정 주식 현재가 querying"""
    try:
        price_data = await stock_service.get_stock_price(stock_code)
        
        if not price_data:
            raise HTTPException(status_code=404, detail="주식 가격 info를 찾을 수 없습니다.")
        
        return {
            "stock_code": stock_code,
            **price_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 주가 querying failed ({stock_code}): {e}")
        raise HTTPException(status_code=500, detail="주가 querying 중 error가 발생했습니다.")

@router.get("/prices")
async def get_all_stock_prices():
    """모니터링 중인 모든 주식 가격 querying"""
    try:
        stocks = await stock_service.get_monitoring_stocks()
        prices = []
        
        for stock in stocks:
            if stock.get("monitoring_enabled", True):
                stock_code = stock["stock_code"]
                price_data = await stock_service.get_stock_price(stock_code)
                
                if price_data:
                    prices.append({
                        "stock_code": stock_code,
                        "stock_name": stock["stock_name"],
                        **price_data
                    })
        
        return {
            "prices": prices,
            "count": len(prices),
            "timestamp": price_data.get("updated_at") if price_data else None
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 전체 주가 querying failed: {e}")
        raise HTTPException(status_code=500, detail="주가 querying 중 error가 발생했습니다.")

# === 주식 모니터링 updating ===

@router.post("/update-prices")
async def manual_price_update():
    """수동 주가 updating"""
    try:
        logger.info("[PROCESS] 수동 주가 updating starting")
        result = await stock_service.update_all_prices()
        
        return {
            "success": True,
            "message": f"주가 updating completed - {result['updated_count']} items 종목, {result['alert_count']} items 알림",
            **result
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 수동 주가 updating failed: {e}")
        raise HTTPException(status_code=500, detail="주가 updating 중 error가 발생했습니다.")

@router.post("/update-now")
async def manual_price_update_alias():
    """수동 주가 업데이트 (별칭 엔드포인트)"""
    return await manual_price_update()

@router.post("/{stock_code}/toggle")
async def toggle_stock_monitoring(stock_code: str, toggle_data: dict):
    """주식 모니터링 토글"""
    try:
        from ..models.stock_models import StockUpdateRequest
        
        enabled = toggle_data.get("enabled", True)
        update_request = StockUpdateRequest(monitoring_enabled=enabled)
        
        return await update_monitoring_stock(stock_code, update_request)
        
    except Exception as e:
        logger.error(f"[ERROR] 주식 모니터링 토글 failed ({stock_code}): {e}")
        raise HTTPException(status_code=500, detail="모니터링 토글 중 error가 발생했습니다.")

# === 통계 및 상태 ===

@router.get("/statistics")
async def get_stock_statistics():
    """주식 모니터링 통계"""
    try:
        stats = await stock_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"[ERROR] 주식 통계 querying failed: {e}")
        raise HTTPException(status_code=500, detail="통계 querying 중 error가 발생했습니다.")

@router.get("/status")
async def get_stock_monitoring_status():
    """주식 모니터링 상태"""
    try:
        stats = await stock_service.get_statistics()
        
        return {
            "service_active": True,
            "market_open": stock_service.is_market_open(),
            "total_stocks": stats["total_stocks"],
            "enabled_stocks": stats["enabled_stocks"],
            "stocks_with_alerts": stats["stocks_with_alerts"],
            "last_update": stats["last_update"],
            "pykrx_available": stock_service.is_pykrx_available(),
            "market_hours": f"{stock_service.market_open.strftime('%H:%M')} - {stock_service.market_close.strftime('%H:%M')}"
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 주식 모니터링 상태 querying failed: {e}")
        raise HTTPException(status_code=500, detail="상태 querying 중 error가 발생했습니다.")

# === 알림 관련 ===

@router.get("/alerts")
async def get_recent_stock_alerts(
    limit: int = Query(20, ge=1, le=100, description="조회할 알림  items수"),
    days: int = Query(7, ge=1, le=30, description="조회 기간")
):
    """최근 주식 가격 알림 querying"""
    try:
        from ..core.database import database
        
        query = """
            SELECT * FROM notification_history
            WHERE notification_type = 'stock'
            AND created_at >= datetime('now', '-{} days')
            ORDER BY created_at DESC
            LIMIT :limit
        """.format(days)
        
        rows = await database.fetch_all(query, {"limit": limit})
        alerts = [dict(row) for row in rows]
        
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 주식 알림 querying failed: {e}")
        raise HTTPException(status_code=500, detail="알림 querying 중 error가 발생했습니다.")

# === 주식 검색 ===

@router.get("/search")
async def search_stock_info(
    query: str = Query(..., description="주식명 또는 종목코드"),
    exact_match: bool = Query(False, description="정확히 일치하는 결과만")
):
    """주식 info 검색 (모니터링 목록에서)"""
    try:
        stocks = await stock_service.get_monitoring_stocks()
        results = []
        
        query_lower = query.lower()
        
        for stock in stocks:
            stock_name = stock.get("stock_name", "").lower()
            stock_code = stock.get("stock_code", "").lower()
            
            if exact_match:
                if query_lower == stock_name or query_lower == stock_code:
                    results.append(stock)
            else:
                if query_lower in stock_name or query_lower in stock_code:
                    results.append(stock)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 주식 검색 failed: {e}")
        raise HTTPException(status_code=500, detail="주식 검색 중 error가 발생했습니다.")

# === 배치 task ===

@router.post("/monitoring/batch-add")
async def batch_add_monitoring_stocks(stocks: List[StockAddRequest]):
    """여러 주식 일괄 추가"""
    try:
        results = []
        success_count = 0
        
        for stock_request in stocks:
            try:
                success = await stock_service.add_monitoring_stock(
                    stock_code=stock_request.stock_code,
                    stock_name=stock_request.stock_name,
                    target_price=stock_request.target_price,
                    stop_loss_price=stock_request.stop_loss_price
                )
                
                if success:
                    success_count += 1
                    results.append({
                        "stock_code": stock_request.stock_code,
                        "success": True,
                        "message": "추가 completed"
                    })
                else:
                    results.append({
                        "stock_code": stock_request.stock_code,
                        "success": False,
                        "message": "추가 failed"
                    })
                    
            except Exception as e:
                results.append({
                    "stock_code": stock_request.stock_code,
                    "success": False,
                    "message": str(e)
                })
        
        return {
            "success": success_count > 0,
            "message": f"총 {len(stocks)} items 중 {success_count} items success",
            "success_count": success_count,
            "total_count": len(stocks),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 일괄 주식 추가 failed: {e}")
        raise HTTPException(status_code=500, detail="일괄 추가 중 error가 발생했습니다.")

@router.delete("/monitoring/batch-remove")
async def batch_remove_monitoring_stocks(stock_codes: List[str]):
    """여러 주식 일괄 제거"""
    try:
        results = []
        success_count = 0
        
        for stock_code in stock_codes:
            try:
                success = await stock_service.remove_monitoring_stock(stock_code)
                
                if success:
                    success_count += 1
                    results.append({
                        "stock_code": stock_code,
                        "success": True,
                        "message": "제거 completed"
                    })
                else:
                    results.append({
                        "stock_code": stock_code,
                        "success": False,
                        "message": "해당 주식을 찾을 수 없음"
                    })
                    
            except Exception as e:
                results.append({
                    "stock_code": stock_code,
                    "success": False,
                    "message": str(e)
                })
        
        return {
            "success": success_count > 0,
            "message": f"총 {len(stock_codes)} items 중 {success_count} items success",
            "success_count": success_count,
            "total_count": len(stock_codes),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 일괄 주식 제거 failed: {e}")
        raise HTTPException(status_code=500, detail="일괄 제거 중 error가 발생했습니다.")