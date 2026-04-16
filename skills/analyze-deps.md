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
