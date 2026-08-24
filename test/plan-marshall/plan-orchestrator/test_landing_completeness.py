#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the landing drain-completeness check (plan 302 D5).

The terminal ``kind: landing`` message must carry a machine-readable
``landing-facts`` block (plan 302 D4). ``check_landing_completeness`` is the
drain-side validator that lets the orchestrator turn "the queue is empty" into
"every REQUIRED fact drained": it reports whether a drained landing carried that
block with every required fact key SUPPLIED — non-empty, and not a degraded
value. Degraded values come in TWO classes, rejected on different terms: an
ANSWERED one (``n/a``) asserts a real end state and is rejected only at the keys
that cannot legitimately be absent, while a COULD-NOT-READ one (``unknown``)
asserts that nothing was observed and is rejected at EVERY key. It does NOT
reach the optional keys (the per-step typed facts, the wall-clock, the repository
end-state), so a ``complete: true`` landing may carry none of them and the check
never establishes that nothing whatsoever is outstanding.

The single most important assertion here is that the check is **SEEN to fail on
a known-incomplete input** — a PRE-FIX, prose-only landing (the historical
narrative shape) carries no ``landing-facts`` block, so the check reports it
incomplete. A completeness check that passed on a prose-only landing would be
the vacuous guard this check exists to replace, so that case is pinned
first and explicitly.

Covered:

- Pure ``check_landing_completeness`` / ``parse_landing_facts`` over the pre-fix
  prose landing (FAILS), a complete facts landing (PASSES), a wrong-schema block
  (fail-closed), and a missing-key block (names the gap).
- The CLI verb ``orchestrator inbox landing-check`` end-to-end: a written
  prose landing reports ``complete: false``, a written facts landing reports
  ``complete: true``.
- The payload-spec doc (D3) derives the delta and classifies the seven control
  findings, keeping the false-merge report NARRATIVE-ONLY.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_script_path, load_script_module, run_script

_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
check_landing_completeness = _inbox.check_landing_completeness
parse_landing_facts = _inbox.parse_landing_facts
LANDING_REQUIRED_KEYS = _inbox.LANDING_REQUIRED_KEYS
LANDING_FACTS_SCHEMA = _inbox.LANDING_FACTS_SCHEMA

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_PAYLOAD_SPEC: Path = _PLAN_MARSHALL / 'plan-orchestrator' / 'standards' / 'landing-payload-spec.md'

EPIC = 'completeness-epic'
SENDER = 'completeness-plan'

_FENCE = '```'

#: The PRE-FIX landing shape: the historical narrative body, with NO
#: ``landing-facts`` block. This is the known-incomplete input the check MUST
#: fail on — a prose-only landing transmits none of the mechanisable delta.
_PRE_FIX_PROSE_LANDING = (
    '## What landed\n\n'
    'The plan shipped as PR #123 and merged. Residue: watch the fourth token '
    'total, it was 3.4% off the others.\n'
)


#: A representative value per required fact key. This is a SAMPLE table, not a
#: second copy of the required-key list: :func:`_facts_block` iterates
#: ``LANDING_REQUIRED_KEYS`` and looks each key up here, so a key added to the
#: constant with no sample fails loudly instead of silently dropping out of every
#: "complete" fixture — which would leave the completeness assertions green while
#: exercising an incomplete block.
_SAMPLE_FACT_VALUES: dict[str, str] = {
    'schema': LANDING_FACTS_SCHEMA,
    'plan_id': 'truthful-signals-302',
    'pr': '#1234',
    'merge_state': 'merged',
    'deliverables_total': '6',
    'deliverables_done': '6',
    'total_tokens': '512000',
    'steps': 'push:done,create-pr:done,archive-plan:done',
}


def _facts_block(**overrides: str) -> str:
    """Build a complete ``landing-facts`` block, with optional key overrides.

    The default key set is ``LANDING_REQUIRED_KEYS`` itself — iterated, not
    transcribed — so a key added to the constant is present in every fixture
    automatically. An override of ``''`` drops a key's value (to exercise the
    missing-key branch) and an override to a non-``None`` value replaces it.
    """
    unmapped = [key for key in LANDING_REQUIRED_KEYS if key not in _SAMPLE_FACT_VALUES]
    assert not unmapped, (
        f'LANDING_REQUIRED_KEYS carries {unmapped}, for which _SAMPLE_FACT_VALUES has no '
        'sample. Add one — omitting it would silently build an INCOMPLETE block and every '
        'assertion that a complete landing passes would be exercising the wrong input.'
    )
    values = {key: _SAMPLE_FACT_VALUES[key] for key in LANDING_REQUIRED_KEYS}
    values.update(overrides)
    lines = '\n'.join(f'{key}={value}' for key, value in values.items())
    return f'{_FENCE}landing-facts\n{lines}\n{_FENCE}'


def _facts_landing(**overrides: str) -> str:
    return (
        '## What landed\n\ntruthful-signals-302 shipped as #1234 (merged).\n\n'
        f'{_facts_block(**overrides)}\n\n## Residue\n\nnone\n'
    )


