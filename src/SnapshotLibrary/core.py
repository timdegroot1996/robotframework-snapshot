"""The snapshot decision logic, free of any Robot Framework dependency."""

from __future__ import annotations

import copy
import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, List, Optional

from . import jsonpath, serializers, store
from .scrubbers import Scrubber, apply_all


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
    scrubbers: Iterable[Scrubber] = (),
):
    """Serialise, mask and scrub ``value``. Returns ``(text, extension)``."""
    data, extension = serializers.to_data(value, fmt)
    paths = split_paths(ignore)
    if paths:
        if extension != serializers.JSON:
            raise ValueError(
                "ignore= takes JSONPath expressions and needs structured data. "
                "Pass a dictionary or list, use format=json for a JSON string, "
                "or use a scrubber for plain text."
            )
        data = copy.deepcopy(data)
        for path in paths:
            jsonpath.mask(data, path)
    text = serializers.render(data, extension)
    text = apply_all(text, scrubbers)
    return serializers.normalize_text(text), extension


def unified_diff(expected: str, actual: str, label: str) -> List[str]:
    return list(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=f"snapshot: {label}",
            tofile="actual",
            lineterm="",
        )
    )


def check(path: Path, actual: str, update: bool = False, strict: bool = False, label: str = "") -> Result:
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
    diff = unified_diff(expected, actual, label or path.name)
    return Result(Outcome.MISMATCH, path, actual, expected, diff)
