#!/usr/bin/env python3
"""
D2 Dash v3 통합 테스트 스크립트
모든 시스템 기능을 종합적으로 검증합니다.
"""
import json
import requests
import time
import threading
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# 테스트 설정
BASE_URL = "http://localhost:5000"
TIMEOUT = 10

class D2DashIntegrationTest:
    """D2 Dash v3 통합 테스트 클래스"""
    
    def __init__(self):
        self.test_results = []
        self.server_process = None
        
    def log_test(self, test_name: str, status: str, message: str = "", data: Any = None):
        """테스트 결과 로깅"""
        result = {
            "test_name": test_name,
            "status": status,  # "PASS", "FAIL", "SKIP"
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[SKIP]"
        print(f"{status_symbol} {test_name}: {message}")
        
    def wait_for_server(self, max_wait: int = 30):
        """서버 시작 대기"""
        print(f"서버 시작 대기 중... (최대 {max_wait}초)")
        
        for i in range(max_wait):
            try:
                response = requests.get(f"{BASE_URL}/api/v1/status", timeout=2)
                if response.status_code == 200:
                    self.log_test("서버 시작", "PASS", f"{i+1}초 후 서버 응답 확인")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
                continue
                
        self.log_test("서버 시작", "FAIL", f"{max_wait}초 후에도 서버 응답 없음")
        return False

    def test_api_endpoints(self):
        """API 엔드포인트 테스트"""
        endpoints = [
            ("/api/v1/status", "GET", "시스템 상태 조회"),
            ("/api/v1/stocks", "GET", "주식 목록 조회"),
            ("/api/v1/dart/companies", "GET", "DART 기업 목록"),
            ("/api/v1/dart/keywords", "GET", "DART 키워드 목록"),
            ("/api/v1/alerts", "GET", "알림 목록 조회"),
        ]
        
        for endpoint, method, description in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                else:
                    response = requests.post(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success', True):  # success 필드가 없으면 True로 간주
                            self.log_test(f"API: {description}", "PASS", 
                                        f"HTTP {response.status_code}")
                        else:
                            self.log_test(f"API: {description}", "FAIL", 
                                        f"응답에서 success=False: {data.get('error', '')}")
                    except json.JSONDecodeError:
                        self.log_test(f"API: {description}", "FAIL", "JSON 파싱 오류")
                else:
                    self.log_test(f"API: {description}", "FAIL", 
                                f"HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_test(f"API: {description}", "FAIL", f"요청 오류: {str(e)}")

    def test_spa_routing(self):
        """SPA 라우팅 테스트"""
        spa_routes = [
            ("/", "메인 페이지"),
            ("/dart", "DART 관리 페이지"),
            ("/alerts", "알림 페이지 (SPA 라우팅)"),
            ("/nonexistent", "존재하지 않는 페이지 (SPA fallback)")
        ]
        
        for route, description in spa_routes:
            try:
                response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)
                
                if response.status_code == 200:
                    content = response.text
                    if "D2 Dash" in content and "html" in content.lower():
                        self.log_test(f"SPA 라우팅: {description}", "PASS", 
                                    f"정상적인 HTML 응답")
                    else:
                        self.log_test(f"SPA 라우팅: {description}", "FAIL", 
                                    "HTML 내용 검증 실패")
                else:
                    self.log_test(f"SPA 라우팅: {description}", "FAIL", 
                                f"HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_test(f"SPA 라우팅: {description}", "FAIL", f"요청 오류: {str(e)}")

    def test_dart_functionality(self):
        """DART 기능 테스트"""
        try:
            # DART 공시 조회 테스트
            response = requests.get(f"{BASE_URL}/api/v1/dart/disclosures", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    disclosures = data.get('disclosures', [])
                    self.log_test("DART 공시 조회", "PASS", 
                                f"{len(disclosures)}개 공시 조회됨")
                else:
                    self.log_test("DART 공시 조회", "FAIL", 
                                f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("DART 공시 조회", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("DART 공시 조회", "FAIL", f"요청 오류: {str(e)}")
            
        # 수동 DART 확인 테스트
        try:
            response = requests.post(f"{BASE_URL}/api/v1/dart/check", 
                                   json={}, timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("DART 수동 확인", "PASS", 
                                f"확인 완료: {data.get('message', '')}")
                else:
                    self.log_test("DART 수동 확인", "FAIL", 
                                f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("DART 수동 확인", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("DART 수동 확인", "FAIL", f"요청 오류: {str(e)}")

    def test_stock_functionality(self):
        """주식 모니터링 기능 테스트"""
        try:
            # 주식 목록 조회
            response = requests.get(f"{BASE_URL}/api/v1/stocks", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    stocks = data.get('stocks', {})
                    self.log_test("주식 목록 조회", "PASS", 
                                f"{len(stocks)}개 종목 모니터링 중")
                else:
                    self.log_test("주식 목록 조회", "FAIL", 
                                f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("주식 목록 조회", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("주식 목록 조회", "FAIL", f"요청 오류: {str(e)}")
            
        # 수동 주식 업데이트 테스트
        try:
            response = requests.post(f"{BASE_URL}/api/v1/stocks/update", 
                                   json={}, timeout=15)  # 주식 업데이트는 시간이 걸릴 수 있음
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("주식 가격 업데이트", "PASS", 
                                f"업데이트 완료: {data.get('message', '')}")
                else:
                    self.log_test("주식 가격 업데이트", "FAIL", 
                                f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("주식 가격 업데이트", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("주식 가격 업데이트", "FAIL", f"요청 오류: {str(e)}")

    def test_error_handling(self):
        """에러 처리 테스트"""
        error_tests = [
            ("/api/v1/nonexistent", "GET", "존재하지 않는 API 엔드포인트"),
            ("/api/v1/dart/disclosures?date=invalid", "GET", "잘못된 날짜 형식"),
        ]
        
        for endpoint, method, description in error_tests:
            try:
                if method == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                else:
                    response = requests.post(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                
                if response.status_code in [400, 404]:
                    try:
                        data = response.json()
                        if 'error' in data:
                            self.log_test(f"에러 처리: {description}", "PASS", 
                                        f"적절한 에러 응답: {response.status_code}")
                        else:
                            self.log_test(f"에러 처리: {description}", "FAIL", 
                                        "에러 응답에 error 필드 누락")
                    except json.JSONDecodeError:
                        self.log_test(f"에러 처리: {description}", "FAIL", 
                                    "에러 응답이 JSON이 아님")
                else:
                    self.log_test(f"에러 처리: {description}", "FAIL", 
                                f"예상치 못한 상태 코드: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_test(f"에러 처리: {description}", "FAIL", f"요청 오류: {str(e)}")

    def test_performance(self):
        """성능 테스트"""
        start_time = time.time()
        
        try:
            response = requests.get(f"{BASE_URL}/api/v1/status", timeout=5)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # ms
            
            if response.status_code == 200 and response_time < 1000:
                self.log_test("API 응답 시간", "PASS", 
                            f"{response_time:.2f}ms (< 1초)")
            elif response.status_code == 200:
                self.log_test("API 응답 시간", "FAIL", 
                            f"{response_time:.2f}ms (너무 느림)")
            else:
                self.log_test("API 응답 시간", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("API 응답 시간", "FAIL", f"요청 오류: {str(e)}")

    def test_ui_components(self):
        """UI 컴포넌트 검증"""
        try:
            # 메인 페이지 HTML 응답 확인
            response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
            
            if response.status_code == 200:
                html_content = response.text
                
                # 필수 UI 요소 확인
                required_elements = [
                    ("주식 모니터링 탭", "주식 모니터링"),
                    ("DART 공시 관리 탭", "DART 공시 관리"),
                    ("서브 탭 네비게이션", "sub-navigation"),
                    ("종목 테이블", "stocks-table"),
                    ("종목 추가 모달", "add-modal"),
                    ("하단 패널", "bottom-panels"),
                    ("일일 내역 테이블", "daily-history-table"),
                    ("실시간 로그", "logs-container"),
                    ("CSS 로드", "style.css"),
                    ("JavaScript 로드", "script.js")
                ]
                
                ui_passed = 0
                for element_name, search_term in required_elements:
                    if search_term in html_content:
                        self.log_test(f"UI: {element_name}", "PASS", "요소 발견됨")
                        ui_passed += 1
                    else:
                        self.log_test(f"UI: {element_name}", "FAIL", "요소 없음")
                
                # UI 완성도 평가
                completion_rate = (ui_passed / len(required_elements)) * 100
                if completion_rate >= 90:
                    self.log_test("UI 완성도", "PASS", f"{completion_rate:.1f}% 완성")
                else:
                    self.log_test("UI 완성도", "FAIL", f"{completion_rate:.1f}% 완성 (90% 미만)")
                    
            else:
                self.log_test("UI 컴포넌트 검증", "FAIL", f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("UI 컴포넌트 검증", "FAIL", f"요청 오류: {str(e)}")

    def test_daily_history_api(self):
        """일일 내역 API 테스트"""
        try:
            response = requests.get(f"{BASE_URL}/api/v1/daily-history", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    history = data.get('data', [])
                    self.log_test("일일 내역 API", "PASS", 
                                f"{len(history)}개 내역 조회됨")
                else:
                    self.log_test("일일 내역 API", "FAIL", 
                                f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("일일 내역 API", "FAIL", 
                            f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("일일 내역 API", "FAIL", f"요청 오류: {str(e)}")

    def test_stock_crud_workflow(self):
        """종목 CRUD 워크플로우 테스트"""
        test_stock = {
            "stock_code": "999999",
            "stock_name": "테스트종목",
            "category": "매수",
            "current_price": 50000,
            "target_price": 60000,
            "stop_loss": 45000,
            "alert_settings": {
                "price_alert_enabled": True,
                "volatility_alert_enabled": True,
                "surge_threshold": 5.0,
                "drop_threshold": -5.0
            },
            "memo": "통합테스트용 종목"
        }
        
        # 종목 추가 테스트
        try:
            response = requests.post(f"{BASE_URL}/api/v1/stocks/add", 
                                   json=test_stock, timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("종목 추가", "PASS", f"종목 추가 성공")
                    
                    # 추가된 종목 확인
                    time.sleep(1)  # 잠시 대기
                    response = requests.get(f"{BASE_URL}/api/v1/stocks", timeout=TIMEOUT)
                    if response.status_code == 200:
                        stocks_data = response.json()
                        if test_stock["stock_code"] in stocks_data.get("stocks", {}):
                            self.log_test("종목 조회 확인", "PASS", "추가된 종목 확인됨")
                        else:
                            self.log_test("종목 조회 확인", "FAIL", "추가된 종목 없음")
                    
                    # 종목 삭제 (정리)
                    delete_response = requests.delete(f"{BASE_URL}/api/v1/stocks/{test_stock['stock_code']}")
                    if delete_response.status_code == 200:
                        delete_data = delete_response.json()
                        if delete_data.get('success'):
                            self.log_test("종목 삭제", "PASS", "테스트 종목 정리 완료")
                        else:
                            self.log_test("종목 삭제", "FAIL", f"삭제 실패: {delete_data.get('error', '')}")
                else:
                    self.log_test("종목 추가", "FAIL", f"API 오류: {data.get('error', '')}")
            else:
                self.log_test("종목 추가", "FAIL", f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("종목 CRUD", "FAIL", f"요청 오류: {str(e)}")

    def test_image_requirements_compliance(self):
        """이미지 요구사항 준수성 검증"""
        try:
            response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
            
            if response.status_code == 200:
                html_content = response.text
                
                # 이미지에서 확인된 필수 요소들
                image_requirements = [
                    ("전체/메자닌/주식 서브탭", ["전체", "메자닌", "주식"]),
                    ("종목 테이블 컬럼", ["종목코드", "종목명", "구분", "현재가", "등락률"]),
                    ("알람설정 컬럼", "알람설정"),
                    ("관리 컬럼", "관리"),
                    ("하단 패널", ["일일 내역", "실시간 로그"]),
                    ("새로고침 주기", ["30초", "60초", "2분", "5분"])
                ]
                
                compliance_score = 0
                total_requirements = len(image_requirements)
                
                for req_name, search_terms in image_requirements:
                    if isinstance(search_terms, list):
                        found = all(term in html_content for term in search_terms)
                    else:
                        found = search_terms in html_content
                    
                    if found:
                        self.log_test(f"이미지 요구사항: {req_name}", "PASS", "요구사항 충족")
                        compliance_score += 1
                    else:
                        self.log_test(f"이미지 요구사항: {req_name}", "FAIL", "요구사항 미충족")
                
                # 전체 준수율 계산
                compliance_rate = (compliance_score / total_requirements) * 100
                if compliance_rate >= 95:
                    self.log_test("이미지 요구사항 전체 준수율", "PASS", f"{compliance_rate:.1f}% 준수")
                else:
                    self.log_test("이미지 요구사항 전체 준수율", "FAIL", f"{compliance_rate:.1f}% 준수 (95% 미만)")
                    
            else:
                self.log_test("이미지 요구사항 검증", "FAIL", f"HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_test("이미지 요구사항 검증", "FAIL", f"요청 오류: {str(e)}")

    def generate_report(self):
        """테스트 결과 리포트 생성"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        skipped_tests = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": round(success_rate, 2)
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # 리포트 파일 저장
        report_filename = f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 콘솔 출력
        print("\n" + "="*60)
        print("D2 Dash v3 통합 테스트 결과")
        print("="*60)
        print(f"총 테스트: {total_tests}개")
        print(f"성공: {passed_tests}개")
        print(f"실패: {failed_tests}개")
        print(f"건너뜀: {skipped_tests}개")
        print(f"성공률: {success_rate:.1f}%")
        print(f"상세 리포트: {report_filename}")
        
        if failed_tests > 0:
            print("\n실패한 테스트:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test_name']}: {result['message']}")
        
        return success_rate >= 80  # 80% 이상 성공 시 통과

    def run_tests(self):
        """전체 테스트 실행"""
        print("D2 Dash v3 통합 테스트 시작")
        print("-" * 60)
        
        # 서버 시작 대기
        if not self.wait_for_server():
            print("ERROR: 서버를 시작할 수 없어 테스트를 중단합니다.")
            return False
        
        print("\n테스트 실행 중...")
        
        # 각 테스트 모듈 실행
        try:
            self.test_api_endpoints()
            self.test_spa_routing() 
            self.test_dart_functionality()
            self.test_stock_functionality()
            self.test_error_handling()
            self.test_performance()
            
            # v3 추가 테스트
            self.test_ui_components()
            self.test_daily_history_api()
            self.test_stock_crud_workflow()
            self.test_image_requirements_compliance()
        except Exception as e:
            self.log_test("테스트 실행", "FAIL", f"예외 발생: {str(e)}")
        
        # 결과 리포트 생성
        return self.generate_report()

def main():
    """메인 함수"""
    tester = D2DashIntegrationTest()
    success = tester.run_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()