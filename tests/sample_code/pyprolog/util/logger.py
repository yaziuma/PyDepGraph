"""ログ設定とロガー管理モジュール

環境に応じたログ設定の自動切り替えを提供します。
設定ファイル（.conf）ベースでログ設定を管理します。
"""

import logging
from typing import Optional

from .logging_config import load_logging_config, detect_environment, get_config_info


# グローバルな初期化フラグ
_initialized = False
_current_environment = None


def setup_logging(
    environment: Optional[str] = None, force_reinit: bool = False
) -> None:
    """ログシステムを初期化します。

    Args:
        environment: 環境名（'production', 'test', 'debug'）。
                    Noneの場合は自動検出します。
        force_reinit: 既に初期化済みでも強制的に再初期化するかどうか。
    """
    global _initialized, _current_environment

    if _initialized and not force_reinit:
        return

    # 環境の検出または指定
    if environment is None:
        environment = detect_environment()

    # ログ設定の読み込みと適用
    load_logging_config(environment)

    _initialized = True
    _current_environment = environment

    # 初期化完了のログ出力
    logger = logging.getLogger("prolog.util.logger")
    logger.info(f"ログシステムを初期化しました (環境: {environment})")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """ロガーを取得します。

    Args:
        name: ロガー名。Noneの場合は"prolog"を使用します。

    Returns:
        設定済みのロガーインスタンス。
    """
    # まだ初期化されていない場合は自動初期化
    if not _initialized:
        setup_logging()

    if name is None:
        name = "prolog"
    elif not name.startswith("prolog."):
        name = f"prolog.{name}"

    return logging.getLogger(name)


def setup_logger(name: str = "prolog") -> logging.Logger:
    """レガシー互換性のためのロガー設定関数。

    Args:
        name: ロガー名。

    Returns:
        設定済みのロガーインスタンス。

    Note:
        この関数は後方互換性のために残されています。
        新しいコードでは get_logger() を使用してください。
    """
    return get_logger(name)


# 自動初期化とデフォルトロガーの作成
setup_logging()
logger = get_logger()


# 環境切り替え用のユーティリティ関数
def switch_to_test_mode() -> None:
    """テストモードに切り替えます。"""
    setup_logging("test", force_reinit=True)


def switch_to_debug_mode() -> None:
    """デバッグモードに切り替えます。"""
    setup_logging("debug", force_reinit=True)


def switch_to_production_mode() -> None:
    """本番モードに切り替えます。"""
    setup_logging("production", force_reinit=True)


def get_current_environment() -> str:
    """現在のログ環境を取得します。"""
    if _current_environment is not None:
        return _current_environment
    return detect_environment()


def get_logging_info() -> dict:
    """現在のログ設定情報を取得します。

    Returns:
        ログ設定情報の辞書
    """
    current_env = get_current_environment()
    config_info = get_config_info(current_env)

    return {
        "initialized": _initialized,
        "current_environment": current_env,
        "config_info": config_info,
        "loggers": {
            "root": {
                "level": logging.getLogger().level,
                "handlers": len(logging.getLogger().handlers),
            },
            "prolog": {
                "level": logging.getLogger("prolog").level,
                "handlers": len(logging.getLogger("prolog").handlers),
            },
        },
    }


def reset_logging() -> None:
    """ログ設定をリセットします。

    Note:
        テスト用途でのみ使用してください。
    """
    global _initialized, _current_environment

    # 既存のハンドラを削除
    for logger_name in logging.Logger.manager.loggerDict:
        logger_obj = logging.getLogger(logger_name)
        for handler in logger_obj.handlers[:]:
            logger_obj.removeHandler(handler)

    # ルートロガーのハンドラも削除
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    _initialized = False
    _current_environment = None
