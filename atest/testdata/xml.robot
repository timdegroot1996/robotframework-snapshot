*** Settings ***
Library    OperatingSystem
Library    XML
Library    SnapshotLibrary

*** Variables ***
${XML_TEXT}    <order a="1"><id>42</id></order>

*** Test Cases ***
Xml String In Canonical Form
    Should Match Snapshot    ${XML_TEXT}    format=xml

Xml Element Is Detected
    ${root}=    Parse XML    ${XML_TEXT}
    Should Match Snapshot    ${root}

Xml File In Canonical Form
    Create File    ${OUTPUT_DIR}/config.xml    ${XML_TEXT}
    Should Match File Snapshot    ${OUTPUT_DIR}/config.xml    format=xml

Xml Ignore By XPath
    Should Match Snapshot    ${XML_TEXT}    format=xml    ignore=.//id
