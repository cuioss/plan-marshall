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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import build_happy_plan_dir  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-manifest-consistency.py'
)
ROUTING_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-routing-decisions.py'
)

# The project-local skill tree this project's own build map routes as production
# (``.claude/skills/*.py`` on the Claude target — a single ``*`` spans ``/`` under
# fnmatch, so the glob covers the nested ``{skill}/scripts/`` layout).
PROJECT_LOCAL_PRODUCTION = [
    '.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py',
    '.claude/skills/sync-plugin-cache/scripts/sync.py',
    '.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py',
    '.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py',
    '.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py',
]


def _write_marshal(base: Path) -> None:
    """Stage a marshal.json whose ``build.map`` mirrors this project's real routes."""
    (base / 'marshal.json').write_text(
        json.dumps(
            {
                'build': {
                    'map': {
                        'python': [
                            {'glob': '.claude/skills/*.py', 'role': 'production', 'build_class': 'prod_compile'},
                            {'glob': 'marketplace/bundles/*.py', 'role': 'production', 'build_class': 'prod_compile'},
                            {'glob': 'test/*.py', 'role': 'test', 'build_class': 'test_run'},
                            {'glob': 'pyproject.toml', 'role': 'config', 'build_class': 'build_config_full'},
                        ]
                    }
                }
            }
        ),
        encoding='utf-8',
    )


def _serialize(body: dict) -> str:
    from toon_parser import serialize_toon

    return serialize_toon(body) + '\n'


def _setup(tmp_path, monkeypatch, manifest: dict, *, plan_id: str = 'oracle-plan') -> tuple[str, Path]:
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    (plan_dir / 'execution.toon').write_text(_serialize(manifest), encoding='utf-8')
    _write_marshal(base)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _write_diff(directory: Path, files: list[str], name: str = 'diff.txt') -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text('\n'.join(files) + ('\n' if files else ''), encoding='utf-8')
    return path


def _check(checks: list, name: str) -> dict:
    for entry in checks:
        if entry.get('name') == name:
            return entry
    raise AssertionError(f'check {name!r} absent from {[c.get("name") for c in checks]}')


# =============================================================================
# D5a — the project-local production tree survives the filter
# =============================================================================


