"""
Personal AI Agent - コンテキスト管理システム
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import deque

from config.settings import Settings

logger = logging.getLogger(__name__)

@dataclass
class ContextItem:
    """コンテキスト項目"""
    timestamp: datetime
    content: str
    context_type: str  # user_input, agent_response, system_event, environment
    importance: float
    metadata: Dict[str, Any]

@dataclass
class UserState:
    """ユーザーの現在状態"""
    current_focus: Optional[str]  # 現在の関心事・作業内容
    mood: Optional[str]  # 推定される気分・状態
    availability: Optional[str]  # 利用可能性（busy, available, away）
    last_active: datetime
    session_duration: timedelta
    interaction_count: int

@dataclass
class EnvironmentContext:
    """環境コンテキスト"""
    time_of_day: str
    day_of_week: str
    is_weekend: bool
    timezone: str
    location: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None

class ContextManager:
    """
    AIエージェントのコンテキスト管理システム
    
    対話履歴、ユーザー状態、環境情報などを統合管理し、
    適切なレスポンス生成のためのコンテキストを提供
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.context_window_size = settings.agent.context_window_size
        
        # コンテキスト履歴（固定長キュー）
        self.context_history: deque = deque(maxlen=self.context_window_size)
        
        # ユーザー状態管理
        self.user_state = UserState(
            current_focus=None,
            mood=None,
            availability="available",
            last_active=datetime.now(),
            session_duration=timedelta(),
            interaction_count=0
        )
        
        # 環境コンテキスト
        self.environment_context = self._initialize_environment_context()
        
        # セッション開始時刻
        self.session_start_time = datetime.now()
        
        # コンテキスト分析キャッシュ
        self.analysis_cache: Dict[str, Any] = {}
        
        logger.info("ContextManager initialized")
    
    async def initialize(self) -> None:
        """コンテキスト管理システムの初期化"""
        try:
            # 環境情報の更新
            await self._update_environment_context()
            
            logger.info("ContextManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize context manager: {e}")
            raise
    
    async def update_context(self, 
                           user_input: str, 
                           additional_context: Optional[Dict[str, Any]] = None) -> None:
        """コンテキストの更新"""
        
        # ユーザー入力をコンテキストに追加
        user_context = ContextItem(
            timestamp=datetime.now(),
            content=user_input,
            context_type="user_input",
            importance=0.8,
            metadata=additional_context or {}
        )
        
        self.context_history.append(user_context)
        
        # ユーザー状態の更新
        await self._update_user_state(user_input, additional_context)
        
        # 環境コンテキストの更新（必要に応じて）
        await self._update_environment_context()
        
        # キャッシュクリア
        self.analysis_cache.clear()
    
    async def add_agent_response(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """エージェントの応答をコンテキストに追加"""
        
        agent_context = ContextItem(
            timestamp=datetime.now(),
            content=response,
            context_type="agent_response",
            importance=0.6,
            metadata=metadata or {}
        )
        
        self.context_history.append(agent_context)
    
    async def add_system_event(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """システムイベントをコンテキストに追加"""
        
        system_context = ContextItem(
            timestamp=datetime.now(),
            content=event,
            context_type="system_event",
            importance=0.4,
            metadata=metadata or {}
        )
        
        self.context_history.append(system_context)
    
    async def get_current_context(self, include_history: bool = True) -> Dict[str, Any]:
        """現在のコンテキスト情報を取得"""
        
        context = {
            "user_state": asdict(self.user_state),
            "environment": asdict(self.environment_context),
            "session_info": {
                "start_time": self.session_start_time.isoformat(),
                "duration": str(datetime.now() - self.session_start_time),
                "interaction_count": self.user_state.interaction_count
            }
        }
        
        if include_history:
            context["history"] = [
                {
                    "timestamp": item.timestamp.isoformat(),
                    "content": item.content,
                    "type": item.context_type,
                    "importance": item.importance,
                    "metadata": item.metadata
                }
                for item in self.context_history
            ]
        
        return context
    
    async def get_relevant_context(self, query: str, max_items: int = 5) -> List[ContextItem]:
        """クエリに関連するコンテキストを取得"""
        
        # 簡単なキーワードベースの関連度計算
        query_words = query.lower().split()
        relevant_items = []
        
        for item in self.context_history:
            relevance_score = 0.0
            content_lower = item.content.lower()
            
            # キーワードマッチング
            for word in query_words:
                if word in content_lower:
                    relevance_score += 1.0
            
            # 重要度による調整
            relevance_score *= item.importance
            
            # 時間による重み付け（新しいほど高い）
            time_weight = self._calculate_time_weight(item.timestamp)
            relevance_score *= time_weight
            
            if relevance_score > 0:
                relevant_items.append((item, relevance_score))
        
        # 関連度でソート
        relevant_items.sort(key=lambda x: x[1], reverse=True)
        
        return [item[0] for item in relevant_items[:max_items]]
    
    async def get_conversation_summary(self) -> str:
        """現在の会話の要約を生成"""
        
        if not self.context_history:
            return "まだ会話が開始されていません。"
        
        # ユーザー入力とエージェント応答のペアを取得
        conversation_pairs = []
        current_pair = {}
        
        for item in self.context_history:
            if item.context_type == "user_input":
                if current_pair:
                    conversation_pairs.append(current_pair)
                current_pair = {"user": item.content, "agent": ""}
            elif item.context_type == "agent_response" and current_pair:
                current_pair["agent"] = item.content
        
        if current_pair:
            conversation_pairs.append(current_pair)
        
        # 簡単な要約生成（実際の実装ではLLMを使用）
        if not conversation_pairs:
            return "システムメッセージのみの履歴です。"
        
        total_exchanges = len(conversation_pairs)
        recent_topics = self._extract_topics_from_conversation(conversation_pairs[-3:])
        
        summary = f"これまでに{total_exchanges}回のやり取りがありました。"
        if recent_topics:
            summary += f" 最近の話題: {', '.join(recent_topics)}"
        
        return summary
    
    async def analyze_user_intent_trend(self) -> Dict[str, Any]:
        """ユーザーの意図の傾向を分析"""
        
        cache_key = "intent_trend_analysis"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        user_inputs = [
            item for item in self.context_history 
            if item.context_type == "user_input"
        ]
        
        if not user_inputs:
            return {"trends": [], "dominant_intent": None}
        
        # 簡単な意図分析（実際の実装ではより高度な分析を行う）
        intent_keywords = {
            "task_management": ["タスク", "todo", "やること", "予定"],
            "information_seeking": ["教えて", "調べて", "知りたい", "?", "？"],
            "communication": ["メール", "連絡", "返信", "draft"],
            "analysis": ["分析", "統計", "データ", "傾向"]
        }
        
        intent_counts = {intent: 0 for intent in intent_keywords.keys()}
        
        for item in user_inputs:
            content_lower = item.content.lower()
            for intent, keywords in intent_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    intent_counts[intent] += 1
        
        # 傾向の計算
        total_inputs = len(user_inputs)
        trends = [
            {
                "intent": intent,
                "count": count,
                "percentage": (count / total_inputs) * 100 if total_inputs > 0 else 0
            }
            for intent, count in intent_counts.items()
            if count > 0
        ]
        
        trends.sort(key=lambda x: x["count"], reverse=True)
        
        dominant_intent = trends[0]["intent"] if trends else None
        
        result = {
            "trends": trends,
            "dominant_intent": dominant_intent,
            "total_inputs": total_inputs
        }
        
        self.analysis_cache[cache_key] = result
        return result
    
    async def _update_user_state(self, 
                               user_input: str, 
                               additional_context: Optional[Dict[str, Any]] = None) -> None:
        """ユーザー状態の更新"""
        
        now = datetime.now()
        
        # 基本統計の更新
        self.user_state.last_active = now
        self.user_state.session_duration = now - self.session_start_time
        self.user_state.interaction_count += 1
        
        # 現在の関心事の推定
        await self._update_current_focus(user_input)
        
        # 気分・状態の推定
        await self._update_mood_estimation(user_input, additional_context)
        
        # 利用可能性の更新
        await self._update_availability(additional_context)
    
    async def _update_current_focus(self, user_input: str) -> None:
        """現在の関心事を更新"""
        
        # キーワードベースの関心事推定
        focus_keywords = {
            "work": ["仕事", "業務", "プロジェクト", "会議", "タスク"],
            "personal": ["個人", "プライベート", "家族", "趣味"],
            "learning": ["学習", "勉強", "教えて", "調べて"],
            "planning": ["予定", "スケジュール", "計画", "todo"],
            "communication": ["メール", "連絡", "返信", "電話"]
        }
        
        user_input_lower = user_input.lower()
        focus_scores = {}
        
        for focus, keywords in focus_keywords.items():
            score = sum(1 for keyword in keywords if keyword in user_input_lower)
            if score > 0:
                focus_scores[focus] = score
        
        if focus_scores:
            self.user_state.current_focus = max(focus_scores.keys(), key=lambda x: focus_scores[x])
    
    async def _update_mood_estimation(self, 
                                    user_input: str, 
                                    additional_context: Optional[Dict[str, Any]] = None) -> None:
        """気分・状態の推定を更新"""
        
        # 簡単な感情分析（実際の実装ではより高度な分析を行う）
        positive_indicators = ["ありがとう", "良い", "嬉しい", "助かる", "素晴らしい"]
        negative_indicators = ["困った", "大変", "疲れ", "忙しい", "問題"]
        urgent_indicators = ["急いで", "至急", "すぐに", "早く"]
        
        user_input_lower = user_input.lower()
        
        if any(indicator in user_input_lower for indicator in urgent_indicators):
            self.user_state.mood = "urgent"
        elif any(indicator in user_input_lower for indicator in negative_indicators):
            self.user_state.mood = "stressed"
        elif any(indicator in user_input_lower for indicator in positive_indicators):
            self.user_state.mood = "positive"
        else:
            self.user_state.mood = "neutral"
    
    async def _update_availability(self, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """利用可能性の更新"""
        
        if additional_context and "availability" in additional_context:
            self.user_state.availability = additional_context["availability"]
        else:
            # デフォルトは利用可能
            self.user_state.availability = "available"
    
    def _initialize_environment_context(self) -> EnvironmentContext:
        """環境コンテキストの初期化"""
        
        now = datetime.now()
        
        return EnvironmentContext(
            time_of_day=self._get_time_of_day(now),
            day_of_week=now.strftime("%A"),
            is_weekend=now.weekday() >= 5,
            timezone=self.settings.agent.timezone
        )
    
    async def _update_environment_context(self) -> None:
        """環境コンテキストの更新"""
        
        now = datetime.now()
        
        self.environment_context.time_of_day = self._get_time_of_day(now)
        self.environment_context.day_of_week = now.strftime("%A")
        self.environment_context.is_weekend = now.weekday() >= 5
        
        # 必要に応じて位置情報や天気情報も更新
        # await self._update_location_context()
        # await self._update_weather_context()
    
    def _get_time_of_day(self, dt: datetime) -> str:
        """時間帯の判定"""
        hour = dt.hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def _calculate_time_weight(self, timestamp: datetime) -> float:
        """時間による重み付けを計算"""
        
        time_diff = datetime.now() - timestamp
        hours_ago = time_diff.total_seconds() / 3600
        
        # 新しいほど重みが大きい（指数減衰）
        return max(0.1, 1.0 / (1.0 + hours_ago * 0.1))
    
    def _extract_topics_from_conversation(self, conversation_pairs: List[Dict[str, str]]) -> List[str]:
        """会話からトピックを抽出"""
        
        # 簡単なキーワード抽出
        all_text = " ".join([
            f"{pair.get('user', '')} {pair.get('agent', '')}"
            for pair in conversation_pairs
        ])
        
        topic_keywords = {
            "タスク管理": ["タスク", "todo", "やること", "予定"],
            "メール": ["メール", "email", "連絡", "返信"],
            "情報検索": ["調べて", "検索", "教えて", "情報"],
            "分析": ["分析", "データ", "統計", "傾向"]
        }
        
        detected_topics = []
        text_lower = all_text.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics
    
    async def get_status(self) -> Dict[str, Any]:
        """コンテキスト管理システムの現在状態を取得"""
        
        return {
            "context_history_length": len(self.context_history),
            "session_duration": str(self.user_state.session_duration),
            "interaction_count": self.user_state.interaction_count,
            "current_focus": self.user_state.current_focus,
            "user_mood": self.user_state.mood,
            "time_of_day": self.environment_context.time_of_day,
            "cache_size": len(self.analysis_cache)
        }