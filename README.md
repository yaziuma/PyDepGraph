# PyDepGraph

Python プロジェクトの依存関係を自動分析し、グラフデータベースに格納して高速検索を可能にするツールです。

## 特徴

- モジュール・関数・クラスレベルの依存関係抽出
- 循環依存検出とグラフ分析機能
- 高速なグラフデータベース（Kùzu）による検索
- CLI による簡単な操作

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