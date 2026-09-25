#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for the manage-files open-in-ide config gate."""

import json

import pytest
from _manage_files_open_in_ide_fixtures import is_open_in_ide_enabled

# =============================================================================
# is_open_in_ide_enabled — config gate
# =============================================================================


def test_is_open_in_ide_enabled_explicit_true(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )

    result = is_open_in_ide_enabled()

    assert result is True


def test_is_open_in_ide_enabled_explicit_false(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': False}}), encoding='utf-8'
    )

    result = is_open_in_ide_enabled()

    assert result is False


def test_is_open_in_ide_enabled_missing_open_in_ide_key_defaults_true(plan_context):
    """plan namespace present but no `open_in_ide` key → default True."""
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'phase-1-init': {'use_worktree': True}}}), encoding='utf-8'
    )

    result = is_open_in_ide_enabled()

    assert result is True


def test_is_open_in_ide_enabled_missing_plan_namespace_defaults_true(plan_context):
    """No plan namespace at all → default True."""
    (plan_context.fixture_dir / 'marshal.json').write_text(json.dumps({'skill_domains': {}}), encoding='utf-8')

    result = is_open_in_ide_enabled()

    assert result is True


def test_is_open_in_ide_enabled_no_marshal_file_defaults_true(plan_context):
    """marshal.json absent entirely → default True."""
    result = is_open_in_ide_enabled()

    assert result is True


@pytest.mark.parametrize(
    'top_level_value',
    ['[]', '"a string"', '42', 'true', 'null'],
)
def test_is_open_in_ide_enabled_non_dict_top_level_raises_value_error(plan_context, top_level_value):
    """Non-dict top-level JSON in marshal.json raises ValueError naming the file.

    Calling `data.get('plan')` on a list or scalar raises AttributeError. The
    isinstance guard turns that into a ValueError naming the file instead.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(top_level_value, encoding='utf-8')

    with pytest.raises(ValueError) as exc_info:
        is_open_in_ide_enabled()

    # The file path must appear in the message so the user can diagnose.
    assert str(marshal_path) in str(exc_info.value)
    assert 'JSON object' in str(exc_info.value)


#: ``{the id naming the case: the value stored at plan.open_in_ide}``. Every
#: entry is a non-bool the strict isinstance check must refuse.
#:
#: The ids come off THIS mapping's own keys rather than being left to pytest.
#: The values are dicts, strings, ints and a list, which pytest can name only by
#: position — so the report read ``open_in_ide_value0`` through
#: ``open_in_ide_value7`` while a per-row name was already being carried as a
#: first tuple element the body unpacked and threw away, putting it nowhere the
#: report could reach.
_NON_BOOL_OPEN_IN_IDE_VALUES = {
    'a-legacy-wrapper-dict-that-enables': {'enabled': True},
    'a-legacy-wrapper-dict-that-disables': {'enabled': False},
    'an-empty-dict': {},
    'the-string-true': 'true',
    'the-string-false': 'false',
    'the-integer-one': 1,
    'the-integer-zero': 0,
    'an-empty-list': [],
}


@pytest.mark.parametrize(
    'open_in_ide_value',
    list(_NON_BOOL_OPEN_IN_IDE_VALUES.values()),
    ids=list(_NON_BOOL_OPEN_IN_IDE_VALUES),
)
def test_is_open_in_ide_enabled_non_bool_value_raises_value_error(plan_context, open_in_ide_value):
    """Non-bool value at plan.open_in_ide raises ValueError naming the file.

    Silent coercion via `bool(...)` would misclassify the wrapped shape
    (`{"enabled": False}` -> `True` because non-empty dicts are truthy) and
    string values (`bool("false")` -> `True`). The strict isinstance check
    fails loudly instead.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'plan': {'open_in_ide': open_in_ide_value}}), encoding='utf-8')

    with pytest.raises(ValueError) as exc_info:
        is_open_in_ide_enabled()

    assert str(marshal_path) in str(exc_info.value)
    assert 'plan.open_in_ide' in str(exc_info.value)
