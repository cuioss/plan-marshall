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
import yaml

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


def _permissions(path: Path) -> list[dict[str, str]] | None:
    """Return the emitted ``permissions`` list, or ``None`` when none is emitted.

    Parsed as YAML, not by line matching: the document OpenCode consumes is a
    mapping, and a line matcher would accept a block that is not one.
    """
    parsed = yaml.safe_load(_frontmatter_block(path))
    assert isinstance(parsed, dict), f'{path} frontmatter is not a mapping'
    rules = parsed.get('permissions')
    assert rules is None or isinstance(rules, list), f'{path} permissions is not a list'
    return rules


def _effect(rules: list[dict[str, str]] | None, action: str) -> str:
    """OpenCode 2 evaluation: last matching rule wins, no match means ``ask``."""
    hits = [rule for rule in (rules or []) if rule['action'] == action]
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
# D1 — the emitted agent carries NO permission rule of any kind
# ---------------------------------------------------------------------------


def test_emitted_agent_carries_no_permission_rules(bundle_root: Path, tmp_path: Path, opencode_config_dir: Path):
    """No rule of any action is emitted for an agent.

    OpenCode 2 appends the agent's rules after the global ones, and an agent
    rule can only be a ``resource: "*"`` catch-all for one action — which
    re-decides every resource a global deny already decided, protected-path read
    denies included. The agent's own base policy already decides the rest.
    """
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    rules = _permissions(out / 'agent' / 'demo-agent.md')
    assert rules is None, f'the emitted agent must carry no permission rule, found {rules}'


def test_emitted_agent_keeps_the_source_description_and_mode(
    bundle_root: Path, tmp_path: Path, opencode_config_dir: Path
):
    """Dropping the rules leaves the frontmatter the client needs intact."""
    out = tmp_path / 'out'
    emit_bundles(bundle_root, out, opencode_config_dir)

    parsed = yaml.safe_load(_frontmatter_block(out / 'agent' / 'demo-agent.md'))
    assert parsed['description'] == 'an agent'
    assert parsed['mode'] == 'subagent'


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
