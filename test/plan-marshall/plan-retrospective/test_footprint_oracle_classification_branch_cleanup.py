# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks."""


from __future__ import annotations

from _footprint_oracle_classification_fixtures import MANIFEST_SCRIPT, _check, _setup, _write_diff

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402


class TestBranchCleanupRuleDoesNotClaimAnEmptyDiff:
    """Rule M4 fails on an EMPTY survivor set, which the filter is what produces."""

    def test_fully_filtered_footprint_names_the_reduction_not_an_empty_diff(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'branch-cleanup']},
            },
        )
        diff = _write_diff(
            tmp_path,
            ['.plan/plans/oracle-plan/status.json', '.plan/plans/oracle-plan/execution.toon'],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        # The raw diff was NOT empty — the guard above already rules that case out.
        assert data['diff']['files_total'] == 2
        cleanup = _check(data['checks'], 'branch_cleanup_changes')
        assert 'diff is empty' not in cleanup['message'], cleanup['message']
        assert 'no implementation file changed' in cleanup['message'], cleanup['message']
        assert 'all 2 diff entries' in cleanup['message'], cleanup['message']

        finding = [f for f in data['findings'] if f['code'] == 'branch_cleanup_without_changes']
        assert finding, data['findings']
        assert 'diff is empty' not in finding[0]['message'], finding[0]['message']
        # The finding says what it knows and stops there: every drop category can
        # hold tracked files that really changed on the branch — a report or config
        # entry plainly, and `.plan/` too, which is only partly git-ignored — so no
        # conclusion about the push follows from this state.
        assert 'nothing to push' not in finding[0]['message'], finding[0]['message']


class TestConsumerDispatchSetsAreKnownCategories:
    """Each consumer selects from ``CATEGORIES`` by name; pin that the names exist.

    This catches a typo or a renamed category. It cannot decide where a genuinely
    NEW category belongs — that stays an edit at each consumer, which is what the
    ``CATEGORIES`` comment says.
    """

    def test_dispatch_sets_are_subsets_of_the_category_vocabulary(self):
        import sys as _sys

        scripts = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts'
        _sys.path.insert(0, str(scripts))
        from _footprint_classification import CATEGORIES

        from conftest import load_script_module

        manifest_mod = load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_dispatch_mod'
        )
        routing_mod = load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-routing-decisions.py', 'crd_dispatch_mod'
        )
        dropped = set(manifest_mod._DROPPED_CATEGORIES)
        production = set(routing_mod._PRODUCTION_CATEGORIES)
        # Non-vacuity FIRST: a subset assertion over an empty set passes trivially,
        # so an emptied dispatch policy would remove this test's coverage without
        # failing it.
        assert dropped, 'the manifest drop policy is empty — this guard would pass vacuously'
        assert production, 'the routing production policy is empty — this guard would pass vacuously'
        assert CATEGORIES, 'the category vocabulary is empty'

        assert dropped <= set(CATEGORIES)
        assert production <= set(CATEGORIES)
        # And the two dispatches must not both claim the same category.
        assert not dropped & production


# =============================================================================
# The summary must be total over what was emitted
# =============================================================================


class TestSummarizeChecksIsTotal:
    """An unrecognised verdict must land in a bucket, not vanish from the summary."""

    def test_every_check_is_counted_even_under_an_unknown_status(self):
        from conftest import load_script_module

        mod = load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_summary_mod'
        )
        checks = [
            {'name': 'a', 'status': 'pass', 'message': ''},
            {'name': 'b', 'status': 'fail', 'message': ''},
            {'name': 'c', 'status': 'skip', 'message': ''},
            {'name': 'd', 'status': mod.STATUS_INDETERMINATE, 'message': ''},
            {'name': 'e', 'status': 'a_status_added_later', 'message': ''},
        ]
        summary = mod.summarize_checks(checks)
        assert sum(summary.values()) == len(checks), summary
        assert summary['a_status_added_later'] == 1, summary

    def test_known_statuses_report_an_explicit_zero(self):
        from conftest import load_script_module

        mod = load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_summary_mod2'
        )
        assert mod.summarize_checks([]) == {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'indeterminate': 0,
        }

    def test_every_status_the_script_emits_has_a_named_bucket(self):
        """Derived from the emitted set, not from the bucket map it is checking."""
        import re as _re

        from conftest import load_script_module

        mod = load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_summary_mod3'
        )
        source = (
            MARKETPLACE_ROOT
            / 'plan-marshall'
            / 'skills'
            / 'plan-retrospective'
            / 'scripts'
            / 'check-manifest-consistency.py'
        ).read_text(encoding='utf-8')
        emitted = set(_re.findall(r"_make_check\(\s*'[^']+',\s*'([a-z]+)'", source))
        emitted.add(mod.STATUS_INDETERMINATE)
        assert emitted, 'no emitted statuses found — the extraction pattern went stale'
        assert emitted <= set(mod._STATUS_BUCKETS), emitted - set(mod._STATUS_BUCKETS)


