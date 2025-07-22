# pyprolog/core/operators.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class OperatorType(Enum):
    """演算子の種類"""

    ARITHMETIC = auto()  # 算術演算子 (+, -, *, /, mod, etc.)
    COMPARISON = auto()  # 比較演算子 (=:=, =\=, >, <, etc.)
    LOGICAL = auto()  # 論理演算子 (=, \=, ==, \==)
    STRUCTURAL = auto()  # 構造演算子 (=.., functor, etc.)
    CONTROL = auto()  # 制御演算子 (!, cut)
    IO = auto()  # 入出力演算子 (write, nl, etc.)


class Associativity(Enum):
    """結合性"""

    LEFT = auto()
    RIGHT = auto()
    NON = auto()


@dataclass
class OperatorInfo:
    """演算子情報"""

    symbol: str  # 演算子記号
    precedence: int  # 優先度 (低い数値 = 高い優先度)
    associativity: Associativity  # 結合性
    operator_type: OperatorType  # 演算子種別
    arity: int  # アリティ (1=単項, 2=二項)
    evaluator: Optional[Callable]  # 評価関数
    token_type: str  # 対応するTokenType名（必須）

    def __post_init__(self):
        """初期化後の検証"""
        if not self.token_type:
            raise ValueError(f"Operator {self.symbol} must have token_type")
        if self.precedence < 1 or self.precedence > 1200:
            raise ValueError(
                f"Operator precedence must be between 1-1200, got {self.precedence}"
            )


