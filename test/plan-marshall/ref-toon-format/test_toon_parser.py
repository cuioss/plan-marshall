#!/usr/bin/env python3
"""Tests for toon_parser.py module."""


# Import shared infrastructure (conftest.py sets up PYTHONPATH)

# Import the module under test (PYTHONPATH set by conftest)
from toon_parser import parse_toon, serialize_toon

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
