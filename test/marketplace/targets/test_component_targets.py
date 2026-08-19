# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the per-component ``targets:`` frontmatter filter."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.base import TargetBase
from marketplace.targets.component_targets import (
    TargetScopeError,
    component_tree_target_names,
    emits_to,
    excluded_emission_roots,
    is_under_any,
    iter_component_manifests,
    read_target_scope,
    registered_target_names,
)

# Every declaration spelling the build must accept, paired with the scope it
# yields. Reading is YAML's job now, so this is a list of the shapes an AUTHOR
# may write rather than of the shapes a scanner happens to survive: each row
# is here because a component could plausibly be written that way, not because
# some hand-rolled rule needed cornering.
_ACCEPTED_FORMS = {
    'inline-flow': ('targets: [claude]', {'claude'}),
    'inline-flow-multi': ('targets: [claude, opencode]', {'claude', 'opencode'}),
    'inline-bare': ('targets: claude', {'claude'}),
    # Not YAML's reading — YAML sees one string — but the build's own
    # comma-splitting convenience. See the module docstring.
    'inline-bare-multi': ('targets: claude, opencode', {'claude', 'opencode'}),
    'block': ('targets:\n  - claude\n  - opencode', {'claude', 'opencode'}),
    'quoted-item': ("targets: ['claude']", {'claude'}),
    'quoted-key': ('"targets": [claude]', {'claude'}),
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
    'flow-below-the-key': ('targets:\n  [claude, opencode]', {'claude', 'opencode'}),
    'comment-then-block': ('targets: # note\n  - claude', {'claude'}),
    'duplicate-item': ('targets: [claude, claude]', {'claude'}),
}

# Shapes a line scanner could not read, and that a YAML reader resolves
# exactly. Every one of these was REJECTED by the hand-rolled parser across
# twelve verification rounds, several of them under a message naming a
# construct the author had not written. They are accepted now because they are
# ordinary YAML naming real targets, and this file exists to keep them so.
_ONCE_REFUSED_NOW_READ = {
    'folded-block-scalar': ('targets: >-\n  claude', {'claude'}),
    'literal-block-scalar': ('targets: |-\n  claude', {'claude'}),
    'block-scalar-with-indent-indicator': ('targets: |2\n   claude', {'claude'}),
    'quoted-scalar-across-lines': ('targets: "claude,\n  opencode"', {'claude', 'opencode'}),
    'plain-scalar-below-the-key': ('targets:\n  claude', {'claude'}),
    'plain-scalar-across-lines': ('targets: claude,\n  opencode', {'claude', 'opencode'}),
    'uniformly-indented-block': (None, {'claude'}),
    'comment-above-an-indented-block': (None, {'claude'}),
    'value-continued-at-column-zero': (None, {'claude'}),
}

# The whole-file spellings for the three rows above that are about the BLOCK
# rather than about one value.
_ONCE_REFUSED_WHOLE_FILE = {
    'uniformly-indented-block': '---\n  name: demo\n  targets: [claude]\n---\n',
    'comment-above-an-indented-block': '---\n# a note\n  name: demo\n  targets: [claude]\n---\n',
    'value-continued-at-column-zero': (
        '---\n  description: "one\ntwo"\n  targets: [claude]\n---\n'
    ),
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
def test_every_authoring_spelling_yields_the_same_scope(tmp_path, frontmatter, expected):
    """Inline-flow, bare-scalar and block spellings all read the same."""
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


@pytest.mark.parametrize(
    ('key', 'expected'),
    [
        pytest.param(key, expected, id=key)
        for key, (_form, expected) in _ONCE_REFUSED_NOW_READ.items()
    ],
)
def test_shapes_a_line_scanner_refused_are_now_read(tmp_path, key, expected):
    """Twelve rounds of rejections that were never the author's fault.

    Every shape here is ordinary YAML naming a registered target, and every
    one was refused by the hand-rolled parser this module used to carry —
    several of them under a message naming a construct the author had not
    written, and three of them by silently reading the whole block as "no
    declaration" and shipping the component everywhere.

    They are accepted because a YAML reader resolves them, which is the point
    of using one. This test is the record that the change is deliberate: any
    future edit that re-refuses one of them must argue for it here.
    """
    whole_file = _ONCE_REFUSED_WHOLE_FILE.get(key)
    if whole_file is None:
        path = _component(tmp_path, _ONCE_REFUSED_NOW_READ[key][0])
    else:
        path = tmp_path / 'demo.md'
        path.write_text(whole_file, encoding='utf-8')

    assert read_target_scope(path) == expected


def test_a_duplicate_key_resolves_the_way_yaml_resolves_it(tmp_path):
    """The LAST declaration wins, because that is what YAML says.

    Carried for eight rounds as an open behavioural survivor: the line scanner
    took the first declaration where YAML takes the last, so a component with
    two ``targets:`` keys could both gain and lose a target relative to what a
    YAML reader sees. Delegating the read closed it without a policy decision.
    """
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\nname: demo\ntargets: [claude]\ntargets: [opencode]\n---\n', encoding='utf-8'
    )

    assert read_target_scope(path) == {'opencode'}


def test_absent_field_means_every_target(tmp_path):
    """A component with no declaration ships everywhere — the default."""
    path = tmp_path / 'demo.md'
    path.write_text('---\nname: demo\ndescription: x\n---\n\n# Body\n', encoding='utf-8')

    assert read_target_scope(path) is None
    for target_name in registered_target_names():
        assert emits_to(path, target_name)


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('# Body only\n', id='no-frontmatter'),
        pytest.param('---\nname: demo\n---\n', id='frontmatter-without-the-field'),
        pytest.param('---\n- a\n- b\n---\n', id='frontmatter-that-is-not-a-mapping'),
        pytest.param('---\n---\ntargets: [claude]\n---\n', id='immediately-closed-block'),
        pytest.param(
            '---\nname: demo\nmetadata:\n  targets: nonsense\n---\n', id='nested-under-a-key'
        ),
    ],
)
def test_shapes_that_declare_nothing(tmp_path, text):
    """None of these is a declaration, so all of them ship everywhere.

    The nested case is the one worth stating: a ``targets:`` inside another
    mapping is a different field, and it stays one however the surrounding
    block is indented.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

    assert read_target_scope(path) is None


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('﻿---\nname: demo\ntargets: [claude]\n---\n', id='byte-order-mark'),
        pytest.param('--- \nname: demo\ntargets: [claude]\n---\n', id='fence-trailing-space'),
        pytest.param('---\nname: demo\ntargets: [claude]\n--- \n', id='close-trailing-space'),
        pytest.param('---\t\nname: demo\ntargets: [claude]\n---\n', id='fence-trailing-tab'),
        pytest.param(
            '---\ndescription: a --- b\ntargets: [claude]\n---\n', id='three-hyphens-in-a-value'
        ),
    ],
)
def test_fence_handling_does_not_hide_a_declaration(tmp_path, text):
    """Finding the block is still this module's job; getting it wrong fails OPEN.

    A BOM, a fence carrying invisible trailing whitespace, a value containing
    three hyphens, a ``----`` line — each of these once read as "no
    frontmatter", which ships the component everywhere with its declaration
    unread AND lets an invalid declaration past the build unreported.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

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


def test_a_four_hyphen_line_inside_the_block_fails_closed(tmp_path):
    """``----`` is neither a fence nor valid YAML, and it is now refused.

    Three readers disagreed about this line. The old line scanner skipped it
    and read the declaration beneath; the tree's canonical frontmatter reader
    (``_dep_detection``) matches a ``---`` PREFIX and treats it as the closing
    fence, so the declaration is body text to it; and YAML calls the block
    malformed. Delegating the read settles it on YAML's answer, which is the
    only one of the three that refuses rather than silently picking a side.
    """
    path = tmp_path / 'demo.md'
    path.write_text('---\ndescription: a\n----\ntargets: [claude]\n---\n', encoding='utf-8')

    with pytest.raises(TargetScopeError, match='not well-formed YAML'):
        read_target_scope(path)


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: [claude,', id='unclosed-flow-sequence'),
        pytest.param('targets: [claude\n  opencode]\n  : x', id='malformed-mapping'),
        pytest.param('targets: [a\n\tb]', id='tab-indentation'),
    ],
)
def test_malformed_frontmatter_fails_closed(tmp_path, frontmatter):
    """Frontmatter YAML cannot read is REFUSED, not read past.

    Guessing at unparseable frontmatter is how a declaration goes unread, and
    a component then ships everywhere carrying an invalid declaration nobody
    was told about. That happened three times under the previous parser, so
    the failure names YAML's own complaint rather than inventing a diagnosis.
    """
    with pytest.raises(TargetScopeError, match='not well-formed YAML'):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    ('frontmatter', 'kind'),
    [
        pytest.param('targets: {claude: yes}', 'dict', id='mapping'),
        pytest.param('targets: 3', 'int', id='number'),
        pytest.param('targets: true', 'bool', id='boolean'),
    ],
)
def test_a_value_that_is_not_a_list_of_names_says_so(tmp_path, frontmatter, kind):
    """Naming the shape beats coercing it and then rejecting the coercion.

    ``targets: {claude: yes}`` is a mapping in any reading. Reporting it as an
    unknown target named ``{claude: yes}`` would name a target nobody wrote —
    the defect this module spent twelve rounds removing from other shapes.
    """
    with pytest.raises(TargetScopeError, match=f'is {kind}, not a list'):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    ('block', 'declares'),
    [
        pytest.param('description: a: b\ntargets: [claude]', True, id='mentions-the-field'),
        pytest.param('description: a: b\n"targets": [claude]', True, id='quoted-key'),
        pytest.param('description: a: b\n  targets: [claude]', True, id='indented-key'),
        pytest.param('description: a: b\nname: demo', False, id='never-mentions-it'),
    ],
)
def test_unparseable_frontmatter_is_refused_only_where_a_declaration_could_hide(
    tmp_path, block, declares
):
    """Target scoping is not the repository's YAML linter.

    Unparseable frontmatter that never mentions ``targets:`` has no
    declaration for this module to misread, so refusing it would widen the
    build's failure surface over a defect belonging to whatever consumes the
    rest of the file. Where the field IS mentioned, guessing is how a
    declaration goes unread — so that fails closed.

    The mention test is deliberately over-inclusive (any indentation, quoted
    or not), because every way it can be wrong REFUSES a malformed file that
    would otherwise pass. It cannot hide a declaration: hiding one would need
    the block to omit the key, and a block omitting the key declares nothing.
    """
    path = tmp_path / 'demo.md'
    path.write_text(f'---\n{block}\n---\n', encoding='utf-8')

    if declares:
        with pytest.raises(TargetScopeError, match='not well-formed YAML'):
            read_target_scope(path)
    else:
        assert read_target_scope(path) is None


def test_a_registered_target_name_may_not_contain_a_comma_or_whitespace(tmp_path):
    """The premise the comma-splitting convenience rests on, enforced not assumed.

    ``targets: a, b`` is one string to YAML and the build splits it, so a name
    carrying a comma could never be matched by that spelling while still
    matching in a list.
    """
    from marketplace.targets import register_target

    for name in ('my target', 'a,b'):
        with pytest.raises(ValueError, match='neither a comma nor'):
            register_target(name, _TreeTarget)


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
