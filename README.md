# Agent Network with MCP Integration

Agent Networkは、特殊化された複数のエージェントを調整し、MCPプロトコルを活用した拡張機能を提供するフレームワークです。異なる専門知識を持つエージェント間の協力と、外部ツールの統合を可能にします。

## 主な機能

- **特殊化されたエージェント**: 各エージェントは特定のタスクに特化（天気情報、旅行計画など）
- **MCPプロトコル統合**: 外部ツールやサービスとの連携を強化
- **エージェント間の協調**: 複数エージェント間でのタスク委譲と連携
- **動的ツール発見**: MCPサーバーからツールを自動的に検出して利用

## インストール

```bash
# リポジトリをクローン
git clone git@github.com:eito2002/python-a2a-mcp-agents.git
cd python-a2a-mcp-agents

# 仮想環境を起動
uv venv
source .venv/bin/activate
# 依存関係をインストール
uv pip install -e .
# または開発用依存関係も含めてインストール
uv pip install -e ".[dev]"
```

## プロジェクト構造

```
/
├── src/                       # ソースコード（パッケージ）
│   ├── agents/                # エージェント実装
│   │   ├── __init__.py        # エージェントモジュール初期化
│   │   ├── mcp/               # MCP対応エージェント実装
│   │   │   ├── __init__.py    # MCPエージェントモジュール初期化
│   │   │   ├── mcp_agent.py   # MCPエージェント基底クラス
│   │   │   ├── mcp_weather_agent.py # MCP対応天気エージェント
│   │   │   └── mcp_travel_agent.py # MCP対応旅行エージェント
│   ├── mcp_servers/           # MCPサーバー実装
│   │   ├── weather_mcp_server.py  # 天気情報MCPサーバー
│   │   ├── maps_mcp_server.py     # 地図生成MCPサーバー
│   │   └── travel_mcp_server.py   # 旅行情報MCPサーバー
│   ├── server/                # サーバー管理
│   │   ├── __init__.py        # サーバーモジュール初期化
│   │   └── agent_server.py    # エージェントサーバー管理クラス
│   ├── routing/               # クエリルーティング
│   │   ├── __init__.py        # ルーティングモジュール初期化
│   │   ├── keyword_router.py  # キーワードベースルーター
│   │   └── ai_router.py       # AIベースルーター
│   ├── utils/                 # ユーティリティ関数
│   │   ├── __init__.py        # ユーティリティモジュール初期化
│   │   └── network_utils.py   # ネットワークユーティリティ
│   ├── __init__.py            # パッケージ初期化
│   ├── __main__.py            # メインエントリーポイント
│   ├── cli.py                 # コマンドラインインターフェース
│   ├── client.py              # ネットワーククライアント
│   ├── config.py              # 設定とロギング
│   └── network.py             # エージェントネットワーク管理
├── pyproject.toml             # プロジェクト設定
└── README.md                  # プロジェクト説明
```

## 使用方法

### MCPサーバーとエージェントの起動（推奨ワークフロー）

MCP対応エージェントを使用するには、まずMCPサーバーを起動した後、個別のエージェントを起動する必要があります：

```bash
# ステップ1: まずMCPサーバーを起動
python -m src.cli mcp

# ステップ2: 各エージェントを別々のターミナルで起動
# ターミナル1: 天気エージェントを固定ポートで起動
python -m src.cli start-agent --agent mcp_weather --port 53537

# ターミナル2: 旅行エージェントを起動し、天気エージェントに接続
python -m src.cli start-agent --agent mcp_travel --port 53543 --connect-to weather:53537
```

この方法により、エージェント間の接続を確実に行えます：
- MCPサーバーが先に起動されるため、エージェントが適切にツールを検出できます
- 固定ポートの指定により、エージェント間の接続が安定します
- `--connect-to`オプションで他のエージェントへの接続を明示的に設定できます

### クエリの送信

特定のエージェントに直接クエリを送信：

```bash
# MCP対応気象エージェントにクエリを送信
python -m src.cli query "Show me a weather map of London" --agent mcp_weather --agent-ports mcp_weather:53537

# MCP対応旅行エージェントにクエリを送信
python -m src.cli query "Plan a 3-day trip to Tokyo considering weather" --agent mcp_travel --agent-ports mcp_travel:53543
```

