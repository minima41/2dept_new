#!/usr/bin/env python3
"""
환경변수 기반 설정 시스템 테스트
"""
import sys
import os
sys.path.append('/mnt/c/2dept/backend')

def test_config_loading():
    """설정 로딩 테스트"""
    print("=== 환경변수 기반 설정 시스템 테스트 ===")
    
    try:
        from app.config import settings
        
        print(f"\n✅ 설정 로딩 성공")
        print(f"   앱 이름: {settings.APP_NAME}")
        print(f"   디버그 모드: {settings.DEBUG}")
        print(f"   운영 환경: {settings.is_production}")
        print(f"   로그 레벨: {settings.log_level}")
        
        print(f"\n📧 이메일 설정:")
        print(f"   발신자: {settings.EMAIL_SENDER}")
        print(f"   SMTP 서버: {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
        
        print(f"\n🏢 DART API 설정:")
        print(f"   API 키: {'설정됨' if settings.DART_API_KEY else '미설정'}")
        print(f"   베이스 URL: {settings.DART_BASE_URL}")
        print(f"   체크 주기: {settings.DART_CHECK_INTERVAL}초")
        
        print(f"\n📊 주가 모니터링 설정:")
        print(f"   업데이트 주기: {settings.STOCK_UPDATE_INTERVAL}초")
        print(f"   시장 시간: {settings.MARKET_OPEN_TIME} - {settings.MARKET_CLOSE_TIME}")
        
        print(f"\n🔒 보안 설정:")
        print(f"   시크릿 키: {'설정됨' if settings.SECRET_KEY != 'your-secret-key-change-in-production' else '기본값 사용 중'}")
        print(f"   JWT 알고리즘: {settings.ALGORITHM}")
        print(f"   토큰 만료: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}분")
        
        print(f"\n📁 파일 경로:")
        print(f"   데이터 디렉토리: {settings.DATA_DIR}")
        print(f"   로그 디렉토리: {settings.LOGS_DIR}")
        
        return True
        
    except Exception as e:
        print(f"❌ 설정 로딩 실패: {e}")
        return False

def test_environment_variables():
    """환경변수 테스트"""
    print(f"\n=== 환경변수 확인 ===")
    
    env_vars = [
        'DART_API_KEY',
        'EMAIL_SENDER', 
        'EMAIL_PASSWORD',
        'EMAIL_RECEIVER',
        'SECRET_KEY',
        'DEBUG'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # 민감한 정보는 마스킹
            if 'password' in var.lower() or 'key' in var.lower():
                masked_value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "****"
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: 미설정")

if __name__ == "__main__":
    test_environment_variables()
    success = test_config_loading()
    
    if success:
        print(f"\n✅ 모든 테스트 통과!")
    else:
        print(f"\n❌ 일부 테스트 실패")
        sys.exit(1)