# =============================================================================
# The check is SEEN to fail on the known-incomplete input (the D5 crux)
# =============================================================================


class TestSeenToFailOnPreFixLanding:
    def test_pre_fix_prose_landing_is_reported_incomplete(self):
        """The crux: a prose-only landing (no facts block) FAILS the check.

        This is what makes the guard non-vacuous — the exact known-incomplete
        input plan 302 exists to catch, pinned explicitly.
        """
        complete, missing = check_landing_completeness(_PRE_FIX_PROSE_LANDING)

        assert complete is False
        # No block at all -> every required key is reported missing.
        assert set(missing) == set(LANDING_REQUIRED_KEYS)

    def test_parse_returns_none_when_no_block_is_present(self):
        assert parse_landing_facts(_PRE_FIX_PROSE_LANDING) is None

    def test_complete_facts_landing_passes(self):
        complete, missing = check_landing_completeness(_facts_landing())

        assert complete is True
        assert missing == []

    def test_wrong_schema_is_fail_closed(self):
        landing = _facts_landing(schema='landing-facts/99')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['schema']

    def test_a_missing_required_key_is_named(self):
        landing = _facts_landing(total_tokens='')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['total_tokens']

    def test_required_key_set_is_the_shared_module_constant(self):
        # The producer (emit-landing) and this validator share ONE source.
        assert 'schema' in LANDING_REQUIRED_KEYS
        assert 'total_tokens' in LANDING_REQUIRED_KEYS
        assert 'steps' in LANDING_REQUIRED_KEYS


# =============================================================================
# A degraded value is MISSING, not a fact — across TWO classes
# =============================================================================
#
# A producer may write a degraded value in place of a fact, and every such value
# is a truthy string, so a presence-only check accepts a landing whose token
# total, step list and deliverable counts all failed to read and reports
# ``complete: true`` over it. Two classes are rejected on DIFFERENT terms, and
# the asymmetry between them is what these tests pin:
#
# - ANSWERED-degraded (``n/a``) asserts a real end state — "there is no such
#   thing" — so it is rejected only at the keys
#   ``LANDING_SENTINEL_REJECTING_KEYS`` names, and stays a legal answer at ``pr``
#   and ``merge_state``.
# - COULD-NOT-READ (``unknown``) asserts only that nothing was observed, so it is
#   rejected at EVERY key with no allow-list — ``pr`` and ``merge_state``
#   included.
#
# That is why the fix was to SPLIT the vocabulary rather than to add
# ``merge_state`` to the rejecting set: ``merge_state=n/a`` must stay an answer
# while ``merge_state=unknown`` must read as a gap, and one gated vocabulary
# cannot express both. The retained negative control
# (``test_degraded_pr_and_merge_state_stay_complete``) is the half that would
# have gone red under the widening, so it is what keeps the split honest.
#
# The expectations below are stated as EXACT literal key lists rather than
# derived from the module's sentinel vocabularies: deriving them would make both
# sides move together, so dropping a member from either set would leave every
# assertion green. The mutation pin at the end of the class proves that
# non-vacuity by execution rather than by assertion.


@contextmanager
def _without_could_not_read_sentinels():
    """Empty the COULD-NOT-READ vocabulary for the duration of the block.

    The mutation vehicle for the non-vacuity pin. It rebinds the MODULE
    attribute — not a local copy — because ``_is_unsupplied`` reads
    ``LANDING_COULD_NOT_READ_SENTINELS`` as a module global at call time, so a
    local rebinding would leave the predicate reading the shipped value and the
    pin would silently prove nothing. Restored in a ``finally`` so a failing
    assertion inside the block cannot leak the mutation into a later test.
    """
    original = _inbox.LANDING_COULD_NOT_READ_SENTINELS
    _inbox.LANDING_COULD_NOT_READ_SENTINELS = frozenset()
    try:
        yield
    finally:
        _inbox.LANDING_COULD_NOT_READ_SENTINELS = original


