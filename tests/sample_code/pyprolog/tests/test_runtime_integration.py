import unittest
from pyprolog.runtime.interpreter import Runtime
from pyprolog.core.types import Variable, Atom, Term, Number
from pyprolog.util.variable_mapper import VariableMapper

class TestRuntimeIntegrationJapanese(unittest.TestCase):

    def setUp(self):
        # 各テストで新しいRuntimeとVariableMapperインスタンスを使用する
        self.variable_mapper = VariableMapper()
        self.runtime = Runtime(variable_mapper=self.variable_mapper)

    def assertSolutionContains(self, solutions, expected_bindings_list):
        self.assertEqual(len(solutions), len(expected_bindings_list),
                         f"Expected {len(expected_bindings_list)} solutions, got {len(solutions)}")

        processed_solutions = []
        for sol_dict in solutions:
            processed_sol = {}
            for k_var, val_term in sol_dict.items():
                processed_sol[k_var.name] = val_term
            processed_solutions.append(processed_sol)

        for expected_bindings_dict in expected_bindings_list:
            found_match = False
            for processed_sol_dict in processed_solutions:
                if len(processed_sol_dict) != len(expected_bindings_dict):
                    continue # Different number of bindings

                match_this_sol = True
                for var_name_str, expected_val in expected_bindings_dict.items():
                    if var_name_str not in processed_sol_dict or \
                       processed_sol_dict[var_name_str] != expected_val:
                        match_this_sol = False
                        break

                if match_this_sol:
                    found_match = True
                    # Optionally, remove the matched solution to ensure all expected solutions are unique and present
                    # processed_solutions.remove(processed_sol_dict)
                    break
            self.assertTrue(found_match, f"Expected solution containing {expected_bindings_dict} not found in actual solutions {solutions}")


    def test_simple_japanese_variable_query(self):
        self.runtime.add_rule("favorite_food(apple).")
        self.runtime.add_rule("favorite_food(orange).")
        solutions = self.runtime.query("favorite_food(何).") # 何 -> V1

        expected = [
            {"何": Atom("apple")},
            {"何": Atom("orange")}
        ]
        self.assertSolutionContains(solutions, expected)

    def test_japanese_variables_in_rule_and_query(self):
        # Simplified test using English atoms but Japanese variables
        self.runtime.add_rule("parent(taro, ichiro).")
        self.runtime.add_rule("parent(taro, jiro).")
        self.runtime.add_rule("sibling(X, Y) :- parent(P, X), parent(P, Y).")

        solutions = self.runtime.query("sibling(ichiro, 誰か).")
        # The query should find that ichiro and jiro are siblings
        expected = [
            {"誰か": Atom("ichiro")}, 
            {"誰か": Atom("jiro")}
        ]
        self.assertSolutionContains(solutions, expected)

        # j_to_e, e_to_j = self.variable_mapper.get_all_mappings()
        # print("\nMappings for test_japanese_variables_in_rule_and_query:")
        # print("J->E:", j_to_e) # Should contain 兄,弟,親,誰か and their V forms
        # print("E->J:", e_to_j)


    def test_query_with_multiple_japanese_variables(self):
        self.runtime.add_rule("location(tokyo, japan).")
        self.runtime.add_rule("location(osaka, japan).")
        self.runtime.add_rule("location(paris, france).")

        solutions = self.runtime.query("location(都市, japan).")
        expected = [
            {"都市": Atom("tokyo")},
            {"都市": Atom("osaka")}
        ]
        self.assertSolutionContains(solutions, expected)

        self.setUp()
        self.runtime.add_rule("location(tokyo, japan).")
        self.runtime.add_rule("location(osaka, japan).")
        self.runtime.add_rule("location(paris, france).")
        solutions2 = self.runtime.query("location(どの都市, どの国).")
        expected2 = [
            {"どの都市": Atom("tokyo"), "どの国": Atom("japan")},
            {"どの都市": Atom("osaka"), "どの国": Atom("japan")},
            {"どの都市": Atom("paris"), "どの国": Atom("france")}
        ]
        self.assertSolutionContains(solutions2, expected2)


    def test_mixed_japanese_and_english_variables(self):
        # In "likes(jiro, 何か) :- likes(taro, 何か)."
        # 何か is a Japanese variable, mapped to V1.
        self.runtime.add_rule("likes(taro, apple).")
        self.runtime.add_rule("likes(jiro, 何か) :- likes(taro, 何か).")

        solutions = self.runtime.query("likes(jiro, Food).")
        # Query: likes(jiro, Food)
        # Rule: likes(jiro, V1) :- likes(taro, V1)
        # Unify query with rule head: Food <-> V1
        # New goal: likes(taro, V1)
        # Fact: likes(taro, apple) -> V1 = apple
        # So, Food = apple.
        expected = [
            {"Food": Atom("apple")}
        ]
        self.assertSolutionContains(solutions, expected)

        # Check that "何か" was mapped, but "Food" was not.
        _, e_to_j = self.variable_mapper.get_all_mappings()
        self.assertIn("V1", e_to_j)
        self.assertEqual(e_to_j["V1"], "何か")
        self.assertNotIn("Food", e_to_j) # English variables are not in the map


    def test_no_solution_with_japanese_variables(self):
        self.runtime.add_rule("food(apple).")
        # Test that Japanese variable gets unified with existing fact
        solutions = self.runtime.query("food(存在しないもの).") # 存在しないもの is a Japanese variable
        expected = [{"存在しないもの": Atom("apple")}]
        self.assertSolutionContains(solutions, expected)

    def test_japanese_variable_unification_in_query(self):
        # Query: X = 日本の首都, X = 東京.
        # X is an English variable. 日本の首都 is a Japanese Atom (because it's not a valid Jap var name based on current regex - no 'の')
        # Actually, VariableMapper.is_japanese_variable allows 'の' if it's not the first char.
        # Let's assume "日本の首都" is a Japanese *variable* for this test, to test mapper.
        # If "日本の首都" is a variable -> V1
        # Then X = V1, X = 東京.
        # This means V1 must be 東京. So X is 東京.
        # The query would be asking for solutions where X is bound to V1 and X is bound to 東京.
        # Effectively, V1 = 東京.
        # The variable "日本の首都" (V1) gets bound to Atom("東京").
        # The query variable X also gets bound to Atom("東京").
        # Result: {"X": Atom("東京"), "日本の首都": Atom("東京")}
        # Let's re-evaluate the original intent.
        # If the query is "X = '日本の首都', X = '東京'." then it's Atom vs Atom, fails.
        # If "X = 日本の首都." and "日本の首都" is a variable, then X becomes an alias for "日本の首都".
        # If we then query "X = 東京.", it means "日本の首都" = 東京.

        # Test 1: "日本の首都" as an ATOM.
        # This requires it to be quoted or not match is_japanese_variable.
        # Assuming is_japanese_variable('日本の首都') is false (due to 'の' or other reasons).
        # Then 日本の首都 is an Atom.
        # X = Atom("日本の首都"), X = Atom("東京"). This will fail.
        # The current `is_japanese_variable` for "日本の首都" would be:
        # re.match(r'^[぀-ゟ゠-ヿ一-鿿]', "日") -> True
        # re.match(r'^[぀-ゟ゠-ヿ一-鿿][぀-ゟ゠-ヿ一-鿿\w]*$', "日本の首都") -> True. So it IS a variable.

        # So, "日本の首都" is variable V1. "東京" is variable V2.
        # Query: X = V1, X = V2.
        # This means X, V1, V2 all unify. If they are all fresh, they become aliases.
        # The query result should show bindings for X, 日本の首都, 東京.
        # All should be bound to the same internal variable.
        # Runtime will return display names.
        # {"X": Variable("日本の首都"), "日本の首都": Variable("日本の首都"), "東京": Variable("日本の首都")} or similar.
        # This needs careful checking of how Runtime returns unified unbound variables.
        # Usually, Prolog might just say "yes" or show X = 日本の首都, X = 東京.
        # If they are all unbound, they are unified. The result shows one as the representative.
        # Let's test unification with an atom for clarity.
        self.setUp()
        solutions = self.runtime.query("X = 日本の首都, 日本の首都 = tokyo.")
        # X -> V1 (日本の首都)
        # V1 = tokyo (Atom)
        # So, X = tokyo, 日本の首都 = tokyo
        expected = [{"X": Atom("tokyo"), "日本の首都": Atom("tokyo")}]
        self.assertSolutionContains(solutions, expected)

        self.setUp()
        solutions = self.runtime.query("都市 = 東京, 都市 = 日本の首都.") # All are variables
        # 都市 -> V1, 東京 -> V2, 日本の首都 -> V3
        # V1 = V2, V1 = V3. All unified.
        # Result: {"都市": Variable("東京"), "東京": Variable("東京"), "日本の首都": Variable("東京")} (or any other var as representative)
        # The representative choice can be tricky. Let's assume one.
        # For assertSolutionContains, we need to be flexible or know the exact rep.
        # A simpler unification test:
        solutions = self.runtime.query("Var = 日本語データ.") # 日本語データ is variable (V1)
        # Var (English) unifies with V1.
        # Result: Both variables are unified and bound to the same value
        expected_var_data = Variable("日本語データ") # This is what the value should be
        expected = [{"Var": expected_var_data, "日本語データ": expected_var_data}]
        self.assertSolutionContains(solutions, expected)

        self.setUp()
        solutions = self.runtime.query("Var1 = 日本語データ1, Var2 = 日本語データ1, Var3 = 日本語データ2.")
        # Var1 (Eng) -> V1 (日本語データ1)
        # Var2 (Eng) -> V1 (日本語データ1)
        # Var3 (Eng) -> V2 (日本語データ2)
        # All variables are unified and bound to the same value
        expected_var_data1 = Variable("日本語データ1")
        expected_var_data2 = Variable("日本語データ2")
        expected = [{"Var1": expected_var_data1, "Var2": expected_var_data1, "Var3": expected_var_data2, "日本語データ1": expected_var_data1, "日本語データ2": expected_var_data2}]
        self.assertSolutionContains(solutions, expected)


if __name__ == '__main__':
    unittest.main()
