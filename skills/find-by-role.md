プロジェクト内のモジュールを役割で検索してください。

ロール: $ARGUMENTS
（選択肢: api, service, model, data_access, cli, config, util, test, extractor, reporting, middleware, external）

```bash
uv run pydepgraph query role --value $ARGUMENTS --format json
```

見つかったモジュールの主要なものを inspect:

```bash
uv run pydepgraph inspect <file_path>
```

結果を以下の形式で報告:
| モジュール名 | ファイルパス | LOC | 主な責務 |
|---|---|---|---|
