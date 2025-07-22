# pyprolog/runtime/__init__.py
from .interpreter import Runtime

# from .builtins import Fail, Cut, Write, Nl, Tab, Retract # These are not currently defined as classes in builtins.py
from .builtins import (
    DynamicAssertAPredicate as AssertA,
)  # Assuming AssertA is DynamicAssertAPredicate
from .builtins import (
    DynamicAssertZPredicate as AssertZ,
)  # Assuming AssertZ is DynamicAssertZPredicate
from .logic_interpreter import LogicInterpreter
from .math_interpreter import MathInterpreter

__all__ = [
    "Runtime",
    "LogicInterpreter",
    "MathInterpreter",
    # "Fail",
    # "Cut",
    # "Write",
    # "Nl",
    # "Tab",
    # "Retract",
    "AssertA",  # Now aliased to DynamicAssertAPredicate
    "AssertZ",  # Now aliased to DynamicAssertZPredicate
]
