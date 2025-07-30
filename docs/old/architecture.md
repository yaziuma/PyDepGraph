# PyDepGraph アーキテクチャ

PyDepGraphの内部構造とデータモデルについて説明します。

## アーキテクチャ概要

### 3層構成
- **UI Layer**: CLI（コマンドラインインターフェース）のみ
- **Service Layer**: Analyzer Service、Query Service、Graph Analytics Service
- **Data Layer**: Extractors（Tach、Code2Flow）、Data Normalizer、Kùzu Graph Database

### 主要コンポーネント

#### Extractors（抽出器）
- **TachExtractor**: モジュール間の依存関係を抽出（✅ 完全実装）
- **Code2FlowExtractor**: 関数・クラス間の呼び出し関係を実Code2Flowで抽出（✅ 完全実装）
  - 実Code2Flow実行による精密な関数レベル解析
  - ASTフォールバック機能付き

#### Data Processing（データ処理）
- **DataIntegrator**: 複数の抽出結果を統合・正規化（✅ 完全実装）
- **型変換機能**: 抽出器のdict形式からモデルオブジェクトへの変換

#### Services（サービス）
- **QueryService**: 基本的なクエリ機能（✅ 完全実装）
- **ExtendedQueryService**: 高度な検索機能（✅ 完全実装）
- **GraphAnalyticsService**: グラフ分析アルゴリズム（✅ 完全実装）

#### Database（データベース）
- **Kùzuグラフデータベース**: 高速な依存関係ストレージと検索（✅ 完全実装）
- **グラフスキーマ**: Module、Function、Classノードと関係性の完全サポート

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

### グラフスキーマ（Kùzu）
- **Module ノード**: name, file_path, package, lines_of_code, complexity_score等
- **Function ノード**: name, qualified_name, module_id, cyclomatic_complexity等  
- **Class ノード**: name, qualified_name, method_count, inheritance_depth等
- **関係**: ModuleImports, FunctionCalls, Inheritance, Contains

## 実装完成度

**現在の実装完成度: 90%** - 高品質な実用的依存関係分析ツールとして完全に機能

### ✅ 完全に動作している機能
- **分析機能**: Tach + Code2Flow実動作による包括的依存関係抽出
- **メタデータ収集**: コード行数、複雑度スコア等の正確な統計情報取得
- **データベース**: 全関係性（427エッジ）の正常保存・検索
- **検索機能**: モジュール・関数・クラスの高速検索
- **グラフ分析**: 統計・循環依存検出・重要性スコア算出
- **レポート生成**: Markdown/JSON/HTML形式の包括的レポート
- **CLI**: 全コマンド（analyze, query, analytics, report）の完全動作
- **ロギング**: Pythonライブラリベストプラクティス準拠の適切なログ出力

### 📊 実際の動作実績
- **pyprologサンプル**: 238関数、20モジュール、427関係を正常抽出
- **コードメトリクス**: 4515行、平均複雑度3.99の正確な統計
- **グラフ密度**: 0.0064
- **循環依存**: 0件（健全なアーキテクチャ）
- **重要モジュール**: io_streams (0.1038), repl (0.0775)