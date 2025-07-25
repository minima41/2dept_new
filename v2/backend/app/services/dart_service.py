"""
V2 Investment Monitor - DART 모니터링 서비스
기존 dart_monitor.py의 핵심 로직을 클래스로 재구성
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import logging
import re
from pathlib import Path

from ..core.config import settings, DART_KEYWORDS, MONITORING_COMPANIES
from ..core.database import database
from ..models.dart_models import DartDisclosureResponse
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class DartService:
    """DART 공시 모니터링 서비스"""
    
    def __init__(self):
        self.api_key = settings.dart_api_key
        self.base_url = settings.dart_base_url
        self.keywords = DART_KEYWORDS
        self.companies = MONITORING_COMPANIES
        self.processed_ids: Set[str] = set()
        self.notification_service = NotificationService()
        
        # processing된 ID 파일 경로
        self.processed_ids_file = settings.data_dir / "processed_ids.txt"
        self._load_processed_ids()
    
    def _load_processed_ids(self) -> None:
        """저장된 processing ID 목록 로드"""
        try:
            if self.processed_ids_file.exists():
                with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                    self.processed_ids = set(f.read().splitlines())
                logger.info(f"📁 processing된 ID {len(self.processed_ids)} items 로드")
        except Exception as e:
            logger.warning(f"[WARNING] processing ID 파일 로드 failed: {e}")
    
    def _save_processed_id(self, disclosure_id: str) -> None:
        """처리 completed된 ID 저장"""
        self.processed_ids.add(disclosure_id)
        
        # 최대 저장  items수 제한
        if len(self.processed_ids) > settings.max_processed_ids:
            sorted_ids = sorted(self.processed_ids, reverse=True)
            self.processed_ids = set(sorted_ids[:settings.max_processed_ids])
        
        try:
            with open(self.processed_ids_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.processed_ids))
        except Exception as e:
            logger.error(f"[ERROR] processing ID 저장 failed: {e}")
    
    async def fetch_recent_disclosures(self, days: int = 1) -> List[Dict]:
        """최근 공시 info querying (실제 dart_monitor.py 로직 적용)"""
        # 오늘 날짜로 querying (기존 로직과 동일)
        today = datetime.now().strftime("%Y%m%d")
        start_date = today
        
        url = "https://opendart.fss.or.kr/api/list.json"
        
        # 관심 기업 코드 목록 (기존 dart_monitor.py 로직)
        corp_codes = list(self.companies.values())
        logger.info(f"📊 관심 기업 {len(corp_codes)} items 공시 querying starting")
        
        total_disclosures = []
        
        # 기업별로  items별 querying (기존 로직과 동일)
        for idx, corp_code in enumerate(corp_codes):
            company_name = next((name for name, code in self.companies.items() if code == corp_code), corp_code)
            
            params = {
                "crtfc_key": self.api_key,
                "corp_code": corp_code,
                "bgn_de": start_date,
                "end_de": today,
                "page_no": "1",
                "page_count": "100"
            }
            
            try:
                logger.info(f"[{idx+1}/{len(corp_codes)}] '{company_name}' 공시 querying in progress...")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # API 사용한도  seconds과 processing (기존 로직)
                    if data.get('status') == '020':
                        logger.warning("[WARNING] API 사용한도  seconds과")
                        break
                    
                    if data.get('status') == '000':
                        disclosures = data.get('list', [])
                        if disclosures:
                            logger.info(f"  [DART] '{company_name}' 공시 {len(disclosures)} items 발견")
                            total_disclosures.extend(disclosures)
                    elif data.get('status') == '013':
                        # 공시정보 없음 - 정상
                        pass
                    else:
                        logger.error(f"[ERROR] DART API error: {data.get('message', '알 수 없는 error')}")
                        
                # API 부하 방지 지연 (기존 로직)
                if idx < len(corp_codes) - 1 and len(corp_codes) > 20:
                    await asyncio.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"[ERROR] '{company_name}' 공시 querying failed: {e}")
        
        logger.info(f"[SUCCESS] 총 {len(total_disclosures)} records 공시 querying completed")
        return total_disclosures
    
    def analyze_disclosure(self, disclosure: Dict) -> Dict:
        """공시 내용  minutes석 및 중요도 점수 계산 (실제 dart_monitor.py 로직 적용)"""
        report_name = disclosure.get("report_nm", "")
        corp_code = disclosure.get("corp_code", "")
        corp_name = disclosure.get("corp_name", "")
        
        # 제외할 키워드 목록 (기존 dart_monitor.py 로직)
        EXCLUDE_KEYWORDS = ["기업설명회", "IR items최", "설명회 items최", "IR)", "(IR)"]
        
        # 제외 키워드 checking
        is_excluded = any(exclude_kw in report_name for exclude_kw in EXCLUDE_KEYWORDS)
        if is_excluded:
            return {
                **disclosure,
                "matched_keywords": [],
                "priority_score": 0,
                "is_important": False,
                "exclusion_reason": "제외 키워드 포함"
            }
        
        # 관심 키워드 매칭 검사 (기존 로직과 동일)
        matched_keywords = []
        for keyword in self.keywords:
            if keyword in report_name:
                matched_keywords.append(keyword)
        
        # 관심 키워드가 없으면 무시 (기존 로직과 동일)
        if not matched_keywords:
            return {
                **disclosure,
                "matched_keywords": [],
                "priority_score": 0,
                "is_important": False,
                "exclusion_reason": "관심 키워드 없음"
            }
        
        # 중요도 점수 계산
        priority_score = 0
        
        # 기본 점수: 키워드 매칭  items수
        priority_score += len(matched_keywords)
        
        # 고중요도 키워드 추가 점수
        high_priority_keywords = ["합병", " minutes할", "매각", "취득", "유상증자", "무상증자", "신주", "배당"]
        for keyword in matched_keywords:
            if keyword in high_priority_keywords:
                priority_score += 3
        
        # 관심 기업 추가 점수
        if corp_code in self.companies.values():
            priority_score += 5
        
        return {
            **disclosure,
            "matched_keywords": matched_keywords,
            "priority_score": priority_score,
            "is_important": len(matched_keywords) > 0,  # 키워드가 있으면 중요
            "company_name": self.companies.get(corp_code, corp_name)
        }
    
    async def process_new_disclosures(self) -> List[Dict]:
        """새로운 공시 processing 및 알림 creating"""
        disclosures = await self.fetch_recent_disclosures()
        new_disclosures = []
        
        for disclosure in disclosures:
            rcept_no = disclosure.get("rcept_no")
            
            # 이미 processing된 공시는  records너뛰기
            if rcept_no in self.processed_ids:
                continue
            
            # 공시  minutes석
            analyzed = self.analyze_disclosure(disclosure)
            
            # 중요한 공시만 processing
            if analyzed["is_important"]:
                try:
                    # 데이터베이스에 저장
                    await self._save_disclosure_to_db(analyzed)
                    
                    # 알림 creating
                    await self.notification_service.create_dart_notification(analyzed)
                    
                    new_disclosures.append(analyzed)
                    logger.info(f"[NOTIFICATION] 새 공시 processing: {analyzed['corp_name']} - {analyzed['report_nm']}")
                    
                except Exception as e:
                    logger.error(f"[ERROR] 공시 processing failed ({rcept_no}): {e}")
            
            # processing completed 표시
            self._save_processed_id(rcept_no)
        
        logger.info(f"[SUCCESS] 새로운 중요 공시 {len(new_disclosures)} records processing completed")
        return new_disclosures
    
    async def _save_disclosure_to_db(self, disclosure: Dict) -> None:
        """공시 info를 데이터베이스에 저장"""
        query = """
            INSERT OR REPLACE INTO dart_disclosures 
            (rcept_no, corp_code, corp_name, report_nm, flr_nm, rcept_dt, rm, 
             matched_keywords, priority_score, is_processed)
            VALUES (:rcept_no, :corp_code, :corp_name, :report_nm, :flr_nm, :rcept_dt, :rm,
                    :matched_keywords, :priority_score, :is_processed)
        """
        
        await database.execute(query, {
            "rcept_no": disclosure["rcept_no"],
            "corp_code": disclosure["corp_code"], 
            "corp_name": disclosure["corp_name"],
            "report_nm": disclosure["report_nm"],
            "flr_nm": disclosure.get("flr_nm"),
            "rcept_dt": disclosure["rcept_dt"],
            "rm": disclosure.get("rm"),
            "matched_keywords": disclosure["matched_keywords"],
            "priority_score": disclosure["priority_score"],
            "is_processed": True
        })
    
    async def get_recent_disclosures_from_db(
        self, 
        limit: int = 20,
        days: int = 7
    ) -> List[Dict]:
        """데이터베이스에서 최근 공시 querying"""
        since_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT * FROM dart_disclosures 
            WHERE created_at >= :since_date
            ORDER BY priority_score DESC, created_at DESC
            LIMIT :limit
        """
        
        rows = await database.fetch_all(query, {
            "since_date": since_date,
            "limit": limit
        })
        
        return [dict(row) for row in rows]
    
    async def get_statistics(self) -> Dict:
        """DART 모니터링 통계 querying"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        queries = {
            "total_processed": "SELECT COUNT(*) FROM dart_disclosures",
            "today_count": "SELECT COUNT(*) FROM dart_disclosures WHERE DATE(created_at) = :today",
            "week_count": "SELECT COUNT(*) FROM dart_disclosures WHERE DATE(created_at) >= :week_ago",
            "high_priority_count": "SELECT COUNT(*) FROM dart_disclosures WHERE priority_score >= 5"
        }
        
        stats = {}
        for key, query in queries.items():
            try:
                if "today" in key:
                    result = await database.fetch_val(query, {"today": today})
                elif "week" in key:
                    result = await database.fetch_val(query, {"week_ago": week_ago})
                else:
                    result = await database.fetch_val(query)
                stats[key] = result or 0
            except:
                stats[key] = 0
        
        stats.update({
            "keywords_count": len(self.keywords),
            "companies_count": len(self.companies),
            "processed_ids_count": len(self.processed_ids)
        })
        
        return stats
    
    def update_keywords(self, keywords: List[str]) -> bool:
        """모니터링 키워드 updating"""
        try:
            self.keywords = keywords
            logger.info(f"🔧 DART 키워드 {len(keywords)} items로 updating")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 키워드 updating failed: {e}")
            return False
    
    def update_companies(self, companies: Dict[str, str]) -> bool:
        """모니터링 기업 updating"""
        try:
            self.companies = companies
            logger.info(f"🏢 관심 기업 {len(companies)} items로 updating")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 기업 목록 updating failed: {e}")
            return False


# === 전역 서비스 인스턴스 ===
dart_service = DartService()