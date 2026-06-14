#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Regression tests for the two phase-6-finalize convergence bugs.

These tests lock in the two bug fixes shipped by this plan from the
regression-defense angle — each test asserts the *converged* behaviour the fix
guarantees, so a future revert of either fix re-breaks a named test here. The
mechanics of each touched surface already have exhaustive unit coverage
elsewhere (``test_mark_step_done.py`` for the dirty-worktree guard,
``test_whole_tree_gate.py`` for the facet machinery,
``test_manage_execution_manifest_compose.py`` for the trigger arm); this module
is deliberately the small high-signal regression suite that ties each fix to
the user-visible symptom it cured.

Bug 1 — simplify loop-back thrash
=================================
Symptom: ``finalize-step-simplify`` left its cognitive-pass edits UNCOMMITTED
in the worktree. ``finalize-step-simplify`` is a member of
``MAY_MUTATE_WORKTREE_STEPS``, so the script-layer dirty-worktree guard in
``manage-status mark-step-done`` refused the ``--outcome done`` transition with
``dirty_worktree_done_refused``, forcing the step to re-issue as ``loop_back``.
Under ``loop_back_without_asking=false`` that prompted the user on every
finalize entry and re-fired the step, never converging.

Fix: ``finalize-step-simplify`` now COMMITS its own edits on the feature branch
before marking ``done`` (see ``standards/finalize-step-simplify.md`` Step 4), so
the worktree is clean at ``mark-step-done`` and the guard is never reached on
the normal path. Regression assertion: a ``finalize-step-simplify`` ``done``
against a CLEAN tree succeeds and persists ``outcome: done`` — no
``dirty_worktree_done_refused``, hence no forced ``loop_back``.

