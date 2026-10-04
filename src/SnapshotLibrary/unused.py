"""Find snapshot files that no test used.

Every suite writes a small usage record to ``${OUTPUT_DIR}/snapshot_usage/``.
The library warns at the end of a suite when it can judge that suite by
itself, and ``python -m SnapshotLibrary unused <output dir>`` merges the
records of a whole run, which is what a parallel run with pabot needs.

A suite is only judged when every one of its tests ran and passed. A test
that was filtered out, skipped or failed before reaching its snapshot would
otherwise make that snapshot look unused.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from . import store

USAGE_DIR_NAME = "snapshot_usage"
PASS = "PASS"


@dataclass
class SuiteUsage:
    """What one suite did with snapshots, in one process."""

    source: str
    total_tests: Optional[int]
    ran: Dict[str, str] = field(default_factory=dict)
    used: Set[str] = field(default_factory=set)
    directories: Set[str] = field(default_factory=set)
    suite_passed: bool = True

    @property
    def complete(self) -> bool:
        if self.total_tests is None or not self.suite_passed:
            return False
        if len(self.ran) < self.total_tests:
            return False
        return all(status == PASS for status in self.ran.values())

    def unused(self) -> List[Path]:
        return find_unused(self.directories, self.used)

    def merge(self, other: "SuiteUsage") -> None:
        if self.total_tests is None:
            self.total_tests = other.total_tests
        for name, status in other.ran.items():
            # a rerun that passes wins over an earlier failure
            if self.ran.get(name) != PASS:
                self.ran[name] = status
        self.used |= other.used
        self.directories |= other.directories
        self.suite_passed = self.suite_passed and other.suite_passed

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "total_tests": self.total_tests,
            "ran": self.ran,
            "used": sorted(self.used),
            "directories": sorted(self.directories),
            "suite_passed": self.suite_passed,
        }

    @classmethod
    def from_json(cls, data: dict) -> "SuiteUsage":
        return cls(
            source=data["source"],
            total_tests=data.get("total_tests"),
            ran=dict(data.get("ran", {})),
            used=set(data.get("used", [])),
            directories=set(data.get("directories", [])),
            suite_passed=bool(data.get("suite_passed", True)),
        )


def _key(path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def find_unused(directories: Iterable, used: Iterable) -> List[Path]:
    """Files in ``directories`` that are not in ``used``. Hidden files are ignored."""
    used_keys = {_key(path) for path in used}
    unused: List[Path] = []
    for directory in sorted({_key(d): Path(d) for d in directories}.values()):
        if not directory.is_dir():
            continue
        for entry in sorted(directory.iterdir()):
            if entry.is_file() and not entry.name.startswith(".") and _key(entry) not in used_keys:
                unused.append(entry)
    return unused


def write_record(output_directory, usage: SuiteUsage) -> Path:
    directory = Path(output_directory) / USAGE_DIR_NAME
    name = store.sanitize(Path(usage.source).stem or "suite")
    target = directory / f"{name}-{os.getpid()}-{abs(hash(usage.source)) % 10**8}.json"
    store.write(target, json.dumps(usage.to_json(), indent=2) + "\n")
    return target


def clear_records(output_directory) -> None:
    directory = Path(output_directory) / USAGE_DIR_NAME
    if directory.is_dir():
        for entry in directory.glob("*.json"):
            try:
                entry.unlink()
            except OSError:
                pass


def read_records(output_directory) -> List[SuiteUsage]:
    """All usage records below ``output_directory``, merged per suite file.

    The search is recursive, so the records pabot leaves in
    ``pabot_results/<n>/snapshot_usage/`` are found from the main output dir.
    """
    merged: Dict[str, SuiteUsage] = {}
    for record in sorted(Path(output_directory).rglob(f"{USAGE_DIR_NAME}/*.json")):
        try:
            usage = SuiteUsage.from_json(json.loads(record.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError):
            continue
        key = _key(usage.source)
        if key in merged:
            merged[key].merge(usage)
        else:
            merged[key] = usage
    return list(merged.values())


def orphan_directories(usages: Iterable[SuiteUsage]) -> List[Path]:
    """Snapshot directories in the default location whose suite file is gone.

    Looks at every ``__snapshots__`` directory the run touched and reports
    sub-directories that match no suite file next to it. This catches a
    renamed or deleted suite, which leaves no usage record at all.
    """
    bases = set()
    for usage in usages:
        for directory in usage.directories:
            base = Path(directory).parent
            if base.name == store.SNAPSHOT_DIR_NAME:
                bases.add(base)
    orphans: List[Path] = []
    for base in sorted(bases):
        suite_directory = base.parent
        expected = {"__init__"}
        for entry in suite_directory.iterdir():
            if entry.is_file():
                try:
                    expected.add(store.sanitize(entry.stem))
                except ValueError:
                    pass
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and entry.name not in expected:
                orphans.append(entry)
    return orphans


@dataclass
class Report:
    unused: List[Path]
    orphan_directories: List[Path]
    checked: List[str]
    not_checked: List[str]

    @property
    def clean(self) -> bool:
        return not self.unused and not self.orphan_directories


def report(output_directory) -> Optional[Report]:
    usages = read_records(output_directory)
    if not usages:
        return None
    unused: List[Path] = []
    checked: List[str] = []
    not_checked: List[str] = []
    for usage in sorted(usages, key=lambda u: u.source):
        if usage.complete:
            checked.append(usage.source)
            unused.extend(usage.unused())
        else:
            not_checked.append(usage.source)
    return Report(unused, orphan_directories(usages), checked, not_checked)
