#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the store-root abstraction in tools-file-ops/file_ops.py (D0).

Covers get_store_dir(store, entry_id):
- 'plans' store round-trips through base_path / get_plan_dir (byte-identical).
- 'orchestrator' store composes onto the git-tracked, cwd-relative config tier
  (get_tracked_config_dir), honouring the PLAN_BASE_DIR test override.
- Unknown store values raise ValueError.
- Real-resolver E2E leg: the orchestrator store resolves under the CWD
  checkout's ``.plan/`` — not the main checkout — with no mocking of the git
  or walk-up resolution.

⛔ An override-based fixture CANNOT detect the tracked-tier move. Under
``PLAN_BASE_DIR`` both ``get_tracked_config_dir`` and
``resolve_main_anchored_path`` short-circuit to that same directory, so the
old and new resolutions are byte-identical there. The override tests are kept
as the deliberate POSITIVE CONTROL (they prove the existing fixtures were
preserved on purpose), and :class:`TestRealResolverE2E` carries the
discriminating coverage.
"""

import subprocess
import uuid
from pathlib import Path

import file_ops
import pytest
from file_ops import base_path, get_archived_orchestrator_dir, get_plan_dir, get_store_dir
from marketplace_paths import resolve_main_anchored_path


def _random_id(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


class TestPlansStore:
    """The 'plans' store routes through the existing cwd-relative base_path."""

    def test_should_equal_get_plan_dir_for_any_plan_id(self):
        plan_id = _random_id('plan')

        store_root = get_store_dir('plans', plan_id)

        assert store_root == get_plan_dir(plan_id)

    def test_should_equal_base_path_plans_for_any_plan_id(self):
        plan_id = _random_id('plan')

        store_root = get_store_dir('plans', plan_id)

        assert store_root == base_path('plans', plan_id)

    def test_should_resolve_under_plan_base_dir_override(self, monkeypatch, tmp_path):
        plan_id = _random_id('plan')
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        store_root = get_store_dir('plans', plan_id)

        assert store_root == tmp_path / 'plans' / plan_id


class TestOrchestratorStore:
    """The 'orchestrator' store composes onto the tracked config tier.

    These two override cases are RETAINED DELIBERATELY as the positive control
    for the tracked-tier move, not merely as legacy coverage: they pass
    identically before and after it, which is precisely the property that makes
    them unable to detect it. See :class:`TestTrackedTierIsNotMainAnchored` for
    the matched pair that pins both halves of that reasoning.
    """

    def test_should_honour_plan_base_dir_override(self, monkeypatch, tmp_path):
        epic_id = _random_id('epic')
        # Newly load-bearing: the store now reads get_tracked_config_dir, whose
        # precedence puts PLAN_TRACKED_CONFIG_DIR ABOVE PLAN_BASE_DIR. The old
        # resolver never consulted it, so this clear is part of the tier move
        # rather than pre-existing hygiene.
        monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        store_root = get_store_dir('orchestrator', epic_id)

        assert store_root == tmp_path / f'orchestrator/{epic_id}'

    def test_should_honour_set_base_dir_override(self, monkeypatch, tmp_path):
        epic_id = _random_id('epic')
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', tmp_path)

        store_root = get_store_dir('orchestrator', epic_id)

        assert store_root == tmp_path / f'orchestrator/{epic_id}'


#: ``{the id naming the case: the rejected store value}``. Two of these rows are
#: unreadable as pytest names them: the empty string renders as nothing at all,
#: and the trailing space on ``'orchestrator '`` is invisible in a report — so
#: those two rows, whose whole distinction is a character a report swallows, are
#: exactly the ones the generated ids cannot show. The ids are therefore stated,
#: and drawn from this mapping's own keys so a reorder carries each name along
#: with its value.
_UNKNOWN_STORE_VALUES = {
    'an-unregistered-store-name-archive': 'archive',
    'an-unregistered-store-name-lessons': 'lessons',
    'the-empty-string': '',
    'a-registered-name-in-the-wrong-case': 'PLANS',
    'a-registered-name-with-trailing-whitespace': 'orchestrator ',
}


class TestUnknownStore:
    """Unknown store values are rejected via ValueError."""

    @pytest.mark.parametrize(
        'store',
        list(_UNKNOWN_STORE_VALUES.values()),
        ids=list(_UNKNOWN_STORE_VALUES),
    )
    def test_should_raise_value_error_for_unknown_store(self, store):
        with pytest.raises(ValueError) as exc_info:
            get_store_dir(store, _random_id('entry'))

        assert repr(store) in str(exc_info.value)


def _git(*args: str, cwd: Path) -> None:
    # Test-controlled fixture helper: args are hardcoded test literals plus
    # caller-supplied git subcommands, never externally-sourced input; 'git'
    # is resolved via PATH intentionally so the fixture works across CI
    # runners without hardcoding an absolute git path.
    subprocess.run(  # argv-list call, never a shell string; see the note above for the PATH decision
        [
            'git',
            '-c',
            'user.name=store-root-test',
            '-c',
            'user.email=test@example.com',
            *args,
        ],  # 'git' is resolved via PATH on purpose so the fixture works on any CI runner
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def linked_worktree_repo(tmp_path):
    """A real git repo with a linked worktree — no mocking of git resolution.

    BOTH trees are given their own ``.plan/local``, and that is load-bearing
    rather than incidental setup. The tracked tier resolves through
    ``_find_plan_root_from_cwd``, a walk-up that stops at the nearest
    ``.plan/local`` ancestor. Without one inside the fixture the walk-up climbs
    straight past ``tmp_path`` — which pytest roots under the repository's own
    ``--basetemp`` — and lands on the REAL repository's ``.plan/local``. Every
    assertion below would then describe the developer's checkout instead of the
    fixture, passing or failing for reasons the test never states.

    Giving the worktree one also makes it a genuine discriminator: the walk-up
    stops there while ``git rev-parse --git-common-dir`` still resolves the main
    checkout, so the two tiers name different directories.
    """
    main_repo = tmp_path / 'main-repo'
    main_repo.mkdir()
    _git('init', '--initial-branch=main', cwd=main_repo)
    _git('commit', '--allow-empty', '-m', 'init', cwd=main_repo)
    worktree = tmp_path / 'linked-worktree'
    _git('worktree', 'add', '-b', 'feature/store-root', str(worktree), cwd=main_repo)
    (main_repo / '.plan' / 'local').mkdir(parents=True)
    (worktree / '.plan' / 'local').mkdir(parents=True)
    return main_repo, worktree


@pytest.fixture()
def no_plan_base_dir(monkeypatch):
    """Clear PLAN_BASE_DIR so resolution falls through to its next source."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)


@pytest.fixture()
def no_base_dir_override(monkeypatch):
    """Clear the in-process base-directory override."""
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)


@pytest.fixture()
def no_tracked_config_override(monkeypatch):
    """Clear PLAN_TRACKED_CONFIG_DIR.

    It outranks PLAN_BASE_DIR inside ``get_tracked_config_dir``, so leaving it
    set would pin the tracked tier to some other directory and make the
    real-resolver assertions below describe that pin rather than the walk-up.
    """
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)


#: The fixtures that together put resolution on the REAL (unoverridden) path.
_REAL_RESOLVER = pytest.mark.usefixtures(
    'no_base_dir_override',
    'no_plan_base_dir',
    'no_tracked_config_override',
)


@_REAL_RESOLVER
class TestRealResolverE2E:
    """Real-resolver E2E leg: cwd-relative tracked-tier resolution, no mocking.

    The orchestrator store is git-tracked, repo-local state, so it resolves
    under the ``.plan/`` of whichever checkout the working directory is in —
    the worktree during phase-5+, main otherwise. This is the leg that can
    actually observe the tier move; the override cases cannot (module
    docstring).
    """

    def test_should_resolve_orchestrator_store_under_worktree_tracked_dir(self, monkeypatch, linked_worktree_repo):
        _main_repo, worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.chdir(worktree)

        store_root = get_store_dir('orchestrator', epic_id)

        expected = (worktree / '.plan' / 'orchestrator' / epic_id).resolve()
        assert store_root.resolve() == expected

    def test_should_resolve_orchestrator_store_under_main_tracked_dir_from_main_cwd(
        self, monkeypatch, linked_worktree_repo
    ):
        main_repo, _worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.chdir(main_repo)

        store_root = get_store_dir('orchestrator', epic_id)

        expected = (main_repo / '.plan' / 'orchestrator' / epic_id).resolve()
        assert store_root.resolve() == expected

    def test_should_support_real_directory_creation_under_resolved_root(self, monkeypatch, linked_worktree_repo):
        _main_repo, worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.chdir(worktree)

        store_root = get_store_dir('orchestrator', epic_id)
        store_root.mkdir(parents=True, exist_ok=False)

        created = worktree / '.plan' / 'orchestrator' / epic_id
        assert created.is_dir()

    def test_should_resolve_archived_dir_under_the_same_tracked_tier(self, monkeypatch, linked_worktree_repo):
        # One epic's active and archived homes must sit in ONE storage tier, or
        # `allow_archived` would resolve a single slug across two of them.
        _main_repo, worktree = linked_worktree_repo
        slug = _random_id('epic')
        monkeypatch.chdir(worktree)

        archived = get_archived_orchestrator_dir(slug)

        assert archived.resolve() == (worktree / '.plan' / 'archived-orchestrators' / slug).resolve()


