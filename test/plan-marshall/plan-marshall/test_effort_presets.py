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
    # After the ladder re-spread, economic adopts the former balanced values
    # (default level-3; phase-3-outline / phase-5-execute.default /
    # phase-6-finalize.post-run-review at level-4).
    assert result['default'] == 'level-3'
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


def test_get_balanced_returns_balanced_preset() -> None:
    result = mp.EffortPresets.get('balanced')
    # After the re-spread, balanced is the even midpoint (summed-level spread
    # 36): default level-4, analytical phases at level-4, the highest-value
    # reasoning slots (phase-3-outline, phase-5-execute.default,
    # phase-6-finalize.post-run-review) at level-5, triage at level-3.
    assert result['default'] == 'level-4'
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
    assert result['roles']['phase-2-refine'] == 'level-4'
    assert result['roles']['phase-3-outline'] == 'level-5'
    assert result['roles']['phase-4-plan'] == 'level-4'
    assert result['roles']['phase-5-execute'] == {
        'default': 'level-5',
        'verification-feedback': 'level-3',
    }
    assert result['roles']['phase-6-finalize'] == {
        'default': 'level-3',
        'verification-feedback': 'level-3',
        'post-run-review': 'level-5',
    }


def test_get_high_end_with_hyphen_returns_high_end_preset() -> None:
    result = mp.EffortPresets.get('high-end')
    assert result['default'] == 'level-4'
    # HIGH_END pushes phase-5-execute.default up to level-5 (opus, high) —
    # the per-task implementation tier for the genuinely-high-end preset.
    assert result['roles']['phase-5-execute']['default'] == 'level-5'


def test_get_high_end_uppercase_underscore_resolves() -> None:
    result = mp.EffortPresets.get('HIGH_END')
    assert result['default'] == 'level-4'


def test_get_high_end_lowercase_underscore_resolves() -> None:
    result = mp.EffortPresets.get('high_end')
    assert result['default'] == 'level-4'


def test_get_mixed_case_resolves() -> None:
    # Sanity: arbitrary case spellings should still resolve.
    result = mp.EffortPresets.get('High-End')
    assert result['default'] == 'level-4'


