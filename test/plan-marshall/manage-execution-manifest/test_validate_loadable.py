#!/usr/bin/env python3
"""Tests for the manage-execution-manifest ``validate-loadable`` subcommand.

Covers the loadability fail-fast guard consumed by phase-6-finalize Step 1.5:

- Single-step happy path (built-in step with present standards file)
- Single-step missing-file path (canonical actionable message)
- External step short-circuit (project: / bundle:skill → loadable=true, no check)
- ``default:`` prefix is accepted and stripped
- ``--all`` happy path against a real manifest
- ``--all`` reports per-step results and unloadable_count when one entry is missing
- Mutual-exclusivity + missing-mode validation errors
- Manifest-missing yields ``file_not_found`` for ``--all``
"""

# ruff: noqa: I001, E402

import importlib.util
from argparse import Namespace
from pathlib import Path


# Tier 2 direct import — match the test layout used by sibling tests.
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_validate_loadable', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_validate_loadable = _mem.cmd_validate_loadable
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess so tests do not depend on a
# running executor.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace helpers
# =============================================================================


def _validate_loadable_ns(
    plan_id: str = 'vl-test',
    step_id: str | None = None,
    use_all: bool = False,
    check_seed: bool = False,
) -> Namespace:
    return Namespace(plan_id=plan_id, step_id=step_id, all=use_all, check_seed=check_seed)


