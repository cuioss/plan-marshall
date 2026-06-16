#!/usr/bin/env python3
"""Distribution-contract tests for the three auto-continuation knobs (D9).

When the ``ceremony_policy`` block was dissolved, the three auto-continuation knobs
(``finalize_without_asking`` / ``loop_back_without_asking`` / ``final_merge_without_asking``)
were distributed back into ``plan.phase-6-finalize`` — the phase whose decisions they
govern. The former ``ceremony_policy.automation`` home and the dedicated
``ceremony-policy`` read verb are both gone.

Three orthogonal assertions per knob:

1. **Homed in plan.phase-6-finalize** — each knob reads back through the standard
   ``plan phase-6-finalize get --field <knob>`` path with its migrated default.
2. **Old home is gone** — neither ``DEFAULT_CEREMONY_POLICY`` nor a top-level
   ``ceremony_policy`` key survives in ``get_default_config()``; the knob lives in
   ``DEFAULT_PLAN_FINALIZE``.
3. **Post-migration defaults are exact** — the distributed defaults match their intended
   post-migration values (forward auto-continue ``True``, reverse halt ``False``,
   final-merge-without-asking ``False``). The first two preserve the historical
   ``ceremony_policy`` defaults; the merge gate's default was deliberately flipped from the
   historical ``auto_merge_after_ci: True`` to ``final_merge_without_asking: False``
   (lesson 2026-06-16-10-001) so new projects prompt before the irreversible merge.

The handlers are exercised via direct importlib loading (the manage-config test
convention); read-only round-trip stability of marshal.json is asserted by hashing
the file before and after each ``get``.
"""

# ruff: noqa: I001, E402

import hashlib
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _MANAGE_CONFIG_SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module('_config_defaults_for_distribution', '_config_defaults.py')
_cmd_quality_phases = _load_module('_cmd_quality_phases_for_distribution', '_cmd_quality_phases.py')
_cmd_init = _load_module('_cmd_init_for_distribution', '_cmd_init.py')

# Import shared infrastructure (conftest.py sets up PYTHONPATH).
import conftest  # noqa: E402, F401


# The three distributed knobs with their post-migration defaults. The first two preserve
# their historical ceremony_policy values; final_merge_without_asking was deliberately
# flipped True->False (lesson 2026-06-16-10-001).
_MIGRATED_KNOBS = (
    ('finalize_without_asking', True),
    ('loop_back_without_asking', False),
    ('final_merge_without_asking', False),
)


def _hash_marshal(fixture_dir):
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


# =============================================================================
# (1) Resolves from the new plan.phase-6-finalize path
# =============================================================================


def test_each_knob_resolves_from_phase_6_finalize(plan_context):
    """Each migrated knob reads back through ``plan phase-6-finalize get`` with its default."""
    # fresh marshal.json (no overrides → default-merge path)
    _cmd_init.cmd_init(Namespace(force=False))
    before = _hash_marshal(plan_context.fixture_dir)

    # each knob resolves to its post-migration default, read-only
    for knob, expected in _MIGRATED_KNOBS:
        result = _cmd_quality_phases.cmd_phase(
            Namespace(verb='get', field=knob), 'phase-6-finalize'
        )
        assert result['status'] == 'success', f'{knob} must resolve'
        assert result['field'] == knob
        assert result['value'] is expected, f'{knob} default must be {expected}'

    # The read path never mutates marshal.json
    assert _hash_marshal(plan_context.fixture_dir) == before


# =============================================================================
# (2) Old ceremony_policy home is gone; knobs live in DEFAULT_PLAN_FINALIZE
# =============================================================================


def test_knobs_homed_in_default_plan_finalize():
    """All three knobs must live in the loose DEFAULT_PLAN_FINALIZE block."""
    for knob, _ in _MIGRATED_KNOBS:
        assert knob in _config_defaults.DEFAULT_PLAN_FINALIZE, (
            f'{knob} must be schema-registered in DEFAULT_PLAN_FINALIZE'
        )


def test_get_default_config_homes_knobs_under_phase_6_finalize():
    """get_default_config() must carry the three knobs under plan.phase-6-finalize."""
    cfg = _config_defaults.get_default_config()
    finalize = cfg['plan']['phase-6-finalize']
    for knob, expected in _MIGRATED_KNOBS:
        assert finalize.get(knob) is expected, (
            f'plan.phase-6-finalize.{knob} must default to {expected}'
        )


def test_ceremony_policy_block_is_dissolved():
    """No top-level ceremony_policy key and no DEFAULT_CEREMONY_POLICY constant survive."""
    cfg = _config_defaults.get_default_config()
    assert 'ceremony_policy' not in cfg, (
        'ceremony_policy must be absent from get_default_config() after dissolution'
    )
    assert not hasattr(_config_defaults, 'DEFAULT_CEREMONY_POLICY'), (
        'DEFAULT_CEREMONY_POLICY must be gone after the dissolution'
    )


# =============================================================================
# (3) Distributed defaults match their intended post-migration values
# =============================================================================


def test_migrated_defaults_match_historical_values():
    """The distributed defaults match their intended post-migration values (merge gate flipped)."""
    finalize = _config_defaults.DEFAULT_PLAN_FINALIZE
    # forward auto-continue True, reverse halt False, final-merge-without-asking False
    for knob, expected in _MIGRATED_KNOBS:
        assert finalize[knob] is expected, (
            f'{knob} must resolve to its post-migration default {expected}'
        )


def test_live_override_survives_and_resolves(plan_context):
    """A live plan.phase-6-finalize override reads back through the phase get verb.

    Confirms the distribution did not strand the write path — an operator who sets
    one knob to a non-default value reads it back unchanged while the untouched
    siblings fall back to their defaults.
    """
    # override loop_back_without_asking to True, leave the others unset
    _cmd_init.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.setdefault('plan', {}).setdefault('phase-6-finalize', {})[
        'loop_back_without_asking'
    ] = True
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    overridden = _cmd_quality_phases.cmd_phase(
        Namespace(verb='get', field='loop_back_without_asking'), 'phase-6-finalize'
    )
    sibling = _cmd_quality_phases.cmd_phase(
        Namespace(verb='get', field='finalize_without_asking'), 'phase-6-finalize'
    )

    # override wins; untouched sibling falls back to default
    assert overridden['value'] is True
    assert sibling['value'] is True  # historical default preserved
