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
    # A continuation line at column 0 whose trailing comment carries a colon.
    # The boundary test that looked for a colon rather than a key rejected it,
    # though it is ordinary YAML. The sibling case — a continuation whose
    # VALUE quotes a colon — cannot live here, because the resulting target
    # name is not registry-valid; it is pinned at parser level instead, in
    # ``test_a_flow_continuation_may_quote_a_colon``.
    'flow-continuation-with-a-url-comment': (
        'targets: [claude,\nopencode] # see https://example.com',
        {'claude', 'opencode'},
    ),
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
        pytest.param(
            'targets: [claude,\ndescription: a demo\nmode: workflow',
            ['[claude'],
            id='unclosed-then-more-keys',
        ),
        pytest.param('targets: [claude,', ['[claude'], id='unclosed-at-the-fence'),
    ],
)
def test_an_unclosed_flow_sequence_does_not_swallow_the_following_fields(
    frontmatter, expected
):
    """Folding the rest of the block in would name the FOLLOWING FIELDS as targets.

    The value is malformed either way and the build rejects it; what this
    pins is that the diagnostic names only the malformed value, not the
    description and mode lines that happen to sit beneath it.
    """
    assert _declared_tokens(f'---\nname: demo\n{frontmatter}\n---\n\n# Body\n') == expected


# The fold boundary is a HEURISTIC for "a new key starts here", and
# :func:`_join_flow_sequence` documents exactly where it is wrong: a
# digit-initial or quoted key is missed and folded in, and a bare URL at
# column 0 is treated as a key and ends the fold early. Both clauses were
# unguarded — each could be falsified in code with the suite fully green —
# so each is pinned here, together with the SAFETY property that makes them
# tolerable: every such misread is rejected, never mis-accepted.
_DOCUMENTED_MISREADS = {
    'digit-initial-key-is-folded-in': (
        'targets: [claude,\n2fa: no',
        ['[claude', '2fa: no'],
    ),
    'quoted-key-is-folded-in': (
        'targets: [claude,\n"q": v',
        ['[claude', 'q": v'],
    ),
    'bare-url-at-column-zero-ends-the-fold': (
        'targets: [claude,\nhttps://example.com',
        ['[claude'],
    ),
}


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [pytest.param(f, e, id=k) for k, (f, e) in _DOCUMENTED_MISREADS.items()],
)
def test_the_fold_boundary_misreads_exactly_where_it_is_documented_to(frontmatter, expected):
    """Pin the two misreads :func:`_join_flow_sequence` names, so neither can drift."""
    assert _declared_tokens(f'---\nname: demo\n{frontmatter}\n---\n\n# Body\n') == expected


@pytest.mark.parametrize(
    'frontmatter',
    [pytest.param(f, id=k) for k, (f, _e) in _DOCUMENTED_MISREADS.items()],
)
def test_every_documented_misread_is_rejected_never_mis_accepted(tmp_path, frontmatter):
    """The safety property the fold's whole design rests on.

    A misread may widen or truncate the text that gets REJECTED; it must never
    produce a scope the author did not write. This is the clause a reviewer
    would have to take on trust otherwise — the docstring asserts it, and
    nothing else in the suite would notice if it stopped holding.
    """
    with pytest.raises(TargetScopeError):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('"targets": [claude]', id='double-quoted-key'),
        pytest.param("'targets': [claude]", id='single-quoted-key'),
    ],
)
def test_a_quoted_key_is_still_a_declaration(tmp_path, frontmatter):
    """``"targets":`` is the same key as ``targets:`` to any YAML reader.

    Missing it failed OPEN: the declaration went unseen and the component
    shipped to every target with nothing reported. Five verification rounds
    did not catch it, which is why the quoted spellings are pinned rather
    than assumed unreachable.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) == {'claude'}


# Keys that are NOT ``targets`` to a YAML reader, and so must not be read as a
# declaration. The first fix for the quoted-key miss stripped a character SET,
# which turned every one of these into ``targets`` — silently narrowing a
# component that had declared no scope at all. That is the same defect in the
# opposite direction, so the boundary is pinned from both sides.
_NOT_THE_TARGETS_KEY = (
    'targets": [claude]',
    "targets': [claude]",
    '"\'targets\'": [claude]',
    '"targets: [claude]',
    '""targets"": [claude]',
    '\'targets": [claude]',
)


@pytest.mark.parametrize('frontmatter', [pytest.param(f, id=f) for f in _NOT_THE_TARGETS_KEY])
def test_a_mismatched_quote_is_not_the_targets_key(tmp_path, frontmatter):
    """Only a MATCHED pair of surrounding quotes makes it the ``targets`` key.

    Each spelling here is a different key to YAML (or is not well-formed at
    all), so the component declares no scope and must ship everywhere.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) is None


