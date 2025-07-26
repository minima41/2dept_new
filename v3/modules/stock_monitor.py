"""
주식 모니터링 모듈
기존 simple_stock_manager_integrated.py의 핵심 로직을 웹 환경에 맞게 리팩토링
"""
import json
import logging
import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from filelock import FileLock
from bs4 import BeautifulSoup
import re

from .config import (
    MONITORING_STOCKS_FILE,
    DEFAULT_MONITORING_STOCKS,
    STOCK_MARKET_OPEN_TIME,
    STOCK_MARKET_CLOSE_TIME,
    STOCK_ALERT_THRESHOLD_HIGH,
    STOCK_ALERT_THRESHOLD_LOW,
    REQUEST_TIMEOUT
)
from .email_utils import send_stock_alert

# PyKrx 가용성 확인
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# 로거 설정
logger = logging.getLogger(__name__)

class StockMonitor:
    """주식 모니터링 클래스"""
    
    def __init__(self):
        self.monitoring_stocks_file = MONITORING_STOCKS_FILE
        self.lock_file = self.monitoring_stocks_file + '.lock'
        
        # 데이터 디렉토리 생성
        os.makedirs(os.path.dirname(self.monitoring_stocks_file), exist_ok=True)
        
        # 초기 데이터 로드
        self.monitoring_stocks = self.load_monitoring_stocks()
    
    def load_monitoring_stocks(self) -> Dict:
        """모니터링 주식 데이터 로드"""
        try:
            if os.path.exists(self.monitoring_stocks_file):
                with FileLock(self.lock_file):
                    with open(self.monitoring_stocks_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # triggered_alerts를 set으로 변환
                        for code, info in data.items():
                            if "triggered_alerts" in info and isinstance(info["triggered_alerts"], list):
                                info["triggered_alerts"] = set(info["triggered_alerts"])
                        
                        logger.info(f"모니터링 주식 데이터 로드: {len(data)}개 종목")
                        return data
            else:
                # 기본 데이터로 초기화
                logger.info("모니터링 주식 파일이 없어 기본 데이터로 초기화")
                default_data = {}
                for stock in DEFAULT_MONITORING_STOCKS:
                    default_data[stock['code']] = {
                        'name': stock['name'],
                        'target_price': stock['target_price'],
                        'stop_loss': stock['stop_loss'],
                        'enabled': stock['enabled'],
                        'category': '주식',
                        'current_price': 0,
                        'change_percent': 0.0,
                        'last_updated': None,
                        'triggered_alerts': set(),
                        'alert_prices': []
                    }
                
                self.save_monitoring_stocks(default_data)
                return default_data
                
        except Exception as e:
            logger.error(f"모니터링 주식 데이터 로드 실패: {e}")
            return {}
    
    def save_monitoring_stocks(self, data: Dict):
        """모니터링 주식 데이터 저장"""
        try:
            # set을 list로 변환하여 JSON 직렬화 가능하게 만듦
            serializable_data = {}
            for code, info in data.items():
                serializable_info = info.copy()
                if 'triggered_alerts' in serializable_info and isinstance(serializable_info['triggered_alerts'], set):
                    serializable_info['triggered_alerts'] = list(serializable_info['triggered_alerts'])
                serializable_data[code] = serializable_info
            
            with FileLock(self.lock_file):
                with open(self.monitoring_stocks_file, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, ensure_ascii=False, indent=2)
                    
            logger.debug(f"모니터링 주식 데이터 저장: {len(data)}개 종목")
            
        except Exception as e:
            logger.error(f"모니터링 주식 데이터 저장 실패: {e}")
    
    def get_stock_price_pykrx(self, stock_code: str) -> Tuple[Optional[int], float, Optional[str]]:
        """PyKrx를 사용한 주가 정보 조회"""
        if not PYKRX_AVAILABLE:
            return None, 0.0, "PyKrx 라이브러리가 설치되지 않았습니다"
        
        try:
            today = datetime.now()
            
            # 최근 10일간 거래 데이터 찾기
            for i in range(10):
                date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
                try:
                    df = stock.get_market_ohlcv_by_date(date_str, date_str, stock_code)
                    
                    if df is not None and not df.empty:
                        current_price = int(df.iloc[0]['종가'])
                        change_percent = float(df.iloc[0]['등락률']) if '등락률' in df.columns else 0.0
                        
                        logger.debug(f"PyKrx 조회 성공: {stock_code} - {current_price}원 ({change_percent:+.2f}%)")
                        return current_price, change_percent, None
                        
                except Exception as e:
                    logger.debug(f"PyKrx 조회 실패: {stock_code}, {date_str} - {e}")
                    continue
            
            logger.warning(f"PyKrx: 최근 10일간 {stock_code}의 거래 데이터를 찾을 수 없음")
            return None, 0.0, "거래 데이터를 찾을 수 없습니다"
            
        except Exception as e:
            logger.error(f"PyKrx 사용 중 오류: {e}")
            return None, 0.0, f"오류 발생: {e}"
    
    def get_stock_price_naver(self, stock_code: str) -> Tuple[Optional[int], float, Optional[str]]:
        """네이버 금융 크롤링을 통한 주가 정보 조회"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.encoding = 'euc-kr'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 현재가 추출
                price_element = soup.select_one('p.no_today .blind')
                if price_element:
                    current_price = int(price_element.text.replace(',', ''))
                    
                    # 등락률 추출
                    change_element = soup.select_one('p.no_exday .blind')
                    change_percent = 0.0
                    if change_element:
                        change_text = change_element.text.strip()
                        change_match = re.search(r'([-+]?\d+\.?\d*)%', change_text)
                        if change_match:
                            change_percent = float(change_match.group(1))
                    
                    logger.debug(f"네이버 크롤링 성공: {stock_code} - {current_price}원 ({change_percent:+.2f}%)")
                    return current_price, change_percent, None
            
            return None, 0.0, "네이버 금융에서 데이터를 찾을 수 없습니다"
            
        except Exception as e:
            logger.error(f"네이버 크롤링 오류: {e}")
            return None, 0.0, f"크롤링 오류: {e}"
    
    def get_stock_price(self, stock_code: str) -> Tuple[Optional[int], float, Optional[str]]:
        """통합 주가 정보 조회 (PyKrx 우선, 실패 시 네이버 크롤링)"""
        # PyKrx 시도
        if PYKRX_AVAILABLE:
            current_price, change_percent, error = self.get_stock_price_pykrx(stock_code)
            if current_price is not None:
                return current_price, change_percent, None
            logger.debug(f"PyKrx 실패, 네이버 크롤링으로 시도: {stock_code}")
        
        # 네이버 크롤링 시도
        current_price, change_percent, error = self.get_stock_price_naver(stock_code)
        if current_price is not None:
            return current_price, change_percent, None
        
        return None, 0.0, error or "주가 정보를 가져올 수 없습니다"
    
    def get_stock_name(self, stock_code: str) -> str:
        """종목명 조회"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.encoding = 'euc-kr'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.select_one('div.wrap_company h2')
                if title_tag:
                    stock_name = title_tag.text.strip()
                    # 종목명에서 코드 부분 제거
                    stock_name = re.sub(r'\s*\([A-Z0-9]+\)$', '', stock_name)
                    return stock_name
            
            return f"종목 {stock_code}"
            
        except Exception as e:
            logger.error(f"종목명 조회 오류: {e}")
            return f"종목 {stock_code}"
    
    def is_market_open(self) -> bool:
        """시장 개장 시간 확인"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 주말 제외
        if now.weekday() >= 5:  # 5: 토요일, 6: 일요일
            return False
        
        return STOCK_MARKET_OPEN_TIME <= current_time <= STOCK_MARKET_CLOSE_TIME
    
    def setup_alert_prices(self, stock_info: Dict, current_price: int):
        """알림 가격 설정 (메자닌/기타 구분)"""
        category = stock_info.get('category', '주식')
        alert_prices = []
        
        # 기본 TP/SL 설정
        tp_price = stock_info.get('target_price', 0)
        sl_price = stock_info.get('stop_loss', 0)
        
        if tp_price > 0:
            alert_prices.append({
                "id": "tp0",
                "price": tp_price,
                "type": "TP Alert",
                "category": "TP"
            })
        
        if sl_price > 0:
            alert_prices.append({
                "id": "sl0", 
                "price": sl_price,
                "type": "SL Alert",
                "category": "SL"
            })
        
        # 메자닌: 패리티 알림 (80%, 100%, 120%)
        if category == "메자닌":
            conversion_price = stock_info.get('conversion_price', current_price)
            for percent in [80, 100, 120]:
                parity_price = int(conversion_price * percent / 100)
                alert_prices.append({
                    "id": f"parity{percent}",
                    "price": parity_price,
                    "type": "Parity Alert",
                    "category": "PARITY", 
                    "parity_percent": percent
                })
        
        # 기타: Up/Down 알림 (5% 상승/하락)
        elif category == "주식" and not alert_prices:
            alert_prices.extend([
                {
                    "id": f"up0_{stock_info.get('code', '')}",
                    "type": "Up Alert",
                    "price": int(current_price * 1.05)
                },
                {
                    "id": f"down0_{stock_info.get('code', '')}",
                    "type": "Down Alert", 
                    "price": int(current_price * 0.95)
                }
            ])
        
        stock_info['alert_prices'] = alert_prices
        return alert_prices
    
    def check_price_alerts(self, stock_code: str, stock_name: str, current_price: int, previous_price: int, stock_info: Dict) -> bool:
        """가격 알림 조건 확인"""
        alert_prices = stock_info.get("alert_prices", [])
        if not alert_prices:
            return False
        
        alert_triggered = False
        
        for alert in alert_prices:
            alert_id = alert.get("id", "")
            target_price = alert.get("price", 0)
            alert_type = alert.get("type", "")
            
            if alert_id in stock_info.get("triggered_alerts", set()):
                continue
            
            # TP/상승 알림
            if alert_type in ["TP Alert", "Up Alert"]:
                if current_price >= target_price and previous_price < target_price:
                    self.send_price_alert(stock_code, stock_name, current_price, target_price, "TARGET_UP", alert_type)
                    stock_info["triggered_alerts"].add(alert_id)
                    alert_triggered = True
            
            # SL/하락 알림  
            elif alert_type in ["SL Alert", "Down Alert"]:
                if current_price <= target_price and previous_price > target_price:
                    alert_msg_type = "STOP_LOSS" if alert_type == "SL Alert" else "TARGET_DOWN"
                    self.send_price_alert(stock_code, stock_name, current_price, target_price, alert_msg_type, alert_type)
                    stock_info["triggered_alerts"].add(alert_id)
                    alert_triggered = True
            
            # 패리티 알림
            elif alert_type == "Parity Alert":
                parity_percent = alert.get("parity_percent", 100)
                if current_price >= target_price and previous_price < target_price:
                    self.send_parity_alert(stock_code, stock_name, current_price, parity_percent)
                    stock_info["triggered_alerts"].add(alert_id)
                    alert_triggered = True
        
        # 일간 급등/급락 알림
        if stock_info.get("daily_alert_enabled", False):
            change_percent = stock_info.get("change_percent", 0.0)
            
            if change_percent >= STOCK_ALERT_THRESHOLD_HIGH:
                self.send_daily_alert(stock_code, stock_name, current_price, change_percent, "SURGE")
                alert_triggered = True
            elif change_percent <= STOCK_ALERT_THRESHOLD_LOW:
                self.send_daily_alert(stock_code, stock_name, current_price, change_percent, "DROP")
                alert_triggered = True
        
        return alert_triggered
    
    def send_price_alert(self, stock_code: str, stock_name: str, current_price: int, target_price: int, alert_type: str, alert_category: str):
        """가격 알림 발송"""
        change_rate = ((current_price - target_price) / target_price) * 100
        
        if alert_type == "TARGET_UP":
            message = f"{alert_category} 도달! 목표가 {target_price:,}원을 달성했습니다."
        elif alert_type == "STOP_LOSS":
            message = f"손절가 {target_price:,}원에 도달했습니다."
        elif alert_type == "TARGET_DOWN":
            message = f"하락 알림! {target_price:,}원 아래로 떨어졌습니다."
        else:
            message = f"가격 알림: {target_price:,}원"
        
        success = send_stock_alert(stock_name, current_price, change_rate, alert_type.lower(), message)
        if success:
            logger.info(f"가격 알림 발송 성공: {stock_name} - {message}")
        else:
            logger.error(f"가격 알림 발송 실패: {stock_name}")
    
    def send_parity_alert(self, stock_code: str, stock_name: str, current_price: int, parity_percent: int):
        """패리티 알림 발송"""
        message = f"패리티 {parity_percent}% 도달!"
        change_rate = 0.0  # 패리티는 변동률 대신 패리티 퍼센트 사용
        
        success = send_stock_alert(stock_name, current_price, change_rate, "parity", message)
        if success:
            logger.info(f"패리티 알림 발송 성공: {stock_name} - {parity_percent}%")
        else:
            logger.error(f"패리티 알림 발송 실패: {stock_name}")
    
    def send_daily_alert(self, stock_code: str, stock_name: str, current_price: int, change_percent: float, alert_type: str):
        """일간 급등/급락 알림 발송"""
        if alert_type == "SURGE":
            message = f"일간 급등 알림! {change_percent:+.2f}% 상승"
        else:
            message = f"일간 급락 알림! {change_percent:+.2f}% 하락"
        
        success = send_stock_alert(stock_name, current_price, change_percent, alert_type.lower(), message)
        if success:
            logger.info(f"일간 알림 발송 성공: {stock_name} - {message}")
        else:
            logger.error(f"일간 알림 발송 실패: {stock_name}")
    
    def update_stock_price(self, stock_code: str) -> Dict:
        """개별 종목 가격 업데이트"""
        stock_info = self.monitoring_stocks.get(stock_code, {})
        if not stock_info.get('enabled', True):
            return stock_info
        
        stock_name = stock_info.get('name', self.get_stock_name(stock_code))
        previous_price = stock_info.get('current_price', 0)
        
        # 주가 조회
        current_price, change_percent, error = self.get_stock_price(stock_code)
        
        if current_price is not None:
            # 정보 업데이트
            stock_info.update({
                'current_price': current_price,
                'change_percent': change_percent,
                'last_updated': datetime.now().isoformat(),
                'error': None
            })
            
            # 알림 가격 설정 (없는 경우)
            if not stock_info.get('alert_prices'):
                self.setup_alert_prices(stock_info, current_price)
            
            # 알림 체크
            if previous_price > 0:
                self.check_price_alerts(stock_code, stock_name, current_price, previous_price, stock_info)
            
        else:
            stock_info['error'] = error
            logger.warning(f"주가 조회 실패: {stock_name} ({stock_code}) - {error}")
        
        self.monitoring_stocks[stock_code] = stock_info
        return stock_info
    
    def update_all_stocks(self) -> Dict[str, Dict]:
        """모든 종목 가격 업데이트"""
        logger.info("모든 모니터링 종목 가격 업데이트 시작")
        
        updated_stocks = {}
        enabled_stocks = [code for code, info in self.monitoring_stocks.items() if info.get('enabled', True)]
        
        for stock_code in enabled_stocks:
            try:
                updated_info = self.update_stock_price(stock_code)
                updated_stocks[stock_code] = updated_info
                time.sleep(0.5)  # API 부하 방지
            except Exception as e:
                logger.error(f"종목 {stock_code} 업데이트 실패: {e}")
        
        # 업데이트된 데이터 저장
        self.save_monitoring_stocks(self.monitoring_stocks)
        
        logger.info(f"가격 업데이트 완료: {len(updated_stocks)}개 종목")
        return updated_stocks
    
    def get_monitoring_stocks(self) -> Dict:
        """모니터링 종목 목록 반환"""
        return self.monitoring_stocks.copy()
    
    def add_stock(self, stock_code: str, stock_name: str = None, target_price: int = 0, stop_loss: int = 0, category: str = "주식") -> bool:
        """모니터링 종목 추가"""
        try:
            if stock_name is None:
                stock_name = self.get_stock_name(stock_code)
            
            self.monitoring_stocks[stock_code] = {
                'name': stock_name,
                'target_price': target_price,
                'stop_loss': stop_loss,
                'category': category,
                'enabled': True,
                'current_price': 0,
                'change_percent': 0.0,
                'last_updated': None,
                'triggered_alerts': set(),
                'alert_prices': [],
                'daily_alert_enabled': True
            }
            
            self.save_monitoring_stocks(self.monitoring_stocks)
            logger.info(f"모니터링 종목 추가: {stock_name} ({stock_code})")
            return True
            
        except Exception as e:
            logger.error(f"종목 추가 실패: {e}")
            return False
    
    def remove_stock(self, stock_code: str) -> bool:
        """모니터링 종목 제거"""
        try:
            if stock_code in self.monitoring_stocks:
                stock_name = self.monitoring_stocks[stock_code].get('name', stock_code)
                del self.monitoring_stocks[stock_code]
                self.save_monitoring_stocks(self.monitoring_stocks)
                logger.info(f"모니터링 종목 제거: {stock_name} ({stock_code})")
                return True
            return False
            
        except Exception as e:
            logger.error(f"종목 제거 실패: {e}")
            return False

# 전역 인스턴스
stock_monitor = StockMonitor()

def update_all_stocks() -> Dict[str, Dict]:
    """모든 종목 가격 업데이트 (편의 함수)"""
    return stock_monitor.update_all_stocks()

def get_monitoring_stocks() -> Dict:
    """모니터링 종목 목록 조회 (편의 함수)"""
    return stock_monitor.get_monitoring_stocks()

def add_monitoring_stock(stock_code: str, stock_name: str = None, target_price: int = 0, stop_loss: int = 0, category: str = "주식") -> bool:
    """모니터링 종목 추가 (편의 함수)"""
    return stock_monitor.add_stock(stock_code, stock_name, target_price, stop_loss, category)

def remove_monitoring_stock(stock_code: str) -> bool:
    """모니터링 종목 제거 (편의 함수)"""
    return stock_monitor.remove_stock(stock_code)