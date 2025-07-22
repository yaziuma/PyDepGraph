from dataclasses import dataclass, field
from typing import List, Union

# 先に PrologType の前方参照を定義
PrologType = Union[
    "Atom", "Variable", "Number", "String", "Term", "ListTerm"
]  # ListTerm を追加


@dataclass
class BaseTerm:  # Termの基底クラス
    pass


@dataclass
class Atom(BaseTerm):
    name: str

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Atom) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


@dataclass
class Variable(BaseTerm):
    name: str

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


@dataclass
class Number(BaseTerm):
    value: Union[int, float]

    def __repr__(self):
        return str(self.value)

    def __eq__(self, other):
        return isinstance(other, Number) and self.value == other.value

    def __hash__(self):
        return hash(self.value)


@dataclass
class String(BaseTerm):
    value: str

    def __repr__(self):
        return f"'{self.value}'"

    def __eq__(self, other):
        return isinstance(other, String) and self.value == other.value

    def __hash__(self):
        return hash(self.value)


@dataclass
class Term(BaseTerm):
    functor: Atom  # 述語名 (アトム)
    args: List[PrologType] = field(default_factory=list)

    def __repr__(self):
        if not self.args:
            return repr(self.functor)
        return f"{repr(self.functor)}({', '.join(map(repr, self.args))})"

    def __eq__(self, other):
        return (
            isinstance(other, Term)
            and self.functor == other.functor
            and self.args == other.args
        )

    def __hash__(self):
        # args をタプルに変換してハッシュ可能にする
        # また、args の要素もハッシュ可能である必要がある
        # ここでは、args の要素が PrologType であることを前提とする
        # リストはハッシュ可能でないため、タプルに変換
        try:
            return hash((self.functor, tuple(self.args)))
        except TypeError:  # args にハッシュ不可能な要素が含まれる場合
            # このような Term は辞書のキーやセットの要素として使えない
            # 必要であれば、より堅牢なハッシュ戦略を検討
            return id(self)  # オブジェクトIDに基づくフォールバック (非推奨だが一時的)


@dataclass
class ListTerm(
    BaseTerm
):  # パーサーが直接 '.'/2 を生成する場合、このクラスは高レベル表現
    elements: List[PrologType] = field(default_factory=list)
    # Prologのリストの末尾は通常 '[]' (アトム) または別のリスト (部分リストの場合は変数)
    tail: Union[Variable, Atom, "ListTerm", None] = None

    def to_internal_list_term(self) -> PrologType:  # Changed Term to PrologType
        """Prologの内部リスト表現 ('.'/2 と '[]') に変換する"""
        current_list_tail: PrologType
        if self.tail is None:
            current_list_tail = Atom("[]")
        elif isinstance(self.tail, ListTerm):  # ネストされたListTermの場合
            current_list_tail = self.tail.to_internal_list_term()
        else:  # Atom('[]') または Variable
            current_list_tail = self.tail

        if not self.elements:
            return current_list_tail

        result = current_list_tail
        for element in reversed(self.elements):
            result = Term(Atom("."), [element, result])
        return result

    def __repr__(self):
        if not self.elements:
            return repr(self.tail) if self.tail is not None else "[]"

        s_elements = ", ".join(map(repr, self.elements))
        if self.tail is not None and not (
            isinstance(self.tail, Atom) and self.tail.name == "[]"
        ):
            return f"[{s_elements} | {repr(self.tail)}]"
        else:  # tail が None または Atom("[]")
            return f"[{s_elements}]"

    def __eq__(self, other):
        if not isinstance(other, ListTerm):
            # ListTerm と Term('.`, H, T) の比較も考慮するべきか？
            # ここでは ListTerm 同士の比較のみ
            return False
        return self.elements == other.elements and self.tail == other.tail

    def __hash__(self):
        # elements と tail がハッシュ可能である必要がある
        try:
            return hash((tuple(self.elements), self.tail))
        except TypeError:
            return id(self)


@dataclass
class Rule:
    head: Term
    body: Term

    def __repr__(self):
        return f"{repr(self.head)} :- {repr(self.body)}."

    def __eq__(self, other):
        return (
            isinstance(other, Rule)
            and self.head == other.head
            and self.body == other.body
        )

    def __hash__(self):
        return hash((self.head, self.body))


@dataclass
class Fact:
    head: Term

    def __repr__(self):
        return f"{repr(self.head)}."

    def __eq__(self, other):
        return isinstance(other, Fact) and self.head == other.head

    def __hash__(self):
        return hash(self.head)
