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
   (``script_call_drift`` / ``argument_naming``) on ``active_rules``, and reaches
   ``analyze_shim_marker`` — the edit-time surface the rule catalogue says it
   serves.
5. A rule that derives a population publishes its size in ``rule_summaries``,
   from the same derivation the findings came from, and on a CLEAN run — the
   only state a passing gate is ever in. A rule that derives none omits the key
   rather than reporting a zero.
"""

from __future__ import annotations

import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, get_scripts_dir, load_script_module

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

_ashm_runner = _load('_analyze_shim_marker.py', '_ashm_runner_test')
_atdw_runner = _load(
    '_analyze_thinking_directive_in_workflow_docs.py', '_atdw_runner_test'
)
_apmt = _load('_analyze_provides_method_table.py', '_apmt_runner_test')
_alc = _load('_analyze_literal_count.py', '_alc_runner_test')
_armc = _load('_analyze_resolver_matrix_coverage.py', '_armc_runner_test')


# The canonical quality-gate emission order, captured verbatim. This is the
# golden snapshot the runner must reproduce exactly: a rule that silently drops
# out of the dispatch (or lands in the wrong position) fails here rather than
# degrading into a registered-but-never-invoked rule that emits no CI signal.
# Adding a rule to the dispatch REQUIRES adding its label here, in position.
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
    'analyze_incident_reference_in_docs',
    'analyze_thinking_directive_in_workflow_docs',
    'analyze_shim_marker',
    'scan_finalize_step_token',
    'analyze_mutates_source_order',
    'scan_step_configurable_contract',
    'analyze_role_field',
    'analyze_lane_frontmatter',
    'analyze_skill_mode',
    'analyze_target_scope',
    'analyze_persona_profile_uniqueness',
    'analyze_persona_binding_resolves',
    'provides-method-table-drift',
    'literal-count-drift',
    'canonical-enum-choices-drift',
    'readme-skill-registration-drift',
    'broken-relative-link',
    'fenced-code-no-language',
    'analyze_fail_closed_gate_reads',
    'analyze_sys_path_bootstrap',
    'analyze_plan_path_in_scripts',
    'analyze_agentfile_line_budget',
    'analyze_agentfile_directory_tree',
    'scan_manage_invocation',
]


def _clean_bundles(root: Path) -> Path:
    """Materialize a minimal finding-free marketplace bundles root.

    The tree is nested two levels deep at ``root/marketplace/bundles`` (not
    ``root/bundles``) so the agentfile-hygiene rules'
    ``repo_root_from_marketplace_root()`` derivation (``.parent.parent``)
    resolves back to the test's own isolated ``tmp_path`` instead of escaping
    to the shared pytest-xdist base temp directory and scanning sibling tests'
    CLAUDE.md fixtures.
    """
    bundles = root / 'marketplace' / 'bundles'
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


# =============================================================================
# Examined-population publication
# =============================================================================

# The rules that derive a population and can report its size on a CLEAN run.
# Both take a ``*_with_population`` entry point on the runner, so the figure
# comes from the same derivation the findings did.
POPULATION_PUBLISHING_LABELS = [
    'analyze_thinking_directive_in_workflow_docs',
    'analyze_shim_marker',
    # A clean tree is the only state a passing gate is ever in, so a rule whose
    # coverage figures ride on its FINDINGS publishes nothing exactly when it
    # matters. This rule carried the figures per-finding only, while two
    # reference documents claimed a clean sweep states what it could not check.
    'canonical-enum-choices-drift',
]


def _real_tree_summaries():
    runner = RuleRunner(CorpusContext.build(MARKETPLACE_ROOT))
    _issues, summaries = runner.run_quality_gate(
        scope_dirs=[],
        scoped=_identity,
        suppressed=_identity,
        scoped_manage_invocation=_no_scoped_manage_invocation,
    )
    return {s['rule']: s for s in summaries}


def test_population_publishing_rules_report_their_size_on_a_clean_tree():
    """Over the REAL tree — clean for both rules — the examined size is published.

    The clean case is the one that matters: ``details.population_size`` rides on
    a FINDING, so before this the size appeared nowhere on a passing gate, and a
    rule that examined nothing was indistinguishable from one that examined the
    whole tree and found it clean. Asserted with ``findings == 0`` alongside, so
    the test cannot be satisfied by a tree that produced findings.
    """
    summaries = _real_tree_summaries()

    for label in POPULATION_PUBLISHING_LABELS:
        assert summaries[label]['findings'] == 0, f'{label} is not clean on the real tree'
        assert summaries[label]['population_size'] > 0, (
            f'{label} reported no examined population on a clean run'
        )


def test_population_size_is_omitted_for_rules_that_do_not_derive_one():
    """An absent figure is absent, never a zero.

    Writing ``population_size: 0`` for a rule that does not derive a population
    would be the defect this field exists to remove, one surface over: a reader
    cannot tell "examined nothing" from "does not report".
    """
    summaries = _real_tree_summaries()

    non_publishing = set(summaries) - set(POPULATION_PUBLISHING_LABELS)

    assert non_publishing, 'expected the gate to run rules that publish no population'
    assert all('population_size' not in summaries[label] for label in non_publishing)


def test_published_population_matches_the_analyzer_derivation():
    """The published figure IS the rule's own derivation, not a re-derived one.

    A second walk to produce the number is a second chance to disagree with the
    one the findings came from.
    """
    summaries = _real_tree_summaries()
    _shim_findings, shim_population = _ashm_runner.analyze_shim_marker_with_population(
        MARKETPLACE_ROOT
    )
    _td_findings, td_population = (
        _atdw_runner.analyze_thinking_directive_in_workflow_docs_with_population(
            MARKETPLACE_ROOT
        )
    )

    assert summaries['analyze_shim_marker']['population_size'] == shim_population
    assert (
        summaries['analyze_thinking_directive_in_workflow_docs']['population_size']
        == td_population
    )


def test_with_population_entry_points_agree_with_the_plain_ones():
    """The plain entry point returns exactly the with-population findings.

    Pins that the delegation did not fork the two into separate code paths.
    """
    shim_findings, _ = _ashm_runner.analyze_shim_marker_with_population(MARKETPLACE_ROOT)
    td_findings, _ = (
        _atdw_runner.analyze_thinking_directive_in_workflow_docs_with_population(
            MARKETPLACE_ROOT
        )
    )

    assert _ashm_runner.analyze_shim_marker(MARKETPLACE_ROOT) == shim_findings
    assert (
        _atdw_runner.analyze_thinking_directive_in_workflow_docs(MARKETPLACE_ROOT)
        == td_findings
    )


# =============================================================================
# analyze-pass reachability
# =============================================================================


def test_shim_marker_rule_is_reachable_from_the_analyze_pass(tmp_path):
    """``analyze_shim_marker`` runs in the analyze pass, as the catalogue states.

    It was emitted only from ``run_quality_gate`` while
    ``references/rule-catalog.md`` § Discovery approach claimed both passes —
    so the edit-time surface the rule was built to serve never ran it.
    """
    bundles = _clean_bundles(tmp_path)
    skill_scripts = bundles / 'qg-clean' / 'skills' / 'noop-skill' / 'scripts'
    skill_scripts.mkdir(parents=True)
    (skill_scripts / 'shim_mod.py').write_text(
        'def read_state(data):\n'
        '    # tolerate a pre-migration key shape written by an older writer\n'
        "    return data.get('old_key')\n",
        encoding='utf-8',
    )
    runner = RuleRunner(CorpusContext.build(bundles))

    issues = runner.run_analyze_marketplace_rules(active_rules=frozenset())

    assert [i for i in issues if i.get('rule_id') == _ashm_runner.RULE_ID]
