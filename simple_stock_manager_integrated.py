"""
간단한 주식 알림 관리자 (Simple Stock Alert Manager)
웹 인터페이스 없이 종목 추가, 삭제, 알림 설정을 관리할 수 있는 간단한 GUI 프로그램
모듈별로 분할된 코드를 통합하는 메인 파일
"""
import os
import sys
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
from filelock import FileLock
import importlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# 트레이 아이콘 관련
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_manager.log', mode='w', encoding='utf-8'),  # 'w'로 변경
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleStockManager")

# 파일 경로 설정 (실행파일/파이썬 모두 지원)
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
STOCKS_FILE = os.path.join(BASE_PATH, "monitoring_stocks.json")
NOTIFICATIONS_FILE = os.path.join(BASE_PATH, "notifications.json")
EMAIL_CONFIG_FILE = os.path.join(BASE_PATH, "email_config.json")
os.makedirs(BASE_PATH, exist_ok=True)

# 전역 변수
monitoring_stocks = {}
notifications = []
daemon_process = None
update_thread = None
is_running = False
update_event = None

# PyKrx 사용 가능 여부 확인
try:
    pykrx_spec = importlib.util.find_spec("pykrx")
    if pykrx_spec is not None:
        from pykrx import stock
        PYKRX_AVAILABLE = True
        logger.info("PyKrx 라이브러리 로드 성공")
    else:
        PYKRX_AVAILABLE = False
        logger.warning("PyKrx 라이브러리가 설치되어 있지 않습니다.")
except ImportError:
    PYKRX_AVAILABLE = False
    logger.warning("PyKrx 라이브러리가 설치되어 있지 않습니다.")

#############################
# Part 1: 기본 유틸리티 함수들
#############################

# PyKrx로 주가 정보 가져오기
def get_stock_price_pykrx(stock_code):
    if not PYKRX_AVAILABLE:
        logger.warning("PyKrx 라이브러리가 설치되지 않았습니다.")
        return None, 0.0, "PyKrx 라이브러리가 설치되지 않았습니다."
    try:
        today = datetime.now()
        for i in range(10):
            date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            try:
                logger.info(f"pykrx 시도: code={stock_code}, date={date_str}")
                ticker_name = stock.get_market_ticker_name(stock_code)
                logger.info(f"pykrx ticker_name: {ticker_name}")
                df = stock.get_market_ohlcv_by_date(date_str, date_str, stock_code)
                logger.info(f"pykrx DataFrame: {df}")
                if df is not None and not df.empty:
                    current_price = int(df.iloc[0]['종가'])
                    change_percent = float(df.iloc[0]['등락률']) if '등락률' in df.columns else 0.0
                    logger.info(f"PyKrx로부터 {stock_code} 정보 조회: 현재가={current_price}, 등락률={change_percent}%")
                    return current_price, change_percent, None
                else:
                    logger.error(f"pykrx DataFrame이 비어있음: code={stock_code}, date={date_str}")
            except Exception as e:
                logger.error(f"pykrx 예외: code={stock_code}, date={date_str}, error={e}")
                continue
        logger.error(f"최근 10일간 {stock_code}의 거래 데이터를 찾을 수 없습니다.")
        return None, 0.0, "거래 데이터를 찾을 수 없습니다."
    except Exception as e:
        logger.error(f"PyKrx 사용 중 오류 발생: {e}")
        return None, 0.0, f"오류 발생: {e}"

# 주가 정보를 가져오는 통합 함수 - PyKrx 우선, 실패 시 네이버 크롤링 시도
def get_stock_price(stock_code):
    try:
        if PYKRX_AVAILABLE:
            current_price, change_percent, error = get_stock_price_pykrx(stock_code)
            if current_price is not None:
                return current_price, change_percent, None
            logger.warning(f"PyKrx로 {stock_code} 정보 가져오기 실패, 네이버 크롤링 시도")
        current_price, change_percent, error = get_stock_price_naver(stock_code)
        if current_price is not None:
            return current_price, change_percent, None
        return None, 0.0, error or "주가 정보를 가져올 수 없습니다."
    except Exception as e:
        logger.error(f"주가 정보 가져오기 오류: {e}")
        return None, 0.0, f"오류 발생: {e}"

# 종목명 가져오기
def get_stock_name(stock_code):
    """네이버 금융에서 종목명을 가져옵니다."""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
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
        logger.error(f"종목명 가져오기 오류: {e}")
        return f"종목 {stock_code}"

# 데이터 로드
def load_data():
    """모니터링 데이터를 파일에서 로드합니다."""
    global monitoring_stocks, notifications
    
    try:
        if os.path.exists(STOCKS_FILE):
            with FileLock(STOCKS_FILE + ".lock"):
                with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                    try:
                        stocks_data = json.load(f)
                    except Exception as e:
                        print(f"[print] monitoring_stocks.json 파싱 오류: {e}")
                        raise
                    if stocks_data and isinstance(stocks_data, dict):
                        for code, info in stocks_data.items():
                            if "triggered_alerts" in info and isinstance(info["triggered_alerts"], list):
                                info["triggered_alerts"] = set(info["triggered_alerts"])
                        monitoring_stocks = stocks_data
                        
        if os.path.exists(NOTIFICATIONS_FILE):
            with FileLock(NOTIFICATIONS_FILE + ".lock"):
                with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        print(f"[print] notifications.json 파싱 오류: {e}")
                        raise
                    if data and isinstance(data, list):
                        notifications = data
        
        logger.info(f"데이터 로드 완료. 종목 수: {len(monitoring_stocks)}, 알림 수: {len(notifications)}")
        return True
    except Exception as e:
        logger.error(f"데이터 로드 오류: {e}")
        messagebox.showerror("데이터 로드 오류", f"파일을 로드하는 중 오류가 발생했습니다:{e}")
        return False

# 데이터 저장
def save_data():
    """모니터링 데이터를 파일에 저장합니다."""
    global monitoring_stocks, notifications
    
    try:
        # set -> list 변환
        serializable_stocks = {}
        for code, info in monitoring_stocks.items():
            serializable_info = info.copy()
            if "triggered_alerts" in serializable_info and isinstance(serializable_info["triggered_alerts"], set):
                serializable_info["triggered_alerts"] = list(serializable_info["triggered_alerts"])
            serializable_stocks[code] = serializable_info
        
        with FileLock(STOCKS_FILE + ".lock"):
            with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_stocks, f, ensure_ascii=False, indent=2)
        
        with FileLock(NOTIFICATIONS_FILE + ".lock"):
            with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, ensure_ascii=False, indent=2)
        
        logger.info("데이터 저장 완료")
        return True
    except Exception as e:
        logger.error(f"데이터 저장 오류: {e}")
        messagebox.showerror("데이터 저장 오류", f"파일을 저장하는 중 오류가 발생했습니다:{e}")
        return False

#############################
# Part 2: 종목 관리 및 알림 기능
#############################

