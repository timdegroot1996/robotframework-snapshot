"""Turn arbitrary values into stable, readable text."""

from __future__ import annotations

import json
from collections.abc import Mapping, Set
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import PurePath
from typing import Any, Tuple

TEXT = "txt"
JSON = "json"
FORMATS = ("auto", "text", "json")


def normalize_text(text: str) -> str:
    """Normalise line endings and end the text with exactly one newline."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n") + "\n"


def to_plain(value: Any) -> Any:
    """Reduce ``value`` to JSON-compatible types with a deterministic layout."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(item) for item in value]
    if isinstance(value, Set):
        return sorted((to_plain(item) for item in value), key=repr)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (Decimal, PurePath)):
        return str(value)
    return str(value)


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _dump(value: Any, indent: int, in_list: bool) -> str:
    pad, inner = "  " * indent, "  " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [
            f"{inner}{_scalar(key)}: {_dump(value[key], indent + 1, False)}"
            for key in sorted(value)
        ]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        # A row of a table: a list of plain values inside another list.
        # Kept on one line, so a changed row is one changed line in the diff.
        if in_list and all(_is_scalar(item) for item in value):
            return "[" + ", ".join(_scalar(item) for item in value) + "]"
        items = [f"{inner}{_dump(item, indent + 1, True)}" for item in value]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return _scalar(value)


def dump_json(data: Any) -> str:
    """Valid JSON with sorted keys, two-space indent and one table row per line."""
    return _dump(data, 0, False) + "\n"


def to_data(value: Any, fmt: str = "auto") -> Tuple[Any, str]:
    """Return ``(data, extension)``.

    ``data`` is a string for text snapshots and a JSON-compatible structure
    for JSON snapshots. Masking by JSONPath happens on that structure before
    it is written out with `render`.
    """
    fmt = (fmt or "auto").lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unknown snapshot format '{fmt}'. Use one of: {', '.join(FORMATS)}.")
    if isinstance(value, bytes) and fmt != "json":
        value = value.decode("utf-8", errors="replace")
    if fmt == "text":
        return (value if isinstance(value, str) else str(value)), TEXT
    if fmt == "json":
        if isinstance(value, (str, bytes)):
            try:
                value = json.loads(value)
            except ValueError as error:
                raise ValueError(f"format=json was given but the value is not valid JSON: {error}") from None
        return to_plain(value), JSON
    if isinstance(value, str):
        return value, TEXT
    return to_plain(value), JSON


def render(data: Any, extension: str) -> str:
    if extension == JSON:
        return dump_json(data)
    return normalize_text(data)
