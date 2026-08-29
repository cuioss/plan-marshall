#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every classification derived from a deliverable's files comes from its WRITE-SET.

A deliverable's ``**Affected files:**`` list mixes two populations: paths it will
change, and paths it will merely consult (``(read)``). Only the first is the
change footprint, so every classification derived from the list — the file-type
bucket, whether a testing profile is warranted — is a statement about the
write-set alone.

The write-set also unions a survey-scope deliverable's ``**Files expected to
mutate:**`` field, which is declared change intent by another name. These
fixtures exercise the ``Affected files`` half only; the survey half has its own
suite in ``test_survey_scope_declaration.py``.

Reading the wholesale list instead let one read-only reference flip a
classification: a consulted test file made a deliverable look test-bearing, and a
consulted ``.py`` made a documentation-only deliverable look like code. The
fixtures below are built so intent and the wholesale list DISAGREE — a
write-set-blind implementation reaches the opposite verdict on every one of them,
which is what makes them discriminating rather than merely green.
"""

import sys

import pytest

from conftest import load_script_module

_parsing = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    '_plan_parsing.py',
    module_name='_plan_parsing_write_set',
)
_mod = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    'manage-solution-outline.py',
    module_name='manage_solution_outline_write_set',
)

deliverable_write_set = _parsing.deliverable_write_set
extract_declared_bucket = _parsing.extract_declared_bucket
extract_deliverables = _parsing.extract_deliverables
validate_deliverable_contract = _mod.validate_deliverable_contract
DECLARED_BUCKET_VOCABULARY = _mod._DECLARED_BUCKET_VOCABULARY

#: A documentation path and a code path, used as the two sides of every
#: disagreement below.
_DOC_PATH = 'doc/developer/build.adoc'
_CODE_PATH = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py'
_TEST_PATH = 'test/plan-marshall/manage-tasks/test_manage_tasks.py'


def _deliverable(affected: list[tuple[str, str | None]], **overrides):
    """Build a deliverable record from ``(path, intent)`` pairs."""
    record = {
        'number': 1,
        'title': 'Sample deliverable',
        'metadata': {},
        'profiles': ['implementation'],
        'affected_files': [{'path': path, 'intent': intent} for path, intent in affected],
        'declared_bucket': None,
        'verification': {},
        'has_success_criteria': True,
    }
    record.update(overrides)
    return record


# =============================================================================
# The write-set itself
# =============================================================================


class TestDeliverableWriteSet:
    """``deliverable_write_set`` separates changed paths from consulted ones."""

    def test_read_intent_paths_are_excluded(self):
        deliverable = _deliverable([(_CODE_PATH, 'read'), (_DOC_PATH, 'write-replace')])

        assert deliverable_write_set(deliverable) == [_DOC_PATH]

    def test_every_mutating_intent_is_included(self):
        """The write-set is the complement of ``read``, not a list of one verb."""
        deliverable = _deliverable(
            [
                ('a.py', 'write-new'),
                ('b.py', 'write-replace'),
                ('c.py', 'delete'),
                ('d.py', 'read'),
            ]
        )

        assert deliverable_write_set(deliverable) == ['a.py', 'b.py', 'c.py']

    def test_missing_intent_marker_counts_as_a_write(self):
        """An unmarked entry must not be quieter than a marked one.

        The marker is mandatory and its absence is already a validation error.
        Treating the unmarked entry as a read would subtract it from the change
        footprint AND report the error, so the classification would silently
        shrink on exactly the input that is least trustworthy.
        """
        deliverable = _deliverable([(_CODE_PATH, None)])

        assert deliverable_write_set(deliverable) == [_CODE_PATH]

    def test_a_wholly_read_only_deliverable_has_an_empty_write_set(self):
        deliverable = _deliverable([(_CODE_PATH, 'read'), (_TEST_PATH, 'read')])

        assert deliverable_write_set(deliverable) == []


# =============================================================================
# The module_testing profile check
# =============================================================================


class TestModuleTestingProfileReadsTheWriteSet:
    """A consulted test file does not give a deliverable a test surface."""

    def test_read_only_test_file_does_not_satisfy_module_testing(self):
        """The disagreement case: the wholesale list has a test path, the write-set does not."""
        deliverable = _deliverable(
            [(_TEST_PATH, 'read'), (_DOC_PATH, 'write-replace')],
            profiles=['implementation', 'module_testing'],
            metadata={
                'change_type': 'feature',
                'execution_mode': 'automated',
                'domain': 'python',
                'module': 'plan-marshall',
                'depends': 'none',
            },
            verification={'command': 'verify', 'criteria': 'green'},
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert any('module_testing profile but no test files' in w for w in warnings), (
            f'a read-only test reference satisfied module_testing; warnings={warnings}'
        )

    def test_wholly_read_only_deliverable_does_not_satisfy_module_testing(self):
        """The sharpest case: an EMPTY write-set under a `module_testing` profile.

        Such a deliverable writes no test file at all, so it is the strongest
        instance of what this check reports — and a non-empty guard on the
        write-set silenced the check exactly there, because the emptiest input
        looked like "nothing to check" rather than "nothing is written".
        """
        deliverable = _deliverable(
            [(_TEST_PATH, 'read'), (_CODE_PATH, 'read')],
            profiles=['implementation', 'module_testing'],
            metadata={
                'change_type': 'feature',
                'execution_mode': 'automated',
                'domain': 'python',
                'module': 'plan-marshall',
                'depends': 'none',
            },
            verification={'command': 'verify', 'criteria': 'green'},
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert any('module_testing profile but no test files' in w for w in warnings), (
            f'a deliverable that writes nothing satisfied module_testing; warnings={warnings}'
        )

    def test_written_test_file_satisfies_module_testing(self):
        """Paired negative: the same path, declared as a write, is a real test surface."""
        deliverable = _deliverable(
            [(_TEST_PATH, 'write-new'), (_DOC_PATH, 'write-replace')],
            profiles=['implementation', 'module_testing'],
            metadata={
                'change_type': 'feature',
                'execution_mode': 'automated',
                'domain': 'python',
                'module': 'plan-marshall',
                'depends': 'none',
            },
            verification={'command': 'verify', 'criteria': 'green'},
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert not any('module_testing profile but no test files' in w for w in warnings), (
            f'a written test file failed to satisfy module_testing; warnings={warnings}'
        )


# =============================================================================
# The declared file-type bucket
# =============================================================================


class TestDeclaredBucketIsParsed:
    """The ``<!-- bucket: X -->`` audit trail is read back, not merely written."""

    def test_bucket_comment_is_extracted_from_the_profiles_line(self):
        content = '**Profiles:** <!-- bucket: documentation_only -->\n- implementation\n'

        assert extract_declared_bucket(content) == 'documentation_only'

    def test_absent_bucket_comment_yields_none(self):
        content = '**Profiles:**\n- implementation\n'

        assert extract_declared_bucket(content) is None

    def test_bucket_comment_in_prose_is_not_read_as_the_declared_bucket(self):
        """Extraction is anchored to the ``**Profiles:**`` line, not the whole body.

        Deliverable prose is free text an author writes, and this convention is
        the kind of thing prose quotes. A free-floating match would take a
        documented example as the deliverable's own declaration and fail it
        against a write-set it never described.
        """
        content = (
            'The bucket convention is recorded as `<!-- bucket: production_only -->`.\n\n'
            '**Profiles:** <!-- bucket: documentation_only -->\n'
            '- implementation\n'
        )

        assert extract_declared_bucket(content) == 'documentation_only'

    def test_bucket_comment_outside_the_profiles_line_is_ignored(self):
        """With no comment on the Profiles line, prose mentions yield nothing."""
        content = (
            'Earlier work used `<!-- bucket: production_only -->` here.\n\n'
            '**Profiles:**\n'
            '- implementation\n'
        )

        assert extract_declared_bucket(content) is None

    def test_bucket_comment_is_not_read_as_a_profile(self):
        """Extraction must not disturb the sibling parse of the same line."""
        section = (
            '### 1. Sample\n\n'
            '**Profiles:** <!-- bucket: production_only -->\n'
            '- implementation\n\n'
        )

        deliverable = extract_deliverables(section)[0]

        assert deliverable['profiles'] == ['implementation']
        assert deliverable['declared_bucket'] == 'production_only'


class TestDeclaredBucketAgreesWithTheWriteSet:
    """The one bucket contradiction this layer can PROVE is adjudicated.

    When every declared write is documentation by suffix, the aggregator's bucket
    is necessarily ``documentation_only``: stage 1 of
    ``_classify_paths_via_extensions`` splits doc paths out before the build
    extensions run, so no other role can be claimed. Any other declared bucket
    over that write-set is therefore false.

    The converse is deliberately NOT adjudicated — see
    :class:`TestNonProvableShapesAreNotAdjudicated`.
    """

    def _contract_fields(self):
        return {
            'metadata': {
                'change_type': 'feature',
                'execution_mode': 'automated',
                'domain': 'python',
                'module': 'plan-marshall',
                'depends': 'none',
            },
            'verification': {'command': 'verify', 'criteria': 'green'},
        }

    def test_read_only_code_reference_does_not_flip_a_docs_only_bucket(self):
        """The archetype: the wholesale list has a ``.py``, every WRITE is documentation.

        A write-set-blind check reads this deliverable as code-bearing and reports
        the ``documentation_only`` bucket as a contradiction — the false positive
        that would push a docs-only deliverable onto the code path.
        """
        deliverable = _deliverable(
            [(_CODE_PATH, 'read'), (_DOC_PATH, 'write-replace')],
            declared_bucket='documentation_only',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), (
            f'a read-only code reference flipped the bucket; errors={errors}'
        )

    def test_code_bucket_over_a_docs_only_write_set_is_rejected(self):
        """A code bucket whose every declared write is documentation.

        This is the shape a read-only reference produces when the author lets it
        decide the bucket, so the error names that cause explicitly. Changing only
        the code path's intent to a write makes the claim un-provable and the
        error disappears (see the paired case below), so this arm is carried by
        the write-set rather than by a check that fires on everything.
        """
        deliverable = _deliverable(
            [(_CODE_PATH, 'read'), (_DOC_PATH, 'write-replace')],
            declared_bucket='production_only',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert any('production_only' in e and 'contradicts' in e for e in errors), (
            f'a docs-only write-set under a code bucket was accepted; errors={errors}'
        )

    def test_the_same_bucket_over_a_code_write_is_not_rejected(self):
        """Paired negative: intent is the only variable, and it flips the verdict."""
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace'), (_DOC_PATH, 'write-replace')],
            declared_bucket='production_only',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), f'errors={errors}'

    def test_bucket_comparison_is_case_insensitive(self):
        """The comment regex accepts any case, so the comparison must too.

        A regex that parses ``<!-- bucket: DOCUMENTATION_ONLY -->`` into a value
        the comparison then fails to recognise reports a docs-only deliverable as
        contradicting its own docs-only write-set.
        """
        deliverable = _deliverable(
            [(_DOC_PATH, 'write-replace')],
            declared_bucket='DOCUMENTATION_ONLY',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), f'errors={errors}'

    def test_no_declared_bucket_is_not_adjudicated(self):
        """A deliverable with no recorded bucket has no claim to contradict."""
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace')],
            declared_bucket=None,
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), f'errors={errors}'

    def test_empty_write_set_is_not_adjudicated(self):
        """A verification-only deliverable declares no writes, so nothing contradicts."""
        deliverable = _deliverable(
            [(_CODE_PATH, 'read')],
            profiles=['verification'],
            declared_bucket='documentation_only',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), f'errors={errors}'


class TestNonProvableShapesAreNotAdjudicated:
    """A ``documentation_only`` claim over a non-doc write is left to the aggregator.

    These write-sets all resolve to ``documentation_only`` in
    ``_classify_paths_via_extensions`` — infrastructure config collapses to it
    because the ``config`` role is excluded from the plan-wide collapse, and a
    template takes the role of what it renders into. None of that is visible from
    paths alone at this layer, so erroring here would reject an outline whose
    bucket is exactly what the classifier mandates.

    Each case is a real shape from this repository, not a synthetic one.
    """

    def _contract_fields(self):
        return {
            'metadata': {
                'change_type': 'feature',
                'execution_mode': 'automated',
                'domain': 'python',
                'module': 'plan-marshall',
                'depends': 'none',
            },
            'verification': {'command': 'verify', 'criteria': 'green'},
        }

    @pytest.mark.parametrize(
        'write_paths',
        [
            ['.github/workflows/python-verify.yml'],
            ['doc/developer/build.adoc', '.github/workflows/python-verify.yml'],
            ['doc/developer/readme.adoc.template'],
        ],
        ids=['infra-config-only', 'docs-plus-infra-config', 'template-rendering-to-docs'],
    )
    def test_documentation_only_over_a_non_doc_write_is_accepted(self, write_paths):
        deliverable = _deliverable(
            [(path, 'write-replace') for path in write_paths],
            declared_bucket='documentation_only',
            **self._contract_fields(),
        )

        errors, _warnings = validate_deliverable_contract(deliverable)

        assert not any('bucket' in e for e in errors), (
            f'the aggregator resolves {write_paths} to documentation_only, but the '
            f'outline validator rejected the matching bucket; errors={errors}'
        )


# =============================================================================
# The three states the bucket check used to pass over in silence
# =============================================================================


def _contract_fields():
    return {
        'metadata': {
            'change_type': 'feature',
            'execution_mode': 'automated',
            'domain': 'python',
            'module': 'plan-marshall',
            'depends': 'none',
        },
        'verification': {'command': 'verify', 'criteria': 'green'},
    }


class TestAbsentBucketIsReported:
    """A deliverable that writes files and declares no bucket now says so.

    The bucket comment is the audit trail that the file-type classifier was
    applied at all, so an absent one means the classification never happened.
    Before, ``not declared`` took the same early return as "checked and found
    consistent" — the check was blindest exactly where the classifier had been
    skipped outright.

    Reported as a WARNING, never an error: outlines authored before the
    required-recording rule carry no bucket comment, and failing them would
    reject documents that are merely older than the rule rather than wrong.
    """

    def test_missing_bucket_over_a_non_empty_write_set_warns(self):
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace')],
            declared_bucket=None,
            **_contract_fields(),
        )

        errors, warnings = validate_deliverable_contract(deliverable)

        assert any('no file-type bucket declared' in w for w in warnings), (
            f'a deliverable writing files with no declared bucket was silent; '
            f'warnings={warnings}'
        )
        assert not any('bucket' in e for e in errors), (
            f'the missing bucket must not be an error; errors={errors}'
        )

    def test_missing_bucket_over_an_empty_write_set_is_silent(self):
        """The matched negative control: a verification-only deliverable.

        It declares no writes, so there is no classification it was supposed to
        have made. Without this control the warning above would be satisfied by
        a check that fires on every bucket-less deliverable, which would flood
        every read-only deliverable in every outline.
        """
        deliverable = _deliverable(
            [(_CODE_PATH, 'read')],
            profiles=['verification'],
            declared_bucket=None,
            **_contract_fields(),
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert not any('no file-type bucket declared' in w for w in warnings), (
            f'a read-only deliverable was asked for a bucket; warnings={warnings}'
        )


class TestBucketVocabularyIsChecked:
    """A value that is not one of the six documented buckets is reported.

    The upstream comment regex accepts any ``[a-z_]+``, and the contradiction
    test is an equality comparison against ``documentation_only`` — so a
    misspelling took the not-equal branch and was compared against the write-set
    as though it were a real code bucket, or passed silently.
    """

    def test_unrecognized_bucket_warns(self):
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace')],
            declared_bucket='documentaton_only',
            **_contract_fields(),
        )

        errors, warnings = validate_deliverable_contract(deliverable)

        assert any('is not one of the documented' in w for w in warnings), (
            f'a misspelled bucket passed unremarked; warnings={warnings}'
        )
        assert not any('bucket' in e for e in errors), (
            f'an unrecognized bucket is not on its own an error; errors={errors}'
        )

    def test_misspelled_docs_bucket_also_trips_the_contradiction(self):
        """The worked case the vocabulary check explains, rather than prevents.

        ``documentaton_only`` over an all-documentation write-set is not equal to
        ``documentation_only``, so the contradiction test treats it as a code
        bucket and — correctly, on the value as written — reports it. Before the
        vocabulary check that error was baffling: the author had declared the
        docs bucket and was told it contradicted a docs-only write-set. Both
        signals now fire together, and the warning is what makes the error
        legible.
        """
        deliverable = _deliverable(
            [(_DOC_PATH, 'write-replace')],
            declared_bucket='documentaton_only',
            **_contract_fields(),
        )

        errors, warnings = validate_deliverable_contract(deliverable)

        assert any('is not one of the documented' in w for w in warnings), (
            f'warnings={warnings}'
        )
        assert any('contradicts' in e for e in errors), f'errors={errors}'

    @pytest.mark.parametrize('bucket', DECLARED_BUCKET_VOCABULARY)
    def test_every_documented_bucket_is_accepted(self, bucket):
        """Iterated over the vocabulary itself, not a restated list of six.

        A seventh bucket added to the constant is covered here the moment it is
        added; a hand-listed set would keep asserting completeness over whatever
        values it was written with.
        """
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace')],
            declared_bucket=bucket,
            **_contract_fields(),
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert not any('is not one of the documented' in w for w in warnings), (
            f'documented bucket {bucket!r} was reported as unrecognized; '
            f'warnings={warnings}'
        )

    def test_vocabulary_check_is_case_insensitive(self):
        """The comment regex accepts any case, so membership must fold case too."""
        deliverable = _deliverable(
            [(_CODE_PATH, 'write-replace')],
            declared_bucket='PRODUCTION_ONLY',
            **_contract_fields(),
        )

        _errors, warnings = validate_deliverable_contract(deliverable)

        assert not any('is not one of the documented' in w for w in warnings), (
            f'an upper-case documented bucket was rejected; warnings={warnings}'
        )


class TestUnavailablePredicateIsReported:
    """The fail-open now says it failed open instead of reading as clean.

    ``_write_set_is_all_documentation`` returns ``None`` when
    ``_manifest_core._is_documentation_path`` cannot be imported. ``not None``
    is truthy, so the un-run comparison took the same early return as a
    comparison that ran and found no contradiction — an ImportError and a clean
    result were the same observable.

    The two cases below are a matched pair over ONE identical deliverable: the
    only variable is whether the predicate module can be imported.
    """

    @staticmethod
    def _contradicting_deliverable():
        """A code bucket over a write-set whose every write is documentation.

        This is the one shape the check can PROVE contradictory, so it is the
        shape whose verdict must visibly change when the predicate is gone.
        """
        return _deliverable(
            [(_CODE_PATH, 'read'), (_DOC_PATH, 'write-replace')],
            declared_bucket='production_only',
            **_contract_fields(),
        )

    def test_with_the_predicate_available_the_contradiction_is_an_error(self):
        """The control arm — the predicate imports, and the check adjudicates."""
        errors, warnings = validate_deliverable_contract(self._contradicting_deliverable())

        assert any('contradicts' in e for e in errors), f'errors={errors}'
        assert not any('could not be imported' in w for w in warnings), (
            f'the predicate was available, so no fail-open should be reported; '
            f'warnings={warnings}'
        )

    def test_with_the_predicate_unimportable_the_fail_open_is_named(self, monkeypatch):
        """The same deliverable, with the predicate module made unimportable.

        Binding ``None`` into ``sys.modules`` is what CPython raises ImportError
        on, so the deferred ``from _manifest_core import ...`` fails exactly as
        it would where the sibling skill's module is off the path — the real
        condition the fail-open exists for.
        """
        monkeypatch.setitem(sys.modules, '_manifest_core', None)

        errors, warnings = validate_deliverable_contract(self._contradicting_deliverable())

        assert not any('contradicts' in e for e in errors), (
            f'a comparison that never ran reported a contradiction; errors={errors}'
        )
        assert any('could not be imported' in w for w in warnings), (
            f'the un-run check was indistinguishable from a clean one; '
            f'warnings={warnings}'
        )
        assert any('not a clean result' in w for w in warnings), (
            f'the warning must say what it is NOT; warnings={warnings}'
        )
