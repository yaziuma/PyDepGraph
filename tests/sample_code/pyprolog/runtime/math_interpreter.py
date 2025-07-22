# pyprolog/runtime/math_interpreter.py
from pyprolog.core.types import Term, Variable, Number, Atom, PrologType
from pyprolog.core.binding_environment import BindingEnvironment
from pyprolog.core.errors import PrologError
from pyprolog.core.operators import operator_registry, OperatorType
from typing import Union, List
import logging

logger = logging.getLogger(__name__)


class MathInterpreter:
    """統合設計を活用した数学的評価エンジン"""

    def __init__(self):
        logger.debug("MathInterpreter initialized")

    def evaluate(
        self, expression: PrologType, env: BindingEnvironment
    ) -> Union[int, float]:
        """統合設計：演算子レジストリを活用した式評価"""

        if isinstance(expression, Number):
            return expression.value

        if isinstance(expression, Variable):
            value = env.get_value(expression.name)
            if value is None:
                raise PrologError(f"Variable {expression.name} is not instantiated")

            # 再帰的評価
            return self.evaluate(value, env)

        if isinstance(expression, Atom):
            # アトムを数値として解釈を試行
            try:
                return float(expression.name)
            except ValueError:
                raise PrologError(f"Cannot evaluate atom '{expression.name}' as number")

        if isinstance(expression, Term):
            functor_name = expression.functor.name
            arity = len(expression.args)

            # 統合設計：operator_registry で演算子判定 (アリティを指定)
            op_info = operator_registry.get_operator(functor_name, arity)

            if op_info and op_info.operator_type == OperatorType.ARITHMETIC:
                if op_info.arity == 2 and arity == 2:  # アリティチェックを明示的に
                    left_val = self.evaluate(expression.args[0], env)
                    right_val = self.evaluate(expression.args[1], env)
                    return self.evaluate_binary_op(functor_name, left_val, right_val)
                elif op_info.arity == 1 and len(expression.args) == 1:
                    operand_val = self.evaluate(expression.args[0], env)
                    return self.evaluate_unary_op(functor_name, operand_val)
                else:
                    raise PrologError(
                        f"Arity mismatch for operator {functor_name}: expected {op_info.arity}, got {len(expression.args)}"
                    )
            else:
                # 関数として評価（例：abs/1, max/2 など）
                return self._evaluate_function(functor_name, expression.args, env)

        raise PrologError(f"Cannot evaluate expression: {expression}")

    def evaluate_binary_op(
        self, op_symbol: str, left_val: Union[int, float], right_val: Union[int, float]
    ) -> Union[int, float]:
        """統合設計：バイナリ演算子の評価"""

        if not isinstance(left_val, (int, float)) or not isinstance(
            right_val, (int, float)
        ):
            raise PrologError(
                f"Arithmetic operation requires numeric arguments: {left_val}, {right_val}"
            )

        # 統合設計：operator_registry から演算子情報を取得
        op_info = operator_registry.get_operator(op_symbol)
        if not op_info:
            raise PrologError(f"Unknown arithmetic operator: {op_symbol}")

        try:
            if op_symbol == "+":
                return left_val + right_val
            elif op_symbol == "-":
                return left_val - right_val
            elif op_symbol == "*":
                return left_val * right_val
            elif op_symbol == "/":
                if right_val == 0:
                    raise PrologError("Division by zero")
                return left_val / right_val
            elif op_symbol == "//":
                if right_val == 0:
                    raise PrologError("Integer division by zero")
                return int(left_val // right_val)
            elif op_symbol == "**":
                return left_val**right_val
            elif op_symbol == "mod":
                if right_val == 0:
                    raise PrologError("Modulo by zero")
                return left_val % right_val
            elif op_symbol == "&":
                return int(left_val) & int(right_val)
            elif op_symbol == "|":
                return int(left_val) | int(right_val)
            elif op_symbol == "^":
                return int(left_val) ^ int(right_val)
            elif op_symbol == "<<":
                return int(left_val) << int(right_val)
            elif op_symbol == ">>":
                return int(left_val) >> int(right_val)
            else:
                raise PrologError(
                    f"Unsupported binary arithmetic operator: {op_symbol}"
                )

        except Exception as e:
            raise PrologError(f"Arithmetic error in {op_symbol}: {e}")

    def evaluate_unary_op(
        self, op_symbol: str, operand_val: Union[int, float]
    ) -> Union[int, float]:
        """単項演算子の評価"""

        if not isinstance(operand_val, (int, float)):
            raise PrologError(
                f"Unary arithmetic operation requires numeric argument: {operand_val}"
            )

        if op_symbol == "-":
            return -operand_val
        elif op_symbol == "+":
            return operand_val
        elif op_symbol == "abs":
            return abs(operand_val)
        elif op_symbol == "~":
            return ~int(operand_val)
        else:
            raise PrologError(f"Unknown unary arithmetic operator: {op_symbol}")

    def evaluate_comparison_op(
        self, op_symbol: str, left_val: Union[int, float], right_val: Union[int, float]
    ) -> bool:
        """統合設計：比較演算子の評価"""

        if not isinstance(left_val, (int, float)) or not isinstance(
            right_val, (int, float)
        ):
            raise PrologError(
                f"Comparison requires numeric arguments: {left_val}, {right_val}"
            )

        # 統合設計：operator_registry から演算子情報を取得
        op_info = operator_registry.get_operator(op_symbol)
        if not op_info or op_info.operator_type != OperatorType.COMPARISON:
            raise PrologError(f"Unknown comparison operator: {op_symbol}")

        if op_symbol == "=:=":
            return left_val == right_val
        elif op_symbol == "=\\=":
            return left_val != right_val
        elif op_symbol == "<":
            return left_val < right_val
        elif op_symbol == "=<":
            return left_val <= right_val
        elif op_symbol == ">":
            return left_val > right_val
        elif op_symbol == ">=":
            return left_val >= right_val
        else:
            raise PrologError(f"Unsupported comparison operator: {op_symbol}")

    def _evaluate_function(
        self, func_name: str, args: List[PrologType], env: BindingEnvironment
    ) -> Union[int, float]:
        """数学関数の評価（拡張可能）"""

        if func_name == "abs" and len(args) == 1:
            val = self.evaluate(args[0], env)
            return abs(val)
        elif func_name == "max" and len(args) == 2:
            val1 = self.evaluate(args[0], env)
            val2 = self.evaluate(args[1], env)
            return max(val1, val2)
        elif func_name == "min" and len(args) == 2:
            val1 = self.evaluate(args[0], env)
            val2 = self.evaluate(args[1], env)
            return min(val1, val2)
        else:
            raise PrologError(f"Unknown mathematical function: {func_name}/{len(args)}")
