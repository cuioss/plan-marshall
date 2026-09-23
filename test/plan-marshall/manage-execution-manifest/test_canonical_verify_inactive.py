#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the canonical-verify footprint pre-filter (inactive case).

``_apply_canonical_verify_inactive`` is the generic, canonical-agnostic
footprint pre-filter: it drops a composed phase-5 ``default:verify:{canonical}``
step when its derived role is a footprint-gated role (``integration`` / ``e2e``)
AND the live, non-empty footprint carries no path of that role. The gate is
driven entirely by the ``_CANONICAL_TO_ROLE`` derivation and the
``_FOOTPRINT_GATED_CANONICAL_ROLES`` membership table — there is no per-canonical
branch in the code path.

Safety against no-evidence footprints: BOTH an UNRESOLVABLE footprint (``None``
— the normal case during early compose at phase-4-plan, before the worktree is
materialised) and a resolvable-but-EMPTY footprint (``[]``) make the pre-filter a
no-op, so every canonical survives. The gate only fires against a NON-empty
footprint that genuinely lacks the gating role's paths — the one state that is
real evidence the role has no paths.

The two no-op states reach the same outcome here but for different reasons, and
the distinction is load-bearing rather than cosmetic: ``[]`` is a substantiated
"nothing changed", while ``None`` is "we could not look". This pre-filter treats
both as no evidence and subtracts nothing, which is why an unresolvable footprint
must not be silently normalised to ``[]`` on the way in — a consumer that DOES
distinguish them (the build verdict) would then read a positive answer off a
state nobody observed.

These tests drive ``_apply_canonical_verify_inactive`` directly with a
monkeypatched ``_resolve_footprint`` so the prefilter logic is exercised
deterministically without a live worktree or git history. ``_footprint_has_role``
is also covered directly.

