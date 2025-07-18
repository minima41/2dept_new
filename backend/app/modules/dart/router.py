from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.modules.dart.models import (
    DartDisclosure, DartDisclosureListResponse, DartKeyword, DartKeywordResponse,
    DartCompany, DartCompanyResponse, DartSettingsResponse, DartAlertResponse,
    DartStatisticsResponse, DartMonitoringSettings
)
from app.modules.dart.service import dart_service
from app.shared.auth import get_current_user_optional
from app.shared.database import database

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/disclosures", response_model=DartDisclosureListResponse)
async def get_disclosures(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    days: int = Query(7, ge=1, le=30, description="조회 일수"),
    keyword: Optional[str] = Query(None, description="키워드 필터"),
    company: Optional[str] = Query(None, description="회사명 필터"),
    current_user = Depends(get_current_user_optional)
):
    """공시 목록 조회"""
    try:
        # 최근 공시 조회
        disclosures = await dart_service.get_recent_disclosures(limit=page_size * 5)
        
        # 필터링
        filtered_disclosures = []
        for disclosure in disclosures:
            # 키워드 필터
            if keyword:
                search_text = f"{disclosure.report_nm} {disclosure.rm or ''}"
                if keyword.lower() not in search_text.lower():
                    continue
            
            # 회사명 필터
            if company:
                if company.lower() not in disclosure.corp_name.lower():
                    continue
            
            filtered_disclosures.append(disclosure)
        
        # 페이지네이션
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_disclosures = filtered_disclosures[start_idx:end_idx]
        
        return DartDisclosureListResponse(
            disclosures=page_disclosures,
            total_count=len(filtered_disclosures),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(filtered_disclosures)
        )
        
    except Exception as e:
        logger.error(f"공시 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="공시 목록 조회에 실패했습니다.")


@router.get("/disclosures/{rcept_no}", response_model=DartDisclosure)
async def get_disclosure_detail(
    rcept_no: str,
    current_user = Depends(get_current_user_optional)
):
    """공시 상세 조회"""
    try:
        # 최근 공시에서 검색
        disclosures = await dart_service.get_recent_disclosures(limit=1000)
        
        for disclosure in disclosures:
            if disclosure.rcept_no == rcept_no:
                return disclosure
        
        raise HTTPException(status_code=404, detail="공시를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"공시 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="공시 상세 조회에 실패했습니다.")


@router.get("/keywords", response_model=DartKeywordResponse)
async def get_keywords(
    current_user = Depends(get_current_user_optional)
):
    """키워드 목록 조회"""
    try:
        keywords = dart_service.keywords
        return DartKeywordResponse(
            keywords=keywords,
            total_count=len(keywords)
        )
        
    except Exception as e:
        logger.error(f"키워드 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="키워드 목록 조회에 실패했습니다.")


@router.put("/keywords", response_model=DartKeywordResponse)
async def update_keywords(
    keywords: List[DartKeyword],
    current_user = Depends(get_current_user_optional)
):
    """키워드 목록 업데이트"""
    try:
        success = await dart_service.update_keywords(keywords)
        if not success:
            raise HTTPException(status_code=500, detail="키워드 업데이트에 실패했습니다.")
        
        return DartKeywordResponse(
            keywords=keywords,
            total_count=len(keywords)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="키워드 업데이트에 실패했습니다.")


@router.get("/companies", response_model=DartCompanyResponse)
async def get_companies(
    current_user = Depends(get_current_user_optional)
):
    """관심기업 목록 조회"""
    try:
        companies = dart_service.companies
        return DartCompanyResponse(
            companies=companies,
            total_count=len(companies)
        )
        
    except Exception as e:
        logger.error(f"관심기업 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="관심기업 목록 조회에 실패했습니다.")


@router.put("/companies", response_model=DartCompanyResponse)
async def update_companies(
    companies: List[DartCompany],
    current_user = Depends(get_current_user_optional)
):
    """관심기업 목록 업데이트"""
    try:
        success = await dart_service.update_companies(companies)
        if not success:
            raise HTTPException(status_code=500, detail="관심기업 업데이트에 실패했습니다.")
        
        return DartCompanyResponse(
            companies=companies,
            total_count=len(companies)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관심기업 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="관심기업 업데이트에 실패했습니다.")


@router.get("/settings", response_model=DartSettingsResponse)
async def get_settings(
    current_user = Depends(get_current_user_optional)
):
    """모니터링 설정 조회"""
    try:
        settings = await dart_service.get_monitoring_settings()
        return DartSettingsResponse(settings=settings)
        
    except Exception as e:
        logger.error(f"설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 조회에 실패했습니다.")


@router.get("/alerts", response_model=DartAlertResponse)
async def get_alerts(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    days: int = Query(7, ge=1, le=30, description="조회 일수"),
    current_user = Depends(get_current_user_optional)
):
    """알림 목록 조회"""
    try:
        # 데이터베이스에서 DART 알림 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 전체 카운트 조회
        count_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'dart' 
            AND created_at >= :start_date 
            AND created_at <= :end_date
        """
        total_count = await database.fetch_val(count_query, {
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 읽지 않은 알림 카운트
        unread_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'dart' 
            AND is_read = false
            AND created_at >= :start_date 
            AND created_at <= :end_date
        """
        unread_count = await database.fetch_val(unread_query, {
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 알림 목록 조회
        offset = (page - 1) * page_size
        alerts_query = """
            SELECT * FROM alert_history 
            WHERE alert_type = 'dart' 
            AND created_at >= :start_date 
            AND created_at <= :end_date
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """
        
        alerts_data = await database.fetch_all(alerts_query, {
            "start_date": start_date,
            "end_date": end_date,
            "limit": page_size,
            "offset": offset
        })
        
        # DartAlert 객체로 변환
        alerts = []
        for alert_data in alerts_data:
            alert = {
                "id": alert_data["id"],
                "rcept_no": "",  # DB에서 별도 저장 필요
                "corp_name": alert_data["stock_name"] or "",
                "report_nm": alert_data["title"].replace("[DART] ", ""),
                "matched_keywords": [],  # 파싱 필요
                "priority_score": 0,
                "dart_url": "",
                "is_sent": True,
                "created_at": alert_data["created_at"],
                "sent_at": alert_data["created_at"]
            }
            alerts.append(alert)
        
        return DartAlertResponse(
            alerts=alerts,
            total_count=total_count or 0,
            unread_count=unread_count or 0
        )
        
    except Exception as e:
        logger.error(f"알림 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 목록 조회에 실패했습니다.")


@router.put("/alerts/{alert_id}/read")
async def mark_alert_as_read(
    alert_id: int,
    current_user = Depends(get_current_user_optional)
):
    """알림을 읽음으로 표시"""
    try:
        query = """
            UPDATE alert_history 
            SET is_read = true 
            WHERE id = :alert_id AND alert_type = 'dart'
        """
        await database.execute(query, {"alert_id": alert_id})
        
        return {"message": "알림이 읽음으로 표시되었습니다."}
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 읽음 처리에 실패했습니다.")


@router.get("/statistics", response_model=DartStatisticsResponse)
async def get_statistics(
    current_user = Depends(get_current_user_optional)
):
    """DART 모니터링 통계 조회"""
    try:
        stats = dart_service.get_statistics()
        
        # 추가 통계 정보 (데이터베이스에서)
        today = datetime.now().date()
        
        # 오늘 발송된 알림 수
        today_alerts_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'dart' 
            AND DATE(created_at) = :today
        """
        today_alerts = await database.fetch_val(today_alerts_query, {"today": today})
        
        # 이번 주 발송된 알림 수
        week_ago = today - timedelta(days=7)
        week_alerts_query = """
            SELECT COUNT(*) FROM alert_history 
            WHERE alert_type = 'dart' 
            AND created_at >= :week_ago
        """
        week_alerts = await database.fetch_val(week_alerts_query, {"week_ago": week_ago})
        
        statistics = {
            "total_disclosures": stats.get("total_processed", 0),
            "matched_disclosures": week_alerts or 0,
            "sent_alerts": today_alerts or 0,
            "companies_monitored": stats.get("companies_count", 0),
            "keywords_count": stats.get("keywords_count", 0),
            "last_check_time": datetime.now(),
            "next_check_time": datetime.now() + timedelta(seconds=dart_service.api_key and 1800 or 0)
        }
        
        return DartStatisticsResponse(statistics=statistics)
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="통계 조회에 실패했습니다.")


@router.post("/check-now")
async def check_disclosures_now(
    current_user = Depends(get_current_user_optional)
):
    """수동으로 공시 체크 실행"""
    try:
        # 새로운 공시 처리
        alerts = await dart_service.process_new_disclosures()
        
        # 알림 발송
        sent_count = await dart_service.send_alerts(alerts)
        
        return {
            "message": "공시 체크가 완료되었습니다.",
            "new_disclosures": len(alerts),
            "sent_alerts": sent_count,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"수동 공시 체크 실패: {e}")
        raise HTTPException(status_code=500, detail="공시 체크에 실패했습니다.")


@router.get("/health")
async def health_check():
    """DART 모듈 헬스체크"""
    try:
        # API 키 확인
        api_key_valid = bool(dart_service.api_key)
        
        # 최근 체크 시간
        last_check = dart_service.processed_ids.last_updated
        
        # 처리된 공시 수
        processed_count = len(dart_service.processed_ids.processed_ids)
        
        return {
            "status": "healthy",
            "api_key_configured": api_key_valid,
            "last_check": last_check.isoformat() if last_check else None,
            "processed_disclosures": processed_count,
            "keywords_count": len(dart_service.keywords),
            "companies_count": len(dart_service.companies)
        }
        
    except Exception as e:
        logger.error(f"DART 헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }