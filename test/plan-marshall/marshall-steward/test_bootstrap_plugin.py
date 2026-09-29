#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for bootstrap_plugin.py script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import os
import subprocess
import sys
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Get script path — use base directory for all steward scripts
_SCRIPTS_DIR = Path(get_script_path('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py')).parent
SCRIPT_PATH = _SCRIPTS_DIR / 'bootstrap_plugin.py'

# Tier 2 direct import — resolution by (bundle, skill, script).
_mod = load_script_module('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py', module_name='bootstrap_plugin')

read_state = _mod.read_state
write_state = _mod.write_state
resolve_bundle_path = _mod.resolve_bundle_path


# =============================================================================
# Test: State file operations (Tier 2 - direct import)
# =============================================================================


def test_state_read_write(plan_context):
    """Test reading and writing state file directly."""
    # Verify initial state is empty
    state = read_state()
    assert state == {} or 'plugin_root' not in state

    # Write state
    write_state({'plugin_root': '/fake/path', 'detected_at': '2026-01-01T00:00:00Z'})

    # Read back
    state = read_state()
    assert state['plugin_root'] == '/fake/path'
    assert state['detected_at'] == '2026-01-01T00:00:00Z'


def test_resolve_bundle_path(plan_context):
    """Test resolve_bundle_path with a mock structure."""
    mock_root = plan_context.fixture_dir / 'mock-cache'
    bundle_dir = mock_root / 'test-bundle' / '1.0.0' / 'skills' / 'test-skill'
    bundle_dir.mkdir(parents=True)
    (bundle_dir / 'SKILL.md').write_text('# Test Skill')

    result = resolve_bundle_path(mock_root, 'test-bundle', 'skills/test-skill/SKILL.md')
    assert result is not None
    assert result.exists()
    assert result.name == 'SKILL.md'


def test_resolve_bundle_path_selects_newest_version(plan_context):
    """resolve_bundle_path must return the newest version dir, not the first."""
    mock_root = plan_context.fixture_dir / 'multi-version-cache'
    subpath = 'skills/test-skill/SKILL.md'
    old = mock_root / 'test-bundle' / '1.0.0' / 'skills' / 'test-skill' / 'SKILL.md'
    new = mock_root / 'test-bundle' / '1.0.10' / 'skills' / 'test-skill' / 'SKILL.md'
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_text('# old')
    new.write_text('# new')

    result = resolve_bundle_path(mock_root, 'test-bundle', subpath)
    # '1.0.10' -> (1, 0, 10) sorts newer than '1.0.0' -> (1, 0, 0), so the newest
    # version dir wins over the lexically-first '1.0.0'.
    assert result == new


def test_resolve_bundle_path_not_found(plan_context):
    """Test resolve_bundle_path returns None for missing path."""
    mock_root = plan_context.fixture_dir / 'empty-cache'
    mock_root.mkdir(parents=True)

    result = resolve_bundle_path(mock_root, 'nonexistent', 'some/path.md')
    assert result is None


def _make_flat_plugin_root(root: Path, *, root_name: str = 'skills', manifest: str = 'opencode.json') -> Path:
    """Build a real flat deployed plugin root and return its skill root.

    ``root_name`` selects the skill-root spelling, and ``manifest`` the target
    marker, so the fixtures cover every combination — including the singular
    spelling, which only a not-yet-installed generated root carries. The
    manifest is written AFTER the skill tree so the root directory exists first.
    """
    skills_root = root / root_name
    skill_dir = skills_root / 'test-bundle-test-skill'
    (skill_dir / 'scripts').mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# Test Skill')
    (skill_dir / 'scripts' / 'run.py').write_text('# script')
    (root / manifest).write_text('{}')
    return skills_root


# =============================================================================
# Flat deployed layout — the shape the OpenCode and Antigravity targets ship
# =============================================================================


def test_resolve_bundle_path_reads_the_deployed_plural_root(plan_context):
    """A flat deployed root resolves the nested-layout subpath against its own spelling.

    No case here covered this shape before: the nested population above needs a
    ``{bundle}/`` directory, which a flat deployment does not have, so every one
    of them returned ``None`` or a constructed path against a real deployment.
    """
    root = plan_context.fixture_dir / 'flat-plural'
    skills_root = _make_flat_plugin_root(root, root_name='skills')

    result = resolve_bundle_path(root, 'test-bundle', 'skills/test-skill/SKILL.md')

    assert result == skills_root / 'test-bundle-test-skill' / 'SKILL.md'
    assert result.is_file()


def test_resolve_bundle_path_reads_the_deployed_plural_root_with_the_claude_manifest(plan_context):
    """The plural root resolves under EITHER target manifest.

    The two former legs gated on one manifest each — ``plugin.json`` for the
    plural leg, ``opencode.json`` for the singular one — so a deployment carrying
    the other manifest found nothing. The manifest identifies the root; it does
    not decide the shape.
    """
    root = plan_context.fixture_dir / 'flat-plural-claude-manifest'
    skills_root = _make_flat_plugin_root(root, root_name='skills', manifest='plugin.json')

    result = resolve_bundle_path(root, 'test-bundle', 'skills/test-skill/SKILL.md')

    assert result == skills_root / 'test-bundle-test-skill' / 'SKILL.md'


def test_resolve_bundle_path_reads_the_singular_generated_root(plan_context):
    """The generated singular tree resolves through the same call.

    The emitter writes ``skill/`` and ``install.sh`` maps it to ``skills/``, so a
    target tree that has not been installed yet carries the singular spelling and
    used to fall through both former legs.
    """
    root = plan_context.fixture_dir / 'flat-singular'
    skills_root = _make_flat_plugin_root(root, root_name='skill')

    result = resolve_bundle_path(root, 'test-bundle', 'skills/test-skill/SKILL.md')

    assert result == skills_root / 'test-bundle-test-skill' / 'SKILL.md'


def test_resolve_bundle_path_reads_a_plural_root_with_no_manifest(plan_context):
    """The skill root alone identifies a flat root, with no manifest beside it.

    The narrowest of the three shapes the former legs could not all cover: the
    gate is "is this a target root", and a skill root answers that on its own.
    """
    root = plan_context.fixture_dir / 'flat-no-manifest'
    skills_root = root / 'skills' / 'test-bundle-test-skill'
    skills_root.mkdir(parents=True)
    (skills_root / 'SKILL.md').write_text('# Test Skill')

    assert resolve_bundle_path(root, 'test-bundle', 'skills/test-skill/SKILL.md') == skills_root / 'SKILL.md'


def test_resolve_bundle_path_reads_a_script_inside_a_flat_skill(plan_context):
    """A sub-path below the skill resolves too, not only the skill root itself.

    ``skills/{skill}/scripts/{script}.py`` is the shape the executor's own path
    helpers use, so a resolver that handled only the bare skill directory would
    still leave the executor unable to find a script.
    """
    root = plan_context.fixture_dir / 'flat-script'
    skills_root = _make_flat_plugin_root(root, root_name='skills')

    result = resolve_bundle_path(root, 'test-bundle', 'skills/test-skill/scripts/run.py')

    assert result == skills_root / 'test-bundle-test-skill' / 'scripts' / 'run.py'
    assert result.is_file()


def test_resolve_bundle_path_prefers_the_deployed_plural_over_singular(plan_context):
    """With both spellings present, the deployed one answers.

    Each spelling carries a DIFFERENT file, so a reader that probed singular
    first would resolve against the wrong root.
    """
    root = plan_context.fixture_dir / 'flat-both'
    plural = root / 'skills' / 'test-bundle-plural-skill'
    singular = root / 'skill' / 'test-bundle-singular-skill'
    for skill_dir in (plural, singular):
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('# skill')
    (root / 'opencode.json').write_text('{}')

    assert resolve_bundle_path(root, 'test-bundle', 'skills/plural-skill/SKILL.md') == plural / 'SKILL.md'
    assert resolve_bundle_path(root, 'test-bundle', 'skills/singular-skill/SKILL.md') == singular / 'SKILL.md'


def test_resolve_bundle_path_resolves_a_root_anchored_path_on_a_flat_root(plan_context):
    """A non-skill-anchored subpath still resolves against the root.

    The former legs carried this ``elif`` beside the flat probe, so it must keep
    working: ``agents/foo.md`` is addressed from the root, not from a skill
    directory, and dropping it would regress a path shape that resolved before.
    """
    root = plan_context.fixture_dir / 'flat-root-anchored'
    _make_flat_plugin_root(root, root_name='skills')
    agent = root / 'agents' / 'some-agent.md'
    agent.parent.mkdir(parents=True)
    agent.write_text('# agent')

    assert resolve_bundle_path(root, 'test-bundle', 'agents/some-agent.md') == agent


def test_resolve_bundle_path_on_a_flat_root_returns_none_for_a_miss(plan_context):
    """A flat root with no matching skill still reports ``None``.

    The flat leg is a probe: it must not fabricate a path. This verb's contract
    is ``None`` for a miss, and a constructed path here would make every
    diagnostic name a file that was never there.
    """
    root = plan_context.fixture_dir / 'flat-miss'
    _make_flat_plugin_root(root, root_name='skills')

    assert resolve_bundle_path(root, 'test-bundle', 'skills/absent-skill/SKILL.md') is None