def _compose_ns(
    plan_id: str,
    phase_6_steps: str | None = None,
    change_type: str = 'feature',
    scope_estimate: str = 'multi_module',
    affected_files_count: int = 5,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


# =============================================================================
# Single-step form
# =============================================================================


class TestSingleStepForm:
    def test_built_in_step_with_present_standards_returns_loadable(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-builtin-ok', step_id='commit-push'))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_id'] == 'commit-push'
        assert result['loadable'] is True
        assert result['standards_path'].endswith('phase-6-finalize/standards/commit-push.md')
        # Happy path carries no `message` field.
        assert 'message' not in result

    def test_default_prefix_is_stripped(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-prefix', step_id='default:commit-push')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['step_id'] == 'commit-push', 'default: prefix must be stripped from echoed step_id'

    def test_missing_standards_file_returns_actionable_message(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-missing', step_id='ghost-step-that-does-not-exist')
        )
        assert result is not None
        assert result['status'] == 'success'
        assert result['loadable'] is False
        # Canonical actionable phrasing — phase-6-finalize Step 1.5 surfaces this verbatim.
        assert 'ghost-step-that-does-not-exist' in result['message']
        assert 'missing standards file' in result['message']
        assert 'deleted the file without sweeping' in result['message']
        assert result['standards_path'].endswith('phase-6-finalize/workflow/ghost-step-that-does-not-exist.md')

    def test_project_step_short_circuits_to_loadable(self, plan_context):
        """External steps (project:foo) are not validated by this guard."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-project', step_id='project:finalize-step-deploy-target')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['standards_path'] == ''
        # External step ids are echoed verbatim (no prefix stripping).
        assert result['step_id'] == 'project:finalize-step-deploy-target'

    def test_skill_step_short_circuits_to_loadable(self, plan_context):
        """Fully-qualified skill steps short-circuit the same way as project: steps."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-skill', step_id='plan-marshall:plan-retrospective')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['standards_path'] == ''


# =============================================================================
# Mutual exclusivity
# =============================================================================


class TestArgumentValidation:
    def test_neither_step_id_nor_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-neither'))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'

    def test_both_step_id_and_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-both', step_id='commit-push', use_all=True)
        )
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'


# =============================================================================
# Bulk (--all) form
# =============================================================================


class TestBulkForm:
    def test_all_against_default_manifest_reports_every_step(self, plan_context):
        cmd_compose(_compose_ns('vl-all-default'))
        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-default', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 0
        results = result['results']
        assert isinstance(results, list)
        assert len(results) == len(DEFAULT_PHASE_6_STEPS)
        for entry in results:
            assert entry['loadable'] is True
            assert entry['step_id'] in DEFAULT_PHASE_6_STEPS

    def test_all_flags_unloadable_step_with_actionable_message(self, plan_context):
        # Compose a manifest then mutate it to add a non-existent step. The
        # composer's candidate-set normalization strips unknown names, so we
        # have to write the manifest directly (re-use the file ops the script
        # itself uses).
        cmd_compose(_compose_ns('vl-all-missing'))
        manifest = _mem.read_manifest('vl-all-missing')
        assert manifest is not None
        manifest['phase_6']['steps'].append('ghost-step-not-on-disk')
        _mem.write_manifest('vl-all-missing', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-missing', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 1
        unloadable = [r for r in result['results'] if not r['loadable']]
        assert len(unloadable) == 1
        ghost = unloadable[0]
        assert ghost['step_id'] == 'ghost-step-not-on-disk'
        assert 'missing standards file' in ghost['message']
        assert 'ghost-step-not-on-disk' in ghost['message']

    def test_all_with_external_steps_marks_them_loadable_without_check(self, plan_context):
        # Compose a default manifest, then inject an external step.
        cmd_compose(_compose_ns('vl-all-mixed'))
        manifest = _mem.read_manifest('vl-all-mixed')
        assert manifest is not None
        manifest['phase_6']['steps'].insert(1, 'project:finalize-step-deploy-target')
        _mem.write_manifest('vl-all-mixed', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-mixed', use_all=True))
        assert result is not None
        assert result['unloadable_count'] == 0
        external_rows = [r for r in result['results'] if ':' in r['step_id']]
        assert len(external_rows) == 1
        assert external_rows[0]['loadable'] is True
        assert external_rows[0]['standards_path'] == ''

    def test_all_with_missing_manifest_returns_file_not_found(self, plan_context, capsys):
        # Do not compose — manifest does not exist on disk.
        result = cmd_validate_loadable(_validate_loadable_ns('vl-no-manifest', use_all=True))
        # cmd_validate_loadable returns None on file_not_found and emits a
        # TOON error to stdout via output_toon_error. Confirm via captured stdout.
        assert result is None
        captured = capsys.readouterr()
        assert 'file_not_found' in captured.out


# =============================================================================
# Helper-level invariants — pin _is_external_step / _resolve_standards_path
# =============================================================================


class TestHelperInvariants:
    def test_is_external_step_classifies_correctly(self):
        assert _mem._is_external_step('project:foo') is True
        assert _mem._is_external_step('plan-marshall:plan-retrospective') is True
        assert _mem._is_external_step('commit-push') is False
        assert _mem._is_external_step('default:commit-push') is False

    def test_resolve_standards_path_strips_default_prefix(self):
        bare_path = _mem._resolve_standards_path('commit-push')
        prefixed_path = _mem._resolve_standards_path('default:commit-push')
        assert bare_path == prefixed_path

    def test_resolve_standards_path_lands_under_phase_6_finalize_standards(self):
        path = _mem._resolve_standards_path('commit-push')
        assert path.parent.name == 'standards'
        assert path.parent.parent.name == 'phase-6-finalize'


# =============================================================================
# Array-authority contract (--all) — composed array is authoritative for order
# =============================================================================
#
# D4 array-authority contract: once the manifest is composed, ``phase_6.steps``
# is the authoritative execution order. The ``--all`` path therefore does NOT
# re-assert ascending order against each step's frontmatter ``order:`` — only
# standards-file loadability is a hard error here. The ascending-order guard
# lives exclusively on the pre-composition SEED path (``--check-seed``, below).
# The order-resolution helpers (``_resolve_step_order``, ``_check_ascending_order``)
# are retained because ``--check-seed`` still consumes them.


class TestArrayAuthorityContract:
    def test_in_order_phase_6_steps_pass(self, plan_context):
        """An --all manifest whose steps are in ascending order returns success."""
        cmd_compose(_compose_ns('vl-order-ok'))
        manifest = _mem.read_manifest('vl-order-ok')
        assert manifest is not None
        # Built-in steps in ascending order (commit-push=10, create-pr=20)
        # followed by project steps in ascending order (80, 85).
        manifest['phase_6']['steps'] = [
            'commit-push',
            'create-pr',
            'project:finalize-step-deploy-target',
            'project:finalize-step-sync-plugin-cache',
        ]
        _mem.write_manifest('vl-order-ok', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-ok', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 0
        assert 'error' not in result

    def test_frontmatter_array_disagreement_does_not_fail(self, plan_context):
        """Per D4, a composed array whose order disagrees with frontmatter still passes.

        The legacy guard returned ``order_inversion`` here. Under the array-authority
        contract the composed ``phase_6.steps`` array is authoritative, so the same
        out-of-frontmatter-order manifest now returns ``status: success`` with no
        order error — only loadability is a hard error on the ``--all`` path.
        """
        cmd_compose(_compose_ns('vl-order-disagree'))
        manifest = _mem.read_manifest('vl-order-disagree')
        assert manifest is not None
        # Frontmatter order would call this an inversion: sync-plugin-cache (85)
        # precedes deploy-target (80). The array says this is the intended order.
        manifest['phase_6']['steps'] = [
            'commit-push',
            'project:finalize-step-sync-plugin-cache',
            'project:finalize-step-deploy-target',
        ]
        _mem.write_manifest('vl-order-disagree', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-disagree', use_all=True))
        assert result is not None
        # No order_inversion error — the array is authoritative.
        assert result['status'] == 'success'
        assert 'error' not in result
        assert 'order_inversion' not in result.values()
        # All steps load, so unloadable_count is zero and results is the full walk.
        assert result['unloadable_count'] == 0
        assert isinstance(result['results'], list)
        assert len(result['results']) == 3

    def test_project_step_order_resolves_from_project_local_skill_md(self):
        """project: step order is read from .claude/skills/{name}/SKILL.md frontmatter."""
        assert _mem._resolve_step_order('project:finalize-step-deploy-target') == 80
        assert _mem._resolve_step_order('project:finalize-step-sync-plugin-cache') == 85

    def test_builtin_step_order_resolves_from_standards_frontmatter(self):
        """Built-in step order is read from its standards/workflow doc frontmatter."""
        assert _mem._resolve_step_order('commit-push') == 10
        assert _mem._resolve_step_order('default:commit-push') == 10
        assert _mem._resolve_step_order('create-pr') == 20

    def test_all_path_reports_only_loadability_not_order(self, plan_context):
        """The --all walk surfaces unloadable steps but never an order error.

        Mixes resolvable-order steps, an unresolvable-order bundle:skill step, and
        a ghost step (no standards file). The ghost step is unloadable, but that is
        a loadability concern; the array is authoritative for order, so no order
        check runs and status stays success on the strength of loadability alone.
        """
        # _resolve_step_order returns None for a non-existent step and for a
        # bundle:skill external step (no project-local SKILL.md).
        assert _mem._resolve_step_order('ghost-step-not-on-disk') is None
        assert _mem._resolve_step_order('plan-marshall:plan-retrospective') is None

        cmd_compose(_compose_ns('vl-order-skip'))
        manifest = _mem.read_manifest('vl-order-skip')
        assert manifest is not None
        manifest['phase_6']['steps'] = [
            'commit-push',
            'plan-marshall:plan-retrospective',
            'project:finalize-step-deploy-target',
            'ghost-step-not-on-disk',
            'project:finalize-step-sync-plugin-cache',
        ]
        _mem.write_manifest('vl-order-skip', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-skip', use_all=True))
        assert result is not None
        # The ghost step is unloadable (no standards file); status stays success
        # only because loadability is the sole hard error on the --all path —
        # order is never checked against frontmatter under the array-authority
        # contract.
        assert result['status'] == 'success'
        assert 'error' not in result
        assert result['unloadable_count'] == 1

    def test_single_step_id_path_reports_no_order_error(self, plan_context):
        """--step-id reports loadability only; no order error on any path now."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-order-single', step_id='project:finalize-step-sync-plugin-cache')
        )
        assert result is not None
        assert result['status'] == 'success'
        assert result['loadable'] is True
        # No order_inversion error on the single-step path.
        assert result.get('error') != 'order_inversion'

    def test_check_ascending_order_helper_returns_none_for_ascending(self):
        """The _check_ascending_order helper returns None for an ascending list."""
        assert _mem._check_ascending_order(['commit-push', 'create-pr']) is None

    def test_check_ascending_order_helper_detects_inversion(self):
        """The _check_ascending_order helper returns a diagnostic for an inversion."""
        message = _mem._check_ascending_order(['create-pr', 'commit-push'])
        assert message is not None
        assert 'commit-push' in message
        assert 'create-pr' in message


# =============================================================================
# Seed-order guard (--check-seed) — reads marshal.json directly
# =============================================================================


class TestCheckSeedMode:
    def test_inverted_seed_returns_seed_order_inversion(self, plan_context, monkeypatch):
        """A seed whose phase-6-finalize steps are inverted returns seed_order_inversion."""
        # An inversion: sync-plugin-cache (85) precedes deploy-target (80).
        inverted = [
            'default:commit-push',
            'project:finalize-step-sync-plugin-cache',
            'project:finalize-step-deploy-target',
        ]
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: inverted)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-inverted', check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'seed_order_inversion'
        assert 'project:finalize-step-deploy-target' in result['message']
        assert 'project:finalize-step-sync-plugin-cache' in result['message']

    def test_correct_seed_passes(self, plan_context, monkeypatch):
        """A seed with ascending phase-6-finalize order returns success."""
        ascending = [
            'default:commit-push',
            'default:create-pr',
            'project:finalize-step-deploy-target',
            'project:finalize-step-sync-plugin-cache',
        ]
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: ascending)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-ok', check_seed=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_count'] == len(ascending)
        assert 'error' not in result

    def test_unreadable_seed_returns_seed_unreadable(self, plan_context, monkeypatch):
        """When the seed cannot be read, the mode returns seed_unreadable."""
        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', lambda phase_key: None)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-seed-missing', check_seed=True))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'seed_unreadable'

    def test_check_seed_reads_phase_6_finalize_key(self, plan_context, monkeypatch):
        """--check-seed sources steps from the phase-6-finalize marshal key."""
        seen: list[str] = []

        def _spy(phase_key):
            seen.append(phase_key)
            return ['default:commit-push']

        monkeypatch.setattr(_mem, '_read_marshal_phase_steps', _spy)
        cmd_validate_loadable(_validate_loadable_ns('vl-seed-key', check_seed=True))
        assert seen == ['phase-6-finalize']

    def test_check_seed_is_mutually_exclusive_with_step_id(self, plan_context):
        """Supplying both --step-id and --check-seed is an invalid_arguments error."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-seed-both', step_id='commit-push', check_seed=True)
        )
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'

    def test_check_seed_is_mutually_exclusive_with_all(self, plan_context):
        """Supplying both --all and --check-seed is an invalid_arguments error."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-seed-all', use_all=True, check_seed=True)
        )
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'


# =============================================================================
# record-metrics order regression — must trail every token-consuming step
# =============================================================================
#
# `default:record-metrics` is the LAST token-accounting finalize step: its
# `end-phase` call folds the `<usage>` spend of every dispatched finalize step
# into the closed `6-finalize` phase row, so it MUST resolve to a frontmatter
# `order` strictly greater than every token-consuming step's order. The
# token-consuming finalize steps are the ones whose bodies dispatch a subagent
# or run a token-spending sweep before record-metrics closes the ledger:
# deploy-target, sync-plugin-cache, lessons-housekeeping, plugin-doctor, and
# pre-submission-self-review. This regression would fail if record-metrics'
# order were reverted below any of them (the defect this plan corrected).


# The token-consuming finalize steps that MUST precede record-metrics, in the
# step-id form `_resolve_step_order` consumes (project: steps resolve from
# `.claude/skills/{bare-name}/SKILL.md`).
_TOKEN_CONSUMING_FINALIZE_STEPS: list[str] = [
    'project:finalize-step-deploy-target',
    'project:finalize-step-sync-plugin-cache',
    'project:finalize-step-lessons-housekeeping',
    'project:finalize-step-plugin-doctor',
    'project:finalize-step-pre-submission-self-review',
]


class TestRecordMetricsOrderAfterTokenConsumingSteps:
    def test_record_metrics_order_exceeds_every_token_consuming_step(self):
        """record-metrics order strictly trails every token-consuming step.

        Fails if record-metrics' frontmatter `order` is reverted at or below
        any token-consuming finalize step — the regression this plan guards.
        """
        record_metrics_order = _mem._resolve_step_order('default:record-metrics')
        assert record_metrics_order is not None

        for step in _TOKEN_CONSUMING_FINALIZE_STEPS:
            step_order = _mem._resolve_step_order(step)
            assert step_order is not None, (
                f'token-consuming step {step!r} has no resolvable frontmatter order'
            )
            assert record_metrics_order > step_order, (
                f'record-metrics order ({record_metrics_order}) must be strictly '
                f'greater than {step!r} order ({step_order}) — record-metrics must '
                f'run after every token-consuming finalize step so end-phase folds '
                f'their token spend into the closed 6-finalize phase row'
            )
