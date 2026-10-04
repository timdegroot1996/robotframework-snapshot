*** Settings ***
Library    SnapshotLibrary

*** Test Cases ***
Short Flag
    Should Match Snapshot    ${HELP}    name=help    shared=True

Long Flag
    Should Match Snapshot    ${HELP}    name=help    shared=True
    ${stored}=    Get Snapshot    name=help    shared=True
    Should Be Equal    ${stored}    ${HELP}\n

Rows
    ${rows}=    Evaluate    [["a", 1, None], ["b", 2, 0.5]]
    Should Match Snapshot    ${rows}
