# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode 2 shape pins for the emitter and its target data.

OpenCode 2 still accepts the OpenCode 1 shape through a normalizer, which is
why the drift stayed silent: the normalizer concatenates the legacy
``permission`` map BEFORE the ``permissions`` list, so a rule written beside a
list is overridden by that list's catch-all. These tests pin the emitted shape
itself rather than trusting the normalizer to reinterpret it.

Deliverable 1 covers the global config and the emitted agent frontmatter;
deliverable 2 covers the mapping's tool names and the skill directive.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.opencode.emitter import emit_bundles

#: Top-level keys OpenCode 2's ``Config.Info`` declares for the global
#: ``opencode.json``. A key outside this set is a shape the normalizer has to
#: interpret — the exact class of silent drift deliverable 1 closes.
OPENCODE2_CONFIG_KEYS = frozenset(
    {
        '$schema',
        'permissions',
        'agents',
        'skills',
        'commands',
        'instructions',
        'plugins',
    }
)


@pytest.fixture()
def opencode_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'opencode'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def bundle_root(tmp_path: Path) -> Path:
    """One bundle exercising a skill, an agent and a command."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps(
            {
                'name': 'demo',
                'version': '0.0.1',
                'description': 'Demo bundle',
                'agents': ['./agents/demo-agent.md'],
                'commands': ['./commands/demo-cmd.md'],
                'skills': ['./skills/demo-skill'],
            },
            indent=2,
        )
        + '\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n'
    )
    _write(
        bundle / 'agents' / 'demo-agent.md',
        '---\ndescription: an agent\ntools: Read, Write, Bash, Task\n---\nagent body\n',
    )
    _write(bundle / 'commands' / 'demo-cmd.md', '---\ndescription: a command\n---\ncmd body\n')
    return marketplace


def _frontmatter_block(path: Path) -> str:
    text = path.read_text(encoding='utf-8')
    assert text.startswith('---\n'), f'{path} carries no frontmatter block'
    end = text.find('\n---\n', 4)
    assert end != -1, f'{path} frontmatter block is unterminated'
    return text[4:end]


def _permissions(path: Path) -> list[dict[str, str]]:
    """Parse the emitted ``permissions`` list from an agent frontmatter block."""
    rules: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_block = False
    for raw in _frontmatter_block(path).splitlines():
        line = raw.rstrip()
        if line == 'permissions:':
            in_block = True
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if stripped.startswith('- '):
            if current is not None:
                rules.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None or ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        current[key.strip()] = value.strip().strip('"')
    if current is not None:
        rules.append(current)
    return rules


def _effect(rules: list[dict[str, str]], action: str) -> str:
    """OpenCode 2 evaluation: last matching rule wins, no match means ``ask``."""
    hits = [rule for rule in rules if rule['action'] == action]
    return hits[-1]['effect'] if hits else 'ask'


# ---------------------------------------------------------------------------
# D1 — the global config is written in the OpenCode 2 shape
# ---------------------------------------------------------------------------


def test_global_config_carries_only_opencode2_config_keys(bundle_root: Path, tmp_path: Path, opencode_config_dir: Path):
    """Every top-level key must be one OpenCode 2's ``Config.Info`` declares."""
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    config = json.loads((out / 'opencode.json').read_text(encoding='utf-8'))
    unknown = set(config) - OPENCODE2_CONFIG_KEYS
    assert not unknown, f'global config carries non-OpenCode-2 top-level keys: {sorted(unknown)}'
    assert 'agent' not in config, 'the OpenCode 1 singular `agent` map must not be emitted'
    assert 'agents' in config, 'the OpenCode 2 `agents` map must be emitted'


def test_global_config_skills_entry_names_the_installed_directory(
    bundle_root: Path, tmp_path: Path, opencode_config_dir: Path
):
    """The skills entry must name a directory the install really creates."""
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    config = json.loads((out / 'opencode.json').read_text(encoding='utf-8'))
    assert isinstance(config['skills'], list), 'OpenCode 2 `skills` is a list of directory strings'
    assert config['skills'], 'the skills list must name at least one directory'

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest)], check=True)

    for entry in config['skills']:
        resolved = (dest / entry).resolve()
        assert resolved.is_dir(), f'{entry!r} does not name a directory the install creates'
        assert list(resolved.glob('*/SKILL.md')), f'{entry!r} contains no installed skill'


# ---------------------------------------------------------------------------
# D1 — the emitted agent carries a permissions LIST, never a permission MAP
# ---------------------------------------------------------------------------


def test_emitted_agent_permissions_carry_action_resource_effect(
    bundle_root: Path, tmp_path: Path, opencode_config_dir: Path
):
    """Each rule is an OpenCode 2 ``{action, resource, effect}`` object."""
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    rules = _permissions(out / 'agent' / 'demo-agent.md')
    assert rules, 'the emitted agent must carry a permissions list'
    for rule in rules:
        assert set(rule) == {'action', 'resource', 'effect'}, f'not an OpenCode 2 rule: {rule}'
        assert rule['effect'] in {'allow', 'ask', 'deny'}


def test_emitted_agent_permissions_evaluate_like_the_source_tool_grants(
    bundle_root: Path, tmp_path: Path, opencode_config_dir: Path
):
    """Last-match-wins evaluation per tool equals the source ``tools:`` grant.

    The source grants ``Read, Write, Bash, Task``. Under OpenCode 2's tool
    names that is ``read``, ``edit`` (Write and Edit both map to ``edit``),
    ``shell`` and ``subagent``: each must evaluate to ``allow``. A tool the
    source did NOT grant must not evaluate to ``allow``.
    """
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    rules = _permissions(out / 'agent' / 'demo-agent.md')
    for granted in ('read', 'edit', 'shell', 'subagent'):
        assert _effect(rules, granted) == 'allow', f'{granted} is granted in source but not allowed after emit'
    for ungranted in ('webfetch', 'websearch', 'glob', 'grep'):
        assert _effect(rules, ungranted) != 'allow', f'{ungranted} is not granted in source but evaluates allow'


def test_emitted_files_carry_no_legacy_permission_map(bundle_root: Path, tmp_path: Path, opencode_config_dir: Path):
    """No emitted file may carry a top-level ``permission:`` map or a ``bash:`` key."""
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    offenders: list[str] = []
    for emitted in sorted(out.rglob('*.md')):
        for number, line in enumerate(emitted.read_text(encoding='utf-8').splitlines(), start=1):
            if line.startswith('permission:') or line.strip().startswith('bash:'):
                offenders.append(f'{emitted.relative_to(out)}:{number}: {line.strip()}')
    assert not offenders, 'OpenCode 1 permission map emitted:\n' + '\n'.join(offenders)


def test_install_prunes_the_opencode2_agents_map(tmp_path: Path, opencode_config_dir: Path):
    """The installer prunes agents of uninstalled bundles from OpenCode 2's ``agents`` map."""
    marketplace = tmp_path / 'bundles'
    for bundle, agent in (('plan-marshall', 'core-agent'), ('pm-dev-java', 'java-agent')):
        root = marketplace / bundle
        _write(
            root / '.claude-plugin' / 'plugin.json',
            json.dumps({'name': bundle, 'agents': [f'./agents/{agent}.md'], 'skills': [f'./skills/{agent}-skill']})
            + '\n',
        )
        _write(root / 'agents' / f'{agent}.md', '---\ndescription: an agent\ntools: Read\n---\nbody\n')
        # A skill makes the emitted tree self-identifying, so install.sh
        # installs the local emit instead of downloading the dist branch.
        _write(
            root / 'skills' / f'{agent}-skill' / 'SKILL.md',
            f'---\nname: {agent}-skill\ndescription: a skill\n---\nbody\n',
        )

    out = tmp_path / 'out'
    emit_bundles(marketplace, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    _write(
        dest / 'opencode.json',
        json.dumps(
            {'agents': {'core-agent': {}, 'java-agent': {}, 'user-agent': {'description': 'mine'}}},
            indent=2,
        )
        + '\n',
    )

    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--core-only'], check=True)

    agents = json.loads((dest / 'opencode.json').read_text(encoding='utf-8'))['agents']
    assert 'core-agent' in agents, 'the installed bundle agent must survive'
    assert 'java-agent' not in agents, 'an uninstalled bundle agent must be pruned'
    assert 'user-agent' in agents, 'a user-defined agent must be preserved'