def test_high_end_reaches_level_5_but_never_level_6_or_7() -> None:
    # Structural guard for the re-spread's lifted reservation: level-5 (opus,
    # high) is now a DELIBERATE preset default in HIGH_END — the top rung is
    # meant to be genuinely high-end, so this test asserts at least one slot
    # actually reaches level-5. It also pins the RETAINED reservation:
    # level-6 (opus, xhigh) and level-7 (fable, max) are alias-capability-gated
    # and must never be baked into a preset default (they silently fall back
    # to the canonical variant when the alias lacks the capability). Any future
    # edit that removes level-5 from HIGH_END, or introduces level-6/level-7
    # into any preset, must fail this test.
    preset = mp.EffortPresets.get('high-end')

    def _leaf_levels(p: dict) -> list[str]:
        levels: list[str] = [p['default']]
        for group_value in p['roles'].values():
            if isinstance(group_value, str):
                levels.append(group_value)
            else:
                levels.extend(group_value.values())
        return levels

    high_end_levels = _leaf_levels(preset)
    assert 'level-5' in high_end_levels, (
        'HIGH_END must reach level-5 (opus, high) so the top rung is '
        'genuinely high-end after the reservation was lifted'
    )
    # Retained reservation: no preset (economic/balanced/high-end) may bake in
    # the alias-gated level-6/level-7 tiers.
    for preset_name in ('economic', 'balanced', 'high-end'):
        for level in _leaf_levels(mp.EffortPresets.get(preset_name)):
            assert level not in ('level-6', 'level-7'), (
                f"preset '{preset_name}' carries alias-gated level '{level}'; "
                'level-6/level-7 stay reserved for explicit per-phase opt-in'
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


# =============================================================================
# (10) Spread ladder — the three presets are EVENLY distinct along the summed
#      level-number metric. This is the anti-drift guard: it encodes the target
#      distribution (economic 30 / balanced 36 / high-end 41) so the ladder
#      cannot silently drift back to front-loaded (the original 23 / 30 / 34,
#      where economic->balanced was +7 but balanced->high-end only +4, and
#      high-end matched balanced in five of nine slots).
# =============================================================================


# The summed-level-number spread targets for the re-spread ladder. Each total
# is the sum of the ordinal N in ``level-N`` across the nine effort slots
# (default + phase-2/3/4 + phase-5{default,verification-feedback} +
# phase-6{default,verification-feedback,post-run-review}).
_SPREAD_TARGET = {'economic': 30, 'balanced': 36, 'high-end': 41}

# Minimum adjacent gap on the summed-level metric. The original ladder's
# balanced->high-end gap was +4; the re-spread requires every adjacent step to
# be at least +5, so the top rung is genuinely distinct from the middle.
_MIN_ADJACENT_GAP = 5


def _spread(preset: dict) -> int:
    """Sum the ordinal level number across a preset's nine effort slots.

    Walks the top-level ``default`` plus every leaf under ``roles`` (a
    string-valued phase contributes one leaf; a dict-valued phase contributes
    one leaf per sub-key). ``level-N`` contributes ``N``; a non-``level-N``
    value (only ``inherit`` is possible, and no preset uses it) would raise,
    which is the intended fail-loud behaviour for a malformed preset.
    """
    def _ordinal(level: str) -> int:
        return int(level.split('-', 1)[1])

    total = _ordinal(preset['default'])
    for group_value in preset['roles'].values():
        if isinstance(group_value, str):
            total += _ordinal(group_value)
        else:
            for sub_value in group_value.values():
                total += _ordinal(sub_value)
    return total


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_preset_spread_matches_target(preset_name: str) -> None:
    """Each preset's summed-level spread equals its re-spread target."""
    preset = mp.EffortPresets.get(preset_name)
    assert _spread(preset) == _SPREAD_TARGET[preset_name], (
        f"preset '{preset_name}' spread {_spread(preset)} != target "
        f'{_SPREAD_TARGET[preset_name]} — the ladder has drifted'
    )


def test_preset_spread_ladder_is_evenly_distributed() -> None:
    """The ladder rises by at least the minimum gap at every adjacent step.

    Guards against the front-loaded regression the re-spread fixes: the
    original ladder rose +7 then only +4. Every adjacent step must now clear
    ``_MIN_ADJACENT_GAP`` so no rung collapses onto its neighbour.
    """
    economic = _spread(mp.EffortPresets.get('economic'))
    balanced = _spread(mp.EffortPresets.get('balanced'))
    high_end = _spread(mp.EffortPresets.get('high-end'))

    assert balanced - economic >= _MIN_ADJACENT_GAP, (
        f'economic->balanced gap {balanced - economic} < {_MIN_ADJACENT_GAP}'
    )
    assert high_end - balanced >= _MIN_ADJACENT_GAP, (
        f'balanced->high-end gap {high_end - balanced} < {_MIN_ADJACENT_GAP}'
    )


# =============================================================================
# (11) identify() — deterministic, legacy-aware preset recognition (D2). A value
#      re-spread changes the payloads, so a project holding a PRE-RESPREAD shape
#      would stop matching every current preset and be silently reclassified as
#      custom. identify() recognises those legacy shapes and reports them as
#      ``previous-ladder`` so the wizard can offer a re-apply.
# =============================================================================


# The pre-respread payload shapes (defined here independently of the module's
# private _LEGACY_PRESETS so a drift in that registry is caught).
_PRE_RESPREAD_ECONOMIC = {
    'default': 'level-2',
    'roles': {
        'phase-2-refine': 'level-3',
        'phase-3-outline': 'level-3',
        'phase-4-plan': 'level-3',
        'phase-5-execute': {'default': 'level-2', 'verification-feedback': 'level-3'},
        'phase-6-finalize': {
            'default': 'level-2',
            'verification-feedback': 'level-3',
            'post-run-review': 'level-2',
        },
    },
}
_PRE_RESPREAD_BALANCED = {
    'default': 'level-3',
    'roles': {
        'phase-2-refine': 'level-3',
        'phase-3-outline': 'level-4',
        'phase-4-plan': 'level-3',
        'phase-5-execute': {'default': 'level-4', 'verification-feedback': 'level-3'},
        'phase-6-finalize': {
            'default': 'level-3',
            'verification-feedback': 'level-3',
            'post-run-review': 'level-4',
        },
    },
}
_PRE_RESPREAD_HIGH_END = {
    'default': 'level-3',
    'roles': {
        'phase-2-refine': 'level-4',
        'phase-3-outline': 'level-4',
        'phase-4-plan': 'level-4',
        'phase-5-execute': {'default': 'level-4', 'verification-feedback': 'level-4'},
        'phase-6-finalize': {
            'default': 'level-3',
            'verification-feedback': 'level-4',
            'post-run-review': 'level-4',
        },
    },
}


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_identify_recognises_each_current_preset(preset_name: str) -> None:
    """A payload equal to a current preset classifies as that preset, ``current``."""
    payload = mp.EffortPresets.get(preset_name)
    assert mp.EffortPresets.identify(payload) == {'name': preset_name, 'status': 'current'}


def test_identify_recognises_pre_respread_economic_as_previous_ladder() -> None:
    """The pre-respread economic shape (spread 23) is recognised, not custom."""
    assert mp.EffortPresets.identify(_PRE_RESPREAD_ECONOMIC) == {
        'name': 'economic',
        'status': 'previous-ladder',
    }


def test_identify_recognises_pre_respread_high_end_as_previous_ladder() -> None:
    """The pre-respread high-end shape (spread 34) is recognised, not custom."""
    assert mp.EffortPresets.identify(_PRE_RESPREAD_HIGH_END) == {
        'name': 'high-end',
        'status': 'previous-ladder',
    }


def test_identify_pre_respread_balanced_resolves_to_current_economic() -> None:
    """Current match wins: the old balanced shape is byte-identical to the new
    economic, so it classifies as ``economic``/``current`` — never a stale
    ``balanced``/``previous-ladder``."""
    assert _PRE_RESPREAD_BALANCED == mp.EffortPresets.get('economic')
    assert mp.EffortPresets.identify(_PRE_RESPREAD_BALANCED) == {
        'name': 'economic',
        'status': 'current',
    }


def test_identify_unknown_shape_is_custom() -> None:
    custom = {
        'default': 'level-1',
        'roles': {'phase-2-refine': 'level-7'},
    }
    assert mp.EffortPresets.identify(custom) == {'name': None, 'status': 'custom'}


@pytest.mark.parametrize('bad', [None, {}, {'default': 'level-3'}, {'roles': {}}, 'not-a-dict', 42])
def test_identify_malformed_payload_is_custom(bad: object) -> None:
    """A payload missing ``default``/``roles`` (or not a dict) is ``custom``, never a crash."""
    assert mp.EffortPresets.identify(bad) == {'name': None, 'status': 'custom'}