Green-report binding pins (D2 hardening): ``summarize_refires`` proves the
verdict-artifact population — ``skipped`` rows never fold into firings, so a
canonical that never executed cannot authorise green — and the refire
arithmetic the triage-iteration bound consumes. The uncommitted-work half is
pinned through ``post_run_source_guard check --fail-on-dirty`` on a hermetic
tmp git repository: a dirty tree blocks (non-zero exit) while the default
stays advisory.
"""

# Tier 2 direct imports, resolved by (bundle, skill, script).

import subprocess
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_canonical_inactive'
)
_apply_canonical_verify_inactive = _mem._apply_canonical_verify_inactive
_footprint_has_role = _mem._footprint_has_role
_FOOTPRINT_GATED_CANONICAL_ROLES = _mem._FOOTPRINT_GATED_CANONICAL_ROLES
_summarize_refires = _mem.summarize_refires

_guard_script = get_script_path('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')


_PLAN_ID = 'canonical-inactive'


def _patch_footprint(monkeypatch, footprint: list[str] | None) -> None:
    """Force ``_resolve_footprint`` to return ``footprint`` for any plan id.

    ``footprint`` is the resolver's three-state return verbatim: ``None``
    (unresolvable), ``[]`` (resolvable and genuinely empty), or a path list.
    ``None`` is deliberately not collapsed into ``[]`` — the pre-filter must be
    handed the real state so its handling of each can be asserted separately.
    """
    monkeypatch.setattr(
        _mem,
        '_resolve_footprint',
        lambda plan_id: None if footprint is None else list(footprint),
    )


class TestFootprintHasRole:
    """``_footprint_has_role`` is a lowercased substring test over the footprint."""

    def test_matches_integration_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/test/FooIT.java'], markers) is True

    def test_matches_e2e_marker_in_path(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['e2e']
        assert _footprint_has_role(['tests/e2e/test_flow.py'], markers) is True

    def test_no_match_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role(['src/main/Foo.java', 'README.md'], markers) is False

    def test_match_is_case_insensitive(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        # The marker ``it.java`` is lowercased; an uppercase path still matches.
        assert _footprint_has_role(['SRC/TEST/BARIT.JAVA'], markers) is True

    def test_empty_footprint_returns_false(self):
        markers = _FOOTPRINT_GATED_CANONICAL_ROLES['integration']
        assert _footprint_has_role([], markers) is False


class TestCanonicalVerifyInactiveDrop:
    """Footprint-gated canonical-verify steps drop when their role is absent."""

    def test_integration_step_dropped_when_footprint_lacks_integration_paths(self, monkeypatch):
        """``default:verify:integration-tests`` drops when the non-empty footprint
        has no integration-role path."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java', 'README.md'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:integration-tests'], _PLAN_ID, {})
        assert kept == []
        assert dropped == ['default:verify:integration-tests']

    def test_e2e_step_dropped_when_footprint_lacks_e2e_paths(self, monkeypatch):
        """``default:verify:e2e`` drops when the non-empty footprint has no e2e path."""
        _patch_footprint(monkeypatch, ['src/main/app.py', 'docs/guide.md'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:e2e'], _PLAN_ID, {})
        assert kept == []
        assert dropped == ['default:verify:e2e']

    def test_bare_canonical_verify_form_is_also_gated(self, monkeypatch):
        """The bare ``verify:{canonical}`` form is gated identically to the prefixed form."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        kept, dropped = _apply_canonical_verify_inactive(['verify:integration-tests'], _PLAN_ID, {})
        assert kept == []
        assert dropped == ['verify:integration-tests']

    def test_only_gated_step_dropped_others_kept(self, monkeypatch):
        """Among mixed steps, only the footprint-gated canonical with no matching
        path is dropped; core canonical-verify steps survive."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        steps = [
            'default:verify:quality-gate',
            'default:verify:integration-tests',
            'default:verify:module-tests',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert dropped == ['default:verify:integration-tests']
        assert kept == ['default:verify:quality-gate', 'default:verify:module-tests']


class TestCanonicalVerifyInactiveKeep:
    """Steps survive the pre-filter when the gate does not fire."""

    def test_integration_step_kept_when_footprint_has_integration_path(self, monkeypatch):
        """A non-empty footprint WITH an integration-role path keeps the step."""
        _patch_footprint(monkeypatch, ['src/test/java/FooIT.java'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:integration-tests'], _PLAN_ID, {})
        assert kept == ['default:verify:integration-tests']
        assert dropped == []

    def test_resolvable_empty_footprint_is_a_noop_every_canonical_survives(self, monkeypatch):
        """A resolvable-but-empty footprint keeps all steps.

        Nothing changed, so no role's paths are present — but "no paths at all"
        is not evidence that the GATING role specifically has none, so the gate
        stays silent rather than subtracting on a technicality.
        """
        _patch_footprint(monkeypatch, [])
        steps = ['default:verify:integration-tests', 'default:verify:e2e']
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_unresolvable_footprint_is_a_noop_every_canonical_survives(self, monkeypatch):
        """An UNRESOLVABLE footprint (early compose, pre-materialisation) keeps all steps.

        The no-evidence safety contract: at phase-4-plan the worktree does not
        exist, so the resolver reports ``None``. The gate must NOT fire against
        it, otherwise a still-unmaterialised plan would lose its integration/e2e
        gate before there was anything to look at. Treating the unresolvable state
        as "no paths of that role" is exactly the absence-of-evidence-as-
        evidence-of-absence read that silently dropped gates elsewhere.
        """
        _patch_footprint(monkeypatch, None)
        steps = ['default:verify:integration-tests', 'default:verify:e2e']
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_unresolvable_and_non_empty_footprint_diverge(self, monkeypatch):
        """The paired opposite: only a REAL footprint lacking the role drops a step.

        Asserting the two against each other is what proves the ``None`` no-op is
        a genuine guard rather than an inert pre-filter — a gate that never fired
        would satisfy the unresolvable case on its own.
        """
        steps = ['default:verify:integration-tests']

        _patch_footprint(monkeypatch, None)
        kept_unresolvable, dropped_unresolvable = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})

        _patch_footprint(monkeypatch, ['src/main/java/Foo.java'])
        kept_real, dropped_real = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})

        assert kept_unresolvable == steps and dropped_unresolvable == []
        assert kept_real == [] and dropped_real == steps

    def test_core_roles_never_footprint_gated(self, monkeypatch):
        """``quality-gate`` / ``module-tests`` / ``coverage`` canonicals are NEVER
        footprint-gated — they survive even when the footprint lacks their paths."""
        _patch_footprint(monkeypatch, ['unrelated/path.txt'])
        steps = [
            'default:verify:quality-gate',
            'default:verify:module-tests',
            'default:verify:coverage',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_non_canonical_and_external_steps_pass_through_untouched(self, monkeypatch):
        """Non-canonical-verify default steps and external (project:/bundle:skill)
        steps are passed through verbatim — only ``verify:{canonical}`` integration
        / e2e steps are footprint-gated."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        steps = [
            'default:some-non-verify-step',
            'another-bare-step',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
        ]
        kept, dropped = _apply_canonical_verify_inactive(steps, _PLAN_ID, {})
        assert kept == steps
        assert dropped == []

    def test_unknown_canonical_passes_through(self, monkeypatch):
        """A ``default:verify:{unknown}`` whose canonical is not in the table has
        role None → not footprint-gated → survives untouched."""
        _patch_footprint(monkeypatch, ['src/main/Foo.java'])
        kept, dropped = _apply_canonical_verify_inactive(['default:verify:not-a-canonical'], _PLAN_ID, {})
        assert kept == ['default:verify:not-a-canonical']
        assert dropped == []


def _execution_row(step_id: str, outcome: str) -> dict:
    """One ``execution_log[]`` row in the shape ``record-step`` appends.

    Token columns carry the unmeasured token — the writer's output when the
    caller passes no measurement — so the firing derivation is exercised on
    the inline-build shape, not on a measured population.
    """
    return {
        'step_id': step_id,
        'phase': '5-execute',
        'outcome': outcome,
        'total_tokens': 'unmeasured',
        'tool_uses': 'unmeasured',
        'duration_ms': 'unmeasured',
    }


def _entry_for(steps: list[dict], step_id: str) -> dict:
    """The single per-step entry for ``step_id`` — the derivation emits one."""
    matches = [entry for entry in steps if entry['step_id'] == step_id]
    assert len(matches) == 1
    return matches[0]


class TestSkippedRowsNeverFire:
    """A skipped/inactive canonical contributes no firing — green is unreachable without a verdict.

    Pins the ``summarize_refires`` half of the fail-closed green-report
    binding: only an ``executed`` row is a firing, so a canonical that never
    ran (every row ``skipped``, or no row at all) leaves ``firings == 0`` and
    no downstream report may read green off it.
    """

    def test_skipped_only_step_has_zero_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:integration-tests', 'skipped'),
                _execution_row('verify:integration-tests', 'skipped'),
            ]
        )
        entry = _entry_for(steps, 'verify:integration-tests')
        assert entry['firings'] == 0
        assert entry['refires'] == 0
        assert entry['skipped'] == 2

    def test_skipped_rows_do_not_fold_into_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:quality-gate', 'executed'),
                _execution_row('verify:quality-gate', 'skipped'),
                _execution_row('verify:quality-gate', 'skipped'),
            ]
        )
        entry = _entry_for(steps, 'verify:quality-gate')
        assert entry['firings'] == 1
        assert entry['refires'] == 0
        assert entry['skipped'] == 2

    def test_single_executed_row_is_one_firing_with_no_refire(self):
        steps, _totals = _summarize_refires([_execution_row('verify:module-tests', 'executed')])
        entry = _entry_for(steps, 'verify:module-tests')
        assert entry['firings'] == 1
        assert entry['refires'] == 0


class TestRefireCountingBoundsTriageIterations:
    """The refire arithmetic the triage-iteration bound consumes.

    ``refires`` is ``max(0, firings - 1)`` per step — the first ``executed``
    row is the firing the pipeline owes, every later one is an extra firing.
    Non-completion outcomes (``failed`` / ``error`` / ``loop_back``) are
    counted apart and never inflate the firing count, so a thorough gate that
    needed several triage rounds is measured, not misgraded.
    """

    def test_three_executions_yield_two_refires(self):
        steps, totals = _summarize_refires([_execution_row('verify:quality-gate', 'executed')] * 3)
        entry = _entry_for(steps, 'verify:quality-gate')
        assert entry['firings'] == 3
        assert entry['refires'] == 2
        assert totals['refires'] == 2

    def test_failures_and_errors_do_not_inflate_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:module-tests', 'executed'),
                _execution_row('verify:module-tests', 'failed'),
                _execution_row('verify:module-tests', 'error'),
                _execution_row('verify:module-tests', 'executed'),
            ]
        )
        entry = _entry_for(steps, 'verify:module-tests')
        assert entry['firings'] == 2
        assert entry['refires'] == 1
        assert entry['failures'] == 1
        assert entry['errors'] == 1


def _git(repo: Path, *args: str) -> None:
    """Run one git command against ``repo`` with a pinned, hermetic identity.

    Identity and signing travel per-invocation so the fixture behaves
    identically on a developer machine with a global gitconfig and on a bare
    CI runner with none.
    """
    subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


@pytest.fixture
def dirty_repo(tmp_path: Path) -> Path:
    """A real git repository with one committed tracked file, then dirtied.

    The worktree starts with exactly one dirty tracked path, so the guard's
    verdict population is fully determined by this fixture.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    target = repo / 'src' / 'tracked.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('print("seed")\n', encoding='utf-8')
    _git(repo, 'add', 'src/tracked.py')
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    target.write_text('print("dirty")\n', encoding='utf-8')
    return repo


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    """A real git repository with one committed tracked file and no dirt."""
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    target = repo / 'src' / 'tracked.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('print("seed")\n', encoding='utf-8')
    _git(repo, 'add', 'src/tracked.py')
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo


class TestUncommittedBlocksGreen:
    """``post_run_source_guard check --fail-on-dirty`` gates the green report.

    A dirty tree trips the gate (non-zero exit) while the default stays
    advisory (exit 0 on the same tree) — the two modes share the payload and
    differ only in whether uncommitted state blocks the caller.
    """

    def test_fail_on_dirty_blocks_dirty_tree(self, dirty_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(dirty_repo),
            '--fail-on-dirty',
        )
        assert result.returncode == 1
        payload = result.toon()
        assert payload['clean'] is False
        assert 'src/tracked.py' in str(payload['offending_paths'])

    def test_default_stays_advisory_on_dirty_tree(self, dirty_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(dirty_repo),
        )
        assert result.returncode == 0
        payload = result.toon()
        assert payload['clean'] is False
        assert 'src/tracked.py' in str(payload['offending_paths'])

    def test_fail_on_dirty_passes_clean_tree(self, clean_repo: Path):
        result = run_script(
            _guard_script,
            'check',
            '--step-id',
            'phase-5-execute:final-quality-sweep',
            '--project-dir',
            str(clean_repo),
            '--fail-on-dirty',
        )
        assert result.returncode == 0
        payload = result.toon()
        assert payload['clean'] is True
        assert payload['offending_paths'] == []
