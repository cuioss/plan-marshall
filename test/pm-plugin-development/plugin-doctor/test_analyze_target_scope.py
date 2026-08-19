# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``targets-scope-invalid`` rule analyzer.

A component may declare the build-time ``targets:`` frontmatter field naming
the build targets it ships to. The multi-target generator rejects an unknown
target name, an empty declaration, and a value spanning more than one line;
this analyzer surfaces each at authoring time. An absent field means "every
target" and is never flagged.

Test layers:
  * Absent / valid declarations → no finding (positive)
  * Unknown target name → one finding, ``reason == targets_unknown``
  * Empty declaration → one finding, ``reason == targets_empty``
  * A multi-line value → one finding under the reason naming its shape:
    ``targets_multiline_scalar``, ``targets_quoted_scalar``, or
    ``targets_block_scalar``
  * Every component kind (agent, command, skill) is in scope
  * The registered set is DERIVED from the targets' own registrations
  * A tree without ``marketplace/targets/`` still runs the registry-free check
"""

from pathlib import Path

import pytest

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ats = _load_module('_analyze_target_scope', '_analyze_target_scope.py')

analyze_target_scope = _ats.analyze_target_scope
component_files = _ats.component_files
declared_targets = _ats.declared_targets
registered_target_names = _ats.registered_target_names
RULE_ID = _ats.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace tree.
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _marketplace(tmp_path: Path, *, targets: tuple[str, ...] = ('claude', 'opencode')) -> Path:
    """Return a bundles root whose sibling targets tree registers ``targets``."""
    root = tmp_path / 'marketplace'
    for name in targets:
        package = name.replace('-', '_')
        _write(
            root / 'targets' / package / '__init__.py',
            f"from marketplace.targets import register_target\n\nregister_target('{name}', object)\n",
        )
    (root / 'bundles').mkdir(parents=True, exist_ok=True)
    return root / 'bundles'


def _component(bundles: Path, rel: str, frontmatter: str = '') -> Path:
    path = bundles / 'demo' / rel
    extra = f'{frontmatter}\n' if frontmatter else ''
    _write(path, f'---\nname: demo\ndescription: d\n{extra}---\n\n# Body\n')
    return path


# ---------------------------------------------------------------------------
# Declaration parsing
# ---------------------------------------------------------------------------


def test_absent_field_is_not_a_declaration():
    """The common case — no field — is never flagged."""
    assert declared_targets('---\nname: a\ndescription: d\n---\n\n# Body\n') is None


def test_inline_and_block_forms_parse_to_the_same_tokens():
    """Both YAML list spellings yield the same token list."""
    inline = declared_targets('---\nname: a\ntargets: [claude, opencode]\n---\n')
    block = declared_targets('---\nname: a\ntargets:\n  - claude\n  - opencode\n---\n')

    assert inline is not None and block is not None
    assert inline[0] == ['claude', 'opencode']
    assert block[0] == ['claude', 'opencode']


def test_declaration_reports_its_file_line_number():
    """The finding anchors on the declaring line, not on line 1."""
    declaration = declared_targets('---\nname: a\ndescription: d\ntargets: [claude]\n---\n')

    assert declaration is not None
    assert declaration[1] == 4


def test_nested_targets_key_is_not_a_declaration():
    """Only a TOP-LEVEL key counts; an indented one is a different field."""
    assert declared_targets('---\nname: a\nmetadata:\n  targets: nonsense\n---\n') is None


def test_comments_do_not_turn_a_declaration_into_an_empty_one():
    """A commented list declares its targets; reporting it empty names a file that does not exist."""
    block = declared_targets('---\nname: a\ntargets:\n  # why\n  - claude  # here\n---\n')
    inline = declared_targets('---\nname: a\ntargets: [claude]  # here\n---\n')

    assert block is not None and block[0] == ['claude']
    assert inline is not None and inline[0] == ['claude']


def test_a_byte_order_mark_does_not_hide_the_declaration():
    """A BOM'd file must not read as having no frontmatter at all."""
    declaration = declared_targets('﻿---\nname: a\ntargets: [cluade]\n---\n')

    assert declaration is not None
    assert declaration[0] == ['cluade']


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('["#claude"]', ['#claude'], id='quoted-leading-hash'),
        pytest.param('[cla#ude]', ['cla#ude'], id='hash-inside-a-name'),
        pytest.param('[claude]#note', ['[claude]#note'], id='hash-with-no-preceding-space'),
    ],
)
def test_a_hash_that_opens_no_token_is_not_a_comment(value, expected):
    """The comment stripper must not eat a ``#`` that is part of a value.

    The analyzer's `_strip_comment` docstring claims it mirrors the
    generator's parser; this is what holds the two to the same answer.
    """
    declaration = declared_targets(f'---\nname: a\ntargets: {value}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize(
    ('block', 'expected'),
    [
        pytest.param('targets: [claude,\n  opencode]', ['claude', 'opencode'], id='across-lines'),
        pytest.param(
            'targets: [claude,  # and\n  opencode]', ['claude', 'opencode'], id='with-comment'
        ),
        pytest.param('targets: [\n  claude\n  ]', ['claude'], id='opened-on-its-own-line'),
        pytest.param(
            'targets: [claude,\ndescription: a demo\nmode: workflow',
            ['[claude'],
            id='unclosed-does-not-swallow-the-following-fields',
        ),
        pytest.param(
            'targets: [claude,\nopencode] # see https://example.com',
            ['claude', 'opencode'],
            id='continuation-with-a-url-comment',
        ),
        pytest.param(
            'targets: [claude,\n"a: b"]',
            ['claude', 'a: b'],
            id='continuation-quoting-a-colon',
        ),
    ],
)
def test_a_flow_sequence_spanning_lines_is_read_whole(block, expected):
    """Reading only the first physical line would report a target nobody wrote.

    The unclosed case is the mirror of that defect: folding in the rest of
    the block would name the FOLLOWING FIELDS as targets instead.
    """
    declaration = declared_targets(f'---\nname: a\n{block}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize(
    'value',
    [pytest.param('"targets"', id='double-quoted'), pytest.param("'targets'", id='single-quoted')],
)
def test_a_quoted_key_is_still_a_declaration(value):
    """``"targets":`` is the same key as ``targets:`` to any YAML reader.

    Missing it failed OPEN in the generator — the component shipped
    everywhere — and silently here, so the authoring-time net missed it too.
    """
    declaration = declared_targets(f'---\nname: a\n{value}: [cluade]\n---\n')

    assert declaration is not None
    assert declaration[0] == ['cluade']


