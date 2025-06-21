"""
Personal AI Agent - 記憶・学習システム
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from uuid import uuid4

from config.settings import Settings

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    """記憶項目の基本構造"""
    id: str
    content: str
    content_type: str  # interaction, learning, knowledge, preference
    timestamp: datetime
    importance: float  # 0.0 - 1.0
    access_count: int
    last_accessed: datetime
    tags: List[str]
    metadata: Dict[str, Any]
    expiry_date: Optional[datetime] = None

@dataclass
class SessionData:
    """セッションデータ"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    interactions: List[str]  # memory_item_ids
    context: Dict[str, Any]
    summary: Optional[str] = None

class MemorySystem:
    """
    AIエージェントの記憶・学習システム
    
    短期記憶・長期記憶・エピソード記憶を管理し、
    学習データの蓄積と検索を行う
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.max_memory_items = settings.agent.max_memory_items
        
        # 記憶ストレージ（実際の実装ではデータベースを使用）
        self.memory_items: Dict[str, MemoryItem] = {}
        self.sessions: Dict[str, SessionData] = {}
        
        # 短期記憶（現在のセッション内での一時的な記憶）
        self.short_term_memory: List[str] = []  # memory_item_ids
        
        # 学習データキャッシュ
        self.learning_cache: Dict[str, Any] = {}
        
        # 記憶の重要度計算用パラメータ
        self.importance_decay_rate = 0.1
        self.access_boost_factor = 0.1
        
        logger.info("MemorySystem initialized")
    
    async def initialize(self) -> None:
        """記憶システムの初期化"""
        try:
            # データベースからの記憶データ読み込み
            await self._load_memory_from_storage()
            
            # 古い記憶の清掃
            await self._cleanup_expired_memories()
            
            logger.info(f"MemorySystem initialized with {len(self.memory_items)} items")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory system: {e}")
            raise
    
    async def store_interaction(self, 
                              user_input: str, 
                              agent_response: str,
                              intent: Dict[str, Any],
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """対話の記憶を保存"""
        
        memory_id = str(uuid4())
        
        interaction_data = {
            "user_input": user_input,
            "agent_response": agent_response,
            "intent": intent,
            "metadata": metadata or {}
        }
        
        # 重要度の計算
        importance = await self._calculate_importance(
            content=json.dumps(interaction_data, ensure_ascii=False),
            content_type="interaction",
            metadata=metadata
        )
        
        memory_item = MemoryItem(
            id=memory_id,
            content=json.dumps(interaction_data, ensure_ascii=False),
            content_type="interaction",
            timestamp=datetime.now(),
            importance=importance,
            access_count=1,
            last_accessed=datetime.now(),
            tags=await self._extract_tags(user_input, agent_response),
            metadata=metadata or {}
        )
        
        await self._store_memory_item(memory_item)
        
        # 短期記憶に追加
        self.short_term_memory.append(memory_id)
        if len(self.short_term_memory) > self.settings.agent.context_window_size:
            self.short_term_memory.pop(0)
        
        return memory_id
    
    async def store_learning_data(self, learning_data: Dict[str, Any]) -> str:
        """学習データの保存"""
        
        memory_id = str(uuid4())
        
        importance = await self._calculate_importance(
            content=json.dumps(learning_data, ensure_ascii=False),
            content_type="learning",
            metadata=learning_data
        )
        
        memory_item = MemoryItem(
            id=memory_id,
            content=json.dumps(learning_data, ensure_ascii=False),
            content_type="learning",
            timestamp=datetime.now(),
            importance=importance,
            access_count=1,
            last_accessed=datetime.now(),
            tags=["learning", learning_data.get("intent", {}).get("primary", "general")],
            metadata=learning_data
        )
        
        await self._store_memory_item(memory_item)
        return memory_id
    
    async def store_knowledge(self, 
                            knowledge: str, 
                            source: str,
                            tags: Optional[List[str]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """知識データの保存"""
        
        memory_id = str(uuid4())
        
        knowledge_data = {
            "content": knowledge,
            "source": source,
            "metadata": metadata or {}
        }
        
        importance = await self._calculate_importance(
            content=knowledge,
            content_type="knowledge",
            metadata=metadata
        )
        
        memory_item = MemoryItem(
            id=memory_id,
            content=json.dumps(knowledge_data, ensure_ascii=False),
            content_type="knowledge",
            timestamp=datetime.now(),
            importance=importance,
            access_count=1,
            last_accessed=datetime.now(),
            tags=tags or ["knowledge"],
            metadata=metadata or {}
        )
        
        await self._store_memory_item(memory_item)
        return memory_id
    
    async def retrieve_memories(self, 
                              query: str,
                              content_type: Optional[str] = None,
                              limit: int = 10,
                              min_importance: float = 0.0) -> List[MemoryItem]:
        """記憶の検索・取得"""
        
        # 簡単なキーワードベース検索（実際の実装ではベクトル検索等を使用）
        query_words = query.lower().split()
        matching_items = []
        
        for memory_item in self.memory_items.values():
            if content_type and memory_item.content_type != content_type:
                continue
                
            if memory_item.importance < min_importance:
                continue
            
            # コンテンツとタグでのマッチング
            content_lower = memory_item.content.lower()
            tags_lower = [tag.lower() for tag in memory_item.tags]
            
            relevance_score = 0.0
            for word in query_words:
                if word in content_lower:
                    relevance_score += 1.0
                if any(word in tag for tag in tags_lower):
                    relevance_score += 0.5
            
            if relevance_score > 0:
                # アクセス履歴の更新
                memory_item.access_count += 1
                memory_item.last_accessed = datetime.now()
                
                matching_items.append((memory_item, relevance_score))
        
        # 関連度と重要度でソート
        matching_items.sort(
            key=lambda x: (x[1], x[0].importance), 
            reverse=True
        )
        
        return [item[0] for item in matching_items[:limit]]
    
    async def get_context_memories(self) -> List[MemoryItem]:
        """現在のコンテキストに関連する記憶を取得"""
        context_memories = []
        
        for memory_id in self.short_term_memory:
            if memory_id in self.memory_items:
                context_memories.append(self.memory_items[memory_id])
        
        return context_memories
    
    async def start_session(self) -> str:
        """新しいセッションを開始"""
        session_id = str(uuid4())
        
        session_data = SessionData(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            interactions=[],
            context={}
        )
        
        self.sessions[session_id] = session_data
        
        # 短期記憶をリセット
        self.short_term_memory = []
        
        logger.info(f"Started new session: {session_id}")
        return session_id
    
    async def end_session(self, session_id: str) -> None:
        """セッションを終了"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session.end_time = datetime.now()
        
        # セッション要約の生成
        if session.interactions:
            session.summary = await self._generate_session_summary(session)
        
        logger.info(f"Ended session: {session_id}")
    
    async def get_user_preferences(self) -> Dict[str, Any]:
        """ユーザーの嗜好・設定を取得"""
        preference_memories = await self.retrieve_memories(
            query="preference setting",
            content_type="preference",
            limit=50
        )
        
        preferences = {}
        for memory in preference_memories:
            try:
                pref_data = json.loads(memory.content)
                preferences.update(pref_data)
            except json.JSONDecodeError:
                continue
        
        return preferences
    
    async def update_user_preference(self, key: str, value: Any) -> None:
        """ユーザー嗜好の更新"""
        preference_data = {key: value}
        
        memory_id = str(uuid4())
        memory_item = MemoryItem(
            id=memory_id,
            content=json.dumps(preference_data, ensure_ascii=False),
            content_type="preference",
            timestamp=datetime.now(),
            importance=0.8,  # 嗜好は高い重要度
            access_count=1,
            last_accessed=datetime.now(),
            tags=["preference", key],
            metadata={"preference_key": key}
        )
        
        await self._store_memory_item(memory_item)
    
    async def _store_memory_item(self, memory_item: MemoryItem) -> None:
        """記憶項目をストレージに保存"""
        self.memory_items[memory_item.id] = memory_item
        
        # メモリサイズ制限のチェック
        if len(self.memory_items) > self.max_memory_items:
            await self._cleanup_old_memories()
        
        # 実際の実装ではデータベースに永続化
        await self._persist_to_storage(memory_item)
    
    async def _calculate_importance(self, 
                                  content: str, 
                                  content_type: str,
                                  metadata: Optional[Dict[str, Any]] = None) -> float:
        """記憶の重要度を計算"""
        base_importance = {
            "interaction": 0.5,
            "learning": 0.7,
            "knowledge": 0.6,
            "preference": 0.8
        }.get(content_type, 0.5)
        
        # コンテンツの長さによる調整
        length_factor = min(len(content) / 1000, 1.0) * 0.2
        
        # メタデータによる調整
        metadata_factor = 0.0
        if metadata:
            if metadata.get("confidence", 0) > 0.8:
                metadata_factor += 0.1
            if metadata.get("user_feedback") == "positive":
                metadata_factor += 0.2
        
        importance = min(base_importance + length_factor + metadata_factor, 1.0)
        return importance
    
    async def _extract_tags(self, user_input: str, agent_response: str) -> List[str]:
        """対話からタグを抽出"""
        # 簡単なキーワード抽出（実際の実装ではNLPライブラリを使用）
        combined_text = f"{user_input} {agent_response}".lower()
        
        tag_keywords = {
            "task": ["タスク", "todo", "やること", "予定"],
            "email": ["メール", "email", "連絡"],
            "schedule": ["スケジュール", "時間", "予定", "カレンダー"],
            "work": ["仕事", "業務", "プロジェクト", "会議"],
            "personal": ["個人", "プライベート", "家族", "趣味"]
        }
        
        tags = ["interaction"]
        for tag, keywords in tag_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                tags.append(tag)
        
        return tags
    
    async def _cleanup_old_memories(self) -> None:
        """古い記憶の清掃"""
        # 重要度が低く、アクセス頻度の少ない項目を削除
        items_by_score = []
        
        for memory_item in self.memory_items.values():
            # 時間による重要度の減衰
            days_old = (datetime.now() - memory_item.timestamp).days
            decayed_importance = memory_item.importance * (1 - self.importance_decay_rate * days_old)
            
            # アクセス頻度による調整
            access_boost = min(memory_item.access_count * self.access_boost_factor, 0.5)
            
            final_score = decayed_importance + access_boost
            items_by_score.append((memory_item.id, final_score))
        
        # スコアでソートし、下位の項目を削除
        items_by_score.sort(key=lambda x: x[1])
        items_to_remove = items_by_score[:len(self.memory_items) // 4]  # 25%削除
        
        for memory_id, _ in items_to_remove:
            del self.memory_items[memory_id]
        
        logger.info(f"Cleaned up {len(items_to_remove)} old memories")
    
    async def _cleanup_expired_memories(self) -> None:
        """期限切れの記憶を削除"""
        now = datetime.now()
        expired_ids = []
        
        for memory_id, memory_item in self.memory_items.items():
            if (memory_item.expiry_date and 
                memory_item.expiry_date < now):
                expired_ids.append(memory_id)
        
        for memory_id in expired_ids:
            del self.memory_items[memory_id]
        
        if expired_ids:
            logger.info(f"Removed {len(expired_ids)} expired memories")
    
    async def _generate_session_summary(self, session: SessionData) -> str:
        """セッションの要約を生成"""
        # 実際の実装ではLLMを使用してより詳細な要約を生成
        interaction_count = len(session.interactions)
        duration = session.end_time - session.start_time if session.end_time else timedelta(0)
        
        return f"Session summary: {interaction_count} interactions over {duration}"
    
    async def _load_memory_from_storage(self) -> None:
        """ストレージから記憶データを読み込み"""
        # 実際の実装ではデータベースから読み込み
        pass
    
    async def _persist_to_storage(self, memory_item: MemoryItem) -> None:
        """記憶項目をストレージに永続化"""
        # 実際の実装ではデータベースに保存
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """記憶システムの現在状態を取得"""
        return {
            "total_memories": len(self.memory_items),
            "short_term_memories": len(self.short_term_memory),
            "active_sessions": len([s for s in self.sessions.values() if s.end_time is None]),
            "memory_types": {
                content_type: len([m for m in self.memory_items.values() if m.content_type == content_type])
                for content_type in ["interaction", "learning", "knowledge", "preference"]
            }
        }
    
    async def close(self) -> None:
        """記憶システムの終了処理"""
        # 未保存のデータがあれば保存
        logger.info("MemorySystem closed")