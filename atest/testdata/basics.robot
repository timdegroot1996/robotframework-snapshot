*** Settings ***
Library    SnapshotLibrary

*** Variables ***
${TEXT}       line one\nline two
&{BODY}       id=${42}    name=Widget    updated_at=2026-01-02 03:04:05

*** Test Cases ***
Text Snapshot
    Should Match Snapshot    ${TEXT}

Structured Snapshot
    Should Match Snapshot    ${BODY}

Several Snapshots In One Test
    Should Match Snapshot    first
    Should Match Snapshot    second
    Should Match Snapshot    ${BODY}    name=body

Ignore By JSONPath
    &{volatile}=    Create Dictionary    id=${RANDOM_ID}    name=Widget
    Should Match Snapshot    ${volatile}    ignore=$.id

Json String In Canonical Form
    Should Match Snapshot    {"b": 1, "a": 2}    format=json

Get Snapshot Returns Stored Value
    Should Match Snapshot    ${BODY}    name=stored
    ${stored}=    Get Snapshot    name=stored
    Should Be Equal    ${stored}[name]    Widget
    Should Match Snapshot    plain
    ${text}=    Get Snapshot
    Should Be Equal    ${text}    plain\n