class OperatorRegistry:
    """演算子レジストリ - 全演算子を一元管理"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """シングルトンパターンで実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._operators: Dict[str, OperatorInfo] = {}
        self._precedence_groups: Dict[int, List[OperatorInfo]] = {}
        self._type_groups: Dict[OperatorType, List[OperatorInfo]] = {}
        self._token_type_map: Dict[str, str] = {}  # symbol -> token_type

        self._initialize_builtin_operators()
        self._initialized = True
        logger.info(
            f"OperatorRegistry initialized with {len(self._operators)} operators"
        )

    def _initialize_builtin_operators(self):
        """組み込み演算子の初期化（単項演算子対応版）"""
        builtin_ops = [
            # 算術演算子 (優先度: ISO Prolog準拠)
            OperatorInfo(
                "**",
                200,
                Associativity.RIGHT,
                OperatorType.ARITHMETIC,
                2,
                None,  # TokenType は register_operator で設定される想定、または不要
                "POWER",
            ),
            # 単項演算子を先に定義（高い優先度）
            OperatorInfo(
                "-",
                200,
                Associativity.NON,
                OperatorType.ARITHMETIC,
                1,
                None,
                "UNARY_MINUS",
            ),
            OperatorInfo(
                "+",
                200,
                Associativity.NON,
                OperatorType.ARITHMETIC,
                1,
                None,
                "UNARY_PLUS",
            ),
            OperatorInfo(
                "~", 200, Associativity.NON, OperatorType.ARITHMETIC, 1, None, "BITWISE_NOT"
            ),
            # ビット単位シフト演算子
            OperatorInfo(
                "<<", 300, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "LSHIFT"
            ),
            OperatorInfo(
                ">>", 300, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "RSHIFT"
            ),
            # 二項算術演算子 (ビット単位 AND, OR, XOR を追加)
            OperatorInfo(
                "&", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "BITWISE_AND"
            ),
            OperatorInfo(
                "|", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "BITWISE_OR"
            ),
            OperatorInfo(
                "^", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "BITWISE_XOR"
            ),
            OperatorInfo(
                "*", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "STAR"
            ),
            OperatorInfo(
                "/", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "SLASH"
            ),
            OperatorInfo(
                "//", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "DIV"
            ),
            OperatorInfo(
                "mod", 400, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "MOD"
            ),
            OperatorInfo(
                "+", 500, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "PLUS"
            ),
            OperatorInfo(
                "-", 500, Associativity.LEFT, OperatorType.ARITHMETIC, 2, None, "MINUS"
            ),
            # 比較演算子 (token_type は None のまま、name を調整)
            OperatorInfo(
                "=:=",
                700,
                Associativity.NON,
                OperatorType.COMPARISON,
                2,
                None,
                "ARITH_EQ",  # 指示書では ARITH_EQUAL だが既存に合わせる
            ),
            OperatorInfo(
                "=\\=",
                700,
                Associativity.NON,
                OperatorType.COMPARISON,
                2,
                None,
                "ARITH_NEQ",  # 指示書では ARITH_NOT_EQUAL だが既存に合わせる
            ),
            OperatorInfo(
                "<", 700, Associativity.NON, OperatorType.COMPARISON, 2, None, "LESS"
            ),
            OperatorInfo(
                "=<",
                700,
                Associativity.NON,
                OperatorType.COMPARISON,
                2,
                None,
                "LESS_EQ",  # 指示書では LESS_EQUAL だが既存に合わせる
            ),
            OperatorInfo(
                ">", 700, Associativity.NON, OperatorType.COMPARISON, 2, None, "GREATER"
            ),
            OperatorInfo(
                ">=",
                700,
                Associativity.NON,
                OperatorType.COMPARISON,
                2,
                None,
                "GREATER_EQ",  # 指示書では GREATER_EQUAL だが既存に合わせる
            ),
            # 論理演算子 (token_type は None のまま、name を調整)
            OperatorInfo(  # 単一化演算子
                "=",
                700,
                Associativity.NON,
                OperatorType.LOGICAL,
                2,
                None,
                "UNIFY",  # 指示書では EQUAL
            ),
            OperatorInfo(
                "==", 700, Associativity.NON, OperatorType.LOGICAL, 2, None, "IDENTICAL"
            ),
            OperatorInfo(
                "\\==",
                700,
                Associativity.NON,
                OperatorType.LOGICAL,
                2,
                None,
                "NOT_IDENTICAL",
            ),
            # 論理制御演算子（コンジャンクション・ディスジャンクション）
            OperatorInfo(  # Conjunction (and)
                ",",
                1000,
                Associativity.RIGHT,
                OperatorType.LOGICAL,
                2,
                None,
                "COMMA",  # 指示書では CONJUNCTION
            ),
            OperatorInfo(  # Disjunction (or)
                ";",
                1100,
                Associativity.RIGHT,  # 指示書では LEFT
                OperatorType.LOGICAL,
                2,
                None,
                "SEMICOLON",  # 指示書では DISJUNCTION
            ),
            OperatorInfo(  # If-then
                "->",
                1050,
                Associativity.RIGHT,  # 指示書では LEFT
                OperatorType.CONTROL,
                2,
                None,
                "IF_THEN",
            ),
            # 否定演算子
            OperatorInfo(  # NOT
                "\\+", 900, Associativity.NON, OperatorType.LOGICAL, 1, None, "NOT"
            ),
            OperatorInfo(
                "\\=",
                700,
                Associativity.NON,
                OperatorType.LOGICAL,
                2,
                None,
                "NON_UNIFIABLE_OPERATOR",
            ),
            # 代替非等価演算子（統一記法）
            OperatorInfo(
                "<>",
                700,
                Associativity.NON,
                OperatorType.LOGICAL,
                2,
                None,
                "NOT_EQUAL",
            ),
            OperatorInfo(
                "!=",
                700,
                Associativity.NON,
                OperatorType.LOGICAL,
                2,
                None,
                "NOT_EQUAL_ALT",
            ),
            # Univ演算子
            OperatorInfo(
                "=..",
                700,
                Associativity.NON,
                OperatorType.STRUCTURAL,
                2,
                None,
                "UNIV",  # xfx
            ),
            # 特殊演算子
            OperatorInfo(  # 'is'/2 は評価演算子
                "is",
                700,
                Associativity.NON,
                OperatorType.ARITHMETIC,
                2,
                None,
                "IS",  # 指示書では EVALUATION
            ),
            OperatorInfo(
                "!", 200, Associativity.NON, OperatorType.CONTROL, 0, None, "CUT"
            ),
            # Rule operator :-
            OperatorInfo(
                ":-",
                1200,
                Associativity.NON,  # Typically xfx
                OperatorType.LOGICAL,  # Or a specific type for rules
                2,
                None,
                "RULE_OPERATOR",  # Scanner will generate COLONMINUS
            ),
            # IO演算子
            OperatorInfo(
                "write", 1, Associativity.NON, OperatorType.IO, 1, None, "WRITE"
            ),
            OperatorInfo("nl", 1, Associativity.NON, OperatorType.IO, 0, None, "NL"),
            OperatorInfo("tab", 1, Associativity.NON, OperatorType.IO, 1, None, "TAB"),
        ]

        for op in builtin_ops:
            self.register_operator(op)

    def register_operator(self, operator_info: OperatorInfo):
        """演算子を登録（重複対応版）"""
        logger.debug(f"Registering operator: {operator_info.symbol}")

        # 同じ記号で異なるarityの演算子をサポート
        key = f"{operator_info.symbol}_{operator_info.arity}"
        self._operators[key] = operator_info

        # 後方互換性のため、記号のみのキーも保持（最後に登録されたものが優先）
        self._operators[operator_info.symbol] = operator_info

        # TokenType が None でない場合のみ token_type_map に登録
        if operator_info.token_type is not None:
            self._token_type_map[operator_info.symbol] = operator_info.token_type
        elif operator_info.symbol not in self._token_type_map:
            # TokenType が None で、かつシンボルがまだマップにない場合、
            # プレースホルダーやデフォルト値を設定するか、エラーを出すか検討。
            # ここでは、既存の動作になるべく影響を与えないよう、何もしないか、
            # シンボル名をそのまま使うなどの対応が考えられる。
            # 指示書では TokenType が None の場合があるので、エラーにしない。
            # 必要であれば、ここでデフォルトのトークンタイプ名を設定。
            # 例: self._token_type_map[operator_info.symbol] = operator_info.symbol.upper()
            pass

        # 優先度グループに追加
        if operator_info.precedence not in self._precedence_groups:
            self._precedence_groups[operator_info.precedence] = []
        self._precedence_groups[operator_info.precedence].append(operator_info)

        # 種別グループに追加
        if operator_info.operator_type not in self._type_groups:
            self._type_groups[operator_info.operator_type] = []
        self._type_groups[operator_info.operator_type].append(operator_info)

    def get_operator_by_arity(self, symbol: str, arity: int) -> Optional[OperatorInfo]:
        """指定されたarityの演算子情報を取得"""
        key = f"{symbol}_{arity}"
        return self._operators.get(key, self._operators.get(symbol))

    def get_operator(
        self, symbol: str, arity: Optional[int] = None
    ) -> Optional[OperatorInfo]:
        """演算子情報を取得（arity指定対応）"""
        if arity is not None:
            return self.get_operator_by_arity(symbol, arity)
        return self._operators.get(symbol)

    def get_operators_by_type(self, op_type: OperatorType) -> List[OperatorInfo]:
        """指定タイプの演算子一覧を取得"""
        return self._type_groups.get(op_type, [])

    def get_operators_by_precedence(self, precedence: int) -> List[OperatorInfo]:
        """指定優先度の演算子一覧を取得"""
        return self._precedence_groups.get(precedence, [])

    def is_operator(self, symbol: str) -> bool:
        """指定文字列が演算子かどうか判定"""
        return symbol in self._operators

    def get_precedence(self, symbol: str) -> Optional[int]:
        """演算子の優先度を取得"""
        op = self.get_operator(symbol)
        return op.precedence if op else None

    def get_token_type(self, symbol: str) -> Optional[str]:
        """演算子のトークンタイプを取得"""
        return self._token_type_map.get(symbol)

    def get_all_symbols(self) -> List[str]:
        """全演算子記号を取得（長さ順でソート）"""
        return sorted(self._operators.keys(), key=len, reverse=True)

    def add_user_operator(
        self,
        symbol: str,
        precedence: int,
        associativity: Associativity,
        op_type: OperatorType,
        arity: int,
        evaluator: Optional[Callable] = None,
    ):
        """ユーザー定義演算子を追加"""
        processed_symbol = (
            symbol.upper()
            .replace(" ", "_")
            .replace("/", "_SLASH_")
            .replace("\\\\", "_BACKSLASH_")
        )
        token_type = f"USER_{processed_symbol}"
        op_info = OperatorInfo(
            symbol, precedence, associativity, op_type, arity, evaluator, token_type
        )
        self.register_operator(op_info)
        logger.info(f"Added user operator: {symbol}")


# グローバルインスタンス（シングルトン）
operator_registry = OperatorRegistry()
