#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-pass two-phase rule runner for the plugin-doctor analyzers.

The runner builds the file/AST corpus ONCE — a shared parse-once
:class:`AstCache` — and dispatches the marketplace-wide rules through one
place.

Emission-order contract
-----------------------
The emitted findings, their ORDER, the per-rule ``_scoped`` / ``_suppressed``
wrapping, and every ``rule_summaries`` label are preserved exactly. The runner
owns ordered per-command dispatch tables that reproduce the canonical emission
sequences. The descriptor ``scope`` field conceptually partitions the
corpus-relational analyzers (which can read the shared :class:`AstCache`) from
the file-local ones, but the runner does NOT reorder the emitted findings: the
shared corpus is the single-pass substrate (AST parsing happens at most once
per file), while emission order is preserved.

A rule summary is a label plus a finding count, and — for a rule that derives
and publishes them — a ``population_size`` and a ``blind_spots``. Both extra
keys are additive and appear only where the rule supplies them, so an absent
figure is never read as a zero; the ORDER and the LABEL set are what this
contract fixes.

Wrapping injection
------------------
``cmd_quality_gate`` owns three closures that depend on its ``--paths`` scope
and the suppression-config load — ``scoped`` (path filter), ``suppressed``
(scope + project/frontmatter suppression), and the scoped manage-invocation
resolver. These are INJECTED into :meth:`RuleRunner.run_quality_gate` rather
than relocated, so the suppression substrate and scope helpers keep their single
definition in ``doctor-marketplace.py`` and the runner owns only the ordered
dispatch table.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from _analyze_agentfile_directory_tree import analyze_agentfile_directory_tree
from _analyze_agentfile_line_budget import analyze_agentfile_line_budget
from _analyze_allowed_tools_drift import analyze_allowed_tools_drift
from _analyze_argument_naming import (
    analyze_argument_naming,
    analyze_argument_naming_with_population,
)
from _analyze_askuserquestion_reachability import (
    analyze_askuserquestion_reachability,
)
from _analyze_bash_chain_shapes_in_skills import analyze_bash_chain_shapes_in_skills
from _analyze_bash_fence_inline_code_exemption import (
    analyze_bash_fence_inline_code_exemption,
)
from _analyze_canonical_enum_drift import (
    analyze_canonical_enum_drift,
    analyze_canonical_enum_drift_with_population,
)
from _analyze_declared_vs_disk import analyze_declared_vs_disk
from _analyze_documented_verb_set_drift import analyze_documented_verb_set_drift
from _analyze_fail_closed_gate_reads import analyze_fail_closed_gate_reads
from _analyze_finalize_step_token import scan_finalize_step_token
from _analyze_frontmatter import analyze_frontmatter
from _analyze_historical_prose_in_skills import analyze_historical_prose_in_skills
from _analyze_incident_reference_in_docs import analyze_incident_reference_in_docs
from _analyze_lane_frontmatter import analyze_lane_frontmatter
from _analyze_lesson_id_in_skill_prose import analyze_lesson_id_in_skill_prose
from _analyze_literal_count import analyze_literal_count
from _analyze_manage_invocation import scan_manage_invocation
from _analyze_mutates_source_order import analyze_mutates_source_order
from _analyze_persona_binding_resolves import analyze_persona_binding_resolves
from _analyze_persona_profile_uniqueness import analyze_persona_profile_uniqueness
from _analyze_plan_path_in_scripts import analyze_plan_path_in_scripts
from _analyze_plugin_json import analyze_plugin_json_orphans
from _analyze_provides_method_table import analyze_provides_method_table
from _analyze_readme_skill_coverage import analyze_readme_skill_coverage
from _analyze_resolver_matrix_coverage import analyze_resolver_matrix_coverage
from _analyze_role_field import analyze_role_field
from _analyze_script_call_drift import analyze_script_call_drift
from _analyze_self_declared_rule_compliance import analyze_self_declared_rule_compliance
from _analyze_shell_substitution_in_skills import analyze_shell_substitution_in_skills
from _analyze_shim_marker import (
    analyze_shim_marker,
    analyze_shim_marker_with_population,
)
from _analyze_simplicity import scan_simplicity
from _analyze_skill_mode import analyze_skill_mode
from _analyze_skill_notation import analyze_skill_notation
from _analyze_skill_relative_temp_path import analyze_skill_relative_temp_path
from _analyze_step_configurable_contract import scan_step_configurable_contract
from _analyze_sys_path_bootstrap import analyze_sys_path_bootstrap
from _analyze_target_scope import analyze_target_scope
from _analyze_thinking_directive_in_workflow_docs import (
    analyze_thinking_directive_in_workflow_docs,
    analyze_thinking_directive_in_workflow_docs_with_population,
)
from _analyze_tmp_redirect_in_skills import analyze_tmp_redirect_in_skills
from _analyze_workflow_doc_toon_error_field import analyze_workflow_doc_toon_error_field
from _cmd_extension import validate_extension_contracts
from _dep_index import AstCache
from _doctor_analysis import analyze_markdown_mirror_rules, scan_argparse_safety


