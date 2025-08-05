# PyDepGraph ユーザーガイド

PyDepGraphは、Pythonプロジェクトの依存関係を分析し、理解を深めるためのCLIツールです。このガイドでは、ツールのインストールから基本的な使い方、各コマンドの詳細までを説明します。

## 1. インストール

PyDepGraphは`uv`を使用して開発されています。以下の手順でインストールしてください。

```bash
# 1. リポジトリをクローン
git clone https://github.com/your-username/PyDepGraph.git
cd PyDepGraph

# 2. 依存関係をインストール
uv sync

# 3. ヘルプメッセージを確認
uv run pydepgraph --help
```

## 2. 設定

PyDepGraphは、プロジェクトのルートディレクトリにある`pydepgraph.toml`というファイルで設定を管理します。ファイルが存在しない場合は、デフォルト設定が使用されます。

### 設定可能な項目

*   **Extractor**: どの依存関係抽出ツールを有効にするか。
*   **Database**: 分析結果を保存するデータベースファイルのパス。
*   **Analysis**: テストファイルを含めるか、分析から除外するファイルパターンなど。

### デフォルト設定 (`pydepgraph.toml`)

```toml
[extractors]
# モジュールレベルの依存関係を抽出するTachを有効化
tach = true

# 関数・クラスレベルの依存関係を抽出するCode2Flowを有効化
[extractors.code2flow]
enabled = true
options = { fallback_to_ast = true } # Code2Flow失敗時にAST解析へフォールバック

[database]
# データベースファイルのパス
path = "pydepgraph.db"
enable_wal = true
buffer_pool_size = "128MB"

[analysis]
# テストファイルも分析対象に含める
include_tests = true
# 分析から除外するファイル・ディレクトリのパターン
exclude_patterns = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "*.pyc",
    "venv",
    ".venv"
]
# 分析対象ファイルの最大サイズ (MB)
max_file_size_mb = 10
# タイムアウト時間 (秒)
timeout_seconds = 300
```

## 3. コマンドリファレンス

PyDepGraphは、以下の4つの主要なサブコマンドを提供します。

*   `analyze`: プロジェクトを分析し、依存関係をデータベースに保存します。
*   `query`: データベースに保存された情報を検索します。
*   `analytics`: グラフ全体に対する高度な分析を実行します。
*   `report`: 包括的な分析レポートを生成します。

### 3.1. `analyze`

プロジェクトのソースコードを静的解析し、依存関係を抽出してデータベースに保存します。**他のコマンドを使用する前に、必ずこのコマンドを実行してください。**

**書式:**
```bash
uv run pydepgraph analyze [PROJECT_PATH] [OPTIONS]
```

**引数:**
*   `PROJECT_PATH`: 分析したいPythonプロジェクトのパス。省略した場合はカレントディレクトリ (`.`) になります。

**オプション:**
*   `--output <json|table>`: 出力形式（デフォルト: `table`）。
*   `--database <PATH>`: 設定ファイルを上書きして、データベースのパスを指定します。

**使用例:**
```bash
# カレントディレクトリを分析
uv run pydepgraph analyze

# 特定のプロジェクトを分析
uv run pydepgraph analyze /path/to/my_project
```

### 3.2. `query`

データベースから特定の情報を検索します。

**書式:**
```bash
uv run pydepgraph query <QUERY_TYPE> [OPTIONS]
```

**引数:**
*   `QUERY_TYPE`: 検索する情報の種類。
    *   `modules`: 全てのモジュール
    *   `functions`: 全ての関数
    *   `classes`: 全てのクラス
    *   `imports`: モジュール間のインポート関係
    *   `calls`: 関数間の呼び出し関係

**オプション:**
*   `--filter <TEXT>`: 結果を名前に基づいてフィルタリングします。
*   `--format <json|table>`: 出力形式（デフォルト: `table`）。

**使用例:**
```bash
# 全てのモジュールを一覧表示
uv run pydepgraph query modules

# "user"という単語を含む関数を検索
uv run pydepgraph query functions --filter user

# インポート関係をJSON形式で出力
uv run pydepgraph query imports --format json
```

### 3.3. `analytics`

依存関係グラフ全体に対するメトリクス計算や高度な分析を行います。

**書式:**
```bash
uv run pydepgraph analytics <ANALYSIS_TYPE> [OPTIONS]
```

**引数:**
*   `ANALYSIS_TYPE`: 実行する分析の種類。
    *   `stats`: グラフの統計情報（ノード数、エッジ数、密度など）を表示します。
    *   `cycles`: 循環依存を検出します。
    *   `importance`: モジュールの重要度をPageRankアルゴリズムで計算します。
    *   `depth`: 指定したモジュールからの依存関係の深さを分析します。

**オプション:**
*   `--node-type <module|function|class>`: 分析対象のノード種別（デフォルト: `module`）。
*   `--root <NODE_NAME>`: `depth`分析の起点となるノード名。
*   `--format <json|table>`: 出力形式（デフォルト: `table`）。

**使用例:**
```bash
# グラフ全体の統計情報を表示
uv run pydepgraph analytics stats

# モジュール間の循環依存を検出
uv run pydepgraph analytics cycles

# クラスの重要度を計算
uv run pydepgraph analytics importance --node-type class

# 'main'モジュールからの依存の深さを分析
uv run pydepgraph analytics depth --root main
```

### 3.4. `report`

プロジェクト全体の包括的な分析レポートを生成します。

**書式:**
```bash
uv run pydepgraph report [OPTIONS]
```

**オプション:**
*   `--output-file <PATH>`: レポートの出力先ファイルパス。省略した場合は標準出力に表示されます。
*   `--format <markdown|json|html>`: レポートの形式（デフォルト: `markdown`）。

**使用例:**
```bash
# Markdown形式でレポートをコンソールに表示
uv run pydepgraph report

# HTML形式でファイルに保存
uv run pydepgraph report --format html --output-file analysis_report.html
```
このコマンドは、統計情報、循環依存、重要なモジュールなど、複数の分析結果をまとめたレポートを生成します。
