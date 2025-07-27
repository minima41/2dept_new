#!/usr/bin/env python3
"""
D2 Dash v3 빠른 검증 스크립트
서버 없이도 실행 가능한 파일 기반 검증
"""

import json
import os
from datetime import datetime

def verify_frontend_files():
    """프론트엔드 파일 검증"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "file_verification": {},
        "ui_compliance": {},
        "overall_status": "UNKNOWN"
    }
    
    # 필수 파일 확인
    required_files = {
        "static/index.html": "메인 HTML 파일",
        "static/style.css": "CSS 스타일시트",
        "static/script.js": "JavaScript 파일",
        "static/dart.js": "DART JavaScript 파일",
        "app.py": "Flask 메인 애플리케이션",
        "modules/config.py": "설정 파일",
        "modules/stock_monitor.py": "주식 모니터링 모듈",
        "modules/email_utils.py": "이메일 유틸리티",
        "data/monitoring_stocks.json": "주식 데이터",
        "data/daily_history.json": "일일 내역 데이터"
    }
    
    file_status = {}
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    size_kb = len(content) / 1024
                file_status[file_path] = {
                    "exists": True,
                    "size_kb": round(size_kb, 2),
                    "description": description,
                    "status": "PASS"
                }
            except Exception as e:
                file_status[file_path] = {
                    "exists": True,
                    "error": str(e),
                    "description": description,
                    "status": "FAIL"
                }
        else:
            file_status[file_path] = {
                "exists": False,
                "description": description,
                "status": "FAIL"
            }
    
    results["file_verification"] = file_status
    
    # HTML UI 요소 검증
    if os.path.exists("static/index.html"):
        try:
            with open("static/index.html", 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            ui_elements = {
                "메인 탭": ["주식 모니터링", "DART 공시 관리"],
                "서브 탭": ["전체", "메자닌", "주식"],
                "테이블 요소": ["stocks-table", "daily-history-table"],
                "모달 요소": ["add-modal", "modal-overlay"],
                "하단 패널": ["bottom-panels", "logs-container"],
                "버튼 요소": ["종목 추가", "새로고침", "수동 업데이트"],
                "알림 설정": ["알람설정", "price-alert-enabled"],
                "새로고침 주기": ["30초", "60초", "2분", "5분"]
            }
            
            ui_compliance = {}
            for category, elements in ui_elements.items():
                found_count = sum(1 for elem in elements if elem in html_content)
                total_count = len(elements)
                compliance_rate = (found_count / total_count) * 100
                
                ui_compliance[category] = {
                    "found": found_count,
                    "total": total_count,
                    "compliance_rate": compliance_rate,
                    "status": "PASS" if compliance_rate >= 80 else "FAIL"
                }
            
            results["ui_compliance"] = ui_compliance
            
        except Exception as e:
            results["ui_compliance"] = {"error": str(e), "status": "FAIL"}
    
    # CSS 검증
    if os.path.exists("static/style.css"):
        try:
            with open("static/style.css", 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            css_features = [
                "bottom-panels",
                "@media",
                "grid",
                "modal",
                "logs-container",
                "data-table",
                "sub-navigation"
            ]
            
            css_compliance = sum(1 for feature in css_features if feature in css_content)
            css_rate = (css_compliance / len(css_features)) * 100
            
            results["css_verification"] = {
                "features_found": css_compliance,
                "total_features": len(css_features),
                "compliance_rate": css_rate,
                "status": "PASS" if css_rate >= 80 else "FAIL"
            }
            
        except Exception as e:
            results["css_verification"] = {"error": str(e), "status": "FAIL"}
    
    # JavaScript 검증
    if os.path.exists("static/script.js"):
        try:
            with open("static/script.js", 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            js_features = [
                "const api",
                "const ui",
                "const dataLoader",
                "addEventListener",
                "updateDailyHistory",
                "addLog",
                "setupLogRefreshInterval",
                "getDailyHistory"
            ]
            
            js_compliance = sum(1 for feature in js_features if feature in js_content)
            js_rate = (js_compliance / len(js_features)) * 100
            
            results["js_verification"] = {
                "features_found": js_compliance,
                "total_features": len(js_features),
                "compliance_rate": js_rate,
                "status": "PASS" if js_rate >= 80 else "FAIL"
            }
            
        except Exception as e:
            results["js_verification"] = {"error": str(e), "status": "FAIL"}
    
    # 전체 상태 평가
    file_pass_count = sum(1 for status in file_status.values() if status["status"] == "PASS")
    file_pass_rate = (file_pass_count / len(file_status)) * 100
    
    ui_pass_count = sum(1 for status in results["ui_compliance"].values() 
                       if isinstance(status, dict) and status.get("status") == "PASS")
    ui_total = len(results["ui_compliance"])
    ui_pass_rate = (ui_pass_count / ui_total) * 100 if ui_total > 0 else 0
    
    css_pass = results.get("css_verification", {}).get("status") == "PASS"
    js_pass = results.get("js_verification", {}).get("status") == "PASS"
    
    overall_score = (file_pass_rate + ui_pass_rate + (100 if css_pass else 0) + (100 if js_pass else 0)) / 4
    
    if overall_score >= 90:
        results["overall_status"] = "EXCELLENT"
    elif overall_score >= 80:
        results["overall_status"] = "GOOD"
    elif overall_score >= 70:
        results["overall_status"] = "ACCEPTABLE"
    else:
        results["overall_status"] = "NEEDS_IMPROVEMENT"
    
    results["overall_score"] = round(overall_score, 2)
    
    return results

def print_verification_report(results):
    """검증 결과 출력"""
    print("D2 Dash v3 빠른 검증 결과")
    print("=" * 50)
    
    # 파일 검증 결과
    print("\n[파일 검증]")
    file_verification = results["file_verification"]
    pass_count = sum(1 for v in file_verification.values() if v["status"] == "PASS")
    total_count = len(file_verification)
    
    print(f"  통과: {pass_count}/{total_count} ({pass_count/total_count*100:.1f}%)")
    
    for file_path, info in file_verification.items():
        status_icon = "[PASS]" if info["status"] == "PASS" else "[FAIL]"
        if info["exists"]:
            size_info = f" ({info.get('size_kb', 0):.1f}KB)" if info.get('size_kb') else ""
            print(f"  {status_icon} {file_path}{size_info}")
        else:
            print(f"  {status_icon} {file_path} (파일 없음)")
    
    # UI 준수성 결과
    print("\n[UI 준수성]")
    ui_compliance = results["ui_compliance"]
    if isinstance(ui_compliance, dict) and "error" not in ui_compliance:
        ui_pass_count = sum(1 for v in ui_compliance.values() 
                           if isinstance(v, dict) and v.get("status") == "PASS")
        ui_total = len(ui_compliance)
        print(f"  통과: {ui_pass_count}/{ui_total} ({ui_pass_count/ui_total*100:.1f}%)")
        
        for category, info in ui_compliance.items():
            if isinstance(info, dict):
                status_icon = "[PASS]" if info["status"] == "PASS" else "[FAIL]"
                rate = info["compliance_rate"]
                print(f"  {status_icon} {category}: {rate:.1f}% ({info['found']}/{info['total']})")
    else:
        print(f"  [FAIL] UI 검증 실패: {ui_compliance.get('error', '알 수 없는 오류')}")
    
    # CSS/JS 검증 결과
    print("\n[코드 품질]")
    css_info = results.get("css_verification", {})
    if "error" not in css_info:
        css_icon = "[PASS]" if css_info.get("status") == "PASS" else "[FAIL]"
        css_rate = css_info.get("compliance_rate", 0)
        print(f"  {css_icon} CSS: {css_rate:.1f}% ({css_info.get('features_found', 0)}/{css_info.get('total_features', 0)} 기능)")
    else:
        print(f"  [FAIL] CSS 검증 실패: {css_info.get('error')}")
    
    js_info = results.get("js_verification", {})
    if "error" not in js_info:
        js_icon = "[PASS]" if js_info.get("status") == "PASS" else "[FAIL]"
        js_rate = js_info.get("compliance_rate", 0)
        print(f"  {js_icon} JavaScript: {js_rate:.1f}% ({js_info.get('features_found', 0)}/{js_info.get('total_features', 0)} 기능)")
    else:
        print(f"  [FAIL] JavaScript 검증 실패: {js_info.get('error')}")
    
    # 전체 결과
    print(f"\n[전체 평가]")
    score = results["overall_score"]
    status = results["overall_status"]
    status_map = {
        "EXCELLENT": "우수",
        "GOOD": "양호", 
        "ACCEPTABLE": "수용 가능",
        "NEEDS_IMPROVEMENT": "개선 필요"
    }
    
    print(f"  점수: {score:.1f}/100")
    print(f"  등급: {status_map.get(status, status)}")
    
    if score >= 90:
        print("  >> 시스템이 이미지 요구사항을 훌륭히 충족합니다!")
    elif score >= 80:
        print("  >> 시스템이 요구사항을 잘 충족합니다.")
    elif score >= 70:
        print("  >> 시스템이 기본 요구사항을 충족하지만 개선 여지가 있습니다.")
    else:
        print("  >> 시스템 개선이 필요합니다.")

def main():
    print("D2 Dash v3 빠른 검증 시작...")
    
    results = verify_frontend_files()
    
    # 결과 출력
    print_verification_report(results)
    
    # JSON 파일로 저장
    report_file = f"quick_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[리포트] 상세 결과가 {report_file}에 저장되었습니다.")
    
    return results["overall_score"] >= 80

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)