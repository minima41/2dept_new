import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
from typing import Optional

from app.config import settings
from app.modules.dart.service import dart_service
from app.shared.websocket import websocket_manager
from app.shared.email import send_system_alert
from app.utils.logger import dart_logger as logger, auto_retry, log_function_call


class DartMonitor:
    """DART 공시 모니터링 백그라운드 작업"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_check_time: Optional[datetime] = None
        self.check_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
    
    async def start(self):
        """모니터링 시작"""
        try:
            if self.is_running:
                logger.warning("DART 모니터링이 이미 실행 중입니다.")
                return
            
            # 스케줄러 설정
            self.scheduler.add_job(
                self.check_disclosures,
                trigger=IntervalTrigger(seconds=settings.DART_CHECK_INTERVAL),
                id="dart_monitor",
                name="DART 공시 모니터링",
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # 시작 지연 작업 (1분 후 첫 체크)
            self.scheduler.add_job(
                self.check_disclosures,
                trigger='date',
                run_date=datetime.now() + timedelta(minutes=1),
                id="dart_monitor_initial",
                name="DART 공시 모니터링 초기 실행"
            )
            
            # 헬스체크 작업 (5분마다)
            self.scheduler.add_job(
                self.health_check,
                trigger=IntervalTrigger(minutes=5),
                id="dart_health_check",
                name="DART 모니터링 헬스체크",
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"DART 모니터링 시작 - 체크 주기: {settings.DART_CHECK_INTERVAL}초")
            
            # 시스템 알림 전송
            await send_system_alert(
                "DART 모니터링 시작",
                f"DART 공시 모니터링이 시작되었습니다. (체크 주기: {settings.DART_CHECK_INTERVAL}초)",
                "success"
            )
            
            # WebSocket으로 시스템 상태 브로드캐스트
            await websocket_manager.send_system_status({
                "service": "dart_monitor",
                "status": "started",
                "check_interval": settings.DART_CHECK_INTERVAL,
                "message": "DART 모니터링이 시작되었습니다."
            })
            
        except Exception as e:
            logger.error(f"DART 모니터링 시작 실패: {e}")
            await self.handle_error(f"모니터링 시작 실패: {e}")
    
    async def stop(self):
        """모니터링 중지"""
        try:
            if not self.is_running:
                return
            
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            
            logger.info("DART 모니터링 중지")
            
            # 시스템 알림 전송
            await send_system_alert(
                "DART 모니터링 중지",
                "DART 공시 모니터링이 중지되었습니다.",
                "warning"
            )
            
            # WebSocket으로 시스템 상태 브로드캐스트
            await websocket_manager.send_system_status({
                "service": "dart_monitor",
                "status": "stopped",
                "message": "DART 모니터링이 중지되었습니다."
            })
            
        except Exception as e:
            logger.error(f"DART 모니터링 중지 실패: {e}")
    
    async def check_disclosures(self):
        """공시 체크 실행"""
        try:
            start_time = datetime.now()
            logger.info("DART 공시 체크 시작")
            
            # 새로운 공시 처리
            new_alerts = await dart_service.process_new_disclosures()
            
            # 알림 발송
            sent_count = await dart_service.send_alerts(new_alerts)
            
            # 통계 업데이트
            self.last_check_time = start_time
            self.check_count += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"DART 공시 체크 완료 - "
                f"새 공시: {len(new_alerts)}건, "
                f"발송: {sent_count}건, "
                f"소요시간: {duration:.2f}초"
            )
            
            # 결과가 있으면 WebSocket으로 브로드캐스트
            if new_alerts:
                await websocket_manager.send_system_status({
                    "service": "dart_monitor",
                    "status": "completed",
                    "new_disclosures": len(new_alerts),
                    "sent_alerts": sent_count,
                    "duration": duration,
                    "checked_at": start_time.isoformat()
                })
                
                # 중요한 공시가 있으면 시스템 알림
                high_priority_alerts = [a for a in new_alerts if a.priority_score >= 3]
                if high_priority_alerts:
                    await send_system_alert(
                        "중요 공시 발견",
                        f"우선순위가 높은 공시 {len(high_priority_alerts)}건이 발견되었습니다.",
                        "warning"
                    )
            
            # 에러 카운트 리셋
            self.error_count = 0
            self.last_error = None
            
        except Exception as e:
            logger.error(f"DART 공시 체크 실패: {e}")
            await self.handle_error(f"공시 체크 실패: {e}")
    
    async def handle_error(self, error_message: str):
        """에러 처리"""
        try:
            self.error_count += 1
            self.last_error = error_message
            
            logger.error(f"DART 모니터링 에러 ({self.error_count}번째): {error_message}")
            
            # 에러 알림 (5번 이상 연속 에러 시)
            if self.error_count >= 5:
                await send_system_alert(
                    "DART 모니터링 오류",
                    f"DART 모니터링에서 연속 {self.error_count}번의 오류가 발생했습니다: {error_message}",
                    "error"
                )
                
                # WebSocket으로 에러 상태 브로드캐스트
                await websocket_manager.send_system_status({
                    "service": "dart_monitor",
                    "status": "error",
                    "error_count": self.error_count,
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 너무 많은 에러 시 모니터링 중지
                if self.error_count >= 10:
                    logger.critical("DART 모니터링 에러가 너무 많아 자동 중지됩니다.")
                    await self.stop()
            
        except Exception as e:
            logger.error(f"에러 처리 중 추가 에러: {e}")
    
    async def health_check(self):
        """헬스체크 수행"""
        try:
            now = datetime.now()
            
            # 마지막 체크 시간이 너무 오래된 경우 경고
            if self.last_check_time:
                time_since_last_check = now - self.last_check_time
                if time_since_last_check > timedelta(seconds=settings.DART_CHECK_INTERVAL * 2):
                    logger.warning(f"DART 모니터링 지연 감지: {time_since_last_check.total_seconds():.0f}초")
                    
                    await send_system_alert(
                        "DART 모니터링 지연",
                        f"DART 모니터링이 {time_since_last_check.total_seconds():.0f}초 동안 실행되지 않았습니다.",
                        "warning"
                    )
            
            # 스케줄러 상태 확인
            if not self.scheduler.running:
                logger.error("DART 모니터링 스케줄러가 중지되었습니다.")
                await self.start()  # 자동 재시작 시도
            
            # 통계 정보 로깅
            if self.check_count > 0:
                logger.debug(
                    f"DART 모니터링 상태 - "
                    f"총 체크: {self.check_count}회, "
                    f"에러: {self.error_count}회, "
                    f"마지막 체크: {self.last_check_time.strftime('%H:%M:%S') if self.last_check_time else 'N/A'}"
                )
            
        except Exception as e:
            logger.error(f"DART 헬스체크 실패: {e}")
    
    def get_status(self) -> dict:
        """모니터링 상태 조회"""
        return {
            "is_running": self.is_running,
            "check_count": self.check_count,
            "error_count": self.error_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_error": self.last_error,
            "next_check_time": self.get_next_check_time(),
            "scheduler_running": self.scheduler.running if hasattr(self, 'scheduler') else False
        }
    
    def get_next_check_time(self) -> Optional[str]:
        """다음 체크 시간 계산"""
        if not self.last_check_time:
            return None
        
        next_time = self.last_check_time + timedelta(seconds=settings.DART_CHECK_INTERVAL)
        return next_time.isoformat()
    
    async def force_check(self):
        """강제 체크 실행"""
        try:
            logger.info("DART 강제 체크 실행")
            await self.check_disclosures()
            return True
        except Exception as e:
            logger.error(f"DART 강제 체크 실패: {e}")
            return False


# 전역 DART 모니터 인스턴스
dart_monitor = DartMonitor()


async def start_dart_monitoring():
    """DART 모니터링 시작 함수"""
    await dart_monitor.start()


async def stop_dart_monitoring():
    """DART 모니터링 중지 함수"""
    await dart_monitor.stop()


def get_dart_monitor_status():
    """DART 모니터링 상태 조회 함수"""
    return dart_monitor.get_status()