#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Resolution surface of the shared orchestrator ledger worktree substrate.

Covers the ``orchestrator.use_worktree`` knob read, the one main-anchored
``marshal.json`` it is read from, the main-anchored worktree location, the
reserved-key predicate, and the refusal type's base class. The creation
lifecycle and the drift detector live in ``test_orchestrator_worktree_create.py``.

Every repository-backed case runs on the real resolver against a real git
sandbox: the main checkout is found through ``git rev-parse --git-common-dir``
from the cwd the test chdirs into, never through a stubbed path.
"""

import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, random_plan_id, use_real_resolver, write_marshal
from input_validation import is_valid_plan_id
from marketplace_paths import ORCHESTRATOR_WORKTREE_KEY, is_orchestrator_worktree_dir
from orchestrator_worktree import (
    LEDGER_PATHSPECS,
    ORCHESTRATOR_WORKTREE_BRANCH,
    OrchestratorStoreUnavailable,
    orchestrator_knob_config_path,
    orchestrator_use_worktree,
    orchestrator_worktree_path,
)


@pytest.fixture
def ledger_repo(tmp_path, monkeypatch):
    """A real sandbox with the cwd on its main checkout and no base-dir override."""
    use_real_resolver(monkeypatch)
    repo = build_ledger_repo(tmp_path)
    monkeypatch.chdir(repo.main)
    return repo


@pytest.fixture
def outside_repository(tmp_path, monkeypatch):
    """A cwd that no git repository contains.

    ``tmp_path`` sits under the test run's base temp, which may itself live
    inside a checkout; ``GIT_CEILING_DIRECTORIES`` stops git's upward discovery
    at ``tmp_path`` so the enclosing checkout cannot answer for the sandbox.
    """
    use_real_resolver(monkeypatch)
    outside = tmp_path / 'outside'
    outside.mkdir()
    monkeypatch.setenv('GIT_CEILING_DIRECTORIES', str(tmp_path))
    monkeypatch.chdir(outside)
    return outside


def _raise_inside_a_runtime_error_handler() -> str:
    """Raise the refusal type inside the broad handler shape the store consumers carry."""
    try:
        raise OrchestratorStoreUnavailable('ledger_cutover_refused', 'refused')
    except RuntimeError:
        return 'intercepted'


class TestPublishedLiterals:
    """The branch, the reserved key and the ledger pathspecs are wire contracts."""

    def test_branch_is_the_chore_prefixed_ledger_branch(self):
        assert ORCHESTRATOR_WORKTREE_BRANCH == 'chore/orchestrator-ledger'

    def test_reserved_key_is_underscore_orchestrator(self):
        assert ORCHESTRATOR_WORKTREE_KEY == '_orchestrator'

    def test_ledger_pathspecs_name_both_store_roots(self):
        assert LEDGER_PATHSPECS == ('.plan/orchestrator', '.plan/archived-orchestrators')


class TestKnobRead:
    """``orchestrator_use_worktree`` is on only for a literal JSON ``true``."""

    def test_is_off_when_marshal_json_is_absent(self, ledger_repo):
        assert orchestrator_use_worktree() is False

    def test_is_off_when_orchestrator_section_is_absent(self, ledger_repo):
        write_marshal(ledger_repo.main, {'project': {'default_base_branch': 'main'}})

        assert orchestrator_use_worktree() is False

    def test_is_off_when_use_worktree_is_false(self, ledger_repo):
        write_marshal(ledger_repo.main, {'orchestrator': {'use_worktree': False}})

        assert orchestrator_use_worktree() is False

    def test_is_on_when_use_worktree_is_true(self, ledger_repo):
        write_marshal(ledger_repo.main, {'orchestrator': {'use_worktree': True}})

        assert orchestrator_use_worktree() is True

    @pytest.mark.parametrize(
        'value',
        ['true', 1, 'yes', None, [True], {'enabled': True}],
        ids=['string-true', 'integer-one', 'string-yes', 'null', 'list', 'mapping'],
    )
    def test_is_off_for_a_non_bool_value(self, ledger_repo, value):
        write_marshal(ledger_repo.main, {'orchestrator': {'use_worktree': value}})

        assert orchestrator_use_worktree() is False

    def test_is_off_when_orchestrator_section_is_not_a_mapping(self, ledger_repo):
        write_marshal(ledger_repo.main, {'orchestrator': True})

        assert orchestrator_use_worktree() is False

    def test_is_off_when_marshal_json_is_malformed(self, ledger_repo):
        path = write_marshal(ledger_repo.main, {})
        path.write_text('{"orchestrator": {"use_worktree": true', encoding='utf-8')

        assert orchestrator_use_worktree() is False

    def test_is_off_outside_a_repository(self, outside_repository):
        assert orchestrator_use_worktree() is False

    def test_plan_worktree_reads_the_main_checkouts_value(self, ledger_repo, monkeypatch):
        """A plan worktree reads main's knob, never its own ``marshal.json``.

        The two files disagree on purpose: a cwd-relative read would return the
        plan worktree's ``false`` and split the knob between checkouts.
        """
        write_marshal(ledger_repo.main, {'orchestrator': {'use_worktree': True}})
        write_marshal(ledger_repo.plan_worktree, {'orchestrator': {'use_worktree': False}})
        monkeypatch.chdir(ledger_repo.plan_worktree)

        assert orchestrator_use_worktree() is True


class TestKnobConfigPath:
    """``orchestrator_knob_config_path`` names the one main-anchored ``marshal.json``."""

    def test_names_mains_marshal_json_from_a_plan_worktree(self, ledger_repo, monkeypatch):
        monkeypatch.chdir(ledger_repo.plan_worktree)

        path = orchestrator_knob_config_path()

        assert path.resolve() == (ledger_repo.main / '.plan' / 'marshal.json').resolve()

    def test_names_mains_marshal_json_from_the_main_checkout(self, ledger_repo):
        path = orchestrator_knob_config_path()

        assert path.resolve() == (ledger_repo.main / '.plan' / 'marshal.json').resolve()

    def test_is_none_outside_a_repository(self, outside_repository):
        assert orchestrator_knob_config_path() is None

    def test_names_the_override_directory_while_an_override_is_active(self, outside_repository, monkeypatch, tmp_path):
        """The override stands in for main, so the knob follows it even outside a repo.

        Matched with :meth:`test_is_none_outside_a_repository`: the same cwd
        yields ``None`` without the override, so the resolved path is the
        override's doing and not a fallback.
        """
        override = tmp_path / 'override'
        monkeypatch.setenv('PLAN_BASE_DIR', str(override))

        assert orchestrator_knob_config_path() == override / 'marshal.json'


class TestWorktreePath:
    """``orchestrator_worktree_path`` is main-anchored under the worktree container."""

    def test_resolves_under_the_main_checkout_from_a_plan_worktree(self, ledger_repo, monkeypatch):
        monkeypatch.chdir(ledger_repo.plan_worktree)

        assert orchestrator_worktree_path().resolve() == ledger_repo.expected_worktree

    def test_resolves_to_the_same_location_from_the_main_checkout(self, ledger_repo):
        assert orchestrator_worktree_path().resolve() == ledger_repo.expected_worktree

    def test_is_not_nested_inside_the_plan_worktree(self, ledger_repo, monkeypatch):
        monkeypatch.chdir(ledger_repo.plan_worktree)

        path = orchestrator_worktree_path().resolve()

        assert not path.is_relative_to(ledger_repo.plan_worktree.resolve())


class TestIsOrchestratorWorktreeDir:
    """The reserved-key predicate matches the final component and nothing else.

    The plan-id-named sibling is the matched negative control for the positive
    case: both sit in the same worktree container, so the only difference the
    predicate can be answering to is the leaf name.
    """

    def test_is_true_for_the_reserved_tree(self, tmp_path):
        assert is_orchestrator_worktree_dir(tmp_path / 'worktrees' / '_orchestrator') is True

    def test_is_false_for_a_plan_id_named_sibling(self, tmp_path):
        assert is_orchestrator_worktree_dir(tmp_path / 'worktrees' / random_plan_id()) is False

    def test_accepts_a_string_path(self, tmp_path):
        assert is_orchestrator_worktree_dir(str(tmp_path / 'worktrees' / '_orchestrator')) is True

    def test_is_false_for_a_child_of_the_reserved_tree(self, tmp_path):
        assert is_orchestrator_worktree_dir(tmp_path / 'worktrees' / '_orchestrator' / '.plan') is False

    def test_is_false_for_a_near_miss_name(self, tmp_path):
        assert is_orchestrator_worktree_dir(tmp_path / 'worktrees' / 'orchestrator') is False

    def test_reserved_key_is_not_a_valid_plan_id(self):
        """No plan id can collide with the reserved key; a generated plan id is the control."""
        assert (is_valid_plan_id(ORCHESTRATOR_WORKTREE_KEY), is_valid_plan_id(random_plan_id())) == (False, True)


class TestOrchestratorStoreUnavailable:
    """The refusal type escapes every broad handler the store consumers carry."""

    @pytest.mark.parametrize('broad_base', [RuntimeError, ValueError, OSError])
    def test_is_not_an_instance_of_a_broad_handler_base(self, broad_base):
        error = OrchestratorStoreUnavailable('ledger_cutover_refused', 'refused')

        assert not isinstance(error, broad_base)

    def test_derives_from_exception_directly(self):
        assert OrchestratorStoreUnavailable.__bases__ == (Exception,)

    def test_escapes_an_except_runtime_error_handler(self):
        with pytest.raises(OrchestratorStoreUnavailable):
            _raise_inside_a_runtime_error_handler()

    def test_carries_code_message_and_fields(self):
        error = OrchestratorStoreUnavailable(
            'ledger_cutover_refused', 'two paths', dirty_paths=['.plan/orchestrator/a.md']
        )

        assert (error.code, error.message, error.fields, str(error)) == (
            'ledger_cutover_refused',
            'two paths',
            {'dirty_paths': ['.plan/orchestrator/a.md']},
            'two paths',
        )
