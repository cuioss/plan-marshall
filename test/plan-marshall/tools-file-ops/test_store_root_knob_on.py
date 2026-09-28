#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The orchestrator store seam with the ``orchestrator.use_worktree`` knob ON.

Covers the knob-gated root in ``tools-file-ops/file_ops.py``:
``get_orchestrator_store_root``, ``get_store_dir('orchestrator', …)`` (including
its ``allow_archived`` fallback), ``get_archived_orchestrator_dir`` and
``resolve_orchestrator_store_file``. The knob-off regression pins live in
``test_store_root.py``.

Every case runs against a real sandbox — a bare ``origin``, a main checkout, a
linked plan worktree — with no base-dir override, because an override stands
in for the main checkout and would collapse the main-anchored location the
knob-on root depends on. The knob is set by writing the MAIN checkout's
``marshal.json``; where the caller stands is selected by ``monkeypatch.chdir``.
"""

from pathlib import Path

import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, use_real_resolver, write_marshal
from file_ops import (
    OrchestratorStoreUnavailable,
    get_archived_orchestrator_dir,
    get_orchestrator_store_root,
    get_store_dir,
    resolve_orchestrator_store_file,
)

_SLUG = 'epic-alpha'
_SPEC = '.plan/orchestrator/epic-alpha/plans/PLAN-01-alpha.md'


def _sandbox(tmp_path: Path, monkeypatch, *, knob: bool):
    """Build a sandbox with the knob set to ``knob`` and the cwd on main."""
    use_real_resolver(monkeypatch)
    # PLAN_TRACKED_CONFIG_DIR outranks the cwd walk-up inside
    # get_tracked_config_dir, so an ambient value would pin the knob-off root
    # somewhere other than the sandbox's main checkout.
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
    repo = build_ledger_repo(tmp_path)
    write_marshal(repo.main, {'orchestrator': {'use_worktree': knob}})
    monkeypatch.chdir(repo.main)
    return repo


@pytest.fixture
def knob_on(tmp_path, monkeypatch):
    return _sandbox(tmp_path, monkeypatch, knob=True)


@pytest.fixture
def knob_off(tmp_path, monkeypatch):
    return _sandbox(tmp_path, monkeypatch, knob=False)


class TestKnobOnRouting:
    """Every orchestrator path resolves under the shared ledger worktree."""

    def test_store_root_is_the_shared_worktree_plan_directory(self, knob_on):
        assert get_orchestrator_store_root().resolve() == knob_on.expected_worktree / '.plan'

    def test_active_epic_resolves_under_the_shared_worktree_from_the_main_checkout(self, knob_on):
        resolved = get_store_dir('orchestrator', _SLUG)

        assert resolved.resolve() == knob_on.expected_worktree / '.plan' / 'orchestrator' / _SLUG

    def test_active_epic_resolves_to_the_same_path_from_a_plan_worktree(self, knob_on, monkeypatch):
        monkeypatch.chdir(knob_on.plan_worktree)

        resolved = get_store_dir('orchestrator', _SLUG)

        assert resolved.resolve() == knob_on.expected_worktree / '.plan' / 'orchestrator' / _SLUG

    def test_archived_home_resolves_under_the_shared_worktree_from_a_plan_worktree(self, knob_on, monkeypatch):
        monkeypatch.chdir(knob_on.plan_worktree)

        archived = get_archived_orchestrator_dir(_SLUG)

        assert archived.resolve() == knob_on.expected_worktree / '.plan' / 'archived-orchestrators' / _SLUG

    def test_allow_archived_fallback_resolves_the_archived_home_inside_the_shared_worktree(self, knob_on):
        archived = knob_on.expected_worktree / '.plan' / 'archived-orchestrators' / _SLUG
        get_orchestrator_store_root()  # first use creates the shared tree
        archived.mkdir(parents=True)

        resolved = get_store_dir('orchestrator', _SLUG, allow_archived=True)

        assert resolved.resolve() == archived

    def test_knob_off_control_resolves_on_the_current_checkout_and_creates_no_tree(self, knob_off):
        resolved = get_store_dir('orchestrator', _SLUG)

        assert resolved.resolve() == (knob_off.main / '.plan' / 'orchestrator' / _SLUG).resolve()
        assert not knob_off.expected_worktree.exists()


#: ``{case id: an entry id the seam must refuse}``.
_UNSAFE_SLUGS = {
    'parent-traversal': '..',
    'embedded-separator': 'epic/escape',
    'backslash-separator': 'epic\\escape',
    'embedded-null-byte': 'epic\x00x',
    'whitespace-only': '   ',
}


class TestUnsafeSlugIsRefusedBeforeAnyWorktreeExists:
    """Containment runs FIRST, so an unsafe slug never reaches a git side effect."""

    @pytest.mark.parametrize('slug', list(_UNSAFE_SLUGS.values()), ids=list(_UNSAFE_SLUGS))
    def test_active_resolver_refuses_without_creating_the_shared_tree(self, knob_on, slug):
        with pytest.raises(ValueError):
            get_store_dir('orchestrator', slug)

        assert not knob_on.expected_worktree.exists()

    @pytest.mark.parametrize('slug', list(_UNSAFE_SLUGS.values()), ids=list(_UNSAFE_SLUGS))
    def test_archived_resolver_refuses_without_creating_the_shared_tree(self, knob_on, slug):
        with pytest.raises(ValueError):
            get_archived_orchestrator_dir(slug)

        assert not knob_on.expected_worktree.exists()

    def test_safe_slug_control_does_create_the_shared_tree(self, knob_on):
        """Matched control: the absence asserted above is observable at all."""
        get_store_dir('orchestrator', _SLUG)

        assert knob_on.expected_worktree.is_dir()


class TestSeamRefusalPropagates:
    """A refused first use surfaces as the typed error, never as a path."""

    def _dirty_the_main_ledger(self, repo) -> str:
        relpath = '.plan/orchestrator/epic-alpha/epic.md'
        target = repo.main / relpath
        target.parent.mkdir(parents=True)
        target.write_text('# uncommitted\n', encoding='utf-8')
        return relpath

    def test_knob_on_refuses_with_the_cutover_code_naming_the_path(self, knob_on):
        relpath = self._dirty_the_main_ledger(knob_on)

        with pytest.raises(OrchestratorStoreUnavailable) as refusal:
            get_store_dir('orchestrator', _SLUG)

        assert refusal.value.code == 'ledger_cutover_refused'
        assert refusal.value.fields['dirty_paths'] == [relpath]
        assert not knob_on.expected_worktree.exists()

    def test_knob_off_control_resolves_despite_the_same_dirty_path(self, knob_off):
        self._dirty_the_main_ledger(knob_off)

        resolved = get_store_dir('orchestrator', _SLUG)

        assert resolved.resolve() == (knob_off.main / '.plan' / 'orchestrator' / _SLUG).resolve()


class TestResolveOrchestratorStoreFile:
    """Only the two ledger prefixes are rebased, and only with the knob on."""

    @pytest.mark.parametrize(
        'pointer',
        [_SPEC, '.plan/archived-orchestrators/epic-alpha/plans/PLAN-01-alpha.md'],
        ids=['active-ledger-prefix', 'archived-ledger-prefix'],
    )
    def test_knob_on_rebases_a_ledger_pointer_onto_the_shared_worktree(self, knob_on, pointer):
        resolved = resolve_orchestrator_store_file(pointer)

        assert resolved == (knob_on.expected_worktree / pointer).resolve()

    @pytest.mark.parametrize(
        'pointer',
        ['.plan/marshal.json', '.plan/orchestrator-notes/x.md', 'orchestrator/x.md', 'docs/x.md'],
        ids=['tracked-config-file', 'lookalike-prefix-component', 'missing-plan-segment', 'unrelated-file'],
    )
    def test_knob_on_leaves_every_other_relative_path_cwd_relative(self, knob_on, pointer):
        resolved = resolve_orchestrator_store_file(pointer)

        assert resolved == (knob_on.main / pointer).resolve()
        assert not knob_on.expected_worktree.exists()

    def test_knob_on_leaves_an_absolute_ledger_path_untouched(self, knob_on):
        absolute = (knob_on.main / _SPEC).resolve()

        assert resolve_orchestrator_store_file(str(absolute)) == absolute
        assert not knob_on.expected_worktree.exists()

    def test_knob_off_resolves_a_ledger_pointer_cwd_relative(self, knob_off):
        resolved = resolve_orchestrator_store_file(_SPEC)

        assert resolved == (knob_off.main / _SPEC).resolve()
        assert not knob_off.expected_worktree.exists()
