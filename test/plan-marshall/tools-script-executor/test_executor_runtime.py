#!/usr/bin/env python3
"""
Runtime regression tests for the executor template's PM_MARKETPLACE_ROOT
path-rewrite hook.

Background
----------
The executor (.plan/execute-script.py) embeds absolute script paths at
generation time. When PM_MARKETPLACE_ROOT is set at runtime, the template's
``_rewrite_scripts_for_env`` helper rewrites those absolute paths so they
resolve under the env-rooted marketplace tree instead of the embedded one.

These tests verify both ends of the contract:

1. With PM_MARKETPLACE_ROOT set to a different marketplace tree, an executor
   generated against tree A invokes the script copy under tree B.
2. Without PM_MARKETPLACE_ROOT, behaviour is byte-identical to the un-hooked
   template — the executor invokes the embedded (tree A) copy.

Approach
--------
Each test builds two minimal "fake marketplace" trees (A and B) under
``tmp_path``. Each tree contains a single trivial script at the same
notation-relative path. The script prints a sentinel identifying which tree
it came from. We render the executor template against tree A, then invoke
it with and without PM_MARKETPLACE_ROOT pointing at tree B and assert which
sentinel was printed.

The fake trees deliberately do NOT contain plan_logging or input_validation,
so we point ``{{LOGGING_DIR}}`` and ``{{SHARED_MODULE_DIRS}}`` at the real
marketplace location (the executor's logging is orthogonal to the
path-rewrite logic under test).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import _MARKETPLACE_SCRIPT_DIRS, MARKETPLACE_ROOT

# ============================================================================
# PATHS
# ============================================================================

SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-script-executor'
TEMPLATES_DIR = SKILL_DIR / 'templates'
EXECUTOR_TEMPLATE = TEMPLATES_DIR / 'execute-script.py.template'

# Real marketplace dirs used purely so the rendered executor can import
# ``plan_logging``. Path-rewrite logic only touches SCRIPTS values whose
# embedded prefix matches ``{embedded_root}/marketplace/bundles/``.
LOGGING_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'logging' / 'scripts'
INPUT_VALIDATION_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-input-validation' / 'scripts'

# The notation we'll register in the embedded SCRIPTS dict. Format is
# ``{bundle}:{skill}`` (matches the existing executor convention).
TEST_NOTATION = 'fakebundle:fakeskill'

# Sentinel script body. Each fake tree gets its own copy that prints a
# different sentinel so we can identify which tree the executor invoked.
SENTINEL_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
import sys
print('SENTINEL:{tree_id}')
sys.exit(0)
"""


# ============================================================================
# FAKE MARKETPLACE TREE BUILDER
# ============================================================================


def _build_fake_marketplace(root: Path, tree_id: str) -> Path:
    """
    Build a minimal fake marketplace tree under ``root``.

    Layout::

        {root}/
          marketplace/
            bundles/
              fakebundle/
                skills/
                  fakeskill/
                    scripts/
                      fakeskill.py     <- prints SENTINEL:{tree_id}

    Returns the absolute path to the script for direct embedding into the
    executor's SCRIPTS dict.
    """
    script_dir = root / 'marketplace' / 'bundles' / 'fakebundle' / 'skills' / 'fakeskill' / 'scripts'
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / 'fakeskill.py'
    script_path.write_text(SENTINEL_SCRIPT_TEMPLATE.format(tree_id=tree_id))
    return script_path.resolve()


def _render_executor(target_path: Path, embedded_script_path: Path) -> Path:
    """
    Render the executor template into ``target_path`` with the SCRIPTS dict
    pointing at ``embedded_script_path``.
    """
    template_content = EXECUTOR_TEMPLATE.read_text()

    mappings_code = f'    "{TEST_NOTATION}": "{embedded_script_path}",'

    rendered = template_content.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    rendered = rendered.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    rendered = rendered.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    rendered = rendered.replace(
        '{{SHARED_MODULE_DIRS}}',
        f"sys.path.insert(0, '{INPUT_VALIDATION_DIR}')",
    )
    rendered = rendered.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    rendered = rendered.replace('{{PLAN_DIR_NAME}}', '.plan')
    rendered = rendered.replace('{{EXECUTOR_TARGET}}', 'claude')
    rendered = rendered.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )

    target_path.write_text(rendered)
    return target_path