def test_a_flow_continuation_may_quote_a_colon():
    """A quoted value containing a colon is ordinary YAML and must fold in.

    This is the second of the two shapes the colon-based boundary broke. It
    is asserted at parser level because ``a: b`` is not a registry-valid
    target name, so the validating entry point would reject it before the
    parse could be observed — and asserting it through a name that IS valid
    would not exercise the colon at all.
    """
    tokens = _declared_tokens('---\nname: demo\ntargets: [claude,\n"a: b"]\n---\n\n# Body\n')

    assert tokens == ['claude', 'a: b']


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [pytest.param(form, expected, id=key) for key, (form, expected) in _HASH_IS_NOT_A_COMMENT.items()],
)
def test_a_hash_that_opens_no_token_is_not_a_comment(frontmatter, expected):
    """The comment stripper must not eat a ``#`` that is part of a value.

    Every case here names an unregistered target, so the build rejects it
    either way — what the assertion pins is WHICH token the diagnostic names,
    which is the whole reason the guard distinguishes a comment from a value.
    """
    assert _declared_tokens(f'---\nname: demo\n{frontmatter}\n---\n\n# Body\n') == expected


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: claude,\n  opencode', id='comma-continued'),
        pytest.param('targets: claude\n  opencode', id='space-continued'),
        pytest.param('targets: claude,\n\n  opencode', id='blank-line-between'),
    ],
)
def test_a_plain_scalar_continued_across_lines_is_rejected(tmp_path, frontmatter):
    """Silent NARROWING is the one direction this mechanism must never fail in.

    ``targets: claude,`` / ``  opencode`` is a single YAML value naming two
    targets. Reading only the first physical line yielded ``{claude}`` — the
    component shipped to one target where its author declared two, with
    nothing reported. It is rejected now, so the author is told rather than
    silently obeyed in part.
    """
    with pytest.raises(TargetScopeError, match='continued across lines'):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param('targets: claude, opencode', {'claude', 'opencode'}, id='single-line-bare'),
        pytest.param('targets: [claude,\n  opencode]', {'claude', 'opencode'}, id='flow-across-lines'),
        pytest.param('targets:\n  - claude', {'claude'}, id='block-form'),
        pytest.param('targets: claude\ndescription: d', {'claude'}, id='bare-then-next-key'),
        pytest.param('targets: claude\n# note\ndescription: d', {'claude'}, id='bare-then-comment'),
    ],
)
def test_the_continuation_check_does_not_disturb_any_supported_form(
    tmp_path, frontmatter, expected
):
    """The rejection above must catch the continued scalar and nothing else.

    A guard that also refused the block form, or a bare value followed by the
    next field, would trade a silent defect for a loud one.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


def test_no_fold_misread_can_smuggle_an_accepted_scope(tmp_path):
    """The safety property the whole fold heuristic rests on, checked by search.

    A misread may widen or truncate the text that gets REJECTED; it must
    never yield a token set the registry accepts. This enumerates every
    two-line continuation drawn from a set chosen to exercise both failure
    directions — surplus absorbed, and fold stopped early — and asserts that
    the only inputs accepted are the ones that actually close their bracket.
    """
    import itertools

    continuations = [
        'opencode]', 'opencode', '2fa: no', '"q": v', 'https://x',
        'description: d', ']', '', '# c',
    ]
    accepted_without_closing = []
    for first, second in itertools.product(continuations, repeat=2):
        frontmatter = f'targets: [claude,\n{first}\n{second}'
        try:
            read_target_scope(_component(tmp_path, frontmatter))
        except TargetScopeError:
            continue
        if not (first.rstrip().endswith(']') or second.rstrip().endswith(']')):
            accepted_without_closing.append(frontmatter)

    assert accepted_without_closing == []


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: claude,\n  - opencode', id='dash-continuation-with-comma'),
        pytest.param('targets: claude\n  - opencode', id='dash-continuation-bare'),
    ],
)
def test_a_dash_continuation_does_not_escape_the_guard(tmp_path, frontmatter):
    """A continuation beginning with ``-`` is still a continuation.

    The first version of this guard exempted such lines, meaning to protect
    the block form — but the guard only runs when the key HAS a value, and a
    block form's key has none, so the exemption protected nothing and left
    the silent-narrowing hole open for exactly this shape. Nothing tested
    it: deleting the exemption reddened no test at all.
    """
    with pytest.raises(TargetScopeError, match='continued across lines'):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: >-\n  claude', id='folded'),
        pytest.param('targets: |-\n  claude', id='literal'),
        pytest.param('targets: >\n  claude', id='folded-clip'),
        pytest.param('targets: |2\n   claude', id='literal-indent-indicator'),
        pytest.param('targets: >3-\n   claude', id='folded-indent-then-chomp'),
        pytest.param('targets: |-2\n   claude', id='literal-chomp-then-indent'),
        pytest.param('targets: >+9\n   claude', id='folded-keep-then-indent'),
    ],
)
def test_a_block_scalar_is_named_as_one(tmp_path, frontmatter):
    """A ``>``/``|`` value is rejected, but not as a "plain scalar".

    PyYAML reads these as the single value ``claude`` — a real target — so
    the rejection is the parser declining a shape it cannot read, not the
    author writing something malformed. Calling it a continued plain scalar
    sent the author looking for a defect that is not in their file.

    The indentation-indicator spellings are here because the first version
    matched a fixed SET of the six chomping spellings, which left 54 of the 60
    legal headers carrying the very message the fix removed.
    """
    with pytest.raises(TargetScopeError, match='block scalar'):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: "claude,\n  opencode"', id='double-quoted'),
        pytest.param("targets: 'claude,\n  opencode'", id='single-quoted'),
    ],
)
def test_a_quoted_scalar_continued_across_lines_is_named_as_one(tmp_path, frontmatter):
    """A quoted multi-line value is rejected, but it is not a PLAIN scalar.

    PyYAML reads both of these as ``claude, opencode`` — two real targets. A
    quoted scalar is by definition not plain, so the word was simply wrong.
    """
    with pytest.raises(TargetScopeError, match='quoted scalar continued across lines'):
        read_target_scope(_component(tmp_path, frontmatter))


def test_the_shape_only_names_the_construct_it_never_decides(tmp_path):
    """Every multi-line shape is rejected; the shape chooses the noun alone.

    The rejection is one condition, so no classification error can turn a
    rejection into an acceptance. Pinned rather than asserted: every earlier
    version tangled the shape test into the rejection condition, and each one
    then changed the verdict on some valid input while improving a sentence.
    """
    from marketplace.targets.component_targets import _MULTILINE_NOUN, _multiline_shape

    shapes = {
        'targets: >-\n  claude': 'block-scalar',
        'targets: "claude,\n  opencode"': 'quoted-scalar',
        'targets: claude,\n  opencode': 'plain-scalar',
    }
    assert set(shapes.values()) == set(_MULTILINE_NOUN)
    for frontmatter, shape in shapes.items():
        assert _multiline_shape(frontmatter.split('\n')[0].partition(':')[2].strip()) == shape
        with pytest.raises(TargetScopeError):
            read_target_scope(_component(tmp_path, frontmatter))


def test_the_fold_joins_with_a_space_and_that_is_what_rejects_an_overrun(tmp_path):
    """The space join is the load-bearing half of the fold's safety argument.

    ``targets: [open`` / ``code]`` closes its bracket, so the bracket half of
    the argument does not apply; only the space in ``open code`` keeps it out
    of the registry. Joining without one would yield an accepted ``opencode``
    — a scope the author never wrote.

    There must be NO comma in the fixture. The first version of this test used
    ``[open,`` / ``code]``, where the comma alone does the splitting, so it
    passed under ``''.join`` too — a test whose name asserted the property and
    whose body did not exercise it, exactly the defect it was written to
    prevent.
    """
    with pytest.raises(TargetScopeError, match='unknown target'):
        read_target_scope(_component(tmp_path, 'targets: [open\ncode]'))


def test_no_registered_target_name_may_contain_a_space(tmp_path):
    """The premise the space-join argument rests on, enforced rather than assumed."""
    from marketplace.targets import register_target

    with pytest.raises(ValueError, match='no whitespace'):
        register_target('my target', _TreeTarget)


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


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('--- \nname: demo\ntargets: [claude]\n---\n', id='opening-space'),
        pytest.param('---\nname: demo\ntargets: [claude]\n--- \n', id='closing-space'),
        pytest.param('---\t\nname: demo\ntargets: [claude]\n---\n', id='opening-tab'),
        pytest.param('---\nname: demo\ntargets: [claude]\n---  ', id='closing-space-at-eof'),
    ],
)
def test_trailing_whitespace_on_a_fence_does_not_hide_the_declaration(tmp_path, text):
    """A space after ``---`` is invisible in an editor and must not fail open.

    ``_dep_detection.extract_frontmatter`` — this tree's own canonical
    frontmatter reader — accepts these fences, so refusing them made two
    parsers in one repository disagree about whether the file has frontmatter
    at all, and the declaration went unread while the component shipped
    everywhere.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

    assert read_target_scope(path) == {'claude'}
    assert emits_to(path, 'opencode') is False


