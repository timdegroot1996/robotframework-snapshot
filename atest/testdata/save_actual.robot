*** Settings ***
Library    SnapshotLibrary    save_actual=True

*** Test Cases ***
Saved On Mismatch
    Should Match Snapshot    ${CONTENT}
