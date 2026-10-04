"""A small JSONPath subset used to mask values before a snapshot is taken.

Supported: ``$.key``, ``$['key']``, ``$.list[0]``, ``$.list[*]``, ``$.*`` and
the recursive ``$..key``. That covers "ignore this field wherever it is"
without adding a dependency.
"""

from __future__ import annotations

import re
from typing import Any, List, Tuple

IGNORED = "<IGNORED>"

_TOKEN = re.compile(
    r"""
    \.\.(?P<deep>[^.\[\]]+)           # ..key
  | \.(?P<key>[^.\[\]]+)              # .key or .*
  | \[\s*(?P<index>-?\d+)\s*\]        # [0]
  | \[\s*\*\s*\]                      # [*]
  | \[\s*(?P<quote>['"])(?P<qkey>.*?)(?P=quote)\s*\]   # ['key']
    """,
    re.VERBOSE,
)


def parse(path: str) -> List[Tuple[str, Any]]:
    path = path.strip()
    if not path.startswith("$"):
        raise ValueError(f"JSONPath '{path}' must start with '$'.")
    tokens: List[Tuple[str, Any]] = []
    position = 1
    while position < len(path):
        match = _TOKEN.match(path, position)
        if not match:
            raise ValueError(f"Unsupported JSONPath syntax in '{path}' at position {position}.")
        if match.group("deep") is not None:
            tokens.append(("deep", match.group("deep")))
        elif match.group("key") is not None:
            key = match.group("key")
            tokens.append(("wild", None) if key == "*" else ("key", key))
        elif match.group("index") is not None:
            tokens.append(("index", int(match.group("index"))))
        elif match.group("qkey") is not None:
            tokens.append(("key", match.group("qkey")))
        else:
            tokens.append(("wild", None))
        position = match.end()
    if not tokens:
        raise ValueError(f"JSONPath '{path}' selects the whole value; nothing would be left to compare.")
    return tokens


def _children(node: Any):
    if isinstance(node, dict):
        return list(node.keys())
    if isinstance(node, list):
        return list(range(len(node)))
    return []


def _apply(node: Any, tokens: List[Tuple[str, Any]], placeholder: str) -> int:
    kind, arg = tokens[0]
    last = len(tokens) == 1
    hits = 0

    def visit(container, key):
        nonlocal hits
        if last:
            container[key] = placeholder
            hits += 1
        else:
            hits += _apply(container[key], tokens[1:], placeholder)

    if kind == "key":
        if isinstance(node, dict) and arg in node:
            visit(node, arg)
    elif kind == "index":
        if isinstance(node, list) and -len(node) <= arg < len(node):
            visit(node, arg)
    elif kind == "wild":
        for key in _children(node):
            visit(node, key)
    elif kind == "deep":
        if isinstance(node, dict) and arg in node:
            visit(node, arg)
        for key in _children(node):
            child = node[key]
            if isinstance(child, (dict, list)) and not (last and key == arg):
                hits += _apply(child, tokens, placeholder)
    return hits


def mask(data: Any, path: str, placeholder: str = IGNORED) -> int:
    """Replace every value selected by ``path`` in place. Returns the hit count."""
    return _apply(data, parse(path), placeholder)
