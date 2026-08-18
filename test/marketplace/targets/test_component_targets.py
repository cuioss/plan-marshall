# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the per-component ``targets:`` frontmatter filter."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.base import TargetBase
from marketplace.targets.component_targets import (
    TargetScopeError,
    _declared_tokens,
    component_tree_target_names,
    emits_to,
    excluded_emission_roots,
    is_under_any,
    iter_component_manifests,
    read_target_scope,
    registered_target_names,
)

# Every declaration form the parser must accept, paired with the tokens it
# yields. Kept as data so a new spelling is one row rather than one test.
_ACCEPTED_FORMS = {
    'inline-flow': ('targets: [claude]', {'claude'}),
    'inline-flow-multi': ('targets: [claude, opencode]', {'claude', 'opencode'}),
    'inline-bare': ('targets: claude', {'claude'}),
    'inline-bare-multi': ('targets: claude, opencode', {'claude', 'opencode'}),
    'block': ('targets:\n  - claude\n  - opencode', {'claude', 'opencode'}),
    'quoted': ("targets: ['claude']", {'claude'}),
    'inline-flow-trailing-comment': ('targets: [claude]  # only here', {'claude'}),
    'inline-bare-trailing-comment': ('targets: claude  # only here', {'claude'}),
    'block-with-comment-line': ('targets:\n  # why\n  - claude', {'claude'}),
    'block-item-trailing-comment': ('targets:\n  - claude  # why', {'claude'}),
    'block-with-blank-line': ('targets:\n\n  - claude', {'claude'}),
    'flow-across-lines': ('targets: [claude,\n  opencode]', {'claude', 'opencode'}),
    'flow-across-lines-with-comment': (
        'targets: [claude,  # and\n  opencode]',
        {'claude', 'opencode'},
    ),
    'flow-opened-on-its-own-line': ('targets: [\n  claude\n  ]', {'claude'}),
}

# Values whose ``#`` does NOT open a token, so it is part of the name rather
# than a comment. Each is paired with the tokens the parser must preserve.
# Without these the comment-stripping guard could be deleted with the suite
# still green — which is how a documented behaviour regresses unnoticed.
_HASH_IS_NOT_A_COMMENT = {
    'quoted-leading-hash': ('targets: ["#claude"]', ['#claude']),
    'hash-inside-a-name': ('targets: [cla#ude]', ['cla#ude']),
    # No space before the ``#``, so it opens no comment and the whole run is
    # one (malformed, and therefore rejected) token — never a silent ``claude``.
    'hash-with-no-preceding-space': ('targets: [claude]#note', ['[claude]#note']),
}


def _component(tmp_path: Path, frontmatter: str, *, name: str = 'demo.md') -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\nname: demo\n{frontmatter}\n---\n\n# Body\n', encoding='utf-8')
    return path


# ---------------------------------------------------------------------------
# Registry-derived target sets
# ---------------------------------------------------------------------------


class _TreelessTarget(TargetBase):
    """A registered target whose output is not a component tree."""

    @property
    def name(self) -> str:
        return 'treeless'

    @property
    def emits_bundle_tree(self) -> bool:
        return False

    def generate(self, marketplace_dir, output_dir, bundles=None):  # noqa: ANN001, ANN201, D102
        return []

    def supports_agents(self) -> bool:
        return False

    def supports_commands(self) -> bool:
        return False

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parent


class _TreeTarget(_TreelessTarget):
    """A registered target whose output IS a component tree."""

    @property
    def name(self) -> str:
        return 'treeful'

    @property
    def emits_bundle_tree(self) -> bool:
        return True


def test_component_tree_names_follow_the_capability_not_a_list(monkeypatch):
    """The component-tree set is derived from ``emits_bundle_tree``, not enumerated.

    Registering two synthetic targets that differ only in that capability is
    what makes the derivation observable: a hard-coded list would report the
    same answer for both.
    """
    monkeypatch.setitem(TARGET_REGISTRY, 'treeless', _TreelessTarget)
    monkeypatch.setitem(TARGET_REGISTRY, 'treeful', _TreeTarget)

    assert 'treeful' in component_tree_target_names()
    assert 'treeless' not in component_tree_target_names()
    assert {'treeful', 'treeless'} <= registered_target_names()


def test_registered_names_cover_every_component_tree_name():
    """Every component-tree target is registered — the sets cannot diverge."""
    assert component_tree_target_names() <= registered_target_names()


# ---------------------------------------------------------------------------
# Declaration parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [pytest.param(form, expected, id=key) for key, (form, expected) in _ACCEPTED_FORMS.items()],
)
def test_declaration_forms_parse_to_the_same_scope(tmp_path, frontmatter, expected):
    """Inline-flow, bare-scalar, and block spellings all yield the same scope."""
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param(form, expected, id=key)
        for key, (form, expected) in _HASH_IS_NOT_A_COMMENT.items()
    ],
)
def test_a_hash_that_opens_no_token_is_not_a_comment(frontmatter, expected):
    """The comment stripper must not eat a ``#`` that is part of a value.

    Every case here names an unregistered target, so the build rejects it
    either way — what the assertion pins is WHICH token the diagnostic names,
    which is the whole reason the guard distinguishes a comment from a value.
    """
    assert _declared_tokens(f'---\nname: demo\n{frontmatter}\n---\n\n# Body\n') == expected


def test_absent_field_means_every_target(tmp_path):
    """A component with no declaration ships everywhere — the default."""
    path = tmp_path / 'demo.md'
    path.write_text('---\nname: demo\ndescription: x\n---\n\n# Body\n', encoding='utf-8')

    assert read_target_scope(path) is None
    for target_name in registered_target_names():
        assert emits_to(path, target_name)


def test_file_without_frontmatter_means_every_target(tmp_path):
    """A component with no frontmatter block declares no scope."""
    path = tmp_path / 'demo.md'
    path.write_text('# Body only\n', encoding='utf-8')

    assert read_target_scope(path) is None


def test_nested_targets_key_is_not_a_declaration(tmp_path):
    """Only a TOP-LEVEL ``targets:`` counts; an indented one is a different field."""
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\nname: demo\nmetadata:\n  targets: nonsense\n---\n\n# Body\n', encoding='utf-8'
    )

    assert read_target_scope(path) is None


def test_three_hyphen_value_does_not_truncate_the_block(tmp_path):
    """A value containing ``---`` must not hide the fields after it."""
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\nname: demo\ndescription: a --- b\ntargets: [claude]\n---\n\n# Body\n',
        encoding='utf-8',
    )

    assert read_target_scope(path) == {'claude'}


def test_a_byte_order_mark_does_not_hide_the_declaration(tmp_path):
    """A BOM'd file must not read as "no frontmatter", which ships it everywhere."""
    path = tmp_path / 'demo.md'
    path.write_text('﻿---\nname: demo\ntargets: [claude]\n---\n\n# Body\n', encoding='utf-8')

    assert read_target_scope(path) == {'claude'}
    assert emits_to(path, 'opencode') is False


def test_crlf_line_endings_do_not_hide_the_declaration(tmp_path):
    """Universal-newline decoding normalises CRLF; pin it rather than assume it."""
    path = tmp_path / 'demo.md'
    path.write_bytes(b'---\r\nname: demo\r\ntargets: [claude]\r\n---\r\n\r\n# Body\r\n')

    assert read_target_scope(path) == {'claude'}


def test_unreadable_component_degrades_to_every_target(tmp_path):
    """A read fault must never be able to REMOVE a component from a target."""
    path = tmp_path / 'demo.md'
    path.write_bytes(b'---\nname: demo\ntargets: [\xff\xfe]\n---\n')

    assert read_target_scope(path) is None
    assert emits_to(path, 'claude') is True


# ---------------------------------------------------------------------------
# The emission predicate
# ---------------------------------------------------------------------------


def test_scoped_component_is_emitted_only_by_a_named_target(tmp_path):
    """``targets: [claude]`` admits claude and refuses every other target."""
    path = _component(tmp_path, 'targets: [claude]')

    assert emits_to(path, 'claude') is True
    for target_name in registered_target_names() - {'claude'}:
        assert emits_to(path, target_name) is False


# ---------------------------------------------------------------------------
# Fail-closed validation
# ---------------------------------------------------------------------------


def test_unknown_target_name_is_rejected(tmp_path):
    """A typo fails the build, naming the component and the unknown value."""
    path = _component(tmp_path, 'targets: [cluade]')

    with pytest.raises(TargetScopeError) as excinfo:
        read_target_scope(path)

    message = str(excinfo.value)
    assert 'cluade' in message
    assert str(path) in message


def test_partially_unknown_target_list_is_rejected(tmp_path):
    """One valid name does not excuse an unknown one beside it."""
    path = _component(tmp_path, 'targets: [claude, nope]')

    with pytest.raises(TargetScopeError, match='nope'):
        read_target_scope(path)


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: []', id='inline-empty'),
        pytest.param('targets:\ndescription: x', id='key-with-no-items'),
    ],
)
def test_empty_declaration_is_rejected(tmp_path, frontmatter):
    """A component shipped nowhere is an authoring error, not an intent."""
    path = _component(tmp_path, frontmatter)

    with pytest.raises(TargetScopeError) as excinfo:
        read_target_scope(path)

    message = str(excinfo.value)
    assert 'empty list' in message
    assert str(path) in message


def test_only_non_component_tree_targets_is_rejected(tmp_path):
    """A registry-valid list that still ships the component nowhere is rejected.

    The offending value passes a membership check, so nothing but the
    ``emits_bundle_tree`` capability separates it from a valid declaration.
    """
    treeless = sorted(registered_target_names() - component_tree_target_names())
    assert treeless, 'fixture assumes at least one registered non-component-tree target'
    path = _component(tmp_path, f'targets: [{", ".join(treeless)}]')

    with pytest.raises(TargetScopeError) as excinfo:
        read_target_scope(path)

    message = str(excinfo.value)
    assert 'ship nowhere' in message
    assert str(path) in message


# ---------------------------------------------------------------------------
# Bundle-level helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def scoped_bundle(tmp_path: Path) -> Path:
    """A bundle holding one scoped and one unscoped component of each kind."""
    bundle = tmp_path / 'demo'
    scoped = '---\nname: {name}\ndescription: d\ntargets: [claude]\n---\n\n# Body\n'
    plain = '---\nname: {name}\ndescription: d\n---\n\n# Body\n'
    for rel, template, name in (
        ('agents/scoped-agent.md', scoped, 'scoped-agent'),
        ('agents/plain-agent.md', plain, 'plain-agent'),
        ('commands/scoped-cmd.md', scoped, 'scoped-cmd'),
        ('commands/plain-cmd.md', plain, 'plain-cmd'),
        ('skills/scoped-skill/SKILL.md', scoped, 'scoped-skill'),
        ('skills/plain-skill/SKILL.md', plain, 'plain-skill'),
    ):
        path = bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template.format(name=name), encoding='utf-8')
    (bundle / 'skills' / 'scoped-skill' / 'standards' / 'x.md').parent.mkdir(parents=True)
    (bundle / 'skills' / 'scoped-skill' / 'standards' / 'x.md').write_text('x\n', encoding='utf-8')
    return bundle


def test_manifests_map_each_component_to_what_it_governs(scoped_bundle):
    """An agent/command governs its file; a skill governs its whole directory."""
    mapped = {
        manifest.relative_to(scoped_bundle).as_posix(): root.relative_to(scoped_bundle).as_posix()
        for manifest, root in iter_component_manifests(scoped_bundle)
    }

    assert mapped['agents/scoped-agent.md'] == 'agents/scoped-agent.md'
    assert mapped['commands/scoped-cmd.md'] == 'commands/scoped-cmd.md'
    assert mapped['skills/scoped-skill/SKILL.md'] == 'skills/scoped-skill'


def test_excluded_roots_name_only_the_scoped_out_components(scoped_bundle):
    """Excluding for a non-named target catches every kind; claude excludes none."""
    excluded = excluded_emission_roots(scoped_bundle, 'opencode')

    assert excluded == {
        Path('agents/scoped-agent.md'),
        Path('commands/scoped-cmd.md'),
        Path('skills/scoped-skill'),
    }
    assert excluded_emission_roots(scoped_bundle, 'claude') == frozenset()


def test_excluded_roots_validate_every_component_not_only_excluded_ones(tmp_path):
    """An invalid declaration fails even for the target it would have admitted."""
    bundle = tmp_path / 'demo'
    path = bundle / 'commands' / 'bad.md'
    path.parent.mkdir(parents=True)
    path.write_text('---\nname: bad\ntargets: [claude, bogus]\n---\n\n# Body\n', encoding='utf-8')

    with pytest.raises(TargetScopeError, match='bogus'):
        excluded_emission_roots(bundle, 'claude')


def test_a_skill_directory_exclusion_covers_its_whole_subtree():
    """Every path beneath an excluded skill directory is excluded with it."""
    roots = frozenset({Path('skills/scoped-skill')})

    assert is_under_any(Path('skills/scoped-skill'), roots) is True
    assert is_under_any(Path('skills/scoped-skill/standards/x.md'), roots) is True
    assert is_under_any(Path('skills/plain-skill/SKILL.md'), roots) is False
    assert is_under_any(Path('skills/scoped-skill-extra/SKILL.md'), roots) is False


def test_no_exclusions_means_nothing_is_under_any():
    """The empty-exclusion fast path agrees with the general answer."""
    assert is_under_any(Path('agents/a.md'), frozenset()) is False
