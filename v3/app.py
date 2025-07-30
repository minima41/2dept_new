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

from flask import Flask, jsonify, request, send_from_directory, render_template_string, session, redirect, url_for
from flask_cors import CORS
from flask_session import Session
import secrets

# 모듈 임포트
from modules.config import (
    FLASK_HOST, 
    FLASK_PORT, 
    FLASK_DEBUG,
    DART_CHECK_INTERVAL,
    STOCK_CHECK_INTERVAL,
    STOCK_MARKET_OPEN_TIME,
    STOCK_MARKET_CLOSE_TIME,
    LOG_LEVEL,
    LOGS_DIR
)
from modules.dart_monitor import check_new_disclosures, send_dart_notifications
from modules.stock_monitor import update_all_stocks, get_monitoring_stocks, stock_monitor
from modules.email_utils import send_email, send_test_email

# 개선된 로깅 시스템 설정
from modules.logger_utils import get_logger, performance_monitor, api_request_logger, log_exception

# 인증 시스템 임포트
from modules.auth import (
    auth_manager, login_user, logout_user, is_logged_in, 
    get_current_user, is_admin, login_required, admin_required
)

# 로거 인스턴스들
logger = get_logger('app')
dart_logger = get_logger('dart')
stock_logger = get_logger('stock')
email_logger = get_logger('email')
websocket_logger = get_logger('websocket')
error_logger = get_logger('error')
performance_logger = get_logger('performance')

# Flask 앱 초기화
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # 모든 origin에서의 요청 허용

# Flask-Session 설정
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), 'data', 'sessions')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'd2dash:'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# 세션 디렉터리 생성
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Session 초기화
Session(app)

# === 전역 에러 핸들러 ===

@app.errorhandler(404)
def not_found_error(error):
    """404 에러 핸들러"""
    error_logger.warning(
        "404 에러 발생",
        url=request.url,
        method=request.method,
        user_agent=request.headers.get('User-Agent', 'Unknown'),
        remote_addr=request.remote_addr
    )
    return jsonify({
        'success': False,
        'error': 'Resource not found',
        'error_code': 'NOT_FOUND',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    error_logger.error(
        "500 내부 서버 에러",
        url=request.url,
        method=request.method,
        error_message=str(error),
        error_type=type(error).__name__,
        remote_addr=request.remote_addr
    )
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'error_code': 'INTERNAL_ERROR',
        'timestamp': datetime.now().isoformat()
    }), 500

@app.errorhandler(400)
def bad_request_error(error):
    """400 에러 핸들러"""
    request_data = request.get_data(as_text=True)[:200] if request.get_data() else 'None'
    
    error_logger.warning(
        "400 잘못된 요청",
        url=request.url,
        method=request.method,
        error_message=str(error),
        request_data=request_data,
        content_type=request.content_type,
        remote_addr=request.remote_addr
    )
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'error_code': 'BAD_REQUEST',
        'timestamp': datetime.now().isoformat()
    }), 400

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """예상치 못한 에러 핸들러"""
    error_logger.critical(
        "예상치 못한 서버 에러",
        url=request.url,
        method=request.method,
        error_message=str(error),
        error_type=type(error).__name__,
        remote_addr=request.remote_addr,
        traceback=True
    )
    
    # 개발 환경에서는 상세한 에러 정보 제공
    error_detail = str(error) if app.debug else "An unexpected error occurred"
    
    return jsonify({
        'success': False,
        'error': error_detail,
        'error_code': 'UNEXPECTED_ERROR',
        'error_type': type(error).__name__,
        'timestamp': datetime.now().isoformat()
    }), 500

def create_error_response(error_message: str, error_code: str = 'API_ERROR', status_code: int = 500):
    """표준 에러 응답 생성 함수"""
    error_logger.error(
        f"API 에러 생성",
        error_code=error_code,
        error_message=error_message,
        status_code=status_code,
        url=request.url,
        method=request.method,
        remote_addr=request.remote_addr
    )
    return jsonify({
        'success': False,
        'error': error_message,
        'error_code': error_code,
        'timestamp': datetime.now().isoformat()
    }), status_code

def create_success_response(data=None, message: str = None):
    """표준 성공 응답 생성 함수"""
    response = {
        'success': True,
        'timestamp': datetime.now().isoformat()
    }
    
    if data is not None:
        response.update(data)
    
    if message:
        response['message'] = message
    
    return jsonify(response)

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

