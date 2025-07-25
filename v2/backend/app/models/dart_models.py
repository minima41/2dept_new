"""
V2 Investment Monitor - DART 관련 Pydantic 모델
DART API 요청/응답 데이터 검증
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime


class DartDisclosureResponse(BaseModel):
    """DART 공시 응답 모델"""
    rcept_no: str = Field(..., description="접수번호")
    corp_code: str = Field(..., description="기업코드")
    corp_name: str = Field(..., description="기업명")
    report_nm: str = Field(..., description="보고서명")
    flr_nm: Optional[str] = Field(None, description="공시대상회사")
    rcept_dt: str = Field(..., description="접수일자")
    rm: Optional[str] = Field(None, description="비고")
    
    #  minutes석 결과
    matched_keywords: Optional[List[str]] = Field(default_factory=list, description="매칭된 키워드")
    priority_score: int = Field(default=0, description="우선순위 점수")
    is_important: bool = Field(default=False, description="중요 공시 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rcept_no": "20240101000001",
                "corp_code": "005930",
                "corp_name": "삼성전자",
                "report_nm": "주요사항보고서(유상증자결정)",
                "flr_nm": "삼성전자",
                "rcept_dt": "20240101",
                "rm": "유상증자 결정 관련",
                "matched_keywords": ["유상증자", "결정"],
                "priority_score": 5,
                "is_important": True
            }
        }


class DartKeywordUpdate(BaseModel):
    """DART 키워드 updating 요청"""
    keywords: List[str] = Field(..., min_items=1, description="모니터링 키워드 목록")
    
    @validator('keywords')
    def validate_keywords(cls, v):
        # 빈 문자열 제거
        keywords = [keyword.strip() for keyword in v if keyword.strip()]
        if not keywords:
            raise ValueError("최소 하나의 키워드가 필요합니다")
        return keywords
    
    class Config:
        json_schema_extra = {
            "example": {
                "keywords": ["합병", " minutes할", "매각", "취득", "유상증자"]
            }
        }


class DartCompanyUpdate(BaseModel):
    """DART 관심기업 updating 요청"""
    companies: Dict[str, str] = Field(..., description="기업코드:기업명 딕셔너리")
    
    @validator('companies')
    def validate_companies(cls, v):
        if not v:
            raise ValueError("최소 하나의 기업이 필요합니다")
        
        # 기업코드 형식 검증 (6자리 숫자)
        for corp_code, corp_name in v.items():
            if not corp_code.isdigit() or len(corp_code) != 6:
                raise ValueError(f"잘못된 기업코드 형식: {corp_code}")
            if not corp_name.strip():
                raise ValueError(f"기업명이 비어있습니다: {corp_code}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "companies": {
                    "005930": "삼성전자",
                    "000660": "SK하이닉스",
                    "035420": "NAVER"
                }
            }
        }


class DartSearchRequest(BaseModel):
    """DART 공시 검색 요청"""
    keyword: str = Field(..., min_length=2, description="검색 키워드")
    limit: int = Field(default=20, ge=1, le=100, description="결과  items수")
    days: int = Field(default=30, ge=1, le=90, description="검색 기간 (일)")
    corp_code: Optional[str] = Field(None, description="특정 기업 코드")
    
    @validator('keyword')
    def validate_keyword(cls, v):
        keyword = v.strip()
        if not keyword:
            raise ValueError("키워드가 비어있습니다")
        return keyword
    
    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "유상증자",
                "limit": 20,
                "days": 30,
                "corp_code": "005930"
            }
        }


class DartStatistics(BaseModel):
    """DART 통계 응답 모델"""
    total_processed: int = Field(default=0, description="총 processing된 공시 수")
    today_count: int = Field(default=0, description="오늘 공시 수")
    week_count: int = Field(default=0, description="이번 주 공시 수")
    high_priority_count: int = Field(default=0, description="고우선순위 공시 수")
    keywords_count: int = Field(default=0, description="모니터링 키워드 수")
    companies_count: int = Field(default=0, description="관심 기업 수")
    processed_ids_count: int = Field(default=0, description="처리된 ID 수")


class DartApiResponse(BaseModel):
    """DART API 기본 응답 구조"""
    status: str = Field(..., description="응답 상태")
    message: Optional[str] = Field(None, description="응답 message")
    list: Optional[List[Dict]] = Field(None, description="공시 목록")
    
    @validator('status')
    def validate_status(cls, v):
        # DART API 상태 코드 검증
        valid_statuses = ['000', '010', '020', '100', '800', '900', '901']
        if v not in valid_statuses:
            raise ValueError(f"알 수 없는 DART API 상태: {v}")
        return v


class DartDisclosureDetail(BaseModel):
    """공시 상세 info 모델"""
    rcept_no: str
    corp_code: str
    corp_name: str
    report_nm: str
    flr_nm: Optional[str] = None
    rcept_dt: str
    rm: Optional[str] = None
    
    # 추가 메타데이터
    matched_keywords: List[str] = Field(default_factory=list)
    priority_score: int = 0
    is_processed: bool = False
    created_at: Optional[datetime] = None
    
    #  minutes석 info
    keyword_matches: Dict[str, int] = Field(default_factory=dict, description="키워드별 매칭 횟수")
    importance_level: str = Field(default="medium", description="중요도 레벨")
    
    @validator('importance_level')
    def validate_importance_level(cls, v):
        valid_levels = ['low', 'medium', 'high', 'critical']
        if v not in valid_levels:
            raise ValueError(f"유효하지 않은 중요도 레벨: {v}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "rcept_no": "20240101000001",
                "corp_code": "005930",
                "corp_name": "삼성전자",
                "report_nm": "주요사항보고서(유상증자결정)",
                "flr_nm": "삼성전자",
                "rcept_dt": "20240101",
                "rm": "유상증자 결정 관련",
                "matched_keywords": ["유상증자", "결정"],
                "priority_score": 8,
                "is_processed": True,
                "keyword_matches": {"유상증자": 2, "결정": 1},
                "importance_level": "high"
            }
        }


class DartConfigUpdate(BaseModel):
    """DART 설정 updating 요청"""
    check_interval: Optional[int] = Field(None, ge=300, le=3600, description="확인 간격 ( seconds)")
    keywords: Optional[List[str]] = Field(None, description="키워드 목록")
    companies: Optional[Dict[str, str]] = Field(None, description="관심 기업 목록")
    enable_email_alerts: Optional[bool] = Field(None, description="이메일 알림 활성화")
    
    @validator('keywords')
    def validate_keywords_optional(cls, v):
        if v is not None:
            keywords = [keyword.strip() for keyword in v if keyword.strip()]
            return keywords
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "check_interval": 1800,
                "keywords": ["합병", " minutes할", "매각"],
                "companies": {"005930": "삼성전자"},
                "enable_email_alerts": True
            }
        }