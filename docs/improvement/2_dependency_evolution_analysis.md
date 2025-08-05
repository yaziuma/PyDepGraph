# 詳細設計: 依存関係の進化分析 (v2)

## 1. 概要

本ドキュメントでは、依存関係グラフの経時的な変化を分析し、コードベースの健全性を評価するための「依存関係の進化分析」機能に関する詳細設計を定義する。Gitのコミットハッシュと連携し、特定のバージョン間での依存構造の変化を追跡・可視化する。

## 2. 設計詳細

### 2.1. 分析結果のスナップショット管理

#### 2.1.1. 担当クラス

-   `pydepgraph.incremental.SnapshotManager` (新規作成)

#### 2.1.2. スナップショットの仕様

-   **ファイル形式**: JSON。人間が可読であり、プログラムでの扱いも容易なため。
-   **命名規則**: `<git_commit_hash>.json`。Gitのバージョンと明確に対応付ける。
-   **保存場所**: プロジェクトルートの`.pydepgraph/snapshots/`ディレクトリ。このディレクトリは`.gitignore`に追加を推奨する。
-   **JSONスキーマ**:
    ```json
    {
      "version": "1.0",
      "commit_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
      "created_at": "2025-08-05T10:30:00Z",
      "graph": {
        "nodes": [
          { "id": "my_app.module_a", "type": "module", "path": "src/my_app/module_a.py" },
          { "id": "my_app.module_b", "type": "module", "path": "src/my_app/module_b.py" }
        ],
        "edges": [
          { "source": "my_app.module_a", "target": "my_app.module_b", "type": "import" }
        ]
      }
    }
    ```

#### 2.1.3. 処理フロー

-   **保存 (`save_snapshot`)**:
    1.  現在のGitコミットハッシュを取得する (`git rev-parse HEAD`)。
    2.  `pydepgraph.models`のグラフオブジェクトを上記のJSONスキーマにシリアライズする。
    3.  `.pydepgraph/snapshots/<commit_hash>.json` として保存する。
-   **読み込み (`load_snapshot`)**:
    1.  引数で指定されたコミットハッシュまたはエイリアス（`latest`, `previous`）を解決する。
        -   `latest`: `git rev-parse HEAD`
        -   `previous`: `git rev-parse HEAD~1`
    2.  対応するJSONファイルを読み込み、`pydepgraph.models`のグラフオブジェクトにデシリアライズして返却する。

### 2.2. グラフの比較

#### 2.2.1. 担当クラス

-   `pydepgraph.incremental.GraphComparator` (新規作成)

#### 2.2.2. 比較ロジック

-   **入力**: 2つのグラフオブジェクト（`graph_before`, `graph_after`）。
-   **キー**: ノードとエッジの同一性は、その`id`（ノードの場合）または`source`と`target`のペア（エッジの場合）によって判断する。
-   **処理フロー**:
    1.  `nodes_before`と`nodes_after`の集合を計算する。
    2.  `added_nodes = nodes_after - nodes_before`
    3.  `deleted_nodes = nodes_before - nodes_after`
    4.  `edges_before`と`edges_after`の集合を計算する。
    5.  `added_edges = edges_after - edges_before`
    6.  `deleted_edges = edges_before - edges_after`
-   **出力**: 比較結果を格納するデータクラス `ComparisonResult` を返す。
    ```python
    @dataclass
    class ComparisonResult:
        added_nodes: Set[Node]
        deleted_nodes: Set[Node]
        added_edges: Set[Dependency]
        deleted_edges: Set[Dependency]
    ```

### 2.3. レポーティングとCLI

#### 2.3.1. 担当クラス

-   `pydepgraph.reporting.EvolutionReporter` (新規作成)

#### 2.3.2. CLIインターフェース

-   `pydepgraph`のサブコマンドとして`evolution`を追加する。
-   **コマンド**: `pydepgraph evolution --from <ref1> --to <ref2>`
    -   `<ref>`: コミットハッシュ、タグ、ブランチ名など、Gitが解釈できる任意の参照。
    -   `--to`が省略された場合は、`HEAD`（現在のワーキングコピー）と比較する。
    -   `--from`も省略された場合は、`HEAD~1`と`HEAD`を比較する。

#### 2.3.3. レポート形式

-   コンソールには、`rich`ライブラリを使用して整形されたサマリーと詳細リストを出力する。

```
$ pydepgraph evolution --from a1b2c3d --to f9e8d7c

Comparing dependency graph from a1b2c3d to f9e8d7c

📊 Evolution Summary
┌─────────────────┬───────┐
│ Change Type     │ Count │
├─────────────────┼───────┤
│ Added Nodes     │ 2     │
│ Deleted Nodes   │ 1     │
│ Added Edges     │ 4     │
│ Deleted Edges   │ 3     │
└─────────────────┴───────┘

[+] Added Nodes
- my_app.services.new_feature
- my_app.utils.temp_helper

[-] Deleted Nodes
- my_app.legacy.old_code

[+] Added Dependencies
- my_app.api -> my_app.services.new_feature
...

[-] Deleted Dependencies
- my_app.api -> my_app.legacy.old_code
...
```

## 4. 期待される効果

-   **コードレビューの質の向上**: Pull Requestのレビュー時に、その変更が依存関係に与える影響（意図しない結合の発生など）を自動的にレポートし、客観的な議論を促進する。
-   **アーキテクチャの維持**: 主要モジュール間の依存関係が追加・削除された際にアラートを出すことで、定義されたアーキチャからの逸脱を早期に検知する。
-   **リファクタリングの評価**: 大規模なリファクタリング前後で依存関係がどれだけ整理されたか（エッジが削減されたか）を定量的に評価できる。