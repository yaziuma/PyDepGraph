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