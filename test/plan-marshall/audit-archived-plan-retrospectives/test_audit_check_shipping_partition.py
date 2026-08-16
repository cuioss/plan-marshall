#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The shipping predicate's corpus partition — an archived plan counts as shipped
only on delivery evidence, and the delivery-cost checks run over that partition
with separate exclusion accounting.
"""

import re
from pathlib import Path

from _audit_fixtures import (
    _write_shipping_plan,
    audit,
)

from conftest import PROJECT_ROOT

_CHECKS_DOC_DIR = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'checks'
)


_SKILL_DOC = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'SKILL.md'
)


# The prose annotation a SKILL.md summary-table row carries when its check runs
# over the shipping partition. Matched case-insensitively so both the leading
# `Runs over ...` and the mid-sentence `Also runs over ...` phrasings count.
_SHIPPING_ANNOTATION = 'runs over the shipping partition'


# Each summary-table row links its sub-document as `checks/{check-name}.md`; the
# link is the row's machine-readable identity (the leading prose cell is a title,
# not a check name).
_CHECK_DOC_LINK_RE = re.compile(r'checks/([a-z0-9-]+)\.md')


def _skill_md_shipping_annotated_checks() -> set[str]:
    """Return the SKILL.md summary-table rows annotated as shipping-partitioned.

    Scans ONLY the ``## Available checks`` section (so an annotation mentioned in
    the surrounding narrative cannot leak in) and collects the check name from
    each annotated row's ``checks/{name}.md`` sub-document link.
    """
    lines = _SKILL_DOC.read_text(encoding='utf-8').splitlines()
    heading = next(
        (i for i, ln in enumerate(lines) if ln.strip() == '## Available checks'),
        None,
    )
    assert heading is not None, 'SKILL.md has no "## Available checks" section'
    annotated: set[str] = set()
    for line in lines[heading + 1:]:
        if line.startswith('## '):
            break
        if not line.startswith('|') or _SHIPPING_ANNOTATION not in line.lower():
            continue
        match = _CHECK_DOC_LINK_RE.search(line)
        assert match is not None, f'annotated row carries no checks/ link: {line}'
        annotated.add(match.group(1))
    return annotated


class TestShippingPartition:
    """`_plan_shipped` / `_partition_shipping` split the corpus on delivery
    evidence alone, and the excluded plans are counted and named SEPARATELY from
    each partitioned check's examined count."""

    def test_pr_record_alone_is_shipping(self, tmp_path: Path):
        # a PR record with an empty footprint still delivered something
        inputs = _write_shipping_plan(tmp_path, 'pr-only', pr_number='4711')

        assert inputs.modified_files_count == 0
        assert audit._plan_shipped(inputs) is True

    def test_footprint_alone_is_shipping(self, tmp_path: Path):
        # a real footprint with no persisted CI run still delivered something
        inputs = _write_shipping_plan(
            tmp_path, 'footprint-only', modified_files=['src/a.py']
        )

        assert audit.plan_pr_number(inputs.plan_dir) == ''
        assert audit._plan_shipped(inputs) is True

    def test_neither_is_excluded_and_labelled_with_its_archived_reason(
        self, tmp_path: Path
    ):
        # no PR record, no footprint → excluded, labelled with the recorded reason
        inputs = _write_shipping_plan(
            tmp_path, 'no-ship', archived_reason='closed_superseded'
        )

        shipping, excluded = audit._partition_shipping([inputs])

        assert shipping == []
        assert [i.plan_id for i in excluded] == ['no-ship']
        assert audit._exclusion_label(excluded[0]) == 'no-ship:closed_superseded'

    def test_missing_archived_reason_is_still_excluded_and_labelled_unrecorded(
        self, tmp_path: Path
    ):
        # the predicate is DERIVED, so an absent reason cannot re-admit the plan;
        # the label degrades to `unrecorded` rather than the exclusion vanishing.
        inputs = _write_shipping_plan(tmp_path, 'no-reason')

        shipping, excluded = audit._partition_shipping([inputs])

        assert shipping == []
        assert audit._exclusion_label(excluded[0]) == 'no-reason:unrecorded'

    def test_other_non_shipping_reason_excluded_by_the_same_predicate(
        self, tmp_path: Path
    ):
        # NOT `closed_superseded`: there is no per-value special case, so any
        # evidence-free plan is excluded and carries its own reason verbatim.
        inputs = _write_shipping_plan(
            tmp_path, 'abandoned', archived_reason='closed_abandoned'
        )

        shipping, excluded = audit._partition_shipping([inputs])

        assert shipping == []
        assert audit._exclusion_label(excluded[0]) == 'abandoned:closed_abandoned'

    def test_partitioned_check_reports_exclusion_apart_from_examined_count(
        self, tmp_path: Path
    ):
        # `scope-estimate-accuracy` is a delivery-cost check: two shipping plans
        # are examined, the third is excluded — two DISTINCT numbers, and the
        # excluded plan is NAMED rather than silently dropped.
        inputs = [
            _write_shipping_plan(tmp_path, 'ship-a', modified_files=['a.py']),
            _write_shipping_plan(tmp_path, 'ship-b', pr_number='99'),
            _write_shipping_plan(
                tmp_path, 'no-ship', archived_reason='closed_superseded'
            ),
        ]

        output = audit.run_checks(inputs, ['scope-estimate-accuracy'], tmp_path)

        assert 'plans_scanned: 2' in output
        assert 'plans_excluded_non_shipping: 1' in output
        assert 'excluded_non_shipping_plan_ids: no-ship:closed_superseded' in output
        # the excluded plan contributes no row to the check's table
        assert 'ship-a' in output
        assert 'ship-b' in output
        assert '\n  no-ship,' not in output

    def test_input_integrity_still_sees_every_plan(self, tmp_path: Path):
        # the no-false-healthy foundation must never be partitioned: it reports
        # one health row per SCANNED plan, and carries no exclusion columns.
        inputs = [
            _write_shipping_plan(tmp_path, 'ship-a', modified_files=['a.py']),
            _write_shipping_plan(
                tmp_path, 'no-ship', archived_reason='closed_superseded'
            ),
        ]

        output = audit.run_checks(inputs, ['input-integrity'], tmp_path)

        assert 'ship-a' in output
        assert 'no-ship' in output
        assert 'plans_excluded_non_shipping' not in output


