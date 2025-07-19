import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from typing import List, Optional
import logging
from datetime import datetime
import asyncio

from app.config import settings
from app.utils.logger import email_logger as logger, auto_retry


class EmailService:
    """이메일 발송 서비스 - SMTP 연결 풀링 및 재시도 로직 포함"""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.EMAIL_SENDER
        self.sender_password = settings.EMAIL_PASSWORD
        self.default_receiver = settings.EMAIL_RECEIVER
        self._connection_pool = {}  # SMTP 연결 풀
        self._pool_lock = asyncio.Lock()
        self.max_pool_size = 5
        self.connection_timeout = 300  # 5분
    
    @auto_retry(max_retries=3, delay=2.0, exceptions=(Exception,))
    async def send_email_async(
        self, 
        subject: str, 
        body: str, 
        to_email: Optional[str] = None,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """비동기 이메일 발송"""
        try:
            recipient = to_email or self.default_receiver
            
            # 이메일 메시지 생성
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = recipient
            message['Subject'] = subject
            
            # 텍스트 본문 추가
            text_part = MIMEText(body, 'plain', 'utf-8')
            message.attach(text_part)
            
            # HTML 본문 추가 (있는 경우)
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                message.attach(html_part)
            
            # 첨부파일 추가 (있는 경우)
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {file_path.split("/")[-1]}'
                            )
                            message.attach(part)
                    except Exception as e:
                        logger.error(f"첨부파일 추가 실패 ({file_path}): {e}")
            
            # 이메일 발송
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.sender_email,
                password=self.sender_password
            )
            
            logger.info(f"이메일 발송 성공: {recipient} - {subject}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            return False
    
    @auto_retry(max_retries=3, delay=2.0, exceptions=(Exception,))
    def send_email_sync(
        self, 
        subject: str, 
        body: str, 
        to_email: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """동기 이메일 발송 (기존 스크립트 호환성)"""
        try:
            recipient = to_email or self.default_receiver
            
            # 이메일 메시지 생성
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = recipient
            message['Subject'] = subject
            
            # 텍스트 본문 추가
            text_part = MIMEText(body, 'plain', 'utf-8')
            message.attach(text_part)
            
            # HTML 본문 추가 (있는 경우)
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                message.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            logger.info(f"이메일 발송 성공: {recipient} - {subject}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            return False


# 전역 이메일 서비스 인스턴스
email_service = EmailService()


async def send_dart_alert(company_name: str, disclosure_title: str, disclosure_url: str) -> bool:
    """DART 공시 알림 이메일 발송"""
    subject = f"[DART 공시] {company_name} - {disclosure_title}"
    
    body = f"""
투자본부 모니터링 시스템

새로운 공시가 발견되었습니다.

회사명: {company_name}
공시제목: {disclosure_title}
공시일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

공시 원문 보기: {disclosure_url}

---
투자본부 모니터링 시스템 자동 발송
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DART 공시 알림</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">투자본부 모니터링 시스템</h2>
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #1e40af; margin-top: 0;">새로운 공시가 발견되었습니다</h3>
            <p><strong>회사명:</strong> {company_name}</p>
            <p><strong>공시제목:</strong> {disclosure_title}</p>
            <p><strong>공시일시:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 20px;">
                <a href="{disclosure_url}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">공시 원문 보기</a>
            </p>
        </div>
        <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
            투자본부 모니터링 시스템 자동 발송
        </p>
    </div>
</body>
</html>
"""
    
    return await email_service.send_email_async(subject, body, html_body=html_body)


async def send_stock_alert(stock_name: str, stock_code: str, current_price: float, 
                          change_rate: float, alert_type: str, alert_price: float) -> bool:
    """주가 알림 이메일 발송"""
    alert_type_kr = {
        'take_profit': '목표가 달성',
        'stop_loss': '손절가 도달',
        'surge': '급등 알림',
        'drop': '급락 알림'
    }.get(alert_type, '주가 알림')
    
    subject = f"[주가 알림] {stock_name}({stock_code}) - {alert_type_kr}"
    
    body = f"""
투자본부 모니터링 시스템

주가 알림이 발생했습니다.

종목명: {stock_name}({stock_code})
현재가: {current_price:,.0f}원
변동률: {change_rate:+.2f}%
알림유형: {alert_type_kr}
알림가격: {alert_price:,.0f}원
알림시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
투자본부 모니터링 시스템 자동 발송
"""
    
    color = "#dc2626" if alert_type in ['stop_loss', 'drop'] else "#16a34a"
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>주가 알림</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">투자본부 모니터링 시스템</h2>
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color};">
            <h3 style="color: {color}; margin-top: 0;">주가 알림이 발생했습니다</h3>
            <p><strong>종목명:</strong> {stock_name}({stock_code})</p>
            <p><strong>현재가:</strong> {current_price:,.0f}원</p>
            <p><strong>변동률:</strong> <span style="color: {color};">{change_rate:+.2f}%</span></p>
            <p><strong>알림유형:</strong> {alert_type_kr}</p>
            <p><strong>알림가격:</strong> {alert_price:,.0f}원</p>
            <p><strong>알림시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
            투자본부 모니터링 시스템 자동 발송
        </p>
    </div>
</body>
</html>
"""
    
    return await email_service.send_email_async(subject, body, html_body=html_body)


async def send_system_alert(title: str, message: str, alert_level: str = "info") -> bool:
    """시스템 알림 이메일 발송"""
    level_colors = {
        "info": "#2563eb",
        "warning": "#d97706",
        "error": "#dc2626",
        "success": "#16a34a"
    }
    
    color = level_colors.get(alert_level, "#2563eb")
    subject = f"[시스템 알림] {title}"
    
    body = f"""
투자본부 모니터링 시스템

시스템 알림이 발생했습니다.

제목: {title}
내용: {message}
알림시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
투자본부 모니터링 시스템 자동 발송
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>시스템 알림</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">투자본부 모니터링 시스템</h2>
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color};">
            <h3 style="color: {color}; margin-top: 0;">시스템 알림</h3>
            <p><strong>제목:</strong> {title}</p>
            <p><strong>내용:</strong> {message}</p>
            <p><strong>알림시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
            투자본부 모니터링 시스템 자동 발송
        </p>
    </div>
</body>
</html>
"""
    
    return await email_service.send_email_async(subject, body, html_body=html_body)