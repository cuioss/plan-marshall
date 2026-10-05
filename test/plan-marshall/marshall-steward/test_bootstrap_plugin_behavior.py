#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for bootstrap_plugin.py detection logic.

The existing bootstrap_plugin suite covers state I/O and a couple of subprocess
smokes. This module exercises the remaining detection surface in-process —
runtime-target reading, Claude/OpenCode plugin-root detection, the cache/detect
flow in ``get_plugin_root``, the resolve helper, and the command handlers plus
``main()`` dispatch — so those branches are covered. Plugin-root probing is
driven with monkeypatched ``Path.home`` / tmp directory layouts so no real
plugin cache is consulted, and state writes are redirected into ``tmp_path``.

The resolve-helper cases at the end build REAL flat deployed trees. The two
cases that preceded them could not: the flat legs they exercised gated on one
target manifest each and looked for a skill root whose name the deployed
OpenCode tree does not carry, so the shape a target actually ships had no case
in the suite at all.
"""

import argparse
import json
from pathlib import Path

import pytest

from conftest import load_script_module

bp = load_script_module('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py', 'bootstrap_plugin_behavior_cov')


@pytest.fixture
def bp_env(tmp_path, monkeypatch):
    """Redirect bootstrap state resolution into an isolated tmp directory."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('PLAN_DIR_NAME', '.plan')
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    return tmp_path


# =============================================================================
# read_runtime_target
# =============================================================================


def test_read_runtime_target_defaults_to_claude_when_absent(outside_repo_dir: Path):
    """read_runtime_target falls back to 'claude' when no local config is found."""
    assert bp.read_runtime_target(cwd=str(outside_repo_dir)) == 'claude'


def test_read_runtime_target_reads_local_harness_config(outside_repo_dir: Path):
    """read_runtime_target returns target from machine-local harness config."""
    harness = outside_repo_dir / '.plan' / 'local' / 'harness'
    harness.mkdir(parents=True)
    (harness / 'opencode.json').write_text(json.dumps({'schema_version': 1, 'harness': 'opencode'}), encoding='utf-8')

    assert bp.read_runtime_target(cwd=str(outside_repo_dir)) == 'opencode'


def test_read_runtime_target_reads_run_configuration(outside_repo_dir: Path):
    """read_runtime_target returns target from machine-local run-configuration.json."""
    plan = outside_repo_dir / '.plan'
    plan.mkdir(parents=True)
    (plan / 'run-configuration.json').write_text(json.dumps({'runtime': {'target': 'antigravity'}}), encoding='utf-8')

    assert bp.read_runtime_target(cwd=str(outside_repo_dir)) == 'antigravity'


def test_read_runtime_target_ignores_shared_marshal_json(outside_repo_dir: Path):
    """read_runtime_target ignores runtime.target in shared marshal.json."""
    plan = outside_repo_dir / '.plan'
    plan.mkdir(parents=True)
    (plan / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8')

    assert bp.read_runtime_target(cwd=str(outside_repo_dir)) == 'claude'


# =============================================================================
# read_runtime_target — env-var detection (tier 1)
# =============================================================================


def test_read_runtime_target_detects_antigravity_from_env(tmp_path: Path, monkeypatch):
    """read_runtime_target returns 'antigravity' when ANTIGRAVITY_AGENT is set."""
    monkeypatch.setenv('ANTIGRAVITY_AGENT', '1')
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'antigravity'


def test_read_runtime_target_detects_claude_from_env(tmp_path: Path, monkeypatch):
    """read_runtime_target returns 'claude' when CLAUDE_CODE_SESSION_ID is set."""
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('OPENCODE', raising=False)
    monkeypatch.delenv('OPENCODE_PID', raising=False)
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'test-session-id')
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'claude'


def test_read_runtime_target_detects_opencode_from_env(tmp_path: Path, monkeypatch):
    """read_runtime_target returns 'opencode' when OPENCODE is set."""
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.delenv('OPENCODE_PID', raising=False)
    monkeypatch.setenv('OPENCODE', '1')
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'opencode'


