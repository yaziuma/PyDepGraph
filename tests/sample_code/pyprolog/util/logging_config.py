import os
import sys
import logging.config
from pathlib import Path
from typing import Optional, List, Dict, Any


def get_config_file_path(environment: str) -> Optional[Path]:
    """指定された環境の設定ファイルパスを取得します。"""
    # パッケージインストール時のパス解決を改善
    current_file = Path(__file__)
    config_dir = current_file.parent.parent / "config" / "logging"
    config_file = config_dir / f"{environment}.conf"

    if not config_file.exists():
        # フォールバック: リソースとしてアクセスを試行
        try:
            import importlib.resources as resources

            # Python 3.9+
            with resources.path(
                "pyprolog.config.logging", f"{environment}.conf"
            ) as path:
                if path.exists():
                    return path
        except (ImportError, AttributeError, FileNotFoundError):
            pass

        # 最終フォールバック: プログラム的設定を使用
        setup_programmatic_logging(environment)
        return None

    return config_file


def setup_programmatic_logging(environment: str) -> None:
    """設定ファイルが見つからない場合のプログラム的ログ設定"""

    # 環境別設定
    config_map = {
        "production": {"level": logging.INFO, "console_level": logging.INFO},
        "debug": {"level": logging.DEBUG, "console_level": logging.DEBUG},
        "test": {"level": logging.WARNING, "console_level": logging.WARNING},
    }

    config = config_map.get(environment, config_map["production"])

    # ログディレクトリ作成
    try:
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(exist_ok=True)
    except PermissionError:
        log_dir = None

    # ロガー設定
    logging.basicConfig(
        level=config["level"],
        format="[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソールハンドラ調整
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers[0].setLevel(config["console_level"])

    # PyProlog専用ロガー
    prolog_logger = logging.getLogger("prolog")
    prolog_logger.setLevel(config["level"])


def setup_logs_directory():
    """ログディレクトリを作成します。"""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)


def detect_environment() -> str:
    """実行環境を自動検出します。

    Returns:
        環境名（'test', 'debug', 'production'）
    """
    # pytest実行中の検出
    if "PYTEST_CURRENT_TEST" in os.environ:
        return "test"

    # unittest実行中の検出
    if any("unittest" in arg for arg in sys.argv if arg):
        return "test"

    # デバッグモードの検出
    if os.environ.get("PROLOG_DEBUG", "").lower() in ("1", "true", "yes"):
        return "debug"

    # 開発環境の検出
    if os.environ.get("PROLOG_ENV", "").lower() == "development":
        return "debug"

    # デフォルトは本番環境
    return "production"


def load_logging_config(environment: str) -> None:
    """指定された環境のログ設定を読み込みます。"""
    valid_environments = {"production", "test", "debug"}
    if environment not in valid_environments:
        raise ValueError(
            f"未知の環境: {environment}. 使用可能な環境: {valid_environments}"
        )

    try:
        # ログディレクトリを作成
        setup_logs_directory()

        # 設定ファイルを読み込み
        config_file = get_config_file_path(environment)
        if config_file and config_file.exists():
            logging.config.fileConfig(config_file, disable_existing_loggers=False)
        # else: setup_programmatic_logging は get_config_file_path 内で既に呼ばれている

    except Exception as e:
        # 全てが失敗した場合の最終フォールバック
        print(
            f"警告: ログ設定の読み込みに失敗しました ({e})。デフォルト設定を使用します。"
        )
        setup_programmatic_logging(environment)


def get_available_environments() -> List[str]:
    """利用可能な環境一覧を取得します。

    Returns:
        利用可能な環境名のリスト
    """
    try:
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        config_dir = project_root / "config" / "logging"

        if not config_dir.exists():
            return []

        environments = []
        for config_file in config_dir.glob("*.conf"):
            environments.append(config_file.stem)

        return sorted(environments)
    except Exception:
        return ["production", "test", "debug"]  # フォールバック


def validate_config_files() -> Dict[str, bool]:
    """すべての設定ファイルの存在を確認します。

    Returns:
        環境名と存在確認結果の辞書
    """
    environments = ["production", "test", "debug"]
    results = {}

    for env in environments:
        try:
            config_file = get_config_file_path(env)
            results[env] = config_file and config_file.exists()
        except Exception:
            results[env] = False

    return results


def get_config_info(environment: str) -> Dict[str, Any]:
    """指定された環境の設定情報を取得します。

    Args:
        environment: 環境名

    Returns:
        設定情報の辞書
    """
    try:
        config_file = get_config_file_path(environment)
        if config_file:
            return {
                "environment": environment,
                "config_file": str(config_file),
                "exists": config_file.exists(),
                "size": config_file.stat().st_size if config_file.exists() else 0,
                "modified": config_file.stat().st_mtime
                if config_file.exists()
                else None,
            }
        else:
            return {
                "environment": environment,
                "config_file": None,
                "exists": False,
                "programmatic": True,
            }
    except Exception as e:
        return {
            "environment": environment,
            "config_file": None,
            "exists": False,
            "error": str(e),
        }
