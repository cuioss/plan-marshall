#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for toon_parser.py module."""


# Import shared infrastructure (conftest.py sets up PYTHONPATH)

# Import the module under test (PYTHONPATH set by conftest)
import pytest
from toon_parser import (
    block_scalar_body_continues,
    block_scalar_header_indent,
    parse_toon,
    parse_toon_table,
    serialize_toon,
    value_needs_quoting,
)

# =============================================================================
# Test: Basic Key-Value Parsing
# =============================================================================


def test_simple_key_value():
    """Test parsing simple key: value pairs."""
    toon = """
name: Alice
age: 30
"""
    result = parse_toon(toon)
    assert result['name'] == 'Alice', f"Expected 'Alice', got {result['name']}"
    assert result['age'] == 30, f'Expected 30, got {result["age"]}'


def test_string_values():
    """Test various string value formats."""
    toon = """
plain: hello world
quoted: "hello, world"
empty:
"""
    result = parse_toon(toon)
    assert result['plain'] == 'hello world'
    assert result['quoted'] == 'hello, world'
    assert result['empty'] == ''


def test_boolean_values():
    """Test boolean parsing."""
    toon = """
active: true
disabled: false
"""
    result = parse_toon(toon)
    assert result['active'] is True
    assert result['disabled'] is False


def test_null_value():
    """Test null parsing."""
    toon = """
value: null
"""
    result = parse_toon(toon)
    assert result['value'] is None


def test_number_values():
    """Test integer and float parsing."""
    toon = """
count: 42
negative: -10
decimal: 3.14159
percent: 75%
"""
    result = parse_toon(toon)
    assert result['count'] == 42
    assert result['negative'] == -10
    assert result['decimal'] == 3.14159
    assert result['percent'] == 75


def test_comments():
    """Test that comments are ignored."""
    toon = """
# This is a comment
name: Alice
# Another comment
age: 30
"""
    result = parse_toon(toon)
    assert result['name'] == 'Alice'
    assert result['age'] == 30
    assert '#' not in str(result)


# =============================================================================
# Test: Nested Objects
# =============================================================================


def test_nested_object():
    """Test parsing nested objects via indentation."""
    toon = """
user:
  name: Alice
  age: 30
"""
    result = parse_toon(toon)
    assert 'user' in result
    assert result['user']['name'] == 'Alice'
    assert result['user']['age'] == 30


def test_deeply_nested_object():
    """Test parsing multiple nesting levels."""
    toon = """
level1:
  level2:
    level3:
      value: deep
"""
    result = parse_toon(toon)
    assert result['level1']['level2']['level3']['value'] == 'deep'


def test_multiple_nested_objects():
    """Test parsing sibling nested objects."""
    toon = """
user:
  name: Alice
metadata:
  created: 2025-12-02
"""
    result = parse_toon(toon)
    assert result['user']['name'] == 'Alice'
    assert result['metadata']['created'] == '2025-12-02'


# =============================================================================
# Test: Uniform Arrays
# =============================================================================


def test_uniform_array():
    """Test parsing uniform array with field headers."""
    toon = """
users[2]{id,name,role}:
1,Alice,admin
2,Bob,user
"""
    result = parse_toon(toon)
    assert 'users' in result
    assert len(result['users']) == 2
    assert result['users'][0] == {'id': 1, 'name': 'Alice', 'role': 'admin'}
    assert result['users'][1] == {'id': 2, 'name': 'Bob', 'role': 'user'}


def test_uniform_array_with_empty_values():
    """Test array rows with missing values."""
    toon = """
items[2]{id,name,description}:
1,Widget,
2,Gadget,A useful gadget
"""
    result = parse_toon(toon)
    assert result['items'][0]['description'] == ''
    assert result['items'][1]['description'] == 'A useful gadget'


