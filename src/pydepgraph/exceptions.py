# pydepgraph/exceptions.py

class PyDepGraphError(Exception):
    """Base exception for PyDepGraph errors."""
    pass


class PrologExecutionError(PyDepGraphError):
    """Custom exception for errors during Prolog execution."""
    pass


class NormalizationError(PyDepGraphError):
    """Custom exception for errors during data normalization."""
    pass


class ExtractionError(PyDepGraphError):
    """Exception for errors during dependency extraction."""
    pass


class ConfigurationError(PyDepGraphError):
    """Exception for configuration errors."""
    pass


class DatabaseError(PyDepGraphError):
    """Exception for database operation errors."""
    pass
