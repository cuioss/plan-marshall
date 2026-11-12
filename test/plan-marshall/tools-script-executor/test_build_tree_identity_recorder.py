#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The build-ledger recorder hashes the tree the freshness gate will hash.

The executor stamps each `kind=build` row at its dispatch boundary. It used to
hash whatever directory the process happened to be in (`os.getcwd()`), while the
gate hashes the plan's resolved worktree root — so a build dispatched from the
main checkout with `--plan-dir {worktree}` recorded the wrong tree, and re-running
it the same way could never clear the gate. These cases pin the fix:

* the row is hashed against the plan's worktree root, resolved through the same
  shared plan-context resolver the gate uses;
* the row NAMES the root it hashed, so the two readings can be compared;
* a plan-less dispatch keeps the working directory, and a dispatch whose working
  directory already IS the worktree root records the same hash as before;
* a root that will not resolve records no hash at all — an unmatched row is the
  fail-closed answer;
* the row carries the tree hash captured at dispatch beside the completion hash,
  so a build that changed the tree under itself is visible; and
* the last case is the round trip the whole change exists for: a build dispatched
  from the MAIN CHECKOUT with a plan's `--plan-id` is read as FRESH by the gate
  against that plan's worktree — with two real git trees whose content differs,
  so a cwd-based hash cannot pass by coincidence.
"""

from __future__ import annotations

import subprocess
import types
from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck
import pytest
from _executor_template_render import TEMPLATE_PATH, render_executor_template
from _ledger_core import read_entries
from _resolve_project_dir_fixtures import patch_query_worktree_path
from marketplace_paths import NO_PLAN_SENTINEL
from worktree_sha import compute_worktree_sha

from conftest import load_script_module

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

_PLAN_ID = 'lb-146-tree-identity'


def _load_template_module() -> types.ModuleType:
    """Render the executor template with inert placeholders and exec it as a module.

    Mirrors the loader the executor's own boundary tests use: every ``{{...}}``
    token takes an inert stand-in, and the template's shared imports
    (``_ledger_core`` / ``worktree_sha`` / ``file_ops`` / ``plan_logging``)
    resolve because the root conftest put every marketplace script dir on
    ``sys.path``. ``main()`` is guarded by ``__name__ == '__main__'``, so exec
    dispatches nothing.
    """
    source = render_executor_template(generated_version='', mappings_fingerprint='')

    module = types.ModuleType('executor_template_tree_identity')
    module.__dict__['__file__'] = str(TEMPLATE_PATH)
    exec(compile(source, str(TEMPLATE_PATH), 'exec'), module.__dict__)
    return module


def _git(repo: Path, *args: str) -> None:
    """Run a git command in ``repo``, raising on failure."""
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path, *, tracked: str, content: str) -> Path:
    """Initialise a real git repo with one committed file of ``content``."""
    repo.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / tracked).write_text(content, encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')
    return repo


def _redirect_ledger(module: types.ModuleType, monkeypatch, ledger_path: Path) -> None:
    """Point the boundary writer at ``ledger_path``."""
    import _ledger_core

    real_append = _ledger_core.append_entry
    monkeypatch.setattr(module, 'append_entry', lambda record: real_append(record, path=ledger_path))


def _record(module: types.ModuleType, *, plan_id: str, dispatch_tree_state=None) -> None:
    """Append one SUCCESSFUL build row through the template's own boundary writer.

    ``stdout`` is a real TOON payload because the boundary derives the row's
    ``status`` from it: an empty payload stamps ``unknown``, which is
    deliberately not a green the freshness gate accepts.
    """
    extra = {} if dispatch_tree_state is None else {'dispatch_tree_state': dispatch_tree_state}
    module._append_build_ledger_record(
        notation=_NOTATION,
        plan_id=plan_id,
        script_args=['run'],
        exit_code=0,
        stdout='status: success\n',
        log_file=None,
        **extra,
    )


def _raise_oserror(_root) -> None:
    """A ``compute_worktree_sha`` stand-in that fails the way a shell-out can."""
    raise OSError('boom')


@pytest.fixture()
def main_checkout(tmp_path) -> Path:
    """The tree a build is dispatched FROM when the caller forgets to cd."""
    return _init_repo(tmp_path / 'main-checkout', tracked='main.py', content='main checkout content\n')


@pytest.fixture()
def worktree(tmp_path) -> Path:
    """The plan's worktree — different content, so its currency hash differs."""
    return _init_repo(tmp_path / 'plan-worktree', tracked='plan.py', content='plan worktree content\n')


@pytest.fixture()
def ledger_path(tmp_path: Path) -> Path:
    return tmp_path / 'change-ledger.jsonl'


