"""
V2 Investment Monitor - 통합 알림 서비스
DART/주식/시스템 알림 통합 processing
"""
import smtplib
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import logging
import json

from ..core.config import settings
from ..core.database import database

logger = logging.getLogger(__name__)


class NotificationService:
    """통합 알림 processing 서비스"""
    
    def __init__(self):
        self.email_sender = settings.email_sender
        self.email_password = settings.email_password
        self.email_receiver = settings.email_receiver
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        
        # 이메일 템플릿
        self.templates = {
            "dart": self._dart_email_template,
            "stock": self._stock_email_template,
            "system": self._system_email_template
        }
    
    async def create_dart_notification(self, disclosure: Dict) -> bool:
        """DART 공시 알림 creating"""
        try:
            title = f"[NOTIFICATION] [{disclosure['corp_name']}] {disclosure['report_nm']}"
            message = self._format_dart_message(disclosure)
            
            # 데이터베이스에 저장
            await self._save_notification(
                notification_type="dart",
                title=title,
                message=message,
                related_id=disclosure.get("rcept_no"),
                data=disclosure,
                priority="high" if disclosure.get("priority_score", 0) >= 5 else "medium"
            )
            
            # 이메일 sending
            await self._send_email_notification("dart", title, disclosure)
            
            logger.info(f"[EMAIL] DART 알림 creating: {disclosure['corp_name']}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] DART 알림 creating failed: {e}")
            return False
    
    async def create_stock_notification(self, alert_data: Dict) -> bool:
        """주식 알림 creating"""
        try:
            title = f"[STOCK] {alert_data['stock_name']} 가격 알림"
            message = alert_data.get("message", "")
            
            # 데이터베이스에 저장
            await self._save_notification(
                notification_type="stock",
                title=title,
                message=message,
                related_id=alert_data.get("stock_code"),
                data=alert_data,
                priority="high"
            )
            
            # 이메일 sending
            await self._send_email_notification("stock", title, alert_data)
            
            logger.info(f"[EMAIL] 주식 알림 creating: {alert_data['stock_name']}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] 주식 알림 creating failed: {e}")
            return False
    
    async def create_system_notification(self, title: str, message: str, priority: str = "medium") -> bool:
        """시스템 알림 creating"""
        try:
            await self._save_notification(
                notification_type="system",
                title=title,
                message=message,
                priority=priority
            )
            
            # 높은 우선순위는 이메일 sending
            if priority == "high":
                await self._send_email_notification("system", title, {"message": message})
            
            logger.info(f"🔧 시스템 알림 creating: {title}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] 시스템 알림 creating failed: {e}")
            return False
    
    async def _save_notification(
        self,
        notification_type: str,
        title: str, 
        message: str,
        related_id: Optional[str] = None,
        data: Optional[Dict] = None,
        priority: str = "medium"
    ) -> None:
        """알림을 데이터베이스에 저장"""
        query = """
            INSERT INTO notification_history 
            (notification_type, title, message, related_id, data, priority, is_sent)
            VALUES (:type, :title, :message, :related_id, :data, :priority, :is_sent)
        """
        
        await database.execute(query, {
            "type": notification_type,
            "title": title,
            "message": message,
            "related_id": related_id,
            "data": json.dumps(data, ensure_ascii=False) if data else None,
            "priority": priority,
            "is_sent": False
        })
    
    async def _send_email_notification(self, notification_type: str, title: str, data: Dict) -> bool:
        """이메일 알림 sending"""
        try:
            # 이메일 템플릿 적용
            if notification_type in self.templates:
                html_content = self.templates[notification_type](title, data)
            else:
                html_content = self._default_email_template(title, data)
            
            # 이메일 message 구성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = self.email_sender
            msg['To'] = self.email_receiver
            
            # HTML 파트 추가
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # SMTP sending
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)
            
            # sending 상태 updating
            await self._update_notification_sent_status(title, True)
            
            logger.info(f"[EMAIL] 이메일 sending success: {title}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] 이메일 sending failed: {e}")
            await self._update_notification_sent_status(title, False)
            return False
    
    async def _update_notification_sent_status(self, title: str, is_sent: bool) -> None:
        """알림 sending 상태 updating"""
        query = """
            UPDATE notification_history 
            SET is_sent = :is_sent, sent_at = :sent_at
            WHERE title = :title AND created_at >= datetime('now', '-1 hour')
        """
        
        await database.execute(query, {
            "is_sent": is_sent,
            "sent_at": datetime.now() if is_sent else None,
            "title": title
        })
    
    def _dart_email_template(self, title: str, disclosure: Dict) -> str:
        """DART 공시 이메일 템플릿"""
        keywords = ", ".join(disclosure.get("matched_keywords", []))
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 10px;">
                    {title}
                </h2>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p><strong>기업명:</strong> {disclosure.get('corp_name', '')}</p>
                    <p><strong>보고서명:</strong> {disclosure.get('report_nm', '')}</p>
                    <p><strong>접수일자:</strong> {disclosure.get('rcept_dt', '')}</p>
                    <p><strong>공시대상:</strong> {disclosure.get('flr_nm', 'N/A')}</p>
                    <p><strong>매칭 키워드:</strong> <span style="color: #dc3545; font-weight: bold;">{keywords}</span></p>
                    <p><strong>우선순위:</strong> {disclosure.get('priority_score', 0)}점</p>
                </div>
                
                {f"<div style='background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0;'><strong>비고:</strong> {disclosure.get('rm', '')}</div>" if disclosure.get('rm') else ''}
                
                <div style="margin-top: 20px; padding: 10px; background-color: #e8f4f8; border-radius: 5px;">
                    <p style="margin: 0; font-size: 12px; color: #666;">
                        투자본부 모니터링 시스템 | {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _stock_email_template(self, title: str, alert_data: Dict) -> str:
        """주식 알림 이메일 템플릿"""
        alert_type = alert_data.get("alert_type", "")
        current_price = alert_data.get("current_price", 0)
        
        # 알림 타입별 색상
        color = "#dc3545" if "stop_loss" in alert_type else "#28a745"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">
                    {title}
                </h2>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p><strong>종목명:</strong> {alert_data.get('stock_name', '')}</p>
                    <p><strong>종목코드:</strong> {alert_data.get('stock_code', '')}</p>
                    <p><strong>현재가:</strong> <span style="font-size: 18px; font-weight: bold; color: {color};">{current_price:,.0f}원</span></p>
                    
                    {f"<p><strong>목표가:</strong> {alert_data.get('target_price', 0):,.0f}원</p>" if alert_data.get('target_price') else ''}
                    {f"<p><strong>손절가:</strong> {alert_data.get('stop_loss_price', 0):,.0f}원</p>" if alert_data.get('stop_loss_price') else ''}
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p style="margin: 0; font-weight: bold;">{alert_data.get('message', '')}</p>
                </div>
                
                <div style="margin-top: 20px; padding: 10px; background-color: #e8f4f8; border-radius: 5px;">
                    <p style="margin: 0; font-size: 12px; color: #666;">
                        투자본부 주식 모니터링 시스템 | {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _system_email_template(self, title: str, data: Dict) -> str:
        """시스템 알림 이메일 템플릿"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #6c757d; border-bottom: 2px solid #6c757d; padding-bottom: 10px;">
                    {title}
                </h2>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p>{data.get('message', '')}</p>
                </div>
                
                <div style="margin-top: 20px; padding: 10px; background-color: #e8f4f8; border-radius: 5px;">
                    <p style="margin: 0; font-size: 12px; color: #666;">
                        투자본부 모니터링 시스템 | {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _default_email_template(self, title: str, data: Dict) -> str:
        """기본 이메일 템플릿"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>{title}</h2>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                    <pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_dart_message(self, disclosure: Dict) -> str:
        """DART 공시 message 포맷팅"""
        keywords = ", ".join(disclosure.get("matched_keywords", []))
        message = f"""
{disclosure.get('corp_name', '')} - {disclosure.get('report_nm', '')}
접수일자: {disclosure.get('rcept_dt', '')}
매칭 키워드: {keywords}
우선순위: {disclosure.get('priority_score', 0)}점
        """.strip()
        
        if disclosure.get('rm'):
            message += f"\n비고: {disclosure['rm']}"
            
        return message
    
    async def get_recent_notifications(
        self, 
        notification_type: Optional[str] = None,
        limit: int = 50,
        days: int = 7
    ) -> List[Dict]:
        """최근 알림 querying"""
        query = """
            SELECT * FROM notification_history 
            WHERE created_at >= datetime('now', '-{} days')
            {} 
            ORDER BY created_at DESC 
            LIMIT {}
        """.format(
            days,
            f"AND notification_type = '{notification_type}'" if notification_type else "",
            limit
        )
        
        rows = await database.fetch_all(query)
        return [dict(row) for row in rows]
    
    async def mark_notifications_read(self, notification_ids: List[int]) -> bool:
        """알림을 읽음으로 표시"""
        try:
            query = """
                UPDATE notification_history 
                SET is_read = true 
                WHERE id IN ({})
            """.format(",".join(map(str, notification_ids)))
            
            await database.execute(query)
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] 알림 읽음 processing failed: {e}")
            return False
    
    async def get_notification_statistics(self) -> Dict:
        """알림 통계 querying"""
        queries = {
            "total_count": "SELECT COUNT(*) FROM notification_history",
            "unread_count": "SELECT COUNT(*) FROM notification_history WHERE is_read = false",
            "unsent_count": "SELECT COUNT(*) FROM notification_history WHERE is_sent = false",
            "dart_count": "SELECT COUNT(*) FROM notification_history WHERE notification_type = 'dart'",
            "stock_count": "SELECT COUNT(*) FROM notification_history WHERE notification_type = 'stock'",
            "system_count": "SELECT COUNT(*) FROM notification_history WHERE notification_type = 'system'"
        }
        
        stats = {}
        for key, query in queries.items():
            try:
                result = await database.fetch_val(query)
                stats[key] = result or 0
            except:
                stats[key] = 0
        
        return stats


# === 전역 서비스 인스턴스 ===
notification_service = NotificationService()