def test_resolve_bundle_path_on_a_nested_root_is_unchanged(plan_context):
    """A nested root still resolves through its own version-dir selection.

    The flat leg is a fallback for the branch where the bundle directory does
    not exist; a root that HAS one must be unaffected, including its
    newest-version-dir behaviour.
    """
    mock_root = plan_context.fixture_dir / 'flat-fallback-nested'
    old = mock_root / 'test-bundle' / '1.0.0' / 'skills' / 'test-skill' / 'SKILL.md'
    new = mock_root / 'test-bundle' / '1.0.10' / 'skills' / 'test-skill' / 'SKILL.md'
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_text('# old')
    new.write_text('# new')

    assert resolve_bundle_path(mock_root, 'test-bundle', 'skills/test-skill/SKILL.md') == new


def test_state_read_empty(plan_context):
    """Test reading state when no state file exists."""
    state = read_state()
    assert state == {} or 'plugin_root' not in state


def test_state_write_creates_directory(plan_context):
    """Test that write_state creates parent directories."""
    write_state({'plugin_root': '/test/path'})
    state = read_state()
    assert state['plugin_root'] == '/test/path'


# =============================================================================
# Bootstrap isolation tests -- verify scripts work WITHOUT executor PYTHONPATH
# =============================================================================


def _run_without_marketplace_pythonpath(script_path: Path, *args: str) -> 'subprocess.CompletedProcess':
    """Run a script with a clean PYTHONPATH (no marketplace dirs).

    This simulates the real bootstrap scenario where the executor hasn't been
    generated yet and PYTHONPATH hasn't been set up by conftest.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    return subprocess.run(
        [sys.executable, str(script_path)] + list(args),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_bootstrap_plugin_imports_without_executor_pythonpath():
    """bootstrap_plugin.py must resolve its own imports without executor PYTHONPATH."""
    result = _run_without_marketplace_pythonpath(SCRIPT_PATH, 'get-root')
    assert result.returncode == 0, f'bootstrap_plugin.py failed without PYTHONPATH:\n{result.stderr}'


def test_determine_mode_imports_without_executor_pythonpath():
    """determine_mode.py must resolve its own imports without executor PYTHONPATH."""
    script = _SCRIPTS_DIR / 'determine_mode.py'
    result = _run_without_marketplace_pythonpath(script, 'mode')
    assert result.returncode in (0, 1), f'determine_mode.py failed without PYTHONPATH:\n{result.stderr}'
    assert 'ModuleNotFoundError' not in result.stderr, f'determine_mode.py has unresolved imports:\n{result.stderr}'


def test_gitignore_setup_imports_without_executor_pythonpath():
    """gitignore_setup.py must resolve its own imports without executor PYTHONPATH."""
    script = _SCRIPTS_DIR / 'gitignore_setup.py'
    result = _run_without_marketplace_pythonpath(script, '--dry-run')
    assert result.returncode == 0, f'gitignore_setup.py failed without PYTHONPATH:\n{result.stderr}'


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing and env-dependent
# =============================================================================


def test_get_root_detects_plugin():
    """Test get-root succeeds when plugin cache exists (env-dependent)."""
    cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
    if not cache_dir.exists():
        result = run_script(SCRIPT_PATH, 'get-root')
        assert result.success, 'Expected exit 0 with error status in TOON'
        assert 'status: error' in result.stdout
        assert 'not found' in result.stdout.lower() or 'error' in result.stdout.lower()
        return

    result = run_script(SCRIPT_PATH, 'get-root')
    assert result.success, f'get-root failed: {result.stderr}'
    assert 'plugin_root' in result.stdout


def test_get_root_with_refresh(plan_context):
    """Test get-root --refresh forces re-detection (env-dependent)."""
    result = run_script(SCRIPT_PATH, 'get-root', '--refresh')
    assert result.returncode == 0


def test_get_root_caches_result(plan_context):
    """Test that get-root caches the result in marshall-state.toon (env-dependent)."""
    result = run_script(SCRIPT_PATH, 'get-root')
    assert result.returncode == 0

    # Only verify cache when operation found the plugin root
    if 'status: success' in result.stdout:
        state_file = plan_context.fixture_dir / 'marshall-state.toon'
        assert state_file.exists(), 'State file should be created after successful get-root'
        content = state_file.read_text()
        assert 'plugin_root' in content
