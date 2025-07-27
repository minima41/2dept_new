#!/usr/bin/env python3
"""
D2 Dash v3 최종 검증 스크립트
시스템의 핵심 기능을 검증합니다.
"""
import os
import sys
import json
import importlib.util
from datetime import datetime

def test_module_imports():
    """필수 모듈 임포트 테스트"""
    test_results = []
    
    modules_to_test = [
        ('modules.config', '설정 모듈'),
        ('modules.dart_monitor', 'DART 모니터링 모듈'),
        ('modules.stock_monitor', '주식 모니터링 모듈'),
        ('modules.email_utils', '이메일 유틸리티'),
        ('modules.logger_utils', '로깅 유틸리티')
    ]
    
    for module_name, description in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            test_results.append((description, "PASS", "모듈 임포트 성공"))
        except Exception as e:
            test_results.append((description, "FAIL", f"모듈 임포트 실패: {str(e)}"))
    
    return test_results

def test_logging_system():
    """로깅 시스템 테스트"""
    test_results = []
    
    try:
        from modules.logger_utils import get_logger, StructuredLogger, PerformanceLogger
        
        # 기본 로거 테스트
        logger = get_logger('test')
        logger.info("테스트 로그 메시지")
        test_results.append(("기본 로거", "PASS", "로거 생성 및 로그 기록 성공"))
        
        # 구조화된 로거 테스트
        structured_logger = StructuredLogger('test_structured')
        structured_logger.structured_log('info', '구조화된 테스트', test_param='value')
        test_results.append(("구조화된 로거", "PASS", "구조화된 로깅 성공"))
        
        # 성능 로거 테스트
        perf_logger = PerformanceLogger()
        with perf_logger.measure_time('테스트 작업'):
            import time
            time.sleep(0.1)
        test_results.append(("성능 로거", "PASS", "성능 모니터링 성공"))
        
    except Exception as e:
        test_results.append(("로깅 시스템", "FAIL", f"로깅 시스템 오류: {str(e)}"))
    
    return test_results

def test_data_files():
    """데이터 파일 접근 테스트"""
    test_results = []
    
    data_files = [
        ('data/monitoring_stocks.json', '주식 모니터링 데이터'),
        ('data/processed_ids.txt', '처리된 공시 ID'),
        ('data/notifications.json', '알림 히스토리')
    ]
    
    for file_path, description in data_files:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    if file_path.endswith('.json'):
                        json.load(f)
                    else:
                        f.read()
                test_results.append((description, "PASS", "파일 읽기 성공"))
            else:
                test_results.append((description, "SKIP", "파일이 존재하지 않음"))
        except Exception as e:
            test_results.append((description, "FAIL", f"파일 접근 오류: {str(e)}"))
    
    return test_results

def test_flask_app_structure():
    """Flask 앱 구조 테스트"""
    test_results = []
    
    try:
        # app.py 파일 확인
        if os.path.exists('app.py'):
            with open('app.py', 'r', encoding='utf-8') as f:
                app_content = f.read()
                
            # 주요 엔드포인트 확인
            required_endpoints = [
                '/api/v1/status',
                '/api/v1/stocks',
                '/api/v1/dart/companies',
                '/api/v1/dart/keywords',
                '/api/v1/alerts'
            ]
            
            missing_endpoints = []
            for endpoint in required_endpoints:
                if endpoint not in app_content:
                    missing_endpoints.append(endpoint)
            
            if not missing_endpoints:
                test_results.append(("Flask 엔드포인트", "PASS", "모든 필수 엔드포인트 정의됨"))
            else:
                test_results.append(("Flask 엔드포인트", "FAIL", f"누락된 엔드포인트: {missing_endpoints}"))
            
            # 로깅 시스템 통합 확인
            if 'logger_utils' in app_content and 'performance_monitor' in app_content:
                test_results.append(("로깅 시스템 통합", "PASS", "로깅 시스템이 Flask 앱에 통합됨"))
            else:
                test_results.append(("로깅 시스템 통합", "FAIL", "로깅 시스템 통합 누락"))
            
        else:
            test_results.append(("Flask 앱", "FAIL", "app.py 파일이 존재하지 않음"))
        
    except Exception as e:
        test_results.append(("Flask 앱 구조", "FAIL", f"앱 구조 검증 오류: {str(e)}"))
    
    return test_results

def test_static_files():
    """정적 파일 테스트"""
    test_results = []
    
    static_files = [
        ('static/index.html', '메인 페이지'),
        ('static/dart.html', 'DART 관리 페이지'),
        ('static/style.css', 'CSS 스타일'),
        ('static/script.js', '메인 JavaScript'),
        ('static/dart.js', 'DART JavaScript')
    ]
    
    for file_path, description in static_files:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 기본 내용 검증
                if file_path.endswith('.html') and 'D2 Dash' in content:
                    test_results.append((description, "PASS", "파일 존재 및 내용 검증 완료"))
                elif file_path.endswith('.js') and '/api/v1/' in content:
                    test_results.append((description, "PASS", "API 엔드포인트 업데이트 확인"))
                elif file_path.endswith('.css'):
                    test_results.append((description, "PASS", "CSS 파일 존재"))
                else:
                    test_results.append((description, "PASS", "파일 존재"))
            else:
                test_results.append((description, "FAIL", "파일이 존재하지 않음"))
        except Exception as e:
            test_results.append((description, "FAIL", f"파일 검증 오류: {str(e)}"))
    
    return test_results

def main():
    """메인 검증 함수"""
    print("=" * 60)
    print("D2 Dash v3 최종 검증")
    print("=" * 60)
    
    all_results = []
    
    # 각 테스트 실행
    test_suites = [
        ("모듈 임포트", test_module_imports),
        ("로깅 시스템", test_logging_system),
        ("데이터 파일", test_data_files),
        ("Flask 앱 구조", test_flask_app_structure),
        ("정적 파일", test_static_files)
    ]
    
    for suite_name, test_function in test_suites:
        print(f"\n{suite_name} 테스트:")
        print("-" * 30)
        
        try:
            results = test_function()
            all_results.extend(results)
            
            for test_name, status, message in results:
                status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[SKIP]"
                print(f"{status_symbol} {test_name}: {message}")
                
        except Exception as e:
            print(f"[ERROR] {suite_name} 테스트 실행 중 오류: {str(e)}")
            all_results.append((f"{suite_name} 테스트", "FAIL", f"테스트 실행 오류: {str(e)}"))
    
    # 결과 요약
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r[1] == "PASS"])
    failed_tests = len([r for r in all_results if r[1] == "FAIL"])
    skipped_tests = len([r for r in all_results if r[1] == "SKIP"])
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 60)
    print("최종 검증 결과")
    print("=" * 60)
    print(f"총 테스트: {total_tests}개")
    print(f"성공: {passed_tests}개")
    print(f"실패: {failed_tests}개")
    print(f"건너뜀: {skipped_tests}개")
    print(f"성공률: {success_rate:.1f}%")
    
    # 실패한 테스트 목록
    if failed_tests > 0:
        print("\n실패한 테스트:")
        for test_name, status, message in all_results:
            if status == "FAIL":
                print(f"  - {test_name}: {message}")
    
    # 결과 저장
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "success_rate": round(success_rate, 2)
        },
        "results": [
            {"test": r[0], "status": r[1], "message": r[2]}
            for r in all_results
        ]
    }
    
    with open("final_verification_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n상세 보고서: final_verification_report.json")
    
    if success_rate >= 80:
        print("\n결과: 시스템이 성공적으로 구성되었습니다!")
        return True
    else:
        print("\n결과: 일부 기능에 문제가 있습니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)