class TestProjectLocalTreeSurvivesFilter:
    """``build.map`` routes the project-local skill tree production, so it is kept."""

    def test_multi_file_project_local_footprint_is_not_filtered(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        diff = _write_diff(tmp_path, PROJECT_LOCAL_PRODUCTION)

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        # Every supplied path is production per the oracle — none may be dropped.
        assert data['diff']['files_total'] == len(PROJECT_LOCAL_PRODUCTION)
        assert data['diff']['files_filtered'] == 0
        assert data['diff']['files_kept'] == len(PROJECT_LOCAL_PRODUCTION)

    def test_runtime_state_directory_is_still_bookkeeping(self, tmp_path, monkeypatch):
        """``.plan/`` stays bookkeeping — it appears in no build map."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(
            tmp_path,
            ['.plan/plans/oracle-plan/status.json', '.claude/skills/sync-plugin-cache/scripts/sync.py'],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['diff']['files_filtered'] == 1
        assert data['diff']['files_kept'] == 1

    def test_routing_check_sees_project_local_production(self, tmp_path, monkeypatch):
        """The SECOND site: ``footprint_has_production`` must see the same tree.

        A ``no_code_delta`` prune of ``finalize-step-simplify`` is a mis-prune when
        the realized footprint touched production code. Pre-fix the private prefix
        tuple hid the project-local tree, so the mis-prune reported ``pass``.
        """
        plan_id, plan_dir = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': ['verify:quality-gate']},
                # Both prunable steps absent → their predicates are re-evaluated.
                'phase_6': {'steps': ['push', 'create-pr']},
            },
        )
        # A readable decision log naming no removal mechanism: the predicate runs.
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, PROJECT_LOCAL_PRODUCTION)

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        simplify = [c for c in data['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify']
        assert simplify, data['mis_prune_checks']
        assert simplify[0]['status'] == 'fail', simplify[0]


    def test_unclassifiable_path_counts_as_production_for_the_mis_prune(self, tmp_path, monkeypatch):
        """Fail-closed: a path no route covers must not exonerate a ``no_code_delta`` prune.

        The oracle is unavailable here (no ``build.map``), so every path is
        unclassified. Answering "not production" would turn an unknown into an
        exoneration and report the mis-prune as a clean ``pass``.
        """
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
        (tmp_path / 'base' / 'marshal.json').unlink()
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'decision.log').write_text('[2026-04-17T10:00:00Z] [INFO] [aaaaaa] nothing\n', encoding='utf-8')
        diff = _write_diff(tmp_path, ['some/unrouted/module.rb'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'fail', simplify[0]

    def test_documentation_alone_does_not_count_as_production(self, tmp_path, monkeypatch):
        """The negative control — a docs-only footprint leaves the prune justified."""
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
        diff = _write_diff(tmp_path, ['doc/developer/build.adoc', '.plan/plans/oracle-plan/status.json'])

        result = run_script(
            ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        simplify = [
            c for c in result.toon()['mis_prune_checks'] if c['check'] == 'mis_prune:finalize-step-simplify'
        ]
        assert simplify[0]['status'] == 'pass', simplify[0]


# =============================================================================
# D5b — a reduced input set reports the reduction
# =============================================================================


class TestReducedInputSetReportsReduction:
    """A rule that saw only a fraction of the supplied footprint must say so."""

    def test_majority_filtered_footprint_never_yields_a_bare_pass(self, tmp_path, monkeypatch):
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                # M1 applies: empty verification_steps, not early-terminate.
                'phase_5': {'early_terminate': False, 'verification_steps': []},
                'phase_6': {'steps': ['push']},
            },
        )
        # Five of six paths are runtime-state bookkeeping; the survivor is a doc,
        # so M1 would otherwise emit a clean pass over one sixth of the input.
        diff = _write_diff(
            tmp_path,
            [
                '.plan/plans/oracle-plan/status.json',
                '.plan/plans/oracle-plan/tasks/TASK-001.json',
                '.plan/plans/oracle-plan/logs/decision.log',
                '.plan/plans/oracle-plan/execution.toon',
                '.plan/marshal.json',
                'doc/developer/build.adoc',
            ],
        )

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()

        docs_only = _check(data['checks'], 'docs_only_diff')
        assert docs_only['status'] == 'indeterminate', docs_only
        assert '5' in docs_only['message'] and '6' in docs_only['message'], docs_only['message']
        assert data['summary'].get('indeterminate') == 1, data['summary']

    def test_unreduced_footprint_still_passes_cleanly(self, tmp_path, monkeypatch):
        """The negative control — no reduction, so the ordinary pass survives."""
        plan_id, _ = _setup(
            tmp_path,
            monkeypatch,
            {
                'manifest_version': 1,
                'plan_id': 'oracle-plan',
                'phase_5': {'early_terminate': False, 'verification_steps': []},
                'phase_6': {'steps': ['push']},
            },
        )
        diff = _write_diff(tmp_path, ['doc/developer/build.adoc', 'doc/developer/marketplace-build.adoc'])

        result = run_script(
            MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', '--diff-file', str(diff)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert _check(data['checks'], 'docs_only_diff')['status'] == 'pass'
        assert data['summary'].get('indeterminate') == 0, data['summary']


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

    def test_both_checks_agree_on_test_ness(self, tmp_path, monkeypatch):
        """The two consumers share one classifier, so neither can disagree here."""
        import sys as _sys

        _sys.path.insert(0, str(MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts'))
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
        assert '2 diff entries were classified as bookkeeping' in cleanup['message'], cleanup['message']

        finding = [f for f in data['findings'] if f['code'] == 'branch_cleanup_without_changes']
        assert finding, data['findings']
        assert 'diff is empty' not in finding[0]['message'], finding[0]['message']


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
        assert set(manifest_mod._DROPPED_CATEGORIES) <= set(CATEGORIES)
        assert set(routing_mod._PRODUCTION_CATEGORIES) <= set(CATEGORIES)
        # And the two dispatches must not both claim the same category.
        assert not set(manifest_mod._DROPPED_CATEGORIES) & set(routing_mod._PRODUCTION_CATEGORIES)
