#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
        f"    ('tools-input-validation', '{INPUT_VALIDATION_DIR}'),",
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
    persona-plan-marshall-agent Hard Rules.
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


# Post-removal contract: lesson 2026-04-29-23-002 originally drove a runtime
# pre-flight validator (SUBCOMMANDS dict + structured TOON rejection). That
# validator was removed in plan fix-generate-executor-ast-subcommands — drift is
# now detected at dev-time via plugin-doctor and post-hoc via plan-retrospective.
# The executor itself stays dumb and delegates to the target script's argparse,
# which produces its own well-formed `invalid choice` error on stderr with
# exit code 2.

# Sentinel multi-subcommand script body — argparse parser with two declared
# subcommands. Used to verify the post-removal contract: argparse handles
# invented subcommands directly with its standard error message shape.
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

POST_REMOVAL_NOTATION = 'fakebundle:fakeskill'


def _render_executor_for_post_removal(
    target_path: Path,
    embedded_script_path: Path,
) -> Path:
    """Render the template with no SUBCOMMANDS surface — the template no
    longer contains a {{SUBCOMMAND_MAPPINGS}} placeholder after the
    pre-flight validator was removed."""
    template_content = EXECUTOR_TEMPLATE.read_text()
    mappings_code = f'    "{POST_REMOVAL_NOTATION}": "{embedded_script_path}",'

    rendered = template_content.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    rendered = rendered.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    rendered = rendered.replace(
        '{{SHARED_MODULE_DIRS}}',
        f"    ('tools-input-validation', '{INPUT_VALIDATION_DIR}'),",
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
def post_removal_executor(tmp_path):
    """Render an executor that embeds a multi-subcommand script. With the
    pre-flight validator removed, dispatch flows straight through to the
    target script's argparse."""
    script_dir = tmp_path / 'pkg' / 'scripts'
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / 'fakeskill.py'
    script_path.write_text(MULTI_SUB_SCRIPT_TEMPLATE)
    script_path = script_path.resolve()

    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    (plan_dir / 'logs').mkdir()

    executor_path = plan_dir / 'execute-script.py'

    _render_executor_for_post_removal(executor_path, script_path)

    yield {
        'executor': executor_path,
        'script': script_path,
        'plan_dir': plan_dir,
    }


def test_known_subcommand_dispatches_to_script(post_removal_executor, monkeypatch):
    """A registered subcommand still reaches the script's argparse handler."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        post_removal_executor['executor'],
        post_removal_executor['plan_dir'],
        POST_REMOVAL_NOTATION,
        'alpha',
    )

    assert result.returncode == 0, (
        f'Known subcommand should dispatch normally.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:alpha' in result.stdout, (
        f'Script should have been invoked with the alpha subcommand.\nstdout: {result.stdout}'
    )


def test_invented_subcommand_reaches_argparse_native_rejection(post_removal_executor, monkeypatch):
    """With the pre-flight validator removed, an invented subcommand falls
    through to the target script's argparse. argparse exits 2 and emits its
    standard `invalid choice` error to stderr — never the legacy
    `invented_subcommand` TOON shape."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        post_removal_executor['executor'],
        post_removal_executor['plan_dir'],
        POST_REMOVAL_NOTATION,
        'invented-verb',
    )

    # argparse exits 2 on invalid subparser choices.
    assert result.returncode == 2, (
        f'argparse should reject invented subcommand with exit 2. '
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )
    # argparse's stderr shape names the invalid choice and lists valid ones.
    assert 'invalid choice' in result.stderr, (
        f'argparse stderr should mention `invalid choice`: {result.stderr}'
    )
    assert "'invented-verb'" in result.stderr, (
        f'argparse stderr should quote the rejected token: {result.stderr}'
    )
    # The legacy pre-flight TOON shape MUST NOT appear — confirms the
    # validator is structurally gone.
    assert 'invented_subcommand' not in result.stderr, (
        f'Legacy `invented_subcommand` TOON shape leaked into stderr: {result.stderr}'
    )
    assert 'lesson: "2026-04-29-23-002"' not in result.stderr


