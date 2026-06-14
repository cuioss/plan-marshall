# ruff: noqa: I001, E402
"""Tests for the ``zero-match-rule`` positive-fixture self-test detector.

``_analyze_zero_match_rule.analyze_zero_match_rule`` enforces the zero-match
acceptance criterion from ``references/rule-provenance.md`` § "Provenance
contract for new rules": a rule claimed by the detector's ``FIXTURE_CORPUS``
must actually fire on its known-defect positive fixture. The detector's
candidate scope is ``corpus_rules ∩ registered_rules`` — it reports one
``zero-match-rule`` finding per claimed-and-registered rule ID that fired on no
fixture, and stays silent both for registered rules WITHOUT a corpus entry and
for corpus rules whose ID is not registered.

Test layers (AAA throughout):
  (a) A registered rule WITH a firing positive fixture produces no finding —
      proven both against the real marketplace and an isolated scratch tree.
  (b) A registered rule WITHOUT any firing positive fixture produces exactly
      one ``zero-match-rule`` finding.
  (c) The finding dict shape matches the documented contract.
  (d) The real marketplace produces zero ``zero-match-rule`` findings — every
      shipped corpus rule fires (the build-failing invariant).
  (e) Candidate-set semantics: a registered rule with NO corpus entry is
      silent; a claimed corpus rule that is NOT registered is skipped.
  (f) The new ``zero-match-rule`` emitter row is present in the provenance
      table (the paired ``test_rule_provenance_table.py`` cross-check).

The detector module is imported directly (the conftest sets up the marketplace
PYTHONPATH on import), so no subprocess is needed.
"""

from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

# ---------------------------------------------------------------------------
# Module under test — loaded via the shared module loader so its intra-bundle
# ``from _analyze_* import ...`` corpus references resolve against the real
# scripts dir on sys.path.
# ---------------------------------------------------------------------------

_zmr = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_zero_match_rule.py',
    '_analyze_zero_match_rule',
)

analyze_zero_match_rule = _zmr.analyze_zero_match_rule
registered_rule_ids = _zmr.registered_rule_ids
FixtureSpec = _zmr.FixtureSpec
RULE_ID = _zmr.RULE_ID
FINDING_TYPE = _zmr.FINDING_TYPE
RULE_NAME = _zmr.RULE_NAME

# The scripts-dir layout the detector resolves relative to a marketplace root.
_DOCTOR_SCRIPTS_REL = 'pm-plugin-development/skills/plugin-doctor/scripts'

PROVENANCE_PATH = (
    MARKETPLACE_ROOT
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'references'
    / 'rule-provenance.md'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scratch_root(tmp_path: Path, analyzer_module_src: str) -> Path:
    """Materialize a scratch marketplace root with one doctor analyzer module.

    Writes ``analyzer_module_src`` to a ``_analyze_<...>.py`` file under the
    scratch root's plugin-doctor scripts dir so ``registered_rule_ids`` and
    ``_emitter_for_rule`` resolve against a controlled module set. Returns the
    scratch marketplace root (the directory the detector is handed).
    """
    scripts_dir = tmp_path / _DOCTOR_SCRIPTS_REL
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / '_analyze_scratch_rule.py').write_text(
        analyzer_module_src, encoding='utf-8'
    )
    return tmp_path


# A scratch analyzer source that statically declares exactly one kebab-case
# rule ID in a ``'type'`` literal position, so ``registered_rule_ids`` extracts
# precisely ``{'scratch-zero-rule'}`` from the scratch tree.
_SCRATCH_ANALYZER_SRC = (
    "def analyze_scratch_rule(root):\n"
    "    return [{'type': 'scratch-zero-rule', 'rule_id': 'scratch-zero-rule'}]\n"
)


# ---------------------------------------------------------------------------
# (a) Registered rule WITH a firing positive fixture → no finding
# ---------------------------------------------------------------------------


def test_registered_rule_with_firing_fixture_produces_no_finding(tmp_path, monkeypatch):
    """A claimed-and-registered rule whose fixture fires yields no finding."""
    # Arrange — a scratch tree registering exactly 'scratch-zero-rule', and a
    # corpus that claims that rule with an analyzer that DOES fire on it.
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)

    def _firing_analyzer(_root):
        return [{'type': 'scratch-zero-rule'}]

    monkeypatch.setattr(
        _zmr,
        '_build_fixture_corpus',
        lambda: {'scratch-zero-rule': FixtureSpec(analyzer=_firing_analyzer, files={})},
    )

    # Act
    findings = analyze_zero_match_rule(scratch_root)

    # Assert — the rule fired on its fixture, so it is NOT reported.
    assert findings == []


# ---------------------------------------------------------------------------
# (b) Registered rule WITHOUT a firing fixture → exactly one finding
# ---------------------------------------------------------------------------


