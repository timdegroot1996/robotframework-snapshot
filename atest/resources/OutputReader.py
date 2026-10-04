"""Reads the output.xml of a run started by `Run Tests`."""

from robot.api import ExecutionResult
from robot.api.deco import keyword, library


@library(scope="TEST")
class OutputReader:
    def __init__(self):
        self._tests = {}
        self._warnings = []

    @keyword
    def read_output(self, path):
        result = ExecutionResult(path)
        self._tests = {test.name: test for test in result.suite.all_tests}
        self._warnings = [message.message for message in result.errors.messages if message.level == "WARN"]

    @keyword
    def test_status_should_be(self, status, *names):
        """Fails unless every test in ``names`` ended with ``status``."""
        for name in names:
            actual = self._test(name).status
            if actual != status:
                raise AssertionError(f"Test '{name}' should be {status} but was {actual}: {self._test(name).message}")

    @keyword
    def get_test_message(self, name):
        return self._test(name).message

    @keyword
    def get_warnings(self):
        return list(self._warnings)

    def _test(self, name):
        if name not in self._tests:
            raise AssertionError(f"No test '{name}' in the run. Tests: {', '.join(self._tests) or 'none'}.")
        return self._tests[name]
