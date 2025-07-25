"""
V2 Investment Monitor - 주식 관련 Pydantic 모델
주식 모니터링 요청/응답 데이터 검증
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal


class StockAddRequest(BaseModel):
    """주식 추가 요청 모델"""
    stock_code: str = Field(..., min_length=6, max_length=6, description="주식 코드 (6자리)")
    stock_name: str = Field(..., min_length=1, max_length=100, description="주식명")
    target_price: Optional[float] = Field(None, gt=0, description="목표가")
    stop_loss_price: Optional[float] = Field(None, gt=0, description="손절가")
    
    @validator('stock_code')
    def validate_stock_code(cls, v):
        if not v.isdigit():
            raise ValueError("주식 코드는 6자리 숫자여야 합니다")
        return v
    
    @validator('stock_name')
    def validate_stock_name(cls, v):
        name = v.strip()
        if not name:
            raise ValueError("주식명이 비어있습니다")
        return name
    
    @validator('stop_loss_price')
    def validate_stop_loss_vs_target(cls, v, values):
        if v is not None and 'target_price' in values and values['target_price'] is not None:
            if v >= values['target_price']:
                raise ValueError("손절가는 목표가보다 낮아야 합니다")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "target_price": 80000.0,
                "stop_loss_price": 65000.0
            }
        }


class StockUpdateRequest(BaseModel):
    """주식 설정 updating 요청"""
    target_price: Optional[float] = Field(None, gt=0, description="목표가")
    stop_loss_price: Optional[float] = Field(None, gt=0, description="손절가")
    monitoring_enabled: Optional[bool] = Field(None, description="모니터링 활성화")
    
    @validator('stop_loss_price')
    def validate_prices(cls, v, values):
        if v is not None and 'target_price' in values and values['target_price'] is not None:
            if v >= values['target_price']:
                raise ValueError("손절가는 목표가보다 낮아야 합니다")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_price": 75000.0,
                "stop_loss_price": 60000.0,
                "monitoring_enabled": True
            }
        }


class StockResponse(BaseModel):
    """주식 info 응답 모델"""
    stock_code: str = Field(..., description="주식 코드")
    stock_name: str = Field(..., description="주식명")
    current_price: Optional[float] = Field(None, description="현재가")
    target_price: Optional[float] = Field(None, description="목표가")
    stop_loss_price: Optional[float] = Field(None, description="손절가")
    monitoring_enabled: bool = Field(default=True, description="모니터링 활성화")
    
    # 가격 변동 info
    price_change: Optional[float] = Field(None, description="가격 변동")
    price_change_rate: Optional[float] = Field(None, description="가격 변동률 (%)")
    volume: Optional[int] = Field(None, description="거래량")
    
    # 메타데이터
    added_at: Optional[datetime] = Field(None, description="추가  hours")
    last_updated: Optional[datetime] = Field(None, description="마지막 updating")
    
    # 알림 상태
    target_reached: Optional[bool] = Field(None, description="목표가 도달 여부")
    stop_loss_reached: Optional[bool] = Field(None, description="손절가 도달 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "current_price": 72000.0,
                "target_price": 80000.0,
                "stop_loss_price": 65000.0,
                "monitoring_enabled": True,
                "price_change": 1000.0,
                "price_change_rate": 1.41,
                "volume": 15000000,
                "target_reached": False,
                "stop_loss_reached": False
            }
        }


class StockPriceResponse(BaseModel):
    """주식 가격 응답 모델"""
    stock_code: str = Field(..., description="주식 코드")
    current_price: float = Field(..., description="현재가")
    change: float = Field(..., description="가격 변동")
    change_rate: float = Field(..., description="변동률 (%)")
    volume: Optional[int] = Field(None, description="거래량")
    updated_at: str = Field(..., description="업데이트  hours")
    data_source: Optional[str] = Field(None, description="데이터 소스")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "current_price": 72000.0,
                "change": 1000.0,
                "change_rate": 1.41,
                "volume": 15000000,
                "updated_at": "2024-01-01T15:30:00",
                "data_source": "pykrx"
            }
        }


class StockAlertResponse(BaseModel):
    """주식 알림 응답 모델"""
    stock_code: str = Field(..., description="주식 코드")
    stock_name: str = Field(..., description="주식명")
    alert_type: str = Field(..., description="알림 타입")
    current_price: float = Field(..., description="현재가")
    target_price: Optional[float] = Field(None, description="목표가")
    stop_loss_price: Optional[float] = Field(None, description="손절가")
    message: str = Field(..., description="알림 message")
    created_at: datetime = Field(..., description="생성  hours")
    
    @validator('alert_type')
    def validate_alert_type(cls, v):
        valid_types = ['target_price_reached', 'stop_loss_reached', 'price_surge', 'price_drop']
        if v not in valid_types:
            raise ValueError(f"유효하지 않은 알림 타입: {v}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "alert_type": "target_price_reached",
                "current_price": 80500.0,
                "target_price": 80000.0,
                "message": "삼성전자 목표가 80,000원 도달! (현재: 80,500원)"
            }
        }


class StockSearchRequest(BaseModel):
    """주식 검색 요청"""
    query: str = Field(..., min_length=1, description="검색어 (주식명 또는 코드)")
    exact_match: bool = Field(default=False, description="정확히 일치하는 결과만")
    limit: int = Field(default=20, ge=1, le=100, description="결과  items수 제한")
    
    @validator('query')
    def validate_query(cls, v):
        query = v.strip()
        if not query:
            raise ValueError("검색어가 비어있습니다")
        return query
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "삼성",
                "exact_match": False,
                "limit": 10
            }
        }


class StockBatchRequest(BaseModel):
    """주식 일괄 processing 요청"""
    stocks: List[StockAddRequest] = Field(..., min_items=1, max_items=50, description="주식 목록")
    
    @validator('stocks')
    def validate_no_duplicates(cls, v):
        stock_codes = [stock.stock_code for stock in v]
        if len(stock_codes) != len(set(stock_codes)):
            raise ValueError("중복된 주식 코드가 있습니다")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "stocks": [
                    {
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                        "target_price": 80000.0
                    },
                    {
                        "stock_code": "000660",
                        "stock_name": "SK하이닉스",
                        "target_price": 150000.0
                    }
                ]
            }
        }


class StockStatistics(BaseModel):
    """주식 모니터링 통계"""
    total_stocks: int = Field(default=0, description="총 주식 수")
    enabled_stocks: int = Field(default=0, description="활성화된 주식 수")
    stocks_with_alerts: int = Field(default=0, description="알림 설정된 주식 수")
    market_open: bool = Field(default=False, description="시장  items장 여부")
    last_update: Optional[str] = Field(None, description="마지막 updating  hours")
    
    # 성과 통계
    stocks_above_target: Optional[int] = Field(None, description="목표가 이상 주식 수")
    stocks_below_stop_loss: Optional[int] = Field(None, description="손절가 이하 주식 수")
    total_alerts_today: Optional[int] = Field(None, description="오늘 총 알림 수")


class StockMonitoringConfig(BaseModel):
    """주식 모니터링 설정"""
    update_interval: int = Field(default=10, ge=5, le=60, description="업데이트 간격 ( seconds)")
    market_open_time: str = Field(default="09:00", description="시장  items장  hours")
    market_close_time: str = Field(default="15:35", description="시장 마감  hours")
    enable_price_alerts: bool = Field(default=True, description="가격 알림 활성화")
    enable_email_notifications: bool = Field(default=True, description="이메일 알림 활성화")
    
    @validator('market_open_time', 'market_close_time')
    def validate_time_format(cls, v):
        try:
            hour, minute = v.split(':')
            hour, minute = int(hour), int(minute)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except:
            raise ValueError(" hours 형식이 올바르지 않습니다 (HH:MM)")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "update_interval": 10,
                "market_open_time": "09:00",
                "market_close_time": "15:35",
                "enable_price_alerts": True,
                "enable_email_notifications": True
            }
        }


class StockPriceHistory(BaseModel):
    """주식 가격 히스토리"""
    stock_code: str
    prices: List[Dict[str, Any]] = Field(..., description="가격 히스토리 데이터")
    period: str = Field(..., description="조회 기간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "prices": [
                    {
                        "date": "2024-01-01",
                        "open": 71000,
                        "high": 72500,
                        "low": 70500,
                        "close": 72000,
                        "volume": 15000000
                    }
                ],
                "period": "1d"
            }
        }