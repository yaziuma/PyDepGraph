import unittest
from pyprolog.util.variable_mapper import VariableMapper

class TestVariableMapper(unittest.TestCase):

    def setUp(self):
        self.mapper = VariableMapper()

    def test_is_japanese_variable_valid(self):
        self.assertTrue(self.mapper.is_japanese_variable("あ"))
        self.assertTrue(self.mapper.is_japanese_variable("ア"))
        self.assertTrue(self.mapper.is_japanese_variable("漢"))
        self.assertTrue(self.mapper.is_japanese_variable("変数"))
        self.assertTrue(self.mapper.is_japanese_variable("日本語変数"))
        self.assertTrue(self.mapper.is_japanese_variable("変数1"))
        self.assertTrue(self.mapper.is_japanese_variable("変数_テスト"))
        self.assertTrue(self.mapper.is_japanese_variable("あいうえお"))
        self.assertTrue(self.mapper.is_japanese_variable("カタカナ"))
        self.assertTrue(self.mapper.is_japanese_variable("漢字テスト"))

    def test_is_japanese_variable_invalid(self):
        self.assertFalse(self.mapper.is_japanese_variable("English"))
        self.assertFalse(self.mapper.is_japanese_variable("X"))
        self.assertFalse(self.mapper.is_japanese_variable("_Variable"))
        self.assertFalse(self.mapper.is_japanese_variable("1Variable"))
        self.assertFalse(self.mapper.is_japanese_variable(""))
        self.assertFalse(self.mapper.is_japanese_variable(" Variable")) # 先頭スペース
        self.assertFalse(self.mapper.is_japanese_variable("English変数")) # 英語で始まる

    def test_map_japanese_to_english_basic(self):
        self.assertEqual(self.mapper.map_japanese_to_english("変数"), "V1")
        self.assertEqual(self.mapper.map_japanese_to_english("テスト"), "V2")
        self.assertEqual(self.mapper.map_japanese_to_english("あいう"), "V3")

    def test_map_japanese_to_english_identity_for_non_japanese(self):
        self.assertEqual(self.mapper.map_japanese_to_english("X"), "X")
        self.assertEqual(self.mapper.map_japanese_to_english("Var"), "Var")

    def test_map_japanese_to_english_consistent_mapping(self):
        self.assertEqual(self.mapper.map_japanese_to_english("変数"), "V1")
        self.assertEqual(self.mapper.map_japanese_to_english("変数"), "V1") # 再度同じものをマップ
        self.assertEqual(self.mapper.map_japanese_to_english("テスト"), "V2")

    def test_map_english_to_japanese_basic(self):
        self.mapper.map_japanese_to_english("変数") # V1
        self.mapper.map_japanese_to_english("テスト") # V2
        self.assertEqual(self.mapper.map_english_to_japanese("V1"), "変数")
        self.assertEqual(self.mapper.map_english_to_japanese("V2"), "テスト")

    def test_map_english_to_japanese_unmapped(self):
        self.assertEqual(self.mapper.map_english_to_japanese("V99"), "V99")
        self.assertEqual(self.mapper.map_english_to_japanese("X"), "X")

    def test_clear_mapping(self):
        self.mapper.map_japanese_to_english("変数")
        self.mapper.map_japanese_to_english("テスト")
        self.mapper.clear_mapping()
        self.assertEqual(self.mapper.map_japanese_to_english("変数"), "V1") # クリア後はV1から
        self.assertEqual(self.mapper.map_english_to_japanese("V1"), "変数")
        j_to_e, e_to_j = self.mapper.get_all_mappings()
        self.assertEqual(len(j_to_e), 1)
        self.assertEqual(len(e_to_j), 1)
        self.mapper.clear_mapping()
        j_to_e, e_to_j = self.mapper.get_all_mappings()
        self.assertEqual(len(j_to_e), 0)
        self.assertEqual(len(e_to_j), 0)


    def test_get_all_mappings(self):
        self.mapper.map_japanese_to_english("変数１") # V1
        self.mapper.map_japanese_to_english("変数２") # V2
        j_to_e, e_to_j = self.mapper.get_all_mappings()
        self.assertEqual(j_to_e, {"変数１": "V1", "変数２": "V2"})
        self.assertEqual(e_to_j, {"V1": "変数１", "V2": "変数２"})

    def test_generate_english_var_collision_avoidance(self):
        # 事前に英語変数をいくつか手動で（VariableMapperの外部で）使われていると仮定し、
        # VariableMapperがそれらを避けて新しい内部変数を生成するか。
        # このテストは現在の VariableMapper の実装では直接テストしづらいが、
        # _generate_english_var が _english_to_japanese を参照しているため、
        # map_japanese_to_english を繰り返せば内部的に衝突回避が行われるはず。
        self.mapper._english_to_japanese["V1"] = "外部変数1" # 外部でV1が使われたと仮定
        self.mapper._next_var_index = 1 # インデックスをリセットして衝突を誘発

        self.assertEqual(self.mapper.map_japanese_to_english("最初の内部変数"), "V2") # V1を避けてV2になるはず
        self.assertEqual(self.mapper.map_japanese_to_english("次の内部変数"), "V3")

if __name__ == '__main__':
    unittest.main()
