#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-92 D1/D2: a lane worktree carries its own executor.

D1 — ``worktree-create`` PRODUCES ``{worktree}/.plan/execute-script.py`` through
the seam the lifecycle's phase-5 move-in already uses
(``prepare_execute._generate_worktree_executor``: generate with
``--marketplace-root {worktree}`` and ``cwd`` pinned to the worktree, then the
copy-from-main fallback), non-fatally and idempotently, with the verdict taken
from the file on disk. The payload states ``executor_in_worktree`` and, when the
verdict is ``absent``, the reason it got there.

D2 — ``worktree-executor-refresh`` re-runs the same seam on demand, so a plan
that adds, removes or renames a script verb can resolve its own new notation
from its own worktree without a direct interpreter call to the generator.

The two fixtures are deliberately different:

* ``main_repo`` stages a real-git checkout whose ``marketplace/`` is ABSENT —
  the consumer-project shape — so both D1 mechanisms can be driven in isolation
  (generation stubbed, real copy fallback; and the reverse).
* ``generated_repo`` stages a real-git checkout whose ``marketplace/`` holds one
  bundle script and runs the REAL generator end-to-end, which is the only way to
  observe the D2 claim that a branch-added script resolves only after the verb.
"""

from __future__ import annotations

import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module, parse_ns

_GIT_WF = ('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

git_workflow = load_script_module(*_GIT_WF)

_PLAN_ID = 'lb-92-lane-worktree-executor'

_MAIN_EXECUTOR_BODY = '#!/usr/bin/env python3\n# the main checkout executor\n'
_CREATION_MARKER = '#!/usr/bin/env python3\n# produced at worktree creation\n'
_MOVE_IN_MARKER = '#!/usr/bin/env python3\n# produced at phase-5 move-in\n'

#: A stand-in bundle script. ``argparse`` is what makes ``--help`` meaningful to
#: the generated executor, so the smoke call below proves dispatch rather than
#: merely proving the file was written. Subparsers are declared so the
#: GENERATED SURFACE has real verbs to validate against — that surface is what a
#: branch-added verb must go through.
_VERB_SCRIPT_RELATIVE = Path('marketplace/bundles/plan-marshall/skills/demo/scripts/alpha.py')
_VERB_SCRIPT_TEMPLATE = (
    'import argparse\n'
    '\n'
    'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
    "sub = parser.add_subparsers(dest='verb')\n"
    '{subparsers}'
    'parser.parse_args()\n'
)

#: A stand-in bundle script with no subcommands, for the added-script case.
_SCRIPT_BODY = (
    'import argparse\n'
    '\n'
    "parser = argparse.ArgumentParser(description='{label}', allow_abbrev=False)\n"
    'parser.parse_args()\n'
)


# =============================================================================
# Fixtures
# =============================================================================


def _init_repo(repo: Path) -> None:
    """A real-git checkout with the canonical ``.plan`` layout, no marketplace."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    plan_dir = repo / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n')
    (repo / '.gitignore').write_text('.plan/local\n.plan/execute-script.py\n.plan/local/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)

    # Gitignored runtime state on main: the plan record the move-in needs and
    # main's own executor (the fallback's byte-source).
    (plan_dir / 'local' / 'plans' / _PLAN_ID).mkdir(parents=True)
    (plan_dir / 'local' / 'plans' / _PLAN_ID / 'status.json').write_text('{"phase": "3-planning"}\n')
    (plan_dir / 'execute-script.py').write_text(_MAIN_EXECUTOR_BODY)


def _anchor(main: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Anchor every cwd-relative resolver at the staged checkout.

    ``PLAN_BASE_DIR`` is REMOVED rather than pointed at the fixture: the
    generator writes its output beside the ``.plan`` that resolver names, so an
    ambient override would make a worktree generation land in the harness's
    sandbox instead of the worktree — a test-only shape production never has.
    With it gone the uniform cwd walk applies, exactly as in production, and the
    staged checkout's own ``.plan/local`` is what resolves.
    """
    monkeypatch.chdir(main)
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)


@pytest.fixture
def main_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    main = tmp_path / 'main'
    main.mkdir()
    _init_repo(main)
    _anchor(main, monkeypatch)
    return main


@pytest.fixture
def generated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real-git checkout owning one bundle script, so the real generator runs.

    main's executor is deliberately ABSENT: the copy-from-main fallback must not
    be able to satisfy the test, so a ``present`` verdict here can only come from
    a real generation against the worktree's own bundle tree.
    """
    main = tmp_path / 'main'
    main.mkdir()
    _init_repo(main)
    (main / '.plan' / 'execute-script.py').unlink()
    _seed_logging_module(main)
    _write_verb_script(main / _VERB_SCRIPT_RELATIVE, ['old'])
    subprocess.run(['git', '-C', str(main), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(main), 'commit', '-q', '-m', 'add alpha'], check=True)
    _anchor(main, monkeypatch)
    return main


# =============================================================================
# Helpers
# =============================================================================


def _write_verb_script(path: Path, verbs: list[str]) -> Path:
    """Rewrite a script's declared verbs, as a branch changing the surface does."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subparsers = ''.join(f"sub.add_parser('{verb}')\n" for verb in verbs)
    path.write_text(_VERB_SCRIPT_TEMPLATE.format(subparsers=subparsers), encoding='utf-8')
    return path


def _seed_demo_script(tree: Path, name: str, label: str) -> Path:
    """Write one stand-in bundle script into ``tree``'s marketplace."""
    scripts = tree / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'demo' / 'scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    script = scripts / f'{name}.py'
    script.write_text(_SCRIPT_BODY.format(label=label), encoding='utf-8')
    return script


def _seed_logging_module(tree: Path) -> None:
    """Seed the module the generated executor's own header imports.

    ``generate_executor`` refuses a base whose ``manage-logging/scripts``
    directory is absent (``logging_module_dir_missing``), and the header it
    emits imports five names from ``plan_logging``. A fixture marketplace
    without that directory — or with a module missing one of the names — can
    never produce a runnable executor, whatever else it holds.
    """
    scripts = tree / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    names = (
        'cleanup_old_script_logs',
        'extract_plan_id',
        'get_log_path',
        'log_entry',
        'log_script_execution',
    )
    body = '"""Stand-in for the names the generated executor header imports."""\n\n'
    body += ''.join(f'def {name}(*_args, **_kwargs):\n    return None\n\n' for name in names)
    (scripts / 'plan_logging.py').write_text(body, encoding='utf-8')


def _create_worktree() -> dict:
    """Run ``worktree-create`` through that script's OWN parser."""
    ns = parse_ns(*_GIT_WF, 'worktree-create', '--plan-id', _PLAN_ID, '--branch', f'fix/{_PLAN_ID}')
    return dict(git_workflow.cmd_worktree_create(ns))


def _prepare_ns() -> Namespace:
    return parse_ns(
        'plan-marshall',
        'workflow-integration-git',
        'prepare_execute.py',
        'prepare',
        '--plan-id',
        _PLAN_ID,
        '--branch',
        f'fix/{_PLAN_ID}',
    )


def _live_prepare_execute():
    """Return the ``prepare_execute`` module the production code will import.

    Several suites in this tree load ``prepare_execute.py`` through
    ``load_script_module`` under its DEFAULT module name, and every such load
    REPLACES the ``sys.modules`` entry — so the object this file bound at import
    time can already be a displaced copy by the time a test runs. A patch has to
    land on the copy production resolves, which is the one published under the
    module's own name at call time.
    """
    import importlib

    return sys.modules.get('prepare_execute') or importlib.import_module('prepare_execute')


def _worktree_executor(worktree: Path) -> Path:
    return worktree / '.plan' / 'execute-script.py'


def _stub_generation(monkeypatch: pytest.MonkeyPatch, body: str | None) -> list[str]:
    """Replace the shared production seam with a deterministic outcome.

    ``body`` writes a marker file (generation succeeded); ``None`` reports the
    failure shape the real seam produces when generation cannot land a file, so
    each test isolates ONE mechanism and the copy-from-main fallback stays REAL
    in every call.
    """
    calls: list[str] = []

    def fake_generate(worktree_path: Path, plan_id: str) -> tuple[bool, str]:
        calls.append(plan_id)
        if body is None:
            return False, 'generation exited 1: no marketplace tree in this fixture'
        target = _worktree_executor(worktree_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        return True, f'worktree executor generated at {target}'

    monkeypatch.setattr(_live_prepare_execute(), '_generate_worktree_executor', fake_generate)
    return calls


def _run_executor(executor: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Dispatch ``args`` through an executor, as a caller would."""
    return subprocess.run(
        [sys.executable, str(executor), *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


# =============================================================================
# D1 — worktree creation produces the executor
# =============================================================================


class TestWorktreeCreationProducesTheExecutor:
    def test_creation_produces_a_non_empty_executor(self, main_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The generated executor is on disk, non-empty, and reported present."""
        calls = _stub_generation(monkeypatch, _CREATION_MARKER)

        payload = _create_worktree()

        assert calls == [_PLAN_ID], f'the shared seam was not the production mechanism (calls={calls})'
        assert payload['status'] == 'success', payload
        executor = _worktree_executor(Path(payload['worktree_path']))
        assert executor.is_file()
        assert executor.stat().st_size > 0
        assert executor.read_text(encoding='utf-8') == _CREATION_MARKER
        assert payload['executor_in_worktree'] == 'present'
        assert 'executor_reason' not in payload, 'a present executor carries no absence reason'

    def test_creation_copies_the_main_executor_when_generation_fails(
        self, main_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The FIX-2 fallback still serves a checkout that cannot generate.

        Generation is left REAL: the fixture tree has no ``marketplace/`` to
        discover, so the generator lands no file and the seam must fall through
        to the copy. Stubbing the seam here would skip the fallback it is
        supposed to exercise.
        """
        payload = _create_worktree()

        assert payload['status'] == 'success', payload
        executor = _worktree_executor(Path(payload['worktree_path']))
        assert executor.read_text(encoding='utf-8') == _MAIN_EXECUTOR_BODY
        assert payload['executor_in_worktree'] == 'present'

    def test_creation_reports_absent_without_failing_the_creation(
        self, main_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Neither mechanism is possible: the worktree still exists, verbatim absent.

        Both mechanisms are REAL: generation has no marketplace tree to discover
        and main carries no executor to copy, which is the one shape that leaves
        the slot empty. The creation must still succeed and say so.
        """
        (main_repo / '.plan' / 'execute-script.py').unlink()

        payload = _create_worktree()

        assert payload['status'] == 'success', 'an absent executor must never fail the creation'
        assert payload['executor_in_worktree'] == 'absent'
        assert 'no main executor available to copy from' in payload['executor_reason']
        assert not _worktree_executor(Path(payload['worktree_path'])).exists()

    def test_phase_five_move_in_still_produces_its_own_executor(
        self, main_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The lifecycle's move-in keeps generating: the lane's change is additive."""
        _stub_generation(monkeypatch, _CREATION_MARKER)
        created = _create_worktree()
        worktree = Path(created['worktree_path'])

        _stub_generation(monkeypatch, _MOVE_IN_MARKER)
        result = _live_prepare_execute().run_prepare_execute(_prepare_ns())

        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        assert result['worktree_executor_generated'] is True
        assert _worktree_executor(worktree).read_text(encoding='utf-8') == _MOVE_IN_MARKER


# =============================================================================
# D2 — the refresh verb resolves the plan's own new script
# =============================================================================


class TestWorktreeExecutorRefresh:
    def test_a_branch_added_verb_is_refused_before_the_refresh_and_runs_after(
        self, generated_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The plan's own new verb: refused while stale, dispatchable after.

        This is the defect class the verb exists for. The executor embeds the
        argparse surface it derived at generation time and validates a call
        against it BEFORE spawning, so a verb the branch adds is refused as
        ``unknown_verb`` until the surface is rebuilt. Path resolution cannot
        save it: the surface check runs against the embedded map.
        """
        created = _create_worktree()
        assert created['status'] == 'success', created
        assert created['executor_in_worktree'] == 'present', created
        worktree = Path(created['worktree_path'])
        executor = _worktree_executor(worktree)

        _write_verb_script(worktree / _VERB_SCRIPT_RELATIVE, ['old', 'new'])
        subprocess.run(['git', '-C', str(worktree), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(worktree), 'commit', '-q', '-m', 'add the new verb'], check=True)

        before = _run_executor(executor, 'plan-marshall:demo:alpha', 'new')
        assert before.returncode != 0, f'the stale surface already accepted the branch verb:\n{before.stdout}'
        assert 'unknown_verb' in (before.stdout + before.stderr), before.stdout + before.stderr

        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda _plan_id: (worktree, None))
        payload = git_workflow.cmd_worktree_executor_refresh(Namespace(plan_id=_PLAN_ID))

        assert payload['status'] == 'success', payload
        assert payload['executor_regenerated'] is True, payload
        assert payload['executor_detail'], 'the verdict must carry its detail'

        after = _run_executor(executor, 'plan-marshall:demo:alpha', 'new')
        assert after.returncode == 0, after.stdout + after.stderr

    def test_the_refresh_maps_a_script_the_branch_added(
        self, generated_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The rebuilt notation map carries a script that did not exist at creation.

        Only the MAP is asserted here, not a before/after refusal: an executor
        whose own worktree carries ``marketplace/bundles`` resolves an unmapped
        notation through its tree-walking legs (the template's leg 0 on OpenCode,
        legs 3 and 4 elsewhere), so an added script is never refused for being
        absent from the map. The map is what the verb rebuilds, and that is what
        this asserts.
        """
        created = _create_worktree()
        assert created['status'] == 'success', created
        worktree = Path(created['worktree_path'])
        executor = _worktree_executor(worktree)
        assert 'beta.py' not in executor.read_text(encoding='utf-8')

        _seed_demo_script(worktree, 'beta', 'added on the branch')
        subprocess.run(['git', '-C', str(worktree), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(worktree), 'commit', '-q', '-m', 'add beta'], check=True)

        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda _plan_id: (worktree, None))
        payload = git_workflow.cmd_worktree_executor_refresh(Namespace(plan_id=_PLAN_ID))

        assert payload['executor_regenerated'] is True, payload
        assert 'beta.py' in executor.read_text(encoding='utf-8')

        after = _run_executor(executor, 'plan-marshall:demo:beta', '--help')
        assert after.returncode == 0, after.stdout + after.stderr
        assert 'usage' in after.stdout.lower(), after.stdout

    def test_refresh_refuses_a_plan_without_a_worktree(self, main_repo: Path) -> None:
        """The canonical resolver's refusal is propagated unchanged."""
        payload = git_workflow.cmd_worktree_executor_refresh(Namespace(plan_id='no-such-plan'))

        assert payload['status'] == 'error'
        assert payload['error'] == 'plan_resolution_failed'
