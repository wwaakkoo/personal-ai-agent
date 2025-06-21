# -*- coding: utf-8 -*-
"""
Personal AI Agent - キャッシュシステム
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import redis
import pickle
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CacheItem:
    """キャッシュ項目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime

class CacheManager:
    """
    キャッシュ管理システム
    
    Redisベースの高速キャッシュとメモリキャッシュを組み合わせて
    効率的なデータアクセスを提供
    """
    
    def __init__(self, 
                 redis_url: Optional[str] = None,
                 enable_memory_cache: bool = True,
                 default_ttl: int = 3600):
        self.redis_url = redis_url
        self.enable_memory_cache = enable_memory_cache
        self.default_ttl = default_ttl
        
        # Redis クライアント
        self.redis_client = None
        
        # メモリキャッシュ
        self.memory_cache: Dict[str, CacheItem] = {}
        self.memory_cache_max_size = 1000
        
        logger.info("CacheManager initialized")
    
    async def initialize(self) -> None:
        """キャッシュシステムの初期化"""
        try:
            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                # 接続テスト
                await self._test_redis_connection()
                logger.info("Redis cache initialized")
            else:
                logger.info("Redis not configured, using memory cache only")
                
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}, falling back to memory cache")
            self.redis_client = None
    
    async def _test_redis_connection(self) -> None:
        """Redis接続のテスト"""
        if self.redis_client:
            self.redis_client.ping()
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None) -> bool:
        """キャッシュに値を設定"""
        
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        try:
            # Redis に保存
            if self.redis_client:
                serialized_value = self._serialize_value(value)
                success = self.redis_client.setex(key, ttl, serialized_value)
                if not success:
                    logger.warning(f"Failed to set Redis cache for key: {key}")
            
            # メモリキャッシュに保存
            if self.enable_memory_cache:
                await self._set_memory_cache(key, value, expires_at)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得"""
        
        try:
            # まずメモリキャッシュを確認
            if self.enable_memory_cache:
                memory_value = await self._get_memory_cache(key)
                if memory_value is not None:
                    return memory_value
            
            # Redis から取得
            if self.redis_client:
                redis_value = self.redis_client.get(key)
                if redis_value:
                    deserialized_value = self._deserialize_value(redis_value)
                    
                    # メモリキャッシュにも保存
                    if self.enable_memory_cache:
                        await self._set_memory_cache(key, deserialized_value)
                    
                    return deserialized_value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """キャッシュから値を削除"""
        
        try:
            success = True
            
            # Redis から削除
            if self.redis_client:
                redis_success = self.redis_client.delete(key)
                success = success and bool(redis_success)
            
            # メモリキャッシュから削除
            if self.enable_memory_cache and key in self.memory_cache:
                del self.memory_cache[key]
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """キャッシュにキーが存在するかチェック"""
        
        try:
            # メモリキャッシュを確認
            if self.enable_memory_cache and key in self.memory_cache:
                item = self.memory_cache[key]
                if item.expires_at and item.expires_at > datetime.now():
                    return True
                elif item.expires_at is None:
                    return True
                else:
                    # 期限切れなので削除
                    del self.memory_cache[key]
            
            # Redis を確認
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check cache existence for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """キーの残り生存時間を取得（秒）"""
        
        try:
            # メモリキャッシュから確認
            if self.enable_memory_cache and key in self.memory_cache:
                item = self.memory_cache[key]
                if item.expires_at:
                    remaining = (item.expires_at - datetime.now()).total_seconds()
                    return max(0, int(remaining))
                else:
                    return -1  # 無期限
            
            # Redis から確認
            if self.redis_client:
                return self.redis_client.ttl(key)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return None
    
    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """キーの生存時間を延長"""
        
        try:
            success = True
            
            # Redis の TTL を延長
            if self.redis_client:
                current_ttl = self.redis_client.ttl(key)
                if current_ttl > 0:
                    new_ttl = current_ttl + additional_seconds
                    redis_success = self.redis_client.expire(key, new_ttl)
                    success = success and redis_success
            
            # メモリキャッシュの TTL を延長
            if self.enable_memory_cache and key in self.memory_cache:
                item = self.memory_cache[key]
                if item.expires_at:
                    item.expires_at += timedelta(seconds=additional_seconds)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to extend TTL for key {key}: {e}")
            return False
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """パターンにマッチするキーと値を取得"""
        
        result = {}
        
        try:
            # Redis からパターンマッチで取得
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                for key in keys:
                    value = await self.get(key)
                    if value is not None:
                        result[key] = value
            
            # メモリキャッシュからも検索
            if self.enable_memory_cache:
                import fnmatch
                for key, item in self.memory_cache.items():
                    if fnmatch.fnmatch(key, pattern):
                        if key not in result:  # Redis の結果を優先
                            if item.expires_at is None or item.expires_at > datetime.now():
                                result[key] = item.value
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get pattern {pattern}: {e}")
            return {}
    
    async def clear(self, pattern: Optional[str] = None) -> bool:
        """キャッシュをクリア"""
        
        try:
            if pattern:
                # パターンマッチするキーのみクリア
                keys_to_delete = []
                
                if self.redis_client:
                    redis_keys = self.redis_client.keys(pattern)
                    for key in redis_keys:
                        self.redis_client.delete(key)
                
                if self.enable_memory_cache:
                    import fnmatch
                    for key in list(self.memory_cache.keys()):
                        if fnmatch.fnmatch(key, pattern):
                            del self.memory_cache[key]
            else:
                # 全てクリア
                if self.redis_client:
                    self.redis_client.flushdb()
                
                if self.enable_memory_cache:
                    self.memory_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    async def _set_memory_cache(self, 
                              key: str, 
                              value: Any, 
                              expires_at: Optional[datetime] = None) -> None:
        """メモリキャッシュに値を設定"""
        
        # キャッシュサイズ制限のチェック
        if len(self.memory_cache) >= self.memory_cache_max_size:
            await self._evict_memory_cache()
        
        cache_item = CacheItem(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            access_count=1,
            last_accessed=datetime.now()
        )
        
        self.memory_cache[key] = cache_item
    
    async def _get_memory_cache(self, key: str) -> Optional[Any]:
        """メモリキャッシュから値を取得"""
        
        if key not in self.memory_cache:
            return None
        
        item = self.memory_cache[key]
        
        # 期限チェック
        if item.expires_at and item.expires_at <= datetime.now():
            del self.memory_cache[key]
            return None
        
        # アクセス情報の更新
        item.access_count += 1
        item.last_accessed = datetime.now()
        
        return item.value
    
    async def _evict_memory_cache(self) -> None:
        """メモリキャッシュの削除ポリシー実行"""
        
        # LRU (Least Recently Used) ポリシーで削除
        items_by_access = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # 古い25%のアイテムを削除
        items_to_remove = len(self.memory_cache) // 4
        
        for i in range(items_to_remove):
            key_to_remove = items_by_access[i][0]
            del self.memory_cache[key_to_remove]
    
    def _serialize_value(self, value: Any) -> str:
        """値をシリアライズ"""
        
        try:
            # JSONでシリアライズできる場合
            return json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            # JSON不可の場合はpickleを使用
            return pickle.dumps(value).hex()
    
    def _deserialize_value(self, serialized: str) -> Any:
        """シリアライズされた値をデシリアライズ"""
        
        try:
            # まずJSONで試行
            return json.loads(serialized)
        except (json.JSONDecodeError, ValueError):
            # JSON不可の場合はpickleを試行
            try:
                return pickle.loads(bytes.fromhex(serialized))
            except Exception:
                # どちらも失敗した場合は文字列として返す
                return serialized
    
    async def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_max_size": self.memory_cache_max_size,
            "redis_connected": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats.update({
                    "redis_used_memory": redis_info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": redis_info.get("connected_clients", 0),
                    "redis_keyspace": redis_info.get("db0", {})
                })
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
        
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """ヘルスチェック"""
        
        health = {
            "memory_cache": True,  # メモリキャッシュは常に利用可能
            "redis": False
        }
        
        if self.redis_client:
            try:
                self.redis_client.ping()
                health["redis"] = True
            except Exception:
                health["redis"] = False
        
        return health