def test_help_flag_reaches_script_help(post_removal_executor, monkeypatch):
    """`--help` flows through to the target script's argparse help path."""
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    result = _run_executor(
        post_removal_executor['executor'],
        post_removal_executor['plan_dir'],
        POST_REMOVAL_NOTATION,
        '--help',
    )

    assert result.returncode == 0, (
        f'Help flag must reach the script.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    # No legacy pre-flight TOON in either stream.
    assert 'invented_subcommand' not in result.stderr
    assert 'invented_subcommand' not in result.stdout


# Self-healing contract: resolve_notation existence-checks the embedded SCRIPTS
# path. A stale/relocated embedded path is NOT returned blindly — resolution
# self-heals via the target-aware resolver (stubbed to None here) and the
# cwd/executor-file upward walk to a live ``marketplace/bundles`` tree.
# PM_MARKETPLACE_ROOT stays UNSET for these tests to prove the env override is no
# longer REQUIRED.

# The cwd-walk fallback resolves a full three-part notation against
# ``marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``.
SELF_HEAL_NOTATION = 'fakebundle:fakeskill:fakeskill'


def _render_executor_with_cwd_walk(target_path: Path, embedded_script_path: Path) -> Path:
    """Render the executor template with the real cwd-walk fallback intact.

    Identical to :func:`_render_executor` except the SCRIPTS dict is keyed by
    the full three-part ``SELF_HEAL_NOTATION`` (so the cwd-walk's
    ``notation.split(':')`` yields a real bundle/skill/script triple), and the
    target-aware resolver is stubbed to ``None`` so resolution must fall through
    to ``_resolve_notation_by_cwd_walk``.
    """
    template_content = EXECUTOR_TEMPLATE.read_text()

    mappings_code = f'    "{SELF_HEAL_NOTATION}": "{embedded_script_path}",'

    rendered = template_content.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    rendered = rendered.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    rendered = rendered.replace(
        '{{SHARED_MODULE_DIRS}}',
        f"    ('tools-input-validation', '{INPUT_VALIDATION_DIR}'),",
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


def test_stale_embedded_path_self_heals_via_cwd_walk(tmp_path, monkeypatch):
    """
    A non-existent embedded SCRIPTS path is NOT returned. With PM_MARKETPLACE_ROOT
    UNSET, resolution self-heals: the cwd-walk discovers the live script under a
    real ``marketplace/bundles`` tree the executor's cwd sits inside.
    """
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    # Build a live marketplace tree the cwd-walk can discover. The script lives
    # at marketplace/bundles/fakebundle/skills/fakeskill/scripts/fakeskill.py.
    checkout_root = tmp_path / 'checkout'
    live_script = _build_fake_marketplace(checkout_root, tree_id='LIVE')

    # The embedded path points at a tree that no longer exists on disk.
    stale_script = tmp_path / 'gone' / 'marketplace' / 'bundles' / 'fakebundle' / 'skills' / 'fakeskill' / 'scripts' / 'fakeskill.py'

    plan_dir = checkout_root / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'logs').mkdir()
    executor_path = plan_dir / 'execute-script.py'
    _render_executor_with_cwd_walk(executor_path, embedded_script_path=stale_script)

    env = os.environ.copy()
    env['PLAN_BASE_DIR'] = str(plan_dir)
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    env.pop('PM_MARKETPLACE_ROOT', None)

    # cwd sits inside the live checkout so the upward walk finds the live tree.
    result = subprocess.run(
        [sys.executable, str(executor_path), SELF_HEAL_NOTATION],
        capture_output=True,
        text=True,
        cwd=str(checkout_root),
        timeout=30,
        env=env,
    )

    assert result.returncode == 0, (
        f'Stale embedded path should self-heal via cwd-walk with PM_MARKETPLACE_ROOT unset.\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:LIVE' in result.stdout, (
        f'Expected the live cwd-walk-discovered script to run, got stdout:\n{result.stdout}'
    )
    # Sanity: the stale embedded path was never on disk.
    assert not stale_script.exists()
    # The live script is the one the walk should have located.
    assert live_script.exists()


def test_valid_embedded_path_returned_directly(tmp_path, monkeypatch):
    """
    A VALID (existing) embedded path is returned directly. The target-aware
    resolver and cwd-walk are stubbed/irrelevant — the direct hit wins because
    the embedded path exists on disk.
    """
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)

    # The embedded script genuinely exists.
    embedded_root = tmp_path / 'embedded'
    embedded_script = _build_fake_marketplace(embedded_root, tree_id='EMBEDDED')

    # A DECOY live tree the cwd-walk WOULD find — its presence proves the direct
    # hit short-circuits before the walk runs.
    decoy_root = tmp_path / 'decoy'
    _build_fake_marketplace(decoy_root, tree_id='DECOY')

    plan_dir = decoy_root / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'logs').mkdir()
    executor_path = plan_dir / 'execute-script.py'
    _render_executor_with_cwd_walk(executor_path, embedded_script_path=embedded_script)

    env = os.environ.copy()
    env['PLAN_BASE_DIR'] = str(plan_dir)
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    env.pop('PM_MARKETPLACE_ROOT', None)

    # cwd sits inside the decoy tree; if the direct hit did NOT win, the walk
    # would discover the decoy and print SENTINEL:DECOY.
    result = subprocess.run(
        [sys.executable, str(executor_path), SELF_HEAL_NOTATION],
        capture_output=True,
        text=True,
        cwd=str(decoy_root),
        timeout=30,
        env=env,
    )

    assert result.returncode == 0, (
        f'Valid embedded path should be returned directly.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'SENTINEL:EMBEDDED' in result.stdout, (
        f'Expected the valid embedded script to run directly, got stdout:\n{result.stdout}'
    )
    assert 'SENTINEL:DECOY' not in result.stdout, (
        f'The cwd-walk decoy must NOT run when the embedded path exists. stdout:\n{result.stdout}'
    )


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
