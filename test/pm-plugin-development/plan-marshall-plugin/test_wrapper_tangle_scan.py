"""Tests for the plan-marshall-plugin-dev ``wrapper-tangle-scan.py`` aspect.

This is the former Surface C of the generic
``plan-marshall:plan-retrospective:direct-gh-glab-usage`` aspect, now homed in
pm-plugin-development and contributed via ``provides_retrospective_aspects()``.

Covers:

(c) Wrapper scripts with an abstraction-leak pattern — a ``subprocess`` /
    ``run_gh`` / ``run_glab`` args list containing both the CLI name AND a
    local-git mutation token (``checkout``, ``branch -d``, ``--delete-branch``,
    ``--remove-source-branch``) — surface ``wrapper_tangle``.
(e) A pure remote-API ``gh api repos/...`` call with no local-git mutation
    token — negative for the wrapper-tangle heuristic.

Plus the extension-point declaration contract and the aggregate output shape.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'plan-marshall-plugin' / 'scripts' / 'wrapper-tangle-scan.py'
)

_EXT_PATH = (
    MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_plugin_development_extension_wt', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


def _write_wrapper(project_root: Path, rel_path: str, content: str) -> None:
    """Write a wrapper-scope Python file whose path matches one of the three
    directories the scanner walks.
    """
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Extension-point declaration contract
# ---------------------------------------------------------------------------


class TestExtensionPointDeclaration:
    """The pm-plugin-development extension must declare the wrapper-tangle aspect."""

    def test_provides_retrospective_aspects_declares_wrapper_tangle(self):
        ext = _load_extension()
        aspects = ext.provides_retrospective_aspects()
        assert isinstance(aspects, list)
        names = {a['aspect'] for a in aspects}
        assert 'wrapper-tangle' in names, f'Expected wrapper-tangle aspect; got {names}'

    def test_wrapper_tangle_aspect_gated_by_plugin_dev_domain(self):
        ext = _load_extension()
        aspect = next(a for a in ext.provides_retrospective_aspects() if a['aspect'] == 'wrapper-tangle')
        assert aspect['domain'] == 'plan-marshall-plugin-dev'
        assert aspect['script'] == 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan'
        assert aspect['reference']
        assert aspect['description']


# ---------------------------------------------------------------------------
# Wrapper-tangle detection (positive)
# ---------------------------------------------------------------------------


class TestWrapperTangle:
    """subprocess / run_gh / run_glab args lists that mix a CLI invocation with
    a local-git mutation token (``checkout``, ``branch -d`` / ``-D``,
    ``--delete-branch``, ``--remove-source-branch``).
    """

    def test_positive_gh_plus_delete_branch_flag(self, tmp_path):
        """``subprocess.run(['gh', 'pr', 'merge', '--delete-branch'])`` is a
        wrapper tangle — CLI name and mutation token appear in the same
        multi-line args window.
        """
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/leaky_wrapper.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Leaky wrapper fixture."""\n'
            'import subprocess\n'
            'def merge(pr_number: str) -> None:\n'
            '    subprocess.run([\n'
            "        'gh', 'pr', 'merge', pr_number, '--delete-branch',\n"
            '    ], check=True)\n',
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-tangle', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspect'] == 'wrapper-tangle'
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert len(tangles) >= 1, f'Expected wrapper_tangle finding; got {tangles}'
        assert any('leaky_wrapper.py' in f['file'] for f in tangles)

    def test_positive_glab_plus_checkout(self, tmp_path):
        """``checkout`` is a mutation token too (glab variant)."""
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/leaky_glab.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Leaky glab wrapper fixture."""\n'
            'import subprocess\n'
            'def checkout_branch(ref: str) -> None:\n'
            "    subprocess.run(['glab', 'mr', 'checkout', ref], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-glab', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert any('leaky_glab.py' in f['file'] for f in tangles), (
            f'Expected wrapper_tangle finding for glab+checkout call; got {tangles}'
        )

    def test_positive_gh_plus_list_style_branch_dash_d(self, tmp_path):
        """List-style ``['git', 'branch', '-d', branch]`` downstream of a gh call
        inside the same window must be flagged (token-aware matching).
        """
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/list_dash_leak.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""List-style branch -d fixture."""\n'
            'import subprocess\n'
            'def cleanup(branch: str) -> None:\n'
            "    subprocess.run(['gh', 'pr', 'merge', branch], check=True)\n"
            "    subprocess.run(['git', 'branch', '-d', branch], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-listdash', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert any('list_dash_leak.py' in f['file'] for f in tangles), (
            f'Expected wrapper_tangle finding for gh + list-style branch -d call; got {tangles}'
        )

    def test_positive_run_gh_wrapper_plus_delete_branch(self, tmp_path):
        """A wrapper-only call site (``run_gh(['pr', 'merge', '--delete-branch'])``)
        must anchor the scan just like a ``subprocess.`` call site does.
        """
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/run_gh_leak.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""run_gh wrapper fixture."""\n'
            'def run_gh(args, *, capture_json=False, timeout=60):\n'
            '    return 0, "", ""\n'
            'def merge(pr_number: str) -> None:\n'
            "    run_gh(['pr', 'merge', pr_number, '--delete-branch'])\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-rungh', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert any('run_gh_leak.py' in f['file'] for f in tangles), (
            f'Expected wrapper_tangle finding for run_gh + --delete-branch call; got {tangles}'
        )

    def test_positive_run_glab_wrapper_plus_remove_source_branch(self, tmp_path):
        """Symmetric GitLab coverage for ``run_glab(['mr', 'merge',
        '--remove-source-branch'])``.
        """
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/run_glab_leak.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""run_glab wrapper fixture."""\n'
            'def run_glab(args, *, capture_json=False, timeout=60):\n'
            '    return 0, "", ""\n'
            'def merge(mr_number: str) -> None:\n'
            "    run_glab(['mr', 'merge', mr_number, '--remove-source-branch'])\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-runglab', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert any('run_glab_leak.py' in f['file'] for f in tangles), (
            f'Expected wrapper_tangle finding for run_glab + --remove-source-branch call; got {tangles}'
        )


