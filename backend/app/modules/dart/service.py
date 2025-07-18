import requests
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from filelock import FileLock
import json
import os

from app.config import settings, COMPANIES, KEYWORDS
from app.modules.dart.models import (
    DartDisclosure, DartDisclosureResponse, DartProcessedIds,
    DartKeyword, DartCompany, DartMonitoringSettings, DartAlert
)
from app.shared.email import send_dart_alert
from app.shared.websocket import websocket_manager
from app.shared.database import database

logger = logging.getLogger(__name__)


class DartService:
    """DART 공시 모니터링 서비스"""
    
    def __init__(self):
        self.api_key = settings.DART_API_KEY
        self.base_url = settings.DART_BASE_URL
        self.processed_ids_file = os.path.join(settings.DATA_DIR, "processed_ids.txt")
        self.processed_ids_lock = FileLock(f"{self.processed_ids_file}.lock")
        self.keywords = self._load_keywords()
        self.companies = self._load_companies()
        self.processed_ids = self._load_processed_ids()
    
    def _load_keywords(self) -> List[DartKeyword]:
        """키워드 목록 로드"""
        return [
            DartKeyword(
                keyword=keyword,
                weight=1.0,
                category="general",
                is_active=True
            )
            for keyword in KEYWORDS
        ]
    
    def _load_companies(self) -> List[DartCompany]:
        """관심기업 목록 로드"""
        return [
            DartCompany(
                stock_code=code,
                corp_code="",  # 실제 구현에서는 DART API로 조회
                corp_name=name,
                is_active=True
            )
            for code, name in COMPANIES.items()
        ]
    
    def _load_processed_ids(self) -> DartProcessedIds:
        """처리된 공시 ID 로드"""
        try:
            with self.processed_ids_lock:
                if os.path.exists(self.processed_ids_file):
                    with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        ids = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
                        return DartProcessedIds(
                            processed_ids=ids,
                            total_processed=len(ids)
                        )
                else:
                    return DartProcessedIds()
        except Exception as e:
            logger.error(f"처리된 ID 로드 실패: {e}")
            return DartProcessedIds()
    
    def _save_processed_ids(self):
        """처리된 공시 ID 저장"""
        try:
            with self.processed_ids_lock:
                with open(self.processed_ids_file, 'w', encoding='utf-8') as f:
                    f.write("# DART 공시 처리된 ID 목록\n")
                    f.write(f"# 마지막 업데이트: {datetime.now().isoformat()}\n")
                    f.write(f"# 총 처리 건수: {len(self.processed_ids.processed_ids)}\n")
                    for rcept_no in self.processed_ids.processed_ids:
                        f.write(f"{rcept_no}\n")
        except Exception as e:
            logger.error(f"처리된 ID 저장 실패: {e}")
    
    async def fetch_disclosures(
        self, 
        start_date: str, 
        end_date: str, 
        page_no: int = 1, 
        page_count: int = 100
    ) -> Optional[DartDisclosureResponse]:
        """DART API에서 공시 목록 조회"""
        try:
            url = f"{self.base_url}/list.json"
            params = {
                'crtfc_key': self.api_key,
                'bgn_de': start_date,
                'end_de': end_date,
                'corp_cls': 'Y',  # 유가증권시장
                'sort': 'date',
                'sort_mth': 'desc',
                'page_no': page_no,
                'page_count': page_count
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != '000':
                logger.error(f"DART API 오류: {data.get('message', 'Unknown error')}")
                return None
            
            # 공시 목록 파싱
            disclosures = []
            for item in data.get('list', []):
                try:
                    disclosure = DartDisclosure(**item)
                    # 주식코드 매핑
                    for code, name in COMPANIES.items():
                        if disclosure.corp_name == name:
                            disclosure.stock_code = code
                            break
                    
                    # DART URL 생성
                    disclosure.dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={disclosure.rcept_no}"
                    
                    disclosures.append(disclosure)
                except Exception as e:
                    logger.error(f"공시 데이터 파싱 실패: {e}")
                    continue
            
            return DartDisclosureResponse(
                status=data.get('status', ''),
                message=data.get('message', ''),
                page_no=data.get('page_no', 1),
                page_count=data.get('page_count', 100),
                total_count=data.get('total_count', 0),
                total_page=data.get('total_page', 1),
                list=disclosures
            )
            
        except requests.RequestException as e:
            logger.error(f"DART API 요청 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"공시 조회 실패: {e}")
            return None
    
    def check_keywords(self, disclosure: DartDisclosure) -> Tuple[List[str], int]:
        """공시에서 키워드 검색 및 우선순위 계산"""
        matched_keywords = []
        priority_score = 0
        
        # 검색 대상 텍스트
        search_text = f"{disclosure.report_nm} {disclosure.rm or ''}"
        
        for keyword_obj in self.keywords:
            if not keyword_obj.is_active:
                continue
                
            keyword = keyword_obj.keyword
            if keyword in search_text:
                matched_keywords.append(keyword)
                priority_score += int(keyword_obj.weight)
        
        return matched_keywords, priority_score
    
    def is_target_company(self, disclosure: DartDisclosure) -> bool:
        """관심기업인지 확인"""
        return disclosure.corp_name in [comp.corp_name for comp in self.companies if comp.is_active]
    
    async def process_new_disclosures(self) -> List[DartAlert]:
        """새로운 공시 처리"""
        try:
            # 오늘 공시 조회
            today = datetime.now().strftime('%Y%m%d')
            
            response = await self.fetch_disclosures(today, today)
            if not response:
                return []
            
            new_alerts = []
            
            for disclosure in response.list:
                # 이미 처리된 공시인지 확인
                if self.processed_ids.is_processed(disclosure.rcept_no):
                    continue
                
                # 관심기업인지 확인
                if not self.is_target_company(disclosure):
                    continue
                
                # 키워드 검색
                matched_keywords, priority_score = self.check_keywords(disclosure)
                
                # 키워드가 매칭되면 알림 생성
                if matched_keywords:
                    disclosure.matched_keywords = matched_keywords
                    disclosure.priority_score = priority_score
                    
                    # 알림 생성
                    alert = DartAlert(
                        rcept_no=disclosure.rcept_no,
                        corp_name=disclosure.corp_name,
                        report_nm=disclosure.report_nm,
                        matched_keywords=matched_keywords,
                        priority_score=priority_score,
                        dart_url=disclosure.dart_url,
                        created_at=datetime.now()
                    )
                    
                    new_alerts.append(alert)
                    
                    # 처리된 ID로 마킹
                    self.processed_ids.add_id(disclosure.rcept_no)
                    
                    logger.info(f"새로운 공시 발견: {disclosure.corp_name} - {disclosure.report_nm}")
                
                else:
                    # 키워드가 없어도 처리된 것으로 마킹 (중복 방지)
                    self.processed_ids.add_id(disclosure.rcept_no)
            
            # 처리된 ID 저장
            self._save_processed_ids()
            
            # 우선순위별 정렬
            new_alerts.sort(key=lambda x: x.priority_score, reverse=True)
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"새로운 공시 처리 실패: {e}")
            return []
    
    async def send_alerts(self, alerts: List[DartAlert]) -> int:
        """알림 발송"""
        sent_count = 0
        
        for alert in alerts:
            try:
                # 이메일 발송
                email_sent = await send_dart_alert(
                    alert.corp_name,
                    alert.report_nm,
                    alert.dart_url
                )
                
                # WebSocket 브로드캐스트
                await websocket_manager.send_dart_update({
                    "rcept_no": alert.rcept_no,
                    "corp_name": alert.corp_name,
                    "report_nm": alert.report_nm,
                    "matched_keywords": alert.matched_keywords,
                    "priority_score": alert.priority_score,
                    "dart_url": alert.dart_url,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                })
                
                # 데이터베이스에 알림 기록 저장
                await self.save_alert_to_db(alert)
                
                if email_sent:
                    alert.is_sent = True
                    alert.sent_at = datetime.now()
                    sent_count += 1
                    
                    logger.info(f"DART 알림 발송 성공: {alert.corp_name} - {alert.report_nm}")
                
            except Exception as e:
                logger.error(f"알림 발송 실패: {e}")
                continue
        
        return sent_count
    
    async def save_alert_to_db(self, alert: DartAlert):
        """알림을 데이터베이스에 저장"""
        try:
            query = """
                INSERT INTO alert_history 
                (alert_type, title, message, stock_code, stock_name, is_read, created_at)
                VALUES (:alert_type, :title, :message, :stock_code, :stock_name, :is_read, :created_at)
            """
            
            await database.execute(query, {
                "alert_type": "dart",
                "title": f"[DART] {alert.corp_name}",
                "message": f"{alert.report_nm} (키워드: {', '.join(alert.matched_keywords)})",
                "stock_code": None,  # DART는 주식코드 없음
                "stock_name": alert.corp_name,
                "is_read": False,
                "created_at": alert.created_at or datetime.now()
            })
            
        except Exception as e:
            logger.error(f"알림 DB 저장 실패: {e}")
    
    async def get_recent_disclosures(self, limit: int = 50) -> List[DartDisclosure]:
        """최근 공시 조회"""
        try:
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            
            response = await self.fetch_disclosures(
                week_ago.strftime('%Y%m%d'),
                today.strftime('%Y%m%d')
            )
            
            if not response:
                return []
            
            # 관심기업 필터링
            target_disclosures = [
                disc for disc in response.list 
                if self.is_target_company(disc)
            ]
            
            # 키워드 매칭 정보 추가
            for disclosure in target_disclosures:
                matched_keywords, priority_score = self.check_keywords(disclosure)
                disclosure.matched_keywords = matched_keywords
                disclosure.priority_score = priority_score
            
            return target_disclosures[:limit]
            
        except Exception as e:
            logger.error(f"최근 공시 조회 실패: {e}")
            return []
    
    async def get_monitoring_settings(self) -> DartMonitoringSettings:
        """모니터링 설정 조회"""
        return DartMonitoringSettings(
            check_interval=settings.DART_CHECK_INTERVAL,
            keywords=self.keywords,
            companies=self.companies,
            email_enabled=True,
            websocket_enabled=True,
            report_types=[]  # 필요시 구현
        )
    
    async def update_keywords(self, keywords: List[DartKeyword]) -> bool:
        """키워드 업데이트"""
        try:
            self.keywords = keywords
            logger.info(f"키워드 업데이트 완료: {len(keywords)}개")
            return True
        except Exception as e:
            logger.error(f"키워드 업데이트 실패: {e}")
            return False
    
    async def update_companies(self, companies: List[DartCompany]) -> bool:
        """관심기업 업데이트"""
        try:
            self.companies = companies
            logger.info(f"관심기업 업데이트 완료: {len(companies)}개")
            return True
        except Exception as e:
            logger.error(f"관심기업 업데이트 실패: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        return {
            "total_processed": len(self.processed_ids.processed_ids),
            "keywords_count": len(self.keywords),
            "companies_count": len(self.companies),
            "last_updated": self.processed_ids.last_updated.isoformat() if self.processed_ids.last_updated else None
        }


# 전역 DART 서비스 인스턴스
dart_service = DartService()