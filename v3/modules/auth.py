"""
사용자 인증 및 권한 관리 모듈
JSON 파일 기반 사용자 관리 시스템
"""
import os
import json
import bcrypt
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, List
from flask import session, request, jsonify, redirect, url_for
from filelock import FileLock

from .logger_utils import get_logger

logger = get_logger('auth')

# 사용자 데이터 파일 경로
USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')
USERS_LOCK = USERS_FILE + '.lock'

class AuthManager:
    """사용자 인증 관리 클래스"""
    
    def __init__(self):
        self.users_file = USERS_FILE
        self.lock_file = USERS_LOCK
        self._ensure_users_file()
        logger.info("AuthManager 초기화 완료")
    
    def _ensure_users_file(self):
        """사용자 파일이 없으면 초기 관리자 계정과 함께 생성"""
        if not os.path.exists(self.users_file):
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            
            # 초기 관리자 계정 생성
            admin_user = {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": self._hash_password("admin123!"),
                "email": "admin@d2dash.com",
                "role": "admin",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "login_attempts": 0,
                "locked_until": None
            }
            
            initial_data = {
                "users": [admin_user],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            with FileLock(self.lock_file):
                with open(self.users_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
            
            logger.info("초기 관리자 계정 생성 완료 (admin/admin123!)")
    
    def _load_users(self) -> Dict:
        """사용자 데이터 로드"""
        try:
            with FileLock(self.lock_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"사용자 데이터 로드 실패: {e}")
            return {"users": [], "created_at": datetime.now().isoformat(), "last_updated": datetime.now().isoformat()}
    
    def _save_users(self, data: Dict):
        """사용자 데이터 저장"""
        try:
            data["last_updated"] = datetime.now().isoformat()
            with FileLock(self.lock_file):
                with open(self.users_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("사용자 데이터 저장 완료")
        except Exception as e:
            logger.error(f"사용자 데이터 저장 실패: {e}")
            raise
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_user(self, username: str, password: str, email: str, role: str = "user") -> Dict:
        """새 사용자 생성"""
        data = self._load_users()
        
        # 중복 사용자명 확인
        for user in data["users"]:
            if user["username"] == username:
                raise ValueError("이미 존재하는 사용자명입니다")
            if user["email"] == email:
                raise ValueError("이미 존재하는 이메일입니다")
        
        # 새 사용자 생성
        new_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": self._hash_password(password),
            "email": email,
            "role": role,
            "status": "pending" if role == "user" else "active",  # 일반 사용자는 관리자 승인 필요
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "login_attempts": 0,
            "locked_until": None
        }
        
        data["users"].append(new_user)
        self._save_users(data)
        
        logger.info(f"새 사용자 생성: {username} (role: {role}, status: {new_user['status']})")
        return new_user
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """사용자 인증"""
        data = self._load_users()
        
        for user in data["users"]:
            if user["username"] == username:
                # 계정 잠금 확인
                if user.get("locked_until") and datetime.fromisoformat(user["locked_until"]) > datetime.now():
                    logger.warning(f"잠긴 계정 로그인 시도: {username}")
                    raise ValueError("계정이 일시적으로 잠겨있습니다")
                
                # 비밀번호 확인
                if self._verify_password(password, user["password_hash"]):
                    # 계정 상태 확인
                    if user["status"] != "active":
                        logger.warning(f"비활성 계정 로그인 시도: {username} (status: {user['status']})")
                        raise ValueError("계정이 활성화되지 않았습니다. 관리자 승인을 기다려주세요")
                    
                    # 로그인 성공 처리
                    user["last_login"] = datetime.now().isoformat()
                    user["login_attempts"] = 0
                    user["locked_until"] = None
                    self._save_users(data)
                    
                    logger.info(f"로그인 성공: {username}")
                    return user
                else:
                    # 로그인 실패 처리
                    user["login_attempts"] = user.get("login_attempts", 0) + 1
                    if user["login_attempts"] >= 5:
                        user["locked_until"] = (datetime.now() + timedelta(minutes=30)).isoformat()
                        logger.warning(f"계정 잠김: {username} (5회 실패)")
                    self._save_users(data)
                    
                    logger.warning(f"로그인 실패: {username} (시도 횟수: {user['login_attempts']})")
                    raise ValueError("사용자명 또는 비밀번호가 올바르지 않습니다")
        
        logger.warning(f"존재하지 않는 사용자 로그인 시도: {username}")
        raise ValueError("사용자명 또는 비밀번호가 올바르지 않습니다")
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """사용자 ID로 사용자 정보 조회"""
        data = self._load_users()
        for user in data["users"]:
            if user["id"] == user_id:
                return user
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """사용자명으로 사용자 정보 조회"""
        data = self._load_users()
        for user in data["users"]:
            if user["username"] == username:
                return user
        return None
    
    def update_user_status(self, user_id: str, status: str) -> bool:
        """사용자 상태 업데이트 (관리자 승인용)"""
        data = self._load_users()
        for user in data["users"]:
            if user["id"] == user_id:
                user["status"] = status
                self._save_users(data)
                logger.info(f"사용자 상태 업데이트: {user['username']} -> {status}")
                return True
        return False
    
    def get_pending_users(self) -> List[Dict]:
        """승인 대기 중인 사용자 목록"""
        data = self._load_users()
        return [user for user in data["users"] if user["status"] == "pending"]
    
    def get_all_users(self) -> List[Dict]:
        """모든 사용자 목록 (관리자용)"""
        data = self._load_users()
        return data["users"]

# 전역 AuthManager 인스턴스
auth_manager = AuthManager()

# 세션 관리 함수들
def login_user(user: Dict):
    """사용자 로그인 (세션 설정)"""
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['logged_in'] = True
    session.permanent = True
    logger.info(f"세션 생성: {user['username']}")

def logout_user():
    """사용자 로그아웃 (세션 정리)"""
    username = session.get('username', 'Unknown')
    session.clear()
    logger.info(f"세션 종료: {username}")

def is_logged_in() -> bool:
    """로그인 상태 확인"""
    return session.get('logged_in', False)

def get_current_user() -> Optional[Dict]:
    """현재 로그인한 사용자 정보"""
    if not is_logged_in():
        return None
    user_id = session.get('user_id')
    if user_id:
        return auth_manager.get_user_by_id(user_id)
    return None

def is_admin() -> bool:
    """관리자 권한 확인"""
    return session.get('role') == 'admin'

# 데코레이터 함수들
def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            if request.is_json:
                return jsonify({'success': False, 'error': '로그인이 필요합니다', 'error_code': 'AUTH_REQUIRED'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """관리자 권한 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            if request.is_json:
                return jsonify({'success': False, 'error': '로그인이 필요합니다', 'error_code': 'AUTH_REQUIRED'}), 401
            return redirect('/login')
        
        if not is_admin():
            if request.is_json:
                return jsonify({'success': False, 'error': '관리자 권한이 필요합니다', 'error_code': 'ADMIN_REQUIRED'}), 403
            return jsonify({'error': '관리자 권한이 필요합니다'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role: str):
    """특정 역할 필수 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_logged_in():
                if request.is_json:
                    return jsonify({'success': False, 'error': '로그인이 필요합니다', 'error_code': 'AUTH_REQUIRED'}), 401
                return redirect('/login')
            
            user_role = session.get('role')
            if user_role != required_role and user_role != 'admin':  # 관리자는 모든 권한 가짐
                if request.is_json:
                    return jsonify({'success': False, 'error': f'{required_role} 권한이 필요합니다', 'error_code': 'ROLE_REQUIRED'}), 403
                return jsonify({'error': f'{required_role} 권한이 필요합니다'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator