#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Footprint TIER resolution — every consumer grades the REALIZED footprint.

The defect this pins: the auditor read the retired `references.modified_files` key
directly. Three consumers took `modified_files_count or affected_files_count`, one
reported a hard `0`, and the shipping predicate tested the raw count — so a plan
carrying a capture-while-true `realized_footprint` was graded on a legacy key that
current writers no longer emit at all.

The replacement is a tier order mirroring the shared resolver's offline tiers:
`realized_footprint` → `merge_commit_sha` → `modified_files`.

⛔ Every fixture below makes `realized_footprint` **disjoint from and differently
sized than** `affected_files`. The disjointness is the whole discriminating power:
against the retired `or` fallback the declared count would satisfy a test whose
fixture merely overlapped, so only a disjoint pair can tell "graded on the realized
set" apart from "fell through to the declared one".
"""

import json
from pathlib import Path

import pytest
from _audit_fixtures import audit

#: Disjoint by construction, and of DIFFERENT cardinality (2 vs 5) so the two can
#: never be confused by an equal count either.
_REALIZED = ['src/realized_one.py', 'src/realized_two.py']
_DECLARED = [
    'docs/declared_a.md',
    'docs/declared_b.md',
    'docs/declared_c.md',
    'docs/declared_d.md',
    'docs/declared_e.md',
]


def _plan(tmp_path: Path, plan_id: str, refs: dict, *, tokens: int = 12_000):
    """Materialise a plan dir with the given `references.json` and collect it."""
    plan_dir = tmp_path / '.plan' / 'temp' / 'footprint-corpus' / plan_id
    (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps({'metadata': {'change_type': 'bug_fix'}}), encoding='utf-8'
    )
    (plan_dir / 'tasks' / 'TASK-001.json').write_text('{}', encoding='utf-8')
    (plan_dir / 'work' / 'metrics.toon').write_text(
        f'[5-execute]\ntotal_tokens: {tokens}\n', encoding='utf-8'
    )
    return audit.collect_inputs(plan_dir)


@pytest.fixture
def disjoint_plan(tmp_path: Path):
    """A plan whose realized footprint is disjoint from its declared one."""
    return _plan(
        tmp_path, 'disjoint',
        {'realized_footprint': _REALIZED, 'affected_files': _DECLARED,
         'scope_estimate': 'surgical'},
    )


class TestTierOrder:
    """`resolve_realized_footprint` returns `(paths, tier)` and names its tier."""

    def test_realized_footprint_is_the_first_tier(self, tmp_path: Path):
        # All three keys present: the capture-while-true set must win outright.
        refs = {
            'realized_footprint': _REALIZED,
            'merge_commit_sha': 'deadbeef' * 5,
            'modified_files': _DECLARED,
        }
        paths, tier = audit.resolve_realized_footprint(tmp_path, refs)

        assert tier == 'realized_footprint'
        assert paths == set(_REALIZED)

    def test_legacy_key_is_the_last_tier(self, tmp_path: Path):
        # No capture and no usable SHA: the retired key still answers, but LAST.
        paths, tier = audit.resolve_realized_footprint(
            tmp_path, {'modified_files': _DECLARED}
        )

        assert tier == 'modified_files'
        assert paths == set(_DECLARED)

    def test_an_unusable_merge_sha_falls_through_rather_than_fabricating(
        self, tmp_path: Path
    ):
        # A SHA this clone cannot resolve must not become an empty "measurement".
        paths, tier = audit.resolve_realized_footprint(
            tmp_path,
            {'merge_commit_sha': 'f' * 40, 'modified_files': _DECLARED},
        )

        assert tier == 'modified_files'
        assert paths == set(_DECLARED)

    def test_no_key_at_all_is_unresolved_not_empty(self, tmp_path: Path):
        paths, tier = audit.resolve_realized_footprint(tmp_path, {})

        assert tier == audit.FOOTPRINT_TIER_UNRESOLVED
        assert paths is None

    def test_a_recorded_empty_list_is_RESOLVED_empty(self, tmp_path: Path):
        """The distinction the retired `or` could not express.

        `realized_footprint: []` is a resolved, genuinely-empty footprint — the
        plan changed nothing — and is a different answer from no key at all.
        """
        paths, tier = audit.resolve_realized_footprint(
            tmp_path, {'realized_footprint': []}
        )

        assert tier == 'realized_footprint'
        assert paths == set()
        assert paths is not None


class TestGradedFileCount:
    """`graded_file_count` branches on the TIER, never on falsiness."""

    def test_resolved_footprint_is_graded_not_the_declared_set(self, disjoint_plan):
        assert disjoint_plan.footprint_tier == 'realized_footprint'
        assert disjoint_plan.realized_footprint_count == len(_REALIZED)
        assert disjoint_plan.affected_files_count == len(_DECLARED)
        assert audit.graded_file_count(disjoint_plan) == len(_REALIZED)

    def test_a_resolved_empty_footprint_does_not_fall_through(self, tmp_path: Path):
        """⛔ The case `realized_footprint_count or affected_files_count` gets wrong.

        Both readings produce `0` for the realized side, so only a tier test can
        keep the declared count out of the answer. Against the retired `or` this
        assertion fails with 5.
        """
        inputs = _plan(
            tmp_path, 'resolved-empty',
            {'realized_footprint': [], 'affected_files': _DECLARED},
        )

        assert inputs.footprint_tier == 'realized_footprint'
        assert audit.graded_file_count(inputs) == 0

    def test_the_declared_set_is_used_only_when_nothing_resolves(self, tmp_path: Path):
        """The negative control: the fallback must remain reachable.

        Without this, every assertion above would pass against an implementation
        that had simply deleted the declared fallback.
        """
        inputs = _plan(tmp_path, 'unresolved', {'affected_files': _DECLARED})

        assert inputs.footprint_tier == audit.FOOTPRINT_TIER_UNRESOLVED
        assert audit.graded_file_count(inputs) == len(_DECLARED)


class TestTheFourConsumingSites:
    """Each consumer graded against the REALIZED set, on the disjoint fixture."""

    def test_site_1_shipping_predicate_reads_the_realized_footprint(self, tmp_path: Path):
        # A plan with NO pr_number and no legacy key, but a real capture: it
        # shipped. Against the retired `modified_files_count > 0` it is excluded
        # from the shipping partition entirely.
        inputs = _plan(
            tmp_path, 'shipped-by-capture',
            {'realized_footprint': _REALIZED, 'affected_files': _DECLARED},
        )

        assert audit._plan_shipped(inputs) is True

        shipping, excluded = audit._partition_shipping([inputs])
        assert [i.plan_id for i in shipping] == ['shipped-by-capture']
        assert excluded == []

    def test_site_1_negative_control_a_resolved_empty_footprint_did_not_ship(
        self, tmp_path: Path
    ):
        # The discriminating half: a resolved-EMPTY footprint with no PR record is
        # not delivery evidence, so the predicate must still say False.
        inputs = _plan(
            tmp_path, 'not-shipped',
            {'realized_footprint': [], 'affected_files': _DECLARED},
        )

        assert audit._plan_shipped(inputs) is False

    def test_site_2_manifest_modified_column_reads_the_realized_footprint(
        self, disjoint_plan, tmp_path: Path
    ):
        row = audit.check_execution_manifest(disjoint_plan, tmp_path, {})

        assert row['modified'] == len(_REALIZED)
        # named against the declared count, which is what the `or` fallback and the
        # hard-`0` read would each have produced instead.
        assert row['modified'] != len(_DECLARED)
        assert row['affected'] == len(_DECLARED)

    def test_site_3_scope_estimate_grades_the_realized_count(self, disjoint_plan):
        row = audit.check_scope_estimate(disjoint_plan)

        assert row['actual_file_count'] == len(_REALIZED)
        assert row['actual_file_count'] != len(_DECLARED)

    def test_site_4_token_economics_files_is_the_realized_count(self, disjoint_plan):
        result = audit.cross_token_economics([disjoint_plan])

        row = next(r for r in result['rows'] if r['plan_id'] == 'disjoint')
        assert row['files'] == len(_REALIZED)
        assert row['files'] != len(_DECLARED)

    def test_site_5_docs_only_classifier_reads_the_realized_PATH_SET(
        self, tmp_path: Path
    ):
        """The fifth site needs the paths, not the cardinality.

        The realized set is all `.py`; the declared set is all `.md`. Under the
        retired `refs['modified_files'] or refs['affected_files']` read — with no
        `modified_files` key present — the classifier saw only `.md` paths and
        called a Python change docs-only. The two sets are disjoint AND of opposite
        file type precisely so this inversion is visible.
        """
        _plan(
            tmp_path, 'docs-only-probe',
            {'realized_footprint': _REALIZED, 'affected_files': _DECLARED},
        )
        plan_dir = tmp_path / '.plan' / 'temp' / 'footprint-corpus' / 'docs-only-probe'
        refs = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))

        realized, tier = audit.resolve_realized_footprint(plan_dir, refs)

        assert tier == 'realized_footprint'
        # every realized path is Python, so the docs-only verdict must be False
        assert realized is not None
        assert all(p.endswith('.py') for p in realized)
        # ...while the declared set it must NOT have used is entirely docs
        assert all(p.endswith('.md') for p in refs['affected_files'])
