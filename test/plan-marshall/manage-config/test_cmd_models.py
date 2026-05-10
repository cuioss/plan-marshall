#!/usr/bin/env python3
"""Tests for `manage-config models apply-preset --preset <name>` write subcommand.

Covers the user-mandated "completely overwrites" semantic, the
case-insensitive / underscore alias resolution that ``ModelPresets.get``
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

# `_cmd_models` imports `model_presets` at module level. Make sure the
# plan-marshall scripts directory is importable BEFORE we load _cmd_models.
if str(_PLAN_MARSHALL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAN_MARSHALL_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_model_presets_mod = _load_module(
    'model_presets', 'model_presets.py', _PLAN_MARSHALL_SCRIPTS_DIR
)
ModelPresets = _model_presets_mod.ModelPresets

_cmd_models_mod = _load_module(
    '_cmd_models', '_cmd_models.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
cmd_models = _cmd_models_mod.cmd_models
cmd_models_apply_preset = _cmd_models_mod.cmd_models_apply_preset
KNOWN_ROLES = _cmd_models_mod.KNOWN_ROLES


def _expanded_preset(preset: dict) -> dict:
    """Return the fully-qualified roles map that apply-preset writes to disk.

    `apply-preset` expands the preset payload so every entry in
    ``KNOWN_ROLES`` is explicit on disk, with the preset's per-role
    overrides taking precedence over ``default``. Tests use this helper
    to assert the on-disk shape without reproducing the expansion logic
    inline.
    """
    default_level = preset['default']
    overrides = preset.get('roles', {})
    expanded_roles = {role: default_level for role in KNOWN_ROLES}
    expanded_roles.update(overrides)
    return {'default': default_level, 'roles': expanded_roles}

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script  # noqa: E402


def _write_marshal_with_models(fixture_dir: Path, models_block: dict | None) -> None:
    """Write marshal.json with optional `models` block on top of the test default."""
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    if models_block is not None:
        config['models'] = models_block
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _read_marshal_models(fixture_dir: Path) -> dict:
    marshal_path = fixture_dir / 'marshal.json'
    return json.loads(marshal_path.read_text(encoding='utf-8'))['models']


# =============================================================================
# (1) apply-preset --preset economic writes the ECONOMIC payload and
#     models read --role default returns level: low
# =============================================================================


def test_apply_preset_economic_writes_expanded_payload():
    with PlanContext() as ctx:
        # Initialise marshal.json with no models block.
        _write_marshal_with_models(ctx.fixture_dir, None)

        result = cmd_models_apply_preset(Namespace(preset='economic'))

        assert result['status'] == 'success'
        assert result['preset'] == 'economic'
        assert result['default'] == 'low'
        # roles_count reflects the EXPANDED set (every KNOWN_ROLES entry
        # is explicit on disk); overrides_count reflects only the
        # explicit per-role overrides from the preset payload.
        assert result['roles_count'] == len(KNOWN_ROLES)
        assert result['overrides_count'] == len(ModelPresets.ECONOMIC['roles'])

        # Disk state matches the EXPANDED ECONOMIC payload — every
        # KNOWN_ROLES entry is present, with preset overrides preserved.
        on_disk = _read_marshal_models(ctx.fixture_dir)
        assert on_disk == _expanded_preset(ModelPresets.ECONOMIC)

        # Self-documenting on-disk shape: every KNOWN_ROLES entry is a
        # key under models.roles so the user can edit them by hand.
        for role in KNOWN_ROLES:
            assert role in on_disk['roles'], (
                f"role '{role}' missing from expanded on-disk roles map"
            )

        # `pr_creation` is now an explicit entry (with the default-level
        # value), so the resolver attributes it to the role row rather
        # than the default fallback.
        read_result = cmd_models(Namespace(role='pr_creation'))
        assert read_result['status'] == 'success'
        assert read_result['level'] == 'low'
        assert read_result['source'] == 'models.roles.pr_creation'

        # Roles explicitly bumped by the preset keep their override level.
        for role, expected in ModelPresets.ECONOMIC['roles'].items():
            assert on_disk['roles'][role] == expected


# =============================================================================
# (2) apply-preset balanced + models read --role research returns
#     level: high, source: models.roles.research
# =============================================================================


def test_apply_preset_balanced_then_read_research_returns_high():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        cmd_models_apply_preset(Namespace(preset='balanced'))

        read_result = cmd_models(Namespace(role='research'))
        assert read_result['status'] == 'success'
        assert read_result['level'] == 'high'
        assert read_result['source'] == 'models.roles.research'


# =============================================================================
# (3) apply-preset overwrites — pre-seeded block is fully replaced
# =============================================================================


def test_apply_preset_high_end_overwrites_pre_seeded_block():
    with PlanContext() as ctx:
        # Pre-seed with a custom block whose values do NOT appear in HIGH_END.
        seeded = {
            'default': 'xxhigh',
            'roles': {
                'q_gate_validation': 'low',
                'phantom_role_not_in_high_end': 'medium',
            },
        }
        _write_marshal_with_models(ctx.fixture_dir, seeded)

        cmd_models_apply_preset(Namespace(preset='high-end'))

        on_disk = _read_marshal_models(ctx.fixture_dir)

        # Disk state is the EXPANDED HIGH_END payload — every KNOWN_ROLES
        # entry is explicit, none of the seeded values survive.
        assert on_disk == _expanded_preset(ModelPresets.HIGH_END)

        # Specifically: the seeded q_gate_validation: low is replaced by xhigh.
        assert on_disk['roles']['q_gate_validation'] == 'xhigh'

        # And the seeded phantom_role is gone entirely (overwrite, not merge —
        # only KNOWN_ROLES survive).
        assert 'phantom_role_not_in_high_end' not in on_disk['roles']

        # Roles not explicitly bumped by HIGH_END are written at the default
        # level ('high') rather than dropped.
        non_override_role = next(
            r for r in KNOWN_ROLES if r not in ModelPresets.HIGH_END['roles']
        )
        assert on_disk['roles'][non_override_role] == 'high'


# =============================================================================
# (4) apply-preset --preset bogus exits non-zero with an argparse-level
#     error mentioning the valid choices
# =============================================================================


def test_apply_preset_bogus_rejected_by_argparse():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        result = run_script(
            SCRIPT_PATH, 'models', 'apply-preset', '--preset', 'bogus'
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


def test_apply_preset_uppercase_underscore_alias_succeeds():
    # argparse `choices=` is the public restriction — but ModelPresets.get
    # accepts the underscore alias internally. The handler delegates to
    # ModelPresets.get, so an alias passed past argparse (e.g. via direct
    # cmd_models_apply_preset call) must resolve to HIGH_END.
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        result = cmd_models_apply_preset(Namespace(preset='HIGH_END'))

        assert result['status'] == 'success'
        assert result['default'] == 'high'

        on_disk = _read_marshal_models(ctx.fixture_dir)
        assert on_disk == _expanded_preset(ModelPresets.HIGH_END)


def test_apply_preset_lowercase_underscore_alias_succeeds():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        result = cmd_models_apply_preset(Namespace(preset='high_end'))

        assert result['status'] == 'success'
        assert result['default'] == 'high'

        on_disk = _read_marshal_models(ctx.fixture_dir)
        assert on_disk == _expanded_preset(ModelPresets.HIGH_END)


# =============================================================================
# (6) Initial-write idempotency — apply-preset against a marshal.json
#     with no models block creates the block cleanly
# =============================================================================


def test_apply_preset_creates_models_block_when_absent():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        # Sanity: no models block on disk yet.
        config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        assert 'models' not in config

        result = cmd_models_apply_preset(Namespace(preset='balanced'))

        assert result['status'] == 'success'
        on_disk = _read_marshal_models(ctx.fixture_dir)
        assert on_disk == _expanded_preset(ModelPresets.BALANCED)


# =============================================================================
# (7) Round-trip — balanced followed by economic produces exactly the
#     ECONOMIC payload (no residue from BALANCED)
# =============================================================================


def test_apply_preset_round_trip_no_residue():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, None)

        cmd_models_apply_preset(Namespace(preset='balanced'))
        balanced_on_disk = _read_marshal_models(ctx.fixture_dir)
        assert balanced_on_disk == _expanded_preset(ModelPresets.BALANCED)

        cmd_models_apply_preset(Namespace(preset='economic'))
        on_disk = _read_marshal_models(ctx.fixture_dir)
        assert on_disk == _expanded_preset(ModelPresets.ECONOMIC)

        # Specifically: any BALANCED-only role overrides (e.g.,
        # automated_review at 'high') must not survive the swap. Since
        # the expansion writes every KNOWN_ROLES entry explicitly,
        # automated_review is now present at the ECONOMIC default
        # ('low') rather than absent — the residue check is on the LEVEL,
        # not the key's presence.
        assert on_disk['roles']['automated_review'] == 'low'
