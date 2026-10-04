"""Normalizers replace changing text, such as timestamps and IDs, with fixed placeholders."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Union

_STAMP = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?"
_OFFSET = r"(?:Z|[+-]\d{2}:?\d{2})"


@dataclass(frozen=True)
class Normalizer:
    name: str
    apply: Callable[[str], str]


def regex_normalizer(name: str, pattern: str, replacement: str) -> Normalizer:
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"Normalizer '{name}' has an invalid pattern: {error}") from None
    return Normalizer(name, lambda text: compiled.sub(replacement, text))


def _path_normalizer() -> Normalizer:
    def apply(text: str) -> str:
        roots: Dict[str, str] = {}
        for label, root in (
            ("<CWD>", os.getcwd()),
            ("<TMP>", tempfile.gettempdir()),
            ("<HOME>", str(Path.home())),
        ):
            if root and len(root) > 1:
                roots.setdefault(root, label)
        # Longest root first, so a temp dir inside the home dir wins over <HOME>.
        for root in sorted(roots, key=len, reverse=True):
            for variant in {root, root.replace("\\", "/"), root.replace("\\", "\\\\")}:
                text = text.replace(variant, roots[root])
        return text

    return Normalizer("path", apply)


def _builtin() -> Dict[str, Normalizer]:
    return {
        "timestamp": regex_normalizer("timestamp", _STAMP + _OFFSET + "?", "<TIMESTAMP>"),
        "timezone": regex_normalizer("timezone", f"({_STAMP}){_OFFSET}", r"\1<TZ>"),
        "uuid": regex_normalizer(
            "uuid",
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "<UUID>",
        ),
        "duration": regex_normalizer(
            "duration",
            r"\b\d+(?:\.\d+)?\s?(?:milliseconds|seconds|ms|sec|s)\b",
            "<DURATION>",
        ),
        "path": _path_normalizer(),
    }


BUILTIN_NAMES = ("timestamp", "timezone", "uuid", "duration", "path")


def builtin(name: str) -> Normalizer:
    normalizers = _builtin()
    key = name.strip().lower()
    if key not in normalizers:
        raise ValueError(
            f"Unknown normalizer '{name}'. Built-in normalizers: {', '.join(BUILTIN_NAMES)}. "
            "Register your own with `Add Snapshot Normalizer`."
        )
    return normalizers[key]


def split_names(names: Optional[Union[str, Iterable[str]]]) -> List[str]:
    if not names:
        return []
    if isinstance(names, str):
        names = names.split(",")
    return [str(name).strip() for name in names if str(name).strip()]


def apply_all(text: str, normalizers: Iterable[Normalizer]) -> str:
    for normalizer in normalizers:
        text = normalizer.apply(text)
    return text
