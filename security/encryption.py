"""
Personal AI Agent - データ暗号化システム
"""

import os
import base64
import logging
from typing import Dict, Optional, Union, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets

logger = logging.getLogger(__name__)

class EncryptionManager:
    """
    データ暗号化管理システム
    
    AES-256暗号化を使用してユーザーデータを保護し、
    安全な鍵管理とデータ暗号化・復号化を提供
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key
        self.fernet_key = None
        self.cipher_suite = None
        
        # 初期化
        self._initialize_encryption()
        
        logger.info("EncryptionManager initialized")
    
    def _initialize_encryption(self) -> None:
        """暗号化システムの初期化"""
        
        if self.master_key:
            # マスターキーから暗号化キーを導出
            self.fernet_key = self._derive_key_from_master(self.master_key)
        else:
            # 新しいキーを生成
            self.fernet_key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(self.fernet_key)
    
    def _derive_key_from_master(self, master_key: str, salt: Optional[bytes] = None) -> bytes:
        """マスターキーから暗号化キーを導出"""
        
        if salt is None:
            # デフォルトのソルト（実運用では動的生成を推奨）
            salt = b'personal_ai_agent_salt_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return key
    
    def encrypt_string(self, plaintext: str) -> str:
        """文字列を暗号化"""
        
        try:
            encrypted_data = self.cipher_suite.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encrypt string: {e}")
            raise
    
    def decrypt_string(self, ciphertext: str) -> str:
        """暗号化された文字列を復号化"""
        
        try:
            encrypted_data = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to decrypt string: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """辞書データを暗号化"""
        
        try:
            import json
            json_string = json.dumps(data, ensure_ascii=False)
            return self.encrypt_string(json_string)
            
        except Exception as e:
            logger.error(f"Failed to encrypt dict: {e}")
            raise
    
    def decrypt_dict(self, ciphertext: str) -> Dict[str, Any]:
        """暗号化された辞書データを復号化"""
        
        try:
            import json
            json_string = self.decrypt_string(ciphertext)
            return json.loads(json_string)
            
        except Exception as e:
            logger.error(f"Failed to decrypt dict: {e}")
            raise
    
    def encrypt_file(self, input_file_path: str, output_file_path: str) -> bool:
        """ファイルを暗号化"""
        
        try:
            with open(input_file_path, 'rb') as infile:
                file_data = infile.read()
            
            encrypted_data = self.cipher_suite.encrypt(file_data)
            
            with open(output_file_path, 'wb') as outfile:
                outfile.write(encrypted_data)
            
            logger.info(f"File encrypted: {input_file_path} -> {output_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to encrypt file: {e}")
            return False
    
    def decrypt_file(self, input_file_path: str, output_file_path: str) -> bool:
        """暗号化されたファイルを復号化"""
        
        try:
            with open(input_file_path, 'rb') as infile:
                encrypted_data = infile.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            
            with open(output_file_path, 'wb') as outfile:
                outfile.write(decrypted_data)
            
            logger.info(f"File decrypted: {input_file_path} -> {output_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to decrypt file: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """セキュアなトークンを生成"""
        
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """パスワードをハッシュ化"""
        
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        hashed_password = kdf.derive(password.encode())
        
        return (
            base64.urlsafe_b64encode(hashed_password).decode('utf-8'),
            base64.urlsafe_b64encode(salt).decode('utf-8')
        )
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """パスワードを検証"""
        
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode('utf-8'))
            expected_hash = base64.urlsafe_b64decode(hashed_password.encode('utf-8'))
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
                backend=default_backend()
            )
            
            kdf.verify(password.encode(), expected_hash)
            return True
            
        except Exception:
            return False
    
    def get_key_info(self) -> Dict[str, str]:
        """暗号化キーの情報を取得"""
        
        return {
            "key_algorithm": "AES-256",
            "key_derivation": "PBKDF2-SHA256",
            "iterations": "100000",
            "has_master_key": bool(self.master_key),
            "key_fingerprint": base64.urlsafe_b64encode(
                hashes.Hash(hashes.SHA256(), backend=default_backend())
                .finalize()[:8]
            ).decode('utf-8')
        }

class SecureStorage:
    """
    セキュアストレージ
    
    暗号化されたデータストレージを提供
    """
    
    def __init__(self, storage_path: str, encryption_manager: EncryptionManager):
        self.storage_path = storage_path
        self.encryption_manager = encryption_manager
        
        # ストレージディレクトリの作成
        os.makedirs(storage_path, exist_ok=True)
        
        logger.info(f"SecureStorage initialized: {storage_path}")
    
    def store_secure_data(self, key: str, data: Any) -> bool:
        """データを暗号化して保存"""
        
        try:
            # データを JSON シリアライズして暗号化
            import json
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            encrypted_data = self.encryption_manager.encrypt_string(json_data)
            
            # ファイルに保存
            file_path = os.path.join(self.storage_path, f"{key}.enc")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            logger.debug(f"Secure data stored: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secure data {key}: {e}")
            return False
    
    def load_secure_data(self, key: str) -> Optional[Any]:
        """暗号化されたデータを読み込み"""
        
        try:
            file_path = os.path.join(self.storage_path, f"{key}.enc")
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
            
            # 復号化してデシリアライズ
            decrypted_data = self.encryption_manager.decrypt_string(encrypted_data)
            
            import json
            return json.loads(decrypted_data)
            
        except Exception as e:
            logger.error(f"Failed to load secure data {key}: {e}")
            return None
    
    def delete_secure_data(self, key: str) -> bool:
        """暗号化されたデータを削除"""
        
        try:
            file_path = os.path.join(self.storage_path, f"{key}.enc")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Secure data deleted: {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete secure data {key}: {e}")
            return False
    
    def list_secure_keys(self) -> list[str]:
        """保存されているキーの一覧を取得"""
        
        try:
            keys = []
            for filename in os.listdir(self.storage_path):
                if filename.endswith('.enc'):
                    keys.append(filename[:-4])  # .enc を除去
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list secure keys: {e}")
            return []

class DataProtectionManager:
    """
    データ保護管理システム
    
    個人情報の検出と保護、データマスキング機能
    """
    
    def __init__(self):
        # 個人情報パターン
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+81|0)\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'japanese_name': r'[一-龯][一-龯\s]{1,10}[一-龯]',
        }
        
        logger.info("DataProtectionManager initialized")
    
    def detect_pii(self, text: str) -> Dict[str, list]:
        """個人情報を検出"""
        
        import re
        detected = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = matches
        
        return detected
    
    def mask_pii(self, text: str, mask_char: str = '*') -> str:
        """個人情報をマスク"""
        
        import re
        
        masked_text = text
        
        for pii_type, pattern in self.pii_patterns.items():
            def mask_match(match):
                matched_text = match.group(0)
                if pii_type == 'email':
                    # メールアドレスのローカル部をマスク
                    local, domain = matched_text.split('@')
                    masked_local = local[0] + mask_char * (len(local) - 2) + local[-1] if len(local) > 2 else mask_char * len(local)
                    return f"{masked_local}@{domain}"
                elif pii_type == 'phone':
                    # 電話番号の中央部をマスク
                    return re.sub(r'\d', mask_char, matched_text[:-4]) + matched_text[-4:]
                elif pii_type == 'credit_card':
                    # クレジットカード番号の中央部をマスク
                    return matched_text[:4] + mask_char * (len(matched_text) - 8) + matched_text[-4:]
                else:
                    # その他は部分マスク
                    if len(matched_text) > 2:
                        return matched_text[0] + mask_char * (len(matched_text) - 2) + matched_text[-1]
                    else:
                        return mask_char * len(matched_text)
            
            masked_text = re.sub(pattern, mask_match, masked_text)
        
        return masked_text
    
    def sanitize_for_logging(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """ログ出力用にデータをサニタイズ"""
        
        if isinstance(data, str):
            return self.mask_pii(data)
        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    sanitized[key] = self.mask_pii(value)
                elif isinstance(value, dict):
                    sanitized[key] = self.sanitize_for_logging(value)
                else:
                    sanitized[key] = value
            return sanitized
        else:
            return data
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """フィールド名から機密情報かどうかを判定"""
        
        sensitive_fields = {
            'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'api_key',
            'access_token', 'refresh_token', 'private_key', 'email', 'phone',
            'credit_card', 'ssn', 'personal_id', 'address'
        }
        
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in sensitive_fields)