# ---------------------------------------------------------------------------
# Wrapper-tangle detection (negative — false-positive guards)
# ---------------------------------------------------------------------------


class TestWrapperTangleNegatives:
    """Guards against false positives."""

    def test_negative_branch_delete_identifier_not_flagged(self, tmp_path):
        """An identifier like ``branch_delete`` must NOT be misread as the
        ``branch -d`` mutation token (anchored matching).
        """
        wrapper_rel = (
            'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/branch_delete_caller.py'
        )
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Identifier-only fixture — no real local-git mutation."""\n'
            'import subprocess\n'
            'def call_remote_branch_delete(branch: str) -> None:\n'
            "    subprocess.run(['gh', 'api', '-X', 'DELETE', "
            "f'repos/o/r/git/refs/heads/{branch}'], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-branchid', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert tangles == [], (
            f'Identifier ``branch_delete`` must not match the branch -d/-D mutation token; got: {tangles}'
        )

    def test_negative_pure_remote_gh_api_not_flagged(self, tmp_path):
        """``gh api repos/...`` with no local-git mutation token is a class-A
        remote-only call — the heuristic MUST NOT trip.
        """
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/remote_only.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Pure remote-API wrapper — no local-git side effects."""\n'
            'import subprocess\n'
            'def list_issues(repo: str) -> None:\n'
            "    subprocess.run(['gh', 'api', f'repos/{repo}/issues'], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-remote-only', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert tangles == [], (
            f'Pure remote-only gh api call must NOT be flagged as a wrapper tangle; got: {tangles}'
        )


# ---------------------------------------------------------------------------
# Aggregate output contract
# ---------------------------------------------------------------------------


class TestAggregateContract:
    """Output shape: domain field + wrapper_tangle counter."""

    def test_counts_reflect_findings_and_domain(self, tmp_path):
        wrapper_rel = 'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/aggregate_leak.py'
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Aggregate fixture."""\n'
            'import subprocess\n'
            'def merge() -> None:\n'
            "    subprocess.run(['gh', 'pr', 'merge', '--delete-branch'], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-aggregate', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspect'] == 'wrapper-tangle'
        assert data['domain'] == 'plan-marshall-plugin-dev'
        findings = data['findings']
        tangle_n = sum(1 for f in findings if f['surface'] == 'wrapper_tangle')
        assert int(data['counts']['by_surface']['wrapper_tangle']) == tangle_n
        assert int(data['counts']['total']) == tangle_n
        assert tangle_n >= 1

    def test_clean_tree_emits_zero_findings(self, tmp_path):
        """A project-root with no wrapper dirs yields zero findings, status success."""
        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', 'wt-clean', '--mode', 'live', '--project-root', str(tmp_path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert int(data['counts']['total']) == 0
        assert data['findings'] == []
