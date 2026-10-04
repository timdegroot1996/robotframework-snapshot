*** Settings ***
Library    SnapshotLibrary    warn_unused=False    AS    Quiet

*** Test Cases ***
Quiet Library
    Quiet.Should Match Snapshot    quiet
