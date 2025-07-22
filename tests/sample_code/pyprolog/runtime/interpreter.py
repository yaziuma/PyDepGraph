# pyprolog/runtime/interpreter.py
from pyprolog.core.types import Term, Variable, Number, Rule, Fact, Atom
from pyprolog.core.binding_environment import BindingEnvironment
from pyprolog.parser.scanner import Scanner
from pyprolog.parser.parser import Parser
from pyprolog.util.variable_mapper import VariableMapper # Added
from pyprolog.util.functor_mapper import FunctorMapper # Added FunctorMapper
from pyprolog.runtime.math_interpreter import MathInterpreter
from pyprolog.runtime.logic_interpreter import LogicInterpreter
from pyprolog.core.operators import operator_registry, OperatorType, OperatorInfo
from pyprolog.core.errors import PrologError, CutException
from pyprolog.runtime.builtins import (
    VarPredicate,
    AtomPredicate,
    NumberPredicate,
    FunctorPredicate,
    ArgPredicate,
    UnivPredicate,
    DynamicAssertAPredicate,
    DynamicAssertZPredicate,
    DynamicRetractPredicate,
    MemberPredicate,
    AppendPredicate,
    FindallPredicate,
    GetCharPredicate,
    ReadLinePredicate,
)
from .io_manager import IOManager
from typing import List, Iterator, Dict, Any, Union, Optional, Callable # Optional was already here
import logging

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(
        self,
        rules: Optional[List[Union[Rule, Fact]]] = None,
        variable_mapper: Optional[VariableMapper] = None,
        functor_mapper: Optional[FunctorMapper] = None
    ):
        self.rules: List[Union[Rule, Fact]] = rules if rules is not None else []
        self.variable_mapper = variable_mapper if variable_mapper is not None else VariableMapper()
        
        # 既存ルールからファンクター名を抽出して衝突回避
        existing_functors = self._extract_existing_functors()
        self.functor_mapper = functor_mapper if functor_mapper is not None else FunctorMapper(existing_functors)
        
        # 既にマッパーが提供されている場合は、既存ファンクターを登録
        if functor_mapper is not None:
            self.functor_mapper.register_existing_functors(existing_functors)
            
        self.math_interpreter = MathInterpreter()
        self.io_manager = IOManager()  # Initialize IOManager
        self.logic_interpreter = LogicInterpreter(
            self.rules, self
        )  # Pass self (Runtime) to LogicInterpreter
        self._operator_evaluators = self._build_unified_evaluator_system()
        logger.info(
            f"Runtime initialized with {len(self.rules)} rules, IOManager, VariableMapper, FunctorMapper, and {len(self._operator_evaluators)} operator evaluators"
        )

    def _extract_existing_functors(self) -> set:
        """既存ルールからファンクター名を抽出"""
        functors = set()
        
        for rule in self.rules:
            if isinstance(rule, Fact):
                functors.update(self._extract_functors_from_term(rule.head))
            elif isinstance(rule, Rule):
                functors.update(self._extract_functors_from_term(rule.head))
                functors.update(self._extract_functors_from_term(rule.body))
        
        return functors

    def _extract_functors_from_term(self, term) -> set:
        """項から再帰的にファンクター名を抽出"""
        functors = set()
        
        if isinstance(term, Term):
            if isinstance(term.functor, Atom):
                functors.add(term.functor.name)
            
            # 引数も再帰的にチェック
            for arg in term.args:
                functors.update(self._extract_functors_from_term(arg))
                
        elif isinstance(term, Atom):
            functors.add(term.name)
            
        elif isinstance(term, list):
            for item in term:
                functors.update(self._extract_functors_from_term(item))
        
        return functors

    def _build_unified_evaluator_system(self) -> Dict[str, Callable]:
        evaluators: Dict[str, Callable] = {}
        arithmetic_ops = operator_registry.get_operators_by_type(
            OperatorType.ARITHMETIC
        )
        for op_info in arithmetic_ops:
            if op_info.symbol == "is":
                evaluators[op_info.symbol] = self._create_is_evaluator()
            else:
                evaluators[op_info.symbol] = self._create_arithmetic_evaluator(op_info)
        comparison_ops = operator_registry.get_operators_by_type(
            OperatorType.COMPARISON
        )
        for op_info in comparison_ops:
            evaluators[op_info.symbol] = self._create_comparison_evaluator(op_info)
        logical_ops = operator_registry.get_operators_by_type(OperatorType.LOGICAL)
        for op_info in logical_ops:
            if op_info.symbol == "=":
                evaluators[op_info.symbol] = self._create_unification_evaluator()
            else:
                evaluators[op_info.symbol] = self._create_logical_evaluator(op_info)
        control_ops = operator_registry.get_operators_by_type(OperatorType.CONTROL)
        for op_info in control_ops:
            evaluators[op_info.symbol] = self._create_control_evaluator(op_info)
        io_ops = operator_registry.get_operators_by_type(OperatorType.IO)
        for op_info in io_ops:
            evaluators[op_info.symbol] = self._create_io_evaluator(op_info)
        logger.debug(f"Built {len(evaluators)} unified operator evaluators")
        return evaluators

    def _create_arithmetic_evaluator(self, op_info: OperatorInfo):
        def evaluator(args: List, env: BindingEnvironment) -> bool:
            if len(args) != op_info.arity:
                raise PrologError(
                    f"Operator {op_info.symbol} expects {op_info.arity} arguments, got {len(args)}"
                )
            if op_info.arity == 2:
                left_val = self.math_interpreter.evaluate(args[0], env)
                right_val = self.math_interpreter.evaluate(args[1], env)
                self.math_interpreter.evaluate_binary_op(
                    op_info.symbol, left_val, right_val
                )
                return True
            raise NotImplementedError(
                f"Unary arithmetic operator {op_info.symbol} not implemented"
            )

        return evaluator

    def _create_comparison_evaluator(self, op_info: OperatorInfo):
        def evaluator(args: List, env: BindingEnvironment) -> bool:
            if len(args) != 2:
                raise PrologError(
                    f"Comparison operator {op_info.symbol} requires 2 arguments"
                )
            left_val = self.math_interpreter.evaluate(args[0], env)
            right_val = self.math_interpreter.evaluate(args[1], env)
            return self.math_interpreter.evaluate_comparison_op(
                op_info.symbol, left_val, right_val
            )

        return evaluator

    def _create_is_evaluator(self):
        def evaluator(
            args: List, env: BindingEnvironment
        ) -> Iterator[BindingEnvironment]:
            if len(args) != 2:
                raise PrologError("'is' operator requires exactly 2 arguments")
            result_term, expression = args[0], args[1]
            try:
                value = self.math_interpreter.evaluate(expression, env)
                result_number = Number(value)
                unified, new_env = self.logic_interpreter.unify(
                    result_term, result_number, env
                )
                if unified:
                    yield new_env
            except Exception as e:
                logger.debug(f"'is' evaluation failed: {e}")

        return evaluator

    def _create_unification_evaluator(self):
        def evaluator(
            args: List, env: BindingEnvironment
        ) -> Iterator[BindingEnvironment]:
            if len(args) != 2:
                raise PrologError("Unification operator = requires exactly 2 arguments")
            unified, new_env = self.logic_interpreter.unify(args[0], args[1], env)
            if unified:
                yield new_env

        return evaluator

    def _create_logical_evaluator(self, op_info: OperatorInfo):
        def evaluator(
            args: List, env: BindingEnvironment
        ) -> Iterator[BindingEnvironment]:
            if op_info.symbol == ",":  # Conjunction
                if len(args) != 2:
                    raise PrologError("Conjunction ,/2 requires exactly 2 arguments")
                left_goal, right_goal = args[0], args[1]
                try:
                    for left_env in self.execute(left_goal, env):
                        logger.debug(
                            f"LOGICAL_EVAL ,: left_env for {left_goal} is {left_env.bindings}"
                        )
                        try:
                            for right_env_solution in self.execute(
                                right_goal, left_env
                            ):
                                logger.debug(
                                    f"LOGICAL_EVAL ,: right_env_solution for {right_goal} is {right_env_solution.bindings}"
                                )
                                yield right_env_solution
                        except CutException:
                            logger.debug(
                                "CutException from right_goal of conjunction, re-raising."
                            )
                            raise
                except CutException:
                    logger.debug(
                        "CutException from left_goal of conjunction. Re-raising."
                    )
                    raise
            elif op_info.symbol == ";":  # Disjunction
                if len(args) != 2:
                    raise PrologError("Disjunction ;/2 requires exactly 2 arguments")
                left_goal, right_goal = args[0], args[1]
                try:
                    for left_env in self.execute(left_goal, env):
                        yield left_env
                except CutException:
                    logger.debug(
                        "CutException from left part of disjunction ';'. Re-raising."
                    )
                    raise
                else:
                    for right_env_solution in self.execute(right_goal, env):
                        yield right_env_solution
            elif op_info.symbol == "\\+":  # Negation as failure
                if len(args) != 1:
                    raise PrologError("Negation \\+/1 requires exactly 1 argument")
                goal_to_negate = args[0]
                success_found = False
                try:
                    for _ in self.execute(goal_to_negate, env):
                        success_found = True
                        break
                except CutException:
                    logger.debug(
                        f"CutException inside \\+ for goal {goal_to_negate}. Standard \\+ would fail here."
                    )
                    success_found = True
                if not success_found:
                    yield env
            elif op_info.symbol == "==":
                if len(args) != 2:
                    raise PrologError("Identity ==/2 requires exactly 2 arguments")
                left_deref = self.logic_interpreter.dereference(args[0], env)
                right_deref = self.logic_interpreter.dereference(args[1], env)
                if left_deref == right_deref:
                    yield env
            elif op_info.symbol == "\\==":
                if len(args) != 2:
                    raise PrologError(
                        "Non-identity \\==/2 requires exactly 2 arguments"
                    )
                left_deref = self.logic_interpreter.dereference(args[0], env)
                right_deref = self.logic_interpreter.dereference(args[1], env)
                if left_deref != right_deref:
                    yield env
            elif op_info.symbol == "\\=":  # \=/2 Term non-unification
                if len(args) != 2:
                    raise PrologError(
                        "Non-unification operator \\=/2 requires exactly 2 arguments"
                    )
                term1, term2 = args[0], args[1]
                # We need to try unification and succeed if it fails.
                # Crucially, unify creates a *copy* of the environment.
                # So, any bindings made during a successful unify attempt should not persist
                # if we are only checking for unifiability.
                unified, _ = self.logic_interpreter.unify(term1, term2, env)
                if not unified:
                    yield env  # Succeeds if unify returns False
            elif op_info.symbol == "<>":  # NOT_EQUAL - alternative to \=
                if len(args) != 2:
                    raise PrologError(
                        "Not-equal operator <>/2 requires exactly 2 arguments"
                    )
                term1, term2 = args[0], args[1]
                # Same logic as \= - succeed if unification fails
                unified, _ = self.logic_interpreter.unify(term1, term2, env)
                if not unified:
                    yield env
            elif op_info.symbol == "!=":  # NOT_EQUAL_ALT - alternative to \=
                if len(args) != 2:
                    raise PrologError(
                        "Not-equal operator !=/2 requires exactly 2 arguments"
                    )
                term1, term2 = args[0], args[1]
                # Same logic as \= - succeed if unification fails
                unified, _ = self.logic_interpreter.unify(term1, term2, env)
                if not unified:
                    yield env
            else:
                raise NotImplementedError(
                    f"Logical operator {op_info.symbol} not implemented"
                )

        return evaluator

    def _create_control_evaluator(self, op_info: OperatorInfo):
        def evaluator(
            args: List, env: BindingEnvironment
        ) -> Iterator[BindingEnvironment]:
            if op_info.symbol == "!":
                if args:
                    raise PrologError("Cut !/0 takes no arguments")
                logger.debug(f"CUTTING! Environment: {env.bindings}")
                yield env
                raise CutException()
            elif op_info.symbol == "->":
                if len(args) != 2:
                    raise PrologError("If-then ->/2 requires exactly 2 arguments")
                condition, then_part = args[0], args[1]
                solution_found_for_condition = False
                try:
                    for cond_env in self.execute(condition, env):
                        solution_found_for_condition = True
                        try:
                            for then_env_solution in self.execute(then_part, cond_env):
                                yield then_env_solution
                        except CutException:
                            logger.debug(
                                "CutException from then_part of '->', re-raising to cut '->' and parent choices."
                            )
                            raise
                        raise CutException()
                except CutException:
                    if solution_found_for_condition:
                        logger.debug(
                            "CutException after processing 'then_part' or from within 'then_part' for '->'. Re-raising."
                        )
                        raise
                    else:
                        logger.debug(
                            "CutException from 'condition' part of '->' before any solution. Re-raising."
                        )
                        raise
            else:
                raise NotImplementedError(
                    f"Control operator {op_info.symbol} not implemented"
                )

        return evaluator

    def _create_io_evaluator(self, op_info: OperatorInfo):
        def evaluator(
            args: List, env: BindingEnvironment
        ) -> Iterator[BindingEnvironment]:
            if op_info.symbol == "write":
                if len(args) != 1:
                    raise PrologError("write/1 requires exactly 1 argument")
                arg_deref = self.logic_interpreter.dereference(args[0], env)
                print(str(arg_deref), end="")
                yield env
            elif op_info.symbol == "nl":
                if len(args) != 0:
                    raise PrologError("nl/0 requires no arguments")
                print()
                yield env
            elif op_info.symbol == "tab":
                if len(args) > 1:
                    raise PrologError("tab requires 0 or 1 arguments")
                if len(args) == 1:
                    count_term = self.logic_interpreter.dereference(args[0], env)
                    if isinstance(count_term, Number):
                        print(" " * int(count_term.value), end="")
                    else:
                        print("\t", end="")
                else:
                    print("\t", end="")
                yield env
            else:
                raise NotImplementedError(
                    f"IO operator {op_info.symbol} not implemented"
                )

        return evaluator

    def execute(
        self, goal: Any, env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        logger.debug(
            f"EXECUTE: Called with goal: {goal} (type: {type(goal)}) in env: {env.bindings}"
        )

        processed_goal: Term
        if (
            isinstance(goal, Atom)
            and goal.name == "!"
            and "!" in self._operator_evaluators
        ):
            logger.debug("EXECUTE: Atom('!') detected, routing to operator.")
            processed_goal = Term(
                goal, []
            )  # Convert to Term to be handled by operator logic
        elif isinstance(goal, Term):
            processed_goal = goal
        elif isinstance(goal, Atom):
            logger.debug(
                f"EXECUTE Atom: Attempting Normal Predicate solve_goal for Atom: {goal}"
            )
            try:
                for item in self.logic_interpreter.solve_goal(goal, env):
                    logger.debug(
                        f"EXECUTE Atom (solve_goal): Yielding: {item.bindings if item else 'None'}"
                    )
                    yield item
            except CutException:
                logger.debug(
                    f"CutException propagated from solve_goal for Atom: {goal}. Re-raising."
                )
                raise
            return
        else:
            logger.debug(
                f"Goal {goal} (type {type(goal)}) is not directly executable by Runtime.execute, failing."
            )
            return

        functor_name = (
            processed_goal.functor.name
            if hasattr(processed_goal.functor, "name")
            else str(processed_goal.functor)
        )
        op_info = operator_registry.get_operator(functor_name)

        if op_info and functor_name in self._operator_evaluators:
            evaluator = self._operator_evaluators[functor_name]
            try:
                if (
                    op_info.operator_type == OperatorType.ARITHMETIC
                    and functor_name != "is"
                ):
                    if evaluator(processed_goal.args, env):
                        logger.debug(
                            f"EXECUTE op {functor_name}: Yielding env (bool success): {env.bindings}"
                        )
                        yield env
                elif op_info.operator_type == OperatorType.COMPARISON:
                    if evaluator(processed_goal.args, env):
                        logger.debug(
                            f"EXECUTE op {functor_name}: Yielding env (bool success): {env.bindings}"
                        )
                        yield env
                else:
                    for item in evaluator(processed_goal.args, env):
                        logger.debug(
                            f"EXECUTE op {functor_name}: Yielding item from evaluator: {item.bindings if item else 'None'}"
                        )
                        yield item
            except CutException:
                logger.debug(
                    f"CutException caught while evaluating operator {functor_name}. Re-raising."
                )
                raise
            except Exception as e:
                logger.error(
                    f"Error evaluating operator {functor_name}: {e}", exc_info=True
                )
                return
        elif functor_name == "var" and len(processed_goal.args) == 1:
            dereferenced_arg = self.logic_interpreter.dereference(
                processed_goal.args[0], env
            )
            var_pred = VarPredicate(dereferenced_arg)
            for item in var_pred.execute(self, env):
                yield item
        elif functor_name == "atom" and len(processed_goal.args) == 1:
            dereferenced_arg = self.logic_interpreter.dereference(
                processed_goal.args[0], env
            )
            atom_pred = AtomPredicate(dereferenced_arg)
            for item in atom_pred.execute(self, env):
                yield item
        elif functor_name == "number" and len(processed_goal.args) == 1:
            dereferenced_arg = self.logic_interpreter.dereference(
                processed_goal.args[0], env
            )
            num_pred = NumberPredicate(dereferenced_arg)
            for item in num_pred.execute(self, env):
                yield item
        elif functor_name == "functor" and len(processed_goal.args) == 3:
            functor_pred = FunctorPredicate(
                processed_goal.args[0], processed_goal.args[1], processed_goal.args[2]
            )
            try:
                for item in functor_pred.execute(self, env):
                    yield item
            except CutException:
                logger.debug("CutException from functor/3. Re-raising.")
                raise
        elif functor_name == "arg" and len(processed_goal.args) == 3:
            arg_pred = ArgPredicate(
                processed_goal.args[0], processed_goal.args[1], processed_goal.args[2]
            )
            try:
                for item in arg_pred.execute(self, env):
                    yield item
            except CutException:
                logger.debug("CutException from arg/3. Re-raising.")
                raise
        elif functor_name == "=.." and len(processed_goal.args) == 2:
            univ_pred = UnivPredicate(processed_goal.args[0], processed_goal.args[1])
            try:
                for item in univ_pred.execute(self, env):
                    yield item
            except CutException:
                logger.debug("CutException from =../2. Re-raising.")
                raise
        elif functor_name == "asserta" and len(processed_goal.args) == 1:
            asserta_pred = DynamicAssertAPredicate(processed_goal.args[0])
            for item in asserta_pred.execute(self, env):
                yield item
        elif functor_name == "assertz" and len(processed_goal.args) == 1:
            assertz_pred = DynamicAssertZPredicate(processed_goal.args[0])
            for item in assertz_pred.execute(self, env):
                yield item
        elif functor_name == "member" and len(processed_goal.args) == 2:
            # Note: MemberPredicate's execute method handles dereferencing its arguments as needed.
            member_pred = MemberPredicate(
                processed_goal.args[0], processed_goal.args[1]
            )
            try:
                for item in member_pred.execute(self, env):
                    yield item
            except CutException:  # Should member/2 propagate CutException? Typically not, but being consistent.
                logger.debug("CutException from member/2. Re-raising.")
                raise
        elif functor_name == "append" and len(processed_goal.args) == 3:
            # AppendPredicate handles dereferencing its arguments internally as needed.
            append_pred = AppendPredicate(
                processed_goal.args[0], processed_goal.args[1], processed_goal.args[2]
            )
            try:
                for item in append_pred.execute(self, env):
                    yield item
            except (
                CutException
            ):  # append/3 is not typically a source of CutException by itself
                logger.debug(
                    "CutException from append/3. Re-raising."
                )  # Though unlikely
                raise
        elif functor_name == "findall" and len(processed_goal.args) == 3:
            findall_pred = FindallPredicate(
                processed_goal.args[0], processed_goal.args[1], processed_goal.args[2]
            )
            # FindallPredicate's execute method handles internal exceptions and re-throws PrologErrors
            # It also handles CutException internally as per standard behavior (cut affects Goal, not findall itself)
            for item in findall_pred.execute(self, env):
                yield item
        elif functor_name == "get_char" and len(processed_goal.args) == 1:
            get_char_pred = GetCharPredicate(processed_goal.args[0])
            for item in get_char_pred.execute(self, env):
                yield item
        elif functor_name == "read_line" and len(processed_goal.args) == 1:
            read_line_pred = ReadLinePredicate(processed_goal.args[0])
            for item in read_line_pred.execute(self, env):
                yield item
        elif functor_name == "retract" and len(processed_goal.args) == 1:
            retract_pred = DynamicRetractPredicate(processed_goal.args[0])
            for item in retract_pred.execute(self, env):  # self is runtime
                yield item
        else:
            logger.debug(
                f"EXECUTE Term: Attempting Normal Predicate solve_goal for: {processed_goal}"
            )
            try:
                for item in self.logic_interpreter.solve_goal(processed_goal, env):
                    logger.debug(
                        f"EXECUTE Term (solve_goal): Yielding: {item.bindings if item else 'None'}"
                    )
                    yield item
            except CutException:
                logger.debug(
                    f"CutException propagated from solve_goal for Term: {processed_goal}. Re-raising."
                )
                raise

    def query(self, query_string: str) -> List[Dict[Variable, Any]]:
        logger.debug(f"QUERY: Executing query: {query_string}")
        solutions = []
        try:
            # Ensure query ends with a dot for parsing consistency
            if not query_string.strip().endswith("."):
                query_string += "."
            tokens = Scanner(query_string, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).scan_tokens()
            parsed_structures = Parser(tokens, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).parse()
            if not parsed_structures:
                logger.warning("Query parsing failed")
                return []
            query_goal: Optional[Any] = None
            if isinstance(parsed_structures[0], Fact):
                query_goal = parsed_structures[0].head
            elif isinstance(parsed_structures[0], Rule):
                query_goal = parsed_structures[0].head
            elif isinstance(parsed_structures[0], Term):
                query_goal = parsed_structures[0]
            elif isinstance(parsed_structures[0], Atom):
                query_goal = parsed_structures[0]

            if query_goal is None:
                logger.error(
                    f"Could not extract a valid goal from parsed: {parsed_structures[0]}"
                )
                return []

            initial_env = BindingEnvironment()

            term_for_vars_extraction: Term
            if isinstance(query_goal, Atom):
                term_for_vars_extraction = Term(query_goal, [])
            elif isinstance(query_goal, Term):
                term_for_vars_extraction = query_goal
            else:
                logger.error(
                    f"Cannot extract vars from non-Term/Atom goal: {query_goal}"
                )
                return []
            query_vars_names = self._extract_variables_names(term_for_vars_extraction)

            try:
                logger.debug(f"QUERY: Starting execute loop for goal: {query_goal}")
                for i, env_solution in enumerate(self.execute(query_goal, initial_env)):
                    logger.debug(
                        f"QUERY: Received solution #{i} from execute: {env_solution.bindings if env_solution else 'None'}"
                    )
                    if env_solution is None:
                        continue
                    result = {}
                    for var_name_str in query_vars_names:
                        var_obj = Variable(var_name_str) # This is the English (mapped) variable name
                        value_fully_dereferenced = (
                            self.logic_interpreter.deep_dereference_term(
                                var_obj, env_solution
                            )
                        )
                        # Convert variable name back to Japanese for display
                        original_var_name = self.variable_mapper.map_english_to_japanese(var_obj.name)
                        display_var_obj = Variable(original_var_name)
                        # Convert any variables within the result term back to Japanese
                        result[display_var_obj] = self._convert_vars_to_japanese(value_fully_dereferenced)
                    solutions.append(result)
            except CutException:
                logger.info(
                    f"Cut execution stopped further solutions at query level. Returning {len(solutions)} solution(s)."
                )

            logger.debug(f"QUERY: Completed with {len(solutions)} solutions")
            return solutions

        except PrologError as pe:  # Catch PrologError specifically
            logger.warning(
                f"PrologError during query execution: {pe}", exc_info=True
            )  # Log as warning or info
            raise pe  # Re-throw PrologError so tests can catch it

        except Exception as e:  # Catch other, unexpected exceptions
            logger.error(
                f"Unexpected query execution error during query '{query_string}': {e}",
                exc_info=True,
            )
            # Re-raise the exception to make it visible in test output
            raise e

    def _extract_variables_names(self, term) -> List[str]:
        variables = set()
        queue = [term]
        while queue:
            current = queue.pop(0)
            if isinstance(current, Variable):
                variables.add(current.name)
            elif isinstance(current, Term):
                if isinstance(current.functor, Variable):
                    variables.add(current.functor.name)
                queue.extend(current.args)
        return list(variables)

    def add_rule(self, rule_string: str) -> bool:
        try:
            if not rule_string.strip().endswith("."):
                rule_string += "."
            tokens = Scanner(rule_string, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).scan_tokens()
            parsed_items = Parser(tokens, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).parse()
            added_count = 0
            if parsed_items:
                for item in parsed_items:
                    if isinstance(item, (Rule, Fact)):
                        self.rules.append(item)
                        added_count += 1
                    else:
                        logger.warning(f"Skipping non-rule/fact from add_rule: {item}")
                if added_count > 0:
                    self.logic_interpreter.rules = self.rules
                    logger.info(f"Added {added_count} rule(s)/fact(s) from string.")
                else:
                    logger.warning("No rules/facts parsed from add_rule string.")
                return added_count > 0
            logger.warning("No rules/facts parsed from add_rule string.")
            return False
        except Exception as e:
            logger.error(f"Failed to add rule: {e}", exc_info=True)
            return False

    def consult(self, filename: str) -> bool:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                source = f.read()
            tokens = Scanner(source, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).scan_tokens()
            new_rules_or_terms = Parser(tokens, variable_mapper=self.variable_mapper, functor_mapper=self.functor_mapper).parse()
            added_count = 0
            for item in new_rules_or_terms:
                if isinstance(item, (Rule, Fact)):
                    self.rules.append(item)
                    added_count += 1
                else:
                    logger.warning(f"Skipping non-rule/fact during consult: {item}")
            if added_count > 0:
                self.logic_interpreter.rules = self.rules
                logger.info(f"Consulted {added_count} rules/facts from {filename}")
            else:
                logger.info(f"No rules or facts consulted from {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to consult {filename}: {e}", exc_info=True)
            return False

    def _convert_vars_to_japanese(self, term: Any) -> Any:
        if isinstance(term, Variable):
            return Variable(self.variable_mapper.map_english_to_japanese(term.name))
        elif isinstance(term, Term):
            new_args = [self._convert_vars_to_japanese(arg) for arg in term.args]
            # FunctorがVariableの場合も変換する（通常はAtomだが念のため）
            current_functor = term.functor
            if isinstance(current_functor, Variable):
                # FunctorがVariableの場合は変数として変換
                functor_display_name = self.variable_mapper.map_english_to_japanese(current_functor.name)
                return Term(Variable(functor_display_name), new_args)
            elif isinstance(current_functor, Atom):
                # FunctorがAtomの場合は、まずファンクター名の日本語復元を試す
                functor_name = current_functor.name
                # FunctorMapperで日本語復元を試行
                restored_functor_name = self.functor_mapper.map_english_to_non_ascii(functor_name)
                return Term(Atom(restored_functor_name), new_args)
            else:
                # その他の場合（通常は発生しない）
                functor_display_name = str(current_functor)
                return Term(Atom(functor_display_name), new_args)
        elif isinstance(term, list): # For lists (e.g. from findall)
            return [self._convert_vars_to_japanese(item) for item in term]
        # Other types (Number, Atom, String) are returned as is.
        return term
