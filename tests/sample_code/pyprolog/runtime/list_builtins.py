"""
リスト関連の組み込み述語実装
分析ファイルで指摘された不足述語を補完
"""

from typing import Iterator
from pyprolog.core.types import Term, Variable, Number, Atom
from pyprolog.core.binding_environment import BindingEnvironment
from pyprolog.core.errors import PrologError
import logging

logger = logging.getLogger(__name__)


class LengthPredicate:
    """length/2述語の実装"""
    
    def __init__(self, list_term, length_term):
        self.list_term = list_term
        self.length_term = length_term
    
    def execute(self, runtime, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """length(List, Length)の実行"""
        try:
            # 引数の逆参照
            list_deref = runtime.logic_interpreter.dereference(self.list_term, env)
            length_deref = runtime.logic_interpreter.dereference(self.length_term, env)
            
            # リストが具体的に与えられている場合
            if not isinstance(list_deref, Variable):
                length = self._calculate_list_length(list_deref)
                if length is not None:
                    unified, new_env = runtime.logic_interpreter.unify(
                        self.length_term, Number(length), env
                    )
                    if unified:
                        yield new_env
            
            # 長さが具体的に与えられている場合（リスト生成）
            elif isinstance(length_deref, Number) and isinstance(list_deref, Variable):
                if length_deref.value >= 0:
                    generated_list = self._generate_list(int(length_deref.value))
                    unified, new_env = runtime.logic_interpreter.unify(
                        self.list_term, generated_list, env
                    )
                    if unified:
                        yield new_env
        
        except Exception as e:
            logger.error(f"Error in length/2: {e}")
            raise PrologError(f"length/2 execution failed: {e}")
    
    def _calculate_list_length(self, term):
        """リストの長さを計算"""
        if isinstance(term, Atom) and term.name == "[]":
            return 0
        elif isinstance(term, Term) and term.functor.name == "." and len(term.args) == 2:
            tail_length = self._calculate_list_length(term.args[1])
            if tail_length is not None:
                return 1 + tail_length
        return None
    
    def _generate_list(self, length: int):
        """指定された長さのリストを生成（変数で埋める）"""
        if length == 0:
            return Atom("[]")
        else:
            var = Variable(f"_G{length}")
            tail = self._generate_list(length - 1)
            return Term(Atom("."), [var, tail])


class SumListPredicate:
    """sum_list/2述語の実装"""
    
    def __init__(self, list_term, sum_term):
        self.list_term = list_term
        self.sum_term = sum_term
    
    def execute(self, runtime, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """sum_list(List, Sum)の実行"""
        try:
            # リストの逆参照
            list_deref = runtime.logic_interpreter.dereference(self.list_term, env)
            
            # リストの合計を計算
            total = self._calculate_sum(list_deref, runtime, env)
            if total is not None:
                unified, new_env = runtime.logic_interpreter.unify(
                    self.sum_term, Number(total), env
                )
                if unified:
                    yield new_env
        
        except Exception as e:
            logger.error(f"Error in sum_list/2: {e}")
            raise PrologError(f"sum_list/2 execution failed: {e}")
    
    def _calculate_sum(self, term, runtime, env: BindingEnvironment):
        """リストの数値合計を計算"""
        if isinstance(term, Atom) and term.name == "[]":
            return 0
        elif isinstance(term, Term) and term.functor.name == "." and len(term.args) == 2:
            head = runtime.logic_interpreter.dereference(term.args[0], env)
            tail = runtime.logic_interpreter.dereference(term.args[1], env)
            
            if isinstance(head, Number):
                tail_sum = self._calculate_sum(tail, runtime, env)
                if tail_sum is not None:
                    return head.value + tail_sum
        return None


class SortPredicate:
    """sort/3述語の実装（簡略版）"""
    
    def __init__(self, key_term, order_term, list_term, sorted_term):
        self.key_term = key_term
        self.order_term = order_term  
        self.list_term = list_term
        self.sorted_term = sorted_term
    
    def execute(self, runtime, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """sort(Key, Order, List, Sorted)の実行（簡略版）"""
        try:
            # 基本的な実装：数値リストの昇順ソート
            list_deref = runtime.logic_interpreter.dereference(self.list_term, env)
            
            # リストを Python リストに変換
            python_list = self._convert_to_python_list(list_deref, runtime, env)
            if python_list is not None:
                # ソート（数値のみサポート）
                try:
                    sorted_list = sorted(python_list)
                    prolog_sorted = self._convert_to_prolog_list(sorted_list)
                    
                    unified, new_env = runtime.logic_interpreter.unify(
                        self.sorted_term, prolog_sorted, env
                    )
                    if unified:
                        yield new_env
                except TypeError:
                    # ソートできない場合はそのまま返す
                    unified, new_env = runtime.logic_interpreter.unify(
                        self.sorted_term, list_deref, env
                    )
                    if unified:
                        yield new_env
        
        except Exception as e:
            logger.error(f"Error in sort/3: {e}")
            raise PrologError(f"sort/3 execution failed: {e}")
    
    def _convert_to_python_list(self, term, runtime, env):
        """Prologリストを Python リストに変換"""
        result = []
        current = term
        
        while True:
            current = runtime.logic_interpreter.dereference(current, env)
            if isinstance(current, Atom) and current.name == "[]":
                break
            elif isinstance(current, Term) and current.functor.name == "." and len(current.args) == 2:
                head = runtime.logic_interpreter.dereference(current.args[0], env)
                if isinstance(head, Number):
                    result.append(head.value)
                elif isinstance(head, Atom):
                    result.append(head.name)
                else:
                    return None  # ソートできない要素
                current = current.args[1]
            else:
                return None  # 不正なリスト構造
        
        return result
    
    def _convert_to_prolog_list(self, python_list):
        """Python リストを Prolog リストに変換"""
        if not python_list:
            return Atom("[]")
        
        result = Atom("[]")
        for item in reversed(python_list):
            if isinstance(item, (int, float)):
                element = Number(item)
            else:
                element = Atom(str(item))
            result = Term(Atom("."), [element, result])
        
        return result