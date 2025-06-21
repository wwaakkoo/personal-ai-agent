# -*- coding: utf-8 -*-
"""
Personal AI Agent - 設定管理モジュール
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import yaml
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

@dataclass
class DatabaseConfig:
    """データベース設定"""
    url: str = "sqlite:///./agent_data.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

@dataclass
class LLMConfig:
    """LLM API設定"""
    provider: str = "openai"  # openai, anthropic
    api_key: Optional[str] = None
    model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.7

@dataclass
class SecurityConfig:
    """セキュリティ設定"""
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    encryption_key: Optional[str] = None
    jwt_expire_minutes: int = 30
    max_login_attempts: int = 5

@dataclass
class InterfaceConfig:
    """インターフェース設定"""
    cli_enabled: bool = True
    web_enabled: bool = True
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    auto_reload: bool = False

@dataclass
class AgentConfig:
    """エージェント動作設定"""
    name: str = "PersonalAI"
    timezone: str = "Asia/Tokyo"
    language: str = "ja"
    learning_enabled: bool = True
    context_window_size: int = 10
    max_memory_items: int = 1000

class Settings:
    """アプリケーション設定管理"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.security = SecurityConfig()
        self.interface = InterfaceConfig()
        self.agent = AgentConfig()
        
        # 環境変数から設定を上書き
        self._load_from_env()
    
    def _load_from_env(self):
        """環境変数から設定を読み込み"""
        # LLM設定
        if api_key := os.getenv("OPENAI_API_KEY"):
            self.llm.api_key = api_key
        if model := os.getenv("LLM_MODEL"):
            self.llm.model = model
            
        # データベース設定
        if db_url := os.getenv("DATABASE_URL"):
            self.database.url = db_url
            
        # セキュリティ設定
        if secret := os.getenv("SECRET_KEY"):
            self.security.secret_key = secret
            
        # インターフェース設定
        if host := os.getenv("WEB_HOST"):
            self.interface.web_host = host
        if port := os.getenv("WEB_PORT"):
            self.interface.web_port = int(port)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        """設定ファイルから読み込み"""
        settings = cls()
        
        if config_path and config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                settings._update_from_dict(config_data)
        
        return settings
    
    @classmethod
    def create_default(cls) -> "Settings":
        """デフォルト設定でインスタンス作成"""
        return cls()
    
    def _update_from_dict(self, config_data: Dict[str, Any]):
        """辞書データから設定を更新"""
        for section, values in config_data.items():
            if hasattr(self, section) and isinstance(values, dict):
                section_obj = getattr(self, section)
                for key, value in values.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
    
    def save(self, config_path: Optional[Path] = None):
        """設定をファイルに保存"""
        if config_path is None:
            config_path = Path("config/settings.yaml")
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            'database': asdict(self.database),
            'llm': asdict(self.llm),
            'security': asdict(self.security),
            'interface': asdict(self.interface),
            'agent': asdict(self.agent)
        }
        
        # API キーなどの機密情報は保存しない
        if 'api_key' in config_data['llm']:
            config_data['llm']['api_key'] = "<set-via-environment>"
        config_data['security']['secret_key'] = "<set-via-environment>"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で設定を取得"""
        return {
            'database': asdict(self.database),
            'llm': asdict(self.llm),
            'security': asdict(self.security),
            'interface': asdict(self.interface),
            'agent': asdict(self.agent)
        }