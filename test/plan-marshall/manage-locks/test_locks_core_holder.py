#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives."""


from __future__ import annotations

import pytest
from _locks_core_fixtures import _mod, holder_has_live_worktree, holder_is_dead, holder_staleness

# =============================================================================
# holder_is_dead — empty / malformed holder
# =============================================================================


def test_holder_is_dead_empty_string_is_dead(plan_context):
    # An empty holder is treated as dead so a corrupt lock file is reclaimable.
    assert holder_is_dead('') is True


def test_holder_is_dead_whitespace_only_is_dead(plan_context):
    # Whitespace is stripped to empty → dead.
    assert holder_is_dead('   ') is True


@pytest.mark.parametrize(
    'malicious_holder',
    [
        '../evil',
        '../../evil',
        'a/../evil',
        'sub/evil',
        'sub\\evil',
        '..',
        'foo\x00bar',
    ],
)
def test_holder_is_dead_rejects_traversal_holder(plan_context, malicious_holder):
    # holder is a plan-id joined DIRECTLY onto the anchored .plan/local base to
    # build the main-checkout (main_plan) and worktree (worktree_plan) plan-dir
    # paths. A holder bearing a path separator, a `..` parent segment, or an
    # embedded NUL must be classified dead (True) BEFORE the path is constructed
    # — otherwise a crafted holder could escape the base, resolve to an unrelated
    # existing dir, report a truly-dead holder "alive", and permanently block
    # lock reclamation (a DoS). Inverse polarity to the sibling
    # holder_has_live_worktree guard (which returns False for the same corpus).
    assert holder_is_dead(malicious_holder) is True


def test_holder_is_dead_traversal_does_not_escape_base(plan_context):
    # Concrete escape scenario: `../evil` would resolve `plans/../evil` to a
    # sibling dir of the plans root (i.e. base/evil). Stage that sibling so,
    # absent the guard, main_plan.exists() would be True and the predicate would
    # report the holder "alive" (False). The guard must reject the traversal and
    # return True (dead) rather than resolving the escaped path.
    base = plan_context.fixture_dir
    (base / 'evil').mkdir(parents=True, exist_ok=True)  # plans/../evil target

    assert holder_is_dead('../evil') is True


# =============================================================================
# holder_is_dead — liveness via main checkout
# =============================================================================


def test_holder_is_dead_false_when_main_plan_dir_exists(plan_context):
    # A holder whose plan dir lives on main (phases 1-4 / post-finalize) is alive.
    plan_context.plan_dir_for('lc-alive-main')

    assert holder_is_dead('lc-alive-main') is False


# =============================================================================
# holder_is_dead — liveness via the holder's worktree
# =============================================================================


def test_holder_is_dead_false_when_worktree_plan_dir_exists(plan_context):
    # While executing, the plan dir is MOVED into the worktree and does NOT
    # exist on main. Checking only main would wrongly declare the holder dead;
    # the worktree-resident path must keep it alive.
    base = plan_context.fixture_dir
    worktree_plan = base / 'worktrees' / 'lc-alive-wt' / '.plan' / 'local' / 'plans' / 'lc-alive-wt'
    worktree_plan.mkdir(parents=True, exist_ok=True)

    assert holder_is_dead('lc-alive-wt') is False


def test_holder_is_dead_true_when_neither_path_exists(plan_context):
    # No main plan dir and no worktree plan dir → the holder is dead.
    assert holder_is_dead('lc-no-such-holder') is True


# =============================================================================
# holder_is_dead — project-qualified liveness (project_root=, machine-global lock)
# =============================================================================
#
# When a lock file is shared across repos (the machine-global lock anchor), a
# recorded holder may live in a DIFFERENT project's checkout. The acquirer must
# judge that holder's liveness against ITS project (project_root=<A>), not the
# acquirer's own checkout — otherwise a foreign LIVE holder is wrongly reclaimed.


def test_holder_is_dead_foreign_live_holder_not_reclaimed_with_project_root(tmp_path, monkeypatch):
    # A holder whose live plan dir exists under project A's checkout must NOT be
    # declared dead when checked with project_root=<A> from a session whose own
    # checkout is project B (where the holder is absent). Caller-anchored
    # (project_root=None) resolution against B still reports it dead.
    holder = 'foreign-live-holder'
    project_a = tmp_path / 'project-a'
    (project_a / '.plan' / 'local' / 'plans' / holder).mkdir(parents=True)

    # The session's own checkout is B — anchor project_root=None resolution there.
    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))

    # Caller-anchored (default) sees B, where the holder is absent → dead.
    assert holder_is_dead(holder) is True
    # Project-qualified against A sees A's live plan dir → NOT dead.
    assert holder_is_dead(holder, project_root=project_a) is False


def test_holder_is_dead_project_root_consults_worktree_plan_dir(tmp_path, monkeypatch):
    # The project-qualified base consults BOTH liveness paths. Here the holder's
    # plan dir lives in its WORKTREE under project A (moved-in mid-execute), not
    # A's main checkout — project_root=<A> must still judge it alive.
    holder = 'foreign-wt-holder'
    project_a = tmp_path / 'project-a'
    wt_plan = project_a / '.plan' / 'local' / 'worktrees' / holder / '.plan' / 'local' / 'plans' / holder
    wt_plan.mkdir(parents=True)

    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))

    assert holder_is_dead(holder, project_root=project_a) is False
    assert holder_is_dead(holder) is True  # caller-anchored at B → dead


def test_holder_is_dead_project_root_dead_when_absent_in_that_project(tmp_path, monkeypatch):
    # project_root does not blanket a holder alive — a holder absent from project
    # A's checkout is still dead when judged against A.
    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))
    project_a = tmp_path / 'project-a'
    project_a.mkdir(parents=True)

    assert holder_is_dead('absent-holder', project_root=project_a) is True


# =============================================================================
# holder_has_live_worktree — genuine live/mid-recovery worktree marker (D3, strengthened)
# =============================================================================
#
# A STRONGER presence signal than holder_is_dead: it does NOT trust the bare
# existence of the worktree DIRECTORY. It returns True ONLY for a genuine
# live/mid-recovery worktree carrying a concrete marker under worktrees/{holder} —
# EITHER a git-worktree gitdir link (a `.git` file or dir at the worktree root) OR
# a live plan dir (worktrees/{holder}/.plan/local/plans/{holder}) — and False for
# an orphaned empty shell carrying neither. The merge_lock acquire path gates the
# automatic stale-reclaim on this being False, so an orphaned shell now permits
# auto-reclaim while a genuine mid-recovery holder stays protected.


def test_holder_has_live_worktree_false_when_worktree_dir_is_bare_shell(plan_context):
    # A bare, empty worktree directory carrying NO git-worktree marker and NO live
    # plan dir is an orphaned shell — under the strengthened contract it must NOT
    # count as live (previously a bare dir.exists() wrongly reported True and
    # permanently blocked the merge-lock auto-reclaim).
    base = plan_context.fixture_dir
    (base / 'worktrees' / 'lc-bare-shell').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-bare-shell') is False


def test_holder_has_live_worktree_false_when_orphaned_empty_shell(plan_context):
    # An orphaned empty shell (the worktree root plus a stray leftover sub-dir, but
    # neither a `.git` marker nor a live plan dir) → False. This is the exact class
    # both observed incidents (a never-persisted plan; a post-migration stranded
    # holder) left on disk.
    base = plan_context.fixture_dir
    shell = base / 'worktrees' / 'lc-orphan-shell'
    (shell / 'some' / 'leftover').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-orphan-shell') is False


def test_holder_has_live_worktree_true_when_git_worktree_marker_present(plan_context):
    # A `.git` marker file at the worktree root is the git-worktree gitdir link —
    # its presence means the worktree's git plumbing is still wired up, so the
    # holder is a genuine (possibly mid-recovery) worktree → True.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-git-marker'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-git-marker\n', encoding='utf-8'
    )

    assert holder_has_live_worktree('lc-git-marker') is True


def test_holder_has_live_worktree_true_when_git_marker_is_directory(plan_context):
    # The `.git` marker may also be a directory (a non-linked worktree layout);
    # either shape counts as live git plumbing → True.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-git-marker-dir'
    (worktree / '.git').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-git-marker-dir') is True


def test_holder_has_live_worktree_true_when_live_plan_dir_present(plan_context):
    # A live plan dir moved into the worktree
    # (worktrees/{holder}/.plan/local/plans/{holder}) — present while the plan is
    # executing or mid-finalize — is the second live-worktree marker → True, even
    # with no `.git` marker staged.
    base = plan_context.fixture_dir
    live_plan = (
        base / 'worktrees' / 'lc-live-plan' / '.plan' / 'local' / 'plans' / 'lc-live-plan'
    )
    live_plan.mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-live-plan') is True


def test_holder_has_live_worktree_false_when_worktree_dir_absent(plan_context):
    # No worktree directory on disk → False.
    assert holder_has_live_worktree('lc-no-worktree-dir') is False


def test_holder_has_live_worktree_empty_string_is_false(plan_context):
    # An empty holder has no worktree → False (distinct from holder_is_dead('')
    # which is True — the two predicates answer different questions).
    assert holder_has_live_worktree('') is False


def test_holder_has_live_worktree_whitespace_only_is_false(plan_context):
    # Whitespace is stripped to empty → no worktree → False.
    assert holder_has_live_worktree('   ') is False


