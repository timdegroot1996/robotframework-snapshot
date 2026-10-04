*** Settings ***
Documentation       What is stored for each kind of value, and how changing values are kept stable.
Resource            ../resources/atest_resource.robot
Test Setup          Create Workspace


*** Variables ***
${XML_COMPACT}      <?xml version="1.0"?><!-- note --><order b="2" a="1"><id>42</id>  <items><item/></items></order>
${XML_INDENTED}     SEPARATOR=\n
...                 <order a="1" b="2">
...                 ${SPACE * 4}<id>42</id>
...                 ${SPACE * 4}<items>
...                 ${SPACE * 8}<item></item>
...                 ${SPACE * 4}</items>
...                 </order>
${XML_STORED}       SEPARATOR=\n
...                 <order a="1" b="2">
...                 ${SPACE * 2}<id>42</id>
...                 ${SPACE * 2}<items>
...                 ${SPACE * 4}<item/>
...                 ${SPACE * 2}</items>
...                 </order>
...                 ${EMPTY}


*** Test Cases ***
Ignore Makes A Changing Field Stable
    Run Tests    basics.robot
    Run Tests    basics.robot    RANDOM_ID=999
    Test Status Should Be    PASS    Ignore By JSONPath
    ${stored}=    Get File    ${SNAPSHOTS}/basics/Ignore_By_JSONPath.json
    Should Contain    ${stored}    "id": "<IGNORED>"

Normalizers And Their Scopes
    Run Tests    normalizers.robot
    Run Should Have Passed
    Snapshot Should Be    normalizers/Import_And_Suite_Normalizers_Apply.txt    id <UUID> at <TIMESTAMP>\n
    Snapshot Should Be    normalizers/Test_Scoped_Custom_Normalizer.txt    order <ORDER> created\n
    Snapshot Should Be    normalizers/Test_Scope_Has_Ended.txt    order ORD-1 created\n
    Snapshot Should Be    normalizers/Per_Call_Normalizer.txt    took <DURATION>\n
    Snapshot Should Be    normalizers/Replacement_With_Group.txt    http://localhost:<PORT>/health\n
    Run Tests    normalizers.robot
    ...    UUID=00000000-0000-4000-8000-000000000000    NOW=2030-12-31 23:59:59    NUMBER=777
    Run Should Have Passed

Xml Is Stored Sorted And Indented
    Run Tests    xml.robot    XML_TEXT=${XML_COMPACT}
    Run Should Have Passed
    Snapshot Files Should Be    xml
    ...    Xml_Element_Is_Detected.xml
    ...    Xml_File_In_Canonical_Form.xml
    ...    Xml_Ignore_By_XPath.xml
    ...    Xml_String_In_Canonical_Form.xml
    Snapshot Should Be    xml/Xml_String_In_Canonical_Form.xml    ${XML_STORED}
    Snapshot Should Be    xml/Xml_Element_Is_Detected.xml    ${XML_STORED}
    Snapshot Should Be    xml/Xml_File_In_Canonical_Form.xml    ${XML_STORED}

Xml Layout Does Not Matter
    Run Tests    xml.robot    XML_TEXT=${XML_COMPACT}
    Run Tests    xml.robot    XML_TEXT=${XML_INDENTED}    SNAPSHOT_STRICT=True
    Run Should Have Passed

Xml Change Fails With A Diff
    Run Tests    xml.robot    XML_TEXT=${XML_COMPACT}
    ${changed}=    Replace String    ${XML_INDENTED}    42    43
    Run Tests    xml.robot    XML_TEXT=${changed}
    Should Be Equal As Integers    ${RC}    3
    Test Status Should Be    PASS    Xml Ignore By XPath
    ${message}=    Get Test Message    Xml String In Canonical Form
    Should Contain    ${message}    +${SPACE * 2}<id>43</id>

Xml Ignore By XPath
    Run Tests    xml.robot    XML_TEXT=${XML_COMPACT}
    ${stored}=    Get File    ${SNAPSHOTS}/xml/Xml_Ignore_By_XPath.xml
    Should Contain    ${stored}    <id>&lt;IGNORED&gt;</id>

File Snapshot And Custom Directory
    Run Tests    files.robot
    Run Should Have Passed
    Snapshot Should Be    files/File_Snapshot_Keeps_Extension.csv    id,name\n1,a\n
    ${custom}=    Get File    ${WORKSPACE}/custom_snaps/files/Custom_Directory.txt
    Should Be Equal    ${custom}    in custom dir\n
    Run Tests    files.robot    CONTENT=b
    Test Status Should Be    FAIL    File Snapshot Keeps Extension
    Test Status Should Be    PASS    Custom Directory

Snapshot In Suite Setup
    Run Tests    suite_setup.robot
    Run Should Have Passed
    Snapshot Files Should Be    suite_setup    After_Setup.txt    __suite__.txt

Shared Snapshot Is One File For Several Tests
    Run Tests    shared.robot
    Run Should Have Passed
    Snapshot Files Should Be    shared    Rows.json    help.txt
    # help is recorded by the first test and matched by the second
    Warnings Should Be    recorded    recorded
    Snapshot Should Be    shared/Rows.json    [\n${SPACE * 2}\["a", 1, null],\n${SPACE * 2}\["b", 2, 0.5]\n]\n
    Run Tests    shared.robot    HELP=changed
    Test Status Should Be    FAIL    Short Flag    Long Flag
