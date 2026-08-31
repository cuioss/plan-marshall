#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The review-match predicate is stated by the producer and nowhere contradicted.

The failure this pins is not a wrong line — it is a doc left BEHIND. The
head-SHA match predicate was widened from whole-field string equality to
``_references_head_sha`` (the SHA recognised as a bare token or embedded in a
commit URL, compared for equality either way). The code changed; three separate
documents stated the OLD predicate, and the diff touched none of those lines, so
six review rounds read them as untouched context rather than as a contract that
had just been refuted. The predicate whose false verdict BLOCKS A MERGE was
documented pre-fix in every consumer that reads it.

Two guards, both derived rather than asserted:

(a) **The producer names the predicate it actually calls.** The name is pulled by
    AST out of ``_match_review`` — specifically the module-level helper that
    ``_match_review`` hands ``head_sha`` to — and the producer doc must name that
    symbol. Replace or rename the predicate without re-reading the doc and this
    fails, because the derivation follows the code and the doc does not.

(b) **No document states the retired equality predicate.** The population is the
    set of bundle documents that mention ``head_sha_verified``, DERIVED by
    scanning the tree, never enumerated here — the finding round named three docs
    and the derived population is larger, which is the whole reason it is derived.
    Membership of the three known consumers is asserted so an empty or misrooted
    scan fails loudly instead of passing vacuously.

⛔ **What (b) does NOT do.** It recognises the retired predicate by its PHRASING,
so a restatement worded differently escapes it. It is a recurrence guard for this
specific refuted claim, not a proof that no doc contradicts the code. The
structural remedy is the one applied to the consumer docs themselves: cross-
reference the producer's signal table rather than restate the predicate, so there
is one statement site to keep true instead of three.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_re_review.py')
#: scripts/ -> workflow-integration-github/ -> skills/ -> plan-marshall/ -> bundles/
_BUNDLES = SCRIPT_PATH.parents[4]

_PRODUCER_DOC = SCRIPT_PATH.parents[1] / 'SKILL.md'
_AR_SKILL = _BUNDLES / 'plan-marshall' / 'skills' / 'automatic-review' / 'SKILL.md'
_BRANCH_CLEANUP_REREVIEW = (
    _BUNDLES
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'branch-cleanup-rereview.md'
)

#: The envelope field whose contract the predicate decides. A document that talks
#: about this field is a document that can state the predicate wrongly.
_FIELD = 'head_sha_verified'

#: The retired claim: the reviewed-commit field EQUALS the head SHA. Deliberately
#: keyed on the word ``equals`` and not on ``equality`` — the shipped wording says
#: the extracted token is "compared for equality", which is correct and must not
#: trip this. Likewise not keyed on ``==``, which the docs legitimately use for the
#: unrelated "has HEAD advanced past the reviewed commit" test.
_RETIRED_EQUALITY_RE = re.compile(
    r'(?is)('
    r'reviewed[\s\-]*commit[^.\n]{0,60}\bequals\b'
    r'|\bSHA\b[^.\n]{0,30}\bequals\b'
    r'|\bequals\b[^.\n]{0,30}head[\s\-_]*sha'
    r')'
)


def _states_retired_equality(text: str) -> bool:
    """Return True when ``text`` asserts whole-field SHA equality as the predicate."""
    return _RETIRED_EQUALITY_RE.search(text) is not None


def _doc_population() -> list[Path]:
    """Every bundle document that discusses the ``head_sha_verified`` contract."""
    found = []
    for path in _BUNDLES.rglob('*.md'):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if _FIELD in text:
            found.append(path)
    return sorted(found)


def _head_sha_predicate_name() -> str:
    """Derive, by AST, the helper ``_match_review`` hands ``head_sha`` to."""
    tree = ast.parse(SCRIPT_PATH.read_text(encoding='utf-8'))
    module_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    matcher = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == '_match_review'
        ),
        None,
    )
    assert matcher is not None, '_match_review not found — the derivation anchor moved'

    candidates = {
        call.func.id
        for call in ast.walk(matcher)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id in module_functions
        and any(isinstance(arg, ast.Name) and arg.id == 'head_sha' for arg in call.args)
    }
    assert len(candidates) == 1, (
        f'expected exactly one head_sha predicate in _match_review, derived {sorted(candidates)}'
    )
    return candidates.pop()


class TestProducerDocNamesThePredicateItCalls:
    """(a) The producer doc names the symbol the code actually decides with."""

    def test_predicate_is_derivable_from_the_matcher(self):
        assert _head_sha_predicate_name() == '_references_head_sha'

    def test_producer_doc_names_the_derived_predicate(self):
        predicate = _head_sha_predicate_name()
        text = _PRODUCER_DOC.read_text(encoding='utf-8')

        assert predicate in text, (
            f'{_PRODUCER_DOC.name} does not name {predicate}, the predicate '
            f'_match_review calls — the producer contract and the code have diverged'
        )

    def test_a_doc_missing_the_predicate_name_is_rejected(self):
        """Planted divergence: the check must fail on a doc that omits the name."""
        predicate = _head_sha_predicate_name()
        planted = 'A signal table that never names the predicate it documents.'

        assert predicate not in planted


class TestNoDocStatesTheRetiredEqualityPredicate:
    """(b) The derived doc population never asserts whole-field SHA equality."""

    def test_population_is_non_empty_and_contains_the_known_consumers(self):
        population = _doc_population()

        assert population, (
            f'derived ZERO documents mentioning {_FIELD} under {_BUNDLES} — the scan '
            f'is misrooted, so a clean result here would be vacuous'
        )
        for known in (_PRODUCER_DOC, _AR_SKILL, _BRANCH_CLEANUP_REREVIEW):
            assert known in population, f'{known} missing from the derived population'

    def test_no_population_member_states_the_retired_predicate(self):
        population = _doc_population()
        offenders = [
            str(path.relative_to(_BUNDLES))
            for path in population
            if _states_retired_equality(path.read_text(encoding='utf-8'))
        ]

        assert not offenders, (
            f'{len(offenders)} of {len(population)} documents state the retired '
            f'whole-field SHA-equality predicate: {offenders}. The shipped predicate '
            f'RECOGNISES the SHA as a bare token or inside a commit URL; cross-'
            f'reference the producer signal table instead of restating it.'
        )

    @pytest.mark.parametrize(
        'planted',
        [
            'a review whose reviewed commit SHA equals `--head-sha`',
            'a review whose reviewed-commit SHA equals `{head_sha}`',
            'matches when the SHA equals the awaited value',
            'the field equals head_sha exactly',
        ],
    )
    def test_planted_divergence_is_detected(self, planted):
        """Positive control — each retired phrasing must trip the detector."""
        assert _states_retired_equality(planted)

    @pytest.mark.parametrize(
        'shipped',
        [
            'reviewed-commit evidence references `--head-sha`',
            'the SHA is extracted and compared for equality either way',
            'Matching the whole field for string equality would recognise only the bare shape',
            'When `{head_sha} == {reviewed_commit_sha}`, HEAD has NOT advanced',
        ],
    )
    def test_shipped_wording_is_not_flagged(self, shipped):
        """Matched negative control — correct wording must NOT trip the detector."""
        assert not _states_retired_equality(shipped)
