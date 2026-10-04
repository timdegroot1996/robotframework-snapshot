"""Scrubbers replace volatile text with stable placeholders."""

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
class Scrubber:
    name: str
    apply: Callable[[str], str]


def regex_scrubber(name: str, pattern: str, replacement: str) -> Scrubber:
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"Scrubber '{name}' has an invalid pattern: {error}") from None
    return Scrubber(name, lambda text: compiled.sub(replacement, text))


def _path_scrubber() -> Scrubber:
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

    return Scrubber("path", apply)


def _builtin() -> Dict[str, Scrubber]:
    return {
        "timestamp": regex_scrubber("timestamp", _STAMP + _OFFSET + "?", "<TIMESTAMP>"),
        "timezone": regex_scrubber("timezone", f"({_STAMP}){_OFFSET}", r"\1<TZ>"),
        "uuid": regex_scrubber(
            "uuid",
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "<UUID>",
        ),
        "duration": regex_scrubber(
            "duration",
            r"\b\d+(?:\.\d+)?\s?(?:milliseconds|seconds|ms|sec|s)\b",
            "<DURATION>",
        ),
        "path": _path_scrubber(),
    }


BUILTIN_NAMES = ("timestamp", "timezone", "uuid", "duration", "path")


def builtin(name: str) -> Scrubber:
    scrubbers = _builtin()
    key = name.strip().lower()
    if key not in scrubbers:
        raise ValueError(
            f"Unknown scrubber '{name}'. Built-in scrubbers: {', '.join(BUILTIN_NAMES)}. "
            "Register your own with `Add Snapshot Scrubber`."
        )
    return scrubbers[key]


def split_names(names: Optional[Union[str, Iterable[str]]]) -> List[str]:
    if not names:
        return []
    if isinstance(names, str):
        names = names.split(",")
    return [str(name).strip() for name in names if str(name).strip()]


def apply_all(text: str, scrubbers: Iterable[Scrubber]) -> str:
    for scrubber in scrubbers:
        text = scrubber.apply(text)
    return text
