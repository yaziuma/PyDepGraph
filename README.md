# PyDepGraph

Python プロジェクトの依存関係を自動分析し、グラフデータベースに格納して高速検索を可能にするツールです。LLM による効率的なコードベース理解を支援する機能を備えています。

## 特徴

- **多層的な依存関係抽出**:
  - `pyproject.toml`や`requirements.txt`を解析し、外部ライブラリへの依存関係を抽出。
  - `tach`を利用した高速なモジュールレベルの依存関係抽出。
  - 高度なAST解析による、ファイル横断での正確な関数・クラスレベルの依存関係（呼び出し、継承）抽出。
- **LLMフレンドリーなAST構造検査**:
  - `inspect` コマンドで、Pythonファイルの公開インターフェース（関数シグネチャ、クラス定義、型アノテーション）をJSON形式で出力。
  - 実装詳細を省き、LLMのトークン消費を最小化しつつコード構造を正確に把握可能。
- **モジュールのロール自動推論**:
  - ディレクトリ名、ファイル名、基底クラス、関数名パターンからモジュールの役割（`api`, `service`, `model`, `cli`, `test`, `config`, `util`, `data_access` 等）を自動推定。
  - `query role --value service` でロールベースのフィルタリング検索が可能。
- **FQN（完全修飾名）正規化**:
  - ファイルパス、ドット区切り名、エイリアスなど異なる名前表現を正規FQNに統一。
  - 相対インポートやエイリアスの解決により、グラフの欠損を防止。
- **高度なグラフ分析**:
  - `networkx`を活用した循環依存検出、重要度計算（PageRank）、依存関係の深さ分析。
  - ファンイン・ファンアウト、各種中心性（媒介中心性、近接中心性）などのメトリクス計算。
- **依存関係の進化分析**:
  - `evolution` コマンドでGitコミット間の依存関係グラフの差分を検出・可視化。
  - ノードやエッジの追加・削除を自動的に検出してレポート。
- **高速なデータストア**:
  - 組み込みグラフデータベース`Kùzu`を使用して、抽出した依存関係データを高速に検索・集計。
- **簡単な操作**:
  - 直感的なCLIを提供し、分析からクエリ、レポート生成までを簡単に実行可能。

## インストール

```bash
# このプロジェクトはuvを使用して開発されています
git clone https://github.com/yaziuma/PyDepGraph.git
cd PyDepGraph
uv sync

# 実行（開発版）
uv run pydepgraph --help
```

## クイックスタート

### 基本的な分析フロー

```bash
# プロジェクトを分析（依存関係をグラフDBに格納）
uv run pydepgraph analyze /path/to/your/project

# 依存関係を検索
uv run pydepgraph query modules
uv run pydepgraph query functions
uv run pydepgraph query classes
uv run pydepgraph query imports
uv run pydepgraph query calls

# グラフ統計を表示
uv run pydepgraph analytics stats
uv run pydepgraph analytics cycles
uv run pydepgraph analytics importance

# レポートを生成
uv run pydepgraph report --output-file report.md
uv run pydepgraph report --format json
uv run pydepgraph report --metrics --sort-by fan_in
```

### LLM向け機能

```bash
# ファイルのAST構造をJSON形式で出力（トークン節約）
uv run pydepgraph inspect src/pydepgraph/core.py
uv run pydepgraph inspect src/pydepgraph/  # ディレクトリも可

# ロール（役割）でモジュールを検索
uv run pydepgraph query role --value service
uv run pydepgraph query role --value api
uv run pydepgraph query role --value model
```

### 依存関係の進化分析

```bash
# Gitコミット間の依存関係変化を比較
uv run pydepgraph evolution --from HEAD~1 --to HEAD /path/to/project
```

## コマンドリファレンス

| コマンド | 説明 |
|---|---|
| `analyze <path>` | プロジェクトの依存関係を分析しDBに格納 |
| `query <type>` | modules/functions/classes/imports/calls/role を検索 |
| `analytics <type>` | stats/cycles/importance/depth のグラフ分析 |
| `report` | 分析レポートを生成（`--metrics`, `--sort-by` 対応） |
| `evolution` | Gitコミット間の依存関係差分を表示 |
| `inspect <target>` | ファイル/ディレクトリのAST構造をJSON出力 |

## LLMとの連携例

PyDepGraph は LLM がコードベースを効率的に理解するためのコンテキストプロバイダーとして設計されています。

```
1. pydepgraph analyze .              # 依存関係を抽出・格納
2. pydepgraph query modules          # 全モジュール一覧を把握
3. pydepgraph query role --value service  # サービス層のモジュールを特定
4. pydepgraph inspect src/app/services/user_service.py  # 対象の構造を把握
5. pydepgraph analytics importance   # 重要モジュールを特定
6. pydepgraph evolution --from v1.0 --to v2.0  # バージョン間の変化を把握
```

このワークフローにより、LLM は「依存関係の把握」→「対象ファイルの構造把握」→「変更影響の分析」をトークンを節約しながらシームレスに実行できます。

## ドキュメント

- [ユーザーガイド](docs/user_guide.md) - 詳細な使用方法とコマンドリファレンス
- [アーキテクチャ](docs/architecture.md) - 内部構造とデータモデル
- [ロギング設計](docs/logging_design.md) - ライブラリロギングのベストプラクティス

## ライセンス

MIT License

## 貢献

作者は管理できないので、興味持たれた方がもし居たら勝手にどんどんフォークして改善してください。

## 作者

yaziuma

---

**注意**: このプロジェクトは個人利用を前提として設計されており、大規模な監視・ログ機構は含まれていません。シンプルで効率的な依存関係分析に焦点を当てています。