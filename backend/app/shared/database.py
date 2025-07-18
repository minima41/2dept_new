from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from databases import Database
import asyncio
from typing import AsyncGenerator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy 설정
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 비동기 데이터베이스 연결
database = Database(settings.DATABASE_URL)


class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AlertHistory(Base):
    """알림 히스토리 테이블"""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False)  # 'dart', 'stock', 'system'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    stock_code = Column(String(20), nullable=True)
    stock_name = Column(String(100), nullable=True)
    price = Column(Float, nullable=True)
    change_rate = Column(Float, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Fund(Base):
    """펀드 정보 테이블"""
    __tablename__ = "funds"
    
    id = Column(Integer, primary_key=True, index=True)
    fund_code = Column(String(20), unique=True, index=True, nullable=False)
    fund_name = Column(String(255), nullable=False)
    fund_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


async def get_db() -> AsyncGenerator[Session, None]:
    """데이터베이스 세션 생성"""
    async with database.transaction():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


async def init_db():
    """데이터베이스 초기화"""
    try:
        await database.connect()
        logger.info("데이터베이스 연결 성공")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 기본 사용자 생성 (개발용)
        if settings.DEBUG:
            await create_default_user()
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


async def create_default_user():
    """기본 사용자 생성 (개발용)"""
    try:
        from app.shared.auth import get_password_hash
        
        # 기본 사용자 확인
        query = "SELECT COUNT(*) FROM users WHERE email = :email"
        result = await database.fetch_val(query, {"email": "admin@inveski.com"})
        
        if result == 0:
            # 기본 사용자 생성
            hashed_password = get_password_hash("admin123")
            query = """
                INSERT INTO users (email, hashed_password, full_name, is_active)
                VALUES (:email, :hashed_password, :full_name, :is_active)
            """
            await database.execute(query, {
                "email": "admin@inveski.com",
                "hashed_password": hashed_password,
                "full_name": "투자본부 관리자",
                "is_active": True
            })
            logger.info("기본 사용자 생성 완료 (admin@inveski.com / admin123)")
            
    except Exception as e:
        logger.error(f"기본 사용자 생성 실패: {e}")


async def close_db():
    """데이터베이스 연결 종료"""
    await database.disconnect()
    logger.info("데이터베이스 연결 종료")


# 헬스체크용 데이터베이스 연결 확인
async def check_database_health() -> bool:
    """데이터베이스 연결 상태 확인"""
    try:
        query = "SELECT 1"
        await database.fetch_val(query)
        return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return False