def test_uniform_array_with_quoted_values():
    """Test array with quoted values containing commas."""
    toon = """
products[2]{id,name,description}:
1,Widget,"Small, efficient gadget"
2,Gadget,"Multi-purpose tool, batteries included"
"""
    result = parse_toon(toon)
    assert result['products'][0]['description'] == 'Small, efficient gadget'
    assert result['products'][1]['description'] == 'Multi-purpose tool, batteries included'


def test_nested_uniform_array():
    """Test uniform array inside nested object."""
    toon = """
data:
  items[2]{id,value}:
  1,alpha
  2,beta
"""
    result = parse_toon(toon)
    assert result['data']['items'][0] == {'id': 1, 'value': 'alpha'}
    assert result['data']['items'][1] == {'id': 2, 'value': 'beta'}


# =============================================================================
# Test: Simple Arrays
# =============================================================================


def test_simple_array():
    """Test parsing simple list with - markers."""
    toon = """
tags[3]:
- python
- toon
- parser
"""
    result = parse_toon(toon)
    assert result['tags'] == ['python', 'toon', 'parser']


def test_simple_array_with_numbers():
    """Test simple array with numeric values."""
    toon = """
scores[3]:
- 100
- 85
- 92
"""
    result = parse_toon(toon)
    assert result['scores'] == [100, 85, 92]


def test_simple_array_with_hyphenated_keys():
    """Test simple arrays where key contains hyphens (e.g., oauth-sheriff-core[1]:)."""
    toon = """
dependencies:
  oauth-sheriff-quarkus-parent[1]:
    - oauth-sheriff-core
  my-module[2]:
    - dep-one
    - dep-two
"""
    result = parse_toon(toon)
    assert 'dependencies' in result
    deps = result['dependencies']
    assert 'oauth-sheriff-quarkus-parent' in deps
    assert deps['oauth-sheriff-quarkus-parent'] == ['oauth-sheriff-core']
    assert 'my-module' in deps
    assert deps['my-module'] == ['dep-one', 'dep-two']


def test_roundtrip_hyphenated_array_keys():
    """Test serialize -> parse roundtrip with hyphenated array keys."""
    original = {'dependencies': {'oauth-sheriff-core': ['lib-one', 'lib-two'], 'my-app-module': ['oauth-sheriff-core']}}
    serialized = serialize_toon(original)
    parsed = parse_toon(serialized)
    assert parsed['dependencies']['oauth-sheriff-core'] == ['lib-one', 'lib-two']
    assert parsed['dependencies']['my-app-module'] == ['oauth-sheriff-core']


# =============================================================================
# Test: Multi-line Values
# =============================================================================


def test_multiline_value():
    """Test parsing multi-line string values."""
    toon = """
description: |
  This is a multi-line
  description that spans
  multiple lines.
name: test
"""
    result = parse_toon(toon)
    assert 'multi-line' in result['description']
    assert result['name'] == 'test'


# =============================================================================
# Test: block_scalar_header_indent / block_scalar_body_continues
# =============================================================================
#
# The two predicates are exported BOUNDARIES: a second reader that must agree
# with parse_toon about where opaque prose starts and stops derives it from here
# instead of restating it. Each side is a matched pair — a rule that always said
# "yes" and one that always said "no" are equally satisfiable by half a pair.


@pytest.mark.parametrize(
    'line,expected_indent,reason',
    [
        ('description: |', 0, 'the canonical example'),
        ('  description: |', 2, 'a nested header reports its own indent'),
        ('task.name: |', 0, 'a dotted key is text before the first colon like any other'),
        ('a b c: |', 0, 'the parser never constrains the key, so spaces are permitted'),
        ('description:   |  ', 0, 'surrounding whitespace around the marker is stripped'),
    ],
)
def test_block_scalar_header_indent_matches_the_parser_key_rule(line, expected_indent, reason):
    """Any text up to the first colon opens a block scalar when the value is ``|``.

    ``_parse_object`` takes ``content.index(':')`` and tests the remainder against
    ``'|'``, so the key class is unbounded. A predicate narrower than that reports
    "not a block scalar" for a line the parser reads as one, and the block's prose
    body is then scanned as document structure by whoever asked.
    """
    assert block_scalar_header_indent(line) == expected_indent, reason


@pytest.mark.parametrize(
    'line,reason',
    [
        ('description: text', 'a value that is not the bare marker'),
        ('description: | more', 'the marker must be the WHOLE value'),
        ('foo: bar: |', 'only the FIRST colon splits, so the value here is "bar: |"'),
        ('steps[2]:', 'an array header carries no value at all'),
        ('# description: |', 'the parser skips comments before it looks for a key'),
        ('', 'a blank line is skipped, never a header'),
        ('   ', 'a whitespace-only line is likewise skipped'),
        ('no colon here', 'a line with no colon is not a key/value pair'),
    ],
)
def test_block_scalar_header_indent_reports_none_for_non_headers(line, reason):
    """MATCHED NEGATIVE — the predicate discriminates rather than accepting every line.

    Without these cases a predicate that returned ``0`` unconditionally would
    satisfy every positive case above, and every document would read as one
    opaque block.
    """
    assert block_scalar_header_indent(line) is None, reason


def test_block_scalar_with_a_key_outside_the_word_class_keeps_its_body_as_prose():
    """END-TO-END — the parser itself treats a dotted-key block as opaque prose.

    This is the case a ``[\\w_-]+`` key class misses. The body carries a line that
    reads as a list header; it must arrive as text inside the value, and must NOT
    become a top-level key.
    """
    toon = 'task.name: |\n  Prose line one.\n  steps:\n    - src/not_a_step.py\nname: after\n'

    result = parse_toon(toon)

    assert result['task.name'] == 'Prose line one.\nsteps:\n  - src/not_a_step.py'
    assert 'steps' not in result
    assert result['name'] == 'after'


@pytest.mark.parametrize(
    'line,continues,reason',
    [
        ('', True, 'a blank line is preserved inside the body'),
        ('      ', True, 'a whitespace-only line is blank for this purpose'),
        ('    deeper', True, 'indented past the header, so still body'),
        ('  same', False, 'at the header indent, so the block has closed'),
        ('outer', False, 'outside the header indent, so the block has closed'),
    ],
)
def test_block_scalar_body_continues_reports_the_block_extent(line, continues, reason):
    """The body runs while lines are blank or deeper, and closes at the first that is not.

    Both directions are pinned in one parametrization: a predicate stuck at
    ``True`` swallows the rest of the document, and one stuck at ``False`` makes
    every block empty.
    """
    assert block_scalar_body_continues(line, 2) is continues, reason


# =============================================================================
# Test: Complete Handoff Document
# =============================================================================


def test_handoff_document():
    """Test parsing a complete handoff document."""
    toon = """
from: plan-init-skill
to: plan-configure-skill
handoff_id: init-001
timestamp: 2025-12-02T10:30:00Z

task:
  description: Initialize plan
  status: completed
  progress: 100

plan_id: jwt-auth

artifacts:
  files_created[2]{path,type}:
  task.md,markdown
  config.toon,toon

next_action: Configure plan type
next_focus: Extract requirements
"""
    result = parse_toon(toon)

    # Check top-level fields
    assert result['from'] == 'plan-init-skill'
    assert result['to'] == 'plan-configure-skill'
    assert result['plan_id'] == 'jwt-auth'

    # Check nested task object
    assert result['task']['status'] == 'completed'
    assert result['task']['progress'] == 100

    # Check artifacts array
    assert len(result['artifacts']['files_created']) == 2
    assert result['artifacts']['files_created'][0]['path'] == 'task.md'


def test_error_handoff_document():
    """Test parsing an error handoff document."""
    toon = """
from: build-verify-agent
to: java-fix-build-agent
handoff_id: error-001

task:
  status: failed

error:
  type: build_failure
  message: Compilation failed

alternatives[3]:
- Fix build error and retry
- View full build log
- Skip to next task
"""
    result = parse_toon(toon)

    assert result['task']['status'] == 'failed'
    assert result['error']['type'] == 'build_failure'
    assert len(result['alternatives']) == 3
    assert result['alternatives'][0] == 'Fix build error and retry'


# =============================================================================
# Test: Serialization
# =============================================================================


def test_serialize_simple():
    """Test serializing simple key-value pairs."""
    data = {'name': 'Alice', 'age': 30, 'active': True}
    result = serialize_toon(data)
    assert 'name: Alice' in result
    assert 'age: 30' in result
    assert 'active: true' in result


def test_serialize_nested():
    """Test serializing nested objects."""
    data = {'user': {'name': 'Alice', 'role': 'admin'}}
    result = serialize_toon(data)
    assert 'user:' in result
    assert 'name: Alice' in result


def test_serialize_uniform_array():
    """Test serializing uniform arrays."""
    data = {'users': [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]}
    result = serialize_toon(data)
    assert 'users[2]{id,name}:' in result
    assert '1,Alice' in result
    assert '2,Bob' in result


def test_serialize_simple_array():
    """Test serializing simple arrays."""
    data = {'tags': ['python', 'toon']}
    result = serialize_toon(data)
    assert 'tags[2]:' in result
    assert '- python' in result
    assert '- toon' in result


def test_roundtrip():
    """Test that parsing then serializing preserves data."""
    original = """
name: Alice
age: 30
active: true

metadata:
  version: 1.0

roles[2]{id,name}:
1,admin
2,user
"""
    parsed = parse_toon(original)
    serialized = serialize_toon(parsed)
    reparsed = parse_toon(serialized)

    assert reparsed['name'] == parsed['name']
    assert reparsed['age'] == parsed['age']
    assert reparsed['active'] == parsed['active']
    assert reparsed['metadata']['version'] == parsed['metadata']['version']
    assert reparsed['roles'] == parsed['roles']


# =============================================================================
# Test: Edge Cases
# =============================================================================


def test_empty_input():
    """Test parsing empty input."""
    result = parse_toon('')
    assert result == {}


def test_only_comments():
    """Test parsing input with only comments."""
    toon = """
# Just a comment
# Another comment
"""
    result = parse_toon(toon)
    assert result == {}


def test_whitespace_handling():
    """Test handling of various whitespace."""
    toon = """
name:   Alice
age:30
"""
    result = parse_toon(toon)
    assert result['name'] == 'Alice'
    assert result['age'] == 30


def test_colon_in_value():
    """Test values containing colons."""
    toon = """
timestamp: 2025-12-02T10:30:00Z
url: https://example.com
"""
    result = parse_toon(toon)
    assert result['timestamp'] == '2025-12-02T10:30:00Z'
    assert result['url'] == 'https://example.com'


# =============================================================================
# Test: parse_toon_table convenience function
# =============================================================================


def test_parse_toon_table_basic():
    """Test extracting a table from TOON content."""
    toon = """
status: success
total: 2
users[2]{id,name,role}:
  1\tAlice\tadmin
  2\tBob\tuser
"""
    users = parse_toon_table(toon, 'users')
    assert len(users) == 2
    assert users[0] == {'id': 1, 'name': 'Alice', 'role': 'admin'}
    assert users[1] == {'id': 2, 'name': 'Bob', 'role': 'user'}


def test_parse_toon_table_missing_key():
    """Test that missing key returns empty list."""
    toon = 'status: success\n'
    result = parse_toon_table(toon, 'items')
    assert result == []


