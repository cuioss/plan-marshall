#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the EffortPresets constant-class.

Covers behavior and cross-checks defined for deliverable 1 of the
``manage-config effort write API`` plan:

1. All three presets exist as class-level attributes.
2. ``get(name)`` resolves canonical names and case/separator aliases.
3. ``get('bogus')`` raises ``ValueError`` listing the valid names.
4. Every level value in every preset is in ``ALLOWED_LEVELS``
   (cross-checked against ``_cmd_effort.ALLOWED_LEVELS`` to catch
   enum drift).
5. Every role key in every preset is in ``KNOWN_ROLES`` (cross-checked
   against ``_cmd_effort.KNOWN_ROLES`` so renaming a role in the
   registry without updating presets fails CI).
6. ``all_names()`` returns ``['economic', 'balanced', 'high-end']`` in
   that exact order.
7. ``describe(name)`` returns a non-empty string for each canonical
   preset.
8. Preset dicts are independent — mutating ``EffortPresets.get('economic')``
   does NOT mutate the class-level constant (deep-copy on read).
"""

from __future__ import annotations

import sys

import pytest
from conftest import get_script_path

PRESETS_SCRIPT = get_script_path('plan-marshall', 'plan-marshall', 'effort_presets.py')
PRESETS_DIR = PRESETS_SCRIPT.parent

CMD_MODELS_SCRIPT = get_script_path('plan-marshall', 'manage-config', '_cmd_effort.py')
CMD_MODELS_DIR = CMD_MODELS_SCRIPT.parent

if str(PRESETS_DIR) not in sys.path:
    sys.path.insert(0, str(PRESETS_DIR))
if str(CMD_MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(CMD_MODELS_DIR))

import _cmd_effort as cmd_effort  # noqa: E402
import effort_presets as mp  # noqa: E402


# =============================================================================
# (1) Presets exist as class-level attributes
# =============================================================================


def test_economic_preset_is_class_attribute() -> None:
    assert isinstance(mp.EffortPresets.ECONOMIC, dict)
    assert 'default' in mp.EffortPresets.ECONOMIC
    assert 'roles' in mp.EffortPresets.ECONOMIC


def test_balanced_preset_is_class_attribute() -> None:
    assert isinstance(mp.EffortPresets.BALANCED, dict)
    assert 'default' in mp.EffortPresets.BALANCED
    assert 'roles' in mp.EffortPresets.BALANCED


def test_high_end_preset_is_class_attribute() -> None:
    assert isinstance(mp.EffortPresets.HIGH_END, dict)
    assert 'default' in mp.EffortPresets.HIGH_END
    assert 'roles' in mp.EffortPresets.HIGH_END


# =============================================================================
# (2) get() resolves canonical names and case/separator aliases
# =============================================================================


def test_get_economic_returns_economic_preset() -> None:
    result = mp.EffortPresets.get('economic')
    assert result['default'] == 'level-2'


def test_get_balanced_returns_balanced_preset() -> None:
    result = mp.EffortPresets.get('balanced')
    assert result['default'] == 'level-3'
    # BALANCED is stored in literal-expanded form: every KNOWN_ROLES phase
    # carries an explicit entry that mirrors the on-disk shape produced by
    # apply-preset balanced after _expand_phase_effort. The wizard's
    # deep-equality match in effort-menu.md Step 1 only recognises
    # ``Current: balanced preset`` when the on-disk config equals the
    # constant verbatim, so the redundancy against bubbling-resolution
    # semantics is intentional.
    assert set(result['roles'].keys()) == {
        'phase-2-refine',
        'phase-3-outline',
        'phase-4-plan',
        'phase-5-execute',
        'phase-6-finalize',
    }
    assert result['roles']['phase-2-refine'] == 'level-3'
    assert result['roles']['phase-3-outline'] == 'level-4'
    assert result['roles']['phase-4-plan'] == 'level-3'
    assert result['roles']['phase-5-execute'] == {
        'default': 'level-4',
        'verification-feedback': 'level-3',
    }
    assert result['roles']['phase-6-finalize'] == {
        'default': 'level-3',
        'verification-feedback': 'level-3',
        'post-run-review': 'level-4',
    }


def test_get_high_end_with_hyphen_returns_high_end_preset() -> None:
    result = mp.EffortPresets.get('high-end')
    assert result['default'] == 'level-3'
    # HIGH_END pushes phase-5-execute.default up to level-4 — the per-task
    # implementation tier for the upper-tier preset.
    assert result['roles']['phase-5-execute']['default'] == 'level-4'


def test_get_high_end_uppercase_underscore_resolves() -> None:
    result = mp.EffortPresets.get('HIGH_END')
    assert result['default'] == 'level-3'


def test_get_high_end_lowercase_underscore_resolves() -> None:
    result = mp.EffortPresets.get('high_end')
    assert result['default'] == 'level-3'


def test_get_mixed_case_resolves() -> None:
    # Sanity: arbitrary case spellings should still resolve.
    result = mp.EffortPresets.get('High-End')
    assert result['default'] == 'level-3'


def test_high_end_contains_no_level_5_anywhere() -> None:
    # Structural guard: HIGH_END is the upper tier, NOT a maximum-cost
    # tier. ``level-5`` ((opus, high)) is reserved for explicit per-phase
    # opt-in as a cost/intensity policy choice, never a preset default.
    # Any future edit that re-introduces ``level-5`` into HIGH_END must
    # fail this test.
    preset = mp.EffortPresets.get('high-end')
    assert preset['default'] != 'level-5'
    for group, group_value in preset['roles'].items():
        if isinstance(group_value, str):
            assert group_value != 'level-5', (
                f"HIGH_END role '{group}' carries forbidden level 'level-5'"
            )
        else:
            for subkey, level in group_value.items():
                assert level != 'level-5', (
                    f"HIGH_END role '{group}.{subkey}' carries forbidden "
                    "level 'level-5'"
                )


# =============================================================================
# (3) get('bogus') raises ValueError mentioning all three valid names
# =============================================================================


def test_get_unknown_name_raises_with_valid_names_listed() -> None:
    with pytest.raises(ValueError) as excinfo:
        mp.EffortPresets.get('bogus')
    msg = str(excinfo.value)
    assert 'economic' in msg
    assert 'balanced' in msg
    assert 'high-end' in msg


# =============================================================================
# (4) Cross-check: every level value in every preset is in
#     _cmd_effort.ALLOWED_LEVELS (catches enum drift)
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_preset_levels_are_subset_of_cmd_models_allowed_levels(preset_name: str) -> None:
    preset = mp.EffortPresets.get(preset_name)
    # Default level must be in the manage-config registry's ALLOWED_LEVELS.
    assert preset['default'] in cmd_effort.ALLOWED_LEVELS, (
        f"preset '{preset_name}' default level '{preset['default']}' "
        f'is not in _cmd_effort.ALLOWED_LEVELS {list(cmd_effort.ALLOWED_LEVELS)}'
    )
    # Every leaf-level value in the (possibly nested) roles map must be in
    # ALLOWED_LEVELS. Walks flat-group string values and nested-group dicts.
    for group, group_value in preset['roles'].items():
        if isinstance(group_value, str):
            assert group_value in cmd_effort.ALLOWED_LEVELS, (
                f"preset '{preset_name}' role '{group}' level "
                f"'{group_value}' is not in _cmd_effort.ALLOWED_LEVELS "
                f'{list(cmd_effort.ALLOWED_LEVELS)}'
            )
        else:
            for subkey, level in group_value.items():
                assert level in cmd_effort.ALLOWED_LEVELS, (
                    f"preset '{preset_name}' role '{group}.{subkey}' level "
                    f"'{level}' is not in _cmd_effort.ALLOWED_LEVELS "
                    f'{list(cmd_effort.ALLOWED_LEVELS)}'
                )


def test_local_allowed_levels_matches_cmd_models_allowed_levels() -> None:
    # Drift guard: the duplicated ALLOWED_LEVELS tuple in effort_presets.py
    # must stay in lock-step with _cmd_effort.ALLOWED_LEVELS.
    assert mp.ALLOWED_LEVELS == cmd_effort.ALLOWED_LEVELS


def test_allowed_levels_is_numeric_palette() -> None:
    # Pin the breaking rename: ALLOWED_LEVELS is the numeric level-N palette
    # plus the special non-numeric `inherit` sentinel. No old token remains.
    assert mp.ALLOWED_LEVELS == (
        'level-1', 'level-2', 'level-3', 'level-4',
        'level-5', 'level-6', 'level-7', 'inherit',
    )


# =============================================================================
# (5) Cross-check: every role key in every preset is in
#     _cmd_effort.KNOWN_ROLES (catches role-rename drift)
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_preset_role_keys_are_subset_of_cmd_models_known_roles(preset_name: str) -> None:
    """Every preset role key must be registered in _cmd_effort.KNOWN_ROLES.

    Walks both top-level groups and nested subkeys: for a flat-group entry
    (string value), the top-level key must be in KNOWN_ROLES; for a nested
    entry (dict value), every subkey must be in the group's declared schema.
    """
    preset = mp.EffortPresets.get(preset_name)
    for group, group_value in preset['roles'].items():
        assert group in cmd_effort.KNOWN_ROLES, (
            f"preset '{preset_name}' role group '{group}' is not in "
            f'_cmd_effort.KNOWN_ROLES — registry rename or preset typo'
        )
        schema = cmd_effort.KNOWN_ROLES[group]
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
    assert mp.EffortPresets.all_names() == ['economic', 'balanced', 'high-end']


# =============================================================================
# (7) describe(name) returns a non-empty string for each preset
# =============================================================================


@pytest.mark.parametrize(
    'preset_name',
    ['economic', 'balanced', 'high-end'],
)
def test_describe_returns_non_empty_string(preset_name: str) -> None:
    description = mp.EffortPresets.describe(preset_name)
    assert isinstance(description, str)
    assert description.strip() != ''


def test_describe_accepts_aliases() -> None:
    # Same alias rules as get(): case-insensitive, underscore -> hyphen.
    via_canonical = mp.EffortPresets.describe('high-end')
    via_underscore = mp.EffortPresets.describe('high_end')
    via_uppercase = mp.EffortPresets.describe('HIGH_END')
    assert via_canonical == via_underscore == via_uppercase


def test_describe_unknown_name_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        mp.EffortPresets.describe('bogus')
    msg = str(excinfo.value)
    assert 'economic' in msg
    assert 'balanced' in msg
    assert 'high-end' in msg


# =============================================================================
# (8) Preset dicts are independent — get() returns a deep copy
# =============================================================================


def test_get_returns_deep_copy_top_level_mutation_does_not_leak() -> None:
    original_default = mp.EffortPresets.ECONOMIC['default']
    snapshot = mp.EffortPresets.get('economic')
    snapshot['default'] = 'CORRUPTED'
    # Class-level constant must be untouched.
    assert mp.EffortPresets.ECONOMIC['default'] == original_default
    # And a fresh get() must still return the pristine value.
    assert mp.EffortPresets.get('economic')['default'] == original_default


def test_get_returns_deep_copy_nested_roles_mutation_does_not_leak() -> None:
    import copy as _copy
    original_roles = _copy.deepcopy(mp.EffortPresets.BALANCED['roles'])
    snapshot = mp.EffortPresets.get('balanced')
    # Mutate a dict-valued phase entry, overwrite a string-valued one,
    # and inject a fresh key — none of these may leak back to the class
    # constant.
    snapshot['roles']['phase-5-execute']['verification-feedback'] = 'CORRUPTED'
    snapshot['roles']['phase-2-refine'] = 'CORRUPTED'
    snapshot['roles']['INJECTED'] = 'CORRUPTED'
    # Class-level constant's roles dict must not be mutated by any edit.
    assert mp.EffortPresets.BALANCED['roles'] == original_roles
    # A fresh get() must still return the pristine roles dict.
    assert mp.EffortPresets.get('balanced')['roles'] == original_roles


# =============================================================================
# (9) Ladder monotonicity — index(ECONOMIC[slot]) <= index(BALANCED[slot])
#     <= index(HIGH_END[slot]) on the ordinal scale across the union of
#     phase/role slots, with unset slots bubbled through the preset's
#     own default per effort-roles.md's polymorphic-value rule.
# =============================================================================


def test_preset_ladder_is_monotonic() -> None:
    """Structural guard: ECONOMIC <= BALANCED <= HIGH_END at every slot.

    Walks the union of phase/role slots across the three presets and
    asserts the ladder monotonicity on the ordinal scale ``(level-1,
    level-2, level-3, level-4, level-5, level-6, level-7)``. Empty preset
    cells bubble through the preset's own ``default`` per the resolver's
    polymorphic-value rule. Any future preset edit that softens the ladder
    at any slot must fail this test.
    """
    ordinal: tuple[str, ...] = (
        'level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7'
    )
    rank = {level: idx for idx, level in enumerate(ordinal)}

    presets = {
        'economic': mp.EffortPresets.get('economic'),
        'balanced': mp.EffortPresets.get('balanced'),
        'high-end': mp.EffortPresets.get('high-end'),
    }

    # Collect the union of (group, subkey) slots seen across all three
    # presets. ``subkey`` is None for flat (string-valued) phase entries.
    slots: set[tuple[str, str | None]] = set()
    for preset in presets.values():
        for group, group_value in preset['roles'].items():
            if isinstance(group_value, dict):
                for subkey in group_value:
                    slots.add((group, subkey))
            else:
                slots.add((group, None))

    def resolve(preset: dict, group: str, subkey: str | None) -> str:
        """Resolve the effective level at (group, subkey) for ``preset``.

        Bubbles through the group's value (string shorthand applies to
        every sub-key under the phase) and falls back to the preset's
        own ``default`` for any slot the preset omits — mirroring the
        bubbling-resolution semantics documented in effort-roles.md.
        """
        group_value = preset['roles'].get(group)
        if group_value is None:
            return str(preset['default'])
        if isinstance(group_value, str):
            return group_value
        # dict-valued group: subkey override wins; missing subkey bubbles
        # to the group's ``default`` entry, then to the preset default.
        if subkey is not None and subkey in group_value:
            return str(group_value[subkey])
        if 'default' in group_value:
            return str(group_value['default'])
        return str(preset['default'])

    # Also include the ``default`` slot itself in the walk.
    slots.add(('__plan_default__', None))

    for group, subkey in sorted(slots, key=lambda s: (s[0], s[1] or '')):
        if group == '__plan_default__':
            eco = presets['economic']['default']
            bal = presets['balanced']['default']
            high = presets['high-end']['default']
            slot_label = 'default'
        else:
            eco = resolve(presets['economic'], group, subkey)
            bal = resolve(presets['balanced'], group, subkey)
            high = resolve(presets['high-end'], group, subkey)
            slot_label = group if subkey is None else f'{group}.{subkey}'

        assert rank[eco] <= rank[bal], (
            f"Ladder violation at slot '{slot_label}': ECONOMIC={eco} "
            f'(rank {rank[eco]}) > BALANCED={bal} (rank {rank[bal]})'
        )
        assert rank[bal] <= rank[high], (
            f"Ladder violation at slot '{slot_label}': BALANCED={bal} "
            f'(rank {rank[bal]}) > HIGH_END={high} (rank {rank[high]})'
        )
