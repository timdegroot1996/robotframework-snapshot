*** Settings ***
Library    SnapshotLibrary    scrubbers=uuid
Suite Setup    Add Snapshot Scrubber    timestamp

*** Test Cases ***
Import And Suite Scrubbers Apply
    Should Match Snapshot    id ${UUID} at ${NOW}

Test Scoped Custom Scrubber
    Add Snapshot Scrubber    order    pattern=ORD-\\d+    scope=test
    Should Match Snapshot    order ORD-${NUMBER} created

Test Scope Has Ended
    [Documentation]    The order scrubber of the previous test must be gone.
    Should Match Snapshot    order ORD-1 created

Per Call Scrubber
    Should Match Snapshot    took ${NUMBER} ms    scrubbers=duration

Replacement With Group
    Add Snapshot Scrubber    port    pattern=(localhost):\\d+    replacement=\\1:<PORT>    scope=test
    Should Match Snapshot    http://localhost:${NUMBER}/health
