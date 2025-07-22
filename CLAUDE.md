# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

** 記載に無い機能の実装は厳禁 **

## プロジェクト概要

**PyDepGraph** は Python プロジェクトの依存関係を自動抽出・グラフ化し、LLM による効率的な依存関係検索を実現するライブラリです。Tach（モジュールレベル）とCode2Flow（関数レベル）を使用して依存関係を抽出し、Kùzuグラフデータベースに格納して高速検索を提供します。

## アーキテクチャ

### 3層構成
- **UI Layer**: CLI（コマンドラインインターフェース）のみ
- **Service Layer**: Analyzer Service、Query Service、Graph Analytics Service
- **Data Layer**: Extractors（Tach、Code2Flow）、Data Normalizer、Kùzu Graph Database

### 主要コンポーネント
- **Extractors**: TachExtractor（モジュール間依存）、Code2FlowExtractor（関数間呼び出し）
- **Data Processing**: 複数の抽出結果を統合・正規化
- **Graph Database**: Kùzuを使用したグラフデータベース操作
- **Services**: 分析実行、クエリ処理、グラフ解析アルゴリズム

## データモデル

### グラフスキーマ（Kùzu）
- **Module ノード**: name, file_path, package, lines_of_code, complexity_score等
- **Function ノード**: name, qualified_name, module_id, cyclomatic_complexity等  
- **Class ノード**: name, qualified_name, method_count, inheritance_depth等
- **関係**: ModuleImports, FunctionCalls, Inheritance, Contains

## 設定管理

- **設定ファイル**: `pydepgraph.toml`（TOML形式）
- **主要設定**: extractors（抽出器設定）、database（DB設定）、analysis（解析設定）
- **デフォルト動作**: テスト含む、標準除外パターン適用

## エラー処理方針

- **部分的失敗の継続**: 一部ファイルの分析失敗時も他ファイルは継続処理
- **詳細エラー報告**: 失敗ファイルと理由をユーザーに明確に報告
- **データ整合性**: トランザクション機能による一貫性保証、増分更新対応

## 実装上の注意点

- **型安全性**: 完全な型ヒント対応が必須
- **モジュラー設計**: 各コンポーネントは独立性を保つ
- **拡張可能性**: 新しい抽出ツールの追加が容易な設計
- **個人利用前提**: 大規模な監視・ログ機構は不要、シンプルな設計を維持

## 開発ツール

- **パッケージ管理**: uvを使用（`uv run pytest`、`uv run ruff`等）
- **テスト実行**: `uv run pytest`
- **リント**: `uv run ruff check`
- **タイプチェック**: `uv run mypy`

## 現在の重大な問題と対策

### 🚨 データベース保存機能の不具合

#### 問題の詳細
1. **型の不整合**: ExtractorBaseのExtractionResultとmodels.pyのExtractionResultが異なる定義
2. **データ変換エラー**: 抽出器がdict形式で返すがcore.pyがオブジェクト形式を期待
3. **不完全なデータ保存**: 分析結果がデータベースに正しく保存されない

#### 根本原因
- **アーキテクチャの不整合**: 抽出器の出力形式とコア処理の期待形式が一致していない
- **型定義の重複**: extractors/base.pyとmodels.pyで同名のExtractionResultが異なる構造
- **データフロー設計の問題**: 各レイヤー間のデータ受け渡し仕様が不明確

#### 必須対策
1. **型定義の統一**: models.pyの型定義を唯一のソースとし、extractors/base.pyのExtractionResultを削除
2. **データ変換層の実装**: 抽出器からコアへの変換を担うDataIntegratorの完全実装
3. **エンドツーエンドテスト**: 抽出→保存→クエリの完全なフローテスト

#### 現在の制限事項
- **実質的に使用不可**: 分析結果がデータベースに保存されないため全機能が無効
- **クエリ結果が空**: データベースが空のため検索・分析機能が機能しない
- **レポート機能無効**: 実データがないため意味のないレポートしか生成できない

### 🛠️ Tach依存関係の問題

#### 修正済み
- **コマンド構文エラー**: `tach report dependencies --format json` → `tach map`に修正済み

#### 残存問題
- **設定ファイル依存**: 多くのTachコマンドが設定ファイル（.tach.yml）を要求
- **出力形式の制限**: JSON形式での構造化出力が困難

### ⚠️ 開発・テスト時の注意事項

