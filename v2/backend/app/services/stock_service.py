"""
V2 Investment Monitor - 주식 모니터링 서비스
기존 simple_stock_manager_integrated.py의 핵심 로직을 클래스로 재구성
"""
import httpx
import asyncio
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Optional
import logging
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

from ..core.config import settings
from ..core.database import database
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

# PyKrx 선택적 import (기존 로직 유지)
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
    logger.info("📊 PyKrx 라이브러리 로드 success")
except ImportError:
    PYKRX_AVAILABLE = False
    logger.warning("[WARNING] PyKrx 라이브러리 없음, 웹 스크래핑 사용")


class StockService:
    """주식 모니터링 서비스 (기존 GUI → 웹 서비스)"""
    
    def __init__(self):
        self.monitoring_stocks: Dict[str, Dict] = {}
        self.notification_service = NotificationService()
        
        # 데이터 파일 경로 (기존 호환성)
        self.stocks_file = settings.data_dir / "monitoring_stocks.json"
        
        # 시장 운영  hours
        self.market_open = dt_time(9, 0)   # 09:00
        self.market_close = dt_time(15, 35)  # 15:35
        
        self._load_monitoring_stocks()
    
    def _load_monitoring_stocks(self) -> None:
        """저장된 모니터링 주식 목록 로드 (기존 파일 호환)"""
        try:
            if self.stocks_file.exists():
                with open(self.stocks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 배열 형식인 경우 딕셔너리로 변환
                    if isinstance(data, list):
                        self.monitoring_stocks = {}
                        for stock in data:
                            stock_code = stock.get("stock_code")
                            if stock_code:
                                # 필드명 정규화
                                normalized_stock = {
                                    "stock_code": stock_code,
                                    "stock_name": stock.get("stock_name", ""),
                                    "target_price": stock.get("target_price"),
                                    "stop_loss_price": stock.get("stop_loss_price"),
                                    "monitoring_enabled": stock.get("enabled", True),
                                    "current_price": None,
                                    "purchase_price": stock.get("purchase_price"),
                                    "quantity": stock.get("quantity"),
                                    "added_at": stock.get("added_date", datetime.now().isoformat()),
                                    "last_updated": datetime.now().isoformat(),
                                    "notes": stock.get("notes", "")
                                }
                                self.monitoring_stocks[stock_code] = normalized_stock
                        logger.info(f"[STOCK] 배열 형식 데이터를 딕셔너리로 변환: {len(self.monitoring_stocks)} items")
                    elif isinstance(data, dict):
                        self.monitoring_stocks = data
                        logger.info(f"[STOCK] 딕셔너리 형식 데이터 로드: {len(self.monitoring_stocks)} items")
                    else:
                        self.monitoring_stocks = {}
                        
                # 변환된 데이터를 파일에 다시 저장 (딕셔너리 형식으로)
                if isinstance(data, list):
                    self._save_monitoring_stocks()
                    
            else:
                self.monitoring_stocks = {}
                logger.info("[STOCK] 새로운 모니터링 파일 creating")
        except Exception as e:
            logger.warning(f"[WARNING] 주식 파일 로드 failed: {e}")
            self.monitoring_stocks = {}
    
    def _save_monitoring_stocks(self) -> None:
        """모니터링 주식 목록 저장 (기존 파일 호환)"""
        try:
            with open(self.stocks_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitoring_stocks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[ERROR] 주식 파일 저장 failed: {e}")
    
    def is_market_open(self) -> bool:
        """장 운영  hours인지 checking"""
        now = datetime.now().time()
        # 주말 제외 체크는 별도 구현 가능
        return self.market_open <= now <= self.market_close
    
    def is_pykrx_available(self) -> bool:
        """PyKrx 라이브러리 사용 가능 여부"""
        return PYKRX_AVAILABLE
    
    async def get_stock_price_pykrx(self, stock_code: str) -> Optional[Dict]:
        """PyKrx로 주가 info querying (기존 로직)"""
        if not PYKRX_AVAILABLE:
            return None
        
        try:
            today = datetime.now().strftime("%Y%m%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            
            # 현재가 querying - 오늘 데이터가 없으면 어제 데이터 사용
            current_price = stock.get_market_ohlcv_by_date(today, today, stock_code)
            if current_price.empty:
                # 장이 열리지 않았거나 데이터가 없는 경우 어제 데이터 사용
                current_price = stock.get_market_ohlcv_by_date(yesterday, yesterday, stock_code)
                if current_price.empty:
                    return None
            
            price_data = current_price.iloc[-1]
            
            # 전일 종가와 비교하여 변화율 계산
            try:
                prev_data = stock.get_market_ohlcv_by_date(yesterday, yesterday, stock_code)
                if not prev_data.empty:
                    prev_close = prev_data.iloc[-1]['종가']
                    current = price_data['종가']
                    change = current - prev_close
                    change_rate = (change / prev_close) * 100 if prev_close != 0 else 0
                else:
                    # 전일 데이터가 없으면 시가 대비로 계산
                    prev_close = price_data['시가']
                    current = price_data['종가']
                    change = current - prev_close
                    change_rate = (change / prev_close) * 100 if prev_close != 0 else 0
                    
            except:
                # 계산 failed 시 0으로 설정
                current = price_data['종가']
                change = 0
                change_rate = 0
            
            return {
                "price": float(current),
                "change": float(change),
                "change_rate": float(change_rate),
                "volume": int(price_data['거래량']),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[ERROR] PyKrx 주가 querying failed ({stock_code}): {e}")
            return None
    
    async def get_stock_price_web(self, stock_code: str) -> Optional[Dict]:
        """웹 스크래핑으로 주가 querying (Naver 증권, 기존 로직)"""
        url = f"https://finance.naver.com/item/main.nhn?code={stock_code}"
        
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=15.0
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 현재가 추출
                price_element = soup.select_one('.no_today .blind')
                if not price_element:
                    return None
                
                current_price = float(price_element.text.replace(',', ''))
                
                # 변화량 추출
                change_element = soup.select_one('.no_exday .blind')
                change = 0
                if change_element:
                    change_text = change_element.text.replace(',', '')
                    change = float(change_text) if change_text.replace('-', '').replace('.', '').isdigit() else 0
                
                # 변화율 계산
                change_rate = (change / (current_price - change)) * 100 if (current_price - change) != 0 else 0
                
                return {
                    "price": current_price,
                    "change": change,
                    "change_rate": change_rate,
                    "volume": 0,  # 웹에서는 거래량 생략
                    "updated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[ERROR] 웹 주가 querying failed ({stock_code}): {e}")
            return None
    
    async def get_stock_price(self, stock_code: str) -> Optional[Dict]:
        """주가 querying (PyKrx 우선, failed 시 웹 스크래핑)"""
        # PyKrx 시도
        price_data = await self.get_stock_price_pykrx(stock_code)
        if price_data:
            return price_data
        
        # 웹 스크래핑 시도
        return await self.get_stock_price_web(stock_code)
    
    async def get_current_price(self, stock_code: str) -> Optional[Dict]:
        """현재 주가 querying (별칭 메서드)"""
        return await self.get_stock_price(stock_code)
    
    async def add_monitoring_stock(
        self, 
        stock_code: str, 
        stock_name: str,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None
    ) -> bool:
        """모니터링 주식 추가"""
        try:
            # 현재 주가 querying
            price_data = await self.get_stock_price(stock_code)
            
            stock_info = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "target_price": target_price,
                "stop_loss_price": stop_loss_price,
                "monitoring_enabled": True,
                "current_price": price_data["price"] if price_data else None,
                "added_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            # 메모리에 저장
            self.monitoring_stocks[stock_code] = stock_info
            
            # 파일에 저장
            self._save_monitoring_stocks()
            
            # 데이터베이스에도 저장
            await self._save_stock_to_db(stock_info)
            
            logger.info(f"[STOCK] 모니터링 주식 추가: {stock_name} ({stock_code})")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] 주식 추가 failed ({stock_code}): {e}")
            return False
    
    async def remove_monitoring_stock(self, stock_code: str) -> bool:
        """모니터링 주식 제거"""
        try:
            if stock_code in self.monitoring_stocks:
                stock_name = self.monitoring_stocks[stock_code].get("stock_name", stock_code)
                del self.monitoring_stocks[stock_code]
                
                # 파일 updating
                self._save_monitoring_stocks()
                
                # DB에서도 제거
                await database.execute(
                    "UPDATE stock_monitoring SET monitoring_enabled = false WHERE stock_code = :code",
                    {"code": stock_code}
                )
                
                logger.info(f"📉 모니터링 주식 제거: {stock_name} ({stock_code})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[ERROR] 주식 제거 failed ({stock_code}): {e}")
            return False
    
    async def update_all_prices(self) -> Dict:
        """모든 모니터링 주식 가격 updating"""
        updated_count = 0
        alert_count = 0
        
        for stock_code, stock_info in self.monitoring_stocks.items():
            if not stock_info.get("monitoring_enabled", True):
                continue
            
            try:
                # 현재 가격 querying
                price_data = await self.get_stock_price(stock_code)
                if not price_data:
                    continue
                
                # 기존 info updating
                old_price = stock_info.get("current_price")
                stock_info.update(price_data)
                stock_info["last_updated"] = datetime.now().isoformat()
                
                # DB updating  
                await self._update_stock_price_in_db(stock_code, price_data)
                
                # 알림 체크
                alerts = await self._check_price_alerts(stock_info, old_price)
                alert_count += len(alerts)
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"[ERROR] 가격 updating failed ({stock_code}): {e}")
        
        # 메모리 → 파일 동기화
        self._save_monitoring_stocks()
        
        result = {
            "updated_count": updated_count,
            "alert_count": alert_count,
            "total_stocks": len(self.monitoring_stocks),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"💹 주가 updating completed: {updated_count} items 종목, {alert_count} items 알림")
        return result
    
    async def _check_price_alerts(self, stock_info: Dict, old_price: Optional[float]) -> List[Dict]:
        """가격 알림 조 records checking (기존 알림 로직)"""
        alerts = []
        current_price = stock_info.get("current_price")
        if not current_price:
            return alerts
        
        stock_code = stock_info["stock_code"]
        stock_name = stock_info["stock_name"]
        
        # 목표가 도달 알림
        target_price = stock_info.get("target_price")
        if target_price and current_price >= target_price:
            if not old_price or old_price < target_price:  # 처음 도달했을 때만
                alert_data = {
                    "stock_code": stock_code,
                    "stock_name": stock_name, 
                    "alert_type": "target_price_reached",
                    "current_price": current_price,
                    "target_price": target_price,
                    "message": f"{stock_name} 목표가 {target_price:,.0f}원 도달! (현재: {current_price:,.0f}원)"
                }
                await self.notification_service.create_stock_notification(alert_data)
                alerts.append(alert_data)
        
        # 손절가 도달 알림
        stop_loss_price = stock_info.get("stop_loss_price")
        if stop_loss_price and current_price <= stop_loss_price:
            if not old_price or old_price > stop_loss_price:  # 처음 도달했을 때만
                alert_data = {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "alert_type": "stop_loss_reached", 
                    "current_price": current_price,
                    "stop_loss_price": stop_loss_price,
                    "message": f"{stock_name} 손절가 {stop_loss_price:,.0f}원 도달! (현재: {current_price:,.0f}원)"
                }
                await self.notification_service.create_stock_notification(alert_data)
                alerts.append(alert_data)
        
        return alerts
    
    async def _save_stock_to_db(self, stock_info: Dict) -> None:
        """주식 info를 데이터베이스에 저장"""
        query = """
            INSERT OR REPLACE INTO stock_monitoring 
            (stock_code, stock_name, target_price, stop_loss_price, monitoring_enabled,
             current_price, last_updated, created_at, updated_at)
            VALUES (:stock_code, :stock_name, :target_price, :stop_loss_price, :monitoring_enabled,
                    :current_price, :last_updated, :created_at, :updated_at)
        """
        
        now = datetime.now()
        await database.execute(query, {
            "stock_code": stock_info["stock_code"],
            "stock_name": stock_info["stock_name"],
            "target_price": stock_info.get("target_price"),
            "stop_loss_price": stock_info.get("stop_loss_price"),
            "monitoring_enabled": stock_info.get("monitoring_enabled", True),
            "current_price": stock_info.get("current_price"),
            "last_updated": now,
            "created_at": now,
            "updated_at": now
        })
    
    async def _update_stock_price_in_db(self, stock_code: str, price_data: Dict) -> None:
        """데이터베이스의 주가 info updating"""
        query = """
            UPDATE stock_monitoring 
            SET current_price = :current_price, 
                price_change = :change,
                price_change_rate = :change_rate,
                last_updated = :last_updated
            WHERE stock_code = :stock_code
        """
        
        await database.execute(query, {
            "current_price": price_data["price"],
            "change": price_data["change"], 
            "change_rate": price_data["change_rate"],
            "last_updated": datetime.now(),
            "stock_code": stock_code
        })
    
    async def get_monitoring_stocks(self) -> List[Dict]:
        """모니터링 중인 주식 목록 querying"""
        return list(self.monitoring_stocks.values())
    
    async def toggle_monitoring(self, stock_code: str, enabled: bool) -> bool:
        """주식 모니터링 상태 토글"""
        try:
            if stock_code in self.monitoring_stocks:
                self.monitoring_stocks[stock_code]["monitoring_enabled"] = enabled
                self.monitoring_stocks[stock_code]["last_updated"] = datetime.now().isoformat()
                
                # 파일 updating
                self._save_monitoring_stocks()
                
                # DB updating
                await database.execute(
                    "UPDATE stock_monitoring SET monitoring_enabled = :enabled, updated_at = :updated_at WHERE stock_code = :code",
                    {
                        "enabled": enabled,
                        "updated_at": datetime.now(),
                        "code": stock_code
                    }
                )
                
                logger.info(f"📊 주식 모니터링 토글: {stock_code} -> {'활성화' if enabled else '비활성화'}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[ERROR] 모니터링 토글 failed ({stock_code}): {e}")
            return False

    async def get_statistics(self) -> Dict:
        """주식 모니터링 통계"""
        total_stocks = len(self.monitoring_stocks)
        enabled_stocks = sum(1 for stock in self.monitoring_stocks.values() 
                           if stock.get("monitoring_enabled", True))
        
        # 알림 설정된 종목 수
        with_alerts = sum(1 for stock in self.monitoring_stocks.values()
                         if stock.get("target_price") or stock.get("stop_loss_price"))
        
        return {
            "total_stocks": total_stocks,
            "enabled_stocks": enabled_stocks,
            "stocks_with_alerts": with_alerts,
            "market_open": self.is_market_open(),
            "last_update": max(
                (stock.get("last_updated", "") for stock in self.monitoring_stocks.values()),
                default=None
            )
        }


# === 전역 서비스 인스턴스 ===
stock_service = StockService()