@log_exception('app')
def dart_monitor_thread():
    """DART 모니터링 백그라운드 스레드"""
    dart_logger.info("DART 모니터링 스레드 시작", thread_name="dart_monitor")
    
    with state_lock:
        app_state['dart_monitoring'] = True
    
    while app_state['dart_monitoring']:
        try:
            dart_logger.info("DART 공시 확인 시작", check_interval=DART_CHECK_INTERVAL)
            
            # 새로운 공시 확인
            new_disclosures = check_new_disclosures()
            
            with state_lock:
                app_state['last_dart_check'] = datetime.now().isoformat()
            
            if new_disclosures:
                dart_logger.info("새로운 공시 발견", 
                    disclosure_count=len(new_disclosures),
                    companies=[d.get('corp_name', 'Unknown') for d in new_disclosures[:3]]  # 최대 3개만 표시
                )
                
                # 이메일 알림 발송
                sent_count = send_dart_notifications(new_disclosures)
                email_logger.info("DART 알림 이메일 발송", sent_count=sent_count, requested_count=len(new_disclosures))
                
                # 알림 히스토리에 추가
                for disclosure in new_disclosures:
                    # 키워드 정보 가져오기
                    keyword_info = disclosure.get('keyword_info', {})
                    keywords_text = ', '.join(disclosure['keywords'])
                    
                    # AND 조건이 매칭된 경우 별도 표시
                    if keyword_info.get('and_groups'):
                        keywords_text += f" [AND: {', '.join(['+'.join(group) for group in keyword_info['and_groups']])}]"
                    
                    add_alert_to_history(
                        'dart',
                        f"{disclosure['company']} - {disclosure['title'][:50]}...",
                        f"우선순위: {disclosure['priority']}점, 키워드: {keywords_text}, 조건: {keyword_info.get('filter_mode', 'OR')}",
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

@log_exception('app')
def stock_monitor_thread():
    """주식 모니터링 백그라운드 스레드"""
    stock_logger.info("주식 모니터링 스레드 시작", thread_name="stock_monitor")
    
    with state_lock:
        app_state['stock_monitoring'] = True
    
    while app_state['stock_monitoring']:
        try:
            stock_logger.info("주식 가격 업데이트 시작", 
                update_interval=STOCK_CHECK_INTERVAL,
                market_hours=f"{STOCK_MARKET_OPEN_TIME}-{STOCK_MARKET_CLOSE_TIME}"
            )
            
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
                stock_logger.info("주식 가격 알림 발생", 
                    alert_count=alert_count,
                    updated_stocks_count=len(updated_stocks)
                )
            
            # 다음 업데이트까지 대기
            time.sleep(STOCK_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"주식 모니터링 오류: {e}")
            time.sleep(30)  # 오류 시 30초 후 재시도
    
    logger.info("주식 모니터링 스레드 종료")

# === 인증 관련 API 엔드포인트 ===

@app.route('/login')
def login_page():
    """로그인 페이지"""
    if is_logged_in():
        return redirect('/')
    
    login_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>D2 Dash - 로그인</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; height: 100vh; display: flex; align-items: center; justify-content: center; }
            .login-container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
            .login-header { text-align: center; margin-bottom: 2rem; }
            .login-header h1 { color: #333; margin: 0; font-size: 1.8rem; }
            .login-header p { color: #666; margin: 0.5rem 0 0 0; }
            .form-group { margin-bottom: 1rem; }
            .form-group label { display: block; margin-bottom: 0.5rem; font-weight: bold; color: #333; }
            .form-group input { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem; box-sizing: border-box; }
            .form-group input:focus { outline: none; border-color: #667eea; }
            .login-btn { width: 100%; padding: 0.75rem; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer; transition: background 0.3s; }
            .login-btn:hover { background: #5a6fd8; }
            .register-link { text-align: center; margin-top: 1rem; }
            .register-link a { color: #667eea; text-decoration: none; }
            .error-msg { color: red; margin-top: 1rem; text-align: center; }
            .success-msg { color: green; margin-top: 1rem; text-align: center; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>D2 Dash</h1>
                <p>투자본부 모니터링 시스템</p>
            </div>
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">사용자명</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">비밀번호</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">로그인</button>
            </form>
            <div class="register-link">
                <a href="/register">회원가입</a>
            </div>
            <div id="message"></div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const messageDiv = document.getElementById('message');
                
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        messageDiv.innerHTML = '<div class="success-msg">로그인 성공! 리디렉션 중...</div>';
                        setTimeout(() => window.location.href = '/', 1000);
                    } else {
                        messageDiv.innerHTML = '<div class="error-msg">' + result.error + '</div>';
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="error-msg">로그인 중 오류가 발생했습니다.</div>';
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(login_html)

@app.route('/register')
def register_page():
    """회원가입 페이지"""
    if is_logged_in():
        return redirect('/')
    
    register_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>D2 Dash - 회원가입</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .register-container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
            .register-header { text-align: center; margin-bottom: 2rem; }
            .register-header h1 { color: #333; margin: 0; font-size: 1.8rem; }
            .register-header p { color: #666; margin: 0.5rem 0 0 0; }
            .form-group { margin-bottom: 1rem; }
            .form-group label { display: block; margin-bottom: 0.5rem; font-weight: bold; color: #333; }
            .form-group input { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem; box-sizing: border-box; }
            .form-group input:focus { outline: none; border-color: #667eea; }
            .register-btn { width: 100%; padding: 0.75rem; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer; transition: background 0.3s; }
            .register-btn:hover { background: #5a6fd8; }
            .login-link { text-align: center; margin-top: 1rem; }
            .login-link a { color: #667eea; text-decoration: none; }
            .error-msg { color: red; margin-top: 1rem; text-align: center; }
            .success-msg { color: green; margin-top: 1rem; text-align: center; }
            .info-msg { color: #666; margin-top: 1rem; text-align: center; font-size: 0.9rem; }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="register-header">
                <h1>D2 Dash</h1>
                <p>회원가입</p>
            </div>
            <form id="registerForm">
                <div class="form-group">
                    <label for="username">사용자명</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="email">이메일</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="password">비밀번호</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div class="form-group">
                    <label for="password_confirm">비밀번호 확인</label>
                    <input type="password" id="password_confirm" name="password_confirm" required>
                </div>
                <button type="submit" class="register-btn">가입신청</button>
            </form>
            <div class="login-link">
                <a href="/login">로그인으로 돌아가기</a>
            </div>
            <div class="info-msg">
                회원가입 후 관리자 승인이 필요합니다.
            </div>
            <div id="message"></div>
        </div>
        
        <script>
            document.getElementById('registerForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const passwordConfirm = document.getElementById('password_confirm').value;
                const messageDiv = document.getElementById('message');
                
                if (password !== passwordConfirm) {
                    messageDiv.innerHTML = '<div class="error-msg">비밀번호가 일치하지 않습니다.</div>';
                    return;
                }
                
                try {
                    const response = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, email, password })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        messageDiv.innerHTML = '<div class="success-msg">가입신청이 완료되었습니다. 관리자 승인을 기다려주세요.</div>';
                        document.getElementById('registerForm').reset();
                    } else {
                        messageDiv.innerHTML = '<div class="error-msg">' + result.error + '</div>';
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="error-msg">회원가입 중 오류가 발생했습니다.</div>';
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(register_html)

@app.route('/admin')
@admin_required
def admin_page():
    """관리자 페이지"""
    admin_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>D2 Dash - 관리자</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #eee; }
            .nav-links a { color: #667eea; text-decoration: none; margin-left: 1rem; }
            .section { margin-bottom: 2rem; }
            .section h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 0.5rem; }
            .user-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            .user-table th, .user-table td { padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }
            .user-table th { background: #f8f9fa; font-weight: bold; }
            .status-pending { color: orange; font-weight: bold; }
            .status-active { color: green; font-weight: bold; }
            .status-inactive { color: red; font-weight: bold; }
            .btn { padding: 0.5rem 1rem; border: none; border-radius: 3px; cursor: pointer; font-size: 0.9rem; }
            .btn-approve { background: #28a745; color: white; }
            .btn-reject { background: #dc3545; color: white; }
            .btn-deactivate { background: #6c757d; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>D2 Dash 관리자</h1>
                <div>
                    <span>환영합니다, {{ session.username }}님</span>
                    <a href="/">대시보드</a>
                    <a href="/logout">로그아웃</a>
                </div>
            </div>
            
            <div class="section">
                <h2>사용자 관리</h2>
                <div id="userList">
                    <div style="text-align: center; padding: 2rem;">로딩 중...</div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadUsers() {
                try {
                    const response = await fetch('/api/auth/admin/users');
                    const result = await response.json();
                    
                    if (result.success) {
                        displayUsers(result.users);
                    } else {
                        document.getElementById('userList').innerHTML = '<div style="color: red;">사용자 목록을 불러올 수 없습니다.</div>';
                    }
                } catch (error) {
                    document.getElementById('userList').innerHTML = '<div style="color: red;">오류가 발생했습니다.</div>';
                }
            }
            
            function displayUsers(users) {
                const userList = document.getElementById('userList');
                
                if (users.length === 0) {
                    userList.innerHTML = '<div>등록된 사용자가 없습니다.</div>';
                    return;
                }
                
                let html = '<table class="user-table">';
                html += '<thead><tr><th>사용자명</th><th>이메일</th><th>역할</th><th>상태</th><th>가입일</th><th>마지막 로그인</th><th>관리</th></tr></thead><tbody>';
                
                users.forEach(user => {
                    const statusClass = user.status === 'pending' ? 'status-pending' : 
                                      user.status === 'active' ? 'status-active' : 'status-inactive';
                    const createdAt = new Date(user.created_at).toLocaleDateString('ko-KR');
                    const lastLogin = user.last_login ? new Date(user.last_login).toLocaleDateString('ko-KR') : '없음';
                    
                    html += '<tr>';
                    html += '<td>' + user.username + '</td>';
                    html += '<td>' + user.email + '</td>';
                    html += '<td>' + user.role + '</td>';
                    html += '<td class="' + statusClass + '">' + user.status + '</td>';
                    html += '<td>' + createdAt + '</td>';
                    html += '<td>' + lastLogin + '</td>';
                    html += '<td>';
                    
                    if (user.status === 'pending') {
                        html += '<button class="btn btn-approve" onclick="updateUserStatus(\'' + user.id + '\', \'active\')">승인</button> ';
                        html += '<button class="btn btn-reject" onclick="updateUserStatus(\'' + user.id + '\', \'inactive\')">거부</button>';
                    } else if (user.status === 'active' && user.role !== 'admin') {
                        html += '<button class="btn btn-deactivate" onclick="updateUserStatus(\'' + user.id + '\', \'inactive\')">비활성화</button>';
                    } else if (user.status === 'inactive') {
                        html += '<button class="btn btn-approve" onclick="updateUserStatus(\'' + user.id + '\', \'active\')">활성화</button>';
                    }
                    
                    html += '</td>';
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                userList.innerHTML = html;
            }
            
            async function updateUserStatus(userId, status) {
                try {
                    const response = await fetch('/api/auth/admin/users/' + userId + '/status', {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: status })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        loadUsers(); // 목록 새로고침
                    } else {
                        alert('상태 업데이트에 실패했습니다: ' + result.error);
                    }
                } catch (error) {
                    alert('오류가 발생했습니다.');
                }
            }
            
            // 페이지 로드 시 사용자 목록 불러오기
            loadUsers();
        </script>
    </body>
    </html>
    """
    return render_template_string(admin_html)

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """로그인 API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '요청 데이터가 없습니다'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        # 사용자 인증
        user = auth_manager.authenticate(username, password)
        
        # 로그인 처리
        login_user(user)
        
        return jsonify({
            'success': True,
            'message': '로그인 성공',
            'user': {
                'username': user['username'],
                'role': user['role']
            }
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 401
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        return jsonify({'success': False, 'error': '로그인 중 오류가 발생했습니다'}), 500

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """회원가입 API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '요청 데이터가 없습니다'}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'success': False, 'error': '모든 필드를 입력해주세요'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': '비밀번호는 6자 이상이어야 합니다'}), 400
        
        # 사용자 생성
        new_user = auth_manager.create_user(username, password, email)
        
        return jsonify({
            'success': True,
            'message': '회원가입이 완료되었습니다. 관리자 승인을 기다려주세요.',
            'user_id': new_user['id']
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"회원가입 오류: {e}")
        return jsonify({'success': False, 'error': '회원가입 중 오류가 발생했습니다'}), 500

@app.route('/logout')
def logout():
    """로그아웃"""
    logout_user()
    return redirect('/login')

@app.route('/api/auth/status')
def auth_status():
    """인증 상태 확인"""
    if is_logged_in():
        user = get_current_user()
        return jsonify({
            'authenticated': True,
            'user': {
                'username': user['username'] if user else session.get('username'),
                'role': user['role'] if user else session.get('role')
            }
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/api/auth/admin/users')
@admin_required
def admin_get_users():
    """관리자용 사용자 목록 조회"""
    try:
        users = auth_manager.get_all_users()
        # 비밀번호 해시 제거
        safe_users = []
        for user in users:
            safe_user = user.copy()
            safe_user.pop('password_hash', None)
            safe_users.append(safe_user)
        
        return jsonify({
            'success': True,
            'users': safe_users
        })
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/admin/users/<user_id>/status', methods=['PATCH'])
@admin_required
def admin_update_user_status(user_id):
    """관리자용 사용자 상태 업데이트"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '요청 데이터가 없습니다'}), 400
        
        new_status = data.get('status')
        if new_status not in ['active', 'inactive', 'pending']:
            return jsonify({'success': False, 'error': '유효하지 않은 상태입니다'}), 400
        
        success = auth_manager.update_user_status(user_id, new_status)
        
        if success:
            return jsonify({
                'success': True,
                'message': '사용자 상태가 업데이트되었습니다'
            })
        else:
            return jsonify({'success': False, 'error': '사용자를 찾을 수 없습니다'}), 404
            
    except Exception as e:
        logger.error(f"사용자 상태 업데이트 오류: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# === API 엔드포인트 ===

@app.route('/')
@login_required
def index():
    """메인 페이지"""
    return send_from_directory('static', 'index.html')

@app.route('/dart')
@login_required
def dart_page():
    """DART 관리 페이지"""
    import os
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, 'dart.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """정적 파일 서빙"""
    return send_from_directory('static', filename)

@app.route('/api/v1/status')
@performance_monitor('시스템 상태 조회')
@api_request_logger
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

@app.route('/api/v1/stocks')
@performance_monitor('주식 목록 조회')
@api_request_logger
def get_stocks():
    """모니터링 주식 목록 조회 (메타데이터 포함)"""
    try:
        # 강제 새로고침 파라미터 확인
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # 메타데이터와 함께 주식 데이터 로드
        try:
            with open(os.path.join(DATA_DIR, 'monitoring_stocks.json'), 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            # 새로운 형식(메타데이터 포함) 확인
            if '_metadata' in file_data and 'stocks' in file_data:
                metadata = file_data['_metadata']
                stocks = file_data['stocks']
            else:
                # 기존 형식인 경우 기본 메타데이터 생성
                stocks = file_data
                metadata = {
                    'last_updated': datetime.now().isoformat(),
                    'update_count': 0,
                    'total_stocks': len(stocks),
                    'enabled_stocks': len([code for code, info in stocks.items() if info.get('enabled', True)]),
                    'data_version': '1.0'
                }
        except (FileNotFoundError, json.JSONDecodeError):
            # 파일이 없거나 잘못된 경우 빈 데이터 반환
            stocks = {}
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'update_count': 0,
                'total_stocks': 0,
                'enabled_stocks': 0,
                'data_version': '1.0'
            }
        
        # 강제 새로고침이 요청된 경우 주가 업데이트 수행
        if force_refresh:
            try:
                update_all_stocks()
                # 업데이트 후 데이터 다시 로드
                with open(os.path.join(DATA_DIR, 'monitoring_stocks.json'), 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                if '_metadata' in file_data and 'stocks' in file_data:
                    metadata = file_data['_metadata']
                    stocks = file_data['stocks']
                else:
                    stocks = file_data
            except Exception as e:
                logger.warning(f"강제 새로고침 실패: {e}")
        
        # JSON 직렬화를 위해 set을 list로 변환
        serializable_stocks = {}
        for code, info in stocks.items():
            serializable_info = info.copy()
            if 'triggered_alerts' in serializable_info and isinstance(serializable_info['triggered_alerts'], set):
                serializable_info['triggered_alerts'] = list(serializable_info['triggered_alerts'])
            serializable_stocks[code] = serializable_info
        
        return create_success_response({
            'metadata': metadata,
            'stocks': serializable_stocks,
            'count': len(serializable_stocks)
        })
        
    except Exception as e:
        return create_error_response(str(e), 'STOCKS_FETCH_ERROR')

@app.route('/api/v1/stocks/update', methods=['POST'])
@performance_monitor('주식 가격 업데이트')
@api_request_logger
def update_stocks():
    """주식 가격 수동 업데이트"""
    try:
        updated_stocks = update_all_stocks()
        
        return create_success_response({
            'updated_count': len(updated_stocks)
        }, f'{len(updated_stocks)}개 종목 업데이트 완료')
        
    except Exception as e:
        return create_error_response(str(e), 'STOCKS_UPDATE_ERROR')

@app.route('/api/v1/dart/check', methods=['POST'])
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

@app.route('/api/v1/alerts')
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

@app.route('/api/v1/alerts/<int:alert_id>/read', methods=['PATCH'])
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

@app.route('/api/v1/dart/companies')
@performance_monitor('DART 기업 목록 조회')
@api_request_logger
def get_dart_companies():
    """DART 관심 기업 목록 조회"""
    try:
        from modules.dart_monitor import dart_monitor
        
        companies = dart_monitor.load_dart_companies()
        
        companies_list = [
            {
                'code': code,
                'name': name,
                'enabled': True  # 기본적으로 모든 기업 활성화
            }
            for code, name in companies.items()
        ]
        
        return create_success_response(
            {
                'companies': companies_list,
                'count': len(companies_list)
            },
            f'DART 기업 목록 {len(companies_list)}개 조회 완료'
        )
        
    except Exception as e:
        return create_error_response(str(e), 'DART_COMPANIES_ERROR')

@app.route('/api/v1/dart/keywords')
@performance_monitor('DART 키워드 목록 조회')
@api_request_logger
def get_dart_keywords():
    """DART 키워드 목록 조회"""
    try:
        from modules.dart_monitor import dart_monitor
        from modules.config import IMPORTANT_SECTIONS
        
        keywords = dart_monitor.load_dart_keywords()
        
        return create_success_response(
            {
                'keywords': keywords,
                'important_sections': IMPORTANT_SECTIONS,
                'keyword_count': len(keywords),
                'section_count': len(IMPORTANT_SECTIONS)
            },
            f'DART 키워드 목록 {len(keywords)}개 조회 완료'
        )
        
    except Exception as e:
        return create_error_response(str(e), 'DART_KEYWORDS_ERROR')

@app.route('/api/v1/dart/disclosures')
@performance_monitor('DART 공시 조회')
@api_request_logger
def get_dart_disclosures():
    """최근 DART 공시 목록 조회"""
    try:
        from modules.dart_monitor import validate_date_format, get_default_date_range
        
        date_filter = request.args.get('date')  # YYYYMMDD 형식
        company_code = request.args.get('company')
        limit = request.args.get('limit', 50, type=int)
        
        # 날짜 검증 및 기본값 설정
        if date_filter:
            if not validate_date_format(date_filter):
                return create_error_response(
                    f"잘못된 날짜 형식입니다. YYYYMMDD 형식으로 입력해주세요: {date_filter}",
                    'INVALID_DATE_FORMAT',
                    400
                )
        else:
            # 기본값: 오늘 날짜
            from datetime import date as date_lib
            date_filter = date_lib.today().strftime("%Y%m%d")
            logger.info(f"날짜 파라미터 없음, 기본값 사용: {date_filter}")
        
        # DART 모니터링 모듈에서 공시 조회
        disclosures = check_new_disclosures(target_date=date_filter)
        
        if company_code:
            disclosures = [d for d in disclosures if d.get('corp_code') == company_code]
        
        # 제한된 개수만 반환
        limited_disclosures = disclosures[:limit]
        
        return create_success_response({
            'disclosures': limited_disclosures,
            'count': len(limited_disclosures),
            'total': len(disclosures),
            'date_used': date_filter,
            'is_default_date': date_filter == date_lib.today().strftime("%Y%m%d")
        })
        
    except Exception as e:
        return create_error_response(str(e), 'DART_DISCLOSURES_ERROR')

@app.route('/api/v1/dart/check', methods=['POST'])
@performance_monitor('수동 DART 확인')
@api_request_logger
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

@app.route('/api/v1/dart/processed-ids')
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


@app.route('/api/v1/test/post', methods=['POST'])
def test_post():
    """POST 메서드 테스트"""
    return jsonify({
        'success': True,
        'message': 'POST 요청이 정상적으로 처리되었습니다',
        'data': request.get_json()
    })

# === 종목 관리 API 엔드포인트 ===

@app.route('/api/v1/stocks/add', methods=['POST'])
@login_required
@performance_monitor('종목 추가')
@api_request_logger
def add_stock():
    """새 종목 추가 (확장된 스키마 지원)"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        # 기본 필드
        stock_code = data.get('stock_code', '').strip()
        stock_name = data.get('stock_name', '').strip()
        target_price = data.get('target_price')
        stop_loss = data.get('stop_loss')
        category = data.get('category', '주식').strip()
        
        # 확장된 필드
        acquisition_price = data.get('acquisition_price', 0)
        conversion_price = data.get('conversion_price', 0)  # 메자닌 전환가
        memo = data.get('memo', '').strip()
        alert_settings = data.get('alert_settings', {})
        
        # 입력 검증
        if not stock_code or len(stock_code) != 6:
            return create_error_response("종목코드는 6자리여야 합니다", 'INVALID_STOCK_CODE', 400)
        
        if not stock_name:
            return create_error_response("종목명을 입력해주세요", 'INVALID_STOCK_NAME', 400)
        
        if not target_price or target_price <= 0:
            return create_error_response("유효한 목표가를 입력해주세요", 'INVALID_TARGET_PRICE', 400)
        
        if not stop_loss or stop_loss <= 0:
            return create_error_response("유효한 손절가를 입력해주세요", 'INVALID_STOP_LOSS', 400)
        
        if stop_loss >= target_price:
            return create_error_response("손절가는 목표가보다 낮아야 합니다", 'INVALID_PRICE_RANGE', 400)
        
        # 취득가 검증 (선택사항)
        if acquisition_price and acquisition_price < 0:
            return create_error_response("취득가는 0 이상이어야 합니다", 'INVALID_ACQUISITION_PRICE', 400)
        # 멤자닌 전환가 검증
        if category == '멤자닌':
            if not conversion_price or conversion_price <= 0:
                return create_error_response('멤자닌 종목은 전환가를 입력해주세요', 'INVALID_CONVERSION_PRICE', 400)
            
            
            # 소수점 둘째자리까지만 허용
            if round(conversion_price, 2) != conversion_price:
                return create_error_response('전환가는 소수점 둘째자리까지만 입력 가능합니다', 'INVALID_CONVERSION_PRICE', 400)
        
        # 종목 추가 (stock_monitor 모듈 사용 - 확장된 파라미터)
        from modules.stock_monitor import add_monitoring_stock
        
        success = add_monitoring_stock(
            stock_code=stock_code,
            stock_name=stock_name,
            target_price=float(target_price),
            stop_loss=float(stop_loss),
            category=category,
            acquisition_price=float(acquisition_price),
            alert_settings=alert_settings,
            memo=memo,
            conversion_price=float(conversion_price) if conversion_price else 0
        )
        
        if success:
            logger.info(f"종목 추가 성공", 
                stock_code=stock_code,
                stock_name=stock_name,
                target_price=target_price,
                stop_loss=stop_loss,
                category=category
            )
            
            return create_success_response(
                {'stock_code': stock_code},
                f'{stock_name}({stock_code}) 종목이 추가되었습니다'
            )
        else:
            return create_error_response("종목 추가에 실패했습니다", 'STOCK_ADD_FAILED')
        
    except Exception as e:
        return create_error_response(str(e), 'STOCK_ADD_ERROR')

@app.route('/api/v1/stocks/<stock_code>', methods=['DELETE'])
@login_required
@performance_monitor('종목 삭제')
@api_request_logger
def delete_stock(stock_code):
    """종목 삭제"""
    try:
        if not stock_code or len(stock_code) != 6:
            return create_error_response("유효한 종목코드를 입력해주세요", 'INVALID_STOCK_CODE', 400)
        
        # 종목 삭제 (stock_monitor 모듈 사용)
        from modules.stock_monitor import remove_monitoring_stock
        
        success = remove_monitoring_stock(stock_code)
        
        if success:
            logger.info(f"종목 삭제 성공", stock_code=stock_code)
            
            return create_success_response(
                {'stock_code': stock_code},
                f'{stock_code} 종목이 삭제되었습니다'
            )
        else:
            return create_error_response("해당 종목을 찾을 수 없습니다", 'STOCK_NOT_FOUND', 404)
        
    except Exception as e:
        return create_error_response(str(e), 'STOCK_DELETE_ERROR')

@app.route('/api/v1/stocks/<stock_code>', methods=['PUT'])
@login_required
@performance_monitor('종목 수정')
@api_request_logger
def update_stock(stock_code):
    """종목 정보 수정 (확장된 스키마 지원)"""
    try:
        if not stock_code or len(stock_code) != 6:
            return create_error_response("유효한 종목코드를 입력해주세요", 'INVALID_STOCK_CODE', 400)
        
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        from modules.stock_monitor import update_monitoring_stock
        
        # 기본 필드
        name = data.get('name')
        target_price = data.get('target_price')
        stop_loss = data.get('stop_loss')
        category = data.get('category')
        enabled = data.get('enabled')
        
        # 확장된 필드
        acquisition_price = data.get('acquisition_price')
        memo = data.get('memo')
        alert_settings = data.get('alert_settings')
        
        # 입력 검증
        if target_price is not None and target_price <= 0:
            return create_error_response("유효한 목표가를 입력해주세요", 'INVALID_TARGET_PRICE', 400)
        
        if stop_loss is not None and stop_loss <= 0:
            return create_error_response("유효한 손절가를 입력해주세요", 'INVALID_STOP_LOSS', 400)
        
        if target_price is not None and stop_loss is not None and stop_loss >= target_price:
            return create_error_response("손절가는 목표가보다 낮아야 합니다", 'INVALID_PRICE_RANGE', 400)
        
        if acquisition_price is not None and acquisition_price < 0:
            return create_error_response("취득가는 0 이상이어야 합니다", 'INVALID_ACQUISITION_PRICE', 400)
        
        # 종목 정보 업데이트 (부분 업데이트 지원)
        success = update_monitoring_stock(
            stock_code=stock_code,
            name=name,
            target_price=target_price,
            stop_loss=stop_loss,
            category=category,
            acquisition_price=acquisition_price,
            alert_settings=alert_settings,
            memo=memo,
            enabled=enabled
        )
        
        if success:
            logger.info(f"종목 수정 성공", 
                stock_code=stock_code,
                updated_fields=list(data.keys())
            )
            
            return create_success_response(
                {'stock_code': stock_code, 'updated_fields': list(data.keys())},
                f'{stock_code} 종목 정보가 수정되었습니다'
            )
        else:
            return create_error_response("해당 종목을 찾을 수 없습니다", 'STOCK_NOT_FOUND', 404)
        
    except Exception as e:
        return create_error_response(str(e), 'STOCK_UPDATE_ERROR')

@app.route('/api/v1/stocks/categories')
@login_required
@performance_monitor('카테고리 목록 조회')
@api_request_logger
def get_stock_categories():
    """주식 카테고리 목록 조회"""
    try:
        from modules.stock_monitor import get_monitoring_stocks
        
        stocks = get_monitoring_stocks()
        categories = {}
        
        for stock_code, stock_info in stocks.items():
            category = stock_info.get('category', '주식')
            if category not in categories:
                categories[category] = {
                    'name': category,
                    'count': 0,
                    'stocks': []
                }
            
            categories[category]['count'] += 1
            categories[category]['stocks'].append({
                'code': stock_code,
                'name': stock_info.get('name', stock_code),
                'enabled': stock_info.get('enabled', True)
            })
        
        return create_success_response({
            'categories': list(categories.values()),
            'total_categories': len(categories)
        })
        
    except Exception as e:
        return create_error_response(str(e), 'CATEGORIES_FETCH_ERROR')

@app.route('/api/v1/stocks/category/<category>')
@login_required
@performance_monitor('카테고리별 종목 조회')
@api_request_logger
def get_stocks_by_category(category):
    """카테고리별 종목 목록 조회"""
    try:
        from modules.stock_monitor import get_monitoring_stocks
        
        stocks = get_monitoring_stocks()
        category_stocks = {}
        
        for stock_code, stock_info in stocks.items():
            if stock_info.get('category', '주식') == category:
                # JSON 직렬화를 위해 set을 list로 변환
                serializable_info = stock_info.copy()
                if 'triggered_alerts' in serializable_info and isinstance(serializable_info['triggered_alerts'], set):
                    serializable_info['triggered_alerts'] = list(serializable_info['triggered_alerts'])
                category_stocks[stock_code] = serializable_info
        
        return create_success_response({
            'category': category,
            'stocks': category_stocks,
            'count': len(category_stocks)
        })
        
    except Exception as e:
        return create_error_response(str(e), 'CATEGORY_STOCKS_FETCH_ERROR')

@app.route('/api/v1/stocks/mezzanine', methods=['POST'])
@login_required
@performance_monitor('메자닌 종목 추가')
@api_request_logger
def add_mezzanine_stock():
    """메자닌 종목 추가 (패리티 알림 포함)"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stock_code = data.get('stock_code', '').strip()
        stock_name = data.get('stock_name', '').strip()
        target_price = data.get('target_price')
        stop_loss = data.get('stop_loss')
        conversion_price = data.get('conversion_price')  # 전환가격
        
        # 입력 검증
        if not stock_code or len(stock_code) != 6:
            return create_error_response("종목코드는 6자리여야 합니다", 'INVALID_STOCK_CODE', 400)
        
        if not stock_name:
            return create_error_response("종목명을 입력해주세요", 'INVALID_STOCK_NAME', 400)
        
        if not conversion_price or conversion_price <= 0:
            return create_error_response("유효한 전환가격을 입력해주세요", 'INVALID_CONVERSION_PRICE', 400)
        
        # 메자닌 종목 추가
        from modules.stock_monitor import stock_monitor
        
        success = stock_monitor.add_stock(
            stock_code=stock_code,
            stock_name=stock_name,
            target_price=target_price or 0,
            stop_loss=stop_loss or 0,
            category="메자닌"
        )
        
        if success:
            # 전환가격 추가
            stock_monitor.monitoring_stocks[stock_code]['conversion_price'] = int(conversion_price)
            stock_monitor.save_monitoring_stocks(stock_monitor.monitoring_stocks)
            
            logger.info(f"메자닌 종목 추가 성공", 
                stock_code=stock_code,
                stock_name=stock_name,
                conversion_price=conversion_price
            )
            
            return create_success_response(
                {'stock_code': stock_code, 'category': '메자닌'},
                f'{stock_name}({stock_code}) 메자닌 종목이 추가되었습니다'
            )
        else:
            return create_error_response("메자닌 종목 추가에 실패했습니다", 'MEZZANINE_ADD_FAILED')
        
    except Exception as e:
        return create_error_response(str(e), 'MEZZANINE_ADD_ERROR')

@app.route('/api/v1/stocks/migrate-categories', methods=['POST'])
@admin_required
@performance_monitor('카테고리 마이그레이션')
@api_request_logger
def migrate_stock_categories():
    """기존 데이터의 카테고리 표준화 (관리자 전용)"""
    try:
        from modules.stock_monitor import stock_monitor
        
        updated_count = 0
        for stock_code, stock_info in stock_monitor.monitoring_stocks.items():
            old_category = stock_info.get('category', '주식')
            new_category = stock_monitor.normalize_category(old_category)
            
            if old_category != new_category:
                stock_info['category'] = new_category
                updated_count += 1
                
                # 알림 가격 재설정
                current_price = stock_info.get('current_price', 0)
                if current_price > 0:
                    stock_monitor.setup_alert_prices(stock_info, current_price)
                    # 기존 트리거된 알림 초기화
                    stock_info['triggered_alerts'] = set()
        
        if updated_count > 0:
            stock_monitor.save_monitoring_stocks(stock_monitor.monitoring_stocks)
        
        logger.info(f"카테고리 마이그레이션 완료", updated_count=updated_count)
        
        return create_success_response(
            {'updated_count': updated_count},
            f'{updated_count}개 종목의 카테고리가 표준화되었습니다'
        )
        
    except Exception as e:
        return create_error_response(str(e), 'CATEGORY_MIGRATION_ERROR')

# === 실시간 모니터링 API 엔드포인트 ===

@app.route('/api/v1/monitoring/start', methods=['POST'])
@login_required
@performance_monitor('실시간 모니터링 시작')
@api_request_logger
def start_real_time_monitoring():
    """실시간 주식 모니터링 시작"""
    try:
        success = stock_monitor.start_real_time_monitoring()
        
        if success:
            logger.info("실시간 모니터링 시작 성공")
            return create_success_response(
                stock_monitor.get_monitoring_status(),
                "실시간 주식 모니터링이 시작되었습니다"
            )
        else:
            return create_error_response("실시간 모니터링이 이미 실행 중입니다", 'MONITORING_ALREADY_RUNNING', 409)
        
    except Exception as e:
        return create_error_response(str(e), 'MONITORING_START_ERROR')

@app.route('/api/v1/monitoring/stop', methods=['POST'])
@login_required
@performance_monitor('실시간 모니터링 중지')
@api_request_logger
def stop_real_time_monitoring():
    """실시간 주식 모니터링 중지"""
    try:
        success = stock_monitor.stop_real_time_monitoring()
        
        if success:
            logger.info("실시간 모니터링 중지 성공")
            return create_success_response(
                stock_monitor.get_monitoring_status(),
                "실시간 주식 모니터링이 중지되었습니다"
            )
        else:
            return create_error_response("실시간 모니터링이 실행되지 않고 있습니다", 'MONITORING_NOT_RUNNING', 409)
        
    except Exception as e:
        return create_error_response(str(e), 'MONITORING_STOP_ERROR')

@app.route('/api/v1/monitoring/status')
@login_required
@performance_monitor('모니터링 상태 조회')
@api_request_logger
def get_monitoring_status():
    """실시간 모니터링 상태 조회"""
    try:
        status = stock_monitor.get_monitoring_status()
        
        return create_success_response({
            'monitoring_status': status,
            'system_info': {
                'current_time': datetime.now().isoformat(),
                'market_hours': f"09:00-15:30 (월-금)",
                'update_interval': f"{stock_monitor.monitor_interval}초"
            }
        })
        
    except Exception as e:
        return create_error_response(str(e), 'MONITORING_STATUS_ERROR')

@app.route('/api/v1/monitoring/daily-report', methods=['POST'])
@login_required
@performance_monitor('수동 일일 보고서 생성')
@api_request_logger
def generate_daily_report():
    """수동 일일 보고서 생성 및 발송"""
    try:
        # 일일 보고서 데이터 생성
        report_data = stock_monitor._generate_daily_report_data()
        
        # 이메일 발송
        success = stock_monitor._send_daily_report_email(report_data)
        
        if success:
            logger.info("수동 일일 보고서 발송 성공")
            return create_success_response(
                {
                    'report_summary': {
                        'date': report_data['date'],
                        'total_stocks': report_data['total_stocks'],
                        'active_stocks': report_data['active_stocks'],
                        'gainers_count': report_data['summary']['gainers_count'],
                        'losers_count': report_data['summary']['losers_count'],
                        'alerts_count': report_data['summary']['alerts_count']
                    }
                },
                "일일 보고서가 성공적으로 발송되었습니다"
            )
        else:
            return create_error_response("일일 보고서 발송에 실패했습니다", 'DAILY_REPORT_SEND_ERROR')
        
    except Exception as e:
        return create_error_response(str(e), 'DAILY_REPORT_ERROR')

@app.route('/api/v1/test/email', methods=['POST'])
@login_required  
@performance_monitor('테스트 이메일 발송')
@api_request_logger
def send_test_email_api():
    """테스트 이메일 발송"""
    try:
        data = request.get_json() or {}
        subject = data.get('subject', '[D2 Dash] 테스트 이메일')
        message = data.get('message', '이메일 시스템 테스트입니다.')
        
        success = send_test_email(subject, message)
        
        if success:
            logger.info("테스트 이메일 발송 성공")
            return create_success_response(
                {'email_type': 'test'},
                "테스트 이메일이 성공적으로 발송되었습니다"
            )
        else:
            return create_error_response("테스트 이메일 발송에 실패했습니다", 'TEST_EMAIL_SEND_ERROR')
        
    except Exception as e:
        return create_error_response(str(e), 'TEST_EMAIL_ERROR')

# === 기업 관리 API 엔드포인트 ===

@app.route('/api/v1/dart/companies', methods=['POST'])
@admin_required
@performance_monitor('기업 추가')
@api_request_logger
def add_company():
    """새 모니터링 기업 추가"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        company_code = data.get('company_code', '').strip()
        company_name = data.get('company_name', '').strip()
        
        # 입력 검증
        if not company_code:
            return create_error_response("기업코드를 입력해주세요", 'INVALID_COMPANY_CODE', 400)
        
        if not company_name:
            return create_error_response("기업명을 입력해주세요", 'INVALID_COMPANY_NAME', 400)
        
        # DART 모니터 인스턴스를 통한 기업 추가
        from modules.dart_monitor import dart_monitor
        
        success = dart_monitor.add_dart_company(company_code, company_name)
        
        if success:
            logger.info(f"기업 추가 성공", 
                company_code=company_code,
                company_name=company_name
            )
            
            return create_success_response(
                {'company_code': company_code},
                f'{company_name}({company_code}) 기업이 추가되었습니다'
            )
        else:
            return create_error_response("기업 추가에 실패했습니다", 'COMPANY_ADD_FAILED')
        
    except Exception as e:
        return create_error_response(str(e), 'COMPANY_ADD_ERROR')

@app.route('/api/v1/dart/companies/<company_code>', methods=['DELETE'])
@admin_required
@performance_monitor('기업 삭제')
@api_request_logger
def delete_company(company_code):
    """모니터링 기업 삭제"""
    try:
        if not company_code:
            return create_error_response("유효한 기업코드를 입력해주세요", 'INVALID_COMPANY_CODE', 400)
        
        # DART 모니터 인스턴스를 통한 기업 삭제
        from modules.dart_monitor import dart_monitor
        
        success = dart_monitor.remove_dart_company(company_code)
        
        if success:
            logger.info(f"DART 기업 삭제 성공", company_code=company_code)
            
            return create_success_response(
                {'company_code': company_code},
                f'{company_code} 기업이 삭제되었습니다'
            )
        else:
            return create_error_response("해당 기업을 찾을 수 없습니다", 'COMPANY_NOT_FOUND', 404)
        
    except Exception as e:
        return create_error_response(str(e), 'COMPANY_DELETE_ERROR')

# === DART 키워드 관리 API ===

@app.route('/api/v1/dart/keywords/add', methods=['POST'])
@admin_required
@performance_monitor('DART 키워드 추가')
@api_request_logger
def add_dart_keyword():
    """DART 필터링 키워드 추가"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        keyword = data.get('keyword', '').strip()
        
        # 입력 검증
        if not keyword:
            return create_error_response("키워드를 입력해주세요", 'INVALID_KEYWORD', 400)
        
        if len(keyword) > 50:
            return create_error_response("키워드는 50자 이하로 입력해주세요", 'KEYWORD_TOO_LONG', 400)
        
        # 키워드 추가
        from modules.dart_monitor import dart_monitor
        
        success = dart_monitor.add_dart_keyword(keyword)
        
        if success:
            dart_logger.info(f"DART 키워드 추가 성공", keyword=keyword)
            
            return create_success_response(
                {'keyword': keyword},
                f'키워드 "{keyword}"가 추가되었습니다'
            )
        else:
            return create_error_response("이미 존재하는 키워드입니다", 'KEYWORD_ALREADY_EXISTS', 409)
        
    except Exception as e:
        return create_error_response(str(e), 'KEYWORD_ADD_ERROR')

@app.route('/api/v1/dart/keywords/<keyword>', methods=['DELETE'])
@admin_required
@performance_monitor('DART 키워드 삭제')
@api_request_logger
def delete_dart_keyword(keyword):
    """DART 필터링 키워드 삭제"""
    try:
        if not keyword:
            return create_error_response("유효한 키워드를 입력해주세요", 'INVALID_KEYWORD', 400)
        
        # URL 디코딩
        from urllib.parse import unquote
        keyword = unquote(keyword)
        
        # 키워드 삭제
        from modules.dart_monitor import dart_monitor
        
        success = dart_monitor.remove_dart_keyword(keyword)
        
        if success:
            dart_logger.info(f"DART 키워드 삭제 성공", keyword=keyword)
            
            return create_success_response(
                {'keyword': keyword},
                f'키워드 "{keyword}"가 삭제되었습니다'
            )
        else:
            return create_error_response("해당 키워드를 찾을 수 없습니다", 'KEYWORD_NOT_FOUND', 404)
        
    except Exception as e:
        return create_error_response(str(e), 'KEYWORD_DELETE_ERROR')

# === DART 실시간 로그 API ===

@app.route('/api/v1/dart/realtime-logs')
@login_required
@performance_monitor('DART 실시간 로그 조회')
@api_request_logger
def get_dart_realtime_logs():
    """DART 실시간 로그 조회"""
    try:
        # 조회 시간 범위 (기본: 24시간)
        hours = request.args.get('hours', 24, type=int)
        
        # 시간 범위 검증 (최대 7일)
        if hours < 1 or hours > 168:
            return create_error_response("조회 시간은 1시간에서 168시간(7일) 사이여야 합니다", 'INVALID_HOURS', 400)
        
        # 로그 조회
        from modules.dart_monitor import dart_monitor
        
        logs = dart_monitor.get_recent_logs(hours)
        
        dart_logger.debug(f"DART 로그 조회", hours=hours, log_count=len(logs))
        
        return create_success_response(
            {
                'logs': logs,
                'hours': hours,
                'total_count': len(logs),
                'generated_at': datetime.now().isoformat()
            },
            f'최근 {hours}시간 DART 로그 {len(logs)}건 조회 완료'
        )
        
    except Exception as e:
        return create_error_response(str(e), 'DART_LOGS_ERROR')

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

# === SPA 지원을 위한 Catch-All 라우트 임시 비활성화 ===
# API 테스트를 위해 임시로 주석 처리
# @app.route('/<path:path>', methods=['GET'])
# def catch_all(path):
#     """
#     SPA(Single Page Application) 지원을 위한 catch-all 라우트
#     GET 요청만 처리하여 정적 파일과 SPA 라우팅 지원
#     """
#     import os
#     
#     # 정적 파일이 실제로 존재하는지 확인
#     static_dir = os.path.join(os.path.dirname(__file__), 'static')
#     static_file_path = os.path.join(static_dir, path)
#     
#     if os.path.isfile(static_file_path):
#         # 정적 파일이 존재하면 해당 파일 서빙
#         return send_from_directory('static', path)
#     
#     # API 경로이지만 GET이 아닌 경우는 이 라우트에서 처리하지 않음
#     if path.startswith('api/v1/'):
#         from flask import abort
#         abort(404)
#     
#     # 그 외의 경우 SPA를 위해 index.html 반환
#     return send_from_directory('static', 'index.html')

# === 새로운 API 엔드포인트들 ===

@app.route('/api/v1/stocks/daily-history', methods=['GET'])
@performance_monitor('일일 내역 조회')
@api_request_logger
def get_daily_history():
    """일일 알림 내역 조회"""
    try:
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # 알림 파일에서 당일 알림 내역 조회
        from modules.config import NOTIFICATIONS_FILE
        import os
        
        daily_alerts = []
        
        if os.path.exists(NOTIFICATIONS_FILE):
            try:
                with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                    notifications = json.load(f)
                    
                    # 날짜별 필터링
                    for notification in notifications:
                        if notification.get('date', '').startswith(target_date):
                            daily_alerts.append(notification)
                            
            except Exception as e:
                logger.warning(f"알림 파일 읽기 실패: {e}")
        
        # 종목별 당일 알림 현황 추가
        stocks = get_monitoring_stocks()
        stock_alerts = []
        
        for code, info in stocks.items():
            triggered_alerts = info.get('triggered_alerts', [])
            if triggered_alerts:
                stock_alerts.append({
                    'stock_code': code,
                    'stock_name': info.get('name', code),
                    'category': info.get('category', '주식'),
                    'current_price': info.get('current_price', 0),
                    'change_percent': info.get('change_percent', 0),
                    'triggered_alerts': list(triggered_alerts) if isinstance(triggered_alerts, set) else triggered_alerts,
                    'alert_count': len(triggered_alerts)
                })
        
        return create_success_response({
            'date': target_date,
            'daily_alerts': daily_alerts,
            'stock_alerts': stock_alerts,
            'total_alerts': len(daily_alerts),
            'total_stock_alerts': len(stock_alerts)
        })
        
    except Exception as e:
        return create_error_response(str(e), 'DAILY_HISTORY_ERROR')

@app.route('/api/v1/stocks/logs', methods=['GET'])
@performance_monitor('실시간 로그 조회')
@api_request_logger
def get_stock_logs():
    """실시간 주식 모니터링 로그 조회"""
    try:
        limit = min(int(request.args.get('limit', 100)), 500)  # 최대 500개 제한
        log_type = request.args.get('type', 'all')  # all, error, alert, update
        
        # 로그 파일에서 최근 로그 읽기
        from modules.config import LOGS_DIR, LOG_FILES
        
        logs = []
        log_file_path = os.path.join(LOGS_DIR, LOG_FILES.get('stock', 'stock_monitor.log'))
        
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    # 최근 로그부터 역순으로 처리
                    recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
                    
                    for line in reversed(recent_lines):
                        if line.strip():
                            # 로그 파싱 (간단한 형태)
                            try:
                                # 타임스탬프 추출
                                if ' - ' in line:
                                    timestamp_part = line.split(' - ')[0]
                                    message_part = ' - '.join(line.split(' - ')[1:])
                                    
                                    log_entry = {
                                        'timestamp': timestamp_part.strip(),
                                        'message': message_part.strip(),
                                        'type': 'info'
                                    }
                                    
                                    # 로그 타입 분류
                                    if 'ERROR' in line.upper() or 'error' in message_part.lower():
                                        log_entry['type'] = 'error'
                                    elif 'alert' in message_part.lower() or '알림' in message_part:
                                        log_entry['type'] = 'alert'
                                    elif 'update' in message_part.lower() or '업데이트' in message_part:
                                        log_entry['type'] = 'update'
                                    
                                    # 타입 필터링
                                    if log_type == 'all' or log_entry['type'] == log_type:
                                        logs.append(log_entry)
                                        
                                        if len(logs) >= limit:
                                            break
                                            
                            except Exception as parse_error:
                                continue
                                
            except Exception as e:
                logger.error(f"로그 파일 읽기 실패: {e}")
        
        # 시스템 상태 정보 추가
        system_status = {
            'monitoring_active': stock_monitor.is_monitoring,
            'market_open': stock_monitor.is_market_open(),
            'total_stocks': len(stock_monitor.monitoring_stocks),
            'active_stocks': len([s for s in stock_monitor.monitoring_stocks.values() if s.get('enabled', True)]),
            'last_update': datetime.now().isoformat()
        }
        
        return create_success_response({
            'logs': logs,
            'system_status': system_status,
            'log_count': len(logs),
            'log_type': log_type
        })
        
    except Exception as e:
        return create_error_response(str(e), 'STOCK_LOGS_ERROR')

@app.route('/api/v1/stocks/validate', methods=['POST'])
@performance_monitor('종목 코드 검증')
@api_request_logger
def validate_stock_code():
    """종목 코드 유효성 검증"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stock_code = data.get('stock_code', '').strip()
        
        if not stock_code:
            return create_error_response("종목코드를 입력해주세요", 'MISSING_STOCK_CODE', 400)
        
        if len(stock_code) != 6:
            return create_error_response("종목코드는 6자리여야 합니다", 'INVALID_STOCK_CODE', 400)
        
        if not stock_code.isdigit():
            return create_error_response("종목코드는 숫자만 입력 가능합니다", 'INVALID_STOCK_CODE_FORMAT', 400)
        
        # 실제 종목 정보 조회 시도
        from modules.stock_monitor import stock_monitor
        
        try:
            # 종목명 조회로 유효성 검증
            stock_name = stock_monitor.get_stock_name(stock_code)
            
            # 현재가 조회 시도 (선택적)
            current_price, change_percent, error = stock_monitor.get_stock_price(stock_code)
            
            validation_result = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'is_valid': True,
                'price_available': current_price is not None,
                'current_price': current_price,
                'change_percent': change_percent,
                'already_monitored': stock_code in stock_monitor.monitoring_stocks
            }
            
            if error:
                validation_result['price_error'] = error
            
            return create_success_response(validation_result)
            
        except Exception as e:
            return create_error_response(f"종목 정보 조회 실패: {str(e)}", 'STOCK_VALIDATION_FAILED', 400)
        
    except Exception as e:
        return create_error_response(str(e), 'STOCK_VALIDATE_ERROR')

# === 손절가 설정 API 엔드포인트 ===

@app.route('/api/v1/stocks/stop-loss/options', methods=['GET'])
@login_required
@performance_monitor('손절가 옵션 조회')
@api_request_logger
def get_stop_loss_options():
    """손절가 설정 옵션 목록 조회"""
    try:
        options = stock_monitor.get_stop_loss_options()
        
        return create_success_response({
            'options': options,
            'default_option': -5,  # 기본값 -5%
            'description': '취득가 기준 손절가 설정 옵션'
        })
        
    except Exception as e:
        return create_error_response(str(e), 'STOP_LOSS_OPTIONS_ERROR')

@app.route('/api/v1/stocks/<stock_code>/stop-loss', methods=['POST'])
@login_required
@performance_monitor('손절가 설정')
@api_request_logger
def set_stop_loss(stock_code):
    """개별 종목 손절가 설정"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stop_loss_option = data.get('stop_loss_option')
        custom_value = data.get('custom_value')
        
        # 필수 파라미터 검증
        if stop_loss_option is None:
            return create_error_response("손절가 옵션을 선택해주세요", 'MISSING_OPTION', 400)
        
        # 커스텀 입력 시 값 검증
        if stop_loss_option == 'custom':
            if custom_value is None or custom_value <= 0:
                return create_error_response("직접입력 시 유효한 손절가 값이 필요합니다", 'INVALID_CUSTOM_VALUE', 400)
        
        # 종목 존재 여부 확인
        if stock_code not in stock_monitor.monitoring_stocks:
            return create_error_response(f"모니터링 중이지 않은 종목입니다: {stock_code}", 'STOCK_NOT_FOUND', 404)
        
        # 손절가 설정 적용
        success = stock_monitor.apply_stop_loss_setting(stock_code, stop_loss_option, custom_value)
        
        if success:
            # 업데이트된 종목 정보 조회
            updated_stock = stock_monitor.monitoring_stocks.get(stock_code, {})
            
            result = {
                'stock_code': stock_code,
                'stock_name': updated_stock.get('name', stock_code),
                'new_stop_loss': updated_stock.get('stop_loss', 0),
                'acquisition_price': updated_stock.get('acquisition_price', 0),
                'stop_loss_option': stop_loss_option,
                'applied_at': datetime.now().isoformat()
            }
            
            if stop_loss_option != 'custom':
                result['stop_loss_percent'] = stop_loss_option
            else:
                result['custom_value'] = custom_value
            
            logger.info(f"손절가 설정 완료: {updated_stock.get('name', stock_code)} ({stock_code}) - {updated_stock.get('stop_loss', 0):,.0f}원")
            
            return create_success_response(result)
        else:
            return create_error_response("손절가 설정에 실패했습니다", 'STOP_LOSS_SET_FAILED', 500)
            
    except Exception as e:
        return create_error_response(str(e), 'STOP_LOSS_SET_ERROR')

@app.route('/api/v1/stocks/<stock_code>/stop-loss/calculate', methods=['POST'])
@login_required
@performance_monitor('손절가 계산')
@api_request_logger
def calculate_stop_loss(stock_code):
    """종목의 손절가 미리 계산 (적용하지 않음)"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stop_loss_percent = data.get('stop_loss_percent', -5.0)
        acquisition_price = data.get('acquisition_price')
        
        # 종목 정보에서 취득가 조회 (파라미터로 제공되지 않은 경우)
        if acquisition_price is None:
            if stock_code in stock_monitor.monitoring_stocks:
                acquisition_price = stock_monitor.monitoring_stocks[stock_code].get('acquisition_price', 0)
            else:
                return create_error_response("취득가 정보가 없습니다", 'NO_ACQUISITION_PRICE', 400)
        
        if acquisition_price <= 0:
            return create_error_response("유효한 취득가가 필요합니다", 'INVALID_ACQUISITION_PRICE', 400)
        
        # 손절가 계산
        calculated_stop_loss = stock_monitor.calculate_stop_loss(acquisition_price, stop_loss_percent)
        
        result = {
            'stock_code': stock_code,
            'acquisition_price': acquisition_price,
            'stop_loss_percent': stop_loss_percent,
            'calculated_stop_loss': calculated_stop_loss,
            'loss_amount': acquisition_price - calculated_stop_loss,
            'loss_percent': stop_loss_percent,
            'calculated_at': datetime.now().isoformat()
        }
        
        return create_success_response(result)
        
    except Exception as e:
        return create_error_response(str(e), 'STOP_LOSS_CALCULATE_ERROR')

@app.route('/api/v1/stocks/stop-loss/batch', methods=['POST'])
@login_required
@performance_monitor('일괄 손절가 설정')
@api_request_logger
def set_batch_stop_loss():
    """여러 종목 일괄 손절가 설정"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stock_codes = data.get('stock_codes', [])
        stop_loss_option = data.get('stop_loss_option')
        custom_value = data.get('custom_value')
        
        if not stock_codes:
            return create_error_response("종목 목록이 비어있습니다", 'EMPTY_STOCK_LIST', 400)
        
        if stop_loss_option is None:
            return create_error_response("손절가 옵션을 선택해주세요", 'MISSING_OPTION', 400)
        
        results = {
            'success': [],
            'failed': [],
            'summary': {
                'total': len(stock_codes),
                'success_count': 0,
                'failed_count': 0
            }
        }
        
        # 각 종목별로 손절가 설정 적용
        for stock_code in stock_codes:
            try:
                success = stock_monitor.apply_stop_loss_setting(stock_code, stop_loss_option, custom_value)
                
                if success:
                    updated_stock = stock_monitor.monitoring_stocks.get(stock_code, {})
                    results['success'].append({
                        'stock_code': stock_code,
                        'stock_name': updated_stock.get('name', stock_code),
                        'new_stop_loss': updated_stock.get('stop_loss', 0)
                    })
                    results['summary']['success_count'] += 1
                else:
                    results['failed'].append({
                        'stock_code': stock_code,
                        'error': '손절가 설정 실패'
                    })
                    results['summary']['failed_count'] += 1
                    
            except Exception as e:
                results['failed'].append({
                    'stock_code': stock_code,
                    'error': str(e)
                })
                results['summary']['failed_count'] += 1
        
        logger.info(f"일괄 손절가 설정 완료: 성공 {results['summary']['success_count']}개, 실패 {results['summary']['failed_count']}개")
        
        return create_success_response(results)
        
    except Exception as e:
        return create_error_response(str(e), 'BATCH_STOP_LOSS_ERROR')

# === 종목 정보 자동 조회 API 엔드포인트 ===

@app.route('/api/v1/stocks/info', methods=['POST'])
@login_required
@performance_monitor('종목 정보 조회')
@api_request_logger
def get_stock_info():
    """종목코드 입력 시 종목명과 전일가 자동 조회"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stock_code = data.get('stock_code', '').strip()
        
        if not stock_code:
            return create_error_response("종목코드를 입력해주세요", 'MISSING_STOCK_CODE', 400)
        
        # 종목코드 형식 검증 (6자리 숫자)
        if not stock_code.isdigit() or len(stock_code) != 6:
            return create_error_response("종목코드는 6자리 숫자여야 합니다", 'INVALID_STOCK_CODE_FORMAT', 400)
        
        # 종목 정보 조회
        from modules.stock_monitor import stock_monitor
        
        # 1. 종목명 조회
        try:
            stock_name = stock_monitor.get_stock_name(stock_code)
            
            # 기본 종목명 형태인 경우 유효하지 않은 종목코드로 판단
            if stock_name == f"종목 {stock_code}":
                return create_error_response(f"존재하지 않은 종목코드입니다: {stock_code}", 'STOCK_NOT_FOUND', 404)
                
        except Exception as e:
            logger.error(f"종목명 조회 실패: {stock_code} - {e}")
            return create_error_response(f"종목명 조회에 실패했습니다: {str(e)}", 'STOCK_NAME_FETCH_FAILED', 500)
        
        # 2. 주가 정보 조회 (전일가 포함)
        current_price = None
        previous_close = None
        change_percent = None
        price_error = None
        
        try:
            # PyKrx를 우선으로 사용하여 주가 정보 조회
            price_info = stock_monitor.get_stock_price(stock_code)
            current_price, change_percent, error = price_info
            
            if current_price is not None:
                # 전일 종가 계산 (현재가에서 등락률 역산)
                if change_percent != 0:
                    previous_close = round(current_price / (1 + change_percent / 100))
                else:
                    previous_close = current_price
            else:
                price_error = error or "주가 정보를 가져올 수 없습니다"
                
        except Exception as e:
            logger.error(f"주가 정보 조회 실패: {stock_code} - {e}")
            price_error = f"주가 정보 조회 실패: {str(e)}"
        
        # 3. 기존 모니터링 여부 확인
        already_monitored = stock_code in stock_monitor.monitoring_stocks
        
        # 4. 응답 데이터 구성
        result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'is_valid': True,
            'price_available': current_price is not None,
            'current_price': current_price,
            'previous_close': previous_close,
            'change_percent': change_percent,
            'already_monitored': already_monitored,
            'fetched_at': datetime.now().isoformat()
        }
        
        # 에러 정보 추가 (있는 경우)
        if price_error:
            result['price_error'] = price_error
            result['price_available'] = False
        
        # 기존 모니터링 종목인 경우 추가 정보 제공
        if already_monitored:
            existing_info = stock_monitor.monitoring_stocks[stock_code]
            result['existing_info'] = {
                'target_price': existing_info.get('target_price', 0),
                'stop_loss': existing_info.get('stop_loss', 0),
                'category': existing_info.get('category', '주식'),
                'acquisition_price': existing_info.get('acquisition_price', 0),
                'enabled': existing_info.get('enabled', True)
            }
        
        logger.info(f"종목 정보 조회 성공: {stock_name} ({stock_code}) - 가격: {current_price}, 전일가: {previous_close}")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"종목 정보 조회 오류: {e}")
        return create_error_response(str(e), 'STOCK_INFO_ERROR')

@app.route('/api/v1/stocks/search', methods=['POST'])
@login_required
@performance_monitor('종목 검색')
@api_request_logger
def search_stocks():
    """종목 검색 (종목명 부분 매칭)"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        query = data.get('query', '').strip()
        
        if not query:
            return create_error_response("검색어를 입력해주세요", 'MISSING_QUERY', 400)
        
        if len(query) < 2:
            return create_error_response("검색어는 2자 이상 입력해주세요", 'QUERY_TOO_SHORT', 400)
        
        # 기존 모니터링 종목에서 검색
        from modules.stock_monitor import stock_monitor
        
        search_results = []
        
        for stock_code, stock_info in stock_monitor.monitoring_stocks.items():
            stock_name = stock_info.get('name', stock_code)
            
            # 종목명에 검색어가 포함되어 있는지 확인
            if query.lower() in stock_name.lower() or query in stock_code:
                search_results.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'current_price': stock_info.get('current_price', 0),
                    'change_percent': stock_info.get('change_percent', 0),
                    'category': stock_info.get('category', '주식'),
                    'enabled': stock_info.get('enabled', True),
                    'last_updated': stock_info.get('last_updated')
                })
        
        # 검색 결과 정렬 (종목명 알파벳 순)
        search_results.sort(key=lambda x: x['stock_name'])
        
        result = {
            'query': query,
            'results': search_results,
            'total_count': len(search_results),
            'searched_at': datetime.now().isoformat()
        }
        
        logger.info(f"종목 검색 완료: '{query}' - {len(search_results)}개 결과")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"종목 검색 오류: {e}")
        return create_error_response(str(e), 'STOCK_SEARCH_ERROR')

@app.route('/api/v1/stocks/quick-add', methods=['POST'])
@login_required
@performance_monitor('빠른 종목 추가')
@api_request_logger
def quick_add_stock():
    """종목코드만으로 빠른 종목 추가 (자동 정보 조회 후 추가)"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("요청 데이터가 없습니다", 'NO_DATA', 400)
        
        stock_code = data.get('stock_code', '').strip()
        category = data.get('category', '주식')
        acquisition_price = data.get('acquisition_price', 0)
        
        if not stock_code:
            return create_error_response("종목코드를 입력해주세요", 'MISSING_STOCK_CODE', 400)
        
        # 종목코드 형식 검증
        if not stock_code.isdigit() or len(stock_code) != 6:
            return create_error_response("종목코드는 6자리 숫자여야 합니다", 'INVALID_STOCK_CODE_FORMAT', 400)
        
        # 이미 모니터링 중인지 확인
        from modules.stock_monitor import stock_monitor
        
        if stock_code in stock_monitor.monitoring_stocks:
            existing_stock = stock_monitor.monitoring_stocks[stock_code]
            return create_error_response(
                f"이미 모니터링 중인 종목입니다: {existing_stock.get('name', stock_code)} ({stock_code})", 
                'STOCK_ALREADY_EXISTS', 409
            )
        
        # 종목 정보 자동 조회
        try:
            stock_name = stock_monitor.get_stock_name(stock_code)
            
            # 기본 종목명 형태인 경우 유효하지 않은 종목코드로 판단
            if stock_name == f"종목 {stock_code}":
                return create_error_response(f"존재하지 않은 종목코드입니다: {stock_code}", 'STOCK_NOT_FOUND', 404)
                
        except Exception as e:
            logger.error(f"종목명 조회 실패: {stock_code} - {e}")
            return create_error_response(f"종목명 조회에 실패했습니다: {str(e)}", 'STOCK_NAME_FETCH_FAILED', 500)
        
        # 현재가 조회 (선택사항)
        current_price = None
        try:
            price_info = stock_monitor.get_stock_price(stock_code)
            current_price, _, _ = price_info
        except Exception as e:
            logger.warning(f"주가 조회 실패 (계속 진행): {stock_code} - {e}")
        
        # 기본 손절가 설정 (-5% 기본값)
        stop_loss = 0
        if acquisition_price > 0:
            stop_loss = stock_monitor.calculate_stop_loss(acquisition_price, -5.0)
        
        # 종목 추가
        success = stock_monitor.add_stock(
            stock_code=stock_code,
            stock_name=stock_name,
            target_price=0,  # 기본 목표가 0
            stop_loss=stop_loss,
            category=category,
            acquisition_price=float(acquisition_price) if acquisition_price else 0,
            alert_settings=None,  # 기본 설정 사용
            memo=''
        )
        
        if success:
            result = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'category': category,
                'acquisition_price': acquisition_price,
                'stop_loss': stop_loss,
                'current_price': current_price,
                'added_at': datetime.now().isoformat(),
                'auto_stop_loss_applied': stop_loss > 0
            }
            
            logger.info(f"빠른 종목 추가 성공: {stock_name} ({stock_code}) - 손절가: {stop_loss:,.0f}원")
            
            return create_success_response(result)
        else:
            return create_error_response("종목 추가에 실패했습니다", 'STOCK_ADD_FAILED', 500)
            
    except Exception as e:
        logger.error(f"빠른 종목 추가 오류: {e}")
        return create_error_response(str(e), 'QUICK_ADD_ERROR')

# === DART API 상태 체크 API 엔드포인트 ===

@app.route('/api/v1/dart/health', methods=['GET'])
@login_required
@performance_monitor('DART API 헬스체크')
@api_request_logger
def check_dart_health():
    """DART API 연동 상태 헬스체크"""
    try:
        from modules.dart_monitor import dart_monitor
        
        # 헬스체크 수행
        health_result = dart_monitor.check_dart_api_health()
        
        # 성공 여부에 따른 HTTP 상태 코드 결정
        if health_result['status'] == 'healthy':
            status_code = 200
        elif health_result['status'] == 'error':
            status_code = 503  # Service Unavailable
        else:  # 'failed'
            status_code = 500  # Internal Server Error
        
        return create_success_response(health_result), status_code
        
    except Exception as e:
        logger.error(f"DART API 헬스체크 오류: {e}")
        return create_error_response(str(e), 'DART_HEALTH_CHECK_ERROR'), 500

@app.route('/api/v1/dart/status', methods=['GET'])
@login_required
@performance_monitor('DART API 상태 요약')
@api_request_logger
def get_dart_status():
    """DART API 상태 요약 정보 조회"""
    try:
        from modules.dart_monitor import dart_monitor
        
        # 상태 요약 정보 조회
        status_summary = dart_monitor.get_dart_api_status_summary()
        
        # 시스템 준비 상태에 따른 HTTP 상태 코드
        if 'error' in status_summary:
            status_code = 500
        elif status_summary.get('system_ready', False):
            status_code = 200
        else:
            status_code = 503  # Service Unavailable
        
        return create_success_response(status_summary), status_code
        
    except Exception as e:
        logger.error(f"DART API 상태 요약 오류: {e}")
        return create_error_response(str(e), 'DART_STATUS_ERROR'), 500

@app.route('/api/v1/dart/test', methods=['POST'])
@login_required
@performance_monitor('DART API 연결성 테스트')
@api_request_logger
def test_dart_connectivity():
    """DART API 연결성 테스트 (여러 기업으로 테스트)"""
    try:
        data = request.get_json() or {}
        company_count = data.get('company_count', 3)
        
        # 기업 수 검증
        if not isinstance(company_count, int) or company_count < 1 or company_count > 10:
            return create_error_response(
                "테스트할 기업 수는 1-10 사이여야 합니다", 
                'INVALID_COMPANY_COUNT', 400
            )
        
        from modules.dart_monitor import dart_monitor
        
        # 연결성 테스트 수행
        test_result = dart_monitor.test_dart_connectivity(company_count)
        
        # 전체 상태에 따른 HTTP 상태 코드
        if test_result['overall_status'] in ['excellent', 'good']:
            status_code = 200
        elif test_result['overall_status'] == 'poor':
            status_code = 206  # Partial Content
        else:  # 'failed', 'error'
            status_code = 503  # Service Unavailable
        
        return create_success_response(test_result), status_code
        
    except Exception as e:
        logger.error(f"DART API 연결성 테스트 오류: {e}")
        return create_error_response(str(e), 'DART_CONNECTIVITY_TEST_ERROR'), 500

@app.route('/api/v1/dart/config', methods=['GET'])
@login_required
@performance_monitor('DART 설정 조회')
@api_request_logger
def get_dart_config():
    """DART 모니터링 설정 정보 조회"""
    try:
        from modules.config import (
            DART_API_URL, DART_API_KEY, REQUEST_TIMEOUT, 
            COMPANIES, KEYWORDS, KEYWORD_AND_CONDITIONS, KEYWORD_FILTER_MODE
        )
        
        config_info = {
            'api_settings': {
                'api_url': DART_API_URL,
                'api_key_configured': bool(DART_API_KEY and DART_API_KEY.strip()),
                'api_key_length': len(DART_API_KEY) if DART_API_KEY else 0,
                'request_timeout': REQUEST_TIMEOUT
            },
            'monitoring_settings': {
                'monitored_companies_count': len(COMPANIES),
                'companies': [
                    {'corp_code': code, 'company_name': name} 
                    for code, name in COMPANIES.items()
                ],
                'keywords_count': len(KEYWORDS),
                'keywords': KEYWORDS,
                'and_conditions': KEYWORD_AND_CONDITIONS,
                'filter_mode': KEYWORD_FILTER_MODE
            },
            'last_updated': datetime.now().isoformat()
        }
        
        return create_success_response(config_info)
        
    except Exception as e:
        logger.error(f"DART 설정 조회 오류: {e}")
        return create_error_response(str(e), 'DART_CONFIG_ERROR')

@app.route('/api/v1/dart/trigger-check', methods=['POST'])
@login_required
@performance_monitor('DART 공시 수동 체크')
@api_request_logger
def trigger_dart_check():
    """DART 공시 수동 체크 트리거"""
    try:
        data = request.get_json() or {}
        target_date = data.get('target_date')  # YYYYMMDD 형식, None이면 오늘
        
        from modules.dart_monitor import dart_monitor
        
        # 수동 공시 체크 수행
        new_disclosures = dart_monitor.check_new_disclosures(target_date)
        
        result = {
            'target_date': target_date or datetime.now().strftime('%Y%m%d'),
            'new_disclosures_count': len(new_disclosures),
            'new_disclosures': new_disclosures,
            'checked_at': datetime.now().isoformat()
        }
        
        # 새로운 공시가 있는지에 따른 로깅
        if new_disclosures:
            logger.info(f"수동 DART 체크: {len(new_disclosures)}건의 새로운 공시 발견")
        else:
            logger.info("수동 DART 체크: 새로운 공시 없음")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"DART 공시 수동 체크 오류: {e}")
        return create_error_response(str(e), 'DART_MANUAL_CHECK_ERROR')

if __name__ == '__main__':
    try:
        # Flask 라우트 등록 현황 출력
        print("=== Flask 라우트 등록 현황 ===")
        for rule in app.url_map.iter_rules():
            print(f"Endpoint: {rule.endpoint}, Rule: {rule.rule}, Methods: {rule.methods}")
        print("=" * 50)
        
        logger.info("D2 Dash 시스템 시작", 
            version="v3",
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug_mode=FLASK_DEBUG,
            dart_interval=DART_CHECK_INTERVAL,
            stock_interval=STOCK_CHECK_INTERVAL
        )
        
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
        logger.info("사용자에 의한 종료 요청", shutdown_reason="키보드 인터럽트")
    except Exception as e:
        error_logger.critical("서버 시작 중 치명적 오류", 
            error_message=str(e),
            error_type=type(e).__name__
        )
    finally:
        stop_monitoring_threads()
        logger.info("D2 Dash 시스템 종료", version="v3")