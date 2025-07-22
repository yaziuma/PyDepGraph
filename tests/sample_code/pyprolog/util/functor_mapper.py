import re
from typing import Dict, Tuple, Set, Optional, List, Union
import logging

logger = logging.getLogger(__name__)


class FunctorMapper:
    """ファンクター名の非ASCII⇔英語マッピング管理"""
    
    def __init__(self, existing_functors: Optional[Set[str]] = None):
        self._non_ascii_to_english: Dict[str, str] = {}
        self._english_to_non_ascii: Dict[str, str] = {}
        self._next_functor_index: int = 1
        self._existing_functors: Set[str] = existing_functors or set()
        logger.debug(f"FunctorMapper initialized with {len(self._existing_functors)} existing functors")

    def register_existing_functors(self, functors: Set[str]):
        """既存ファンクター名を登録（衝突回避用）"""
        self._existing_functors.update(functors)
        logger.debug(f"Registered {len(functors)} additional functors. Total: {len(self._existing_functors)}")

    def _generate_safe_english_functor(self) -> str:
        """
        安全な英語ファンクター名生成：
        - プレフィックス: MAPPED_ （衝突回避）
        - 形式: MAPPED_F1, MAPPED_F2, ...
        - 既存ファンクターとの衝突チェック
        """
        while True:
            # より安全なプレフィックスを使用
            candidate = f"MAPPED_F{self._next_functor_index}"
            
            # 既存ファンクターとの衝突チェック
            if (candidate not in self._english_to_non_ascii and 
                candidate not in self._existing_functors):
                self._next_functor_index += 1
                return candidate
                
            self._next_functor_index += 1

    def map_non_ascii_to_english(self, functor: str) -> str:
        """非ASCII文字を含むファンクター名を英語に変換"""
        if not self.needs_mapping(functor):
            return functor  # マッピング不要な場合はそのまま返す

        if functor in self._non_ascii_to_english:
            return self._non_ascii_to_english[functor]

        # 新規マッピング作成（安全性チェック付き）
        english_functor = self._generate_safe_english_functor()
        self._non_ascii_to_english[functor] = english_functor
        self._english_to_non_ascii[english_functor] = functor

        logger.debug(f"Mapped non-ASCII functor '{functor}' to '{english_functor}'")
        return english_functor

    def map_english_to_non_ascii(self, english_functor: str) -> str:
        """英語ファンクター名を元の形に復元"""
        return self._english_to_non_ascii.get(english_functor, english_functor)

    def needs_mapping(self, name: str) -> bool:
        """
        マッピングが必要な文字の判定条件：
        1. ASCII範囲外の文字を含む（Unicode全般）
        2. Prolog識別子として安全でない文字を含む
        3. 既存の英語ファンクターでない
        """
        if not name:
            return False
        
        # ASCII範囲外の文字が含まれているかチェック
        has_non_ascii = any(ord(char) > 127 for char in name)
        
        # Prolog識別子として問題のある文字をチェック（基本的な区切り文字）
        unsafe_chars = re.search(r'[()[\]{}.,;:!|"\'`~@#$%^&*+=<>?/\\]', name)
        
        # ただし、既に登録済みの英語ファンクターは除外
        if name in self._existing_functors and not has_non_ascii:
            return False
            
        return has_non_ascii or bool(unsafe_chars)

    def _is_valid_identifier_char(self, char: str) -> bool:
        """識別子として有効な文字かチェック"""
        if not char:
            return False
        
        # 基本的な制御文字や区切り文字は除外
        invalid_chars = set('()[]{}.,;:!|"\'`~@#$%^&*+-=<>?/\\')
        return char not in invalid_chars and not char.isspace()

    def extract_functors_from_string(self, prolog_string: str) -> Set[str]:
        """Prolog文字列から基本的なファンクター名を抽出（簡易版）"""
        functors = set()
        
        # 簡易的な正規表現でファンクター名を抽出
        # この実装は基本的なケースに対応し、完全な解析は後でParserで行う
        functor_pattern = r'\b([a-zA-Z][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(functor_pattern, prolog_string)
        
        for match in matches:
            functors.add(match)
            
        return functors

    def clear_mapping(self):
        """マッピング情報をクリア"""
        self._non_ascii_to_english.clear()
        self._english_to_non_ascii.clear()
        self._next_functor_index = 1
        logger.debug("FunctorMapper mapping cleared")

    def get_all_mappings(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """全マッピング情報を取得"""
        return self._non_ascii_to_english.copy(), self._english_to_non_ascii.copy()

    def get_non_ascii_to_english_map(self) -> Dict[str, str]:
        """非ASCII→英語マッピング辞書を取得"""
        return self._non_ascii_to_english.copy()

    def get_english_to_non_ascii_map(self) -> Dict[str, str]:
        """英語→非ASCIIマッピング辞書を取得"""
        return self._english_to_non_ascii.copy()

    def get_existing_functors(self) -> Set[str]:
        """登録済み既存ファンクター名を取得"""
        return self._existing_functors.copy()

    # 後方互換性のためのメソッド（既存のインターフェースを維持）
    def map_japanese_to_english(self, japanese_functor: str) -> str:
        """日本語ファンクター名を英語に変換（後方互換性用）"""
        return self.map_non_ascii_to_english(japanese_functor)

    def map_english_to_japanese(self, english_functor: str) -> str:
        """英語ファンクター名を日本語に復元（後方互換性用）"""
        return self.map_english_to_non_ascii(english_functor)

    def is_japanese_functor(self, name: str) -> bool:
        """日本語ファンクター名かどうかを判定（後方互換性用）"""
        if not name:
            return False
        # 日本語文字が含まれているかチェック
        japanese_chars = re.search(r'[ぁ-ゟ゠-ヿ一-鿿]', name)
        return japanese_chars is not None