# Agent Network with MCP Integration

Agent Networkは、特殊化された複数のエージェントを調整し、MCPプロトコルを活用した拡張機能を提供するフレームワークです。異なる専門知識を持つエージェント間の協力と、外部ツールの統合を可能にします。

## 主な機能

- **特殊化されたエージェント**: 各エージェントは特定のタスクに特化（知識クエリ、数学計算、天気情報、旅行計画など）
- **MCPプロトコル統合**: 外部ツールやサービスとの連携を強化
- **エージェント間の協調**: 複数エージェント間でのタスク委譲と会話
- **動的ツール発見**: MCPサーバーからツールを自動的に検出して利用
- **複数エージェント会話**: 順次または並列にエージェントを活用する会話フロー

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/agent_network.git
cd agent_network

# 依存関係をインストール
pip install -r requirements.txt
```

## 使用方法

### 標準エージェントの起動

```bash
python -m cli start
```

これにより、利用可能なすべての標準エージェント（知識、数学など）がスタートします。

### MCPサーバーとエージェントの起動（推奨ワークフロー）

MCP対応エージェントを使用するには、まずMCPサーバーを起動した後、個別のエージェントを起動する必要があります：

```bash
# ステップ1: まずMCPサーバーを起動
python -m cli mcp --servers-only

# ステップ2: 各エージェントを別々のターミナルで起動
# ターミナル1: 天気エージェントを固定ポートで起動
python -m cli start-agent --agent mcp_weather --port 53537

# ターミナル2: 旅行エージェントを起動し、天気エージェントに接続
python -m cli start-agent --agent mcp_travel --port 53543 --connect-to weather:53537
```

この方法により、エージェント間の接続を確実に行えます：
- MCPサーバーが先に起動されるため、エージェントが適切にツールを検出できます
- 固定ポートの指定により、エージェント間の接続が安定します
- `--connect-to`オプションで他のエージェントへの接続を明示的に設定できます

### 全てのコンポーネントを一度に起動（シンプルな方法）

すべてのMCPサーバーとエージェントを一度に起動する場合：

```bash
python -m cli mcp
```

オプションで特定のコンポーネントのみ起動することも可能です：

```bash
# MCPサーバーのみ起動
python -m cli mcp --servers-only

# MCPエージェントのみ起動
python -m cli mcp --agents-only

# 標準エージェントと同時に起動
python -m cli mcp --with-standard-agents

# 特定のポートを指定して起動
python -m cli mcp --agent-ports mcp_weather:53537 mcp_travel:53543
```

### 利用可能なエージェントの一覧表示

```bash
python -m cli list
```

### クエリの送信

特定のエージェントに直接クエリを送信：

```bash
# 知識エージェントにクエリを送信
python -m cli query --agent knowledge "What's the capital of Japan?"

# MCP対応気象エージェントにクエリを送信
python -m cli query --agent mcp_weather "Show me a weather map of London"

# MCP対応旅行エージェントにクエリを送信
python -m cli query --agent mcp_travel "Plan a 3-day trip to Tokyo considering weather"

# 特定のポートを指定してクエリを送信
python -m cli query --agent mcp_travel --agent-ports mcp_travel:53543 "Plan a weekend trip to Kyoto"
```

または、最適なエージェントに自動的にルーティング：

```bash
python -m cli query "What's 25 * 12?"
```

### エージェント間会話の実行

複数のエージェントを経由する会話を開始：

```bash
# 知識エージェントと数学エージェントを使った会話
python -m cli conversation --workflow "knowledge,math" "What's the population of Tokyo multiplied by 2?"

# 知識エージェントと気象エージェントを使った会話
python -m cli conversation --workflow "knowledge,mcp_weather" "Show me a weather map of the capital of France"

# 旅行エージェントと気象エージェントを使った会話
python -m cli conversation --workflow "mcp_travel,mcp_weather" "What activities can I do in Paris based on the current weather?"

# 特定のポートを指定して会話を実行
python -m cli conversation --workflow "mcp_travel,mcp_weather" --agent-ports mcp_travel:53543 mcp_weather:53537 "What activities can I do in Tokyo this weekend?"
```

## 利用可能なエージェント

### 標準エージェント

- **知識エージェント**: 一般的な知識クエリに回答（例：「日本の首都は？」）
- **数学エージェント**: 数学計算を処理（例：「25 * 12は？」）

### MCP対応エージェント

- **気象エージェント**: 天気情報と天気図を提供（例：「ロンドンの天気は？」）
- **旅行エージェント**: 旅行計画と活動提案を提供、気象情報に基づいて最適化（例：「天気を考慮して東京への3日間の旅行を計画して」）

## エージェント間連携の例

### 天気に基づく旅行計画

旅行エージェントは気象エージェントと連携して、最新の天気情報に基づいた旅行計画を提供します：

```bash
python -m cli query --agent mcp_travel "Plan a weekend trip to London based on weather"
```

このクエリを処理するとき、旅行エージェントは：

1. 気象エージェントに接続して現在のロンドンの天気を確認
2. 天気情報に基づいて適切な活動を計画（雨天ならば屋内活動、晴れならば屋外活動）
3. 完全な旅行計画を回答として返す

### 複数エージェントを経由する複合クエリ

複雑なクエリでは、複数のエージェントを連携させることができます：

```bash
python -m cli conversation --workflow "knowledge,mcp_travel,mcp_weather" "What activities should I do during rainy season in Tokyo?"
```

このクエリの処理フロー：

1. 知識エージェントが「東京の雨季はいつか」を判断
2. 旅行エージェントが雨季に適した東京の活動を提案
3. 気象エージェントが現在の東京の天気予報を提供して計画を補完

## カスタマイズと拡張

新しいエージェントやMCPサーバーを追加することで、システムを拡張できます。詳細は`docs/extending.md`を参照してください。

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