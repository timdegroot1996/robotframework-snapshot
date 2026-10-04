*** Settings ***
Documentation       Recording, matching, updating and strict mode.
Resource            ../resources/atest_resource.robot
Test Setup          Create Workspace


*** Test Cases ***
First Run Records And Warns
    Run Tests    basics.robot
    Run Should Have Passed
    Snapshot Files Should Be    basics
    ...    Get_Snapshot_Returns_Stored_Value.txt
    ...    Get_Snapshot_Returns_Stored_Value__stored.json
    ...    Ignore_By_JSONPath.json
    ...    Json_String_In_Canonical_Form.json
    ...    Several_Snapshots_In_One_Test.txt
    ...    Several_Snapshots_In_One_Test__2.txt
    ...    Several_Snapshots_In_One_Test__body.json
    ...    Structured_Snapshot.json
    ...    Text_Snapshot.txt
    @{warnings}=    Get Warnings
    Length Should Be    ${warnings}    9
    FOR    ${warning}    IN    @{warnings}
        Should Contain    ${warning}    did not exist and was recorded
    END

Recorded Content Is Readable
    Run Tests    basics.robot
    Snapshot Should Be    basics/Text_Snapshot.txt    line one\nline two\n
    Snapshot Should Be    basics/Structured_Snapshot.json
    ...    {\n${SPACE * 2}"id": 42,\n${SPACE * 2}"name": "Widget",\n${SPACE * 2}"updated_at": "2026-01-02 03:04:05"\n}\n
    Snapshot Should Be    basics/Json_String_In_Canonical_Form.json    {\n${SPACE * 2}"a": 2,\n${SPACE * 2}"b": 1\n}\n

Second Run Matches Without Warnings
    Run Tests    basics.robot
    Run Tests    basics.robot
    Run Should Have Passed
    There Should Be No Warnings

Change Fails With A Diff In The Message
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=changed text
    Should Be Equal As Integers    ${RC}    1
    Test Status Should Be    FAIL    Text Snapshot
    Test Status Should Be    PASS    Structured Snapshot
    ${message}=    Get Test Message    Text Snapshot
    Should Contain    ${message}    suites/__snapshots__/basics/Text_Snapshot.txt' does not match
    Should Contain    ${message}    -line two
    Should Contain    ${message}    +changed text
    Should Contain    ${message}    REFERENCE_RUN:True
    Should Contain    ${message}    --- snapshot\n+++ actual\n
    # a diff that fits in the message is logged in colour, folded
    ${messages}=    Get Log Messages    Text Snapshot
    Should Contain Match    ${messages}    <details><summary><b>Diff in colour</b>*
    Snapshot Should Be    basics/Text_Snapshot.txt    line one\nline two\n

Long Diff Is Shortened At The End, Not By Robot Framework
    Run Tests    basics.robot
    ${long}=    Evaluate    "\\n".join(f"changed line {n}" for n in range(60))
    Run Tests    basics.robot    TEXT=${long}
    ${message}=    Get Test Message    Text Snapshot
    Should Not Contain    ${message}    Message content over the limit has been removed
    Should Contain    ${message}    +changed line 0
    Should Contain    ${message}    more diff lines. The full diff is in the log; run with --maxerrorlines NONE
    Should End With    ${message}    --variable REFERENCE_RUN:True
    ${messages}=    Get Log Messages    Text Snapshot
    Should Contain Match    ${messages}    <details open><summary><b>Full diff in colour. The failure message shows the first * of * lines</b>*

Long Diff Is Shown Whole Without A Message Limit
    Run Tests    basics.robot
    ${long}=    Evaluate    "\\n".join(f"changed line {n}" for n in range(60))
    Run Tests    basics.robot    --maxerrorlines    NONE    TEXT=${long}
    ${message}=    Get Test Message    Text Snapshot
    Should Contain    ${message}    +changed line 59
    Should Not Contain    ${message}    more diff lines

Actual Value Is Not Saved By Default
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=changed text
    Directory Should Not Exist    ${OUTDIR}/snapshot_actual

Actual Value Is Saved When Asked With A Variable
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=changed text    SNAPSHOT_SAVE_ACTUAL=True
    ${actual}=    Get File    ${OUTDIR}/snapshot_actual/basics/Text_Snapshot.txt
    Should Be Equal    ${actual}    changed text\n

Actual Value Is Saved When Asked On Import
    Run Tests    save_actual.robot
    Run Tests    save_actual.robot    CONTENT=b
    ${actual}=    Get File    ${OUTDIR}/snapshot_actual/save_actual/Saved_On_Mismatch.txt
    Should Be Equal    ${actual}    b\n

Reference Run Updates
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=new text    REFERENCE_RUN=True
    Run Should Have Passed
    There Should Be No Warnings
    Snapshot Should Be    basics/Text_Snapshot.txt    new text\n
    ${messages}=    Get Log Messages    Text Snapshot
    Should Contain Match    ${messages}    <details open><summary><b>Changes written to the snapshot</b>*
    Run Tests    basics.robot    TEXT=new text
    Run Should Have Passed

Strict Mode Fails On A Missing Snapshot And Records Nothing
    Run Tests    basics.robot    --test    Text Snapshot    SNAPSHOT_STRICT=True
    Should Be Equal As Integers    ${RC}    1
    ${message}=    Get Test Message    Text Snapshot
    Should Contain    ${message}    does not exist and strict mode is on
    Directory Should Not Exist    ${SNAPSHOTS}/basics

Strict Mode Passes When Snapshots Exist
    Run Tests    basics.robot
    Run Tests    basics.robot    SNAPSHOT_STRICT=True
    Run Should Have Passed

False Like Values Do Not Enable A Mode
    Run Tests    basics.robot
    Run Tests    basics.robot    TEXT=changed    REFERENCE_RUN=False
    Test Status Should Be    FAIL    Text Snapshot