def test_a_uniformly_indented_frontmatter_block_is_still_top_level(tmp_path):
    """Top-level is relative to the BLOCK, not to column zero.

    YAML reads every key here as top-level, because nothing opened a mapping
    above them. Scanning for column-zero keys instead read "no declaration"
    and shipped a claude-only component into every target's tree — the same
    silent widening as the unrecognised quoted key, one shape over.
    """
    path = tmp_path / 'demo.md'
    path.write_text('---\n  name: demo\n  targets: [claude]\n---\n', encoding='utf-8')

    assert read_target_scope(path) == {'claude'}
    assert emits_to(path, 'opencode') is False


def test_dedenting_does_not_promote_a_genuinely_nested_key(tmp_path):
    """The other side of the dedent: a key indented BEYOND its siblings stays nested.

    Without this, the fix for the uniformly-indented block would be an
    over-correction that read someone else's ``targets:`` as the component's.
    """
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\n  name: demo\n  metadata:\n    targets: nonsense\n---\n', encoding='utf-8'
    )

    assert read_target_scope(path) is None


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


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param('targets:\n  claude', 'plain scalar continued', id='indented-scalar'),
        pytest.param('targets:\n  claude, opencode', 'plain scalar continued', id='indented-list'),
    ],
)
def test_a_valueless_key_with_an_indented_scalar_is_not_an_empty_declaration(
    tmp_path, frontmatter, expected
):
    """``targets:`` / ``  claude`` is the value ``claude``, not an empty list.

    Both are rejected either way, so the build outcome is unchanged — but
    "declares an empty list" describes a file the author did not write, which
    is the same misdiagnosis the block-scalar and quoted-scalar shapes carried.
    """
    with pytest.raises(TargetScopeError, match=expected):
        read_target_scope(_component(tmp_path, frontmatter))


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets:\nname: after', id='next-key-at-column-zero'),
        pytest.param('targets:', id='nothing-follows'),
        pytest.param('targets:\n\n  # only a comment', id='comment-only'),
    ],
)
def test_a_valueless_key_with_no_indented_content_is_still_empty(tmp_path, frontmatter):
    """The other side: a genuinely empty declaration keeps its own message.

    Without this the fix above would be an over-correction, renaming every
    empty declaration after the construct it is not.
    """
    with pytest.raises(TargetScopeError, match='empty list'):
        read_target_scope(_component(tmp_path, frontmatter))


# ---------------------------------------------------------------------------
# Round 11: shapes the previous round's fixes left open, and the guards those
# fixes added that nothing pinned.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        pytest.param(
            '---\n# a note\n  name: demo\n  targets: [claude]\n---\n',
            {'claude'},
            id='comment-above-an-indented-block',
        ),
        pytest.param(
            '---\n  name: demo\n# a note\n  targets: [claude]\n---\n',
            {'claude'},
            id='comment-among-indented-keys',
        ),
        pytest.param(
            '---\n\n  name: demo\n  targets: [claude]\n---\n',
            {'claude'},
            id='blank-line-above-an-indented-block',
        ),
    ],
)
def test_a_comment_does_not_defeat_the_dedent(tmp_path, text, expected):
    """A comment line carries no structure and must not set the block's indent.

    ``textwrap.dedent`` ignores blank lines but not comment lines, so one
    ``#`` at column 0 pinned the common prefix at zero and re-opened the
    fail-open the dedent was added to close: every key skipped, the
    declaration unread, the component shipped everywhere. Worse, an INVALID
    declaration under such a comment passed the build unreported — the
    fail-closed contract defeated by a comment.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

    assert read_target_scope(path) == expected


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('---\n# note\n  targets: [typo]\n---\n', id='unknown-name'),
        pytest.param('---\n# note\n  targets: []\n---\n', id='empty-list'),
    ],
)
def test_an_invalid_declaration_under_a_comment_still_fails_the_build(tmp_path, text):
    """The direction that matters most: fail-closed must not be evadable.

    A fail-open here is not only a component shipping too widely — it is a
    typo'd or empty declaration passing the build with nothing reported.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

    with pytest.raises(TargetScopeError):
        read_target_scope(path)


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param('targets: # note\n- opencode', {'opencode'}, id='block-at-column-zero'),
        pytest.param('targets: # note\n  - opencode', {'opencode'}, id='block-indented'),
        pytest.param('targets:  # note\n  - claude', {'claude'}, id='two-spaces-before-the-hash'),
    ],
)
def test_a_comment_is_not_an_inline_value(tmp_path, frontmatter, expected):
    """``targets: # note`` has no inline value to YAML; the list below is the value.

    Testing the raw text for emptiness treated the comment as the value and
    reported a perfectly good declaration as "declares an empty list" —
    describing a file the author did not write.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param('targets:\n  [claude, opencode]', {'claude', 'opencode'}, id='one-line'),
        pytest.param('targets:\n  [claude,\n  opencode]', {'claude', 'opencode'}, id='two-lines'),
        pytest.param('targets:\n  [claude]  # why', {'claude'}, id='with-a-comment'),
    ],
)
def test_a_flow_sequence_may_open_on_the_line_below_the_key(tmp_path, frontmatter, expected):
    """A flow sequence is one value however many lines it spans.

    Opening it below the key was reported first as "declares an empty list"
    and then, after the shape work, as "a plain scalar continued across
    lines". Both name a construct the author did not write; the value is a
    flow sequence and is now read as one.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


