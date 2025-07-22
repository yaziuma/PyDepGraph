from pyprolog.core.types import Term, Variable, Atom, Number, PrologType, Rule, Fact
from pyprolog.core.binding_environment import BindingEnvironment
from pyprolog.core.errors import (
    PrologError,
    CutException,
)  # Assuming CutException might be relevant for some builtins
from typing import TYPE_CHECKING, Iterator, List
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pyprolog.runtime.interpreter import Runtime


class BuiltinPredicate:
    def __init__(self, *args):
        self.args = args

    def execute(
        self, runtime: "Runtime", bindings: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        raise NotImplementedError


class VarPredicate(BuiltinPredicate):
    def __init__(self, arg1: PrologType):
        super().__init__(arg1)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        arg1 = self.args[0]
        if isinstance(arg1, Variable):
            yield env


class AtomPredicate(BuiltinPredicate):
    def __init__(self, arg1: PrologType):
        super().__init__(arg1)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        arg1 = self.args[0]
        if isinstance(arg1, Atom):
            yield env


class NumberPredicate(BuiltinPredicate):
    def __init__(self, arg1: PrologType):
        super().__init__(arg1)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        arg1 = self.args[0]
        if isinstance(arg1, Number):
            yield env


class FunctorPredicate(BuiltinPredicate):
    def __init__(
        self, term_arg: PrologType, functor_arg: PrologType, arity_arg: PrologType
    ):
        super().__init__(term_arg, functor_arg, arity_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        term, d_functor, d_arity = self.args[0], self.args[1], self.args[2]

        term_val = runtime.logic_interpreter.dereference(term, env)
        functor_val = runtime.logic_interpreter.dereference(d_functor, env)
        arity_val = runtime.logic_interpreter.dereference(d_arity, env)

        if not isinstance(term, Variable) or (
            isinstance(term, Variable) and not env.is_unbound(term.name)
        ):  # Analysis
            actual_functor: PrologType
            actual_arity: Number

            if isinstance(term_val, Term):
                actual_functor = term_val.functor
                actual_arity = Number(len(term_val.args))
            elif isinstance(term_val, Atom):
                actual_functor = term_val
                actual_arity = Number(0)
            elif isinstance(term_val, Number):
                actual_functor = term_val
                actual_arity = Number(0)
            else:
                return

            unified_functor, env1 = runtime.logic_interpreter.unify(
                functor_val, actual_functor, env
            )
            if not unified_functor:
                return

            unified_arity, env2 = runtime.logic_interpreter.unify(
                arity_val, actual_arity, env1
            )
            if not unified_arity:
                return

            yield env2
            return

        elif isinstance(term, Variable) and env.is_unbound(term.name):  # Synthesis
            if not isinstance(functor_val, (Atom, Number)):
                return
            if (
                not isinstance(arity_val, Number)
                or not arity_val.value.is_integer()
                or arity_val.value < 0
            ):
                return
            if isinstance(functor_val, Number) and arity_val.value != 0:
                return

            constructed_term: PrologType
            arity_int = int(arity_val.value)

            if arity_int == 0:
                constructed_term = functor_val
            else:
                if not isinstance(functor_val, Atom):
                    return
                args = [
                    Variable(f"_GFA{runtime.logic_interpreter._unique_var_counter + i}")
                    for i in range(arity_int)
                ]
                runtime.logic_interpreter._unique_var_counter += arity_int
                constructed_term = Term(functor_val, args)

            unified_term, final_env = runtime.logic_interpreter.unify(
                term, constructed_term, env
            )
            if unified_term:
                yield final_env
            return
        return


class ArgPredicate(BuiltinPredicate):
    def __init__(
        self, index_arg: PrologType, term_arg: PrologType, value_arg: PrologType
    ):
        super().__init__(index_arg, term_arg, value_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        index_val = runtime.logic_interpreter.dereference(self.args[0], env)
        term_val = runtime.logic_interpreter.dereference(self.args[1], env)

        if (
            not isinstance(index_val, Number)
            or not index_val.value.is_integer()
            or index_val.value <= 0
        ):
            return
        if not isinstance(term_val, Term):
            return

        idx = int(index_val.value)
        if idx > len(term_val.args):
            return

        target_arg = term_val.args[idx - 1]
        unified, final_env = runtime.logic_interpreter.unify(
            self.args[2], target_arg, env
        )
        if unified:
            yield final_env


class UnivPredicate(BuiltinPredicate):  # =../2
    def __init__(self, term_arg: PrologType, list_arg: PrologType):
        super().__init__(term_arg, list_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        # Determine mode based on which argument is a variable vs instantiated
        term_is_var_unbound = isinstance(self.args[0], Variable) and env.is_unbound(
            self.args[0].name
        )
        list_is_var_unbound = isinstance(self.args[1], Variable) and env.is_unbound(
            self.args[1].name
        )

        term_val = runtime.logic_interpreter.dereference(self.args[0], env)
        list_val = runtime.logic_interpreter.dereference(self.args[1], env)

        if not term_is_var_unbound:  # Analysis: Term -> List
            result_list_content: List[PrologType] = []
            if isinstance(term_val, Term):
                result_list_content.append(term_val.functor)
                result_list_content.extend(term_val.args)
            elif isinstance(term_val, (Atom, Number)):
                result_list_content.append(term_val)
            else:
                return

            prolog_list: PrologType = Atom("[]")
            for i in range(len(result_list_content) - 1, -1, -1):
                prolog_list = Term(Atom("."), [result_list_content[i], prolog_list])

            unified, final_env = runtime.logic_interpreter.unify(
                self.args[1], prolog_list, env
            )
            if unified:
                yield final_env
            return

        elif term_is_var_unbound and not list_is_var_unbound:  # Synthesis: List -> Term
            if not isinstance(list_val, Term) and not (
                isinstance(list_val, Atom) and list_val.name == "[]"
            ):
                return  # List must be a proper list or empty list atom

            py_list: List[PrologType] = []
            current_cell = list_val
            while (
                isinstance(current_cell, Term)
                and current_cell.functor.name == "."
                and len(current_cell.args) == 2
            ):
                py_list.append(
                    runtime.logic_interpreter.dereference(current_cell.args[0], env)
                )  # Deref elements during deconstruction
                current_cell = runtime.logic_interpreter.dereference(
                    current_cell.args[1], env
                )

            if not (isinstance(current_cell, Atom) and current_cell.name == "[]"):
                return
            if not py_list:
                return

            functor_from_list = py_list[0]
            args_from_list = py_list[1:]

            if not isinstance(functor_from_list, (Atom, Number)):
                return
            if isinstance(functor_from_list, Number) and args_from_list:
                return
            if (
                isinstance(functor_from_list, Atom)
                and functor_from_list.name == "[]"
                and args_from_list
            ):
                return

            MAX_ARITY = 50
            if len(args_from_list) > MAX_ARITY:
                return

            constructed_term: PrologType
            if not args_from_list:
                constructed_term = functor_from_list
            else:
                if not isinstance(functor_from_list, Atom):
                    return
                constructed_term = Term(functor_from_list, args_from_list)

            unified, final_env = runtime.logic_interpreter.unify(
                self.args[0], constructed_term, env
            )
            if unified:
                yield final_env
            return
        # Other cases like both vars, or both instantiated (check mode)
        elif term_is_var_unbound and list_is_var_unbound:  # Both vars: Error
            return
        # If both are instantiated, it becomes a check. This is implicitly handled if neither of the above blocks execute.
        # However, the logic for analysis (Term->List) will perform the check if list_val is also instantiated.
        return


class DynamicAssertAPredicate(BuiltinPredicate):
    def __init__(self, clause_arg: PrologType):
        super().__init__(clause_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        logger.debug(f"ASSERTA: Entered with arg: {self.args[0]}")
        clause_val = runtime.logic_interpreter.dereference(self.args[0], env)
        logger.debug(
            f"ASSERTA: Dereferenced clause_val: {clause_val} (type: {type(clause_val)})"
        )

        if isinstance(clause_val, Variable):
            logger.warning(
                f"ASSERTA: Attempt to assert an uninstantiated variable: {clause_val}. Failing."
            )
            return
        if not isinstance(clause_val, (Term, Atom)):
            logger.warning(
                f"ASSERTA: Attempt to assert a non-term/non-atom: {clause_val} (type: {type(clause_val)}). Failing."
            )
            return

        try:
            clause_val_as_term = (
                Term(clause_val, []) if isinstance(clause_val, Atom) else clause_val
            )
            logger.debug(f"ASSERTA: clause_val_as_term: {clause_val_as_term}")

            if (
                clause_val_as_term.functor.name == ":-"
                and len(clause_val_as_term.args) == 2
            ):
                head = clause_val_as_term.args[0]
                body = clause_val_as_term.args[1]
                logger.debug(f"ASSERTA: Identified as rule. Head: {head}, Body: {body}")
                if not isinstance(head, (Term, Atom)):
                    logger.warning(
                        f"ASSERTA: Rule head is not Term or Atom: {head}. Failing on clause: {clause_val}"
                    )
                    return
                if isinstance(head, Atom):
                    head = Term(head, [])
                    logger.debug(f"ASSERTA: Converted Atom head to Term: {head}")

                processed_body = body
                if isinstance(body, Atom):
                    processed_body = Term(body, [])
                    logger.debug(
                        f"ASSERTA: Converted Atom body {body} to Term: {processed_body}"
                    )
                elif not isinstance(body, Term):
                    logger.warning(
                        f"ASSERTA: Rule body {body} (type: {type(body)}) is not an Atom or Term. Failing assertion for clause: {clause_val}"
                    )
                    return  # Fail the assertion

                new_rule = Rule(
                    head, processed_body
                )  # Now head and processed_body are Term
                logger.debug(f"ASSERTA: Created Rule: {new_rule}")
                runtime.rules.insert(0, new_rule)
                logger.info(f"ASSERTA: Successfully asserted rule: {new_rule}")
            else:
                logger.debug(f"ASSERTA: Identified as fact: {clause_val_as_term}")
                new_fact = Fact(clause_val_as_term)
                logger.debug(f"ASSERTA: Created Fact: {new_fact}")
                runtime.rules.insert(0, new_fact)
                logger.info(f"ASSERTA: Successfully asserted fact: {new_fact}")

            # This line is intentionally left as is, as per instructions.
            # runtime.logic_interpreter.rules = runtime.rules

            logger.debug(
                f"ASSERTA: About to yield environment for: {clause_val_as_term}"
            )
            yield env
            logger.debug(
                f"ASSERTA: Successfully yielded environment for: {clause_val_as_term}"
            )

        except Exception as e:
            logger.error(
                f"ASSERTA: Unexpected Python exception during assertion of {clause_val}: {e}",
                exc_info=True,
            )
            return  # Ensure no yield happens if an error occurred


class DynamicAssertZPredicate(BuiltinPredicate):
    def __init__(self, clause_arg: PrologType):
        super().__init__(clause_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        logger.debug(f"ASSERTZ: Entered with arg: {self.args[0]}")
        clause_val = runtime.logic_interpreter.dereference(self.args[0], env)
        logger.debug(
            f"ASSERTZ: Dereferenced clause_val: {clause_val} (type: {type(clause_val)})"
        )

        if isinstance(clause_val, Variable):
            logger.warning(
                f"ASSERTZ: Attempt to assert an uninstantiated variable: {clause_val}. Failing."
            )
            return
        if not isinstance(clause_val, (Term, Atom)):
            logger.warning(
                f"ASSERTZ: Attempt to assert a non-term/non-atom: {clause_val} (type: {type(clause_val)}). Failing."
            )
            return

        try:
            clause_val_as_term = (
                Term(clause_val, []) if isinstance(clause_val, Atom) else clause_val
            )
            logger.debug(f"ASSERTZ: clause_val_as_term: {clause_val_as_term}")

            if (
                clause_val_as_term.functor.name == ":-"
                and len(clause_val_as_term.args) == 2
            ):
                head = clause_val_as_term.args[0]
                body = clause_val_as_term.args[1]
                logger.debug(f"ASSERTZ: Identified as rule. Head: {head}, Body: {body}")
                if not isinstance(head, (Term, Atom)):
                    logger.warning(
                        f"ASSERTZ: Rule head is not Term or Atom: {head}. Failing on clause: {clause_val}"
                    )
                    return
                if isinstance(head, Atom):
                    head = Term(head, [])
                    logger.debug(f"ASSERTZ: Converted Atom head to Term: {head}")

                processed_body = body
                if isinstance(body, Atom):
                    processed_body = Term(body, [])
                    logger.debug(
                        f"ASSERTZ: Converted Atom body {body} to Term: {processed_body}"
                    )
                elif not isinstance(body, Term):
                    logger.warning(
                        f"ASSERTZ: Rule body {body} (type: {type(body)}) is not an Atom or Term. Failing assertion for clause: {clause_val}"
                    )
                    return  # Fail the assertion

                new_rule = Rule(
                    head, processed_body
                )  # Now head and processed_body are Term
                logger.debug(f"ASSERTZ: Created Rule: {new_rule}")
                runtime.rules.append(new_rule)
                logger.info(f"ASSERTZ: Successfully asserted rule: {new_rule}")
            else:
                logger.debug(f"ASSERTZ: Identified as fact: {clause_val_as_term}")
                new_fact = Fact(clause_val_as_term)
                logger.debug(f"ASSERTZ: Created Fact: {new_fact}")
                runtime.rules.append(new_fact)
                logger.info(f"ASSERTZ: Successfully asserted fact: {new_fact}")

            # This line is intentionally left as is, as per instructions.
            # runtime.logic_interpreter.rules = runtime.rules

            logger.debug(
                f"ASSERTZ: About to yield environment for: {clause_val_as_term}"
            )
            yield env
            logger.debug(
                f"ASSERTZ: Successfully yielded environment for: {clause_val_as_term}"
            )

        except Exception as e:
            logger.error(
                f"ASSERTZ: Unexpected Python exception during assertion of {clause_val}: {e}",
                exc_info=True,
            )
            return  # Ensure no yield happens if an error occurred


class MemberPredicate(BuiltinPredicate):
    def __init__(self, element_arg: PrologType, list_arg: PrologType):
        super().__init__(element_arg, list_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        current_list = runtime.logic_interpreter.dereference(self.args[1], env)
        element_to_match = self.args[0]  # This will be unified, use original arg

        while (
            isinstance(current_list, Term)
            and isinstance(current_list.functor, Atom)
            and current_list.functor.name == "."
            and len(current_list.args) == 2
        ):
            head = current_list.args[0]
            head = current_list.args[0]
            tail = current_list.args[1]
            logger.debug(
                f"MEMBER: Loop iteration. current_list='{current_list}', head='{head}', tail='{tail}', element_to_match='{element_to_match}'"
            )

            unified, next_env = runtime.logic_interpreter.unify(
                element_to_match, head, env
            )
            logger.debug(
                f"MEMBER: Unify result for element '{element_to_match}' and head '{head}': {unified}. Env after unify: {next_env.bindings if unified else 'N/A'}"
            )
            if unified:
                yield next_env

            current_list_before_deref = tail
            current_list = runtime.logic_interpreter.dereference(tail, env)
            logger.debug(
                f"MEMBER: Tail dereferenced. Before='{current_list_before_deref}', After='{current_list}', Type After='{type(current_list)}'"
            )
        return


class AppendPredicate(BuiltinPredicate):
    def __init__(
        self, list1_arg: PrologType, list2_arg: PrologType, list3_arg: PrologType
    ):
        super().__init__(list1_arg, list2_arg, list3_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        # --- Choice Point 1: append([], L2, L2). ---
        env_clause1 = env.copy()
        unified_l1_empty, env_clause1_after_l1 = runtime.logic_interpreter.unify(
            self.args[0], Atom("[]"), env_clause1
        )
        logger.debug(
            f"APPEND_CP1: L1='{self.args[0]}', L2='{self.args[1]}', L3='{self.args[2]}'. Trying to unify L1 with []."
        )
        if unified_l1_empty:
            logger.debug(
                f"APPEND_CP1: L1 unified with []. Env after L1 unify: {env_clause1_after_l1.bindings}"
            )
            # L1 is []. Unify L2 and L3.
            unified_l2_l3, final_env_clause1 = runtime.logic_interpreter.unify(
                self.args[1], self.args[2], env_clause1_after_l1
            )
            if unified_l2_l3:
                logger.debug(
                    f"APPEND_CP1: L2 and L3 unified. Yielding solution from CP1. Env: {final_env_clause1.bindings}"
                )
                yield final_env_clause1
            else:
                logger.debug(f"APPEND_CP1: L2 and L3 failed to unify.")
        else:
            logger.debug(f"APPEND_CP1: L1 failed to unify with [].")

        # --- Choice Point 2: append([H|T1], L2, [H|T3]) :- append(T1, L2, T3). ---
        logger.debug(
            f"APPEND_CP2: L1='{self.args[0]}', L2='{self.args[1]}', L3='{self.args[2]}'. Creating patterns."
        )
        env_clause2 = env.copy()

        # Create fresh variables for the components of List1 and List3 for this specific choice point
        # Use unique names to avoid clashes with variables from outer scopes in the environment.
        counter = runtime.logic_interpreter._unique_var_counter
        h1_var = Variable(f"_HAppend_{counter}")
        t1_var = Variable(f"_T1Append_{counter + 1}")
        # For list3_pattern, H must be the *same* variable instance as in list1_pattern
        t3_var = Variable(f"_T3Append_{counter + 2}")
        runtime.logic_interpreter._unique_var_counter += 3

        list1_pattern = Term(Atom("."), [h1_var, t1_var])
        logger.debug(
            f"APPEND_CP2: Attempting to unify L1 ('{self.args[0]}') with pattern '{list1_pattern}'."
        )
        unified_l1_cons, env_clause2_after_l1 = runtime.logic_interpreter.unify(
            self.args[0], list1_pattern, env_clause2
        )

        if unified_l1_cons:
            logger.debug(
                f"APPEND_CP2: L1 unified with '{list1_pattern}'. Env after L1 unify: {env_clause2_after_l1.bindings}"
            )
            # L1 successfully unified with [h1_var | t1_var].
            # h1_var and t1_var are now (potentially) bound in env_clause2_after_l1.

            # List3 must match [h1_var | t3_var].
            # The h1_var in this pattern is the same Variable instance as in list1_pattern.
            # Unification will use its binding from env_clause2_after_l1.
            list3_pattern = Term(
                Atom("."), [h1_var, t3_var]
            )  # uses the same h1_var Variable object
            logger.debug(
                f"APPEND_CP2: Attempting to unify L3 ('{self.args[2]}') with pattern '{list3_pattern}'."
            )
            unified_l3_cons, env_clause2_after_l3 = runtime.logic_interpreter.unify(
                self.args[2], list3_pattern, env_clause2_after_l1
            )

            if unified_l3_cons:
                logger.debug(
                    f"APPEND_CP2: L3 unified with '{list3_pattern}'. Env after L3 unify: {env_clause2_after_l3.bindings}"
                )
                # Recursively call append(t1_var, List2_original, t3_var)
                # using env_clause2_after_l3.
                # The original self.args[1] is List2.
                # t1_var and t3_var are passed (their bound values if bound, or the Variable objects themselves)
                logger.debug(
                    f"APPEND_CP2: Making recursive call: append({t1_var}, {self.args[1]}, {t3_var}) with env: {env_clause2_after_l3.bindings}"
                )
                recursive_predicate = AppendPredicate(t1_var, self.args[1], t3_var)
                yield from recursive_predicate.execute(runtime, env_clause2_after_l3)
            else:
                logger.debug(f"APPEND_CP2: L3 failed to unify with '{list3_pattern}'.")
        else:
            logger.debug(f"APPEND_CP2: L1 failed to unify with '{list1_pattern}'.")
        return  # End of AppendPredicate


class FindallPredicate(BuiltinPredicate):
    def __init__(
        self, template_arg: PrologType, goal_arg: PrologType, list_arg: PrologType
    ):
        super().__init__(template_arg, goal_arg, list_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        template = self.args[0]
        goal_to_prove = runtime.logic_interpreter.dereference(
            self.args[1], env
        )  # Dereference goal in current env
        result_list_arg = self.args[2]

        # 2.a: Check if Goal is a callable term
        if isinstance(goal_to_prove, Variable):  # Uninstantiated variable
            raise PrologError(
                f"instantiation_error: Goal in findall/3 cannot be an unbound variable. Got: {goal_to_prove}"
            )

        # Standard Prolog: `[]` is not callable. Other atoms are callable (arity 0). Terms are callable.
        if isinstance(goal_to_prove, Atom) and goal_to_prove.name == "[]":
            raise PrologError(
                f"type_error(callable, {goal_to_prove}): Goal '[]' in findall/3 is not a callable term."
            )
        elif not isinstance(
            goal_to_prove, (Atom, Term)
        ):  # Numbers, strings (if distinct type) etc.
            raise PrologError(
                f"type_error(callable, {goal_to_prove}): Goal in findall/3 must be a callable term."
            )
        # At this point, goal_to_prove is an Atom (not '[]') or a Term.

        collected_templates: List[PrologType] = []

        # Create a pristine environment for proving the goal, independent of findall's own environment,
        # but able to see rules.
        # However, variables in `goal_to_prove` should be interpreted relative to `env` initially if they are shared.
        # The standard findall behavior is that `goal_to_prove` is called as if it's a normal goal.
        # Variables in `goal_to_prove` that are bound *outside* findall are part of the goal.
        # Variables *local* to `goal_to_prove` and `template` are the ones that vary per solution.

        # It's crucial that variables in `template` that are *not* part of `goal_to_prove`
        # (i.e., "free" variables in the template) are preserved as variables in each instantiated template.
        # The `instantiate_term_for_findall` helper needs to handle this correctly.
        # It should copy `template` and then apply only the bindings relevant to variables *within* that copied template
        # that were bound by the `goal_to_prove`'s solution.

        try:
            # Iterate over all solutions for the goal
            # Each solution from runtime.execute will be a BindingEnvironment
            # We need to use the original `env` because `goal_to_prove` might contain variables
            # bound in `env` that are part of the query.
            for solution_env in runtime.execute(goal_to_prove, env):
                # For each solution, instantiate the template.
                # This requires a careful instantiation that:
                # 1. Takes a *copy* of the original template.
                # 2. Applies bindings from `solution_env` to this copy.
                # 3. Variables in the template that were not bound by the goal remain as (copied) variables.
                # This is often done by "refreshing" or "skolemizing" variables from the template
                # that are *not* bound by the goal's solution, to ensure they are unique across results if needed,
                # or more simply, just applying the bindings from solution_env to a fresh copy of template.
                # A common approach: substitute known bindings from solution_env into a copy of template.

                # The logic_interpreter.instantiate_term should handle this:
                # It should take the template, and an environment (solution_env),
                # and return a new term with variables from template substituted if they are in solution_env.
                # Variables in template not in solution_env should remain as they are (or copies).
                instantiated_template = runtime.logic_interpreter.instantiate_term(
                    template, solution_env
                )
                collected_templates.append(instantiated_template)

        except CutException:
            # findall/3 is transparent to cuts *within* Goal.
            # If a cut is encountered inside Goal, it prunes choices for Goal, but findall continues.
            # If a cut is trying to escape Goal (which it shouldn't if prove handles it),
            # that would be an issue for the interpreter design.
            # For now, assume prove handles cuts internally and findall just collects all results it's given.
            # If CutException propagates here, it might be an error or specific design choice.
            # Standard behavior: cut inside findall/3 does not affect choice points outside findall/3.
            # It *does* affect the solutions generated for Goal.
            pass  # Let collected_templates be what we have so far if cut happened.
        except PrologError as e:
            # 2.e: If proving Goal raises an exception, findall/3 should re-throw that exception.
            raise e  # Re-throw other Prolog errors.

        # 2.c & 2.d: Convert collected_templates to a Prolog list
        prolog_solutions_list: PrologType = Atom("[]")
        for item in reversed(collected_templates):
            prolog_solutions_list = Term(Atom("."), [item, prolog_solutions_list])

        # Unify the resulting Prolog list with the List argument
        unified, final_env = runtime.logic_interpreter.unify(
            result_list_arg, prolog_solutions_list, env
        )
        if unified:
            yield final_env
        # If unification fails, findall/3 fails (no solutions yielded).
        return


class GetCharPredicate(BuiltinPredicate):
    """
    Built-in predicate get_char/1.
    Reads the next character from the current input stream and unifies it with Arg.
    """

    def __init__(self, arg: "PrologType"):
        super().__init__(arg)
        if len(self.args) != 1:
            # This check is mostly for consistency, as Runtime.execute usually checks arity.
            raise PrologError(f"get_char/1 expects 1 argument, got {len(self.args)}")

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        # 1. Get a character string from the IOManager
        # Assuming read_char_from_current() returns a single character string,
        # or an empty string for EOF.
        char_str = runtime.io_manager.read_char_from_current()

        # 2. Determine the target Prolog Atom based on the character string
        target_atom: Atom
        if char_str == "":  # EOF
            target_atom = Atom("end_of_file")
        elif len(char_str) == 1:  # Standard case: single character
            target_atom = Atom(char_str)
        else:
            # This case should ideally not happen if read_char_from_current adheres to
            # returning a single char or empty string. If it can return more,
            # the behavior of get_char/1 might need further specification for such cases.
            # For now, let's treat unexpected multi-character strings as an error or take the first.
            # Standard get_char/1 expects to read one char.
            # If read_char_from_current might return more (e.g. from a buffered non-interactive stream),
            # this predicate would need to handle that (e.g. by only taking the first char and perhaps
            # leaving the rest in an internal buffer for subsequent reads - complex).
            # Simplest for now: if it's not EOF and not a single char, it's an issue or undefined.
            # Let's assume for now read_char_from_current() guarantees single char or empty.
            # If for some reason it doesn't, this is a point of potential failure/unexpected behavior.
            # For robustness, if it could return None or other non-string types:
            if char_str is None:  # Defensive, if read_char could return None
                target_atom = Atom("end_of_file")  # Treat None like EOF
            else:  # Should be multi-character string if not "" or len 1
                # This path indicates an unexpected return from read_char_from_current
                # For now, we'll be strict and expect single chars or EOF marker.
                # Standard get_char would typically not be in this state from a conforming stream.
                # If the underlying stream gives more than one char, get_char usually takes one.
                # To be safe and simple for now, if it's not empty, take the first char.
                # This part might need refinement based on stream behavior.
                target_atom = Atom(char_str[0])

        # 3. Get the argument to get_char/1 (the Prolog variable or term)
        prolog_arg = self.args[0]

        # 4. Attempt to unify the argument with the target_atom
        # unify returns a tuple: (bool_success, resulting_environment)
        unified, next_env = runtime.logic_interpreter.unify(
            prolog_arg, target_atom, env
        )

        # 5. Yield successful unifications
        if unified:
            yield next_env
        # If unification fails, the predicate simply fails (yields nothing).


class ReadLinePredicate(BuiltinPredicate):
    """
    Built-in predicate read_line/1.
    Reads a line from the current input stream and unifies it with Arg.
    """

    def __init__(self, arg: "PrologType"):
        super().__init__(arg)
        if len(self.args) != 1:
            raise PrologError(f"read_line/1 expects 1 argument, got {len(self.args)}")

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        # 1. Read a line from the IOManager
        line_str = runtime.io_manager.read_line_from_current()

        # 2. Determine the target Prolog Atom based on the line string
        target_atom: Atom
        if line_str is None:  # EOF
            target_atom = Atom("end_of_file")
        else:
            target_atom = Atom(line_str)

        # 3. Unify the target atom with the argument
        unified, final_env = runtime.logic_interpreter.unify(
            self.args[0], target_atom, env
        )
        if unified:
            yield final_env
        # If unification fails, read_line/1 fails (no solutions yielded).
        return


class DynamicRetractPredicate(BuiltinPredicate):
    def __init__(self, clause_arg: PrologType):
        super().__init__(clause_arg)

    def execute(
        self, runtime: "Runtime", env: BindingEnvironment
    ) -> Iterator[BindingEnvironment]:
        logger.debug(f"RETRACT: Entered with arg: {self.args[0]}")

        # Dereference the argument to retract
        clause_to_retract_orig = self.args[0]
        # Create a deep copy for unification to avoid binding variables in the original query term structure
        import copy

        clause_to_retract_for_unify = copy.deepcopy(
            runtime.logic_interpreter.dereference(clause_to_retract_orig, env)
        )

        logger.debug(
            f"RETRACT: Dereferenced clause_to_retract_for_unify: {clause_to_retract_for_unify} (type: {type(clause_to_retract_for_unify)})"
        )

        if isinstance(clause_to_retract_for_unify, Variable):
            logger.warning(
                f"RETRACT: Attempt to retract an uninstantiated variable: {clause_to_retract_for_unify}. Failing (Instantiation Error)."
            )
            # Standard Prolog would raise instantiation_error. Here, we fail.
            return

        if not isinstance(clause_to_retract_for_unify, (Term, Atom)):
            logger.warning(
                f"RETRACT: Argument is not a Term or Atom: {clause_to_retract_for_unify} (type: {type(clause_to_retract_for_unify)}). Failing (Type Error)."
            )
            # Standard Prolog would raise type_error(callable, Clause). Here, we fail.
            return

        # Convert Atom to Term for consistent matching, e.g. retract(foo) matches foo.
        target_clause_struct = (
            Term(clause_to_retract_for_unify, [])
            if isinstance(clause_to_retract_for_unify, Atom)
            else clause_to_retract_for_unify
        )

        is_retracting_rule_form = (
            isinstance(target_clause_struct, Term)
            and target_clause_struct.functor.name == ":-"
            and len(target_clause_struct.args) == 2
        )

        target_head_to_match = (
            target_clause_struct.args[0]
            if is_retracting_rule_form
            else target_clause_struct
        )
        target_body_to_match = (
            target_clause_struct.args[1] if is_retracting_rule_form else None
        )  # None if retracting a fact or simple term

        # Iterate over a copy of the rules list to allow modification, or iterate by index
        # Iterating by index in reverse is safer for removal.
        for i in range(len(runtime.rules) - 1, -1, -1):
            db_clause = runtime.rules[i]

            # Important: For unification with DB clause, rename variables from DB clause
            # to avoid clashes and incorrect unifications with variables in target_clause_struct
            renamed_db_clause = runtime.logic_interpreter._rename_variables(db_clause)

            db_head: Term
            db_body: Optional[PrologType] = None

            if isinstance(renamed_db_clause, Fact):
                db_head = renamed_db_clause.head
                if is_retracting_rule_form:  # Cannot match a fact with a rule form H:-B
                    continue
            elif isinstance(renamed_db_clause, Rule):
                db_head = renamed_db_clause.head
                db_body = renamed_db_clause.body
                if (
                    not is_retracting_rule_form and db_body is not None
                ):  # retract(H) should not match H:-B unless B is 'true' or matches var
                    # Standard retract(H) can match Rule H:-Body if Body unifies with 'true'
                    # For simplicity here, if retracting a fact-form, only match facts or rules H:-true.
                    # A more complete retract would handle Body unification with 'true'.
                    # For now, if retracting H, and DB is H:-B, we only match if target_body_to_match is not None (i.e. retracting H:-B1)
                    # or if db_body is Atom('true') - this part is not implemented here yet.
                    pass  # Allow retract(H) to potentially match Rule(H,B) head.
            else:
                logger.error(f"RETRACT: Unknown clause type in DB: {db_clause}")
                continue

            # Try to unify the head parts
            # Unify target_head_to_match with db_head using a *copy* of env for this attempt
            unified_head, head_env = runtime.logic_interpreter.unify(
                target_head_to_match, db_head, env.copy()
            )

            if unified_head:
                if is_retracting_rule_form:
                    # If retracting H:-B, bodies must also unify
                    if db_body is None:  # DB is Fact, cannot match H:-B
                        continue

                    # Ensure db_body is Term if it's Atom for unification consistency if target_body is Term
                    db_body_term = (
                        Term(db_body, []) if isinstance(db_body, Atom) else db_body
                    )
                    if (
                        not isinstance(db_body_term, Term)
                        and target_body_to_match is not None
                    ):  # e.g. db_body is Number
                        continue

                    unified_body, final_env = runtime.logic_interpreter.unify(
                        target_body_to_match, db_body_term, head_env
                    )
                    if unified_body:
                        logger.info(
                            f"RETRACT: Matched and removed rule: {runtime.rules[i]}"
                        )
                        del runtime.rules[i]
                        runtime.logic_interpreter.rules = (
                            runtime.rules
                        )  # Update logic interpreter's reference
                        yield final_env  # Yield the environment from successful unification
                        return  # Retract first match only for now
                else:  # Retracting a fact form (simple term)
                    # Standard Prolog: retract(H) can retract Fact(H) or Rule(H, true_body).
                    # For simplicity, this version retracts Fact(H) or any Rule(H, Body)
                    # This part might need refinement for strict standard compliance regarding Body.
                    logger.info(
                        f"RETRACT: Matched and removed clause: {runtime.rules[i]} (using head match for fact-form retract)"
                    )
                    del runtime.rules[i]
                    runtime.logic_interpreter.rules = runtime.rules
                    yield head_env  # Yield the environment from head unification
                    return  # Retract first match

        logger.debug(f"RETRACT: No matching clause found for: {target_clause_struct}")
        return  # Failed to find a match
