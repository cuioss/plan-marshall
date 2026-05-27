#!/usr/bin/env python3
"""Tests for `manage-config effort apply-preset --preset <name>` write subcommand.

Covers the user-mandated "completely overwrites" semantic, the
case-insensitive / underscore alias resolution that ``EffortPresets.get``
exposes, and round-trip stability when chaining multiple presets. The
argparse-rejection case for unknown presets is exercised through the
CLI plumbing (subprocess) since argparse validation runs before the
handler.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH, create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)
_PLAN_MARSHALL_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)

# `_cmd_effort` imports `effort_presets` at module level. Make sure the
# plan-marshall scripts directory is importable BEFORE we load _cmd_effort.
if str(_PLAN_MARSHALL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAN_MARSHALL_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_effort_presets_mod = _load_module(
    'effort_presets', 'effort_presets.py', _PLAN_MARSHALL_SCRIPTS_DIR
)
EffortPresets = _effort_presets_mod.EffortPresets

_cmd_effort_mod = _load_module(
    '_cmd_effort', '_cmd_effort.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
cmd_effort = _cmd_effort_mod.cmd_effort
cmd_effort_apply_preset = _cmd_effort_mod.cmd_effort_apply_preset
KNOWN_ROLES = _cmd_effort_mod.KNOWN_ROLES


def _expanded_preset(preset: dict) -> dict:
    """Return the ``{"default": …, "roles": {…}}`` preset-payload view
    of the on-disk shape that ``apply-preset`` writes.

    Per the writer in :func:`_cmd_effort._expand_phase_effort`:
      - A string-valued phase in the preset is preserved verbatim
        (single-level shorthand stays a string on disk).
      - A dict-valued phase is expanded so every sub-key in the phase's
        schema is explicit (preset overrides win; missing sub-keys
        receive the global default).
      - A phase the preset omits entirely is shorthand-written as the
        global default string.

    The test helper translates that on-disk shape back to the
    preset-payload view (matching the ``EffortPresets`` constants) so
    assertions can compare the preset's intent without re-implementing
    the inverse transform inline.
    """
    default_level = preset['default']
    preset_roles = preset.get('roles', {})
    roles_view: dict = {}
    for group, schema in KNOWN_ROLES.items():
        preset_group = preset_roles.get(group)
        if isinstance(preset_group, dict):
            sub_dict: dict = {}
            for subkey in schema:
                sub_value = preset_group.get(subkey, default_level)
                sub_dict[subkey] = (
                    sub_value if isinstance(sub_value, str) else default_level
                )
            roles_view[group] = sub_dict
        elif isinstance(preset_group, str):
            roles_view[group] = preset_group
        else:
            roles_view[group] = default_level
    return {'default': default_level, 'roles': roles_view}

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402


def _write_marshal_with_models(fixture_dir: Path, models_block: dict | None) -> None:
    """Write marshal.json with optional effort config.

    Accepts the preset-payload-shape ``{"default": <level>, "roles":
    {<phase>: ...}}`` view in test bodies and translates to the on-disk
    storage shape (``plan.effort`` for the plan-wide fallback,
    ``plan.<phase>.effort`` for per-phase overrides).
    """
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('effort', None)
    config.pop('models', None)
    plan_block = config.get('plan', {})
    if isinstance(plan_block, dict):
        plan_block.pop('effort', None)
        for phase_entry in plan_block.values():
            if isinstance(phase_entry, dict):
                phase_entry.pop('effort', None)
    if models_block is not None:
        plan_block = config.setdefault('plan', {})
        default = models_block.get('default')
        if default is not None:
            plan_block['effort'] = default
        for phase, value in models_block.get('roles', {}).items():
            phase_entry = plan_block.setdefault(phase, {})
            if isinstance(phase_entry, dict):
                phase_entry['effort'] = value
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _read_marshal_models(fixture_dir: Path) -> dict:
    """Reconstruct the ``{default, roles}`` preset-payload view of
    effort config.

    Reads the per-phase storage shape on disk and emits the
    preset-payload view so assertions can compare against
    ``EffortPresets`` constants directly.
    """
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    plan_block = config.get('plan', {})
    result: dict = {}
    if isinstance(plan_block, dict) and 'effort' in plan_block:
        result['default'] = plan_block['effort']
    roles: dict = {}
    if isinstance(plan_block, dict):
        for phase, entry in plan_block.items():
            if phase == 'effort':
                continue
            if isinstance(entry, dict) and 'effort' in entry:
                roles[phase] = entry['effort']
    result['roles'] = roles
    return result


# =============================================================================
# (1) apply-preset --preset economic writes the ECONOMIC payload and
#     models read --role default returns level: low
# =============================================================================


def _expected_roles_count(preset: dict) -> int:
    """Total leaf-level entries the writer reports for ``roles_count``.

    Mirrors :func:`_cmd_effort._count_roles`: a string-valued phase
    contributes 1; a dict-valued phase contributes ``len(dict)`` after
    the schema-expansion fills missing sub-keys.
    """
    expanded = _expanded_preset(preset)['roles']
    count = 0
    for value in expanded.values():
        if isinstance(value, str):
            count += 1
        elif isinstance(value, dict):
            count += len(value)
    return count


def _expected_overrides_count(preset: dict) -> int:
    """Number of leaf entries differing from the preset's default level.

    Mirrors :func:`_cmd_effort._count_overrides`.
    """
    default_level = preset['default']
    expanded = _expanded_preset(preset)['roles']
    count = 0
    for value in expanded.values():
        if isinstance(value, str):
            if value != default_level:
                count += 1
        elif isinstance(value, dict):
            for sub_value in value.values():
                if isinstance(sub_value, str) and sub_value != default_level:
                    count += 1
    return count


def test_apply_preset_economic_writes_expanded_payload(plan_context):
    # Initialise marshal.json with no models block.
    _write_marshal_with_models(plan_context.fixture_dir, None)

    result = cmd_effort_apply_preset(Namespace(preset='economic'))

    assert result['status'] == 'success'
    assert result['preset'] == 'economic'
    assert result['default'] == 'medium'
    # roles_count reflects the leaf-level EXPANDED set (flat groups
    # contribute 1, nested groups contribute len(subkeys)). Overrides
    # count is the per-leaf override count from the preset payload.
    assert result['roles_count'] == _expected_roles_count(EffortPresets.ECONOMIC)
    assert result['overrides_count'] == _expected_overrides_count(
        EffortPresets.ECONOMIC
    )

    # Disk state matches the EXPANDED ECONOMIC payload.
    on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert on_disk == _expanded_preset(EffortPresets.ECONOMIC)

    # Self-documenting on-disk shape: every group is present (either as
    # a string shorthand or as a dict; the writer picks the compact
    # shape that fits the preset).
    for group, schema in KNOWN_ROLES.items():
        assert group in on_disk['roles'], (
            f"group '{group}' missing from expanded on-disk roles map"
        )
        value = on_disk['roles'][group]
        if isinstance(value, dict):
            for subkey in schema:
                assert subkey in value, (
                    f"subkey '{group}.{subkey}' missing from on-disk map"
                )

    # ECONOMIC carries `phase-6-finalize` as a dict-valued override
    # ({'verification-feedback': 'high'}); the writer expands the
    # dict so every sub-key is explicit on disk (overrides win,
    # missing sub-keys receive the ECONOMIC default of 'medium').
    # The resolver returns the sub-key-specific source path because
    # the on-disk phase-6-finalize entry is a dict.
    read_result = cmd_effort(
        Namespace(role='phase-6-finalize.verification-feedback', phase=None, default=False)
    )
    assert read_result['status'] == 'success'
    assert read_result['level'] == 'high'
    assert read_result['source'] == 'plan.phase-6-finalize.effort.verification-feedback'


# =============================================================================
# (2) apply-preset balanced + models read --role phase-6-finalize.verification-feedback
#     returns level: high, source: plan.phase-6-finalize.effort.verification-feedback
# =============================================================================


def test_apply_preset_balanced_then_read_phase_6_verification_feedback_returns_high(plan_context):
    _write_marshal_with_models(plan_context.fixture_dir, None)

    cmd_effort_apply_preset(Namespace(preset='balanced'))

    read_result = cmd_effort(
        Namespace(role='phase-6-finalize.verification-feedback', phase=None, default=False)
    )
    assert read_result['status'] == 'success'
    assert read_result['level'] == 'high'
    assert read_result['source'] == 'plan.phase-6-finalize.effort.verification-feedback'


# =============================================================================
# (3) apply-preset overwrites — pre-seeded block is fully replaced
# =============================================================================


def test_apply_preset_high_end_overwrites_pre_seeded_block(plan_context):
    # Pre-seed every KNOWN_ROLES phase with a non-HIGH_END value.
    # apply-preset must overwrite each of those with HIGH_END's
    # per-phase value — the seeded "before" state shouldn't survive
    # under any KNOWN_ROLES key.
    seeded = {
        'default': 'xxhigh',
        'roles': {
            'phase-1-init': 'low',
            'phase-2-refine': 'low',
            'phase-3-outline': 'low',
            'phase-4-plan': 'low',
            'phase-5-execute': {'default': 'low', 'verification-feedback': 'low'},
            'phase-6-finalize': {
                'default': 'low',
                'verification-feedback': 'low',
                'post-run-review': 'low',
            },
        },
    }
    _write_marshal_with_models(plan_context.fixture_dir, seeded)

    cmd_effort_apply_preset(Namespace(preset='high-end'))

    on_disk = _read_marshal_models(plan_context.fixture_dir)

    # Disk state is the EXPANDED HIGH_END payload — every KNOWN_ROLES
    # entry is overwritten with HIGH_END's per-phase value.
    assert on_disk == _expanded_preset(EffortPresets.HIGH_END)

    # phase-6-finalize.verification-feedback is set to its HIGH_END
    # override level (no longer 'low').
    assert on_disk['roles']['phase-6-finalize']['verification-feedback'] == 'xhigh'

    # phase-1-init has no overrides in HIGH_END; it is written as the
    # global default shorthand ('high').
    assert on_disk['roles']['phase-1-init'] == 'high'


# =============================================================================
# (4) apply-preset --preset bogus exits non-zero with an argparse-level
#     error mentioning the valid choices
# =============================================================================


def test_apply_preset_bogus_rejected_by_argparse(plan_context):
    _write_marshal_with_models(plan_context.fixture_dir, None)

    result = run_script(
        SCRIPT_PATH, 'effort', 'apply-preset', '--preset', 'bogus'
    )

    assert not result.success, 'argparse should reject unknown preset'
    # argparse choices= produces an error mentioning the valid options.
    combined = (result.stdout + result.stderr).lower()
    assert 'economic' in combined
    assert 'balanced' in combined
    assert 'high-end' in combined


# =============================================================================
# (5) Case-insensitive / underscore alias — HIGH_END and high_end resolve
# =============================================================================


def test_apply_preset_uppercase_underscore_alias_succeeds(plan_context):
    # argparse `choices=` is the public restriction — but EffortPresets.get
    # accepts the underscore alias internally. The handler delegates to
    # EffortPresets.get, so an alias passed past argparse (e.g. via direct
    # cmd_effort_apply_preset call) must resolve to HIGH_END.
    _write_marshal_with_models(plan_context.fixture_dir, None)

    result = cmd_effort_apply_preset(Namespace(preset='HIGH_END'))

    assert result['status'] == 'success'
    assert result['default'] == 'high'

    on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert on_disk == _expanded_preset(EffortPresets.HIGH_END)


def test_apply_preset_lowercase_underscore_alias_succeeds(plan_context):
    _write_marshal_with_models(plan_context.fixture_dir, None)

    result = cmd_effort_apply_preset(Namespace(preset='high_end'))

    assert result['status'] == 'success'
    assert result['default'] == 'high'

    on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert on_disk == _expanded_preset(EffortPresets.HIGH_END)


# =============================================================================
# (6) Initial-write idempotency — apply-preset against a marshal.json
#     with no models block creates the block cleanly
# =============================================================================


def test_apply_preset_creates_models_block_when_absent(plan_context):
    _write_marshal_with_models(plan_context.fixture_dir, None)

    # Sanity: no models block on disk yet.
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert 'models' not in config

    result = cmd_effort_apply_preset(Namespace(preset='balanced'))

    assert result['status'] == 'success'
    on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert on_disk == _expanded_preset(EffortPresets.BALANCED)


# =============================================================================
# (7) Round-trip — balanced followed by economic produces exactly the
#     ECONOMIC payload (no residue from BALANCED)
# =============================================================================


def test_apply_preset_round_trip_no_residue(plan_context):
    _write_marshal_with_models(plan_context.fixture_dir, None)

    cmd_effort_apply_preset(Namespace(preset='balanced'))
    balanced_on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert balanced_on_disk == _expanded_preset(EffortPresets.BALANCED)

    cmd_effort_apply_preset(Namespace(preset='economic'))
    on_disk = _read_marshal_models(plan_context.fixture_dir)
    assert on_disk == _expanded_preset(EffortPresets.ECONOMIC)

    # BALANCED's per-phase entries must not survive the swap.
    # ECONOMIC's clean-slate write replaces every per-phase entry
    # with the ECONOMIC payload after writer-expansion: phase-6-finalize
    # is a dict-valued override in ECONOMIC ({'verification-feedback':
    # 'high'}), so the writer emits a dict with the ECONOMIC default
    # ('medium') filling every other sub-key.
    assert on_disk['roles']['phase-6-finalize'] == {
        'default': 'medium',
        'verification-feedback': 'high',
        'post-run-review': 'medium',
    }
    # phase-2-refine is bumped to 'high' in both BALANCED and ECONOMIC
    # (the new ladder pushes the three analytical phases up); the
    # writer keeps the string shorthand for flat-group overrides.
    assert on_disk['roles']['phase-2-refine'] == 'high'
