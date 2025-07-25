"""
V2 Investment Monitor - 시스템 API 라우터
시스템 상태, 설정, 관리 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List
import logging
import asyncio
import psutil
import sys
from datetime import datetime
from pathlib import Path

from ..core.config import settings
from ..core.database import check_database_health, database
from ..services.dart_service import dart_service
from ..services.stock_service import stock_service
from ..services.notification_service import notification_service
from ..services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# === 시스템 상태 ===

@router.get("/health")
async def health_check():
    """기본 헬스체크"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.now().isoformat(),
        "debug_mode": settings.debug
    }

@router.get("/status")
async def get_system_status():
    """상세 시스템 상태 querying"""
    try:
        # 데이터베이스 상태
        db_health = await check_database_health()
        
        # 서비스 상태
        dart_stats = await dart_service.get_statistics()
        stock_stats = await stock_service.get_statistics()
        notification_stats = await notification_service.get_notification_statistics()
        
        # WebSocket 상태
        websocket_connections = websocket_manager.get_connection_count()
        
        # 시스템 리소스
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        cpu_percent = psutil.Process().cpu_percent()
        
        return {
            "system": {
                "status": "running",
                "uptime": "실행 중",
                "debug_mode": settings.debug,
                "python_version": sys.version,
                "memory_usage_mb": round(memory_usage, 2),
                "cpu_percent": cpu_percent
            },
            "database": {
                "status": "connected" if db_health else "disconnected",
                "url": settings.database_url.split("///")[-1] if "sqlite" in settings.database_url else settings.database_url
            },
            "services": {
                "dart_monitor": {
                    "status": "active",
                    "processed_disclosures": dart_stats.get("total_processed", 0),
                    "monitored_companies": dart_stats.get("companies_count", 0),
                    "monitored_keywords": dart_stats.get("keywords_count", 0)
                },
                "stock_monitor": {
                    "status": "active",
                    "total_stocks": stock_stats.get("total_stocks", 0),
                    "enabled_stocks": stock_stats.get("enabled_stocks", 0),
                    "market_open": stock_stats.get("market_open", False)
                },
                "notification": {
                    "status": "active",
                    "total_notifications": notification_stats.get("total_count", 0),
                    "unread_notifications": notification_stats.get("unread_count", 0)
                },
                "websocket": {
                    "status": "active",
                    "connected_clients": websocket_connections
                }
            },
            "external_apis": {
                "dart_api": {
                    "configured": bool(settings.dart_api_key),
                    "base_url": settings.dart_base_url
                },
                "email_smtp": {
                    "configured": bool(settings.email_sender and settings.email_password),
                    "server": f"{settings.smtp_server}:{settings.smtp_port}"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 시스템 상태 querying failed: {e}")
        raise HTTPException(status_code=500, detail="시스템 상태 querying 중 error가 발생했습니다.")

@router.get("/diagnostics")
async def run_system_diagnostics():
    """시스템 진단 실행"""
    try:
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 1. 데이터베이스 connected 테스트
        try:
            db_health = await check_database_health()
            diagnostics["checks"]["database"] = {
                "status": "pass" if db_health else "fail",
                "message": "데이터베이스 connected 정상" if db_health else "데이터베이스 connected failed"
            }
        except Exception as e:
            diagnostics["checks"]["database"] = {
                "status": "fail",
                "message": f"데이터베이스 테스트 failed: {str(e)}"
            }
        
        # 2. DART API 테스트
        try:
            disclosures = await dart_service.fetch_recent_disclosures(days=1)
            if disclosures is not None:
                diagnostics["checks"]["dart_api"] = {
                    "status": "pass",
                    "message": f"DART API 응답 정상 ({len(disclosures) if disclosures else 0} records querying)"
                }
            else:
                diagnostics["checks"]["dart_api"] = {
                    "status": "fail",
                    "message": "DART API 응답 없음"
                }
        except Exception as e:
            diagnostics["checks"]["dart_api"] = {
                "status": "fail", 
                "message": f"DART API 테스트 failed: {str(e)}"
            }
        
        # 3. 주식 가격 querying 테스트
        try:
            # 삼성전자로 테스트
            price_data = await stock_service.get_stock_price("005930")
            if price_data:
                diagnostics["checks"]["stock_api"] = {
                    "status": "pass",
                    "message": f"주식 API 응답 정상 (삼성전자: {price_data.get('current_price', 0):,}원)"
                }
            else:
                diagnostics["checks"]["stock_api"] = {
                    "status": "warn",
                    "message": "주식 API 응답 없음 (시장  hours 외일 수 있음)"
                }
        except Exception as e:
            diagnostics["checks"]["stock_api"] = {
                "status": "fail",
                "message": f"주식 API 테스트 failed: {str(e)}"
            }
        
        # 4. 이메일 설정 checking
        email_configured = bool(settings.email_sender and settings.email_password)
        diagnostics["checks"]["email_config"] = {
            "status": "pass" if email_configured else "warn",
            "message": "이메일 설정 정상" if email_configured else "이메일 설정이 불완전합니다"
        }
        
        # 5. 파일 시스템 checking
        try:
            data_dir = settings.data_dir
            logs_dir = settings.logs_dir
            
            data_writable = data_dir.exists() and data_dir.is_dir()
            logs_writable = logs_dir.exists() and logs_dir.is_dir()
            
            if data_writable and logs_writable:
                diagnostics["checks"]["filesystem"] = {
                    "status": "pass",
                    "message": f"파일 시스템 접근 정상 (데이터: {data_dir}, 로그: {logs_dir})"
                }
            else:
                diagnostics["checks"]["filesystem"] = {
                    "status": "fail",
                    "message": "파일 시스템 접근 failed"
                }
        except Exception as e:
            diagnostics["checks"]["filesystem"] = {
                "status": "fail",
                "message": f"파일 시스템 테스트 failed: {str(e)}"
            }
        
        # 전체 상태 판단
        failed_checks = sum(1 for check in diagnostics["checks"].values() if check["status"] == "fail")
        warn_checks = sum(1 for check in diagnostics["checks"].values() if check["status"] == "warn")
        
        if failed_checks == 0 and warn_checks == 0:
            overall_status = "healthy"
        elif failed_checks == 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        diagnostics["overall_status"] = overall_status
        diagnostics["summary"] = {
            "total_checks": len(diagnostics["checks"]),
            "passed": sum(1 for check in diagnostics["checks"].values() if check["status"] == "pass"),
            "warnings": warn_checks,
            "failures": failed_checks
        }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"[ERROR] 시스템 진단 failed: {e}")
        raise HTTPException(status_code=500, detail="시스템 진단 중 error가 발생했습니다.")

# === 설정 관리 ===

@router.get("/config")
async def get_system_config():
    """시스템 설정 querying (보안 info 제외)"""
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.version,
            "debug": settings.debug
        },
        "server": {
            "host": settings.host,
            "port": settings.port
        },
        "monitoring": {
            "dart_check_interval": settings.dart_check_interval,
            "stock_update_interval": settings.stock_update_interval,
            "market_hours": {
                "open": settings.market_open_time,
                "close": settings.market_close_time
            }
        },
        "limits": {
            "max_websocket_connections": settings.max_websocket_connections,
            "max_processed_ids": settings.max_processed_ids,
            "notification_batch_size": settings.notification_batch_size
        },
        "paths": {
            "data_dir": str(settings.data_dir),
            "logs_dir": str(settings.logs_dir)
        }
    }

