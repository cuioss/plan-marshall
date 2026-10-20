# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode 2 tool-name and skill-directive pins (PLAN-LB-48 D2).

PLAN-LB-67 changed ``Task`` in ``tool_permissions`` to ``subagent`` but left the
runtime, the mapping's own note and four standards on ``task`` — and OpenCode 2's
``skill`` tool takes ``{id}``, not OpenCode 1's ``{name}``. These tests pin the
target data and the shipped prose so the two halves cannot drift apart again.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.body_transform_engine import load_transform_rules, rewrite_skill_directives


@pytest.fixture()
def opencode_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'opencode'


def test_mapping_uses_opencode2_tool_names(opencode_config_dir: Path):
    mapping = json.loads((opencode_config_dir / 'mapping.json').read_text(encoding='utf-8'))
    tools = mapping['tool_permissions']
    assert tools['Bash'] == 'shell', 'Bash must map to OpenCode 2 `shell`'
    assert tools['Task'] == 'subagent', 'Task must map to OpenCode 2 `subagent`'


def test_mapping_skill_directive_passes_an_id(opencode_config_dir: Path):
    mapping = json.loads((opencode_config_dir / 'mapping.json').read_text(encoding='utf-8'))
    template = mapping['directive_rewrites']['skill_directive']['template']
    assert '{ id:' in template, f'the skill directive must pass `{{ id: ... }}`, got {template!r}'
    assert '{ name:' not in template, f'the OpenCode 1 `{{ name: ... }}` input must be gone, got {template!r}'


def test_emitted_skill_directive_reads_id(opencode_config_dir: Path):
    """The rendered body must pass ``{ id: "<bundle>-<skill>" }``."""
    rules = load_transform_rules(opencode_config_dir / 'mapping.json')
    rendered = rewrite_skill_directives(
        'Skill: alpha:beta\n',
        rules.directive_rewrites['skill_directive']['template'],
    )
    assert '{ id: "alpha-beta" }' in rendered


def test_mapping_task_note_agrees_with_its_tool_mapping(opencode_config_dir: Path):
    """The mapping's own note must not name the OpenCode sub-agent tool ``task``."""
    mapping = json.loads((opencode_config_dir / 'mapping.json').read_text(encoding='utf-8'))
    note = mapping['body_idiom_rewrites']['Task:']['note']
    assert '`task`' not in note, f'the mapping note still names the OpenCode tool `task`: {note!r}'


def test_no_bundle_standard_names_the_opencode_subagent_tool_as_task():
    """No bundle standard may name OpenCode's sub-agent tool ``task``."""
    standards = Path(PROJECT_ROOT) / 'marketplace' / 'bundles'
    offenders: list[str] = []
    for path in sorted(standards.glob('*/skills/*/standards/*.md')):
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if 'OpenCode `task`' in line:
                offenders.append(f'{path.relative_to(standards)}:{number}: {line.strip()}')
    assert not offenders, 'OpenCode 1 sub-agent tool name in a bundle standard:\n' + '\n'.join(offenders)
