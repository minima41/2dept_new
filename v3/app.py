"""
Flask 백엔드 서버 - 투자본부 모니터링 시스템 v3
DART 공시 모니터링과 주식 가격 추적을 통합 제공하는 웹 서버
"""
import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List

from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS

# 모듈 임포트
from modules.config import (
    FLASK_HOST, 
    FLASK_PORT, 
    FLASK_DEBUG,
    DART_CHECK_INTERVAL,
    STOCK_CHECK_INTERVAL,
    LOG_LEVEL,
    LOGS_DIR
)
from modules.dart_monitor import check_new_disclosures, send_dart_notifications
from modules.stock_monitor import update_all_stocks, get_monitoring_stocks
from modules.email_utils import send_email

# 로깅 설정
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # 모든 origin에서의 요청 허용

# 전역 상태 관리
app_state = {
    'dart_monitoring': False,
    'stock_monitoring': False,
    'last_dart_check': None,
    'last_stock_update': None,
    'dart_alerts_today': 0,
    'stock_alerts_today': 0,
    'system_start_time': datetime.now(),
    'recent_alerts': []  # 최근 알림 목록
}

# 스레드 동시성 제어
state_lock = threading.Lock()
monitoring_threads = {}

def add_alert_to_history(alert_type: str, title: str, message: str, priority: int = 1):
    """알림 히스토리에 추가"""
    with state_lock:
        alert = {
            'id': len(app_state['recent_alerts']) + 1,
            'type': alert_type,  # 'dart', 'stock'
            'title': title,
            'message': message,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        app_state['recent_alerts'].insert(0, alert)  # 최신 순으로 정렬
        
        # 최대 100개까지만 유지
        if len(app_state['recent_alerts']) > 100:
            app_state['recent_alerts'] = app_state['recent_alerts'][:100]
        
        # 오늘 알림 수 업데이트
        if alert_type == 'dart':
            app_state['dart_alerts_today'] += 1
        elif alert_type == 'stock':
            app_state['stock_alerts_today'] += 1

def dart_monitor_thread():
    """DART 모니터링 백그라운드 스레드"""
    logger.info("DART 모니터링 스레드 시작")
    
    with state_lock:
        app_state['dart_monitoring'] = True
    
    while app_state['dart_monitoring']:
        try:
            logger.info("DART 공시 확인 시작")
            
            # 새로운 공시 확인
            new_disclosures = check_new_disclosures()
            
            with state_lock:
                app_state['last_dart_check'] = datetime.now().isoformat()
            
            if new_disclosures:
                logger.info(f"새로운 공시 {len(new_disclosures)}건 발견")
                
                # 이메일 알림 발송
                sent_count = send_dart_notifications(new_disclosures)
                logger.info(f"DART 알림 이메일 {sent_count}건 발송")
                
                # 알림 히스토리에 추가
                for disclosure in new_disclosures:
                    add_alert_to_history(
                        'dart',
                        f"{disclosure['company']} - {disclosure['title'][:50]}...",
                        f"우선순위: {disclosure['priority']}점, 키워드: {', '.join(disclosure['keywords'])}",
                        disclosure['priority']
                    )
            else:
                logger.info("새로운 공시 없음")
            
            # 다음 체크까지 대기
            time.sleep(DART_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"DART 모니터링 오류: {e}")
            time.sleep(60)  # 오류 시 1분 후 재시도
    
    logger.info("DART 모니터링 스레드 종료")

def stock_monitor_thread():
    """주식 모니터링 백그라운드 스레드"""
    logger.info("주식 모니터링 스레드 시작")
    
    with state_lock:
        app_state['stock_monitoring'] = True
    
    while app_state['stock_monitoring']:
        try:
            logger.info("주식 가격 업데이트 시작")
            
            # 모든 종목 가격 업데이트
            updated_stocks = update_all_stocks()
            
            with state_lock:
                app_state['last_stock_update'] = datetime.now().isoformat()
            
            # 알림이 발생한 종목 확인
            alert_count = 0
            for stock_code, stock_info in updated_stocks.items():
                if stock_info.get('triggered_alerts'):
                    alert_count += len(stock_info['triggered_alerts'])
                    
                    # 알림 히스토리에 추가 (간단화)
                    add_alert_to_history(
                        'stock',
                        f"{stock_info.get('name', stock_code)} 가격 알림",
                        f"현재가: {stock_info.get('current_price', 0):,}원 ({stock_info.get('change_percent', 0):+.2f}%)",
                        2
                    )
            
            if alert_count > 0:
                logger.info(f"주식 알림 {alert_count}건 발생")
            
            # 다음 업데이트까지 대기
            time.sleep(STOCK_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"주식 모니터링 오류: {e}")
            time.sleep(30)  # 오류 시 30초 후 재시도
    
    logger.info("주식 모니터링 스레드 종료")

# === API 엔드포인트 ===

@app.route('/')
def index():
    """메인 페이지"""
    return send_from_directory('static', 'index.html')

@app.route('/dart')
def dart_page():
    """DART 관리 페이지"""
    import os
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, 'dart.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """정적 파일 서빙"""
    return send_from_directory('static', filename)

@app.route('/api/status')
def get_status():
    """시스템 상태 조회"""
    with state_lock:
        status = {
            'system': {
                'status': 'running',
                'uptime_seconds': int((datetime.now() - app_state['system_start_time']).total_seconds()),
                'start_time': app_state['system_start_time'].isoformat()
            },
            'dart_monitoring': {
                'enabled': app_state['dart_monitoring'],
                'last_check': app_state['last_dart_check'],
                'alerts_today': app_state['dart_alerts_today'],
                'check_interval': DART_CHECK_INTERVAL
            },
            'stock_monitoring': {
                'enabled': app_state['stock_monitoring'],
                'last_update': app_state['last_stock_update'],
                'alerts_today': app_state['stock_alerts_today'],
                'update_interval': STOCK_CHECK_INTERVAL
            },
            'monitoring_stocks_count': len(get_monitoring_stocks()),
            'recent_alerts_count': len(app_state['recent_alerts'])
        }
    
    return jsonify(status)

@app.route('/api/stocks')
def get_stocks():
    """모니터링 주식 목록 조회"""
    try:
        stocks = get_monitoring_stocks()
        
        # JSON 직렬화를 위해 set을 list로 변환
        serializable_stocks = {}
        for code, info in stocks.items():
            serializable_info = info.copy()
            if 'triggered_alerts' in serializable_info and isinstance(serializable_info['triggered_alerts'], set):
                serializable_info['triggered_alerts'] = list(serializable_info['triggered_alerts'])
            serializable_stocks[code] = serializable_info
        
        return jsonify({
            'success': True,
            'stocks': serializable_stocks,
            'count': len(serializable_stocks)
        })
        
    except Exception as e:
        logger.error(f"주식 목록 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stocks/update', methods=['POST'])
def update_stocks():
    """주식 가격 수동 업데이트"""
    try:
        updated_stocks = update_all_stocks()
        
        return jsonify({
            'success': True,
            'message': f'{len(updated_stocks)}개 종목 업데이트 완료',
            'updated_count': len(updated_stocks),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"주식 업데이트 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dart/check', methods=['POST'])
def check_dart():
    """DART 공시 수동 확인"""
    try:
        new_disclosures = check_new_disclosures()
        
        if new_disclosures:
            # 알림 발송
            sent_count = send_dart_notifications(new_disclosures)
            
            # 히스토리 업데이트
            for disclosure in new_disclosures:
                add_alert_to_history(
                    'dart',
                    f"{disclosure['company']} - {disclosure['title'][:50]}...",
                    f"우선순위: {disclosure['priority']}점",
                    disclosure['priority']
                )
            
            return jsonify({
                'success': True,
                'message': f'새로운 공시 {len(new_disclosures)}건 발견',
                'disclosures': new_disclosures,
                'notifications_sent': sent_count
            })
        else:
            return jsonify({
                'success': True,
                'message': '새로운 공시가 없습니다',
                'disclosures': [],
                'notifications_sent': 0
            })
            
    except Exception as e:
        logger.error(f"DART 확인 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/alerts')
def get_alerts():
    """통합 알림 목록 조회"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        alert_type = request.args.get('type', 'all')  # 'all', 'dart', 'stock'
        
        with state_lock:
            alerts = app_state['recent_alerts'].copy()
        
        # 타입 필터링
        if alert_type != 'all':
            alerts = [alert for alert in alerts if alert['type'] == alert_type]
        
        # 페이지네이션
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_alerts = alerts[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'alerts': page_alerts,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(alerts),
                'has_next': end_idx < len(alerts)
            }
        })
        
    except Exception as e:
        logger.error(f"알림 목록 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/alerts/<int:alert_id>/read', methods=['PATCH'])
def mark_alert_read(alert_id):
    """알림 읽음 처리"""
    try:
        with state_lock:
            for alert in app_state['recent_alerts']:
                if alert['id'] == alert_id:
                    alert['read'] = True
                    return jsonify({
                        'success': True,
                        'message': '알림을 읽음으로 처리했습니다'
                    })
        
        return jsonify({
            'success': False,
            'error': '해당 알림을 찾을 수 없습니다'
        }), 404
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === DART 관련 API 엔드포인트 ===

@app.route('/api/dart/companies')
def get_dart_companies():
    """DART 관심 기업 목록 조회"""
    try:
        from modules.config import COMPANIES
        
        companies_list = [
            {
                'code': code,
                'name': name,
                'enabled': True  # 기본적으로 모든 기업 활성화
            }
            for code, name in COMPANIES.items()
        ]
        
        return jsonify({
            'success': True,
            'companies': companies_list,
            'count': len(companies_list)
        })
        
    except Exception as e:
        logger.error(f"DART 기업 목록 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dart/keywords')
def get_dart_keywords():
    """DART 키워드 목록 조회"""
    try:
        from modules.config import KEYWORDS, IMPORTANT_SECTIONS
        
        return jsonify({
            'success': True,
            'keywords': KEYWORDS,
            'important_sections': IMPORTANT_SECTIONS,
            'keyword_count': len(KEYWORDS),
            'section_count': len(IMPORTANT_SECTIONS)
        })
        
    except Exception as e:
        logger.error(f"DART 키워드 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dart/disclosures')
def get_dart_disclosures():
    """최근 DART 공시 목록 조회"""
    try:
        date_filter = request.args.get('date')  # YYYYMMDD 형식
        company_code = request.args.get('company')
        limit = request.args.get('limit', 50, type=int)
        
        # DART 모니터링 모듈에서 공시 조회
        disclosures = check_new_disclosures(target_date=date_filter)
        
        if company_code:
            disclosures = [d for d in disclosures if d.get('corp_code') == company_code]
        
        # 제한된 개수만 반환
        limited_disclosures = disclosures[:limit]
        
        return jsonify({
            'success': True,
            'disclosures': limited_disclosures,
            'count': len(limited_disclosures),
            'total': len(disclosures)
        })
        
    except Exception as e:
        logger.error(f"DART 공시 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'disclosures': [],
            'count': 0
        }), 500

@app.route('/api/dart/check', methods=['POST'])
def manual_dart_check():
    """수동 DART 공시 확인"""
    try:
        # 수동으로 공시 확인 실행
        new_disclosures = check_new_disclosures()
        
        # 결과를 알림 히스토리에 추가
        if new_disclosures:
            for disclosure in new_disclosures:
                add_alert_to_history(
                    'dart',
                    f"{disclosure.get('corp_name', 'Unknown')} 공시",
                    disclosure.get('report_nm', ''),
                    3  # high priority
                )
        
        return jsonify({
            'success': True,
            'message': f'DART 공시 확인 완료: {len(new_disclosures)}개 발견',
            'new_disclosures': len(new_disclosures),
            'disclosures': new_disclosures[:10]  # 최대 10개만 반환
        })
        
    except Exception as e:
        logger.error(f"수동 DART 확인 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dart/processed-ids')
def get_processed_ids():
    """처리된 공시 ID 목록 조회"""
    try:
        from modules.dart_monitor import get_processed_ids
        
        processed_ids = get_processed_ids()
        
        return jsonify({
            'success': True,
            'processed_ids': list(processed_ids),
            'count': len(processed_ids)
        })
        
    except Exception as e:
        logger.error(f"처리된 ID 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test/email', methods=['POST'])
def test_email():
    """이메일 발송 테스트"""
    try:
        data = request.get_json() or {}
        subject = data.get('subject', '[테스트] 투자본부 모니터링 시스템')
        message = data.get('message', '이메일 발송 테스트입니다.')
        
        success = send_email(subject, message)
        
        if success:
            return jsonify({
                'success': True,
                'message': '테스트 이메일이 발송되었습니다'
            })
        else:
            return jsonify({
                'success': False,
                'error': '이메일 발송에 실패했습니다'
            }), 500
            
    except Exception as e:
        logger.error(f"이메일 테스트 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def start_monitoring_threads():
    """백그라운드 모니터링 스레드 시작"""
    global monitoring_threads
    
    # DART 모니터링 스레드
    dart_thread = threading.Thread(target=dart_monitor_thread, daemon=True)
    dart_thread.start()
    monitoring_threads['dart'] = dart_thread
    
    # 주식 모니터링 스레드  
    stock_thread = threading.Thread(target=stock_monitor_thread, daemon=True)
    stock_thread.start()
    monitoring_threads['stock'] = stock_thread
    
    logger.info("모든 백그라운드 모니터링 스레드 시작 완료")

def stop_monitoring_threads():
    """백그라운드 모니터링 스레드 종료"""
    with state_lock:
        app_state['dart_monitoring'] = False
        app_state['stock_monitoring'] = False
    
    logger.info("모니터링 스레드 종료 신호 전송")

if __name__ == '__main__':
    try:
        logger.info("투자본부 모니터링 시스템 v3 시작")
        logger.info(f"서버 주소: http://{FLASK_HOST}:{FLASK_PORT}")
        
        # 백그라운드 모니터링 스레드 시작
        start_monitoring_threads()
        
        # Flask 서버 시작
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            use_reloader=False,  # 백그라운드 스레드 중복 방지
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("사용자에 의한 종료 요청")
    except Exception as e:
        logger.error(f"서버 시작 오류: {e}")
    finally:
        stop_monitoring_threads()
        logger.info("투자본부 모니터링 시스템 v3 종료")