class TestDegradedSentinelFacts:
    def test_degraded_counts_tokens_and_steps_are_reported_missing(self):
        """A landing whose mechanisable facts all read ``n/a`` is INCOMPLETE.

        The four keys below can never legitimately be unknown for a landed plan,
        so a sanctioned degraded value for any of them is a gap the drain must
        record — not a fact it may reconcile against.
        """
        landing = _facts_landing(
            deliverables_total='n/a',
            deliverables_done='n/a',
            total_tokens='n/a',
            steps='n/a',
        )

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == [
            'deliverables_total',
            'deliverables_done',
            'total_tokens',
            'steps',
        ]

    def test_degraded_plan_id_is_reported_missing(self):
        """``plan_id`` identifies the landing; a degraded one is not an identity."""
        landing = _facts_landing(plan_id='n/a')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['plan_id']

    def test_degraded_pr_and_merge_state_stay_complete(self):
        """The asymmetry: ``pr`` / ``merge_state`` MAY be ``n/a``.

        "No PR exists" is a real end state the payload spec names, so a degraded
        value there is an answer rather than a gap. Pinning this alongside the
        rejection cases is what keeps the sentinel rule from being widened into a
        blanket ban.
        """
        landing = _facts_landing(pr='n/a', merge_state='n/a')

        complete, missing = check_landing_completeness(landing)

        assert complete is True
        assert missing == []

    def test_sentinel_match_ignores_case_and_surrounding_space(self):
        """A producer's ``N/A`` is the same sanctioned degraded value as ``n/a``."""
        landing = _facts_landing(total_tokens='  N/A  ')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['total_tokens']

    def test_a_genuine_zero_count_is_not_a_degraded_value(self):
        """``0`` is a real count, and must not be swept up by the sentinel rule."""
        landing = _facts_landing(deliverables_done='0')

        complete, missing = check_landing_completeness(landing)

        assert complete is True
        assert missing == []

    # -- COULD-NOT-READ class: positive controls -----------------------------

    def test_could_not_read_merge_state_is_reported_missing(self):
        """POSITIVE CONTROL: ``merge_state=unknown`` is a GAP, not a fact.

        The defect this split closes. ``merge_state`` is deliberately OUTSIDE
        ``LANDING_SENTINEL_REJECTING_KEYS`` — so that ``n/a`` stays an answer
        there — which meant the single-vocabulary check absorbed ``unknown`` as a
        settled merge fact. The payload spec defines ``unknown`` as "a PR whose
        state could not be read, and asserts only that nothing was observed", so
        reconciling against it would drain a failed read as a merge outcome.
        """
        landing = _facts_landing(merge_state='unknown')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['merge_state']

    def test_could_not_read_pr_is_reported_missing(self):
        """``pr`` is the other key outside the rejecting set — same rule applies."""
        landing = _facts_landing(pr='unknown')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['pr']

    def test_could_not_read_at_a_rejecting_set_key_is_reported_missing(self):
        """The class also rejects at a key the ANSWERED gate already covers.

        ``total_tokens`` is in ``LANDING_SENTINEL_REJECTING_KEYS``, so both
        classes are unsupplied there. Pinning it proves the could-not-read rule
        is unconditional rather than an else-branch that only fires at the two
        keys the gate omits.
        """
        landing = _facts_landing(total_tokens='unknown')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['total_tokens']

    def test_could_not_read_match_ignores_case_and_surrounding_space(self):
        """A producer's ``  UNKNOWN  `` is the same could-not-read value.

        Mirrors ``test_sentinel_match_ignores_case_and_surrounding_space`` for
        the ANSWERED class, so both vocabularies are pinned to the same
        strip-then-casefold normalisation.
        """
        landing = _facts_landing(merge_state='  UNKNOWN  ')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['merge_state']

    def test_a_value_merely_containing_unknown_is_not_swept_up(self):
        """The comparison is EXACT after normalisation, never a substring test.

        A real value that happens to contain the sentinel's letters is a fact.
        Checked at a key outside the rejecting set AND at one inside it, so the
        exactness holds on both branches of the predicate rather than only on the
        one a single sample would have exercised.
        """
        landing = _facts_landing(
            merge_state='unknown_at_dequeue', deliverables_done='3 unknown-to-spec'
        )

        complete, missing = check_landing_completeness(landing)

        assert complete is True
        assert missing == []

    # -- The mutation pin ----------------------------------------------------

    def test_mutation_pin_dropping_unknown_turns_the_positive_control_red(self):
        """The positive controls pass BECAUSE ``unknown`` is in the vocabulary.

        A guard that would pass no matter what the module declared proves
        nothing. This drops ``unknown`` from the could-not-read vocabulary and
        observes the SAME input flip to complete — so the assertions above are
        load-bearing — then confirms the restore. The mutation is applied to the
        module attribute rather than to a local copy because
        ``_is_unsupplied`` reads the module global at call time.
        """
        landing = _facts_landing(merge_state='unknown')

        # Baseline: the positive control holds against the shipped vocabulary.
        assert check_landing_completeness(landing) == (False, ['merge_state'])

        # Mutation: with the vocabulary emptied, the same landing reads complete.
        with _without_could_not_read_sentinels():
            assert check_landing_completeness(landing) == (True, [])

        # Restored: the mutation was scoped, not permanent.
        assert check_landing_completeness(landing) == (False, ['merge_state'])


# =============================================================================
# The two DOCUMENTED enumerations agree with the constant
# =============================================================================
#
# ``LANDING_REQUIRED_KEYS`` is restated twice in prose: the payload spec's
# required-key table, and the producer's Step 2 enumeration. Nothing derived
# either from the constant, so a key added to or removed from the constant left
# both documents describing a payload shape the validator no longer enforces —
# and a producer following the stale enumeration emits a landing the drain
# rejects. Both parsers extract the documented set and assert EQUALITY, so a
# divergence in either direction fails.

_EMIT_LANDING_DOC: Path = _PLAN_MARSHALL / 'phase-6-finalize' / 'standards' / 'emit-landing.md'