class TestDeliveryCostPartitionContract:
    """Pins the partition against the LIVE `CHECK_NAMES` registry.

    Assertion strength is deliberately uneven and recorded here so a future
    reader does not mistake a tautology for a proof:

    - `test_delivery_cost_checks_are_declared_checks` is the LOAD-BEARING
      assertion. It is the one that can actually fail against the set-difference
      derivation (a typo'd or retired name in the decision set), and it is what
      makes the exact cover below real rather than merely arithmetic.
    - `test_partitions_are_disjoint` and `test_partitions_exactly_cover_check_names`
      are PROVABLY IMPLIED by `FULL_CORPUS_CHECKS = frozenset(CHECK_NAMES) -
      DELIVERY_COST_CHECKS` plus the load-bearing assertion, and cannot fail
      today. They are kept as REGRESSION TRIPWIRES, not as independent evidence:
      they become non-vacuous the moment someone re-authors `FULL_CORPUS_CHECKS`
      as a literal list — exactly the drift the derived construction exists to
      prevent — which is why they are written against the live module attributes.
    - `test_check_names_has_no_duplicates` is independent of the derivation (the
      set-based exact cover cannot see a duplicated entry) and can genuinely fail.
    - `test_documentation_is_in_lock_step_with_the_partition` iterates the two
      live constants rather than a copied filename list, so a membership change
      moves the documentation obligation with it. It guards BOTH hand-maintained
      prose mirrors of the membership: the per-check `checks/{name}.md`
      sub-documents AND the `SKILL.md` "Available checks" summary table, whose
      shipping-partition row annotations are asserted equal to the live
      `DELIVERY_COST_CHECKS` frozenset.
    """

    def test_delivery_cost_checks_are_declared_checks(self):
        # no phantom member that is not a real declared check
        assert audit.DELIVERY_COST_CHECKS <= frozenset(audit.CHECK_NAMES)

    def test_partitions_are_disjoint(self):
        # regression tripwire — see the class docstring
        assert audit.DELIVERY_COST_CHECKS.isdisjoint(audit.FULL_CORPUS_CHECKS)

    def test_partitions_exactly_cover_check_names(self):
        # regression tripwire — see the class docstring
        assert (
            audit.DELIVERY_COST_CHECKS | audit.FULL_CORPUS_CHECKS
            == frozenset(audit.CHECK_NAMES)
        )

    def test_check_names_has_no_duplicates(self):
        # the set-based exact cover above compares SETS, so a duplicated entry in
        # CHECK_NAMES would slip past it; this assertion is what catches one.
        assert len(audit.CHECK_NAMES) == len(set(audit.CHECK_NAMES))

    def test_track_selection_accuracy_falls_into_the_full_corpus_side(self):
        # it grades a per-plan planning decision against its counterfactual, not
        # a cost-per-delivery ratio, so a non-shipping plan is a legitimate and
        # informative observation for it. No hand edit puts it here — the
        # derivation does.
        assert 'track-selection-accuracy' in audit.FULL_CORPUS_CHECKS

    def test_input_integrity_falls_into_the_full_corpus_side(self):
        # the declared no-false-healthy foundation; a partition would blind it.
        assert 'input-integrity' in audit.FULL_CORPUS_CHECKS

    def test_documentation_is_in_lock_step_with_the_partition(self):
        # every partitioned check documents the exclusion columns, and no
        # unpartitioned check claims them. Iterates the live constants so a
        # membership change moves the obligation with it.
        missing: list[str] = []
        for name in sorted(audit.DELIVERY_COST_CHECKS):
            doc = _CHECKS_DOC_DIR / f'{name}.md'
            if not doc.is_file():
                missing.append(f'{name}: no checks/{name}.md')
                continue
            if 'plans_excluded_non_shipping' not in doc.read_text(encoding='utf-8'):
                missing.append(f'{name}: doc omits plans_excluded_non_shipping')
        stray: list[str] = []
        for name in sorted(audit.FULL_CORPUS_CHECKS):
            doc = _CHECKS_DOC_DIR / f'{name}.md'
            if not doc.is_file():
                continue
            if 'plans_excluded_non_shipping' in doc.read_text(encoding='utf-8'):
                stray.append(name)

        assert missing == [], missing
        assert stray == [], stray

        # The SKILL.md "Available checks" table is the SECOND hand-maintained
        # prose mirror of the same membership. Its shipping-partition row
        # annotations must be exactly DELIVERY_COST_CHECKS — no more (a row
        # annotated for a check the code does not partition), no fewer (a
        # partitioned check whose row lost, or never gained, the annotation).
        assert _skill_md_shipping_annotated_checks() == set(
            audit.DELIVERY_COST_CHECKS
        )
