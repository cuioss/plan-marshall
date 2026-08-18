# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end tests for target-scoped component emission.

Exercises the ``targets:`` filter through both component-tree-emitting
targets' real pipelines: a scoped component reaches the target it names and
no other, an unscoped one reaches every target, and the Claude equality gate
reads a scoped-out component as deliberately absent rather than as drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.claude.emitter import iter_bundle_dirs
from marketplace.targets.claude.equality_check import run_equality_check
from marketplace.targets.claude.target import ClaudeTarget
from marketplace.targets.component_targets import (
    TargetScopeError,
    component_tree_target_names,
)
from marketplace.targets.opencode.target import OpenCodeTarget

_SCOPED = '---\nname: {name}\ndescription: scoped to claude only\ntargets: [claude]\n---\n\n# Body\n'
_PLAIN = '---\nname: {name}\ndescription: ships everywhere\n---\n\n# Body\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def marketplace(tmp_path: Path) -> Path:
    """A one-bundle marketplace holding a scoped and an unscoped component of each kind."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundle = bundles / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps(
            {
                'name': 'demo',
                'version': '0.0.1',
                'description': 'Demo bundle',
                'agents': [],
                'commands': [],
                'skills': [],
            },
            indent=2,
        )
        + '\n',
    )
    _write(
        bundles.parent / '.claude-plugin' / 'marketplace.json',
        json.dumps(
            {
                'name': 'demo-marketplace',
                'owner': {'name': 'demo'},
                'plugins': [
                    {'name': 'demo', 'source': './bundles/demo', 'description': 'Demo bundle'}
                ],
            },
            indent=2,
        )
        + '\n',
    )
    _write(bundle / 'agents' / 'scoped-agent.md', _SCOPED.format(name='scoped-agent'))
    _write(bundle / 'agents' / 'plain-agent.md', _PLAIN.format(name='plain-agent'))
    _write(bundle / 'commands' / 'scoped-cmd.md', _SCOPED.format(name='scoped-cmd'))
    _write(bundle / 'commands' / 'plain-cmd.md', _PLAIN.format(name='plain-cmd'))
    _write(bundle / 'skills' / 'scoped-skill' / 'SKILL.md', _SCOPED.format(name='scoped-skill'))
    _write(bundle / 'skills' / 'scoped-skill' / 'standards' / 'x.md', '# standard\n')
    _write(bundle / 'skills' / 'plain-skill' / 'SKILL.md', _PLAIN.format(name='plain-skill'))
    return bundles


@pytest.fixture()
def claude_tree(marketplace: Path, tmp_path: Path) -> Path:
    """The emitted Claude output tree."""
    output = tmp_path / 'out' / 'claude'
    ClaudeTarget().generate(marketplace, output)
    return output


@pytest.fixture()
def opencode_tree(marketplace: Path, tmp_path: Path) -> Path:
    """The emitted OpenCode output tree."""
    output = tmp_path / 'out' / 'opencode'
    target = OpenCodeTarget()
    target.generate(marketplace, output)
    return output


# ---------------------------------------------------------------------------
# The filter, through each target's real pipeline
# ---------------------------------------------------------------------------


def test_scoped_components_reach_the_target_they_name(claude_tree: Path):
    """``targets: [claude]`` is emitted by the Claude target."""
    bundle = claude_tree / 'demo'

    assert (bundle / 'agents' / 'scoped-agent.md').is_file()
    assert (bundle / 'commands' / 'scoped-cmd.md').is_file()
    assert (bundle / 'skills' / 'scoped-skill' / 'SKILL.md').is_file()


def test_scoped_components_are_absent_from_every_other_target(opencode_tree: Path):
    """The same components are simply not there on a target they do not name."""
    assert not (opencode_tree / 'agent' / 'scoped-agent.md').exists()
    assert not (opencode_tree / 'command' / 'scoped-cmd.md').exists()
    assert not (opencode_tree / 'skill' / 'demo-scoped-skill').exists()


def test_a_scoped_skill_takes_its_whole_subtree_with_it(opencode_tree: Path):
    """A skill's declaration governs its verbatim sub-directories too."""
    assert not (opencode_tree / 'skill' / 'demo-scoped-skill' / 'standards').exists()


def test_unscoped_components_reach_every_target(claude_tree: Path, opencode_tree: Path):
    """A component with no declaration is untouched by the mechanism."""
    assert (claude_tree / 'demo' / 'agents' / 'plain-agent.md').is_file()
    assert (claude_tree / 'demo' / 'commands' / 'plain-cmd.md').is_file()
    assert (claude_tree / 'demo' / 'skills' / 'plain-skill' / 'SKILL.md').is_file()
    assert (opencode_tree / 'agent' / 'plain-agent.md').is_file()
    assert (opencode_tree / 'command' / 'plain-cmd.md').is_file()
    assert (opencode_tree / 'skill' / 'demo-plain-skill' / 'SKILL.md').is_file()


def test_every_component_tree_target_honours_the_filter():
    """The filter's reach is the derived capability set, not a pair of names.

    Quantifying over the registry is what makes a target registered later
    covered by this expectation rather than silently exempt.
    """
    assert component_tree_target_names() == {
        name for name, target_cls in TARGET_REGISTRY.items() if target_cls().emits_bundle_tree
    }


# ---------------------------------------------------------------------------
# Manifest and equality gate
# ---------------------------------------------------------------------------


def test_manifest_drops_a_scoped_out_component_in_lock_step(marketplace: Path, tmp_path: Path):
    """The regenerated manifest lists exactly what the tree carries, per target.

    Reading the manifest for a target that excludes the component is what
    proves the drop is keyed on the target rather than on the component's
    mere existence.
    """
    from marketplace.targets.claude.plugin_json_gen import build_plugin_json

    bundle_dir = marketplace / 'demo'

    for_claude = build_plugin_json(bundle_dir, target_name='claude')
    for_opencode = build_plugin_json(bundle_dir, target_name='opencode')

    assert './commands/scoped-cmd.md' in for_claude['commands']
    assert './agents/scoped-agent.md' in for_claude['agents']
    assert './commands/scoped-cmd.md' not in for_opencode['commands']
    assert './agents/scoped-agent.md' not in for_opencode['agents']
    assert './commands/plain-cmd.md' in for_opencode['commands']


def test_emitted_manifest_matches_the_emitted_tree(claude_tree: Path):
    """The manifest the emit wrote declares the components the emit produced."""
    manifest = json.loads(
        (claude_tree / 'demo' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8')
    )

    assert sorted(manifest['commands']) == ['./commands/plain-cmd.md', './commands/scoped-cmd.md']
    assert sorted(manifest['agents']) == ['./agents/plain-agent.md', './agents/scoped-agent.md']


def test_equality_gate_passes_over_a_tree_holding_a_scoped_component(
    marketplace: Path, claude_tree: Path
):
    """A scoped component is deliberately absent, never drift."""
    result = run_equality_check(claude_tree, list(iter_bundle_dirs(marketplace, None)))

    assert result.passed, result.summary
    assert result.diffs == []


# ---------------------------------------------------------------------------
# Fail-closed, through the pipeline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('declaration', 'expected_fragment'),
    [
        pytest.param('targets: [cluade]', 'cluade', id='unknown-name'),
        pytest.param('targets: []', 'empty list', id='empty-list'),
    ],
)
def test_generation_fails_on_an_invalid_declaration(
    marketplace: Path, tmp_path: Path, declaration: str, expected_fragment: str
):
    """An invalid declaration aborts the emit rather than narrowing it silently."""
    _write(
        marketplace / 'demo' / 'commands' / 'bad.md',
        f'---\nname: bad\ndescription: d\n{declaration}\n---\n\n# Body\n',
    )

    with pytest.raises(TargetScopeError) as excinfo:
        ClaudeTarget().generate(marketplace, tmp_path / 'out' / 'bad')

    assert expected_fragment in str(excinfo.value)
    assert 'bad.md' in str(excinfo.value)


def test_generation_fails_when_no_named_target_emits_a_component_tree(
    marketplace: Path, tmp_path: Path
):
    """A registry-valid list that still ships the component nowhere is refused."""
    treeless = sorted(set(TARGET_REGISTRY) - component_tree_target_names())
    assert treeless, 'fixture assumes at least one registered non-component-tree target'
    _write(
        marketplace / 'demo' / 'commands' / 'nowhere.md',
        f'---\nname: nowhere\ndescription: d\ntargets: [{", ".join(treeless)}]\n---\n\n# Body\n',
    )

    with pytest.raises(TargetScopeError, match='ship nowhere'):
        ClaudeTarget().generate(marketplace, tmp_path / 'out' / 'nowhere')
