import pytest

from SnapshotLibrary import core


def xml(value, ignore):
    return core.prepare(value, "xml", ignore)[0]


def test_element_content_is_masked():
    assert xml("<a><id>7</id><n>x</n></a>", ".//id") == "<a>\n  <id>&lt;IGNORED&gt;</id>\n  <n>x</n>\n</a>\n"


def test_children_of_a_masked_element_are_dropped():
    assert xml('<a><meta k="1"><t>1</t></meta></a>', "meta") == '<a>\n  <meta k="1">&lt;IGNORED&gt;</meta>\n</a>\n'


def test_attribute_is_masked():
    assert xml('<a><o id="9" n="x"/></a>', ".//o/@id") == '<a>\n  <o id="&lt;IGNORED&gt;" n="x"/>\n</a>\n'


def test_absolute_path_and_several_paths():
    text = xml('<a id="1"><b>2</b></a>', "//b;/@id")
    assert text == '<a id="&lt;IGNORED&gt;">\n  <b>&lt;IGNORED&gt;</b>\n</a>\n'


def test_document_prefixes_work_in_the_path_and_are_kept():
    source = '<s:Envelope xmlns:s="urn:soap"><s:Body><s:Id>1</s:Id></s:Body></s:Envelope>'
    text = xml(source, ".//s:Id")
    assert text == '<s:Envelope xmlns:s="urn:soap">\n  <s:Body>\n    <s:Id>&lt;IGNORED&gt;</s:Id>\n  </s:Body>\n</s:Envelope>\n'


def test_predicate():
    assert "<i>keep</i>" in xml('<a><i k="x">1</i><i>keep</i></a>', ".//i[@k='x']")


def test_no_match_changes_nothing():
    assert xml("<a><b>1</b></a>", ".//missing") == "<a>\n  <b>1</b>\n</a>\n"


def test_invalid_xpath_fails_clearly():
    with pytest.raises(ValueError, match="Unsupported XPath"):
        xml("<a/>", ".//b[")
