#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The survey pair reaches the lesson consult, and its two contracts are enforced.

Three defects that all reduce to one shape — a derived set that is smaller than
the thing it claims to describe, with nothing able to see the difference.

**The consult read ``affected_files`` wholesale.** ``_derive_components`` maps a
deliverable's paths to ``{bundle}:{skill}`` lesson components, and it read the
flat field directly. That is wrong in BOTH directions: a survey-scope
deliverable declares ``Files to survey`` + ``Files expected to mutate`` INSTEAD
of the flat list, so its ``affected_files`` is empty and every component it was
about to change derived to nothing — the consult reported a confident
``surfaced_count: 0`` for a plan whose edits it never looked at. And a
``(read)`` entry names a file the deliverable consults and leaves untouched, so
counting it surfaced lessons for a component the plan does not edit. The source
is now ``deliverable_write_set``, which applies ``declares_change`` across both
write-bearing fields.

**The write-set deduplicated on the RAW spelling.** ``./src/a.py`` and
``src/a.py`` name one file, and both survived as members. Every set-guarding
consumer downstream compares normalized, so the pair became one matched member
and one permanent phantom gap — the projection closure reported whichever
spelling no task happened to use as a declared write nobody targets.

**The survey pair's disjointness was documented and unchecked.**
``deliverable_write_set`` states it as a property of the standard and
deduplicates defensively against it, but nothing rejected a violation — so a
path declared under both headings was silently resolved in ONE direction (into
the write-set), while the survey declaration calling it read-only stood
unchallenged in the document. The deliverable then said two contradictory things
about one path, and each consumer believed whichever field it read.
"""

from __future__ import annotations

from typing import Any

import pytest

from conftest import load_script_module

_lessons_query = load_script_module(
    'plan-marshall', 'manage-lessons', '_lessons_query.py', '_lessons_query_survey_pair'
)
_parsing = load_script_module(
    'plan-marshall', 'manage-solution-outline', '_plan_parsing.py', '_plan_parsing_survey_pair'
)
_mso = load_script_module('plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py', '_mso_survey_pair')

_derive_components = _lessons_query._derive_components
deliverable_write_set = _parsing.deliverable_write_set
normalize_declared_path = _parsing.normalize_declared_path
validate_deliverable_contract = _mso.validate_deliverable_contract

_SKILL_A = 'marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py'
_SKILL_B = 'marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md'
_OUTSIDE = 'doc/developer/build.adoc'


def _entries(paths: list[str], intent: str | None) -> list[dict[str, Any]]:
    return [{'path': p, 'intent': intent} for p in paths]


def _deliverable(
    *,
    number: int = 1,
    affected: list[str] | None = None,
    survey: list[str] | None = None,
    mutate: list[str] | None = None,
    affected_intent: str | None = 'write-replace',
) -> dict[str, Any]:
    """A deliverable in the shape ``extract_deliverables`` returns."""
    return {
        'number': number,
        'title': 'D',
        'affected_files': _entries(affected or [], affected_intent),
        # The documented survey-pair form carries no per-path markers; the parser
        # gives a survey bullet the `read` default and leaves a mutation bullet
        # unset, which `declares_change` counts as a write.
        'survey_scope': _entries(survey or [], 'read'),
        'mutation_scope': _entries(mutate or [], None),
    }


# =============================================================================
# _derive_components reads the WRITE-SET
# =============================================================================


class TestDeriveComponentsUsesTheWriteSet:
    def test_a_survey_pair_only_deliverable_yields_its_components(self):
        """THE regression: this deliverable's ``affected_files`` is empty.

        Reading the flat field returned no components at all, so the consult
        surfaced nothing for a plan that was about to edit two skills.
        """
        deliverable = _deliverable(survey=[_SKILL_B], mutate=[_SKILL_A])

        components, unmapped = _derive_components([deliverable])

        assert components == ['plan-marshall:manage-locks']
        assert unmapped == []

    def test_a_survey_only_path_is_not_a_component(self):
        """A surveyed path is examined, not edited — it belongs to no write-set.

        Paired with the case above, this is what proves the derivation reads the
        write-set rather than simply widening to every declared field: the same
        deliverable's survey entry does NOT contribute a component.
        """
        deliverable = _deliverable(survey=[_SKILL_B], mutate=[_SKILL_A])

        components, _unmapped = _derive_components([deliverable])

        assert 'plan-marshall:manage-status' not in components

    def test_a_read_intent_affected_file_is_not_a_component(self):
        """A ``(read)`` entry must not surface lessons for a component nobody edits."""
        deliverable = _deliverable(affected=[_SKILL_A], affected_intent='read')

        components, unmapped = _derive_components([deliverable])

        assert components == []
        assert unmapped == []

    def test_a_write_intent_affected_file_is_still_a_component(self):
        """Positive control — the flat path was never the defect."""
        deliverable = _deliverable(affected=[_SKILL_A])

        components, _unmapped = _derive_components([deliverable])

        assert components == ['plan-marshall:manage-locks']

    def test_a_non_skill_write_path_is_reported_as_unmapped(self):
        """A changed path outside the skill tree is reported, never dropped."""
        deliverable = _deliverable(affected=[_OUTSIDE])

        components, unmapped = _derive_components([deliverable])

        assert components == []
        assert unmapped == [_OUTSIDE]

    def test_components_are_deduplicated_and_sorted_across_deliverables(self):
        """Determinism: the result must not depend on document order."""
        first = _deliverable(number=1, mutate=[_SKILL_B])
        second = _deliverable(number=2, affected=[_SKILL_A, _SKILL_B])

        components, _unmapped = _derive_components([first, second])

        assert components == ['plan-marshall:manage-locks', 'plan-marshall:manage-status']


# =============================================================================
# deliverable_write_set deduplicates on the NORMALIZED spelling
# =============================================================================


class TestWriteSetNormalization:
    @pytest.mark.parametrize(
        'spellings',
        [
            pytest.param(['./src/a.py', 'src/a.py'], id='dot_slash_then_bare'),
            pytest.param(['src/a.py', './src/a.py'], id='bare_then_dot_slash'),
            pytest.param(['./src/a.py', './src/a.py'], id='both_dot_slash'),
            pytest.param(['src/a.py/', 'src/a.py'], id='trailing_separator'),
        ],
    )
    def test_two_spellings_of_one_path_yield_one_member(self, spellings):
        deliverable = _deliverable(affected=spellings)

        assert deliverable_write_set(deliverable) == ['src/a.py']

    def test_the_member_is_the_canonical_spelling(self):
        """A raw member cannot be compared against the step target it must match."""
        deliverable = _deliverable(affected=['./src/a.py'])

        assert deliverable_write_set(deliverable) == ['src/a.py']

    def test_dedup_spans_the_two_write_bearing_fields(self):
        """``affected_files`` and ``mutation_scope`` union to ONE member."""
        deliverable = _deliverable(affected=['./src/a.py'], mutate=['src/a.py'])

        assert deliverable_write_set(deliverable) == ['src/a.py']

    def test_a_path_that_normalizes_to_empty_is_dropped(self):
        """``./`` is a non-empty string that normalizes to ``''``.

        An empty write-set member would be compared against step targets and
        reported as a gap named ``''``.
        """
        deliverable = _deliverable(affected=['./', 'src/a.py'])

        assert deliverable_write_set(deliverable) == ['src/a.py']

    def test_distinct_paths_are_not_collapsed(self):
        """Positive control — normalization must not merge two real files."""
        deliverable = _deliverable(affected=['./src/a.py', 'src/b.py'])

        assert deliverable_write_set(deliverable) == ['src/a.py', 'src/b.py']

    def test_normalization_preserves_a_leading_dot_directory(self):
        """Only ``./`` prefixes are stripped — a dotfile tree keeps its dot."""
        assert normalize_declared_path('.claude/skills/x/SKILL.md') == '.claude/skills/x/SKILL.md'


# =============================================================================
# The survey pair must be DISJOINT
# =============================================================================


def _contract_deliverable(*, survey: list[str], mutate: list[str]) -> dict[str, Any]:
    """A deliverable complete enough that only the disjointness check can fail."""
    return {
        'number': 4,
        'title': 'D',
        'metadata': {
            'change_type': 'bug_fix',
            'execution_mode': 'automated',
            'domain': 'plan-marshall-plugin-dev',
            'module': 'plan-marshall',
            'depends': 'none',
        },
        'profiles': ['implementation'],
        'affected_files': [],
        'survey_scope': _entries(survey, 'read'),
        'mutation_scope': _entries(mutate, None),
        'verification': {'command': 'x', 'criteria': 'y'},
        'has_success_criteria': True,
    }


def _disjointness_errors(errors: list[str]) -> list[str]:
    return [e for e in errors if 'declared under BOTH' in e]


class TestSurveyPairDisjointness:
    def test_a_doubly_declared_path_is_an_error(self):
        errors, _warnings = validate_deliverable_contract(
            _contract_deliverable(survey=[_SKILL_A, _SKILL_B], mutate=[_SKILL_A])
        )

        offending = _disjointness_errors(errors)
        assert len(offending) == 1, errors
        assert _SKILL_A in offending[0]
        assert 'D4' in offending[0]

    def test_a_disjoint_survey_pair_is_clean(self):
        """Positive control — the ordinary correct shape must not be flagged."""
        errors, _warnings = validate_deliverable_contract(_contract_deliverable(survey=[_SKILL_B], mutate=[_SKILL_A]))

        assert _disjointness_errors(errors) == [], errors

    @pytest.mark.parametrize(
        ('survey_spelling', 'mutate_spelling'),
        [
            pytest.param('./src/a.py', 'src/a.py', id='dot_slash_in_survey'),
            pytest.param('src/a.py', './src/a.py', id='dot_slash_in_mutate'),
            pytest.param('src/a.py/', 'src/a.py', id='trailing_separator'),
        ],
    )
    def test_the_comparison_is_on_the_normalized_spelling(self, survey_spelling, mutate_spelling):
        """Two spellings of one path are the one path they name.

        A raw comparison would let the contradiction through under any
        alternative spelling, which is the easiest way to author it by accident.
        """
        errors, _warnings = validate_deliverable_contract(
            _contract_deliverable(survey=[survey_spelling], mutate=[mutate_spelling])
        )

        assert len(_disjointness_errors(errors)) == 1, errors

    def test_every_doubly_declared_path_is_named(self):
        """One error per offending path — a count alone is not actionable."""
        errors, _warnings = validate_deliverable_contract(
            _contract_deliverable(survey=[_SKILL_A, _SKILL_B], mutate=[_SKILL_A, _SKILL_B])
        )

        offending = _disjointness_errors(errors)
        assert len(offending) == 2
        assert any(_SKILL_A in e for e in offending)
        assert any(_SKILL_B in e for e in offending)
