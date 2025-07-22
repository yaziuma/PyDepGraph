# pyprolog/runtime/io_manager.py
from .io_streams import IOStream, ConsoleStream
from typing import Optional


class IOManager:
    """
    Manages the current input and output streams for the Prolog runtime.
    Allows switching streams, for example, between console and string-based I/O.
    """

    def __init__(self) -> None:
        """
        Initializes the IOManager, defaulting to console streams.
        """
        self.current_input_stream: IOStream = ConsoleStream()
        self.current_output_stream: IOStream = ConsoleStream()
        # Future extensions might include user_input, user_output, error_stream
        # self.user_input_stream: IOStream = self.current_input_stream
        # self.user_output_stream: IOStream = self.current_output_stream
        # self.error_stream: IOStream = ConsoleStream() # Example for error stream

    def set_input_stream(self, stream: IOStream) -> None:
        """
        Sets the current input stream.
        """
        self.current_input_stream = stream

    def set_output_stream(self, stream: IOStream) -> None:
        """
        Sets the current output stream.
        """
        self.current_output_stream = stream

    def get_input_stream(self) -> IOStream:
        """
        Returns the current input stream.
        """
        return self.current_input_stream

    def get_output_stream(self) -> IOStream:
        """
        Returns the current output stream.
        """
        return self.current_output_stream

    def read_char_from_current(self) -> str:
        """
        Reads a single character from the current input stream.
        """
        return self.current_input_stream.read_char()

    def read_line_from_current(self) -> Optional[str]:
        """
        Reads a line from the current input stream.
        Returns None on EOF.
        """
        return self.current_input_stream.read_line()

    def write_char_to_current(self, char: str) -> None:
        """
        Writes a single character to the current output stream.
        """
        self.current_output_stream.write_char(char)

    # Placeholder for future methods that might involve terms
    # def read_term_from_current(self) -> 'PrologType':
    #     return self.current_input_stream.read_term()

    # def write_term_to_current(self, term: 'PrologType') -> None:
    #     self.current_output_stream.write_term(term)