def test_a_three_hyphen_prefix_line_does_not_close_the_block(tmp_path):
    """The closing fence is a whole LINE. Nothing pinned the line-end anchor.

    The first version of this test used ``description: ---x``, where the
    hyphens sit mid-line and the pattern never reaches them - green either
    way, and so no pin at all. The ``----`` must START a line for the anchor
    to be what rejects it.

    This also pins the one documented divergence from the tree's canonical
    frontmatter reader, which matches a ``---`` PREFIX and does close here.
    Adopting that would truncate this block and hide ``targets:`` - the
    defect the whole-line match exists to prevent.
    """
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\ndescription: a\n----\ntargets: [claude]\n---\n', encoding='utf-8'
    )

    assert read_target_scope(path) == {'claude'}


@pytest.mark.parametrize(
    'frontmatter',
    [
        pytest.param('targets: claude,\n# why\n  opencode', id='inline-value'),
        pytest.param('targets:\n# why\n  claude', id='no-inline-value'),
    ],
)
def test_a_comment_at_column_zero_does_not_end_a_continuation(tmp_path, frontmatter):
    """A comment carries no structure, so it cannot be what ends a value.

    Treating it as structure made the first meaningful line a column-zero one,
    so the continuation went undetected and the value was read as its first
    line alone - silent narrowing, the one direction this must never fail in.
    """
    with pytest.raises(TargetScopeError, match='continued across lines'):
        read_target_scope(_component(tmp_path, frontmatter))


def test_an_immediately_closed_block_has_no_fields(tmp_path):
    """``---`` / ``---`` is an EMPTY frontmatter block; what follows is body.

    This is the only shape the fence search's ``start - 1`` offset changes.
    Nothing pinned it: searching from ``start`` instead skipped the real
    closing fence and read the body's first lines as frontmatter fields.
    """
    path = tmp_path / 'demo.md'
    path.write_text('---\n---\ntargets: [claude]\n---\n', encoding='utf-8')

    assert read_target_scope(path) is None


@pytest.mark.parametrize(
    ('frontmatter', 'expected_noun'),
    [
        pytest.param('targets: >gibberish\n  claude', 'plain scalar', id='not-a-header-at-all'),
        pytest.param('targets: |x\n  claude', 'plain scalar', id='indicator-then-junk'),
        pytest.param('targets: > # c\n  claude', 'block scalar', id='header-with-a-comment'),
        pytest.param('targets: "claude"\n  extra', 'plain scalar', id='quote-already-closed'),
        pytest.param('targets: "claude,\n  opencode"', 'quoted scalar', id='quote-left-open'),
    ],
)
def test_the_shape_boundaries_are_where_they_are_documented(tmp_path, frontmatter, expected_noun):
    """Pin each edge of the two shape tests; all three were unguarded.

    The block-header pattern's end anchor, its comment stripping, and the
    quoted test's "the quote does not recur" threshold could each be loosened
    with the whole suite green. Every input here is rejected either way — what
    is pinned is which construct the failure NAMES, which is the entire point
    of having three nouns.
    """
    with pytest.raises(TargetScopeError, match=expected_noun):
        read_target_scope(_component(tmp_path, frontmatter))


# ---------------------------------------------------------------------------
# Round 12: the indent rule's third attempt, and guards nothing reached.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'text',
    [
        pytest.param(
            '---\n  description: "one\ntwo"\n  targets: [cluade]\n---\n',
            id='quoted-continuation-at-column-zero',
        ),
        pytest.param(
            '---\n  description: "one\ntwo"\n  targets: []\n---\n',
            id='and-the-declaration-is-invalid',
        ),
        pytest.param(
            '---\n  tools: [a,\nb]\n  targets: [cluade]\n---\n',
            id='flow-continuation-at-column-zero',
        ),
    ],
)
def test_an_unreadable_indent_fails_closed_rather_than_open(tmp_path, text):
    """A structural line shallower than the block's keys is refused, not guessed.

    It is either a multi-line value's continuation or malformed YAML, and a
    line scanner cannot tell which. Two earlier indent rules answered it by
    shipping the component everywhere with its declaration UNREAD — which
    also let an invalid declaration past the build with nothing reported.
    Refusing is the module's own stated direction; guessing is not.
    """
    path = tmp_path / 'demo.md'
    path.write_text(text, encoding='utf-8')

    with pytest.raises(TargetScopeError, match='indented LESS'):
        read_target_scope(path)


