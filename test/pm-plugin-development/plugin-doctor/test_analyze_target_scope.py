# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``targets-scope-invalid`` rule analyzer.

A component may declare the build-time ``targets:`` frontmatter field naming
the build targets it ships to. The build reads it with ``yaml.safe_load``;
this analyzer is stdlib-only and cannot, so it reads the shapes it is certain
of and stays SILENT on the rest rather than guessing.

The promise it makes is soundness, not completeness: anything it reports is a
real build failure. ``test_every_finding_is_a_real_build_failure`` is that
promise, enforced over a corpus rather than asserted in prose.

Test layers:
  * Absent / valid declarations → no finding (positive)
  * Unknown target name → one finding, ``reason == targets_unknown``
  * Empty declaration → one finding, ``reason == targets_empty``
  * Shapes the scanner will not read → no finding, and the build decides
  * Soundness: every finding it does produce is a build failure
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
# What the scanner reads, and what it declines to
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('targets: [claude, opencode]', ['claude', 'opencode'], id='inline-flow'),
        pytest.param('targets: claude', ['claude'], id='bare-scalar'),
        pytest.param('targets: claude, opencode', ['claude', 'opencode'], id='bare-list'),
        pytest.param('targets:\n  - claude\n  - opencode', ['claude', 'opencode'], id='block'),
        pytest.param('targets: [claude]  # why', ['claude'], id='trailing-comment'),
        pytest.param('targets:\n  # why\n  - claude', ['claude'], id='comment-in-a-block'),
        pytest.param('targets: [cla#ude]', ['cla#ude'], id='hash-inside-a-name'),
        pytest.param('"targets": [claude]', ['claude'], id='quoted-key'),
        pytest.param('targets: []', [], id='empty-flow'),
        pytest.param('targets:', [], id='no-value'),
        pytest.param('targets: ~', [], id='tilde-null'),
        pytest.param('targets: null', [], id='null'),
        pytest.param('targets:\nname: after', [], id='next-key-follows'),
        # A sequence at column zero is idiomatic YAML and is what an author
        # writes first. Treating it as the next field made this rule fail the
        # quality gate on a valid component.
        pytest.param('targets:\n- claude', ['claude'], id='block-at-column-zero'),
        pytest.param('targets:\n- claude\n- opencode', ['claude', 'opencode'], id='two-at-zero'),
        pytest.param('targets:\n\n- claude', ['claude'], id='blank-then-column-zero'),
        # YAML resolves a duplicate key to the LAST. Reading the first meant
        # reporting on a declaration the build does not use.
        pytest.param('targets: [cluade]\ntargets: [claude]', ['claude'], id='duplicate-last-wins'),
        pytest.param('targets:\ntargets: [claude]', ['claude'], id='duplicate-empty-then-list'),
        pytest.param('targets: [claude]\ntargets:', [], id='duplicate-list-then-empty'),
    ],
)
def test_shapes_the_scanner_reads(value, expected):
    """The spellings this rule is certain of, and the names each yields."""
    declaration = declared_targets(f'---\nname: a\n{value}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: >-\n  claude', id='folded-block-scalar'),
        pytest.param('targets: |2\n   claude', id='literal-with-indicator'),
        pytest.param('targets: "claude,\n  opencode"', id='quoted-across-lines'),
        pytest.param('targets: [claude,\n  opencode]', id='flow-across-lines'),
        pytest.param('targets:\n  [claude]', id='flow-below-the-key'),
        pytest.param('targets:\n  claude', id='scalar-below-the-key'),
        pytest.param('targets: claude,\n  opencode', id='scalar-across-lines'),
        pytest.param('targets: {claude: yes}', id='mapping'),
        pytest.param('targets: &anchor [claude]', id='anchor'),
        pytest.param("targets: 'claude'", id='quoted-scalar'),
        # These reach the opener check itself. The three rows above them do
        # not: a continuation or the bracket test declines each one first, so
        # dropping `>`/`|`/`&` from the opener set left the suite green.
        pytest.param('targets: >', id='bare-folded-indicator'),
        pytest.param('targets: &a claude', id='anchor-without-a-continuation'),
        pytest.param('targets: *a', id='alias'),
        # If any occurrence is unreadable the file is, because the scanner
        # cannot then know which declaration the build will use.
        pytest.param('targets: >-\n  claude\ntargets: [cluade]', id='unreadable-duplicate'),
    ],
)
def test_shapes_the_scanner_declines_to_read(value):
    """Silence, not a guess. Every one of these is legal YAML the build reads.

    The previous version of this rule tried to read them and was wrong about
    six of the ten across twelve verification rounds — twice reporting a
    perfectly good declaration as an error, and three times reading a whole
    block as "no declaration" while the build did the same. Declining is the
    accurate answer for a scanner that cannot parse YAML, and it is what keeps
    the rule's findings trustworthy.
    """
    assert declared_targets(f'---\nname: a\n{value}\n---\n') is None


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('---\n  name: a\n  targets: [claude]\n---\n', id='indented-block'),
        pytest.param('---\nname: a\nmeta:\n  targets: nonsense\n---\n', id='nested-key'),
        pytest.param('# no frontmatter\n', id='no-frontmatter'),
        pytest.param('---\nname: a\n---\n', id='no-field'),
        pytest.param('---\nname: a\ntargets": [claude]\n---\n', id='mismatched-quote'),
        # No whitespace after the colon, so YAML reads the whole line as a
        # plain scalar and there is no key. The build sees none either.
        pytest.param('---\ntargets:#c\n---\n', id='hash-straight-after-the-colon'),
        pytest.param('---\ntargets:[claude]\n---\n', id='bracket-straight-after-the-colon'),
        pytest.param('---\ntargets:claude\n---\n', id='value-straight-after-the-colon'),
        # An immediately-closed block is EMPTY; what follows is body.
        pytest.param('---\n---\ntargets: [cluade]\n---\n', id='immediately-closed-block'),
    ],
)
def test_blocks_that_yield_no_declaration(text):
    """No key here, or none this scanner will claim. Either way: silence.

    The indented block is the interesting row — the build reads it correctly
    and this does not, so the honest answer is to say nothing rather than to
    reimplement YAML's indentation rules, which took three attempts and never
    came out right.
    """
    assert declared_targets(text) is None


def test_a_byte_order_mark_does_not_hide_the_declaration():
    """A BOM must not read as "no frontmatter", which reports nothing at all.

    Pinned in this suite once, dropped in the rewrite, and unpinned until
    round 13 found the mutant surviving.
    """
    declaration = declared_targets('\ufeff---\nname: a\ntargets: [cluade]\n---\n')

    assert declaration is not None
    assert declaration[0] == ['cluade']


def test_a_declaration_reports_its_file_line_number():
    """The finding anchors on the declaring line, not on line 1."""
    declaration = declared_targets('---\nname: a\ndescription: d\ntargets: [claude]\n---\n')

    assert declaration is not None
    assert declaration[1] == 4


# ---------------------------------------------------------------------------
# Soundness — the promise this rule actually makes
# ---------------------------------------------------------------------------

# Every shape either suite exercises, valid and invalid together. The
# soundness test below runs each one through BOTH the rule and the build.
_SOUNDNESS_CORPUS = (
    # Readable, valid.
    'targets: [claude]', 'targets: [claude, opencode]', 'targets: claude',
    'targets: claude, opencode', 'targets:\n  - claude', 'targets:\n- claude',
    'targets:\n- claude\n- opencode', 'targets: [claude]  # why',
    'targets:\n  # why\n  - claude', 'targets:\n\n- claude',
    'targets: [claude, claude]', '"targets": [claude]', "'targets': [claude]",
    # Readable, invalid.
    'targets: [cluade]', 'targets: [claude, cluade]', 'targets: cluade',
    'targets: []', 'targets:', 'targets: ~', 'targets: null', 'targets: NULL',
    'targets: [pr-agent]', 'targets:\n- cluade', 'targets:\nname: after',
    # Duplicate keys - YAML takes the LAST, and reading the first meant
    # reporting on a declaration the build does not use.
    'targets: [cluade]\ntargets: [claude]', 'targets: [claude]\ntargets: [cluade]',
    'targets:\ntargets: [claude]', 'targets: cluade\ntargets: claude',
    'targets: [claude]\ntargets:', 'targets: [claude]\ntargets: [opencode]',
    # No space after the colon - a plain scalar to YAML, not a key at all.
    'targets:#c', 'targets:[claude]', 'targets:claude',
    # Shapes the scanner must decline rather than read.
    'targets: >-\n  claude', 'targets: |2\n   claude', 'targets: "claude,\n  opencode"',
    'targets: [claude,\n  opencode]', 'targets:\n  [claude]', 'targets:\n  claude',
    'targets: claude,\n  opencode', 'targets: {claude: yes}', 'targets: 3',
    'targets: true', 'targets: [1, 2]', 'targets: &a [claude]', 'targets: *a',
    "targets: 'claude'", 'targets: !!str claude', 'targets:\n  -\n', 'targets: [claude,',
    'targets: [cla#ude]', 'targets": [claude]', 'targets: [claude] extra',
    # No declaration.
    'name: only', 'metadata:\n  targets: nonsense',
)


def test_every_finding_is_a_real_build_failure(tmp_path):
    """The rule's one promise, enforced over a corpus rather than asserted.

    This analyzer is an approximation of a build that reads YAML properly, so
    it may MISS a defect — that is the documented trade. What it must never do
    is report one the build accepts: a false positive spends an author's time
    on a correct file and teaches them to distrust the rule.

    Written as a test rather than left to review because every previous round
    of this work re-derived the same ground in a throwaway corpus that died
    with the session, and the next divergence was always found by the next
    round rather than by the suite.
    """
    from marketplace.targets.component_targets import TargetScopeError, read_target_scope

    for index, frontmatter in enumerate(_SOUNDNESS_CORPUS):
        bundles = _marketplace(tmp_path / f'case{index}')
        component = _component(bundles, 'commands/case.md', frontmatter)
        findings = analyze_target_scope(bundles)
        if not findings:
            continue
        try:
            scope = read_target_scope(component)
        except TargetScopeError:
            continue
        raise AssertionError(
            f'{frontmatter!r}: the rule reported '
            f'{findings[0]["details"]["reason"]} but the build accepted it as {scope}'
        )


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


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: [[claude]]', id='nested-flow-sequence'),
        pytest.param('targets: [a, [b]]', id='nested-second-item'),
        pytest.param('targets: [{a: b}]', id='mapping-inside-a-sequence'),
        pytest.param('targets: a: b', id='a-colon-in-a-bare-value'),
        # The comment must sit at COLUMN ZERO. An indented one is already
        # 'indented' to the guard, so it pins nothing — the first draft of
        # this row indented it and the mutant survived.
        pytest.param('targets: claude\n# why\n  opencode', id='column-zero-comment-then-continuation'),
    ],
)
def test_further_shapes_the_scanner_declines_to_read(value):
    """Three `_is_readable` guards and the continuation's comment skip.

    Each was unpinned: dropping it left the whole suite green while the
    scanner read a value it has no business reading. None of them broke
    soundness on its own, which is exactly why nothing caught them — a guard
    that only stops the rule being WRONG-but-still-failing is invisible to a
    test that only checks the verdict.
    """
    assert declared_targets(f'---\nname: a\n{value}\n---\n') is None