@pytest.mark.parametrize(
    'malicious_holder',
    [
        '../evil',
        '../../evil',
        'a/../evil',
        'sub/evil',
        'sub\\evil',
        '..',
        'foo\x00bar',
    ],
)
def test_holder_has_live_worktree_rejects_traversal_holder(plan_context, malicious_holder):
    # holder is a plan-id joined DIRECTLY onto the worktrees root to build a
    # filesystem path. A holder bearing a path separator, a `..` parent segment,
    # or an embedded NUL must be rejected as having no live worktree BEFORE the
    # path is constructed — otherwise a crafted holder could escape the worktrees
    # root, resolve to an unrelated existing dir, and permanently block lock
    # reclamation (a DoS).
    assert holder_has_live_worktree(malicious_holder) is False


def test_holder_has_live_worktree_traversal_does_not_escape_worktrees_root(plan_context):
    # Concrete escape scenario: `../evil` would resolve `worktrees/../evil` to a
    # sibling dir of the worktrees root. Stage that sibling so, absent the guard,
    # the predicate would report the holder "alive". The guard must reject the
    # traversal and return False rather than resolving the escaped path.
    base = plan_context.fixture_dir
    (base / 'evil').mkdir(parents=True, exist_ok=True)  # worktrees/../evil target

    assert holder_has_live_worktree('../evil') is False


# =============================================================================
# holder_staleness — main-anchored three-valued verdict (D1)
# =============================================================================
#
# holder_staleness composes the two main-anchored predicates into a fresh / stale
# / unknown verdict, consulting ONLY main-anchored paths — never a cwd-scoped
# plan/worktree enumeration. It is the guard the manual-release recovery path
# lacked (the #948 sibling-worktree misjudgement). fresh = alive or mid-recovery;
# stale = main-anchored-dead AND no live worktree; unknown = the main-anchored
# .plan/local base could not be resolved (ADR-009: evidence-absent is surfaced
# explicitly, NEVER collapsed into stale).


def test_holder_staleness_fresh_when_alive_on_main(plan_context):
    # A holder whose plan dir lives on main (phases 1-4 / post-finalize) is alive
    # → fresh (must NOT be force-released).
    plan_context.plan_dir_for('lc-fresh-main')

    assert holder_staleness('lc-fresh-main') == 'fresh'


def test_holder_staleness_fresh_when_alive_in_worktree(plan_context):
    # While executing, the plan dir is MOVED into the worktree (absent on main).
    # The worktree-resident plan dir keeps the holder alive → fresh. This is the
    # exact #948 shape: a holder live in a (sibling) worktree is never stale.
    base = plan_context.fixture_dir
    wt_plan = base / 'worktrees' / 'lc-fresh-wt' / '.plan' / 'local' / 'plans' / 'lc-fresh-wt'
    wt_plan.mkdir(parents=True, exist_ok=True)

    assert holder_staleness('lc-fresh-wt') == 'fresh'


def test_holder_staleness_fresh_when_mid_recovery_live_worktree(plan_context):
    # dead-by-plan-dir (plan dir absent on main AND in the worktree's .plan) BUT a
    # genuine git-worktree marker is present → mid-recovery → fresh. An interrupted
    # finalize move-back must never be force-released.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-midrec'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-midrec\n', encoding='utf-8'
    )

    # Precondition: dead by plan-dir absence, yet a live worktree marker exists.
    assert holder_is_dead('lc-midrec') is True
    assert holder_has_live_worktree('lc-midrec') is True
    # Composed verdict: the live worktree wins → fresh.
    assert holder_staleness('lc-midrec') == 'fresh'


def test_holder_staleness_stale_when_dead_and_no_worktree(plan_context):
    # No plan dir on main, no plan dir in a worktree, no live worktree marker →
    # the holder is provably dead → stale (the only force-releasable verdict).
    assert holder_staleness('lc-genuinely-dead') == 'stale'


def test_holder_staleness_stale_for_empty_holder(plan_context):
    # An empty/corrupt holder is dead-by-shape with no worktree → stale, mirroring
    # holder_is_dead('') is True (the corrupt-lock-file-reclaimable intent).
    assert holder_staleness('') == 'stale'


def test_holder_staleness_unknown_when_base_unresolvable(plan_context, monkeypatch):
    # When the main-anchored .plan/local base cannot be resolved, the underlying
    # liveness predicate raises RuntimeError (a real resolution failure, propagated
    # loudly). holder_staleness converts THAT — and only that — into the explicit
    # 'unknown' verdict, NEVER swallowing a resolution failure as 'stale' (ADR-009:
    # absence of evidence fails closed, it is not proof of death).
    def _boom():
        raise RuntimeError('main-anchored base unresolvable')

    monkeypatch.setattr(_mod, '_main_plan_local_base', _boom)

    assert holder_staleness('lc-any-holder') == 'unknown'