# 종목 추가 함수
def add_stock(stock_code, tp_price=0, sl_price=0, memo="", parity_percents=[80, 100, 120], conversion_price=0, conversion_price_floor=0, daily_alert_enabled=True, daily_up_threshold=5, daily_down_threshold=-5, category="기타"):
    """새 종목을 모니터링 목록에 추가합니다."""
    global monitoring_stocks
    
    if stock_code in monitoring_stocks:
        messagebox.showwarning("경고", f"종목코드 {stock_code}는 이미 모니터링 중입니다.")
        return False
    
    if not (stock_code.isdigit() and len(stock_code) == 6):
        messagebox.showwarning("경고", "종목코드는 6자리 숫자여야 합니다.")
        return False
    
    # pykrx에서 종목명 확인
    ticker_name = None
    if PYKRX_AVAILABLE:
        try:
            ticker_name = stock.get_market_ticker_name(stock_code)
        except Exception as e:
            logger.error(f"pykrx 종목명 조회 오류: {e}")
    if not ticker_name:
        messagebox.showwarning("경고", f"pykrx에서 종목명을 찾을 수 없습니다. 올바른 상장 종목코드만 추가 가능합니다.")
        return False
    
    try:
        stock_name = get_stock_name(stock_code)
        current_price, change_percent, error = get_stock_price(stock_code)
        if error:
            messagebox.showwarning("경고", f"주가 정보를 가져오지 못했습니다: {error}")
            return False
        
        # 알림 가격 설정
        alert_prices = []
        
        # 목표가(TP) 알림 설정
        if tp_price > 0:
            alert_prices.append({
                "id": "tp0",
                "price": tp_price,
                "type": "TP Alert",
                "category": "TP"
            })
        
        # 손절가(SL) 알림 설정
        if sl_price > 0:
            alert_prices.append({
                "id": "sl0",
                "price": sl_price,
                "type": "SL Alert",
                "category": "SL"
            })
        
        # 메자닌이 아니면 Up/Down Alert(커스텀) 자동 추가
        if category != "메자닌" and not alert_prices:
            alert_prices.extend([
                {"id": f"up0_{stock_code}", "type": "Up Alert", "price": int(current_price * 1.05)},
                {"id": f"down0_{stock_code}", "type": "Down Alert", "price": int(current_price * 0.95)}
            ])
        
        # 패리티 알림 추가 (80/100/120만, floor는 제외)
        if category == "메자닌":
            for percent in [80, 100, 120]:
                alert_prices.append({
                    "id": f"parity{percent}",
                    "price": int(current_price * percent / 100),
                    "type": "Parity Alert",
                    "category": "PARITY",
                    "parity_percent": percent
                })
        elif parity_percents:
            for percent in parity_percents:
                alert_prices.append({
                    "id": f"parity{percent}",
                    "price": int(current_price * percent / 100),
                    "type": "Parity Alert",
                    "category": "PARITY",
                    "parity_percent": percent
                })
        
        # 이메일 주소 설정
        email_config = load_email_config()
        email = email_config["receiver"] if email_config else "ljm@inveski.com"
        
        # 모니터링 종목 추가
        monitoring_stocks[stock_code] = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": current_price,
            "change_percent": change_percent,
            "alert_prices": alert_prices,
            "email": email,
            "memo": memo,
            "status": "모니터링 중",
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "triggered_alerts": set(),
            "opening_price": current_price,  # 임시로 현재가를 시초가로 설정
            "daily_up_alert_sent": False,
            "daily_down_alert_sent": False,
            "last_daily_check_date": datetime.now().strftime("%Y-%m-%d"),
            "daily_alert_enabled": daily_alert_enabled,
            "daily_up_threshold": daily_up_threshold,
            "daily_down_threshold": daily_down_threshold,
            "conversion_price": conversion_price,
            "conversion_price_floor": conversion_price_floor,
            "category": category
        }
        
        # 데이터 저장
        save_data()
        
        logger.info(f"종목 추가 완료: {stock_name}({stock_code})")

        # --- 기존 메자닌 종목의 Up/Down Alert 자동 정리 ---
        for code, info in monitoring_stocks.items():
            if info.get("category") == "메자닌":
                info["alert_prices"] = [a for a in info.get("alert_prices", []) if a.get("category") == "PARITY"]
        save_data()
        
        return True
    except Exception as e:
        logger.error(f"종목 추가 오류: {e}")
        messagebox.showerror("오류", f"종목을 추가하는 중 오류가 발생했습니다:{e}")
        return False

# 종목 삭제 함수
def delete_stock(stock_code):
    """모니터링 목록에서 종목을 삭제합니다."""
    global monitoring_stocks
    
    if stock_code in monitoring_stocks:
        stock_name = monitoring_stocks[stock_code]["stock_name"]
        
        # 확인 메시지
        if messagebox.askyesno("확인", f"{stock_name}({stock_code})을(를) 정말 삭제하시겠습니까?"):
            del monitoring_stocks[stock_code]
            save_data()
            logger.info(f"종목 삭제 완료: {stock_name}({stock_code})")
            return True
    
    return False

# 이메일 설정 로드
def load_email_config():
    """이메일 설정을 로드합니다."""
    try:
        if os.path.exists(EMAIL_CONFIG_FILE):
            with open(EMAIL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except Exception as e:
                    print(f"[print] email_config.json 파싱 오류: {e}")
                    raise
        return None
    except Exception as e:
        logger.error(f"이메일 설정 로드 오류: {e}")
        return None

# 이메일 설정 저장
def save_email_config(sender, password, receiver):
    """이메일 설정을 저장합니다."""
    try:
        config = {
            "sender": sender,
            "password": password,
            "receiver": receiver
        }
        
        with open(EMAIL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info("이메일 설정 저장 완료")
        return True
    except Exception as e:
        logger.error(f"이메일 설정 저장 오류: {e}")
        return False

def send_daily_summary_email():
    """메자닌/기타 종목을 분리하여 각각 HTML 표로 이메일 2회 발송 (정렬/컬럼/수익률/제목/정렬 등 반영)"""
    global monitoring_stocks
    try:
        email_config = load_email_config()
        sender = email_config.get("sender", "") if email_config else ""
        password = email_config.get("password", "") if email_config else ""
        receiver = email_config.get("receiver", "") if email_config else ""
        if not (sender and password and receiver):
            logger.warning("이메일 설정이 누락되어 있어 요약 메일을 발송하지 않습니다.")
            return False
        stocks = list(monitoring_stocks.values())
        mezzanine = [s for s in stocks if s.get('category') == '메자닌']
        others = [s for s in stocks if s.get('category') != '메자닌']
        def make_html_table(stocks, is_mezzanine):
            if is_mezzanine:
                header = "<tr>"
                header += "<th style='text-align:center'>순위</th>"
                header += "<th style='text-align:center'>종목명</th>"
                header += "<th style='text-align:center'>현재가</th>"
                header += "<th style='text-align:center'>등락률</th>"
                header += "<th style='text-align:center'>패리티(%)</th>"
                header += "</tr>"
            else:
                header = "<tr>"
                header += "<th style='text-align:center'>순위</th>"
                header += "<th style='text-align:center'>종목명</th>"
                header += "<th style='text-align:center'>현재가</th>"
                header += "<th style='text-align:center'>등락률</th>"
                header += "<th style='text-align:center'>수익률</th>"
                header += "</tr>"
            rows = [header]
            for idx, info in enumerate(sorted(stocks, key=lambda x: x.get('change_percent', 0), reverse=True), 1):
                name = info.get('stock_name', '-')
                price = info.get('current_price', '-')
                change = info.get('change_percent', 0.0)
                # 등락률 색상
                if change > 0:
                    change_str = f"<span style='color:red'>+{change:.2f}%</span>"
                elif change < 0:
                    change_str = f"<span style='color:blue'>{change:.2f}%</span>"
                else:
                    change_str = f"{change:.2f}%"
                if is_mezzanine:
                    conv = info.get('conversion_price', 0)
                    parity = f"{round(price / conv * 100, 2):.2f}%" if conv else "-"
                    row = f"<tr><td style='text-align:center'>{idx}</td><td>{name}</td><td align='right'>{price:,}원</td><td align='right'>{change_str}</td><td align='right'>{parity}</td></tr>"
                else:
                    acq = info.get('acquisition_price', None)
                    if acq and isinstance(acq, (int, float)) and acq > 0:
                        profit = (price - acq) / acq * 100
                        if profit > 0:
                            profit_str = f"<span style='color:red'>+{profit:.2f}%</span>"
                        elif profit < 0:
                            profit_str = f"<span style='color:blue'>{profit:.2f}%</span>"
                        else:
                            profit_str = f"{profit:.2f}%"
                    else:
                        profit_str = ""
                    row = f"<tr><td style='text-align:center'>{idx}</td><td>{name}</td><td align='right'>{price:,}원</td><td align='right'>{change_str}</td><td align='right'>{profit_str}</td></tr>"
                rows.append(row)
            return "<table border='1' cellpadding='4' cellspacing='0'>" + ''.join(rows) + "</table>"
        # 메자닌 메일
        if mezzanine:
            try:
                subject = '[주가알림] 금일 주가 변동 현황(메자닌)'
                body = make_html_table(mezzanine, True)
                msg = MIMEText(body, 'html')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = receiver
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)
                logger.info(f"마감 요약 이메일(메자닌) 발송 완료: {receiver}")
            except Exception as e:
                logger.error(f"마감 요약 이메일(메자닌) 발송 실패: {e}")
        # 기타 메일
        if others:
            try:
                subject = '[주가알림] 금일 주가 변동 현황(기타)'
                body = make_html_table(others, False)
                msg = MIMEText(body, 'html')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = receiver
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)
                logger.info(f"마감 요약 이메일(기타) 발송 완료: {receiver}")
            except Exception as e:
                logger.error(f"마감 요약 이메일(기타) 발송 실패: {e}")
        return True
    except Exception as e:
        logger.error(f"마감 요약 이메일 발송 실패: {e}")
        return False