def test_an_indented_continuation_inside_an_indented_block_is_not_ambiguous(tmp_path):
    """The other side: a continuation that keeps the block's indent reads fine.

    Without this the fail-closed guard would be an over-correction, refusing
    every indented block that happens to carry a multi-line value.
    """
    path = tmp_path / 'demo.md'
    path.write_text(
        '---\n  description: "one\n  two"\n  targets: [claude]\n---\n', encoding='utf-8'
    )

    assert read_target_scope(path) == {'claude'}


@pytest.mark.parametrize(
    ('frontmatter', 'expected_noun'),
    [
        pytest.param('targets:\n  >-\n  claude', 'block scalar', id='block-scalar-below-the-key'),
        pytest.param('targets:\n  |2\n   claude', 'block scalar', id='block-header-with-indicator'),
        pytest.param(
            'targets:\n  "claude,\n  opencode"', 'quoted scalar', id='quoted-below-the-key'
        ),
        pytest.param('targets:\n  claude', 'plain scalar', id='plain-below-the-key'),
    ],
)
def test_a_value_opening_below_the_key_is_diagnosed_not_assumed(
    tmp_path, frontmatter, expected_noun
):
    """The no-inline-value path must diagnose the shape, like the inline path.

    It hard-coded "plain scalar" instead, so a block scalar and a quoted
    scalar opening below the key were both misnamed — reinstating, at a site
    created to fix a different defect, the exact misdiagnosis three earlier
    rounds were spent removing.
    """
    with pytest.raises(TargetScopeError, match=expected_noun):
        read_target_scope(_component(tmp_path, frontmatter))


def test_a_shallow_comment_is_dedented_without_becoming_a_key(tmp_path):
    """The dedent's short-line branch: a line shorter than the base indent.

    Such a line is left-stripped rather than sliced, and nothing pinned that
    — slicing a comment line by the base indent instead turns
    ``#targets: [opencode]`` into a ``targets:`` key at column zero, and the
    component ships to a scope no author wrote.
    """
    path = tmp_path / 'demo.md'
    path.write_text('---\n#targets: [opencode]\n targets: [claude]\n---\n', encoding='utf-8')

    assert read_target_scope(path) == {'claude'}


@pytest.mark.parametrize(
    ('frontmatter', 'expected'),
    [
        pytest.param(
            'targets: [claude,\n  opencode]\n2fa: no', {'claude', 'opencode'}, id='fold-stops-at-]'
        ),
        pytest.param('targets: claude\n2fa: no', {'claude'}, id='bare-value-is-never-folded'),
        pytest.param('targets: [claude]\n2fa: no', {'claude'}, id='closed-value-is-never-folded'),
    ],
)
def test_the_fold_only_runs_where_it_is_meant_to(tmp_path, frontmatter, expected):
    """The fold's entry guard and its closing-bracket exit were both unpinned.

    Deleting either left the suite green while folding the FOLLOWING FIELD
    into the value — ``claude 2fa: no`` — and rejecting a declaration that is
    perfectly well formed. A guard that only the docstring describes is a
    guard that can be deleted by accident.
    """
    assert read_target_scope(_component(tmp_path, frontmatter)) == expected


def test_the_shape_is_read_from_the_raw_value_not_the_comment_stripped_one(tmp_path):
    """Which text the shape test sees is observable, and was unpinned.

    ``targets: "a # b"`` closes its quote, so the raw value is not a continued
    quoted scalar. Stripping the comment first would cut it to ``"a``, whose
    quote does not recur, and the failure would name a construct the author
    did not write. Both readings reject; only the noun differs.
    """
    with pytest.raises(TargetScopeError, match='plain scalar'):
        read_target_scope(_component(tmp_path, 'targets: "a # b"\n  x'))
