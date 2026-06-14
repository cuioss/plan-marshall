# ruff: noqa: I001, E402
"""Tests for ``parse_flat_yaml_config`` in ``_analyze_shared.py``.

Focus: the bare comma-separated inline value form. A value such as
``plugin-doctor-disable: rule-1, rule-2`` must be split into a multi-element
list (each rule individually suppressible), not stored as a single scalar
string. This guards the fix that always routes a present inline value through
``_parse_inline_list`` rather than only the bracketed ``[..]`` form.
"""

import sys

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')
sys.path.insert(0, str(_SCRIPTS_DIR))

_shared = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_shared.py', '_analyze_shared'
)

parse_flat_yaml_config = _shared.parse_flat_yaml_config
read_frontmatter_disable_list = _shared.read_frontmatter_disable_list


def test_bare_comma_separated_value_splits_into_list():
    # Arrange
    content = 'plugin-doctor-disable: rule-1, rule-2, rule-3\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1', 'rule-2', 'rule-3']


def test_bracketed_inline_list_still_parsed():
    # Arrange
    content = 'plugin-doctor-disable: [rule-1, rule-2]\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1', 'rule-2']


def test_single_scalar_value_normalised_to_single_element_list():
    # Arrange
    content = 'plugin-doctor-disable: rule-1\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1']


def test_block_list_form_still_parsed():
    # Arrange
    content = 'plugin-doctor-disable:\n  - rule-1\n  - rule-2\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1', 'rule-2']


def test_bare_comma_separated_value_with_trailing_comment():
    # Arrange
    content = 'plugin-doctor-disable: rule-1, rule-2  # justified\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1', 'rule-2']


def test_quoted_tokens_in_bare_comma_separated_value_stripped():
    # Arrange
    content = 'plugin-doctor-disable: "rule-1", \'rule-2\'\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == ['rule-1', 'rule-2']


def test_empty_value_retained_as_empty_list():
    # Arrange
    content = 'plugin-doctor-disable:\n'

    # Act
    result = parse_flat_yaml_config(content)

    # Assert
    assert result['plugin-doctor-disable'] == []


def test_read_frontmatter_disable_list_handles_bare_comma_separated():
    # Arrange
    content = '---\nplugin-doctor-disable: rule-1, rule-2\n---\nbody\n'

    # Act
    result = read_frontmatter_disable_list(content)

    # Assert
    assert result == {'rule-1', 'rule-2'}
