"""The snapshot decision logic, free of any Robot Framework dependency."""

from __future__ import annotations

import copy
import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

from . import jsonpath, serializers, store, xmlpath
from .normalizers import Normalizer, apply_all


class Outcome(Enum):
    MATCHED = "matched"
    RECORDED = "recorded"
    UPDATED = "updated"
    MISSING = "missing"
    MISMATCH = "mismatch"


@dataclass
class Result:
    outcome: Outcome
    path: Path
    actual: str
    expected: Optional[str] = None
    diff: Optional[List[str]] = None

    @property
    def passed(self) -> bool:
        return self.outcome in (Outcome.MATCHED, Outcome.RECORDED, Outcome.UPDATED)


def split_paths(ignore) -> List[str]:
    """``ignore`` is one JSONPath, several separated by ``;``, or a list."""
    if not ignore:
        return []
    if isinstance(ignore, str):
        ignore = ignore.split(";")
    return [str(path).strip() for path in ignore if str(path).strip()]


def prepare(
    value: Any,
    fmt: str = "auto",
    ignore=None,
    normalizers: Iterable[Normalizer] = (),
):
    """Serialise, mask and normalise ``value``. Returns ``(text, extension)``."""
    data, extension = serializers.to_data(value, fmt)
    paths = split_paths(ignore)
    if paths:
        if extension == serializers.JSON:
            data = copy.deepcopy(data)
            for path in paths:
                jsonpath.mask(data, path)
        elif extension == serializers.XML:
            data = serializers.canonical_xml(xmlpath.mask(data, paths))
        else:
            raise ValueError(
                "ignore= needs structured data: JSONPath for a dictionary, a list or "
                "a JSON string with format=json, XPath for XML with format=xml. "
                "For plain text, use a normalizer."
            )
    text = serializers.render(data, extension)
    text = apply_all(text, normalizers)
    return serializers.normalize_text(text), extension


UPDATE_HINT = "If the change is intended, update the snapshot with: --variable REFERENCE_RUN:True"
# Robot Framework counts a message line longer than this as several lines
# when it checks a failure message against --maxerrorlines.
_MESSAGE_LINE_WIDTH = 78


def _message_lines(lines: Iterable[str]) -> int:
    return sum(max(1, -(-len(line) // _MESSAGE_LINE_WIDTH)) for line in lines)


def _omitted_note(count: int) -> str:
    return (
        f"... {count} more diff line{'s' if count != 1 else ''}. The full diff is in the log; "
        "run with --maxerrorlines NONE to show it here."
    )


def mismatch_message(label: str, diff: List[str], max_lines: Optional[int] = None) -> Tuple[str, int]:
    """The failure message for a snapshot that does not match, and how many diff lines it leaves out.

    Robot Framework removes the middle of a failure message that is longer
    than ``max_lines`` (its ``--maxerrorlines``, ``None`` for no limit). To
    keep the start of the diff readable the message is shortened here
    instead: diff lines are shown from the top until the limit is reached,
    followed by a note on how to see the rest.
    """
    header = [f"Snapshot '{label}' does not match."]
    footer = ["", UPDATE_HINT]
    if max_lines is None or _message_lines(header + diff + footer) <= max_lines:
        return "\n".join(header + diff + footer), 0
    budget = max_lines - _message_lines(header + footer + [_omitted_note(len(diff))])
    shown: List[str] = []
    for line in diff:
        if _message_lines(shown + [line]) > budget:
            break
        shown.append(line)
    omitted = len(diff) - len(shown)
    return "\n".join(header + shown + [_omitted_note(omitted)] + footer), omitted


def unified_diff(expected: str, actual: str) -> List[str]:
    # No path in the header: every message that shows a diff already names the snapshot.
    return list(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="snapshot",
            tofile="actual",
            lineterm="",
        )
    )


def check(path: Path, actual: str, update: bool = False, strict: bool = False) -> Result:
    """Compare ``actual`` with the snapshot at ``path`` and record or update as the mode allows.

    | Mode    | Snapshot missing | Snapshot differs |
    | default | record           | mismatch         |
    | update  | record           | overwrite        |
    | strict  | missing          | mismatch         |

    ``update`` wins over ``strict`` when both are set.
    """
    path = Path(path)
    if not path.is_file():
        if strict and not update:
            return Result(Outcome.MISSING, path, actual)
        store.write(path, actual)
        return Result(Outcome.RECORDED, path, actual)
    expected = store.read(path)
    if expected == actual:
        return Result(Outcome.MATCHED, path, actual, expected)
    if update:
        store.write(path, actual)
        return Result(Outcome.UPDATED, path, actual, expected)
    diff = unified_diff(expected, actual)
    return Result(Outcome.MISMATCH, path, actual, expected, diff)
