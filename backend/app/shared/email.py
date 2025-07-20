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


async def send_daily_summary_email(stocks_data: dict) -> bool:
    """일일 마감 요약 이메일 발송"""
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # 메자닌과 기타 종목 분리 (MonitoringStock 객체 처리)
        all_stocks = stocks_data.get('stocks', [])
        mezzanine_stocks = []
        other_stocks = []
        
        for stock in all_stocks:
            # MonitoringStock 객체를 dict로 변환
            if hasattr(stock, 'category'):
                if stock.category == 'mezzanine':
                    mezzanine_stocks.append(stock.dict() if hasattr(stock, 'dict') else stock)
                else:
                    other_stocks.append(stock.dict() if hasattr(stock, 'dict') else stock)
            else:
                # 기본값으로 기타 투자로 분류
                other_stocks.append(stock.dict() if hasattr(stock, 'dict') else stock)
        
        # 등락률 기준 정렬 (dict 접근 방식) - None 값 처리
        def safe_get_change_rate(item):
            try:
                if isinstance(item, dict):
                    return item.get('change_rate') or 0
                else:
                    return getattr(item, 'change_rate', None) or 0
            except:
                return 0
        
        mezzanine_stocks.sort(key=safe_get_change_rate, reverse=True)
        other_stocks.sort(key=safe_get_change_rate, reverse=True)
        
        # 통계 정보
        statistics = stocks_data.get('statistics', {})
        
        subject = f"[투자본부] 일일 마감 요약 - {current_date}"
        
        # 텍스트 본문
        body = f"""
투자본부 모니터링 시스템 일일 마감 요약

마감일시: {current_date} {current_time}
총 종목 수: {statistics.get('total_stocks', 0)}개

=== 메자닌 투자 ({len(mezzanine_stocks)}개 종목) ===
투자금액: {statistics.get('mezzanine_investment', 0):,.0f}원
평가금액: {statistics.get('mezzanine_portfolio_value', 0):,.0f}원
손익금액: {statistics.get('mezzanine_profit_loss', 0):,.0f}원 ({statistics.get('mezzanine_profit_loss_rate', 0):.2f}%)

=== 기타 투자 ({len(other_stocks)}개 종목) ===
투자금액: {statistics.get('other_investment', 0):,.0f}원
평가금액: {statistics.get('other_portfolio_value', 0):,.0f}원
손익금액: {statistics.get('other_profit_loss', 0):,.0f}원 ({statistics.get('other_profit_loss_rate', 0):.2f}%)

=== 전체 요약 ===
총 투자금액: {statistics.get('total_investment', 0):,.0f}원
총 평가금액: {statistics.get('total_portfolio_value', 0):,.0f}원
총 손익금액: {statistics.get('total_profit_loss', 0):,.0f}원 ({statistics.get('total_profit_loss_rate', 0):.2f}%)

---
투자본부 모니터링 시스템 자동 발송
"""
        
        # HTML 본문 생성
        html_body = _generate_daily_summary_html(
            current_date, current_time, mezzanine_stocks, other_stocks, statistics
        )
        
        return await email_service.send_email_async(subject, body, html_body=html_body)
        
    except Exception as e:
        logger.error(f"일일 마감 요약 이메일 발송 실패: {e}")
        return False


