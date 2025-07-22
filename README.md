# PyDepGraph

**PyDepGraph** は Python プロジェクトの依存関係を自動抽出・グラフ化し、LLM による効率的な依存関係検索を実現するライブラリです。

## 概要

PyDepGraphは以下の機能を提供します：

- **多層依存関係抽出**: Tach（モジュール間）とAST解析（関数・クラス間）を組み合わせた包括的な依存関係抽出
- **高速グラフデータベース**: Kùzuグラフデータベースによる高速な依存関係検索
- **高度な分析機能**: 循環依存検出、重要性スコア算出、依存関係の深度分析
- **直感的なCLI**: 分析、クエリ、レポート生成を簡単に実行

## インストール

```bash
# uvを使用する場合（推奨）
uv add pydepgraph

# pipを使用する場合
pip install pydepgraph
```

## 依存関係

- Python 3.12+
- Kùzu (グラフデータベース)
- NetworkX (グラフ分析)
- Tach (モジュール依存関係抽出)

## クイックスタート

### 1. プロジェクトの分析

```bash
# 現在のディレクトリを分析
pydepgraph analyze

# 特定のプロジェクトを分析
pydepgraph analyze /path/to/your/project

# JSON形式で結果を出力
pydepgraph analyze --output json
```

### 2. 依存関係の検索

```bash
# 全モジュール一覧
pydepgraph query modules

# 全関数一覧
pydepgraph query functions

# 全クラス一覧
pydepgraph query classes

# import関係一覧
pydepgraph query imports

# 関数呼び出し一覧
pydepgraph query calls
```

### 3. グラフ分析

```bash
# グラフ統計情報
pydepgraph analytics stats

# 循環依存検出
pydepgraph analytics cycles

# 重要性スコア算出
pydepgraph analytics importance

# 依存関係の深度分析
pydepgraph analytics depth --root module_name
```

### 4. レポート生成

```bash
# Markdown形式レポート
pydepgraph report --format markdown

# JSONレポート
pydepgraph report --format json

# ファイルに保存
pydepgraph report --output-file dependency_report.md
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

## 使用例

### 基本的な使用方法

```bash
# 1. プロジェクトを分析
pydepgraph analyze

# 2. 循環依存を確認
pydepgraph analytics cycles

# 3. 重要なモジュールを特定
pydepgraph analytics importance

# 4. レポートを生成
pydepgraph report --output-file report.md
```

### 高度な分析

```bash
# 特定モジュールからの依存関係の深度分析
pydepgraph analytics depth --root my_module --node-type module

# 関数レベルでの循環依存検出
pydepgraph analytics cycles --node-type function

# クラスの重要性スコア
pydepgraph analytics importance --node-type class

# 複雑度でフィルタした関数検索
pydepgraph query functions --filter "complexity > 5"
```

### 出力形式の指定

```bash
# JSON形式で全モジュール取得
pydepgraph query modules --format json

# テーブル形式でグラフ統計表示
pydepgraph analytics stats --format table
```

## アーキテクチャ

### 3層構成
- **UI Layer**: CLI（コマンドラインインターフェース）
- **Service Layer**: Analyzer Service、Query Service、Graph Analytics Service
- **Data Layer**: Extractors（Tach、AST解析）、Data Normalizer、Kùzu Graph Database

### 主要コンポーネント

#### Extractors
- **TachExtractor**: モジュール間の依存関係を抽出
- **Code2FlowExtractor**: 関数・クラス間の呼び出し関係をAST解析で抽出

#### Services
- **QueryService**: 基本的なクエリ機能
- **ExtendedQueryService**: 高度な検索機能
- **GraphAnalyticsService**: グラフ分析アルゴリズム

#### Database
- **Kùzuグラフデータベース**: 高速な依存関係ストレージと検索

## データモデル

### ノード（実体）
- **Module**: Pythonモジュール（ファイル）
- **Function**: 関数・メソッド
- **Class**: クラス定義

### 関係（エッジ）
- **ModuleImports**: モジュール間のimport関係
- **FunctionCalls**: 関数間の呼び出し関係
- **Inheritance**: クラス間の継承関係
- **Contains**: 包含関係（モジュールが関数・クラスを含む）

## コマンドリファレンス

### analyze
プロジェクト全体の依存関係を分析

```bash
pydepgraph analyze [PROJECT_PATH] [OPTIONS]
```

**オプション:**
- `--output {json,table}`: 出力形式（デフォルト: table）
- `--database PATH`: データベースファイルパス

### query
依存関係の検索

```bash
pydepgraph query {modules,functions,classes,imports,calls} [OPTIONS]
```

**オプション:**
- `--filter EXPRESSION`: フィルタ条件
- `--format {json,table}`: 出力形式（デフォルト: table）

### analytics
グラフ分析の実行

```bash
pydepgraph analytics {stats,cycles,importance,depth} [OPTIONS]
```

**オプション:**
- `--node-type {module,function,class}`: 分析対象ノードタイプ（デフォルト: module）
- `--root NODE`: 深度分析の起点ノード
- `--format {json,table}`: 出力形式（デフォルト: table）

### report
包括的なレポート生成

```bash
pydepgraph report [OPTIONS]
```

**オプション:**
- `--output-file FILE`: 出力ファイルパス
- `--format {json,html,markdown}`: レポート形式（デフォルト: markdown）

## 開発

### 開発環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/your-username/pydepgraph.git
cd pydepgraph

# uvを使用して依存関係をインストール
uv sync

# 開発用依存関係もインストール
uv sync --dev
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 特定フェーズのテスト
uv run pytest tests/test_phase1.py
uv run pytest tests/test_phase2.py
uv run pytest tests/test_phase3.py
uv run pytest tests/test_phase4.py

# カバレッジ付きテスト
uv run pytest --cov=pydepgraph
```

### コード品質チェック

```bash
# リント
uv run ruff check

# 型チェック
uv run mypy

# フォーマット
uv run ruff format
```

## トラブルシューティング

### よくある問題

**Q: "Database not found" エラーが表示される**
A: 最初にプロジェクトを分析してください：`pydepgraph analyze`

**Q: 大きなプロジェクトで分析が遅い**
A: 設定ファイルで除外パターンを追加し、不要なファイルを除外してください

**Q: メモリ不足エラーが発生する**
A: 設定ファイルで `max_file_size_mb` を小さくするか、バッファプールサイズを調整してください

### ログ出力

詳細なログを確認したい場合は `-v` オプションを使用：

```bash
# 詳細ログ
pydepgraph -v analyze

# デバッグログ
pydepgraph -vv analyze
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 作者

PyDepGraph Development Team

---

**注意**: このプロジェクトは個人利用を前提として設計されており、大規模な監視・ログ機構は含まれていません。シンプルで効率的な依存関係分析に焦点を当てています。