"""
주식 모니터링 모듈
기존 simple_stock_manager_integrated.py의 핵심 로직을 웹 환경에 맞게 리팩토링
"""
import json
import logging
import os
import requests
import time
import threading
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
    REQUEST_TIMEOUT,
    STOCK_DATA_SCHEMA,
    STOCK_CATEGORIES,
    DEFAULT_STOCK_CATEGORY,
    DEFAULT_ALERT_SETTINGS,
    MIGRATION_VERSION,
    BACKUP_ENABLED
)
from .email_utils import (
    send_stock_alert, 
    send_parity_alert_enhanced, 
    send_volatility_alert, 
    send_target_stop_alert_enhanced
)

# PyKrx 가용성 확인
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# 개선된 로깅 시스템 적용
from .logger_utils import get_logger, performance_monitor, log_exception

# 로거 설정
logger = get_logger('stock')

class StockMonitor:
    """주식 모니터링 클래스"""
    
    def __init__(self):
        self.monitoring_stocks_file = MONITORING_STOCKS_FILE
        self.lock_file = self.monitoring_stocks_file + '.lock'
        
        # 일일 내역 파일 경로
        self.daily_history_file = os.path.join(os.path.dirname(MONITORING_STOCKS_FILE), 'daily_history.json')
        self.daily_history_lock_file = self.daily_history_file + '.lock'
        
        # 데이터 디렉토리 생성
        os.makedirs(os.path.dirname(self.monitoring_stocks_file), exist_ok=True)
        
        # 초기 데이터 로드
        self.monitoring_stocks = self.load_monitoring_stocks()
        
        # 실시간 모니터링 관련 변수
        self.is_monitoring = False
        self.monitoring_thread = None
        self.monitor_interval = 10  # 10초 간격
        self.last_daily_report_date = None
        
        # 주기적 데이터 저장 관련 변수
        self.last_save_time = datetime.now()
        self.save_interval = 60  # 60초 간격으로 데이터 저장
        self.save_counter = 0
    
    def calculate_return_rate(self, current_price: float, acquisition_price: float) -> float:
        """
        취득가 대비 수익률 계산
        
        Args:
            current_price (float): 현재가
            acquisition_price (float): 취득가
            
        Returns:
            float: 수익률 (백분율)
        """
        if acquisition_price is None or acquisition_price <= 0:
            return 0.0
            
        if current_price is None or current_price <= 0:
            return 0.0
            
        try:
            return_rate = ((current_price - acquisition_price) / acquisition_price) * 100
            return round(return_rate, 2)
        except (TypeError, ZeroDivisionError):
            return 0.0
    
    def calculate_stop_loss(self, acquisition_price: float, stop_loss_percent: float = -5.0) -> float:
        """
        취득가 기준 손절가 계산
        
        Args:
            acquisition_price (float): 취득가
            stop_loss_percent (float): 손절가 퍼센트 (기본값: -5%)
            
        Returns:
            float: 계산된 손절가
        """
        if acquisition_price is None or acquisition_price <= 0:
            return 0.0
            
        try:
            stop_loss_price = acquisition_price * (1 + stop_loss_percent / 100)
            return round(stop_loss_price, 0)  # 정수로 반올림
        except (TypeError, ZeroDivisionError):
            return 0.0
    
    def get_stop_loss_options(self) -> List[Dict[str, any]]:
        """
        손절가 설정 옵션 제공
        
        Returns:
            List[Dict]: 손절가 옵션 목록
        """
        return [
            {'value': -5, 'label': '-5%', 'description': '취득가 대비 5% 하락'},
            {'value': -10, 'label': '-10%', 'description': '취득가 대비 10% 하락'},
            {'value': 'custom', 'label': '직접입력', 'description': '사용자 지정 손절가'}
        ]
    
    def apply_stop_loss_setting(self, stock_code: str, stop_loss_option: any, custom_value: float = None) -> bool:
        """
        종목에 손절가 설정 적용
        
        Args:
            stock_code (str): 종목코드
            stop_loss_option: 손절가 옵션 (-5, -10, 'custom')
            custom_value (float): 직접입력 시 손절가 값
            
        Returns:
            bool: 적용 성공 여부
        """
        try:
            if stock_code not in self.monitoring_stocks:
                logger.error(f"존재하지 않는 종목: {stock_code}")
                return False
                
            stock_info = self.monitoring_stocks[stock_code]
            acquisition_price = stock_info.get('acquisition_price', 0)
            
            if stop_loss_option == 'custom':
                if custom_value is None or custom_value <= 0:
                    logger.error("직접입력 시 유효한 손절가 값이 필요합니다")
                    return False
                new_stop_loss = float(custom_value)
            else:
                if acquisition_price <= 0:
                    logger.warning(f"취득가가 설정되지 않은 종목: {stock_code}, 기본 동작 유지")
                    return True  # 취득가가 0인 경우 기본 동작 유지
                    
                stop_loss_percent = float(stop_loss_option)
                new_stop_loss = self.calculate_stop_loss(acquisition_price, stop_loss_percent)
            
            # 손절가 업데이트
            stock_info['stop_loss'] = new_stop_loss
            
            # 변경사항 저장
            self.save_monitoring_stocks(self.monitoring_stocks)
            
            stock_name = stock_info.get('name', stock_code)
            logger.info(f"손절가 설정 적용: {stock_name} ({stock_code}) - {new_stop_loss:,.0f}원")
            
            return True
            
        except Exception as e:
            logger.error(f"손절가 설정 적용 실패: {e}")
            return False
    
    def get_stock_category_display(self, category_key: str) -> str:
        """
        주식 카테고리 표시명 반환
        
        Args:
            category_key (str): 카테고리 키
            
        Returns: 
            str: 카테고리 표시명
        """
        from .config import STOCK_CATEGORIES, DEFAULT_STOCK_CATEGORY
        
        if category_key in STOCK_CATEGORIES:
            return STOCK_CATEGORIES[category_key]
        return STOCK_CATEGORIES.get(DEFAULT_STOCK_CATEGORY, '기타')
    
    def is_market_time(self) -> bool:
        """
        주식 시장 시간대(9:00-15:30) 체크
        
        Returns:
            bool: 시장 시간 내이면 True, 아니면 False
        """
        now = datetime.now()
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def can_send_stock_alert(self, stock_code: str, alert_type: str) -> bool:
        """
        주식 알림 발송 가능 여부 체크 (시간 제한 + 중복 방지)
        
        Args:
            stock_code (str): 종목 코드
            alert_type (str): 알림 유형 (surge, drop, target, stop_loss 등)
            
        Returns:
            bool: 알림 발송 가능하면 True, 아니면 False
        """
        # 1. 시장 시간 체크
        if not self.is_market_time():
            logger.debug(f"시장 시간 외로 인한 알림 제한: {stock_code}_{alert_type}")
            return False
            
        # 2. 당일 중복 알림 체크
        today = datetime.now().date()
        alert_key = f"{stock_code}_{alert_type}_{today}"
        
        # 당일 발송된 알림 목록에서 확인
        if hasattr(self, 'sent_alerts_today'):
            if alert_key in self.sent_alerts_today:
                logger.debug(f"당일 중복 알림 방지: {alert_key}")
                return False
        else:
            # 당일 알림 추적 세트 초기화
            self.sent_alerts_today = set()
            
        return True
    
    def mark_alert_sent(self, stock_code: str, alert_type: str):
        """
        알림 발송 완료 후 마킹 처리
        
        Args:
            stock_code (str): 종목 코드
            alert_type (str): 알림 유형
        """
        today = datetime.now().date()
        alert_key = f"{stock_code}_{alert_type}_{today}"
        
        if not hasattr(self, 'sent_alerts_today'):
            self.sent_alerts_today = set()
            
        self.sent_alerts_today.add(alert_key)
        logger.info(f"알림 발송 마킹: {alert_key}")
    
    def reset_daily_alerts_if_needed(self):
        """
        새로운 날이 시작되면 당일 알림 목록 초기화
        """
        today = datetime.now().date()
        
        if not hasattr(self, 'last_alert_reset_date'):
            self.last_alert_reset_date = today
            self.sent_alerts_today = set()
        elif self.last_alert_reset_date != today:
            logger.info(f"새로운 날이 시작: {today}, 당일 알림 목록 초기화") 
            self.sent_alerts_today = set()
            self.last_alert_reset_date = today
    
    def load_monitoring_stocks(self) -> Dict:
        """모니터링 주식 데이터 로드 (확장된 스키마 지원)"""
        try:
            if os.path.exists(self.monitoring_stocks_file):
                with FileLock(self.lock_file):
                    with open(self.monitoring_stocks_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # 데이터 마이그레이션 및 검증
                        migrated_data = self._migrate_stock_data(data)
                        
                        # triggered_alerts를 set으로 변환
                        for code, info in migrated_data.items():
                            if "triggered_alerts" in info and isinstance(info["triggered_alerts"], list):
                                info["triggered_alerts"] = set(info["triggered_alerts"])
                        
                        logger.info(f"모니터링 주식 데이터 로드: {len(migrated_data)}개 종목")
                        return migrated_data
            else:
                # 기본 데이터로 초기화
                logger.info("모니터링 주식 파일이 없어 기본 데이터로 초기화")
                default_data = self._create_default_stocks_data()
                self.save_monitoring_stocks(default_data)
                return default_data
                
        except Exception as e:
            logger.error(f"모니터링 주식 데이터 로드 실패: {e}")
            return {}
    
    def _migrate_stock_data(self, data: Dict) -> Dict:
        """기존 데이터를 새 스키마로 마이그레이션"""
        migrated_data = {}
        migration_count = 0
        
        for code, info in data.items():
            try:
                # 기존 데이터 구조 확인
                migrated_info = self._validate_and_migrate_stock_info(code, info)
                migrated_data[code] = migrated_info
                
                # 마이그레이션이 필요했던 경우 카운트
                if self._needs_migration(info):
                    migration_count += 1
                    
            except Exception as e:
                logger.error(f"종목 {code} 마이그레이션 실패: {e}")
                continue
        
        if migration_count > 0:
            logger.info(f"데이터 마이그레이션 완료: {migration_count}개 종목")
            
            # 백업 생성 (옵션)
            if BACKUP_ENABLED:
                self._create_backup()
        
        return migrated_data
    
    def _validate_and_migrate_stock_info(self, code: str, info: Dict) -> Dict:
        """개별 종목 정보 검증 및 마이그레이션"""
        migrated_info = {}
        
        # 필수 필드 처리
        migrated_info['name'] = info.get('name', f'종목 {code}')
        migrated_info['target_price'] = float(info.get('target_price', 0))
        migrated_info['stop_loss'] = float(info.get('stop_loss', 0))
        migrated_info['enabled'] = bool(info.get('enabled', True))
        
        # 새로운 필드들 (기본값 설정)
        migrated_info['category'] = self._validate_category(info.get('category', DEFAULT_STOCK_CATEGORY))
        migrated_info['acquisition_price'] = float(info.get('acquisition_price', 0))
        migrated_info['alert_settings'] = self._validate_alert_settings(info.get('alert_settings', {}))
        migrated_info['memo'] = str(info.get('memo', ''))
        
        # 시스템 관리 필드들
        migrated_info['current_price'] = float(info.get('current_price', 0))
        migrated_info['change_percent'] = float(info.get('change_percent', 0.0))
        migrated_info['last_updated'] = info.get('last_updated')
        migrated_info['triggered_alerts'] = info.get('triggered_alerts', [])
        migrated_info['alert_prices'] = info.get('alert_prices', [])
        migrated_info['error'] = info.get('error')
        
        # 추가 필드들
        migrated_info['daily_alert_enabled'] = bool(info.get('daily_alert_enabled', True))
        
        return migrated_info
    
    def _validate_category(self, category: str) -> str:
        """카테고리 유효성 검증"""
        if category in STOCK_CATEGORIES:
            return category
        
        # "기타" 카테고리를 "주식"으로 마이그레이션
        if category == "기타":
            return "주식"
        
        # 기존 "주식" 카테고리를 "주식"으로 매핑 (유지)
        if category in ["주식", "stock", "equity"]:
            return "주식"
        return DEFAULT_STOCK_CATEGORY
    
    def _validate_alert_settings(self, alert_settings: Dict) -> Dict:
        """알림 설정 유효성 검증"""
        validated_settings = DEFAULT_ALERT_SETTINGS.copy()
        
        if isinstance(alert_settings, dict):
            for key, value in alert_settings.items():
                if key in DEFAULT_ALERT_SETTINGS:
                    try:
                        # 타입에 따른 검증
                        if isinstance(DEFAULT_ALERT_SETTINGS[key], bool):
                            validated_settings[key] = bool(value)
                        elif isinstance(DEFAULT_ALERT_SETTINGS[key], (int, float)):
                            validated_settings[key] = float(value)
                        else:
                            validated_settings[key] = value
                    except (ValueError, TypeError):
                        logger.warning(f"알림 설정 {key} 값이 유효하지 않음: {value}")
        
        return validated_settings
    
    def _needs_migration(self, info: Dict) -> bool:
        """마이그레이션이 필요한지 확인"""
        required_new_fields = ['category', 'acquisition_price', 'alert_settings', 'memo']
        return not all(field in info for field in required_new_fields)
    
    def _create_default_stocks_data(self) -> Dict:
        """기본 주식 데이터 생성 (확장된 스키마)"""
        default_data = {}
        
        for stock in DEFAULT_MONITORING_STOCKS:
            default_data[stock['code']] = {
                'name': stock['name'],
                'target_price': float(stock['target_price']),
                'stop_loss': float(stock['stop_loss']),
                'enabled': bool(stock['enabled']),
                'category': DEFAULT_STOCK_CATEGORY,
                'acquisition_price': 0.0,
                'alert_settings': DEFAULT_ALERT_SETTINGS.copy(),
                'memo': '',
                'current_price': 0.0,
                'change_percent': 0.0,
                'last_updated': None,
                'triggered_alerts': set(),
                'alert_prices': [],
                'error': None,
                'daily_alert_enabled': True
            }
        
        return default_data
    
    def _create_backup(self):
        """데이터 백업 생성"""
        try:
            if os.path.exists(self.monitoring_stocks_file):
                backup_filename = f"{self.monitoring_stocks_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.monitoring_stocks_file, backup_filename)
                logger.info(f"데이터 백업 생성: {backup_filename}")
        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
    
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
    
    def save_monitoring_stocks_with_metadata(self, data: Dict):
        """메타데이터를 포함한 모니터링 주식 데이터 저장"""
        try:
            # set을 list로 변환하여 JSON 직렬화 가능하게 만듦
            serializable_data = {}
            for code, info in data.items():
                serializable_info = info.copy()
                if 'triggered_alerts' in serializable_info and isinstance(serializable_info['triggered_alerts'], set):
                    serializable_info['triggered_alerts'] = list(serializable_info['triggered_alerts'])
                serializable_data[code] = serializable_info
            
            # 메타데이터 추가
            output_data = {
                '_metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'update_count': getattr(self, 'save_counter', 0),
                    'total_stocks': len(data),
                    'enabled_stocks': len([code for code, info in data.items() if info.get('enabled', True)]),
                    'data_version': '1.0'
                },
                'stocks': serializable_data
            }
            
            with FileLock(self.lock_file):
                with open(self.monitoring_stocks_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                    
            logger.debug(f"메타데이터 포함 모니터링 주식 데이터 저장: {len(data)}개 종목")
            
        except Exception as e:
            logger.error(f"메타데이터 포함 모니터링 주식 데이터 저장 실패: {e}")
    
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
        """시장 개장 시간 확인 (09:00-15:30)"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 주말 제외
        if now.weekday() >= 5:  # 5: 토요일, 6: 일요일
            return False
        
        # 한국 주식 시장 시간: 09:00-15:30
        return "09:00" <= current_time <= "15:30"
    
    def is_market_closing_time(self) -> bool:
        """장 종료 시간 확인 (15:30)"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        return current_time == "15:30" and now.weekday() < 5
    
    def normalize_category(self, category: str) -> str:
        """카테고리 명칭 표준화"""
        category_mapping = {
            '주식': '주식',
            'other': '주식',
            'stock': '주식',
            'mezzanine': '메자닌'
        }
        return category_mapping.get(category.lower(), category)
    
    def setup_alert_prices(self, stock_info: Dict, current_price: int):
        """알림 가격 설정 (메자닌/주식 구분)"""
        category = self.normalize_category(stock_info.get('category', '주식'))
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
        
        # 주식: TP/SL 없으면 Up/Down 알림 (5% 상승/하락)
        elif category == "주식" and len(alert_prices) == 0:
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
        """가격 알림 조건 확인 (확장된 알림 시스템)"""
        alert_triggered = False
        
        # 시장 시간 체크 (09:00-15:30)
        if not self.is_market_open():
            return False
        
        # 1. 패리티 알림 체크 (메자닌 전용)
        parity_alert = self.check_parity_alerts(stock_code, stock_info, current_price, previous_price)
        if parity_alert:
            alert_triggered = True
        
        # 2. 목표가/손절가 알림 체크
        target_stop_alert = self.check_target_stop_alerts(stock_code, stock_info, current_price, previous_price)
        if target_stop_alert:
            alert_triggered = True
        
        # 3. 급등급락 알림 체크
        volatility_alert = self.check_volatility_alerts(stock_code, stock_info, current_price)
        if volatility_alert:
            alert_triggered = True
        
        # 4. 기존 alert_prices 시스템 호환성 유지
        alert_prices = stock_info.get("alert_prices", [])
        if alert_prices:
            legacy_alert = self._check_legacy_alerts(stock_code, stock_name, current_price, previous_price, stock_info)
            if legacy_alert:
                alert_triggered = True
        
        return alert_triggered
    
    def _check_legacy_alerts(self, stock_code: str, stock_name: str, current_price: int, previous_price: int, stock_info: Dict) -> bool:
        """기존 alert_prices 시스템 체크 (호환성 유지)"""
        alert_prices = stock_info.get("alert_prices", [])
        triggered_alerts = stock_info.get("triggered_alerts", set())
        alert_triggered = False
        
        for alert in alert_prices:
            alert_id = alert.get("id", "")
            target_price = alert.get("price", 0)
            alert_type = alert.get("type", "")
            
            if alert_id in triggered_alerts:
                continue
            
            # TP/상승 알림
            if alert_type in ["TP Alert", "Up Alert"]:
                if current_price >= target_price and previous_price < target_price:
                    self.send_price_alert(stock_code, stock_name, current_price, target_price, "TARGET_UP", alert_type)
                    triggered_alerts.add(alert_id)
                    alert_triggered = True
            
            # SL/하락 알림  
            elif alert_type in ["SL Alert", "Down Alert"]:
                if current_price <= target_price and previous_price > target_price:
                    alert_msg_type = "STOP_LOSS" if alert_type == "SL Alert" else "TARGET_DOWN"
                    self.send_price_alert(stock_code, stock_name, current_price, target_price, alert_msg_type, alert_type)
                    triggered_alerts.add(alert_id)
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
    
    def add_stock(self, 
                  stock_code: str, 
                  stock_name: str = None, 
                  target_price: float = 0, 
                  stop_loss: float = 0, 
                  category: str = None,
                  acquisition_price: float = 0,
                  alert_settings: Dict = None,
                  memo: str = '',
                  conversion_price: float = 0) -> bool:
        """모니터링 종목 추가 (확장된 스키마 지원)"""
        try:
            if stock_name is None:
                stock_name = self.get_stock_name(stock_code)
            
            if category is None:
                category = DEFAULT_STOCK_CATEGORY
            
            if alert_settings is None:
                alert_settings = DEFAULT_ALERT_SETTINGS.copy()
            
            # 카테고리 유효성 검증
            validated_category = self._validate_category(category)
            validated_alert_settings = self._validate_alert_settings(alert_settings)
            
            self.monitoring_stocks[stock_code] = {
                'name': stock_name,
                'target_price': float(target_price),
                'stop_loss': float(stop_loss),
                'category': validated_category,
                'acquisition_price': float(acquisition_price),
                'alert_settings': validated_alert_settings,
                'memo': str(memo),
                'conversion_price': float(conversion_price),
                'enabled': True,
                'current_price': 0.0,
                'change_percent': 0.0,
                'last_updated': None,
                'triggered_alerts': set(),
                'alert_prices': [],
                'error': None,
                'daily_alert_enabled': True
            }
            
            self.save_monitoring_stocks(self.monitoring_stocks)
            logger.info(f"모니터링 종목 추가: {stock_name} ({stock_code}) - 카테고리: {validated_category}")
            return True
            
        except Exception as e:
            logger.error(f"종목 추가 실패: {e}")
            return False
    
    def update_stock_info(self, 
                         stock_code: str,
                         name: str = None,
                         target_price: float = None,
                         stop_loss: float = None,
                         category: str = None,
                         acquisition_price: float = None,
                         alert_settings: Dict = None,
                         memo: str = None,
                         enabled: bool = None) -> bool:
        """종목 정보 업데이트"""
        try:
            if stock_code not in self.monitoring_stocks:
                logger.error(f"존재하지 않는 종목: {stock_code}")
                return False
            
            stock_info = self.monitoring_stocks[stock_code]
            
            # 필드별 업데이트
            if name is not None:
                stock_info['name'] = str(name)
            if target_price is not None:
                stock_info['target_price'] = float(target_price)
            if stop_loss is not None:
                stock_info['stop_loss'] = float(stop_loss)
            if category is not None:
                stock_info['category'] = self._validate_category(category)
            if acquisition_price is not None:
                stock_info['acquisition_price'] = float(acquisition_price)
            if alert_settings is not None:
                stock_info['alert_settings'] = self._validate_alert_settings(alert_settings)
            if memo is not None:
                stock_info['memo'] = str(memo)
            if enabled is not None:
                stock_info['enabled'] = bool(enabled)
            
            self.save_monitoring_stocks(self.monitoring_stocks)
            logger.info(f"종목 정보 업데이트: {stock_info['name']} ({stock_code})")
            return True
            
        except Exception as e:
            logger.error(f"종목 정보 업데이트 실패: {e}")
            return False
    
    def get_stocks_by_category(self, category: str = None) -> Dict:
        """카테고리별 종목 조회"""
        if category is None:
            return self.monitoring_stocks.copy()
        
        filtered_stocks = {}
        for code, info in self.monitoring_stocks.items():
            if info.get('category') == category:
                filtered_stocks[code] = info
        
        return filtered_stocks
    
    def validate_stock_data(self, stock_data: Dict) -> Dict:
        """종목 데이터 유효성 검증"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 필수 필드 확인
            required_fields = ['name', 'target_price', 'stop_loss']
            for field in required_fields:
                if field not in stock_data:
                    validation_result['errors'].append(f"필수 필드 누락: {field}")
                    validation_result['valid'] = False
            
            # 숫자 필드 검증
            numeric_fields = ['target_price', 'stop_loss', 'acquisition_price', 'current_price', 'change_percent']
            for field in numeric_fields:
                if field in stock_data:
                    try:
                        float(stock_data[field])
                    except (ValueError, TypeError):
                        validation_result['errors'].append(f"숫자 필드 오류: {field}")
                        validation_result['valid'] = False
            
            # 카테고리 검증
            if 'category' in stock_data:
                if stock_data['category'] not in STOCK_CATEGORIES:
                    validation_result['warnings'].append(f"알 수 없는 카테고리: {stock_data['category']}")
            
            # 목표가와 손절가 논리 검증
            if 'target_price' in stock_data and 'stop_loss' in stock_data:
                try:
                    tp = float(stock_data['target_price'])
                    sl = float(stock_data['stop_loss'])
                    if tp > 0 and sl > 0 and tp <= sl:
                        validation_result['warnings'].append("목표가가 손절가보다 낮거나 같습니다")
                except (ValueError, TypeError):
                    pass
            
        except Exception as e:
            validation_result['errors'].append(f"검증 중 오류: {e}")
            validation_result['valid'] = False
        
        return validation_result
    
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
    
    def start_real_time_monitoring(self):
        """실시간 모니터링 시작"""
        if self.is_monitoring:
            logger.warning("실시간 모니터링이 이미 실행 중입니다")
            return False
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("실시간 주식 모니터링 시작")
        return True
    
    def stop_real_time_monitoring(self):
        """실시간 모니터링 중지"""
        if not self.is_monitoring:
            logger.warning("실시간 모니터링이 실행되지 않고 있습니다")
            return False
        
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("실시간 주식 모니터링 중지")
        return True
    
    def _monitoring_loop(self):
        """모니터링 루프 (별도 스레드에서 실행)"""
        logger.info("모니터링 루프 시작")
        
        while self.is_monitoring:
            try:
                current_time = datetime.now()
                
                # 시장 시간 체크
                if self.is_market_open():
                    logger.debug("시장 개장 중 - 주가 업데이트 실행")
                    self._update_all_stocks_realtime()
                    
                    # 장 종료 시간에 일일 보고서 발송
                    if self.is_market_closing_time():
                        self._send_daily_report()
                else:
                    logger.debug("시장 폐장 중 - 대기")
                
                # 주기적 데이터 저장 체크 (60초마다)
                if (current_time - self.last_save_time).total_seconds() >= self.save_interval:
                    logger.debug("주기적 데이터 저장 실행")
                    self.save_monitoring_stocks_with_metadata(self.monitoring_stocks)
                    self.last_save_time = current_time
                    self.save_counter += 1
                    logger.info(f"데이터 주기 저장 완료: {self.save_counter}번째")
                
                # 10초 대기
                for _ in range(self.monitor_interval):
                    if not self.is_monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(self.monitor_interval)
        
        logger.info("모니터링 루프 종료")
    
    def _update_all_stocks_realtime(self):
        """실시간 모든 종목 업데이트 (모니터링 스레드용)"""
        try:
            enabled_stocks = [code for code, info in self.monitoring_stocks.items() if info.get('enabled', True)]
            
            for stock_code in enabled_stocks:
                if not self.is_monitoring:  # 모니터링 중지 시 즉시 종료
                    break
                
                try:
                    self.update_stock_price(stock_code)
                    time.sleep(0.5)  # API 부하 방지
                except Exception as e:
                    logger.error(f"실시간 업데이트 중 오류 - {stock_code}: {e}")
            
            # 업데이트된 데이터 저장
            self.save_monitoring_stocks(self.monitoring_stocks)
            
        except Exception as e:
            logger.error(f"실시간 전체 업데이트 실패: {e}")
    
    def _send_daily_report(self):
        """일일 보고서 발송"""
        try:
            today = datetime.now().date()
            
            # 이미 오늘 보고서를 발송했다면 스킵
            if self.last_daily_report_date == today:
                return
            
            logger.info("일일 주식 모니터링 보고서 생성 시작")
            
            # 오늘의 주요 변동사항 수집
            report_data = self._generate_daily_report_data()
            
            # 이메일 발송
            success = self._send_daily_report_email(report_data)
            
            if success:
                self.last_daily_report_date = today
                logger.info("일일 보고서 발송 완료")
            else:
                logger.error("일일 보고서 발송 실패")
                
        except Exception as e:
            logger.error(f"일일 보고서 생성 중 오류: {e}")
    
    def _generate_daily_report_data(self) -> Dict:
        """일일 보고서 데이터 생성"""
        today = datetime.now().date()
        report_data = {
            'date': today.strftime('%Y-%m-%d'),
            'total_stocks': len(self.monitoring_stocks),
            'active_stocks': len([s for s in self.monitoring_stocks.values() if s.get('enabled', True)]),
            'gainers': [],
            'losers': [],
            'alert_triggered': [],
            'summary': {}
        }
        
        # 각 종목별 분석
        for code, info in self.monitoring_stocks.items():
            if not info.get('enabled', True):
                continue
                
            change_percent = info.get('change_percent', 0)
            current_price = info.get('current_price', 0)
            
            stock_data = {
                'code': code,
                'name': info.get('name', code),
                'current_price': current_price,
                'change_percent': change_percent,
                'category': info.get('category', '주식')
            }
            
            # 상승/하락 분류 (3% 이상)
            if change_percent >= 3.0:
                report_data['gainers'].append(stock_data)
            elif change_percent <= -3.0:
                report_data['losers'].append(stock_data)
            
            # 오늘 트리거된 알림 확인
            if info.get('triggered_alerts'):
                stock_data['alerts'] = list(info.get('triggered_alerts', []))
                report_data['alert_triggered'].append(stock_data)
        
        # 정렬
        report_data['gainers'].sort(key=lambda x: x['change_percent'], reverse=True)
        report_data['losers'].sort(key=lambda x: x['change_percent'])
        
        # 요약 정보
        report_data['summary'] = {
            'gainers_count': len(report_data['gainers']),
            'losers_count': len(report_data['losers']),
            'alerts_count': len(report_data['alert_triggered'])
        }
        
        return report_data
    
    def _send_daily_report_email(self, report_data: Dict) -> bool:
        """일일 보고서 이메일 발송"""
        try:
            from .email_utils import send_daily_stock_report
            
            # 보고서 HTML 생성
            html_content = self._generate_report_html(report_data)
            
            # 이메일 발송
            subject = f"[D2 Dash] 일일 주식 모니터링 보고서 - {report_data['date']}"
            success = send_daily_stock_report(subject, html_content, report_data)
            
            return success
            
        except Exception as e:
            logger.error(f"일일 보고서 이메일 발송 중 오류: {e}")
            return False
    
    def _generate_report_html(self, report_data: Dict) -> str:
        """보고서 HTML 생성"""
        html = f"""
        <h2>📊 일일 주식 모니터링 보고서</h2>
        <p><strong>날짜:</strong> {report_data['date']}</p>
        <p><strong>모니터링 종목:</strong> {report_data['active_stocks']}/{report_data['total_stocks']}개</p>
        
        <h3>📈 주요 상승 종목 ({report_data['summary']['gainers_count']}개)</h3>
        <ul>
        """
        
        for stock in report_data['gainers']:
            html += f"<li><strong>{stock['name']} ({stock['code']})</strong>: {stock['current_price']:,}원 (+{stock['change_percent']:.2f}%)</li>"
        
        if not report_data['gainers']:
            html += "<li>3% 이상 상승한 종목이 없습니다.</li>"
        
        html += f"""
        </ul>
        
        <h3>📉 주요 하락 종목 ({report_data['summary']['losers_count']}개)</h3>
        <ul>
        """
        
        for stock in report_data['losers']:
            html += f"<li><strong>{stock['name']} ({stock['code']})</strong>: {stock['current_price']:,}원 ({stock['change_percent']:.2f}%)</li>"
        
        if not report_data['losers']:
            html += "<li>3% 이상 하락한 종목이 없습니다.</li>"
        
        html += f"""
        </ul>
        
        <h3>🚨 오늘 발생한 알림 ({report_data['summary']['alerts_count']}개)</h3>
        <ul>
        """
        
        for stock in report_data['alert_triggered']:
            alerts_str = ', '.join(stock.get('alerts', []))
            html += f"<li><strong>{stock['name']} ({stock['code']})</strong>: {alerts_str}</li>"
        
        if not report_data['alert_triggered']:
            html += "<li>오늘 발생한 알림이 없습니다.</li>"
        
        html += """
        </ul>
        
        <hr>
        <p><small>D2 Dash 투자 모니터링 시스템에서 자동 발송된 메일입니다.</small></p>
        """
        
        return html
    
    def get_monitoring_status(self) -> Dict:
        """모니터링 상태 정보 반환"""
        return {
            'is_monitoring': self.is_monitoring,
            'is_market_open': self.is_market_open(),
            'monitor_interval': self.monitor_interval,
            'active_stocks_count': len([s for s in self.monitoring_stocks.values() if s.get('enabled', True)]),
            'total_stocks_count': len(self.monitoring_stocks),
            'last_daily_report_date': self.last_daily_report_date.isoformat() if self.last_daily_report_date else None
        }
    
    def save_daily_alert(self, stock_code: str, stock_name: str, alert_type: str, message: str, 
                         current_price: int = 0, change_percent: float = 0.0) -> bool:
        """일일 알림 내역 저장"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # 기존 일일 내역 로드
            daily_history = self.load_daily_history()
            
            # 오늘 날짜 키가 없으면 생성
            if today not in daily_history['alerts']:
                daily_history['alerts'][today] = []
            
            # 새 알림 내역 추가
            alert_entry = {
                'time': current_time,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'alert_type': alert_type,
                'message': message,
                'current_price': current_price,
                'change_percent': change_percent,
                'timestamp': datetime.now().isoformat()
            }
            
            daily_history['alerts'][today].append(alert_entry)
            
            # 7일 이전 데이터 정리 (옵션)
            self._cleanup_old_alerts(daily_history, days_to_keep=7)
            
            # 파일에 저장
            with FileLock(self.daily_history_lock_file):
                with open(self.daily_history_file, 'w', encoding='utf-8') as f:
                    json.dump(daily_history, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"일일 알림 내역 저장: {stock_name} - {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"일일 알림 내역 저장 실패: {e}")
            return False
    
    def load_daily_history(self) -> Dict:
        """일일 내역 데이터 로드"""
        try:
            if os.path.exists(self.daily_history_file):
                with FileLock(self.daily_history_lock_file):
                    with open(self.daily_history_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # 기본 구조 확인 및 초기화
                        if 'alerts' not in data:
                            data['alerts'] = {}
                        if 'description' not in data:
                            data['description'] = "일일 알림 내역 저장 파일"
                        if 'version' not in data:
                            data['version'] = "1.0"
                        
                        return data
            else:
                # 기본 구조로 초기화
                default_data = {
                    "description": "일일 알림 내역 저장 파일",
                    "version": "1.0",
                    "alerts": {}
                }
                
                with FileLock(self.daily_history_lock_file):
                    with open(self.daily_history_file, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, ensure_ascii=False, indent=2)
                
                return default_data
                
        except Exception as e:
            logger.error(f"일일 내역 데이터 로드 실패: {e}")
            return {
                "description": "일일 알림 내역 저장 파일",
                "version": "1.0",
                "alerts": {}
            }
    
    def _cleanup_old_alerts(self, daily_history: Dict, days_to_keep: int = 7):
        """오래된 알림 내역 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            dates_to_remove = []
            for date_str in daily_history['alerts'].keys():
                if date_str < cutoff_str:
                    dates_to_remove.append(date_str)
            
            for date_str in dates_to_remove:
                del daily_history['alerts'][date_str]
                logger.debug(f"오래된 알림 내역 삭제: {date_str}")
                
        except Exception as e:
            logger.warning(f"오래된 알림 내역 정리 중 오류: {e}")
    
    def check_parity_alerts(self, stock_code: str, stock_info: Dict, current_price: int, previous_price: int) -> bool:
        """패리티 알림 체크 (메자닌 전용)"""
        if stock_info.get('category') != '메자닌':
            return False
        
        alert_settings = stock_info.get('alert_settings', {})
        if not alert_settings.get('parity_enabled', True):
            return False
        
        # 전환가격 확인
        conversion_price = stock_info.get('acquisition_price', 0)  # 취득가를 전환가격으로 사용
        if conversion_price <= 0:
            return False
        
        triggered_alerts = stock_info.get('triggered_alerts', set())
        alert_triggered = False
        
        # 패리티 임계값들 체크 (80%, 100%, 120%)
        parity_thresholds = [80, 100, 120]
        
        for threshold in parity_thresholds:
            alert_id = f"parity_{threshold}"
            if alert_id in triggered_alerts:
                continue
            
            # 패리티 계산
            current_parity = (current_price / conversion_price) * 100
            previous_parity = (previous_price / conversion_price) * 100 if previous_price > 0 else 0
            
            # 임계값 도달 체크
            if current_parity >= threshold and previous_parity < threshold:
                stock_name = stock_info.get('name', stock_code)
                
                # 확장된 패리티 알림 발송
                success = send_parity_alert_enhanced(
                    stock_name, stock_code, current_price, threshold, conversion_price
                )
                
                if success:
                    # 트리거된 알림 기록
                    triggered_alerts.add(alert_id)
                    
                    # 일일 내역 저장
                    self.save_daily_alert(
                        stock_code, stock_name, f"패리티_{threshold}%", 
                        f"패리티 {threshold}% 도달", current_price, 0.0
                    )
                    
                    alert_triggered = True
                    logger.info(f"패리티 알림 발송: {stock_name} - {threshold}%")
        
        return alert_triggered
    
    def check_target_stop_alerts(self, stock_code: str, stock_info: Dict, current_price: int, previous_price: int) -> bool:
        """목표가/손절가 알림 체크"""
        alert_settings = stock_info.get('alert_settings', {})
        if not alert_settings.get('target_stop_enabled', True):
            return False
        
        triggered_alerts = stock_info.get('triggered_alerts', set())
        alert_triggered = False
        stock_name = stock_info.get('name', stock_code)
        acquisition_price = stock_info.get('acquisition_price', 0)
        
        # 목표가 체크
        target_price = stock_info.get('target_price', 0)
        if target_price > 0:
            alert_id = f"target_price_{target_price}"
            if alert_id not in triggered_alerts:
                if current_price >= target_price and previous_price < target_price:
                    success = send_target_stop_alert_enhanced(
                        stock_name, stock_code, current_price, target_price, 
                        "target_price", acquisition_price
                    )
                    
                    if success:
                        triggered_alerts.add(alert_id)
                        self.save_daily_alert(
                            stock_code, stock_name, "목표가_달성", 
                            f"목표가 {target_price:,}원 달성", current_price
                        )
                        alert_triggered = True
                        logger.info(f"목표가 알림 발송: {stock_name} - {target_price:,}원")
        
        # 손절가 체크
        stop_loss = stock_info.get('stop_loss', 0)
        if stop_loss > 0:
            alert_id = f"stop_loss_{stop_loss}"
            if alert_id not in triggered_alerts:
                if current_price <= stop_loss and previous_price > stop_loss:
                    success = send_target_stop_alert_enhanced(
                        stock_name, stock_code, current_price, stop_loss, 
                        "stop_loss", acquisition_price
                    )
                    
                    if success:
                        triggered_alerts.add(alert_id)
                        self.save_daily_alert(
                            stock_code, stock_name, "손절가_도달", 
                            f"손절가 {stop_loss:,}원 도달", current_price
                        )
                        alert_triggered = True
                        logger.info(f"손절가 알림 발송: {stock_name} - {stop_loss:,}원")
        
        return alert_triggered
    
    def check_volatility_alerts(self, stock_code: str, stock_info: Dict, current_price: int) -> bool:
        """급등급락 알림 체크"""
        alert_settings = stock_info.get('alert_settings', {})
        if not alert_settings.get('volatility_enabled', True):
            return False
        
        change_percent = stock_info.get('change_percent', 0.0)
        triggered_alerts = stock_info.get('triggered_alerts', set())
        alert_triggered = False
        stock_name = stock_info.get('name', stock_code)
        
        # 급등 체크
        surge_threshold = alert_settings.get('surge_threshold', 5.0)
        surge_alert_id = f"surge_{datetime.now().strftime('%Y%m%d')}"
        
        if (change_percent >= surge_threshold and 
            surge_alert_id not in triggered_alerts):
            
            success = send_volatility_alert(
                stock_name, stock_code, current_price, change_percent, 
                "surge", surge_threshold
            )
            
            if success:
                triggered_alerts.add(surge_alert_id)
                self.save_daily_alert(
                    stock_code, stock_name, "급등", 
                    f"일일 급등 {change_percent:+.2f}%", current_price, change_percent
                )
                alert_triggered = True
                logger.info(f"급등 알림 발송: {stock_name} - {change_percent:+.2f}%")
        
        # 급락 체크
        drop_threshold = alert_settings.get('drop_threshold', -5.0)
        drop_alert_id = f"drop_{datetime.now().strftime('%Y%m%d')}"
        
        if (change_percent <= drop_threshold and 
            drop_alert_id not in triggered_alerts):
            
            success = send_volatility_alert(
                stock_name, stock_code, current_price, change_percent, 
                "drop", drop_threshold
            )
            
            if success:
                triggered_alerts.add(drop_alert_id)
                self.save_daily_alert(
                    stock_code, stock_name, "급락", 
                    f"일일 급락 {change_percent:+.2f}%", current_price, change_percent
                )
                alert_triggered = True
                logger.info(f"급락 알림 발송: {stock_name} - {change_percent:+.2f}%")
        
        return alert_triggered

    def get_daily_alert_history(self, target_date: str = None) -> Dict:
        """일일 알림 내역 조회"""
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        alert_history = {
            'date': target_date,
            'stock_alerts': [],
            'price_alerts': [],
            'daily_reports': [],
            'summary': {
                'total_alerts': 0,
                'stock_count': 0,
                'alert_types': {}
            }
        }
        
        try:
            # 종목별 트리거된 알림 수집
            for code, info in self.monitoring_stocks.items():
                triggered_alerts = info.get('triggered_alerts', set())
                if triggered_alerts:
                    stock_alert = {
                        'stock_code': code,
                        'stock_name': info.get('name', code),
                        'category': info.get('category', '주식'),
                        'current_price': info.get('current_price', 0),
                        'change_percent': info.get('change_percent', 0),
                        'triggered_alerts': list(triggered_alerts) if isinstance(triggered_alerts, set) else triggered_alerts,
                        'alert_count': len(triggered_alerts),
                        'last_updated': info.get('last_updated', '')
                    }
                    alert_history['stock_alerts'].append(stock_alert)
                    alert_history['summary']['total_alerts'] += len(triggered_alerts)
                    
                    # 알림 타입별 카운트
                    for alert_id in triggered_alerts:
                        alert_type = 'unknown'
                        if 'tp' in alert_id.lower():
                            alert_type = 'target_price'
                        elif 'sl' in alert_id.lower():
                            alert_type = 'stop_loss'
                        elif 'up' in alert_id.lower():
                            alert_type = 'price_up'
                        elif 'down' in alert_id.lower():
                            alert_type = 'price_down'
                        elif 'parity' in alert_id.lower():
                            alert_type = 'parity'
                        
                        alert_history['summary']['alert_types'][alert_type] = \
                            alert_history['summary']['alert_types'].get(alert_type, 0) + 1
            
            alert_history['summary']['stock_count'] = len(alert_history['stock_alerts'])
            
            # 가격 알림 내역 생성 (alert_prices에서 추출)
            for code, info in self.monitoring_stocks.items():
                alert_prices = info.get('alert_prices', [])
                for alert in alert_prices:
                    if alert.get('id') in info.get('triggered_alerts', set()):
                        price_alert = {
                            'stock_code': code,
                            'stock_name': info.get('name', code),
                            'alert_id': alert.get('id'),
                            'alert_type': alert.get('type', 'Unknown'),
                            'target_price': alert.get('price', 0),
                            'current_price': info.get('current_price', 0),
                            'category': alert.get('category', 'OTHER'),
                            'triggered_time': info.get('last_updated', '')
                        }
                        alert_history['price_alerts'].append(price_alert)
            
            return alert_history
            
        except Exception as e:
            logger.error(f"일일 알림 내역 조회 실패: {e}")
            return alert_history

# 전역 인스턴스
stock_monitor = StockMonitor()

@performance_monitor('주식 가격 업데이트')
@log_exception('stock')
def update_all_stocks() -> Dict[str, Dict]:
    """모든 종목 가격 업데이트 (편의 함수)"""
    return stock_monitor.update_all_stocks()

def get_monitoring_stocks() -> Dict:
    """모니터링 종목 목록 조회 (편의 함수)"""
    return stock_monitor.get_monitoring_stocks()

def add_monitoring_stock(stock_code: str, 
                        stock_name: str = None, 
                        target_price: float = 0, 
                        stop_loss: float = 0, 
                        category: str = None,
                        acquisition_price: float = 0,
                        alert_settings: Dict = None,
                        memo: str = '',
                        conversion_price: float = 0) -> bool:
    """모니터링 종목 추가 (편의 함수)"""
    return stock_monitor.add_stock(stock_code, stock_name, target_price, stop_loss, category, acquisition_price, alert_settings, memo, conversion_price)

def update_monitoring_stock(stock_code: str, **kwargs) -> bool:
    """모니터링 종목 정보 업데이트 (편의 함수)"""
    return stock_monitor.update_stock_info(stock_code, **kwargs)

def get_stocks_by_category(category: str = None) -> Dict:
    """카테고리별 종목 조회 (편의 함수)"""
    return stock_monitor.get_stocks_by_category(category)

def validate_stock_data(stock_data: Dict) -> Dict:
    """종목 데이터 유효성 검증 (편의 함수)"""
    return stock_monitor.validate_stock_data(stock_data)

def remove_monitoring_stock(stock_code: str) -> bool:
    """모니터링 종목 제거 (편의 함수)"""
    return stock_monitor.remove_stock(stock_code)

def get_daily_alert_history(target_date: str = None) -> Dict:
    """일일 알림 내역 조회 (편의 함수)"""
    return stock_monitor.get_daily_alert_history(target_date)

def save_daily_alert(stock_code: str, stock_name: str, alert_type: str, message: str, 
                     current_price: int = 0, change_percent: float = 0.0) -> bool:
    """일일 알림 내역 저장 (편의 함수)"""
    return stock_monitor.save_daily_alert(stock_code, stock_name, alert_type, message, current_price, change_percent)