def _generate_daily_summary_html(date: str, time: str, mezzanine_stocks: list, other_stocks: list, statistics: dict) -> str:
    """일일 마감 요약 HTML 템플릿 생성"""
    
    def format_currency(amount):
        return f"{amount:,.0f}" if amount else "0"
    
    def format_percent(percent):
        return f"{percent:+.2f}%" if percent else "0.00%"
    
    def get_color_class(value):
        if value > 0:
            return "#dc2626"  # 빨간색 (상승)
        elif value < 0:
            return "#2563eb"  # 파란색 (하락)
        else:
            return "#6b7280"  # 회색 (보합)
    
    def generate_stock_table(stocks, table_type="other"):
        if not stocks:
            return f"<p style='text-align: center; color: #6b7280; padding: 20px;'>{table_type} 종목이 없습니다.</p>"
        
        # 메자닌과 기타에 따라 다른 헤더
        if table_type == "mezzanine":
            header_row = """
                <tr style="background-color: #f3f4f6;">
                    <th style="padding: 12px; text-align: left; border: 1px solid #e5e7eb;">종목명</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">현재가</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">변동률</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">패리티</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">전환가</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">취득가</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">수량</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">투자금액</th>
                </tr>
            """
        else:
            header_row = """
                <tr style="background-color: #f3f4f6;">
                    <th style="padding: 12px; text-align: left; border: 1px solid #e5e7eb;">종목명</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">현재가</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">변동률</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">수익률</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">취득가</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">수량</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">투자금액</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #e5e7eb;">손익금액</th>
                </tr>
            """
        
        rows = []
        for stock in stocks:
            change_color = get_color_class(stock.get('change_rate', 0))
            profit_color = get_color_class(stock.get('profit_loss_rate', 0) if table_type == "other" else stock.get('parity', 0))
            
            if table_type == "mezzanine":
                parity = stock.get('parity', 0)
                parity_color = "#16a34a" if parity >= 100 else "#dc2626"  # 녹색: 100% 이상, 빨간색: 100% 미만
                
                row = f"""
                    <tr style="background-color: white;">
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{stock.get('name', '')}<br><small style="color: #6b7280;">{stock.get('code', '')}</small></td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('current_price', 0))}원</td>
                        <td style="padding: 8px; text-align: right; color: {change_color}; border: 1px solid #e5e7eb; font-weight: bold;">{format_percent(stock.get('change_rate', 0))}</td>
                        <td style="padding: 8px; text-align: right; color: {parity_color}; border: 1px solid #e5e7eb; font-weight: bold;">{parity:.2f}%</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('conversion_price', 0))}원</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('acquisition_price') or stock.get('purchase_price', 0))}원</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('quantity', 0))}주</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency((stock.get('acquisition_price') or stock.get('purchase_price', 0)) * stock.get('quantity', 0))}원</td>
                    </tr>
                """
            else:
                row = f"""
                    <tr style="background-color: white;">
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{stock.get('name', '')}<br><small style="color: #6b7280;">{stock.get('code', '')}</small></td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('current_price', 0))}원</td>
                        <td style="padding: 8px; text-align: right; color: {change_color}; border: 1px solid #e5e7eb; font-weight: bold;">{format_percent(stock.get('change_rate', 0))}</td>
                        <td style="padding: 8px; text-align: right; color: {profit_color}; border: 1px solid #e5e7eb; font-weight: bold;">{format_percent(stock.get('profit_loss_rate', 0))}</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('acquisition_price') or stock.get('purchase_price', 0))}원</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency(stock.get('quantity', 0))}주</td>
                        <td style="padding: 8px; text-align: right; border: 1px solid #e5e7eb;">{format_currency((stock.get('acquisition_price') or stock.get('purchase_price', 0)) * stock.get('quantity', 0))}원</td>
                        <td style="padding: 8px; text-align: right; color: {profit_color}; border: 1px solid #e5e7eb; font-weight: bold;">{'+' if stock.get('profit_loss', 0) >= 0 else ''}{format_currency(stock.get('profit_loss', 0))}원</td>
                    </tr>
                """
            rows.append(row)
        
        return f"""
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                {header_row}
                {''.join(rows)}
            </table>
        """
    
    # 전체 HTML 템플릿
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>일일 마감 요약</title>
</head>
<body style="font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9fafb;">
    <div style="max-width: 1000px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        
        <!-- 헤더 -->
        <div style="background-color: #2563eb; color: white; padding: 20px;">
            <h1 style="margin: 0; font-size: 24px;">투자본부 모니터링 시스템</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">일일 마감 요약 - {date}</p>
        </div>
        
        <!-- 전체 요약 -->
        <div style="padding: 20px; background-color: #f8fafc; border-bottom: 1px solid #e5e7eb;">
            <h2 style="margin: 0 0 15px 0; color: #1f2937;">📊 전체 포트폴리오 요약</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #2563eb;">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">총 종목 수</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #1f2937;">{statistics.get('total_stocks', 0)}개</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #16a34a;">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">총 투자금액</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('total_investment', 0))}원</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #d97706;">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">총 평가금액</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('total_portfolio_value', 0))}원</p>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid {get_color_class(statistics.get('total_profit_loss', 0))};">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">총 손익</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: {get_color_class(statistics.get('total_profit_loss', 0))};">{'+' if statistics.get('total_profit_loss', 0) >= 0 else ''}{format_currency(statistics.get('total_profit_loss', 0))}원 ({format_percent(statistics.get('total_profit_loss_rate', 0))})</p>
                </div>
            </div>
        </div>
        
        <!-- 메자닌 투자 섹션 -->
        <div style="padding: 20px;">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <h2 style="margin: 0; color: #1f2937;">🎯 메자닌 투자</h2>
                <span style="margin-left: 10px; background-color: #ddd6fe; color: #7c3aed; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{len(mezzanine_stocks)}개 종목</span>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 20px;">
                <div style="background: #f3f4f6; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">투자금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('mezzanine_investment', 0))}원</p>
                </div>
                <div style="background: #f3f4f6; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">평가금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('mezzanine_portfolio_value', 0))}원</p>
                </div>
                <div style="background: #f3f4f6; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">손익금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: {get_color_class(statistics.get('mezzanine_profit_loss', 0))};">{'+' if statistics.get('mezzanine_profit_loss', 0) >= 0 else ''}{format_currency(statistics.get('mezzanine_profit_loss', 0))}원</p>
                </div>
                <div style="background: #f3f4f6; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">수익률</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: {get_color_class(statistics.get('mezzanine_profit_loss', 0))};">{format_percent(statistics.get('mezzanine_profit_loss_rate', 0))}</p>
                </div>
            </div>
            
            {generate_stock_table(mezzanine_stocks, "mezzanine")}
        </div>
        
        <!-- 기타 투자 섹션 -->
        <div style="padding: 20px; background-color: #f8fafc;">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <h2 style="margin: 0; color: #1f2937;">📈 기타 투자</h2>
                <span style="margin-left: 10px; background-color: #dbeafe; color: #2563eb; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{len(other_stocks)}개 종목</span>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 20px;">
                <div style="background: white; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">투자금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('other_investment', 0))}원</p>
                </div>
                <div style="background: white; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">평가금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #1f2937;">{format_currency(statistics.get('other_portfolio_value', 0))}원</p>
                </div>
                <div style="background: white; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">손익금액</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: {get_color_class(statistics.get('other_profit_loss', 0))};">{'+' if statistics.get('other_profit_loss', 0) >= 0 else ''}{format_currency(statistics.get('other_profit_loss', 0))}원</p>
                </div>
                <div style="background: white; padding: 12px; border-radius: 6px;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">수익률</p>
                    <p style="margin: 5px 0 0 0; font-weight: bold; color: {get_color_class(statistics.get('other_profit_loss', 0))};">{format_percent(statistics.get('other_profit_loss_rate', 0))}</p>
                </div>
            </div>
            
            {generate_stock_table(other_stocks, "other")}
        </div>
        
        <!-- 푸터 -->
        <div style="padding: 20px; background-color: #1f2937; color: white; text-align: center;">
            <p style="margin: 0; font-size: 14px;">투자본부 모니터링 시스템 자동 발송</p>
            <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.7;">마감일시: {date} {time}</p>
        </div>
        
    </div>
</body>
</html>
"""
    
    return html_template


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