#: A backticked code span. Used to pull key names out of a prose enumeration.
_CODE_SPAN = re.compile(r'`([^`]+)`')

#: A fact KEY as written in either enumeration: lowercase words and underscores,
#: optionally followed by ``=`` and a sample value (the spec writes the schema
#: marker as ``schema=landing-facts/1``). A fence info-string
#: (``landing-facts``) and a placeholder (``{step}:{outcome}``) carry characters
#: outside the class and are excluded by construction.
_FACT_KEY = re.compile(r'^([a-z][a-z0-9_]*)(?:=.*)?$')

#: The degraded-value tokens the producer prose writes in code spans. A sentinel
#: is a VALUE, never a fact key, but ``unknown`` is spelled exactly like one —
#: lowercase letters and nothing else — so ``_FACT_KEY`` cannot tell the two
#: apart and would harvest it as a ninth required key, failing the equality below
#: against prose that is entirely correct. The sibling sentinel ``n/a`` is kept
#: out by ``_FACT_KEY`` alone, but only by the accident of its slash: resting a
#: key set on a token's punctuation is what let this through, so both
#: vocabularies are excluded explicitly.
#:
#: Derived from the module's own vocabularies rather than transcribed, so a token
#: added to either is excluded here without a second edit. The derivation cannot
#: mask a divergence: excluding a token that IS a required key would drop it from
#: the extracted set and turn the equality RED, never green.
#:
#: Only a BARE sentinel is dropped. A key-qualified span (``merge_state=unknown``)
#: still yields ``merge_state``, because such a span names a key whatever its
#: sample value is.
_SENTINEL_TOKENS = frozenset(
    token.casefold()
    for token in (_inbox.LANDING_ANSWERED_SENTINELS | _inbox.LANDING_COULD_NOT_READ_SENTINELS)
)


def _keys_from_code_spans(text: str) -> set[str]:
    """Every fact key named by a backticked code span in ``text``."""
    keys = set()
    for span in _CODE_SPAN.findall(text):
        match = _FACT_KEY.match(span.strip())
        if match and match.group(1).casefold() not in _SENTINEL_TOKENS:
            keys.add(match.group(1))
    return keys


