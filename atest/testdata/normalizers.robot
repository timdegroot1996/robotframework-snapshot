*** Settings ***
Library    SnapshotLibrary    normalizers=uuid
Suite Setup    Add Snapshot Normalizer    timestamp

*** Test Cases ***
Import And Suite Normalizers Apply
    Should Match Snapshot    id ${UUID} at ${NOW}

Test Scoped Custom Normalizer
    Add Snapshot Normalizer    order    pattern=ORD-\\d+    scope=test
    Should Match Snapshot    order ORD-${NUMBER} created

Test Scope Has Ended
    [Documentation]    The order normalizer of the previous test must be gone.
    Should Match Snapshot    order ORD-1 created

Per Call Normalizer
    Should Match Snapshot    took ${NUMBER} ms    normalizers=duration

Replacement With Group
    Add Snapshot Normalizer    port    pattern=(localhost):\\d+    replacement=\\1:<PORT>    scope=test
    Should Match Snapshot    http://localhost:${NUMBER}/health
