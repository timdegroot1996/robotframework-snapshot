*** Settings ***
Documentation       Finding snapshot files that no test used, in the run and from the command line.
Resource            ../resources/atest_resource.robot
Test Setup          Create Workspace


*** Test Cases ***
Unused Snapshot Is Warned About After A Full Passing Run
    Run Tests    basics.robot
    Leave Snapshot Behind
    Run Tests    basics.robot
    Run Should Have Passed
    Warnings Should Be    Unused snapshot: suites/__snapshots__/basics/Removed_Test.txt

No Warning When Tests Were Filtered
    Run Tests    basics.robot
    Leave Snapshot Behind
    Run Tests    basics.robot    --test    Text Snapshot
    There Should Be No Warnings

No Warning When A Test Failed
    Run Tests    basics.robot
    Leave Snapshot Behind
    Run Tests    basics.robot    TEXT=changed
    Should Be Equal As Integers    ${RC}    1
    There Should Be No Warnings

No Warning In A Dry Run
    Run Tests    basics.robot
    Run Tests    basics.robot    --dryrun
    Run Should Have Passed
    There Should Be No Warnings

Warning Can Be Turned Off
    Run Tests    no_warn.robot
    Leave Snapshot Behind    no_warn
    Run Tests    no_warn.robot
    There Should Be No Warnings

Snapshot Left Behind By A Type Change Is Reported
    [Documentation]    Text becoming JSON changes the extension; the old file is then unused.
    Run Tests    basics.robot
    Leave Snapshot Behind    basics    Structured_Snapshot.txt
    Run Tests    basics.robot
    Warnings Should Be    Structured_Snapshot.txt

Command Line Reports And Deletes After A Robot Run
    Run Tests
    ${left}=    Leave Snapshot Behind
    Run Tests
    Run Unused Check
    Should Be Equal As Integers    ${RC}    1    ${STDOUT}
    Should Contain    ${STDOUT}    suites/__snapshots__/basics/Removed_Test.txt
    Run Unused Check    --delete
    Should Be Equal As Integers    ${RC}    0    ${STDOUT}
    File Should Not Exist    ${left}
    ${count}=    Count Files In Directory    ${SNAPSHOTS}/basics
    Should Be Equal As Integers    ${count}    9

Command Line Does Not Judge A Filtered Run
    Run Tests    basics.robot
    Leave Snapshot Behind
    Run Tests    basics.robot    --test    Text Snapshot
    Run Unused Check
    Should Be Equal As Integers    ${RC}    0    ${STDOUT}
    Should Contain    ${STDOUT}    Not checked
    Should Contain    ${STDOUT}    basics.robot

Command Line Reports The Directory Of A Removed Suite
    Run Tests
    Remove File    ${WORKSPACE}/suites/shared.robot
    Run Tests
    Run Unused Check
    Should Be Equal As Integers    ${RC}    1    ${STDOUT}
    Should Contain    ${STDOUT}    Snapshot directories without a suite file: 1
    Should Contain    ${STDOUT}    __snapshots__/shared

Old Records In The Output Directory Do Not Hide Unused Snapshots
    [Documentation]    A second run into the same output directory must not inherit the usage of the first.
    Run Tests    basics.robot
    Create File    ${WORKSPACE}/suites/basics.robot
    ...    *** Settings ***\nLibrary${SPACE * 4}SnapshotLibrary\n\n*** Test Cases ***\nOnly Test\n${SPACE * 4}Should Match Snapshot${SPACE * 4}only\n
    Set Test Variable    ${RUNS}    ${0}
    Run Tests    basics.robot
    Run Unused Check
    Should Be Equal As Integers    ${RC}    1    ${STDOUT}
    Should Contain    ${STDOUT}    Text_Snapshot.txt
