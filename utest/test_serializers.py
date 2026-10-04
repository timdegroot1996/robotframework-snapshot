from datetime import datetime
from decimal import Decimal

import pytest

from SnapshotLibrary import serializers


def test_text_gets_one_trailing_newline_and_unix_line_endings():
    data, ext = serializers.to_data("a\r\nb\r\n\r\n")
    assert ext == "txt"
    assert serializers.render(data, ext) == "a\nb\n"


def test_dict_is_sorted_indented_json():
    data, ext = serializers.to_data({"b": 1, "a": [1, 2]})
    assert ext == "json"
    assert serializers.render(data, ext) == '{\n  "a": [\n    1,\n    2\n  ],\n  "b": 1\n}\n'


def test_key_order_does_not_matter():
    first = serializers.render(*serializers.to_data({"a": 1, "b": 2}))
    second = serializers.render(*serializers.to_data({"b": 2, "a": 1}))
    assert first == second


def test_non_json_types_are_converted():
    value = {1: (1, 2), "when": datetime(2026, 1, 2, 3, 4, 5), "price": Decimal("1.10"), "tags": {"b", "a"}}
    data, _ = serializers.to_data(value)
    assert data == {"1": [1, 2], "when": "2026-01-02T03:04:05", "price": "1.10", "tags": ["a", "b"]}


def test_unicode_is_kept_readable():
    assert "é" in serializers.render(*serializers.to_data({"name": "café"}))


def test_json_string_is_canonicalised_with_format_json():
    data, ext = serializers.to_data('{"b":1,"a":2}', "json")
    assert ext == "json"
    assert serializers.render(data, ext) == '{\n  "a": 2,\n  "b": 1\n}\n'


def test_invalid_json_string_with_format_json_fails():
    with pytest.raises(ValueError, match="not valid JSON"):
        serializers.to_data("nope", "json")


def test_format_text_forces_text():
    data, ext = serializers.to_data(42, "text")
    assert (data, ext) == ("42", "txt")


def test_unknown_format_fails():
    with pytest.raises(ValueError, match="Unknown snapshot format"):
        serializers.to_data("x", "yaml")


def test_table_rows_are_one_line_each_and_valid_json():
    import json

    rows = [["2026-01-01", "suite", 3, None], ["2026-01-02", "other", 4, 1.5]]
    text = serializers.render(*serializers.to_data(rows))
    assert text == '[\n  ["2026-01-01", "suite", 3, null],\n  ["2026-01-02", "other", 4, 1.5]\n]\n'
    assert json.loads(text) == rows


def test_scalar_list_as_dict_value_stays_one_value_per_line():
    text = serializers.render(*serializers.to_data({"data": [1, 2]}))
    assert text == '{\n  "data": [\n    1,\n    2\n  ]\n}\n'


def test_empty_containers_and_nested_output_is_valid_json():
    import json

    value = {"a": [], "b": {}, "c": [{"x": [1, [2, 3]]}, []], "d": 'quote " and \\ backslash'}
    assert json.loads(serializers.render(*serializers.to_data(value))) == value
