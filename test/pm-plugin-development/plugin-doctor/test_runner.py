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
6. ``analyze_argument_naming`` additionally publishes ``blind_spots`` — the part
   of its population it looked at and could not decide. A population figure
   alone cannot separate a rule that resolved an authority for every site from
   one that resolved it for two thirds, and this cluster's authority is
   git-ignored, so the unresolved share is a state a checkout is routinely in.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from _plugin_doctor_dispatching_executor import (
    FIXTURE_NOTATION,
    seed_notation_registry,
    write_dispatching_executor,
)
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
_aan = _load('_analyze_argument_naming.py', '_aan_runner_test')


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

    That same two-level nesting is what puts the seeded notation registry at
    ``root/.plan/execute-script.py``, which is where the runner's
    ``analyze_argument_naming(root.parent)`` call resolves it from. Without the
    seed the tree is unexaminable rather than finding-free, and
    ``ARGUMENT_NAMING_SUBSTRATE_ABSENT`` says so — correctly. See
    ``seed_notation_registry``.
    """
    seed_notation_registry(root)
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
# Each takes a ``*_with_population`` entry point on the runner, so the figure
# comes from the same derivation the findings did.
POPULATION_PUBLISHING_LABELS = [
    # Its accept-set is the git-ignored generated executor, so "enumerated the
    # corpus and could judge none of it" is a state a checkout is routinely in
    # and a bare finding count cannot express.
    'analyze_argument_naming',
    'analyze_thinking_directive_in_workflow_docs',
    'analyze_shim_marker',
    # A clean tree is the only state a passing gate is ever in, so a rule whose
    # coverage figures ride on its FINDINGS publishes nothing exactly when it
    # matters. This rule carried the figures per-finding only, while two
    # reference documents claimed a clean sweep states what it could not check.
    'canonical-enum-choices-drift',
]

#: The rules that additionally publish ``blind_spots``.
#:
#: A strict subset of the list above, and deliberately its own list rather than
#: a reuse: a rule may know how big its population is without being able to say
#: which part of it went undecided, so the two capabilities are independent and
#: the omission test below has to be able to tell them apart.
BLIND_SPOT_PUBLISHING_LABELS = [
    'analyze_argument_naming',
]


@lru_cache(maxsize=1)
def _real_tree_summaries():
    """Run the whole gate over the real tree ONCE per worker and share the result.

    The tree does not change during a session and the gate is the most expensive
    thing in this module, so re-running it per test bought nothing. Sharing it
    also removes a way for two assertions about "the real tree" to be made
    against two different runs of it.
    """
    runner = RuleRunner(CorpusContext.build(MARKETPLACE_ROOT))
    _issues, summaries = runner.run_quality_gate(
        scope_dirs=[],
        scoped=_identity,
        suppressed=_identity,
        scoped_manage_invocation=_no_scoped_manage_invocation,
    )
    return {s['rule']: s for s in summaries}


def test_population_publishing_rules_report_their_size_on_a_clean_tree():
    """Over the REAL tree — clean for every one of them — the examined size is published.

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
# Blind-spot publication — the undecided part of the examined population
# =============================================================================


def test_blind_spots_is_omitted_for_rules_that_derive_none():
    """A rule that cannot say what it failed to decide omits the key.

    The mirror of the ``population_size`` omission rule, and it needs its own
    assertion: knowing a population's SIZE and knowing which part of it went
    undecided are separate capabilities, so the rules that publish the first are
    a superset of those that publish the second. Zeroing the key for the
    difference would report "nothing went undecided" on rules that never asked.
    """
    summaries = _real_tree_summaries()

    non_publishing = set(summaries) - set(BLIND_SPOT_PUBLISHING_LABELS)

    assert non_publishing, 'expected the gate to run rules that publish no blind-spot figure'
    assert all('blind_spots' not in summaries[label] for label in non_publishing)


def test_argument_naming_blind_spots_are_a_share_of_its_own_population():
    """The two figures are one unit, so the undecided part cannot exceed the whole.

    A ``blind_spots`` counted over a different corpus than ``population_size``
    would be unreadable beside it — a fraction whose denominator is somewhere
    else. Bounding it against the published population is what fixes the unit.
    """
    summary = _real_tree_summaries()['analyze_argument_naming']

    assert summary['population_size'] > 0, (
        'the real tree carries executor invocations, so an empty population means '
        'the corpus walk found nothing rather than that the corpus is empty'
    )
    assert 0 <= summary['blind_spots'] <= summary['population_size']


