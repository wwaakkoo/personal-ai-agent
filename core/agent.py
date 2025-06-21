# -*- coding: utf-8 -*-
"""
Personal AI Agent - メインエージェントクラス
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config.settings import Settings
from core.memory import MemorySystem
from core.context import ContextManager
from modules.task_manager import TaskManager
from modules.communication import CommunicationModule
from modules.web_scraper import WebScraperModule
from modules.qa_system import QASystem
from modules.life_analytics import LifeAnalyticsModule
from integrations.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    """エージェント応答データ"""
    content: str
    confidence: float
    sources: List[str]
    actions_taken: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]

class PersonalAIAgent:
    """
    私専用AIエージェント - メインクラス
    
    個人の業務・生活をサポートする学習型AIエージェント
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.agent_id = f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # コアシステム初期化
        self.memory = MemorySystem(settings)
        self.context = ContextManager(settings)
        self.llm = LLMProvider(settings.llm)
        
        # 機能モジュール初期化
        self.task_manager = TaskManager(self.memory, self.llm)
        self.communication = CommunicationModule(self.llm)
        self.web_scraper = WebScraperModule()
        self.qa_system = QASystem(self.memory, self.llm)
        self.analytics = LifeAnalyticsModule(self.memory)
        
        # 状態管理
        self.is_running = False
        self.current_session_id = None
        
        logger.info(f"PersonalAIAgent initialized: {self.agent_id}")
    
    async def initialize(self) -> None:
        """エージェントの初期化処理"""
        try:
            # 各モジュールの初期化
            await self.memory.initialize()
            await self.context.initialize()
            
            # セッション開始
            self.current_session_id = await self.memory.start_session()
            self.is_running = True
            
            logger.info("PersonalAIAgent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def process_input(self, 
                          user_input: str, 
                          input_type: str = "text",
                          context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        ユーザー入力を処理してレスポンスを生成
        
        Args:
            user_input: ユーザーからの入力
            input_type: 入力タイプ (text, voice, image, etc.)
            context: 追加コンテキスト情報
            
        Returns:
            AgentResponse: 処理結果とメタデータ
        """
        if not self.is_running:
            await self.initialize()
        
        try:
            # コンテキスト更新
            await self.context.update_context(user_input, context)
            
            # 入力の意図分析
            intent = await self._analyze_intent(user_input)
            
            # 適切なモジュールに処理を委譲
            response = await self._route_to_module(intent, user_input, context)
            
            # メモリに記録
            await self.memory.store_interaction(
                user_input=user_input,
                agent_response=response.content,
                intent=intent,
                metadata=response.metadata
            )
            
            # 学習データ更新
            if self.settings.agent.learning_enabled:
                await self._update_learning_data(user_input, response, intent)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return AgentResponse(
                content=f"申し訳ありません。処理中にエラーが発生しました: {str(e)}",
                confidence=0.0,
                sources=[],
                actions_taken=[],
                suggestions=["エラー詳細を確認して再試行してください"],
                metadata={"error": str(e)}
            )
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """ユーザー入力の意図を分析"""
        # 簡単なキーワードベースの意図分析
        # 実際の実装では、より高度なNLP処理を行う
        
        intent_mapping = {
            "task": ["タスク", "todo", "やること", "予定", "スケジュール"],
            "email": ["メール", "email", "連絡", "返信", "draft"],
            "search": ["検索", "調べて", "探して", "情報", "web"],
            "question": ["質問", "教えて", "どう", "なぜ", "?", "？"],
            "analysis": ["分析", "統計", "データ", "傾向", "パターン"]
        }
        
        user_input_lower = user_input.lower()
        intent_scores = {}
        
        for intent_type, keywords in intent_mapping.items():
            score = sum(1 for keyword in keywords if keyword in user_input_lower)
            if score > 0:
                intent_scores[intent_type] = score
        
        # 最も高いスコアの意図を選択
        if intent_scores:
            primary_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
            confidence = intent_scores[primary_intent] / len(user_input.split())
        else:
            primary_intent = "general"
            confidence = 0.5
        
        return {
            "primary": primary_intent,
            "confidence": confidence,
            "scores": intent_scores
        }
    
    async def _route_to_module(self, 
                             intent: Dict[str, Any], 
                             user_input: str, 
                             context: Optional[Dict[str, Any]]) -> AgentResponse:
        """意図に基づいて適切なモジュールに処理を委譲"""
        
        primary_intent = intent["primary"]
        
        try:
            if primary_intent == "task":
                return await self._handle_task_intent(user_input, context)
            elif primary_intent == "email":
                return await self._handle_communication_intent(user_input, context)
            elif primary_intent == "search":
                return await self._handle_search_intent(user_input, context)
            elif primary_intent == "question":
                return await self._handle_qa_intent(user_input, context)
            elif primary_intent == "analysis":
                return await self._handle_analytics_intent(user_input, context)
            else:
                return await self._handle_general_intent(user_input, context)
                
        except Exception as e:
            logger.error(f"Error in module routing: {e}")
            raise
    
    async def _handle_task_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """タスク関連の処理"""
        result = await self.task_manager.process_request(user_input, context)
        
        return AgentResponse(
            content=result["message"],
            confidence=result.get("confidence", 0.8),
            sources=["TaskManager"],
            actions_taken=result.get("actions", []),
            suggestions=result.get("suggestions", []),
            metadata={"module": "task_manager", "result": result}
        )
    
    async def _handle_communication_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """コミュニケーション関連の処理"""
        result = await self.communication.generate_draft(user_input, context)
        
        return AgentResponse(
            content=result["content"],
            confidence=result.get("confidence", 0.8),
            sources=["CommunicationModule"],
            actions_taken=["draft_generated"],
            suggestions=result.get("suggestions", []),
            metadata={"module": "communication", "draft_type": result.get("type")}
        )
    
    async def _handle_search_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """Web検索関連の処理"""
        result = await self.web_scraper.search_and_summarize(user_input, context)
        
        return AgentResponse(
            content=result["summary"],
            confidence=result.get("confidence", 0.7),
            sources=result.get("sources", []),
            actions_taken=["web_search", "content_summarization"],
            suggestions=result.get("suggestions", []),
            metadata={"module": "web_scraper", "query": user_input}
        )
    
    async def _handle_qa_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """質問応答の処理"""
        result = await self.qa_system.answer_question(user_input, context)
        
        return AgentResponse(
            content=result["answer"],
            confidence=result.get("confidence", 0.8),
            sources=result.get("sources", []),
            actions_taken=["knowledge_retrieval", "answer_generation"],
            suggestions=result.get("suggestions", []),
            metadata={"module": "qa_system", "question_type": result.get("type")}
        )
    
    async def _handle_analytics_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """分析関連の処理"""
        result = await self.analytics.generate_insights(user_input, context)
        
        return AgentResponse(
            content=result["insights"],
            confidence=result.get("confidence", 0.7),
            sources=["LifeAnalytics"],
            actions_taken=["data_analysis", "insight_generation"],
            suggestions=result.get("suggestions", []),
            metadata={"module": "life_analytics", "analysis_type": result.get("type")}
        )
    
    async def _handle_general_intent(self, user_input: str, context: Optional[Dict[str, Any]]) -> AgentResponse:
        """一般的な対話の処理"""
        # LLMを使用した一般的な応答生成
        prompt = f"""
        ユーザーからの入力: {user_input}
        
        あなたは個人専用のAIアシスタントです。
        親しみやすく、役立つ回答を生成してください。
        必要に応じて、具体的なアクションや提案も含めてください。
        """
        
        response = await self.llm.generate_response(prompt, context)
        
        return AgentResponse(
            content=response["content"],
            confidence=response.get("confidence", 0.6),
            sources=["LLM"],
            actions_taken=["general_response"],
            suggestions=response.get("suggestions", []),
            metadata={"module": "general", "llm_model": self.settings.llm.model}
        )
    
    async def _update_learning_data(self, 
                                  user_input: str, 
                                  response: AgentResponse, 
                                  intent: Dict[str, Any]) -> None:
        """学習データの更新"""
        learning_data = {
            "input": user_input,
            "response": response.content,
            "intent": intent,
            "confidence": response.confidence,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.current_session_id
        }
        
        await self.memory.store_learning_data(learning_data)
    
    async def get_status(self) -> Dict[str, Any]:
        """エージェントの現在状態を取得"""
        return {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "current_session": self.current_session_id,
            "memory_status": await self.memory.get_status(),
            "context_status": await self.context.get_status(),
            "modules_loaded": [
                "TaskManager", "CommunicationModule", "WebScraperModule",
                "QASystem", "LifeAnalyticsModule"
            ]
        }
    
    async def shutdown(self) -> None:
        """エージェントの終了処理"""
        try:
            if self.current_session_id:
                await self.memory.end_session(self.current_session_id)
            
            await self.memory.close()
            self.is_running = False
            
            logger.info("PersonalAIAgent shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise