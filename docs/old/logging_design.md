
自分のライブラリでロギングを実装する際の一般的なプラクティスは、非常にシンプルですが重要です。

-----

### ライブラリ実装におけるロギングの基本

ライブラリ内部でログを出力する場合、以下の点が最も重要です。

1.  **専用のロガーインスタンスを取得する**
2.  **ログレベルを設定しない**
3.  **ハンドラやフォーマッタを追加しない**

順に見ていきましょう。

#### 1\. 専用のロガーインスタンスを取得する

各モジュールで、`logging.getLogger(__name__)` を使ってロガーインスタンスを取得します。これにより、ライブラリの利用側（アプリケーション）が、そのライブラリの特定のモジュールからのログを制御しやすくなります。

```python
# my_library/module_a.py

import logging

# このモジュール専用のロガーを取得
# __name__ はPythonがモジュールのパスに基づいて自動的に設定する
# 例: 'my_library.module_a'
logger = logging.getLogger(__name__)

def do_something_useful():
    logger.debug("Debug message from module_a")
    logger.info("Doing something useful in module_a...")
    try:
        result = 10 / 0 # 例外を発生させる
    except ZeroDivisionError:
        logger.error("An error occurred: Division by zero!", exc_info=True) # exc_info=True でスタックトレースも出力
    return "Done"

```

```python
# my_library/module_b.py

import logging

logger = logging.getLogger(__name__)

def another_function(data):
    if not data:
        logger.warning("Input data is empty in module_b.")
        return None
    logger.info(f"Processing data: {data}")
    return len(data)

```

#### 2\. ログレベルを設定しない

ライブラリのコード内でロガーの**レベル（`logger.setLevel(...)`）を設定してはいけません**。なぜなら、ログレベルはライブラリを利用する側のアプリケーションが決定すべきことだからです。

もしライブラリ側で `logger.setLevel(logging.INFO)` のように設定してしまうと、アプリケーション側がたとえデバッグ目的で `DEBUG` レベルのログを見たい場合でも、ライブラリが出力する `DEBUG` メッセージは表示されなくなってしまいます。

ライブラリは、あくまで\*\*可能な限り詳細な情報（`DEBUG`レベルから`CRITICAL`レベルまで）をログとして出力する「能力」\*\*を提供するに留めるべきです。どのレベルのログを実際に表示するかは、利用者に委ねます。

#### 3\. ハンドラやフォーマッタを追加しない

同様に、ライブラリのコード内でロガーに**ハンドラ（`logger.addHandler(...)`）やフォーマッタ（`handler.setFormatter(...)`）を追加してはいけません**。

もしライブラリが勝手にコンソールに出力するハンドラを追加してしまうと、ライブラリをインポートするだけで利用者のコンソールに意図しないログが出力されたり、複数のライブラリがそれぞれハンドラを追加してログが重複して出力されたりする可能性があります。これは非常に迷惑です。

ログの出力先（コンソール、ファイルなど）やフォーマットも、完全に**ライブラリの利用側（アプリケーション）が制御すべき**部分です。

-----

### ライブラリ利用時のロギング動作

上記のルールに従ってライブラリを実装すると、ライブラリのログは以下のように動作します。

  * **アプリケーションがログ設定をしていない場合:**

      * Pythonの`logging`モジュールは、**デフォルトで`WARNING`以上のログをコンソールに出力**します（ただし、ルートロガーにハンドラが設定されていない場合）。
      * ライブラリが出力する`INFO`や`DEBUG`レベルのログは、デフォルトでは**どこにも出力されません**。これは、ライブラリとしては正しい挙動です。不必要に詳細なログを利用者に押し付けないためです。

  * **アプリケーションがログ設定をしている場合:**

      * アプリケーション側で`logging.basicConfig()`や`logging.config.dictConfig()`などを使ってロガー、ハンドラ、フォーマッタを設定すると、**ライブラリが出力するログもその設定に従って適切に処理されます**。
      * 例えば、アプリケーションが`my_library`ロガーのレベルを`DEBUG`に設定し、ファイルハンドラを追加すれば、`my_library`からのデバッグログもファイルに出力されるようになります。

    <!-- end list -->

    ```python
    # アプリケーション側のコード (例: main.py)

    import logging
    import logging.config

    # ライブラリからのログも拾えるように dictConfig で詳細に設定
    LOGGING_CONFIG = {
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': 'INFO', # アプリケーションのコンソールはINFOから
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': 'app_debug.log',
                'formatter': 'standard',
                'level': 'DEBUG', # ファイルにはDEBUGまで出力
            },
        },
        'loggers': {
            'my_library': { # ここでライブラリのロガーを指定
                'handlers': ['console', 'file'],
                'level': 'DEBUG', # my_libraryからのログはDEBUGレベルから扱う
                'propagate': False,
            },
            '': { # ルートロガー
                'handlers': ['console'],
                'level': 'WARNING',
            }
        }
    }

    logging.config.dictConfig(LOGGING_CONFIG)

    # ここで自分のライブラリをインポートして利用
    from my_library import module_a, module_b

    module_a.do_something_useful()
    module_b.another_function("some_data")
    module_b.another_function("") # 警告メッセージが出力される
    ```

-----

### まとめ

ライブラリを実装する際には、ロギングは「**メッセージを発行するだけ**」にとどめ、そのメッセージを「**どこに、どのような形式で、どのレベルから出力するか**」という設定は、**完全にライブラリの利用者（アプリケーション開発者）に委ねる**のが、Pythonにおけるロギングのベストプラクティスです。

これは、多くの人気のあるPythonライブラリ（`requests`, `Django`, `Flask`など）が採用しているアプローチでもあります。

