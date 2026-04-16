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
