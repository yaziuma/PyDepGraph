import unittest
from pyprolog.parser.scanner import Scanner
from pyprolog.parser.parser import Parser
from pyprolog.parser.token_type import TokenType
from pyprolog.core.types import Variable, Term, Atom
from pyprolog.util.variable_mapper import VariableMapper

class TestScannerParserIntegration(unittest.TestCase):

    def setUp(self):
        self.variable_mapper = VariableMapper()
        # スキャナとパーサで同じマッパーインスタンスを共有することが重要
        self.scanner = Scanner(source="", variable_mapper=self.variable_mapper)
        self.parser = Parser(tokens=[], variable_mapper=self.variable_mapper)

    def _scan_and_parse_fact(self, prolog_code: str):
        # Scannerのsourceを更新して再利用
        self.scanner._source = prolog_code
        self.scanner._tokens = []
        self.scanner._current = 0
        self.scanner._start = 0
        self.scanner._line = 1
        # Ensure the prolog_code ends with a dot for the parser
        if not prolog_code.strip().endswith("."):
            prolog_code += "."
            self.scanner._source = prolog_code # Update source if dot was added

        tokens = self.scanner.scan_tokens()

        # Parserのtokensを更新して再利用
        self.parser._tokens = tokens
        self.parser._current = 0
        parsed_rules = self.parser.parse()
        if parsed_rules:
            return parsed_rules[0] # Fact or Rule object
        return None

    def test_japanese_variable_in_simple_fact(self):
        # Test Japanese variable handling with English functor
        fact = self._scan_and_parse_fact("favorite_food(日本語変数).")
        self.assertIsNotNone(fact)
        self.assertIsInstance(fact.head, Term)
        self.assertEqual(fact.head.functor.name, "favorite_food")
        self.assertEqual(len(fact.head.args), 1)
        self.assertIsInstance(fact.head.args[0], Variable)
        # Scanner により Token.literal が "V1" になっているはず
        # Parser は Token.literal を使って Variable.name を設定する
        self.assertEqual(fact.head.args[0].name, "V1")
        # VariableMapper で逆引きできることを確認
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V1"), "日本語変数")

    def test_multiple_japanese_variables_in_fact(self):
        # Test multiple Japanese variables with English functor
        # Note: In Prolog, unquoted lowercase terms are atoms. Japanese terms starting with Hiragana/Katakana/Kanji
        # without being uppercase English-like are treated as atoms by default unless VariableMapper identifies them as variables.
        # The current VariableMapper identifies Japanese starting terms as variables.
        # So, ちち, はは, こども will be treated as variables by the VariableMapper logic.
        # Let's adjust the test to reflect this, or use quoted atoms if they must be atoms.
        # Assuming the intent is for these to be variables:
        fact = self._scan_and_parse_fact("family(ちち, はは, こども).")
        self.assertIsNotNone(fact)
        self.assertIsInstance(fact.head, Term)
        self.assertEqual(fact.head.functor.name, "family")
        self.assertEqual(len(fact.head.args), 3)
        self.assertIsInstance(fact.head.args[0], Variable) # ちち -> V1
        self.assertEqual(fact.head.args[0].name, "V1")
        self.assertIsInstance(fact.head.args[1], Variable) # はは -> V2
        self.assertEqual(fact.head.args[1].name, "V2")
        self.assertIsInstance(fact.head.args[2], Variable) # こども -> V3
        self.assertEqual(fact.head.args[2].name, "V3")
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V1"), "ちち")
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V2"), "はは")
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V3"), "こども")

        # Test second fact with English functor
        self.setUp() # Reset mapper for next part of test
        fact2 = self._scan_and_parse_fact("relation(へんすうA, へんすうB).")
        self.assertIsNotNone(fact2)
        self.assertIsInstance(fact2.head, Term)
        self.assertEqual(fact2.head.functor.name, "relation")
        self.assertEqual(len(fact2.head.args), 2)
        self.assertIsInstance(fact2.head.args[0], Variable)
        self.assertEqual(fact2.head.args[0].name, "V1") # "へんすうA" -> V1
        self.assertIsInstance(fact2.head.args[1], Variable)
        self.assertEqual(fact2.head.args[1].name, "V2") # "へんすうB" -> V2
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V1"), "へんすうA")
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V2"), "へんすうB")

    def test_mixed_variables_and_atoms_in_fact(self):
        # "data(value1, 日本語データ, X)."
        self.setUp()
        fact = self._scan_and_parse_fact("data(value1, 日本語データ, VarX).")
        self.assertIsNotNone(fact)
        self.assertIsInstance(fact.head, Term)
        self.assertEqual(fact.head.functor.name, "data")
        self.assertEqual(len(fact.head.args), 3)
        self.assertIsInstance(fact.head.args[0], Atom)
        self.assertEqual(fact.head.args[0].name, "value1")
        self.assertIsInstance(fact.head.args[1], Variable) # 日本語データ is a variable
        self.assertEqual(fact.head.args[1].name, "V1")
        self.assertIsInstance(fact.head.args[2], Variable) # VarX is a variable
        self.assertEqual(fact.head.args[2].name, "VarX") # English variable name remains as is
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V1"), "日本語データ")
        # VarX は日本語変数ではないのでマッピングされない
        self.assertEqual(self.variable_mapper.map_english_to_japanese("VarX"), "VarX")


    def test_english_variable_does_not_get_mapped(self):
        fact = self._scan_and_parse_fact("english_fact(AnEnglishVar).")
        self.assertIsNotNone(fact)
        self.assertIsInstance(fact.head.args[0], Variable)
        self.assertEqual(fact.head.args[0].name, "AnEnglishVar")
        # マッピングされていないことを確認
        j_to_e, e_to_j = self.variable_mapper.get_all_mappings()
        self.assertEqual(len(j_to_e), 0)
        self.assertEqual(len(e_to_j), 0)

    def test_atom_starting_with_uppercase_is_atom(self):
        # Prologでは 'Atom' はアトムとして扱われる（クォートされていれば）
        # クォートなしの 大文字で始まるものは変数。
        # ここではクォートなしアトムのテストは難しいので、小文字アトムで確認
        # Scanner logic: text[0].isupper() or text[0] == "_" -> TokenType.VARIABLE
        # else -> TokenType.ATOM
        # So, 'Atom' would be a Variable. 'atom' is an Atom.
        # '日本語アトム' is identified as a variable by VariableMapper.
        # To test atoms explicitly:
        fact = self._scan_and_parse_fact("p(an_atom).")
        self.assertIsNotNone(fact)
        self.assertIsInstance(fact.head.args[0], Atom)
        self.assertEqual(fact.head.args[0].name, "an_atom")

        # 日本語アトム: VariableMapperが日本語を変数として扱うため、これは変数になる
        self.setUp() # Reset mapper
        fact_jp_var = self._scan_and_parse_fact("q(日本語アトム名).") # This will be V1
        self.assertIsNotNone(fact_jp_var)
        self.assertIsInstance(fact_jp_var.head.args[0], Variable)
        self.assertEqual(fact_jp_var.head.args[0].name, "V1")
        self.assertEqual(self.variable_mapper.map_english_to_japanese("V1"), "日本語アトム名")

        # 明示的にアトムとして扱いたい日本語はシングルクォートで囲む必要がある
        # Current scanner tokenizes 'text' as STRING then Parser converts STRING token to Atom.
        self.setUp()
        fact_jp_quoted_atom = self._scan_and_parse_fact("r('これはアトム').")
        self.assertIsNotNone(fact_jp_quoted_atom)
        self.assertIsInstance(fact_jp_quoted_atom.head.args[0], Atom)
        self.assertEqual(fact_jp_quoted_atom.head.args[0].name, "これはアトム")


if __name__ == '__main__':
    unittest.main()