# 주가 정보 업데이트 스레드
def update_prices_thread():
    """백그라운드에서 주가 정보를 주기적으로 업데이트합니다."""
    global monitoring_stocks, is_running, update_event
    daily_mail_sent = False  # 1일 1회 발송 플래그
    while is_running:
        try:
            now = datetime.now()
            # 09:00~15:35만 주가 업데이트
            if (now.hour > 9 or (now.hour == 9 and now.minute >= 0)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 35)):
                for stock_code, stock_info in list(monitoring_stocks.items()):
                    try:
                        current_price, change_percent, error = get_stock_price(stock_code)
                        if not error and current_price is not None:
                            previous_price = stock_info.get("current_price", 0)
                            monitoring_stocks[stock_code]["current_price"] = current_price
                            monitoring_stocks[stock_code]["change_percent"] = change_percent
                            monitoring_stocks[stock_code]["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            monitoring_stocks[stock_code]["status"] = "모니터링 중"
                            if check_price_alerts(stock_code, stock_info.get("stock_name", ""), current_price, previous_price, stock_info):
                                save_data()
                            logger.debug(f"주가 업데이트: {stock_info['stock_name']}({stock_code}) - {current_price:,}원 ({change_percent:+.2f}%)")
                        else:
                            logger.error(f"주가 업데이트 실패: {stock_code} - {error}")
                            monitoring_stocks[stock_code]["status"] = "비활성"
                    except Exception as e:
                        logger.error(f"종목 업데이트 오류: {stock_code} - {e}")
                if update_event is not None:
                    update_event.set()
                save_data()
                time.sleep(60)
                daily_mail_sent = False  # 장중에는 매일 플래그 초기화
            else:
                # 15:35~15:40 사이에만 1회 요약 메일 발송
                if (now.hour == 15 and now.minute >= 35 and now.minute < 40) and not daily_mail_sent:
                    if send_daily_summary_email():
                        daily_mail_sent = True
                time.sleep(30)
        except Exception as e:
            logger.error(f"가격 업데이트 스레드 오류: {e}")
            time.sleep(10)

# 알림 조건 확인 함수
def check_price_alerts(stock_code, stock_name, current_price, previous_price, stock_info):
    """가격 알림 조건을 확인합니다."""
    global notifications
    
    # 알림이 설정되어 있는지 확인
    alert_prices = stock_info.get("alert_prices", [])
    if not alert_prices:
        return False
    
    alert_triggered = False
    
    # 트리거된 알림 목록이 없으면 초기화
    if "triggered_alerts" not in stock_info:
        stock_info["triggered_alerts"] = set()
    
    # 알림 확인 로직
    for alert in alert_prices:
        alert_type = alert.get("type", "")
        alert_id = alert.get("id", "")
        target_price = alert.get("price", 0)
        
        # 상승 알림
        if alert_type.startswith("Up") or alert_type == "TP Alert":
            if current_price >= target_price and previous_price < target_price and alert_id not in stock_info["triggered_alerts"]:
                add_notification(stock_code, stock_name, current_price, target_price, "TARGET_UP")
                stock_info["triggered_alerts"].add(alert_id)
                alert_triggered = True
        
        # 하락 알림
        elif alert_type.startswith("Down"):
            if current_price <= target_price and previous_price > target_price and alert_id not in stock_info["triggered_alerts"]:
                add_notification(stock_code, stock_name, current_price, target_price, "TARGET_DOWN")
                stock_info["triggered_alerts"].add(alert_id)
                alert_triggered = True
        
        # 손절가 알림
        elif alert_type == "SL Alert":
            if current_price <= target_price and previous_price > target_price and alert_id not in stock_info["triggered_alerts"]:
                add_notification(stock_code, stock_name, current_price, target_price, "STOP_LOSS")
                stock_info["triggered_alerts"].add(alert_id)
                alert_triggered = True
    
    # 일간 급등/급락 알림
    if stock_info.get("daily_alert_enabled", False):
        change_percent = stock_info.get("change_percent", 0.0)
        daily_up_threshold = stock_info.get("daily_up_threshold", 5.0)
        daily_down_threshold = stock_info.get("daily_down_threshold", -5.0)
        
        # 현재 날짜와 마지막 일간 알림 체크 날짜 비교
        today = datetime.now().date().strftime("%Y-%m-%d")
        last_check_date = stock_info.get("last_daily_check_date", "")
        
        # 날짜가 바뀌면 알림 플래그 초기화
        if today != last_check_date:
            stock_info["daily_up_alert_sent"] = False
            stock_info["daily_down_alert_sent"] = False
            stock_info["last_daily_check_date"] = today
        
        # 일간 급등 알림
        if change_percent >= daily_up_threshold and not stock_info.get("daily_up_alert_sent", False):
            add_notification(stock_code, stock_name, current_price, change_percent, "DAILY_UP", True)
            stock_info["daily_up_alert_sent"] = True
            alert_triggered = True
        
        # 일간 급락 알림
        if change_percent <= daily_down_threshold and not stock_info.get("daily_down_alert_sent", False):
            add_notification(stock_code, stock_name, current_price, change_percent, "DAILY_DOWN", True)
            stock_info["daily_down_alert_sent"] = True
            alert_triggered = True
    
    return alert_triggered

# 알림 추가 함수
def add_notification(stock_code, stock_name, current_price, target_value, alert_type, is_daily_alert=False):
    global notifications
    # 오늘 날짜
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 동일 알림(종목, 알림유형, 기준값, 날짜)이 이미 있으면 무시
    for n in notifications:
        if (
            n.get("stock_code") == stock_code and
            n.get("alert_type") == alert_type and
            n.get("target_value") == target_value and
            n.get("time", "").startswith(today_str)
        ):
            logger.info(f"동일 알림(중복) 무시: {stock_code}, {alert_type}, {target_value}, {today_str}")
            return False
    # 알림 메시지 생성
    if alert_type == "TARGET_UP":
        subject = f"[주가알림] 상승 목표가 도달: {stock_name}"
        alert_message = f"{stock_name}({stock_code})의 현재가({current_price:,}원)가 목표가({target_value:,}원)에 도달했습니다."
    elif alert_type == "TARGET_DOWN":
        subject = f"[주가알림] 하락 목표가 도달: {stock_name}"
        alert_message = f"{stock_name}({stock_code})의 현재가({current_price:,}원)가 목표가({target_value:,}원)에 도달했습니다."
    elif alert_type == "STOP_LOSS":
        subject = f"[주가알림] 손절가 도달: {stock_name}"
        alert_message = f"{stock_name}({stock_code})의 현재가({current_price:,}원)가 손절가({target_value:,}원)에 도달했습니다."
    elif alert_type == "DAILY_UP":
        subject = f"[주가알림] 일간 급등: {stock_name}"
        alert_message = f"{stock_name}({stock_code})의 가격이 오늘 {target_value}% 이상 급등했습니다. 현재가: {current_price:,}원"
    elif alert_type == "DAILY_DOWN":
        subject = f"[주가알림] 일간 급락: {stock_name}"
        alert_message = f"{stock_name}({stock_code})의 가격이 오늘 {abs(target_value)}% 이상 급락했습니다. 현재가: {current_price:,}원"
    else:
        subject = f"[주가알림] 알림: {stock_name}"
        alert_message = f"{stock_name}({stock_code}) 알림: 현재가 {current_price:,}원, 기준값: {target_value}"
    notification = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "current_price": current_price,
        "target_value": target_value,
        "alert_type": alert_type,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_daily_alert": is_daily_alert
    }
    notifications.append(notification)
    logger.info(f"알림 추가: {subject} - {alert_message}")
    # 시스템 트레이에 알림 표시
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(subject, alert_message, duration=5, threaded=True)
    except:
        pass
    # 실제 이메일 발송
    try:
        email_config = load_email_config()
        if email_config:
            sender = email_config.get("sender", "")
            password = email_config.get("password", "")
            receiver = email_config.get("receiver", "")
            if sender and password and receiver:
                msg = MIMEText(alert_message)
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = receiver
                try:
                    logger.info("SMTP 서버 연결 시도")
                    with smtplib.SMTP('smtp.gmail.com', 587) as server:
                        server.set_debuglevel(1)  # SMTP 통신 로그
                        server.starttls()
                        logger.info("STARTTLS 성공")
                        server.login(sender, password)
                        logger.info("SMTP 로그인 성공")
                        server.send_message(msg)
                        logger.info(f"이메일 알림 전송 성공: {receiver}")
                except Exception as smtp_e:
                    logger.error(f"SMTP 단계별 오류: {smtp_e}")
            else:
                logger.warning("이메일 설정이 누락되어 있어 메일을 발송하지 않습니다.")
        else:
            logger.warning("이메일 설정 파일이 없어 메일을 발송하지 않습니다.")
    except Exception as e:
        logger.error(f"이메일 알림 전송 오류: {e}")
    return True

# --- 실시간 로그 Text 핸들러 구현 ---
class LogTextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.configure(state='disabled')

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

# === 아래에 UI 클래스(SimpleStockManager) 통합 ===

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading

class SimpleStockManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Stock Manager")
        self.root.geometry("1000x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.tray_icon = None
        self.is_tray = False
        self.update_thread = None
        self.create_menu()
        self.create_stock_list_frame()
        self.create_notification_frame()
        self.create_status_bar()
        self.load_data()
        self.update_event = threading.Event()
        self.start_monitoring()
        # --- 부가 위젯 복구 ---
        # 실시간 로그 패널
        self.log_label = ttk.Label(root, text="실시간 로그", anchor="w")
        self.log_label.pack(fill="x", padx=10, pady=(10,0))
        self.log_text = tk.Text(root, height=8, state='disabled', bg="#f8f8f8", fg="#222", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=False, padx=10, pady=(0,10))
        self.log_text_handler = LogTextHandler(self.log_text)
        self.log_text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_text_handler)
        # 새로고침 버튼
        self.refresh_btn = ttk.Button(root, text="새로고침", command=self.refresh_data)
        self.refresh_btn.pack(anchor="ne", padx=10, pady=(10,0))
        # 새로고침 주기 드롭다운
        self.refresh_interval_var = tk.StringVar(value="60")
        self.refresh_interval_label = ttk.Label(root, text="새로고침 주기:")
        self.refresh_interval_label.pack(anchor="ne", padx=10, pady=(0,0))
        self.refresh_interval_combo = ttk.Combobox(root, textvariable=self.refresh_interval_var, state="readonly", width=8)
        self.refresh_interval_combo['values'] = ("30", "60", "300")
        self.refresh_interval_combo.pack(anchor="ne", padx=10, pady=(0,10))
        self.refresh_interval_combo.bind("<<ComboboxSelected>>", self.on_refresh_interval_change)
        self.auto_refresh_job = None
        self.schedule_auto_refresh()
        # Treeview 스타일 및 tag 색상 설정
        style = ttk.Style()
        style.configure("Treeview", foreground="#222")
        style.map("Treeview", foreground=[('selected', '#fff')], background=[('selected', '#4BE04B')])
        self.stock_tree.tag_configure("up", foreground="#d32f2f")  # 빨강
        self.stock_tree.tag_configure("down", foreground="#1976d2")  # 파랑
        self.stock_tree.tag_configure("none", foreground="#222")  # 검정
        self.stock_tree.tag_configure("inactive", foreground="#888")  # 비활성화
        # 테마 상태 변수
        self.is_prompt_theme = False

    def on_closing(self):
        global is_running
        is_running = False
        save_data()
        self.root.destroy()

    def hide_to_tray(self):
        self.is_tray = True
        self.root.withdraw()
        if self.tray_icon is None:
            self.tray_icon = self.create_tray_icon()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        self.is_tray = False
        self.root.after(0, self.root.deiconify)
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def create_tray_icon(self):
        if PYSTRAY_AVAILABLE:
            # 아이콘 이미지 생성 (16x16)
            image = self.get_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem('복원', self.show_from_tray),
                pystray.MenuItem('종료', self.exit_from_tray)
            )
            icon = pystray.Icon("SimpleStockManager", image, "Simple Stock Manager", menu)
            return icon
        return None

    def get_tray_icon_image(self):
        # 기본 아이콘(파란 원)
        image = Image.new('RGB', (16, 16), color='white')
        draw = ImageDraw.Draw(image)
        draw.ellipse((2, 2, 14, 14), fill='blue')
        return image

    def exit_from_tray(self, icon=None, item=None):
        global is_running
        is_running = False
        save_data()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.destroy)

    def start_monitoring(self):
        global is_running, update_event
        is_running = True
        self.update_status_icon()
        if update_event is None:
            self.update_event = threading.Event()
        if self.update_thread is None or not self.update_thread.is_alive():
            self.update_thread = threading.Thread(target=update_prices_thread, daemon=True)
            self.update_thread.start()

    def stop_monitoring(self):
        global is_running
        is_running = False
        self.update_status_icon()

    def toggle_monitoring(self):
        global is_running
        if is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def schedule_ui_update(self):
        global is_running
        if is_running:
            if self.update_event.is_set():
                self.update_stock_list()
                self.update_notification_list()
                self.update_event.clear()
            self.root.after(1000, self.schedule_ui_update)

    def show_help(self):
        help_text = """
        === Simple Stock Manager 사용 방법 ===
        1. 종목 추가: '종목 추가' 버튼 클릭 후 정보 입력
        2. 알림 설정: 종목 선택 후 알림 설정
        3. 모니터링: '모니터링 시작' 클릭
        4. 알림 확인: 하단 알림 내역 확인
        5. 이메일 설정: 파일 메뉴에서 설정
        """
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("사용 방법")
        help_dialog.geometry("500x400")
        help_dialog.transient(self.root)
        text = tk.Text(help_dialog, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
        close_button = ttk.Button(help_dialog, text="닫기", command=help_dialog.destroy)
        close_button.pack(pady=10)

    def show_about(self):
        about_text = """
        Simple Stock Manager\n버전: 1.0.0\n설명: 간단한 주식 알림 관리자입니다.\n제작: StockTPSL
        """
        messagebox.showinfo("프로그램 정보", about_text)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="새로고침", command=self.refresh_data)
        file_menu.add_command(label="이메일 설정", command=self.setup_email)
        file_menu.add_separator()
        # 리포트 전송 메뉴 추가
        file_menu.add_command(label="리포트 전송", command=self.send_report_menu)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_closing)
        menubar.add_cascade(label="파일", menu=file_menu)
        stock_menu = tk.Menu(menubar, tearoff=0)
        stock_menu.add_command(label="종목 추가", command=self.add_stock_dialog)
        stock_menu.add_command(label="선택 종목 삭제", command=self.delete_selected_stock)
        stock_menu.add_command(label="선택 종목 정보", command=self.show_stock_info)
        stock_menu.add_command(label="선택 종목 알림 설정", command=self.setup_alerts_for_selected)
        menubar.add_cascade(label="종목", menu=stock_menu)
        alert_menu = tk.Menu(menubar, tearoff=0)
        alert_menu.add_command(label="알림 초기화", command=self.reset_alerts)
        alert_menu.add_command(label="알림 기록 삭제", command=self.clear_notifications)
        alert_menu.add_command(label="알림 내역 저장", command=self.save_notifications)
        menubar.add_cascade(label="알림", menu=alert_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="사용 방법", command=self.show_help)
        help_menu.add_command(label="프로그램 정보", command=self.show_about)
        menubar.add_cascade(label="도움말", menu=help_menu)
        # 테마 메뉴 추가
        theme_menu = tk.Menu(menubar, tearoff=0)
        theme_menu.add_command(label="프롬프트 테마로 변경", command=self.toggle_theme)
        menubar.add_cascade(label="테마", menu=theme_menu)
        self.theme_menu = theme_menu  # 토글에서 사용
        self.root.config(menu=menubar)

    def send_report_menu(self):
        result = send_daily_summary_email()
        if result:
            messagebox.showinfo("리포트 전송", "마감 요약 리포트가 이메일로 발송되었습니다.")
        else:
            messagebox.showerror("리포트 전송", "리포트 전송에 실패했습니다. 이메일 설정을 확인하세요.")

    def create_stock_list_frame(self):
        top_frame = ttk.LabelFrame(self.root, text="모니터링 종목")
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        # 구분 필터 라디오버튼 추가
        self.category_var = tk.StringVar(value="전체")
        filter_frame = tk.Frame(top_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)
        for cat in ["전체", "메자닌", "기타"]:
            rb = ttk.Radiobutton(filter_frame, text=cat, variable=self.category_var, value=cat, command=self.update_stock_list)
            rb.pack(side=tk.LEFT, padx=2)
        # Treeview 컬럼 동적 생성
        self.stock_tree_columns = ["종목코드", "종목명", "현재가", "등락률", "목표가(TP)", "손절가(SL)", "마지막 체크", "상태", "일일급등락알림"]
        self.stock_tree = ttk.Treeview(top_frame, columns=self.stock_tree_columns, show="headings", height=15)
        for col in self.stock_tree_columns:
            self.stock_tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.stock_tree, c, False))
        self.stock_tree.column("종목코드", width=70, anchor="center")
        self.stock_tree.column("종목명", width=120, anchor="w")
        self.stock_tree.column("현재가", width=100, anchor="e")
        self.stock_tree.column("등락률", width=80, anchor="e")
        self.stock_tree.column("목표가(TP)", width=100, anchor="e")
        self.stock_tree.column("손절가(SL)", width=100, anchor="e")
        self.stock_tree.column("마지막 체크", width=150, anchor="center")
        self.stock_tree.column("상태", width=100, anchor="center")
        self.stock_tree.column("일일급등락알림", width=60, anchor="center")
        scrollbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.stock_tree.bind("<Double-1>", lambda event: self.show_stock_info())
        self.stock_tree.bind("<Button-3>", self.show_stock_context_menu)
        self.stock_tree.bind("<Button-1>", self.on_stock_tree_click)

    def create_notification_frame(self):
        bottom_frame = ttk.LabelFrame(self.root, text="알림 내역")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ("시간", "종목코드", "종목명", "알림 유형", "현재가", "기준값")
        self.notification_tree = ttk.Treeview(bottom_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.notification_tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.notification_tree, c, False))
        self.notification_tree.column("시간", width=150, anchor="center")
        self.notification_tree.column("종목코드", width=70, anchor="center")
        self.notification_tree.column("종목명", width=120, anchor="w")
        self.notification_tree.column("알림 유형", width=120, anchor="w")
        self.notification_tree.column("현재가", width=100, anchor="e")
        self.notification_tree.column("기준값", width=100, anchor="e")
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.notification_tree.yview)
        self.notification_tree.configure(yscrollcommand=scrollbar.set)
        self.notification_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notification_tree.bind("<Double-1>", lambda event: self.show_notification_detail())
        self.notification_tree.bind("<Button-3>", self.show_notification_context_menu)

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="모니터링 중", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)
        self.status_icon = tk.Canvas(self.status_bar, width=16, height=16, highlightthickness=0)
        self.status_icon.pack(side=tk.LEFT)
        self.update_status_icon()

    def update_status_icon(self):
        self.status_icon.delete("all")
        color = "#4BE04B" if is_running else "#FF6B6B"
        self.status_icon.create_oval(2, 2, 14, 14, fill=color)

    def load_data(self):
        global monitoring_stocks, notifications
        load_data()
        self.update_stock_list()
        self.update_notification_list()
        logger.info(f"UI 데이터 로드 완료. 종목 수: {len(monitoring_stocks)}, 알림 수: {len(notifications)}")

    def update_stock_list(self):
        global monitoring_stocks
        selected_cat = self.category_var.get() if hasattr(self, 'category_var') else "전체"
        # 메자닌이면 종목코드, 종목명, 현재가, 등락률, 패리티(%), 패리티(floor)(%), 목표가, 손절가, 마지막 체크, 상태, 일일급등락알림
        if selected_cat == "메자닌":
            columns = ["종목코드", "종목명", "현재가", "등락률", "패리티(%)", "패리티(floor)(%)", "목표가(TP)", "손절가(SL)", "마지막 체크", "상태", "일일급등락알림"]
        elif selected_cat == "기타":
            columns = ["종목코드", "종목명", "현재가", "등락률", "수익률", "목표가(TP)", "손절가(SL)", "마지막 체크", "상태", "일일급등락알림"]
        else:
            columns = ["종목코드", "종목명", "현재가", "등락률", "목표가(TP)", "손절가(SL)", "마지막 체크", "상태", "일일급등락알림"]
        self.stock_tree.config(columns=columns)
        for col in columns:
            self.stock_tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.stock_tree, c, False))
        col_settings = {
            "종목코드": (70, "center"), "종목명": (120, "w"), "현재가": (100, "e"), "패리티(%)": (80, "e"),
            "패리티(floor)(%)": (80, "e"), "등락률": (80, "e"), "수익률": (80, "e"), "목표가(TP)": (100, "e"), "손절가(SL)": (100, "e"), "마지막 체크": (150, "center"), "상태": (100, "center"), "일일급등락알림": (60, "center")
        }
        for col in columns:
            w, a = col_settings.get(col, (100, "center"))
            self.stock_tree.column(col, width=w, anchor=a)
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        for stock_code, stock_info in sorted(monitoring_stocks.items()):
            category = stock_info.get("category", "기타")
            if selected_cat != "전체" and category != selected_cat:
                continue
            tp_price = 0
            sl_price = 0
            for alert in stock_info.get("alert_prices", []):
                if alert.get("type") == "TP Alert":
                    tp_price = alert.get("price", 0)
                elif alert.get("type") == "SL Alert":
                    sl_price = alert.get("price", 0)
            change_percent = stock_info.get("change_percent", 0.0)
            parity_str = "-"
            parity_fg = None
            parity_floor_str = "-"
            parity_floor_fg = None
            current_price = stock_info.get("current_price", 0)
            # 수익률 계산 (기타)
            profit_str = ""
            if selected_cat == "기타":
                acq = stock_info.get("acquisition_price", None)
                if acq and isinstance(acq, (int, float)) and acq > 0:
                    profit = (current_price - acq) / acq * 100
                    if profit > 0:
                        profit_str = f"+{profit:.2f}%"
                    elif profit < 0:
                        profit_str = f"{profit:.2f}%"
                    else:
                        profit_str = f"{profit:.2f}%"
                else:
                    profit_str = ""
            if change_percent > 0:
                change_percent_str = f"+{change_percent:.2f}%"
            elif change_percent < 0:
                change_percent_str = f"{change_percent:.2f}%"
            else:
                change_percent_str = f"{change_percent:.2f}%"
            status = stock_info.get("status", "모니터링 중")
            daily_alert_enabled = stock_info.get("daily_alert_enabled", True)
            daily_alert_str = "on" if daily_alert_enabled else "off"
            # 목표가, 손절가, 현재가 모두 세자리 콤마, 소수점 없이
            current_price_str = f"{int(current_price):,}" if isinstance(current_price, (int, float)) else current_price
            tp_price_str = f"{int(tp_price):,}" if tp_price else "-"
            sl_price_str = f"{int(sl_price):,}" if sl_price else "-"
            if selected_cat == "메자닌":
                conversion_price = stock_info.get("conversion_price", 0)
                conversion_price_floor = stock_info.get("conversion_price_floor", 0)
                if conversion_price:
                    parity = round(current_price / conversion_price * 100, 2)
                    parity_str = f"{parity:.2f}%"
                    parity_fg = "green" if parity >= 100 else "red"
                floor_base = conversion_price_floor if conversion_price_floor else conversion_price
                if floor_base:
                    parity_floor = round(current_price / floor_base * 100, 2)
                    parity_floor_str = f"{parity_floor:.2f}%"
                    parity_floor_fg = "green" if parity_floor >= 100 else "red"
                values = [stock_code, stock_info.get("stock_name", "-"), current_price_str, change_percent_str, parity_str, parity_floor_str, tp_price_str, sl_price_str, stock_info.get("last_checked", "-"), status, daily_alert_str]
            elif selected_cat == "기타":
                values = [stock_code, stock_info.get("stock_name", "-"), current_price_str, change_percent_str, profit_str, tp_price_str, sl_price_str, stock_info.get("last_checked", "-"), status, daily_alert_str]
            else:
                values = [stock_code, stock_info.get("stock_name", "-"), current_price_str, change_percent_str, tp_price_str, sl_price_str, stock_info.get("last_checked", "-"), status, daily_alert_str]
            if change_percent > 0:
                tag = "up"
            elif change_percent < 0:
                tag = "down"
            elif status == "비활성":
                tag = "inactive"
            else:
                tag = "none"
            item_id = self.stock_tree.insert("", "end", values=values, tags=(tag,))
            if selected_cat == "메자닌":
                if parity_fg and parity_str != "-":
                    self.stock_tree.tag_configure(f"parity_{item_id}", foreground=parity_fg)
                    self.stock_tree.item(item_id, tags=(tag, f"parity_{item_id}"))
                if parity_floor_fg and parity_floor_str != "-":
                    self.stock_tree.tag_configure(f"parity_floor_{item_id}", foreground=parity_floor_fg)
                    self.stock_tree.item(item_id, tags=(tag, f"parity_floor_{item_id}"))

    def update_notification_list(self):
        global notifications
        for item in self.notification_tree.get_children():
            self.notification_tree.delete(item)
        for notification in sorted(notifications, key=lambda x: x.get("time", ""), reverse=True)[:50]:
            alert_type = notification.get("alert_type", "")
            alert_type_str = ""
            if alert_type == "TARGET_UP":
                alert_type_str = "목표가 도달↑"
            elif alert_type == "TARGET_DOWN":
                alert_type_str = "목표가 도달↓"
            elif alert_type == "STOP_LOSS":
                alert_type_str = "손절가 도달"
            elif alert_type == "DAILY_UP":
                alert_type_str = "일간 급등"
            elif alert_type == "DAILY_DOWN":
                alert_type_str = "일간 급락"
            else:
                alert_type_str = alert_type
            target_value = notification.get("target_value", 0)
            # 기준값 표기: 일간 급등/급락은 % 소수점 2자리, 나머지는 정수(원)
            if alert_type in ["DAILY_UP", "DAILY_DOWN"]:
                target_value_str = f"{target_value:.2f}%"
            else:
                try:
                    target_value_int = int(float(target_value))
                except Exception:
                    target_value_int = target_value
                target_value_str = f"{target_value_int:,}원"
            # 현재가 bold, 등락률 이모지
            current_price = notification.get('current_price', 0)
            if alert_type in ["TARGET_UP", "DAILY_UP"]:
                tag = "up"
            elif alert_type in ["TARGET_DOWN", "DAILY_DOWN", "STOP_LOSS"]:
                tag = "down"
            else:
                tag = "none"
            values = (
                notification.get("time", ""),
                notification.get("stock_code", ""),
                notification.get("stock_name", ""),
                alert_type_str,
                f"{current_price:,}원",
                target_value_str
            )
            self.notification_tree.insert("", tk.END, values=values, tags=(tag,))
        self.notification_tree.tag_configure("up", foreground="red")
        self.notification_tree.tag_configure("down", foreground="blue")

    def refresh_data(self):
        self.load_data()
        logger.info("수동 새로고침 실행됨.")

    def setup_email(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("이메일 설정")
        dialog.geometry("350x220")
        dialog.transient(self.root)
        tk.Label(dialog, text="발신자 이메일").pack(pady=5)
        sender_entry = tk.Entry(dialog)
        sender_entry.pack(pady=5)
        tk.Label(dialog, text="비밀번호(앱 비밀번호)").pack(pady=5)
        password_entry = tk.Entry(dialog, show='*')
        password_entry.pack(pady=5)
        tk.Label(dialog, text="수신자 이메일").pack(pady=5)
        receiver_entry = tk.Entry(dialog)
        receiver_entry.pack(pady=5)
        # 기존 값 불러오기
        email_config = load_email_config()
        if email_config:
            sender_entry.insert(0, email_config.get("sender", ""))
            password_entry.insert(0, email_config.get("password", ""))
            receiver_entry.insert(0, email_config.get("receiver", ""))
        def on_save():
            sender = sender_entry.get().strip()
            password = password_entry.get().strip()
            receiver = receiver_entry.get().strip()
            save_email_config(sender, password, receiver)
            messagebox.showinfo("저장 완료", "이메일 설정이 저장되었습니다.")
            dialog.destroy()
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        save_btn = ttk.Button(btn_frame, text="저장", command=on_save)
        save_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="취소", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def add_stock_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("종목 추가")
        dialog.geometry("320x750")
        dialog.transient(self.root)
        # --- 분류(메자닌/기타) 라디오버튼 추가 ---
        tk.Label(dialog, text="종목 분류").pack(pady=5)
        category_var = tk.StringVar(value="기타")
        cat_frame = tk.Frame(dialog)
        cat_frame.pack(pady=2)
        for cat in ["메자닌", "기타"]:
            rb = ttk.Radiobutton(cat_frame, text=cat, variable=category_var, value=cat)
            rb.pack(side=tk.LEFT, padx=2)
        tk.Label(dialog, text="종목코드(6자리)").pack(pady=5)
        code_entry = tk.Entry(dialog)
        code_entry.pack(pady=5)
        tk.Label(dialog, text="목표가(TP, 옵션)").pack(pady=5)
        tp_entry = tk.Entry(dialog)
        tp_entry.pack(pady=5)
        tk.Label(dialog, text="손절가(SL, 옵션)").pack(pady=5)
        sl_entry = tk.Entry(dialog)
        sl_entry.pack(pady=5)
        tk.Label(dialog, text="전환가(옵션)").pack(pady=5)
        conv_entry = tk.Entry(dialog)
        conv_entry.pack(pady=5)
        tk.Label(dialog, text="전환가(floor, 옵션)").pack(pady=5)
        conv_floor_entry = tk.Entry(dialog)
        conv_floor_entry.pack(pady=5)
        # --- 취득가 입력란 추가 ---
        tk.Label(dialog, text="취득가(옵션)").pack(pady=5)
        acq_entry = tk.Entry(dialog)
        acq_entry.pack(pady=5)
        # 여백 추가
        tk.Label(dialog, text="").pack(pady=10)
        # 일일 급등락 알림
        daily_alert_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="일일 급등락 알림 활성화", variable=daily_alert_var).pack(pady=2)
        tk.Label(dialog, text="급등 임계값(%)").pack(pady=2)
        daily_up_entry = tk.Entry(dialog)
        daily_up_entry.insert(0, "5")
        daily_up_entry.pack(pady=2)
        tk.Label(dialog, text="급락 임계값(%)").pack(pady=2)
        daily_down_entry = tk.Entry(dialog)
        daily_down_entry.insert(0, "5")
        daily_down_entry.pack(pady=2)
        tk.Label(dialog, text="메모(옵션)").pack(pady=5)
        memo_entry = tk.Entry(dialog)
        memo_entry.pack(pady=5)
        # 패리티 알림 퍼센트 입력란 개선
        tk.Label(dialog, text="패리티 알림 퍼센트").pack(pady=5)
        parity_frame = tk.Frame(dialog)
        parity_frame.pack(pady=2)
        parity_entry = tk.Entry(parity_frame, width=6)
        parity_entry.pack(side=tk.LEFT)
        parity_add_btn = ttk.Button(parity_frame, text="추가")
        parity_add_btn.pack(side=tk.LEFT, padx=2)
        parity_list_frame = tk.Frame(dialog)
        parity_list_frame.pack(pady=2)
        parity_percents = [80, 100, 120]
        parity_labels = []
        def refresh_parity_list():
            for w in parity_labels:
                w.destroy()
            parity_labels.clear()
            for p in parity_percents:
                f = tk.Frame(parity_list_frame)
                f.pack(anchor="w")
                l = tk.Label(f, text=f"{p}%")
                l.pack(side=tk.LEFT)
                b = ttk.Button(f, text="X", width=2, command=lambda val=p: remove_parity(val))
                b.pack(side=tk.LEFT, padx=2)
                parity_labels.append(f)
        def add_parity():
            val = parity_entry.get().strip()
            if val.isdigit():
                v = int(val)
                if v not in parity_percents:
                    parity_percents.append(v)
                    parity_percents.sort()
                    refresh_parity_list()
            parity_entry.delete(0, tk.END)
        def remove_parity(val):
            if val in parity_percents:
                parity_percents.remove(val)
                refresh_parity_list()
        parity_add_btn.config(command=add_parity)
        refresh_parity_list()
        def on_add():
            code = code_entry.get().strip()
            tp = tp_entry.get().strip()
            sl = sl_entry.get().strip()
            conv = conv_entry.get().strip()
            conv_floor = conv_floor_entry.get().strip()
            acq = acq_entry.get().strip()
            memo = memo_entry.get().strip()
            daily_alert_enabled = daily_alert_var.get()
            category = category_var.get()
            try:
                tp_val = int(float(tp)) if tp else 0
                sl_val = int(float(sl)) if sl else 0
                conv_val = int(float(conv)) if conv else 0
                conv_floor_val = int(float(conv_floor)) if conv_floor else 0
                acq_val = int(float(acq)) if acq else None
                daily_up_val = float(daily_up_entry.get().strip() or 5)
                daily_down_val = -abs(float(daily_down_entry.get().strip() or 5))
                if not code or len(code) != 6 or not code.isdigit():
                    messagebox.showwarning("입력 오류", "종목코드는 6자리 숫자로 입력하세요.")
                    return
                if code in monitoring_stocks:
                    messagebox.showwarning("중복", "이미 등록된 종목입니다.")
                    return
                add_stock(
                    code,
                    tp_price=tp_val,
                    sl_price=sl_val,
                    memo=memo,
                    parity_percents=parity_percents.copy(),
                    conversion_price=conv_val,
                    conversion_price_floor=conv_floor_val,
                    daily_alert_enabled=daily_alert_enabled,
                    daily_up_threshold=daily_up_val,
                    daily_down_threshold=daily_down_val,
                    category=category,
                    acquisition_price=acq_val
                )
                dialog.destroy()
                self.update_stock_list()
                self.update_notification_list()
            except Exception as e:
                messagebox.showerror("오류", f"종목 추가 중 오류: {e}")
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        add_btn = ttk.Button(btn_frame, text="추가", command=on_add)
        add_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="취소", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def delete_selected_stock(self):
        selected = self.stock_tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "삭제할 종목을 선택하세요.")
            return
        for item in selected:
            code = self.stock_tree.item(item, 'values')[0]
            if delete_stock(code):
                self.update_stock_list()

    def show_stock_info(self):
        # 더블클릭 시 종목 조건 수정 다이얼로그 호출
        selected = self.stock_tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "수정할 종목을 선택하세요.")
            return
        code = self.stock_tree.item(selected[0], 'values')[0]
        self.show_edit_stock_dialog(code)

    def show_edit_stock_dialog(self, stock_code):
        global monitoring_stocks
        if stock_code not in monitoring_stocks:
            messagebox.showerror("오류", "해당 종목 정보를 찾을 수 없습니다.")
            return
        info = monitoring_stocks[stock_code]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"종목 조건 수정 - {stock_code}")
        dialog.geometry("320x900")  # 세로 길이 확장
        dialog.transient(self.root)
        category = info.get("category", "기타")
        tk.Label(dialog, text="종목 분류").pack(pady=5)
        category_var = tk.StringVar(value=category)
        cat_frame = tk.Frame(dialog)
        cat_frame.pack(pady=2)
        for cat in ["메자닌", "기타"]:
            rb = ttk.Radiobutton(cat_frame, text=cat, variable=category_var, value=cat)
            rb.pack(side=tk.LEFT, padx=2)
        tp = next((a["price"] for a in info.get("alert_prices", []) if a.get("type") == "TP Alert"), "")
        sl = next((a["price"] for a in info.get("alert_prices", []) if a.get("type") == "SL Alert"), "")
        tp_entry = tk.Entry(dialog)
        tp_entry.insert(0, str(int(float(tp))) if tp else "")
        tp_entry.pack(pady=5)
        sl_entry = tk.Entry(dialog)
        sl_entry.insert(0, str(int(float(sl))) if sl else "")
        sl_entry.pack(pady=5)
        conv = info.get("conversion_price", "")
        conv_floor = info.get("conversion_price_floor", "")
        memo = info.get("memo", "")
        daily_alert_enabled = info.get("daily_alert_enabled", True)
        daily_up_threshold = info.get("daily_up_threshold", 5)
        daily_down_threshold = abs(info.get("daily_down_threshold", 5))
        parity_percents = [a.get("parity_percent") for a in info.get("alert_prices", []) if a.get("category") == "PARITY"]
        if not parity_percents:
            parity_percents = [80, 100, 120]
        parity_labels = []
        tk.Label(dialog, text="목표가(TP)").pack(pady=5)
        tp_entry = tk.Entry(dialog)
        tp_entry.insert(0, tp)
        tp_entry.pack(pady=5)
        tk.Label(dialog, text="손절가(SL)").pack(pady=5)
        sl_entry = tk.Entry(dialog)
        sl_entry.insert(0, sl)
        sl_entry.pack(pady=5)
        tk.Label(dialog, text="전환가").pack(pady=5)
        conv_entry = tk.Entry(dialog)
        conv_entry.insert(0, conv)
        conv_entry.pack(pady=5)
        tk.Label(dialog, text="전환가(floor)").pack(pady=5)
        conv_floor_entry = tk.Entry(dialog)
        conv_floor_entry.insert(0, conv_floor)
        conv_floor_entry.pack(pady=5)
        # --- 취득가 입력란 추가 ---
        acq = info.get("acquisition_price", "")
        tk.Label(dialog, text="취득가(옵션)").pack(pady=5)
        acq_entry = tk.Entry(dialog)
        acq_entry.insert(0, str(acq) if acq else "")
        acq_entry.pack(pady=5)
        tk.Label(dialog, text="").pack(pady=10)
        daily_alert_var = tk.BooleanVar(value=daily_alert_enabled)
        tk.Checkbutton(dialog, text="일일 급등락 알림 활성화", variable=daily_alert_var).pack(pady=2)
        tk.Label(dialog, text="급등 임계값(%)").pack(pady=2)
        daily_up_entry = tk.Entry(dialog)
        daily_up_entry.insert(0, str(daily_up_threshold))
        daily_up_entry.pack(pady=2)
        tk.Label(dialog, text="급락 임계값(%)").pack(pady=2)
        daily_down_entry = tk.Entry(dialog)
        daily_down_entry.insert(0, str(daily_down_threshold))
        daily_down_entry.pack(pady=2)
        tk.Label(dialog, text="메모").pack(pady=5)
        memo_entry = tk.Entry(dialog)
        memo_entry.insert(0, memo)
        memo_entry.pack(pady=5)
        tk.Label(dialog, text="패리티 알림 퍼센트").pack(pady=5)
        parity_frame = tk.Frame(dialog)
        parity_frame.pack(pady=2)
        parity_entry = tk.Entry(parity_frame, width=6)
        parity_entry.pack(side=tk.LEFT)
        parity_add_btn = ttk.Button(parity_frame, text="추가")
        parity_add_btn.pack(side=tk.LEFT, padx=2)
        parity_list_frame = tk.Frame(dialog)
        parity_list_frame.pack(pady=2)
        def refresh_parity_list():
            for w in parity_labels:
                w.destroy()
            parity_labels.clear()
            for p in parity_percents:
                f = tk.Frame(parity_list_frame)
                f.pack(anchor="w")
                l = tk.Label(f, text=f"{p}%")
                l.pack(side=tk.LEFT)
                b = ttk.Button(f, text="X", width=2, command=lambda val=p: remove_parity(val))
                b.pack(side=tk.LEFT, padx=2)
                parity_labels.append(f)
        def add_parity():
            val = parity_entry.get().strip()
            if val.isdigit():
                v = int(val)
                if v not in parity_percents:
                    parity_percents.append(v)
                    parity_percents.sort()
                    refresh_parity_list()
            parity_entry.delete(0, tk.END)
        def remove_parity(val):
            if val in parity_percents:
                parity_percents.remove(val)
                refresh_parity_list()
        parity_add_btn.config(command=add_parity)
        refresh_parity_list()
        def on_save():
            try:
                tp_val = int(float(tp_entry.get().strip())) if tp_entry.get().strip() else 0
                sl_val = int(float(sl_entry.get().strip())) if sl_entry.get().strip() else 0
                conv_val = int(float(conv_entry.get().strip())) if conv_entry.get().strip() else 0
                conv_floor_val = int(float(conv_floor_entry.get().strip())) if conv_floor_entry.get().strip() else 0
                acq_val = int(float(acq_entry.get().strip())) if acq_entry.get().strip() else None
                daily_alert_enabled = daily_alert_var.get()
                daily_up_threshold = int(float(daily_up_entry.get().strip())) if daily_up_entry.get().strip() else 5
                daily_down_threshold = -abs(int(float(daily_down_entry.get().strip()))) if daily_down_entry.get().strip() else -5
                memo_val = memo_entry.get().strip()
                category = category_var.get()
                if not parity_percents:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("입력 오류", "목표가/손절가/전환가/전환가(floor)/패리티/급등락 임계값/취득가는 숫자여야 합니다.")
                return
            alert_prices = []
            if tp_val > 0:
                alert_prices.append({"id": "tp0", "price": tp_val, "type": "TP Alert", "category": "TP"})
            if sl_val > 0:
                alert_prices.append({"id": "sl0", "price": sl_val, "type": "SL Alert", "category": "SL"})
            current_price = info.get("current_price", 0)
            for percent in parity_percents:
                alert_prices.append({
                    "id": f"parity{percent}",
                    "price": int(current_price * percent / 100),
                    "type": "Parity Alert",
                    "category": "PARITY",
                    "parity_percent": percent
                })
            info["alert_prices"] = alert_prices
            info["memo"] = memo_val
            info["conversion_price"] = conv_val
            info["conversion_price_floor"] = conv_floor_val
            info["daily_alert_enabled"] = daily_alert_enabled
            info["daily_up_threshold"] = daily_up_threshold
            info["daily_down_threshold"] = daily_down_threshold
            info["category"] = category
            info["acquisition_price"] = acq_val
            save_data()
            self.update_stock_list()
            dialog.destroy()
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        save_btn = ttk.Button(btn_frame, text="저장", command=on_save)
        save_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="취소", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        dialog.bind('<Return>', lambda e: on_save())

        # --- 취득가 입력란 아래 목표가/손절가 퍼센트 자동계산 UI 추가 ---
        # 목표가 퍼센트 선택
        tk.Label(dialog, text="목표가 퍼센트").pack(pady=2)
        tp_percent_var = tk.StringVar(value="10")
        tp_percent_frame = tk.Frame(dialog)
        tp_percent_frame.pack(pady=2)
        for v in ["5", "10", "20"]:
            rb = ttk.Radiobutton(tp_percent_frame, text=f"{v}%", variable=tp_percent_var, value=v)
            rb.pack(side=tk.LEFT, padx=2)
        tp_custom_entry = tk.Entry(tp_percent_frame, width=5)
        tp_custom_entry.pack(side=tk.LEFT, padx=2)
        tp_custom_entry.insert(0, "")
        ttk.Label(tp_percent_frame, text="직접입력").pack(side=tk.LEFT)
        # 손절가 퍼센트 선택
        tk.Label(dialog, text="손절가 퍼센트").pack(pady=2)
        sl_percent_var = tk.StringVar(value="10")
        sl_percent_frame = tk.Frame(dialog)
        sl_percent_frame.pack(pady=2)
        for v in ["5", "10", "20"]:
            rb = ttk.Radiobutton(sl_percent_frame, text=f"{v}%", variable=sl_percent_var, value=v)
            rb.pack(side=tk.LEFT, padx=2)
        sl_custom_entry = tk.Entry(sl_percent_frame, width=5)
        sl_custom_entry.pack(side=tk.LEFT, padx=2)
        sl_custom_entry.insert(0, "")
        ttk.Label(sl_percent_frame, text="직접입력").pack(side=tk.LEFT)
        # 목표가/손절가 자동계산 함수
        def update_tp_sl_from_acq(*args):
            try:
                acq = float(acq_entry.get()) if acq_entry.get() else 0
                # 목표가
                tp_percent = float(tp_percent_var.get()) if tp_percent_var.get() else 0
                if tp_custom_entry.get():
                    tp_percent = float(tp_custom_entry.get())
                tp_val = int(acq * (1 + tp_percent / 100)) if acq and tp_percent else ""
                tp_entry.delete(0, tk.END)
                if tp_val:
                    tp_entry.insert(0, str(tp_val))
                # 손절가
                sl_percent = float(sl_percent_var.get()) if sl_percent_var.get() else 0
                if sl_custom_entry.get():
                    sl_percent = float(sl_custom_entry.get())
                sl_val = int(acq * (1 - sl_percent / 100)) if acq and sl_percent else ""
                sl_entry.delete(0, tk.END)
                if sl_val:
                    sl_entry.insert(0, str(sl_val))
            except Exception:
                pass
        # trace 연결
        acq_entry.bind('<KeyRelease>', lambda e: update_tp_sl_from_acq())
        tp_percent_var.trace_add('write', lambda *a: update_tp_sl_from_acq())
        sl_percent_var.trace_add('write', lambda *a: update_tp_sl_from_acq())
        tp_custom_entry.bind('<KeyRelease>', lambda e: update_tp_sl_from_acq())
        sl_custom_entry.bind('<KeyRelease>', lambda e: update_tp_sl_from_acq())

    def setup_alerts_for_selected(self):
        messagebox.showinfo("알림 설정", "알림 설정 기능은 추후 구현 예정입니다.")

    def show_stock_context_menu(self, event=None):
        # 종목리스트에서 우클릭 시 컨텍스트 메뉴(종목 삭제) 제공
        iid = self.stock_tree.identify_row(event.y) if event else None
        if iid:
            self.stock_tree.selection_set(iid)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="종목 삭제", command=lambda: self.delete_selected_stock())
            menu.tk_popup(event.x_root, event.y_root)
        else:
            messagebox.showinfo("종목 컨텍스트 메뉴", "종목을 선택 후 우클릭하세요.")

    def show_notification_detail(self):
        messagebox.showinfo("알림 상세", "알림 상세 보기 기능은 추후 구현 예정입니다.")

    def show_notification_context_menu(self, event=None):
        messagebox.showinfo("알림 컨텍스트 메뉴", "알림 컨텍스트 메뉴 기능은 추후 구현 예정입니다.")

    def reset_alerts(self):
        messagebox.showinfo("알림 초기화", "알림 초기화 기능은 추후 구현 예정입니다.")

    def clear_notifications(self):
        messagebox.showinfo("알림 기록 삭제", "알림 기록 삭제 기능은 추후 구현 예정입니다.")

    def save_notifications(self):
        messagebox.showinfo("알림 내역 저장", "알림 내역 저장 기능은 추후 구현 예정입니다.")

    def sort_treeview(self, tree, col, reverse):
        # Treeview 컬럼 정렬 기능 구현
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        # 숫자/한글/영문 구분하여 정렬
        def try_float(val):
            try:
                return float(val.replace(",", "").replace("원", "").replace("%", ""))
            except:
                return val
        l.sort(key=lambda t: try_float(t[0]), reverse=reverse)
        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
        # 다음 클릭 시 정렬 방향 토글
        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))

    def on_refresh_interval_change(self, event=None):
        self.schedule_auto_refresh()
        logger.info(f"새로고침 주기 변경: {self.refresh_interval_var.get()}초")

    def schedule_auto_refresh(self):
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)
        interval = int(self.refresh_interval_var.get()) * 1000
        self.auto_refresh_job = self.root.after(interval, self.auto_refresh)

    def auto_refresh(self):
        self.refresh_data()
        self.schedule_auto_refresh()

    def toggle_theme(self):
        style = ttk.Style()
        style.theme_use('default')  # 테마 강제 지정
        if not self.is_prompt_theme:
            self.root.configure(bg="#111")
            self.log_text.configure(bg="#111", fg="#39ff14")
            self.stock_tree.tag_configure("up", foreground="#39ff14")
            self.stock_tree.tag_configure("down", foreground="#39ff14")
            self.stock_tree.tag_configure("none", foreground="#39ff14")
            self.stock_tree.tag_configure("inactive", foreground="#39ff14")
            self.notification_tree.tag_configure("up", foreground="#39ff14")
            self.notification_tree.tag_configure("down", foreground="#39ff14")
            self.notification_tree.tag_configure("none", foreground="#39ff14")
            self.refresh_btn.configure(style="Prompt.TButton")
            self.refresh_interval_label.configure(background="#111", foreground="#39ff14")
            self.refresh_interval_combo.configure(background="#111", foreground="#39ff14")
            self.log_label.configure(background="#111", foreground="#39ff14")
            style.configure("Treeview", background="#111", fieldbackground="#111", foreground="#39ff14")
            style.configure("TCombobox", fieldbackground="#111", foreground="#39ff14", background="#111")
            style.configure("Prompt.TButton", background="#222", foreground="#39ff14")
            self.theme_menu.entryconfig(0, label="기본 테마로 변경")
            self.is_prompt_theme = True
        else:
            self.root.configure(bg="#f8f8f8")
            self.log_text.configure(bg="#f8f8f8", fg="#222")
            self.stock_tree.tag_configure("up", foreground="#d32f2f")
            self.stock_tree.tag_configure("down", foreground="#1976d2")
            self.stock_tree.tag_configure("none", foreground="#222")
            self.stock_tree.tag_configure("inactive", foreground="#888")
            self.notification_tree.tag_configure("up", foreground="#d32f2f")
            self.notification_tree.tag_configure("down", foreground="#1976d2")
            self.notification_tree.tag_configure("none", foreground="#222")
            self.refresh_btn.configure(style="TButton")
            self.refresh_interval_label.configure(background="#f8f8f8", foreground="#222")
            self.refresh_interval_combo.configure(background="#fff", foreground="#222")
            self.log_label.configure(background="#f8f8f8", foreground="#222")
            style.configure("Treeview", background="#fff", fieldbackground="#fff", foreground="#222")
            style.configure("TCombobox", fieldbackground="#fff", foreground="#222", background="#fff")
            self.theme_menu.entryconfig(0, label="프롬프트 테마로 변경")
            self.is_prompt_theme = False

    def on_stock_tree_click(self, event):
        # 일일급등락알림 컬럼 클릭 시 ON/OFF 토글
        region = self.stock_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.stock_tree.identify_column(event.x)
        col_num = int(col.replace("#", "")) - 1
        columns = self.stock_tree["columns"]
        if columns[col_num] == "일일급등락알림":
            row_id = self.stock_tree.identify_row(event.y)
            if not row_id:
                return
            code = self.stock_tree.item(row_id, 'values')[0]
            if code in monitoring_stocks:
                monitoring_stocks[code]["daily_alert_enabled"] = not monitoring_stocks[code].get("daily_alert_enabled", True)
                save_data()
                self.update_stock_list()

# ... 이하 part3의 나머지 메서드(이벤트, 다이얼로그 등)는 필요시 추가 ...

# 임시 테스트 함수: pykrx 단일 종목 테스트
def test_pykrx_single():
    for code in ["005930", "035420"]:
        logger.info(f"[TEST] pykrx 단일 테스트: {code}")
        price, change, err = get_stock_price_pykrx(code)
        logger.info(f"[TEST] 결과: code={code}, price={price}, change={change}, err={err}")

if __name__ == "__main__":
    # test_pykrx_single()  # 필요시만 테스트
    root = tk.Tk()
    app = SimpleStockManager(root)
    root.mainloop()
