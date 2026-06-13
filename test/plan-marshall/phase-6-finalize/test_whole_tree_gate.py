#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the whole-tree completeness gate surfacer (``whole_tree_gate.py``).

The surfacer backs the ``default:finalize-step-whole-tree-gate`` finalize step.
It is the NOT-diff-scoped complement to the diff-scoped finalize gates: it
greps the ENTIRE ``marketplace/`` tree for survivors of deletions the plan was
meant to make, and compares the request's enumerated mandate against the diff's
touched files. The script makes no FAIL/PASS judgement — it only surfaces two
candidate lists for the LLM cognitive pass to classify.

These tests pin both surfacing halves AND the two whole-tree facet checks at
the unit and integration levels:

1. **Whole-tree survivor sweep** — a planted surviving reference to a deleted
   identifier is flagged as a ``survivors[]`` row, anchored on word boundaries,
   excluding ``.plan`` / ``__pycache__`` / vendored dirs and non-text suffixes.
2. **Intent-vs-diff scope check** — a request-named mandate file with zero
   representation in the diff's touched files is flagged as a ``mandate_gaps[]``
   row, while a represented mandate item is not.
3. **F1 doctor facet** — a changed plugin-doctor / plan-doctor analyzer in the
   changed set triggers the marketplace-wide doctor pass over the FULL
   ``marketplace/`` root (not the build-map-scoped subset).
4. **F2 sweep-test facet** — a changed ``whole_tree_sweep``-marked guard test in
   the changed set triggers the marked-guard re-run with the full scan root.

Negative coverage: a changed set that hits no facet trigger leaves both
facets ``triggered: False`` / ``ran: False`` / ``passed: True`` (vacuously
clean, no seam invoked), and the always-run survivor sweep is unchanged by the
facet machinery.

The ``scan`` entry point's ``diff_runner`` / ``diff_names_runner`` seams let the
integration tests drive the orchestration without a live git worktree, and the
``worktree_path`` override points the sweep at an isolated fixture tree. The
``run_facets`` ``doctor_runner`` / ``sweep_runner`` seams drive each facet's
structured result without a live doctor run or live pytest run.
"""

from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import MARKETPLACE_ROOT, PlanContext  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Load the script module directly (hyphenated skill dir -> importlib)
# ---------------------------------------------------------------------------

_GATE_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
    / 'whole_tree_gate.py'
)
_spec = importlib.util.spec_from_file_location('whole_tree_gate_under_test', str(_GATE_SCRIPT))
assert _spec is not None
gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gate)


# ---------------------------------------------------------------------------
# Fixture-tree builders
# ---------------------------------------------------------------------------


def _make_marketplace_tree(root: Path, files: dict[str, str]) -> Path:
    """Materialize a ``{root}/marketplace`` subtree from {rel_path: content}.

    ``rel_path`` is relative to the ``marketplace`` subdir. Parent directories
    are created as needed. Returns the worktree root (``root``) so the caller
    can pass it straight to ``sweep_survivors`` / ``scan``.
    """
    for rel, content in files.items():
        target = root / 'marketplace' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    return root


# ===========================================================================
# extract_deleted_identifiers
# ===========================================================================


class TestExtractDeletedIdentifiers:
    """The removed-line identifier extractor that seeds the survivor sweep."""

    def test_collects_symbol_from_removed_line(self):
        # Arrange
        diff = '-    result = compute_widget_total(items)\n'

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'compute_widget_total' in identifiers

    def test_ignores_old_file_header_lines(self):
        # Arrange — the unified-diff '---' header is not a content removal.
        diff = '--- a/marketplace/some_renamed_helper.py\n'

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'some_renamed_helper' not in identifiers

    def test_ignores_added_and_context_lines(self):
        # Arrange
        diff = (
            '+    surviving_added_symbol = 1\n'
            '     context_only_symbol = 2\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert identifiers == []

    def test_drops_short_identifiers(self):
        # Arrange — 'os' / 'id' are below the minimum identifier length.
        diff = '-import os as id\n'

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'os' not in identifiers
        assert 'id' not in identifiers

    def test_drops_stopwords(self):
        # Arrange — 'return', 'self', 'class' are language-keyword stopwords.
        diff = '-        return self.value  # class scope\n'

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'return' not in identifiers
        assert 'self' not in identifiers
        assert 'class' not in identifiers

    def test_result_is_sorted_and_deduplicated(self):
        # Arrange — zebra_handler appears twice, alpha_handler once.
        diff = (
            '-    zebra_handler()\n'
            '-    alpha_handler()\n'
            '-    zebra_handler()\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert identifiers == ['alpha_handler', 'zebra_handler']

    def test_empty_diff_yields_empty_list(self):
        # Arrange / Act
        identifiers = gate.extract_deleted_identifiers('')

        # Assert
        assert identifiers == []


# ===========================================================================
# sweep_survivors  (the whole-tree survivor sweep — mandated criterion #1)
# ===========================================================================


class TestSweepSurvivors:
    """Whole-tree grep for surviving references to deleted identifiers."""

    def test_flags_planted_surviving_reference(self, tmp_path):
        # Arrange — a deleted identifier still referenced in a marketplace file.
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/plan-marshall/skills/foo/SKILL.md':
                    'The deleted_widget_helper is still mentioned here.\n',
            },
        )

        # Act
        survivors = gate.sweep_survivors(root, ['deleted_widget_helper'])

        # Assert — the planted reference is surfaced with file/line/identifier.
        assert len(survivors) == 1
        row = survivors[0]
        assert row['identifier'] == 'deleted_widget_helper'
        assert row['line'] == 1
        assert row['file'] == 'marketplace/bundles/plan-marshall/skills/foo/SKILL.md'

    def test_word_boundary_anchored(self, tmp_path):
        # Arrange — 'foo_bar' deleted; 'foo_barbaz' must NOT match it.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/scripts/x.py': 'value = foo_barbaz()\n'},
        )

        # Act
        survivors = gate.sweep_survivors(root, ['foo_bar'])

        # Assert
        assert survivors == []

    def test_excludes_plan_and_pycache_dirs(self, tmp_path):
        # Arrange — survivors inside excluded dirs must not be reported.
        root = tmp_path
        (root / 'marketplace' / '.plan' / 'archived-plans').mkdir(parents=True)
        (root / 'marketplace' / '.plan' / 'archived-plans' / 'old.md').write_text(
            'lingering_symbol reference\n', encoding='utf-8'
        )
        (root / 'marketplace' / 'bundles' / '__pycache__').mkdir(parents=True)
        (root / 'marketplace' / 'bundles' / '__pycache__' / 'cached.py').write_text(
            'lingering_symbol = 1\n', encoding='utf-8'
        )

        # Act
        survivors = gate.sweep_survivors(root, ['lingering_symbol'])

        # Assert
        assert survivors == []

    def test_excludes_non_text_suffixes(self, tmp_path):
        # Arrange — a .png is outside the sweep suffix allow-list.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/diagram.png': 'binary_lookalike_symbol\n'},
        )

        # Act
        survivors = gate.sweep_survivors(root, ['binary_lookalike_symbol'])

        # Assert
        assert survivors == []

    def test_empty_identifier_list_short_circuits(self, tmp_path):
        # Arrange
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/x.py': 'anything = 1\n'},
        )

        # Act
        survivors = gate.sweep_survivors(root, [])

        # Assert
        assert survivors == []

    def test_missing_marketplace_subdir_yields_no_survivors(self, tmp_path):
        # Arrange — no marketplace/ subtree at all.

        # Act
        survivors = gate.sweep_survivors(tmp_path, ['some_symbol'])

        # Assert
        assert survivors == []

    def test_rows_sorted_by_file_line_identifier(self, tmp_path):
        # Arrange — two identifiers across two files in non-sorted plant order.
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/z_bundle/skills/s/late.py': 'beta_symbol = 1\n',
                'bundles/a_bundle/skills/s/early.py':
                    'alpha_symbol = 1\nbeta_symbol = 2\n',
            },
        )

        # Act
        survivors = gate.sweep_survivors(root, ['alpha_symbol', 'beta_symbol'])

        # Assert — sorted by (file, line, identifier).
        keys = [(r['file'], r['line'], r['identifier']) for r in survivors]
        assert keys == sorted(keys)
        assert keys[0][0].endswith('a_bundle/skills/s/early.py')


# ===========================================================================
# extract_mandate_items / _path_represented  (mandated criterion #2)
# ===========================================================================


class TestExtractMandateItems:
    """Intent-vs-diff scope check — request-named paths absent from the diff."""

    def test_flags_unrepresented_mandate_item(self):
        # Arrange — request names a file the diff never touched.
        request = 'The plan MUST delete marketplace/old/_legacy_parser.py entirely.\n'
        changed = ['marketplace/new/_modern_parser.py']

        # Act
        gaps = gate.extract_mandate_items(request, changed)

        # Assert
        assert 'marketplace/old/_legacy_parser.py' in gaps

    def test_represented_mandate_item_not_flagged(self):
        # Arrange — request names a path the diff carries verbatim.
        request = 'Edit marketplace/skills/foo/SKILL.md to add the gate.\n'
        changed = ['marketplace/skills/foo/SKILL.md']

        # Act
        gaps = gate.extract_mandate_items(request, changed)

        # Assert
        assert gaps == []

    def test_basename_in_request_matched_by_full_path_in_diff(self):
        # Arrange — request names a basename; diff carries the full repo-rel path.
        request = 'Remove the _plan_parsing.py helper.\n'
        changed = ['marketplace/bundles/plan-marshall/skills/x/scripts/_plan_parsing.py']

        # Act
        gaps = gate.extract_mandate_items(request, changed)

        # Assert
        assert gaps == []

    def test_no_named_paths_yields_no_gaps(self):
        # Arrange — prose with no path-shaped tokens.
        request = 'Generally tidy up the codebase and improve clarity.\n'
        changed = ['marketplace/x.py']

        # Act
        gaps = gate.extract_mandate_items(request, changed)

        # Assert
        assert gaps == []

    def test_gaps_sorted_and_deduplicated(self):
        # Arrange — same unrepresented path named twice plus another.
        request = (
            'Delete marketplace/z_late.py.\n'
            'Also delete marketplace/a_early.py.\n'
            'Confirm marketplace/z_late.py is gone.\n'
        )
        changed: list[str] = []

        # Act
        gaps = gate.extract_mandate_items(request, changed)

        # Assert
        assert gaps == ['marketplace/a_early.py', 'marketplace/z_late.py']


class TestPathRepresented:
    """The suffix-tolerant path-match predicate behind the mandate check."""

    def test_exact_match(self):
        assert gate._path_represented('marketplace/x.py', ['marketplace/x.py']) is True

    def test_suffix_match_basename_against_full_path(self):
        assert gate._path_represented(
            '_helper.py', ['marketplace/skills/s/scripts/_helper.py']
        ) is True

    def test_request_full_path_matched_by_diff_basename(self):
        # Request named a full repo-relative path; diff carries a shorter tail.
        assert gate._path_represented(
            'marketplace/skills/s/scripts/_helper.py', ['scripts/_helper.py']
        ) is True

    def test_no_match(self):
        assert gate._path_represented(
            'marketplace/a.py', ['marketplace/b.py']
        ) is False

    def test_leading_slash_normalized(self):
        assert gate._path_represented('/marketplace/x.py', ['marketplace/x.py']) is True


# ===========================================================================
# scan  (end-to-end orchestration via the diff seams)
# ===========================================================================


class TestScan:
    """The ``scan`` entry point wiring sweep + mandate via test seams."""

    def test_surfaces_survivor_and_mandate_gap_together(self, tmp_path):
        # Arrange — a deleted identifier that survives in the tree, AND a
        # request-named mandate file the diff never touches.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'orphaned_helper still referenced\n'},
        )
        diff_text = '-    orphaned_helper()\n'
        changed_files = ['marketplace/bundles/b/skills/s/SKILL.md']
        request = 'The plan MUST delete marketplace/old/_unrepresented.py.\n'

        with PlanContext(plan_id='wtg-scan-both') as ctx:
            (ctx.plan_dir / 'request.md').write_text(request, encoding='utf-8')

            # Act
            result = gate.scan(
                'wtg-scan-both',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
            )

        # Assert — both candidate lists are populated.
        assert result['status'] == 'success'
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'
        assert result['mandate_gap_count'] == 1
        assert result['mandate_gaps'][0]['mandate_item'] == 'marketplace/old/_unrepresented.py'

    def test_clean_plan_surfaces_nothing(self, tmp_path):
        # Arrange — deleted identifier has no survivors; mandate file IS touched.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'no stale references here at all\n'},
        )
        diff_text = '-    fully_removed_symbol()\n'
        changed_files = ['marketplace/old/_represented.py']
        request = 'Delete marketplace/old/_represented.py.\n'

        with PlanContext(plan_id='wtg-scan-clean') as ctx:
            (ctx.plan_dir / 'request.md').write_text(request, encoding='utf-8')

            # Act
            result = gate.scan(
                'wtg-scan-clean',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
            )

        # Assert
        assert result['status'] == 'success'
        assert result['survivor_count'] == 0
        assert result['mandate_gap_count'] == 0
        assert result['deleted_identifier_count'] == 1

    def test_base_ref_override_passed_through_to_seams(self, tmp_path):
        # Arrange — capture the base_ref the seams receive.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})
        seen: dict[str, str] = {}

        def _diff(_wt, ref):
            seen['diff'] = ref
            return ''

        def _names(_wt, ref):
            seen['names'] = ref
            return []

        with PlanContext(plan_id='wtg-scan-ref') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # Act
            gate.scan(
                'wtg-scan-ref',
                worktree_path=str(root),
                base_ref='develop',
                diff_runner=_diff,
                diff_names_runner=_names,
            )

        # Assert
        assert seen['diff'] == 'develop'
        assert seen['names'] == 'develop'

    def test_missing_request_yields_no_mandate_gaps(self, tmp_path):
        # Arrange — no request.md written; the resolver returns empty text.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})

        with PlanContext(plan_id='wtg-scan-noreq'):
            # Act — deliberately do NOT write request.md.
            result = gate.scan(
                'wtg-scan-noreq',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [],
            )

        # Assert
        assert result['status'] == 'success'
        assert result['mandate_gap_count'] == 0


# ===========================================================================
# run_facets  (the two whole-tree facet checks — mandated criteria #3/#4)
# ===========================================================================
#
# The F1 doctor analyzer paths live under ``marketplace/bundles/**``; the
# fixtures below pick paths that isolate the facet under test wherever a
# single-facet assertion is intended.

# Representative paths matching exactly one facet trigger category in isolation
# of the others.
_DOCTOR_TRIGGER_PATH = (
    'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/'
    'scripts/_analyze_rule.py'
)
_PLAN_DOCTOR_TRIGGER_PATH = (
    'marketplace/bundles/plan-marshall/skills/plan-doctor/scripts/plan_doctor.py'
)
_SWEEP_TEST_TRIGGER_PATH = 'test/plan-marshall/phase-6-finalize/test_invariant_sweep.py'
# A non-trigger path: a docs file under a non-bundle, non-target, non-test dir.
_NO_TRIGGER_PATH = 'doc/developer/build.adoc'


def _passing_doctor(_wt):
    return {'passed': True, 'finding_count': 0, 'summary': 'doctor seam: clean'}


def _passing_sweep(_wt):
    return {'passed': True, 'summary': 'sweep seam: clean'}


class TestRunFacetsDoctor:
    """F1 — marketplace-wide static-analysis sweep, gated on the doctor trigger."""

    def test_doctor_analyzer_in_changed_set_runs_doctor_facet(self, tmp_path):
        # Arrange — a changed plugin-doctor analyzer; record the worktree root
        # the seam receives so we can assert it is the FULL marketplace root.
        seen: dict[str, Path] = {}

        def _doctor(wt):
            seen['root'] = wt
            return {'passed': True, 'finding_count': 0, 'summary': 'ran'}

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_doctor,
            sweep_runner=_passing_sweep,
        )

        # Assert — the doctor facet fired and the seam saw the worktree root
        # (the full marketplace/ scan root, NOT a build-map-scoped subset).
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert facets['doctor']['passed'] is True
        assert facets['doctor']['summary'] == 'ran'
        assert seen['root'] == tmp_path

    def test_plan_doctor_path_also_triggers_doctor_facet(self, tmp_path):
        # Arrange — the plan-doctor trigger glob is the second doctor category.
        calls: list[Path] = []

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_PLAN_DOCTOR_TRIGGER_PATH],
            doctor_runner=lambda wt: (calls.append(wt) or _passing_doctor(wt)),
            sweep_runner=_passing_sweep,
        )

        # Assert
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert calls == [tmp_path]

    def test_doctor_seam_failure_is_surfaced_not_raised(self, tmp_path):
        # Arrange — the doctor seam reports findings (passed: False). This is a
        # SURFACED finding, not an error — the facet still ran.
        def _failing_doctor(_wt):
            return {
                'passed': False,
                'finding_count': 3,
                'summary': 'three rule violations',
            }

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_failing_doctor,
            sweep_runner=_passing_sweep,
        )

        # Assert — the surfacer makes no verdict; passed: False is just surfaced.
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert facets['doctor']['passed'] is False
        assert facets['doctor']['finding_count'] == 3

    def test_doctor_seam_runtime_error_marks_ran_false(self, tmp_path):
        # Arrange — an infrastructure failure inside the seam must NOT be
        # silently treated as clean: ran: False, passed: False, error captured.
        def _exploding_doctor(_wt):
            raise RuntimeError('plugin-doctor could not be invoked')

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_exploding_doctor,
            sweep_runner=_passing_sweep,
        )

        # Assert
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is False
        assert facets['doctor']['passed'] is False
        assert 'could not be invoked' in facets['doctor']['error']


class TestRunFacetsSweepTest:
    """F2 — whole-tree grep-sweep guard re-run, gated on the sweep-test trigger."""

    def test_sweep_guard_test_in_changed_set_runs_sweep_facet(self, tmp_path):
        # Arrange — a changed whole-tree grep-sweep guard test; capture the
        # worktree root the seam receives (the full scan root).
        seen: dict[str, Path] = {}

        def _sweep(wt):
            seen['root'] = wt
            return {'passed': True, 'summary': 'guard tests passed'}

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_sweep,
        )

        # Assert — the sweep-test facet fired with the full tree as scan root.
        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is True
        assert facets['sweep_test']['passed'] is True
        assert seen['root'] == tmp_path

    def test_sweep_seam_failure_is_surfaced(self, tmp_path):
        # Arrange — the marked guard tests fail (passed: False) — surfaced.
        def _failing_sweep(_wt):
            return {'passed': False, 'summary': 'a guard test failed'}

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_failing_sweep,
        )

        # Assert
        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is True
        assert facets['sweep_test']['passed'] is False

    def test_sweep_seam_runtime_error_marks_ran_false(self, tmp_path):
        # Arrange
        def _exploding_sweep(_wt):
            raise RuntimeError('pytest -m whole_tree_sweep could not be invoked')

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_exploding_sweep,
        )

        # Assert
        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is False
        assert facets['sweep_test']['passed'] is False
        assert 'could not be invoked' in facets['sweep_test']['error']


class TestRunFacetsNoTrigger:
    """Negative coverage — no facet fires, no seam runs, all vacuously clean."""

    def test_no_trigger_leaves_all_facets_untriggered_and_clean(self, tmp_path):
        # Arrange — a changed set that hits no facet trigger glob, plus failing
        # seams that MUST NOT be invoked (their failure would prove a leak).
        def _must_not_run_doctor(_wt):
            raise AssertionError('doctor seam invoked without a doctor trigger')

        def _must_not_run_sweep(_wt):
            raise AssertionError('sweep seam invoked without a sweep-test trigger')

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_NO_TRIGGER_PATH],
            doctor_runner=_must_not_run_doctor,
            sweep_runner=_must_not_run_sweep,
        )

        # Assert — every facet is untriggered, un-run, and vacuously clean. No
        # seam raised, proving none was invoked.
        for name in ('doctor', 'sweep_test'):
            assert facets[name]['triggered'] is False, name
            assert facets[name]['ran'] is False, name
            assert facets[name]['passed'] is True, name

    def test_empty_changed_set_fires_no_facet(self, tmp_path):
        # Arrange / Act — an empty changed set (pre-diff shape) fires nothing.
        facets = gate.run_facets(
            tmp_path,
            [],
            doctor_runner=lambda _wt: pytest.fail('doctor must not run'),
            sweep_runner=lambda _wt: pytest.fail('sweep must not run'),
        )

        # Assert
        assert facets['doctor']['triggered'] is False
        assert facets['sweep_test']['triggered'] is False

    def test_one_facet_fires_others_stay_untriggered(self, tmp_path):
        # Arrange — only the sweep-test trigger is in the changed set; the
        # doctor seam MUST NOT run.
        def _must_not_run(_wt):
            raise AssertionError('unrelated facet seam invoked')

        # Act
        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_must_not_run,
            sweep_runner=_passing_sweep,
        )

        # Assert — exactly one facet fired.
        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is True
        assert facets['doctor']['triggered'] is False
        assert facets['doctor']['ran'] is False


# ===========================================================================
# scan + facets  (full-gate integration covering all three facets)
# ===========================================================================


class TestScanWithFacets:
    """The ``scan`` entry point wires ``run_facets`` and folds the facet block
    into the return TOON, and the always-run survivor sweep is unchanged by it."""

    def test_full_gate_covers_both_facets(self, tmp_path):
        # Arrange — a changed set that hits BOTH facet triggers at once,
        # with a planted survivor proving the sweep half still runs alongside.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'orphaned_helper still referenced\n'},
        )
        diff_text = '-    orphaned_helper()\n'
        changed_files = [
            _DOCTOR_TRIGGER_PATH,       # F1 doctor
            _SWEEP_TEST_TRIGGER_PATH,   # F2 sweep-test
        ]

        with PlanContext(plan_id='wtg-scan-facets-all') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # Act
            result = gate.scan(
                'wtg-scan-facets-all',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
                doctor_runner=_passing_doctor,
                sweep_runner=_passing_sweep,
            )

        # Assert — both facets ran AND the survivor sweep is unchanged.
        assert result['status'] == 'success'
        facets = result['facets']
        assert facets['doctor']['ran'] is True
        assert facets['sweep_test']['ran'] is True
        # The always-run survivor sweep still surfaced the planted reference.
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'

    def test_no_facet_trigger_leaves_survivor_sweep_unchanged(self, tmp_path):
        # Arrange — a changed set hitting NO facet trigger; the survivor sweep
        # half must behave exactly as in the facet-free TestScan cases.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'orphaned_helper still referenced\n'},
        )
        diff_text = '-    orphaned_helper()\n'
        changed_files = [_NO_TRIGGER_PATH]

        with PlanContext(plan_id='wtg-scan-facets-none') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # Act
            result = gate.scan(
                'wtg-scan-facets-none',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
                doctor_runner=lambda _wt: pytest.fail('doctor must not run'),
                sweep_runner=lambda _wt: pytest.fail('sweep must not run'),
            )

        # Assert — no facet fired, yet the survivor sweep is identical.
        assert result['status'] == 'success'
        assert result['facets']['doctor']['triggered'] is False
        assert result['facets']['sweep_test']['triggered'] is False
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'

    def test_scan_default_facet_seams_resolve_without_override(self, tmp_path):
        # Arrange — when no facet runners are passed AND no trigger fires, scan
        # must not invoke the real (live) facet seams at all.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})

        with PlanContext(plan_id='wtg-scan-facets-default') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # Act — no facet trigger in the changed set, so the real seams are
            # never reached even though no override was supplied.
            result = gate.scan(
                'wtg-scan-facets-default',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [_NO_TRIGGER_PATH],
            )

        # Assert — every facet is untriggered/clean with the real defaults wired.
        assert result['status'] == 'success'
        for name in ('doctor', 'sweep_test'):
            assert result['facets'][name]['triggered'] is False
            assert result['facets'][name]['passed'] is True


# ===========================================================================
# cmd_scan  (CLI wrapper error propagation)
# ===========================================================================


class TestCmdScan:
    """The CLI wrapper translating a git-seam RuntimeError to an error TOON."""

    def test_git_failure_surfaces_error_toon(self, tmp_path, capsys, monkeypatch):
        # Arrange — force the real diff runner to raise, simulating a git failure.
        def _boom(_wt, _ref):
            raise RuntimeError('git diff main...HEAD failed: fatal: bad revision')

        monkeypatch.setattr(gate, '_run_git_diff', _boom)

        with PlanContext(plan_id='wtg-cmd-err'):
            args = Namespace(
                plan_id='wtg-cmd-err',
                worktree_path=str(tmp_path),
                base_ref='main',
            )

            # Act
            rc = gate.cmd_scan(args)

        # Assert
        out = capsys.readouterr().out
        assert rc == 1
        assert 'status: error' in out
        assert 'bad revision' in out

    def test_success_emits_status_success_and_returns_zero(self, tmp_path, capsys, monkeypatch):
        # Arrange — both seams succeed with no survivors / no gaps.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})
        monkeypatch.setattr(gate, '_run_git_diff', lambda _wt, _ref: '')
        monkeypatch.setattr(gate, '_run_git_diff_names', lambda _wt, _ref: [])

        with PlanContext(plan_id='wtg-cmd-ok') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')
            args = Namespace(
                plan_id='wtg-cmd-ok',
                worktree_path=str(root),
                base_ref='main',
            )

            # Act
            rc = gate.cmd_scan(args)

        # Assert
        out = capsys.readouterr().out
        assert rc == 0
        assert 'status: success' in out


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
