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

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import load_script_module


# Called with LITERALS rather than through a `_load_module(name, filename)`
# helper, which is the pattern this directory's other suites use. The loader
# contract guard (`test/plan-marshall/script-shared/`) resolves a call site
# statically only when its arguments are literals or module-level constants;
# a helper that forwards its parameters is invisible to it, and every such
# site widens the blind spot the guard bounds. Passing literals keeps this
# file inside what the guard can see.
_ats = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_target_scope.py', '_analyze_target_scope'
)

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
# The shape fixtures. Both the parametrize lists BELOW and the soundness
# corpus read these, so a row cannot be added to one and missed by the other —
# which is how the last three soundness breaks each reached a released commit.
# ---------------------------------------------------------------------------

#: (value, names) - shapes this scanner reads, with what each yields.
_READS: tuple[tuple[str, list[str], str], ...] = (
    ('targets: [claude, opencode]', ['claude', 'opencode'], 'inline-flow'),
    ('targets: claude', ['claude'], 'bare-scalar'),
    ('targets: claude, opencode', ['claude', 'opencode'], 'bare-list'),
    ('targets:\n  - claude\n  - opencode', ['claude', 'opencode'], 'block'),
    ('targets: [claude]  # why', ['claude'], 'trailing-comment'),
    ('targets:\n  # why\n  - claude', ['claude'], 'comment-in-a-block'),
    ('targets: [cla#ude]', ['cla#ude'], 'hash-inside-a-name'),
    ('"targets": [claude]', ['claude'], 'quoted-key'),
    ('targets: []', [], 'empty-flow'),
    ('targets:', [], 'no-value'),
    ('targets: ~', [], 'tilde-null'),
    ('targets: null', [], 'null'),
    ('targets: Null', [], 'capitalised-null'),
    ('targets: NULL', [], 'shouted-null'),
    ('targets:\nname: after', [], 'next-key-follows'),
    ('targets:\n- claude', ['claude'], 'block-at-column-zero'),
    ('targets:\n- claude\n- opencode', ['claude', 'opencode'], 'two-at-zero'),
    ('targets:\n\n- claude', ['claude'], 'blank-then-column-zero'),
    ('targets: [cluade]\ntargets: [claude]', ['claude'], 'duplicate-last-wins'),
    ('targets:\ntargets: [claude]', ['claude'], 'duplicate-empty-then-list'),
    ('targets: [claude]\ntargets:', [], 'duplicate-list-then-empty'),
    ('targets: ~\ntargets: [claude]', ['claude'], 'null-then-list'),
    ('targets: null\ntargets: claude', ['claude'], 'null-word-then-scalar'),
    ('targets: [a]\ntargets: [b]\ntargets: [claude]', ['claude'], 'three-keys'),
    ('"targets": [a]\ntargets: [claude]', ['claude'], 'quoted-then-bare'),
)

#: Shapes this scanner must DECLINE. Each is legal YAML the build reads, or a
#: shape whose value it cannot resolve; every one must yield no finding.
_DECLINES: tuple[tuple[str, str], ...] = (
    ('targets: >-\n  claude', 'folded-block-scalar'),
    ('targets: |2\n   claude', 'literal-with-indicator'),
    ('targets: "claude,\n  opencode"', 'quoted-across-lines'),
    ('targets: [claude,\n  opencode]', 'flow-across-lines'),
    ('targets:\n  [claude]', 'flow-below-the-key'),
    ('targets:\n  claude', 'scalar-below-the-key'),
    ('targets: claude,\n  opencode', 'scalar-across-lines'),
    ('targets: {claude: yes}', 'mapping'),
    ('targets: &anchor [claude]', 'anchor'),
    ("targets: 'claude'", 'quoted-scalar'),
    ('targets: "claude"', 'double-quoted-scalar'),
    ('targets: >', 'bare-folded-indicator'),
    ('targets: |', 'bare-literal-indicator'),
    ('targets: &a claude', 'anchor-without-a-continuation'),
    ('targets: *a', 'alias'),
    ('targets: >-\n  claude\ntargets: [cluade]', 'unreadable-duplicate'),
    ('targets: [cluade]\ntargets:\n  claude', 'unreadable-block-duplicate'),
    ('targets:\n- "claude"', 'quoted-item-in-a-block'),
    ('targets: ["claude"]', 'quoted-item-in-a-flow-sequence'),
    ("targets: ['claude']", 'single-quoted-item'),
    ('targets: [!!str claude]', 'tagged-item'),
    ('targets: [&a claude]', 'anchored-item'),
    ('targets: [claude, "claude"]', 'one-bare-one-quoted'),
    ('targets: [cluade,', 'unclosed-flow-sequence'),
    ('targets: [[claude]]', 'nested-flow-sequence'),
    ('targets: [a, [b]]', 'nested-second-item'),
    ('targets: [{a: b}]', 'mapping-inside-a-sequence'),
    ('targets: [a{b]', 'brace-inside-a-sequence'),
    ('targets: a: b', 'a-colon-in-a-bare-value'),
    ('targets: claude\n# why\n  opencode', 'column-zero-comment-then-continuation'),
    # An empty item. Without the emptiness check the scanner indexes into
    # an empty string and raises INSIDE a quality-gate rule.
    ('targets:\n  -\n', 'an-empty-block-item'),
)