@dataclass
class CorpusContext:
    """The parse-once corpus a single rule-runner pass shares across analyzers.

    Built once at the head of a command. ``marketplace_root`` is the bundles
    root; ``ast_cache`` is the shared :class:`AstCache` threaded into every
    AST-parsing analyzer so each ``.py`` file is read and parsed at most once
    per pass. The cache is a transparent parse memoization — reusing it never
    changes an analyzer's findings.
    """

    marketplace_root: Path
    ast_cache: AstCache

    @classmethod
    def build(cls, marketplace_root: Path) -> CorpusContext:
        return cls(marketplace_root=marketplace_root, ast_cache=AstCache())


class RuleRunner:
    """Drives the marketplace-wide rule dispatch for ``analyze`` / ``quality-gate``.

    One instance per command invocation, holding the shared
    :class:`CorpusContext`. The two ``run_*`` methods reproduce the exact
    pre-D5 emission order, wrapping, and summary labels of the respective
    command bodies.
    """

    def __init__(self, context: CorpusContext) -> None:
        self.context = context

    # ------------------------------------------------------------------
    # quality-gate
    # ------------------------------------------------------------------
    def run_quality_gate(
        self,
        *,
        scope_dirs: list[Path],
        scoped: Callable[[list[dict]], list[dict]],
        suppressed: Callable[[list[dict]], list[dict]],
        scoped_manage_invocation: Callable[[Path, list[Path]], list[dict]],
    ) -> tuple[list[dict], list[dict]]:
        """Run the quality-gate invariant rule set; return (issues, rule_summaries).

        Preserves the canonical ``cmd_quality_gate`` dispatch: the same ordered
        rule calls, the same ``_scoped`` / ``_suppressed`` wrapping per rule, the
        same ``rule_summaries`` labels in the same positions (including the
        ``provides-method-table-drift`` / ``literal-count-drift`` rule-name
        labels and the two-entry markdown-mirror split), and the same
        scoped-vs-unscoped manage-invocation branch. Four summaries additionally
        carry ``population_size`` (see :func:`emit`), one of which —
        ``analyze_argument_naming`` — also carries ``blind_spots``. Re-count both
        here rather than carrying the numbers forward; the population count said
        "two" for a round after the third was wired in this same file.
        """
        root = self.context.marketplace_root
        cache = self.context.ast_cache
        all_issues: list[dict] = []
        rule_summaries: list[dict] = []

        def emit(
            label: str,
            findings: list[dict],
            population_size: int | None = None,
            blind_spots: int | None = None,
        ) -> None:
            """Record a rule's findings and, where the rule knows them, its coverage figures.

            ``findings`` alone cannot report coverage: ``details.population_size``
            rides on a FINDING, so on a clean tree — the only state a passing gate
            is ever in — the size the rule derived appears nowhere, and a rule
            that examined nothing is indistinguishable from one that examined the
            whole tree and found it clean. A rule that can report the figures
            supplies them here and they are published alongside the count.

            ``population_size`` is what the rule enumerated; ``blind_spots`` is
            the part of that population it looked at and could not decide. The
            second is not derivable from the first two numbers, and without it a
            rule that resolved an authority for a third of its population reports
            exactly like one that resolved all of it.

            Both figures are WHOLE-TREE and are not narrowed by ``--paths``: the
            rule runs over the whole tree and only its FINDINGS are
            scope-filtered, so reporting a scope-narrowed population would
            describe a derivation that never happened. Each key is omitted
            entirely for a rule that does not publish it, so an absent figure is
            never read as a zero.
            """
            all_issues.extend(findings)
            summary: dict = {'rule': label, 'findings': len(findings)}
            if population_size is not None:
                summary['population_size'] = population_size
            if blind_spots is not None:
                summary['blind_spots'] = blind_spots
            rule_summaries.append(summary)

        emit('scan_argparse_safety', scoped(scan_argparse_safety(root, cache=cache)))

        # validate_extension_contracts ALWAYS runs whole-tree and is NEVER
        # filtered, even under --paths — extension-contract compliance has no
        # per-path subset, and a scoped gate must still catch a broken contract.
        contract_result = validate_extension_contracts(root.parent)
        contract_errors = contract_result.get('errors', [])
        for err in contract_errors:
            all_issues.append(
                {
                    'type': 'extension_contract',
                    'rule': err.get('rule', ''),
                    'file': err.get('file', ''),
                    'message': err.get('message', ''),
                    'severity': 'error',
                }
            )
        rule_summaries.append(
            {'rule': 'validate_extension_contracts', 'findings': len(contract_errors)}
        )

        # ``root`` is the BUNDLES dir (see CorpusContext), but
        # analyze_argument_naming derives ``root/'bundles'`` for its markdown
        # corpus and ``root.parent/'.plan'`` for the executor registry — so it
        # takes the MARKETPLACE dir, exactly like validate_extension_contracts
        # above. Passing ``root`` here resolved the executor to
        # ``marketplace/.plan/execute-script.py``, which does not exist: the
        # registry came back empty and the cluster returned [] before scanning a
        # single file, reporting a clean zero it had never derived.
        #
        # The cluster publishes BOTH coverage figures because its authority — the
        # generated executor — is git-ignored, so "judged nothing" is a state a
        # checkout can genuinely be in while the finding count still reads zero.
        naming_findings, naming_population, naming_blind_spots = (
            analyze_argument_naming_with_population(root.parent)
        )
        emit(
            'analyze_argument_naming',
            scoped(naming_findings),
            naming_population,
            naming_blind_spots,
        )
        emit(
            'analyze_shell_substitution_in_skills',
            scoped(analyze_shell_substitution_in_skills(root)),
        )
        emit(
            'analyze_workflow_doc_toon_error_field',
            scoped(analyze_workflow_doc_toon_error_field(root)),
        )
        emit(
            'analyze_skill_relative_temp_path',
            scoped(analyze_skill_relative_temp_path(root)),
        )
        emit(
            'analyze_lesson_id_in_skill_prose',
            suppressed(analyze_lesson_id_in_skill_prose(root)),
        )
        emit(
            'analyze_allowed_tools_drift',
            suppressed(analyze_allowed_tools_drift(root)),
        )
        emit(
            'analyze_self_declared_rule_compliance',
            suppressed(analyze_self_declared_rule_compliance(root)),
        )
        emit(
            'analyze_historical_prose_in_skills',
            suppressed(analyze_historical_prose_in_skills(root)),
        )
        emit(
            'analyze_incident_reference_in_docs',
            suppressed(analyze_incident_reference_in_docs(root)),
        )
        thinking_findings, thinking_population = (
            analyze_thinking_directive_in_workflow_docs_with_population(root)
        )
        emit(
            'analyze_thinking_directive_in_workflow_docs',
            scoped(thinking_findings),
            thinking_population,
        )
        shim_findings, shim_population = analyze_shim_marker_with_population(root)
        emit('analyze_shim_marker', scoped(shim_findings), shim_population)
        emit('scan_finalize_step_token', scoped(scan_finalize_step_token(root)))
        emit(
            'analyze_mutates_source_order',
            scoped(analyze_mutates_source_order(root)),
        )
        emit(
            'scan_step_configurable_contract',
            scoped(scan_step_configurable_contract(root)),
        )
        emit('analyze_role_field', scoped(analyze_role_field(root)))
        # lane-frontmatter-invalid — validates every lane-participating element's
        # ``lane:`` frontmatter block (closed-enum ``class`` + ``cost_size``, the
        # ``prunable_when`` requirement for ``class: prunable``, and a valid
        # ``tier``) consumed by the manage-execution-manifest lane resolver. The
        # enums are owned by extension-api/standards/ext-point-lane-element.md.
        # Routed through ``suppressed`` so per-file ``plugin-doctor-disable`` and
        # project-config exemptions apply (CodeRabbit PR #811 review fix).
        emit('analyze_lane_frontmatter', suppressed(analyze_lane_frontmatter(root)))
        emit('analyze_skill_mode', scoped(analyze_skill_mode(root)))
        # targets-scope-invalid — a component's build-time `targets:` frontmatter
        # naming an unregistered target, or declaring an empty list. The
        # multi-target build rejects both; catching them here reports the defect
        # while the author is still looking at the file.
        emit('analyze_target_scope', scoped(analyze_target_scope(root)))
        emit(
            'analyze_persona_profile_uniqueness',
            scoped(analyze_persona_profile_uniqueness(root)),
        )
        emit(
            'analyze_persona_binding_resolves',
            scoped(analyze_persona_binding_resolves(root)),
        )
        # provides-method-table-drift / literal-count-drift use the rule-id
        # label, not the function name.
        emit(
            'provides-method-table-drift',
            scoped(analyze_provides_method_table(root, cache=cache)),
        )
        emit('literal-count-drift', scoped(analyze_literal_count(root, cache=cache)))
        # canonical-enum-choices-drift — a documented ``{a|b|c}`` enum in a skill's
        # ``## Canonical invocations`` block that diverges from the flag's live
        # argparse ``choices=`` (the same mirror-vs-derived shape as the two rules
        # above, one surface over from the flag-name check the argument-naming
        # cluster performs).
        enum_findings, enum_population = analyze_canonical_enum_drift_with_population(
            root, cache=cache
        )
        emit(
            'canonical-enum-choices-drift',
            scoped(enum_findings),
            enum_population,
        )
        # readme-skill-registration-drift — a bundle README that fails to name a
        # skill its plugin.json registers (the same mirror-vs-derived shape, one
        # surface out: README enumeration vs plugin.json registration).
        emit(
            'readme-skill-registration-drift',
            scoped(analyze_readme_skill_coverage(root)),
        )

        # markdown-mirror cluster — one analyzer call, TWO summary entries
        # partitioned by rule_id (de-registration of either regresses the build).
        markdown_mirror_findings = scoped(analyze_markdown_mirror_rules(root))
        all_issues.extend(markdown_mirror_findings)
        rule_summaries.append(
            {
                'rule': 'broken-relative-link',
                'findings': sum(
                    1
                    for f in markdown_mirror_findings
                    if f.get('rule_id') == 'broken-relative-link'
                ),
            }
        )
        rule_summaries.append(
            {
                'rule': 'fenced-code-no-language',
                'findings': sum(
                    1
                    for f in markdown_mirror_findings
                    if f.get('rule_id') == 'fenced-code-no-language'
                ),
            }
        )

        emit(
            'analyze_fail_closed_gate_reads',
            scoped(analyze_fail_closed_gate_reads(root)),
        )
        emit(
            'analyze_sys_path_bootstrap',
            scoped(analyze_sys_path_bootstrap(root)),
        )
        # plan-path-in-scripts — forms A + B are per-file, form C is
        # population-derived over the whole tree. The analyzer takes the
        # marketplace root (it joins `bundles/` itself), so it receives
        # ``root.parent`` rather than the bundles root every other rule takes.
        emit(
            'analyze_plan_path_in_scripts',
            scoped(analyze_plan_path_in_scripts(root.parent)),
        )
        # agentfile-hygiene cluster — the two deterministic backstop rules
        # (line-budget + directory-tree) that embody the rubric owned by
        # plan-marshall:ref-agentfile-hygiene/standards/rubric.md. Build-failing
        # under quality-gate; they stay active in analyze mode too.
        emit(
            'analyze_agentfile_line_budget',
            scoped(analyze_agentfile_line_budget(root)),
        )
        emit(
            'analyze_agentfile_directory_tree',
            scoped(analyze_agentfile_directory_tree(root)),
        )

        # manage-invocation cluster — scoped uses the referenced-notation index,
        # unscoped uses the eager whole-marketplace scan. find_marketplace_root
        # returns bundles/, but the manage-invocation helpers expect its parent.
        if scope_dirs:
            manage_invocation_findings = scoped_manage_invocation(root.parent, scope_dirs)
        else:
            manage_invocation_findings = scan_manage_invocation(root.parent)
        all_issues.extend(manage_invocation_findings)
        rule_summaries.append(
            {'rule': 'scan_manage_invocation', 'findings': len(manage_invocation_findings)}
        )

        return all_issues, rule_summaries

    # ------------------------------------------------------------------
    # analyze (marketplace-wide portion)
    # ------------------------------------------------------------------
    def run_analyze_marketplace_rules(self, *, active_rules: frozenset[str]) -> list[dict]:
        """Run the marketplace-wide rule set for ``cmd_analyze``; return findings.

        Ordered analyzer calls with the same ``active_rules`` gating for the two
        opt-in clusters (``script_call_drift`` and ``argument_naming``). The
        per-component ``analyze_component`` loop, the suppression filter, and the
        categorize step stay in ``cmd_analyze``.

        ``analyze_shim_marker`` runs here beside its sibling
        ``analyze_thinking_directive_in_workflow_docs``: the rule catalogue
        states it is reachable from both passes, and the edit-time surface is the
        one an unmarked shim should surface on — while the author is still
        looking at the file, rather than at the build gate.
        """
        root = self.context.marketplace_root
        cache = self.context.ast_cache
        issues: list[dict] = []

        issues.extend(scan_argparse_safety(root, cache=cache))
        issues.extend(scan_simplicity(root))
        issues.extend(analyze_shell_substitution_in_skills(root))
        issues.extend(analyze_bash_chain_shapes_in_skills(root))
        issues.extend(analyze_sys_path_bootstrap(root))
        issues.extend(analyze_tmp_redirect_in_skills(root))
        issues.extend(analyze_skill_relative_temp_path(root))
        issues.extend(analyze_workflow_doc_toon_error_field(root))
        issues.extend(analyze_askuserquestion_reachability(root))
        issues.extend(analyze_bash_fence_inline_code_exemption(root))
        issues.extend(analyze_lesson_id_in_skill_prose(root))
        issues.extend(analyze_allowed_tools_drift(root))
        issues.extend(analyze_self_declared_rule_compliance(root))
        issues.extend(analyze_historical_prose_in_skills(root))
        issues.extend(analyze_incident_reference_in_docs(root))
        issues.extend(analyze_thinking_directive_in_workflow_docs(root))
        issues.extend(analyze_shim_marker(root))
        issues.extend(analyze_agentfile_line_budget(root))
        issues.extend(analyze_agentfile_directory_tree(root))
        issues.extend(analyze_role_field(root))
        issues.extend(analyze_lane_frontmatter(root))
        issues.extend(analyze_declared_vs_disk(root))
        issues.extend(analyze_plugin_json_orphans(root))
        issues.extend(analyze_provides_method_table(root, cache=cache))
        issues.extend(analyze_literal_count(root, cache=cache))
        issues.extend(analyze_canonical_enum_drift(root, cache=cache))
        issues.extend(analyze_readme_skill_coverage(root))
        issues.extend(analyze_skill_notation(root))
        issues.extend(analyze_frontmatter(root))
        issues.extend(analyze_target_scope(root))
        issues.extend(analyze_resolver_matrix_coverage(root, cache=cache))

        if 'script_call_drift' in active_rules:
            issues.extend(analyze_script_call_drift(root))

        if 'argument_naming' in active_rules:
            # ``root.parent`` for the same reason as the quality-gate dispatch
            # above: the analyzer takes the MARKETPLACE dir, not the bundles
            # dir. This call carried the bug too, so opting the cluster in on
            # the analyze path silently produced nothing on every run.
            issues.extend(analyze_argument_naming(root.parent))

        if 'documented_verb_set_drift' in active_rules:
            # ⛔ Opt-in and reachable ONLY here — deliberately absent from
            # ``run_quality_gate``. That gate derives status as
            # ``'fail' if all_issues else 'pass'``: it is severity-blind, so it
            # has no registered-but-non-failing mode, and wiring a rule with a
            # non-zero standing finding count into it would turn the tree red.
            # (``cmd_test_conventions`` DOES derive status from error-severity
            # findings only, but its scope is the test tree, not this one.)
            # The promotion path and its two preconditions are recorded in
            # ``references/rule-catalog.md``.
            #
            # ``root.parent`` for the same reason as ``argument_naming`` above:
            # the analyzer takes the MARKETPLACE dir, not the bundles dir.
            issues.extend(analyze_documented_verb_set_drift(root.parent))

        return issues
