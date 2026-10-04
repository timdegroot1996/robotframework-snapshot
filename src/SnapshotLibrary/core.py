"""The snapshot decision logic, free of any Robot Framework dependency."""

from __future__ import annotations

import copy
import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, List, Optional

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
