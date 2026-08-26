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

import re
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
    # Deliberately passing non-dict / malformed inputs to exercise the guard.
    assert mp.EffortPresets.identify(bad) == {'name': None, 'status': 'custom'}  # type: ignore[arg-type]


# =============================================================================
# (12) describe() reconstruction — a preset's description string, read ALONE,
#      rebuilds every one of the nine effort slots of the payload it describes.
#
#      The description is what an operator sees in the wizard's preset prompt;
#      it is the only thing they see. A description that leaves a slot to be
#      inferred from prose ("the analytical phases", "post-run-review") is one
#      the operator cannot resolve without already knowing the registry, and a
#      description that omits a slot deviating from its stated default
#      overstates or understates the tier being chosen.
#
#      The reconstruction below is deliberately preset-AGNOSTIC: it knows only
#      the canonical slot tokens and the rule "a slot the description does not
#      name reconstructs to the stated default". It carries no per-preset alias
#      table, so it cannot supply knowledge a description failed to supply.
# =============================================================================


# The eight role slots; the ninth is the plan-level ``default``. This tuple is
# not trusted as an assertion — ``test_expanded_slot_population_is_nine``
# derives the population from the preset payloads and pins it against this
# tuple, so a registry change that adds or drops a slot fails there first.
_ROLE_SLOTS: tuple[str, ...] = (
    'phase-2-refine',
    'phase-3-outline',
    'phase-4-plan',
    'phase-5-execute.default',
    'phase-5-execute.verification-feedback',
    'phase-6-finalize.default',
    'phase-6-finalize.verification-feedback',
    'phase-6-finalize.post-run-review',
)

_LEVEL_RE = re.compile(r'level-\d')
_STATED_DEFAULT_RE = re.compile(r'\bdefault\s+(level-\d)\b')
_STATED_SPREAD_RE = re.compile(r'\bsummed-level spread (\d+)\b')


def _expand_slots(preset: dict) -> dict[str, str]:
    """Flatten a preset payload into its dotted ``slot -> level`` map.

    A string-valued phase contributes one slot under the bare phase name; a
    dict-valued phase contributes one ``phase.subkey`` slot per sub-key. The
    plan-level ``default`` is carried under the key ``default``.
    """
    slots: dict[str, str] = {'default': str(preset['default'])}
    for group, group_value in preset['roles'].items():
        if isinstance(group_value, str):
            slots[group] = group_value
        else:
            for subkey, level in group_value.items():
                slots[f'{group}.{subkey}'] = level
    return slots


def _mentioned_slots(description: str) -> dict[str, str]:
    """Return the slots the description NAMES, mapped to the level it gives them.

    A slot is named only by its canonical token (the dotted ``phase.subkey``
    form, or the bare phase name for a phase with no sub-keys). The level
    governing a mention is the first ``level-N`` token that follows it, which
    is what makes an enumerated list ("A, B and C at level-5") resolve for
    every member. A slot named twice must be given the same level both times.

    Raises:
        AssertionError: when a named slot is followed by no level at all, or
            when two mentions of the same slot disagree — both are descriptions
            no reader could resolve, so they fail loudly rather than silently
            reconstructing to something.
    """
    level_positions = [(m.start(), m.group(0)) for m in _LEVEL_RE.finditer(description)]
    mentioned: dict[str, str] = {}
    for slot in _ROLE_SLOTS:
        governing: set[str] = set()
        start = description.find(slot)
        while start != -1:
            following = [level for pos, level in level_positions if pos > start]
            if not following:
                raise AssertionError(
                    f"slot '{slot}' is named at offset {start} but no level-N "
                    f'follows it: {description!r}'
                )
            governing.add(following[0])
            start = description.find(slot, start + 1)
        if not governing:
            continue
        if len(governing) > 1:
            raise AssertionError(
                f"slot '{slot}' is named with conflicting levels "
                f'{sorted(governing)}: {description!r}'
            )
        mentioned[slot] = governing.pop()
    return mentioned


def _stated_default(description: str) -> str:
    match = _STATED_DEFAULT_RE.search(description)
    if match is None:
        raise AssertionError(
            f'description states no plan-level default: {description!r}'
        )
    return match.group(1)


def _reconstruct_from_description(description: str) -> dict[str, str]:
    """Rebuild the full nine-slot map from the description string alone.

    Named slots take the level the description gives them; every other slot
    reconstructs to the stated plan-level default, mirroring the bubbling
    resolution an operator would apply when reading the string.
    """
    stated_default = _stated_default(description)
    mentioned = _mentioned_slots(description)
    reconstructed: dict[str, str] = {'default': stated_default}
    for slot in _ROLE_SLOTS:
        reconstructed[slot] = mentioned.get(slot, stated_default)
    return reconstructed


