"""Mask parts of an XML document by XPath before a snapshot is taken.

Uses the XPath subset of ``xml.etree.ElementTree``: ``.//tag``, ``a/b``,
``*``, ``[@attr]``, ``[@attr='value']``, ``[tag]`` and ``[1]``. A path that
ends in ``/@name`` masks that attribute instead of the element. Namespace
prefixes declared in the document can be used in the path, for example
``.//soap:Body``.
"""

from __future__ import annotations

import io
from typing import Dict, Iterable
from xml.etree import ElementTree

IGNORED = "<IGNORED>"


def _namespaces(source: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for _, (prefix, uri) in ElementTree.iterparse(io.StringIO(source), events=("start-ns",)):
        found.setdefault(prefix, uri)
    return found


def _split(path: str):
    path = path.strip()
    if not path:
        raise ValueError("An empty XPath selects nothing.")
    if path.startswith("/"):
        path = "." + path
    head, _, last = path.rpartition("/")
    if last.startswith("@"):
        return (head or "."), last[1:]
    return path, None


def _expand(name: str, namespaces: Dict[str, str]) -> str:
    prefix, colon, local = name.partition(":")
    if colon and prefix in namespaces:
        return f"{{{namespaces[prefix]}}}{local}"
    return name


def mask(source: str, paths: Iterable[str], placeholder: str = IGNORED) -> str:
    """Return ``source`` with every element or attribute selected by ``paths`` masked.

    A masked element keeps its tag and attributes, but its content is
    replaced by ``placeholder``.
    """
    namespaces = _namespaces(source)
    root = ElementTree.fromstring(source)
    for path in paths:
        element_path, attribute = _split(path)
        try:
            matches = ElementTree.ElementTree(root).findall(element_path, namespaces)
        except (SyntaxError, KeyError, TypeError) as error:
            raise ValueError(f"Unsupported XPath '{path}': {error}") from None
        for element in matches:
            if attribute is None:
                for child in list(element):
                    element.remove(child)
                element.text = placeholder
            else:
                key = _expand(attribute, namespaces)
                if key in element.attrib:
                    element.set(key, placeholder)
    # Keep the document's own prefixes instead of ns0, ns1, ...
    for prefix, uri in namespaces.items():
        try:
            ElementTree.register_namespace(prefix, uri)
        except ValueError:  # a prefix such as ns0 is reserved; ElementTree picks one itself
            pass
    return ElementTree.tostring(root, encoding="unicode")
