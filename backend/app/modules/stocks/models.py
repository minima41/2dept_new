from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, time
from enum import Enum
import json


class AlertType(str, Enum):
    """알림 유형"""
    TAKE_PROFIT = "take_profit"  # 목표가 달성
    STOP_LOSS = "stop_loss"      # 손절가 도달
    DAILY_SURGE = "daily_surge"  # 일일 급등
    DAILY_DROP = "daily_drop"    # 일일 급락
    CUSTOM = "custom"            # 사용자 정의


class MarketStatus(str, Enum):
    """시장 상태"""
    OPEN = "open"          # 장 중
    CLOSED = "closed"      # 장 마감
    PRE_MARKET = "pre_market"  # 장 시작 전
    AFTER_MARKET = "after_market"  # 장 마감 후


class StockData(BaseModel):
    """주가 데이터 모델"""
    code: str = Field(..., description="종목코드")
    name: str = Field(..., description="종목명")
    current_price: float = Field(..., description="현재가")
    prev_close: float = Field(..., description="전일종가")
    change: float = Field(..., description="변동가")
    change_rate: float = Field(..., description="변동률(%)")
    volume: int = Field(0, description="거래량")
    trading_value: int = Field(0, description="거래대금")
    market_cap: Optional[int] = Field(None, description="시가총액")
    high: Optional[float] = Field(None, description="고가")
    low: Optional[float] = Field(None, description="저가")
    open_price: Optional[float] = Field(None, description="시가")
    updated_at: datetime = Field(default_factory=datetime.now, description="업데이트 시간")
    
    @validator('change_rate')
    def round_change_rate(cls, v):
        return round(v, 2)
    
    @validator('current_price', 'prev_close', 'change')
    def round_price(cls, v):
        return round(v, 0)


class StockAlert(BaseModel):
    """주가 알림 모델"""
    id: Optional[int] = Field(None, description="알림 ID")
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    alert_type: AlertType = Field(..., description="알림 유형")
    target_price: float = Field(..., description="목표가격")
    current_price: float = Field(..., description="현재가격")
    change_rate: float = Field(..., description="변동률")
    message: str = Field(..., description="알림 메시지")
    triggered_at: datetime = Field(default_factory=datetime.now, description="발생시간")
    is_sent: bool = Field(False, description="발송 여부")
    sent_at: Optional[datetime] = Field(None, description="발송시간")


