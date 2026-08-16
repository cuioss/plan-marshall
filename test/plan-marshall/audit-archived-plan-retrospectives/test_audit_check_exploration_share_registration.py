#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``exploration-share`` registration and denominator — the check registers in the
aspect table, an absent counter is indeterminate rather than zero, and the
denominator counts tool-call spend rather than plan count.
"""

from pathlib import Path

import pytest
from _audit_fixtures import (
    _counters,
    _plan_with_counters,
    _shares_plan,
    audit,
)


class TestExplorationShareRegistration:
    """The check is registered at every audit.py site, and the ordering
    invariant (`cross-check-synthesis` stays LAST) survives the insertion."""

    def test_registered_in_every_table(self):
        assert 'exploration-share' in audit.CHECK_NAMES
        assert 'exploration-share' in audit.CROSS_PLAN_CHECKS
        assert 'exploration-share' in audit.CHECK_ERA

    def test_cross_check_synthesis_remains_last(self):
        # the new check is inserted BEFORE the facet-completeness critic, which
        # consumes the other checks' retained results and must run last.
        assert audit.CHECK_NAMES[-1] == 'cross-check-synthesis'
        assert audit.CHECK_NAMES.index('exploration-share') < audit.CHECK_NAMES.index(
            'cross-check-synthesis'
        )

    def test_era_stamp_rides_the_emitted_block(self, tmp_path: Path):
        # The stamp VALUE is pinned in test_audit.py, the mirror
        # project:finalize-step-era-stamp-fill rewrites in lock-step with audit.py;
        # pinning the literal here too would go stale the moment the fill resolves
        # it, so this asserts only that whatever CHECK_ERA holds reaches the block.
        _shares_plan(
            tmp_path, 'p1',
            exploration_calls=1, other_calls=1,
            exploration_bytes=1, other_bytes=1,
        )
        block = audit._stamp_era(
            audit.emit_exploration_share_block(audit.cross_exploration_share([]))
        )

        assert f'fixed_since: {audit.CHECK_ERA["exploration-share"]}' in block

    def test_check_accepted_as_a_cli_choice(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # --check choices are sourced from CHECK_NAMES; drive the real parser so an
        # argparse-level rejection would fail here rather than at audit time.
        _shares_plan(
            tmp_path, 'p1',
            exploration_calls=1, other_calls=1,
            exploration_bytes=1, other_bytes=1,
        )
        # The sandbox carries a real `.plan/local` marker, and cwd is a NESTED
        # subdirectory of it, so `cwd != repo_root` and the persisted-report write
        # lands where it does only because `_resolve_repo_root` walked up. Under a
        # `repo_root = Path.cwd()` derivation the report would land beneath `nested`
        # instead, which both assertions below catch.
        (tmp_path / '.plan' / 'local').mkdir(parents=True, exist_ok=True)
        nested = tmp_path / 'nested' / 'workdir'
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        exit_code = audit.main(
            ['--check', 'exploration-share', '--plan-dir', str(tmp_path)]
        )

        assert exit_code == 0
        assert list((tmp_path / audit.AUDIT_REPORTS_REL).glob('*.toon')), (
            'persisted report did not land under the resolved repo root'
        )
        assert not (nested / audit.AUDIT_REPORTS_REL).exists(), (
            'persisted report followed cwd instead of the resolved repo root'
        )


class TestExplorationShareAbsentIsNotZero:
    """A plan whose counters are ABSENT measured nothing and is EXCLUDED from the
    corpus — never admitted at zero exploration, which would enter it as a
    maximally efficient plan. A MEASURED zero is a real observation and stays in."""

    def test_plan_without_counters_is_excluded_not_zeroed(self, tmp_path: Path):
        # a pre-counter archived plan: phase sections, but no counter field
        inputs = _plan_with_counters(tmp_path, 'pre-counters', {'5-execute': {}})

        result = audit.cross_exploration_share([inputs])

        assert result['plans_in_corpus'] == 0
        assert result['plans_excluded_no_counters'] == 1
        assert result['excluded_plan_ids'] == ['pre-counters']
        assert result['rows'] == []

    def test_measured_zero_stays_in_the_corpus(self, tmp_path: Path):
        # the walk ran and found no calls: a real observation, not an absence
        inputs = _plan_with_counters(
            tmp_path, 'measured-zero', {'5-execute': _counters(0, 0)}
        )

        result = audit.cross_exploration_share([inputs])

        assert result['plans_in_corpus'] == 1
        assert result['plans_excluded_no_counters'] == 0
        row = result['rows'][0]
        assert row['plan_id'] == 'measured-zero'
        # a zero denominator yields no share — reported as n/a, never as 0%.
        assert row['turn_share'] is None
        assert row['denom_calls'] == 0

    def test_missing_metrics_file_is_excluded(self, tmp_path: Path):
        plan_dir = tmp_path / '.plan' / 'local' / 'archived-plans' / 'nometrics'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

        result = audit.cross_exploration_share([audit.collect_inputs(plan_dir)])

        assert result['excluded_plan_ids'] == ['nometrics']

    def test_counters_sum_across_phases_and_count_measured_phases(self, tmp_path: Path):
        inputs = _plan_with_counters(
            tmp_path,
            'multi',
            {
                '3-outline': _counters(4, 1),
                '5-execute': _counters(6, 9),
                '6-finalize': {},  # carries no counter — not a measured phase
            },
        )

        result = audit.cross_exploration_share([inputs])

        row = result['rows'][0]
        assert row['phases'] == 2
        assert row['exploration_calls'] == 10
        assert row['denom_calls'] == 20


class TestExplorationShareDenominator:
    """`exploration + work + execute` is the productive denominator; the
    `orchestration` and `unclassified` buckets are read and surfaced but excluded
    from every share."""

    def test_orchestration_and_unclassified_excluded_from_share(self, tmp_path: Path):
        inputs = _shares_plan(
            tmp_path, 'excl',
            exploration_calls=3, other_calls=1,
            exploration_bytes=30, other_bytes=10,
            orchestration_calls=100, orchestration_bytes=1000,
            unclassified_calls=50, unclassified_bytes=500,
        )

        result = audit.cross_exploration_share([inputs])

        row = result['rows'][0]
        # denominators carry ONLY the productive buckets, so the huge orchestration
        # and unclassified volumes do not dilute either share.
        assert row['denom_calls'] == 4
        assert row['denom_bytes'] == 40
        assert row['turn_share'] == 0.75
        assert row['byte_share'] == 0.75
        # ...but the unclassified count is still surfaced on the row.
        assert row['unclassified'] == 50
