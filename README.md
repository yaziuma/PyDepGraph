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

## Claude Code スキル（スラッシュコマンド）

PyDepGraph を Claude Code から活用するためのカスタムスラッシュコマンドです。  
以下のファイルを `.claude/commands/` ディレクトリに配置すると、Claude Code 上で `/analyze-deps` のようにスラッシュコマンドとして実行できます。

```bash
mkdir -p .claude/commands
```

---

### `/analyze-deps` — 依存関係を分析して全体像を把握

`.claude/commands/analyze-deps.md`:

````markdown
指定されたプロジェクトの依存関係を PyDepGraph で分析し、全体像を把握してください。

対象: $ARGUMENTS（省略時はカレントディレクトリ）

以下を順に実行して結果を統合してください:

```bash
uv run pydepgraph analyze ${ARGUMENTS:-.}
uv run pydepgraph analytics stats
uv run pydepgraph analytics cycles
uv run pydepgraph analytics importance
uv run pydepgraph report --metrics --sort-by fan_in --format table
```

結果を以下の観点で要約:
- **全体規模**: モジュール数、関数数、クラス数、LOC
- **依存関係の健全性**: 循環依存の有無、グラフ密度
- **中心的モジュール**: fan_in が高いモジュール
- **リスクポイント**: 循環依存、複雑度の高いモジュール、密結合の箇所
- **改善提案**: 依存関係の観点からの具体的な改善案
````

---

### `/find-impact` — 変更の影響範囲を特定

`.claude/commands/find-impact.md`:

````markdown
指定されたファイルを変更した場合の影響範囲を分析してください。

対象: $ARGUMENTS

以下を実行:

```bash
uv run pydepgraph inspect $ARGUMENTS
uv run pydepgraph query imports --format json
uv run pydepgraph query calls --format json
```

imports の結果から対象モジュールを target_module に持つ関係を抽出し、影響を受けるファイルそれぞれに `uv run pydepgraph inspect <file>` を実行してください。

以下の形式で影響分析レポートを出力:
- **変更対象**: ファイル名、公開インターフェース
- **直接影響**: このモジュールを直接 import しているモジュール一覧
- **間接影響**: 直接影響のさらに上流（2段階まで）
- **影響を受ける関数/クラス**: 具体的な名前リスト
- **リスク評価**: 影響範囲に基づく変更リスク（低/中/高）
- **推奨事項**: 変更を安全に行うための具体的なステップ
````

---

### `/understand-module` — モジュールの役割と接続を理解

`.claude/commands/understand-module.md`:

````markdown
指定されたモジュールの役割、公開インターフェース、依存関係を包括的に理解してください。

対象: $ARGUMENTS

以下を実行:

```bash
uv run pydepgraph inspect $ARGUMENTS
uv run pydepgraph query imports --format json
```

imports の結果から対象モジュールの依存先（source_module として持つ関係）と依存元（target_module として持つ関係）を抽出してください。
対象モジュールのロールを推定し、同じロールのモジュールも検索:

```bash
uv run pydepgraph query role --value <推定ロール> --format json
```

以下の形式で出力:
- **モジュール名**: ファイルパスとモジュール名
- **推定ロール**: service, api, model, cli, util 等
- **責務**: 主な責務（1〜3文）
- **公開インターフェース**: 主要な関数・クラスのシグネチャ
- **依存先 / 依存元**: 他モジュールとの関係
- **アーキテクチャ上の位置**: UI/Service/Data のどこに位置するか
````

---

### `/review-architecture` — アーキテクチャをレビュー

`.claude/commands/review-architecture.md`:

````markdown
PyDepGraph を使ってプロジェクト全体のアーキテクチャを俯瞰レビューしてください。

対象: $ARGUMENTS（省略時はカレントディレクトリ）

```bash
uv run pydepgraph analyze ${ARGUMENTS:-.}
uv run pydepgraph analytics stats
uv run pydepgraph analytics cycles
uv run pydepgraph report --metrics --sort-by betweenness --format table
```

ロール別にモジュールを分類:

```bash
uv run pydepgraph query role --value api --format json
uv run pydepgraph query role --value service --format json
uv run pydepgraph query role --value model --format json
uv run pydepgraph query role --value data_access --format json
uv run pydepgraph query role --value cli --format json
uv run pydepgraph query role --value util --format json
```

以下の形式で出力:
- **レイヤー構成**: 各ロールに属するモジュール一覧
- **依存関係の方向性**: 正しい方向（上位→下位）と逆方向の依存
- **アーキテクチャ上の懸念**: 循環依存、神モジュール、レイヤー違反
- **改善提案**: 優先度付きリファクタリング案
````

---

### `/track-evolution` — 依存関係の進化を追跡

`.claude/commands/track-evolution.md`:

````markdown
Git コミット間の依存関係変化を分析してください。

引数: $ARGUMENTS（例: `HEAD~5 HEAD`、`v1.0 v2.0`。省略時は `HEAD~1 HEAD`）

```bash
uv run pydepgraph evolution --from <from_ref> --to <to_ref>
```

以下の形式で出力:
- **変更サマリー**: 追加/削除されたモジュール・依存関係の数
- **追加された要素**: 新規モジュール一覧（ロール推定付き）、新規依存関係
- **削除された要素**: 削除されたモジュール、依存関係
- **変更の評価**: 複雑度の変化、アーキテクチャへの影響、リグレッションリスク
````

---

### `/inspect-file` — ファイル構造をトークン効率よく把握

`.claude/commands/inspect-file.md`:

````markdown
指定された Python ファイルの公開インターフェースを、ソース全体を読むより少ないトークンで把握してください。

対象: $ARGUMENTS

```bash
uv run pydepgraph inspect $ARGUMENTS
```

出力 JSON を解析し、以下を整理して報告:
- **クラス一覧**: クラス名、基底クラス、メソッドシグネチャ、クラス変数
- **関数一覧**: シグネチャ（引数名、型、デフォルト値、戻り値型）、デコレータ
- **モジュールレベル**: import 一覧、定数、モジュール docstring
````

---

### `/find-by-role` — ロールでモジュールを検索

`.claude/commands/find-by-role.md`:

````markdown
プロジェクト内のモジュールを役割で検索してください。

ロール: $ARGUMENTS
（選択肢: api, service, model, data_access, cli, config, util, test, extractor, reporting, middleware, external）

```bash
uv run pydepgraph query role --value $ARGUMENTS --format json
```

見つかったモジュールの主要なものを inspect:

```bash
uv run pydepgraph inspect <file_path>
```

結果を以下の形式で報告:
| モジュール名 | ファイルパス | LOC | 主な責務 |
|---|---|---|---|
````

---

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