#: Whole-file shapes: what the scanner does with a BLOCK rather than a value.
_BLOCKS_WITHOUT_A_DECLARATION: tuple[tuple[str, str], ...] = (
    ('---\n  name: a\n  targets: [claude]\n---\n', 'indented-block'),
    ('---\nname: a\nmeta:\n  targets: nonsense\n---\n', 'nested-key'),
    ('# no frontmatter\n', 'no-frontmatter'),
    ('---\nname: a\n---\n', 'no-field'),
    ('---\nname: a\ntargets": [claude]\n---\n', 'mismatched-quote'),
    ('---\n"targetsX: [cluade]\n---\n', 'unmatched-opening-quote-on-the-key'),
    ('---\ntargets\n---\n', 'a-bare-word-is-not-a-key'),
    ('---\ntargets:#c\n---\n', 'hash-straight-after-the-colon'),
    ('---\ntargets:[claude]\n---\n', 'bracket-straight-after-the-colon'),
    ('---\ntargets:claude\n---\n', 'value-straight-after-the-colon'),
    ('---\n---\ntargets: [cluade]\n---\n', 'immediately-closed-block'),
    # A `targets:` line inside a construct opened above it only LOOKS like a
    # key. Six root causes of unsoundness have been found in this rule; this
    # was the sixth, and it survived the fixes for the fourth and fifth.
    (
        '---\nname: real\ndescription: "a description\ntargets: [cluade]\nthat wraps"\n---\n',
        'inside-a-multi-line-quoted-scalar',
    ),
    ('---\na: [\ntargets: [cluade]\n]\n---\n', 'inside-an-unterminated-flow-sequence'),
    ('---\na: {\ntargets: bad\n}\n---\n', 'inside-an-unterminated-flow-mapping'),
    ('---\ndescription: "one\ntargets:\n"\n---\n', 'valueless-key-inside-a-quoted-scalar'),
)

#: Whole-file shapes the scanner DOES read, so the guard above cannot become
#: an over-correction that silences everything.
_BLOCKS_WITH_A_DECLARATION: tuple[tuple[str, list[str], str], ...] = (
    ('\ufeff---\nname: a\ntargets: [cluade]\n---\n', ['cluade'], 'byte-order-mark'),
    ('--- \nname: a\ntargets: [cluade]\n---\n', ['cluade'], 'open-fence-space'),
    ('---\nname: a\ntargets: [cluade]\n--- \n', ['cluade'], 'close-fence-space'),
    ('---\nname: a\ntargets: [cluade]\n---', ['cluade'], 'close-fence-at-eof'),
    (
        '---\ndescription: a\n----\ntargets: [cluade]\n---\n',
        ['cluade'],
        'four-hyphen-line-is-not-a-fence',
    ),
    ("---\ndescription: it's fine\ntargets: [cluade]\n---\n", ['cluade'], 'an-apostrophe-is-not-a-quoted-scalar'),
    ('---\ntools: [a, b]\ntargets: [cluade]\n---\n', ['cluade'], 'a-closed-flow-above-the-key'),
)


