from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.modules.stocks.models import (
    StockData, StockDataResponse, StockListResponse, MonitoringStock,
    MonitoringStockResponse, StockAlertResponse, StockStatisticsResponse,
    StockSettingsResponse, StockSearchResponse, MarketInfoResponse,
    AddStockRequest, UpdateStockRequest, AlertSettingsRequest,
    StockPriceRequest, StockMonitoringSettings
)
from app.modules.stocks.service import stock_service
from app.shared.auth import get_current_user_optional
from app.shared.database import database

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/prices/{code}", response_model=StockDataResponse)
async def get_stock_price(
    code: str = Path(..., description="종목코드"),
    current_user = Depends(get_current_user_optional)
):
    """개별 종목 주가 조회"""
    try:
        stock_data = await stock_service.get_stock_price(code)
        if not stock_data:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
        
        return StockDataResponse(stock=stock_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주가 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주가 조회에 실패했습니다.")


@router.post("/prices", response_model=StockListResponse)
async def get_multiple_stock_prices(
    request: StockPriceRequest,
    current_user = Depends(get_current_user_optional)
):
    """여러 종목 주가 조회"""
    try:
        if len(request.codes) > 50:
            raise HTTPException(status_code=400, detail="한번에 조회할 수 있는 종목은 최대 50개입니다.")
        
        stock_prices = await stock_service.get_multiple_stock_prices(request.codes)
        stocks = list(stock_prices.values())
        
        return StockListResponse(
            stocks=stocks,
            total_count=len(stocks),
            page=1,
            page_size=len(stocks),
            has_next=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"다중 주가 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주가 조회에 실패했습니다.")


@router.get("/monitoring", response_model=MonitoringStockResponse)
async def get_monitoring_stocks(
    current_user = Depends(get_current_user_optional)
):
    """모니터링 주식 목록 조회"""
    try:
        stocks = stock_service.get_monitoring_stocks()
        
        # 현재 주가 정보 포함
        for stock in stocks:
            if stock.current_price:
                stock.calculate_profit_loss()
        
        return MonitoringStockResponse(
            stocks=stocks,
            total_count=len(stocks)
        )
        
    except Exception as e:
        logger.error(f"모니터링 주식 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 주식 조회에 실패했습니다.")


@router.post("/monitoring", response_model=MonitoringStockResponse)
async def add_monitoring_stock(
    request: AddStockRequest,
    current_user = Depends(get_current_user_optional)
):
    """모니터링 주식 추가"""
    try:
        # 종목 존재 확인
        stock_data = await stock_service.get_stock_price(request.code)
        if not stock_data:
            raise HTTPException(status_code=404, detail="존재하지 않는 종목코드입니다.")
        
        # 이미 모니터링 중인지 확인
        existing_stock = stock_service.get_monitoring_stock(request.code)
        if existing_stock:
            raise HTTPException(status_code=400, detail="이미 모니터링 중인 종목입니다.")
        
        # 모니터링 주식 생성
        monitoring_stock = MonitoringStock(
            code=request.code,
            name=request.name or stock_data.name,
            purchase_price=request.purchase_price,
            quantity=request.quantity,
            take_profit=request.take_profit,
            stop_loss=request.stop_loss,
            daily_surge_threshold=request.daily_surge_threshold,
            daily_drop_threshold=request.daily_drop_threshold,
            alert_enabled=request.alert_enabled,
            current_price=stock_data.current_price,
            change_rate=stock_data.change_rate
        )
        
        monitoring_stock.calculate_profit_loss()
        
        # 추가
        success = await stock_service.add_monitoring_stock(monitoring_stock)
        if not success:
            raise HTTPException(status_code=500, detail="모니터링 주식 추가에 실패했습니다.")
        
        # 업데이트된 목록 반환
        stocks = stock_service.get_monitoring_stocks()
        return MonitoringStockResponse(
            stocks=stocks,
            total_count=len(stocks),
            message="모니터링 주식이 성공적으로 추가되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모니터링 주식 추가 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 주식 추가에 실패했습니다.")


@router.put("/monitoring/{code}", response_model=MonitoringStockResponse)
async def update_monitoring_stock(
    code: str = Path(..., description="종목코드"),
    request: UpdateStockRequest = ...,
    current_user = Depends(get_current_user_optional)
):
    """모니터링 주식 정보 업데이트"""
    try:
        # 기존 주식 조회
        existing_stock = stock_service.get_monitoring_stock(code)
        if not existing_stock:
            raise HTTPException(status_code=404, detail="모니터링 중인 종목을 찾을 수 없습니다.")
        
        # 업데이트할 필드만 변경
        if request.purchase_price is not None:
            existing_stock.purchase_price = request.purchase_price
        if request.quantity is not None:
            existing_stock.quantity = request.quantity
        if request.take_profit is not None:
            existing_stock.take_profit = request.take_profit
        if request.stop_loss is not None:
            existing_stock.stop_loss = request.stop_loss
        if request.daily_surge_threshold is not None:
            existing_stock.daily_surge_threshold = request.daily_surge_threshold
        if request.daily_drop_threshold is not None:
            existing_stock.daily_drop_threshold = request.daily_drop_threshold
        if request.alert_enabled is not None:
            existing_stock.alert_enabled = request.alert_enabled
        
        existing_stock.last_updated = datetime.now()
        existing_stock.calculate_profit_loss()
        
        # 업데이트
        success = await stock_service.update_monitoring_stock(existing_stock)
        if not success:
            raise HTTPException(status_code=500, detail="모니터링 주식 업데이트에 실패했습니다.")
        
        # 업데이트된 목록 반환
        stocks = stock_service.get_monitoring_stocks()
        return MonitoringStockResponse(
            stocks=stocks,
            total_count=len(stocks),
            message="모니터링 주식이 성공적으로 업데이트되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모니터링 주식 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 주식 업데이트에 실패했습니다.")


@router.delete("/monitoring/{code}")
async def remove_monitoring_stock(
    code: str = Path(..., description="종목코드"),
    current_user = Depends(get_current_user_optional)
):
    """모니터링 주식 제거"""
    try:
        # 존재 확인
        existing_stock = stock_service.get_monitoring_stock(code)
        if not existing_stock:
            raise HTTPException(status_code=404, detail="모니터링 중인 종목을 찾을 수 없습니다.")
        
        # 제거
        success = await stock_service.remove_monitoring_stock(code)
        if not success:
            raise HTTPException(status_code=500, detail="모니터링 주식 제거에 실패했습니다.")
        
        return {"message": "모니터링 주식이 성공적으로 제거되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모니터링 주식 제거 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 주식 제거에 실패했습니다.")


@router.get("/alerts", response_model=StockAlertResponse)
async def get_stock_alerts(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    days: int = Query(7, ge=1, le=30, description="조회 일수"),
    current_user = Depends(get_current_user_optional)
):
    """주가 알림 목록 조회"""
    try:
        # 데이터베이스에서 주가 알림 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 전체 카운트 조회
        count_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'stock' 
            AND created_at >= :start_date 
            AND created_at <= :end_date
        """
        total_count = await database.fetch_val(count_query, {
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 읽지 않은 알림 카운트
        unread_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'stock' 
            AND is_read = false
            AND created_at >= :start_date 
            AND created_at <= :end_date
        """
        unread_count = await database.fetch_val(unread_query, {
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 알림 목록 조회
        offset = (page - 1) * page_size
        alerts_query = """
            SELECT * FROM alert_history 
            WHERE alert_type = 'stock' 
            AND created_at >= :start_date 
            AND created_at <= :end_date
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """
        
        alerts_data = await database.fetch_all(alerts_query, {
            "start_date": start_date,
            "end_date": end_date,
            "limit": page_size,
            "offset": offset
        })
        
        # StockAlert 객체로 변환
        alerts = []
        for alert_data in alerts_data:
            alert = {
                "id": alert_data["id"],
                "stock_code": alert_data["stock_code"] or "",
                "stock_name": alert_data["stock_name"] or "",
                "alert_type": "custom",  # DB에서 세부 타입 추출 필요
                "target_price": 0,
                "current_price": alert_data["price"] or 0,
                "change_rate": alert_data["change_rate"] or 0,
                "message": alert_data["message"] or "",
                "triggered_at": alert_data["created_at"],
                "is_sent": True,
                "sent_at": alert_data["created_at"]
            }
            alerts.append(alert)
        
        return StockAlertResponse(
            alerts=alerts,
            total_count=total_count or 0,
            unread_count=unread_count or 0
        )
        
    except Exception as e:
        logger.error(f"주가 알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주가 알림 조회에 실패했습니다.")


@router.put("/alerts/{alert_id}/read")
async def mark_alert_as_read(
    alert_id: int,
    current_user = Depends(get_current_user_optional)
):
    """알림을 읽음으로 표시"""
    try:
        query = """
            UPDATE alert_history 
            SET is_read = true 
            WHERE id = :alert_id AND alert_type = 'stock'
        """
        await database.execute(query, {"alert_id": alert_id})
        
        return {"message": "알림이 읽음으로 표시되었습니다."}
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 읽음 처리에 실패했습니다.")


@router.get("/statistics", response_model=StockStatisticsResponse)
async def get_stock_statistics(
    current_user = Depends(get_current_user_optional)
):
    """주가 모니터링 통계 조회"""
    try:
        stats = stock_service.get_statistics()
        market_info = stock_service.get_market_info()
        
        # 오늘 발송된 알림 수
        today = datetime.now().date()
        today_alerts_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'stock' 
            AND DATE(created_at) = :today
        """
        today_alerts = await database.fetch_val(today_alerts_query, {"today": today})
        
        from app.modules.stocks.models import StockStatistics
        
        statistics = StockStatistics(
            total_stocks=stats.get("total_stocks", 0),
            active_alerts=stats.get("active_stocks", 0),
            today_alerts=today_alerts or 0,
            market_status=market_info.status,
            last_update=datetime.fromisoformat(stats["last_updated"]) if stats.get("last_updated") else None,
            total_portfolio_value=stats.get("total_portfolio_value", 0),
            total_profit_loss=stats.get("total_profit_loss", 0),
            total_profit_loss_rate=stats.get("total_profit_loss_rate", 0)
        )
        
        return StockStatisticsResponse(statistics=statistics)
        
    except Exception as e:
        logger.error(f"주가 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주가 통계 조회에 실패했습니다.")


@router.get("/settings", response_model=StockSettingsResponse)
async def get_stock_settings(
    current_user = Depends(get_current_user_optional)
):
    """주가 모니터링 설정 조회"""
    try:
        settings = stock_service.get_settings()
        return StockSettingsResponse(settings=settings)
        
    except Exception as e:
        logger.error(f"설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 조회에 실패했습니다.")


@router.put("/settings", response_model=StockSettingsResponse)
async def update_stock_settings(
    settings: StockMonitoringSettings,
    current_user = Depends(get_current_user_optional)
):
    """주가 모니터링 설정 업데이트"""
    try:
        success = await stock_service.update_settings(settings)
        if not success:
            raise HTTPException(status_code=500, detail="설정 업데이트에 실패했습니다.")
        
        return StockSettingsResponse(
            settings=settings,
            message="설정이 성공적으로 업데이트되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 업데이트에 실패했습니다.")


@router.get("/search", response_model=StockSearchResponse)
async def search_stocks(
    q: str = Query(..., description="검색어"),
    current_user = Depends(get_current_user_optional)
):
    """주식 검색"""
    try:
        if len(q) < 2:
            raise HTTPException(status_code=400, detail="검색어는 최소 2자 이상이어야 합니다.")
        
        results = await stock_service.search_stocks(q)
        
        return StockSearchResponse(
            results=results,
            total_count=len(results),
            query=q
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주식 검색 실패: {e}")
        raise HTTPException(status_code=500, detail="주식 검색에 실패했습니다.")


@router.get("/market-info", response_model=MarketInfoResponse)
async def get_market_info(
    current_user = Depends(get_current_user_optional)
):
    """시장 정보 조회"""
    try:
        market_info = stock_service.get_market_info()
        return MarketInfoResponse(market_info=market_info)
        
    except Exception as e:
        logger.error(f"시장 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="시장 정보 조회에 실패했습니다.")


@router.post("/check-now")
async def check_stocks_now(
    current_user = Depends(get_current_user_optional)
):
    """수동으로 주가 체크 실행"""
    try:
        # 모니터링 주식 업데이트
        alerts = await stock_service.update_monitoring_stocks()
        
        # 알림 발송
        sent_count = await stock_service.send_alerts(alerts)
        
        return {
            "message": "주가 체크가 완료되었습니다.",
            "alerts_triggered": len(alerts),
            "alerts_sent": sent_count,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"수동 주가 체크 실패: {e}")
        raise HTTPException(status_code=500, detail="주가 체크에 실패했습니다.")


@router.get("/health")
async def health_check():
    """주가 모듈 헬스체크"""
    try:
        market_info = stock_service.get_market_info()
        monitoring_stocks = stock_service.get_monitoring_stocks()
        
        return {
            "status": "healthy",
            "market_status": market_info.status,
            "is_trading_hours": market_info.is_trading_hours,
            "monitoring_stocks_count": len(monitoring_stocks),
            "active_alerts_count": len([s for s in monitoring_stocks if s.alert_enabled])
        }
        
    except Exception as e:
        logger.error(f"주가 헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }