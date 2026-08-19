# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Each test here pins one deliverable of the plan that introduced
``_footprint_classification`` and was verified to FAIL against the pre-fix code:

* ``TestProjectLocalTreeSurvivesFilter`` (D5a) — a multi-file footprint under the
  project-local skill tree survives the filter intact, because ``build.map``
  routes it ``production``. Pre-fix the private ``('.plan/', '.claude/')`` prefix
  tuple discarded every one of them.
* ``TestReducedInputSetReportsReduction`` (D5b) — a rule whose input set was
  reduced reports the reduction instead of a bare clean pass.
* ``TestTestsOnlyRuleFires`` (D5c) — rule M3 fires on the composer's REAL
  ``verify:``-prefixed step-list shape. Pre-fix it compared against a bare
  ``['module-tests']`` the composer never emits, so it could never fire.
* ``TestDiffFileRelativeResolution`` (D5d) — the documented plan-relative
  ``--diff-file`` invocation produces the same verdict as the absolute one, and a
  genuinely unresolvable path fails loudly rather than reporting skip.
"""


from __future__ import annotations

import json
from pathlib import Path

from _footprint_oracle_classification_fixtures import (
    MANIFEST_SCRIPT,
    PROJECT_LOCAL_PRODUCTION,
    ROUTING_SCRIPT,
    _check,
    _setup,
    _write_diff,
)

from conftest import run_script  # noqa: E402

# =============================================================================
# D5c — rule M3 fires on the composer's real step-list shape
# =============================================================================


class TestTestsOnlyRuleFires:
    """M3 must recognise ``verify:module-tests`` — what the composer actually emits."""

    def test_m3_fires_on_canonical_verify_step_shape(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                # DEFAULT_PHASE_5_STEPS narrowed to the module-tests role. The
                # composer boundary-normalizes ``default:verify:module-tests`` to
                # ``verify:module-tests`` — never to a bare ``module-tests``.
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:module-tests']},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(
            tmp_path,
            ['marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py'],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        tests_only = _check(data['checks'], 'tests_only_diff')
        assert tests_only['status'] == 'fail', tests_only
        codes = [f['code'] for f in data['findings']]
        assert 'tests_only_diff_violation' in codes, data['findings']

    def test_m3_passes_when_the_diff_really_is_tests_only(self, tmp_path, monkeypatch):
        """The negative control — the rule fires, and correctly reports a pass."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:module-tests']},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(tmp_path, ['test/plan-marshall/plan-retrospective/test_check_routing_decisions.py'])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert _check(data['checks'], 'tests_only_diff')['status'] == 'pass'

    def test_m3_still_recognises_the_bare_module_tests_form(self, tmp_path, monkeypatch):
        """An archived manifest carrying the bare form keeps being evaluated."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['module-tests']},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(
            tmp_path,
            ['marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py'],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        assert _check(result.toon()['checks'], 'tests_only_diff')['status'] == 'fail'


# =============================================================================
# D5d — the documented relative invocation equals the absolute one
# =============================================================================


class TestDiffFileRelativeResolution:
    """``--diff-file work/footprint.txt`` (the documented form) must not degrade."""

    def _routing_setup(self, tmp_path, monkeypatch):
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
        return plan_id, plan_dir

    def test_documented_relative_form_matches_the_absolute_form(self, tmp_path, monkeypatch):
        plan_id, plan_dir = self._routing_setup(tmp_path, monkeypatch)
        absolute = _write_diff(plan_dir / 'work', PROJECT_LOCAL_PRODUCTION, name='footprint.txt')

        by_absolute = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(absolute)
        )
        by_relative = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', 'work/footprint.txt'
        )
        assert by_absolute.success, by_absolute.stderr
        assert by_relative.success, by_relative.stderr

        absolute_data = by_absolute.toon()
        relative_data = by_relative.toon()
        assert relative_data['footprint_source'] == 'diff_file'
        assert relative_data['footprint_source'] == absolute_data['footprint_source']
        assert relative_data['mis_prune_checks'] == absolute_data['mis_prune_checks']

    def test_unresolvable_diff_file_fails_loudly(self, tmp_path, monkeypatch):
        """A supplied-but-unresolvable path is never reported with the skip token."""
        plan_id, _ = self._routing_setup(tmp_path, monkeypatch)

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', 'work/absent.txt'
        )
        assert not result.success, result.stdout

    def test_manifest_check_also_resolves_the_relative_form(self, tmp_path, monkeypatch):
        """The sibling flag on the manifest check resolves plan-relative too."""
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push']},
            },
        )
        absolute = _write_diff(plan_dir / 'work', PROJECT_LOCAL_PRODUCTION, name='footprint.txt')

        by_absolute = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(absolute)
        )
        by_relative = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', 'work/footprint.txt'
        )
        assert by_absolute.success, by_absolute.stderr
        assert by_relative.success, by_relative.stderr
        # The deliverable's words are "produce the same verdict" — so compare the
        # verdict, not one count of it.
        absolute_data = by_absolute.toon()
        relative_data = by_relative.toon()
        assert relative_data['checks'] == absolute_data['checks']
        assert relative_data['findings'] == absolute_data['findings']
        assert relative_data['summary'] == absolute_data['summary']
        assert relative_data['diff'] == absolute_data['diff']


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