def test_read_runtime_target_detects_opencode_pid_from_env(tmp_path: Path, monkeypatch):
    """read_runtime_target returns 'opencode' when OPENCODE_PID is set."""
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.delenv('OPENCODE', raising=False)
    monkeypatch.setenv('OPENCODE_PID', '12345')
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'opencode'


def test_read_runtime_target_antigravity_precedence_over_opencode(tmp_path: Path, monkeypatch):
    """ANTIGRAVITY_AGENT wins over OPENCODE signals."""
    monkeypatch.setenv('ANTIGRAVITY_AGENT', '1')
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'test-session-id')
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'antigravity'


def test_read_runtime_target_opencode_precedence_over_claude(tmp_path: Path, monkeypatch):
    """OPENCODE wins over CLAUDE_CODE_SESSION_ID."""
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'test-session-id')
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'opencode'


def test_read_runtime_target_opencode_env_takes_precedence_over_local_config(outside_repo_dir: Path, monkeypatch):
    """OPENCODE env signal (tier 1) wins over local config (tier 2)."""
    harness = outside_repo_dir / '.plan' / 'local' / 'harness'
    harness.mkdir(parents=True)
    (harness / 'claude.json').write_text(json.dumps({'schema_version': 1, 'harness': 'claude'}), encoding='utf-8')
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.delenv('OPENCODE_PID', raising=False)
    monkeypatch.setenv('OPENCODE', '1')
    assert bp.read_runtime_target(cwd=str(outside_repo_dir)) == 'opencode'


def test_cmd_get_root_auto_detect_returns_opencode_target(tmp_path: Path, monkeypatch):
    """cmd_get_root auto-detect returns target opencode without --target or config."""
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.delenv('OPENCODE_PID', raising=False)
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (Path('/opencode-root'), 'detected'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target=None))

    assert result['status'] == 'success'
    assert result['target'] == 'opencode'


def test_cmd_get_root_opencode_bypasses_targetless_cache(bp_env, tmp_path: Path, monkeypatch):
    """cmd_get_root on OpenCode bypasses a targetless cached root via detection."""
    cached = tmp_path / 'cached-root'
    cached.mkdir()
    bp.write_state({'plugin_root': str(cached)})
    monkeypatch.delenv('ANTIGRAVITY_AGENT', raising=False)
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.delenv('OPENCODE_PID', raising=False)
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.chdir(tmp_path)
    fresh = tmp_path / 'opencode-root'
    fresh.mkdir()
    calls: dict = {}

    def fake_detect(target=None):
        calls['target'] = target
        return fresh

    monkeypatch.setattr(bp, 'detect_plugin_root', fake_detect)

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target=None))

    assert calls.get('target') == 'opencode'
    assert result['status'] == 'success'
    assert result['plugin_root'] == str(fresh)
    assert result['target'] == 'opencode'
    assert result['source'] == 'detected'


def test_read_runtime_target_env_takes_precedence_over_marshal(tmp_path: Path, monkeypatch):
    """Env var detection (tier 1) wins over marshal.json config (tier 2)."""
    plan = tmp_path / '.plan'
    plan.mkdir()
    (plan / 'marshal.json').write_text('{"runtime": {"target": "claude"}}')

    monkeypatch.setenv('ANTIGRAVITY_AGENT', '1')
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'antigravity'


# =============================================================================
# detect_plugin_root — fallback probing (tier 3)
# =============================================================================


def test_detect_plugin_root_fallback_probes_antigravity(monkeypatch):
    """When Claude root is None, detect_plugin_root falls back to Antigravity."""
    monkeypatch.setattr(bp, 'read_runtime_target', lambda: 'claude')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: None)
    sentinel = Path('/fake/antigravity-fallback')
    monkeypatch.setattr(bp, '_detect_antigravity_root', lambda: sentinel)
    monkeypatch.setattr(bp, '_detect_opencode_root', lambda: None)

    assert bp.detect_plugin_root() == sentinel


def test_detect_plugin_root_fallback_probes_opencode(monkeypatch):
    """When Claude and Antigravity roots are None, falls back to OpenCode."""
    monkeypatch.setattr(bp, 'read_runtime_target', lambda: 'claude')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: None)
    monkeypatch.setattr(bp, '_detect_antigravity_root', lambda: None)
    sentinel = Path('/fake/opencode-fallback')
    monkeypatch.setattr(bp, '_detect_opencode_root', lambda: sentinel)

    assert bp.detect_plugin_root() == sentinel


def test_detect_plugin_root_explicit_claude_target_never_falls_back(monkeypatch):
    """An explicit target='claude' returns None on a miss — never another runtime's root."""
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: None)
    monkeypatch.setattr(bp, '_detect_antigravity_root', lambda: Path('/fake/antigravity-fallback'))
    monkeypatch.setattr(bp, '_detect_opencode_root', lambda: Path('/fake/opencode-fallback'))

    assert bp.detect_plugin_root(target='claude') is None


# =============================================================================
# _detect_claude_root
# =============================================================================


@pytest.fixture
def claude_roots(tmp_path: Path):
    """Stub the runtime-resolved bundle-cache roots at a tmp plugin-cache root.

    ``_detect_claude_root`` derives its cache base from
    ``get_bundle_cache_roots()`` rather than a hardcoded ``~/.claude`` literal,
    so detection tests must stub the op output — not ``Path.home``.
    """
    base = tmp_path / '.claude' / 'plugins' / 'cache'
    return lambda: (str(base / 'plan-marshall'),)


def test_detect_claude_root_none_when_cache_absent(tmp_path: Path, monkeypatch, claude_roots):
    """_detect_claude_root returns None when the plugin cache does not exist."""
    monkeypatch.setattr(bp, 'get_bundle_cache_roots', claude_roots)

    assert bp._detect_claude_root() is None


def test_detect_claude_root_finds_marker(tmp_path: Path, monkeypatch, claude_roots):
    """_detect_claude_root returns the plugin dir holding a bundle marker file."""
    monkeypatch.setattr(bp, 'get_bundle_cache_roots', claude_roots)
    version_dir = tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'plan-marshall' / '1.0.0'
    marker = version_dir / '.claude-plugin'
    marker.mkdir(parents=True)
    (marker / 'plugin.json').write_text('{}')

    root = bp._detect_claude_root()

    assert root is not None
    assert root.name == 'plan-marshall'


def test_detect_claude_root_none_without_marker(tmp_path: Path, monkeypatch, claude_roots):
    """_detect_claude_root returns None when no bundle carries the marker file."""
    monkeypatch.setattr(bp, 'get_bundle_cache_roots', claude_roots)
    (tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'bundle' / '1.0.0').mkdir(parents=True)

    assert bp._detect_claude_root() is None


# =============================================================================
# _detect_opencode_root
# =============================================================================


def test_detect_opencode_root_via_absolute_root(tmp_path: Path, monkeypatch):
    """_detect_opencode_root finds a plan-marshall skill under a user-global root."""
    cfg = tmp_path / 'cfg'
    skills = cfg / 'skills'
    (skills / 'plan-marshall-core').mkdir(parents=True)
    monkeypatch.setattr(bp, 'get_project_skill_roots', lambda: (str(skills),))
    monkeypatch.chdir(tmp_path)

    root = bp._detect_opencode_root()

    assert root is not None
    assert root == skills.resolve()


def test_detect_opencode_root_via_relative_root(tmp_path: Path, monkeypatch):
    """_detect_opencode_root finds a plan-marshall skill under .opencode/skills."""
    monkeypatch.setattr(bp, 'get_project_skill_roots', lambda: ('.opencode/skills',))
    work = tmp_path / 'work'
    (work / '.opencode' / 'skills' / 'plan-marshall-x').mkdir(parents=True)
    monkeypatch.chdir(work)

    root = bp._detect_opencode_root()

    assert root is not None
    assert root.name == 'skills'


def test_detect_opencode_root_none_when_no_skills(tmp_path: Path, monkeypatch):
    """_detect_opencode_root returns None when no discovery root carries a skill."""
    monkeypatch.setattr(bp, 'get_project_skill_roots', lambda: ('.opencode/skills', '.claude/skills'))
    monkeypatch.setattr(bp, 'get_bundle_cache_roots', lambda: ())
    empty = tmp_path / 'empty-work'
    empty.mkdir()
    monkeypatch.chdir(empty)

    assert bp._detect_opencode_root() is None


# =============================================================================
# detect_plugin_root dispatch
# =============================================================================


def test_detect_plugin_root_routes_to_opencode(monkeypatch):
    """detect_plugin_root delegates to the OpenCode resolver for that target."""
    sentinel = Path('/fake/opencode')
    monkeypatch.setattr(bp, '_detect_opencode_root', lambda: sentinel)

    assert bp.detect_plugin_root(target='opencode') == sentinel


def test_detect_plugin_root_routes_to_claude(monkeypatch):
    """detect_plugin_root delegates to the Claude resolver for that target."""
    sentinel = Path('/fake/claude')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: sentinel)

    assert bp.detect_plugin_root(target='claude') == sentinel


def test_detect_plugin_root_auto_reads_runtime_target(monkeypatch):
    """detect_plugin_root resolves the target from marshal.json when omitted."""
    monkeypatch.setattr(bp, 'read_runtime_target', lambda: 'claude')
    sentinel = Path('/fake/auto')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: sentinel)

    assert bp.detect_plugin_root() == sentinel


# =============================================================================
# get_plugin_root
# =============================================================================


def test_get_plugin_root_returns_cached(bp_env, tmp_path):
    """get_plugin_root returns a still-existing cached root with source 'cached'."""
    cached = tmp_path / 'cached-root'
    cached.mkdir()
    bp.write_state({'plugin_root': str(cached)})

    root, source = bp.get_plugin_root(target='claude')

    assert root == cached
    assert source == 'cached'


def test_get_plugin_root_redetects_when_cache_stale(bp_env, tmp_path, monkeypatch):
    """get_plugin_root re-detects when the cached path no longer exists."""
    bp.write_state({'plugin_root': str(tmp_path / 'gone')})
    fresh = tmp_path / 'fresh'
    fresh.mkdir()
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: fresh)

    root, source = bp.get_plugin_root(target='claude')

    assert root == fresh
    assert source == 'detected'


def test_get_plugin_root_detected_persists_state(bp_env, tmp_path, monkeypatch):
    """get_plugin_root caches a freshly detected root into the state file."""
    fresh = tmp_path / 'detected'
    fresh.mkdir()
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: fresh)

    root, source = bp.get_plugin_root(refresh=True, target='claude')

    assert root == fresh
    assert source == 'detected'
    assert bp.read_state()['plugin_root'] == str(fresh)


def test_get_plugin_root_not_found(bp_env, monkeypatch):
    """get_plugin_root reports 'not_found' when detection yields nothing."""
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: None)

    root, source = bp.get_plugin_root(refresh=True, target='claude')

    assert root is None
    assert source == 'not_found'


# =============================================================================
# resolve_bundle_path (extra branch)
# =============================================================================


def test_resolve_bundle_path_none_when_subpath_missing(tmp_path: Path):
    """resolve_bundle_path returns None when the bundle exists but the subpath does not."""
    root = tmp_path / 'cache'
    (root / 'plan-marshall' / '1.0.0').mkdir(parents=True)

    assert bp.resolve_bundle_path(root, 'plan-marshall', 'skills/missing/SKILL.md') is None


# =============================================================================
# resolve_bundle_path — the flat deployed shape
# =============================================================================
#
# Real trees, not constructed paths. The two former flat legs differed only in
# which target manifest gated them and whether the skill root was spelled
# ``skills/`` or ``skill/``, and the second pair could never fire: the deployed
# OpenCode root carries the PLURAL spelling, because the emitter writes a
# singular ``skill/`` tree and ``install.sh`` maps it to the plural at install
# time. Every case below is a shape at least one of those two legs missed.


def _flat_plugin_root(root: Path, *, root_name: str = 'skills', manifest: str | None = 'opencode.json') -> Path:
    """Build a real flat deployed plugin root and return the skill directory.

    The manifest is written AFTER the skill tree, so the root directory exists
    before the file lands in it.
    """
    skill_dir = root / root_name / 'plan-marshall-manage-status'
    (skill_dir / 'scripts').mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# skill')
    (skill_dir / 'scripts' / 'manage-status.py').write_text('# script')
    if manifest is not None:
        (root / manifest).write_text('{}')
    return skill_dir


@pytest.mark.parametrize(
    ('root_name', 'manifest'),
    [
        ('skills', 'opencode.json'),
        ('skills', 'plugin.json'),
        ('skills', None),
        ('skill', 'opencode.json'),
        ('skill', None),
    ],
    ids=[
        'deployed-plural-opencode-manifest',
        'deployed-plural-claude-manifest',
        'deployed-plural-no-manifest',
        'generated-singular-opencode-manifest',
        'generated-singular-no-manifest',
    ],
)
def test_flat_root_resolves_every_shape_a_target_deploys(tmp_path: Path, root_name: str, manifest):
    """Every root shape a target produces resolves, and resolves to a real file.

    The manifest rows are the discrimination: the former legs gated the plural
    root on ``plugin.json`` and the singular one on ``opencode.json``, so each
    spelling resolved under exactly one of the two manifests. A reader that kept
    that split fails the complementary rows.
    """
    root = tmp_path / f'root-{root_name}-{manifest}'
    skill_dir = _flat_plugin_root(root, root_name=root_name, manifest=manifest)

    resolved = bp.resolve_bundle_path(root, 'plan-marshall', 'skills/manage-status/SKILL.md')

    assert resolved == skill_dir / 'SKILL.md'
    assert resolved.is_file()


def test_flat_root_resolves_a_script_below_the_skill(tmp_path: Path):
    """``skills/{skill}/scripts/{script}.py`` resolves, not only the skill root.

    This is the shape the executor's own path helpers ask for, so a resolver that
    handled only the bare skill directory would still leave the executor unable
    to find a script on a flat deployment.
    """
    root = tmp_path / 'root-script'
    skill_dir = _flat_plugin_root(root, root_name='skills')

    resolved = bp.resolve_bundle_path(root, 'plan-marshall', 'skills/manage-status/scripts/manage-status.py')

    assert resolved == skill_dir / 'scripts' / 'manage-status.py'


def test_flat_root_prefers_the_deployed_plural_spelling(tmp_path: Path):
    """With both spellings present, the deployed one answers.

    Each spelling carries a DIFFERENT file, so a reader probing singular-first
    would resolve against the wrong root and fail here.
    """
    root = tmp_path / 'root-both'
    plural = root / 'skills' / 'plan-marshall-plural-skill'
    singular = root / 'skill' / 'plan-marshall-singular-skill'
    for skill_dir in (plural, singular):
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('# skill')
    (root / 'opencode.json').write_text('{}')

    assert bp.resolve_bundle_path(root, 'plan-marshall', 'skills/plural-skill/SKILL.md') == plural / 'SKILL.md'
    assert bp.resolve_bundle_path(root, 'plan-marshall', 'skills/singular-skill/SKILL.md') == singular / 'SKILL.md'


def test_flat_root_still_resolves_a_root_anchored_path(tmp_path: Path):
    """A non-skill-anchored subpath resolves against the root.

    A consumer pointing at ``agents/foo.md`` is not asking about a skill at all,
    so the root-anchored shape has to keep resolving alongside the flat
    skill-anchored one.
    """
    root = tmp_path / 'root-anchored'
    _flat_plugin_root(root, root_name='skills')
    agent = root / 'agents' / 'an-agent.md'
    agent.parent.mkdir(parents=True)
    agent.write_text('# agent')

    assert bp.resolve_bundle_path(root, 'plan-marshall', 'agents/an-agent.md') == agent


def test_flat_root_reports_a_miss_as_none_rather_than_a_constructed_path(tmp_path: Path):
    """A flat root with no matching skill yields ``None``.

    This verb's contract is ``None`` for a miss. A resolver that returned the
    nested-shaped construction on a flat root would make every diagnostic name a
    path that was never there, and the caller could not tell it apart from a hit.
    """
    root = tmp_path / 'root-miss'
    _flat_plugin_root(root, root_name='skills')

    assert bp.resolve_bundle_path(root, 'plan-marshall', 'skills/absent-skill/SKILL.md') is None


def test_the_two_former_flat_legs_are_gone(tmp_path: Path, monkeypatch):
    """``resolve_bundle_path`` holds ONE flat leg, not two near-duplicates.

    Asserted on behaviour rather than on the source text: the two legs differed
    only in the manifest that gated them and the skill-root spelling they
    probed, and a body carrying both would satisfy every case above by
    construction. Counting the flat probes through the shared resolver is what
    makes the collapse observable — a body that re-probed per manifest would
    call the shared resolver more than once for a single lookup.
    """
    calls: list[tuple[str, str]] = []
    real = bp.resolve_skill_path

    def _recording(plugin_root, bundle, relative_path):
        calls.append((bundle, relative_path))
        return real(plugin_root, bundle, relative_path)

    monkeypatch.setattr(bp, 'resolve_skill_path', _recording)

    root = tmp_path / 'root-once'
    _flat_plugin_root(root, root_name='skills', manifest=None)
    bp.resolve_bundle_path(root, 'plan-marshall', 'skills/manage-status/SKILL.md')

    assert len(calls) == 1, f'one lookup must probe the shared resolver once, not once per former leg: {calls}'


# =============================================================================
# cmd_get_root / cmd_resolve
# =============================================================================


def test_cmd_get_root_success(monkeypatch):
    """cmd_get_root returns a success envelope with the resolved plugin root."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (Path('/p'), 'detected'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='claude'))

    assert result['status'] == 'success'
    assert result['plugin_root'] == '/p'
    assert result['target'] == 'claude'


def test_cmd_get_root_error_claude_hint(monkeypatch):
    """cmd_get_root returns an error with the Claude-specific hint when not found."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (None, 'not_found'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='claude'))

    assert result['status'] == 'error'
    assert 'Claude Code' in result['hint']


def test_cmd_get_root_error_opencode_hint(monkeypatch):
    """cmd_get_root returns the OpenCode-specific hint when not found for that target."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (None, 'not_found'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='opencode'))

    assert result['status'] == 'error'
    assert 'OpenCode' in result['hint']


def test_cmd_resolve_plugin_not_found(monkeypatch):
    """cmd_resolve errors when the plugin root cannot be resolved."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (None, 'not_found'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='b', path='p'))

    assert result['status'] == 'error'
    assert result['error'] == 'Plugin root not found'


def test_cmd_resolve_success(tmp_path: Path, monkeypatch):
    """cmd_resolve returns the resolved path for an existing bundle subpath."""
    root = tmp_path / 'cache'
    target = root / 'plan-marshall' / '1.0.0' / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('# skill')
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='plan-marshall', path='skills/s/SKILL.md'))

    assert result['status'] == 'success'
    assert result['resolved_path'] == str(target)


def test_cmd_resolve_path_not_found(tmp_path: Path, monkeypatch):
    """cmd_resolve errors when the bundle resolves but the subpath is absent."""
    root = tmp_path / 'cache'
    (root / 'plan-marshall' / '1.0.0').mkdir(parents=True)
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='plan-marshall', path='skills/x/SKILL.md'))

    assert result['status'] == 'error'
    assert 'Path not found' in result['error']


# =============================================================================
# main() dispatch (safe_main wraps with sys.exit)
# =============================================================================


def test_main_get_root_dispatch(monkeypatch, capsys):
    """main() routes 'get-root' and emits the resolved root as TOON."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (Path('/root'), 'detected'))
    monkeypatch.setattr(bp, 'read_runtime_target', lambda *a, **k: 'claude')
    monkeypatch.setattr('sys.argv', ['bootstrap_plugin', 'get-root'])

    with pytest.raises(SystemExit) as exc:
        bp.main()

    assert exc.value.code in (0, None)
    assert 'plugin_root' in capsys.readouterr().out


def test_main_resolve_dispatch(tmp_path: Path, monkeypatch, capsys):
    """main() routes 'resolve' and emits the resolved path as TOON."""
    root = tmp_path / 'cache'
    target = root / 'plan-marshall' / '1.0.0' / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('# skill')
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))
    monkeypatch.setattr(
        'sys.argv',
        ['bootstrap_plugin', 'resolve', '--bundle', 'plan-marshall', '--path', 'skills/s/SKILL.md'],
    )

    with pytest.raises(SystemExit) as exc:
        bp.main()

    assert exc.value.code in (0, None)
    assert 'resolved_path' in capsys.readouterr().out


# =============================================================================
# Antigravity target tests
# =============================================================================


def test_detect_antigravity_root_workspace(tmp_path: Path, monkeypatch):
    """_detect_antigravity_root finds workspace plugin under .agents/plugins/plan-marshall."""
    ws = tmp_path / 'ws'
    plugin_dir = ws / '.agents' / 'plugins' / 'plan-marshall'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text('{"name": "plan-marshall"}')
    monkeypatch.chdir(ws)

    root = bp._detect_antigravity_root()
    assert root == plugin_dir


def test_detect_antigravity_root_global(tmp_path: Path, monkeypatch):
    """_detect_antigravity_root finds global plugin under <gemini_config>/plugins/plan-marshall."""
    cfg = tmp_path / 'gemini' / 'config'
    plugin_dir = cfg / 'plugins' / 'plan-marshall'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text('{"name": "plan-marshall"}')
    monkeypatch.setenv('GEMINI_CONFIG_DIR', str(cfg))
    empty_ws = tmp_path / 'empty'
    empty_ws.mkdir()
    monkeypatch.chdir(empty_ws)

    root = bp._detect_antigravity_root()
    assert root == plugin_dir


def test_detect_plugin_root_routes_to_antigravity(monkeypatch):
    """detect_plugin_root delegates to the Antigravity resolver for that target."""
    sentinel = Path('/fake/antigravity')
    monkeypatch.setattr(bp, '_detect_antigravity_root', lambda: sentinel)

    assert bp.detect_plugin_root(target='antigravity') == sentinel


def test_resolve_bundle_path_antigravity_flat_layout(tmp_path: Path):
    """resolve_bundle_path resolves skills in Antigravity flat directory layout."""
    plugin_root = tmp_path / 'plugin'
    skill_dir = plugin_root / 'skills' / 'plan-marshall-manage-tasks'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# Tasks')
    (plugin_root / 'plugin.json').write_text('{"name": "plan-marshall"}')

    resolved = bp.resolve_bundle_path(plugin_root, 'plan-marshall', 'skills/manage-tasks/SKILL.md')
    assert resolved == skill_dir / 'SKILL.md'


def test_cmd_get_root_error_antigravity_hint(monkeypatch):
    """cmd_get_root returns the Antigravity-specific hint when not found for that target."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (None, 'not_found'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='antigravity'))

    assert result['status'] == 'error'
    assert 'gemini' in result['hint']


def test_resolve_bundle_path_opencode_singular_layout(tmp_path: Path):
    """resolve_bundle_path resolves skills in OpenCode singular directory layout."""
    plugin_root = tmp_path / 'plugin'
    skill_dir = plugin_root / 'skill' / 'plan-marshall-manage-tasks'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# Tasks')
    (plugin_root / 'opencode.json').write_text('{"$schema": "https://opencode.ai/config.json"}')

    resolved = bp.resolve_bundle_path(plugin_root, 'plan-marshall', 'skills/manage-tasks/SKILL.md')
    assert resolved == skill_dir / 'SKILL.md'
