# -*- coding: utf-8 -*-
"""
Personal AI Agent - 認証・認可システム
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets
from functools import wraps

from config.settings import SecurityConfig
from .encryption import EncryptionManager

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """ユーザー役割"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class Permission(Enum):
    """権限定義"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SYSTEM = "system"

@dataclass
class User:
    """ユーザー情報"""
    user_id: str
    username: str
    email: Optional[str]
    role: UserRole
    permissions: List[Permission]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class Session:
    """セッション情報"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_active: bool

class AuthenticationManager:
    """
    認証管理システム
    
    JWT トークンベースの認証とセッション管理を提供
    """
    
    def __init__(self, config: SecurityConfig, encryption_manager: EncryptionManager):
        self.config = config
        self.encryption_manager = encryption_manager
        
        # セッション管理
        self.active_sessions: Dict[str, Session] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        
        # JWT設定
        self.jwt_algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=config.jwt_expire_minutes)
        self.refresh_token_expire = timedelta(days=7)
        
        logger.info("AuthenticationManager initialized")
    
    def create_user(self, 
                   username: str,
                   password: str,
                   email: Optional[str] = None,
                   role: UserRole = UserRole.USER) -> User:
        """新しいユーザーを作成"""
        
        # パスワードハッシュ化
        password_hash, salt = self.encryption_manager.hash_password(password)
        
        # ユーザーID生成
        user_id = secrets.token_urlsafe(16)
        
        # 権限設定
        permissions = self._get_default_permissions(role)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions,
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            metadata={
                "password_hash": password_hash,
                "salt": salt,
                "created_by": "system"
            }
        )
        
        logger.info(f"User created: {username}")
        return user
    
    def authenticate_user(self, 
                         username: str, 
                         password: str,
                         ip_address: Optional[str] = None) -> Optional[tuple[User, str, str]]:
        """ユーザー認証"""
        
        # レート制限チェック
        if not self._check_rate_limit(username, ip_address):
            logger.warning(f"Rate limit exceeded for user: {username}")
            return None
        
        # ユーザー検索（実際の実装ではデータベースから取得）
        user = self._find_user_by_username(username)
        if not user or not user.is_active:
            self._record_failed_attempt(username, ip_address)
            return None
        
        # パスワード検証
        if not self.encryption_manager.verify_password(
            password, 
            user.metadata["password_hash"], 
            user.metadata["salt"]
        ):
            self._record_failed_attempt(username, ip_address)
            return None
        
        # 認証成功
        user.last_login = datetime.now()
        
        # トークン生成
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)
        
        logger.info(f"User authenticated: {username}")
        return user, access_token, refresh_token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT トークンの検証"""
        
        try:
            payload = jwt.decode(
                token, 
                self.config.secret_key, 
                algorithms=[self.jwt_algorithm]
            )
            
            # トークンの有効期限チェック
            if datetime.fromtimestamp(payload["exp"]) < datetime.now():
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """アクセストークンの更新"""
        
        try:
            payload = jwt.decode(
                refresh_token, 
                self.config.secret_key, 
                algorithms=[self.jwt_algorithm]
            )
            
            if payload.get("type") != "refresh":
                return None
            
            # ユーザー取得
            user = self._find_user_by_id(payload["user_id"])
            if not user or not user.is_active:
                return None
            
            # 新しいアクセストークン生成
            return self._generate_access_token(user)
            
        except jwt.InvalidTokenError:
            return None
    
    def logout_user(self, token: str) -> bool:
        """ユーザーログアウト"""
        
        payload = self.verify_token(token)
        if not payload:
            return False
        
        session_id = payload.get("session_id")
        if session_id and session_id in self.active_sessions:
            self.active_sessions[session_id].is_active = False
            logger.info(f"User logged out: {payload['username']}")
            return True
        
        return False
    
    def create_session(self, 
                      user: User,
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> Session:
        """セッション作成"""
        
        session_id = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.access_token_expire,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )
        
        self.active_sessions[session_id] = session
        return session
    
    def get_active_session(self, session_id: str) -> Optional[Session]:
        """アクティブセッション取得"""
        
        session = self.active_sessions.get(session_id)
        if session and session.is_active and session.expires_at > datetime.now():
            return session
        
        return None
    
    def _generate_access_token(self, user: User) -> str:
        """アクセストークン生成"""
        
        session = self.create_session(user)
        
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "permissions": [p.value for p in user.permissions],
            "session_id": session.session_id,
            "type": "access",
            "iat": datetime.now(),
            "exp": datetime.now() + self.access_token_expire
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.jwt_algorithm)
    
    def _generate_refresh_token(self, user: User) -> str:
        """リフレッシュトークン生成"""
        
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "type": "refresh",
            "iat": datetime.now(),
            "exp": datetime.now() + self.refresh_token_expire
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.jwt_algorithm)
    
    def _get_default_permissions(self, role: UserRole) -> List[Permission]:
        """役割に基づくデフォルト権限"""
        
        if role == UserRole.ADMIN:
            return [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN]
        elif role == UserRole.USER:
            return [Permission.READ, Permission.WRITE]
        else:  # GUEST
            return [Permission.READ]
    
    def _check_rate_limit(self, username: str, ip_address: Optional[str]) -> bool:
        """レート制限チェック"""
        
        key = ip_address or username
        now = datetime.now()
        window = timedelta(minutes=15)
        
        if key not in self.failed_attempts:
            return True
        
        # 15分以内の失敗試行をカウント
        recent_attempts = [
            attempt for attempt in self.failed_attempts[key]
            if now - attempt < window
        ]
        
        return len(recent_attempts) < self.config.max_login_attempts
    
    def _record_failed_attempt(self, username: str, ip_address: Optional[str]) -> None:
        """失敗試行を記録"""
        
        key = ip_address or username
        if key not in self.failed_attempts:
            self.failed_attempts[key] = []
        
        self.failed_attempts[key].append(datetime.now())
        
        # 古い記録をクリーンアップ
        window = timedelta(minutes=15)
        self.failed_attempts[key] = [
            attempt for attempt in self.failed_attempts[key]
            if datetime.now() - attempt < window
        ]
    
    def _find_user_by_username(self, username: str) -> Optional[User]:
        """ユーザー名でユーザー検索（模擬実装）"""
        # 実際の実装ではデータベースから取得
        return None
    
    def _find_user_by_id(self, user_id: str) -> Optional[User]:
        """ユーザーIDでユーザー検索（模擬実装）"""
        # 実際の実装ではデータベースから取得
        return None

class AuthorizationManager:
    """
    認可管理システム
    
    ユーザーの権限チェックとアクセス制御
    """
    
    def __init__(self):
        self.resource_permissions: Dict[str, List[Permission]] = {}
        logger.info("AuthorizationManager initialized")
    
    def register_resource(self, resource: str, required_permissions: List[Permission]) -> None:
        """リソースに必要な権限を登録"""
        self.resource_permissions[resource] = required_permissions
    
    def check_permission(self, user: User, resource: str, action: Permission) -> bool:
        """ユーザーの権限をチェック"""
        
        # ユーザーがアクティブかチェック
        if not user.is_active:
            return False
        
        # 管理者は全権限を持つ
        if Permission.ADMIN in user.permissions:
            return True
        
        # リソース固有の権限チェック
        if resource in self.resource_permissions:
            required_permissions = self.resource_permissions[resource]
            if action not in required_permissions:
                return True  # 権限が不要なアクション
        
        # ユーザーが必要な権限を持っているかチェック
        return action in user.permissions
    
    def require_permission(self, resource: str, action: Permission):
        """権限チェックデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 実際の実装では現在のユーザーを取得
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise PermissionError("Authentication required")
                
                if not self.check_permission(current_user, resource, action):
                    raise PermissionError(f"Permission denied for {action.value} on {resource}")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