または、最適なエージェントに自動的にルーティング：

```bash
python -m src.cli query "What's the weather like in Tokyo?" --agent-ports mcp_weather:53537 mcp_travel:53543
```

## 利用可能なエージェント

### MCP対応エージェント

- **気象エージェント**: 天気情報と天気図を提供（例：「ロンドンの天気は？」）
- **旅行エージェント**: 旅行計画と活動提案を提供、気象情報に基づいて最適化（例：「天気を考慮して東京への3日間の旅行を計画して」）

## エージェント機能詳細

### MCPWeatherAgent (気象エージェント)

気象エージェントは、MCPプロトコルを活用して以下の機能を提供します：

#### 基本機能
- **現在の天気情報取得**
  - 説明: 指定した都市の現在の天気状況を提供
  - 対応項目: 気象状態、気温、湿度、風速
  - 使用例: `What's the weather in Tokyo?`, `Is it raining in London?`

- **天気予報取得**
  - 説明: 最大7日間の天気予報を提供
  - 対応項目: 日付ごとの天気状態、最高/最低気温、降水確率
  - 使用例: `What's the forecast for Paris?`, `Will it rain in New York tomorrow?`

- **天気マップ生成**
  - 説明: 指定した地域の天気マップを視覚的に表示
  - 対応項目: 温度マップ、降水マップ
  - 使用例: `Show me a weather map of Europe`, `Generate a precipitation map for Japan`

- **気象警報取得**
  - 説明: 指定地域の気象警報・注意報を表示
  - 対応項目: 警報タイプ、重要度、説明、発令時間、有効期限
  - 使用例: `Are there any weather alerts for Sydney?`

#### 堅牢性機能
- 複数のレスポンス形式に対応するJSONパース処理
- 必須フィールドの欠落時の自動補完機能
- 詳細なエラーログとスタックトレース情報

### MCPTravelAgent (旅行エージェント)

旅行エージェントは、気象エージェントと連携して以下の機能を提供します：

#### 基本機能
- **旅行計画作成**
  - 説明: 天気情報を考慮した旅程を作成
  - 対応項目: 日程ごとの活動提案、天候に応じた代替プラン、交通手段のヒント
  - 使用例: `Plan a 3-day trip to London considering weather`, `Create a weekend itinerary for Tokyo`

- **アクティビティ提案**
  - 説明: 天候に基づいた最適な活動を提案
  - 対応項目: 屋内/屋外アクティビティ、天候別おすすめ活動
  - 使用例: `What should I do in Paris tomorrow if it rains?`, `Outdoor activities in Sydney based on weather`

- **旅行アドバイザリー**
  - 説明: 安全情報・健康情報・入国要件などを提供
  - 対応項目: 安全レベル、健康アドバイス、入国条件、現地法律情報
  - 使用例: `Any travel alerts for New York this weekend?`, `Is it safe to travel to London next week?`

- **目的地情報提供**
  - 説明: 観光スポット、アクティビティ、食事、交通手段などの情報を提供
  - 対応項目: 観光名所、屋内/屋外活動、料理、交通、言語、通貨、タイムゾーン
  - 使用例: `Tell me about Tokyo`, `What are the top attractions in Paris?`

#### 堅牢性機能
- 気象エージェントとの連携による天気情報の取得と活用
- MCPサーバーからの様々なレスポンス形式への対応
- 必須データの欠落時の補完処理
- 詳細なログ記録とエラーハンドリング

## エージェント間連携の例

### 天気に基づく旅行計画

旅行エージェントは気象エージェントと連携して、最新の天気情報に基づいた旅行計画を提供します：

```bash
python -m src.cli query "Plan a weekend trip to London based on weather" --agent mcp_travel --agent-ports mcp_travel:53543 mcp_weather:53537
```

このクエリを処理するとき、旅行エージェントは：

1. 気象エージェントに接続して現在のロンドンの天気を確認
2. 天気情報に基づいて適切な活動を計画（雨天ならば屋内活動、晴れならば屋外活動）
3. 完全な旅行計画を回答として返す

