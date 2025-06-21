"""
Personal AI Agent - LLM API統合プロバイダー
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import openai
import anthropic

from config.settings import LLMConfig

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """LLMプロバイダーの種類"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

@dataclass
class LLMResponse:
    """LLM応答データ"""
    content: str
    model: str
    provider: str
    confidence: float
    usage: Dict[str, int]
    metadata: Dict[str, Any]

@dataclass
class ChatMessage:
    """チャットメッセージ"""
    role: str  # system, user, assistant
    content: str
    metadata: Optional[Dict[str, Any]] = None

class BaseLLMClient(ABC):
    """LLMクライアントの基底クラス"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """クライアントの初期化"""
        pass
    
    @abstractmethod
    async def generate_response(self, 
                              messages: List[ChatMessage],
                              **kwargs) -> LLMResponse:
        """レスポンス生成"""
        pass
    
    @abstractmethod
    async def generate_stream(self, 
                            messages: List[ChatMessage],
                            **kwargs) -> AsyncGenerator[str, None]:
        """ストリーミングレスポンス生成"""
        pass
    
    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキスト埋め込みの生成"""
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI GPT クライアント"""
    
    async def initialize(self) -> None:
        """OpenAI クライアントの初期化"""
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.AsyncOpenAI(api_key=self.config.api_key)
        logger.info("OpenAI client initialized")
    
    async def generate_response(self, 
                              messages: List[ChatMessage],
                              temperature: Optional[float] = None,
                              max_tokens: Optional[int] = None,
                              **kwargs) -> LLMResponse:
        """OpenAI GPT レスポンス生成"""
        
        if not self.client:
            await self.initialize()
        
        try:
            # ChatMessage を OpenAI 形式に変換
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                **kwargs
            )
            
            # 使用量情報の取得
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider="openai",
                confidence=0.8,  # OpenAI doesn't provide confidence scores
                usage=usage,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "response_id": response.id
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def generate_stream(self, 
                            messages: List[ChatMessage],
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            **kwargs) -> AsyncGenerator[str, None]:
        """OpenAI ストリーミングレスポンス"""
        
        if not self.client:
            await self.initialize()
        
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """OpenAI テキスト埋め込み"""
        
        if not self.client:
            await self.initialize()
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI embeddings error: {e}")
            raise

class AnthropicClient(BaseLLMClient):
    """Anthropic Claude クライアント"""
    
    async def initialize(self) -> None:
        """Anthropic クライアントの初期化"""
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
        logger.info("Anthropic client initialized")
    
    async def generate_response(self, 
                              messages: List[ChatMessage],
                              temperature: Optional[float] = None,
                              max_tokens: Optional[int] = None,
                              **kwargs) -> LLMResponse:
        """Anthropic Claude レスポンス生成"""
        
        if not self.client:
            await self.initialize()
        
        try:
            # システムメッセージと会話メッセージを分離
            system_messages = [msg for msg in messages if msg.role == "system"]
            conversation_messages = [msg for msg in messages if msg.role != "system"]
            
            system_prompt = " ".join([msg.content for msg in system_messages]) if system_messages else None
            
            # ChatMessage を Anthropic 形式に変換
            anthropic_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in conversation_messages
            ]
            
            kwargs_anthropic = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                **kwargs
            }
            
            if system_prompt:
                kwargs_anthropic["system"] = system_prompt
            
            if temperature is not None:
                kwargs_anthropic["temperature"] = temperature
            elif self.config.temperature != 0.7:  # デフォルト値でない場合のみ設定
                kwargs_anthropic["temperature"] = self.config.temperature
            
            response = await self.client.messages.create(**kwargs_anthropic)
            
            # 使用量情報の取得
            usage = {
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
                "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            }
            
            return LLMResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                provider="anthropic",
                confidence=0.8,  # Anthropic doesn't provide confidence scores
                usage=usage,
                metadata={
                    "stop_reason": response.stop_reason,
                    "response_id": response.id
                }
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def generate_stream(self, 
                            messages: List[ChatMessage],
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            **kwargs) -> AsyncGenerator[str, None]:
        """Anthropic ストリーミングレスポンス"""
        
        if not self.client:
            await self.initialize()
        
        try:
            system_messages = [msg for msg in messages if msg.role == "system"]
            conversation_messages = [msg for msg in messages if msg.role != "system"]
            
            system_prompt = " ".join([msg.content for msg in system_messages]) if system_messages else None
            
            anthropic_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in conversation_messages
            ]
            
            kwargs_anthropic = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens or self.config.max_tokens,
                "stream": True,
                **kwargs
            }
            
            if system_prompt:
                kwargs_anthropic["system"] = system_prompt
            
            if temperature is not None:
                kwargs_anthropic["temperature"] = temperature
            elif self.config.temperature != 0.7:
                kwargs_anthropic["temperature"] = self.config.temperature
            
            async with self.client.messages.stream(**kwargs_anthropic) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Anthropic では現在埋め込みAPIは提供されていない"""
        raise NotImplementedError("Anthropic does not provide embeddings API")

