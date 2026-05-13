#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the ModelPresets constant-class.

Covers behavior and cross-checks defined for deliverable 1 of the
``manage-config models write API`` plan:

1. All three presets exist as class-level attributes.
2. ``get(name)`` resolves canonical names and case/separator aliases.
3. ``get('bogus')`` raises ``ValueError`` listing the valid names.
4. Every level value in every preset is in ``ALLOWED_LEVELS``
   (cross-checked against ``_cmd_models.ALLOWED_LEVELS`` to catch
   enum drift).
5. Every role key in every preset is in ``KNOWN_ROLES`` (cross-checked
   against ``_cmd_models.KNOWN_ROLES`` so renaming a role in the
   registry without updating presets fails CI).
6. ``all_names()`` returns ``['economic', 'balanced', 'high-end']`` in
   that exact order.
7. ``describe(name)`` returns a non-empty string for each canonical
   preset.
8. Preset dicts are independent — mutating ``ModelPresets.get('economic')``
   does NOT mutate the class-level constant (deep-copy on read).
"""

from __future__ import annotations

import sys

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

PRESETS_SCRIPT = get_script_path('plan-marshall', 'plan-marshall', 'model_presets.py')
PRESETS_DIR = PRESETS_SCRIPT.parent

CMD_MODELS_SCRIPT = get_script_path('plan-marshall', 'manage-config', '_cmd_models.py')
CMD_MODELS_DIR = CMD_MODELS_SCRIPT.parent

if str(PRESETS_DIR) not in sys.path:
    sys.path.insert(0, str(PRESETS_DIR))
if str(CMD_MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(CMD_MODELS_DIR))

import _cmd_models as cmd_models  # noqa: E402
import model_presets as mp  # noqa: E402


# =============================================================================
# (1) Presets exist as class-level attributes
# =============================================================================


def test_economic_preset_is_class_attribute() -> None:
    assert isinstance(mp.ModelPresets.ECONOMIC, dict)
    assert 'default' in mp.ModelPresets.ECONOMIC
    assert 'roles' in mp.ModelPresets.ECONOMIC


def test_balanced_preset_is_class_attribute() -> None:
    assert isinstance(mp.ModelPresets.BALANCED, dict)
    assert 'default' in mp.ModelPresets.BALANCED
    assert 'roles' in mp.ModelPresets.BALANCED


def test_high_end_preset_is_class_attribute() -> None:
    assert isinstance(mp.ModelPresets.HIGH_END, dict)
    assert 'default' in mp.ModelPresets.HIGH_END
    assert 'roles' in mp.ModelPresets.HIGH_END


# =============================================================================
# (2) get() resolves canonical names and case/separator aliases
# =============================================================================


def test_get_economic_returns_economic_preset() -> None:
    result = mp.ModelPresets.get('economic')
    assert result['default'] == 'low'


def test_get_balanced_returns_balanced_preset() -> None:
    result = mp.ModelPresets.get('balanced')
    assert result['default'] == 'medium'


def test_get_high_end_with_hyphen_returns_high_end_preset() -> None:
    result = mp.ModelPresets.get('high-end')
    assert result['default'] == 'high'


def test_get_high_end_uppercase_underscore_resolves() -> None:
    result = mp.ModelPresets.get('HIGH_END')
    assert result['default'] == 'high'


def test_get_high_end_lowercase_underscore_resolves() -> None:
    result = mp.ModelPresets.get('high_end')
    assert result['default'] == 'high'


def test_get_mixed_case_resolves() -> None:
    # Sanity: arbitrary case spellings should still resolve.
    result = mp.ModelPresets.get('High-End')
    assert result['default'] == 'high'


# =============================================================================
# (3) get('bogus') raises ValueError mentioning all three valid names
# =============================================================================


def test_get_unknown_name_raises_with_valid_names_listed() -> None:
    with pytest.raises(ValueError) as excinfo:
        mp.ModelPresets.get('bogus')
    msg = str(excinfo.value)
    assert 'economic' in msg
    assert 'balanced' in msg
    assert 'high-end' in msg


# =============================================================================
# (4) Cross-check: every level value in every preset is in
#     _cmd_models.ALLOWED_LEVELS (catches enum drift)
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_preset_levels_are_subset_of_cmd_models_allowed_levels(preset_name: str) -> None:
    preset = mp.ModelPresets.get(preset_name)
    # Default level must be in the manage-config registry's ALLOWED_LEVELS.
    assert preset['default'] in cmd_models.ALLOWED_LEVELS, (
        f"preset '{preset_name}' default level '{preset['default']}' "
        f'is not in _cmd_models.ALLOWED_LEVELS {list(cmd_models.ALLOWED_LEVELS)}'
    )
    # Every leaf-level value in the (possibly nested) roles map must be in
    # ALLOWED_LEVELS. Walks flat-group string values and nested-group dicts.
    for group, group_value in preset['roles'].items():
        if isinstance(group_value, str):
            assert group_value in cmd_models.ALLOWED_LEVELS, (
                f"preset '{preset_name}' role '{group}' level "
                f"'{group_value}' is not in _cmd_models.ALLOWED_LEVELS "
                f'{list(cmd_models.ALLOWED_LEVELS)}'
            )
        else:
            for subkey, level in group_value.items():
                assert level in cmd_models.ALLOWED_LEVELS, (
                    f"preset '{preset_name}' role '{group}.{subkey}' level "
                    f"'{level}' is not in _cmd_models.ALLOWED_LEVELS "
                    f'{list(cmd_models.ALLOWED_LEVELS)}'
                )


def test_local_allowed_levels_matches_cmd_models_allowed_levels() -> None:
    # Drift guard: the duplicated ALLOWED_LEVELS tuple in model_presets.py
    # must stay in lock-step with _cmd_models.ALLOWED_LEVELS.
    assert mp.ALLOWED_LEVELS == cmd_models.ALLOWED_LEVELS


# =============================================================================
# (5) Cross-check: every role key in every preset is in
#     _cmd_models.KNOWN_ROLES (catches role-rename drift)
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_preset_role_keys_are_subset_of_cmd_models_known_roles(preset_name: str) -> None:
    """Every preset role key must be registered in _cmd_models.KNOWN_ROLES.

    Walks both top-level groups and nested subkeys: for a flat-group entry
    (string value), the top-level key must be in KNOWN_ROLES; for a nested
    entry (dict value), every subkey must be in the group's declared schema.
    """
    preset = mp.ModelPresets.get(preset_name)
    for group, group_value in preset['roles'].items():
        assert group in cmd_models.KNOWN_ROLES, (
            f"preset '{preset_name}' role group '{group}' is not in "
            f'_cmd_models.KNOWN_ROLES — registry rename or preset typo'
        )
        schema = cmd_models.KNOWN_ROLES[group]
        if isinstance(group_value, dict):
            for subkey in group_value:
                assert subkey in schema, (
                    f"preset '{preset_name}' subkey '{group}.{subkey}' is "
                    f"not registered (valid: {list(schema)})"
                )


# =============================================================================
# (6) all_names() returns canonical names in display order
# =============================================================================


def test_all_names_returns_canonical_order() -> None:
    assert mp.ModelPresets.all_names() == ['economic', 'balanced', 'high-end']


# =============================================================================
# (7) describe(name) returns a non-empty string for each preset
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_describe_returns_non_empty_string(preset_name: str) -> None:
    description = mp.ModelPresets.describe(preset_name)
    assert isinstance(description, str)
    assert description.strip() != ''


def test_describe_accepts_aliases() -> None:
    # Same alias rules as get(): case-insensitive, underscore -> hyphen.
    via_canonical = mp.ModelPresets.describe('high-end')
    via_underscore = mp.ModelPresets.describe('high_end')
    via_uppercase = mp.ModelPresets.describe('HIGH_END')
    assert via_canonical == via_underscore == via_uppercase


def test_describe_unknown_name_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        mp.ModelPresets.describe('bogus')
    msg = str(excinfo.value)
    assert 'economic' in msg
    assert 'balanced' in msg
    assert 'high-end' in msg


# =============================================================================
# (8) Preset dicts are independent — get() returns a deep copy
# =============================================================================


def test_get_returns_deep_copy_top_level_mutation_does_not_leak() -> None:
    original_default = mp.ModelPresets.ECONOMIC['default']
    snapshot = mp.ModelPresets.get('economic')
    snapshot['default'] = 'CORRUPTED'
    # Class-level constant must be untouched.
    assert mp.ModelPresets.ECONOMIC['default'] == original_default
    # And a fresh get() must still return the pristine value.
    assert mp.ModelPresets.get('economic')['default'] == original_default


def test_get_returns_deep_copy_nested_roles_mutation_does_not_leak() -> None:
    import copy as _copy
    original_roles = _copy.deepcopy(mp.ModelPresets.BALANCED['roles'])
    snapshot = mp.ModelPresets.get('balanced')
    # Mutate the top-level group dict, a nested-group subkey, and a new
    # injected entry — none of these may leak back to the class constant.
    snapshot['roles']['phase-3']['research'] = 'CORRUPTED'
    snapshot['roles']['phase-3']['default'] = 'CORRUPTED'
    snapshot['roles']['INJECTED'] = 'CORRUPTED'
    # Class-level constant's roles dict must not be mutated by any edit.
    assert mp.ModelPresets.BALANCED['roles'] == original_roles
    # A fresh get() must still return the pristine roles dict.
    assert mp.ModelPresets.get('balanced')['roles'] == original_roles
