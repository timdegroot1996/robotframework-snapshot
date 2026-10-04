import os
import tempfile

import pytest

from SnapshotLibrary import scrubbers


@pytest.mark.parametrize(
    "text",
    [
        "2026-08-17 02:15:12",
        "2026-08-17T02:15:12Z",
        "2026-08-17 06:00:04.123457+00:00",
        "2026-08-17T06:00:04,123-0530",
    ],
)
def test_timestamp(text):
    assert scrubbers.builtin("timestamp").apply(f"at {text} done") == "at <TIMESTAMP> done"


def test_timezone_keeps_the_time():
    apply = scrubbers.builtin("timezone").apply
    assert apply("2026-08-17 02:15:12+02:00") == "2026-08-17 02:15:12<TZ>"
    assert apply("2026-08-17 06:00:04.123457-05:00") == "2026-08-17 06:00:04.123457<TZ>"
    assert apply("2026-08-17 02:15:12") == "2026-08-17 02:15:12"


def test_uuid():
    apply = scrubbers.builtin("uuid").apply
    assert apply("id=3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90.") == "id=<UUID>."


@pytest.mark.parametrize("text", ["1.2s", "350 ms", "3 seconds", "12ms"])
def test_duration(text):
    assert scrubbers.builtin("duration").apply(f"took {text}") == "took <DURATION>"


def test_duration_leaves_plain_numbers_and_words():
    apply = scrubbers.builtin("duration").apply
    assert apply("5 suites, 12 tests") == "5 suites, 12 tests"


def test_path_replaces_cwd_and_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    apply = scrubbers.builtin("path").apply
    assert apply(f"wrote {os.getcwd()}{os.sep}out.txt") == f"wrote <CWD>{os.sep}out.txt"
    other = os.path.join(tempfile.gettempdir(), "zzz")
    assert apply(other) == f"<TMP>{os.sep}zzz"


def test_unknown_builtin_names_the_available_ones():
    with pytest.raises(ValueError, match="timestamp, timezone, uuid"):
        scrubbers.builtin("nope")


def test_regex_scrubber_with_group():
    scrubber = scrubbers.regex_scrubber("port", r"(localhost):\d+", r"\1:<PORT>")
    assert scrubber.apply("http://localhost:8123/x") == "http://localhost:<PORT>/x"


def test_invalid_regex_fails_early():
    with pytest.raises(ValueError, match="invalid pattern"):
        scrubbers.regex_scrubber("bad", "(", "x")


def test_split_names():
    assert scrubbers.split_names(" timestamp , uuid,") == ["timestamp", "uuid"]
    assert scrubbers.split_names(["a", " b "]) == ["a", "b"]
    assert scrubbers.split_names(None) == []
