#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Distribution-contract tests for the three auto-continuation knobs (D9).

When the ``ceremony_policy`` block was dissolved, the three auto-continuation knobs
were distributed out of ``ceremony_policy.automation``. Two
(``finalize_without_asking`` / ``loop_back_without_asking``) became flat fields under
``plan.phase-6-finalize`` — the phase whose decisions they govern. The third
(``final_merge_without_asking``) is now a step-owned param nested under
``default:branch-cleanup`` in the keyed-map ``steps`` structure, read via the one-stop
``step get`` verb. The former ``ceremony_policy.automation`` home and the dedicated
``ceremony-policy`` read verb are both gone.

Orthogonal assertions per knob:

1. **Homed correctly** — the two flat knobs read back through the standard
   ``plan phase-6-finalize get --field <knob>`` path; the step-owned knob reads back
   through ``step get --step-id default:branch-cleanup``; each with its migrated default.
2. **Old home is gone** — neither ``DEFAULT_CEREMONY_POLICY`` nor a top-level
   ``ceremony_policy`` key survives in ``get_default_config()``; the flat knobs live in
   ``DEFAULT_PLAN_FINALIZE`` and the step-owned knob is declared in its step's
   ``configurable:`` frontmatter (resolved via the ``configurable_contract`` parser).
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


# The two flat auto-continuation knobs that remain phase-level fields, with their
# post-migration defaults (preserved from the historical ceremony_policy values).
# final_merge_without_asking is NOT here — it became a step-owned param nested under
# default:branch-cleanup and is covered by the dedicated step-shape tests below
# (its default was deliberately flipped True->False, lesson 2026-06-16-10-001).
_MIGRATED_KNOBS = (
    ('finalize_without_asking', True),
    ('loop_back_without_asking', False),
)

# The step-owned knob: (step_id, param, default).
_STEP_OWNED_KNOB = ('default:branch-cleanup', 'final_merge_without_asking', False)


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from the keyed-map form of steps.

    `plan.phase-6-finalize.steps` serializes as the canonical keyed map:
    `{step_id: {params}}` (`{}` for a config-less step). Returns the step's nested
    param object, or ``None`` when the step id is absent (preserving the
    `.get(param)` call-site contract).
    """
    return steps_map.get(step_id)


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


def test_final_merge_without_asking_resolves_via_step_get(plan_context):
    """final_merge_without_asking reads back via ``step get`` on default:branch-cleanup, read-only."""
    _cmd_init.cmd_init(Namespace(force=False))
    before = _hash_marshal(plan_context.fixture_dir)

    step_id, param, expected = _STEP_OWNED_KNOB
    result = _cmd_quality_phases.cmd_phase(
        Namespace(verb='step', step_verb='get', step_id=step_id), 'phase-6-finalize'
    )

    assert result['status'] == 'success'
    assert result['step_id'] == step_id
    assert result['params'][param] is expected, f'{param} default must be {expected}'

    # The read path never mutates marshal.json
    assert _hash_marshal(plan_context.fixture_dir) == before


# =============================================================================
# (2) Old ceremony_policy home is gone; knobs live in DEFAULT_PLAN_FINALIZE
# =============================================================================


def test_flat_knobs_homed_in_default_plan_finalize():
    """The two flat knobs must live in the loose DEFAULT_PLAN_FINALIZE block."""
    for knob, _ in _MIGRATED_KNOBS:
        assert knob in _config_defaults.DEFAULT_PLAN_FINALIZE, (
            f'{knob} must be schema-registered in DEFAULT_PLAN_FINALIZE'
        )


def test_step_owned_knob_homed_in_configurable_declaration():
    """final_merge_without_asking must resolve under default:branch-cleanup via the parser."""
    from configurable_contract import resolve_step_defaults

    step_id, param, expected = _STEP_OWNED_KNOB
    step_params = resolve_step_defaults(step_id)
    assert param in step_params, (
        f"{param} must be declared under {step_id}'s configurable: frontmatter"
    )
    assert step_params[param] is expected
    # the centralized constant is gone
    assert not hasattr(_config_defaults, '_FINALIZE_STEP_PARAMS'), (
        '_FINALIZE_STEP_PARAMS must be deleted — params resolve via the parser'
    )
    # and it is NOT a flat sibling of steps
    assert param not in _config_defaults.DEFAULT_PLAN_FINALIZE


def test_get_default_config_homes_flat_knobs_under_phase_6_finalize():
    """get_default_config() must carry the two flat knobs under plan.phase-6-finalize."""
    cfg = _config_defaults.get_default_config()
    finalize = cfg['plan']['phase-6-finalize']
    for knob, expected in _MIGRATED_KNOBS:
        assert finalize.get(knob) is expected, (
            f'plan.phase-6-finalize.{knob} must default to {expected}'
        )


def test_get_default_config_homes_step_owned_knob_under_branch_cleanup():
    """get_default_config() must nest final_merge_without_asking under default:branch-cleanup."""
    cfg = _config_defaults.get_default_config()
    step_id, param, expected = _STEP_OWNED_KNOB
    branch_cleanup = _params_for(cfg['plan']['phase-6-finalize']['steps'], step_id)
    assert branch_cleanup.get(param) is expected, (
        f'steps[{step_id}].{param} must default to {expected}'
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