def _corpus_with_one_decidable_and_one_undecidable_site(root: Path) -> Path:
    """Build a marketplace carrying exactly one site of each judgeability class.

    Returns the MARKETPLACE root — the parent of ``bundles/``, which is the
    argument the cluster itself takes.

    Both invocations name a REGISTERED notation, so neither is a notation-drift
    finding and the tree stays clean; what separates them is whether the
    accept-set could be derived. ``qg-probe:probe-skill:probe`` resolves to a
    real argparse script the dispatching executor can probe, so its verb and
    flag are judged and found correct. ``FIXTURE_NOTATION`` deliberately
    resolves to no script, so ``build_script_index`` drops it fail-closed and
    the site is examined without a verdict — a blind spot.

    The pair is matched on purpose: with only the second site, a ``blind_spots``
    implementation that simply returned the population size would pass.
    """
    marketplace_root = root / 'marketplace'
    probe_notation = 'qg-probe:probe-skill:probe'
    write_dispatching_executor(root / '.plan', [probe_notation, FIXTURE_NOTATION])

    skill_dir = marketplace_root / 'bundles' / 'qg-probe' / 'skills' / 'probe-skill'
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True)
    (scripts_dir / 'probe.py').write_text(
        '#!/usr/bin/env python3\n'
        '"""Synthetic argparse surface for the blind-spot control."""\n'
        'import argparse\n'
        '\n'
        'parser = argparse.ArgumentParser()\n'
        'subparsers = parser.add_subparsers(dest="command")\n'
        'p_run = subparsers.add_parser("run")\n'
        'p_run.add_argument("--thing")\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    parser.parse_args()\n',
        encoding='utf-8',
    )
    (skill_dir / 'SKILL.md').write_text(
        '# Probe\n'
        '\n'
        '```bash\n'
        f'python3 .plan/execute-script.py {probe_notation} run --thing X\n'
        '```\n'
        '\n'
        '```bash\n'
        f'python3 .plan/execute-script.py {FIXTURE_NOTATION} list\n'
        '```\n',
        encoding='utf-8',
    )
    return marketplace_root


def test_blind_spots_counts_only_the_sites_that_went_undecided(tmp_path):
    """A clean tree still separates what was judged from what was merely seen.

    This is the state the whole deliverable is about: zero findings, and two
    numbers that nonetheless say the sweep enumerated two sites and ruled on
    one. Without the split, the run is reported as a clean gate over a corpus
    the reader is told nothing about.
    """
    marketplace_root = _corpus_with_one_decidable_and_one_undecidable_site(tmp_path)

    findings, population_size, blind_spots = _aan.analyze_argument_naming_with_population(
        marketplace_root
    )

    assert findings == [], f'the control tree is meant to be clean, got {findings!r}'
    assert population_size == 2, 'both invocations belong to the enumerated population'
    assert blind_spots == 1, (
        'only the site whose accept-set could not be derived went undecided; the '
        'probe site was judged and found correct'
    )


def test_argument_naming_plain_entry_point_returns_the_with_population_findings(tmp_path):
    """The projection did not fork into a second implementation.

    ``analyze_argument_naming`` is defined as ``_with_population`` with the two
    figures dropped, so a divergence here means someone re-implemented the walk
    and the published numbers no longer describe the findings beside them.

    The tree is deliberately given a DRIFTING site first. Run against the clean
    control the comparison is ``[] == []``, which two independently broken
    implementations would also satisfy — the equality has to carry a finding to
    be evidence of anything.
    """
    marketplace_root = _corpus_with_one_decidable_and_one_undecidable_site(tmp_path)
    skill_md = (
        marketplace_root / 'bundles' / 'qg-probe' / 'skills' / 'probe-skill' / 'SKILL.md'
    )
    skill_md.write_text(
        skill_md.read_text(encoding='utf-8')
        + '\n```bash\n'
        'python3 .plan/execute-script.py qg-probe:probe-skill:probe run --invented\n'
        '```\n',
        encoding='utf-8',
    )

    findings, _population_size, _blind_spots = _aan.analyze_argument_naming_with_population(
        marketplace_root
    )

    assert findings, 'the equality below is vacuous unless the tree yields a finding'
    assert _aan.analyze_argument_naming(marketplace_root) == findings


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
