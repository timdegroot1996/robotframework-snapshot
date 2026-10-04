"""Turn arbitrary values into stable, readable text."""

from __future__ import annotations

import json
from collections.abc import Mapping, Set
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import PurePath
from typing import Any, Tuple
from xml.dom import minidom
from xml.etree import ElementTree

TEXT = "txt"
JSON = "json"
XML = "xml"
FORMATS = ("auto", "text", "json", "xml")


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


def _is_xml_element(value: Any) -> bool:
    if isinstance(value, ElementTree.ElementTree):
        return True
    if type(value).__module__.startswith("lxml"):
        return hasattr(value, "tag") or hasattr(value, "getroot")
    return isinstance(value, ElementTree.Element)


def _element_to_string(value: Any) -> str:
    if type(value).__module__.startswith("lxml"):
        from lxml import etree

        return etree.tostring(value, encoding="unicode")
    if isinstance(value, ElementTree.ElementTree):
        value = value.getroot()
    return ElementTree.tostring(value, encoding="unicode")


def canonical_xml(source: str) -> str:
    """Canonical XML (C14N 2.0), indented two spaces per level.

    Attributes are sorted, comments, the XML declaration and the doctype are
    dropped, and whitespace around text and between elements is not
    significant.
    """
    try:
        canonical = ElementTree.canonicalize(source, strip_text=True)
    except ElementTree.ParseError as error:
        raise ValueError(f"format=xml was given but the value is not valid XML: {error}") from None
    return minidom.parseString(canonical).documentElement.toprettyxml(indent="  ")


def to_data(value: Any, fmt: str = "auto") -> Tuple[Any, str]:
    """Return ``(data, extension)``.

    ``data`` is a string for text and XML snapshots and a JSON-compatible
    structure for JSON snapshots. Masking by JSONPath happens on that structure before
    it is written out with `render`.
    """
    fmt = (fmt or "auto").lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unknown snapshot format '{fmt}'. Use one of: {', '.join(FORMATS)}.")
    if fmt in ("auto", "xml") and _is_xml_element(value):
        return canonical_xml(_element_to_string(value)), XML
    if fmt == "xml":
        if not isinstance(value, (str, bytes)):
            raise ValueError(f"format=xml needs an XML string or element, got {type(value).__name__}.")
        # bytes go to the parser as they are, so an encoding declaration is honoured
        return canonical_xml(value), XML
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
