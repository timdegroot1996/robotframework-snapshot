# Changelog

## 0.1.0 (unreleased)

- `Should Match Snapshot` for text and structured data, with default, update
  (`REFERENCE_RUN`) and strict (`SNAPSHOT_STRICT`) modes.
- `Should Match File Snapshot`, `Add Snapshot Scrubber`, `Set Snapshot Directory`, `Get Snapshot`.
- Built-in scrubbers: `timestamp`, `timezone`, `uuid`, `duration`, `path`.
- `ignore=` for masking values in structured data by JSONPath.
- `shared=True` to let several tests compare against one named snapshot.
- XML in canonical form (sorted attributes, no comments, indented) with `format=xml`;
  XML elements are detected automatically. `Should Match File Snapshot` takes `format=json|xml`.
- Lists of rows are stored one row per line, so a changed row is one changed line.
- Warning at the end of a suite for snapshot files no test used (`warn_unused`), and
  `python -m SnapshotLibrary unused <output dir> [--delete]` for parallel runs and CI.
- Unified diff in the log and the actual value saved under `${OUTPUT_DIR}/snapshot_actual/`.
