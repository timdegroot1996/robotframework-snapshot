# Robot Framework Snapshot
[![PyPI - Version](https://img.shields.io/pypi/v/robotframework-snapshot.svg)](https://pypi.org/project/robotframework-snapshot)
[![License](https://img.shields.io/pypi/l/robotframework-snapshot?cacheSeconds=600)](LICENSE)

Looking for the keywords? Here is the [Keyword Documentation](https://timdegroot1996.github.io/robotframework-snapshot/).

Robot Framework Snapshot is a library for [Robot Framework](https://robotframework.org) that checks text and data
against a stored expected value, without you writing that expected value by hand. The first time a test runs, the
library saves the value to a file next to your suite. Every run after that compares against the file and fails with a
diff when something changed. It works well for command line output, API responses, database rows, XML and generated
files: anything where the expected value is long, tedious to type out and changes now and then on purpose.

## Contents

- [Installation](#installation)
- [Getting Started](#getting-started)
- [Modes](#modes)
- [What You Can Snapshot](#what-you-can-snapshot)
  - [Should Match Snapshot or Should Match File Snapshot?](#should-match-snapshot-or-should-match-file-snapshot)
- [How Snapshot Files Are Found](#how-snapshot-files-are-found)
- [Values That Change Every Run: Normalizers and Ignore](#values-that-change-every-run-normalizers-and-ignore)
  - [Normalizers: replace changing text with a placeholder](#normalizers-replace-changing-text-with-a-placeholder)
  - [Ignore: mask fields in JSON and XML](#ignore-mask-fields-in-json-and-xml)
- [Unused Snapshots](#unused-snapshots)
  - [Parallel Runs and CI](#parallel-runs-and-ci)
- [Keywords](#keywords)
- [Images, PDFs and Screenshots](#images-pdfs-and-screenshots)
- [Contributions](#contributions)
- [License](#license)

## Installation

Install Robot Framework 6.1 or higher (if not already installed):
```bash
pip install robotframework
```
Install Robot Framework Snapshot:
```bash
pip install robotframework-snapshot
```
Python 3.9 or higher is required.

## Getting Started

```robotframework
*** Settings ***
Library    Process
Library    SnapshotLibrary

*** Test Cases ***
Help Text Is Stable
    ${result}=    Run Process    mytool    --help
    Should Match Snapshot    ${result.stdout}
```

**First run:** there is no snapshot yet, so the library writes the output of `mytool --help` to
`__snapshots__/<suite file name>/Help_Text_Is_Stable.txt` and the test passes with a warning:
```
[ WARN ] Snapshot 'tests/__snapshots__/cli/Help_Text_Is_Stable.txt' did not exist and was recorded. Review and commit it.
```
Open the file, check that the content is what you expect, and commit it together with your tests.

**Every run after that:** the output is compared with the file. When they differ the test fails, and the failure
message shows exactly what changed, in the console, `log.html` and `report.html`:
```
Snapshot 'tests/__snapshots__/cli/Help_Text_Is_Stable.txt' does not match.
--- snapshot
+++ actual
@@ -3,3 +3,3 @@
 Options:
-  -o, --output FILE   write results to FILE
+  -o, --output PATH   write results to PATH
   -h, --help          show this help

If the change is intended, update the snapshot with: --variable REFERENCE_RUN:True
```

**When the change is intended:** run once with `--variable REFERENCE_RUN:True`. Every snapshot that differs is
overwritten with the new value and the tests pass. Review the changed files like any other change and commit them.

## Modes

| Mode | How to switch it on | Snapshot file missing | Value differs from the file |
| --- | --- | --- | --- |
| Default | nothing | Recorded, test passes with a warning | Test fails with a diff |
| Update | `--variable REFERENCE_RUN:True` | Recorded | File is overwritten, test passes |
| Strict | `--variable SNAPSHOT_STRICT:True` or `Library    SnapshotLibrary    strict=True` | Test fails | Test fails with a diff |

I recommend strict mode in CI. In default mode a snapshot you forgot to commit is simply recorded on the build machine,
so the test passes without checking anything.

The failure message shows as much of the diff as fits within Robot Framework's `--maxerrorlines` (40 lines by
default), starting at the top, and says how many lines were left out. Run with `--maxerrorlines NONE` to get the whole
diff in the message. The log also has the full diff in colour, removed lines red and added lines green: folded away
when the message already shows everything, open when the message had to leave lines out.

By default the diff only ends up in the test message and the log. When you'd also like the full actual value as a file,
for example to open it in a diff tool, switch on `save_actual`. It is then written to
`${OUTPUT_DIR}/snapshot_actual/<suite file name>/` whenever a snapshot does not match:
```robotframework
Library    SnapshotLibrary    save_actual=True
```
or for a single run: `--variable SNAPSHOT_SAVE_ACTUAL:True`.

## What You Can Snapshot

| Type | Stored as | Example |
| --- | --- | --- |
| Text | `.txt` | `Should Match Snapshot    ${result.stdout}` |
| JSON: dictionaries and lists | `.json`, keys sorted, two-space indent | `Should Match Snapshot    ${response.json()}` |
| JSON string | `.json`, keys sorted, two-space indent | `Should Match Snapshot    ${response.text}    format=json` |
| Rows: database results, table contents | `.json`, one row per line | `Should Match Snapshot    ${rows}` |
| XML string | `.xml`, attributes sorted, comments removed, two-space indent | `Should Match Snapshot    ${body}    format=xml` |
| XML element (from the XML library) | `.xml`, same as above | `Should Match Snapshot    ${root}` |
| File | the file's own extension | `Should Match File Snapshot    ${OUTPUT_DIR}/export.csv` |

Sorting keys and attributes and fixing the indentation means the snapshot only changes when the content changes, not
when the system happens to write the same data in another order or layout.

For example, this list of rows:
```robotframework
${rows}=    Evaluate    [("2026-03-14", "Checkout", 12, 0), ("2026-03-15", "Checkout", 11, 1)]
Should Match Snapshot    ${rows}
```
is stored as:
```json
[
  ["2026-03-14", "Checkout", 12, 0],
  ["2026-03-15", "Checkout", 11, 1]
]
```
so a changed row shows up as one changed line in the diff.

The same goes for JSON and XML: because of the fixed layout, a changed value is one changed line. When the stored order
says `"status": "paid"` and the API now returns `refunded`:
```
Snapshot 'tests/__snapshots__/orders/Order_Has_Expected_Body.json' does not match.
--- snapshot
+++ actual
@@ -1,5 +1,5 @@
 {
   "id": 1042,
-  "status": "paid",
+  "status": "refunded",
   "total": 19.95
 }

If the change is intended, update the snapshot with: --variable REFERENCE_RUN:True
```
and when an XML total changed from `19.95` to `24.95`:
```
Snapshot 'tests/__snapshots__/orders/Order_Xml.xml' does not match.
--- snapshot
+++ actual
@@ -1,3 +1,3 @@
 <order id="1042">
-  <total>19.95</total>
+  <total>24.95</total>
 </order>

If the change is intended, update the snapshot with: --variable REFERENCE_RUN:True
```

### Should Match Snapshot or Should Match File Snapshot?

- `Should Match Snapshot` takes a **value**: the content of a variable, the return value of a keyword.
- `Should Match File Snapshot` takes a **path to a file** the system under test created, reads that file and compares
  its content. The snapshot keeps the file's extension, so `export.csv` is stored as a `.csv` snapshot. Add
  `format=json` or `format=xml` to have the file sorted and indented like the table above.

## How Snapshot Files Are Found

There is no variable or setting that points to a snapshot file. The location follows from where the keyword is called:

```
<folder of the suite file>/__snapshots__/<suite file name>/<test name>.<extension>
```

The suite file name is used without `.robot`, and characters that are not letters, digits, `.` or `-` in the test
name become `_`. The extension follows from the type of the value (see the table above).

When a test takes more than one snapshot, the first one gets the plain test name, the next ones a number in the order
they are taken. Give a snapshot a `name=` to get a readable file name that does not depend on the order:

```robotframework
*** Test Cases ***
Create Order
    Should Match Snapshot    ${response.text}                  # Create_Order.txt
    Should Match Snapshot    ${confirmation_email}             # Create_Order__2.txt
    Should Match Snapshot    ${response.headers}    name=headers    # Create_Order__headers.json
```

```
tests/
├── orders.robot
└── __snapshots__/
    └── orders/
        ├── Create_Order.txt
        ├── Create_Order__2.txt
        └── Create_Order__headers.json
```

A snapshot taken in a suite setup or teardown is stored as `__suite__.<extension>`.

**Several tests, one snapshot.** When several tests should compare against the same file, for example the short and
the long form of a command line option, add `shared=True` together with a `name`. The file is then stored under that
name alone, `__snapshots__/<suite file name>/<name>.<extension>`:

```robotframework
*** Test Cases ***
Short Help Flag
    ${result}=    Run Process    mytool    -h
    Should Match Snapshot    ${result.stdout}    name=help    shared=True    # help.txt

Long Help Flag
    ${result}=    Run Process    mytool    --help
    Should Match Snapshot    ${result.stdout}    name=help    shared=True    # the same help.txt
```

**All snapshots in one folder.** Import the library with `snapshot_directory=snapshots` (relative to the directory
you run `robot` from) or call `Set Snapshot Directory`. The suite file name and test name part stays the same:
`snapshots/<suite file name>/<test name>.<extension>`.

## Values That Change Every Run: Normalizers and Ignore

Timestamps, generated IDs and durations differ on every run. There are two ways to keep them out of the comparison:
normalizers for any value, and `ignore=` for fields in JSON and XML.

### Normalizers: replace changing text with a placeholder

A normalizer is a regular expression that replaces matching text with a fixed placeholder, before the value is compared
and before it is recorded. They work on every type of value.

```robotframework
*** Test Cases ***
Order Confirmation Is Stable
    # ${output} is: Order ORD-1042 created at 2026-03-14 09:26:53 by 3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90
    ${output}=    Get Confirmation Message
    Add Snapshot Normalizer    order_id    pattern=ORD-\\d+    scope=test
    Should Match Snapshot    ${output}    normalizers=timestamp,uuid
```
is stored, and from then on compared, as:
```
Order <ORDER_ID> created at <TIMESTAMP> by <UUID>
```
so the next run with `ORD-1043`, another time and another UUID still passes.

Built-in normalizers:

| Name | Replaces | Example | Becomes |
| --- | --- | --- | --- |
| `timestamp` | Date and time | `2026-03-14 09:26:53.123+01:00` | `<TIMESTAMP>` |
| `timezone` | Only the UTC offset after a date and time | `2026-03-14 09:26:53+01:00` | `2026-03-14 09:26:53<TZ>` |
| `uuid` | UUIDs | `3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90` | `<UUID>` |
| `duration` | Durations | `1.2s`, `350 ms`, `3 seconds` | `<DURATION>` |
| `path` | The working, temp and home directory | `C:\Users\me\project\out` | `<CWD>\out` |

You can switch normalizers on for the whole run, a suite, a test or a single call:

```robotframework
*** Settings ***
Library    SnapshotLibrary    normalizers=uuid    # every snapshot in the run

*** Test Cases ***
Import Job Summary
    Add Snapshot Normalizer    timestamp    # every snapshot in this suite (scope=suite is the default)
    Add Snapshot Normalizer    job_id    pattern=JOB-\\d+    scope=test    # your own, this test only
    # ${summary} is: JOB-77 by 3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90 started 2026-03-14 09:26:53, took 1.2s
    ${summary}=    Get Job Summary
    Should Match Snapshot    ${summary}    normalizers=duration    # this call only
```
is stored as:
```
<JOB_ID> by <UUID> started <TIMESTAMP>, took <DURATION>
```
`Add Snapshot Normalizer` also takes `scope=global`, which keeps the normalizer for the rest of the run.

A custom normalizer replaces its matches with `<NAME>` in capitals, or with your own `replacement=`, which can use
groups from the pattern: `pattern=(localhost):\\d+    replacement=\\1:<PORT>` turns `localhost:8080` into
`localhost:<PORT>`.

### Ignore: mask fields in JSON and XML

For JSON and XML you can point at the fields to leave out with `ignore=`. Their value is replaced by `<IGNORED>`:

```robotframework
# ${order} is: {"id": 1042, "status": "paid", "total": 19.95, "updated_at": "2026-03-14T09:26:53"}
Should Match Snapshot    ${order}    ignore=$.id;$.updated_at
```
```json
{
  "id": "<IGNORED>",
  "status": "paid",
  "total": 19.95,
  "updated_at": "<IGNORED>"
}
```

```robotframework
# ${body} is: <order status="paid" id="1042"><total>19.95</total><created>2026-03-14T09:26:53</created></order>
Should Match Snapshot    ${body}    format=xml    ignore=.//created;@id
```
```xml
<order id="&lt;IGNORED&gt;" status="paid">
  <total>19.95</total>
  <created>&lt;IGNORED&gt;</created>
</order>
```

| Type | Path syntax | Examples |
| --- | --- | --- |
| JSON | JSONPath | `$.id`, `$.items[0]`, `$.items[*].price`, `$.*`, `$..updated_at` (any depth) |
| XML | XPath, as supported by Python's ElementTree, relative to the root element | `.//created`, `items/item`, `.//item[@type='gift']`, `@id`, `.//item/@id` |

Separate several paths with `;`. A path ending in `/@name` masks that attribute. Namespace prefixes declared in the
document can be used in the path, for example `.//soap:Body`. Plain text has no fields, so `ignore=` does not apply to
it; use a normalizer there.

## Unused Snapshots

When you rename or remove a test, its snapshot file stays behind. At the end of each suite the library warns about
files in that suite's snapshot folder that no test used:
```
[ WARN ] Unused snapshot: tests/__snapshots__/orders/Old_Test_Name.json. No test used them in this run. Delete them if they are no longer needed.
```

A suite is only checked when all of its tests ran and passed. Otherwise a test you filtered out with `--test`, or one
that failed before it reached its snapshot, would make its snapshot look unused. Turn the warning off with
`Library    SnapshotLibrary    warn_unused=False`.

### Parallel Runs and CI

With `pabot --testlevelsplit` every test runs in its own process, so no process sees a whole suite and the warning
never shows up. Check the finished run from the command line instead. This works for plain `robot` runs too:

```bash
python -m SnapshotLibrary unused results/            # list them, exit code 1 if there are any
python -m SnapshotLibrary unused results/ --delete   # delete them
```

The command reads the usage records the library writes to `<output dir>/snapshot_usage/`. It also reports snapshot
folders whose suite file no longer exists, which is what renaming or deleting a suite file leaves behind.

Good to know:

- A snapshot that is only taken under a condition (inside an `IF`) is reported as unused in runs where the condition
  is false.
- Folders of renamed or deleted suites are only found when you use the default `__snapshots__` folders. Those sit next
  to the suite files, so the command can see that `__snapshots__/orders/` has no `orders.robot` beside it. With
  `snapshot_directory` all suites share one folder, possibly from several test directories, so the command cannot tell
  which suite file a folder belonged to. Unused files inside the folders of suites that did run are still found.
- Snapshots taken in the setup of an `__init__.robot` are only checked when every test below that folder passed.

## Keywords

| Keyword | What it does |
| --- | --- |
| `Should Match Snapshot` | Compares a value (text, dictionary, list, XML) with its snapshot file |
| `Should Match File Snapshot` | Reads a file from disk and compares its content with its snapshot file |
| `Add Snapshot Normalizer` | Switches on a built-in normalizer or adds your own, for a test, a suite or the whole run |
| `Set Snapshot Directory` | Stores snapshots in one folder of your choice instead of `__snapshots__` next to each suite |
| `Get Snapshot` | Returns the content of a snapshot file, for your own checks |

All arguments and more examples are in the [Keyword Documentation](https://timdegroot1996.github.io/robotframework-snapshot/).

## Images, PDFs and Screenshots

This library compares text and data only, and that will stay so. For images, PDFs, print jobs and screenshots use
[DocTestLibrary](https://github.com/manykarim/robotframework-doctestlibrary).

The two work well side by side. Both read the same `REFERENCE_RUN` variable, so one run updates text snapshots and
visual baselines together:

```robotframework
*** Settings ***
Library    Browser
Library    SnapshotLibrary
Library    DocTest.WebVisualTest

*** Test Cases ***
Checkout Page
    New Page    https://shop.example.com/checkout
    ${items}=    Evaluate JavaScript    ${None}    () => window.cart.items
    Should Match Snapshot          ${items}         # the data is right
    Compare Page To Baseline       checkout         # the page looks right
```

```bash
robot --variable REFERENCE_RUN:True tests/
```

`Compare Page To Baseline` is part of `DocTest.WebVisualTest`; check the DocTestLibrary documentation for the version
that includes it.

The way this library records on the first run and updates with `REFERENCE_RUN` follows DocTestLibrary by Many
Kasiriha, so that people using both get the same experience.

## Contributions

Contributions are welcome! If you run into an issue, have an idea for an improvement or would like to add something
yourself, feel free to open an issue or a pull request. How to set up the project and run the tests is described in
[Contributing](./CONTRIBUTING.md).

## License
This project is licensed under the MIT License.

> **Note:** This project is not officially affiliated with or endorsed by Robot Framework.
