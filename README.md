# Agent Network

Agent Networkは、特殊化された複数のエージェントを調整し、インテリジェントなルーティングを提供するフレームワークです。異なる専門知識を持つエージェント間の協力を可能にします。

## 特徴

- **専門エージェント**: 天気、数学、一般知識など、特定の機能に特化したエージェント
- **インテリジェントなルーティング**: キーワードベースまたはAIベースのルーティングで、最適なエージェントに質問を自動的に振り分け
- **エージェント間通信**: エージェント同士が協力して複雑なタスクを解決する会話ワークフロー
- **拡張可能なアーキテクチャ**: 新しい種類のエージェントを簡単に追加できる設計
- **MCP統合**: Machine Conversation Protocol (MCP) を活用した外部ツールとの連携

## インストール

必要な依存関係をインストールします：

```bash
uv venv
source ./.venv/bin/activate
uv pip install python-a2a
```

## 使用方法

### 標準エージェントの起動

```bash
python -m cli start
```

これにより、利用可能なすべてのエージェント（天気、数学、知識）がスタートします。

### MCPエージェントとサーバーの起動

```bash
python -m cli mcp
```

これにより、MCPサーバーとMCP対応エージェントが起動します。オプションで特定のコンポーネントのみ起動することも可能です：

```bash
# MCPサーバーのみ起動
python -m cli mcp --servers-only

# MCPエージェントのみ起動
python -m cli mcp --agents-only
```

### 利用可能なエージェントの一覧表示

```bash
python -m cli list
```

### クエリの送信

特定のエージェントに直接クエリを送信：

```bash
python -m cli query --agent weather "What's the weather in Tokyo?"
```

MCP対応エージェントにクエリを送信：

```bash
python -m cli query --agent mcp_weather "Show me a weather map of London"
```

または、最適なエージェントに自動的にルーティング：

```bash
python -m cli query "What's 25 * 12?"
```

### エージェント間会話の実行

複数のエージェントを経由する会話を開始：

```bash
python -m cli conversation --workflow "weather,knowledge" "What's the weather in the capital of Japan?"
```

MCP対応エージェントを含む会話：

```bash
python -m cli conversation --workflow "knowledge,mcp_weather" "Show me a weather map of the capital of France"
```

## アーキテクチャ

Agent Networkは、モジュール化されたアーキテクチャで設計されています：

- **エージェント**: 各エージェントは特定のドメインに特化
  - **標準エージェント**: 基本的なメッセージ処理とタスク処理機能
  - **MCP対応エージェント**: 外部ツールと連携する拡張機能
- **MCPサーバー**: 特定の機能やツールを提供する独立したサービス
- **ルーター**: クエリを最適なエージェントに振り分ける
- **会話オーケストレーター**: エージェント間の会話フローを管理
- **ネットワークコーディネーター**: エージェントの登録と通信を処理

## MCP統合の特徴

### MCPエージェント

MCPエージェントは、外部ツールやサービスと連携するための拡張機能を持つエージェントです：

- **ツール発見**: 接続されたMCPサーバーから利用可能なツールを自動的に発見
- **非同期処理**: 非同期メッセージ処理とタスク処理をサポート
- **関数呼び出し**: LLMからの関数呼び出しをMCPツールに変換
- **スキル拡張**: 発見したMCPツールをエージェントのスキルとして登録

### MCPサーバー

MCPサーバーは、特定の機能やツールを提供する独立したサービスです：

- **ツール定義**: 関数デコレータを使用した簡単なツール定義
- **リソース提供**: URIベースのリソースアクセス
- **非同期対応**: 非同期処理をネイティブにサポート
- **プロトコル準拠**: MCP (Machine Conversation Protocol) 標準に準拠

## 拡張

### 新しいエージェントの追加

標準エージェントを追加するには：

1. `BaseAgent`を継承した新しいエージェントクラスを作成
2. `handle_message`と`handle_task`メソッドを実装
3. エージェントのスキルと機能を定義
4. エージェントモジュールに登録する

MCP対応エージェントを追加するには：

1. `MCPEnabledAgent`を継承した新しいエージェントクラスを作成
2. `handle_message_async`と`handle_task_async`メソッドを実装
3. 必要なMCPサーバーとの連携を設定
4. `cli.py`の設定に追加する

### 新しいMCPサーバーの追加

1. `FastMCP`を使用して新しいMCPサーバーを作成
2. ツールとリソースを関数デコレータで定義
3. `cli.py`の設定に追加する

## APIドキュメント

詳細なAPIドキュメントについては、`/docs`ディレクトリを参照してください。

## ライセンス

MIT License

## 寄稿

バグ修正や機能追加のプルリクエストを歓迎します。大きな変更を行う前に、まず問題を開いて議論してください。