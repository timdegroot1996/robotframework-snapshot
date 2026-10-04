"""End-to-end checks: real robot runs against real files."""

import pytest
from robot.version import get_version

from conftest import unused_cli

RF_MAJOR = int(get_version().split(".")[0])
PABOT = ("pabot", "--testlevelsplit", "--processes", "4")
needs_working_pabot = pytest.mark.skipif(RF_MAJOR < 7, reason="pabot 5 fails to merge its own results on Robot Framework 6")

DEFAULTS = dict(RANDOM_ID=1, UUID="3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90", NOW="2026-01-02T03:04:05Z", NUMBER=1, CONTENT="a", HELP="usage")


def names(directory):
    return sorted(path.name for path in directory.iterdir())


# -- lifecycle ---------------------------------------------------------------

def test_first_run_records_and_warns(workspace):
    run = workspace.run("basics.robot", **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert names(workspace.snapshots("basics")) == [
        "Get_Snapshot_Returns_Stored_Value.txt",
        "Get_Snapshot_Returns_Stored_Value__stored.json",
        "Ignore_By_JSONPath.json",
        "Json_String_In_Canonical_Form.json",
        "Several_Snapshots_In_One_Test.txt",
        "Several_Snapshots_In_One_Test__2.txt",
        "Several_Snapshots_In_One_Test__body.json",
        "Structured_Snapshot.json",
        "Text_Snapshot.txt",
    ]
    assert len(run.warnings) == 9
    assert all("did not exist and was recorded" in warning for warning in run.warnings)


def test_recorded_content_is_readable(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    snapshots = workspace.snapshots("basics")
    assert (snapshots / "Text_Snapshot.txt").read_text() == "line one\nline two\n"
    assert (snapshots / "Structured_Snapshot.json").read_text() == (
        '{\n  "id": 42,\n  "name": "Widget",\n  "updated_at": "2026-01-02 03:04:05"\n}\n'
    )
    assert (snapshots / "Json_String_In_Canonical_Form.json").read_text() == '{\n  "a": 2,\n  "b": 1\n}\n'


def test_second_run_matches_without_warnings(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert run.warnings == []


def test_change_fails_with_diff_and_saves_actual(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", "--variable", "TEXT:changed text", **DEFAULTS)
    assert run.returncode == 1
    assert run.status("Text Snapshot") == "FAIL"
    message = run.message("Text Snapshot")
    assert "suites/__snapshots__/basics/Text_Snapshot.txt' does not match" in message
    assert "-line two" in message and "+changed text" in message
    assert "REFERENCE_RUN:True" in message
    # the snapshot is untouched, the actual value is kept beside the output
    assert (workspace.snapshots("basics") / "Text_Snapshot.txt").read_text() == "line one\nline two\n"
    actual = workspace.root / "out2" / "snapshot_actual" / "basics" / "Text_Snapshot.txt"
    assert actual.read_text() == "changed text\n"
    assert run.status("Structured Snapshot") == "PASS"


def test_reference_run_updates(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", "--variable", "TEXT:new text", REFERENCE_RUN=True, **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert run.warnings == []
    assert (workspace.snapshots("basics") / "Text_Snapshot.txt").read_text() == "new text\n"
    assert workspace.run("basics.robot", "--variable", "TEXT:new text", **DEFAULTS).returncode == 0


def test_strict_fails_on_missing_and_records_nothing(workspace):
    run = workspace.run("basics.robot", "--test", "Text Snapshot", SNAPSHOT_STRICT=True, **DEFAULTS)
    assert run.returncode == 1
    assert "does not exist and strict mode is on" in run.message("Text Snapshot")
    assert not workspace.snapshots("basics").exists()


def test_strict_passes_when_snapshots_exist(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    assert workspace.run("basics.robot", SNAPSHOT_STRICT=True, **DEFAULTS).returncode == 0


def test_false_like_values_do_not_enable_modes(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", "--variable", "TEXT:changed", REFERENCE_RUN=False, **DEFAULTS)
    assert run.status("Text Snapshot") == "FAIL"


# -- volatile values -----------------------------------------------------------

def test_ignore_makes_volatile_field_stable(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", **{**DEFAULTS, "RANDOM_ID": 999})
    assert run.status("Ignore By JSONPath") == "PASS"
    stored = (workspace.snapshots("basics") / "Ignore_By_JSONPath.json").read_text()
    assert '"id": "<IGNORED>"' in stored


def test_scrubbers_and_their_scopes(workspace):
    first = workspace.run("scrubbers.robot", **DEFAULTS)
    assert first.returncode == 0, first.stdout
    snapshots = workspace.snapshots("scrubbers")
    assert (snapshots / "Import_And_Suite_Scrubbers_Apply.txt").read_text() == "id <UUID> at <TIMESTAMP>\n"
    assert (snapshots / "Test_Scoped_Custom_Scrubber.txt").read_text() == "order <ORDER> created\n"
    assert (snapshots / "Test_Scope_Has_Ended.txt").read_text() == "order ORD-1 created\n"
    assert (snapshots / "Per_Call_Scrubber.txt").read_text() == "took <DURATION>\n"
    assert (snapshots / "Replacement_With_Group.txt").read_text() == "http://localhost:<PORT>/health\n"
    changed = dict(DEFAULTS, UUID="00000000-0000-4000-8000-000000000000", NOW="2030-12-31 23:59:59", NUMBER=777)
    second = workspace.run("scrubbers.robot", **changed)
    assert second.returncode == 0, second.stdout


# -- xml ---------------------------------------------------------------------

XML_A = '<?xml version="1.0"?><!-- note --><order b="2" a="1"><id>42</id>  <items><item/></items></order>'
XML_B = '<order a="1" b="2">\n    <id>42</id>\n    <items>\n        <item></item>\n    </items>\n</order>'
XML_EXPECTED = '<order a="1" b="2">\n  <id>42</id>\n  <items>\n    <item/>\n  </items>\n</order>\n'


def test_xml_is_stored_canonical_and_layout_does_not_matter(workspace):
    first = workspace.run("xml.robot", XML_TEXT=XML_A)
    assert first.returncode == 0, first.stdout
    snapshots = workspace.snapshots("xml")
    assert names(snapshots) == [
        "Xml_Element_Is_Detected.xml",
        "Xml_File_In_Canonical_Form.xml",
        "Xml_String_In_Canonical_Form.xml",
    ]
    for path in snapshots.iterdir():
        assert path.read_text(encoding="utf-8") == XML_EXPECTED
    second = workspace.run("xml.robot", XML_TEXT=XML_B, SNAPSHOT_STRICT=True)
    assert second.returncode == 0, second.stdout
    changed = workspace.run("xml.robot", XML_TEXT=XML_B.replace("42", "43"))
    assert changed.returncode == 3
    assert "+  <id>43</id>" in changed.message("Xml String In Canonical Form")


# -- files, directories, suite setup ------------------------------------------

def test_file_snapshot_and_custom_directory(workspace):
    first = workspace.run("files.robot", **DEFAULTS)
    assert first.returncode == 0, first.stdout
    assert (workspace.snapshots("files") / "File_Snapshot_Keeps_Extension.csv").read_text() == "id,name\n1,a\n"
    assert (workspace.root / "custom_snaps" / "files" / "Custom_Directory.txt").read_text() == "in custom dir\n"
    second = workspace.run("files.robot", **{**DEFAULTS, "CONTENT": "b"})
    assert second.status("File Snapshot Keeps Extension") == "FAIL"
    assert second.status("Custom Directory") == "PASS"


def test_snapshot_in_suite_setup(workspace):
    run = workspace.run("suite_setup.robot", **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert names(workspace.snapshots("suite_setup")) == ["After_Setup.txt", "__suite__.txt"]


def test_shared_snapshot_is_one_file_for_several_tests(workspace):
    first = workspace.run("shared.robot", **DEFAULTS)
    assert first.returncode == 0, first.stdout
    assert names(workspace.snapshots("shared")) == ["Rows.json", "help.txt"]
    assert len(first.warnings) == 2  # help is recorded once, the second test matches it
    assert (workspace.snapshots("shared") / "Rows.json").read_text() == '[\n  ["a", 1, null],\n  ["b", 2, 0.5]\n]\n'
    second = workspace.run("shared.robot", **{**DEFAULTS, "HELP": "changed"})
    assert second.status("Short Flag") == "FAIL" and second.status("Long Flag") == "FAIL"


# -- whole directory and parallel runs ----------------------------------------

def test_all_suites_in_one_run_keep_scopes_apart(workspace):
    first = workspace.run("", **DEFAULTS)
    assert first.returncode == 0, first.stdout
    second = workspace.run("", SNAPSHOT_STRICT=True, **DEFAULTS)
    assert second.returncode == 0, second.stdout
    assert second.warnings == []


@needs_working_pabot
def test_pabot_records_and_matches(workspace):
    first = workspace.run("", runner=("pabot", "--testlevelsplit", "--processes", "4"), **DEFAULTS)
    assert first.returncode == 0, first.stdout
    assert len(names(workspace.snapshots("basics"))) == 9
    second = workspace.run("", runner=("pabot", "--testlevelsplit", "--processes", "4"), SNAPSHOT_STRICT=True, **DEFAULTS)
    assert second.returncode == 0, second.stdout


# -- unused snapshots ----------------------------------------------------------

def orphan(workspace, suite="basics", name="Removed_Test.txt"):
    path = workspace.snapshots(suite) / name
    path.write_text("left behind\n")
    return path


def test_unused_snapshot_is_warned_about_after_a_full_passing_run(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    orphan(workspace)
    run = workspace.run("basics.robot", **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert len(run.warnings) == 1
    assert "Unused snapshot: suites/__snapshots__/basics/Removed_Test.txt" in run.warnings[0]


def test_no_unused_warning_when_tests_were_filtered(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    orphan(workspace)
    run = workspace.run("basics.robot", "--test", "Text Snapshot", **DEFAULTS)
    assert run.warnings == []


def test_no_unused_warning_when_a_test_failed(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    orphan(workspace)
    run = workspace.run("basics.robot", "--variable", "TEXT:changed", **DEFAULTS)
    assert run.returncode == 1
    assert run.warnings == []


def test_no_unused_warning_in_dry_run(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    run = workspace.run("basics.robot", "--dryrun", **DEFAULTS)
    assert run.returncode == 0, run.stdout
    assert run.warnings == []


def test_unused_warning_can_be_turned_off(workspace):
    workspace.run("no_warn.robot", **DEFAULTS)
    orphan(workspace, "no_warn")
    assert workspace.run("no_warn.robot", **DEFAULTS).warnings == []


def test_snapshot_left_behind_by_a_type_change_is_reported(workspace):
    """Text becoming JSON changes the extension; the old file is then unused."""
    workspace.run("basics.robot", **DEFAULTS)
    (workspace.snapshots("basics") / "Structured_Snapshot.txt").write_text("old text form\n")
    run = workspace.run("basics.robot", **DEFAULTS)
    assert any("Structured_Snapshot.txt" in warning for warning in run.warnings)


def test_cli_reports_and_deletes_after_a_robot_run(workspace):
    workspace.run("", **DEFAULTS)
    left = orphan(workspace)
    workspace.run("", **DEFAULTS)
    code, output = unused_cli(workspace.root / "out2", cwd=workspace.root)
    assert code == 1, output
    assert "suites/__snapshots__/basics/Removed_Test.txt" in output.replace("\\", "/")
    code, output = unused_cli(workspace.root / "out2", "--delete", cwd=workspace.root)
    assert code == 0 and not left.exists()
    assert len(names(workspace.snapshots("basics"))) == 9


def test_cli_does_not_judge_a_filtered_run(workspace):
    workspace.run("basics.robot", **DEFAULTS)
    orphan(workspace)
    workspace.run("basics.robot", "--test", "Text Snapshot", **DEFAULTS)
    code, output = unused_cli(workspace.root / "out2", cwd=workspace.root)
    assert code == 0, output
    assert "Not checked" in output and "basics.robot" in output


def test_cli_reports_directory_of_a_removed_suite(workspace):
    workspace.run("", **DEFAULTS)
    (workspace.suites / "shared.robot").unlink()
    workspace.run("", **DEFAULTS)
    code, output = unused_cli(workspace.root / "out2", cwd=workspace.root)
    assert code == 1, output
    assert "Snapshot directories without a suite file: 1" in output
    assert "__snapshots__/shared" in output.replace("\\", "/")


def test_old_records_in_the_output_directory_do_not_hide_unused_snapshots(workspace):
    """A second run into the same output dir must not inherit the first run's usage."""
    workspace.run("basics.robot", **DEFAULTS)
    used_before = workspace.snapshots("basics") / "Text_Snapshot.txt"
    workspace.runs = 0  # reuse out1
    (workspace.suites / "basics.robot").write_text(
        "*** Settings ***\nLibrary    SnapshotLibrary\n\n*** Test Cases ***\nOnly Test\n    Should Match Snapshot    only\n"
    )
    workspace.run("basics.robot", **DEFAULTS)
    code, output = unused_cli(workspace.root / "out1", cwd=workspace.root)
    assert code == 1 and used_before.name in output


@needs_working_pabot
def test_pabot_run_is_checked_with_the_cli(workspace):
    workspace.run("", runner=PABOT, **DEFAULTS)
    left = orphan(workspace)
    run = workspace.run("", runner=PABOT, **DEFAULTS)
    assert run.returncode == 0, run.stdout
    # with one test per process no process can judge a suite, so nothing is warned in the run
    assert not any("Unused snapshot" in warning for warning in run.warnings)
    code, output = unused_cli(workspace.root / "out2", cwd=workspace.root)
    assert code == 1, output
    assert "Removed_Test.txt" in output and "Unused snapshots: 1" in output
    assert "Not checked" not in output
    code, _ = unused_cli(workspace.root / "out2", "--delete", cwd=workspace.root)
    assert code == 0 and not left.exists()
