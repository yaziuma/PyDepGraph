# PyDepGraph

Python プロジェクトの依存関係を自動分析し、グラフデータベースに格納して高速検索を可能にするツールです。

## 特徴

- **多層的な依存関係抽出**:
  - `tach`を利用した高速なモジュールレベルの依存関係抽出。
  - `code2flow`とAST解析による、関数・クラスレベルの詳細な依存関係（呼び出し、継承）抽出。
- **高度なグラフ分析**:
  - `networkx`を活用した循環依存検出、重要度計算（PageRank）、依存関係の深さ分析。
- **高速なデータストア**:
  - 組み込みグラフデータベース`Kùzu`を使用して、抽出した依存関係データを高速に検索・集計。
- **簡単な操作**:
  - 直感的なCLIを提供し、分析からクエリ、レポート生成までを簡単に実行可能。

## インストール

```bash
# このプロジェクトはuvを使用して開発されています
git clone https://github.com/your-username/PyDepGraph.git
cd PyDepGraph
uv sync

# 実行（開発版）
uv run pydepgraph --help
```

## クイックスタート

```bash
# プロジェクトを分析
uv run pydepgraph analyze /path/to/your/project

# 依存関係を検索
uv run pydepgraph query modules

# グラフ統計を表示
uv run pydepgraph analytics stats

# レポートを生成
uv run pydepgraph report --output-file report.md
```

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