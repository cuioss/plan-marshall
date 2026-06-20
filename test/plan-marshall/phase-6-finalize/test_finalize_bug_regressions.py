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
# Also the Bug-1 ordering surface (cmd_compose / read_manifest) used by
# TestSimplifyComposesAfterCommitPush below.
_manifest = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    '_regr_manifest_compose',
)

# Quiet the best-effort decision-log subprocess so the compose-driven ordering
# tests don't depend on a running executor (handler is already try/except wrapped).
_manifest._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


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
# Bug 1 (ordering) — finalize-step-simplify composes AFTER commit-push
# ===========================================================================


class TestSimplifyComposesAfterCommitPush:
    """The composed manifest orders ``finalize-step-simplify`` after ``commit-push``.

    The convergence fix has two co-operating halves: the per-step commit
    (covered by ``TestSimplifyConvergesWithoutLoopBack`` above) AND the
    manifest-ordering reorder that places the may-mutate ``finalize-step-simplify``
    step *after* ``commit-push`` so its edits run against a tree the commit
    already flushed clean. This class locks the ordering half from the
    regression angle: reverting the reorder (simplify back ahead of
    commit-push) re-introduces the dirty-worktree loop-back thrash and fails the
    assertion here.
    """

    @staticmethod
    def _compose_default_feature(plan_id: str) -> dict:
        # A default code-shaped feature compose: change_type=feature with files
        # present keeps both ``commit-push`` and ``finalize-step-simplify`` (the
        # simplify_inactive gate passes), so the composed ordering is exercised.
        return _manifest.cmd_compose(
            Namespace(
                plan_id=plan_id,
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=5,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(_manifest.DEFAULT_PHASE_6_STEPS),
                commit_and_push=None,
            )
        )

    def test_composed_manifest_orders_simplify_after_commit_push(self, plan_context):
        plan_id = 'regr-simplify-order-after-commit'
        result = self._compose_default_feature(plan_id)

        assert result['status'] == 'success', f'compose failed: {result!r}'
        manifest = _manifest.read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Both steps survive the default feature compose.
        assert 'commit-push' in steps
        assert 'finalize-step-simplify' in steps
        # The reorder invariant — fails if Deliverable 1 is reverted.
        assert steps.index('finalize-step-simplify') > steps.index('commit-push')

    def test_compose_reorders_simplify_ahead_of_commit_push(self, plan_context):
        # Auto-reorder: even if a candidate set re-orders simplify ahead of
        # commit-push (the reverted-reorder shape), the compose-time may-mutate
        # auto-reorder moves the offending step after commit-push and composes
        # successfully — rather than emitting an order that would loop-back at
        # finalize, or rejecting the manifest.
        plan_id = 'regr-simplify-ahead-reordered'
        result = _manifest.cmd_compose(
            Namespace(
                plan_id=plan_id,
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=5,
                phase_5_steps='quality-gate,module-tests',
                phase_6_steps=','.join(
                    ['finalize-step-simplify', 'commit-push', 'create-pr', 'lessons-capture']
                ),
                commit_and_push=None,
            )
        )

        assert result['status'] == 'success', f'expected success, got {result!r}'
        manifest = _manifest.read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # The offending may-mutate step is reordered after commit-push.
        assert steps.index('finalize-step-simplify') > steps.index('commit-push')


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


_CREATE_PR_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'create-pr.md'
)


class TestCreatePrTitleAndBodyGrounding:
    """Regression pins for the create-pr.md deterministic-title corrections.

    Before this plan, create-pr.md passed an ungrounded ``--title "{title
    from request.md}"`` placeholder (no deterministic source) and read a dead
    ``--section summary`` (request.md has no such section). These pins fail
    against the pre-fix document and pass against the post-fix one.
    """

    def test_no_residual_ungrounded_title_placeholder(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert '{title from request.md}' not in text, (
            'create-pr.md must not carry the ungrounded {title from request.md} '
            'placeholder — the title is now bound from the persisted pr_title field.'
        )

    def test_title_bound_from_persisted_pr_title(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert 'manage-status metadata --get --field pr_title' in text or (
            'metadata' in text and '--get --field pr_title' in text
        ), (
            'create-pr.md must resolve the PR title via the canonical '
            'manage-status metadata --get --field pr_title read.'
        )
        assert '--title "{pr_title}"' in text, (
            'create-pr.md must pass the grounded --title "{pr_title}" to ci pr create.'
        )

    def test_body_reads_clarified_request_not_summary(self):
        text = _CREATE_PR_DOC.read_text(encoding='utf-8')
        assert '--section clarified_request' in text, (
            'create-pr.md body generation must read --section clarified_request.'
        )
        assert '--section summary' not in text, (
            'create-pr.md must not read the dead --section summary (request.md has '
            'no Summary section).'
        )


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
