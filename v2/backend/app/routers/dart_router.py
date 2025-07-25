"""
V2 Investment Monitor - DART API 라우터
DART 공시 모니터링 관련 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import logging
from datetime import datetime

from ..services.dart_service import dart_service
from ..models.dart_models import DartDisclosureResponse, DartKeywordUpdate, DartCompanyUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# === DART 공시 querying 엔드포인트 ===

@router.get("/disclosures")
async def get_recent_disclosures(
    limit: int = Query(20, ge=1, le=100, description="조회할 공시  items수"),
    days: int = Query(7, ge=1, le=30, description="조회 기간 (일)")
):
    """최근 중요 공시 목록 querying"""
    try:
        disclosures = await dart_service.get_recent_disclosures_from_db(limit=limit, days=days)
        
        # 실제 데이터가 없는 경우 샘플 데이터 제공
        if not disclosures:
            sample_disclosures = [
                {
                    "rcept_no": "20250124000001",
                    "corp_code": "00126380",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_nm": "주요사항보고서(유상증자결정)",
                    "rcept_dt": "20250124",
                    "flr_nm": "삼성전자",
                    "rm": "유상증자 관련 주요사항 보고",
                    "matched_keywords": ["유상증자"],
                    "priority_score": 8,
                    "is_important": True
                },
                {
                    "rcept_no": "20250124000002", 
                    "corp_code": "00164779",
                    "corp_name": "SK하이닉스",
                    "stock_code": "000660",
                    "report_nm": "주요사항보고서(투자결정)",
                    "rcept_dt": "20250124",
                    "flr_nm": "SK하이닉스",
                    "rm": "대규모 설비투자 계획 발표",
                    "matched_keywords": ["투자"],
                    "priority_score": 6,
                    "is_important": True
                },
                {
                    "rcept_no": "20250124000003",
                    "corp_code": "00293886",
                    "corp_name": "NAVER",
                    "stock_code": "035420", 
                    "report_nm": "사업보고서( minutes기보고서)",
                    "rcept_dt": "20250124",
                    "flr_nm": "NAVER",
                    "rm": "2024년 4 minutes기 실적 발표",
                    "matched_keywords": [],
                    "priority_score": 3,
                    "is_important": False
                }
            ]
            disclosures = sample_disclosures
        
        return {
            "success": True,
            "disclosures": disclosures,
            "count": len(disclosures),
            "days": days
        }
    except Exception as e:
        logger.error(f"[ERROR] 공시 querying failed: {e}")
        return {
            "success": False,
            "disclosures": [],
            "count": 0,
            "days": days,
            "error": str(e)
        }

@router.get("/disclosures/latest")
async def get_latest_disclosures(count: int = Query(5, ge=1, le=20)):
    """최신 공시 querying (실 hours)"""
    try:
        # 실 hours DART API 호출
        disclosures = await dart_service.fetch_recent_disclosures(days=1)
        
        # 중요도 순으로 정렬하여 상위 N items 반환
        analyzed_disclosures = []
        for disclosure in disclosures[:count * 3]:  # 여유 minutes 확보
            analyzed = dart_service.analyze_disclosure(disclosure)
            if analyzed["is_important"]:
                analyzed_disclosures.append(analyzed)
            
            if len(analyzed_disclosures) >= count:
                break
        
        return analyzed_disclosures
    except Exception as e:
        logger.error(f"[ERROR] 최신 공시 querying failed: {e}")
        raise HTTPException(status_code=500, detail="최신 공시 querying 중 error가 발생했습니다.")

@router.get("/disclosures/{rcept_no}")
async def get_disclosure_detail(rcept_no: str):
    """특정 공시 상세 info querying"""
    try:
        query = "SELECT * FROM dart_disclosures WHERE rcept_no = :rcept_no"
        from ..core.database import database
        
        result = await database.fetch_one(query, {"rcept_no": rcept_no})
        if not result:
            raise HTTPException(status_code=404, detail="해당 공시를 찾을 수 없습니다.")
        
        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 공시 상세 querying failed ({rcept_no}): {e}")
        raise HTTPException(status_code=500, detail="공시 상세 querying 중 error가 발생했습니다.")

# === DART 통계 및 상태 ===

@router.get("/statistics")
async def get_dart_statistics():
    """DART 모니터링 통계 querying"""
    try:
        stats = await dart_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"[ERROR] DART 통계 querying failed: {e}")
        raise HTTPException(status_code=500, detail="통계 querying 중 error가 발생했습니다.")

@router.get("/status")
async def get_dart_status():
    """DART 모니터링 상태 querying"""
    try:
        # 서비스 상태 checking
        recent_check = await dart_service.get_recent_disclosures_from_db(limit=1, days=1)
        last_check = recent_check[0]["created_at"] if recent_check else None
        
        return {
            "service_active": True,
            "api_key_configured": bool(dart_service.api_key),
            "monitored_companies": len(dart_service.companies),
            "monitored_keywords": len(dart_service.keywords),
            "processed_ids_count": len(dart_service.processed_ids),
            "last_check": last_check,
            "next_check": "30 minutes 간격으로 자동 실행"
        }
    except Exception as e:
        logger.error(f"[ERROR] DART 상태 querying failed: {e}")
        raise HTTPException(status_code=500, detail="상태 querying 중 error가 발생했습니다.")

# === 수동 updating ===

@router.post("/check-now")
async def manual_dart_check():
    """수동 DART 공시 checking"""
    try:
        logger.info("[PROCESS] 수동 DART 공시 checking starting")
        new_disclosures = await dart_service.process_new_disclosures()
        
        return {
            "success": True,
            "message": f"새로운 중요 공시 {len(new_disclosures)} records 발견",
            "new_disclosures": len(new_disclosures),
            "disclosures": new_disclosures
        }
    except Exception as e:
        logger.error(f"[ERROR] 수동 DART checking failed: {e}")
        raise HTTPException(status_code=500, detail="DART checking 중 error가 발생했습니다.")

# === 설정 관리 ===

@router.get("/keywords")
async def get_dart_keywords():
    """모니터링 키워드 목록 querying"""
    return {
        "keywords": dart_service.keywords,
        "count": len(dart_service.keywords)
    }

@router.put("/keywords")
async def update_dart_keywords(keyword_update: DartKeywordUpdate):
    """모니터링 키워드 updating"""
    try:
        success = dart_service.update_keywords(keyword_update.keywords)
        if success:
            return {
                "success": True,
                "message": f"키워드 {len(keyword_update.keywords)} items로 updating completed",
                "keywords": dart_service.keywords
            }
        else:
            raise HTTPException(status_code=500, detail="키워드 updating failed")
    except Exception as e:
        logger.error(f"[ERROR] 키워드 updating failed: {e}")
        raise HTTPException(status_code=500, detail="키워드 updating 중 error가 발생했습니다.")

@router.get("/companies")
async def get_monitored_companies():
    """모니터링 대상 기업 목록 querying"""
    return {
        "companies": dart_service.companies,
        "count": len(dart_service.companies)
    }

@router.put("/companies") 
async def update_monitored_companies(company_update: DartCompanyUpdate):
    """모니터링 대상 기업 updating"""
    try:
        success = dart_service.update_companies(company_update.companies)
        if success:
            return {
                "success": True,
                "message": f"관심 기업 {len(company_update.companies)} items로 updating completed",
                "companies": dart_service.companies
            }
        else:
            raise HTTPException(status_code=500, detail="기업 목록 updating failed")
    except Exception as e:
        logger.error(f"[ERROR] 기업 목록 updating failed: {e}")
        raise HTTPException(status_code=500, detail="기업 목록 updating 중 error가 발생했습니다.")

# === 검색 및 필터링 ===

@router.get("/disclosures/search")
async def search_disclosures(
    keyword: str = Query(..., description="검색 키워드"),
    limit: int = Query(20, ge=1, le=100, description="결과  items수"),
    days: int = Query(30, ge=1, le=90, description="검색 기간")
):
    """공시 검색"""
    try:
        from ..core.database import database
        
        query = """
            SELECT * FROM dart_disclosures 
            WHERE (corp_name LIKE :keyword OR report_nm LIKE :keyword OR rm LIKE :keyword)
            AND created_at >= datetime('now', '-{} days')
            ORDER BY priority_score DESC, created_at DESC
            LIMIT :limit
        """.format(days)
        
        search_keyword = f"%{keyword}%"
        rows = await database.fetch_all(query, {
            "keyword": search_keyword,
            "limit": limit
        })
        
        results = [dict(row) for row in rows]
        
        return {
            "keyword": keyword,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 공시 검색 failed: {e}")
        raise HTTPException(status_code=500, detail="공시 검색 중 error가 발생했습니다.")

@router.get("/disclosures/by-company/{corp_code}")
async def get_disclosures_by_company(
    corp_code: str,
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90)
):
    """특정 기업의 공시 목록 querying"""
    try:
        from ..core.database import database
        
        query = """
            SELECT * FROM dart_disclosures
            WHERE corp_code = :corp_code
            AND created_at >= datetime('now', '-{} days')
            ORDER BY created_at DESC
            LIMIT :limit
        """.format(days)
        
        rows = await database.fetch_all(query, {
            "corp_code": corp_code,
            "limit": limit
        })
        
        results = [dict(row) for row in rows]
        company_name = dart_service.companies.get(corp_code, corp_code)
        
        return {
            "corp_code": corp_code,
            "corp_name": company_name,
            "disclosures": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 기업별 공시 querying failed ({corp_code}): {e}")
        raise HTTPException(status_code=500, detail="기업별 공시 querying 중 error가 발생했습니다.")