import pytest

from SnapshotLibrary import jsonpath

M = jsonpath.IGNORED


def test_top_level_key():
    data = {"id": 1, "name": "a"}
    assert jsonpath.mask(data, "$.id") == 1
    assert data == {"id": M, "name": "a"}


def test_nested_key_and_bracket_notation():
    data = {"a": {"b c": 1, "d": 2}}
    jsonpath.mask(data, "$.a['b c']")
    assert data == {"a": {"b c": M, "d": 2}}


def test_index_and_wildcard():
    data = {"items": [{"id": 1, "n": "x"}, {"id": 2, "n": "y"}]}
    jsonpath.mask(data, "$.items[0].n")
    jsonpath.mask(data, "$.items[*].id")
    assert data == {"items": [{"id": M, "n": M}, {"id": M, "n": "y"}]}


def test_negative_index():
    data = [1, 2, 3]
    jsonpath.mask(data, "$[-1]")
    assert data == [1, 2, M]


def test_recursive_key():
    data = {"updated": 1, "a": [{"updated": 2, "b": {"updated": 3, "keep": 4}}]}
    assert jsonpath.mask(data, "$..updated") == 3
    assert data == {"updated": M, "a": [{"updated": M, "b": {"updated": M, "keep": 4}}]}


def test_recursive_key_with_tail():
    data = {"meta": {"ts": 1, "v": 2}, "rows": [{"meta": {"ts": 3}}]}
    jsonpath.mask(data, "$..meta.ts")
    assert data == {"meta": {"ts": M, "v": 2}, "rows": [{"meta": {"ts": M}}]}


def test_no_match_is_not_an_error():
    data = {"a": 1}
    assert jsonpath.mask(data, "$.missing.deeper") == 0
    assert data == {"a": 1}


@pytest.mark.parametrize("path", ["id", "$", "$.a[?(@.b)]", "$.a[1:2]"])
def test_unsupported_paths_fail(path):
    with pytest.raises(ValueError):
        jsonpath.mask({"a": 1}, path)