def _sum_ordinals(slots: dict[str, str]) -> int:
    return sum(int(level.split('-', 1)[1]) for level in slots.values())


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_expanded_slot_population_is_nine(preset_name: str) -> None:
    """The nine-slot claim is DERIVED from the payload, not asserted.

    Every preset is stored literal-expanded, so flattening it must yield
    exactly the plan default plus the eight role slots. A registry change that
    adds or removes a slot fails here, before any reconstruction test can pass
    against a stale slot list.
    """
    slots = _expand_slots(mp.EffortPresets.get(preset_name))
    assert set(slots) == {'default', *_ROLE_SLOTS}, (
        f"preset '{preset_name}' expands to slots {sorted(slots)}, which is "
        f'not the expected population {sorted({"default", *_ROLE_SLOTS})}'
    )
    assert len(slots) == 9


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_describe_reconstructs_every_slot_of_its_payload(preset_name: str) -> None:
    """describe(name) alone rebuilds the payload get(name) returns — all nine slots."""
    payload_slots = _expand_slots(mp.EffortPresets.get(preset_name))
    reconstructed = _reconstruct_from_description(mp.EffortPresets.describe(preset_name))
    differing = {
        slot: (reconstructed[slot], level)
        for slot, level in payload_slots.items()
        if reconstructed[slot] != level
    }
    assert reconstructed == payload_slots, (
        f"preset '{preset_name}' description does not reconstruct its "
        f'payload; slot -> (reconstructed, actual): {differing}'
    )


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_describe_names_every_slot_that_deviates_from_the_stated_default(
    preset_name: str,
) -> None:
    """Unnamed means default — so every deviating slot MUST be named.

    Naming a slot that happens to equal the default is fine (``balanced`` does
    exactly that for the analytical phases); leaving a deviating slot unnamed
    is the failure, because it silently reconstructs to the wrong level.
    """
    description = mp.EffortPresets.describe(preset_name)
    slots = _expand_slots(mp.EffortPresets.get(preset_name))
    stated_default = _stated_default(description)
    deviating = {
        slot for slot, level in slots.items()
        if slot != 'default' and level != stated_default
    }
    named = set(_mentioned_slots(description))
    assert deviating <= named, (
        f"preset '{preset_name}' description leaves deviating slot(s) "
        f'{sorted(deviating - named)} unnamed — they would reconstruct to the '
        f'stated default {stated_default}'
    )


@pytest.mark.parametrize('preset_name', ['economic', 'balanced', 'high-end'])
def test_describe_stated_spread_matches_the_reconstructed_spread(preset_name: str) -> None:
    """The spread the description quotes is the spread its own words add up to.

    Three numbers must agree: the literal in the description, the sum over the
    reconstruction, and the sum over the actual payload. A description that
    quotes the payload's true spread while its words add up to something else
    is the exact failure this deliverable removes.
    """
    preset = mp.EffortPresets.get(preset_name)
    description = mp.EffortPresets.describe(preset_name)
    match = _STATED_SPREAD_RE.search(description)
    assert match is not None, (
        f"preset '{preset_name}' description quotes no summed-level spread"
    )
    stated_spread = int(match.group(1))
    reconstructed_spread = _sum_ordinals(_reconstruct_from_description(description))
    assert stated_spread == reconstructed_spread == _spread(preset), (
        f"preset '{preset_name}': stated spread {stated_spread}, "
        f'reconstructed spread {reconstructed_spread}, payload spread '
        f'{_spread(preset)} — the three must agree'
    )


def test_reconstruction_detects_a_description_that_drops_a_deviating_slot() -> None:
    """Matched negative control: the reconstruction above is not vacuous.

    Removing a deviating slot's name from a truthful description must make the
    reconstruction disagree with the payload. Without this, every assertion in
    this section could pass against a parser that recognised nothing at all.
    """
    payload_slots = _expand_slots(mp.EffortPresets.get('economic'))
    truthful = mp.EffortPresets.describe('economic')
    assert 'phase-3-outline, ' in truthful
    lossy = truthful.replace('phase-3-outline, ', '', 1)

    reconstructed = _reconstruct_from_description(lossy)
    assert reconstructed != payload_slots
    # And it fails in the specific way the contract predicts: the dropped slot
    # silently reconstructs to the stated default instead of its real level.
    assert reconstructed['phase-3-outline'] == _stated_default(truthful)
    assert payload_slots['phase-3-outline'] != _stated_default(truthful)


def test_reconstruction_detects_a_description_that_misstates_a_level() -> None:
    """Matched negative control: a wrong level is caught, not just a missing name."""
    payload_slots = _expand_slots(mp.EffortPresets.get('high-end'))
    truthful = mp.EffortPresets.describe('high-end')
    assert 'at level-5' in truthful
    wrong = truthful.replace('at level-5', 'at level-3', 1)

    assert _reconstruct_from_description(wrong) != payload_slots


def test_reconstruction_rejects_a_self_contradictory_description() -> None:
    """A slot named twice with two different levels fails loudly, never resolves."""
    truthful = mp.EffortPresets.describe('economic')
    contradictory = truthful + ' Also phase-3-outline at level-2.'
    with pytest.raises(AssertionError) as excinfo:
        _reconstruct_from_description(contradictory)
    assert 'conflicting levels' in str(excinfo.value)