# === 로그 관리 ===

@router.get("/logs")
async def get_available_logs():
    """사용 가능한 로그 파일 목록"""
    try:
        logs_dir = settings.logs_dir
        if not logs_dir.exists():
            return {"logs": [], "message": "로그 디렉터리가 존재하지 않습니다."}
        
        log_files = []
        for log_file in logs_dir.glob("*.log"):
            if log_file.is_file():
                stat = log_file.stat()
                log_files.append({
                    "name": log_file.name,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "logs": log_files,
            "total_files": len(log_files),
            "logs_dir": str(logs_dir)
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 로그 목록 querying failed: {e}")
        raise HTTPException(status_code=500, detail="로그 목록 querying 중 error가 발생했습니다.")

@router.get("/logs/{log_name}")
async def get_log_content(
    log_name: str,
    lines: int = Query(100, ge=1, le=1000, description="조회할 라인 수"),
    tail: bool = Query(True, description="파일 끝부터 querying")
):
    """로그 파일 내용 querying"""
    try:
        log_file = settings.logs_dir / log_name
        
        if not log_file.exists() or not log_file.is_file():
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")
        
        # 파일 크기 제한 (10MB)
        if log_file.stat().st_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="로그 파일이 너무 큽니다.")
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            if tail:
                # 파일 끝부터 지정된 라인 수만큼 읽기
                all_lines = f.readlines()
                content_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            else:
                # 파일 처음부터 지정된 라인 수만큼 읽기
                content_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    content_lines.append(line)
        
        return {
            "log_name": log_name,
            "lines_returned": len(content_lines),
            "total_lines": len(all_lines) if tail else "unknown",
            "content": "".join(content_lines),
            "truncated": len(all_lines) > lines if tail else False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 로그 내용 querying failed ({log_name}): {e}")
        raise HTTPException(status_code=500, detail="로그 내용 querying 중 error가 발생했습니다.")

# === 데이터베이스 관리 ===

@router.get("/database/stats")
async def get_database_statistics():
    """데이터베이스 통계"""
    try:
        tables = ["dart_disclosures", "stock_monitoring", "notification_history", "users"]
        stats = {}
        
        for table in tables:
            try:
                count_query = f"SELECT COUNT(*) FROM {table}"
                count = await database.fetch_val(count_query)
                stats[table] = count or 0
            except:
                stats[table] = 0
        
        # 전체 크기 (SQLite만)
        if "sqlite" in settings.database_url:
            db_path = Path(settings.database_url.split("///")[-1])
            if db_path.exists():
                db_size = db_path.stat().st_size
                stats["database_size_mb"] = round(db_size / 1024 / 1024, 2)
        
        return {
            "tables": stats,
            "database_type": "sqlite" if "sqlite" in settings.database_url else "other"
        }
        
    except Exception as e:
        logger.error(f"[ERROR] 데이터베이스 통계 querying failed: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 통계 querying 중 error가 발생했습니다.")

# === WebSocket 관리 ===

@router.get("/websocket/connections")
async def get_websocket_connections():
    """WebSocket connected info"""
    try:
        connections = websocket_manager.get_connection_info()
        
        return {
            "active_connections": len(connections),
            "connections": connections,
            "max_connections": settings.max_websocket_connections
        }
        
    except Exception as e:
        logger.error(f"[ERROR] WebSocket connected info querying failed: {e}")
        raise HTTPException(status_code=500, detail="WebSocket connected info querying 중 error가 발생했습니다.")

# === 시스템 관리 task ===

@router.post("/maintenance/cleanup")
async def run_maintenance_cleanup(
    cleanup_logs: bool = Query(False, description="오래된 로그 파일 정리"),
    cleanup_notifications: bool = Query(True, description="오래된 알림 정리"),
    days_to_keep: int = Query(90, ge=30, le=365, description="보관 기간 (일)")
):
    """시스템 정리 task 실행"""
    try:
        results = {
            "timestamp": datetime.now().isoformat(),
            "operations": []
        }
        
        # 알림 정리
        if cleanup_notifications:
            query = f"SELECT COUNT(*) FROM notification_history WHERE created_at < datetime('now', '-{days_to_keep} days')"
            old_count = await database.fetch_val(query)
            
            if old_count > 0:
                delete_query = f"DELETE FROM notification_history WHERE created_at < datetime('now', '-{days_to_keep} days')"
                await database.execute(delete_query)
                
                results["operations"].append({
                    "type": "cleanup_notifications",
                    "success": True,
                    "message": f"{old_count} items의 오래된 알림을 정리했습니다."
                })
            else:
                results["operations"].append({
                    "type": "cleanup_notifications", 
                    "success": True,
                    "message": "정리할 오래된 알림이 없습니다."
                })
        
        # 로그 파일 정리
        if cleanup_logs:
            logs_dir = settings.logs_dir
            cleaned_files = 0
            
            if logs_dir.exists():
                for log_file in logs_dir.glob("*.log.*"):  # 로테이션된 파일들
                    try:
                        if log_file.is_file():
                            stat = log_file.stat()
                            age_days = (datetime.now().timestamp() - stat.st_mtime) / 86400
                            
                            if age_days > days_to_keep:
                                log_file.unlink()
                                cleaned_files += 1
                    except:
                        continue
            
            results["operations"].append({
                "type": "cleanup_logs",
                "success": True,
                "message": f"{cleaned_files} items의 오래된 로그 파일을 정리했습니다."
            })
        
        return results
        
    except Exception as e:
        logger.error(f"[ERROR] 시스템 정리 failed: {e}")
        raise HTTPException(status_code=500, detail="시스템 정리 중 error가 발생했습니다.")

@router.post("/test-services")
async def test_all_services():
    """모든 서비스 기능 테스트"""
    try:
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # DART 서비스 테스트
        try:
            disclosures = await dart_service.fetch_recent_disclosures(days=1)
            results["tests"]["dart_service"] = {
                "status": "pass",
                "message": f"DART 서비스 정상 ({len(disclosures or [])} records querying)"
            }
        except Exception as e:
            results["tests"]["dart_service"] = {
                "status": "fail",
                "message": f"DART 서비스 failed: {str(e)}"
            }
        
        # 주식 서비스 테스트
        try:
            price_data = await stock_service.get_stock_price("005930")
            results["tests"]["stock_service"] = {
                "status": "pass" if price_data else "warn",
                "message": f"주식 서비스 {'정상' if price_data else '경고 (시장  hours 외)'}"
            }
        except Exception as e:
            results["tests"]["stock_service"] = {
                "status": "fail",
                "message": f"주식 서비스 failed: {str(e)}"
            }
        
        # 알림 서비스 테스트
        try:
            await notification_service.create_system_notification(
                "시스템 테스트",
                "서비스 테스트 중입니다.",
                "low"
            )
            results["tests"]["notification_service"] = {
                "status": "pass",
                "message": "알림 서비스 정상"
            }
        except Exception as e:
            results["tests"]["notification_service"] = {
                "status": "fail", 
                "message": f"알림 서비스 failed: {str(e)}"
            }
        
        return results
        
    except Exception as e:
        logger.error(f"[ERROR] 서비스 테스트 failed: {e}")
        raise HTTPException(status_code=500, detail="서비스 테스트 중 error가 발생했습니다.")