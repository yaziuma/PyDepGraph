# PyDepGraph ユーザーガイド

PyDepGraphの詳細な使用方法とコマンドリファレンスです。

## 目次

- [クイックスタート](#クイックスタート)
- [コマンドリファレンス](#コマンドリファレンス)
- [設定](#設定)
- [実際の使用例](#実際の使用例)
- [トラブルシューティング](#トラブルシューティング)

## クイックスタート

### 1. プロジェクトの分析

```bash
# 現在のディレクトリを分析
uv run pydepgraph analyze

# 特定のプロジェクトを分析
uv run pydepgraph analyze /path/to/your/project

# JSON形式で結果を出力
uv run pydepgraph analyze --output json

# 分析結果例
# Analysis completed successfully!
# Modules found: 24
# Functions found: 238
# Classes found: 0
# Import relationships: 20
# Function calls: 407
```

### 2. 依存関係の検索

```bash
# 全モジュール一覧
uv run pydepgraph query modules

# 特定の名前を含む関数を検索
uv run pydepgraph query functions --filter "run"

# 全クラス一覧
uv run pydepgraph query classes

# import関係一覧
uv run pydepgraph query imports

# 関数呼び出し一覧（フィルタ付き）
uv run pydepgraph query calls --filter "repl"

# JSON形式で出力
uv run pydepgraph query modules --format json
```

### 3. グラフ分析

```bash
# グラフ統計情報
uv run pydepgraph analytics stats

# 出力例:
# Graph Statistics:
# ====================
# Nodes: 258
#   - Modules: 20
#   - Functions: 238
#   - Classes: 0
# Edges: 427
#   - Imports: 20
#   - Function Calls: 407
#   - Inheritance: 0
# Density: 0.0064
# Total Lines of Code: 4515
# Average Complexity: 3.99

# 循環依存検出
uv run pydepgraph analytics cycles

# 重要性スコア算出
uv run pydepgraph analytics importance

# 依存関係の深度分析
uv run pydepgraph analytics depth --root module_name
```

### 4. レポート生成

```bash
# Markdown形式レポート（デフォルト）
uv run pydepgraph report

# JSONレポート
uv run pydepgraph report --format json

# HTMLレポート
uv run pydepgraph report --format html

# ファイルに保存
uv run pydepgraph report --output-file dependency_report.md
```

## コマンドリファレンス

### analyze
プロジェクト全体の依存関係を分析し、データベースに保存

```bash
uv run pydepgraph analyze [PROJECT_PATH] [OPTIONS]
```

**オプション:**
- `--output {json,table}`: 出力形式（デフォルト: table）
- `--database PATH`: データベースファイルパス

**例:**
```bash
uv run pydepgraph analyze                    # 現在のディレクトリを分析
uv run pydepgraph analyze ./my_project       # 特定プロジェクトを分析
uv run pydepgraph analyze --output json      # JSON形式で出力
```

### query
依存関係データベースからの検索

```bash
uv run pydepgraph query {modules,functions,classes,imports,calls,role,context} [OPTIONS]
```

**サブコマンド:**
- `modules`: モジュール検索
- `functions`: 関数検索（メソッド含む）
- `classes`: クラス検索
- `imports`: インポート関係検索
- `calls`: 関数呼び出し関係検索
- `role`: ロール推定結果でのモジュール検索（`--value` 必須）
- `context`: LLM向けコンテキスト出力（依存=骨格、対象=フル実装）

**オプション:**
- `--filter TEXT`: フィルタ条件（部分一致）
- `--format {json,table}`: 出力形式（デフォルト: dict形式）

**例:**
```bash
uv run pydepgraph query functions --filter "run"     # "run"を含む関数を検索
uv run pydepgraph query modules --format json        # 全モジュールをJSON形式で取得
uv run pydepgraph query calls --filter "repl"        # "repl"関連の関数呼び出し
uv run pydepgraph query role --value service         # service ロールのモジュールを検索
uv run pydepgraph query context --target src/pydepgraph/core.py --depth 1
```

### inspect（LLM向けの実用的な使い方）

```bash
# 1) まず骨格のみ
uv run pydepgraph inspect src/pydepgraph/core.py --skeleton

# 2) 周辺依存を最小情報で確認（依存は骨格、対象はフル）
uv run pydepgraph query context --target src/pydepgraph/core.py --depth 1

# 3) 必要な関数だけ詳細実装を取得
uv run pydepgraph inspect src/pydepgraph/core.py --target-function analyze
```

この順（**skeleton → context → target-function**）で使うと、LLMに渡すトークンを抑えつつ、必要箇所だけ深掘りできます。

### analytics
グラフ分析機能

```bash
uv run pydepgraph analytics {stats,cycles,importance} [OPTIONS]
```

**サブコマンド:**
- `stats`: グラフ統計情報（ノード数、エッジ数、密度）
- `cycles`: 循環依存検出
- `importance`: 重要性スコア算出（PageRankベース）

**オプション:**
- `--format {json,table}`: 出力形式（デフォルト: table）

**例:**
```bash
uv run pydepgraph analytics stats           # グラフ統計表示
uv run pydepgraph analytics cycles          # 循環依存検出
uv run pydepgraph analytics importance      # 重要モジュールランキング
```

### report
包括的なレポート生成

```bash
uv run pydepgraph report [OPTIONS]
```

**オプション:**
- `--output-file FILE`: 出力ファイルパス
- `--format {json,html,markdown}`: レポート形式（デフォルト: markdown）

**例:**
```bash
uv run pydepgraph report                               # 標準出力にMarkdownレポート
uv run pydepgraph report --output-file analysis.md    # ファイルに保存
uv run pydepgraph report --format json                # JSON形式レポート
```

## 設定

プロジェクトルートに `pydepgraph.toml` を配置することで設定をカスタマイズできます：

```toml
[extractors]
# Tach抽出器の設定
tach = { enabled = true }

# Code2Flow抽出器の設定（AST解析フォールバック付き）
code2flow = { enabled = true, options = { fallback_to_ast = true } }

[database]
# データベースファイルのパス
path = "pydepgraph.db"

# WALモードの有効化
enable_wal = true

# バッファプールサイズ
buffer_pool_size = "128MB"

[analysis]
# テストファイルを含めるか
include_tests = true

# 除外パターン
exclude_patterns = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "*.pyc",
    "venv",
    ".venv"
]

# 最大ファイルサイズ（MB）
max_file_size_mb = 10

# タイムアウト（秒）
timeout_seconds = 300
```

## 実際の使用例

### 基本的なワークフロー

```bash
# 1. プロジェクトを分析
uv run pydepgraph analyze tests/sample_code/pyprolog

# 出力例:
# Analysis completed successfully!
# Modules found: 24
# Functions found: 238
# Classes found: 0
# Import relationships: 20
# Function calls: 407

# 2. グラフ統計を確認
uv run pydepgraph analytics stats

# 出力例:
# Graph Statistics:
# ====================
# Nodes: 258
# Edges: 427
# Density: 0.0064

# 3. 循環依存を確認
uv run pydepgraph analytics cycles
# 出力: No results found (循環依存なし)

# 4. 重要なモジュールを特定
uv run pydepgraph analytics importance

# 5. 包括的レポートを生成
uv run pydepgraph report --output-file report.md
```

### 検索とフィルタリング

```bash
# 特定の関数を検索
uv run pydepgraph query functions --filter "run"

# 出力例:
# {'name': 'run()', 'qualified_name': 'interactive_repl::InteractiveProlog.run', ...}
# {'name': 'run_repl()', 'qualified_name': 'repl::run_repl', ...}

# 特定モジュールに関連する関数呼び出しを検索
uv run pydepgraph query calls --filter "repl"

# モジュール一覧をJSON形式で取得
uv run pydepgraph query modules --format json
```

### 高度な分析

```bash
# 重要性スコアによるモジュールランキング
uv run pydepgraph analytics importance

# 出力例:
# - io_streams: 0.1038
# - repl: 0.0775
# - io_manager: 0.0754
# - logging_config: 0.0754

# グラフ密度分析
uv run pydepgraph analytics stats

# 循環依存の検出
uv run pydepgraph analytics cycles
```

### レポート形式の活用

```bash
# Markdownレポート（推奨）
uv run pydepgraph report

# 出力例:
# # PyDepGraph Analysis Report
# ## Summary
# - Total Nodes: 258
# - Total Edges: 427
# - Graph Density: 0.0064
# ## Circular Dependencies
# No circular dependencies found.
# ## Top 10 Important Modules
# - io_streams: 0.1038
# - repl: 0.0775

# JSONレポート（プログラム処理用）
uv run pydepgraph report --format json

# ファイル保存
uv run pydepgraph report --output-file project_analysis.md
```

## トラブルシューティング

### よくある問題

**Q: "Database not found" エラーが表示される**
A: 最初にプロジェクトを分析してください：`uv run pydepgraph analyze`

**Q: 分析結果が表示されない**
A: データベースにデータが保存されているか確認：`uv run pydepgraph analytics stats`

**Q: Code2Flowが動作しない**
A: Code2Flowがインストールされていない場合、ASTフォールバックが動作します（通常は問題ありません）

**Q: 大きなプロジェクトで分析が遅い**
A: 設定ファイルで除外パターンを追加し、不要なファイルを除外してください

### デバッグ用ログ出力

PyDepGraphは適切なロギングシステムを実装しており、ライブラリとしてアプリケーション側でログレベルを制御できます。

詳細なログを確認したい場合は `-v` オプションを使用：

```bash
# 詳細ログ
uv run pydepgraph -v analyze

# より詳細なログ
uv run pydepgraph -vv analyze
```

**ライブラリとしての利用時**：アプリケーション側で `logging.basicConfig()` や `logging.config.dictConfig()` を使用してPyDepGraphのログレベルを制御できます。
