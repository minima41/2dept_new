"""
공통 이메일 발송 유틸리티 모듈
기존 shared/email.py 모듈의 래퍼 함수들 제공
"""
from typing import Optional, List
import asyncio
from datetime import datetime

from app.shared.email import (
    email_service,
    send_dart_alert,
    send_stock_alert, 
    send_system_alert
)
from app.utils.logger import email_logger as logger


async def send_email(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
    html_body: Optional[str] = None,
    attachments: Optional[List[str]] = None
) -> bool:
    """
    간편한 이메일 발송 함수
    
    Args:
        subject: 이메일 제목
        body: 이메일 본문 (텍스트)
        to_email: 수신자 이메일 (None이면 기본 수신자)
        html_body: HTML 본문 (선택사항)
        attachments: 첨부파일 경로 리스트 (선택사항)
    
    Returns:
        발송 성공 여부
    """
    return await email_service.send_email_async(
        subject=subject,
        body=body,
        to_email=to_email,
        html_body=html_body,
        attachments=attachments
    )


def send_email_sync(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
    html_body: Optional[str] = None
) -> bool:
    """
    동기식 이메일 발송 함수 (기존 스크립트 호환성)
    
    Args:
        subject: 이메일 제목
        body: 이메일 본문 (텍스트)
        to_email: 수신자 이메일 (None이면 기본 수신자)
        html_body: HTML 본문 (선택사항)
    
    Returns:
        발송 성공 여부
    """
    return email_service.send_email_sync(
        subject=subject,
        body=body,
        to_email=to_email,
        html_body=html_body
    )


async def send_notification(
    title: str,
    message: str,
    notification_type: str = "info",
    to_email: Optional[str] = None
) -> bool:
    """
    일반적인 알림 이메일 발송
    
    Args:
        title: 알림 제목
        message: 알림 메시지
        notification_type: 알림 유형 (info, warning, error, success)
        to_email: 수신자 이메일
    
    Returns:
        발송 성공 여부
    """
    return await send_system_alert(
        title=title,
        message=message,
        alert_level=notification_type
    )


async def send_batch_emails(
    emails: List[dict],
    delay_between_emails: float = 1.0
) -> List[bool]:
    """
    배치 이메일 발송 (대량 발송 시 사용)
    
    Args:
        emails: 이메일 정보 딕셔너리 리스트
                [{"subject": "...", "body": "...", "to_email": "..."}, ...]
        delay_between_emails: 이메일 간 발송 지연 시간 (초)
    
    Returns:
        각 이메일 발송 성공 여부 리스트
    """
    results = []
    
    for i, email_data in enumerate(emails):
        try:
            result = await send_email(
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                to_email=email_data.get("to_email"),
                html_body=email_data.get("html_body")
            )
            results.append(result)
            
            # 마지막 이메일이 아니면 지연
            if i < len(emails) - 1:
                await asyncio.sleep(delay_between_emails)
                
        except Exception as e:
            logger.error(f"배치 이메일 발송 실패 (인덱스 {i}): {e}")
            results.append(False)
    
    success_count = sum(results)
    logger.info(f"배치 이메일 발송 완료: {success_count}/{len(emails)} 성공")
    
    return results


def validate_email_config() -> bool:
    """
    이메일 설정 유효성 검증
    
    Returns:
        설정이 유효한지 여부
    """
    try:
        from app.config import settings
        
        required_settings = [
            settings.EMAIL_SENDER,
            settings.EMAIL_PASSWORD,
            settings.EMAIL_RECEIVER,
            settings.SMTP_SERVER
        ]
        
        if not all(required_settings):
            logger.error("필수 이메일 설정이 누락되었습니다")
            return False
            
        if settings.SMTP_PORT not in [25, 587, 465, 993, 995]:
            logger.warning(f"비표준 SMTP 포트 사용 중: {settings.SMTP_PORT}")
            
        return True
        
    except Exception as e:
        logger.error(f"이메일 설정 검증 실패: {e}")
        return False


# 전용 알림 함수들 (기존 호환성 유지)
send_dart_notification = send_dart_alert
send_stock_notification = send_stock_alert
send_system_notification = send_system_alert

__all__ = [
    'send_email',
    'send_email_sync', 
    'send_notification',
    'send_batch_emails',
    'validate_email_config',
    'send_dart_notification',
    'send_stock_notification',
    'send_system_notification'
]