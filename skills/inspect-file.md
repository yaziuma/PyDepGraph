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
