from pyprolog.core.types import Term, Variable, TRUE_TERM, FALSE_TERM


class Number(Term):
    """数値を表すTerm"""

    def __init__(self, value):
        super().__init__(value)  # pred に数値を格納
        self.value = value

    def match(self, other, bindings=None):
        if bindings is None:
            bindings = {}

        if isinstance(other, Variable):
            return other.match(self, bindings)

        if isinstance(other, Number):
            return bindings if self.value == other.value else None

        return None

    def substitute(self, bindings):
        return self

    def __str__(self):
        return str(self.value)

    # 算術演算メソッド
    def add(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value)
        raise TypeError(f"Cannot add Number and {type(other)}")

    def subtract(self, other):  # Renamed from substract
        if isinstance(other, Number):
            return Number(self.value - other.value)
        raise TypeError(f"Cannot subtract Number and {type(other)}")

    def multiply(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value)
        raise TypeError(f"Cannot multiply Number and {type(other)}")

    def divide(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                raise ZeroDivisionError("Division by zero")
            return Number(self.value / other.value)
        raise TypeError(f"Cannot divide Number and {type(other)}")

    # 比較演算メソッド
    def equal(self, other):
        if isinstance(other, Number):
            return self.value == other.value
        return False

    def not_equal(self, other):
        return not self.equal(other)

    def less(self, other):
        if isinstance(other, Number):
            return self.value < other.value
        raise TypeError(f"Cannot compare Number and {type(other)}")

    def equal_less(self, other):
        if isinstance(other, Number):
            return self.value <= other.value
        raise TypeError(f"Cannot compare Number and {type(other)}")

    def greater(self, other):
        if isinstance(other, Number):
            return self.value > other.value
        raise TypeError(f"Cannot compare Number and {type(other)}")

    def greater_equal(self, other):
        if isinstance(other, Number):
            return self.value >= other.value
        raise TypeError(f"Cannot compare Number and {type(other)}")


class Arithmetic(Variable):
    """算術式を含む変数"""

    def __init__(self, name, expression):
        super().__init__(name)
        self.expression = expression

    def evaluate(self, interpreter):
        """MathInterpreterを使って式を評価"""
        return interpreter._evaluate_expr(self.expression)


class Logic(Term):
    """論理式を表すTerm"""

    def __init__(self, expression):
        super().__init__("logic", expression)
        self.expression = expression

    def evaluate(self, interpreter):
        """LogicInterpreterを使って式を評価"""
        return interpreter._evaluate_expr(self.expression)


# 定数
TRUE = TRUE_TERM
FALSE = FALSE_TERM


# TermFunction の追加実装（runtime/interpreter.py で必要）
class TermFunction(Term):
    """Python関数を呼び出し可能なTerm"""

    def __init__(self, predicate_name, *args, python_callable=None):
        super().__init__(predicate_name, *args)
        self.python_callable = python_callable
        self._executed = False

    def _execute_func(self):
        """Python関数を実行してargs を更新"""
        if self.python_callable and not self._executed:
            # 引数を Python オブジェクトに変換
            py_args = []
            for arg in self.args:
                if isinstance(arg, Number):
                    py_args.append(arg.value)
                elif isinstance(arg, Term) and str(arg.pred) in ["true", "false"]:
                    py_args.append(str(arg.pred) == "true")
                else:
                    py_args.append(str(arg))

            # 関数を実行
            result = self.python_callable(*py_args)

            # 結果を Prolog の Term に変換
            if isinstance(result, bool):
                self.args = [Term("true") if result else Term("false")]
            elif isinstance(result, (int, float)):
                self.args = [Number(result)]
            else:
                self.args = [Term(str(result))]

            self._executed = True

    def match(self, other, bindings=None):
        # 実行前に関数を呼び出す
        self._execute_func()
        return super().match(other, bindings)
