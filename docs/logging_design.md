# PyDepGraph ロギング設計

## 基本方針

PyDepGraphはライブラリとして利用される可能性も考慮し、Pythonの標準的な`logging`モジュールに基づいた、柔軟で邪魔にならないロギング方針を採用しています。

1.  **ライブラリとしての責務**: PyDepGraphライブラリ自体は、ロガーを取得してログメッセージを発行することに専念します。ログのフォーマットや出力先（コンソール、ファイルなど）の具体的な設定は、ライブラリの利用者（この場合はCLIアプリケーション）に委ねられます。
2.  **デフォルトでは何もしない**: ライブラリ利用者が明示的に設定しない限り、ログがコンソール等に勝手に出力されることはありません。`logging.NullHandler`の思想に近いです。
3.  **CLIアプリケーションとしての責務**: CLIツールとして実行される際には、ユーザーの利便性のために適切なデフォルトのロギング設定を提供します。

## ロガーの階層構造

PyDepGraph内の各モジュールは、`logging.getLogger(__name__)`を呼び出すことで、自身のモジュールパスに基づいた名前付きロガーを取得します。

これにより、以下のような階層的なロガー構造が形成されます。

```
pydepgraph
├── cli
├── core
├── database
├── extractors
│   ├── tach_extractor
│   └── code2flow_extractor
└── services
    ├── analytics_service
    └── query_service
```

この構造により、利用者は特定のコンポーネント（例: `pydepgraph.extractors`）のログレベルだけを個別に制御することが可能になります。

## CLIにおけるロギング設定

`pydepgraph.cli`モジュールは、アプリケーションのエントリーポイントとして、以下のロギング設定を行います。

### ログレベルの制御

*   `-v` / `--verbose` オプションによって、出力されるログの詳細度を制御できます。
    *   オプションなし: `WARNING`レベル以上のログのみ表示されます。
    *   `-v`: `INFO`レベル以上のログが表示されます（処理の進行状況など）。
    *   `-vv`: `DEBUG`レベル以上のログが表示されます（より詳細な内部情報）。

### 設定の実装 (`cli.py`)

`setup_logging`関数がこのロジックを担当します。

```python
# pydepgraph/cli.py

def setup_logging(verbose: int = 0):
    """ログレベルを設定"""
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # ライブラリとしては、ルートロガーのレベルのみ設定
    # ハンドラやフォーマッタの設定はアプリケーション側に委ねる
    logging.getLogger().setLevel(level)
```

この実装のポイントは、**ハンドラを設定していない**点です。`uv run`のようなモダンなPython実行環境や、他のツールに組み込まれた場合、ルートロガーには既にハンドラが設定されていることが期待されます。PyDepGraphは、その既存の設定を尊重し、ログレベルの変更のみを行います。これにより、他のツールと組み合わせた際のログ出力の衝突や重複を避けることができます。

## ライブラリ開発者向けのガイドライン

PyDepGraphの内部コードを開発する際は、以下のガイドラインに従ってください。

1.  **各モジュールの先頭でロガーを取得する**:
    ```python
    import logging
    logger = logging.getLogger(__name__)
    ```

2.  **適切なログレベルを使用する**:
    *   `logger.debug()`: デバッグ時にのみ役立つ詳細情報（変数の値、特定の処理ブロックの通過など）。
    *   `logger.info()`: 通常の操作における重要なイベントの報告（処理の開始・終了、主要なステップの完了など）。
    *   `logger.warning()`: 予期しない事態や、将来問題を引き起こす可能性のある状況（ただし、処理は続行可能）。例えば、特定のファイルの解析失敗など。
    *   `logger.error()`: より深刻な問題。プログラムは処理の実行を継続できない場合が多い。
    *   `logger.critical()`: プログラムの実行を中止せざるを得ない致命的なエラー。

3.  **ログメッセージにはf-stringを使用する**:
    ```python
    # 推奨
    logger.debug(f"Analyzing file: {file_path}")
    
    # 非推奨 (古い %-formatting)
    logger.debug("Analyzing file: %s", file_path)
    ```
    ログレベルが満たされない場合、f-stringの評価自体が行われないため、パフォーマンス上の懸念はほとんどありません。

4.  **例外処理では`exc_info=True`を活用する**:
    `try...except`ブロックで例外を補足してログを記録する際は、`exc_info=True`を使用すると、スタックトレース情報も合わせて記録され、デバッグが容易になります。
    ```python
    try:
        # ... 何らかの処理 ...
    except Exception as e:
        logger.error(f"Analysis failed for project: {project_path}", exc_info=True)
    ```