def test_registered_rule_without_firing_fixture_produces_one_finding(tmp_path, monkeypatch):
    """A claimed-and-registered rule whose fixture never fires yields exactly one finding."""
    # Arrange — same scratch tree (registers 'scratch-zero-rule'), but the
    # corpus claims that rule with an analyzer that fires on NOTHING.
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)

    def _non_firing_analyzer(_root):
        return []

    monkeypatch.setattr(
        _zmr,
        '_build_fixture_corpus',
        lambda: {
            'scratch-zero-rule': FixtureSpec(analyzer=_non_firing_analyzer, files={})
        },
    )

    # Act
    findings = analyze_zero_match_rule(scratch_root)

    # Assert — exactly one zero-match-rule finding for the dead claimed rule.
    assert len(findings) == 1
    assert findings[0]['snippet'] == 'scratch-zero-rule'
    assert findings[0]['type'] == FINDING_TYPE


# ---------------------------------------------------------------------------
# (c) Finding dict shape matches the contract
# ---------------------------------------------------------------------------


def test_finding_dict_shape_matches_contract(tmp_path, monkeypatch):
    """The emitted finding carries exactly the documented keys and values."""
    # Arrange — a non-firing claimed-and-registered rule to force one finding.
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)
    monkeypatch.setattr(
        _zmr,
        '_build_fixture_corpus',
        lambda: {'scratch-zero-rule': FixtureSpec(analyzer=lambda _r: [], files={})},
    )

    # Act
    findings = analyze_zero_match_rule(scratch_root)

    # Assert — exact key set and the contract-fixed field values.
    assert len(findings) == 1
    finding = findings[0]
    assert set(finding.keys()) == {
        'rule_id',
        'type',
        'rule',
        'file',
        'line',
        'severity',
        'fixable',
        'snippet',
        'description',
    }
    assert finding['rule_id'] == RULE_ID
    assert finding['type'] == FINDING_TYPE
    assert finding['rule'] == RULE_NAME
    assert finding['line'] == 0
    assert finding['severity'] == 'warning'
    assert finding['fixable'] is False
    assert finding['snippet'] == 'scratch-zero-rule'
    assert isinstance(finding['description'], str) and finding['description']
    # The emitter path resolves to the scratch analyzer module that declares
    # the rule (best-effort _emitter_for_rule), not the empty string.
    assert finding['file'].endswith('_analyze_scratch_rule.py')


# ---------------------------------------------------------------------------
# (d) Real marketplace → zero findings (build-failing invariant)
# ---------------------------------------------------------------------------


def test_real_marketplace_produces_zero_zero_match_findings():
    """Every shipped corpus rule fires on its fixture — the real tree is clean.

    This is the build-failing invariant: if any rule claimed by the live
    FIXTURE_CORPUS stops firing (matcher rot), this assertion fails and the
    detector's quality-gate wiring blocks the merge.
    """
    # Arrange / Act — run the detector unmodified over the real marketplace.
    findings = analyze_zero_match_rule(MARKETPLACE_ROOT)

    # Assert — no zero-match-rule findings on a healthy tree.
    assert findings == [], (
        'zero-match-rule findings on the real marketplace — a claimed '
        f'FIXTURE_CORPUS rule fired on no fixture: '
        f'{[f["snippet"] for f in findings]}'
    )


def test_all_corpus_rules_are_registered_in_real_tree():
    """Every rule the live corpus claims is actually emitted by a real analyzer.

    Guards the second half of the candidate intersection: a claimed rule that
    is not registered would be silently skipped, hiding corpus rot. Pinning
    ``claimed ⊆ registered`` against the real tree keeps the corpus honest.
    """
    # Arrange
    claimed = set(_zmr._build_fixture_corpus().keys())
    registered = registered_rule_ids(MARKETPLACE_ROOT)

    # Act
    unregistered = claimed - registered

    # Assert
    assert not unregistered, (
        f'FIXTURE_CORPUS claims rules not registered by any analyzer: '
        f'{sorted(unregistered)}'
    )


# ---------------------------------------------------------------------------
# (e) Candidate-set semantics
# ---------------------------------------------------------------------------


def test_registered_rule_without_corpus_entry_is_silent(tmp_path, monkeypatch):
    """A registered rule with NO corpus entry is out of scope — no finding."""
    # Arrange — scratch tree registers 'scratch-zero-rule', but the corpus is
    # empty (the rule makes no positive-fixture claim).
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)
    monkeypatch.setattr(_zmr, '_build_fixture_corpus', dict)

    # Act
    findings = analyze_zero_match_rule(scratch_root)

    # Assert — the detector stays silent for uncovered registered rules.
    assert findings == []


def test_claimed_rule_not_registered_is_skipped(tmp_path, monkeypatch):
    """A corpus entry whose rule ID is not registered is skipped, not reported."""
    # Arrange — scratch tree registers only 'scratch-zero-rule', but the corpus
    # claims a DIFFERENT, unregistered rule with a non-firing analyzer. The
    # corpus cannot prove a rule the analyzers do not emit.
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)
    monkeypatch.setattr(
        _zmr,
        '_build_fixture_corpus',
        lambda: {'unregistered-rule': FixtureSpec(analyzer=lambda _r: [], files={})},
    )

    # Act
    findings = analyze_zero_match_rule(scratch_root)

    # Assert — the unregistered claimed rule is outside the candidate set.
    assert findings == []


