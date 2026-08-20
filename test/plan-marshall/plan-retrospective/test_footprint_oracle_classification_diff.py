# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the oracle-backed footprint classification shared by the two checks.

Its sections, in order:

* D5c — rule M3 fires on the composer's real step-list shape
* D5d — the documented relative invocation equals the absolute one
* The reduction report's membership is derived, not mirrored
"""


from __future__ import annotations

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