## アーキテクチャ

Agent Networkは、モジュール化されたアーキテクチャで設計されています：

- **MCP対応エージェント**: 外部ツールと連携する拡張機能を持つエージェント
- **MCPサーバー**: 特定の機能やツールを提供する独立したサービス
- **ルーター**: クエリを最適なエージェントに振り分ける
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

### 新しいMCP対応エージェントの追加

1. `BaseMCPAgent`を継承した新しいエージェントクラスを作成
2. `handle_message_async`と`handle_task_async`メソッドを実装
3. 必要なMCPサーバーとの連携を設定
4. `cli.py`の設定に追加する

### 新しいMCPサーバーの追加

1. `FastMCP`を使用して新しいMCPサーバーを作成
2. ツールとリソースを関数デコレータで定義
3. `cli.py`の設定に追加する

## 依存関係

- python-a2a: エージェント間通信の基盤
- asyncio: 非同期処理のサポート
- fastapi: FastAPIベースのエージェントのためのWebフレームワーク
- uvicorn: ASGI サーバー
- multiprocessing: MCPサーバーの並列実行

## ライセンス

MIT License

## 寄稿

バグ修正や機能追加のプルリクエストを歓迎します。大きな変更を行う前に、まず問題を開いて議論してください。

## MCPサーバー機能詳細

MCPサーバーは、MCP対応エージェントにツールとリソースを提供する独立したサービスです。

### weather_mcp_server (天気MCPサーバー)

天気MCPサーバーは以下のツールとリソースを提供します：

#### ツール
- **get_current_weather**
  - 説明: 指定した場所の現在の天気情報を取得
  - パラメータ: location (場所名)
  - 戻り値: 気象状態、気温、湿度、風速などのJSON

- **get_weather_forecast**
  - 説明: 指定した場所の天気予報を取得
  - パラメータ: location (場所名), days (予報日数, デフォルト3)
  - 戻り値: 日付ごとの予報データのJSON

- **get_weather_alert**
  - 説明: 指定した場所の気象警報を取得
  - パラメータ: location (場所名)
  - 戻り値: 警報情報を含むJSON

#### リソース
- **/weather/current/{location}**: 現在の天気情報リソース
- **/weather/forecast/{location}/{days}**: 天気予報リソース

### maps_mcp_server (地図MCPサーバー)

地図MCPサーバーは以下のツールとリソースを提供します：

#### ツール
- **generate_weather_map**
  - 説明: 指定した場所の天気マップを生成
  - パラメータ: location (場所名), type (マップタイプ, デフォルト"temperature")
  - 戻り値: マップデータまたはビジュアル表現

- **generate_terrain_map**
  - 説明: 指定した場所の地形マップを生成
  - パラメータ: location (場所名)
  - 戻り値: 地形マップデータ

#### リソース
- **/maps/weather/{location}/{type}**: 天気マップリソース
- **/maps/terrain/{location}**: 地形マップリソース

### travel_mcp_server (旅行MCPサーバー)

旅行MCPサーバーは以下のツールとリソースを提供します：

#### ツール
- **get_destination_info**
  - 説明: 指定した場所の目的地情報を取得
  - パラメータ: location (場所名)
  - 戻り値: 観光スポット、活動、食事、交通などの情報

- **suggest_activities**
  - 説明: 指定した場所と天気に基づいた活動を提案
  - パラメータ: location (場所名), weather_condition (天気状態)
  - 戻り値: おすすめアクティビティのリスト

- **get_travel_advisory**
  - 説明: 指定した場所の旅行アドバイザリーを取得
  - パラメータ: location (場所名)
  - 戻り値: 安全情報、健康情報、入国要件、現地法情報

- **create_trip_itinerary**
  - 説明: 指定した場所と日数に基づいて旅程を作成
  - パラメータ: location (場所名), days (日数), weather_condition (オプション)
  - 戻り値: 詳細な旅行計画

#### リソース
- **/travel/destination/{location}**: 目的地情報リソース
- **/travel/advisory/{location}**: 旅行アドバイザリーリソース
- **/travel/itinerary/{location}/{days}**: 旅程リソース