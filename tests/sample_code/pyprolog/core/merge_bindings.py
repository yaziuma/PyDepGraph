# pyprolog/core/merge_bindings.py
from pyprolog.util.logger import logger


def merge_bindings(bindings1, bindings2=None):
    """バインディングを結合する（簡素化版）

    Args:
        bindings1: 最初のバインディング（辞書またはBindingEnvironment）
        bindings2: 2番目のバインディング（辞書またはBindingEnvironment、オプション）

    Returns:
        結合されたバインディング辞書またはBindingEnvironment
    """
    from pyprolog.core.binding_environment import BindingEnvironment

    # bindings1がNoneの場合の処理
    if bindings1 is None:
        if bindings2 is None:
            return {}
        return bindings2

    # bindings2がNoneの場合の処理
    if bindings2 is None:
        return bindings1

    # BindingEnvironmentの場合は新しいmerge_withメソッドを使用
    if isinstance(bindings1, BindingEnvironment):
        return bindings1.merge_with(bindings2)

    if isinstance(bindings2, BindingEnvironment):
        return bindings2.merge_with(bindings1)

    # 両方が辞書の場合（従来の動作を維持 + 具体値優先ロジック）
    if isinstance(bindings1, dict) and isinstance(bindings2, dict):
        merged = bindings1.copy()

        for key, value2 in bindings2.items():
            if key in merged:
                value1 = merged[key]
                # 具体値を優先するロジック
                # Variable は pyprolog.core.types からインポートする必要がある
                from pyprolog.core.types import Variable

                if isinstance(value1, Variable) and not isinstance(value2, Variable):
                    merged[key] = value2  # bindings2の具体値を優先
                elif isinstance(value2, Variable) and not isinstance(value1, Variable):
                    # value1（具体値）をそのまま維持
                    pass
                else:
                    # 両方ともVariable、または両方とも具体値の場合はbindings2が優先
                    merged[key] = value2
            else:
                merged[key] = value2

        return merged

    # 片方が辞書の場合
    if isinstance(bindings1, dict):
        env = dict_to_binding_environment(bindings1)
        return env.merge_with(bindings2)

    if isinstance(bindings2, dict):
        env = dict_to_binding_environment(bindings2)
        return bindings1.merge_with(env)

    logger.warning(
        f"merge_bindings: Unexpected types: {type(bindings1)}, {type(bindings2)}"
    )
    return bindings1 if bindings1 is not None else bindings2


def bindings_to_dict(bindings):
    """BindingEnvironmentまたは辞書を辞書形式に変換する

    Args:
        bindings: BindingEnvironmentインスタンスまたは辞書

    Returns:
        dict: バインディング辞書
    """
    from pyprolog.core.binding_environment import BindingEnvironment

    if bindings is None:
        return {}

    if isinstance(bindings, dict):
        return bindings.copy()

    if isinstance(bindings, BindingEnvironment):
        # BindingEnvironmentの新しいto_dictメソッドを使用
        return bindings.to_dict()

    logger.warning(f"bindings_to_dict: Unexpected type: {type(bindings)}")
    return {}


def dict_to_binding_environment(bindings_dict):
    """辞書をBindingEnvironmentに変換する

    Args:
        bindings_dict: バインディング辞書

    Returns:
        BindingEnvironment: 新しいバインディング環境
    """
    from pyprolog.core.binding_environment import BindingEnvironment

    env = BindingEnvironment()

    if bindings_dict:
        for var, value in bindings_dict.items():
            # シンプルなbindメソッドを使用
            env.bind(var, value)

    return env


def unify_with_bindings(term1, term2, bindings=None):
    """2つの項を既存のバインディングに基づいて単一化する

    Args:
        term1: 単一化する項1
        term2: 単一化する項2
        bindings: 既存のバインディング（辞書またはBindingEnvironment、オプション）

    Returns:
        tuple: (成功したかどうか, 更新されたバインディング)
    """
    from pyprolog.core.binding_environment import BindingEnvironment

    # バインディング環境の準備
    if isinstance(bindings, BindingEnvironment):
        env = bindings.copy()
    elif isinstance(bindings, dict):
        env = dict_to_binding_environment(bindings)
    else:
        env = BindingEnvironment()

    # 簡単な単一化を試行
    success = env.unify(term1, term2)

    # 結果を返す（元のバインディングの形式に合わせる）
    if isinstance(bindings, dict):
        return success, env.to_dict()
    else:
        return success, env


def apply_substitution(term, bindings):
    """項にバインディングを適用して置換する

    Args:
        term: 置換する項
        bindings: バインディング（辞書またはBindingEnvironment）

    Returns:
        置換された項
    """
    from pyprolog.core.binding_environment import BindingEnvironment

    if hasattr(term, "substitute"):
        return term.substitute(bindings)

    # BindingEnvironmentの場合の直接処理
    if isinstance(bindings, BindingEnvironment):
        return bindings.get_value(term)

    # 辞書の場合
    if isinstance(bindings, dict) and term in bindings:
        return bindings[term]

    return term
