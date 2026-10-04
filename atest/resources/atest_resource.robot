*** Settings ***
Documentation       Runs the suites in atest/testdata with robot or pabot and checks the results.
...
...                 Every test gets its own copy of the test data in
...                 ${WORKSPACES}/<suite>-<test>/suites, so snapshots recorded
...                 by one test never leak into another, also not when the
...                 acceptance tests themselves run in parallel with pabot. The
...                 workspaces are kept after the run, to look at what a test did.
...                 They are not under the output directory, because pabot would
...                 merge the inner runs' output.xml files into its own results.
Library             Collections
Library             OperatingSystem
Library             Process
Library             String
Library             OutputReader.py


*** Variables ***
${TESTDATA}         ${CURDIR}${/}..${/}testdata
${WORKSPACES}       ${EXECDIR}${/}results${/}workspaces
# set per test by `Create Workspace` and `Run Tests`
${WORKSPACE}        ${EMPTY}
${SNAPSHOTS}        ${EMPTY}
${PYTHON}           ${EMPTY}
${SCRIPTS}          ${EMPTY}
${RUNS}             ${0}
${OUTDIR}           ${EMPTY}
${RC}               ${-1}
${STDOUT}           ${EMPTY}
&{DEFAULTS}         RANDOM_ID=1    UUID=3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90    NOW=2026-01-02T03:04:05Z
...                 NUMBER=1    CONTENT=a    HELP=usage


*** Keywords ***
Create Workspace
    [Documentation]    Copies the test data into a fresh directory for this test.
    ${name}=    Replace String Using Regexp    ${SUITE NAME}-${TEST NAME}    [^\\w-]+    _
    ${workspace}=    Normalize Path    ${WORKSPACES}${/}${name}
    Remove Directory    ${workspace}    recursive=True
    Copy Directory    ${TESTDATA}    ${workspace}${/}suites
    ${python}=    Evaluate    sys.executable    modules=sys
    ${scripts}=    Evaluate    os.path.dirname(sys.executable)    modules=os,sys
    Set Test Variable    ${WORKSPACE}    ${workspace}
    Set Test Variable    ${SNAPSHOTS}    ${workspace}${/}suites${/}__snapshots__
    Set Test Variable    ${PYTHON}    ${python}
    Set Test Variable    ${SCRIPTS}    ${scripts}
    Set Test Variable    ${RUNS}    ${0}

Run Tests
    [Documentation]    Runs ``suite`` (a file in atest/testdata, or empty for all of them)
    ...    in the workspace and reads its output.xml.
    ...
    ...    ``options`` are passed to robot as they are, ``variables`` become
    ...    ``--variable NAME:value`` on top of ${DEFAULTS}. Sets ${RC}, ${STDOUT}
    ...    and ${OUTDIR} for the test.
    [Arguments]    ${suite}=    @{options}    ${runner}=robot    &{variables}
    ${runs}=    Evaluate    ${RUNS} + 1
    Set Test Variable    ${RUNS}    ${runs}
    ${outdir}=    Set Variable    ${WORKSPACE}${/}out${runs}
    IF    '${runner}' == 'pabot'
        # pabot inside pabot: the inner run must not start a second PabotLib server on the same port
        @{command}=    Create List    -m    pabot.pabot    --no-pabotlib    --testlevelsplit    --processes    4
    ELSE
        @{command}=    Create List    -m    robot
    END
    Append To List    ${command}    --outputdir    ${outdir}    --log    NONE    --report    NONE
    ${all}=    Create Dictionary    &{DEFAULTS}    &{variables}
    FOR    ${name}    ${value}    IN    &{all}
        Append To List    ${command}    --variable    ${name}:${value}
    END
    ${target}=    Set Variable If    '${suite}'    suites${/}${suite}    suites
    # pabot starts `robot` from PATH, so put this interpreter's scripts first
    # in case the virtual environment is not activated.
    ${result}=    Run Process    ${PYTHON}    @{command}    @{options}    ${target}
    ...    cwd=${WORKSPACE}    stderr=STDOUT    env:PATH=${SCRIPTS}${:}%{PATH}
    Log    ${result.stdout}
    Set Test Variable    ${RC}    ${result.rc}
    Set Test Variable    ${STDOUT}    ${result.stdout}
    Set Test Variable    ${OUTDIR}    ${outdir}
    Read Output    ${outdir}${/}output.xml

Run Should Have Passed
    Should Be Equal As Integers    ${RC}    0    Run failed:\n${STDOUT}

Run Unused Check
    [Documentation]    Runs ``python -m SnapshotLibrary unused`` on the output of the last run.
    ...    Sets ${RC} and ${STDOUT}, with forward slashes in paths.
    [Arguments]    @{options}
    ${result}=    Run Process    ${PYTHON}    -m    SnapshotLibrary    unused    ${OUTDIR}    @{options}
    ...    cwd=${WORKSPACE}    stderr=STDOUT
    ${stdout}=    Replace String    ${result.stdout}    \\    /
    Log    ${stdout}
    Set Test Variable    ${RC}    ${result.rc}
    Set Test Variable    ${STDOUT}    ${stdout}

Snapshot Should Be
    [Documentation]    ``path`` is relative to the __snapshots__ directory, for example ``basics/Text_Snapshot.txt``.
    [Arguments]    ${path}    ${expected}
    ${content}=    Get File    ${SNAPSHOTS}${/}${path}
    Should Be Equal    ${content}    ${expected}

Snapshot Files Should Be
    [Arguments]    ${suite}    @{expected}
    @{files}=    List Files In Directory    ${SNAPSHOTS}${/}${suite}
    Sort List    ${files}
    Lists Should Be Equal    ${files}    ${expected}

Leave Snapshot Behind
    [Documentation]    Creates a snapshot file no test uses, as a removed test would leave it.
    [Arguments]    ${suite}=basics    ${name}=Removed_Test.txt
    Create File    ${SNAPSHOTS}${/}${suite}${/}${name}    left behind\n
    RETURN    ${SNAPSHOTS}${/}${suite}${/}${name}

Warnings Should Be
    [Documentation]    Every warning of the last run must contain one of ``expected``, in order.
    [Arguments]    @{expected}
    @{warnings}=    Get Warnings
    Length Should Be    ${warnings}    ${{len($expected)}}    Warnings: ${warnings}
    FOR    ${warning}    ${text}    IN ZIP    ${warnings}    ${expected}
        Should Contain    ${warning}    ${text}
    END

There Should Be No Warnings
    Warnings Should Be

Skip If Pabot Cannot Merge
    ${major}=    Evaluate    int(robot.version.get_version().split('.')[0])    modules=robot.version
    Skip If    ${major} < 7    pabot 5 fails to merge its own results on Robot Framework 6
