# tests/extractors/test_cross_file_resolver.py
import pytest
from pathlib import Path
import tempfile
import shutil
import textwrap

# The extractor we are going to extend
from pydepgraph.extractors.code2flow_extractor import Code2FlowExtractor
from pydepgraph.extractors.base import RawExtractionResult

@pytest.fixture
def cross_file_project():
    """Creates a sample project with cross-file calls for resolver testing."""
    project_dir = Path(tempfile.mkdtemp())

    # File with definitions
    (project_dir / "definitions.py").write_text(textwrap.dedent("""\
        def top_level_func():
            return "original"

        class MyClass:
            def __init__(self):
                pass

            def instance_method(self, value):
                return f"processed: {value}"

            @staticmethod
            def static_method():
                return "static"
    """))

    # File with calls
    (project_dir / "caller.py").write_text(textwrap.dedent("""\
        import definitions
        from definitions import MyClass
        from definitions import top_level_func as aliased_func

        class CallerClass:
            def do_stuff(self):
                # Call 1: via module
                definitions.top_level_func()

                # Call 2: via imported class
                instance = MyClass()
                instance.instance_method(1)

                # Call 3: via aliased function import
                aliased_func()

                # Call 4: to a method on self
                self.helper_method()

                # Call 5: to a built-in, should be ignored
                print("done")

            def helper_method(self):
                return "helper"

        def main():
            # Call 6: direct call to static method
            MyClass.static_method()

            # Call 7: another call
            c = CallerClass()
            c.do_stuff()

    """))

    yield str(project_dir)
    shutil.rmtree(project_dir)


def test_cross_file_call_resolution(cross_file_project):
    """
    Tests that the enhanced extractor can resolve function and method
    calls that cross file boundaries.
    """
    # This import will be for the *enhanced* extractor.
    # The current implementation will likely fail this test.
    from pydepgraph.extractors.code2flow_extractor import Code2FlowExtractor

    project_path = cross_file_project
    # For this test, we need to ensure we use the new AST-based analysis.
    # We will later modify the extractor to perhaps accept an "ast_only" mode.
    extractor = Code2FlowExtractor(ast_mode=True)
    result = extractor.extract(project_path)

    assert isinstance(result, RawExtractionResult)

    # We only care about FunctionCall relationships for this test
    calls = [
        rel["data"] for rel in result.relationships
        if rel.get("type") == "FunctionCall"
    ]

    # Create a set of (source_fqn, target_fqn) tuples for easy checking
    call_pairs = {(call["source_function"], call["target_function"]) for call in calls}

    # Expected calls to be resolved.
    # Note: `__init__` calls are not explicitly traced by this logic.
    expected_calls = {
        # Call 1
        ("caller.CallerClass.do_stuff", "definitions.top_level_func"),
        # Call 2
        ("caller.CallerClass.do_stuff", "definitions.MyClass.instance_method"),
        # Call 3
        ("caller.CallerClass.do_stuff", "definitions.top_level_func"),
        # Call 4
        ("caller.CallerClass.do_stuff", "caller.CallerClass.helper_method"),
        # Call 6
        ("caller.main", "definitions.MyClass.static_method"),
        # Call 7
        ("caller.main", "caller.CallerClass.do_stuff"),
    }

    # Add print statements for debugging
    print("\\nResolved call pairs:")
    for pair in sorted(list(call_pairs)):
        print(f"  {pair}")

    print("\\nExpected call pairs:")
    for pair in sorted(list(expected_calls)):
        print(f"  {pair}")

    # Check that all expected calls were found
    assert expected_calls.issubset(call_pairs)

    # We also check that calls to built-ins like print() are not present
    for source, target in call_pairs:
        assert "print" not in target
