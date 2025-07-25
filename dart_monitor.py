import requests
import time
from datetime import datetime, date, timedelta
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
import socket
from config import (
    DART_API_KEY, 
    EMAIL_SENDER, 
    EMAIL_PASSWORD, 
    EMAIL_RECEIVER,
    KEYWORDS,
    IMPORTANT_SECTIONS,
    CONTEXT_WINDOW,
    CHECK_INTERVAL,
    COMPANIES
)
import sendgrid
from sendgrid.helpers.mail import Mail

import logging
from logging.handlers import RotatingFileHandler

# 로깅 설정
log_file = 'dart_monitor.log'
log_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

# 콘솔 출력용 핸들러 추가 (인코딩 명시)
import sys
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(console_handler)

# 로깅과 콘솔 출력을 함께하는 함수
def log_print(message):
    logger.info(message)
    print(message)  # 디버깅 시 콘솔 출력도 유지

def prevent_multiple_instances():
    """소켓을 사용하여 중복 실행을 방지합니다."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 포트 12345에 바인딩 시도
        sock.bind(('localhost', 12345))
    except socket.error:
        log_print("DART 모니터링 시스템이 이미 실행 중입니다.")
        log_print("중복 실행을 방지하기 위해 프로그램을 종료합니다.")
        sys.exit(0)
    return sock

_sock = None

def get_processed_ids():
    try:
        with open('processed_ids.txt', 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_processed_id(id):
    processed_ids = get_processed_ids()
    processed_ids.add(id)
    
    # 최대 저장 개수 제한 (예: 최근 1000개만 유지)
    MAX_PROCESSED_IDS = 1000
    if len(processed_ids) > MAX_PROCESSED_IDS:
        # ID를 정렬하여 최신 ID만 유지 (리셉션 번호는 일반적으로 시간순으로 증가하므로 큰 숫자가 최신)
        processed_ids = set(sorted(processed_ids, reverse=True)[:MAX_PROCESSED_IDS])
        log_print(f"처리된 ID 목록 정리: {MAX_PROCESSED_IDS}개만 유지")
    
    with open('processed_ids.txt', 'w') as f:
        f.write('\n'.join(processed_ids))

def get_last_checked_id():
    try:
        with open('last_checked.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_checked_id(id):
    with open('last_checked.txt', 'w') as f:
        f.write(str(id))

def send_email(subject, text_content, html_content=None):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject

        # 디버깅을 위한 출력
        log_print(f"이메일 준비 중: {subject}")
        log_print(f"보내는 사람: {EMAIL_SENDER}")
        log_print(f"받는 사람: {EMAIL_RECEIVER}")

        # 텍스트 버전 첨부
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        log_print("텍스트 버전 첨부 완료")
        
        # HTML 버전이 있으면 첨부
        if html_content:
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            log_print("HTML 버전 첨부 완료")

        log_print("SMTP 서버 연결 시도...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        log_print("SMTP 서버 연결 성공")
        
        log_print("TLS 시작...")
        server.starttls()
        log_print("TLS 설정 완료")
        
        log_print("로그인 시도...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        log_print("로그인 성공")
        
        log_print("이메일 발송 시도...")
        server.send_message(msg)
        log_print("이메일 발송 완료")
        
        server.quit()
        log_print(f"이메일 전송 성공: {subject}")
    except Exception as e:
        import traceback
        log_print(f"이메일 전송 실패: {e}")
        log_print("상세 오류 정보:")
        traceback.print_exc()

def analyze_disclosure_content(content):
    # 중요 섹션 찾기
    important_content = ""
    for section in IMPORTANT_SECTIONS:
        # \Z 대신 $ 사용
        pattern = f"{section}[：:](.*?)(?=\n\n|$)"
        matches = re.finditer(pattern, content, re.DOTALL)
        for match in matches:
            important_content += match.group(1).strip() + "\n\n"

    # 키워드 분석
    found_keywords = []
    for keyword in KEYWORDS:
        if keyword in important_content:
            # 키워드 주변 문맥 추출
            start = max(0, important_content.find(keyword) - CONTEXT_WINDOW)
            end = min(len(important_content), important_content.find(keyword) + len(keyword) + CONTEXT_WINDOW)
            context = important_content[start:end]
            found_keywords.append((keyword, context))

    return found_keywords

def test_specific_disclosures():
    log_print("특정 공시 테스트 시작...")
    
    # 테스트할 공시 목록
    test_disclosures = [
        {
            "company_name": "유디엠텍",
            "report_name": "주식등의대량보유상황보고서(약식)",
            "rcept_dt": "2024-03-24",
            "rcept_no": "20240324000001"
        },
        {
            "company_name": "차바이오텍",
            "report_name": "효력발생안내(2025.3.24. 제출 증권신고서(지분증권))",
            "rcept_dt": "2024-03-24",
            "rcept_no": "20240324000002"
        },
        {
            "company_name": "메타바이오메드",
            "report_name": "[연장결정]주요사항보고서(자기주식취득신탁계약체결결정)",
            "rcept_dt": "2024-03-24",
            "rcept_no": "20240324000003"
        },
        {
            "company_name": "네온테크",
            "report_name": "[첨부정정]주요사항보고서(전환사채권발행결정)",
            "rcept_dt": "2024-03-24",
            "rcept_no": "20240324000004"
        }
    ]
    
    # 테스트 이메일 내용 작성
    email_subject = "[공시 알림 테스트] 최근 공시 목록"
    email_content = "최근 공시 목록입니다:\n\n"
    
    # HTML 버전 생성
    html_content = "<h3>최근 공시 목록입니다:</h3>\n\n"
    
    for item in test_disclosures:
        # 텍스트 버전
        email_content += f"회사명: {item['company_name']}\n"
        email_content += f"공시제목: {item['report_name']}\n"
        email_content += f"공시일시: {item['rcept_dt']}\n"
        link_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item['rcept_no']}"
        email_content += f"공시링크: {link_url}\n\n"
        
        # HTML 버전
        html_content += f"<p>회사명: {item['company_name']}<br>\n"
        html_content += f"공시제목: {item['report_name']}<br>\n"
        html_content += f"공시일시: {item['rcept_dt']}<br>\n"
        html_content += f"공시링크: <a href=\"{link_url}\">{link_url}</a></p>\n\n"
    
    send_email(email_subject, email_content, html_content)
    log_print("테스트 이메일 전송 완료")

def check_new_disclosures():
    last_id = get_last_checked_id()
    processed_ids = get_processed_ids()
    
    log_print(f"마지막으로 확인한 공시 ID: {last_id}")
    log_print(f"이미 처리한 공시 개수: {len(processed_ids)}")
    
    # 항상 당일 데이터만 조회하여 API 호출 최소화
    start_date = date.today().strftime("%Y%m%d")
    today = date.today().strftime("%Y%m%d")
    log_print(f"오늘 날짜 {today} 공시 조회")
    
    # DART API 전체 공시 목록 호출
    url = "https://opendart.fss.or.kr/api/list.json"
    
    # 관심 종목 코드 목록
    corp_codes = list(COMPANIES.values())
    log_print(f"관심 기업 코드 수: {len(corp_codes)}")
    
    # API 최적화: 관심 기업별로 직접 조회
    total_disclosures = []
    
    # 한 번에 한 기업씩 조회 (API가 여러 corp_code를 지원하지 않음)
    for idx, corp_code in enumerate(corp_codes):
        # 페이지네이션 변수 초기화
        page_no = 1
        page_count = 100  # API 최대 허용값으로 보임
        company_disclosures = []
        
        company_name = next((name for name, code in COMPANIES.items() if code == corp_code), corp_code)
        
        # 각 기업당 1페이지(최신 100개)만 조회
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,  # 한 번에 하나의 기업 코드만 사용
            "bgn_de": start_date,
            "end_de": today,
            "page_no": page_no,
            "page_count": page_count
        }
        
        try:
            log_print(f"[{idx+1}/{len(corp_codes)}] '{company_name}' 공시 조회 중...")
            response = requests.get(url, params=params)
            data = response.json()
            
            # API 사용한도 초과 처리
            if data.get('status') == '020':
                log_print(f"API 사용한도 초과: 다음 스케줄까지 기다립니다.")
                return
            
            if data.get('status') == '000':
                disclosures = data.get('list', [])
                current_page_count = len(disclosures)
                company_disclosures.extend(disclosures)
                
                if current_page_count > 0:
                    log_print(f"  '{company_name}' 공시 {current_page_count}개 발견")
                
            elif data.get('status') == '013':  # 공시정보 없음
                pass  # 로그 출력 최소화
            else:
                log_print(f"API 오류: {data.get('message', '알 수 없는 오류')}")
                
        except Exception as e:
            import traceback
            log_print(f"공시 확인 중 오류 발생: {e}")
            traceback.print_exc()
        
        # 해당 기업의 결과 추가
        total_disclosures.extend(company_disclosures)
        
        # API 부하 방지를 위한 약간의 지연
        if idx < len(corp_codes) - 1 and len(corp_codes) > 20:  # 기업이 많을 때만 지연
            time.sleep(0.2)  # 0.2초 지연
    
    # 새로운 공시만 필터링
    new_disclosures = [item for item in total_disclosures if str(item['rcept_no']) not in processed_ids]
    if new_disclosures:
        log_print(f"\n새로운 공시 {len(new_disclosures)}개 발견!")
    
    # 제외할 키워드 목록 (불필요한 공시 키워드)
    EXCLUDE_KEYWORDS = ["기업설명회", "IR개최", "설명회개최", "IR)", "(IR)"]
    
    # 이메일 발송
    for item in new_disclosures:
        current_id = str(item['rcept_no'])
        corp_code = item['corp_code']
        
        # 기업명 가져오기 - COMPANIES에 없으면 API 응답에서 기업명 사용
        if corp_code in COMPANIES.values():
            company_name = next((name for name, code in COMPANIES.items() if code == corp_code), item['corp_name'])
        else:
            company_name = item['corp_name']  # API 응답에서 직접 가져옴
            
        report_name = item['report_nm']
        
        # 제외 키워드 확인 - 제외 키워드가 포함된 공시는 무시
        if any(exclude_kw in report_name for exclude_kw in EXCLUDE_KEYWORDS):
            log_print(f"제외된 공시: {company_name} - {report_name} (제외 키워드에 포함됨)")
            save_processed_id(current_id)  # 처리한 것으로 표시
            continue
        
        # 필터링: 관심 키워드에 포함된 공시만 허용
        should_send = False
        for keyword in KEYWORDS:
            if keyword in report_name:
                should_send = True
                break
        
        if not should_send:
            log_print(f"무시된 공시: {company_name} - {report_name} (관심 키워드에 포함되지 않음)")
            save_processed_id(current_id)  # 처리한 것으로 표시
            continue
        
        log_print(f"새로운 공시: {company_name} - {report_name} (ID: {current_id})")
        
        # 이메일 제목
        email_subject = f"[공시 알림] {company_name} - {report_name}"
        
        # 텍스트 버전 이메일 내용
        email_content = f"회사명: {company_name}\n"
        email_content += f"공시명: {report_name}\n"
        email_content += f"접수일자: {item['rcept_dt']}\n"
        
        # 링크 URL이 올바른 형식인지 확인
        link_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item['rcept_no']}"
        # URL이 https://로 시작하는지 확인
        if not link_url.startswith("https://"):
            link_url = "https://" + link_url.lstrip("http://")  # http:// 중복 방지
        
        # 텍스트 버전에 링크 추가
        email_content += f"공시링크: {link_url}\n\n"
        
        # HTML 버전 생성 (간단하게 링크만 HTML로)
        html_content = f"<p>회사명: {company_name}<br>\n"
        html_content += f"공시명: {report_name}<br>\n"
        html_content += f"접수일자: {item['rcept_dt']}<br>\n"
        html_content += f"공시링크: <a href=\"{link_url}\">{link_url}</a></p>\n"
        
        send_email(email_subject, email_content, html_content)
        # 처리한 ID 저장
        save_processed_id(current_id)
        # 마지막 ID 갱신 (기존 방식 유지)
        if not last_id or current_id > last_id:
            save_last_checked_id(current_id)
    
    log_print(f"총 관심 기업 공시 개수: {len(total_disclosures)}")
    if not total_disclosures:
        log_print("오늘 관심 기업의 공시가 없습니다.")

def main():
    global _sock
    
    # 중복 실행 방지
    _sock = prevent_multiple_instances()
    
    log_print("DART 모니터링 시스템 시작...")
    log_print(f"모니터링 간격: {CHECK_INTERVAL}초")
    
    # 마지막 체크 시간 기록 파일 초기화
    with open('last_check_time.txt', 'w') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    while True:
        try:
            log_print("\n" + "="*50)
            log_print(f"공시 확인 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 마지막 체크 시간 기록
            with open('last_check_time.txt', 'w') as f:
                f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            check_new_disclosures()
            
            log_print(f"다음 확인까지 {CHECK_INTERVAL}초 대기...")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            import traceback
            log_print(f"오류 발생: {e}")
            log_print("상세 오류 정보:")
            traceback.print_exc()
            log_print(f"10초 후 재시도...")
            time.sleep(10)

# main() 함수 끝 부분, if __name__ == "__main__": 앞에 추가
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        log_print(f"프로그램 실행 중 예상치 못한 오류 발생: {e}")
        logger.error(traceback.format_exc())
        
        # 10초 대기 후 프로그램 재시작 시도
        time.sleep(10)
        os.execl(sys.executable, sys.executable, *sys.argv)