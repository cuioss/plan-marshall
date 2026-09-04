# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Its sections, in order:

* The oracle can be silent about test files, and silence must not read as production
* The summary must be total over what was emitted
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

# MODULE IDENTITY, not merely reachability: the category vocabulary read here has
# to be the SAME object the loaded consumers resolve, so a plain import — which
# binds whatever ``sys.modules`` holds — is what the guard below depends on. Its
# marketplace ``scripts/`` directory is already on ``sys.path`` via the root
# conftest.
import _footprint_classification
from _footprint_oracle_classification_fixtures import (
    MANIFEST_SCRIPT,
    ROUTING_SCRIPT,
    _check,
    _setup,
    _write_diff,
)

from conftest import MARKETPLACE_ROOT, load_script_module, run_script

# =============================================================================
# The oracle can be silent about test files, and silence must not read as production
# =============================================================================


class TestTestRecognitionSurvivesAnOracleWithNoTestRoute:
    """A tests-only footprint must not become a mis-prune where no ``test`` route exists.

    Both consumers treat an ``unclassified`` path fail-closed as possible
    production. A project whose ``build.map`` declares no ``test`` route would
    therefore have every test file counted as production, turning a tests-only
    footprint into a fabricated ``mis_prune`` FAIL. Test-ness by filename
    convention is recognised where the oracle is silent, which is what prevents it.
    """

    @staticmethod
    def _write_production_only_marshal(base: Path) -> None:
        (base / 'marshal.json').write_text(
            json.dumps(
                {'build': {'map': {'python': [{'glob': 'src/*.py', 'role': 'production'}]}}}
            ),
            encoding='utf-8',
        )

    def _setup_routing(self, tmp_path, monkeypatch):
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        self._write_production_only_marshal(tmp_path / 'base')
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        return plan_id

    def test_tests_only_footprint_is_not_a_mis_prune(self, tmp_path, monkeypatch):
        plan_id = self._setup_routing(tmp_path, monkeypatch)
        diff = _write_diff(tmp_path, ['test/plan-marshall/plan-retrospective/test_check_routing_decisions.py'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'pass', simplify[0]

    def test_a_production_file_in_the_same_footprint_still_fails(self, tmp_path, monkeypatch):
        """The negative control — recognising tests must not blind the rule to code."""
        plan_id = self._setup_routing(tmp_path, monkeypatch)
        diff = _write_diff(
            tmp_path,
            ['test/plan-marshall/plan-retrospective/test_check_routing_decisions.py', 'src/module.py'],
        )

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'fail', simplify[0]

    def test_the_shared_convention_recognises_the_documented_test_shapes(self):
        """Both consumers draw test-ness from THIS set — the positive shapes it names."""
        from _footprint_classification import CATEGORIES, CATEGORY_TEST, classify_path, is_test_path

        for path in (
            'test/a/b.py',
            'nested/tests/c.py',
            'pkg/test_thing.py',
            'pkg/thing_test.py',
            'java/FooTest.java',
            'java/FooSpec.java',
            'js/a.test.js',
            'js/a.spec.js',
        ):
            assert is_test_path(path), path
            assert classify_path(path, []) == CATEGORY_TEST, path
        assert CATEGORY_TEST in CATEGORIES

    def test_the_directory_tokens_are_boundary_anchored(self):
        """A path merely CONTAINING "test" is not a test path.

        The routing check's retired copy matched its bare ``test/`` token with an
        unanchored ``token in path``, so ``latest/foo.py`` read as a test file. The
        shared set is boundary-anchored, which moves such a path to ``unclassified``
        — the fail-closed direction, since the routing consumer then treats it as
        possible production.
        """
        from _footprint_classification import CATEGORY_UNCLASSIFIED, classify_path, is_test_path

        for path in ('latest/foo.py', 'contest/x.py', 'mytest/helper.py', 'foo/bartests/z.py'):
            assert not is_test_path(path), path
            assert classify_path(path, []) == CATEGORY_UNCLASSIFIED, path

    def test_the_two_predicates_answer_different_questions(self):
        """``is_test_path`` and ``classify_path`` share a vocabulary, not an answer.

        Pins the documented precedence rather than a claim that they agree: the
        ``test`` rung sits behind the oracle and behind the ``documentation`` rung,
        so a docs-shaped or oracle-routed path resolves there while still looking
        like a test to the rule-side predicate.
        """
        from _footprint_classification import (
            CATEGORY_DOCUMENTATION,
            CATEGORY_PRODUCTION,
            classify_path,
            is_test_path,
        )

        assert is_test_path('test/foo/README.md')
        assert classify_path('test/foo/README.md', []) == CATEGORY_DOCUMENTATION

        assert is_test_path('test/a/b.py')
        assert classify_path('test/a/b.py', [('test/*.py', 'production')]) == CATEGORY_PRODUCTION

    def test_docs_directory_tokens_never_classify_a_source_file(self):
        """A ``.py`` under ``references/`` is not documentation to the CLASSIFIER.

        The rule-side ``is_docs_path`` is wider than the classification rung, and
        the difference is load-bearing: reading a source file under ``references/``
        as documentation would let a consumer that maps documentation to
        "not production" exonerate a real source change.
        """
        from _footprint_classification import (
            CATEGORY_DOCUMENTATION,
            CATEGORY_UNCLASSIFIED,
            classify_path,
            is_docs_path,
            is_docs_suffix_path,
        )

        for path in ('src/references/helper.py', 'pkg/templates/render.py'):
            assert is_docs_path(path), path
            assert not is_docs_suffix_path(path), path
            assert classify_path(path, []) == CATEGORY_UNCLASSIFIED, path

        assert classify_path('doc/references/x.md', []) == CATEGORY_DOCUMENTATION

    def test_an_unrouted_source_file_under_references_still_counts_as_production(
        self, tmp_path, monkeypatch
    ):
        """The consumer-level consequence of the rung above."""
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, ['src/references/helper.py'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'fail', simplify[0]


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
        # The vocabulary this guard compares against is the registered module —
        # the one any importer, including the two consumers loaded below,
        # resolves. Asserted rather than assumed: a second copy would leave this
        # guard comparing two independent vocabularies, so it would keep passing
        # while the real ones drifted apart.
        assert sys.modules['_footprint_classification'] is _footprint_classification
        CATEGORIES = _footprint_classification.CATEGORIES

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