# =============================================================================
# The reduction report's membership is derived, not mirrored
# =============================================================================


class TestDiffFedRuleRegistryIsTheSingleSource:
    """A diff-fed rule cannot be evaluated while bypassing the reduction report.

    `_DIFF_FED_CHECKS` used to be a hardcoded name set mirroring the dispatch
    table. A new filtered evaluator added to one and not the other would silently
    escape D2's guarantee and emit a bare clean pass over a majority-discarded
    footprint — the exact failure the reduction report exists to prevent, reached
    through the report's own membership test.
    """

    @staticmethod
    def _mod():
        from conftest import load_script_module

        return load_script_module(
            'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'cmc_registry_mod'
        )

    def test_the_membership_set_is_derived_from_the_registry(self):
        mod = self._mod()
        assert mod._DIFF_FED_RULES, 'the rule registry is empty — every guard below would be vacuous'
        assert mod._DIFF_FED_CHECKS == frozenset(mod._DIFF_FED_RULES)

    def test_every_registered_evaluator_symbol_exists_and_is_callable(self):
        mod = self._mod()
        for name, symbol in mod._DIFF_FED_RULES.items():
            evaluator = getattr(mod, symbol, None)
            assert callable(evaluator), f'{name} names {symbol}, which is not callable'

    def test_every_registered_rule_emits_a_check_of_that_name(self, tmp_path, monkeypatch):
        """Quantified over the registry, so a rule added later is covered by construction."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': []},
                'phase_6': {'steps': ['push', 'branch-cleanup']},
            },
        )
        diff = _write_diff(tmp_path, ['doc/a.adoc', 'src/b.py'])
        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        emitted = {c['name'] for c in result.toon()['checks']}
        mod = self._mod()
        assert set(mod._DIFF_FED_RULES) <= emitted, set(mod._DIFF_FED_RULES) - emitted

    def test_the_branch_cleanup_exclusion_names_a_registered_rule(self):
        """The separately-dispatched rule must be IN the registry, not beside it."""
        mod = self._mod()
        assert mod._BRANCH_CLEANUP_CHECK in mod._DIFF_FED_RULES


# =============================================================================
# A verdict over no evidence is not a clean result
# =============================================================================


class TestVerdictWithheldWhenNoDiffEvidenceExists:
    """An ABSENT diff observation and a RESOLVED empty one are different states.

    The zero-evidence sibling of the majority-discarded case, and the filtering
    logic cannot see it: nothing was discarded, so the reduction is empty, yet the
    rule evaluated an empty footprint it never received and said "all 0 entries are
    docs-shaped".
    """

    _MANIFEST = {
        'manifest_version': 1,
        'plan_id': 'oracle-plan',
        'phase_5': {'early_terminate': False, 'verification_steps': []},
        'phase_6': {'steps': ['push']},
    }

    def test_no_diff_file_and_no_base_ref_withholds_the_verdict(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(tmp_path, monkeypatch, self._MANIFEST)

        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is False
        docs_only = _check(data['checks'], 'docs_only_diff')
        assert docs_only['status'] == 'indeterminate', docs_only
        assert 'no diff evidence was available' in docs_only['message']

    def test_a_supplied_empty_diff_file_is_evidence_and_still_passes(self, tmp_path, monkeypatch):
        """The negative control, and the distinction that matters.

        A supplied file naming nothing is a RESOLVED empty footprint — the run
        really did change nothing — so a rule may pass on it. Inferring absence
        from `len(files) == 0` would collapse this into the case above.
        """
        plan_id, _ = _setup(tmp_path, monkeypatch, self._MANIFEST)
        diff = _write_diff(tmp_path, [])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        assert data['diff']['diff_available'] is True
        assert data['diff']['files_total'] == 0
        assert _check(data['checks'], 'docs_only_diff')['status'] == 'pass'
