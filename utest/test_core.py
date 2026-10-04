import pytest

from SnapshotLibrary import core, normalizers, store
from SnapshotLibrary.core import Outcome


def test_missing_snapshot_is_recorded(tmp_path):
    path = tmp_path / "s" / "t.txt"
    result = core.check(path, "hello\n")
    assert result.outcome is Outcome.RECORDED and result.passed
    assert path.read_text(encoding="utf-8") == "hello\n"


def test_matching_snapshot_passes_and_is_untouched(tmp_path):
    path = tmp_path / "t.txt"
    store.write(path, "hello\n")
    before = path.stat().st_mtime_ns
    assert core.check(path, "hello\n").outcome is Outcome.MATCHED
    assert path.stat().st_mtime_ns == before


def test_mismatch_fails_with_diff_and_keeps_snapshot(tmp_path):
    path = tmp_path / "t.txt"
    store.write(path, "a\nb\n")
    result = core.check(path, "a\nc\n")
    assert result.outcome is Outcome.MISMATCH and not result.passed
    assert "-b" in result.diff and "+c" in result.diff
    assert store.read(path) == "a\nb\n"


def test_update_overwrites(tmp_path):
    path = tmp_path / "t.txt"
    store.write(path, "old\n")
    assert core.check(path, "new\n", update=True).outcome is Outcome.UPDATED
    assert store.read(path) == "new\n"


def test_strict_fails_on_missing_and_writes_nothing(tmp_path):
    path = tmp_path / "t.txt"
    assert core.check(path, "x\n", strict=True).outcome is Outcome.MISSING
    assert not path.exists()


def test_update_wins_over_strict(tmp_path):
    path = tmp_path / "t.txt"
    assert core.check(path, "x\n", update=True, strict=True).outcome is Outcome.RECORDED


def test_snapshot_with_windows_line_endings_still_matches(tmp_path):
    path = tmp_path / "t.txt"
    path.write_bytes(b"a\r\nb\r\n")
    assert core.check(path, "a\nb\n").outcome is Outcome.MATCHED


def test_prepare_masks_then_normalizes():
    value = {"id": 7, "at": "2026-01-02 03:04:05", "name": "x"}
    text, ext = core.prepare(value, ignore="$.id", normalizers=[normalizers.builtin("timestamp")])
    assert ext == "json"
    assert '"id": "<IGNORED>"' in text and '"at": "<TIMESTAMP>"' in text


def test_prepare_does_not_modify_the_callers_value():
    value = {"id": 7}
    core.prepare(value, ignore="$.id")
    assert value == {"id": 7}


def test_ignore_on_plain_text_explains_what_to_do():
    with pytest.raises(ValueError, match="normalizer"):
        core.prepare("plain", ignore="$.id")


def test_split_paths():
    assert core.split_paths("$.a; $.b") == ["$.a", "$.b"]
    assert core.split_paths(["$.a"]) == ["$.a"]
    assert core.split_paths(None) == []


@pytest.mark.parametrize(
    "name, index, expected",
    [(None, 1, "My_Test.txt"), (None, 2, "My_Test__2.txt"), ("runs table", 1, "My_Test__runs_table.txt")],
)
def test_snapshot_path(tmp_path, name, index, expected):
    path = store.snapshot_path(tmp_path, "01_suite", "My Test", "txt", name, index)
    assert path == tmp_path / "01_suite" / expected


def test_sanitize_keeps_unicode_and_rejects_empty():
    assert store.sanitize("Prüfe: Größe/Übersicht") == "Prüfe_Größe_Übersicht"
    with pytest.raises(ValueError):
        store.sanitize("///")


def test_shared_snapshot_path_has_no_test_name(tmp_path):
    path = store.snapshot_path(tmp_path, "00_cli", "Any Test", "txt", "help", shared=True)
    assert path == tmp_path / "00_cli" / "help.txt"


def test_shared_snapshot_needs_a_name(tmp_path):
    with pytest.raises(ValueError, match="needs a name"):
        store.snapshot_path(tmp_path, "s", "t", "txt", None, shared=True)


# -- failure message -----------------------------------------------------------

def _robot_would_cut(message, max_lines):
    from robot.utils import text

    old = text.MAX_ERROR_LINES
    text.MAX_ERROR_LINES = max_lines
    try:
        return text.cut_long_message(message) != message
    finally:
        text.MAX_ERROR_LINES = old


def _diff(count, width=10):
    return [f"-{'x' * width} {n}" for n in range(count)]


def test_short_diff_is_shown_whole():
    message, omitted = core.mismatch_message("a.txt", _diff(5), 40)
    assert omitted == 0
    assert message.count("\n-") == 5
    assert "more diff line" not in message
    assert message.endswith(core.UPDATE_HINT)


@pytest.mark.parametrize("max_lines", [11, 20, 40, 100])
@pytest.mark.parametrize("width", [10, 100, 300])
def test_long_diff_is_shortened_so_robot_does_not_cut_it(max_lines, width):
    diff = _diff(500, width)
    message, omitted = core.mismatch_message("a.txt", diff, max_lines)
    assert omitted > 0
    assert not _robot_would_cut(message, max_lines)
    assert message.startswith("Snapshot 'a.txt' does not match.\n" + diff[0][:20])
    assert "more diff lines. The full diff is in the log; run with --maxerrorlines NONE" in message
    assert message.endswith(core.UPDATE_HINT)


def test_count_of_omitted_lines_is_right():
    message, omitted = core.mismatch_message("a.txt", _diff(100), 40)
    assert omitted == 100 - message.count("\n-")
    assert f"... {omitted} more diff lines." in message


def test_no_limit_shows_everything():
    message, omitted = core.mismatch_message("a.txt", _diff(500), None)
    assert omitted == 0
    assert message.count("\n-") == 500
    assert "more diff line" not in message
