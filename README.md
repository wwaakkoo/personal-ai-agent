# 🤖 Personal AI Agent

私専用のAIエージェント - 仕事・私生活を包括的にサポートする学習型・適応型AIシステム

## ✨ 主要機能

- **📝 タスク・スケジュール管理**: 自然言語でのタスク登録・整理・優先順位付け
- **✉️ メール・チャット草案作成**: コンテキストに応じた下書き生成
- **🌐 Web情報収集・要約**: 指定トピックの自動収集と整理
- **💬 質問応答システム**: 個人データに基づいた精度の高い回答
- **📊 ライフログ分析**: 行動パターンの分析と改善提案

## 🚀 クイックスタート

### 1. 環境準備

```bash
# リポジトリをクローン
git clone <repository-url>
cd personal-ai-agent

# Python 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

```bash
# 環境変数ファイルをコピー
cp .env.example .env

# .env ファイルを編集してAPIキーを設定
# OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 初期セットアップ

```bash
# データベースと設定を初期化
python main.py setup
```

### 4. エージェント起動

```bash
# CLI インターフェースで起動
python main.py start

# Web インターフェースで起動
python main.py start --interface web
```

## 🏗️ プロジェクト構造

```
personal-ai-agent/
├── core/                    # コアエンジン
│   ├── agent.py            # メインエージェントクラス
│   ├── memory.py           # 記憶・学習システム
│   └── context.py          # コンテキスト管理
├── modules/                 # 機能モジュール
│   ├── task_manager.py     # タスク管理
│   ├── communication.py    # コミュニケーション支援
│   ├── web_scraper.py      # Web情報収集
│   ├── qa_system.py        # 質問応答システム
│   └── life_analytics.py   # ライフログ分析
├── integrations/           # 外部API連携
│   ├── llm_provider.py     # LLM API統合
│   ├── calendar_sync.py    # カレンダー連携
│   └── email_client.py     # メール連携
├── security/               # セキュリティ層
│   ├── encryption.py       # データ暗号化
│   ├── auth.py            # 認証・認可
│   └── privacy.py         # プライバシー保護
├── storage/               # データ永続化
│   ├── database.py        # データベース管理
│   ├── cache.py          # キャッシュシステム
│   └── backup.py         # バックアップ管理
├── interfaces/           # ユーザーインターフェース
│   ├── cli.py           # コマンドライン
│   ├── web_ui.py        # Webインターフェース
│   └── api.py           # REST API
├── config/              # 設定管理
│   ├── settings.py      # アプリケーション設定
│   └── preferences.py   # ユーザー設定
├── tests/               # テストコード
└── docs/                # ドキュメント
```

## ⚙️ 設定

設定は以下の優先順位で適用されます：

1. 環境変数
2. `config/settings.yaml`
3. デフォルト値

主要な設定項目：

- **LLM設定**: APIキー、モデル、パラメータ
- **データベース**: 接続情報、プール設定
- **セキュリティ**: 暗号化キー、認証設定
- **インターフェース**: ホスト、ポート設定

## 🔒 セキュリティ

- **データ暗号化**: AES-256によるローカルデータ暗号化
- **プライバシー保護**: ローカルファースト、最小権限の原則
- **API管理**: 環境変数によるキー管理
- **アクセス制御**: JWT トークンベース認証

## 🧪 開発

### テスト実行

```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=. --cov-report=html
```

### コード品質チェック

```bash
# フォーマット
black .

# リント
flake8 .

# 型チェック
mypy .
```

### Web UI 開発

```bash
# Node.js依存関係インストール
npm install

# 開発サーバー起動
npm run dev

# ビルド
npm run build
```

## 📚 API リファレンス

Web API は `http://localhost:8000/docs` でSwagger UIを確認できます。

主要エンドポイント：

- `POST /api/chat` - AIエージェントとの対話
- `GET /api/tasks` - タスク一覧取得
- `POST /api/tasks` - タスク作成
- `GET /api/analytics` - 分析データ取得

## 🤝 コントリビューション

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 📞 サポート

- バグ報告: GitHub Issues
- 機能要望: GitHub Discussions
- ドキュメント: `docs/` ディレクトリ

---

Made with ❤️ for personal productivity and AI assistance.