class MonitoringStock(BaseModel):
    """모니터링 주식 모델"""
    code: str = Field(..., description="종목코드")
    name: str = Field(..., description="종목명")
    purchase_price: float = Field(..., description="취득가")
    quantity: int = Field(..., description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트")
    
    # 런타임 데이터
    current_price: Optional[float] = Field(None, description="현재가")
    change_rate: Optional[float] = Field(None, description="변동률")
    profit_loss: Optional[float] = Field(None, description="손익금액")
    profit_loss_rate: Optional[float] = Field(None, description="손익률")
    
    def calculate_profit_loss(self):
        """손익 계산"""
        if self.current_price is None:
            return
        
        self.profit_loss = (self.current_price - self.purchase_price) * self.quantity
        self.profit_loss_rate = ((self.current_price - self.purchase_price) / self.purchase_price) * 100
    
    def should_alert(self, current_price: float, change_rate: float) -> List[AlertType]:
        """알림 조건 확인"""
        alerts = []
        
        if not self.alert_enabled:
            return alerts
        
        # 목표가 달성
        if self.take_profit and current_price >= self.take_profit:
            alerts.append(AlertType.TAKE_PROFIT)
        
        # 손절가 도달
        if self.stop_loss and current_price <= self.stop_loss:
            alerts.append(AlertType.STOP_LOSS)
        
        # 일일 급등
        if change_rate >= self.daily_surge_threshold:
            alerts.append(AlertType.DAILY_SURGE)
        
        # 일일 급락
        if change_rate <= self.daily_drop_threshold:
            alerts.append(AlertType.DAILY_DROP)
        
        return alerts


class StockMonitoringSettings(BaseModel):
    """주가 모니터링 설정"""
    check_interval: int = Field(10, description="체크 주기(초)")
    market_open: time = Field(time(9, 0), description="장 시작 시간")
    market_close: time = Field(time(15, 35), description="장 마감 시간")
    enable_email_alerts: bool = Field(True, description="이메일 알림 활성화")
    enable_websocket_alerts: bool = Field(True, description="WebSocket 알림 활성화")
    max_alerts_per_day: int = Field(100, description="일일 최대 알림 수")
    retry_attempts: int = Field(3, description="재시도 횟수")
    timeout_seconds: int = Field(30, description="타임아웃(초)")


class StockMonitoringData(BaseModel):
    """모니터링 데이터 파일 모델"""
    stocks: List[MonitoringStock] = Field(default_factory=list, description="모니터링 주식 목록")
    settings: StockMonitoringSettings = Field(default_factory=StockMonitoringSettings, description="설정")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트")
    
    def get_stock_by_code(self, code: str) -> Optional[MonitoringStock]:
        """종목코드로 주식 조회"""
        for stock in self.stocks:
            if stock.code == code:
                return stock
        return None
    
    def add_stock(self, stock: MonitoringStock) -> bool:
        """주식 추가"""
        if self.get_stock_by_code(stock.code):
            return False  # 이미 존재
        
        self.stocks.append(stock)
        self.last_updated = datetime.now()
        return True
    
    def update_stock(self, stock: MonitoringStock) -> bool:
        """주식 정보 업데이트"""
        for i, existing_stock in enumerate(self.stocks):
            if existing_stock.code == stock.code:
                self.stocks[i] = stock
                self.last_updated = datetime.now()
                return True
        return False
    
    def remove_stock(self, code: str) -> bool:
        """주식 제거"""
        for i, stock in enumerate(self.stocks):
            if stock.code == code:
                del self.stocks[i]
                self.last_updated = datetime.now()
                return True
        return False


class StockPriceHistory(BaseModel):
    """주가 히스토리 모델"""
    code: str = Field(..., description="종목코드")
    date: datetime = Field(..., description="날짜")
    open_price: float = Field(..., description="시가")
    high_price: float = Field(..., description="고가")
    low_price: float = Field(..., description="저가")
    close_price: float = Field(..., description="종가")
    volume: int = Field(..., description="거래량")
    trading_value: int = Field(..., description="거래대금")


class StockSearchResult(BaseModel):
    """주식 검색 결과 모델"""
    code: str = Field(..., description="종목코드")
    name: str = Field(..., description="종목명")
    market: str = Field(..., description="시장구분")
    current_price: Optional[float] = Field(None, description="현재가")
    change_rate: Optional[float] = Field(None, description="변동률")


class MarketInfo(BaseModel):
    """시장 정보 모델"""
    status: MarketStatus = Field(..., description="시장 상태")
    open_time: time = Field(..., description="장 시작 시간")
    close_time: time = Field(..., description="장 마감 시간")
    current_time: datetime = Field(default_factory=datetime.now, description="현재 시간")
    is_trading_hours: bool = Field(..., description="장중 여부")
    next_open: Optional[datetime] = Field(None, description="다음 장 시작 시간")


# 응답 모델들
class StockDataResponse(BaseModel):
    """주가 데이터 응답 모델"""
    stock: StockData
    message: str = "주가 데이터를 성공적으로 조회했습니다."


class StockListResponse(BaseModel):
    """주식 목록 응답 모델"""
    stocks: List[StockData]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class MonitoringStockResponse(BaseModel):
    """모니터링 주식 응답 모델"""
    stocks: List[MonitoringStock]
    total_count: int
    message: str = "모니터링 주식 목록을 성공적으로 조회했습니다."


class StockAlertResponse(BaseModel):
    """주가 알림 응답 모델"""
    alerts: List[StockAlert]
    total_count: int
    unread_count: int


class StockStatistics(BaseModel):
    """주가 통계 모델"""
    total_stocks: int = Field(0, description="총 모니터링 주식 수")
    active_alerts: int = Field(0, description="활성 알림 수")
    today_alerts: int = Field(0, description="오늘 발송된 알림 수")
    market_status: MarketStatus = Field(MarketStatus.CLOSED, description="시장 상태")
    last_update: Optional[datetime] = Field(None, description="마지막 업데이트")
    total_portfolio_value: float = Field(0, description="총 포트폴리오 가치")
    total_profit_loss: float = Field(0, description="총 손익")
    total_profit_loss_rate: float = Field(0, description="총 손익률")


class StockStatisticsResponse(BaseModel):
    """주가 통계 응답 모델"""
    statistics: StockStatistics
    message: str = "통계를 성공적으로 조회했습니다."


class StockSettingsResponse(BaseModel):
    """주가 설정 응답 모델"""
    settings: StockMonitoringSettings
    message: str = "설정을 성공적으로 조회했습니다."


class StockSearchResponse(BaseModel):
    """주식 검색 응답 모델"""
    results: List[StockSearchResult]
    total_count: int
    query: str


class MarketInfoResponse(BaseModel):
    """시장 정보 응답 모델"""
    market_info: MarketInfo
    message: str = "시장 정보를 성공적으로 조회했습니다."


class StockPriceRequest(BaseModel):
    """주가 조회 요청 모델"""
    codes: List[str] = Field(..., description="종목코드 목록")
    include_history: bool = Field(False, description="히스토리 포함 여부")


class AddStockRequest(BaseModel):
    """주식 추가 요청 모델"""
    code: str = Field(..., description="종목코드")
    name: str = Field(..., description="종목명")
    purchase_price: float = Field(..., description="취득가")
    quantity: int = Field(..., description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")


class UpdateStockRequest(BaseModel):
    """주식 정보 업데이트 요청 모델"""
    purchase_price: Optional[float] = Field(None, description="취득가")
    quantity: Optional[int] = Field(None, description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: Optional[float] = Field(None, description="일일 급등 임계값(%)")
    daily_drop_threshold: Optional[float] = Field(None, description="일일 급락 임계값(%)")
    alert_enabled: Optional[bool] = Field(None, description="알림 활성화")


class AlertSettingsRequest(BaseModel):
    """알림 설정 요청 모델"""
    stock_code: str = Field(..., description="종목코드")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")