@pytest.mark.parametrize(
    'value',
    [pytest.param('"targets"', id='double-quoted'), pytest.param("'targets'", id='single-quoted')],
)
def test_a_quoted_key_reaches_the_rule_itself(tmp_path, value):
    """The NET must flag it, not merely the parser underneath the net.

    Asserting only the parser leaves the claim "the authoring-time net
    missed it too" resting on an entry point no test exercises.
    """
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/quoted.md', f'{value}: [cluade]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['unknown_targets'] == ['cluade']


@pytest.mark.parametrize(
    'value',
    [pytest.param('targets"', id='trailing-quote-only'), pytest.param('"targets', id='leading-quote-only')],
)
def test_a_mismatched_quote_is_not_the_targets_key(tmp_path, value):
    """A mismatched quote is a different key — or no key at all — so nothing is flagged.

    ``targets"`` is a distinct key to YAML; ``"targets`` is not well-formed
    YAML at all. Either way the component declares no scope here.
    """
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/mismatched.md', f'{value}: [cluade]')

    assert analyze_target_scope(bundles) == []


@pytest.mark.parametrize(
    ('block', 'expected'),
    [
        pytest.param('targets: [claude,\n2fa: no', ['[claude', '2fa: no'], id='digit-initial-key'),
        pytest.param('targets: [claude,\n"q": v', ['[claude', 'q": v'], id='quoted-key'),
        pytest.param(
            'targets: [claude,\nhttps://example.com', ['[claude'], id='bare-url-at-column-zero'
        ),
    ],
)
def test_the_fold_boundary_misreads_exactly_where_it_is_documented_to(block, expected):
    """Pin the two misreads the fold's docstring names, so neither can drift.

    Both were unguarded: each could be falsified in code with this suite
    fully green. Every one of these inputs is rejected downstream, which is
    the property that makes the heuristic tolerable.
    """
    declaration = declared_targets(f'---\nname: a\n{block}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


def test_a_plain_scalar_continued_across_lines_is_flagged(tmp_path):
    """The authoring-time net reports the shape the build rejects."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/multiline.md', 'targets: claude,\n  opencode')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_multiline_scalar'
    assert 'continued across lines' in findings[0]['description']


def test_a_supported_form_is_not_flagged_as_a_continued_scalar(tmp_path):
    """The block form is indented too; it must not trip the continuation check."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/block.md', 'targets:\n  - claude')

    assert analyze_target_scope(bundles) == []


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: claude,\n  - opencode', id='dash-continuation'),
        pytest.param('targets: claude\n  - opencode', id='dash-continuation-bare'),
    ],
)
def test_a_dash_continuation_does_not_escape_the_guard(tmp_path, value):
    """A continuation beginning with ``-`` is still a continuation."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/dash.md', value)

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_multiline_scalar'


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: >-\n  claude', id='folded'),
        pytest.param('targets: |-\n  claude', id='literal'),
        pytest.param('targets: |2\n   claude', id='indent-indicator'),
        pytest.param('targets: >3-\n   claude', id='indent-then-chomp'),
        pytest.param('targets: |-2\n   claude', id='chomp-then-indent'),
    ],
)
def test_a_block_scalar_is_reported_as_one(tmp_path, value):
    """The finding names the construct the author wrote, not a different one.

    The indentation-indicator spellings are here because the first version
    matched a fixed SET of the six chomping spellings, leaving 54 of the 60
    legal headers reported as continued plain scalars.
    """
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/block.md', value)

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_block_scalar'
    assert 'block scalar' in findings[0]['description']


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: "claude,\n  opencode"', id='double-quoted'),
        pytest.param("targets: 'claude,\n  opencode'", id='single-quoted'),
    ],
)
def test_a_quoted_scalar_continued_across_lines_is_reported_as_one(tmp_path, value):
    """A quoted multi-line value is flagged, but it is not a PLAIN scalar."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/quoted.md', value)

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_quoted_scalar'
    assert 'quoted scalar continued across lines' in findings[0]['description']


@pytest.mark.parametrize(
    'sentinel_text',
    [
        pytest.param('\x00multiline-plain-scalar', id='plain'),
        pytest.param('\x00quoted-scalar', id='quoted'),
        pytest.param('\x00block-scalar', id='block'),
    ],
)
def test_a_real_token_equal_to_a_sentinel_is_not_mistaken_for_one(tmp_path, sentinel_text):
    """EVERY sentinel is compared by IDENTITY, and that is what makes them safe.

    A component could declare a sentinel's literal text as a target name. It
    must be treated as an unknown NAME, not as the shape the sentinel stands
    for — which is why the comparison is ``is`` and not ``==``. Nothing pinned
    that: swapping the operator left the suite green, and when the check was
    later duplicated per shape only one of the copies was covered.
    """
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/collide.md', f'targets: ["{sentinel_text}"]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_unknown'


def test_every_multiline_shape_has_a_finding_of_its_own(tmp_path):
    """The sentinel table and the finding table cover the same shapes.

    A shape added to the parser with no finding to report it would classify
    silently and then fall through to the empty-declaration branch, reporting
    a component that ships nowhere — a message describing a file that does
    not exist.
    """
    assert set(_ats._MULTILINE_SENTINELS) == set(_ats._MULTILINE_FINDING)
    reasons = {reason for _description, reason in _ats._MULTILINE_FINDING.values()}
    assert len(reasons) == len(_ats._MULTILINE_FINDING)


def test_the_fold_joins_with_a_space_and_that_is_what_rejects_an_overrun(tmp_path):
    """The space join is the load-bearing half of the fold's safety argument.

    ``targets: [open`` / ``code]`` closes its bracket, so only the space in
    ``open code`` keeps it out of the registry; ``''.join`` would yield an
    accepted ``opencode``. There must be NO comma in the fixture — with one,
    the comma does the splitting and the test passes either way. The generator
    suite had exactly that defect, and this suite had no such test at all.
    """
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/fold.md', 'targets: [open\ncode]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_unknown'
    assert findings[0]['details']['unknown_targets'] == ['open code']


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('--- \nname: demo\ntargets: [cluade]\n---\n', id='opening-space'),
        pytest.param('---\nname: demo\ntargets: [cluade]\n--- \n', id='closing-space'),
        pytest.param('---\n  name: demo\n  targets: [cluade]\n---\n', id='uniform-indent'),
    ],
)
def test_shapes_the_column_zero_scan_missed_are_still_scanned(tmp_path, text):
    """Two fail-open shapes: a whitespace-suffixed fence, and a uniform indent.

    Both read as "no declaration" before, in the build and here alike, so a
    typo'd component shipped everywhere with nothing reported at authoring
    time either.
    """
    bundles = _marketplace(tmp_path)
    _write(bundles / 'demo' / 'commands' / 'shape.md', text)

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_unknown'


def test_dedenting_does_not_promote_a_genuinely_nested_key(tmp_path):
    """A key indented BEYOND its siblings stays nested after the dedent."""
    bundles = _marketplace(tmp_path)
    _write(
        bundles / 'demo' / 'commands' / 'nested.md',
        '---\n  name: demo\n  metadata:\n    targets: [cluade]\n---\n',
    )

    assert analyze_target_scope(bundles) == []


