"""
DART 공시 모니터링 모듈
기존 dart_monitor.py의 핵심 로직을 웹 환경에 맞게 리팩토링
"""
import requests
import json
import re
import logging
import os
from datetime import datetime, date
from typing import List, Dict, Set, Optional
from filelock import FileLock

from .config import (
    DART_API_KEY,
    COMPANIES,
    KEYWORDS,
    IMPORTANT_SECTIONS,
    CONTEXT_WINDOW,
    PROCESSED_IDS_FILE,
    REQUEST_TIMEOUT,
    DART_API_URL
)
from .email_utils import send_dart_alert

# 로거 설정
logger = logging.getLogger(__name__)

class DartMonitor:
    """DART 공시 모니터링 클래스"""
    
    def __init__(self):
        self.processed_ids_file = PROCESSED_IDS_FILE
        self.lock_file = self.processed_ids_file + '.lock'
        
        # 데이터 디렉토리 생성
        os.makedirs(os.path.dirname(self.processed_ids_file), exist_ok=True)
    
    def get_processed_ids(self) -> Set[str]:
        """처리된 공시 ID 목록 가져오기"""
        try:
            if os.path.exists(self.processed_ids_file):
                with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                    return set(f.read().splitlines())
            return set()
        except Exception as e:
            logger.error(f"처리된 ID 목록 읽기 실패: {e}")
            return set()
    
    def save_processed_ids(self, processed_ids: Set[str]):
        """처리된 공시 ID 목록 저장"""
        try:
            # FileLock을 사용하여 동시 접근 방지
            with FileLock(self.lock_file):
                # 최대 저장 개수 제한 (최근 1000개만 유지)
                MAX_PROCESSED_IDS = 1000
                if len(processed_ids) > MAX_PROCESSED_IDS:
                    processed_ids = set(sorted(processed_ids, reverse=True)[:MAX_PROCESSED_IDS])
                    logger.info(f"처리된 ID 목록 정리: {MAX_PROCESSED_IDS}개만 유지")
                
                with open(self.processed_ids_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(processed_ids))
                    
        except Exception as e:
            logger.error(f"처리된 ID 목록 저장 실패: {e}")
    
    def calculate_priority_score(self, report_name: str, company_name: str) -> int:
        """공시의 우선순위 점수 계산"""
        score = 0
        
        # 기본 점수
        score += 10
        
        # 중요 키워드 점수
        high_priority_keywords = ["합병", "분할", "매각", "취득", "투자", "지분", "출자"]
        medium_priority_keywords = ["유상증자", "무상증자", "배당", "자기주식"]
        
        for keyword in high_priority_keywords:
            if keyword in report_name:
                score += 30
                
        for keyword in medium_priority_keywords:
            if keyword in report_name:
                score += 20
        
        # 일반 키워드 점수
        for keyword in KEYWORDS:
            if keyword in report_name:
                score += 10
        
        # 중요 기업 가산점
        major_companies = ["삼성전자", "SK하이닉스", "네이버", "카카오"]
        if company_name in major_companies:
            score += 20
            
        return min(score, 100)  # 최대 100점
    
    def analyze_disclosure_content(self, content: str) -> List[tuple]:
        """공시 내용 분석하여 키워드와 문맥 추출"""
        found_keywords = []
        
        # 중요 섹션 찾기
        important_content = ""
        for section in IMPORTANT_SECTIONS:
            pattern = f"{section}[：:](.*?)(?=\n\n|$)"
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                important_content += match.group(1).strip() + "\n\n"
        
        # 키워드 분석
        for keyword in KEYWORDS:
            if keyword in important_content:
                # 키워드 주변 문맥 추출
                start = max(0, important_content.find(keyword) - CONTEXT_WINDOW)
                end = min(len(important_content), important_content.find(keyword) + len(keyword) + CONTEXT_WINDOW)
                context = important_content[start:end]
                found_keywords.append((keyword, context))
        
        return found_keywords
    
    def fetch_disclosures_for_date(self, target_date: str) -> List[Dict]:
        """특정 날짜의 공시 목록 조회"""
        all_disclosures = []
        
        # 관심 기업별로 조회
        for corp_code in COMPANIES.keys():
            try:
                params = {
                    'crtfc_key': DART_API_KEY,
                    'corp_code': corp_code,
                    'bgn_de': target_date,
                    'end_de': target_date,
                    'page_no': '1',
                    'page_count': '100'
                }
                
                response = requests.get(
                    f"{DART_API_URL}/list.json",
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == '000' and 'list' in data:
                        all_disclosures.extend(data['list'])
                        logger.debug(f"{COMPANIES[corp_code]} 공시 {len(data['list'])}건 조회")
                else:
                    logger.warning(f"DART API 응답 오류: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"공시 조회 실패 ({COMPANIES[corp_code]}): {e}")
                continue
        
        return all_disclosures
    
    def filter_disclosures(self, disclosures: List[Dict]) -> List[Dict]:
        """공시 필터링 (키워드 기반)"""
        filtered = []
        
        # 제외할 키워드
        exclude_keywords = ["기업설명회", "IR개최", "설명회개최", "IR)", "(IR)"]
        
        for disclosure in disclosures:
            report_name = disclosure.get('report_nm', '')
            
            # 제외 키워드 확인
            if any(exclude_kw in report_name for exclude_kw in exclude_keywords):
                logger.debug(f"제외된 공시: {report_name}")
                continue
            
            # 관심 키워드 확인
            should_include = False
            for keyword in KEYWORDS:
                if keyword in report_name:
                    should_include = True
                    break
            
            if should_include:
                filtered.append(disclosure)
            else:
                logger.debug(f"무시된 공시: {report_name}")
        
        return filtered
    
    def check_new_disclosures(self, target_date: Optional[str] = None) -> List[Dict]:
        """
        새로운 공시 확인 및 반환
        
        Args:
            target_date: 조회할 날짜 (YYYYMMDD), None이면 오늘
            
        Returns:
            새로운 공시 목록 [{'company': str, 'title': str, 'link': str, 'time': str, 'priority': int, 'keywords': list}, ...]
        """
        if target_date is None:
            target_date = date.today().strftime("%Y%m%d")
        
        logger.info(f"DART 공시 확인 시작: {target_date}")
        
        # 처리된 ID 목록 가져오기
        processed_ids = self.get_processed_ids()
        
        # 공시 목록 조회
        disclosures = self.fetch_disclosures_for_date(target_date)
        logger.info(f"전체 공시 {len(disclosures)}건 조회")
        
        # 공시 필터링
        filtered_disclosures = self.filter_disclosures(disclosures)
        logger.info(f"필터링 후 공시 {len(filtered_disclosures)}건")
        
        # 새로운 공시 식별
        new_disclosures = []
        new_processed_ids = processed_ids.copy()
        
        for disclosure in filtered_disclosures:
            rcept_no = str(disclosure['rcept_no'])
            
            if rcept_no not in processed_ids:
                corp_code = disclosure['corp_code']
                company_name = COMPANIES.get(corp_code, disclosure.get('corp_name', '알 수 없음'))
                report_name = disclosure['report_nm']
                
                # 우선순위 점수 계산
                priority_score = self.calculate_priority_score(report_name, company_name)
                
                # 매칭된 키워드 찾기
                matched_keywords = []
                for keyword in KEYWORDS:
                    if keyword in report_name:
                        matched_keywords.append(keyword)
                
                # DART URL 생성
                dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                
                new_disclosure = {
                    'company': company_name,
                    'title': report_name,
                    'link': dart_url,
                    'time': disclosure['rcept_dt'],
                    'priority': priority_score,
                    'keywords': matched_keywords,
                    'rcept_no': rcept_no
                }
                
                new_disclosures.append(new_disclosure)
                new_processed_ids.add(rcept_no)
                
                logger.info(f"새로운 공시 발견: {company_name} - {report_name} (우선순위: {priority_score})")
        
        # 처리된 ID 목록 업데이트
        if new_processed_ids != processed_ids:
            self.save_processed_ids(new_processed_ids)
        
        logger.info(f"새로운 공시 {len(new_disclosures)}건 발견")
        return new_disclosures
    
    def send_notifications(self, new_disclosures: List[Dict]) -> int:
        """
        새로운 공시에 대한 이메일 알림 발송
        
        Args:
            new_disclosures: 새로운 공시 목록
            
        Returns:
            발송 성공한 이메일 수
        """
        sent_count = 0
        
        for disclosure in new_disclosures:
            try:
                success = send_dart_alert(
                    corp_name=disclosure['company'],
                    report_name=disclosure['title'],
                    keywords=disclosure['keywords'],
                    priority_score=disclosure['priority'],
                    dart_url=disclosure['link']
                )
                
                if success:
                    sent_count += 1
                    logger.info(f"알림 발송 성공: {disclosure['company']} - {disclosure['title']}")
                else:
                    logger.error(f"알림 발송 실패: {disclosure['company']} - {disclosure['title']}")
                    
            except Exception as e:
                logger.error(f"알림 발송 중 오류: {e}")
        
        return sent_count

# 전역 인스턴스
dart_monitor = DartMonitor()

def check_new_disclosures(target_date: Optional[str] = None) -> List[Dict]:
    """새로운 공시 확인 (편의 함수)"""
    return dart_monitor.check_new_disclosures(target_date)

def send_dart_notifications(new_disclosures: List[Dict]) -> int:
    """공시 알림 발송 (편의 함수)"""
    return dart_monitor.send_notifications(new_disclosures)