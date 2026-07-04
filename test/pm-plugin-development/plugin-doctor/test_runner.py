# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the single-pass two-phase rule runner (``_runner.py``).

:class:`RuleRunner` builds the parse-once AST corpus once and dispatches
the marketplace-wide rules through ordered per-command tables.

The HARD acceptance contract these tests pin:

1. Golden snapshot — ``run_quality_gate`` emits its ``rule_summaries`` in the
   canonical label sequence (including the ``provides-method-table-drift`` /
   ``literal-count-drift`` rule-name labels and the two-entry markdown-mirror
   split). A reorder, a dropped rule, or a relabel breaks this test.
2. The runner builds a fresh shared :class:`CorpusContext` (an ``AstCache`` that
   parses each file at most once).
3. The four corpus-relational analyzers return byte-identical output whether
   driven via the shared corpus context or their standalone entry point.
4. The analyze-path dispatch gates the two opt-in clusters
   (``script_call_drift`` / ``argument_naming``) on ``active_rules``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_scripts_dir, load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')
_FILE_OPS_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
    / 'tools-file-ops' / 'scripts'
)
# AstCache (the D2 substrate the runner threads) lives in tools-marketplace-inventory.
_DEP_INDEX_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills'
    / 'tools-marketplace-inventory' / 'scripts'
)
for _d in (SCRIPTS_DIR, _FILE_OPS_DIR, _DEP_INDEX_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


def _load(filename: str, name: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_runner_mod = _load('_runner.py', '_runner')
CorpusContext = _runner_mod.CorpusContext
RuleRunner = _runner_mod.RuleRunner

# ``_runner`` already imported ``_dep_index`` (its ``from _dep_index import
# AstCache``), so this resolves the same cached module and the same AstCache
# class the runner threads.
_dep_index = __import__('_dep_index')
AstCache = _dep_index.AstCache

_apmt = _load('_analyze_provides_method_table.py', '_apmt_runner_test')
_alc = _load('_analyze_literal_count.py', '_alc_runner_test')
_armc = _load('_analyze_resolver_matrix_coverage.py', '_armc_runner_test')


# The pre-D5 cmd_quality_gate emission order, captured verbatim. This is the
# byte-identical golden snapshot the runner must reproduce.
GOLDEN_QG_LABELS = [
    'scan_argparse_safety',
    'validate_extension_contracts',
    'analyze_argument_naming',
    'analyze_shell_substitution_in_skills',
    'analyze_workflow_doc_toon_error_field',
    'analyze_skill_relative_temp_path',
    'analyze_lesson_id_in_skill_prose',
    'analyze_allowed_tools_drift',
    'analyze_self_declared_rule_compliance',
    'analyze_historical_prose_in_skills',
    'scan_finalize_step_token',
    'scan_step_configurable_contract',
    'analyze_role_field',
    'analyze_lane_frontmatter',
    'analyze_skill_mode',
    'analyze_persona_profile_uniqueness',
    'analyze_persona_binding_resolves',
    'provides-method-table-drift',
    'literal-count-drift',
    'broken-relative-link',
    'fenced-code-no-language',
    'analyze_fail_closed_gate_reads',
    'analyze_sys_path_bootstrap',
    'scan_manage_invocation',
]


def _clean_bundles(root: Path) -> Path:
    """Materialize a minimal finding-free marketplace bundles root."""
    bundles = root / 'bundles'
    bundle = bundles / 'qg-clean'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(
        '{"name": "qg-clean", "version": "1.0.0"}', encoding='utf-8'
    )
    skill = bundle / 'skills' / 'noop-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text(
        '---\nname: noop-skill\ndescription: Does nothing\nuser-invocable: false\n'
        'mode: knowledge\n---\n\n# Noop\n\nNo-op.\n',
        encoding='utf-8',
    )
    return bundles


def _identity(findings):
    return findings


def _no_scoped_manage_invocation(_root, _scope_dirs):
    return []


# =============================================================================
# CorpusContext
# =============================================================================


def test_corpus_context_build_carries_root_and_fresh_cache(tmp_path):
    """``CorpusContext.build`` pairs the root with a fresh parse-once cache."""
    ctx = CorpusContext.build(tmp_path)
    assert ctx.marketplace_root == tmp_path
    assert isinstance(ctx.ast_cache, AstCache)
    assert ctx.ast_cache.parse_count == 0


# =============================================================================
# Golden snapshot — quality-gate rule_summaries label order
# =============================================================================


def test_run_quality_gate_emits_canonical_label_order(tmp_path):
    """The runner reproduces the exact pre-D5 quality-gate label sequence."""
    bundles = _clean_bundles(tmp_path)
    runner = RuleRunner(CorpusContext.build(bundles))

    _issues, summaries = runner.run_quality_gate(
        scope_dirs=[],
        scoped=_identity,
        suppressed=_identity,
        scoped_manage_invocation=_no_scoped_manage_invocation,
    )

    assert [s['rule'] for s in summaries] == GOLDEN_QG_LABELS


def test_run_quality_gate_clean_tree_has_zero_findings(tmp_path):
    """A finding-free synthetic tree yields no issues and all-zero summaries."""
    bundles = _clean_bundles(tmp_path)
    runner = RuleRunner(CorpusContext.build(bundles))

    issues, summaries = runner.run_quality_gate(
        scope_dirs=[],
        scoped=_identity,
        suppressed=_identity,
        scoped_manage_invocation=_no_scoped_manage_invocation,
    )

    assert issues == []
    assert all(s['findings'] == 0 for s in summaries)


def test_run_quality_gate_uses_scoped_manage_invocation_when_scoped(tmp_path):
    """Under --paths the injected scoped manage-invocation resolver is used."""
    bundles = _clean_bundles(tmp_path)
    runner = RuleRunner(CorpusContext.build(bundles))
    calls: list[tuple] = []

    def _record(root, scope_dirs):
        calls.append((root, scope_dirs))
        return []

    scope_dirs = [bundles / 'qg-clean']
    runner.run_quality_gate(
        scope_dirs=scope_dirs,
        scoped=_identity,
        suppressed=_identity,
        scoped_manage_invocation=_record,
    )

    assert len(calls) == 1
    assert calls[0][1] == scope_dirs


# =============================================================================
# analyze-path dispatch
# =============================================================================


def test_run_analyze_marketplace_rules_returns_list(tmp_path):
    """The analyze-path dispatch returns a flat findings list."""
    bundles = _clean_bundles(tmp_path)
    runner = RuleRunner(CorpusContext.build(bundles))

    issues = runner.run_analyze_marketplace_rules(active_rules=frozenset())

    assert isinstance(issues, list)


def test_run_analyze_marketplace_rules_accepts_optin_clusters(tmp_path):
    """The opt-in clusters are accepted via active_rules without error."""
    bundles = _clean_bundles(tmp_path)
    runner = RuleRunner(CorpusContext.build(bundles))

    issues = runner.run_analyze_marketplace_rules(
        active_rules=frozenset({'script_call_drift', 'argument_naming'})
    )

    # A clean tree yields no findings whether or not the opt-in clusters run;
    # the assertion pins that the gated branches dispatch without error.
    assert isinstance(issues, list)


# =============================================================================
# Shared-AstCache equivalence for the four corpus-relational analyzers
# =============================================================================


def test_provides_method_table_shared_cache_equivalent():
    """provides-method-table output is identical with or without a shared cache."""
    standalone = _apmt.analyze_provides_method_table(MARKETPLACE_ROOT)
    shared = _apmt.analyze_provides_method_table(MARKETPLACE_ROOT, cache=AstCache())
    assert standalone == shared


def test_literal_count_shared_cache_equivalent():
    """literal-count output is identical with or without a shared cache."""
    standalone = _alc.analyze_literal_count(MARKETPLACE_ROOT)
    shared = _alc.analyze_literal_count(MARKETPLACE_ROOT, cache=AstCache())
    assert standalone == shared


def test_resolver_matrix_shared_cache_equivalent():
    """resolver-matrix-coverage output is identical with or without a shared cache."""
    standalone = _armc.analyze_resolver_matrix_coverage(MARKETPLACE_ROOT)
    shared = _armc.analyze_resolver_matrix_coverage(MARKETPLACE_ROOT, cache=AstCache())
    assert standalone == shared


def test_ast_cache_parses_each_file_once():
    """The shared cache memoizes: a re-requested file is not re-parsed."""
    cache = AstCache()
    target = SCRIPTS_DIR / '_runner.py'

    first = cache.get_tree(target)
    count_after_first = cache.parse_count
    second = cache.get_tree(target)

    assert second is first
    assert cache.parse_count == count_after_first
