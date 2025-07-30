"""
DART 공시 모니터링 모듈
기존 dart_monitor.py의 핵심 로직을 웹 환경에 맞게 리팩토링
"""
import requests
import json
import re
import logging
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Set, Optional
from filelock import FileLock

from .config import (
    DART_API_KEY,
    COMPANIES,
    KEYWORDS,
    KEYWORD_AND_CONDITIONS,
    KEYWORD_FILTER_MODE,
    IMPORTANT_SECTIONS,
    CONTEXT_WINDOW,
    PROCESSED_IDS_FILE,
    REQUEST_TIMEOUT,
    DART_API_URL,
    DART_COMPANIES_FILE,
    DART_KEYWORDS_FILE,
    DEFAULT_DART_KEYWORDS
)
from .email_utils import send_dart_alert

# 개선된 로깅 시스템 적용
from .logger_utils import get_logger, performance_monitor, log_exception

# 로거 설정
logger = get_logger('dart')

class DartMonitor:
    """DART 공시 모니터링 클래스"""
    
    def __init__(self):
        self.processed_ids_file = PROCESSED_IDS_FILE
        self.lock_file = self.processed_ids_file + '.lock'
        
        # 데이터 디렉토리 생성
        os.makedirs(os.path.dirname(self.processed_ids_file), exist_ok=True)
        
        # DART 데이터 파일 경로
        self.companies_file = DART_COMPANIES_FILE
        self.keywords_file = DART_KEYWORDS_FILE
        self.companies_lock = self.companies_file + '.lock'
        self.keywords_lock = self.keywords_file + '.lock'
        
        # 웹 연동용 DART 알림 파일 경로
        self.dart_alerts_file = os.path.join(os.path.dirname(self.processed_ids_file), 'dart_alerts.json')
        self.dart_alerts_lock = self.dart_alerts_file + '.lock'
    
    def validate_date_format(self, date_str: str) -> bool:
        """날짜 형식 검증 (YYYYMMDD)"""
        try:
            if not date_str or len(date_str) != 8:
                return False
            
            # 숫자인지 확인
            if not date_str.isdigit():
                return False
            
            # 실제 날짜인지 확인
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # 기본적인 범위 확인
            if not (1900 <= year <= 2100):
                return False
            if not (1 <= month <= 12):
                return False
            if not (1 <= day <= 31):
                return False
            
            # datetime으로 실제 날짜 검증
            datetime.strptime(date_str, "%Y%m%d")
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"날짜 형식 검증 실패: {date_str} - {e}")
            return False
    
    def get_default_date_range(self) -> tuple[str, str]:
        """기본 날짜 범위 반환 (최근 12개월)"""
        today = date.today()
        twelve_months_ago = today - timedelta(days=365)
        
        return (
            twelve_months_ago.strftime("%Y%m%d"),
            today.strftime("%Y%m%d")
        )
    
    def normalize_date_input(self, target_date: Optional[str] = None) -> str:
        """날짜 입력 정규화 및 검증"""
        if target_date is None:
            # 기본값: 오늘 날짜
            return date.today().strftime("%Y%m%d")
        
        # 날짜 형식 검증
        if not self.validate_date_format(target_date):
            logger.warning(f"잘못된 날짜 형식: {target_date}, 오늘 날짜로 대체")
            return date.today().strftime("%Y%m%d")
        
        return target_date
    
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
    
    def load_dart_companies(self) -> Dict[str, str]:
        """DART 모니터링 대상 기업 목록 로드"""
        try:
            if os.path.exists(self.companies_file):
                with FileLock(self.companies_lock):
                    with open(self.companies_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        companies = data.get('companies', {})
                        logger.debug(f"DART 기업 목록 로드 성공: {len(companies)}개 기업")
                        return companies
            else:
                # 파일이 없으면 기본 데이터로 생성
                logger.info("DART 기업 파일이 없어 기본 데이터로 생성")
                default_companies = COMPANIES.copy()
                self.save_dart_companies(default_companies)
                return default_companies
        except Exception as e:
            logger.error(f"DART 기업 목록 로드 실패: {e}")
            # 오류 시 config.py의 기본값 반환
            return COMPANIES.copy()
    
    def save_dart_companies(self, companies: Dict[str, str]) -> bool:
        """DART 모니터링 대상 기업 목록 저장"""
        try:
            with FileLock(self.companies_lock):
                data = {
                    "companies": companies,
                    "metadata": {
                        "version": "1.0",
                        "description": "DART 모니터링 대상 기업 목록",
                        "total_companies": len(companies),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                }
                
                with open(self.companies_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"DART 기업 목록 저장 성공: {len(companies)}개 기업")
                return True
                
        except Exception as e:
            logger.error(f"DART 기업 목록 저장 실패: {e}")
            return False
    
    def load_dart_keywords(self) -> List[str]:
        """DART 공시 필터링 키워드 목록 로드"""
        try:
            if os.path.exists(self.keywords_file):
                with FileLock(self.keywords_lock):
                    with open(self.keywords_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        keywords = data.get('keywords', [])
                        logger.debug(f"DART 키워드 목록 로드 성공: {len(keywords)}개 키워드")
                        return keywords
            else:
                # 파일이 없으면 기본 데이터로 생성
                logger.info("DART 키워드 파일이 없어 기본 데이터로 생성")
                default_keywords = DEFAULT_DART_KEYWORDS.copy()
                self.save_dart_keywords(default_keywords)
                return default_keywords
        except Exception as e:
            logger.error(f"DART 키워드 목록 로드 실패: {e}")
            # 오류 시 config.py의 기본값 반환
            return KEYWORDS.copy()
    
    def save_dart_keywords(self, keywords: List[str]) -> bool:
        """DART 공시 필터링 키워드 목록 저장"""
        try:
            with FileLock(self.keywords_lock):
                # 중복 제거 및 정렬
                unique_keywords = sorted(list(set(keywords)))
                
                # 우선순위 키워드 식별
                priority_keywords = [kw for kw in DEFAULT_DART_KEYWORDS if kw in unique_keywords]
                
                data = {
                    "keywords": unique_keywords,
                    "metadata": {
                        "version": "1.0",
                        "description": "DART 공시 필터링용 키워드 목록",
                        "total_keywords": len(unique_keywords),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "filter_mode": "OR",
                        "priority_keywords": priority_keywords
                    }
                }
                
                with open(self.keywords_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"DART 키워드 목록 저장 성공: {len(unique_keywords)}개 키워드")
                return True
                
        except Exception as e:
            logger.error(f"DART 키워드 목록 저장 실패: {e}")
            return False
    
    def add_dart_company(self, company_code: str, company_name: str) -> bool:
        """DART 모니터링 대상 기업 추가"""
        try:
            companies = self.load_dart_companies()
            
            # 중복 확인
            if company_code in companies:
                logger.warning(f"기업 코드 중복: {company_code}")
                return False
            
            companies[company_code] = company_name
            success = self.save_dart_companies(companies)
            
            if success:
                logger.info(f"DART 기업 추가 성공: {company_code} - {company_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"DART 기업 추가 실패: {e}")
            return False
    
    def remove_dart_company(self, company_code: str) -> bool:
        """DART 모니터링 대상 기업 삭제"""
        try:
            companies = self.load_dart_companies()
            
            # 존재 확인
            if company_code not in companies:
                logger.warning(f"삭제할 기업 코드가 없음: {company_code}")
                return False
            
            company_name = companies[company_code]
            del companies[company_code]
            success = self.save_dart_companies(companies)
            
            if success:
                logger.info(f"DART 기업 삭제 성공: {company_code} - {company_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"DART 기업 삭제 실패: {e}")
            return False
    
    def add_dart_keyword(self, keyword: str) -> bool:
        """DART 필터링 키워드 추가"""
        try:
            keyword = keyword.strip()
            if not keyword:
                logger.warning("빈 키워드는 추가할 수 없습니다")
                return False
            
            keywords = self.load_dart_keywords()
            
            # 중복 확인
            if keyword in keywords:
                logger.warning(f"키워드 중복: {keyword}")
                return False
            
            keywords.append(keyword)
            success = self.save_dart_keywords(keywords)
            
            if success:
                logger.info(f"DART 키워드 추가 성공: {keyword}")
            
            return success
            
        except Exception as e:
            logger.error(f"DART 키워드 추가 실패: {e}")
            return False
    
    def remove_dart_keyword(self, keyword: str) -> bool:
        """DART 필터링 키워드 삭제"""
        try:
            keywords = self.load_dart_keywords()
            
            # 존재 확인
            if keyword not in keywords:
                logger.warning(f"삭제할 키워드가 없음: {keyword}")
                return False
            
            keywords.remove(keyword)
            success = self.save_dart_keywords(keywords)
            
            if success:
                logger.info(f"DART 키워드 삭제 성공: {keyword}")
            
            return success
            
        except Exception as e:
            logger.error(f"DART 키워드 삭제 실패: {e}")
            return False
    
    def get_recent_logs(self, hours: int = 24) -> List[Dict]:
        """최근 지정된 시간 내의 DART 로그 반환"""
        try:
            import os
            from .config import LOGS_DIR
            
            log_file = os.path.join(LOGS_DIR, 'dart_monitor.log')
            
            if not os.path.exists(log_file):
                logger.warning(f"로그 파일이 없습니다: {log_file}")
                return []
            
            # 시간 기준 계산
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_logs = []
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # 최근 100줄만 처리 (성능 최적화)
                for line in lines[-100:]:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 로그 시간 파싱 시도
                    try:
                        # 로그 형식: YYYY-MM-DD HH:MM:SS - ... 
                        if ' - ' in line:
                            time_part = line.split(' - ')[0]
                            log_time = datetime.strptime(time_part, '%Y-%m-%d %H:%M:%S')
                            
                            if log_time >= cutoff_time:
                                recent_logs.append({
                                    'timestamp': log_time.isoformat(),
                                    'message': line,
                                    'level': self._extract_log_level(line)
                                })
                    except ValueError:
                        # 시간 파싱 실패 시 그냥 추가
                        recent_logs.append({
                            'timestamp': datetime.now().isoformat(),
                            'message': line,
                            'level': 'INFO'
                        })
                        
            except Exception as e:
                logger.error(f"로그 파일 읽기 실패: {e}")
                return []
            
            # 시간순 정렬 (최신순)
            recent_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.debug(f"최근 {hours}시간 DART 로그 {len(recent_logs)}건 조회")
            return recent_logs
            
        except Exception as e:
            logger.error(f"최근 로그 조회 실패: {e}")
            return []
    
    def _extract_log_level(self, log_line: str) -> str:
        """로그 라인에서 로그 레벨 추출"""
        if ' - ERROR - ' in log_line:
            return 'ERROR'
        elif ' - WARNING - ' in log_line:
            return 'WARNING'
        elif ' - DEBUG - ' in log_line:
            return 'DEBUG'
        else:
            return 'INFO'
    
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
        # 날짜 형식 검증
        if not self.validate_date_format(target_date):
            logger.error(f"잘못된 날짜 형식: {target_date}")
            return []
        
        all_disclosures = []
        failed_companies = []
        
        logger.info(f"DART API 공시 조회 시작: {target_date}")
        
        # 관심 기업별로 조회
        for corp_code in COMPANIES.keys():
            company_name = COMPANIES[corp_code]
            
            try:
                params = {
                    'crtfc_key': DART_API_KEY,
                    'corp_code': corp_code,
                    'bgn_de': target_date,
                    'end_de': target_date,
                    'page_no': '1',
                    'page_count': '100'
                }
                
                logger.debug(f"DART API 요청: {company_name} ({corp_code})")
                
                # 재시도 로직이 포함된 API 요청
                data = self.make_api_request_with_retry(
                    f"{DART_API_URL}/list.json",
                    params
                )
                
                # API 요청 실패 시 다음 기업으로 이동
                if data is None:
                    logger.error(f"DART API 요청 실패: {company_name}")
                    failed_companies.append(company_name)
                    continue
                
                # 공시 데이터 처리
                if 'list' in data and data['list']:
                    disclosures = data['list']
                    
                    # 데이터 표준화
                    standardized_disclosures = []
                    for disclosure in disclosures:
                        standardized = self.standardize_disclosure_data(disclosure, corp_code)
                        if standardized:
                            standardized_disclosures.append(standardized)
                    
                    all_disclosures.extend(standardized_disclosures)
                    logger.debug(f"{company_name} 공시 {len(standardized_disclosures)}건 조회 성공")
                else:
                    logger.debug(f"{company_name} 공시 없음")
                    
            except requests.exceptions.Timeout:
                logger.error(f"DART API 타임아웃 ({company_name}): {REQUEST_TIMEOUT}초 초과")
                failed_companies.append(company_name)
            except requests.exceptions.ConnectionError:
                logger.error(f"DART API 연결 실패 ({company_name}): 네트워크 오류")
                failed_companies.append(company_name)
            except Exception as e:
                logger.error(f"공시 조회 예상치 못한 오류 ({company_name}): {type(e).__name__} - {e}")
                failed_companies.append(company_name)
        
        # 결과 요약 로깅
        success_count = len(COMPANIES) - len(failed_companies)
        logger.info(f"DART API 조회 완료: 성공 {success_count}/{len(COMPANIES)}개 기업, 총 {len(all_disclosures)}건 조회")
        
        if failed_companies:
            logger.warning(f"조회 실패 기업: {', '.join(failed_companies)}")
        
        return all_disclosures
    
    def standardize_disclosure_data(self, disclosure: Dict, corp_code: str) -> Optional[Dict]:
        """공시 데이터 표준화"""
        try:
            # 필수 필드 확인
            required_fields = ['rcept_no', 'report_nm', 'rcept_dt']
            for field in required_fields:
                if field not in disclosure or not disclosure[field]:
                    logger.warning(f"필수 필드 누락: {field} in {disclosure}")
                    return None
            
            # 표준화된 형태로 변환
            standardized = {
                'rcept_no': str(disclosure['rcept_no']).strip(),
                'corp_code': corp_code,
                'corp_name': COMPANIES.get(corp_code, disclosure.get('corp_name', '알 수 없음')),
                'report_nm': disclosure['report_nm'].strip(),
                'rcept_dt': disclosure['rcept_dt'].strip(),
                'flr_nm': disclosure.get('flr_nm', '').strip(),
                'rm': disclosure.get('rm', '').strip()
            }
            
            # 날짜 형식 검증
            if not self.validate_date_format(standardized['rcept_dt']):
                logger.warning(f"잘못된 공시 날짜: {standardized['rcept_dt']}")
                return None
            
            return standardized
            
        except Exception as e:
            logger.error(f"공시 데이터 표준화 실패: {e}")
            return None
    
    def filter_disclosures(self, disclosures: List[Dict]) -> List[Dict]:
        """공시 필터링 (키워드 기반 - AND/OR 조건 지원)"""
        filtered = []
        
        # 제외할 키워드
        exclude_keywords = ["기업설명회", "IR개최", "설명회개최", "IR)", "(IR)"]
        
        for disclosure in disclosures:
            report_name = disclosure.get('report_nm', '')
            
            # 제외 키워드 확인
            if any(exclude_kw in report_name for exclude_kw in exclude_keywords):
                logger.debug(f"제외된 공시: {report_name}")
                continue
            
            # 키워드 필터링 모드에 따른 처리
            should_include = self._evaluate_keyword_conditions(report_name)
            
            if should_include:
                filtered.append(disclosure)
                logger.debug(f"포함된 공시: {report_name}")
            else:
                logger.debug(f"무시된 공시: {report_name}")
        
        return filtered
    
    def _evaluate_keyword_conditions(self, report_name: str) -> bool:
        """키워드 조건 평가 (AND/OR 로직)"""
        
        if KEYWORD_FILTER_MODE == 'AND':
            # 모든 키워드가 포함되어야 함
            return all(keyword in report_name for keyword in KEYWORDS)
        
        elif KEYWORD_FILTER_MODE == 'MIXED':
            # AND 조건과 OR 조건을 모두 확인
            
            # 1. AND 조건 그룹 확인
            and_condition_met = False
            if KEYWORD_AND_CONDITIONS:
                for and_group in KEYWORD_AND_CONDITIONS:
                    if all(keyword in report_name for keyword in and_group):
                        and_condition_met = True
                        logger.debug(f"AND 조건 만족: {and_group} in '{report_name}'")
                        break
            
            # 2. 기본 OR 조건 확인
            or_condition_met = any(keyword in report_name for keyword in KEYWORDS)
            
            # AND 조건이 있으면 AND 조건 우선, 없으면 OR 조건
            if KEYWORD_AND_CONDITIONS:
                return and_condition_met
            else:
                return or_condition_met
                
        else:  # 기본값: 'OR'
            # 키워드 중 하나라도 포함되면 포함
            return any(keyword in report_name for keyword in KEYWORDS)
    
    def get_matched_keywords(self, report_name: str) -> Dict:
        """공시에서 매칭된 키워드 정보 반환"""
        matched_info = {
            'or_keywords': [],
            'and_groups': [],
            'filter_mode': KEYWORD_FILTER_MODE
        }
        
        # OR 키워드 매칭
        for keyword in KEYWORDS:
            if keyword in report_name:
                matched_info['or_keywords'].append(keyword)
        
        # AND 그룹 매칭
        for and_group in KEYWORD_AND_CONDITIONS:
            if all(keyword in report_name for keyword in and_group):
                matched_info['and_groups'].append(and_group)
        
        return matched_info
    
    def validate_dart_api_key(self) -> bool:
        """DART API 키 유효성 검증"""
        try:
            if not DART_API_KEY or DART_API_KEY.strip() == '':
                logger.error("DART API 키가 설정되지 않았습니다")
                return False
            
            if len(DART_API_KEY) != 40:  # DART API 키는 40자리
                logger.error(f"DART API 키 길이가 올바르지 않습니다: {len(DART_API_KEY)}자리")
                return False
            
            # 간단한 API 키 형식 검증 (영숫자)
            if not DART_API_KEY.isalnum():
                logger.error("DART API 키 형식이 올바르지 않습니다: 영숫자만 허용")
                return False
            
            logger.debug("DART API 키 검증 성공")
            return True
            
        except Exception as e:
            logger.error(f"DART API 키 검증 중 오류: {e}")
            return False
    
    def check_dart_api_health(self) -> Dict[str, any]:
        """
        DART API 연동 상태 헬스체크
        
        Returns:
            Dict: {
                'status': str,  # 'healthy', 'error', 'failed'
                'response_time': float,  # 응답 시간(초)
                'api_key_valid': bool,  # API 키 유효성
                'last_check': str,  # 마지막 체크 시간
                'error_message': str,  # 에러 메시지 (있는 경우)
                'test_api_url': str  # 테스트에 사용된 URL
            }
        """
        health_result = {
            'status': 'unknown',
            'response_time': 0.0,
            'api_key_valid': False,
            'last_check': datetime.now().isoformat(),
            'error_message': '',
            'test_api_url': f"{DART_API_URL}/list.json"
        }
        
        try:
            # 1. API 키 유효성 검증
            health_result['api_key_valid'] = self.validate_dart_api_key()
            
            if not health_result['api_key_valid']:
                health_result['status'] = 'failed'
                health_result['error_message'] = 'DART API 키가 유효하지 않습니다'
                return health_result
            
            # 2. 테스트 API 호출 (간단한 요청)
            test_params = {
                'crtfc_key': DART_API_KEY,
                'corp_code': '00126380',  # 삼성전자 코드
                'bgn_de': datetime.now().strftime('%Y%m%d'),
                'end_de': datetime.now().strftime('%Y%m%d'),
                'page_no': '1',
                'page_count': '1'  # 최소한의 데이터만 요청
            }
            
            import time
            start_time = time.time()
            
            # API 요청 (단일 시도, 재시도 없이)
            response = requests.get(
                health_result['test_api_url'], 
                params=test_params, 
                timeout=REQUEST_TIMEOUT
            )
            
            end_time = time.time()
            health_result['response_time'] = round(end_time - start_time, 3)
            
            # 3. HTTP 상태 코드 확인
            if response.status_code != 200:
                health_result['status'] = 'error'
                health_result['error_message'] = f'HTTP 오류: {response.status_code}'
                return health_result
            
            # 4. JSON 파싱 확인
            try:
                data = response.json()
            except ValueError as e:
                health_result['status'] = 'error'
                health_result['error_message'] = f'JSON 파싱 실패: {str(e)}'
                return health_result
            
            # 5. DART API 응답 상태 확인
            api_status = data.get('status', '')
            if api_status == '000':  # 성공
                health_result['status'] = 'healthy'
                logger.debug(f"DART API 헬스체크 성공: {health_result['response_time']}초")
            elif api_status == '013':  # 데이터 없음 (정상 상황)
                health_result['status'] = 'healthy'
                logger.debug("DART API 상태 정상 (데이터 없음)")
            else:
                health_result['status'] = 'error'
                health_result['error_message'] = f'DART API 오류: {api_status} - {data.get("message", "Unknown error")}'
            
        except requests.exceptions.Timeout:
            health_result['status'] = 'failed'
            health_result['error_message'] = f'API 요청 타임아웃: {REQUEST_TIMEOUT}초 초과'
        except requests.exceptions.ConnectionError:
            health_result['status'] = 'failed'
            health_result['error_message'] = '네트워크 연결 오류: DART 서버에 연결할 수 없습니다'
        except Exception as e:
            health_result['status'] = 'failed'
            health_result['error_message'] = f'예상치 못한 오류: {type(e).__name__} - {str(e)}'
        
        # 로깅
        if health_result['status'] == 'healthy':
            logger.info(f"DART API 헬스체크 성공: {health_result['response_time']}초")
        else:
            logger.error(f"DART API 헬스체크 실패: {health_result['error_message']}")
        
        return health_result
    
    def get_dart_api_status_summary(self) -> Dict[str, any]:
        """
        DART API 상태 요약 정보 반환
        
        Returns:
            Dict: API 상태, 설정 정보, 통계 등
        """
        try:
            # 헬스체크 수행
            health_status = self.check_dart_api_health()
            
            # 기본 설정 정보
            config_info = {
                'api_url': DART_API_URL,
                'request_timeout': REQUEST_TIMEOUT,
                'monitored_companies_count': len(COMPANIES),
                'keywords_count': len(KEYWORDS),
                'api_key_configured': bool(DART_API_KEY and DART_API_KEY.strip()),
                'api_key_length': len(DART_API_KEY) if DART_API_KEY else 0
            }
            
            # 모니터링 대상 기업 목록
            companies_list = []
            for corp_code, company_name in COMPANIES.items():
                companies_list.append({
                    'corp_code': corp_code,
                    'company_name': company_name
                })
            
            # 키워드 목록
            keywords_info = {
                'or_keywords': KEYWORDS,
                'and_conditions': KEYWORD_AND_CONDITIONS,
                'filter_mode': KEYWORD_FILTER_MODE
            }
            
            # 종합 상태 요약
            summary = {
                'health_status': health_status,
                'config_info': config_info,
                'companies': companies_list,
                'keywords': keywords_info,
                'last_updated': datetime.now().isoformat(),
                'system_ready': (
                    health_status['status'] == 'healthy' and
                    config_info['api_key_configured'] and
                    config_info['monitored_companies_count'] > 0
                )
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"DART API 상태 요약 생성 실패: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat(),
                'system_ready': False
            }
    
    def test_dart_connectivity(self, company_count: int = 3) -> Dict[str, any]:
        """
        DART API 연결성 테스트 (여러 기업으로 테스트)
        
        Args:
            company_count (int): 테스트할 기업 수 (기본 3개)
            
        Returns:
            Dict: 테스트 결과 상세 정보
        """
        test_result = {
            'test_started': datetime.now().isoformat(),
            'total_companies_tested': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'test_details': [],
            'overall_status': 'unknown'
        }
        
        try:
            # 테스트할 기업 선택 (첫 번째부터 company_count개)
            test_companies = list(COMPANIES.items())[:company_count]
            test_result['total_companies_tested'] = len(test_companies)
            
            total_response_time = 0.0
            
            for corp_code, company_name in test_companies:
                company_test = {
                    'corp_code': corp_code,
                    'company_name': company_name,
                    'status': 'unknown',
                    'response_time': 0.0,
                    'error_message': ''
                }
                
                try:
                    # 테스트 파라미터
                    test_params = {
                        'crtfc_key': DART_API_KEY,
                        'corp_code': corp_code,
                        'bgn_de': datetime.now().strftime('%Y%m%d'),
                        'end_de': datetime.now().strftime('%Y%m%d'),
                        'page_no': '1',
                        'page_count': '1'
                    }
                    
                    import time
                    start_time = time.time()
                    
                    # API 요청
                    response = requests.get(
                        f"{DART_API_URL}/list.json",
                        params=test_params,
                        timeout=REQUEST_TIMEOUT
                    )
                    
                    end_time = time.time()
                    company_test['response_time'] = round(end_time - start_time, 3)
                    total_response_time += company_test['response_time']
                    
                    # 응답 검증
                    if response.status_code == 200:
                        data = response.json()
                        api_status = data.get('status', '')
                        
                        if api_status in ['000', '013']:  # 성공 또는 데이터 없음
                            company_test['status'] = 'success'
                            test_result['successful_requests'] += 1
                        else:
                            company_test['status'] = 'api_error'
                            company_test['error_message'] = f"API 오류: {api_status}"
                            test_result['failed_requests'] += 1
                    else:
                        company_test['status'] = 'http_error'
                        company_test['error_message'] = f"HTTP 오류: {response.status_code}"
                        test_result['failed_requests'] += 1
                        
                except requests.exceptions.Timeout:
                    company_test['status'] = 'timeout'
                    company_test['error_message'] = f'타임아웃: {REQUEST_TIMEOUT}초 초과'
                    test_result['failed_requests'] += 1
                except requests.exceptions.ConnectionError:
                    company_test['status'] = 'connection_error'
                    company_test['error_message'] = '연결 오류'
                    test_result['failed_requests'] += 1
                except Exception as e:
                    company_test['status'] = 'unknown_error'
                    company_test['error_message'] = str(e)
                    test_result['failed_requests'] += 1
                
                test_result['test_details'].append(company_test)
                
                # 요청 간 짧은 대기 (API 레이트 리미트 방지)
                import time
                time.sleep(0.5)
            
            # 평균 응답 시간 계산
            if test_result['successful_requests'] > 0:
                test_result['average_response_time'] = round(
                    total_response_time / len(test_companies), 3
                )
            
            # 전체 상태 결정
            success_rate = test_result['successful_requests'] / test_result['total_companies_tested']
            if success_rate >= 0.8:  # 80% 이상 성공
                test_result['overall_status'] = 'excellent'
            elif success_rate >= 0.5:  # 50% 이상 성공
                test_result['overall_status'] = 'good'
            elif success_rate > 0:  # 일부 성공
                test_result['overall_status'] = 'poor'
            else:  # 전체 실패
                test_result['overall_status'] = 'failed'
            
            test_result['test_completed'] = datetime.now().isoformat()
            
            logger.info(f"DART API 연결성 테스트 완료: {test_result['successful_requests']}/{test_result['total_companies_tested']} 성공")
            
            return test_result
            
        except Exception as e:
            logger.error(f"DART API 연결성 테스트 실패: {e}")
            test_result['overall_status'] = 'error'
            test_result['error'] = str(e)
            test_result['test_completed'] = datetime.now().isoformat()
            return test_result
    
    def make_api_request_with_retry(self, url: str, params: dict, max_retries: int = 3) -> Optional[dict]:
        """재시도 로직이 포함된 API 요청"""
        for attempt in range(max_retries):
            try:
                logger.debug(f"DART API 요청 시도 {attempt + 1}/{max_retries}: {params.get('corp_code', 'Unknown')}")
                
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                # HTTP 상태 코드 확인
                if response.status_code != 200:
                    logger.warning(f"HTTP 오류 {response.status_code} (시도 {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:  # 마지막 시도
                        return None
                    continue
                
                # JSON 파싱
                try:
                    data = response.json()
                    
                    # DART API 응답 상태 확인
                    if data.get('status') == '000':  # 성공
                        return data
                    else:
                        error_msg = data.get('message', '알 수 없는 오류')
                        logger.warning(f"DART API 오류: {data.get('status')} - {error_msg} (시도 {attempt + 1}/{max_retries})")
                        
                        # 일시적 오류가 아닌 경우 재시도하지 않음
                        if data.get('status') in ['010', '011', '012', '013']:  # 인증 관련 오류
                            logger.error(f"API 키 인증 오류로 재시도 중단: {data.get('status')}")
                            return None
                        
                        if attempt == max_retries - 1:  # 마지막 시도
                            return None
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API 요청 타임아웃 (시도 {attempt + 1}/{max_retries}): {REQUEST_TIMEOUT}초 초과")
                if attempt == max_retries - 1:
                    return None
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"API 연결 실패 (시도 {attempt + 1}/{max_retries}): 네트워크 오류")
                if attempt == max_retries - 1:
                    return None
                    
            except Exception as e:
                logger.error(f"예상치 못한 API 요청 오류 (시도 {attempt + 1}/{max_retries}): {type(e).__name__} - {e}")
                if attempt == max_retries - 1:
                    return None
            
            # 재시도 전 대기 (지수 백오프)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1초, 2초, 4초...
                logger.debug(f"{wait_time}초 후 재시도...")
                import time
                time.sleep(wait_time)
        
        return None
    
    def check_new_disclosures(self, target_date: Optional[str] = None) -> List[Dict]:
        """
        새로운 공시 확인 및 반환
        
        Args:
            target_date: 조회할 날짜 (YYYYMMDD), None이면 오늘
            
        Returns:
            새로운 공시 목록 [{'company': str, 'title': str, 'link': str, 'time': str, 'priority': int, 'keywords': list}, ...]
        """
        # 날짜 입력 정규화 및 검증
        target_date = self.normalize_date_input(target_date)
        
        logger.info(f"DART 공시 확인 시작: {target_date}")
        
        try:
            # DART API 키 검증
            if not self.validate_dart_api_key():
                logger.error("DART API 키 검증 실패로 공시 확인을 중단합니다")
                return []
            # 처리된 ID 목록 가져오기
            processed_ids = self.get_processed_ids()
            logger.debug(f"기존 처리된 공시 ID: {len(processed_ids)}개")
            
            # 공시 목록 조회
            disclosures = self.fetch_disclosures_for_date(target_date)
            logger.info(f"전체 공시 {len(disclosures)}건 조회")
            
            if not disclosures:
                logger.info("조회된 공시가 없습니다")
                return []
            
            # 공시 필터링
            filtered_disclosures = self.filter_disclosures(disclosures)
            logger.info(f"필터링 후 공시 {len(filtered_disclosures)}건")
            
            # 새로운 공시 식별
            new_disclosures = []
            new_processed_ids = processed_ids.copy()
            
            for disclosure in filtered_disclosures:
                try:
                    rcept_no = str(disclosure['rcept_no'])
                    
                    if rcept_no not in processed_ids:
                        # 공시 데이터 추출
                        corp_code = disclosure.get('corp_code', '')
                        company_name = disclosure.get('corp_name', COMPANIES.get(corp_code, '알 수 없음'))
                        report_name = disclosure.get('report_nm', '')
                        rcept_dt = disclosure.get('rcept_dt', target_date)
                        
                        # 데이터 유효성 검사
                        if not report_name:
                            logger.warning(f"공시명이 없는 데이터 무시: {rcept_no}")
                            continue
                        
                        # 우선순위 점수 계산
                        priority_score = self.calculate_priority_score(report_name, company_name)
                        
                        # 매칭된 키워드 정보 가져오기
                        keyword_info = self.get_matched_keywords(report_name)
                        matched_keywords = keyword_info['or_keywords']
                        
                        # AND 조건 그룹이 매칭된 경우 추가 정보 로깅
                        if keyword_info['and_groups']:
                            logger.info(f"AND 조건 매칭: {keyword_info['and_groups']} - {report_name[:50]}...")
                        
                        # DART URL 생성
                        dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                        
                        # 표준화된 공시 정보
                        new_disclosure = {
                            'company': company_name,
                            'title': report_name,
                            'link': dart_url,
                            'time': rcept_dt,
                            'priority': priority_score,
                            'keywords': matched_keywords,
                            'keyword_info': keyword_info,  # 키워드 매칭 정보 추가
                            'rcept_no': rcept_no,
                            'corp_code': corp_code,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        new_disclosures.append(new_disclosure)
                        new_processed_ids.add(rcept_no)
                        
                        logger.info(f"새로운 공시 발견: {company_name} - {report_name[:50]}... (우선순위: {priority_score})")
                    
                except Exception as e:
                    logger.error(f"공시 처리 중 오류: {e}")
                    continue
            
            # 처리된 ID 목록 업데이트
            if new_processed_ids != processed_ids:
                self.save_processed_ids(new_processed_ids)
                logger.debug(f"처리된 ID 목록 업데이트: {len(new_processed_ids)}개")
            
            # 결과 요약
            logger.info(f"DART 공시 확인 완료: 새로운 공시 {len(new_disclosures)}건 발견")
            
            if new_disclosures:
                # 우선순위별 요약
                high_priority = [d for d in new_disclosures if d['priority'] >= 70]
                medium_priority = [d for d in new_disclosures if 40 <= d['priority'] < 70]
                low_priority = [d for d in new_disclosures if d['priority'] < 40]
                
                logger.info(f"우선순위별 공시: 높음 {len(high_priority)}건, 중간 {len(medium_priority)}건, 낮음 {len(low_priority)}건")
            
            return new_disclosures
            
        except Exception as e:
            logger.error(f"DART 공시 확인 중 예상치 못한 오류: {type(e).__name__} - {e}")
            return []
    
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

@performance_monitor('DART 공시 확인')
@log_exception('dart')
def check_new_disclosures(target_date: Optional[str] = None) -> List[Dict]:
    """
    새로운 공시 확인 (편의 함수)
    
    Args:
        target_date: 조회할 날짜 (YYYYMMDD), None이면 오늘
        
    Returns:
        새로운 공시 목록
    """
    return dart_monitor.check_new_disclosures(target_date)

def send_dart_notifications(new_disclosures: List[Dict]) -> int:
    """
    공시 알림 발송 (편의 함수)
    
    Args:
        new_disclosures: 발송할 공시 목록
        
    Returns:
        발송 성공한 알림 수
    """
    return dart_monitor.send_notifications(new_disclosures)

def get_processed_ids() -> Set[str]:
    """처리된 공시 ID 목록 조회 (편의 함수)"""
    return dart_monitor.get_processed_ids()

def validate_date_format(date_str: str) -> bool:
    """날짜 형식 검증 (편의 함수)"""
    return dart_monitor.validate_date_format(date_str)

def get_default_date_range() -> tuple[str, str]:
    """기본 날짜 범위 반환 (편의 함수)"""
    return dart_monitor.get_default_date_range()