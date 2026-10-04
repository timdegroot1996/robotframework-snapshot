from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any, List, Optional, Union

from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import is_truthy

from . import core, scrubbers as scrubbing, serializers, store, unused as usage_tracking
from .core import Outcome
from .version import __version__

ACTUAL_DIR_NAME = "snapshot_actual"
MAX_DIFF_LINES_IN_MESSAGE = 40
SCOPES = ("test", "suite", "global")


@library(scope="GLOBAL", version=__version__, doc_format="ROBOT")
class SnapshotLibrary:
    """Snapshot testing for text and structured data.

    The first run records the actual value to a file. Later runs compare
    against it. You review expected values as file diffs in version control
    instead of writing them by hand.

    | *** Settings ***
    | Library    SnapshotLibrary
    |
    | *** Test Cases ***
    | Help Text Is Stable
    |     ${result}=    Run Process    mytool    --help
    |     Should Match Snapshot    ${result.stdout}
    |
    | Order Has Expected Body
    |     ${response}=    GET    ${URL}/orders/42
    |     Should Match Snapshot    ${response.json()}    ignore=$.updated_at

    = Snapshot lifecycle =

    | =Mode=  | =How to enable=                      | =Snapshot missing=             | =Snapshot differs=   |
    | Default | nothing                              | Recorded, passes with a warning | Fails with a diff    |
    | Update  | ``--variable REFERENCE_RUN:True``    | Recorded                       | Overwritten, passes  |
    | Strict  | ``--variable SNAPSHOT_STRICT:True`` or ``strict=True`` | Fails          | Fails with a diff    |

    Use strict mode in CI, so a snapshot that was never committed fails the
    build instead of being recorded on the build machine.

    = Where snapshots are stored =

    Snapshots are plain files meant to be committed:
    ``__snapshots__/<suite file name>/<test name>.<ext>`` next to the suite
    file. Text is stored as ``.txt``, dictionaries and lists as sorted,
    indented ``.json``. A second snapshot in the same test gets the suffix
    ``__2``, or ``__<name>`` when ``name=`` is given. With ``shared=True``
    the file is ``<name>.<ext>`` without the test name, so several tests can
    compare against one snapshot. A list of rows is written one row per line.

    = Volatile values =

    Scrubbers replace volatile text with placeholders before comparing and
    before recording. Built in: ``timestamp``, ``timezone``, ``uuid``,
    ``duration`` and ``path``. Add your own with `Add Snapshot Scrubber`.
    For structured data, ``ignore=`` masks values by JSONPath.

    = Unused snapshots =

    When a test is renamed or removed, its snapshot file stays behind. At the
    end of each suite the library warns about files in that suite's snapshot
    directory that no test used. It only does so when every test of the suite
    ran and passed, because a filtered, skipped or failed test would make its
    snapshot look unused. Turn the warning off with ``warn_unused=False``.

    A parallel run with ``pabot --testlevelsplit`` runs each test in its own
    process, so no process sees a whole suite. Check such a run afterwards,
    from the command line:

    | python -m SnapshotLibrary unused <output directory>
    | python -m SnapshotLibrary unused <output directory> --delete

    The command exits with 1 when it finds unused snapshots, so it can fail a
    build. It also reports snapshot directories whose suite file is gone.

    = Images, PDFs and screenshots =

    This library does not compare visual content. Use
    [https://github.com/manykarim/robotframework-doctestlibrary|DocTestLibrary]
    for that. Its baseline lifecycle inspired this library, and both use the
    same ``REFERENCE_RUN`` variable, so one command updates snapshots and
    visual baselines together.
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(
        self,
        snapshot_directory: Optional[str] = None,
        scrubbers: Optional[Union[str, List[str]]] = None,
        strict: bool = False,
        warn_unused: bool = True,
    ):
        """
        | =Argument= | =Description= |
        | ``snapshot_directory`` | Directory for all snapshots. Relative paths resolve against ``${EXECDIR}``. Default: ``__snapshots__`` next to each suite file. |
        | ``scrubbers`` | Built-in scrubbers applied to every snapshot, comma separated, for example ``timestamp,uuid``. |
        | ``strict`` | Fail when a snapshot is missing instead of recording it. Can also be set per run with ``--variable SNAPSHOT_STRICT:True``. |
        | ``warn_unused`` | Warn at the end of a suite about snapshot files no test used. See `Unused snapshots`. |
        """
        # The library is its own listener (API v3), to know when tests and suites start and end.
        self.ROBOT_LIBRARY_LISTENER = self
        self.snapshot_directory = snapshot_directory
        self.strict = is_truthy(strict)
        self.warn_unused = is_truthy(warn_unused)
        self._usage: List[usage_tracking.SuiteUsage] = []
        self._global_scrubbers = [scrubbing.builtin(name) for name in scrubbing.split_names(scrubbers)]
        self._suite_scrubbers: List[List[scrubbing.Scrubber]] = []
        self._test_scrubbers: List[scrubbing.Scrubber] = []
        self._unnamed_count = 0

    # -- listener: scopes and per-test numbering ---------------------------

    def _start_suite(self, data, result):
        self._suite_scrubbers.append([])
        self._unnamed_count = 0
        if data.parent is None:
            output_dir = self._variable("${OUTPUT DIR}")
            if output_dir:
                usage_tracking.clear_records(output_dir)
        self._usage.append(usage_tracking.SuiteUsage(str(data.source or ""), self._count_tests(data.source)))

    def _end_suite(self, data, result):
        if self._suite_scrubbers:
            self._suite_scrubbers.pop()
        if self._usage:
            self._close_usage(self._usage.pop(), data, result)

    def _start_test(self, data, result):
        self._test_scrubbers = []
        self._unnamed_count = 0

    def _end_test(self, data, result):
        self._test_scrubbers = []
        self._unnamed_count = 0
        if self._usage:
            self._usage[-1].ran[result.name] = result.status

    # -- unused snapshots ----------------------------------------------------

    @staticmethod
    def _count_tests(source) -> Optional[int]:
        """Number of tests the suite file defines, to notice a filtered run."""
        if not source:
            return None
        source = Path(source)
        if source.is_dir():
            return 0
        try:
            from robot.api import TestSuite

            return len(TestSuite.from_file_system(str(source)).tests)
        except Exception:  # an unreadable suite must never break the run
            return None

    def _is_dry_run(self) -> bool:
        try:
            from robot.running.context import EXECUTION_CONTEXTS

            return bool(EXECUTION_CONTEXTS.current.dry_run)
        except Exception:
            return False

    def _close_usage(self, usage, data, result):
        if not usage.source or self._is_dry_run():
            return
        own_tests_only = Path(usage.source).is_file()
        # A directory suite fails when any test below it fails; that says nothing
        # about its own snapshots, but there is no cheaper safe signal.
        usage.suite_passed = True if own_tests_only else bool(result.passed)
        # has_setup first: a suite without setup still has a placeholder object whose status is FAIL
        if own_tests_only and (
            (result.has_setup and result.setup.failed) or (result.has_teardown and result.teardown.failed)
        ):
            usage.suite_passed = False
        default_directory = self._snapshot_base(Path(usage.source)) / store.sanitize(self._suite_folder(Path(usage.source)))
        usage.directories.add(str(default_directory))
        output_dir = self._variable("${OUTPUT DIR}")
        if output_dir:
            try:
                usage_tracking.write_record(output_dir, usage)
            except OSError as error:
                logger.debug(f"Could not write the snapshot usage record: {error}")
        if self.warn_unused and usage.complete:
            unused = usage.unused()
            if unused:
                listing = ", ".join(self._label(path) for path in unused)
                logger.warn(
                    f"Unused snapshot{'s' if len(unused) > 1 else ''}: {listing}. "
                    "No test used them in this run. Delete them if they are no longer needed."
                )

    def _mark_used(self, path: Path):
        if self._usage:
            self._usage[-1].used.add(str(path))
            self._usage[-1].directories.add(str(path.parent))

    # -- keywords ----------------------------------------------------------

    @keyword
    def should_match_snapshot(
        self,
        value: Any,
        name: Optional[str] = None,
        ignore: Optional[Union[str, List[str]]] = None,
        scrubbers: Optional[Union[str, List[str]]] = None,
        format: str = "auto",
        shared: bool = False,
    ):
        """Compares ``value`` with its stored snapshot.

        If the snapshot does not exist yet it is recorded and the keyword
        passes with a warning. See `Snapshot lifecycle` for update and strict
        mode.

        | =Argument= | =Description= |
        | ``value`` | A string, or anything that can be written as JSON: dictionary, list, number, boolean. |
        | ``name`` | Name for this snapshot. Needed only to give several snapshots in one test readable file names. |
        | ``ignore`` | JSONPath of values to mask in structured data, for example ``$.id`` or ``$..updated_at``. Several paths: separate with ``;`` or pass a list. |
        | ``scrubbers`` | Extra scrubbers for this call only, comma separated. |
        | ``format`` | ``auto`` (default), ``text`` or ``json``. Use ``json`` to store a JSON string in canonical form. |
        | ``shared`` | Store the snapshot under ``name`` alone, without the test name, so several tests in the suite compare against the same file. Needs ``name``. |

        Examples:
        | `Should Match Snapshot`    ${output}
        | `Should Match Snapshot`    ${rows}    name=runs    scrubbers=timezone
        | `Should Match Snapshot`    ${response.json()}    ignore=$.id;$..updated_at
        | `Should Match Snapshot`    ${response.text}    format=json
        | `Should Match Snapshot`    ${help_text}    name=help    shared=True
        """
        text, extension = core.prepare(value, format, ignore, self._active_scrubbers(scrubbers))
        self._assert(text, extension, name, shared)

    @keyword
    def should_match_file_snapshot(
        self,
        path: str,
        name: Optional[str] = None,
        scrubbers: Optional[Union[str, List[str]]] = None,
        encoding: str = "UTF-8",
        shared: bool = False,
    ):
        """Compares the text content of the file at ``path`` with its stored snapshot.

        Use it for files the system under test produced: reports, exports,
        generated configuration. The snapshot keeps the file's extension.

        Examples:
        | `Should Match File Snapshot`    ${OUTPUT_DIR}/export.csv
        | `Should Match File Snapshot`    ${TEMPDIR}/report.html    scrubbers=timestamp
        """
        source = Path(path)
        if not source.is_file():
            raise AssertionError(f"File '{path}' does not exist.")
        with open(source, "r", encoding=encoding, newline="") as file:
            content = file.read()
        text, _ = core.prepare(content, "text", None, self._active_scrubbers(scrubbers))
        extension = source.suffix.lstrip(".") or serializers.TEXT
        self._assert(text, extension, name, shared)

    @keyword
    def add_snapshot_scrubber(
        self,
        name: str,
        pattern: Optional[str] = None,
        replacement: Optional[str] = None,
        scope: str = "suite",
    ):
        """Adds a scrubber that replaces volatile text before comparing and recording.

        With only ``name`` a built-in scrubber is enabled: ``timestamp``,
        ``timezone``, ``uuid``, ``duration`` or ``path``. With ``pattern`` a
        custom one is registered; ``replacement`` defaults to ``<NAME>`` and
        may use regular expression groups such as ``\\\\1``.

        ``scope`` is ``test``, ``suite`` (default) or ``global``. A test-scoped
        scrubber is dropped when the test ends, a suite-scoped one when the
        suite ends.

        Examples:
        | `Add Snapshot Scrubber`    timestamp
        | `Add Snapshot Scrubber`    order_id    pattern=ORD-\\\\d+    scope=test
        | `Add Snapshot Scrubber`    port    pattern=(localhost):\\\\d+    replacement=\\\\1:<PORT>
        """
        scope = scope.strip().lower()
        if scope not in SCOPES:
            raise ValueError(f"Unknown scope '{scope}'. Use one of: {', '.join(SCOPES)}.")
        if pattern is None:
            scrubber = scrubbing.builtin(name)
        else:
            if replacement is None:
                replacement = f"<{name.upper()}>"
            scrubber = scrubbing.regex_scrubber(name, pattern, replacement)
        if scope == "global":
            self._global_scrubbers.append(scrubber)
        elif scope == "test" and self._in_test():
            self._test_scrubbers.append(scrubber)
        else:
            if not self._suite_scrubbers:
                self._suite_scrubbers.append([])
            self._suite_scrubbers[-1].append(scrubber)

    @keyword
    def set_snapshot_directory(self, snapshot_directory: Optional[str] = None) -> Optional[str]:
        """Changes the directory snapshots are stored in and returns the previous setting.

        Relative paths resolve against ``${EXECDIR}``. Without an argument the
        default is restored: ``__snapshots__`` next to each suite file.

        Example:
        | ${previous}=    `Set Snapshot Directory`    ${EXECDIR}/snapshots/staging
        """
        previous = self.snapshot_directory
        self.snapshot_directory = snapshot_directory or None
        return previous

    @keyword
    def get_snapshot(self, name: Optional[str] = None, shared: bool = False) -> Any:
        """Returns the stored snapshot, for custom assertions.

        JSON snapshots are returned as dictionaries or lists, everything else
        as a string. Without ``name`` the first unnamed snapshot of the
        current test is returned. Fails if the snapshot does not exist.

        Example:
        | ${stored}=    `Get Snapshot`    name=runs
        """
        base = self._path(name, "*", index=1, shared=shared).with_suffix("")
        matches = sorted(base.parent.glob(base.name + ".*")) if base.parent.is_dir() else []
        matches = [match for match in matches if match.stem == base.name]
        if not matches:
            raise AssertionError(f"Snapshot '{self._label(base)}.*' does not exist.")
        self._mark_used(matches[0])
        text = store.read(matches[0])
        if matches[0].suffix == "." + serializers.JSON:
            return json.loads(text)
        return text

    # -- internals ---------------------------------------------------------

    def _assert(self, text: str, extension: str, name: Optional[str], shared: bool = False):
        if name:
            index = 1
        else:
            self._unnamed_count += 1
            index = self._unnamed_count
        path = self._path(name, extension, index, shared)
        self._mark_used(path)
        label = self._label(path)
        update = is_truthy(self._variable("${REFERENCE_RUN}", False))
        strict = self.strict or is_truthy(self._variable("${SNAPSHOT_STRICT}", False))
        result = core.check(path, text, update=update, strict=strict, label=label)

        if result.outcome is Outcome.MATCHED:
            logger.info(f"Snapshot '{label}' matches.")
        elif result.outcome is Outcome.RECORDED:
            message = f"Snapshot '{label}' did not exist and was recorded. Review and commit it."
            if update:
                logger.info(message)
            else:
                logger.warn(message)
        elif result.outcome is Outcome.UPDATED:
            self._log_diff(core.unified_diff(result.expected, result.actual, label))
            logger.info(f"Reference run: snapshot '{label}' was updated.")
        elif result.outcome is Outcome.MISSING:
            raise AssertionError(
                f"Snapshot '{label}' does not exist and strict mode is on. "
                "Record it locally (run without strict mode) and commit the file."
            )
        else:
            actual_path = self._save_actual(path, text)
            self._log_diff(result.diff)
            if actual_path:
                logger.info(f"Actual value saved to '{actual_path}'.")
            shown = result.diff[:MAX_DIFF_LINES_IN_MESSAGE]
            if len(result.diff) > len(shown):
                shown.append(f"... {len(result.diff) - len(shown)} more diff lines in the log")
            raise AssertionError(
                f"Snapshot '{label}' does not match.\n"
                + "\n".join(shown)
                + "\n\nIf the change is intended, update the snapshot with: --variable REFERENCE_RUN:True"
            )

    def _active_scrubbers(self, extra) -> List[scrubbing.Scrubber]:
        active = list(self._global_scrubbers)
        for suite_level in self._suite_scrubbers:
            active.extend(suite_level)
        active.extend(self._test_scrubbers)
        known = {scrubber.name: scrubber for scrubber in active}
        for name in scrubbing.split_names(extra):
            active.append(known.get(name) or scrubbing.builtin(name))
        return active

    def _variable(self, name: str, default=None):
        return BuiltIn().get_variable_value(name, default)

    def _in_test(self) -> bool:
        return bool(self._variable("${TEST NAME}"))

    def _exec_dir(self) -> Path:
        return Path(self._variable("${EXECDIR}", os.getcwd()))

    @staticmethod
    def _suite_folder(source: Path) -> str:
        return "__init__" if source.is_dir() else source.stem

    def _snapshot_base(self, source: Optional[Path]) -> Path:
        """The directory that holds the per-suite snapshot folders."""
        if self.snapshot_directory:
            base = Path(self.snapshot_directory)
            return base if base.is_absolute() else self._exec_dir() / base
        if source is None:
            return self._exec_dir() / store.SNAPSHOT_DIR_NAME
        directory = source if source.is_dir() else source.parent
        return directory / store.SNAPSHOT_DIR_NAME

    def _path(self, name: Optional[str], extension: str, index: int, shared: bool = False) -> Path:
        source = self._variable("${SUITE SOURCE}")
        source = Path(source) if source else None
        suite = self._suite_folder(source) if source else self._variable("${SUITE NAME}", "suite")
        base = self._snapshot_base(source)
        test = self._variable("${TEST NAME}") or "__suite__"
        if extension == "*":
            return store.snapshot_path(base, suite, test, "x", name, index, shared).with_suffix(".*")
        return store.snapshot_path(base, suite, test, extension, name, index, shared)

    def _label(self, path: Path) -> str:
        try:
            return Path(os.path.relpath(path, self._exec_dir())).as_posix()
        except ValueError:  # different drive on Windows
            return path.as_posix()

    def _save_actual(self, snapshot: Path, text: str) -> Optional[Path]:
        output_dir = self._variable("${OUTPUT DIR}")
        if not output_dir:
            return None
        target = Path(output_dir) / ACTUAL_DIR_NAME / snapshot.parent.name / snapshot.name
        try:
            store.write(target, text)
        except OSError as error:
            logger.debug(f"Could not save the actual value: {error}")
            return None
        return target

    @staticmethod
    def _log_diff(diff: List[str]):
        if not diff:
            return
        styles = {"+": "color:#1a7f37", "-": "color:#cf222e", "@": "color:#6e7781"}
        lines = []
        for line in diff:
            style = styles.get(line[:1], "")
            escaped = html.escape(line)
            lines.append(f'<span style="{style}">{escaped}</span>' if style else escaped)
        logger.info('<pre style="margin:0">' + "\n".join(lines) + "</pre>", html=True)
