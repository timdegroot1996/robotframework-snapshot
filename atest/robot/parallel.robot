*** Settings ***
Documentation       All suites in one run, and parallel runs with pabot.
Resource            ../resources/atest_resource.robot
Test Setup          Create Workspace


*** Test Cases ***
All Suites In One Run Keep Their Scopes Apart
    Run Tests
    Run Should Have Passed
    Run Tests    SNAPSHOT_STRICT=True
    Run Should Have Passed
    There Should Be No Warnings

Pabot Records And Matches
    Skip If Pabot Cannot Merge
    Run Tests    runner=pabot
    Run Should Have Passed
    ${count}=    Count Files In Directory    ${SNAPSHOTS}/basics
    Should Be Equal As Integers    ${count}    9
    Run Tests    runner=pabot    SNAPSHOT_STRICT=True
    Run Should Have Passed

Pabot Run Is Checked With The Command Line
    Skip If Pabot Cannot Merge
    Run Tests    runner=pabot
    ${left}=    Leave Snapshot Behind
    Run Tests    runner=pabot
    Run Should Have Passed
    # with one test per process no process can judge a whole suite, so nothing is warned in the run
    @{warnings}=    Get Warnings
    FOR    ${warning}    IN    @{warnings}
        Should Not Contain    ${warning}    Unused snapshot
    END
    Run Unused Check
    Should Be Equal As Integers    ${RC}    1    ${STDOUT}
    Should Contain    ${STDOUT}    Removed_Test.txt
    Should Contain    ${STDOUT}    Unused snapshots: 1
    Should Not Contain    ${STDOUT}    Not checked
    Run Unused Check    --delete
    Should Be Equal As Integers    ${RC}    0    ${STDOUT}
    File Should Not Exist    ${left}
