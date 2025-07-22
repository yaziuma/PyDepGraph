class InterpreterError(Exception):
    pass


class ScannerError(Exception):
    pass


class ParserError(Exception):
    pass


class PrologError(Exception):
    pass


class UnificationError(Exception):
    pass


class CutException(Exception):
    """カット演算子 (!) が実行されたことを示す例外"""

    pass
