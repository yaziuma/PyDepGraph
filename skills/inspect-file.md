# inspect-file

指定された Python ファイルを、**最小トークンで正確に理解**するための手順。

対象: `$ARGUMENTS`（例: `src/pydepgraph/core.py`）

---

## 使い方（目的に応じて選択）

### A. 構造を素早く把握したいとき（骨格）
```bash
uv run pydepgraph inspect $ARGUMENTS --skeleton
```

把握できる情報:
- クラス名 / 継承関係
- 関数・メソッドのシグネチャ
- 定数・docstring・import

### B. 対象 + 周辺依存を一緒に見たいとき（context）
```bash
uv run pydepgraph query context --target $ARGUMENTS --depth 1
```

`--depth` は必要に応じて変更可能です（例: `--depth 2`）。

### C. 関数単位で詳細を見たいとき
```bash
uv run pydepgraph inspect $ARGUMENTS --target-function <function_name>
```

---

## 回答テンプレート

1. **概要**: このファイルの責務（1〜2文）
2. **公開インターフェース**: クラス/関数シグネチャ一覧
3. **依存関係**: 主要な依存先（必要なものだけ）
4. **詳細実装（必要箇所のみ）**: `--target-function` で取得した内容を要約

上記A/B/Cを、要求に合わせて自由に組み合わせて使ってください。
