# ruff: noqa: I001, E402
"""Tests for ``parse_declared_tools`` in ``_analyze_coverage.py``.

Focus: the inline comma-separated tool-list form. ``parse_declared_tools``
must accept both documented field names — the ``tools:`` field and the
``allowed-tools:`` field — and return an identical, order-preserving list for
the same inline value. This guards the behavioral identity between the two
field names so neither spelling silently drops declared tools.
"""

import sys

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')
sys.path.insert(0, str(_SCRIPTS_DIR))

_coverage = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_coverage.py', '_analyze_coverage'
)

parse_declared_tools = _coverage.parse_declared_tools


def test_inline_tools_and_allowed_tools_field_names_are_equivalent():
    # Arrange
    tools_frontmatter = 'tools: Read, Write, Edit'
    allowed_tools_frontmatter = 'allowed-tools: Read, Write, Edit'

    # Act
    tools_result = parse_declared_tools(tools_frontmatter)
    allowed_tools_result = parse_declared_tools(allowed_tools_frontmatter)

    # Assert
    assert tools_result == ['Read', 'Write', 'Edit']
    assert allowed_tools_result == ['Read', 'Write', 'Edit']
    assert tools_result == allowed_tools_result
