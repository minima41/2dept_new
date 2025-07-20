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


class StockCategory(str, Enum):
    """종목 카테고리"""
    MEZZANINE = "mezzanine"  # 메자닌 투자
    OTHER = "other"          # 기타 투자


class AlertPrice(BaseModel):
    """알림 가격 설정"""
    price: float = Field(..., description="알림 가격")
    alert_type: str = Field(..., description="알림 유형")
    is_enabled: bool = Field(True, description="활성화 상태")
    description: Optional[str] = Field(None, description="설명")


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
    # acquisition_price는 purchase_price를 대체하되 기존 호환성 유지
    purchase_price: float = Field(..., description="취득가 (기존 호환성)")
    acquisition_price: Optional[float] = Field(None, description="취득가 (새 필드)")
    quantity: int = Field(..., description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트")
    
    # 메자닌 투자 관련 필드
    category: StockCategory = Field(StockCategory.OTHER, description="종목 카테고리")
    conversion_price: Optional[float] = Field(None, description="전환가격")
    conversion_price_floor: Optional[float] = Field(None, description="전환가격 바닥가")
    
    # 복잡한 알림 시스템 필드
    triggered_alerts: List[str] = Field(default_factory=list, description="발송된 알림 ID 목록")
    alert_prices: List[AlertPrice] = Field(default_factory=list, description="사용자 정의 알림 가격 목록")
    daily_up_alert_sent: bool = Field(False, description="일일 상승 알림 발송 여부")
    daily_down_alert_sent: bool = Field(False, description="일일 하락 알림 발송 여부")
    
    # 런타임 데이터
    current_price: Optional[float] = Field(None, description="현재가")
    change_rate: Optional[float] = Field(None, description="변동률")
    profit_loss: Optional[float] = Field(None, description="손익금액")
    profit_loss_rate: Optional[float] = Field(None, description="손익률")
    parity: Optional[float] = Field(None, description="패리티 (%)")
    parity_floor: Optional[float] = Field(None, description="패리티 바닥가 (%)")
    
    @property
    def effective_acquisition_price(self) -> float:
        """실제 취득가 반환 (새 필드 우선, 없으면 기존 필드)"""
        return self.acquisition_price if self.acquisition_price is not None else self.purchase_price
    
    def calculate_profit_loss(self):
        """손익 계산"""
        if self.current_price is None:
            return
        
        acquisition_price = self.effective_acquisition_price
        self.profit_loss = (self.current_price - acquisition_price) * self.quantity
        self.profit_loss_rate = ((self.current_price - acquisition_price) / acquisition_price) * 100
    
    def calculate_parity(self) -> Optional[float]:
        """패리티 계산 (메자닌 투자용)"""
        if self.category != StockCategory.MEZZANINE or not self.conversion_price or not self.current_price:
            return None
        
        parity = (self.current_price / self.conversion_price) * 100
        self.parity = round(parity, 2)
        return self.parity
    
    def calculate_parity_floor(self) -> Optional[float]:
        """패리티 바닥가 계산 (메자닌 투자용)"""
        if self.category != StockCategory.MEZZANINE or not self.conversion_price_floor or not self.current_price:
            return None
        
        parity_floor = (self.current_price / self.conversion_price_floor) * 100
        self.parity_floor = round(parity_floor, 2)
        return self.parity_floor
    
    def update_all_calculations(self):
        """모든 계산 업데이트"""
        self.calculate_profit_loss()
        if self.category == StockCategory.MEZZANINE:
            self.calculate_parity()
            self.calculate_parity_floor()
    
    def add_alert_price(self, price: float, alert_type: str, description: Optional[str] = None) -> bool:
        """사용자 정의 알림 가격 추가"""
        # 중복 체크
        for alert_price in self.alert_prices:
            if alert_price.price == price and alert_price.alert_type == alert_type:
                return False
        
        self.alert_prices.append(AlertPrice(
            price=price,
            alert_type=alert_type,
            description=description
        ))
        return True
    
    def remove_alert_price(self, price: float, alert_type: str) -> bool:
        """사용자 정의 알림 가격 제거"""
        for i, alert_price in enumerate(self.alert_prices):
            if alert_price.price == price and alert_price.alert_type == alert_type:
                del self.alert_prices[i]
                return True
        return False
    
    def is_alert_triggered(self, alert_id: str) -> bool:
        """알림이 이미 발송되었는지 확인"""
        return alert_id in self.triggered_alerts
    
    def mark_alert_triggered(self, alert_id: str):
        """알림을 발송된 것으로 표시"""
        if alert_id not in self.triggered_alerts:
            self.triggered_alerts.append(alert_id)
    
    def reset_daily_alerts(self):
        """일일 알림 상태 리셋"""
        self.daily_up_alert_sent = False
        self.daily_down_alert_sent = False
        # 일일 알림 ID들만 제거 (take_profit, stop_loss 등은 유지)
        daily_alert_ids = [alert_id for alert_id in self.triggered_alerts 
                          if 'daily_' in alert_id or 'surge_' in alert_id or 'drop_' in alert_id]
        for alert_id in daily_alert_ids:
            self.triggered_alerts.remove(alert_id)
    
    def check_alert_prices(self, current_price: float) -> List[AlertPrice]:
        """사용자 정의 알림 가격 체크"""
        triggered = []
        for alert_price in self.alert_prices:
            if not alert_price.is_enabled:
                continue
                
            alert_id = f"{alert_price.alert_type}_{alert_price.price}"
            if self.is_alert_triggered(alert_id):
                continue
                
            should_trigger = False
            if alert_price.alert_type == "above" and current_price >= alert_price.price:
                should_trigger = True
            elif alert_price.alert_type == "below" and current_price <= alert_price.price:
                should_trigger = True
            elif alert_price.alert_type == "parity" and self.category == StockCategory.MEZZANINE:
                if self.parity and self.parity >= alert_price.price:
                    should_trigger = True
                    
            if should_trigger:
                self.mark_alert_triggered(alert_id)
                triggered.append(alert_price)
                
        return triggered
    
    def should_alert(self, current_price: float, change_rate: float) -> List[AlertType]:
        """알림 조건 확인 (중복 방지 포함)"""
        alerts = []
        
        if not self.alert_enabled:
            return alerts
        
        # 목표가 달성
        if self.take_profit and current_price >= self.take_profit:
            alert_id = f"take_profit_{self.take_profit}"
            if not self.is_alert_triggered(alert_id):
                alerts.append(AlertType.TAKE_PROFIT)
                self.mark_alert_triggered(alert_id)
        
        # 손절가 도달
        if self.stop_loss and current_price <= self.stop_loss:
            alert_id = f"stop_loss_{self.stop_loss}"
            if not self.is_alert_triggered(alert_id):
                alerts.append(AlertType.STOP_LOSS)
                self.mark_alert_triggered(alert_id)
        
        # 일일 급등 (하루에 한 번만)
        if change_rate >= self.daily_surge_threshold and not self.daily_up_alert_sent:
            alerts.append(AlertType.DAILY_SURGE)
            self.daily_up_alert_sent = True
        
        # 일일 급락 (하루에 한 번만)
        if change_rate <= self.daily_drop_threshold and not self.daily_down_alert_sent:
            alerts.append(AlertType.DAILY_DROP)
            self.daily_down_alert_sent = True
        
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
    purchase_price: float = Field(..., description="취득가 (기존 호환성)")
    acquisition_price: Optional[float] = Field(None, description="취득가 (새 필드)")
    quantity: int = Field(..., description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")
    
    # 메자닌 투자 관련 필드
    category: StockCategory = Field(StockCategory.OTHER, description="종목 카테고리")
    conversion_price: Optional[float] = Field(None, description="전환가격")
    conversion_price_floor: Optional[float] = Field(None, description="전환가격 바닥가")


class UpdateStockRequest(BaseModel):
    """주식 정보 업데이트 요청 모델"""
    purchase_price: Optional[float] = Field(None, description="취득가 (기존 호환성)")
    acquisition_price: Optional[float] = Field(None, description="취득가 (새 필드)")
    quantity: Optional[int] = Field(None, description="보유수량")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: Optional[float] = Field(None, description="일일 급등 임계값(%)")
    daily_drop_threshold: Optional[float] = Field(None, description="일일 급락 임계값(%)")
    alert_enabled: Optional[bool] = Field(None, description="알림 활성화")
    
    # 메자닌 투자 관련 필드
    category: Optional[StockCategory] = Field(None, description="종목 카테고리")
    conversion_price: Optional[float] = Field(None, description="전환가격")
    conversion_price_floor: Optional[float] = Field(None, description="전환가격 바닥가")


class AlertSettingsRequest(BaseModel):
    """알림 설정 요청 모델"""
    stock_code: str = Field(..., description="종목코드")
    take_profit: Optional[float] = Field(None, description="목표가")
    stop_loss: Optional[float] = Field(None, description="손절가")
    daily_surge_threshold: float = Field(5.0, description="일일 급등 임계값(%)")
    daily_drop_threshold: float = Field(-5.0, description="일일 급락 임계값(%)")
    alert_enabled: bool = Field(True, description="알림 활성화")