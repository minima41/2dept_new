"""
V2 Investment Monitor - 알림 API 라우터
통합 알림 관리 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import logging

from ..services.notification_service import notification_service

logger = logging.getLogger(__name__)
router = APIRouter()

# === 알림 목록 querying ===

@router.get("/")
async def get_notifications(
    notification_type: Optional[str] = Query(None, description="알림 타입 (dart, stock, system)"),
    limit: int = Query(50, ge=1, le=200, description="조회할 알림  items수"),
    days: int = Query(7, ge=1, le=90, description="조회 기간 (일)"),
    unread_only: bool = Query(False, description="읽지 않은 알림만 querying")
):
    """알림 목록 querying"""
    try:
        notifications = await notification_service.get_recent_notifications(
            notification_type=notification_type,
            limit=limit,
            days=days
        )
        
        # 읽지 않은 알림만 필터링
        if unread_only:
            notifications = [n for n in notifications if not n.get("is_read", False)]
        
        return {
            "notifications": notifications,
            "count": len(notifications),
            "filters": {
                "type": notification_type,
                "days": days,
                "unread_only": unread_only
            }
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 알림 querying failed: {e}")
        raise HTTPException(status_code=500, detail="알림 querying 중 error가 발생했습니다.")

@router.get("/unread")
async def get_unread_notifications():
    """읽지 않은 알림 querying"""
    try:
        from ..core.database import database
        
        query = """
            SELECT * FROM notification_history
            WHERE is_read = false
            ORDER BY priority DESC, created_at DESC
            LIMIT 100
        """
        
        rows = await database.fetch_all(query)
        notifications = [dict(row) for row in rows]
        
        # 우선순위별  minutes류
        high_priority = [n for n in notifications if n.get("priority") == "high"]
        medium_priority = [n for n in notifications if n.get("priority") == "medium"]
        low_priority = [n for n in notifications if n.get("priority") == "low"]
        
        return {
            "notifications": notifications,
            "total_count": len(notifications),
            "by_priority": {
                "high": len(high_priority),
                "medium": len(medium_priority), 
                "low": len(low_priority)
            },
            "high_priority_items": high_priority[:10]  # 상위 10 items만
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 읽지 않은 알림 querying failed: {e}")
        raise HTTPException(status_code=500, detail="읽지 않은 알림 querying 중 error가 발생했습니다.")

@router.get("/recent/{notification_type}")
async def get_recent_notifications_by_type(
    notification_type: str,
    limit: int = Query(20, ge=1, le=100)
):
    """타입별 최근 알림 querying"""
    if notification_type not in ["dart", "stock", "system"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 알림 타입입니다.")
    
    try:
        notifications = await notification_service.get_recent_notifications(
            notification_type=notification_type,
            limit=limit,
            days=30
        )
        
        return {
            "notification_type": notification_type,
            "notifications": notifications,
            "count": len(notifications)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 타입별 알림 querying failed ({notification_type}): {e}")
        raise HTTPException(status_code=500, detail="알림 querying 중 error가 발생했습니다.")

# === 알림 상태 관리 ===

@router.patch("/mark-read")
async def mark_notifications_read(notification_ids: List[int]):
    """알림을 읽음으로 표시"""
    try:
        if not notification_ids:
            raise HTTPException(status_code=400, detail="알림 ID가 필요합니다.")
        
        success = await notification_service.mark_notifications_read(notification_ids)
        
        if success:
            return {
                "success": True,
                "message": f"{len(notification_ids)} items 알림을 읽음으로 표시했습니다.",
                "marked_ids": notification_ids
            }
        else:
            raise HTTPException(status_code=500, detail="알림 읽음 processing failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 알림 읽음 processing failed: {e}")
        raise HTTPException(status_code=500, detail="알림 읽음 processing 중 error가 발생했습니다.")

@router.patch("/mark-all-read")
async def mark_all_notifications_read(
    notification_type: Optional[str] = Query(None, description="특정 타입만 읽음 processing")
):
    """모든 알림을 읽음으로 표시"""
    try:
        from ..core.database import database
        
        if notification_type:
            query = """
                UPDATE notification_history 
                SET is_read = true 
                WHERE is_read = false AND notification_type = :type
            """
            await database.execute(query, {"type": notification_type})
            message = f"{notification_type} 타입 알림을 모두 읽음으로 표시했습니다."
        else:
            query = """
                UPDATE notification_history 
                SET is_read = true 
                WHERE is_read = false
            """
            await database.execute(query)
            message = "모든 알림을 읽음으로 표시했습니다."
        
        return {
            "success": True,
            "message": message,
            "notification_type": notification_type
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 전체 알림 읽음 processing failed: {e}")
        raise HTTPException(status_code=500, detail="알림 읽음 processing 중 error가 발생했습니다.")

# === 알림 통계 ===

@router.get("/statistics")
async def get_notification_statistics():
    """알림 통계 querying"""
    try:
        stats = await notification_service.get_notification_statistics()
        return stats
    except Exception as e:
        logger.error(f"[ERROR] 알림 통계 querying failed: {e}")
        raise HTTPException(status_code=500, detail="알림 통계 querying 중 error가 발생했습니다.")

@router.get("/statistics/summary")
async def get_notification_summary():
    """알림 요약 통계"""
    try:
        from ..core.database import database
        
        # 기본 통계
        queries = {
            "total": "SELECT COUNT(*) FROM notification_history",
            "unread": "SELECT COUNT(*) FROM notification_history WHERE is_read = false",
            "today": "SELECT COUNT(*) FROM notification_history WHERE DATE(created_at) = DATE('now')",
            "this_week": "SELECT COUNT(*) FROM notification_history WHERE created_at >= datetime('now', '-7 days')",
            "unsent": "SELECT COUNT(*) FROM notification_history WHERE is_sent = false"
        }
        
        stats = {}
        for key, query in queries.items():
            try:
                result = await database.fetch_val(query)
                stats[key] = result or 0
            except:
                stats[key] = 0
        
        # 타입별 통계
        type_query = """
            SELECT notification_type, COUNT(*) as count
            FROM notification_history
            GROUP BY notification_type
        """
        type_rows = await database.fetch_all(type_query)
        stats["by_type"] = {row["notification_type"]: row["count"] for row in type_rows}
        
        # 우선순위별 통계
        priority_query = """
            SELECT priority, COUNT(*) as count
            FROM notification_history
            WHERE is_read = false
            GROUP BY priority
        """
        priority_rows = await database.fetch_all(priority_query)
        stats["unread_by_priority"] = {row["priority"]: row["count"] for row in priority_rows}
        
        return {
            "summary": stats,
            "health_indicators": {
                "high_priority_unread": stats["unread_by_priority"].get("high", 0),
                "unsent_notifications": stats["unsent"],
                "daily_average": round(stats["this_week"] / 7, 1) if stats["this_week"] else 0
            }
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 알림 요약 통계 failed: {e}")
        raise HTTPException(status_code=500, detail="알림 요약 통계 querying 중 error가 발생했습니다.")

# === 테스트 알림 ===

@router.post("/test")
async def send_test_notification(
    notification_type: str = Query("system", description="테스트할 알림 타입"),
    priority: str = Query("medium", description="우선순위")
):
    """테스트 알림 sending"""
    if notification_type not in ["dart", "stock", "system"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 알림 타입입니다.")
    
    if priority not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 우선순위입니다.")
    
    try:
        test_messages = {
            "dart": "테스트 DART 공시 알림입니다.",
            "stock": "테스트 주식 가격 알림입니다.",
            "system": "테스트 시스템 알림입니다."
        }
        
        title = f"[테스트] {notification_type.upper()} 알림"
        message = test_messages[notification_type]
        
        if notification_type == "dart":
            test_data = {
                "corp_name": "테스트기업",
                "report_nm": "테스트공시",
                "matched_keywords": ["테스트"],
                "priority_score": 3,
                "rcept_no": "test123"
            }
            success = await notification_service.create_dart_notification(test_data)
        elif notification_type == "stock":
            test_data = {
                "stock_name": "테스트주식",
                "stock_code": "000000",
                "alert_type": "test_alert",
                "current_price": 10000,
                "message": message
            }
            success = await notification_service.create_stock_notification(test_data)
        else:  # system
            success = await notification_service.create_system_notification(title, message, priority)
        
        if success:
            return {
                "success": True,
                "message": f"테스트 알림({notification_type})이 sending되었습니다.",
                "notification_type": notification_type,
                "priority": priority
            }
        else:
            raise HTTPException(status_code=500, detail="테스트 알림 sending failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 테스트 알림 failed: {e}")
        raise HTTPException(status_code=500, detail="테스트 알림 중 error가 발생했습니다.")

# === 알림 검색 및 필터링 ===

@router.get("/search")
async def search_notifications(
    keyword: str = Query(..., description="검색 키워드"),
    notification_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """알림 검색"""
    try:
        from ..core.database import database
        
        # 기본 쿼리
        where_conditions = ["(title LIKE :keyword OR message LIKE :keyword)"]
        params = {"keyword": f"%{keyword}%", "limit": limit}
        
        # 필터 추가
        if notification_type:
            where_conditions.append("notification_type = :type")
            params["type"] = notification_type
            
        if priority:
            where_conditions.append("priority = :priority")
            params["priority"] = priority
        
        query = f"""
            SELECT * FROM notification_history
            WHERE {' AND '.join(where_conditions)}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        
        rows = await database.fetch_all(query, params)
        results = [dict(row) for row in rows]
        
        return {
            "keyword": keyword,
            "filters": {
                "type": notification_type,
                "priority": priority
            },
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 알림 검색 failed: {e}")
        raise HTTPException(status_code=500, detail="알림 검색 중 error가 발생했습니다.")

# === 알림 상세 info ===

@router.get("/{notification_id}")
async def get_notification_detail(notification_id: int):
    """특정 알림 상세 info querying"""
    try:
        from ..core.database import database
        
        query = "SELECT * FROM notification_history WHERE id = :id"
        result = await database.fetch_one(query, {"id": notification_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="해당 알림을 찾을 수 없습니다.")
        
        notification = dict(result)
        
        # 데이터 파싱
        if notification.get("data"):
            try:
                import json
                notification["data"] = json.loads(notification["data"])
            except:
                pass
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 알림 상세 querying failed ({notification_id}): {e}")
        raise HTTPException(status_code=500, detail="알림 상세 querying 중 error가 발생했습니다.")

# === 일괄 task ===

@router.delete("/cleanup")
async def cleanup_old_notifications(
    days: int = Query(90, ge=30, le=365, description="보관 기간 (일)"),
    notification_type: Optional[str] = Query(None, description="삭제할 알림 타입")
):
    """오래된 알림 정리"""
    try:
        from ..core.database import database
        
        where_condition = f"created_at < datetime('now', '-{days} days')"
        params = {}
        
        if notification_type:
            where_condition += " AND notification_type = :type"
            params["type"] = notification_type
        
        # 삭제 전  items수 checking
        count_query = f"SELECT COUNT(*) FROM notification_history WHERE {where_condition}"
        count = await database.fetch_val(count_query, params)
        
        # 삭제 실행
        delete_query = f"DELETE FROM notification_history WHERE {where_condition}"
        await database.execute(delete_query, params)
        
        return {
            "success": True,
            "message": f"{count} items의 오래된 알림을 정리했습니다.",
            "deleted_count": count,
            "criteria": f"{days}일 이전" + (f" ({notification_type} 타입)" if notification_type else "")
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 알림 정리 failed: {e}")
        raise HTTPException(status_code=500, detail="알림 정리 중 error가 발생했습니다.")