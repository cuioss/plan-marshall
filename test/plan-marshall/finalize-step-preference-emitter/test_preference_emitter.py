#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Seed-wiring tests for the ``default:finalize-step-preference-emitter`` step.

The step body is an LLM-orchestration doc; the deterministic, unit-testable
surface is the seed wiring:

- the step id is a discovered default-on built-in finalize-step implementor (via
  ``extension_discovery.find_implementors``, the SOLE discovery path; the
  ``BUILT_IN_FINALIZE_STEPS`` constant was removed) so a fresh consumer
  marshal.json picks it up,
- the step declares ``post_run_review: true`` and the paired
  ``mutates_source: false``, and is ordered accordingly — after the merge gate
  ``default:branch-cleanup`` and after ``default:lessons-capture``, but still
  before ``default:record-metrics`` / ``default:archive-plan``,
- a non-empty discovered description exists for the step,
- the configurable contract resolves the ``preference_min_recurrence`` default
  (2) from the step's ``configurable:`` frontmatter, and
- the seeded ``DEFAULT_PLAN_FINALIZE['steps']`` keyed map carries the step with
  that nested default.

Every ordering assertion compares POSITIONS in the live discovered seed list
rather than literal ``order`` integers, so a renumber that preserves the
relations keeps these tests green while a renumber that breaks one fails.
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
    assert spec is not None and spec.loader is not None
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
            # `or ''` (not the `.get` default) so a present-but-null description
            # coerces to '' rather than the truthy literal string 'None'.
            return str(rec.get('description') or '')
    return ''


def _discovered_record(step_id: str) -> dict:
    """Return the discovered implementor record for a finalize-step id."""
    from extension_discovery import find_implementors

    for rec in find_implementors(_config_defaults.FINALIZE_STEP_EXT_POINT):
        if rec.get('name') == step_id:
            return rec
    return {}


class TestPreferenceEmitterSeedWiring:
    """The step is a discovered default-on built-in finalize-step implementor.

    Covers its discovered presence, the frontmatter facts that classify it
    (``post_run_review`` / ``mutates_source``), and the ordering relations those
    facts oblige.
    """

    def test_step_registered_in_built_in_finalize_steps(self):
        assert _STEP_ID in _discovered_seed_step_ids(), (
            f'{_STEP_ID} must be a discovered default-on built-in step so a fresh '
            'consumer marshal.json discovers it'
        )

    def test_step_ordered_after_merge_gate(self):
        # The step is post_run_review: it generalizes finding DISPOSITIONS, and
        # the merge gate's re-review barrier is still producing and triaging
        # findings when it runs. Its evidence is therefore only complete once
        # default:branch-cleanup has run, so it MUST be ordered AFTER the gate.
        # It no longer writes tracked source (see test_step_declares_mutates_source_false),
        # so the pre-merge source-edit pushability invariant no longer applies to it.
        steps = _discovered_seed_step_ids()
        assert _STEP_ID in steps
        assert 'default:branch-cleanup' in steps
        assert steps.index(_STEP_ID) > steps.index('default:branch-cleanup'), (
            'preference-emitter reads dispositions the merge gate itself produces, '
            'so it must run AFTER default:branch-cleanup — reporting before that '
            'gate would generalize over evidence that does not exist yet'
        )

    def test_step_ordered_after_lessons_capture(self):
        # Unchanged relative constraint: it learns from dispositions settled by
        # lessons-capture, so it must run AFTER it. Together with the merge-gate
        # and record-metrics bounds, this pins the step's slot.
        steps = _discovered_seed_step_ids()
        assert _STEP_ID in steps
        assert 'default:lessons-capture' in steps
        assert steps.index(_STEP_ID) > steps.index('default:lessons-capture'), (
            'preference-emitter learns from settled dispositions, so it must run '
            'after default:lessons-capture'
        )

    def test_step_declares_post_run_review(self):
        # deliverable 1: the post-run-review role is a DECLARED frontmatter fact,
        # not an undeclared convention — it is what obliges the post-merge
        # placement asserted above and what the derivation guard reads.
        record = _discovered_record(_STEP_ID)
        assert record, (
            f'{_STEP_ID} must be a discovered finalize-step implementor'
        )
        from extension_discovery import _read_frontmatter_fields

        fields = _read_frontmatter_fields(Path(record['path']), ('post_run_review',))
        assert fields.get('post_run_review') is True, (
            f"{_STEP_ID} output is an assessment of the just-finished run (P1) and "
            'reads dispositions only determined at or after the merge gate (P2), so '
            'its frontmatter must declare post_run_review: true'
        )

    def test_step_declares_mutates_source_false(self):
        # deliverable 1: the source write is REMOVED, not relocated — the owed
        # architecture hints are filed as a follow-up artifact instead. The
        # declaration must be EXPLICIT (`is False`, so an absent key fails too):
        # a step ordered at or after the merge gate that declares no
        # mutates_source key is the mutates_source_declaration_missing error.
        record = _discovered_record(_STEP_ID)
        assert record, (
            f'{_STEP_ID} must be a discovered finalize-step implementor'
        )
        from extension_discovery import _read_frontmatter_fields

        fields = _read_frontmatter_fields(Path(record['path']), ('mutates_source',))
        assert fields.get('mutates_source') is False, (
            f'{_STEP_ID} runs after the merge gate, where a tracked-source edit '
            'could never ride the plan PR, so its frontmatter must explicitly '
            'declare mutates_source: false'
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
