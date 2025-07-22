# pyprolog/parser/token_type.py
from enum import Enum
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """動的に拡張可能なトークンタイプ"""

    # 基本トークン
    ATOM = "ATOM"
    VARIABLE = "VARIABLE"
    NUMBER = "NUMBER"
    STRING = "STRING"

    # 区切り文字
    LEFTPAREN = "LEFTPAREN"
    RIGHTPAREN = "RIGHTPAREN"
    LEFTBRACKET = "LEFTBRACKET"
    RIGHTBRACKET = "RIGHTBRACKET"
    COMMA = "COMMA"
    DOT = "DOT"
    BAR = "BAR"

    # 制御構造
    COLONMINUS = "COLONMINUS"  # :-
    UNDERSCORE = "UNDERSCORE"  # _

    # 特殊述語
    TRUE = "TRUE"
    FAIL = "FAIL"
    RETRACT = "RETRACT"
    ASSERTA = "ASSERTA"
    ASSERTZ = "ASSERTZ"

    CUT = "CUT"  # ! 演算子

    EOF = "EOF"


class TokenTypeManager:
    """TokenTypeの動的管理クラス"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._dynamic_tokens: Dict[str, Any] = {}
        self._initialized = True

    def ensure_operator_tokens(self):
        """演算子トークンの動的生成を保証"""
        # 遅延インポートで循環参照回避
        from pyprolog.core.operators import operator_registry

        for symbol, op_info in operator_registry._operators.items():
            token_name = op_info.token_type
            if not hasattr(TokenType, token_name):
                # 動的にトークンタイプを追加
                setattr(TokenType, token_name, token_name)
                self._dynamic_tokens[token_name] = token_name

                # Enumの内部構造も更新
                TokenType._member_map_[token_name] = getattr(TokenType, token_name)
                TokenType._value2member_map_[token_name] = getattr(
                    TokenType, token_name
                )

                logger.debug(f"Added dynamic token: {token_name}")

        logger.info(f"Ensured {len(self._dynamic_tokens)} dynamic operator tokens")

    def get_token_type(self, name: str):
        """トークンタイプを取得（存在しない場合は作成）"""
        if hasattr(TokenType, name):
            return getattr(TokenType, name)

        # 動的作成
        setattr(TokenType, name, name)
        self._dynamic_tokens[name] = name
        TokenType._member_map_[name] = getattr(TokenType, name)
        TokenType._value2member_map_[name] = getattr(TokenType, name)

        logger.debug(f"Dynamically created token: {name}")
        return getattr(TokenType, name)


# グローバルマネージャー
token_type_manager = TokenTypeManager()


def ensure_operator_tokens():
    """演算子トークンの初期化（外部から呼び出し可能）"""
    token_type_manager.ensure_operator_tokens()
