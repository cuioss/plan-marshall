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

# The fixture's components, as data: stem -> the scope its frontmatter declares
# (``None`` = no declaration = every target). The fixture WRITES from this table
# and the registry sweep READS its expectation from it, so the two cannot drift
# — and neither is derived from the code under test.
#
# Both scope directions are present deliberately. A fixture scoped only TO
# claude exercises the OpenCode skip alone, leaving the Claude emitter's own
# exclusion path unobserved.
_FIXTURE_SCOPES: dict[str, frozenset[str] | None] = {
    'scoped-agent': frozenset({'claude'}),
    'scoped-cmd': frozenset({'claude'}),
    'scoped-skill': frozenset({'claude'}),
    'other-agent': frozenset({'opencode'}),
    'other-cmd': frozenset({'opencode'}),
    'other-skill': frozenset({'opencode'}),
    'plain-agent': None,
    'plain-cmd': None,
    'plain-skill': None,
}

_UNSCOPED_COMMAND = 'plain-cmd'


def _frontmatter(stem: str) -> str:
    scope = _FIXTURE_SCOPES[stem]
    declaration = '' if scope is None else f'targets: [{", ".join(sorted(scope))}]\n'
    return f'---\nname: {stem}\ndescription: fixture component\n{declaration}---\n\n# Body\n'


def _scoped_away_from(target_name: str) -> set[str]:
    """Stems whose declaration excludes ``target_name`` — what it must NOT emit."""
    return {
        stem
        for stem, scope in _FIXTURE_SCOPES.items()
        if scope is not None and target_name not in scope
    }


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
    for stem in _FIXTURE_SCOPES:
        if stem.endswith('-agent'):
            _write(bundle / 'agents' / f'{stem}.md', _frontmatter(stem))
        elif stem.endswith('-cmd'):
            _write(bundle / 'commands' / f'{stem}.md', _frontmatter(stem))
        else:
            _write(bundle / 'skills' / stem / 'SKILL.md', _frontmatter(stem))
            _write(bundle / 'skills' / stem / 'standards' / 'x.md', '# standard\n')
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


def test_the_claude_pipeline_also_excludes_what_scopes_it_out(claude_tree: Path):
    """The filter is symmetric — the Claude target skips what names only another.

    Every other case in this module scopes a component TO claude, which
    exercises the OpenCode skip alone; this one is what makes the Claude
    emitter's own exclusion path observable.
    """
    bundle = claude_tree / 'demo'

    assert not (bundle / 'agents' / 'other-agent.md').exists()
    assert not (bundle / 'commands' / 'other-cmd.md').exists()
    assert not (bundle / 'skills' / 'other-skill').exists()


def test_components_scoped_away_from_claude_still_reach_the_target_they_name(
    opencode_tree: Path,
):
    """The exclusion above is a scope decision, not a component that got lost."""
    assert (opencode_tree / 'agent' / 'other-agent.md').is_file()
    assert (opencode_tree / 'command' / 'other-cmd.md').is_file()
    assert (opencode_tree / 'skill' / 'demo-other-skill' / 'SKILL.md').is_file()
    assert (opencode_tree / 'skill' / 'demo-other-skill' / 'standards' / 'x.md').is_file()


def test_unscoped_components_reach_every_target(claude_tree: Path, opencode_tree: Path):
    """A component with no declaration is untouched by the mechanism."""
    assert (claude_tree / 'demo' / 'agents' / 'plain-agent.md').is_file()
    assert (claude_tree / 'demo' / 'commands' / 'plain-cmd.md').is_file()
    assert (claude_tree / 'demo' / 'skills' / 'plain-skill' / 'SKILL.md').is_file()
    assert (opencode_tree / 'agent' / 'plain-agent.md').is_file()
    assert (opencode_tree / 'command' / 'plain-cmd.md').is_file()
    assert (opencode_tree / 'skill' / 'demo-plain-skill' / 'SKILL.md').is_file()


def test_every_component_tree_target_honours_the_filter(marketplace: Path, tmp_path: Path):
    """Generate through EVERY registered component-tree target; none may emit a scoped-out component.

    Honouring the filter is per-target wiring — no shared code can apply it on
    a target's behalf, because only the target knows which paths it emits — so
    this is what makes the obligation enforceable rather than merely
    documented. Quantifying over the registry is the load-bearing part: a
    target registered later is generated here too, and fails unless it wired
    the filter in.

    The assertion is made from each target's OWN emitted-path list, not from
    the filter's return value, so it cannot agree with the filter by
    construction.
    """
    tree_targets = sorted(component_tree_target_names())
    assert tree_targets, 'no component-tree target registered — the sweep would be vacuous'

    for name in tree_targets:
        target = TARGET_REGISTRY[name]()
        emitted = target.generate(marketplace, tmp_path / 'sweep' / name)
        # A skill is emitted as a directory, and each target names that
        # directory its own way, so match on any path SEGMENT rather than on a
        # filename: that covers the file-shaped and directory-shaped
        # components with one rule and needs no per-target path knowledge.
        segments = {segment for path in emitted for segment in Path(path).parts}
        emitted_stems = {Path(path).stem for path in emitted}

        for stem in sorted(_scoped_away_from(name)):
            assert not any(stem in segment for segment in segments), (
                f'{name} emitted {stem}, which declares a scope excluding {name}'
            )

        # Anti-vacuity: a target that emitted nothing would satisfy every
        # assertion above. The unscoped command must actually be there.
        if target.supports_commands():
            assert _UNSCOPED_COMMAND in emitted_stems, (
                f'{name} emitted no unscoped command; the absences above are vacuous'
            )


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
    # The scoped-away pair is absent from BOTH halves of the lock-step: the
    # manifest does not declare it and the tree does not carry it.
    assert not (claude_tree / 'demo' / 'commands' / 'other-cmd.md').exists()


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


def test_validate_only_mode_rejects_an_invalid_skill_declaration(
    marketplace: Path, tmp_path: Path, monkeypatch
):
    """Validate-only mode must not pass a declaration an emit would reject.

    The equality path regenerates the manifest only, and the manifest never
    lists skills, so without an explicit component walk a skill's invalid
    declaration reaches validate-only mode unexamined.
    """
    output = tmp_path / 'out' / 'claude'
    ClaudeTarget().generate(marketplace, output)
    monkeypatch.setattr(
        'marketplace.targets.claude.target.DEFAULT_VALIDATE_TARGET_DIR', output
    )
    _write(
        marketplace / 'demo' / 'skills' / 'bad-skill' / 'SKILL.md',
        '---\nname: bad-skill\ndescription: d\ntargets: [cluade]\n---\n\n# Body\n',
    )

    with pytest.raises(TargetScopeError, match='cluade'):
        ClaudeTarget().generate(marketplace, None)


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