# ---------------------------------------------------------------------------
# The derived registry
# ---------------------------------------------------------------------------


def test_registered_names_are_derived_from_the_targets_own_registrations(tmp_path):
    """Adding a target's registration widens the set with no edit to the rule."""
    bundles = _marketplace(tmp_path, targets=('claude', 'opencode', 'newcomer'))

    assert registered_target_names(bundles) == frozenset({'claude', 'opencode', 'newcomer'})


def test_registry_is_unavailable_without_a_targets_tree(tmp_path):
    """A consumer install carries no targets tree, so names cannot be checked."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True)

    assert registered_target_names(bundles) is None


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def test_valid_declaration_produces_no_finding(tmp_path):
    """A registry-valid declaration is accepted."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/ok.md', 'targets: [claude]')

    assert analyze_target_scope(bundles) == []


def test_component_without_the_field_produces_no_finding(tmp_path):
    """The default — ship everywhere — is not a defect."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/plain.md')

    assert analyze_target_scope(bundles) == []


def test_unknown_target_name_is_flagged(tmp_path):
    """A typo is reported with the offending value and the registered set."""
    bundles = _marketplace(tmp_path)
    path = _component(bundles, 'commands/typo.md', 'targets: [cluade]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['file'] == str(path)
    assert finding['severity'] == 'error'
    assert finding['details']['reason'] == 'targets_unknown'
    assert finding['details']['unknown_targets'] == ['cluade']
    assert finding['details']['registered_targets'] == ['claude', 'opencode']
    assert 'cluade' in finding['description']
    # The text an operator reads must not claim the component still ships to
    # SOME targets — the build rejects the declaration and ships it nowhere.
    assert 'the build fails rather than shipping the component anywhere' in finding['description']
    assert 'ships to fewer targets' not in finding['description']


def test_one_valid_name_does_not_excuse_an_unknown_one(tmp_path):
    """A partially-valid list is still rejected."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/mixed.md', 'targets: [claude, nope]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['unknown_targets'] == ['nope']


def test_empty_declaration_is_flagged(tmp_path):
    """A component that ships nowhere is an authoring error."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/empty.md', 'targets: []')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_empty'


def test_empty_declaration_is_flagged_without_a_targets_tree(tmp_path):
    """The registry-free check still runs where names cannot be validated."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    _component(bundles, 'commands/empty.md', 'targets: []')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_empty'


def test_unknown_name_is_not_flagged_without_a_targets_tree(tmp_path):
    """An absent registry is reported by silence, never by a fabricated verdict."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    _component(bundles, 'commands/typo.md', 'targets: [cluade]')

    assert analyze_target_scope(bundles) == []


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_every_component_kind_is_scanned(tmp_path):
    """Agents, commands, and skill manifests all carry the field."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'agents/a.md')
    _component(bundles, 'commands/c.md')
    _component(bundles, 'skills/s/SKILL.md')

    scanned = {path.relative_to(bundles / 'demo').as_posix() for path in component_files(bundles)}

    assert scanned == {'agents/a.md', 'commands/c.md', 'skills/s/SKILL.md'}


def test_every_component_kind_is_flagged(tmp_path):
    """A defect is reported wherever it lives, not only in commands."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'agents/a.md', 'targets: [cluade]')
    _component(bundles, 'commands/c.md', 'targets: [cluade]')
    _component(bundles, 'skills/s/SKILL.md', 'targets: [cluade]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 3
    assert {Path(f['file']).name for f in findings} == {'a.md', 'c.md', 'SKILL.md'}


def test_a_skill_directory_without_a_manifest_is_not_scanned(tmp_path):
    """A skill directory carrying no SKILL.md contributes no component."""
    bundles = _marketplace(tmp_path)
    _write(bundles / 'demo' / 'skills' / 'empty-skill' / 'notes.md', '# notes\n')

    assert component_files(bundles) == []


def test_a_valueless_key_with_an_indented_scalar_is_not_an_empty_declaration(tmp_path):
    """``targets:`` / ``  claude`` is the value ``claude``, not an empty list."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/valueless.md', 'targets:\n  claude')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_multiline_scalar'


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets:\nextra: after', id='next-key-at-column-zero'),
        pytest.param('targets:', id='nothing-follows'),
    ],
)
def test_a_valueless_key_with_no_indented_content_is_still_empty(tmp_path, value):
    """The other side, so the fix above cannot become an over-correction."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/empty.md', value)

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_empty'
