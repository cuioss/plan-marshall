#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every classification derived from a deliverable's files comes from its WRITE-SET.

A deliverable's ``**Affected files:**`` list mixes two populations: paths it will
change, and paths it will merely consult (``(read)``). Only the first is the
change footprint, so every classification derived from the list — the file-type
bucket, whether a testing profile is warranted — is a statement about the
write-set alone.

Reading the wholesale list instead let one read-only reference flip a
classification: a consulted test file made a deliverable look test-bearing, and a
consulted ``.py`` made a documentation-only deliverable look like code. The
fixtures below are built so intent and the wholesale list DISAGREE — a
write-set-blind implementation reaches the opposite verdict on every one of them,
which is what makes them discriminating rather than merely green.
"""

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