# ---------------------------------------------------------------------------
# (f) Provenance cross-check — the new emitter row is present
# ---------------------------------------------------------------------------


def test_zero_match_rule_present_in_provenance_table():
    """The new ``zero-match-rule`` emitter has a row in rule-provenance.md.

    Mirrors the paired ``test_rule_provenance_table.py`` invariant (every
    emitted rule_id must have a provenance row) for the rule added by this
    deliverable, so the cross-check is explicit and deterministic here too.
    """
    # Arrange / Act
    content = PROVENANCE_PATH.read_text(encoding='utf-8')

    # Assert — the kebab rule ID appears verbatim somewhere in the table.
    assert 'zero-match-rule' in content, (
        'zero-match-rule must have a row in rule-provenance.md — the provenance '
        'audit (test_rule_provenance_table.py) requires every emitted rule_id '
        'to be documented.'
    )


# ---------------------------------------------------------------------------
# Sanity: registered_rule_ids extracts the scratch rule
# ---------------------------------------------------------------------------


def test_registered_rule_ids_extracts_scratch_rule(tmp_path):
    """The static rule-ID extractor finds the scratch analyzer's declared rule."""
    # Arrange
    scratch_root = _make_scratch_root(tmp_path, _SCRATCH_ANALYZER_SRC)

    # Act
    registered = registered_rule_ids(scratch_root)

    # Assert
    assert registered == {'scratch-zero-rule'}


def test_registered_rule_ids_empty_for_missing_scripts_dir(tmp_path):
    """A marketplace root with no plugin-doctor scripts dir registers nothing."""
    # Arrange — bare tmp dir, no scripts dir materialized.
    # Act
    registered = registered_rule_ids(tmp_path)

    # Assert
    assert registered == set()


# ---------------------------------------------------------------------------
# Sibling-cross-reference corpus entries (deliverable D3)
# ---------------------------------------------------------------------------
#
# The sibling-cross-reference rule (MARKDOWN_LINK_BARE_FILENAME) must carry a
# positive fixture in FIXTURE_CORPUS that actually fires. The real-tree invariant
# (test_real_marketplace_produces_zero_zero_match_findings) covers this
# implicitly; these tests pin it deterministically per-rule so a regression
# names exactly which rule stopped firing.


@pytest.mark.parametrize(
    'rule_id',
    ['MARKDOWN_LINK_BARE_FILENAME'],
)
def test_new_sibling_rule_present_in_corpus(rule_id):
    """Each new sibling-cross-reference rule has a FIXTURE_CORPUS entry."""
    # Arrange / Act
    corpus = _zmr._build_fixture_corpus()

    # Assert — the rule ID is a claimed corpus key with a positive fixture.
    assert rule_id in corpus, (
        f'{rule_id} must be registered in FIXTURE_CORPUS, got keys: {sorted(corpus)}'
    )
    spec = corpus[rule_id]
    assert spec.files, f'{rule_id} corpus entry must carry a non-empty positive fixture'


@pytest.mark.parametrize(
    'rule_id',
    ['MARKDOWN_LINK_BARE_FILENAME'],
)
def test_new_sibling_rule_fires_on_positive_fixture(rule_id):
    """Each new sibling-cross-reference rule fires on its positive fixture.

    Drives the corpus self-test (_fired_rule_ids materializes each spec's
    fixture under an isolated scratch tree and runs its analyzer); asserts the
    rule ID is in the fired set, proving its positive fixture produces findings.
    """
    # Arrange / Act — the union of rule IDs that fired across the live corpus.
    fired = _zmr._fired_rule_ids()

    # Assert — the new rule's matcher tripped on its known-defect fixture.
    assert rule_id in fired, (
        f'{rule_id} must fire on its positive fixture; fired set: {sorted(fired)}'
    )


def test_new_sibling_rule_in_candidate_intersection():
    """The new rule is claimed-and-registered (in the detector's candidate set).

    The detector's scope is ``corpus_rules ∩ registered_rules``; a claimed rule
    that is not registered is silently skipped, hiding a dead matcher. Pinning
    the new rule in the intersection guarantees the zero-match self-test
    actually evaluates it against the real tree.
    """
    # Arrange
    claimed = set(_zmr._build_fixture_corpus().keys())
    registered = registered_rule_ids(MARKETPLACE_ROOT)

    # Act
    candidates = claimed & registered

    # Assert
    assert 'MARKDOWN_LINK_BARE_FILENAME' in candidates, (
        'MARKDOWN_LINK_BARE_FILENAME must be both claimed and registered '
        f'(claimed={"MARKDOWN_LINK_BARE_FILENAME" in claimed}, '
        f'registered={"MARKDOWN_LINK_BARE_FILENAME" in registered})'
    )


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
