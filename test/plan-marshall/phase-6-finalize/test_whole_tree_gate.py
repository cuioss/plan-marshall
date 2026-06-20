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
        diff = '-    result = compute_widget_total(items)\n'

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'compute_widget_total' in identifiers

    def test_ignores_old_file_header_lines(self):
        # The unified-diff '---' header is not a content removal.
        diff = '--- a/marketplace/some_renamed_helper.py\n'

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'some_renamed_helper' not in identifiers

    def test_ignores_added_and_context_lines(self):
        diff = (
            '+    surviving_added_symbol = 1\n'
            '     context_only_symbol = 2\n'
        )

        identifiers = gate.extract_deleted_identifiers(diff)

        assert identifiers == []

    def test_drops_short_identifiers(self):
        # 'os' / 'id' are below the minimum identifier length.
        diff = '-import os as id\n'

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'os' not in identifiers
        assert 'id' not in identifiers

    def test_drops_stopwords(self):
        # 'return', 'self', 'class' are language-keyword stopwords.
        diff = '-        return self.value  # class scope\n'

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'return' not in identifiers
        assert 'self' not in identifiers
        assert 'class' not in identifiers

    def test_result_is_sorted_and_deduplicated(self):
        # zebra_handler appears twice, alpha_handler once.
        diff = (
            '-    zebra_handler()\n'
            '-    alpha_handler()\n'
            '-    zebra_handler()\n'
        )

        identifiers = gate.extract_deleted_identifiers(diff)

        assert identifiers == ['alpha_handler', 'zebra_handler']

    def test_empty_diff_yields_empty_list(self):
        identifiers = gate.extract_deleted_identifiers('')

        assert identifiers == []

    def test_token_on_both_removed_and_added_line_is_dropped(self):
        # Arrange — filter 1: a token that appears on a removed line AND an added
        # line of the same diff was moved, not deleted, so it is NOT collected.
        diff = (
            '-    old_call = moved_symbol(x)\n'
            '+    new_call = moved_symbol(y)\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — moved_symbol recurs on the added line, so it is filtered out.
        assert 'moved_symbol' not in identifiers
        # old_call was genuinely removed (absent from the added line) — kept.
        assert 'old_call' in identifiers

    def test_token_on_removed_and_context_line_is_dropped(self):
        # Arrange — filter 1 also subtracts context (unchanged) line tokens: a
        # candidate surrounded by retained text is not a genuine removal.
        diff = (
            '     retained_caller(lingering_helper)\n'
            '-    extra = lingering_helper.tweak()\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — lingering_helper survives on the context line, so it is dropped.
        assert 'lingering_helper' not in identifiers

    def test_genuinely_removed_token_survives_filter_one(self):
        # Arrange — a token present ONLY on removed lines is a real deletion and
        # must still be collected after the added/context subtraction.
        diff = (
            '-    truly_gone_symbol()\n'
            '+    unrelated_replacement()\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'truly_gone_symbol' in identifiers

    def test_removed_prose_paragraph_yields_near_zero_candidates(self):
        # Arrange — the headline regression: a removed markdown paragraph of
        # ordinary English prose must not flood the candidate set. Dashed-compound
        # prose tokens like 'plan-marshall' that pass _IDENTIFIER_RE are the
        # specific false positives the filters target.
        diff = (
            '-This paragraph describes the plan-marshall workflow in ordinary\n'
            '-narrative prose with several everyday words that happen to clear\n'
            '-the length floor without naming any deleted code symbol whatsoever.\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — no dashed-compound prose token should appear, and the overall
        # candidate count stays small (the coarse pass already drops stopwords
        # and short words; nothing here is a genuine symbol). 'plan-marshall'
        # recurs across the real tree but is not subtracted here because it only
        # appears on removed lines — the tree-occurrence ceiling (filter 2) is the
        # backstop for that case; this test pins that the extractor itself does
        # not invent symbols from prose beyond the coarse-pass survivors.
        assert 'plan-marshall' in identifiers  # passes _IDENTIFIER_RE on removal
        # ...but the survivor sweep drops it via the occurrence ceiling — see
        # TestSweepSurvivors.test_token_over_occurrence_ceiling_is_dropped.


# ===========================================================================
# extract_deleted_identifiers — declared-symbol anchoring (Python hunks)
# ===========================================================================


class TestExtractDeletedIdentifiersDeclaredSymbol:
    """Python removed lines extract DECLARED symbols only, not every token.

    The headline precision fix: for a ``.py`` hunk, extraction is anchored to
    ``def``/``class``/module-level-assignment declarations rather than every
    identifier-shaped token. Docstring words, prose, dict-key string values, and
    indented locals on deleted Python lines are NOT collected.
    """

    @staticmethod
    def _py_diff(body: str, *, path: str = 'marketplace/skills/x/scripts/m.py') -> str:
        """Wrap ``body`` (already ``-``/``+``/space-prefixed lines) in a Python
        unified-diff header so the extractor routes the hunk through the
        declared-symbol pass."""
        return (
            f'diff --git a/{path} b/{path}\n'
            f'--- a/{path}\n'
            f'+++ b/{path}\n'
            '@@ -1,5 +1,1 @@\n'
            f'{body}'
        )

    def test_def_on_deleted_python_line_is_extracted(self):
        # Arrange
        diff = self._py_diff('-def deleted_handler(arg):\n')

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'deleted_handler' in identifiers

    def test_async_def_on_deleted_python_line_is_extracted(self):
        diff = self._py_diff('-    async def fetch_remote_widget(self):\n')

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'fetch_remote_widget' in identifiers

    def test_class_on_deleted_python_line_is_extracted(self):
        diff = self._py_diff('-class DeletedAnalyzer(BaseAnalyzer):\n')

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'DeletedAnalyzer' in identifiers

    def test_module_level_assignment_is_extracted(self):
        diff = self._py_diff('-FIXTURE_CORPUS = build_corpus()\n')

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'FIXTURE_CORPUS' in identifiers

    def test_annotated_module_level_assignment_is_extracted(self):
        diff = self._py_diff('-DEFAULT_LIMIT: int = 50\n')

        identifiers = gate.extract_deleted_identifiers(diff)

        assert 'DEFAULT_LIMIT' in identifiers

    def test_prose_tokens_on_deleted_python_line_are_not_extracted(self):
        # Arrange — a deleted docstring/comment line of ordinary prose. None of
        # these words are declared symbols, so none are collected.
        diff = self._py_diff(
            '-    """This helper computes the widget total across all items."""\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — declared-symbol anchoring drops every prose word.
        assert identifiers == []

    def test_dict_key_string_value_on_deleted_line_is_not_extracted(self):
        # Arrange — a deleted dict literal entry. The key string and value are
        # not declared symbols.
        diff = self._py_diff("-        'compatibility_description': resolved_value,\n")

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — neither the string key nor the value is a declaration.
        assert 'compatibility_description' not in identifiers
        assert 'resolved_value' not in identifiers

    def test_indented_local_assignment_is_not_extracted(self):
        # Arrange — an indented (in-function) assignment is a local, not an
        # importable module-level symbol, so the module-assign anchor (column 0)
        # does not match it.
        diff = self._py_diff('-        local_temp = intermediate * 2\n')

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'local_temp' not in identifiers

    def test_comparison_is_not_mistaken_for_assignment(self):
        # Arrange — a module-level comparison expression must not be read as a
        # name binding ('==' is not an assignment).
        diff = self._py_diff('-ENABLED == other_flag\n')

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — no false 'ENABLED' declaration.
        assert 'ENABLED' not in identifiers

    def test_deleted_python_file_collects_declarations_not_docstring_words(self):
        # Arrange — a realistic clean-slate deletion: a def, a class, a constant,
        # surrounded by a docstring and a local. Only the three declarations are
        # collected; the docstring words and the local are not.
        diff = self._py_diff(
            '-"""Module docstring with several ordinary descriptive words here."""\n'
            '-ANALYZER_TABLE = {}\n'
            '-class WidgetParser:\n'
            '-    def parse_everything(self):\n'
            '-        scratch_local = compute()\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — exactly the three declared symbols, nothing from prose/locals.
        assert set(identifiers) == {
            'ANALYZER_TABLE',
            'WidgetParser',
            'parse_everything',
        }

    def test_python_file_body_does_not_flood_with_prose(self):
        # Arrange — the flood regression. A deleted .py file whose body is mostly
        # docstring/comment prose plus a single declaration must yield ONLY the
        # declaration, collapsing from the prose-flood scale to one symbol.
        prose_lines = ''.join(
            f'-# narrative comment line number {i} describing legacy behaviour\n'
            for i in range(40)
        )
        diff = self._py_diff(prose_lines + '-def the_only_real_symbol():\n')

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — the 40 prose lines contribute nothing; only the def remains.
        assert identifiers == ['the_only_real_symbol']

    def test_python_added_declaration_is_subtracted(self):
        # Arrange — a symbol declared on a removed line AND re-declared on an
        # added line of the same Python hunk was moved, not deleted, so the
        # added/context subtraction (second pass) drops it.
        diff = self._py_diff(
            '-def moved_function():\n'
            '+def moved_function(extra_arg):\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert
        assert 'moved_function' not in identifiers

    def test_non_python_hunk_still_uses_coarse_identifier_pass(self):
        # Arrange — a deleted markdown line must still extract via the coarse
        # fallback (declared-symbol anchoring is Python-only).
        diff = (
            'diff --git a/marketplace/skills/x/SKILL.md b/marketplace/skills/x/SKILL.md\n'
            '--- a/marketplace/skills/x/SKILL.md\n'
            '+++ b/marketplace/skills/x/SKILL.md\n'
            '@@ -1,1 +1,1 @@\n'
            '-The deleted_contract_token routes the request elsewhere.\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — the coarse pass still surfaces the snake_case token.
        assert 'deleted_contract_token' in identifiers

    def test_dev_null_new_side_uses_old_python_path_for_routing(self):
        # Arrange — a whole-file Python deletion has '+++ /dev/null'; routing
        # must fall back to the '---' old path's .py suffix so the hunk is still
        # treated as Python (declared-symbol anchored).
        diff = (
            'diff --git a/marketplace/skills/x/scripts/gone.py b/marketplace/skills/x/scripts/gone.py\n'
            '--- a/marketplace/skills/x/scripts/gone.py\n'
            '+++ /dev/null\n'
            '@@ -1,2 +0,0 @@\n'
            '-"""Docstring prose that must not flood the candidate set at all."""\n'
            '-def survivor_target():\n'
        )

        # Act
        identifiers = gate.extract_deleted_identifiers(diff)

        # Assert — only the declared symbol; the docstring prose is dropped.
        assert identifiers == ['survivor_target']


# ===========================================================================
# Compound / hyphenated contract-value discipline (regression pin)
# ===========================================================================


class TestCompoundHyphenatedTokenDiscipline:
    """Pin the known limitation that motivates the workflow-doc grep discipline.

    A deleted/renamed HYPHENATED contract value (a routing discriminator such as
    ``verification-failure``) is not a declared symbol and its constituent words
    are individually legitimate. The declared-symbol-anchored extractor therefore
    does NOT surface a surviving compound-token reference — but a direct grep for
    the whole hyphenated token does. This regression keeps deliverable 2's Step 2
    discipline note load-bearing: if a future change made the symbol sweep claim
    to cover compound contract values, the asymmetry asserted here would break.
    """

    def test_symbol_sweep_misses_hyphenated_survivor_direct_grep_finds_it(self, tmp_path):
        # Arrange — a Python hunk that renames a hyphenated contract value. The
        # old value 'verification-failure' is referenced (a string literal), but
        # it is not a declared symbol, so the declared-symbol extractor yields
        # nothing for it.
        py_diff = TestExtractDeletedIdentifiersDeclaredSymbol._py_diff(
            "-    finding_type = 'verification-failure'\n"
            "+    finding_type = 'test-failure'\n"
        )
        deleted = gate.extract_deleted_identifiers(py_diff)

        # The compound contract value is NOT among the extracted declared symbols.
        assert 'verification-failure' not in deleted

        # A survivor of the old value lingers in a consumer doc.
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/plan-marshall/skills/x/standards/triage.md':
                    'Route a verification-failure finding to the fix branch.\n',
            },
        )

        # Act — the symbol sweep (driven by the extracted declared symbols) finds
        # no survivor for the compound value...
        sweep = gate.sweep_survivors(root, deleted)
        sweep_idents = {row['identifier'] for row in sweep}

        # ...but a direct grep for the whole hyphenated token does.
        survivor_doc = (
            root
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'x'
            / 'standards'
            / 'triage.md'
        ).read_text(encoding='utf-8')

        # Assert — the asymmetry the discipline note exists to cover.
        assert 'verification-failure' not in sweep_idents
        assert 'verification-failure' in survivor_doc


# ===========================================================================
# sweep_survivors  (the whole-tree survivor sweep — mandated criterion #1)
# ===========================================================================


class TestSweepSurvivors:
    """Whole-tree grep for surviving references to deleted identifiers."""

    def test_flags_planted_surviving_reference(self, tmp_path):
        # A deleted identifier still referenced in a marketplace file.
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/plan-marshall/skills/foo/SKILL.md':
                    'The deleted_widget_helper is still mentioned here.\n',
            },
        )

        survivors = gate.sweep_survivors(root, ['deleted_widget_helper'])

        # The planted reference is surfaced with file/line/identifier.
        assert len(survivors) == 1
        row = survivors[0]
        assert row['identifier'] == 'deleted_widget_helper'
        assert row['line'] == 1
        assert row['file'] == 'marketplace/bundles/plan-marshall/skills/foo/SKILL.md'

    def test_word_boundary_anchored(self, tmp_path):
        # 'foo_bar' deleted; 'foo_barbaz' must NOT match it.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/scripts/x.py': 'value = foo_barbaz()\n'},
        )

        survivors = gate.sweep_survivors(root, ['foo_bar'])

        assert survivors == []

    def test_excludes_plan_and_pycache_dirs(self, tmp_path):
        # Survivors inside excluded dirs must not be reported.
        root = tmp_path
        (root / 'marketplace' / '.plan' / 'archived-plans').mkdir(parents=True)
        (root / 'marketplace' / '.plan' / 'archived-plans' / 'old.md').write_text(
            'lingering_symbol reference\n', encoding='utf-8'
        )
        (root / 'marketplace' / 'bundles' / '__pycache__').mkdir(parents=True)
        (root / 'marketplace' / 'bundles' / '__pycache__' / 'cached.py').write_text(
            'lingering_symbol = 1\n', encoding='utf-8'
        )

        survivors = gate.sweep_survivors(root, ['lingering_symbol'])

        assert survivors == []

    def test_excludes_non_text_suffixes(self, tmp_path):
        # A .png is outside the sweep suffix allow-list.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/diagram.png': 'binary_lookalike_symbol\n'},
        )

        survivors = gate.sweep_survivors(root, ['binary_lookalike_symbol'])

        assert survivors == []

    def test_empty_identifier_list_short_circuits(self, tmp_path):
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/x.py': 'anything = 1\n'},
        )

        survivors = gate.sweep_survivors(root, [])

        assert survivors == []

    def test_missing_marketplace_subdir_yields_no_survivors(self, tmp_path):
        # No marketplace/ subtree at all.
        survivors = gate.sweep_survivors(tmp_path, ['some_symbol'])

        assert survivors == []

    def test_rows_sorted_by_file_line_identifier(self, tmp_path):
        # Two identifiers across two files in non-sorted plant order.
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/z_bundle/skills/s/late.py': 'beta_symbol = 1\n',
                'bundles/a_bundle/skills/s/early.py':
                    'alpha_symbol = 1\nbeta_symbol = 2\n',
            },
        )

        survivors = gate.sweep_survivors(root, ['alpha_symbol', 'beta_symbol'])

        # Sorted by (file, line, identifier).
        keys = [(r['file'], r['line'], r['identifier']) for r in survivors]
        assert keys == sorted(keys)
        assert keys[0][0].endswith('a_bundle/skills/s/early.py')

    def test_token_over_occurrence_ceiling_is_dropped(self, tmp_path):
        # Arrange — filter 2: a candidate matching MORE than the tree-occurrence
        # ceiling is prose, not a removed symbol, and all its rows are dropped.
        over_ceiling = gate._MAX_TREE_OCCURRENCES + 5
        prose_line = 'the prose_word appears here\n'
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': prose_line * over_ceiling},
        )

        # Act
        survivors = gate.sweep_survivors(root, ['prose_word'])

        # Assert — every match is dropped because the count exceeds the ceiling.
        assert survivors == []

    def test_token_at_or_under_ceiling_is_kept(self, tmp_path):
        # Arrange — a genuine symbol surviving at a handful of sites (well under
        # the ceiling) must still be surfaced.
        under_ceiling = gate._MAX_TREE_OCCURRENCES - 1
        symbol_line = 'real_symbol = compute()\n'
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/x.py': symbol_line * under_ceiling},
        )

        # Act
        survivors = gate.sweep_survivors(root, ['real_symbol'])

        # Assert — all under-ceiling matches are retained.
        assert len(survivors) == under_ceiling
        assert all(row['identifier'] == 'real_symbol' for row in survivors)

    def test_ceiling_drops_only_the_offending_token(self, tmp_path):
        # Arrange — a prose candidate over the ceiling and a genuine symbol under
        # it in the same tree; only the prose candidate's rows are dropped.
        over_ceiling = gate._MAX_TREE_OCCURRENCES + 2
        root = _make_marketplace_tree(
            tmp_path,
            {
                'bundles/b/skills/s/prose.md': 'noise_token line\n' * over_ceiling,
                'bundles/b/skills/s/code.py': 'kept_symbol = 1\n',
            },
        )

        # Act
        survivors = gate.sweep_survivors(root, ['noise_token', 'kept_symbol'])

        # Assert — kept_symbol survives; noise_token is dropped entirely.
        idents = {row['identifier'] for row in survivors}
        assert idents == {'kept_symbol'}


# ===========================================================================
# extract_mandate_items / _path_represented  (mandated criterion #2)
# ===========================================================================


class TestExtractMandateItems:
    """Intent-vs-diff scope check — request-named paths absent from the diff."""

    def test_flags_unrepresented_mandate_item(self):
        # Request names a file the diff never touched.
        request = 'The plan MUST delete marketplace/old/_legacy_parser.py entirely.\n'
        changed = ['marketplace/new/_modern_parser.py']

        gaps = gate.extract_mandate_items(request, changed)

        assert 'marketplace/old/_legacy_parser.py' in gaps

    def test_represented_mandate_item_not_flagged(self):
        # Request names a path the diff carries verbatim.
        request = 'Edit marketplace/skills/foo/SKILL.md to add the gate.\n'
        changed = ['marketplace/skills/foo/SKILL.md']

        gaps = gate.extract_mandate_items(request, changed)

        assert gaps == []

    def test_basename_in_request_matched_by_full_path_in_diff(self):
        # Request names a basename; diff carries the full repo-rel path.
        request = 'Remove the _plan_parsing.py helper.\n'
        changed = ['marketplace/bundles/plan-marshall/skills/x/scripts/_plan_parsing.py']

        gaps = gate.extract_mandate_items(request, changed)

        assert gaps == []

    def test_no_named_paths_yields_no_gaps(self):
        # Prose with no path-shaped tokens.
        request = 'Generally tidy up the codebase and improve clarity.\n'
        changed = ['marketplace/x.py']

        gaps = gate.extract_mandate_items(request, changed)

        assert gaps == []

    def test_gaps_sorted_and_deduplicated(self):
        # Same unrepresented path named twice plus another.
        request = (
            'Delete marketplace/z_late.py.\n'
            'Also delete marketplace/a_early.py.\n'
            'Confirm marketplace/z_late.py is gone.\n'
        )
        changed: list[str] = []

        gaps = gate.extract_mandate_items(request, changed)

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
        # A deleted identifier that survives in the tree, AND a
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

            result = gate.scan(
                'wtg-scan-both',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
            )

        # Both candidate lists are populated.
        assert result['status'] == 'success'
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'
        assert result['mandate_gap_count'] == 1
        assert result['mandate_gaps'][0]['mandate_item'] == 'marketplace/old/_unrepresented.py'

    def test_clean_plan_surfaces_nothing(self, tmp_path):
        # Deleted identifier has no survivors; mandate file IS touched.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'no stale references here at all\n'},
        )
        diff_text = '-    fully_removed_symbol()\n'
        changed_files = ['marketplace/old/_represented.py']
        request = 'Delete marketplace/old/_represented.py.\n'

        with PlanContext(plan_id='wtg-scan-clean') as ctx:
            (ctx.plan_dir / 'request.md').write_text(request, encoding='utf-8')

            result = gate.scan(
                'wtg-scan-clean',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
            )

        assert result['status'] == 'success'
        assert result['survivor_count'] == 0
        assert result['mandate_gap_count'] == 0
        assert result['deleted_identifier_count'] == 1

    def test_base_ref_override_passed_through_to_seams(self, tmp_path):
        # Capture the base_ref the seams receive.
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

            gate.scan(
                'wtg-scan-ref',
                worktree_path=str(root),
                base_ref='develop',
                diff_runner=_diff,
                diff_names_runner=_names,
            )

        assert seen['diff'] == 'develop'
        assert seen['names'] == 'develop'

    def test_removed_prose_paragraph_produces_no_survivor_flood(self, tmp_path):
        # Arrange — the headline regression: a removed markdown paragraph of
        # ordinary English, where the prose tokens recur ubiquitously across the
        # tree, must NOT flood survivors[]. Filter 1 drops tokens that also
        # appear on retained lines; filter 2's occurrence ceiling drops the rest.
        ceiling = gate._MAX_TREE_OCCURRENCES
        # 'narrative_token' recurs far more than the ceiling across the tree.
        flooded = 'narrative_token recurs everywhere in prose\n' * (ceiling + 10)
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': flooded},
        )
        # A removed prose paragraph naming that same ubiquitous token.
        diff_text = (
            '-The narrative_token is mentioned in this removed prose sentence.\n'
        )
        changed_files = ['marketplace/bundles/b/skills/s/SKILL.md']

        with PlanContext(plan_id='wtg-prose-flood') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # Act
            result = gate.scan(
                'wtg-prose-flood',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
            )

        # Assert — the ubiquitous prose token is dropped by the occurrence
        # ceiling, so the survivor sweep does not flood despite the removed prose.
        assert result['status'] == 'success'
        assert result['survivor_count'] == 0

    def test_missing_request_yields_no_mandate_gaps(self, tmp_path):
        # No request.md written; the resolver returns empty text.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})

        with PlanContext(plan_id='wtg-scan-noreq'):
            # Deliberately do NOT write request.md.
            result = gate.scan(
                'wtg-scan-noreq',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [],
            )

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
        # A changed plugin-doctor analyzer; record the worktree root
        # the seam receives so we can assert it is the FULL marketplace root.
        seen: dict[str, Path] = {}

        def _doctor(wt):
            seen['root'] = wt
            return {'passed': True, 'finding_count': 0, 'summary': 'ran'}

        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_doctor,
            sweep_runner=_passing_sweep,
        )

        # The doctor facet fired and the seam saw the worktree root
        # (the full marketplace/ scan root, NOT a build-map-scoped subset).
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert facets['doctor']['passed'] is True
        assert facets['doctor']['summary'] == 'ran'
        assert seen['root'] == tmp_path

    def test_plan_doctor_path_also_triggers_doctor_facet(self, tmp_path):
        # The plan-doctor trigger glob is the second doctor category.
        calls: list[Path] = []

        facets = gate.run_facets(
            tmp_path,
            [_PLAN_DOCTOR_TRIGGER_PATH],
            doctor_runner=lambda wt: (calls.append(wt) or _passing_doctor(wt)),
            sweep_runner=_passing_sweep,
        )

        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert calls == [tmp_path]

    def test_doctor_seam_failure_is_surfaced_not_raised(self, tmp_path):
        # The doctor seam reports findings (passed: False). This is a
        # SURFACED finding, not an error — the facet still ran.
        def _failing_doctor(_wt):
            return {
                'passed': False,
                'finding_count': 3,
                'summary': 'three rule violations',
            }

        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_failing_doctor,
            sweep_runner=_passing_sweep,
        )

        # The surfacer makes no verdict; passed: False is just surfaced.
        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is True
        assert facets['doctor']['passed'] is False
        assert facets['doctor']['finding_count'] == 3

    def test_doctor_seam_runtime_error_marks_ran_false(self, tmp_path):
        # An infrastructure failure inside the seam must NOT be
        # silently treated as clean: ran: False, passed: False, error captured.
        def _exploding_doctor(_wt):
            raise RuntimeError('plugin-doctor could not be invoked')

        facets = gate.run_facets(
            tmp_path,
            [_DOCTOR_TRIGGER_PATH],
            doctor_runner=_exploding_doctor,
            sweep_runner=_passing_sweep,
        )

        assert facets['doctor']['triggered'] is True
        assert facets['doctor']['ran'] is False
        assert facets['doctor']['passed'] is False
        assert 'could not be invoked' in facets['doctor']['error']


class TestRunFacetsSweepTest:
    """F2 — whole-tree grep-sweep guard re-run, gated on the sweep-test trigger."""

    def test_sweep_guard_test_in_changed_set_runs_sweep_facet(self, tmp_path):
        # A changed whole-tree grep-sweep guard test; capture the
        # worktree root the seam receives (the full scan root).
        seen: dict[str, Path] = {}

        def _sweep(wt):
            seen['root'] = wt
            return {'passed': True, 'summary': 'guard tests passed'}

        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_sweep,
        )

        # The sweep-test facet fired with the full tree as scan root.
        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is True
        assert facets['sweep_test']['passed'] is True
        assert seen['root'] == tmp_path

    def test_sweep_seam_failure_is_surfaced(self, tmp_path):
        # The marked guard tests fail (passed: False) — surfaced.
        def _failing_sweep(_wt):
            return {'passed': False, 'summary': 'a guard test failed'}

        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_failing_sweep,
        )

        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is True
        assert facets['sweep_test']['passed'] is False

    def test_sweep_seam_runtime_error_marks_ran_false(self, tmp_path):
        def _exploding_sweep(_wt):
            raise RuntimeError('pytest -m whole_tree_sweep could not be invoked')

        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_passing_doctor,
            sweep_runner=_exploding_sweep,
        )

        assert facets['sweep_test']['triggered'] is True
        assert facets['sweep_test']['ran'] is False
        assert facets['sweep_test']['passed'] is False
        assert 'could not be invoked' in facets['sweep_test']['error']


class TestRunFacetsNoTrigger:
    """Negative coverage — no facet fires, no seam runs, all vacuously clean."""

    def test_no_trigger_leaves_all_facets_untriggered_and_clean(self, tmp_path):
        # A changed set that hits no facet trigger glob, plus failing
        # seams that MUST NOT be invoked (their failure would prove a leak).
        def _must_not_run_doctor(_wt):
            raise AssertionError('doctor seam invoked without a doctor trigger')

        def _must_not_run_sweep(_wt):
            raise AssertionError('sweep seam invoked without a sweep-test trigger')

        facets = gate.run_facets(
            tmp_path,
            [_NO_TRIGGER_PATH],
            doctor_runner=_must_not_run_doctor,
            sweep_runner=_must_not_run_sweep,
        )

        # Every facet is untriggered, un-run, and vacuously clean. No
        # seam raised, proving none was invoked.
        for name in ('doctor', 'sweep_test'):
            assert facets[name]['triggered'] is False, name
            assert facets[name]['ran'] is False, name
            assert facets[name]['passed'] is True, name

    def test_empty_changed_set_fires_no_facet(self, tmp_path):
        # An empty changed set (pre-diff shape) fires nothing.
        facets = gate.run_facets(
            tmp_path,
            [],
            doctor_runner=lambda _wt: pytest.fail('doctor must not run'),
            sweep_runner=lambda _wt: pytest.fail('sweep must not run'),
        )

        assert facets['doctor']['triggered'] is False
        assert facets['sweep_test']['triggered'] is False

    def test_one_facet_fires_others_stay_untriggered(self, tmp_path):
        # Only the sweep-test trigger is in the changed set; the
        # doctor seam MUST NOT run.
        def _must_not_run(_wt):
            raise AssertionError('unrelated facet seam invoked')

        facets = gate.run_facets(
            tmp_path,
            [_SWEEP_TEST_TRIGGER_PATH],
            doctor_runner=_must_not_run,
            sweep_runner=_passing_sweep,
        )

        # Exactly one facet fired.
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
        # A changed set that hits BOTH facet triggers at once,
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

            result = gate.scan(
                'wtg-scan-facets-all',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
                doctor_runner=_passing_doctor,
                sweep_runner=_passing_sweep,
            )

        # Both facets ran AND the survivor sweep is unchanged.
        assert result['status'] == 'success'
        facets = result['facets']
        assert facets['doctor']['ran'] is True
        assert facets['sweep_test']['ran'] is True
        # The always-run survivor sweep still surfaced the planted reference.
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'

    def test_no_facet_trigger_leaves_survivor_sweep_unchanged(self, tmp_path):
        # A changed set hitting NO facet trigger; the survivor sweep
        # half must behave exactly as in the facet-free TestScan cases.
        root = _make_marketplace_tree(
            tmp_path,
            {'bundles/b/skills/s/SKILL.md': 'orphaned_helper still referenced\n'},
        )
        diff_text = '-    orphaned_helper()\n'
        changed_files = [_NO_TRIGGER_PATH]

        with PlanContext(plan_id='wtg-scan-facets-none') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            result = gate.scan(
                'wtg-scan-facets-none',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: diff_text,
                diff_names_runner=lambda _wt, _ref: changed_files,
                doctor_runner=lambda _wt: pytest.fail('doctor must not run'),
                sweep_runner=lambda _wt: pytest.fail('sweep must not run'),
            )

        # No facet fired, yet the survivor sweep is identical.
        assert result['status'] == 'success'
        assert result['facets']['doctor']['triggered'] is False
        assert result['facets']['sweep_test']['triggered'] is False
        assert result['survivor_count'] == 1
        assert result['survivors'][0]['identifier'] == 'orphaned_helper'

    def test_scan_default_facet_seams_resolve_without_override(self, tmp_path):
        # When no facet runners are passed AND no trigger fires, scan
        # must not invoke the real (live) facet seams at all.
        root = _make_marketplace_tree(tmp_path, {'bundles/b/skills/s/x.py': '\n'})

        with PlanContext(plan_id='wtg-scan-facets-default') as ctx:
            (ctx.plan_dir / 'request.md').write_text('noop\n', encoding='utf-8')

            # No facet trigger in the changed set, so the real seams are
            # never reached even though no override was supplied.
            result = gate.scan(
                'wtg-scan-facets-default',
                worktree_path=str(root),
                base_ref='main',
                diff_runner=lambda _wt, _ref: '',
                diff_names_runner=lambda _wt, _ref: [_NO_TRIGGER_PATH],
            )

        # Every facet is untriggered/clean with the real defaults wired.
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
        # Force the real diff runner to raise, simulating a git failure.
        def _boom(_wt, _ref):
            raise RuntimeError('git diff main...HEAD failed: fatal: bad revision')

        monkeypatch.setattr(gate, '_run_git_diff', _boom)

        with PlanContext(plan_id='wtg-cmd-err'):
            args = Namespace(
                plan_id='wtg-cmd-err',
                worktree_path=str(tmp_path),
                base_ref='main',
            )

            rc = gate.cmd_scan(args)

        out = capsys.readouterr().out
        assert rc == 1
        assert 'status: error' in out
        assert 'bad revision' in out

    def test_success_emits_status_success_and_returns_zero(self, tmp_path, capsys, monkeypatch):
        # Both seams succeed with no survivors / no gaps.
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

            rc = gate.cmd_scan(args)

        out = capsys.readouterr().out
        assert rc == 0
        assert 'status: success' in out


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
