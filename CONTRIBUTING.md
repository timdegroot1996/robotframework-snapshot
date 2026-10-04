# Contributing

This document describes how to get the project up and running, how to run the tests and how a release is made.

## Getting Started

Clone the repository and create a virtual environment in the root of the project:
```sh
git clone https://github.com/timdegroot1996/robotframework-snapshot.git
cd robotframework-snapshot
python -m venv .venv
```
Activate it, on Windows:
```
.venv\Scripts\activate
```
or on Linux and macOS:
```sh
source .venv/bin/activate
```
Then install the library in editable mode, together with everything the tests need (pytest and pabot):
```
scripts\install.bat
```
or
```sh
bash scripts/install.sh
```
Editable mode means changes in `src/SnapshotLibrary/` are picked up right away, there is no need to reinstall after
every change.

> **Note:** keep the virtual environment activated when running the scripts below. pabot starts `robot` from your
> `PATH`, and without the activated environment it picks up another Python installation that does not have the
> library installed.

## Project Layout

| Path | What |
| --- | --- |
| `src/SnapshotLibrary/library.py` | The keywords, and the listener that tracks tests and suites |
| `src/SnapshotLibrary/core.py` | The compare, record and update decision, without any Robot Framework import |
| `src/SnapshotLibrary/serializers.py` | Turning values into text: sorted JSON, rows on one line, sorted XML |
| `src/SnapshotLibrary/normalizers.py` | Built-in and custom normalizers |
| `src/SnapshotLibrary/jsonpath.py`, `xmlpath.py` | `ignore=` for JSON and XML |
| `src/SnapshotLibrary/store.py` | Snapshot file names and reading and writing files |
| `src/SnapshotLibrary/unused.py`, `__main__.py` | Unused snapshot detection and `python -m SnapshotLibrary unused` |
| `utest/` | Python unit tests |
| `atest/` | Robot Framework acceptance tests |
| `scripts/` | Install, test and release scripts |

## Tests

There are two levels of tests in this project.

### Python Unit Tests
Located in `utest/` and run with pytest. They test the parts that do not need a Robot Framework run.
```
scripts\python-tests.bat
```
or
```sh
bash scripts/python-tests.sh
```
Extra arguments are passed on to pytest, for example `scripts\python-tests.bat -k xml`.

### Robot Framework Acceptance Tests
Located in `atest/` and set up the same way as the acceptance tests of Robot Framework itself:

| Path | What |
| --- | --- |
| `atest/testdata/` | Suites that use SnapshotLibrary, the way a user would |
| `atest/robot/` | The actual tests. Each one runs suites from `testdata` with `robot` or `pabot` and checks the result |
| `atest/resources/atest_resource.robot` | Keywords to run the test data and check the outcome: `Run Tests`, `Snapshot Should Be`, `Warnings Should Be`, ... |
| `atest/resources/OutputReader.py` | Reads the statuses, messages and warnings from the `output.xml` of such a run |

A typical test runs the test data twice and looks at what happened in between:
```robotframework
Reference Run Updates
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=new text    REFERENCE_RUN=True
    Run Should Have Passed
    Snapshot Should Be    basics/Text_Snapshot.txt    new text\n
```
Arguments in the form `NAME=value` become `--variable NAME:value` for the inner run, other arguments are passed to
`robot` as they are. Every test works on its own copy of `atest/testdata` in `results/workspaces/<suite>-<test>/`,
so snapshots recorded by one test never affect another. The workspaces are kept after the run, so you can look at
the snapshot files and the inner `output.xml` of a failed test.

Run all acceptance tests in parallel with pabot:
```
scripts\robot-tests.bat
```
or
```sh
bash scripts/robot-tests.sh
```
The number of processes defaults to 4 and can be changed with the `ROBOT_PROCESSES` environment variable. Extra
arguments are passed on to pabot, for example `scripts\robot-tests.bat --test "Reference*"`. The results end up in
`results/` (`log.html`, `report.html`, `output.xml`).

A single suite also runs fine with plain Robot Framework:
```sh
robot --outputdir results atest/robot/lifecycle.robot
```

### In GitHub Actions
Both test levels run on every push to `main` and on every pull request, see `.github/workflows/tests.yml`. The
matrix covers Python 3.9 to 3.13, Robot Framework 6.1, 7.0 and the latest version, on Linux, and the latest versions
on Windows and macOS. When the acceptance tests fail, their `log.html` and `output.xml` are uploaded as an artifact of
the workflow run.

## Keyword Documentation

The keyword documentation is generated from the docstrings in `library.py` and published to
[GitHub Pages](https://timdegroot1996.github.io/robotframework-snapshot/) on every push to `main`, see
`.github/workflows/docs.yml`. To look at it before pushing:
```sh
python -m robot.libdoc SnapshotLibrary results/SnapshotLibrary.html
```

## Releasing

Releases are made by hand, so no PyPI credentials are stored anywhere.

1. Update the version in `src/SnapshotLibrary/version.py` and move the changes in `CHANGELOG.md` under that version.
2. Commit, tag the commit (`git tag v0.1.0`) and push both.
3. Build and upload to PyPI:
   ```
   scripts\release.bat
   ```
   twine asks for your PyPI API token.
4. Create a release on GitHub for the tag, with the changelog entries as description.