Bug 2 — content-drift facet
===========================
Symptom: the whole-tree gate carried a third ``generator/drift`` facet/trigger
category whose globs (``marketplace/targets/**``, ``marketplace/bundles/**``)
matched essentially every marketplace plan — including paths under the
gitignored generated ``target/claude`` tree — and the facet's import path
failed from inside a worktree, blocking finalize convergence.

Fix: the third trigger category and its facet were removed. The gate now
surfaces exactly two facets (``doctor`` / ``sweep_test``), and the composer's
``_WHOLE_TREE_INVARIANT_TRIGGER_GLOBS`` no longer carries the drift globs.
Regression assertions: (1) ``whole_tree_gate.scan`` returns a ``facets`` block
keyed by exactly ``{doctor, sweep_test}`` — no ``content_drift`` /
``generator`` / ``drift`` key; (2) the composer trigger-glob constant carries
neither ``marketplace/targets/**`` nor the bare ``marketplace/bundles/**``
drift glob; (3) ``scan`` converges (status ``success``, no import-fail) on a
changed set that touches ``marketplace/bundles/**`` — the removed facet no
longer fires for an ordinary bundle change.
"""

from __future__ import annotations

import importlib.util
from argparse import Namespace

import pytest
from conftest import (  # type: ignore[import-not-found]
    MARKETPLACE_ROOT,
    PlanContext,
    load_script_module,
)

# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

# Bug 1 surface: the mark-step-done command handler carrying the dirty-worktree
# guard and the MAY_MUTATE_WORKTREE_STEPS membership set.
_mark_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_mark_step.py', '_regr_mark_step_cmd'
)
_status_core = load_script_module(
    'plan-marshall', 'manage-status', '_status_core.py', '_regr_mark_step_core'
)
_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_regr_mark_step_lifecycle'
)

cmd_mark_step_done = _mark_step.cmd_mark_step_done
cmd_create = _lifecycle.cmd_create
read_status = _status_core.read_status

# Bug 2 surface: the whole-tree gate surfacer (hyphenated skill dir -> importlib).
_GATE_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
    / 'whole_tree_gate.py'
)
_spec = importlib.util.spec_from_file_location('whole_tree_gate_regr', str(_GATE_SCRIPT))
assert _spec is not None
gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gate)

# Bug 2 surface: the manifest composer carrying the trigger-glob constant.
_manifest = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    '_regr_manifest_compose',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Finalize Bug Regression',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _mark_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    *,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
    )


# ===========================================================================
# Bug 1 — simplify converges to done without a forced loop_back
# ===========================================================================


class TestSimplifyConvergesWithoutLoopBack:
    """The simplify step reaches ``done`` directly once its edits are committed.

    The fix makes ``finalize-step-simplify`` commit its own worktree edits
    before ``mark-step-done``, so the tree is clean at that point and the
    dirty-worktree guard — which would otherwise force a ``loop_back`` and, under
    ``loop_back_without_asking=false``, re-fire-and-prompt forever — is never
    reached.
    """

    def test_finalize_step_simplify_is_a_may_mutate_worktree_step(self):
        # The whole bug hinges on simplify being a may-mutate step: that is what
        # subjects its ``done`` transition to the dirty-worktree guard. If this
        # membership ever changed, the fix's rationale (commit-before-done) would
        # no longer apply — pin it.
        assert 'finalize-step-simplify' in _mark_step.MAY_MUTATE_WORKTREE_STEPS

    def test_clean_tree_done_succeeds_and_emits_no_loop_back(self, plan_context, monkeypatch):
        # Simplify has committed its edits, so the tree is CLEAN at
        # mark-step-done. Stub the porcelain probe to report clean (the fixture
        # worktree is otherwise always dirty under test).
        plan_id = 'regr-simplify-clean-done'
        _make_plan(plan_id)
        monkeypatch.setattr(_mark_step, '_worktree_is_dirty', lambda _path: False)

        # Mark the step done exactly as the fixed Step 4 does.
        result = cmd_mark_step_done(
            _mark_args(
                plan_id,
                '6-finalize',
                'finalize-step-simplify',
                'done',
                display_detail='Simplify: 2 edits, 0 findings',
                head_at_completion='a' * 40,
            )
        )

        # Convergence: the step is done, NOT refused, NOT looped back.
        assert result['status'] == 'success'
        assert result['outcome'] == 'done'
        assert result['error'] != 'dirty_worktree_done_refused' if 'error' in result else True
        assert result.get('loop_back_target') is None

        persisted = read_status(plan_id)
        entry = persisted['metadata']['phase_steps']['6-finalize']['finalize-step-simplify']
        assert entry['outcome'] == 'done'
        # No loop-back classification ever attached to the converged entry.
        assert 'loop_back_target' not in entry

    def test_uncommitted_edits_would_have_forced_loop_back(self, plan_context, monkeypatch):
        # The PRE-FIX state: simplify left edits uncommitted, so the
        # tree is dirty at mark-step-done. This test documents the symptom the
        # fix removed: with a dirty tree, the guard refuses ``done`` and steers
        # the caller to re-issue as ``loop_back`` (the re-fire/prompt thrash).
        plan_id = 'regr-simplify-dirty-refused'
        _make_plan(plan_id)
        monkeypatch.setattr(_mark_step, '_worktree_is_dirty', lambda _path: True)

        result = cmd_mark_step_done(
            _mark_args(plan_id, '6-finalize', 'finalize-step-simplify', 'done')
        )

        # The guard fires and the message names the loop_back escape, so
        # leaving edits uncommitted is exactly what re-introduces the thrash. The
        # fix avoids reaching this path by committing first (covered above).
        assert result['status'] == 'error'
        assert result['error'] == 'dirty_worktree_done_refused'
        assert 'loop_back' in result['message']

        # Persistence unchanged — the refused outcome was never written.
        persisted = read_status(plan_id)
        assert 'phase_steps' not in persisted.get('metadata', {})


# ===========================================================================
# Bug 2 — content-drift facet is gone; finalize converges
# ===========================================================================


def _make_marketplace_tree(root, files):
    """Materialize a ``{root}/marketplace`` subtree from {rel_path: content}."""
    for rel, content in files.items():
        target = root / 'marketplace' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    return root


class TestContentDriftFacetRemoved:
    """The third generator/content-drift facet and its trigger globs are gone.

    The facet's import path failed from inside a worktree, and its globs matched
    nearly every marketplace plan (including gitignored ``target/claude`` paths),
    so it blocked finalize convergence. The fix removed the facet and the trigger
    category entirely.
    """

    def test_scan_surfaces_exactly_two_facets(self, tmp_path):
        # A minimal tree; the changed set hits no facet trigger so the
        # facet block is computed but every facet is vacuously clean.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})

        with PlanContext(plan_id='regr-drift-two-facets') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            result = gate.scan(
                'regr-drift-two-facets',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [],
            )

        # Exactly the two surviving facets, no content_drift/generator.
        assert result['status'] == 'success'
        assert set(result['facets'].keys()) == {'doctor', 'sweep_test'}
        for removed in ('content_drift', 'generator', 'drift', 'generator_drift'):
            assert removed not in result['facets']

    def test_trigger_glob_constant_drops_the_drift_category(self):
        # Read the composer's single source-of-truth constant.
        globs = _manifest._WHOLE_TREE_INVARIANT_TRIGGER_GLOBS

        # Neither drift glob survives. The doctor / sweep-test globs DO
        # survive (proving the constant was trimmed, not emptied).
        assert 'marketplace/targets/**' not in globs
        assert 'marketplace/bundles/**' not in globs
        assert any('plugin-doctor' in g for g in globs)
        assert any('sweep' in g for g in globs)

    def test_bundle_source_change_no_longer_triggers_a_facet(self, tmp_path):
        # A changed set touching ONLY a bundle SKILL.md. Pre-fix this
        # path matched the ``marketplace/bundles/**`` drift glob and fired the
        # content-drift facet; post-fix it must fire NO facet, and scan must
        # converge with status success (no import-fail).
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})
        bundle_change = 'marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md'

        with PlanContext(plan_id='regr-drift-bundle-change') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # The facet seams MUST NOT run — a bundle-source change is not a
            # doctor / sweep-test trigger, and the drift facet no longer exists.
            result = gate.scan(
                'regr-drift-bundle-change',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [bundle_change],
                doctor_runner=lambda _wt: pytest.fail('doctor facet must not fire for a bundle change'),
                sweep_runner=lambda _wt: pytest.fail('sweep facet must not fire for a bundle change'),
            )

        # Convergence: success, both surviving facets untriggered/clean.
        assert result['status'] == 'success'
        assert result['facets']['doctor']['triggered'] is False
        assert result['facets']['sweep_test']['triggered'] is False
        assert result['facets']['doctor']['passed'] is True
        assert result['facets']['sweep_test']['passed'] is True

    def test_gitignored_target_claude_path_does_not_trigger_a_facet(self, tmp_path):
        # A path under the gitignored generated target tree. Pre-fix the
        # bare ``marketplace/**`` / ``marketplace/bundles/**`` drift glob shape
        # made generated-tree churn fire the facet; post-fix nothing fires.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})
        generated_change = 'target/claude/plan-marshall/skills/manage-status/SKILL.md'

        with PlanContext(plan_id='regr-drift-target-claude') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            result = gate.scan(
                'regr-drift-target-claude',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [generated_change],
                doctor_runner=lambda _wt: pytest.fail('doctor facet must not fire for target/claude churn'),
                sweep_runner=lambda _wt: pytest.fail('sweep facet must not fire for target/claude churn'),
            )

        # Convergence with no facet fired.
        assert result['status'] == 'success'
        assert result['facets']['doctor']['triggered'] is False
        assert result['facets']['sweep_test']['triggered'] is False


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
