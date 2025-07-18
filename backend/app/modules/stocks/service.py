import requests
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, time, timedelta
import logging
from filelock import FileLock
import json
import os
from bs4 import BeautifulSoup
import re

from app.config import settings
from app.modules.stocks.models import (
    StockData, StockAlert, MonitoringStock, StockMonitoringData,
    StockMonitoringSettings, AlertType, MarketStatus, MarketInfo,
    StockSearchResult, StockPriceHistory
)
from app.shared.email import send_stock_alert
from app.shared.websocket import websocket_manager
from app.shared.database import database

logger = logging.getLogger(__name__)


class StockService:
    """주가 모니터링 서비스"""
    
    def __init__(self):
        self.monitoring_file = os.path.join(settings.DATA_DIR, "monitoring_stocks.json")
        self.file_lock = FileLock(f"{self.monitoring_file}.lock")
        self.monitoring_data = self._load_monitoring_data()
        self.triggered_alerts: Set[str] = set()  # 중복 알림 방지
        self.last_prices: Dict[str, float] = {}  # 이전 가격 저장
        
    def _load_monitoring_data(self) -> StockMonitoringData:
        """모니터링 데이터 로드"""
        try:
            with self.file_lock:
                if os.path.exists(self.monitoring_file):
                    with open(self.monitoring_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return StockMonitoringData(**data)
                else:
                    # 기본 데이터 생성
                    return StockMonitoringData()
        except Exception as e:
            logger.error(f"모니터링 데이터 로드 실패: {e}")
            return StockMonitoringData()
    
    def _save_monitoring_data(self):
        """모니터링 데이터 저장"""
        try:
            with self.file_lock:
                with open(self.monitoring_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        self.monitoring_data.dict(),
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str
                    )
        except Exception as e:
            logger.error(f"모니터링 데이터 저장 실패: {e}")
    
    async def get_stock_price_pykrx(self, code: str) -> Optional[StockData]:
        """PyKrx를 사용한 주가 조회"""
        try:
            # PyKrx는 동기 함수이므로 비동기 처리
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _get_price():
                try:
                    from pykrx import stock
                    
                    # 현재 가격 조회
                    today = datetime.now().strftime('%Y%m%d')
                    df = stock.get_market_ohlcv_by_date(today, today, code)
                    
                    if df.empty:
                        return None
                    
                    # 종목 정보 조회
                    ticker_name = stock.get_market_ticker_name(code)
                    
                    # 최신 데이터 추출
                    latest_data = df.iloc[-1]
                    
                    # 전일 종가 조회
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    prev_df = stock.get_market_ohlcv_by_date(yesterday, yesterday, code)
                    prev_close = prev_df.iloc[-1]['종가'] if not prev_df.empty else latest_data['종가']
                    
                    # 변동가 및 변동률 계산
                    current_price = latest_data['종가']
                    change = current_price - prev_close
                    change_rate = (change / prev_close) * 100 if prev_close != 0 else 0
                    
                    return StockData(
                        code=code,
                        name=ticker_name,
                        current_price=current_price,
                        prev_close=prev_close,
                        change=change,
                        change_rate=change_rate,
                        volume=latest_data['거래량'],
                        trading_value=latest_data['거래대금'],
                        high=latest_data['고가'],
                        low=latest_data['저가'],
                        open_price=latest_data['시가']
                    )
                    
                except Exception as e:
                    logger.error(f"PyKrx 주가 조회 실패 ({code}): {e}")
                    return None
            
            return await loop.run_in_executor(None, _get_price)
            
        except Exception as e:
            logger.error(f"PyKrx 주가 조회 오류: {e}")
            return None
    
    async def get_stock_price_naver(self, code: str) -> Optional[StockData]:
        """네이버 증권을 사용한 주가 조회 (폴백)"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 종목명
            name_element = soup.find('h2', class_='blind')
            name = name_element.get_text().strip() if name_element else f"종목{code}"
            
            # 현재가
            price_element = soup.find('strong', id='_nowVal')
            if not price_element:
                return None
            
            current_price = float(price_element.get_text().replace(',', ''))
            
            # 전일 대비
            change_element = soup.find('strong', id='_diff')
            change = float(change_element.get_text().replace(',', '')) if change_element else 0
            
            # 변동률
            rate_element = soup.find('strong', id='_rate')
            change_rate = float(rate_element.get_text().replace('%', '')) if rate_element else 0
            
            # 전일 종가
            prev_close = current_price - change
            
            # 거래량
            volume_element = soup.find('strong', id='_volume')
            volume = int(volume_element.get_text().replace(',', '')) if volume_element else 0
            
            # 고가/저가
            high_element = soup.find('strong', id='_high')
            low_element = soup.find('strong', id='_low')
            
            high = float(high_element.get_text().replace(',', '')) if high_element else current_price
            low = float(low_element.get_text().replace(',', '')) if low_element else current_price
            
            return StockData(
                code=code,
                name=name,
                current_price=current_price,
                prev_close=prev_close,
                change=change,
                change_rate=change_rate,
                volume=volume,
                high=high,
                low=low,
                open_price=current_price  # 네이버에서 시가 정보 제한적
            )
            
        except Exception as e:
            logger.error(f"네이버 주가 조회 실패 ({code}): {e}")
            return None
    
    async def get_stock_price(self, code: str) -> Optional[StockData]:
        """주가 조회 (PyKrx 우선, 실패시 네이버)"""
        try:
            # PyKrx 시도
            stock_data = await self.get_stock_price_pykrx(code)
            if stock_data:
                return stock_data
            
            # 네이버 폴백
            logger.warning(f"PyKrx 실패, 네이버로 폴백 ({code})")
            return await self.get_stock_price_naver(code)
            
        except Exception as e:
            logger.error(f"주가 조회 실패 ({code}): {e}")
            return None
    
    async def get_multiple_stock_prices(self, codes: List[str]) -> Dict[str, StockData]:
        """여러 종목 주가 조회"""
        try:
            tasks = [self.get_stock_price(code) for code in codes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            stock_prices = {}
            for i, result in enumerate(results):
                if isinstance(result, StockData):
                    stock_prices[codes[i]] = result
                elif isinstance(result, Exception):
                    logger.error(f"주가 조회 실패 ({codes[i]}): {result}")
            
            return stock_prices
            
        except Exception as e:
            logger.error(f"다중 주가 조회 실패: {e}")
            return {}
    
    async def check_price_alerts(self, stock_data: StockData) -> List[StockAlert]:
        """가격 알림 체크"""
        try:
            alerts = []
            monitoring_stock = self.monitoring_data.get_stock_by_code(stock_data.code)
            
            if not monitoring_stock or not monitoring_stock.alert_enabled:
                return alerts
            
            # 알림 조건 확인
            alert_types = monitoring_stock.should_alert(stock_data.current_price, stock_data.change_rate)
            
            for alert_type in alert_types:
                # 중복 알림 방지 (같은 종목, 같은 타입, 같은 날)
                alert_key = f"{stock_data.code}_{alert_type}_{datetime.now().date()}"
                if alert_key in self.triggered_alerts:
                    continue
                
                # 알림 생성
                alert = self._create_alert(stock_data, monitoring_stock, alert_type)
                alerts.append(alert)
                
                # 중복 방지 키 추가
                self.triggered_alerts.add(alert_key)
            
            return alerts
            
        except Exception as e:
            logger.error(f"가격 알림 체크 실패: {e}")
            return []
    
    def _create_alert(self, stock_data: StockData, monitoring_stock: MonitoringStock, alert_type: AlertType) -> StockAlert:
        """알림 생성"""
        messages = {
            AlertType.TAKE_PROFIT: f"{stock_data.name} 목표가 {monitoring_stock.take_profit:,.0f}원 달성! 현재가: {stock_data.current_price:,.0f}원",
            AlertType.STOP_LOSS: f"{stock_data.name} 손절가 {monitoring_stock.stop_loss:,.0f}원 도달! 현재가: {stock_data.current_price:,.0f}원",
            AlertType.DAILY_SURGE: f"{stock_data.name} 일일 급등 {stock_data.change_rate:+.2f}% 발생! 현재가: {stock_data.current_price:,.0f}원",
            AlertType.DAILY_DROP: f"{stock_data.name} 일일 급락 {stock_data.change_rate:+.2f}% 발생! 현재가: {stock_data.current_price:,.0f}원"
        }
        
        target_prices = {
            AlertType.TAKE_PROFIT: monitoring_stock.take_profit or 0,
            AlertType.STOP_LOSS: monitoring_stock.stop_loss or 0,
            AlertType.DAILY_SURGE: stock_data.prev_close * (1 + monitoring_stock.daily_surge_threshold / 100),
            AlertType.DAILY_DROP: stock_data.prev_close * (1 + monitoring_stock.daily_drop_threshold / 100)
        }
        
        return StockAlert(
            stock_code=stock_data.code,
            stock_name=stock_data.name,
            alert_type=alert_type,
            target_price=target_prices[alert_type],
            current_price=stock_data.current_price,
            change_rate=stock_data.change_rate,
            message=messages[alert_type]
        )
    
    async def send_alerts(self, alerts: List[StockAlert]) -> int:
        """알림 발송"""
        sent_count = 0
        
        for alert in alerts:
            try:
                # 이메일 발송
                email_sent = await send_stock_alert(
                    alert.stock_name,
                    alert.stock_code,
                    alert.current_price,
                    alert.change_rate,
                    alert.alert_type,
                    alert.target_price
                )
                
                # WebSocket 브로드캐스트
                await websocket_manager.send_stock_update({
                    "type": "alert",
                    "stock_code": alert.stock_code,
                    "stock_name": alert.stock_name,
                    "alert_type": alert.alert_type,
                    "current_price": alert.current_price,
                    "change_rate": alert.change_rate,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat()
                })
                
                # 데이터베이스에 알림 저장
                await self.save_alert_to_db(alert)
                
                if email_sent:
                    alert.is_sent = True
                    alert.sent_at = datetime.now()
                    sent_count += 1
                    
                    logger.info(f"주가 알림 발송 성공: {alert.stock_name} - {alert.alert_type}")
                
            except Exception as e:
                logger.error(f"알림 발송 실패: {e}")
                continue
        
        return sent_count
    
    async def save_alert_to_db(self, alert: StockAlert):
        """알림을 데이터베이스에 저장"""
        try:
            query = """
                INSERT INTO alert_history 
                (alert_type, title, message, stock_code, stock_name, price, change_rate, is_read, created_at)
                VALUES (:alert_type, :title, :message, :stock_code, :stock_name, :price, :change_rate, :is_read, :created_at)
            """
            
            await database.execute(query, {
                "alert_type": "stock",
                "title": f"[주가] {alert.stock_name}",
                "message": alert.message,
                "stock_code": alert.stock_code,
                "stock_name": alert.stock_name,
                "price": alert.current_price,
                "change_rate": alert.change_rate,
                "is_read": False,
                "created_at": alert.triggered_at
            })
            
        except Exception as e:
            logger.error(f"알림 DB 저장 실패: {e}")
    
    async def update_monitoring_stocks(self) -> List[StockAlert]:
        """모니터링 주식 업데이트"""
        try:
            if not self.monitoring_data.stocks:
                return []
            
            # 시장 시간 확인
            market_info = self.get_market_info()
            if not market_info.is_trading_hours:
                logger.debug("장 시간이 아니므로 주가 업데이트 스킵")
                return []
            
            # 모니터링 종목 코드 추출
            codes = [stock.code for stock in self.monitoring_data.stocks if stock.alert_enabled]
            
            if not codes:
                return []
            
            # 주가 조회
            stock_prices = await self.get_multiple_stock_prices(codes)
            
            # 알림 체크
            all_alerts = []
            for code, stock_data in stock_prices.items():
                # 모니터링 주식 정보 업데이트
                monitoring_stock = self.monitoring_data.get_stock_by_code(code)
                if monitoring_stock:
                    monitoring_stock.current_price = stock_data.current_price
                    monitoring_stock.change_rate = stock_data.change_rate
                    monitoring_stock.calculate_profit_loss()
                    monitoring_stock.last_updated = datetime.now()
                
                # 알림 체크
                alerts = await self.check_price_alerts(stock_data)
                all_alerts.extend(alerts)
                
                # WebSocket으로 실시간 주가 브로드캐스트
                await websocket_manager.send_stock_update({
                    "type": "price_update",
                    "stock_code": stock_data.code,
                    "stock_name": stock_data.name,
                    "current_price": stock_data.current_price,
                    "change": stock_data.change,
                    "change_rate": stock_data.change_rate,
                    "volume": stock_data.volume,
                    "updated_at": stock_data.updated_at.isoformat()
                })
            
            # 데이터 저장
            self._save_monitoring_data()
            
            return all_alerts
            
        except Exception as e:
            logger.error(f"모니터링 주식 업데이트 실패: {e}")
            return []
    
    def get_market_info(self) -> MarketInfo:
        """시장 정보 조회"""
        try:
            now = datetime.now()
            current_time = now.time()
            
            # 설정에서 시장 시간 조회
            market_open = self.monitoring_data.settings.market_open
            market_close = self.monitoring_data.settings.market_close
            
            # 주말 체크
            if now.weekday() >= 5:  # 토요일(5), 일요일(6)
                status = MarketStatus.CLOSED
                is_trading_hours = False
            # 평일 시장 시간 체크
            elif market_open <= current_time <= market_close:
                status = MarketStatus.OPEN
                is_trading_hours = True
            elif current_time < market_open:
                status = MarketStatus.PRE_MARKET
                is_trading_hours = False
            else:
                status = MarketStatus.AFTER_MARKET
                is_trading_hours = False
            
            # 다음 장 시작 시간 계산
            next_open = None
            if not is_trading_hours:
                if current_time < market_open and now.weekday() < 5:
                    # 오늘 장 시작 전
                    next_open = datetime.combine(now.date(), market_open)
                else:
                    # 다음 영업일
                    next_business_day = now.date() + timedelta(days=1)
                    while next_business_day.weekday() >= 5:
                        next_business_day += timedelta(days=1)
                    next_open = datetime.combine(next_business_day, market_open)
            
            return MarketInfo(
                status=status,
                open_time=market_open,
                close_time=market_close,
                current_time=now,
                is_trading_hours=is_trading_hours,
                next_open=next_open
            )
            
        except Exception as e:
            logger.error(f"시장 정보 조회 실패: {e}")
            return MarketInfo(
                status=MarketStatus.CLOSED,
                open_time=time(9, 0),
                close_time=time(15, 35),
                is_trading_hours=False
            )
    
    # 모니터링 주식 관리 메서드들
    async def add_monitoring_stock(self, stock: MonitoringStock) -> bool:
        """모니터링 주식 추가"""
        try:
            success = self.monitoring_data.add_stock(stock)
            if success:
                self._save_monitoring_data()
                logger.info(f"모니터링 주식 추가: {stock.name}({stock.code})")
            return success
        except Exception as e:
            logger.error(f"모니터링 주식 추가 실패: {e}")
            return False
    
    async def update_monitoring_stock(self, stock: MonitoringStock) -> bool:
        """모니터링 주식 업데이트"""
        try:
            success = self.monitoring_data.update_stock(stock)
            if success:
                self._save_monitoring_data()
                logger.info(f"모니터링 주식 업데이트: {stock.name}({stock.code})")
            return success
        except Exception as e:
            logger.error(f"모니터링 주식 업데이트 실패: {e}")
            return False
    
    async def remove_monitoring_stock(self, code: str) -> bool:
        """모니터링 주식 제거"""
        try:
            success = self.monitoring_data.remove_stock(code)
            if success:
                self._save_monitoring_data()
                logger.info(f"모니터링 주식 제거: {code}")
            return success
        except Exception as e:
            logger.error(f"모니터링 주식 제거 실패: {e}")
            return False
    
    def get_monitoring_stocks(self) -> List[MonitoringStock]:
        """모니터링 주식 목록 조회"""
        return self.monitoring_data.stocks
    
    def get_monitoring_stock(self, code: str) -> Optional[MonitoringStock]:
        """특정 모니터링 주식 조회"""
        return self.monitoring_data.get_stock_by_code(code)
    
    def get_settings(self) -> StockMonitoringSettings:
        """설정 조회"""
        return self.monitoring_data.settings
    
    async def update_settings(self, settings: StockMonitoringSettings) -> bool:
        """설정 업데이트"""
        try:
            self.monitoring_data.settings = settings
            self._save_monitoring_data()
            logger.info("주가 모니터링 설정 업데이트")
            return True
        except Exception as e:
            logger.error(f"설정 업데이트 실패: {e}")
            return False
    
    async def search_stocks(self, query: str) -> List[StockSearchResult]:
        """주식 검색"""
        try:
            # 간단한 검색 구현 (실제로는 더 복잡한 검색 로직 필요)
            from app.config import COMPANIES
            
            results = []
            for code, name in COMPANIES.items():
                if query.lower() in name.lower() or query in code:
                    # 현재 주가 조회
                    stock_data = await self.get_stock_price(code)
                    
                    result = StockSearchResult(
                        code=code,
                        name=name,
                        market="KOSPI",  # 실제로는 시장 구분 로직 필요
                        current_price=stock_data.current_price if stock_data else None,
                        change_rate=stock_data.change_rate if stock_data else None
                    )
                    results.append(result)
            
            return results[:20]  # 최대 20개 결과
            
        except Exception as e:
            logger.error(f"주식 검색 실패: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        try:
            total_stocks = len(self.monitoring_data.stocks)
            active_stocks = len([s for s in self.monitoring_data.stocks if s.alert_enabled])
            
            # 포트폴리오 계산
            total_value = 0
            total_profit_loss = 0
            for stock in self.monitoring_data.stocks:
                if stock.current_price:
                    stock_value = stock.current_price * stock.quantity
                    total_value += stock_value
                    total_profit_loss += (stock.current_price - stock.purchase_price) * stock.quantity
            
            total_investment = sum(s.purchase_price * s.quantity for s in self.monitoring_data.stocks)
            total_profit_loss_rate = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
            
            return {
                "total_stocks": total_stocks,
                "active_stocks": active_stocks,
                "total_portfolio_value": total_value,
                "total_profit_loss": total_profit_loss,
                "total_profit_loss_rate": total_profit_loss_rate,
                "last_updated": self.monitoring_data.last_updated.isoformat() if self.monitoring_data.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def reset_daily_alerts(self):
        """일일 알림 리셋 (자정에 실행)"""
        try:
            self.triggered_alerts.clear()
            logger.info("일일 알림 리셋 완료")
        except Exception as e:
            logger.error(f"일일 알림 리셋 실패: {e}")


# 전역 주가 서비스 인스턴스
stock_service = StockService()