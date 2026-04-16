# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**PyDepGraph** は Python プロジェクトの依存関係を自動抽出・グラフ化し、LLM による効率的な依存関係検索を実現するライブラリです。Tach（モジュールレベル）とCode2Flow（関数レベル）を使用して依存関係を抽出し、Kùzuグラフデータベースに格納して高速検索を提供します。

## 開発コマンド

### 基本操作
- **パッケージ管理**: `uv` を使用
- **依存関係インストール**: `uv sync`
- **CLI実行**: `uv run pydepgraph --help`

### テスト実行
- **基本実行（ファイル/ディレクトリ単位、トークン節約）**: `uv run pytest -q`
- **詳細実行（個別テストや詳細情報が必要な場合）**: `uv run pytest -v`
- **特定テスト実行**: `uv run pytest tests/test_integration_pyprolog.py -v`

### 品質チェック
- **リント**: `uv run ruff check`
- **タイプチェック**: `uv run mypy`

### 実用コマンド例
```bash
# プロジェクト分析
uv run pydepgraph analyze /path/to/project

# 依存関係検索
uv run pydepgraph query modules
uv run pydepgraph query functions
uv run pydepgraph query role --value service

# グラフ統計
uv run pydepgraph analytics stats

# レポート生成
uv run pydepgraph report --output-file report.md
uv run pydepgraph report --metrics --sort-by fan_in

# AST構造検査（LLMフレンドリー）
uv run pydepgraph inspect src/pydepgraph/core.py

# 依存関係の進化分析
uv run pydepgraph evolution --from HEAD~1 --to HEAD /path/to/project
```

## アーキテクチャ

### 3層構成
- **UI Layer**: CLI（コマンドラインインターフェース）のみ
- **Service Layer**: Analyzer Service、Query Service、Graph Analytics Service
- **Data Layer**: Extractors（Tach、Code2Flow）、Data Normalizer、Kùzu Graph Database

### 主要コンポーネント
- **Core** (`core.py`): メインの分析エンジン、プロジェクト分析のエントリーポイント
- **Extractors**: TachExtractor（モジュール間依存）、Code2FlowExtractor（関数間呼び出し）、DependencyFileExtractor（外部依存）
- **Data Processing**: DataIntegrator（複数の抽出結果を統合・正規化）
- **Normalizer** (`normalizer.py`): FQN（完全修飾名）正規化、エイリアス解決
- **Role Inferrer** (`role_inferrer.py`): モジュールのロール（役割）自動推論
- **Inspector** (`inspect.py`): LLMフレンドリーなAST構造要約生成
- **Graph Database** (`database.py`): Kùzuを使用したグラフデータベース操作
- **Services**: Analytics Service（グラフ分析）、Query Service（検索機能）
- **Incremental**: SnapshotManager（スナップショット管理）、GraphComparator（グラフ比較）
- **Reporting**: EvolutionReporter（進化レポート生成）
- **CLI** (`cli.py`): すべてのユーザーインターフェース

### データフロー
1. **抽出**: 各Extractorがプロジェクトから依存関係を抽出
2. **統合**: DataIntegratorが異なる形式の抽出結果を統一モデルに変換
3. **正規化**: DataNormalizerがFQNの統一、エイリアス解決を実施
4. **ロール推論**: RoleInferrerがモジュールの役割を自動推定
5. **保存**: GraphDatabaseがKùzuにノード（Module、Function、Class）とエッジ（関係性）を保存
6. **分析・検索**: Services層が高度なクエリとグラフ分析を提供

## 設定管理

- **設定ファイル**: `pydepgraph.toml`（TOML形式）
- **主要設定**: extractors（抽出器設定）、database（DB設定）、analysis（解析設定）
- **デフォルト動作**: テスト含む、標準除外パターン適用

## データモデル

### グラフスキーマ（Kùzu）
- **Module ノード**: name, file_path, package, lines_of_code, complexity_score, role等
- **Function ノード**: name, qualified_name, file_path, cyclomatic_complexity等  
- **Class ノード**: name, qualified_name, method_count, inheritance_depth等
- **関係**: ModuleImports, FunctionCalls, Inheritance, Contains

## 実装上の注意点

- **型安全性**: 完全な型ヒント対応が必須
- **モジュラー設計**: 各コンポーネントは独立性を保つ
- **拡張可能性**: 新しい抽出ツールの追加が容易な設計
- **個人利用前提**: 大規模な監視・ログ機構は不要、シンプルな設計を維持
- **エラー処理**: 部分的失敗の継続、詳細エラー報告、データ整合性保証

## テスト戦略

### 重要原則
- **モック使用の禁止**: 実装品質を保証するため、`MagicMock`、`patch`等によるモック化は一切使用しない
- **実データでのテスト**: 実際のPythonファイルを使用した分析テスト
- **エンドツーエンドテスト**: 抽出→保存→検索→分析の完全なフロー確認
- **実ファイルでのデータベース操作**: 実際のKùzuデータベースファイルを使用

### テストファイル構造
- **統合テスト**: `tests/test_integration_pyprolog.py` - 実際のサンプルプロジェクトを使用
- **Code2Flow実動作テスト**: `tests/test_code2flow_real_execution.py` - 実際のCode2Flow実行検証
- **サンプルプロジェクト**: `tests/sample_code/pyprolog/` - テスト用の実際のPythonプロジェクト

## 現在の実装状況

### 完全動作する機能
- ✅ **エンドツーエンド分析**: プロジェクト→抽出→正規化→ロール推論→データベース保存→検索の完全なパイプライン
- ✅ **マルチ抽出器**: Tach、Code2Flow、DependencyFileの統合動作
- ✅ **グラフデータベース**: Kùzuによる高速なノード・エッジ保存と検索
- ✅ **メタデータ収集**: lines_of_code、complexity_scoreの正確な取得
- ✅ **CLI全機能**: analyze, query, analytics, report, evolution, inspectコマンド
- ✅ **Code2Flow実動作**: 実際のCode2Flow実行による精密な関数レベル解析
- ✅ **Evolution機能**: Gitコミット間の依存関係グラフ差分検出・レポート
- ✅ **Reportメトリクス**: `--metrics`、`--sort-by`オプションによる詳細メトリクスレポート
- ✅ **AST構造検査**: `inspect`コマンドによるLLMフレンドリーなJSON出力
- ✅ **ロール自動推論**: ディレクトリ名・ファイル名・AST解析によるモジュール役割の自動推定
- ✅ **FQN正規化**: エイリアス解決、パス→ドット名変換による名前の統一

### テスト結果
- **統合テスト**: 7/7成功 ✅
- **Code2Flow実動作テスト**: 13/13成功 ✅
- **CLIレポートテスト**: 1/1成功 ✅
- **その他単体テスト**: 全パス ✅

## ログ設計

- **ライブラリとしてのベストプラクティス**: アプリケーション側にログ設定を委ねる
- **レベル設定のみ**: ハンドラやフォーマッタは設定しない
- **詳細なデバッグ情報**: `-v`、`-vv`オプションによる段階的ログレベル制御