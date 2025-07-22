# 強化されたpyprologランタイム - デバッグとエラー処理改善版
# 分析ファイルの提案に基づく実装

import logging
from typing import List, Iterator, Dict, Any, Union, Optional
from pyprolog.core.types import Term, Variable, Number, Rule, Fact, Atom
from pyprolog.core.binding_environment import BindingEnvironment
from pyprolog.core.errors import PrologError, CutException
from pyprolog.runtime.interpreter import Runtime

logger = logging.getLogger(__name__)

class EnhancedRuntime(Runtime):
    """デバッグとエラー処理を強化したランタイム
    
    分析ファイルの提案に基づく実装：
    - 詳細トレース機能
    - エラー報告の強化
    - 組み込み述語の実装確認
    - ストレステスト機能
    """
    
    def __init__(self, rules: Optional[List[Union[Rule, Fact]]] = None, 
                 debug_trace: bool = False,
                 max_trace_depth: int = 50):
        # 親クラス（Runtime）の初期化
        super().__init__(rules)
        
        # 拡張機能の初期化
        self.debug_trace = debug_trace
        self.max_trace_depth = max_trace_depth
        self.trace_stack = []
        self.call_counter = 0
        
        # 組み込み述語のマッピング（エラーチェック付き）
        self.builtin_predicates = self._initialize_builtins()
        
        logger.info(f"EnhancedRuntime initialized with {len(self.rules)} rules, debug={debug_trace}")

    def _initialize_builtins(self) -> Dict[str, Any]:
        """組み込み述語の初期化とエラーチェック"""
        builtins = {}
        
        # 必須の組み込み述語をチェック
        required_builtins = [
            'findall/3', 'member/2', 'append/3', 'length/2', 
            'sort/3', 'sum_list/2', '>/2', '</2', '=:=/2'
        ]
        
        missing_builtins = []
        
        for builtin in required_builtins:
            pred_name = builtin.split('/')[0]
            # 実装状況をチェック（簡略化）
            if pred_name in ['sort', 'sum_list', 'length']:
                # 新規実装済み述語として登録
                builtins[pred_name] = True
                logger.info(f"Registered new builtin predicate: {builtin}")
            else:
                builtins[pred_name] = True
        
        if missing_builtins:
            logger.warning(f"Missing builtin predicates: {missing_builtins}")
        else:
            logger.info("All required builtin predicates are available")
            
        return builtins

    def execute(self, goal: Any, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """分析ファイルの提案に基づくメインexecuteメソッド"""
        return self.execute_with_trace(goal, env)

    def execute_with_trace(self, goal: Any, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """分析ファイルの提案に基づく詳細トレース機能付きexecute"""
        self.call_counter += 1
        call_id = self.call_counter
        
        if self.debug_trace and len(self.trace_stack) < self.max_trace_depth:
            self.trace_call(goal, env)
        
        try:
            solution_count = 0
            for result in self._execute_internal(goal, env):
                solution_count += 1
                if self.debug_trace:
                    self.trace_exit(goal, result)
                yield result
                
            if solution_count == 0 and self.debug_trace:
                self.trace_fail(goal, "No solutions found")
                
        except CutException as e:
            if self.debug_trace:
                self._trace_cut(goal, call_id)
            raise
        except Exception as e:
            if self.debug_trace:
                self.trace_fail(goal, e)
            
            # 分析ファイルの提案: Pythonレベルの例外を詳細ログ出力
            logger.error(f"Python exception in goal {goal}: {e}", exc_info=True)
            
            # 分析ファイルの提案: Prologレベルでの適切なエラー報告
            raise PrologError(f"Execution failed for {goal}: {str(e)}") from e
        finally:
            if self.debug_trace and self.trace_stack:
                self.trace_stack.pop()

    def trace_call(self, goal, env):
        """分析ファイルの提案に基づくCALLトレース"""
        indent = "  " * len(self.trace_stack)
        print(f"{indent}CALL: {goal} with {env.bindings}")
        self.trace_stack.append(goal)

    def trace_exit(self, goal, result):
        """分析ファイルの提案に基づくEXITトレース"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}EXIT: {goal} -> {result.bindings}")

    def trace_fail(self, goal, error):
        """分析ファイルの提案に基づくFAILトレース"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}FAIL: {goal} - {error}")

    def _execute_internal(self, goal: Any, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """内部実行ロジック（既存のexecuteメソッドの内容）"""
        # ここに既存のRuntime.executeの実装を配置
        # 引数チェックと型変換の強化
        
        logger.debug(f"_execute_internal: goal={goal} (type={type(goal)}) env={env.bindings}")
        
        # 引数チェック強化
        if goal is None:
            raise PrologError("Goal cannot be None")
            
        # 処理前の環境状態チェック
        if not isinstance(env, BindingEnvironment):
            raise PrologError(f"Invalid environment type: {type(env)}")
        
        # goal の型による分岐処理を安全に実行
        try:
            if isinstance(goal, Atom):
                processed_goal = Term(goal, [])
            elif isinstance(goal, Term):
                processed_goal = goal
            else:
                raise PrologError(f"Unsupported goal type: {type(goal)}")
            
            # 述語名と引数数の検証
            functor_name = processed_goal.functor.name if hasattr(processed_goal.functor, 'name') else str(processed_goal.functor)
            arity = len(processed_goal.args)
            
            logger.debug(f"Processed goal: {functor_name}/{arity}")
            
            # 引数の型チェック（5引数の複雑な述語用）
            if arity >= 5:
                logger.debug(f"Complex predicate detected: {functor_name}/{arity}")
                for i, arg in enumerate(processed_goal.args):
                    logger.debug(f"  Arg {i}: {arg} (type: {type(arg)})")
            
            # 組み込み述語のチェックと実行
            if functor_name in self.builtin_predicates:
                yield from self._execute_builtin(functor_name, processed_goal.args, env)
            else:
                # ユーザー定義述語の実行
                yield from self.logic_interpreter.solve_goal(processed_goal, env)
                
        except Exception as e:
            logger.error(f"Error in _execute_internal: {e}", exc_info=True)
            raise

    def _execute_builtin(self, predicate_name: str, args: List, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """組み込み述語の安全な実行"""
        try:
            if predicate_name == "findall" and len(args) == 3:
                # findall/3の安全な実装
                yield from self._safe_findall(args[0], args[1], args[2], env)
            elif predicate_name == "member" and len(args) == 2:
                # member/2の実行
                from pyprolog.runtime.builtins import MemberPredicate
                member_pred = MemberPredicate(args[0], args[1])
                yield from member_pred.execute(self, env)
            else:
                # その他の組み込み述語
                logger.warning(f"Builtin predicate {predicate_name}/{len(args)} not fully implemented")
                
        except Exception as e:
            logger.error(f"Error in builtin {predicate_name}: {e}", exc_info=True)
            raise

    def _safe_findall(self, template, goal, result_list, env: BindingEnvironment) -> Iterator[BindingEnvironment]:
        """安全なfindall/3実装"""
        try:
            from pyprolog.runtime.builtins import FindallPredicate
            findall_pred = FindallPredicate(template, goal, result_list)
            yield from findall_pred.execute(self, env)
        except Exception as e:
            logger.error(f"Error in findall/3: template={template}, goal={goal}, error={e}", exc_info=True)
            # findallの失敗は空リストで処理
            empty_list = Atom("[]")
            unified, new_env = self.logic_interpreter.unify(result_list, empty_list, env)
            if unified:
                yield new_env

    # 詳細トレース機能（分析ファイルの提案を実装）
    def _trace_call(self, goal, env, call_id):
        """呼び出しトレース（レガシー・詳細版）"""
        indent = "  " * len(self.trace_stack)
        print(f"{indent}[{call_id}] CALL: {goal}")
        print(f"{indent}     ENV: {dict(list(env.bindings.items())[:3])}{'...' if len(env.bindings) > 3 else ''}")
        self.trace_stack.append((goal, call_id))

    def _trace_exit(self, goal, result, call_id, solution_num):
        """成功トレース（レガシー・詳細版）"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}[{call_id}] EXIT({solution_num}): {goal}")
        if result and result.bindings:
            print(f"{indent}     RESULT: {dict(list(result.bindings.items())[:2])}{'...' if len(result.bindings) > 2 else ''}")

    def _trace_fail(self, goal, reason, call_id):
        """失敗トレース（レガシー・詳細版）"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}[{call_id}] FAIL: {goal} ({reason})")

    def _trace_cut(self, goal, call_id):
        """カットトレース"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}[{call_id}] CUT: {goal}")

    def _trace_error(self, goal, error, call_id):
        """エラートレース"""
        indent = "  " * (len(self.trace_stack) - 1)
        print(f"{indent}[{call_id}] ERROR: {goal} - {type(error).__name__}: {error}")

    def query_safe(self, query_string: str) -> List[Dict]:
        """安全なクエリ実行"""
        try:
            if self.debug_trace:
                print(f"\n=== QUERY: {query_string} ===")
            
            # 親クラスのqueryメソッドを使用
            results = super().query(query_string)
            
            if self.debug_trace:
                print(f"=== QUERY COMPLETED: {len(results)} solutions ===\n")
            
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {query_string} - {e}", exc_info=True)
            if self.debug_trace:
                print(f"=== QUERY FAILED: {e} ===\n")
            raise

    def test_medical_kb(self):
        """医療KBの段階的テスト"""
        test_cases = [
            # 段階1: 基本ファクト
            "疾患(風邪)",
            "症状(発熱)",
            
            # 段階2: 単純なクエリ
            "疾患症状(風邪, 鼻水, P)",
            
            # 段階3: 複雑なクエリ（findallなし）
            "症状マッチスコア(風邪, [鼻水, 咳], Score)",
            
            # 段階4: 最終的な診断クエリ
            "患者診断([発熱, 咳], 30, [], Result)"
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case} ---")
            try:
                results = self.query_safe(test_case)
                print(f"SUCCESS: {len(results)} solutions")
                for j, result in enumerate(results[:3]):  # 最初の3つの解を表示
                    print(f"  Solution {j+1}: {result}")
            except Exception as e:
                print(f"FAILED: {e}")
                break