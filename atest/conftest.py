import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from robot.api import ExecutionResult

SUITES = Path(__file__).parent / "suites"


class Run:
    def __init__(self, returncode, output_xml, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.result = ExecutionResult(str(output_xml))
        self.tests = {test.name: test for test in self.result.suite.all_tests}
        self.warnings = [message.message for message in self.result.errors.messages]

    def status(self, name):
        return self.tests[name].status

    def message(self, name):
        return self.tests[name].message


class Workspace:
    """A copy of the acceptance suites in a temp dir, so runs can record freely."""

    def __init__(self, root: Path):
        self.root = root
        self.suites = root / "suites"
        shutil.copytree(SUITES, self.suites)
        self.runs = 0

    def snapshots(self, suite: str) -> Path:
        return self.suites / "__snapshots__" / suite

    def run(self, suite: str, *options: str, runner=("robot",), **variables) -> Run:
        self.runs += 1
        out = self.root / f"out{self.runs}"
        args = [sys.executable, "-m", *_module(runner), "--outputdir", str(out), "--log", "NONE", "--report", "NONE"]
        for name, value in variables.items():
            args += ["--variable", f"{name}:{value}"]
        args += [*options, str(self.suites / suite) if suite else str(self.suites)]
        done = subprocess.run(args, cwd=self.root, capture_output=True, text=True, env=_env())
        return Run(done.returncode, out / "output.xml", done.stdout + done.stderr)


def _module(runner):
    return ("robot",) if runner[0] == "robot" else ("pabot.pabot", *runner[1:])


def _env():
    # pabot starts `robot` from PATH, so put this interpreter's scripts first
    # in case the virtual environment is not activated.
    scripts = Path(sys.executable).parent
    return {**os.environ, "PATH": f"{scripts}{os.pathsep}{os.environ.get('PATH', '')}"}


def unused_cli(output_directory, *options, cwd=None):
    done = subprocess.run(
        [sys.executable, "-m", "SnapshotLibrary", "unused", str(output_directory), *options],
        cwd=cwd, capture_output=True, text=True,
    )
    return done.returncode, done.stdout + done.stderr


@pytest.fixture
def workspace(tmp_path):
    return Workspace(tmp_path)
