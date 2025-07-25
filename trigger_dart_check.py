#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART 모니터링을 수동으로 트리거하는 스크립트
"""

import asyncio
import sys
import os

# 백엔드 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.modules.dart.monitor import dart_monitor

async def trigger_dart_check():
    """DART 모니터링 강제 실행"""
    print("=== DART 모니터링 강제 실행 ===")
    
    try:
        # 강제 체크 실행
        result = await dart_monitor.force_check()
        
        if result:
            print("[OK] DART 모니터링 강제 실행 성공!")
        else:
            print("[ERROR] DART 모니터링 강제 실행 실패")
            
        # 현재 상태 조회
        status = dart_monitor.get_status()
        print(f"\n모니터링 상태:")
        print(f"  실행 중: {status['is_running']}")
        print(f"  총 체크 횟수: {status['check_count']}")
        print(f"  에러 횟수: {status['error_count']}")
        print(f"  마지막 체크 시간: {status['last_check_time']}")
        print(f"  다음 체크 시간: {status['next_check_time']}")
        
    except Exception as e:
        print(f"[ERROR] 실행 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_dart_check())