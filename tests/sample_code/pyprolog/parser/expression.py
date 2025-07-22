from abc import ABC, abstractmethod


class Visitor(ABC):
    """Visitor pattern for expression evaluation"""

    @abstractmethod
    def visit_binary(self, expr):
        pass

    @abstractmethod
    def visit_primary(self, expr):
        pass


class Expression(ABC):
    """Base class for expressions"""

    @abstractmethod
    def accept(self, visitor):
        pass


class BinaryExpression(Expression):
    """Binary expression like 'a + b' or 'x > y'"""

    def __init__(self, left, operand, right):
        self.left = left
        self.operand = operand
        self.right = right

    def accept(self, visitor):
        return visitor.visit_binary(self)

    def __str__(self):
        return f"({self.left} {self.operand} {self.right})"

    def __repr__(self):
        return str(self)


class PrimaryExpression(Expression):
    """Primary expression like a number or variable"""

    def __init__(self, exp):
        self.exp = exp

    def accept(self, visitor):
        return visitor.visit_primary(self)

    def __str__(self):
        return str(self.exp)

    def __repr__(self):
        return str(self)
