import re
from typing import Dict, Tuple

class VariableMapper:
    def __init__(self):
        self._japanese_to_english: Dict[str, str] = {}
        self._english_to_japanese: Dict[str, str] = {}
        self._next_var_index = 1

    def _generate_english_var(self) -> str:
        # 内部的な英語変数を V1, V2, ... の形式で生成
        # 既存のマッピングと衝突しないようにインデックスを調整
        while True:
            var_name = f"V{self._next_var_index}"
            if var_name not in self._english_to_japanese:
                self._next_var_index += 1
                return var_name
            self._next_var_index += 1


    def map_japanese_to_english(self, japanese_var: str) -> str:
        if not self.is_japanese_variable(japanese_var):
            # 日本語変数でない場合はそのまま返すか、エラーを出すか検討。
            # 設計書では Validator を別途設けるような記述はないが、
            # ここではひとまずそのまま返し、呼び出し元で is_japanese_variable を使う想定とする。
            return japanese_var

        if japanese_var in self._japanese_to_english:
            return self._japanese_to_english[japanese_var]

        english_var = self._generate_english_var()
        self._japanese_to_english[japanese_var] = english_var
        self._english_to_japanese[english_var] = japanese_var
        return english_var

    def map_english_to_japanese(self, english_var: str) -> str:
        return self._english_to_japanese.get(english_var, english_var)

    def is_japanese_variable(self, var_name: str) -> bool:
        # 設計書に基づいた日本語変数の定義
        # - ひらがな、カタカナ、漢字で始まる
        # - Unicode 文字クラス：Hiragana, Katakana, CJK Unified Ideographs
        # - 英数字、アンダースコアとの組み合わせ可
        if not var_name:
            return False

        # 最初の文字が日本語文字かチェック
        # ぀-ゟ : Hiragana
        # ゠-ヿ : Katakana
        # 一-鿿 : CJK Unified Ideographs
        # 々-〇 : CJK Symbols and Punctuation (々, 〆, 〇) - これらも変数名に含めるか検討
        first_char_is_japanese = bool(re.match(r'^[぀-ゟ゠-ヿ一-鿿]', var_name[0]))

        if not first_char_is_japanese:
            return False

        # 2文字目以降は英数字、アンダースコア、日本語文字が使える
        # ^[日本語文字][日本語文字_英数字]*$
        return bool(re.match(r'^[぀-ゟ゠-ヿ一-鿿][぀-ゟ゠-ヿ一-鿿\w]*$', var_name))

    def clear_mapping(self):
        self._japanese_to_english.clear()
        self._english_to_japanese.clear()
        self._next_var_index = 1

    def get_all_mappings(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        return self._japanese_to_english.copy(), self._english_to_japanese.copy()

    def get_japanese_to_english_map(self) -> Dict[str, str]:
        return self._japanese_to_english.copy()

    def get_english_to_japanese_map(self) -> Dict[str, str]:
        return self._english_to_japanese.copy()
