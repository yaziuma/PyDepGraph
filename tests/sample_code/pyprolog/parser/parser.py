# pyprolog/parser/parser.py
from pyprolog.parser.token import Token
from pyprolog.parser.token_type import TokenType
from pyprolog.core.types import Term, Variable, Atom, Number, String, Rule, Fact
from pyprolog.core.operators import operator_registry, Associativity
from typing import List, Optional, Callable, Union # Added Optional
from pyprolog.util.variable_mapper import VariableMapper # Added VariableMapper
from pyprolog.util.functor_mapper import FunctorMapper # Added FunctorMapper
import logging

logger = logging.getLogger(__name__)


def default_error_handler(token: Token, message: str):
    logger.error(f"Parse error at '{token.lexeme}': {message}")


class Parser:
    """演算子統合設計を活用したパーサー"""

    def __init__(
        self,
        tokens: List[Token],
        error_handler: Callable[[Token, str], None] = default_error_handler,
        variable_mapper: Optional[VariableMapper] = None, # Added variable_mapper
        functor_mapper: Optional[FunctorMapper] = None, # Added functor_mapper
    ):
        self._tokens = tokens
        self._current = 0
        self._error_handler = error_handler
        self._variable_mapper = variable_mapper if variable_mapper is not None else VariableMapper() # Initialize variable_mapper
        self._functor_mapper = functor_mapper # Store functor_mapper
        logger.debug(f"Parser initialized with {len(tokens)} tokens")

    def parse(self) -> List[Union[Rule, Fact]]:
        """プログラム全体を解析"""
        rules = []

        while not self._is_at_end():
            if self._peek_token_type() == TokenType.EOF:
                break

            rule = self._parse_rule()
            if rule:
                rules.append(rule)

            if not self._match(TokenType.DOT):
                if not self._is_at_end():
                    self._error(self._peek(), "Expected '.' after rule or fact")
                break

        logger.info(f"Parsed {len(rules)} rules/facts")
        return rules

    def _parse_rule(self) -> Optional[Union[Rule, Fact]]:
        """ルール解析（統合設計対応版）"""
        # Parse the head term with a precedence just below that of ':-' (1200)
        # This ensures that ':-' is not consumed as part of the head term itself.
        head_term = self._parse_expression_with_precedence(1199)
        if head_term is None:
            return None

        # Termに変換 (Atom以外もTermにラップする)
        if not isinstance(head_term, Term):
            if isinstance(head_term, Atom):
                head_term = Term(head_term, [])
            elif isinstance(head_term, (Number, String, Variable)):
                # Atom以外の型をfunctorとしてTermを作成する場合は、Atomに変換する
                head_term = Term(Atom(str(head_term)), [])
            else:
                # 予期しない型の場合はエラー処理またはNoneを返す
                self._error(
                    self._previous(), f"Unexpected head term type: {type(head_term)}"
                )
                return None

        if self._match(TokenType.COLONMINUS):
            # ルール本体の解析
            body_terms = []
            while not self._check(TokenType.DOT) and not self._is_at_end():
                term = self._parse_term()
                if term is None:
                    return None
                body_terms.append(term)

                if self._match(TokenType.COMMA):
                    continue
                elif self._check(TokenType.DOT):
                    break
                else:
                    self._error(self._peek(), "Expected ',' or '.' in rule body")
                    return None

            if not body_terms:
                self._error(self._peek(), "Rule body cannot be empty")
                return None

            # 統合設計：コンジャンクションも通常の Term として構築
            body = self._build_conjunction(body_terms)
            if isinstance(body, Atom):
                body = Term(body, [])

            return Rule(head_term, body)
        else:
            return Fact(head_term)

    def _build_conjunction(self, terms: List) -> Union[Term, Atom]:
        """項リストからコンジャンクションを構築（統合設計版）"""
        if len(terms) == 1:
            return terms[0]

        # 演算子統合設計：カンマ演算子として構築
        result = terms[-1]
        for i in range(len(terms) - 2, -1, -1):
            # 統合設計：通常の Term として構築
            result = Term(Atom(","), [terms[i], result])

        return result

    def _parse_term(self):
        """項の解析（統合設計：演算子優先度活用）"""
        return self._parse_expression_with_precedence(1200)

    def _parse_expression_with_precedence(self, max_precedence: int):
        """演算子優先度を考慮した式解析（統合設計の核心）"""
        token = self._peek()
        left = None

        # 前置単項演算子の処理 (例: \+)
        # TokenType.NOT が \+ に対応すると仮定 (scanner と operator_registry で設定)
        if token.token_type == TokenType.NOT:  # \+ (not)
            op_symbol = token.lexeme  # Should be "\+"
            # 演算子情報を取得して優先度を確認
            op_info = operator_registry.get_operator(op_symbol, arity=1)
            if not op_info:
                self._error(token, f"Operator information for '{op_symbol}' not found.")
                return None

            # 現在の最大優先度と比較して、この前置演算子を処理すべきか判断
            if (
                op_info.precedence <= max_precedence
            ):  # 通常、前置演算子の優先度は高い(数値が小さい)
                self._advance()  # 演算子トークンを消費
                # オペランドを、この単項演算子の優先度でパース (fy の場合、同じ優先度を許容)
                operand = self._parse_expression_with_precedence(op_info.precedence)
                if operand is None:
                    self._error(
                        self._peek(),
                        f"Expected operand after prefix operator '{op_symbol}'",
                    )
                    return None
                left = Term(Atom(op_symbol), [operand])
            else:  # この前置演算子は現在のコンテキストでは処理されない (優先度が高すぎる)
                left = self._parse_primary()
        else:  # 前置単項演算子で始まらない場合
            left = self._parse_primary()

        if left is None:
            return None  # _parse_primary or operand parsing failed and reported error

        # 後置/二項演算子のループ
        while not self._is_at_end():
            bin_token = self._peek()
            bin_symbol = bin_token.lexeme

            # 二項演算子としての情報を取得 (arity=2)
            # 注意: '-' や '+' のような記号は単項にも二項にもなりうるため、arity指定が重要
            bin_op_info = operator_registry.get_operator(bin_symbol, arity=2)

            if not bin_op_info or bin_op_info.precedence > max_precedence:
                break  # この二項演算子は処理しない (優先度が低いか、ループ終了)

            # 結合性に基づいて次の優先度を計算
            if bin_op_info.associativity == Associativity.LEFT:
                next_max_prec = bin_op_info.precedence - 1
            elif bin_op_info.associativity == Associativity.RIGHT:
                next_max_prec = bin_op_info.precedence
            else:  # NON_ASSOCIATIVE (xfx など)
                next_max_prec = bin_op_info.precedence - 1

            self._advance()  # 二項演算子トークンを消費
            right = self._parse_expression_with_precedence(next_max_prec)
            if right is None:
                self._error(self._peek(), f"Expected right operand for '{bin_symbol}'")
                return None
            left = Term(Atom(bin_symbol), [left, right])

        return left

    def _parse_primary(self):
        """基本要素の解析（引数解析修正版）"""
        if self._match(
            TokenType.ATOM,
            TokenType.ASSERTA,
            TokenType.ASSERTZ,
            TokenType.RETRACT,
            TokenType.FAIL,
            TokenType.TRUE,
        ):  # Added FAIL, TRUE
            # Note: Retract might need different handling if it's to behave like an operator.
            # For now, treat like a standard predicate call.
            token = self._previous()
            atom_name = token.lexeme  # e.g., "asserta", "p", "fail"

            # Convert specific TokenTypes to their canonical atom names for the Term functor
            # This is mainly for asserta, assertz, retract, fail, true if they are parsed with their own TokenTypes
            # For a normal ATOM, atom_name is already correct.
            if token.token_type in [
                TokenType.ASSERTA,
                TokenType.ASSERTZ,
                TokenType.RETRACT,
                TokenType.FAIL,
                TokenType.TRUE,
            ]:
                functor_atom = Atom(
                    atom_name
                )  # Use the keyword itself as functor name (e.g. Atom('fail'))
            else:  # TokenType.ATOM
                functor_atom = Atom(atom_name)

            if self._match(TokenType.LEFTPAREN):
                # 複合項の引数解析
                args = []
                if not self._check(TokenType.RIGHTPAREN):
                    while True:
                        # 引数解析時はコンマ演算子の優先度より高い優先度で解析
                        # コンマの優先度は1000なので、それより低い999を指定
                        arg = self._parse_expression_with_precedence(999)
                        if arg is None:
                            return None
                        args.append(arg)
                        if self._match(TokenType.COMMA):
                            continue
                        break
                self._consume(TokenType.RIGHTPAREN, "Expected ')' after arguments")
                return Term(functor_atom, args)  # Use functor_atom
            else:
                # If it's one of the special predicates but no '(', it's an atom.
                # e.g. query "asserta." should be Atom('asserta')
                return functor_atom  # Use functor_atom

        elif self._match(TokenType.NUMBER):
            return Number(self._previous().literal)

        elif self._match(TokenType.VARIABLE):
            return Variable(self._previous().literal) # Changed lexeme to literal

        elif self._match(TokenType.STRING):  # Handling of single-quoted atoms
            token = self._previous()
            return Atom(token.literal)  # Convert the content within quotes to Atom

        elif self._match(TokenType.DOT):  # Handling when a dot appears alone
            # It's necessary to distinguish if this is the dot for '.'/2 separator or '.' as an atom.
            # If it's difficult to determine from context, treat it as an atom in specific situations (e.g., outside list construction).
            # If this match is called in term arguments, Atom('.') might be acceptable.
            # A safer approach is to treat the DOT token as a special case and
            # check in _parse_term or similar if a . (period) is expected as a Functor.
            # For the current predicate tests, DOT needs to be interpretable as Atom('.').
            # A simple fix is as follows, but be aware of potential context dependency.
            return Atom(".")  # Interpret a standalone . as Atom(".")

        elif self._match(TokenType.LEFTPAREN):
            expr = self._parse_term()
            if expr is None:
                return None
            self._consume(TokenType.RIGHTPAREN, "Expected ')' after expression")
            return expr

        elif self._match(TokenType.LEFTBRACKET):
            return self._parse_list()

        elif self._match(TokenType.CUT):  # Handle CUT token
            return Atom("!")

        self._error(self._peek(), "Expected expression")
        return None

    def _parse_list(self):
        """リストの解析（引数解析修正版）"""
        elements = []
        if not self._check(TokenType.RIGHTBRACKET):
            while True:
                # リスト要素解析時もコンマ演算子の優先度より高い優先度で解析
                # [H|T] の H が | を越えて読み込まないように、優先度を調整
                # 仮に199とする（多くの二項演算子より優先度を低く設定し、BARを演算子として読まないようにする）
                # これにより、リスト要素内で直接演算子を使う場合（例: [X+Y, Z]）に影響が出る可能性がある
                elem = self._parse_expression_with_precedence(199) # 999 から 199 に変更
                if elem is None:
                    return None
                elements.append(elem)
                if self._match(TokenType.COMMA):
                    continue
                break

        tail = None
        if self._match(TokenType.BAR):
            # リストの尾部も同様に解析
            tail = self._parse_expression_with_precedence(999)
            if tail is None:
                return None

        self._consume(TokenType.RIGHTBRACKET, "Expected ']' after list")

        # リストを内部表現に変換
        # elements が空で、tail が指定されている場合 (例: [|T]) は tail そのもの。
        # tail が指定されていない場合 (例: []) は Atom("[]")。
        # tail が指定されておらず elements も空の場合 (例: []) は Atom("[]")。
        if not elements:
            return tail if tail is not None else Atom("[]")

        # elements が存在する場合
        # tail が BAR によって設定されていなければ、デフォルトの tail は Atom("[]")
        current_tail = tail if tail is not None else Atom("[]")

        # elements を逆順に処理して '.'/2 の入れ子構造を作る
        # ループの最初の result の初期値は current_tail
        result = current_tail
        for element in reversed(elements):
            result = Term(Atom("."), [element, result])
        return result

    # ユーティリティメソッド
    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()

        self._error(self._peek(), message)
        return Token(token_type, "", None, 0)  # ダミートークン

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek_token_type() == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek_token_type() == TokenType.EOF

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _peek_token_type(self) -> TokenType:
        token = self._peek()
        return getattr(token, "token_type", TokenType.EOF)

    def _error(self, token: Token, message: str):
        self._error_handler(token, message)