@_REAL_RESOLVER
class TestTrackedTierIsNotMainAnchored:
    """The discriminator: on the real resolver the two tiers DISAGREE.

    This is the assertion an override-based fixture structurally cannot make.
    It is stated as a matched pair with
    :meth:`test_override_collapses_both_tiers_onto_one_directory` below, so the
    record carries both halves: where the two tiers differ, and where they
    coincide (and therefore why the retained override tests prove nothing about
    this change).
    """

    def test_orchestrator_store_differs_from_the_main_anchored_path(self, monkeypatch, linked_worktree_repo):
        main_repo, worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.chdir(worktree)

        store_root = get_store_dir('orchestrator', epic_id).resolve()
        main_anchored = resolve_main_anchored_path(f'orchestrator/{epic_id}').resolve()

        assert store_root != main_anchored
        # Both sides are pinned, so a future regression cannot satisfy the
        # inequality by moving the WRONG one.
        assert store_root == (worktree / '.plan' / 'orchestrator' / epic_id).resolve()
        assert main_anchored == (main_repo / '.plan' / 'local' / 'orchestrator' / epic_id).resolve()


class TestOverridePositiveControl:
    """Why the retained override tests cannot detect the tracked-tier move."""

    def test_override_collapses_both_tiers_onto_one_directory(self, monkeypatch, tmp_path):
        # get_tracked_config_dir and resolve_main_anchored_path BOTH
        # short-circuit on PLAN_BASE_DIR, so under an override the pre- and
        # post-change resolutions are byte-identical. Pinning that equality is
        # what makes the retained override coverage a deliberate control rather
        # than an oversight.
        epic_id = _random_id('epic')
        # PLAN_TRACKED_CONFIG_DIR outranks PLAN_BASE_DIR inside
        # get_tracked_config_dir, so an ambient value would pin one side of the
        # equality somewhere else and the collapse being asserted would not be
        # the one under test.
        monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        assert get_store_dir('orchestrator', epic_id) == resolve_main_anchored_path(f'orchestrator/{epic_id}')


class TestAllowArchivedFallback:
    """``allow_archived`` read-fallback — unchanged in intent by the tier move.

    Four cases, because the flag has two inputs (does the active path exist,
    does the archived one) and the default must be pinned separately from the
    opt-in.
    """

    @pytest.fixture()
    def override_root(self, monkeypatch, tmp_path):
        # Both the active and the archived resolver now read
        # get_tracked_config_dir, where PLAN_TRACKED_CONFIG_DIR OUTRANKS
        # PLAN_BASE_DIR — an ambient value would send the archived half of every
        # pair below to a different tree than the active half.
        monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        return tmp_path

    def test_resolves_archived_when_only_archived_exists(self, override_root):
        slug = _random_id('epic')
        archived = get_archived_orchestrator_dir(slug)
        archived.mkdir(parents=True)

        assert get_store_dir('orchestrator', slug, allow_archived=True) == archived

    def test_returns_active_path_when_neither_exists(self, override_root):
        # A genuine not-found still names the canonical ACTIVE location.
        slug = _random_id('epic')

        resolved = get_store_dir('orchestrator', slug, allow_archived=True)

        assert resolved == override_root / 'orchestrator' / slug
        assert not resolved.exists()

    def test_prefers_active_when_both_exist(self, override_root):
        slug = _random_id('epic')
        active = override_root / 'orchestrator' / slug
        active.mkdir(parents=True)
        get_archived_orchestrator_dir(slug).mkdir(parents=True)

        assert get_store_dir('orchestrator', slug, allow_archived=True) == active

    def test_default_never_falls_back_to_archived(self, override_root):
        # An archived epic is the frozen audit record; a write/scaffold caller
        # must not be handed it just because the active path is absent.
        slug = _random_id('epic')
        get_archived_orchestrator_dir(slug).mkdir(parents=True)

        assert get_store_dir('orchestrator', slug) == override_root / 'orchestrator' / slug