# =============================================================================
# The root the row is hashed against
# =============================================================================


def test_the_row_is_hashed_against_the_plans_worktree_root(main_checkout, worktree, ledger_path, monkeypatch) -> None:
    """Dispatched from the main checkout, the row describes the WORKTREE."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    with patch_query_worktree_path(True, str(worktree)):
        _record(module, plan_id=_PLAN_ID)

    entries = read_entries(path=ledger_path)
    assert len(entries) == 1
    entry = entries[0]
    assert Path(entry['worktree_root']).resolve() == worktree.resolve()
    assert entry['worktree_sha'] == compute_worktree_sha(worktree)
    assert entry['worktree_sha'] != compute_worktree_sha(main_checkout), (
        'the row was hashed against the working directory — the wrong-tree defect itself'
    )


def test_a_dispatch_from_the_worktree_records_the_same_hash(monkeypatch, worktree, ledger_path) -> None:
    """CONTROL: when cwd already is the worktree root, nothing changes."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(worktree)

    with patch_query_worktree_path(True, str(worktree)):
        _record(module, plan_id=_PLAN_ID)

    entry = read_entries(path=ledger_path)[0]
    assert entry['worktree_sha'] == compute_worktree_sha(worktree)
    assert entry['worktree_sha'] == compute_worktree_sha(Path.cwd())


def test_a_plan_less_dispatch_records_the_working_directory(monkeypatch, main_checkout, worktree, ledger_path) -> None:
    """A plan-less build is a build of the tree it was dispatched from."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    with patch_query_worktree_path(True, str(worktree)):
        _record(module, plan_id=NO_PLAN_SENTINEL)

    entry = read_entries(path=ledger_path)[0]
    assert Path(entry['worktree_root']).resolve() == main_checkout.resolve()
    assert entry['worktree_sha'] == compute_worktree_sha(main_checkout)


def test_a_plan_less_dispatch_hashes_the_working_directory(monkeypatch, main_checkout, ledger_path) -> None:
    """CONTROL: a plan-less build keeps hashing the tree it was dispatched from."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    _record(module, plan_id=NO_PLAN_SENTINEL)

    entry = read_entries(path=ledger_path)[0]
    assert entry['worktree_sha'] == compute_worktree_sha(main_checkout)


def test_an_unresolvable_root_records_no_hash(monkeypatch, main_checkout, ledger_path) -> None:
    """A root nobody can resolve records nothing rather than a guessed tree."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    def _raise(_plan_id):
        raise RuntimeError('deliberately unresolvable')

    monkeypatch.setattr(module, 'resolve_plan_context', _raise)

    _record(module, plan_id=_PLAN_ID)

    entry = read_entries(path=ledger_path)[0]
    assert entry['worktree_root'] is None
    assert entry['worktree_sha'] is None, 'a hash of some other tree would read as a match for it'


# =============================================================================
# The two hashes
# =============================================================================


def test_the_row_records_both_hashes(monkeypatch, main_checkout, worktree, ledger_path) -> None:
    """The dispatch capture and the completion capture are both recorded."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    dispatch_sha = 'd' * 64
    with patch_query_worktree_path(True, str(worktree)):
        _record(module, plan_id=_PLAN_ID, dispatch_tree_state=(str(worktree), dispatch_sha))

    entry = read_entries(path=ledger_path)[0]
    assert entry['worktree_sha_at_dispatch'] == dispatch_sha
    assert entry['worktree_sha'] == compute_worktree_sha(worktree)
    assert entry['worktree_sha'] != entry['worktree_sha_at_dispatch'], (
        'both hashes must be recorded from their own capture, not one stamped twice'
    )


#: A build child that edits a tracked file while it runs — the "file edited
#: during the build" shape, driven through the executor's own ``main()``.
_EDITING_BUILD = """
import os
from pathlib import Path

target = Path(os.environ['PM_TEST_EDIT_FILE'])
target.write_text(target.read_text(encoding='utf-8') + 'edited during the build\\n', encoding='utf-8')
print('status: success')
"""


