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

# datetime import 추가
from datetime import datetime