"""
이메일 유틸리티 모듈
SMTP와 SendGrid를 모두 지원하는 통합 이메일 발송 기능
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import sendgrid
from sendgrid.helpers.mail import Mail

from .config import (
    EMAIL_SENDER,
    EMAIL_PASSWORD, 
    EMAIL_RECEIVER,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL
)

# 로거 설정
logger = logging.getLogger(__name__)

def send_email_smtp(subject: str, text_content: str, html_content: Optional[str] = None) -> bool:
    """
    SMTP를 통한 이메일 발송
    
    Args:
        subject: 이메일 제목
        text_content: 텍스트 내용
        html_content: HTML 내용 (선택사항)
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        
        logger.info(f"SMTP 이메일 준비: {subject}")
        logger.info(f"보내는 사람: {EMAIL_SENDER}, 받는 사람: {EMAIL_RECEIVER}")
        
        # 텍스트 버전 첨부
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        # HTML 버전이 있으면 첨부
        if html_content:
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            logger.info("HTML 버전 첨부 완료")
        
        # SMTP 서버 연결
        logger.info("SMTP 서버 연결 시도...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # 로그인
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        logger.info("SMTP 로그인 성공")
        
        # 이메일 발송
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
        
        server.quit()
        logger.info(f"SMTP 이메일 전송 성공: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"SMTP 이메일 전송 실패: {e}")
        logger.error(f"상세 오류: {str(e)}")
        return False

def send_email_sendgrid(subject: str, text_content: str, html_content: Optional[str] = None) -> bool:
    """
    SendGrid를 통한 이메일 발송
    
    Args:
        subject: 이메일 제목
        text_content: 텍스트 내용
        html_content: HTML 내용 (선택사항)
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        if not SENDGRID_API_KEY:
            logger.warning("SendGrid API 키가 설정되지 않음")
            return False
        
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=EMAIL_RECEIVER,
            subject=subject,
            plain_text_content=text_content,
            html_content=html_content
        )
        
        logger.info(f"SendGrid 이메일 준비: {subject}")
        
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"SendGrid 이메일 전송 성공: {subject}")
            return True
        else:
            logger.error(f"SendGrid 이메일 전송 실패: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"SendGrid 이메일 전송 실패: {e}")
        return False

def send_email(subject: str, text_content: str, html_content: Optional[str] = None, method: str = 'auto') -> bool:
    """
    통합 이메일 발송 함수
    
    Args:
        subject: 이메일 제목
        text_content: 텍스트 내용
        html_content: HTML 내용 (선택사항)
        method: 발송 방식 ('smtp', 'sendgrid', 'auto')
    
    Returns:
        bool: 발송 성공 여부
    """
    logger.info(f"이메일 발송 시작: {subject}")
    
    if method == 'smtp':
        return send_email_smtp(subject, text_content, html_content)
    elif method == 'sendgrid':
        return send_email_sendgrid(subject, text_content, html_content)
    elif method == 'auto':
        # SendGrid가 설정되어 있으면 우선 사용, 아니면 SMTP
        if SENDGRID_API_KEY:
            logger.info("SendGrid로 이메일 발송 시도")
            success = send_email_sendgrid(subject, text_content, html_content)
            if success:
                return True
            else:
                logger.info("SendGrid 실패, SMTP로 재시도")
                return send_email_smtp(subject, text_content, html_content)
        else:
            logger.info("SMTP로 이메일 발송")
            return send_email_smtp(subject, text_content, html_content)
    else:
        logger.error(f"알 수 없는 이메일 발송 방식: {method}")
        return False

def send_dart_alert(corp_name: str, report_name: str, keywords: list, priority_score: int, dart_url: str) -> bool:
    """
    DART 공시 알림 이메일 발송
    
    Args:
        corp_name: 기업명
        report_name: 보고서명
        keywords: 매칭된 키워드 목록
        priority_score: 우선순위 점수
        dart_url: DART 원문 URL
    
    Returns:
        bool: 발송 성공 여부
    """
    subject = f"[DART 알림] {corp_name} - {report_name}"
    
    text_content = f"""
DART 공시 알림

기업명: {corp_name}
보고서명: {report_name}
우선순위: {priority_score}점
매칭 키워드: {', '.join(keywords)}

원문 보기: {dart_url}

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    html_content = f"""
<html>
<body>
    <h2>🔔 DART 공시 알림</h2>
    <table border="1" style="border-collapse:collapse; width:100%;">
        <tr>
            <td><strong>기업명</strong></td>
            <td>{corp_name}</td>
        </tr>
        <tr>
            <td><strong>보고서명</strong></td>
            <td>{report_name}</td>
        </tr>
        <tr>
            <td><strong>우선순위</strong></td>
            <td>{priority_score}점</td>
        </tr>
        <tr>
            <td><strong>매칭 키워드</strong></td>
            <td>{', '.join(keywords)}</td>
        </tr>
    </table>
    <br>
    <a href="{dart_url}" target="_blank" style="background-color:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;">원문 보기</a>
    <br><br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)

def send_stock_alert(stock_name: str, current_price: int, change_rate: float, alert_type: str, message: str) -> bool:
    """
    주식 가격 알림 이메일 발송
    
    Args:
        stock_name: 종목명
        current_price: 현재가
        change_rate: 변동률
        alert_type: 알림 타입 (target_price, stop_loss, surge, drop)
        message: 알림 메시지
    
    Returns:
        bool: 발송 성공 여부
    """
    subject = f"[주가 알림] {stock_name} - {alert_type.upper()}"
    
    text_content = f"""
주식 가격 알림

종목명: {stock_name}
현재가: {current_price:,}원
변동률: {change_rate:+.2f}%
알림 유형: {alert_type}

{message}

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # 변동률에 따른 색상 설정
    color = "#d32f2f" if change_rate < 0 else "#1976d2" if change_rate > 0 else "#757575"
    
    html_content = f"""
<html>
<body>
    <h2>📈 주가 알림</h2>
    <table border="1" style="border-collapse:collapse; width:100%;">
        <tr>
            <td><strong>종목명</strong></td>
            <td>{stock_name}</td>
        </tr>
        <tr>
            <td><strong>현재가</strong></td>
            <td>{current_price:,}원</td>
        </tr>
        <tr>
            <td><strong>변동률</strong></td>
            <td style="color:{color};font-weight:bold;">{change_rate:+.2f}%</td>
        </tr>
        <tr>
            <td><strong>알림 유형</strong></td>
            <td>{alert_type}</td>
        </tr>
    </table>
    <br>
    <div style="background-color:#f5f5f5;padding:10px;border-radius:4px;">
        {message}
    </div>
    <br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)

def send_stock_alert_with_time_limit(stock_code: str, stock_name: str, current_price: int, change_rate: float, alert_type: str, message: str) -> bool:
    """
    시간 제한 및 중복 방지 기능이 포함된 주식 기가 알림 이메일 발송
    
    Args:
        stock_code (str): 종목 코드 (6자리)
        stock_name (str): 종목명
        current_price (int): 현재가
        change_rate (float): 변동률
        alert_type (str): 알림 타입 (target_price, stop_loss, surge, drop)
        message (str): 알림 메시지
        
    Returns:
        bool: 발송 성공 여부 (시간 제한으로 인한 실패 포함)
    """
    from .logger_utils import get_logger
    
    logger = get_logger('email')
    
    # StockMonitor 인스턴스를 가져와서 시간 체크
    try:
        from .stock_monitor import stock_monitor
        
        # 시간 제한 및 중복 방지 체크
        if not stock_monitor.can_send_stock_alert(stock_code, alert_type):
            return False
            
        # 실제 알림 발송
        result = send_stock_alert(stock_name, current_price, change_rate, alert_type, message)
        
        # 발송 성공 시 마킹
        if result:
            stock_monitor.mark_alert_sent(stock_code, alert_type)
            logger.info(f"주식 알림 발송 성공: {stock_name}({stock_code}) - {alert_type}")
        else:
            logger.warning(f"주식 알림 발송 실패: {stock_name}({stock_code}) - {alert_type}")
            
        return result
        
    except Exception as e:
        logger.error(f"주식 알림 발송 오류: {e}")
        # 오류 발생 시 기존 함수로 폴백
        return send_stock_alert(stock_name, current_price, change_rate, alert_type, message)

def is_stock_market_time() -> bool:
    """
    주식 시장 시간대(9:00-15:30) 체크 - 독립 함수
    
    Returns:
        bool: 시장 시간 내이면 True, 아니면 False
    """
    from datetime import datetime
    
    now = datetime.now()
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= now <= market_close

# datetime import 추가
from datetime import datetime

def send_daily_stock_report(subject: str, html_content: str, report_data: dict) -> bool:
    """
    일일 주식 모니터링 보고서 이메일 발송
    
    Args:
        subject: 이메일 제목
        html_content: HTML 내용
        report_data: 보고서 데이터
    
    Returns:
        bool: 발송 성공 여부
    """
    
    # 텍스트 버전 생성
    text_content = f"""
일일 주식 모니터링 보고서 - {report_data['date']}

모니터링 종목: {report_data['active_stocks']}/{report_data['total_stocks']}개

주요 상승 종목 ({report_data['summary']['gainers_count']}개):
"""
    
    for stock in report_data['gainers']:
        text_content += f"- {stock['name']} ({stock['code']}): {stock['current_price']:,}원 (+{stock['change_percent']:.2f}%)\n"
    
    if not report_data['gainers']:
        text_content += "- 3% 이상 상승한 종목이 없습니다.\n"
    
    text_content += f"\n주요 하락 종목 ({report_data['summary']['losers_count']}개):\n"
    
    for stock in report_data['losers']:
        text_content += f"- {stock['name']} ({stock['code']}): {stock['current_price']:,}원 ({stock['change_percent']:.2f}%)\n"
    
    if not report_data['losers']:
        text_content += "- 3% 이상 하락한 종목이 없습니다.\n"
    
    text_content += f"\n오늘 발생한 알림 ({report_data['summary']['alerts_count']}개):\n"
    
    for stock in report_data['alert_triggered']:
        alerts_str = ', '.join(stock.get('alerts', []))
        text_content += f"- {stock['name']} ({stock['code']}): {alerts_str}\n"
    
    if not report_data['alert_triggered']:
        text_content += "- 오늘 발생한 알림이 없습니다.\n"
    
    text_content += f"\n발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    text_content += "\nD2 Dash 투자 모니터링 시스템에서 자동 발송된 메일입니다."
    
    return send_email(subject, text_content, html_content)

def send_parity_alert_enhanced(stock_name: str, stock_code: str, current_price: int, 
                               parity_percent: int, conversion_price: int) -> bool:
    """
    패리티 알림 전용 이메일 발송 (확장 버전)
    
    Args:
        stock_name: 종목명
        stock_code: 종목코드
        current_price: 현재가
        parity_percent: 패리티 퍼센트 (80, 100, 120)
        conversion_price: 전환가격
    
    Returns:
        bool: 발송 성공 여부
    """
    subject = f"[패리티 알림] {stock_name} - {parity_percent}% 도달"
    
    text_content = f"""
📊 메자닌 패리티 알림

종목명: {stock_name} ({stock_code})
현재가: {current_price:,}원
전환가격: {conversion_price:,}원
패리티: {parity_percent}%

패리티 {parity_percent}%에 도달했습니다!

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # 패리티 퍼센트에 따른 배경색 설정
    bg_color = "#fff3e0" if parity_percent < 100 else "#e8f5e8" if parity_percent == 100 else "#fff8e1"
    border_color = "#ff9800" if parity_percent < 100 else "#4caf50" if parity_percent == 100 else "#ffc107"
    
    html_content = f"""
<html>
<body>
    <h2>📊 메자닌 패리티 알림</h2>
    <div style="background-color:{bg_color};padding:15px;border-radius:8px;border-left:4px solid {border_color};margin:10px 0;">
        <h3 style="margin:0 0 10px 0;">패리티 {parity_percent}% 도달!</h3>
        <p style="margin:0;font-size:16px;"><strong>{stock_name} ({stock_code})</strong></p>
    </div>
    
    <table border="1" style="border-collapse:collapse; width:100%; margin:15px 0;">
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>현재가</strong></td>
            <td style="padding:8px;">{current_price:,}원</td>
        </tr>
        <tr>
            <td style="padding:8px;"><strong>전환가격</strong></td>
            <td style="padding:8px;">{conversion_price:,}원</td>
        </tr>
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>패리티</strong></td>
            <td style="padding:8px;color:{border_color};font-weight:bold;">{parity_percent}%</td>
        </tr>
    </table>
    
    <div style="background-color:#e3f2fd;padding:10px;border-radius:4px;">
        <strong>💡 패리티란?</strong> 현재 주가를 전환가격으로 나눈 비율로, 전환 시점의 수익성을 나타냅니다.
    </div>
    
    <br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)

def send_volatility_alert(stock_name: str, stock_code: str, current_price: int, 
                         change_percent: float, alert_type: str, threshold: float) -> bool:
    """
    급등급락 알림 전용 이메일 발송
    
    Args:
        stock_name: 종목명
        stock_code: 종목코드
        current_price: 현재가
        change_percent: 변동률
        alert_type: 알림 타입 (surge/drop)
        threshold: 임계값
    
    Returns:
        bool: 발송 성공 여부
    """
    is_surge = alert_type == "surge"
    emoji = "🚀" if is_surge else "📉"
    direction = "급등" if is_surge else "급락"
    color = "#4caf50" if is_surge else "#f44336"
    
    subject = f"[{direction} 알림] {stock_name} - {change_percent:+.2f}%"
    
    text_content = f"""
{emoji} 일일 {direction} 알림

종목명: {stock_name} ({stock_code})
현재가: {current_price:,}원
변동률: {change_percent:+.2f}%
임계값: {threshold:+.1f}%

{direction} 임계값 {threshold:+.1f}%를 {'돌파' if is_surge else '하회'}했습니다!

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    html_content = f"""
<html>
<body>
    <h2>{emoji} 일일 {direction} 알림</h2>
    <div style="background-color:{'#e8f5e8' if is_surge else '#ffebee'};padding:15px;border-radius:8px;border-left:4px solid {color};margin:10px 0;">
        <h3 style="margin:0 0 10px 0;color:{color};">{direction} 임계값 {'돌파' if is_surge else '하회'}!</h3>
        <p style="margin:0;font-size:16px;"><strong>{stock_name} ({stock_code})</strong></p>
    </div>
    
    <table border="1" style="border-collapse:collapse; width:100%; margin:15px 0;">
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>현재가</strong></td>
            <td style="padding:8px;">{current_price:,}원</td>
        </tr>
        <tr>
            <td style="padding:8px;"><strong>일일 변동률</strong></td>
            <td style="padding:8px;color:{color};font-weight:bold;font-size:18px;">{change_percent:+.2f}%</td>
        </tr>
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>알림 임계값</strong></td>
            <td style="padding:8px;">{threshold:+.1f}%</td>
        </tr>
    </table>
    
    <div style="background-color:#fff3e0;padding:10px;border-radius:4px;">
        <strong>⚠️ 주의사항:</strong> 급격한 가격 변동이 발생했습니다. 시장 상황을 면밀히 모니터링하시기 바랍니다.
    </div>
    
    <br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)

def send_target_stop_alert_enhanced(stock_name: str, stock_code: str, current_price: int, 
                                   target_price: int, alert_type: str, acquisition_price: int = 0) -> bool:
    """
    목표가/손절가 알림 전용 이메일 발송 (확장 버전)
    
    Args:
        stock_name: 종목명
        stock_code: 종목코드
        current_price: 현재가
        target_price: 목표가/손절가
        alert_type: 알림 타입 (target_price/stop_loss)
        acquisition_price: 취득가 (선택)
    
    Returns:
        bool: 발송 성공 여부
    """
    is_target = alert_type == "target_price"
    emoji = "🎯" if is_target else "🛑"
    title = "목표가 달성" if is_target else "손절가 도달"
    color = "#4caf50" if is_target else "#f44336"
    
    subject = f"[{title}] {stock_name} - {target_price:,}원"
    
    # 수익률 계산 (취득가가 있는 경우)
    profit_rate = 0
    if acquisition_price > 0:
        profit_rate = ((current_price - acquisition_price) / acquisition_price) * 100
    
    text_content = f"""
{emoji} {title} 알림

종목명: {stock_name} ({stock_code})
현재가: {current_price:,}원
{'목표가' if is_target else '손절가'}: {target_price:,}원
"""
    
    if acquisition_price > 0:
        text_content += f"취득가: {acquisition_price:,}원\n수익률: {profit_rate:+.2f}%\n"
    
    text_content += f"""
{'목표가에 도달했습니다!' if is_target else '손절가에 도달했습니다.'}

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    html_content = f"""
<html>
<body>
    <h2>{emoji} {title} 알림</h2>
    <div style="background-color:{'#e8f5e8' if is_target else '#ffebee'};padding:15px;border-radius:8px;border-left:4px solid {color};margin:10px 0;">
        <h3 style="margin:0 0 10px 0;color:{color};">{'🎉 목표가 달성!' if is_target else '⚠️ 손절가 도달'}</h3>
        <p style="margin:0;font-size:16px;"><strong>{stock_name} ({stock_code})</strong></p>
    </div>
    
    <table border="1" style="border-collapse:collapse; width:100%; margin:15px 0;">
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>현재가</strong></td>
            <td style="padding:8px;">{current_price:,}원</td>
        </tr>
        <tr>
            <td style="padding:8px;"><strong>{'목표가' if is_target else '손절가'}</strong></td>
            <td style="padding:8px;color:{color};font-weight:bold;">{target_price:,}원</td>
        </tr>
"""
    
    if acquisition_price > 0:
        profit_color = "#4caf50" if profit_rate >= 0 else "#f44336"
        html_content += f"""
        <tr style="background-color:#f5f5f5;">
            <td style="padding:8px;"><strong>취득가</strong></td>
            <td style="padding:8px;">{acquisition_price:,}원</td>
        </tr>
        <tr>
            <td style="padding:8px;"><strong>수익률</strong></td>
            <td style="padding:8px;color:{profit_color};font-weight:bold;font-size:18px;">{profit_rate:+.2f}%</td>
        </tr>
"""
    
    html_content += f"""
    </table>
    
    <div style="background-color:{'#e3f2fd' if is_target else '#fff3e0'};padding:10px;border-radius:4px;">
        <strong>{'💡 투자 의사결정' if is_target else '⚠️ 리스크 관리'}:</strong> 
        {'목표가 달성으로 수익 실현을 고려해보세요.' if is_target else '손절가 도달로 리스크 관리가 필요합니다.'}
    </div>
    
    <br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)

def send_test_email(subject: str = None, message: str = None) -> bool:
    """
    테스트 이메일 발송
    
    Args:
        subject: 이메일 제목 (선택사항)
        message: 이메일 내용 (선택사항)
    
    Returns:
        bool: 발송 성공 여부
    """
    if not subject:
        subject = "[D2 Dash] 이메일 테스트"
    
    if not message:
        message = "D2 Dash 투자 모니터링 시스템 이메일 테스트입니다."
    
    text_content = f"""
{message}

발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

이 메일은 테스트 목적으로 발송되었습니다.
"""
    
    html_content = f"""
<html>
<body>
    <h2>✅ 이메일 테스트</h2>
    <p>{message}</p>
    <br>
    <div style="background-color:#e8f5e8;padding:10px;border-radius:4px;border-left:4px solid #4CAF50;">
        <strong>✓ 이메일 시스템이 정상적으로 작동하고 있습니다.</strong>
    </div>
    <br>
    <small>발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
    <br>
    <small>이 메일은 테스트 목적으로 발송되었습니다.</small>
</body>
</html>
"""
    
    return send_email(subject, text_content, html_content)