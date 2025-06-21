"""
Personal AI Agent - CLI インターフェース
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.spinner import Spinner

logger = logging.getLogger(__name__)

class CLIInterface:
    """
    コマンドライン インターフェース
    
    Richライブラリを使用した美しいCLI体験を提供
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.console = Console()
        self.running = True
        
        # セッション状態
        self.session_active = False
        self.command_history = []
        
        logger.info("CLI Interface initialized")
    
    async def run(self) -> None:
        """CLI メインループの実行"""
        
        self._display_welcome()
        
        try:
            # エージェント初期化
            await self.agent.initialize()
            self.session_active = True
            
            self.console.print("✅ AIエージェントが起動しました", style="green")
            self.console.print()
            
            # メインループ
            while self.running:
                await self._process_input_loop()
                
        except KeyboardInterrupt:
            self.console.print("\n👋 AIエージェントを終了します...", style="yellow")
        except Exception as e:
            self.console.print(f"❌ エラーが発生しました: {e}", style="red")
            logger.error(f"CLI error: {e}")
        finally:
            await self._cleanup()
    
    def _display_welcome(self) -> None:
        """ウェルカムメッセージの表示"""
        
        welcome_text = Text()
        welcome_text.append("🤖 Personal AI Agent", style="bold blue")
        welcome_text.append("\n私専用のAIアシスタントです", style="dim")
        
        welcome_panel = Panel(
            welcome_text,
            title="Welcome",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        self.console.print()
        
        # 使用方法の表示
        usage_table = Table(show_header=False, box=None, padding=(0, 2))
        usage_table.add_row("💬", "自然言語で話しかけてください")
        usage_table.add_row("📝", "/task - タスク管理")
        usage_table.add_row("✉️", "/email - メール草案作成")
        usage_table.add_row("📊", "/status - システム状況")
        usage_table.add_row("❓", "/help - ヘルプ表示")
        usage_table.add_row("🚪", "/quit - 終了")
        
        usage_panel = Panel(
            usage_table,
            title="使用方法",
            border_style="green",
            padding=(1, 0)
        )
        
        self.console.print(usage_panel)
        self.console.print()
    
    async def _process_input_loop(self) -> None:
        """入力処理ループ"""
        
        try:
            # プロンプト表示
            user_input = Prompt.ask(
                "[bold cyan]You[/bold cyan]",
                console=self.console
            ).strip()
            
            if not user_input:
                return
            
            # コマンド履歴に追加
            self.command_history.append(user_input)
            
            # システムコマンドのチェック
            if user_input.startswith('/'):
                await self._handle_system_command(user_input)
            else:
                # AIエージェントに処理を委譲
                await self._handle_agent_interaction(user_input)
                
        except EOFError:
            self.running = False
        except Exception as e:
            self.console.print(f"❌ 入力処理エラー: {e}", style="red")
            logger.error(f"Input processing error: {e}")
    
    async def _handle_system_command(self, command: str) -> None:
        """システムコマンドの処理"""
        
        command = command.lower()
        
        if command == "/quit" or command == "/exit":
            self.running = False
            
        elif command == "/help":
            self._display_help()
            
        elif command == "/status":
            await self._display_status()
            
        elif command.startswith("/task"):
            await self._handle_task_command(command)
            
        elif command.startswith("/email"):
            await self._handle_email_command(command)
            
        elif command == "/clear":
            self.console.clear()
            
        elif command == "/history":
            self._display_history()
            
        else:
            self.console.print(f"❓ 不明なコマンド: {command}", style="yellow")
            self.console.print("ヘルプは /help で確認できます")
    
    async def _handle_agent_interaction(self, user_input: str) -> None:
        """AIエージェントとの対話処理"""
        
        # 応答生成中の表示
        with self.console.status("[bold green]考え中...", spinner="dots"):
            try:
                response = await self.agent.process_input(user_input)
                
                # レスポンスの表示
                self._display_agent_response(response)
                
            except Exception as e:
                self.console.print(f"❌ エラーが発生しました: {e}", style="red")
                logger.error(f"Agent interaction error: {e}")
    
    def _display_agent_response(self, response) -> None:
        """エージェント応答の表示"""
        
        # メイン応答
        response_text = Text()
        response_text.append("🤖 Assistant: ", style="bold green")
        response_text.append(response.content)
        
        self.console.print()
        self.console.print(response_text)
        
        # 信頼度表示
        if hasattr(response, 'confidence') and response.confidence:
            confidence_text = f"信頼度: {response.confidence:.1%}"
            self.console.print(confidence_text, style="dim")
        
        # 実行されたアクション
        if hasattr(response, 'actions_taken') and response.actions_taken:
            actions_text = "実行アクション: " + ", ".join(response.actions_taken)
            self.console.print(actions_text, style="blue")
        
        # 提案
        if hasattr(response, 'suggestions') and response.suggestions:
            self.console.print()
            suggestions_table = Table(show_header=False, box=None, padding=(0, 1))
            for i, suggestion in enumerate(response.suggestions[:3], 1):
                suggestions_table.add_row(f"{i}.", suggestion)
            
            suggestions_panel = Panel(
                suggestions_table,
                title="💡 提案",
                border_style="yellow",
                padding=(0, 1)
            )
            self.console.print(suggestions_panel)
        
        self.console.print()
    
    async def _handle_task_command(self, command: str) -> None:
        """タスクコマンドの処理"""
        
        if command == "/task":
            # タスク一覧表示
            await self._display_tasks()
        elif command == "/task create":
            await self._create_task_interactive()
        else:
            self.console.print("使用方法: /task または /task create", style="yellow")
    
    async def _handle_email_command(self, command: str) -> None:
        """メールコマンドの処理"""
        
        if command == "/email":
            await self._create_email_interactive()
        else:
            self.console.print("使用方法: /email", style="yellow")
    
    async def _display_tasks(self) -> None:
        """タスク一覧の表示"""
        
        try:
            # タスク管理システムからタスクを取得
            response = await self.agent.task_manager.process_request("タスク一覧を表示", {})
            
            self.console.print()
            self.console.print("📝 タスク一覧", style="bold")
            self.console.print(response["message"])
            
        except Exception as e:
            self.console.print(f"❌ タスク取得エラー: {e}", style="red")
    
    async def _create_task_interactive(self) -> None:
        """対話的タスク作成"""
        
        self.console.print()
        self.console.print("📝 新しいタスクを作成します", style="bold green")
        
        try:
            title = Prompt.ask("タスクのタイトル", console=self.console)
            description = Prompt.ask("説明（オプション）", default="", console=self.console)
            priority = Prompt.ask(
                "優先度", 
                choices=["low", "medium", "high", "urgent"], 
                default="medium",
                console=self.console
            )
            
            # タスク作成リクエスト
            task_input = f"タスクを作成: {title}"
            if description:
                task_input += f" - {description}"
            task_input += f" 優先度: {priority}"
            
            response = await self.agent.task_manager.process_request(task_input, {})
            
            self.console.print()
            self.console.print("✅ " + response["message"], style="green")
            
        except Exception as e:
            self.console.print(f"❌ タスク作成エラー: {e}", style="red")
    
    async def _create_email_interactive(self) -> None:
        """対話的メール作成"""
        
        self.console.print()
        self.console.print("✉️ メール草案を作成します", style="bold green")
        
        try:
            email_type = Prompt.ask(
                "メールの種類",
                choices=["依頼", "お礼", "報告", "その他"],
                default="その他",
                console=self.console
            )
            
            content = Prompt.ask("メールの内容", console=self.console)
            tone = Prompt.ask(
                "文体",
                choices=["formal", "professional", "casual"],
                default="professional",
                console=self.console
            )
            
            # メール草案生成リクエスト
            email_input = f"{email_type}のメールを{tone}な文体で作成: {content}"
            
            response = await self.agent.communication.generate_draft(email_input, {})
            
            self.console.print()
            email_panel = Panel(
                response["content"],
                title="📧 メール草案",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(email_panel)
            
        except Exception as e:
            self.console.print(f"❌ メール生成エラー: {e}", style="red")
    
    async def _display_status(self) -> None:
        """システム状況の表示"""
        
        try:
            status = await self.agent.get_status()
            
            # ステータステーブル作成
            status_table = Table(title="🔧 システム状況")
            status_table.add_column("項目", style="cyan", no_wrap=True)
            status_table.add_column("状態", style="green")
            
            status_table.add_row("エージェントID", status["agent_id"])
            status_table.add_row("実行状態", "✅ 実行中" if status["is_running"] else "❌ 停止中")
            status_table.add_row("現在セッション", status["current_session"] or "なし")
            
            # メモリ状況
            if "memory_status" in status:
                memory = status["memory_status"]
                status_table.add_row("記憶項目数", str(memory.get("total_memories", 0)))
                status_table.add_row("短期記憶", str(memory.get("short_term_memories", 0)))
            
            self.console.print()
            self.console.print(status_table)
            
        except Exception as e:
            self.console.print(f"❌ ステータス取得エラー: {e}", style="red")
    
    def _display_help(self) -> None:
        """ヘルプ情報の表示"""
        
        help_table = Table(title="❓ ヘルプ")
        help_table.add_column("コマンド", style="cyan", no_wrap=True)
        help_table.add_column("説明", style="white")
        
        help_table.add_row("/help", "このヘルプを表示")
        help_table.add_row("/status", "システム状況を表示")
        help_table.add_row("/task", "タスク一覧を表示")
        help_table.add_row("/task create", "新しいタスクを作成")
        help_table.add_row("/email", "メール草案を作成")
        help_table.add_row("/history", "コマンド履歴を表示")
        help_table.add_row("/clear", "画面をクリア")
        help_table.add_row("/quit", "エージェントを終了")
        
        self.console.print()
        self.console.print(help_table)
        
        self.console.print()
        self.console.print("💬 自然言語での対話も可能です", style="dim")
        self.console.print("例: 「今日のタスクを教えて」「メールの草案を作って」", style="dim")
    
    def _display_history(self) -> None:
        """コマンド履歴の表示"""
        
        if not self.command_history:
            self.console.print("📜 コマンド履歴はありません", style="dim")
            return
        
        history_table = Table(title="📜 コマンド履歴")
        history_table.add_column("#", style="dim", width=4)
        history_table.add_column("コマンド", style="white")
        
        # 最新10件を表示
        recent_commands = self.command_history[-10:]
        for i, command in enumerate(recent_commands, 1):
            history_table.add_row(str(i), command)
        
        self.console.print()
        self.console.print(history_table)
    
    async def _cleanup(self) -> None:
        """クリーンアップ処理"""
        
        try:
            if self.session_active:
                await self.agent.shutdown()
            
            self.console.print("✅ 正常に終了しました", style="green")
            
        except Exception as e:
            self.console.print(f"❌ 終了処理エラー: {e}", style="red")
            logger.error(f"Cleanup error: {e}")