- **Phase 4は実質的に未完成**: データ保存の根本的問題により実用不可
- **統合テストが必要**: 各コンポーネント単体では動作するが連携時に失敗
- **型安全性の確保**: 完全な型ヒント対応が必須だが現在は不整合状態

### 📋 テスト方針の重要な修正

#### 🚨 既存テストの問題点
現在のPhaseテスト（test_phase1.py ～ test_phase4.py）は **完全にモック化されており、実装の品質を全く保証していない**。

**問題のあるテストパターン例:**
```python
# これは実装の問題を隠蔽する偽のテスト
mock_module.to_dict.return_value = {"name": "test_module"}
mock_query.get_all_modules.return_value = [mock_module]
```

#### ✅ 必須のテスト方針
**各Phaseの確認テストでは以下を厳守すること:**

1. **モックの使用禁止**: `MagicMock`、`patch`等によるモック化は一切使用しない
2. **実データでのテスト**: 実際のPythonファイルを使用した分析テスト
3. **エンドツーエンドテスト**: 抽出→保存→検索→分析の完全なフロー確認
4. **実ファイルでのデータベース操作**: 実際のKùzuデータベースファイルを使用
5. **型の実整合性確認**: 実際のオブジェクトと型定義の一致確認

#### 🔍 正しいテスト実装例
```python
def test_phase_integration():
    """実際のファイルとデータベースを使った統合テスト"""
    # 実際のPythonプロジェクトを分析
    config = Config.get_default_config()
    core = PyDepGraphCore(config)
    result = core.analyze_project("path/to/real/project")
    
    # 実際のデータベース確認
    db = GraphDatabase(config.database.path)
    modules = db.execute_query("MATCH (m:Module) RETURN m")
    assert len(modules) > 0  # 実際のデータが存在すること
```

#### ⚠️ 重要
**モック化されたテストは実装品質の保証にならない。必ず実際のデータとファイルを使用してテストすること。**

### 📊 テスト結果分析（2025年7月現在）

#### 🗑️ モックテスト削除後の状況
**削除されたファイル:**
- `tests/test_phase1.py` - `tests/test_phase5.py` (全Phase別モックテスト)
- 理由: MagicMockによる偽の成功を排除し、実装の真の状態を把握するため

#### 📈 現在のテスト状況
**統合テスト結果（tests/test_integration_pyprolog.py）:**
- **✅ 3個成功 / ❌ 4個失敗**
- 成功: サンプルプロジェクト存在確認、Tach実データ抽出、出力形式一貫性
- 失敗: Code2Flow統合、データベースクエリ、完全パイプライン、モック検証

**pyprologサンプルテスト結果:**
- **✅ 15個成功**: スキャナ・パーサ・変数マッパー（基本機能）
- **❌ 6個失敗**: ランタイム統合テスト（日本語変数処理）

#### 🚨 発見された具体的問題

##### 1. Code2FlowExtractor不具合
```
AssertionError: assert 'code2flow_ast' == 'code2flow'
```
- **問題**: 実際のCode2Flowが失敗し、ASTフォールバックが動作
- **影響**: 関数レベル依存関係の抽出が不完全

##### 2. Kùzuデータベースクエリ構文エラー
```
RuntimeError: Parser exception: extraneous input 'SHOW' expecting {ALTER, ATTACH...}
```
- **問題**: `SHOW TABLES`がKùzu Cypherで無効
- **影響**: データベーススキーマ確認が不可能

##### 3. データ変換レイヤーの問題
```
AttributeError: 'dict' object has no attribute 'name'
```
- **問題**: 抽出器（dict形式）とコア処理（オブジェクト形式）の型不整合
- **影響**: 分析結果のデータベース保存が完全に失敗

##### 4. 統合パイプライン未完成
- **TachExtractor**: ✅ 動作（10モジュール、14依存関係を抽出）
- **Code2FlowExtractor**: ❌ フォールバック動作のみ
- **DataIntegrator**: ❌ 型変換エラーで停止
- **Database保存**: ❌ 完全に失敗
- **検索・分析機能**: ❌ 空のデータベースのため無意味

#### 📋 品質評価結果
**実装完成度: 約30%**
- ✅ 基本コンポーネント（個別テスト成功）
- ✅ CLI基本構造
- ❌ エンドツーエンド統合
- ❌ データベース保存
- ❌ 実用的な機能動作

#### 🎯 結論
**Phase 4は実質的に未完成。** モックテストは15/15成功だったが、実データテストは7/7で4個失敗。これは実装品質の保証がいかに重要かを示している。

この問題を解決せずに完成とすることは不可能です。