"""Where snapshots live on disk and how they are read and written."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

SNAPSHOT_DIR_NAME = "__snapshots__"
_UNSAFE = re.compile(r"[^\w.-]+", re.UNICODE)


def sanitize(name: str) -> str:
    """Reduce a suite, test or snapshot name to a safe file name part."""
    cleaned = _UNSAFE.sub("_", str(name)).strip(".")
    if not cleaned.strip("_"):
        raise ValueError(f"Name '{name}' contains no characters usable in a file name.")
    return cleaned


def snapshot_path(
    base_directory: Path,
    suite: str,
    test: str,
    extension: str,
    name: Optional[str] = None,
    index: int = 1,
    shared: bool = False,
) -> Path:
    """``<base>/<suite>/<test>[__<name>|__<n>].<ext>``

    The first unnamed snapshot of a test has no suffix, later unnamed ones are
    numbered from 2 in call order. A shared snapshot is stored under its name
    alone, ``<base>/<suite>/<name>.<ext>``, so several tests can use it.
    """
    if shared:
        if not name:
            raise ValueError("A shared snapshot needs a name: use name=... together with shared=True.")
        return Path(base_directory) / sanitize(suite) / f"{sanitize(name)}.{extension}"
    stem = sanitize(test)
    if name:
        stem += "__" + sanitize(name)
    elif index > 1:
        stem += f"__{index}"
    return Path(base_directory) / sanitize(suite) / f"{stem}.{extension}"


def read(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read().replace("\r\n", "\n").replace("\r", "\n")


def write(path: Path, text: str) -> None:
    """Write atomically, so a parallel process never reads a half-written snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(temporary, "w", encoding="utf-8", newline="\n") as file:
        file.write(text)
    os.replace(temporary, path)
