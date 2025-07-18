from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DartReportType(str, Enum):
    """DART 보고서 유형"""
    A = "A"  # 정기보고서
    B = "B"  # 주요사항보고서
    C = "C"  # 발행공시서류
    D = "D"  # 지분공시서류
    E = "E"  # 기타공시서류
    F = "F"  # 외부감사관련
    G = "G"  # 펀드공시서류
    H = "H"  # 자산유동화
    I = "I"  # 거래소공시서류
    J = "J"  # 공정위공시서류


class DartDisclosure(BaseModel):
    """DART 공시 데이터 모델"""
    rcept_no: str = Field(..., description="접수번호")
    corp_cls: str = Field(..., description="법인구분")
    corp_code: str = Field(..., description="고유번호")
    corp_name: str = Field(..., description="회사명")
    report_nm: str = Field(..., description="보고서명")
    rcept_dt: str = Field(..., description="접수일자")
    flr_nm: str = Field(..., description="공시대상회사의 명칭")
    rm: Optional[str] = Field(None, description="비고")
    
    # 추가 정보
    stock_code: Optional[str] = Field(None, description="주식코드")
    matched_keywords: List[str] = Field(default_factory=list, description="매칭된 키워드")
    priority_score: int = Field(0, description="우선순위 점수")
    dart_url: str = Field("", description="DART 상세 URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DartDisclosureResponse(BaseModel):
    """DART API 응답 모델"""
    status: str = Field(..., description="응답상태")
    message: str = Field(..., description="응답메시지")
    page_no: int = Field(..., description="페이지번호")
    page_count: int = Field(..., description="페이지별 건수")
    total_count: int = Field(..., description="총 건수")
    total_page: int = Field(..., description="총 페이지 수")
    list: List[DartDisclosure] = Field(default_factory=list, description="공시목록")


class DartKeyword(BaseModel):
    """DART 키워드 모델"""
    keyword: str = Field(..., description="키워드")
    weight: float = Field(1.0, description="가중치")
    category: str = Field("general", description="카테고리")
    is_active: bool = Field(True, description="활성화 여부")


class DartCompany(BaseModel):
    """DART 관심기업 모델"""
    stock_code: str = Field(..., description="주식코드")
    corp_code: str = Field(..., description="고유번호")
    corp_name: str = Field(..., description="회사명")
    is_active: bool = Field(True, description="모니터링 활성화")
    last_checked: Optional[datetime] = Field(None, description="마지막 체크 시간")


class DartMonitoringSettings(BaseModel):
    """DART 모니터링 설정 모델"""
    check_interval: int = Field(1800, description="체크 주기(초)")
    keywords: List[DartKeyword] = Field(default_factory=list, description="키워드 목록")
    companies: List[DartCompany] = Field(default_factory=list, description="관심기업 목록")
    email_enabled: bool = Field(True, description="이메일 알림 활성화")
    websocket_enabled: bool = Field(True, description="WebSocket 알림 활성화")
    report_types: List[DartReportType] = Field(default_factory=list, description="모니터링 보고서 유형")


class DartAlert(BaseModel):
    """DART 알림 모델"""
    id: Optional[int] = Field(None, description="알림 ID")
    rcept_no: str = Field(..., description="접수번호")
    corp_name: str = Field(..., description="회사명")
    report_nm: str = Field(..., description="보고서명")
    matched_keywords: List[str] = Field(default_factory=list, description="매칭된 키워드")
    priority_score: int = Field(0, description="우선순위 점수")
    dart_url: str = Field("", description="DART URL")
    is_sent: bool = Field(False, description="발송 여부")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    sent_at: Optional[datetime] = Field(None, description="발송일시")


class DartStatistics(BaseModel):
    """DART 통계 모델"""
    total_disclosures: int = Field(0, description="총 공시 건수")
    matched_disclosures: int = Field(0, description="매칭된 공시 건수")
    sent_alerts: int = Field(0, description="발송된 알림 건수")
    companies_monitored: int = Field(0, description="모니터링 기업 수")
    keywords_count: int = Field(0, description="키워드 개수")
    last_check_time: Optional[datetime] = Field(None, description="마지막 체크 시간")
    next_check_time: Optional[datetime] = Field(None, description="다음 체크 시간")


class DartRequest(BaseModel):
    """DART API 요청 모델"""
    crtfc_key: str = Field(..., description="API 키")
    bgn_de: str = Field(..., description="시작일자")
    end_de: str = Field(..., description="종료일자")
    corp_cls: str = Field("Y", description="법인구분")
    sort: str = Field("date", description="정렬")
    sort_mth: str = Field("desc", description="정렬방법")
    page_no: int = Field(1, description="페이지번호")
    page_count: int = Field(100, description="페이지별 건수")


class DartProcessedIds(BaseModel):
    """처리된 DART 공시 ID 관리 모델"""
    processed_ids: List[str] = Field(default_factory=list, description="처리된 공시 ID 목록")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트 시간")
    total_processed: int = Field(0, description="총 처리 건수")
    
    def add_id(self, rcept_no: str):
        """새로운 공시 ID 추가"""
        if rcept_no not in self.processed_ids:
            self.processed_ids.append(rcept_no)
            self.total_processed += 1
            self.last_updated = datetime.now()
    
    def is_processed(self, rcept_no: str) -> bool:
        """공시 ID가 처리되었는지 확인"""
        return rcept_no in self.processed_ids
    
    def cleanup_old_ids(self, keep_count: int = 10000):
        """오래된 ID 정리 (메모리 관리)"""
        if len(self.processed_ids) > keep_count:
            self.processed_ids = self.processed_ids[-keep_count:]
            self.last_updated = datetime.now()


# 응답 모델들
class DartDisclosureListResponse(BaseModel):
    """공시 목록 응답 모델"""
    disclosures: List[DartDisclosure]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class DartKeywordResponse(BaseModel):
    """키워드 응답 모델"""
    keywords: List[DartKeyword]
    total_count: int


class DartCompanyResponse(BaseModel):
    """회사 응답 모델"""
    companies: List[DartCompany]
    total_count: int


class DartSettingsResponse(BaseModel):
    """설정 응답 모델"""
    settings: DartMonitoringSettings
    message: str = "설정이 성공적으로 조회되었습니다."


class DartAlertResponse(BaseModel):
    """알림 응답 모델"""
    alerts: List[DartAlert]
    total_count: int
    unread_count: int


class DartStatisticsResponse(BaseModel):
    """통계 응답 모델"""
    statistics: DartStatistics
    message: str = "통계가 성공적으로 조회되었습니다."