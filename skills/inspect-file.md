指定された Python ファイルの公開インターフェースを、ソース全体を読むより少ないトークンで把握してください。

対象: $ARGUMENTS

```bash
uv run pydepgraph inspect $ARGUMENTS --skeleton
```

まずスケルトンを解析し、以下を整理して報告:
- **クラス一覧**: クラス名、基底クラス、メソッドシグネチャ、クラス変数
- **関数一覧**: シグネチャ（引数名、型、デフォルト値、戻り値型）、デコレータ
- **モジュールレベル**: import 一覧、定数、モジュール docstring

特定関数の詳細実装が必要な場合のみ、以下を実行:

```bash
uv run pydepgraph inspect $ARGUMENTS --target-function <function_name>
```

関連コードの「検索」を最小トークンで行う場合は、次の順で段階的に実行:

1. まず定義名ベースで絞り込み（関数/クラスの一覧把握）

```bash
uv run pydepgraph inspect $ARGUMENTS --skeleton
```

2. 依存周辺を薄く確認（依存先は骨格のみ）

```bash
uv run pydepgraph query context --target $ARGUMENTS --depth 1
```

3. それでも不足する場合のみ、ピンポイントで詳細化
   - 対象関数がわかる: `--target-function`
   - 依存範囲を広げる: `--depth 2` 以上

LLM向け運用ルール:
- いきなりファイル全体を読まず、**skeleton → context → target-function** の順で情報量を増やす。
- 回答では、まず公開インターフェース（シグネチャ）を要約し、実装詳細は必要箇所だけ引用する。
