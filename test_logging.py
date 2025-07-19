#!/usr/bin/env python3
"""
통합 로깅 시스템 테스트 스크립트
"""
import sys
import os
sys.path.append('/mnt/c/2dept/backend')

from app.utils.logger import app_logger, auto_retry, log_function_call

# 자동 재시도 테스트
@auto_retry(max_retries=2, delay=0.1)
def test_retry_function(should_fail=True):
    """재시도 테스트 함수"""
    if should_fail:
        raise Exception("테스트 예외 발생")
    return "성공!"

# 함수 호출 로그 테스트
@log_function_call()
def test_function_logging(param1, param2=None):
    """함수 호출 로그 테스트"""
    app_logger.info(f"함수 내부 로그: param1={param1}, param2={param2}")
    return f"결과: {param1}-{param2}"

def main():
    print("=== 통합 로깅 시스템 테스트 ===")
    
    # 기본 로깅 테스트
    print("\n1. 기본 로깅 테스트")
    app_logger.debug("디버그 메시지")
    app_logger.info("정보 메시지") 
    app_logger.warning("경고 메시지")
    app_logger.error("오류 메시지")
    
    # 함수 호출 로그 테스트
    print("\n2. 함수 호출 로그 테스트")
    try:
        result = test_function_logging("테스트", param2="값")
        print(f"함수 결과: {result}")
    except Exception as e:
        print(f"함수 실행 오류: {e}")
    
    # 자동 재시도 테스트 (실패)
    print("\n3. 자동 재시도 테스트 (실패 케이스)")
    try:
        test_retry_function(should_fail=True)
    except Exception as e:
        print(f"재시도 후 최종 실패: {e}")
    
    # 자동 재시도 테스트 (성공)
    print("\n4. 자동 재시도 테스트 (성공 케이스)")
    try:
        result = test_retry_function(should_fail=False)
        print(f"재시도 성공: {result}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()