class SecurityAuditLogger:
    """
    セキュリティ監査ログ
    
    認証・認可に関するセキュリティイベントを記録
    """
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        
        # セキュリティ専用ログ設定
        self.security_logger = logging.getLogger('security_audit')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.INFO)
    
    def log_authentication_success(self, username: str, ip_address: Optional[str] = None) -> None:
        """認証成功ログ"""
        self.security_logger.info(
            f"AUTH_SUCCESS - User: {username}, IP: {ip_address or 'unknown'}"
        )
    
    def log_authentication_failure(self, username: str, ip_address: Optional[str] = None, reason: str = "") -> None:
        """認証失敗ログ"""
        self.security_logger.warning(
            f"AUTH_FAILURE - User: {username}, IP: {ip_address or 'unknown'}, Reason: {reason}"
        )
    
    def log_permission_denied(self, username: str, resource: str, action: str) -> None:
        """権限拒否ログ"""
        self.security_logger.warning(
            f"PERMISSION_DENIED - User: {username}, Resource: {resource}, Action: {action}"
        )
    
    def log_session_created(self, username: str, session_id: str) -> None:
        """セッション作成ログ"""
        self.security_logger.info(
            f"SESSION_CREATED - User: {username}, Session: {session_id}"
        )
    
    def log_session_expired(self, username: str, session_id: str) -> None:
        """セッション期限切れログ"""
        self.security_logger.info(
            f"SESSION_EXPIRED - User: {username}, Session: {session_id}"
        )
    
    def log_suspicious_activity(self, event: str, details: Dict[str, Any]) -> None:
        """疑わしい活動ログ"""
        self.security_logger.warning(
            f"SUSPICIOUS_ACTIVITY - Event: {event}, Details: {details}"
        )

class SecurityConfig:
    """セキュリティ設定"""
    
    @staticmethod
    def get_secure_headers() -> Dict[str, str]:
        """セキュアHTTPヘッダー"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """パスワード強度チェック"""
        
        checks = {
            "length": len(password) >= 8,
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digit": any(c.isdigit() for c in password),
            "special": any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
        }
        
        score = sum(checks.values())
        
        return {
            "valid": score >= 4,
            "score": score,
            "max_score": 5,
            "checks": checks,
            "strength": "weak" if score < 3 else "medium" if score < 5 else "strong"
        }