def _spec_table_keys() -> set[str]:
    """The `Key` column of the payload spec's required-fact-keys table.

    The section is located by its heading and bounded by the next heading, so a
    table added elsewhere in the document is not folded in.
    """
    text = _PAYLOAD_SPEC.read_text(encoding='utf-8')
    section = re.search(
        r'^## Required machine-readable fact keys$(.*?)(?=^## |\Z)',
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert section, (
        f'{_PAYLOAD_SPEC.name} carries no "## Required machine-readable fact keys" '
        'section, so this guard would read an empty table.'
    )
    keys = set()
    for row in re.finditer(r'^\|\s*`([^`]+)`\s*\|', section.group(1), re.MULTILINE):
        keys.add(row.group(1).strip())
    return keys


def _emit_landing_enumeration_keys() -> set[str]:
    """The required keys enumerated in emit-landing.md's Step 2 body part 2.

    The enumeration is truncated at ``Optional keys``, which introduces the keys a
    landing MAY carry: folding those in would make the set a superset of the
    required one and the equality assertion could never hold.
    """
    text = _EMIT_LANDING_DOC.read_text(encoding='utf-8')
    item = re.search(r'^2\. \*\*The required.*$', text, re.MULTILINE)
    assert item, (
        f'{_EMIT_LANDING_DOC.name} carries no Step 2 "The required `landing-facts` fenced '
        'block" enumeration item, so this guard would read nothing.'
    )
    body = item.group(0)
    optional_at = body.find('Optional keys')
    assert optional_at != -1, (
        'The Step 2 enumeration no longer names "Optional keys", so the truncation that '
        'separates required from optional has nothing to cut at and the extracted set '
        'would silently include the optional keys.'
    )
    return _keys_from_code_spans(body[:optional_at])


class TestDocumentedEnumerationsMatchTheConstant:
    def test_the_extractors_are_not_vacuous(self):
        """Both parsers must find something, or the equalities below prove nothing."""
        assert _spec_table_keys(), 'the payload-spec table parser extracted no keys'
        assert _emit_landing_enumeration_keys(), (
            'the emit-landing Step 2 enumeration parser extracted no keys'
        )

    def test_a_bare_sentinel_is_not_harvested_as_a_fact_key(self):
        """A degraded VALUE in a code span is not a fact key.

        ``unknown`` is spelled exactly like a key — lowercase letters, nothing
        else — so without an explicit exclusion the producer prose that NAMES the
        token to state the could-not-read rule contributes a ninth "required key"
        and the equality below fails against text that is entirely correct.

        The key-qualified spelling is pinned in the same breath: dropping a BARE
        sentinel must not also drop the key a ``key=value`` span names, or a
        future enumeration written ``merge_state=unknown`` would lose a real key
        and the equality would fail in the other direction.
        """
        assert _SENTINEL_TOKENS, (
            'the sentinel vocabularies are empty, so the loop below asserts nothing'
        )
        assert any(_FACT_KEY.match(token) for token in _SENTINEL_TOKENS), (
            'no sentinel is spelled like a fact key any more, so `_FACT_KEY` already rejects '
            'every token and the membership test in `_keys_from_code_spans` is never reached: '
            'this test would stay green with `_SENTINEL_TOKENS` doing nothing.'
        )
        for token in sorted(_SENTINEL_TOKENS):
            assert _keys_from_code_spans(f'written `{token}`') == set(), token
            assert _keys_from_code_spans(f'written `merge_state={token}`') == {'merge_state'}, (
                token
            )

    def test_payload_spec_table_names_exactly_the_required_keys(self):
        assert _spec_table_keys() == set(LANDING_REQUIRED_KEYS), (
            'The payload spec\'s "Required machine-readable fact keys" table and '
            '`LANDING_REQUIRED_KEYS` disagree. A key in the table but not the constant is '
            'documented as required and enforced by nothing; a key in the constant but not '
            'the table is enforced by the drain and documented nowhere, so a producer '
            f'following the spec emits a landing the drain rejects. Table: '
            f'{sorted(_spec_table_keys())}; constant: {sorted(LANDING_REQUIRED_KEYS)}.'
        )

    def test_emit_landing_enumeration_names_exactly_the_required_keys(self):
        assert _emit_landing_enumeration_keys() == set(LANDING_REQUIRED_KEYS), (
            "emit-landing.md's Step 2 enumeration and `LANDING_REQUIRED_KEYS` disagree. "
            'The enumeration is what the PRODUCER follows, so a key it omits is one the '
            'emitted landing will not carry and the drain will reject. Enumeration: '
            f'{sorted(_emit_landing_enumeration_keys())}; constant: '
            f'{sorted(LANDING_REQUIRED_KEYS)}.'
        )

    def test_the_two_documents_agree_with_each_other(self):
        """Transitively implied by the two equalities, asserted for a direct message."""
        assert _spec_table_keys() == _emit_landing_enumeration_keys()


# =============================================================================
# The PRODUCER routes each CONDITION to the token the consumer expects
# =============================================================================
#
# ``_is_unsupplied`` splits the degraded vocabulary by TOKEN. The two producer
# documents are what decide which CONDITION reaches which token, and the split
# is worth nothing unless the two halves agree:
#
#   observed absence ("there is no such thing" — no PR was ever created, the
#                     step legitimately did not run)   -> ``n/a``
#   failed read      ("this could not be read")        -> ``unknown``
#
# Routing a FAILED READ to ``n/a`` is invisible to every consumer-side test in
# this file. ``merge_state`` sits OUTSIDE ``LANDING_SENTINEL_REJECTING_KEYS`` by
# design — ``test_degraded_pr_and_merge_state_stay_complete`` pins that, and it
# MUST stay green — so a producer that degrades an UNREADABLE merge state to
# ``n/a`` drains as ``complete: true``: a settled "no PR exists" for a fact
# nobody read. The consumer is correct there; only the producer instructions
# were wrong, which is why widening the rejecting set is the wrong remedy and
# only a doc-contract guard can see this half of the defect.
#
# The scan is UNIT-based, never whole-document: both documents legitimately
# CONTRAST the two tokens in one breath ("it never inherits the exemption
# ``n/a`` gets at those two"), so the rejected shape is narrower than
# co-occurrence — a failed-read CONDITION in the same unit as an instruction to
# WRITE ``n/a``, with no mention of ``unknown`` carrying the contrast.

_PRODUCER_DOCS: dict[str, Path] = {
    'emit-landing.md': _EMIT_LANDING_DOC,
    'landing-payload-spec.md': _PAYLOAD_SPEC,
}

#: Phrasings that name the FAILED-READ condition — a value the producer tried to
#: obtain and could not. Deliberately does NOT cover "its step did not run",
#: which is an OBSERVED ABSENCE and whose ``n/a`` routing is correct.
_FAILED_READ_CONDITION = re.compile(
    '|'.join((
        r'could not (?:be )?read',
        r'a read that fail\w*',
        r'a read genuinely fail\w*',
        r'a failed read',
        r'returns an error',
    )),
    re.IGNORECASE,
)

#: An instruction to WRITE the ANSWERED token. Requires a write/degrade verb
#: within one unbroken run of a unit ahead of the literal ``n/a`` code span, so
#: prose that merely NAMES the token ("the exemption `n/a` gets at those two")
#: is not read as an instruction to write it.
#:
#: The leading negation guard carries the NEGATION half: an instruction and a
#: PROHIBITION are otherwise indistinguishable to this pattern, so "Never write
#: `n/a` for a value that could not be read" — a CORRECT sentence that the
#: producer docs state verbatim — would be reported as the very defect it
#: forbids. Relying on such a sentence also naming ``unknown`` to earn the
#: contrast exemption is an accident, not negation handling: consolidating that
#: trailing clause away would turn the build red against correct prose.
#:
#: The negator is recognised wherever it GOVERNS the write verb, not only where
#: it abuts it. The match is anchored at the unit start and refuses to advance
#: over a negator that reaches the verb, so "must not be written as `n/a`" and
#: "Do not ever write `n/a`" are read as prohibitions too — an adjacency-only
#: guard would be the same accident of phrasing this comment rejects above.
#: Only AUXILIARIES may sit in the gap, which is what keeps the widening from
#: swallowing the offenders: the failed-read condition itself contains "could
#: not be read", and there the gap holds an ordinary verb, so that negator does
#: not reach the write verb and "…could not be read is written as `n/a`" stays
#: flagged. Every guard is a lookAHEAD, so no width restriction applies.
_WRITE_THE_ANSWERED_TOKEN = re.compile(
    r'^(?:(?!\b(?:not|never|cannot)\b'
    r'(?:\s+(?:be|been|being|ever|to|then|also|again|yet))*'
    r'\s+(?:writ|degrad|sanction))[\s\S])*?'
    r'(?:writ|degrad|sanction)\w*[^.`]{0,60}`n/a`',
    re.IGNORECASE,
)

#: The COULD-NOT-READ token, in any spelling a document may use for it — bare,
#: or qualified as ``merge_state=unknown``. Its presence in a unit is what marks
#: that unit as CONTRASTING the two tokens rather than mis-routing a condition.
_COULD_NOT_READ_TOKEN = re.compile(r'unknown', re.IGNORECASE)


def _prose_units(text: str) -> list[str]:
    """Split a producer document into the units the routing rule is judged over.

    A unit is one sentence of prose or one table row. Blocks are separated by
    blank lines first so a sentence can never run across a section boundary, and
    a block whose every line is a table row contributes one unit per row — the
    Error Handling table states its CONDITION and its ACTION in two cells of the
    same row, so splitting a row on its pipes would separate exactly the pair
    this guard exists to catch.

    For the same reason the sentence split refuses to cut at ``e.g.``, ``i.e.``
    and ``cf.``: an abbreviation's period is not a sentence end, and cutting
    there can strand a failed-read CONDITION in one unit and its write-``n/a``
    ACTION in the next, letting a genuine offender through unseen.
    """
    units: list[str] = []
    for block in re.split(r'\n\s*\n', text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.startswith('|') for line in lines):
            units.extend(lines)
            continue
        joined = re.sub(r'\s+', ' ', ' '.join(lines))
        split_at = r'(?<=[.!?])(?<!e\.g\.)(?<!i\.e\.)(?<!cf\.) '
        units.extend(part for part in re.split(split_at, joined) if part.strip())
    return units


def _answered_class_definition() -> str:
    """The payload spec's paragraph DEFINING the answered-degraded class.

    Located by its opening sentence and bounded by the next blank line, so the
    could-not-read paragraph that follows it is not folded in — the two
    paragraphs define the two classes and the guard is about the first one only.
    """
    text = _PAYLOAD_SPEC.read_text(encoding='utf-8')
    match = re.search(
        r'^The \*\*answered-degraded\*\* class is `n/a`\..*?(?=\n\s*\n|\Z)',
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match, (
        f'{_PAYLOAD_SPEC.name} carries no paragraph opening "The **answered-degraded** class '
        'is `n/a`.", so this guard would read nothing. Keep that opening sentence verbatim: '
        'it is the anchor for the definition the guard checks.'
    )
    return match.group(0)


class TestProducerRoutesConditionsToTokens:
    def test_the_scan_population_is_non_empty(self):
        """Both parsers must find units, or every assertion below is vacuous."""
        for name, path in _PRODUCER_DOCS.items():
            units = _prose_units(path.read_text(encoding='utf-8'))
            assert len(units) > 20, f'{name}: the unit splitter extracted {len(units)} units'
        assert _answered_class_definition().strip(), (
            'the answered-class definition extractor returned an empty paragraph'
        )

    def test_no_producer_unit_writes_the_answered_token_for_a_failed_read(self):
        """A failed read is NEVER written as ``n/a`` — the headline defect.

        ``n/a`` says "there is no such thing"; a read that failed observed
        nothing at all and has no business claiming an end state. At ``pr`` and
        ``merge_state`` — the two keys the answered class is exempt at — that
        mis-routing is what turns an unread merge state into a settled landing.
        """
        offenders: list[str] = []
        for name, path in _PRODUCER_DOCS.items():
            for unit in _prose_units(path.read_text(encoding='utf-8')):
                if not _FAILED_READ_CONDITION.search(unit):
                    continue
                if not _WRITE_THE_ANSWERED_TOKEN.search(unit):
                    continue
                if _COULD_NOT_READ_TOKEN.search(unit):
                    # The unit contrasts the two tokens rather than routing to one.
                    continue
                offenders.append(f'{name}: {unit}')

        assert not offenders, (
            'A producer document instructs the emitter to write `n/a` for a value it could '
            'not READ. `n/a` is the ANSWERED token ("there is no such thing") and is exempt '
            'at `pr` and `merge_state`, so a failed read routed there drains as a settled '
            'fact — the false-completeness class this check exists to close. Route the '
            'failed-read condition to `unknown` instead, which is a gap at every key. '
            f'Offending units: {offenders}'
        )

    def test_the_answered_class_definition_is_not_a_failed_read(self):
        """The spec must not DEFINE the answered class by a could-not-read condition.

        The other half of the same defect, and the half that made a one-sided
        repair of ``emit-landing.md`` inconsistent with its own contract: a
        definition reading "`emit-landing.md` sanctions writing it for a field
        the producer could not read" hands the failed-read condition to the
        answered token in the document that WINS when the three sites disagree.
        """
        definition = _answered_class_definition()
        found = _FAILED_READ_CONDITION.findall(definition)

        assert not found, (
            f'{_PAYLOAD_SPEC.name} defines the answered-degraded class (`n/a`) in terms of a '
            'read that FAILED. That condition belongs to the could-not-read class '
            '(`unknown`); `n/a` is for an absence the run observed. Because this document '
            'wins when producer, validator and drain disagree, the definition here is what a '
            f'one-sided fix of emit-landing.md would contradict. Matched: {found}'
        )

    def test_both_producer_docs_route_a_failed_read_to_the_could_not_read_token(self):
        """Positive control: each document STATES the failed-read routing.

        The rejection test above would also pass on a document that simply never
        mentions a failed read. This one requires the routing to be present, so
        the pair cannot be satisfied by deleting the subject.
        """
        for name, path in _PRODUCER_DOCS.items():
            conditions = [
                unit
                for unit in _prose_units(path.read_text(encoding='utf-8'))
                if _FAILED_READ_CONDITION.search(unit)
            ]
            assert conditions, (
                f'{name} names no failed-read condition anywhere, so the rejection guard '
                'above passes vacuously over it.'
            )
            routed = [unit for unit in conditions if _COULD_NOT_READ_TOKEN.search(unit)]
            assert routed, (
                f'{name} names a failed-read condition in {len(conditions)} unit(s) and '
                'routes it to `unknown` in none of them. The producer instructions must say '
                'which token a failed read is written as, or the emitter is left to guess.'
            )

    # -- The mutation pin ----------------------------------------------------

    def test_mutation_pin_the_scan_flags_every_pre_fix_sentence(self):
        """The guards above pass BECAUSE the documents were changed.

        A doc-contract guard that would pass over the defective text proves
        nothing, and observing it fail once before the edit leaves no executable
        record. So the four PRE-FIX units are carried here verbatim and fed to
        the same predicate: each MUST be flagged. Paired with the sanctioned
        units below — which MUST NOT be — this pins both directions in one run,
        permanently, instead of relying on a red observation nobody can repeat.
        """
        pre_fix_units = (
            # emit-landing.md § Step 1 — the read-failure routing sentence.
            'A read that fails degrades its field to `n/a` (Error Handling), never the '
            'whole message.',
            # emit-landing.md § Step 2 — the fenced-block enumeration.
            'A value that could not be read is written as `n/a` (its key still present).',
            # emit-landing.md § Step 2 — the follow-up that sanctioned it.
            'Writing `n/a` there is still the correct thing to do when a read genuinely '
            'failed (it never blocks the emission), but it is recorded as a gap rather '
            'than absorbed as a value.',
            # emit-landing.md § Error Handling — condition and action, one row.
            '| A fact read (`manage-status`) returns an error | Write that field as `n/a` '
            'in the fenced block (key still present) and continue |',
        )

        for unit in pre_fix_units:
            flagged = bool(
                _FAILED_READ_CONDITION.search(unit)
                and _WRITE_THE_ANSWERED_TOKEN.search(unit)
                and not _COULD_NOT_READ_TOKEN.search(unit)
            )
            assert flagged, f'the scan does not flag the pre-fix unit: {unit}'

    def test_mutation_pin_the_scan_leaves_the_sanctioned_units_alone(self):
        """The matched negative control: correct prose must survive the scan.

        Both shapes below are legitimate and both are within a hair of the
        rejected one — an OBSERVED-ABSENCE routing to `n/a`, and a sentence that
        names both tokens to CONTRAST them. A predicate that swept these up
        would force the documents to stop saying true things, so they are pinned
        as explicitly as the violations are.
        """
        sanctioned_units = (
            # Observed absence — the step did not run — correctly routed to `n/a`.
            'A fact absent because its step did not run (the manifest excluded it, or it '
            'has no record) is written as `n/a`, its key still present, per the Error '
            'Handling table.',
            # A contrast between the two tokens, not a routing of either.
            'A value asserting only that a state could not be READ — written '
            '`merge_state=unknown` — is a gap at EVERY required key, so it never inherits '
            'the exemption `n/a` gets at those two.',
        )

        for unit in sanctioned_units:
            flagged = bool(
                _FAILED_READ_CONDITION.search(unit)
                and _WRITE_THE_ANSWERED_TOKEN.search(unit)
                and not _COULD_NOT_READ_TOKEN.search(unit)
            )
            assert not flagged, f'the scan wrongly flags a sanctioned unit: {unit}'

    def test_a_prohibition_is_not_read_as_an_instruction(self):
        """A PROHIBITION of the defect must not be flagged AS the defect.

        The producer docs state this rule verbatim. It carries a failed-read
        condition and the literal ``n/a``, so only the write-verb's negation
        separates it from a real offender. The control deliberately OMITS the
        trailing clause naming ``unknown``: with that clause present the sentence
        earns the contrast exemption and survives for a reason unrelated to
        negation, which would let this control pass over an unfixed predicate.
        """
        prohibition = 'Never write `n/a` for a value that could not be read.'

        flagged = bool(
            _FAILED_READ_CONDITION.search(prohibition)
            and _WRITE_THE_ANSWERED_TOKEN.search(prohibition)
            and not _COULD_NOT_READ_TOKEN.search(prohibition)
        )
        assert not flagged, (
            'the scan reads a PROHIBITION of the defect as an INSTRUCTION to commit it: '
            f'{prohibition}'
        )

    def test_an_abbreviation_does_not_split_a_condition_from_its_action(self):
        """An offender must not escape by carrying an abbreviation mid-sentence.

        Condition-and-action co-location inside ONE unit is this guard's entire
        mechanism, so any split that separates the pair is an escape hatch. An
        abbreviation's period is not a sentence end; cutting there would leave
        the failed-read condition in one unit and the write-``n/a`` action in the
        next, and the offender predicate would match neither half.
        """
        offender = 'A read that fails, i.e. the source errored, is written as `n/a`.'

        units = _prose_units(offender)
        flagged = any(
            _FAILED_READ_CONDITION.search(unit)
            and _WRITE_THE_ANSWERED_TOKEN.search(unit)
            and not _COULD_NOT_READ_TOKEN.search(unit)
            for unit in units
        )
        assert flagged, (
            'the sentence splitter cut at an abbreviation and separated the failed-read '
            f'CONDITION from its write-`n/a` ACTION, so the offender escaped. Units: {units}'
        )


# =============================================================================
# The CLI verb transports the verdict end-to-end
# =============================================================================


def _env(plan_context) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}


def _scaffold(plan_context):
    return run_script(SCRIPT_PATH, 'scaffold', '--slug', EPIC, env_overrides=_env(plan_context))


def _write_landing(plan_context, tmp_path: Path, body: str, name: str) -> str:
    payload = tmp_path / name
    payload.write_text(body, encoding='utf-8')
    run_script(
        SCRIPT_PATH,
        'inbox', 'write',
        '--slug', EPIC,
        '--sender-type', 'plan',
        '--sender-id', SENDER,
        '--kind', 'landing',
        '--payload-file', str(payload),
        env_overrides=_env(plan_context),
    )
    return f'{SENDER}-001.md'


def _landing_check(plan_context, message: str):
    return run_script(
        SCRIPT_PATH,
        'inbox', 'landing-check',
        '--slug', EPIC,
        '--message', message,
        env_overrides=_env(plan_context),
    )


class TestLandingCheckCli:
    def test_prose_landing_reports_incomplete_end_to_end(self, plan_context, tmp_path):
        _scaffold(plan_context)
        message = _write_landing(plan_context, tmp_path, _PRE_FIX_PROSE_LANDING, 'prose.md')

        result = _landing_check(plan_context, message)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'complete: false' in result.stdout

    def test_facts_landing_reports_complete_end_to_end(self, plan_context, tmp_path):
        _scaffold(plan_context)
        message = _write_landing(plan_context, tmp_path, _facts_landing(), 'facts.md')

        result = _landing_check(plan_context, message)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'complete: true' in result.stdout

    def test_missing_message_is_file_not_found(self, plan_context):
        _scaffold(plan_context)

        result = _landing_check(plan_context, f'{SENDER}-404.md')

        assert 'error: file_not_found' in result.stdout


# =============================================================================
# The payload spec (D3) derives the delta and classifies the seven findings
# =============================================================================


class TestPayloadSpecDoc:
    def _text(self) -> str:
        return _PAYLOAD_SPEC.read_text(encoding='utf-8')

    def test_spec_exists_and_names_both_classes(self):
        text = self._text()

        assert 'MECHANISABLE' in text
        assert 'NARRATIVE-ONLY' in text

    def test_spec_carries_the_seven_findings_control(self):
        text = self._text()

        # The seven known report-only findings are the non-empty control.
        for anchor in (
            'fourth token total',
            'housekeeping',
            'RUNTIME step order',
            'merged: true',
            'three-way disagreement',
            'split guard',
            'review-bot withdrawal',
        ):
            assert anchor in text, anchor

    def test_false_merge_is_classified_narrative_only(self):
        """The control item the plan flags as 'may not be mechanisable at all'."""
        text = self._text()
        # The false-merge row must NOT force the report into a fact.
        assert 'arrived as operator narrative, not as a step fact' in text

    def test_spec_states_the_empirical_sample_was_not_taken(self):
        text = self._text()

        assert 'The empirical sample was not' in text
