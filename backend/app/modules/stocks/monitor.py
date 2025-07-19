import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, time
import logging
from typing import Optional, List

from app.config import settings
from app.modules.stocks.service import stock_service
from app.modules.stocks.models import StockAlert
from app.shared.websocket import websocket_manager
from app.shared.email import send_system_alert
from app.utils.logger import stock_logger as logger, auto_retry, log_function_call


class StockMonitor:
    """주가 모니터링 백그라운드 작업"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_check_time: Optional[datetime] = None
        self.check_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.alerts_sent_today = 0
        
    async def start(self):
        """모니터링 시작"""
        try:
            if self.is_running:
                logger.warning("주가 모니터링이 이미 실행 중입니다.")
                return
            
            # 설정 로드
            monitoring_settings = stock_service.get_settings()
            
            # 실시간 주가 업데이트 작업 (시장 시간 중에만)
            self.scheduler.add_job(
                self.update_stock_prices,
                trigger=IntervalTrigger(seconds=monitoring_settings.check_interval),
                id="stock_price_update",
                name="실시간 주가 업데이트",
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # 시장 상태 체크 작업 (1분마다)
            self.scheduler.add_job(
                self.check_market_status,
                trigger=IntervalTrigger(minutes=1),
                id="market_status_check",
                name="시장 상태 체크",
                replace_existing=True
            )
            
            # 일일 알림 리셋 작업 (자정)
            self.scheduler.add_job(
                self.reset_daily_alerts,
                trigger=CronTrigger(hour=0, minute=0),
                id="daily_alert_reset",
                name="일일 알림 리셋",
                replace_existing=True
            )
            
            # 헬스체크 작업 (5분마다)
            self.scheduler.add_job(
                self.health_check,
                trigger=IntervalTrigger(minutes=5),
                id="stock_health_check",
                name="주가 모니터링 헬스체크",
                replace_existing=True
            )
            
            # 시작 지연 작업 (30초 후 첫 체크)
            self.scheduler.add_job(
                self.update_stock_prices,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=30),
                id="stock_monitor_initial",
                name="주가 모니터링 초기 실행"
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"주가 모니터링 시작 - 업데이트 주기: {monitoring_settings.check_interval}초")
            
            # 시스템 알림 전송
            await send_system_alert(
                "주가 모니터링 시작",
                f"주가 모니터링이 시작되었습니다. (업데이트 주기: {monitoring_settings.check_interval}초)",
                "success"
            )
            
            # WebSocket으로 시스템 상태 브로드캐스트
            await websocket_manager.send_system_status({
                "service": "stock_monitor",
                "status": "started",
                "update_interval": monitoring_settings.check_interval,
                "message": "주가 모니터링이 시작되었습니다."
            })
            
        except Exception as e:
            logger.error(f"주가 모니터링 시작 실패: {e}")
            await self.handle_error(f"모니터링 시작 실패: {e}")
    
    async def stop(self):
        """모니터링 중지"""
        try:
            if not self.is_running:
                return
            
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            
            logger.info("주가 모니터링 중지")
            
            # 시스템 알림 전송
            await send_system_alert(
                "주가 모니터링 중지",
                "주가 모니터링이 중지되었습니다.",
                "warning"
            )
            
            # WebSocket으로 시스템 상태 브로드캐스트
            await websocket_manager.send_system_status({
                "service": "stock_monitor",
                "status": "stopped",
                "message": "주가 모니터링이 중지되었습니다."
            })
            
        except Exception as e:
            logger.error(f"주가 모니터링 중지 실패: {e}")
    
    async def update_stock_prices(self):
        """주가 업데이트 실행"""
        try:
            start_time = datetime.now()
            
            # 시장 시간 확인
            market_info = stock_service.get_market_info()
            if not market_info.is_trading_hours:
                logger.debug("장 시간이 아니므로 주가 업데이트 스킵")
                return
            
            logger.info("주가 업데이트 시작")
            
            # 모니터링 주식 업데이트 및 알림 체크
            alerts = await stock_service.update_monitoring_stocks()
            
            # 알림 발송
            sent_count = await stock_service.send_alerts(alerts)
            self.alerts_sent_today += sent_count
            
            # 통계 업데이트
            self.last_check_time = start_time
            self.check_count += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"주가 업데이트 완료 - "
                f"알림 발생: {len(alerts)}건, "
                f"발송: {sent_count}건, "
                f"소요시간: {duration:.2f}초"
            )
            
            # 결과가 있으면 WebSocket으로 브로드캐스트
            if alerts:
                await websocket_manager.send_system_status({
                    "service": "stock_monitor",
                    "status": "completed",
                    "alerts_triggered": len(alerts),
                    "alerts_sent": sent_count,
                    "duration": duration,
                    "checked_at": start_time.isoformat()
                })
                
                # 중요한 알림이 있으면 시스템 알림
                important_alerts = [a for a in alerts if a.alert_type in ["take_profit", "stop_loss"]]
                if important_alerts:
                    await send_system_alert(
                        "중요 주가 알림",
                        f"목표가/손절가 알림 {len(important_alerts)}건이 발생했습니다.",
                        "warning"
                    )
            
            # 에러 카운트 리셋
            self.error_count = 0
            self.last_error = None
            
        except Exception as e:
            logger.error(f"주가 업데이트 실패: {e}")
            await self.handle_error(f"주가 업데이트 실패: {e}")
    
    async def check_market_status(self):
        """시장 상태 체크"""
        try:
            market_info = stock_service.get_market_info()
            
            # 시장 시간 변경 시 알림
            current_status = market_info.status
            
            # 장 시작 알림
            if current_status.value == "open" and hasattr(self, '_last_market_status'):
                if self._last_market_status != "open":
                    await send_system_alert(
                        "장 시작",
                        "주식 시장이 열렸습니다. 실시간 모니터링을 시작합니다.",
                        "info"
                    )
                    
                    await websocket_manager.send_system_status({
                        "service": "stock_monitor",
                        "status": "market_opened",
                        "message": "주식 시장이 열렸습니다."
                    })
            
            # 장 마감 알림
            elif current_status.value == "closed" and hasattr(self, '_last_market_status'):
                if self._last_market_status == "open":
                    await send_system_alert(
                        "장 마감",
                        f"주식 시장이 마감되었습니다. 오늘 총 {self.alerts_sent_today}건의 알림이 발송되었습니다.",
                        "info"
                    )
                    
                    await websocket_manager.send_system_status({
                        "service": "stock_monitor",
                        "status": "market_closed",
                        "alerts_sent_today": self.alerts_sent_today,
                        "message": "주식 시장이 마감되었습니다."
                    })
            
            self._last_market_status = current_status.value
            
        except Exception as e:
            logger.error(f"시장 상태 체크 실패: {e}")
    
    async def reset_daily_alerts(self):
        """일일 알림 리셋"""
        try:
            # 서비스의 일일 알림 리셋
            stock_service.reset_daily_alerts()
            
            # 모니터의 일일 카운터 리셋
            self.alerts_sent_today = 0
            
            logger.info("일일 알림 리셋 완료")
            
            # 일일 통계 알림
            stats = stock_service.get_statistics()
            await send_system_alert(
                "일일 통계",
                f"어제 총 {self.alerts_sent_today}건의 알림이 발송되었습니다. "
                f"현재 {stats.get('total_stocks', 0)}개 종목을 모니터링 중입니다.",
                "info"
            )
            
        except Exception as e:
            logger.error(f"일일 알림 리셋 실패: {e}")
    
    async def health_check(self):
        """헬스체크 수행"""
        try:
            now = datetime.now()
            market_info = stock_service.get_market_info()
            
            # 시장 시간 중인데 마지막 체크가 너무 오래된 경우 경고
            if market_info.is_trading_hours and self.last_check_time:
                time_since_last_check = now - self.last_check_time
                max_delay = timedelta(seconds=stock_service.get_settings().check_interval * 3)
                
                if time_since_last_check > max_delay:
                    logger.warning(f"주가 모니터링 지연 감지: {time_since_last_check.total_seconds():.0f}초")
                    
                    await send_system_alert(
                        "주가 모니터링 지연",
                        f"주가 모니터링이 {time_since_last_check.total_seconds():.0f}초 동안 실행되지 않았습니다.",
                        "warning"
                    )
            
            # 스케줄러 상태 확인
            if not self.scheduler.running:
                logger.error("주가 모니터링 스케줄러가 중지되었습니다.")
                await self.start()  # 자동 재시작 시도
            
            # 통계 정보 로깅
            if self.check_count > 0:
                logger.debug(
                    f"주가 모니터링 상태 - "
                    f"총 체크: {self.check_count}회, "
                    f"에러: {self.error_count}회, "
                    f"오늘 알림: {self.alerts_sent_today}건, "
                    f"시장 상태: {market_info.status}, "
                    f"마지막 체크: {self.last_check_time.strftime('%H:%M:%S') if self.last_check_time else 'N/A'}"
                )
            
            # 모니터링 주식 수 확인
            monitoring_stocks = stock_service.get_monitoring_stocks()
            if len(monitoring_stocks) == 0:
                logger.warning("모니터링 중인 주식이 없습니다.")
            
        except Exception as e:
            logger.error(f"주가 헬스체크 실패: {e}")
    
    async def handle_error(self, error_message: str):
        """에러 처리"""
        try:
            self.error_count += 1
            self.last_error = error_message
            
            logger.error(f"주가 모니터링 에러 ({self.error_count}번째): {error_message}")
            
            # 에러 알림 (3번 이상 연속 에러 시)
            if self.error_count >= 3:
                await send_system_alert(
                    "주가 모니터링 오류",
                    f"주가 모니터링에서 연속 {self.error_count}번의 오류가 발생했습니다: {error_message}",
                    "error"
                )
                
                # WebSocket으로 에러 상태 브로드캐스트
                await websocket_manager.send_system_status({
                    "service": "stock_monitor",
                    "status": "error",
                    "error_count": self.error_count,
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 너무 많은 에러 시 모니터링 중지
                if self.error_count >= 10:
                    logger.critical("주가 모니터링 에러가 너무 많아 자동 중지됩니다.")
                    await self.stop()
            
        except Exception as e:
            logger.error(f"에러 처리 중 추가 에러: {e}")
    
    def get_status(self) -> dict:
        """모니터링 상태 조회"""
        market_info = stock_service.get_market_info()
        monitoring_stocks = stock_service.get_monitoring_stocks()
        
        return {
            "is_running": self.is_running,
            "market_status": market_info.status,
            "is_trading_hours": market_info.is_trading_hours,
            "check_count": self.check_count,
            "error_count": self.error_count,
            "alerts_sent_today": self.alerts_sent_today,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_error": self.last_error,
            "monitoring_stocks_count": len(monitoring_stocks),
            "active_alerts_count": len([s for s in monitoring_stocks if s.alert_enabled]),
            "next_check_time": self.get_next_check_time(),
            "scheduler_running": self.scheduler.running if hasattr(self, 'scheduler') else False
        }
    
    def get_next_check_time(self) -> Optional[str]:
        """다음 체크 시간 계산"""
        if not self.last_check_time:
            return None
        
        settings = stock_service.get_settings()
        next_time = self.last_check_time + timedelta(seconds=settings.check_interval)
        return next_time.isoformat()
    
    async def force_update(self):
        """강제 업데이트 실행"""
        try:
            logger.info("주가 강제 업데이트 실행")
            await self.update_stock_prices()
            return True
        except Exception as e:
            logger.error(f"주가 강제 업데이트 실패: {e}")
            return False
    
    async def update_monitoring_interval(self, interval_seconds: int):
        """모니터링 주기 업데이트"""
        try:
            if self.is_running:
                # 기존 작업 제거
                self.scheduler.remove_job("stock_price_update")
                
                # 새로운 주기로 작업 추가
                self.scheduler.add_job(
                    self.update_stock_prices,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id="stock_price_update",
                    name="실시간 주가 업데이트",
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True
                )
                
                logger.info(f"주가 모니터링 주기 업데이트: {interval_seconds}초")
                
                await websocket_manager.send_system_status({
                    "service": "stock_monitor",
                    "status": "interval_updated",
                    "new_interval": interval_seconds,
                    "message": f"모니터링 주기가 {interval_seconds}초로 변경되었습니다."
                })
                
        except Exception as e:
            logger.error(f"모니터링 주기 업데이트 실패: {e}")


# 전역 주가 모니터 인스턴스
stock_monitor = StockMonitor()


async def start_stock_monitoring():
    """주가 모니터링 시작 함수"""
    await stock_monitor.start()


async def stop_stock_monitoring():
    """주가 모니터링 중지 함수"""
    await stock_monitor.stop()


def get_stock_monitor_status():
    """주가 모니터링 상태 조회 함수"""
    return stock_monitor.get_status()


async def force_stock_update():
    """강제 주가 업데이트 함수"""
    return await stock_monitor.force_update()