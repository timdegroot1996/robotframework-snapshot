from pathlib import Path

from SnapshotLibrary import __main__ as cli
from SnapshotLibrary import unused
from SnapshotLibrary.unused import SuiteUsage


def touch(path: Path, text="x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_find_unused_lists_only_unreferenced_visible_files(tmp_path):
    used = touch(tmp_path / "s" / "A.txt")
    orphan = touch(tmp_path / "s" / "Old.txt")
    touch(tmp_path / "s" / ".A.txt.123.tmp")
    (tmp_path / "s" / "sub").mkdir()
    assert unused.find_unused([tmp_path / "s", tmp_path / "missing"], [used]) == [orphan]


def test_complete_needs_every_test_to_run_and_pass():
    usage = SuiteUsage("s.robot", total_tests=2, ran={"a": "PASS", "b": "PASS"})
    assert usage.complete
    assert not SuiteUsage("s.robot", 2, {"a": "PASS"}).complete                 # filtered run
    assert not SuiteUsage("s.robot", 2, {"a": "PASS", "b": "FAIL"}).complete    # may not have reached its snapshot
    assert not SuiteUsage("s.robot", 2, {"a": "PASS", "b": "SKIP"}).complete
    assert not SuiteUsage("s.robot", None, {"a": "PASS"}).complete              # suite could not be parsed
    assert not SuiteUsage("s.robot", 1, {"a": "PASS"}, suite_passed=False).complete


def test_more_tests_than_parsed_is_complete():
    # data-driven suites generate tests at run time
    assert SuiteUsage("s.robot", 1, {"a": "PASS", "b": "PASS", "c": "PASS"}).complete


def test_merge_combines_processes_and_a_passing_rerun_wins():
    first = SuiteUsage("s.robot", 2, {"a": "PASS", "b": "FAIL"}, {"/x/a.txt"}, {"/x"})
    second = SuiteUsage("s.robot", 2, {"b": "PASS"}, {"/x/b.txt"}, {"/x"})
    first.merge(second)
    assert first.complete
    assert first.used == {"/x/a.txt", "/x/b.txt"}


def test_records_round_trip_and_merge_across_directories(tmp_path):
    snapshots = tmp_path / "tests" / "__snapshots__" / "s"
    a, b = touch(snapshots / "a.txt"), touch(snapshots / "b.txt")
    orphan = touch(snapshots / "old.txt")
    source = str(touch(tmp_path / "tests" / "s.robot"))
    # two pabot processes, one test each
    unused.write_record(tmp_path / "out" / "pabot_results" / "0", SuiteUsage(source, 2, {"a": "PASS"}, {str(a)}, {str(snapshots)}))
    unused.write_record(tmp_path / "out" / "pabot_results" / "1", SuiteUsage(source, 2, {"b": "PASS"}, {str(b)}, {str(snapshots)}))
    result = unused.report(tmp_path / "out")
    assert result.checked == [source] and result.not_checked == []
    assert result.unused == [orphan]


def test_report_skips_incomplete_suites(tmp_path):
    snapshots = tmp_path / "__snapshots__" / "s"
    touch(snapshots / "old.txt")
    source = str(touch(tmp_path / "s.robot"))
    unused.write_record(tmp_path / "out", SuiteUsage(source, 2, {"a": "PASS"}, set(), {str(snapshots)}))
    result = unused.report(tmp_path / "out")
    assert result.not_checked == [source] and result.unused == [] and result.clean


def test_report_without_records_is_none(tmp_path):
    assert unused.report(tmp_path) is None


def test_orphan_directory_of_a_removed_suite(tmp_path):
    base = tmp_path / "tests" / "__snapshots__"
    kept = touch(base / "kept" / "a.txt")
    touch(base / "renamed_away" / "a.txt")
    touch(base / "__init__" / "__suite__.txt")
    source = str(touch(tmp_path / "tests" / "kept.robot"))
    usage = SuiteUsage(source, 1, {"a": "PASS"}, {str(kept)}, {str(base / "kept")})
    assert unused.orphan_directories([usage]) == [base / "renamed_away"]


def test_clear_records(tmp_path):
    unused.write_record(tmp_path, SuiteUsage("s.robot", 0))
    assert list((tmp_path / unused.USAGE_DIR_NAME).glob("*.json"))
    unused.clear_records(tmp_path)
    assert not list((tmp_path / unused.USAGE_DIR_NAME).glob("*.json"))


def test_cli_exit_codes_and_delete(tmp_path, capsys):
    assert cli.main(["unused", str(tmp_path)]) == 2
    snapshots = tmp_path / "__snapshots__" / "s"
    used, orphan = touch(snapshots / "a.txt"), touch(snapshots / "old.txt")
    source = str(touch(tmp_path / "s.robot"))
    unused.write_record(tmp_path / "out", SuiteUsage(source, 1, {"a": "PASS"}, {str(used)}, {str(snapshots)}))
    assert cli.main(["unused", str(tmp_path / "out")]) == 1
    assert "old.txt" in capsys.readouterr().out and orphan.exists()
    assert cli.main(["unused", str(tmp_path / "out"), "--delete"]) == 0
    assert not orphan.exists() and used.exists()
    assert cli.main(["unused", str(tmp_path / "out")]) == 0
    assert "No unused snapshots." in capsys.readouterr().out