def test_parse_toon_table_null_markers():
    """Test null_markers converts specified values to None."""
    toon = """
items[2]{id,name,value}:
  1\tAlice\t-
  2\t~\t100
"""
    items = parse_toon_table(toon, 'items', null_markers={'-', '~'})
    assert len(items) == 2
    assert items[0]['value'] is None
    assert items[1]['name'] is None
    assert items[1]['value'] == 100


def test_parse_toon_table_empty_array():
    """Test extracting empty table."""
    toon = 'items[0]{id,name}:\n'
    items = parse_toon_table(toon, 'items')
    assert items == []


def test_parse_toon_table_non_list_key():
    """Test that a non-list key returns empty list."""
    toon = 'status: success\n'
    result = parse_toon_table(toon, 'status')
    assert result == []


# =============================================================================
# Test: value_needs_quoting — the serializer's exported quoting decision
# =============================================================================
#
# The predicate is the serializer's own rule, exported so consumers can tell a
# quote serialize_toon was OBLIGED to add from one a human added by hand. Each
# disjunct it decides gets a case here, because a consumer that mis-reads any
# one of them mis-classifies a legitimate quote as an anti-pattern (or the
# reverse).


@pytest.mark.parametrize(
    'value,reason',
    [
        ('a,b', 'comma would split a CSV row'),
        ('bundle:skill', 'colon would read as a key/value separator'),
        ('line one\nline two', 'newline would break the record'),
        ('say "hi"', 'embedded double-quote needs escaping'),
        ('#leading-hash', 'leading # would read as a comment'),
        ('- leading dash', 'leading "- " would read as a list item'),
        ('true', 'reserved literal would parse as a boolean'),
        ('false', 'reserved literal would parse as a boolean'),
        ('null', 'reserved literal would parse as None'),
        ('', 'empty string is indistinguishable from an absent value'),
        ('42', 'bare integer would parse as int'),
        ('-42', 'negative integer would parse as int'),
        ('3.14', 'bare float would parse as float'),
        ('95%', 'percentage would parse as int'),
    ],
)
def test_value_needs_quoting_true_for_each_disjunct(value, reason):
    """Every disjunct the predicate decides reports True."""
    assert value_needs_quoting(value) is True, f'expected quoting because {reason}'


@pytest.mark.parametrize(
    'value',
    [
        'plain',
        'hello world',
        'write-replace',
        'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md',
        'a-b_c',
        'not#leading',
        '-notalistitem',
        '3.x',
    ],
)
def test_value_needs_quoting_false_for_plain_values(value):
    """A value with no special character or reserved shape is emitted bare.

    This is the matched negative side of the parametrization above: without it a
    predicate that simply returned True would pass every case there.
    """
    assert value_needs_quoting(value) is False


def test_value_needs_quoting_honours_the_active_table_separator():
    """The separator argument is what makes the decision table-aware.

    A tab is unremarkable in a comma-separated table and fatal in a
    tab-separated one; the predicate must answer differently for the same value.
    """
    assert value_needs_quoting('a\tb', table_separator='\t') is True
    assert value_needs_quoting('a\tb', table_separator=',') is False


def test_serialize_toon_output_is_byte_exact_for_every_quoting_disjunct():
    """Pin the serializer's exact bytes for a record exercising the quoting rule.

    ``value_needs_quoting`` was extracted out of ``_serialize_value`` as a pure
    move, so the emitted bytes must not shift. This golden literal is what makes
    a future edit to the predicate observable here rather than only in a
    consumer: any change to which values get quoted changes this string.
    """
    data = {
        'plain': 'hello world',
        'notation': 'bundle:skill',
        'listy': ['a,b', 'plain', '42'],
        'rows': [{'target': 'src/a.py', 'intent': 'write-replace'}],
    }

    assert serialize_toon(data) == (
        'plain: hello world\n'
        'notation: "bundle:skill"\n'
        'listy[3]:\n'
        '  - "a,b"\n'
        '  - plain\n'
        '  - "42"\n'
        'rows[1]{target,intent}:\n'
        '  src/a.py,write-replace'
    )
