#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백엔드 서버 재시작 스크립트
"""

import os
import subprocess
import sys
import time
import requests
from datetime import datetime

def check_server_running(url="http://localhost:8000", timeout=5):
    """서버 실행 상태 확인"""
    try:
        response = requests.get(f"{url}/health", timeout=timeout)
        return response.status_code == 200
    except:
        return False

def kill_existing_server():
    """기존 서버 프로세스 종료"""
    print("기존 서버 프로세스 확인 중...")
    
    try:
        # Windows에서 Python 프로세스 중 main.py를 실행하는 것 찾기
        import psutil
        killed_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any('main.py' in arg for arg in cmdline):
                        print(f"  프로세스 종료: PID {proc.info['pid']} - {' '.join(cmdline)}")
                        proc.terminate()
                        killed_processes.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if killed_processes:
            print(f"종료된 프로세스: {len(killed_processes)}개")
            time.sleep(2)  # 종료 대기
        else:
            print("종료할 프로세스 없음")
            
    except ImportError:
        print("psutil 라이브러리가 없어서 수동으로 종료해야 합니다.")
        print("Ctrl+C로 기존 서버를 종료하고 다시 실행하세요.")
        return False
    
    return True

def start_server():
    """새 서버 시작"""
    print("새 서버 시작 중...")
    
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    # 환경 변수 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = backend_dir
    
    try:
        # 백그라운드에서 서버 실행
        process = subprocess.Popen(
            [sys.executable, 'app/main.py'],
            cwd=backend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        print(f"서버 프로세스 시작: PID {process.pid}")
        
        # 서버 시작 대기
        for i in range(30):  # 최대 30초 대기
            if check_server_running():
                print(f"서버가 성공적으로 시작되었습니다! ({i+1}초 소요)")
                return True
            time.sleep(1)
            print(f"서버 시작 대기 중... ({i+1}/30)")
        
        print("서버 시작 실패 - 타임아웃")
        return False
        
    except Exception as e:
        print(f"서버 시작 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("=== 백엔드 서버 재시작 ===")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 기존 서버 상태 확인
    if check_server_running():
        print("기존 서버가 실행 중입니다.")
        
        # 2. 기존 서버 종료
        if not kill_existing_server():
            print("기존 서버 종료에 실패했습니다.")
            return False
    else:
        print("실행 중인 서버가 없습니다.")
    
    # 3. 새 서버 시작
    if start_server():
        print("\n=== 서버 재시작 완료 ===")
        print("API 테스트를 진행할 수 있습니다.")
        return True
    else:
        print("\n=== 서버 재시작 실패 ===")
        print("수동으로 서버를 시작해주세요:")
        print("cd backend && python app/main.py")
        return False

if __name__ == "__main__":
    main()