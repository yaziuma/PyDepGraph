指定されたモジュールの役割、公開インターフェース、依存関係を包括的に理解してください。

対象: $ARGUMENTS

以下を実行:

```bash
uv run pydepgraph inspect $ARGUMENTS --skeleton
uv run pydepgraph query context --target $ARGUMENTS --depth 1
uv run pydepgraph query imports --format json
```

imports の結果から対象モジュールの依存先（source_module として持つ関係）と依存元（target_module として持つ関係）を抽出してください。
対象モジュールのロールを推定し、同じロールのモジュールも検索:

```bash
uv run pydepgraph query role --value <推定ロール> --format json
```

以下の形式で出力:
- **モジュール名**: ファイルパスとモジュール名
- **推定ロール**: service, api, model, cli, util 等
- **責務**: 主な責務（1〜3文）
- **公開インターフェース**: 主要な関数・クラスのシグネチャ
- **依存先 / 依存元**: 他モジュールとの関係
- **アーキテクチャ上の位置**: UI/Service/Data のどこに位置するか
