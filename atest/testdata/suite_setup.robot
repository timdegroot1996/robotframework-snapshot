*** Settings ***
Library        SnapshotLibrary
Suite Setup    Should Match Snapshot    from suite setup

*** Test Cases ***
After Setup
    Should Match Snapshot    from test
