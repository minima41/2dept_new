#!/usr/bin/env python3
"""
WSL2 네트워크 연결 테스트 스크립트
"""
import socket
import subprocess
import sys
import time
import requests

def test_port_listening(host, port):
    """포트가 리스닝 중인지 확인"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Socket error for {host}:{port} - {e}")
        return False

def test_http_endpoint(url):
    """HTTP 엔드포인트 테스트"""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200, response.text[:100]
    except Exception as e:
        return False, str(e)

def get_network_info():
    """네트워크 정보 수집"""
    print("=== 네트워크 정보 ===")
    
    # WSL2 IP 주소
    try:
        result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                              capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if 'inet ' in line and '127.0.0.1' not in line:
                wsl_ip = line.strip().split()[1].split('/')[0]
                print(f"WSL2 IP: {wsl_ip}")
                return wsl_ip
    except Exception as e:
        print(f"WSL2 IP 가져오기 실패: {e}")
    
    return None

def main():
    print("WSL2 네트워크 연결 테스트 시작")
    print("=" * 50)
    
    # 네트워크 정보 수집
    wsl_ip = get_network_info()
    
    # 테스트할 엔드포인트들
    test_targets = [
        ("localhost", 8000),
        ("127.0.0.1", 8000),
        ("0.0.0.0", 8000),
        ("localhost", 3000),
        ("127.0.0.1", 3000),
    ]
    
    if wsl_ip:
        test_targets.extend([
            (wsl_ip, 8000),
            (wsl_ip, 3000),
        ])
    
    print("\n=== 포트 연결 테스트 ===")
    for host, port in test_targets:
        is_open = test_port_listening(host, port)
        status = "✅ OPEN" if is_open else "❌ CLOSED"
        print(f"{host}:{port} - {status}")
    
    print("\n=== HTTP 엔드포인트 테스트 ===")
    http_targets = [
        "http://localhost:8000/health",
        "http://127.0.0.1:8000/health",
        "http://localhost:3000/",
        "http://127.0.0.1:3000/",
    ]
    
    if wsl_ip:
        http_targets.extend([
            f"http://{wsl_ip}:8000/health",
            f"http://{wsl_ip}:3000/",
        ])
    
    for url in http_targets:
        success, response = test_http_endpoint(url)
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{url} - {status}")
        if success:
            print(f"  Response: {response}")
        else:
            print(f"  Error: {response}")
    
    print("\n=== 프로세스 확인 ===")
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if ':8000' in line or ':3000' in line:
                print(line)
    except Exception as e:
        print(f"프로세스 확인 실패: {e}")

if __name__ == "__main__":
    main()