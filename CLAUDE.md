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

# グラフ統計
uv run pydepgraph analytics stats

# レポート生成
uv run pydepgraph report --output-file report.md
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
- **Graph Database** (`database.py`): Kùzuを使用したグラフデータベース操作
- **Services**: Analytics Service（グラフ分析）、Query Service（検索機能）
- **CLI** (`cli.py`): すべてのユーザーインターフェース

### データフロー
1. **抽出**: 各Extractorがプロジェクトから依存関係を抽出
2. **統合**: DataIntegratorが異なる形式の抽出結果を統一モデルに変換
3. **保存**: GraphDatabaseがKùzuにノード（Module、Function、Class）とエッジ（関係性）を保存
4. **分析・検索**: Services層が高度なクエリとグラフ分析を提供

## 設定管理

- **設定ファイル**: `pydepgraph.toml`（TOML形式）
- **主要設定**: extractors（抽出器設定）、database（DB設定）、analysis（解析設定）
- **デフォルト動作**: テスト含む、標準除外パターン適用

## データモデル

### グラフスキーマ（Kùzu）
- **Module ノード**: name, file_path, package, lines_of_code, complexity_score等
- **Function ノード**: name, qualified_name, module_id, cyclomatic_complexity等  
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
- ✅ **エンドツーエンド分析**: プロジェクト→抽出→データベース保存→検索の完全なパイプライン
- ✅ **マルチ抽出器**: Tach、Code2Flow、DependencyFileの統合動作
- ✅ **グラフデータベース**: Kùzuによる高速なノード・エッジ保存と検索
- ✅ **メタデータ収集**: lines_of_code、complexity_scoreの正確な取得
- ✅ **CLI基本機能**: analyze, query, analytics, reportコマンド
- ✅ **Code2Flow実動作**: 実際のCode2Flow実行による精密な関数レベル解析

### 🚨 未完成機能（Critical）

#### Evolution機能の実装不完全
- **症状**: `evolution`コマンドがCLIに実装されていない
- **現状**: 
  - バックエンドは完全実装済み（SnapshotManager, GraphComparator, EvolutionReporter）
  - テストファイル存在（tests/test_cli_evolution.py）だが、`cmd_evolution`関数が未実装
  - READMEでは利用可能と記載されているが実際は使用不可
- **影響**: 依存関係の進化分析機能が利用できない
- **必要作業**: 
  1. CLI parser に evolution サブコマンドを追加
  2. `cmd_evolution` 関数の実装
  3. main関数でのルーティング追加

#### Report機能の部分的実装
- **症状**: `--metrics`、`--sort-by` オプションが実装されていない
- **現状**: 基本的なreportコマンドは動作するが、高度なメトリクス機能が未完成
- **影響**: 詳細なメトリクスレポート生成が不可能

### テスト結果
- **統合テスト**: 7/7成功 ✅
- **Code2Flow実動作テスト**: 13/13成功 ✅
- **Evolution CLIテスト**: ImportErrorで失敗 ❌
- **実用価値**: 基本機能は完全に利用可能、進化分析機能は未利用

## ログ設計

- **ライブラリとしてのベストプラクティス**: アプリケーション側にログ設定を委ねる
- **レベル設定のみ**: ハンドラやフォーマッタは設定しない
- **詳細なデバッグ情報**: `-v`、`-vv`オプションによる段階的ログレベル制御