def _run_executor(
    executor_path: Path,
    plan_dir: Path,
    *args: str,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Invoke the rendered executor with optional env overrides."""
    env = os.environ.copy()
    env['PLAN_BASE_DIR'] = str(plan_dir)
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath

    if env_overrides:
        env.update(env_overrides)
    else:
        # Ensure PM_MARKETPLACE_ROOT is unset for the "no env" baseline test.
        env.pop('PM_MARKETPLACE_ROOT', None)

    return subprocess.run(
        [sys.executable, str(executor_path)] + list(args),
        capture_output=True,
        text=True,
        cwd=str(executor_path.parent.parent),
        timeout=30,
        env=env,
    )


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def two_marketplace_trees(tmp_path):
    """
    Build two fake marketplace trees (A and B) plus a generated executor
    rooted in tree A.

    Yields a dict with:
        tree_a_root: Path (parent containing marketplace/bundles/...)
        tree_b_root: Path (parent containing marketplace/bundles/...)
        script_a: absolute Path of fakeskill.py inside tree A
        script_b: absolute Path of fakeskill.py inside tree B
        executor: Path to rendered executor (embeds script_a)
        plan_dir: PLAN_BASE_DIR for executor logging isolation
    """
    tree_a_root = tmp_path / 'tree-a'
    tree_b_root = tmp_path / 'tree-b'
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    (plan_dir / 'logs').mkdir()

    script_a = _build_fake_marketplace(tree_a_root, tree_id='A')
    script_b = _build_fake_marketplace(tree_b_root, tree_id='B')

    executor_path = plan_dir / 'execute-script.py'
    _render_executor(executor_path, embedded_script_path=script_a)

    yield {
        'tree_a_root': tree_a_root,
        'tree_b_root': tree_b_root,
        'script_a': script_a,
        'script_b': script_b,
        'executor': executor_path,
        'plan_dir': plan_dir,
    }


# ============================================================================
# TESTS
# ============================================================================


def test_pm_marketplace_root_unset_uses_embedded_tree(two_marketplace_trees, monkeypatch):
    """
    Baseline: with PM_MARKETPLACE_ROOT unset, the executor invokes the script
    embedded at generation time (tree A).
    """
    # Defensive: ensure no inherited PM_MARKETPLACE_ROOT leaks from outer env.
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        two_marketplace_trees['executor'],
        two_marketplace_trees['plan_dir'],
        TEST_NOTATION,
    )

    assert result.returncode == 0, (
        f'Executor failed without PM_MARKETPLACE_ROOT.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:A' in result.stdout, (
        f'Expected embedded tree A to be invoked, got stdout:\n{result.stdout}'
    )
    assert 'SENTINEL:B' not in result.stdout, (
        f'Tree B should NOT have been invoked when PM_MARKETPLACE_ROOT is unset. stdout:\n{result.stdout}'
    )


def test_pm_marketplace_root_set_rewrites_to_env_tree(two_marketplace_trees, monkeypatch):
    """
    With PM_MARKETPLACE_ROOT pointing at tree B, the executor invokes the
    script under tree B even though tree A's path is embedded in SCRIPTS.

    Note: monkeypatch.setenv is the canonical way to set the env var — never
    use the inline ``VAR=val cmd`` shape, which is forbidden by
    dev-agent-behavior-rules Hard Rules.
    """
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(two_marketplace_trees['tree_b_root']))

    result = _run_executor(
        two_marketplace_trees['executor'],
        two_marketplace_trees['plan_dir'],
        TEST_NOTATION,
        env_overrides={'PM_MARKETPLACE_ROOT': str(two_marketplace_trees['tree_b_root'])},
    )

    assert result.returncode == 0, (
        f'Executor failed with PM_MARKETPLACE_ROOT set.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:B' in result.stdout, (
        f'Expected env-rooted tree B to be invoked, got stdout:\n{result.stdout}'
    )
    assert 'SENTINEL:A' not in result.stdout, (
        f'Tree A should NOT have been invoked when PM_MARKETPLACE_ROOT redirects to tree B. stdout:\n{result.stdout}'
    )


def test_pm_marketplace_root_matching_embedded_root_is_noop(two_marketplace_trees, monkeypatch):
    """
    When PM_MARKETPLACE_ROOT points at the same tree as the embedded one, the
    rewrite helper short-circuits (embedded_root == new_root path) and the
    executor still invokes the embedded script.
    """
    # Tree A is the embedded tree; pointing the env var at it should be a no-op.
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(two_marketplace_trees['tree_a_root']))

    result = _run_executor(
        two_marketplace_trees['executor'],
        two_marketplace_trees['plan_dir'],
        TEST_NOTATION,
        env_overrides={'PM_MARKETPLACE_ROOT': str(two_marketplace_trees['tree_a_root'])},
    )

    assert result.returncode == 0, (
        f'Executor failed with PM_MARKETPLACE_ROOT=embedded_root.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:A' in result.stdout, (
        f'Expected tree A to remain invoked when PM_MARKETPLACE_ROOT matches embedded root. stdout:\n{result.stdout}'
    )


# ============================================================================
# PRE-FLIGHT SUBCOMMAND VALIDATOR (lesson 2026-04-29-23-002)
# ============================================================================

# Sentinel multi-subcommand script body — argparse parser with two declared
# subcommands. When invoked with a registered subcommand the script prints a
# sentinel and exits 0; argparse handles invalid subcommands itself (which is
# precisely the failure mode the pre-flight validator now intercepts upstream).
MULTI_SUB_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='cmd', required=True)
    subs.add_parser('alpha')
    subs.add_parser('bravo')
    args = parser.parse_args()
    print(f'SENTINEL:{args.cmd}')
    sys.exit(0)

if __name__ == '__main__':
    main()
"""

PREFLIGHT_NOTATION = 'fakebundle:fakeskill'


def _render_executor_with_subcommands(
    target_path: Path,
    embedded_script_path: Path,
    subcommands_block: str,
) -> Path:
    """Render the template with a populated SUBCOMMAND_MAPPINGS block.

    ``subcommands_block`` is the literal text to substitute for
    ``{{SUBCOMMAND_MAPPINGS}}`` — a multi-line string of dict-literal entries
    indented for embedding inside the SUBCOMMANDS dict.
    """
    template_content = EXECUTOR_TEMPLATE.read_text()
    mappings_code = f'    "{PREFLIGHT_NOTATION}": "{embedded_script_path}",'

    rendered = template_content.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    rendered = rendered.replace('{{SUBCOMMAND_MAPPINGS}}', subcommands_block)
    rendered = rendered.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    rendered = rendered.replace(
        '{{SHARED_MODULE_DIRS}}',
        f"sys.path.insert(0, '{INPUT_VALIDATION_DIR}')",
    )
    rendered = rendered.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    rendered = rendered.replace('{{PLAN_DIR_NAME}}', '.plan')
    rendered = rendered.replace('{{EXECUTOR_TARGET}}', 'claude')
    rendered = rendered.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )

    target_path.write_text(rendered)
    return target_path


@pytest.fixture
def preflight_executor(tmp_path):
    """Render an executor that embeds a multi-subcommand script and its
    SUBCOMMANDS mapping. Yields the rendered executor path plus the script
    path and plan_dir for logging isolation."""
    script_dir = tmp_path / 'pkg' / 'scripts'
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / 'fakeskill.py'
    script_path.write_text(MULTI_SUB_SCRIPT_TEMPLATE)
    script_path = script_path.resolve()

    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    (plan_dir / 'logs').mkdir()

    executor_path = plan_dir / 'execute-script.py'

    # Populate SUBCOMMANDS with the two declared subcommand names.
    subcommands_block = f'    "{PREFLIGHT_NOTATION}": ["alpha", "bravo"],'

    _render_executor_with_subcommands(executor_path, script_path, subcommands_block)

    yield {
        'executor': executor_path,
        'script': script_path,
        'plan_dir': plan_dir,
    }


def test_known_subcommand_passes(preflight_executor, monkeypatch):
    """A subcommand declared in SUBCOMMANDS dispatches to the script normally."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        preflight_executor['executor'],
        preflight_executor['plan_dir'],
        PREFLIGHT_NOTATION,
        'alpha',
    )

    assert result.returncode == 0, (
        f'Known subcommand should dispatch normally.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:alpha' in result.stdout, (
        f'Script should have been invoked with the alpha subcommand.\nstdout: {result.stdout}'
    )


def test_invented_subcommand_rejected(preflight_executor, monkeypatch):
    """An invented subcommand is rejected pre-flight with the structured TOON
    contract that names lesson 2026-04-29-23-002."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        preflight_executor['executor'],
        preflight_executor['plan_dir'],
        PREFLIGHT_NOTATION,
        'invented-verb',
    )

    assert result.returncode != 0, (
        f'Invented subcommand must exit non-zero.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    # Script must NOT have run — no SENTINEL output.
    assert 'SENTINEL' not in result.stdout, (
        f'Script must not be invoked when validator rejects subcommand.\nstdout: {result.stdout}'
    )
    # Structured TOON fields per the contract.
    assert 'status: error' in result.stderr
    assert 'error: "invented_subcommand"' in result.stderr
    assert f'notation: "{PREFLIGHT_NOTATION}"' in result.stderr
    assert 'invented: "invented-verb"' in result.stderr
    assert 'alpha' in result.stderr and 'bravo' in result.stderr, (
        'valid_choices must list the declared subcommand names.'
    )
    assert 'lesson: "2026-04-29-23-002"' in result.stderr


def test_help_flag_bypasses_preflight(preflight_executor, monkeypatch):
    """The validator must let -h / --help through so callers can still
    discover the subcommand surface via the script's own help output."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        preflight_executor['executor'],
        preflight_executor['plan_dir'],
        PREFLIGHT_NOTATION,
        '--help',
    )

    # The script's argparse --help exits 0 and prints usage to stdout.
    assert result.returncode == 0, (
        f'Help flag must bypass pre-flight and reach the script.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    # The pre-flight TOON must NOT have been emitted.
    assert 'invented_subcommand' not in result.stderr


def test_pm_marketplace_root_with_trailing_slash_rewrites(two_marketplace_trees, monkeypatch):
    """
    The rewrite helper rstrips trailing slashes — a trailing-slash form of
    PM_MARKETPLACE_ROOT must produce identical behaviour to the bare form.
    """
    env_value = str(two_marketplace_trees['tree_b_root']) + '/'
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', env_value)

    result = _run_executor(
        two_marketplace_trees['executor'],
        two_marketplace_trees['plan_dir'],
        TEST_NOTATION,
        env_overrides={'PM_MARKETPLACE_ROOT': env_value},
    )

    assert result.returncode == 0, (
        f'Executor failed with trailing-slash PM_MARKETPLACE_ROOT.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:B' in result.stdout, (
        f'Expected env-rooted tree B to be invoked with trailing-slash root. stdout:\n{result.stdout}'
    )