class LLMProviderManager:
    """
    LLMプロバイダー管理クラス
    
    複数のLLMプロバイダーを統合管理し、
    統一されたインターフェースを提供
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.clients: Dict[str, BaseLLMClient] = {}
        self.active_client: Optional[BaseLLMClient] = None
        
        # プロバイダーの初期化
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """利用可能なプロバイダーを初期化"""
        
        if self.config.provider == "openai":
            self.clients["openai"] = OpenAIClient(self.config)
            self.active_client = self.clients["openai"]
        elif self.config.provider == "anthropic":
            self.clients["anthropic"] = AnthropicClient(self.config)
            self.active_client = self.clients["anthropic"]
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")
    
    async def initialize(self) -> None:
        """アクティブなクライアントを初期化"""
        if self.active_client:
            await self.active_client.initialize()
    
    async def generate_response(self, 
                              prompt: str,
                              context: Optional[Dict[str, Any]] = None,
                              **kwargs) -> Dict[str, Any]:
        """統一されたレスポンス生成インターフェース"""
        
        if not self.active_client:
            raise RuntimeError("No active LLM client")
        
        # コンテキストを考慮したメッセージ構築
        messages = self._build_messages(prompt, context)
        
        try:
            response = await self.active_client.generate_response(messages, **kwargs)
            
            return {
                "content": response.content,
                "confidence": response.confidence,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage,
                "metadata": response.metadata
            }
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise
    
    async def generate_stream(self, 
                            prompt: str,
                            context: Optional[Dict[str, Any]] = None,
                            **kwargs) -> AsyncGenerator[str, None]:
        """統一されたストリーミング生成インターフェース"""
        
        if not self.active_client:
            raise RuntimeError("No active LLM client")
        
        messages = self._build_messages(prompt, context)
        
        try:
            async for chunk in self.active_client.generate_stream(messages, **kwargs):
                yield chunk
                
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキスト埋め込み生成"""
        
        if not self.active_client:
            raise RuntimeError("No active LLM client")
        
        try:
            return await self.active_client.get_embeddings(texts)
            
        except NotImplementedError:
            # フォールバック: OpenAI を使用
            if "openai" not in self.clients:
                openai_config = LLMConfig(
                    provider="openai",
                    api_key=self.config.api_key,
                    model="text-embedding-ada-002"
                )
                self.clients["openai"] = OpenAIClient(openai_config)
                await self.clients["openai"].initialize()
            
            return await self.clients["openai"].get_embeddings(texts)
        
        except Exception as e:
            logger.error(f"Embeddings generation error: {e}")
            raise
    
    def _build_messages(self, 
                       prompt: str, 
                       context: Optional[Dict[str, Any]] = None) -> List[ChatMessage]:
        """プロンプトとコンテキストからメッセージを構築"""
        
        messages = []
        
        # システムメッセージ
        system_prompt = self._build_system_prompt(context)
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        # コンテキスト履歴がある場合は追加
        if context and "history" in context:
            for item in context["history"][-5:]:  # 直近5件のみ
                if item["type"] == "user_input":
                    messages.append(ChatMessage(role="user", content=item["content"]))
                elif item["type"] == "agent_response":
                    messages.append(ChatMessage(role="assistant", content=item["content"]))
        
        # ユーザーの現在の入力
        messages.append(ChatMessage(role="user", content=prompt))
        
        return messages
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """システムプロンプトの構築"""
        
        base_prompt = """あなたは個人専用のAIアシスタントです。
ユーザーの仕事と私生活を包括的にサポートし、以下の原則に従って行動してください：

1. 親しみやすく、丁寧で役立つ回答を提供する
2. ユーザーのプライバシーと機密性を最大限尊重する
3. 具体的で実行可能なアドバイスを提供する
4. 必要に応じて追加の質問や確認を行う
5. ユーザーの文脈や状況を考慮した個別化された対応を行う"""
        
        if not context:
            return base_prompt
        
        # ユーザー状態の情報を追加
        context_info = []
        
        if context.get("user_state"):
            user_state = context["user_state"]
            if user_state.get("current_focus"):
                context_info.append(f"現在の関心事: {user_state['current_focus']}")
            if user_state.get("mood"):
                context_info.append(f"推定気分: {user_state['mood']}")
        
        if context.get("environment"):
            env = context["environment"]
            context_info.append(f"時間帯: {env.get('time_of_day', 'unknown')}")
            if env.get("is_weekend"):
                context_info.append("週末モード")
        
        if context_info:
            return f"{base_prompt}\n\n現在の状況:\n" + "\n".join(f"- {info}" for info in context_info)
        
        return base_prompt
    
    async def switch_provider(self, provider: str) -> None:
        """LLMプロバイダーを切り替え"""
        
        if provider not in self.clients:
            raise ValueError(f"Provider {provider} is not initialized")
        
        self.active_client = self.clients[provider]
        self.config.provider = provider
        
        logger.info(f"Switched to LLM provider: {provider}")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        
        return {
            "active_provider": self.config.provider,
            "active_model": self.config.model,
            "available_providers": list(self.clients.keys()),
            "initialized": self.active_client is not None
        }