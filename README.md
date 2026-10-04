# robotframework-snapshot

Snapshot testing for text and structured data in [Robot Framework](https://robotframework.org).

The first run records the actual value to a file. Later runs compare against it.
You review expected values as file diffs in version control instead of writing
and maintaining them by hand, and one flag regenerates them when behaviour
changes on purpose.

```robotframework
*** Settings ***
Library    Process
Library    SnapshotLibrary

*** Test Cases ***
Help Text Is Stable
    ${result}=    Run Process    mytool    --help
    Should Match Snapshot    ${result.stdout}
```

The first run writes `__snapshots__/<suite>/Help_Text_Is_Stable.txt` and passes
with a warning. Commit that file. From then on the test fails with a diff
whenever the output changes.

## Installation

```bash
pip install robotframework-snapshot
```

Requires Python 3.9+ and Robot Framework 6.1+.

## What you can snapshot

| Value | Stored as | Example |
| --- | --- | --- |
| Text: CLI output, logs, emails, rendered templates | `.txt` | `Should Match Snapshot    ${result.stdout}` |
| Dictionaries and lists: API responses, parsed config | sorted, indented `.json` | `Should Match Snapshot    ${response.json()}` |
| Rows: database query results, table contents | `.json`, one row per line | `Should Match Snapshot    ${rows}` |
| A JSON string, in canonical form | `.json` | `Should Match Snapshot    ${body}    format=json` |
| A file the system produced | same extension | `Should Match File Snapshot    ${OUTPUT_DIR}/export.csv` |

### UI state as data

You can check what a page shows without comparing pixels, by snapshotting the
data behind it. The diff then names the value that changed, and the check does
not depend on fonts or browser rendering.

```robotframework
Sales Chart Shows Expected Data
    ${data}=    Evaluate JavaScript    ${None}    () => window.salesChart.data
    Should Match Snapshot    ${data}

Orders Table Lists Expected Rows
    ${cells}=    Get Table Cells As Rows    id=orders    # your own keyword
    Should Match Snapshot    ${cells}
```

This tells you the right data is shown. It cannot tell you the page renders
correctly; keep a few visual checks for that (see [Images, PDFs and
screenshots](#images-pdfs-and-screenshots)).

## Snapshot lifecycle

| Mode | How to enable | Snapshot missing | Snapshot differs |
| --- | --- | --- | --- |
| Default | nothing | Recorded, passes with a warning | Fails with a diff |
| Update | `--variable REFERENCE_RUN:True` | Recorded | Overwritten, passes |
| Strict | `--variable SNAPSHOT_STRICT:True` or `Library    SnapshotLibrary    strict=True` | Fails | Fails with a diff |

Use strict mode in CI. Otherwise a snapshot that was never committed is
recorded on the build machine and the test passes without checking anything.

When a snapshot does not match, the log shows a unified diff, and the actual
value is saved to `${OUTPUT_DIR}/snapshot_actual/` so you can inspect it or
copy it over.

## Volatile values

### Scrubbers

A scrubber replaces volatile text with a stable placeholder before the
comparison and before recording.

| Built-in | Replaces | With |
| --- | --- | --- |
| `timestamp` | ISO-style date-times such as `2026-01-31 12:00:00.123+01:00` | `<TIMESTAMP>` |
| `timezone` | Only the UTC offset after a date-time | `<TZ>` |
| `uuid` | UUIDs | `<UUID>` |
| `duration` | Values such as `1.2s`, `350 ms`, `3 seconds` | `<DURATION>` |
| `path` | The working, temp and home directories | `<CWD>`, `<TMP>`, `<HOME>` |

```robotframework
*** Settings ***
Library    SnapshotLibrary    scrubbers=timestamp,uuid        # every snapshot

*** Test Cases ***
Example
    Add Snapshot Scrubber    order_id    pattern=ORD-\\d+    scope=test
    Should Match Snapshot    ${output}    scrubbers=duration   # this call only
```

### Ignoring fields in structured data

`ignore=` masks values by JSONPath. Supported: `$.key`, `$.list[0]`,
`$.list[*].key`, `$.*` and the recursive `$..key`. Separate several paths
with `;`.

```robotframework
Should Match Snapshot    ${response.json()}    ignore=$.id;$..updated_at
```

## Where snapshots are stored

```
tests/
  orders.robot
  __snapshots__/
    orders/
      Order_Has_Expected_Body.json
      Order_Has_Expected_Body__2.json        second unnamed snapshot in the test
      Order_Has_Expected_Body__headers.json  name=headers
```

When several tests should compare against the same snapshot, for example the
short and the long form of a command-line option, give it a name and share it.
It is then stored as `__snapshots__/<suite>/<name>.<ext>`:

```robotframework
Should Match Snapshot    ${result.stdout}    name=help    shared=True
```

Commit the `__snapshots__` directories. To keep all snapshots in one place,
import the library with `snapshot_directory=snapshots`, or call
`Set Snapshot Directory`.

## Unused snapshots

When a test is renamed or removed, its snapshot file stays behind. At the end
of each suite the library warns about files in that suite's snapshot directory
that no test used:

```
[ WARN ] Unused snapshot: tests/__snapshots__/orders/Old_Test_Name.json. No test used them in this run. Delete them if they are no longer needed.
```

A suite is only judged when every one of its tests ran and passed. A test that
was filtered out, skipped or failed before reaching its snapshot would
otherwise make that snapshot look unused. Turn the warning off with
`Library    SnapshotLibrary    warn_unused=False`.

### Parallel runs and CI

`pabot --testlevelsplit` runs each test in its own process, so no process sees
a whole suite and nothing is warned during the run. Check the finished run from
the command line instead. This works for plain `robot` runs too:

```bash
python -m SnapshotLibrary unused results/            # list, exit code 1 if any
python -m SnapshotLibrary unused results/ --delete   # remove them
```

The command reads the usage records the library writes to
`<output dir>/snapshot_usage/`. It also reports snapshot directories whose
suite file no longer exists, which is what a renamed suite leaves behind.

A snapshot that is only taken under a condition (inside an `IF`, say) is
reported as unused in runs where the condition is false.

## Keywords

| Keyword | Purpose |
| --- | --- |
| `Should Match Snapshot` | Compare a value with its stored snapshot |
| `Should Match File Snapshot` | Compare the text content of a file with its stored snapshot |
| `Add Snapshot Scrubber` | Enable a built-in scrubber or register a custom one |
| `Set Snapshot Directory` | Change where snapshots are stored |
| `Get Snapshot` | Return a stored snapshot for custom assertions |

`python -m SnapshotLibrary unused <output dir>` checks a finished run for
unused snapshots.

Generate the full keyword documentation with:

```bash
libdoc SnapshotLibrary docs/SnapshotLibrary.html
```

## Images, PDFs and screenshots

This library does not compare visual content, and it will not. Use
[DocTestLibrary](https://github.com/manykarim/robotframework-doctestlibrary)
for images, PDFs, print jobs and web page screenshots.

The two work well side by side. Both read the same `REFERENCE_RUN` variable,
so one command refreshes text snapshots and visual baselines together:

```robotframework
*** Settings ***
Library    Browser
Library    SnapshotLibrary
Library    DocTest.WebVisualTest

*** Test Cases ***
Checkout Page
    New Page    https://shop.example.com/checkout
    ${prices}=    Evaluate JavaScript    ${None}    () => window.cart.items
    Should Match Snapshot          ${prices}        # the data is right
    Compare Page To Baseline       checkout         # the page looks right
```

```bash
robot --variable REFERENCE_RUN:True tests/
```

`Compare Page To Baseline` is part of `DocTest.WebVisualTest`; check the
DocTestLibrary documentation for the version that includes it.

## Acknowledgement

The record-on-first-run lifecycle and the `REFERENCE_RUN` switch follow the
usage format of [DocTestLibrary](https://github.com/manykarim/robotframework-doctestlibrary)
by Many Kasiriha, which does for visual content what this library does for
text and data. The idea of snapshot testing itself comes from tools such as
Jest, syrupy and ApprovalTests.

## License

MIT