def test_main_captures_the_tree_before_the_build_edits_it(worktree, ledger_path, tmp_path, monkeypatch) -> None:
    """The dispatch capture is a PRE-BUILD observation of the plan's tree.

    Drives the executor's own ``main()``: the build child edits a tracked file
    while it runs, so the row must carry two DIFFERING hashes. A capture taken
    after the subprocess — or a row that never receives the captured value —
    would fold the edit into one green, which is the false-fresh this whole
    change exists to remove.
    """
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    editing_build = tmp_path / 'editing_build.py'
    editing_build.write_text(_EDITING_BUILD, encoding='utf-8')
    monkeypatch.setenv('PM_TEST_EDIT_FILE', str(worktree / 'plan.py'))
    monkeypatch.setattr(module, 'resolve_notation', lambda _notation: str(editing_build))
    monkeypatch.setattr(module.sys, 'argv', ['execute-script.py', _NOTATION, 'run', '--plan-id', _PLAN_ID])

    with patch_query_worktree_path(True, str(worktree)), pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 0
    entry = read_entries(path=ledger_path)[0]
    assert Path(entry['worktree_root']).resolve() == worktree.resolve()
    assert entry['worktree_sha_at_dispatch'] is not None, 'main() did not pass a dispatch capture to the writer'
    assert entry['worktree_sha'] != entry['worktree_sha_at_dispatch'], (
        'the build edited the tree; a capture taken after the subprocess would hide that'
    )


def test_a_build_that_changes_nothing_records_equal_hashes(monkeypatch, worktree, ledger_path) -> None:
    """A build that changed nothing stamps two IDENTICAL hashes.

    The dispatch capture is taken for real here, against the tree the completion
    hash is then computed on, so this pins the equal-hash case rather than
    asserting it from a hand-made value.
    """
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(worktree)

    with patch_query_worktree_path(True, str(worktree)):
        dispatch_tree_state = module._capture_dispatch_tree_state(_PLAN_ID)
        _record(module, plan_id=_PLAN_ID, dispatch_tree_state=dispatch_tree_state)

    entry = read_entries(path=ledger_path)[0]
    assert entry['worktree_sha_at_dispatch'] == entry['worktree_sha']
    assert entry['worktree_sha'] == compute_worktree_sha(worktree)


def test_the_dispatch_capture_never_raises(monkeypatch) -> None:
    """A capture that fails yields no hash instead of failing the build it precedes."""
    module = _load_template_module()
    monkeypatch.setattr(module, 'compute_worktree_sha', _raise_oserror)

    assert module._capture_dispatch_tree_state(NO_PLAN_SENTINEL) == (None, None)


def test_a_recorder_fault_never_fails_the_build(monkeypatch, ledger_path) -> None:
    """The boundary stays fire-and-forget: no row, and no exception."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.setattr(module, 'compute_worktree_sha', _raise_oserror)

    _record(module, plan_id=NO_PLAN_SENTINEL)

    assert read_entries(path=ledger_path) == []


# =============================================================================
# The round trip the change exists for — recorder then gate, two real trees
# =============================================================================


def _load_gate_module() -> types.ModuleType:
    """Load the freshness gate's command module, unregistered under a unique name."""
    module: types.ModuleType = load_script_module(
        'plan-marshall',
        'manage-tasks',
        '_cmd_pre_commit_verify_freshness.py',
        'freshness_gate_tree_identity_round_trip',
        register=False,
    )
    return module


def test_a_main_checkout_dispatch_is_read_fresh_against_the_worktree(
    main_checkout, worktree, ledger_path, monkeypatch
) -> None:
    """The writer and the reader agree on ONE tree, across two different trees."""
    module = _load_template_module()
    _redirect_ledger(module, monkeypatch, ledger_path)
    monkeypatch.chdir(main_checkout)

    with patch_query_worktree_path(True, str(worktree)):
        dispatch_tree_state = module._capture_dispatch_tree_state(_PLAN_ID)
        _record(module, plan_id=_PLAN_ID, dispatch_tree_state=dispatch_tree_state)

    gate = _load_gate_module()
    monkeypatch.setattr(gate, '_build_necessity_verdict', lambda _plan_id: {'decision': 'build'})
    monkeypatch.setattr(gate, 'resolve_ledger_path', lambda: ledger_path)
    monkeypatch.setattr(gate, '_resolve_required_coverage', lambda _plan_id: (None, 'unused_in_this_case'))
    monkeypatch.setattr(
        _freshness_crosscheck,
        'resolve_expected_notations',
        lambda _project_dir: (frozenset({_NOTATION}), None),
    )

    with patch_query_worktree_path(True, str(worktree)):
        verdict = gate.cmd_pre_commit_verify_freshness(Namespace(plan_id=_PLAN_ID))

    assert verdict['status'] == 'fresh', verdict
    assert Path(verdict['worktree_root']).resolve() == worktree.resolve()
    assert verdict['worktree_sha'] == compute_worktree_sha(worktree)
    # The verdict must NAME the row it rests on — a `fresh` read on the bare
    # status token is exactly the vacuous control this gate's own consumer guard
    # rejects, and the evidence keys are how a reader checks the row it cited.
    assert verdict['matched_notation'] == _NOTATION
    assert verdict['matched_entry_index'] == 0
