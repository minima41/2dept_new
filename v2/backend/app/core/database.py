"""
V2 Investment Monitor - 데이터베이스 설정
SQLAlchemy 2.0 + 비동기 지원
"""
from sqlalchemy import create_engine, MetaData, Column, Integer, String, DateTime, Boolean, Float, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from databases import Database
from datetime import datetime
from typing import AsyncGenerator, Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

# === SQLAlchemy 2.0 스타일 ===
class Base(DeclarativeBase):
    """베이스 모델 클래스"""
    pass

# === 데이터베이스 connected ===
# SQLite용 ( items발환경)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# 비동기 데이터베이스 (선택적)
database = Database(settings.database_url)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === 데이터 모델 (기존 기능 기반) ===

class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DartDisclosure(Base):
    """DART 공시 info 테이블"""
    __tablename__ = "dart_disclosures"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rcept_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 접수번호
    corp_code: Mapped[str] = mapped_column(String(20), index=True)  # 기업코드
    corp_name: Mapped[str] = mapped_column(String(255), index=True)  # 기업명
    report_nm: Mapped[str] = mapped_column(Text)  # 보고서명
    flr_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 공시대상회사
    rcept_dt: Mapped[str] = mapped_column(String(20))  # 접수일자
    rm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 비고
    
    #  minutes석 결과
    matched_keywords: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # 매칭된 키워드
    priority_score: Mapped[int] = mapped_column(Integer, default=0)  # 우선순위 점수
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockMonitoring(Base):
    """주식 모니터링 테이블"""
    __tablename__ = "stock_monitoring"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # 종목코드
    stock_name: Mapped[str] = mapped_column(String(255), index=True)  # 종목명
    
    # 모니터링 설정
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 목표가
    stop_loss_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 손절가
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 현재 상태
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True) 
    price_change_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationHistory(Base):
    """알림 히스토리 테이블""" 
    __tablename__ = "notification_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), index=True)  # 'dart', 'stock', 'system'
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    
    # 관련 데이터
    related_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 관련 ID (접수번호, 종목코드 등)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 추가 데이터
    
    # 상태
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# === 데이터베이스 유틸리티 ===

def get_db() -> AsyncGenerator[SessionLocal, None]:
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_database():
    """데이터베이스  seconds기화"""
    try:
        await database.connect()
        
        # 테이블 creating
        Base.metadata.create_all(bind=engine)
        
        logger.info("[SUCCESS] 데이터베이스  seconds기화 completed")
        
        #  items발용 기본 데이터 creating
        if settings.debug:
            await create_sample_data()
            
    except Exception as e:
        logger.error(f"[ERROR] 데이터베이스  seconds기화 failed: {e}")
        raise


async def create_sample_data():
    """ items발용 샘플 데이터 creating"""
    try:
        # 기본 사용자 checking/생성
        query = "SELECT COUNT(*) FROM users WHERE email = :email"
        result = await database.fetch_val(query, {"email": "admin@inveski.com"})
        
        if result == 0:
            from app.services.auth_service import get_password_hash
            hashed_password = get_password_hash("admin123")
            
            query = """
                INSERT INTO users (email, hashed_password, full_name, is_active)
                VALUES (:email, :hashed_password, :full_name, :is_active)
            """
            await database.execute(query, {
                "email": "admin@inveski.com",
                "hashed_password": hashed_password,
                "full_name": "관리자",
                "is_active": True
            })
            logger.info("👤 기본 사용자 creating: admin@inveski.com / admin123")
            
    except Exception as e:
        logger.warning(f"[WARNING] 샘플 데이터 creating 중 error: {e}")


async def close_database():
    """데이터베이스 connected stopping"""
    await database.disconnect()
    logger.info("[CONNECTION] 데이터베이스 connected stopping")


# === 헬스체크 ===
async def check_database_health() -> bool:
    """데이터베이스 connected 상태 checking"""
    try:
        await database.fetch_val("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 connected failed: {e}")
        return False