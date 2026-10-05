# Changelog

## 0.1.1 (unreleased)

- `python -m SnapshotLibrary unused` no longer reports every suite folder as orphaned, and no longer
  deletes them with `--delete`, when `snapshot_directory` points to a directory named `__snapshots__`.
  Only the `__snapshots__` directory next to a suite file is checked for folders of removed suites.

## 0.1.0 (2026-10-05)

- `Should Match Snapshot` for text and structured data, with default, update
  (`REFERENCE_RUN`) and strict (`SNAPSHOT_STRICT`) modes.
- `Should Match File Snapshot`, `Add Snapshot Normalizer`, `Set Snapshot Directory`, `Get Snapshot`.
- Built-in normalizers: `timestamp`, `timezone`, `uuid`, `duration`, `path`.
- `ignore=` for masking values by JSONPath in JSON and by XPath in XML.
- `shared=True` to let several tests compare against one named snapshot.
- XML stored with sorted attributes, without comments and indented, with `format=xml`;
  XML elements are detected automatically. `Should Match File Snapshot` takes `format=json|xml`.
- Lists of rows are stored one row per line, so a changed row is one changed line.
- Warning at the end of a suite for snapshot files no test used (`warn_unused`), and
  `python -m SnapshotLibrary unused <output dir> [--delete]` for parallel runs and CI.
- Unified diff in the failure message, shortened at the end to fit `--maxerrorlines`. The log has
  the full diff in colour, in a block that can be folded.
- With `save_actual` (or `SNAPSHOT_SAVE_ACTUAL`) the actual value is also saved under
  `${OUTPUT_DIR}/snapshot_actual/`.