# ---------------------------------------------------------------------------
# What the scanner reads, and what it declines to
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('value', 'expected'),
    [pytest.param(value, expected, id=key) for value, expected, key in _READS],
)
def test_shapes_the_scanner_reads(value, expected):
    """The spellings this rule is certain of, and the names each yields."""
    declaration = declared_targets(f'---\nname: a\n{value}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize('value', [pytest.param(value, id=key) for value, key in _DECLINES])
def test_shapes_the_scanner_declines_to_read(value):
    """Silence, not a guess. Every one of these is legal YAML the build reads.

    An earlier version of this rule tried to read them and was wrong about six
    distinct families across fifteen verification rounds — twice reporting a
    perfectly good declaration as a build-failing error, and three times
    reading a whole block as "no declaration" while the build did the same.
    Declining is the accurate answer for a scanner that cannot parse YAML, and
    it is what keeps this rule's findings trustworthy.
    """
    assert declared_targets(f'---\nname: a\n{value}\n---\n') is None


@pytest.mark.parametrize(
    'text', [pytest.param(text, id=key) for text, key in _BLOCKS_WITHOUT_A_DECLARATION]
)
def test_blocks_that_yield_no_declaration(text):
    """No key here, or none this scanner will claim. Either way: silence."""
    assert declared_targets(text) is None


@pytest.mark.parametrize(
    ('text', 'expected'),
    [pytest.param(text, expected, id=key) for text, expected, key in _BLOCKS_WITH_A_DECLARATION],
)
def test_blocks_the_scanner_does_read(text, expected):
    """The other side of every block-level guard.

    Without these, each guard above could be widened until the rule declined
    everything — sound, and useless. A BOM, an invisible fence space, a fence
    at end-of-file, a ``----`` line, an apostrophe, and a closed flow sequence
    above the key must all still read.
    """
    declaration = declared_targets(text)

    assert declaration is not None
    assert declaration[0] == expected


def test_a_declaration_reports_its_file_line_number():
    """The finding anchors on the declaring line, not on line 1."""
    declaration = declared_targets('---\nname: a\ndescription: d\ntargets: [claude]\n---\n')

    assert declaration is not None
    assert declaration[1] == 4


# ---------------------------------------------------------------------------
# Soundness — the promise this rule actually makes
# ---------------------------------------------------------------------------

# The corpus is DERIVED, not transcribed. Two hand-copied versions each
# omitted the shape that was breaking soundness at the time — round 13's
# missed the column-zero block, and its replacement missed the quoted flow
# item that the generator suite pins as valid three files away. Pulling the
# rows from the fixtures both suites already maintain means a shape cannot be
# added to either suite and left out of the soundness check.
def _soundness_corpus() -> list[tuple[str, bool]]:
    """Every declaration shape either suite exercises, as ``(text, whole_file)``.

    DERIVED, from five fixtures across two files, because three hand-copied
    versions each omitted the shape that was breaking soundness at the time:
    round 13's missed the column-zero block, round 14's missed the quoted flow
    item that the generator suite pins as valid, and round 15's read only the
    per-value dict and so missed the whole-file rows beside it — one of which
    is the indented sibling of the family that broke soundness a sixth time.

    Pulling every row from the fixtures both suites already parametrize over
    means a shape cannot be added to either suite and left out of this check.
    """
    import importlib.util
    import pathlib

    sibling = (
        pathlib.Path(__file__).resolve().parents[2]
        / 'marketplace' / 'targets' / 'test_component_targets.py'
    )
    spec = importlib.util.spec_from_file_location('_ct_fixtures', sibling)
    assert spec is not None and spec.loader is not None, sibling
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)

    rows: list[tuple[str, bool]] = []
    # Each derived source is asserted non-empty. Without this, renaming or
    # emptying one drops its contribution to zero while the hardcoded rows
    # below keep `rows` truthy — the sweep stays green over less than it
    # claims, which is the exact regression the derivation exists to prevent.
    for name in ('_ACCEPTED_FORMS', '_ONCE_REFUSED_NOW_READ', '_ONCE_REFUSED_WHOLE_FILE'):
        source = getattr(fixtures, name, None)
        assert source, f'{sibling}: {name} is missing or empty — the corpus would narrow silently'

    for form, _expected in fixtures._ACCEPTED_FORMS.values():
        rows.append((form, False))
    for form, _expected in fixtures._ONCE_REFUSED_NOW_READ.values():
        if form:
            rows.append((form, False))
    # The whole-file spellings for the rows whose payload lives in a separate
    # dict. Reading only the dict beside them is exactly what round 15 missed.
    for text in fixtures._ONCE_REFUSED_WHOLE_FILE.values():
        rows.append((text, True))
    rows += [(value, False) for value, _names, _key in _READS]
    rows += [(value, False) for value, _key in _DECLINES]
    rows += [(text, True) for text, _key in _BLOCKS_WITHOUT_A_DECLARATION]
    rows += [(text, True) for text, _names, _key in _BLOCKS_WITH_A_DECLARATION]
    # Invalid values. Neither suite's shape fixtures carry these, because both
    # are about what is READ rather than about what the build then rejects.
    rows += [
        (value, False)
        for value in (
            'targets: [cluade]', 'targets: [claude, cluade]', 'targets: cluade',
            'targets: [pr-agent]', 'targets:\n- cluade', 'targets: ["cluade"]',
            "targets: ['cluade']", 'targets:\n- "cluade"', 'targets: 3',
            'targets: true', 'targets: [1, 2]', 'targets: !!str claude',
            'targets: [claude] extra', 'targets: [pr-agent, claude]',
            'name: only', 'metadata:\n  targets: nonsense',
        )
    ]
    return rows



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

    The fake tree registers the SAME target set the build has, ``pr-agent``
    included. Registering fewer made the two sides disagree about what a name
    means, so a false positive on a `pr-agent`-bearing declaration would have
    been created or masked by the mismatch rather than measured.
    """
    from marketplace.targets import TARGET_REGISTRY
    from marketplace.targets.component_targets import TargetScopeError, read_target_scope

    # DERIVED, not transcribed: the fake tree must register exactly what the
    # build resolves against, or the differential measures a registry mismatch
    # instead of the rule. Registering a fourth target would otherwise
    # reintroduce that disagreement with no test failure to signal it.
    registered = tuple(sorted(TARGET_REGISTRY))
    assert registered, 'no target registered — the differential would be vacuous'

    corpus = _soundness_corpus()
    for index, (text, whole_file) in enumerate(corpus):
        bundles = _marketplace(tmp_path / f'case{index}', targets=registered)
        if whole_file:
            component = bundles / 'demo' / 'commands' / 'case.md'
            _write(component, text)
        else:
            component = _component(bundles, 'commands/case.md', text)
        findings = analyze_target_scope(bundles)
        if not findings:
            continue
        try:
            scope = read_target_scope(component)
        except TargetScopeError:
            continue
        raise AssertionError(
            f'{text!r}: the rule reported '
            f'{findings[0]["details"]["reason"]} but the build accepted it as {scope}'
        )


# ---------------------------------------------------------------------------
# The derived registry
# ---------------------------------------------------------------------------


def test_a_hyphenated_target_name_is_derived(tmp_path):
    """The registry regex must accept every character a name may contain.

    Narrowing it to ``[a-z]+`` left the suite green while `pr-agent` dropped
    out of the derived set — so a declaration naming it was reported unknown
    while the build accepted it. The registry-mismatch class again, and the
    corpus alone cannot catch it: `targets: [pr-agent]` fails the build anyway
    for naming no component-tree target, so only a MIXED declaration
    discriminates.
    """
    bundles = _marketplace(tmp_path, targets=('claude', 'pr-agent'))

    assert registered_target_names(bundles) == frozenset({'claude', 'pr-agent'})


def test_the_rule_is_build_failing(tmp_path):
    """Its severity is what makes it a gate, and it was asserted only in prose.

    Downgrading `error` to `warning` left every test green while the rule
    stopped failing the build — the thing two register documents describe it
    as doing.
    """
    assert _ats.RULE_DESCRIPTOR.severity == 'error'

    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/bad.md', 'targets: [cluade]')

    assert analyze_target_scope(bundles)[0]['severity'] == 'error'


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


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('targets: ~\ntargets: [claude]', ['claude'], id='null-then-list'),
        pytest.param('targets: null\ntargets: claude', ['claude'], id='null-word-then-scalar'),
        pytest.param('targets: [a]\ntargets: [b]\ntargets: [claude]', ['claude'], id='three-keys'),
        pytest.param('"targets": [a]\ntargets: [claude]', ['claude'], id='quoted-then-bare'),
    ],
)
def test_the_last_readable_declaration_wins_whatever_the_earlier_ones_are(value, expected):
    """Every branch of the duplicate-key loop, not only the list-then-list one.

    The null branch was unpinned and reverting it to first-wins left the suite
    green while the rule reported an empty declaration the build accepts.
    """
    declaration = declared_targets(f'---\nname: a\n{value}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('targets: [cluade]\ntargets:\n  claude', id='unreadable-block-duplicate'),
        pytest.param('targets:\n- "claude"', id='quoted-item-in-a-block'),
        pytest.param('targets: ["claude"]', id='quoted-item-in-a-flow-sequence'),
        pytest.param("targets: ['claude']", id='single-quoted-item'),
        pytest.param('targets: [!!str claude]', id='tagged-item'),
        pytest.param('targets: [&a claude]', id='anchored-item'),
        pytest.param('targets: [claude, "claude"]', id='one-bare-one-quoted'),
        pytest.param('targets: "claude"', id='double-quoted-scalar'),
        pytest.param('targets: [cluade,', id='unclosed-flow-sequence'),
        pytest.param('targets: |', id='bare-literal-indicator'),
        pytest.param('targets: Null', id='capitalised-null-is-empty-not-a-name'),
    ],
)
def test_shapes_that_must_not_produce_a_finding(value):
    """Each of these was unpinned, and dropping its guard breaks SOUNDNESS.

    The quoted-item rows are the fifth way this rule managed to fail a valid
    file: `_is_readable` inspected only the value's first character, so a
    quoted item inside a flow sequence read as a bare name and was reported —
    with its quotes — as an unknown target. The generator suite pins that
    exact spelling as one an author may write.
    """
    declaration = declared_targets(f'---\nname: a\n{value}\n---\n')

    assert declaration is None or declaration[0] == []


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('--- \nname: a\ntargets: [cluade]\n---\n', id='open-fence-space'),
        pytest.param('---\nname: a\ntargets: [cluade]\n--- \n', id='close-fence-space'),
        pytest.param('---\nname: a\ntargets: [cluade]\n---', id='close-fence-at-eof'),
    ],
)
def test_fence_tolerance_is_pinned_here_too(text):
    """All three fence properties were pinned in the generator suite and neither here.

    The mirror-parity gap again: parser-vs-parser behaviour is checked by a
    differential, while each suite's own coverage is checked by reading.
    """
    declaration = declared_targets(text)

    assert declaration is not None
    assert declaration[0] == ['cluade']


def test_the_rule_walks_every_component_kind_the_build_walks(tmp_path):
    """`component_files` must find exactly what `iter_component_manifests` does.

    The two walks are duplicated because this module is stdlib-only and cannot
    import `marketplace.targets`. The duplication is forced; the differential
    is not. Without it, a fourth component directory added to the build's walk
    would silently stop being scanned here, and this suite would stay green
    because its other tests pin this module's own literal set rather than
    comparing the two.

    This test lives in the meta-project, so it may import what the module it
    tests may not.
    """
    from marketplace.targets.component_targets import iter_component_manifests

    bundles = _marketplace(tmp_path)
    bundle = bundles / 'demo'
    for rel in ('agents/a.md', 'commands/c.md', 'skills/s/SKILL.md'):
        _write(bundle / rel, '---\nname: x\ndescription: d\n---\n\n# B\n')
    # Shapes neither walk counts, so the differential is not trivially equal.
    _write(bundle / 'skills' / 'no-manifest' / 'reference.md', '# not a manifest\n')
    _write(bundle / 'commands' / '.hidden.md', '---\nname: h\n---\n')

    from_the_build = {manifest for manifest, _root in iter_component_manifests(bundle)}
    from_the_rule = set(component_files(bundles))

    assert from_the_rule, 'the walk found nothing — the comparison would be vacuous'
    assert from_the_rule == from_the_build
