# inspect-file

指定された Python ファイルを、**最小トークンで正確に理解**するための手順。

対象: `$ARGUMENTS`（例: `src/pydepgraph/core.py`）

---

## 基本手順（必須）

### 1) まず骨格だけ取る
```bash
uv run pydepgraph inspect $ARGUMENTS --skeleton
```

ここでは以下のみ把握する:
- クラス名 / 継承関係
- 関数・メソッドのシグネチャ
- 定数・docstring・import

### 2) 周辺依存を薄く取る（必要時）
```bash
uv run pydepgraph query context --target $ARGUMENTS --depth 1
```

- 依存先は skeleton
- 対象ファイルは full 実装

### 3) ピンポイント詳細（必要時）
```bash
uv run pydepgraph inspect $ARGUMENTS --target-function <function_name>
```

---

## 判断ルール

- 最初から全文を読まない。
- 原則: **skeleton → context → target-function** の順で情報を増やす。
- 深さを増やすのは、`--depth 1` で足りないときだけ。

---

## 回答テンプレート

1. **概要**: このファイルの責務（1〜2文）
2. **公開インターフェース**: クラス/関数シグネチャ一覧
3. **依存関係**: 主要な依存先（必要なものだけ）
4. **詳細実装（必要箇所のみ）**: `--target-function` で取得した内容を要約

不要な長文転記は禁止。要点のみを返すこと。
