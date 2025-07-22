# prolog/runtime/io_streams.py
from abc import ABC, abstractmethod
import sys
from typing import List, Optional  # For Python list type hint in StringStream

# To use 'PrologType' as a type hint, it would typically be imported:
# from prolog.core.types import PrologType
# However, to avoid potential circular dependencies at this stage of module creation,
# we can use it as a string literal in type hints: 'PrologType'.


class IOStream(ABC):
    """
    Abstract base class for Prolog I/O streams.
    Defines the interface for reading and writing characters and terms.
    """

    @abstractmethod
    def read_char(self) -> str:
        """
        Reads a single character from the stream.
        Returns the character read.
        Should raise an appropriate exception on EOF or error.
        """
        pass

    @abstractmethod
    def read_line(self) -> Optional[str]:
        """
        Reads a line from the stream (up to and including newline).
        Returns the line without the newline character.
        Returns None on EOF.
        """
        pass

    @abstractmethod
    def write_char(self, char: str) -> None:
        """
        Writes a single character to the stream.
        """
        pass

    @abstractmethod
    def read_term(self) -> "PrologType":
        """
        Reads a Prolog term from the stream.
        Returns the Prolog term.
        Should handle parsing and raise appropriate exceptions on syntax error or EOF.
        """
        pass

    @abstractmethod
    def write_term(self, term: "PrologType") -> None:
        """
        Writes a Prolog term to the stream.
        Should handle term serialization.
        """
        pass


class ConsoleStream(IOStream):
    """
    Concrete IOStream implementation for standard console I/O.
    """

    def __init__(self):
        super().__init__()
        # No specific initialization needed for stdin/stdout if using sys directly.

    def write_char(self, char: str) -> None:
        sys.stdout.write(char)
        sys.stdout.flush()

    def read_char(self) -> str:
        # sys.stdin.read(1) can be blocking and platform-dependent for raw char reads.
        # For simple line-buffered input or when input is redirected from a file, it's okay.
        # Returns empty string "" on EOF.
        return sys.stdin.read(1)

    def read_line(self) -> Optional[str]:
        # Read a line from stdin, strip the newline character
        try:
            line = sys.stdin.readline()
            if line == "":  # EOF
                return None
            if line.endswith('\n'):
                return line[:-1]
            return line
        except EOFError:
            return None

    def read_term(self) -> "PrologType":
        # This will require a parser integrated with the stream.
        raise NotImplementedError("ConsoleStream.read_term() is not yet implemented.")

    def write_term(self, term: "PrologType") -> None:
        # This will require a term serializer.
        raise NotImplementedError("ConsoleStream.write_term() is not yet implemented.")


class StringStream(IOStream):
    """
    Concrete IOStream implementation for reading from and writing to strings/buffers.
    """

    def __init__(self, initial_input: str = "", output_buffer: List[str] = None):
        super().__init__()
        self.input_string = initial_input
        self.read_position = 0
        # Ensure output_buffer is a list. If None is passed, create a new list.
        self.output_buffer: List[str] = (
            output_buffer if output_buffer is not None else []
        )

    def write_char(self, char: str) -> None:
        self.output_buffer.append(char)

    def read_char(self) -> str:
        if self.read_position < len(self.input_string):
            char = self.input_string[self.read_position]
            self.read_position += 1
            return char
        else:
            return ""  # Signify EOF

    def read_line(self) -> Optional[str]:
        if self.read_position >= len(self.input_string):
            return None  # EOF - return None to distinguish from empty line
        
        # Find the next newline character
        newline_pos = self.input_string.find('\n', self.read_position)
        
        if newline_pos == -1:
            # No newline found, return rest of string
            line = self.input_string[self.read_position:]
            self.read_position = len(self.input_string)
            return line
        else:
            # Newline found, return line without newline
            line = self.input_string[self.read_position:newline_pos]
            self.read_position = newline_pos + 1  # Skip the newline
            return line

    def get_output_string(self) -> str:
        """Helper method to get the accumulated output as a single string."""
        return "".join(self.output_buffer)

    def clear_output_buffer(self) -> None:
        """Helper method to clear the output buffer."""
        self.output_buffer.clear()

    def reset_input(self, new_input_string: str = "") -> None:
        """Helper method to reset or set a new input string."""
        self.input_string = new_input_string
        self.read_position = 0

    def read_term(self) -> "PrologType":
        # This will require a parser integrated with the stream (reading from self.input_string).
        raise NotImplementedError("StringStream.read_term() is not yet implemented.")

    def write_term(self, term: "PrologType") -> None:
        # This will require a term serializer (writing to self.output_buffer).
        raise NotImplementedError("StringStream.write_term() is not yet implemented.")
