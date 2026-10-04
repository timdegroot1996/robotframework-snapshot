*** Settings ***
Library    OperatingSystem
Library    SnapshotLibrary

*** Test Cases ***
File Snapshot Keeps Extension
    Create File    ${OUTPUT_DIR}/export.csv    id,name\n1,${CONTENT}\n
    Should Match File Snapshot    ${OUTPUT_DIR}/export.csv

Missing File Fails
    Run Keyword And Expect Error    File '*' does not exist.
    ...    Should Match File Snapshot    ${OUTPUT_DIR}/nope.txt

Custom Directory
    ${previous}=    Set Snapshot Directory    ${EXECDIR}/custom_snaps
    Should Match Snapshot    in custom dir
    Set Snapshot Directory    ${previous}
