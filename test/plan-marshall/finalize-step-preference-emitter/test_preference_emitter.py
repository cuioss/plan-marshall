#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Seed-wiring tests for the ``default:finalize-step-preference-emitter`` step.

The step body is an LLM-orchestration doc; the deterministic, unit-testable
surface is the seed wiring:

- the step id is a discovered default-on built-in finalize-step implementor (via
  ``extension_discovery.find_implementors``, the SOLE discovery path; the
  ``BUILT_IN_FINALIZE_STEPS`` constant was removed) so a fresh consumer
  marshal.json picks it up,
- a non-empty discovered description exists for the step,
- the configurable contract resolves the ``preference_min_recurrence`` default
  (2) from the step's ``configurable:`` frontmatter, and
- the seeded ``DEFAULT_PLAN_FINALIZE['steps']`` keyed map carries the step with
  that nested default.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from pathlib import Path

_BUNDLES = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
)
_CONFIG_SCRIPTS = _BUNDLES / 'manage-config' / 'scripts'
_EXT_SCRIPTS = _BUNDLES / 'extension-api' / 'scripts'

for _d in (_CONFIG_SCRIPTS, _EXT_SCRIPTS):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module(
    '_config_defaults_for_preference_emitter_test', _CONFIG_SCRIPTS / '_config_defaults.py'
)
_configurable_contract = _load_module(
    '_configurable_contract_for_preference_emitter_test',
    _EXT_SCRIPTS / 'configurable_contract.py',
)

_STEP_ID = 'default:finalize-step-preference-emitter'


def _discovered_seed_step_ids() -> list:
    """Return the default-on built-in finalize-step ids, in seed order.

    Derived from ``extension_discovery.find_implementors`` (filter
    ``default_on == true``, sort by ``(order, name)``), mirroring
    ``_seed_finalize_steps()``.
    """
    from extension_discovery import find_implementors

    seed_records = sorted(
        (
            rec
            for rec in find_implementors(_config_defaults.FINALIZE_STEP_EXT_POINT)
            if rec.get('default_on')
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [rec['name'] for rec in seed_records if rec.get('name')]


def _discovered_description(step_id: str) -> str:
    """Return the discovered ``description`` for a finalize-step id."""
    from extension_discovery import find_implementors

    for rec in find_implementors(_config_defaults.FINALIZE_STEP_EXT_POINT):
        if rec.get('name') == step_id:
            return rec.get('description', '')
    return ''


class TestPreferenceEmitterSeedWiring:
    """The step id is a discovered default-on built-in finalize-step implementor."""

    def test_step_registered_in_built_in_finalize_steps(self):
        assert _STEP_ID in _discovered_seed_step_ids(), (
            f'{_STEP_ID} must be a discovered default-on built-in step so a fresh '
            'consumer marshal.json discovers it'
        )

    def test_step_ordered_after_branch_cleanup(self):
        # order: 80 places it after branch-cleanup (70) so dispositions are stable
        steps = _discovered_seed_step_ids()
        assert _STEP_ID in steps
        assert 'default:branch-cleanup' in steps
        assert steps.index(_STEP_ID) > steps.index('default:branch-cleanup'), (
            'preference-emitter must follow branch-cleanup'
        )

    def test_step_ordered_before_record_metrics(self):
        # before record-metrics / archive-plan, which move the plan dir out from
        # under the manage-findings read
        steps = _discovered_seed_step_ids()
        assert steps.index(_STEP_ID) < steps.index('default:record-metrics')
        assert steps.index(_STEP_ID) < steps.index('default:archive-plan')

    def test_description_entry_present_and_non_empty(self):
        description = _discovered_description(_STEP_ID)
        assert description, (
            f'{_STEP_ID} discovered description must be non-empty'
        )


class TestPreferenceEmitterConfigurableContract:
    """The configurable contract resolves the step's nested param default."""

    def test_preference_min_recurrence_default_resolves_to_two(self):
        resolved = _configurable_contract.resolve_step_defaults_optional(_STEP_ID)
        assert resolved is not None, (
            f'{_STEP_ID} owns a configurable param, so it must resolve to a '
            'non-None default map'
        )
        assert resolved['preference_min_recurrence'] == 2, (
            'preference_min_recurrence default must be 2'
        )


class TestPreferenceEmitterSeededIntoDefaultConfig:
    """The seeded keyed-map finalize steps carry the step and its nested default."""

    def test_default_plan_finalize_steps_carry_the_step(self):
        config = _config_defaults.get_default_config()
        steps = config['plan']['phase-6-finalize']['steps']
        assert _STEP_ID in steps, (
            f'{_STEP_ID} must appear in the seeded DEFAULT_PLAN_FINALIZE steps'
        )
        assert steps[_STEP_ID]['preference_min_recurrence'] == 2, (
            'the seeded step must carry the preference_min_recurrence default of 2'
        )
