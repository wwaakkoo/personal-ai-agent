#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Personal AI Agent - メインエントリーポイント
個人業務・生活支援AIエージェントシステム
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from config.settings import Settings
from core.agent import PersonalAIAgent
from interfaces.cli import CLIInterface

app = typer.Typer(help="Personal AI Agent - 私専用AIエージェント")
console = Console()

def setup_logging(debug: bool = False) -> None:
    """ログ設定の初期化"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console)]
    )

@app.command()
def start(
    debug: bool = typer.Option(False, "--debug", "-d", help="デバッグモードで実行"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="設定ファイルパス"),
    interface: str = typer.Option("cli", "--interface", "-i", help="インターフェース選択 (cli/web)")
):
    """AIエージェントを起動"""
    setup_logging(debug)
    
    console.print("[bold green]🤖 Personal AI Agent を起動中...[/bold green]")
    
    try:
        # 設定読み込み
        settings = Settings.load(config)
        
        # エージェント初期化
        agent = PersonalAIAgent(settings)
        
        if interface == "cli":
            # CLI インターフェース起動
            cli = CLIInterface(agent)
            asyncio.run(cli.run())
        elif interface == "web":
            # Web インターフェース起動
            from interfaces.web_ui import WebInterface
            web = WebInterface(agent)
            asyncio.run(web.run())
        else:
            console.print(f"[red]エラー: 不明なインターフェース '{interface}'[/red]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 AIエージェントを終了します...[/yellow]")
    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1)

@app.command()
def setup():
    """初期セットアップを実行"""
    console.print("[bold blue]🔧 Personal AI Agent セットアップ[/bold blue]")
    
    # データベース初期化
    console.print("📊 データベースを初期化中...")
    # TODO: データベース初期化処理
    
    # 設定ファイル作成
    console.print("⚙️ 設定ファイルを作成中...")
    settings = Settings.create_default()
    settings.save()
    
    console.print("[green]✅ セットアップが完了しました！[/green]")
    console.print("次のコマンドでエージェントを起動できます:")
    console.print("  python main.py start")

@app.command()
def version():
    """バージョン情報を表示"""
    console.print("Personal AI Agent v0.1.0")

if __name__ == "__main__":
    app()