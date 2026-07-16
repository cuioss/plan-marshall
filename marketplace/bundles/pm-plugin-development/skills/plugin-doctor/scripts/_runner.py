#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-pass two-phase rule runner for the plugin-doctor analyzers.

The runner builds the file/AST corpus ONCE — a shared parse-once
:class:`AstCache` — and dispatches the marketplace-wide rules through one
place.

Byte-identical contract
-----------------------
The emitted findings, their ORDER, the per-rule ``_scoped`` / ``_suppressed``
wrapping, and every ``rule_summaries`` label are preserved byte-for-byte. The
runner owns ordered per-command dispatch tables that preserve the canonical
emission sequences exactly. The descriptor ``scope`` field conceptually
partitions the corpus-relational analyzers (which can read the shared
:class:`AstCache`) from the file-local ones, but the runner does NOT reorder
the emitted findings: the shared corpus is the single-pass substrate (AST
parsing happens at most once per file), while emission order is preserved.

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
from _analyze_argument_naming import analyze_argument_naming
from _analyze_askuserquestion_reachability import (
    analyze_askuserquestion_reachability,
)
from _analyze_bash_chain_shapes_in_skills import analyze_bash_chain_shapes_in_skills
from _analyze_bash_fence_inline_code_exemption import (
    analyze_bash_fence_inline_code_exemption,
)
from _analyze_declared_vs_disk import analyze_declared_vs_disk
from _analyze_fail_closed_gate_reads import analyze_fail_closed_gate_reads
from _analyze_finalize_step_token import scan_finalize_step_token
from _analyze_frontmatter import analyze_frontmatter
from _analyze_historical_prose_in_skills import analyze_historical_prose_in_skills
from _analyze_lane_frontmatter import analyze_lane_frontmatter
from _analyze_lesson_id_in_skill_prose import analyze_lesson_id_in_skill_prose
from _analyze_literal_count import analyze_literal_count
from _analyze_manage_invocation import scan_manage_invocation
from _analyze_persona_binding_resolves import analyze_persona_binding_resolves
from _analyze_persona_profile_uniqueness import analyze_persona_profile_uniqueness
from _analyze_plugin_json import analyze_plugin_json_orphans
from _analyze_provides_method_table import analyze_provides_method_table
from _analyze_resolver_matrix_coverage import analyze_resolver_matrix_coverage
from _analyze_role_field import analyze_role_field
from _analyze_script_call_drift import analyze_script_call_drift
from _analyze_self_declared_rule_compliance import analyze_self_declared_rule_compliance
from _analyze_shell_substitution_in_skills import analyze_shell_substitution_in_skills
from _analyze_simplicity import scan_simplicity
from _analyze_skill_mode import analyze_skill_mode
from _analyze_skill_notation import analyze_skill_notation
from _analyze_skill_relative_temp_path import analyze_skill_relative_temp_path
from _analyze_step_configurable_contract import scan_step_configurable_contract
from _analyze_sys_path_bootstrap import analyze_sys_path_bootstrap
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

        Preserves the canonical ``cmd_quality_gate`` dispatch byte-for-byte: the
        same ordered rule calls, the same ``_scoped`` / ``_suppressed`` wrapping
        per rule, the same ``rule_summaries`` labels (including the
        ``provides-method-table-drift`` / ``literal-count-drift`` rule-name
        labels and the two-entry markdown-mirror split), and the same
        scoped-vs-unscoped manage-invocation branch.
        """
        root = self.context.marketplace_root
        cache = self.context.ast_cache
        all_issues: list[dict] = []
        rule_summaries: list[dict] = []

        def emit(label: str, findings: list[dict]) -> None:
            all_issues.extend(findings)
            rule_summaries.append({'rule': label, 'findings': len(findings)})

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

        emit('analyze_argument_naming', scoped(analyze_argument_naming(root)))
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
        emit('scan_finalize_step_token', scoped(scan_finalize_step_token(root)))
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

        Preserves the canonical ``cmd_analyze`` marketplace-wide dispatch
        byte-for-byte: the same ordered analyzer calls and the same
        ``active_rules`` gating for the two opt-in clusters (``script_call_drift``
        and ``argument_naming``). The per-component ``analyze_component`` loop,
        the suppression filter, and the categorize step stay in ``cmd_analyze``.
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
        issues.extend(analyze_agentfile_line_budget(root))
        issues.extend(analyze_agentfile_directory_tree(root))
        issues.extend(analyze_role_field(root))
        issues.extend(analyze_lane_frontmatter(root))
        issues.extend(analyze_declared_vs_disk(root))
        issues.extend(analyze_plugin_json_orphans(root))
        issues.extend(analyze_provides_method_table(root, cache=cache))
        issues.extend(analyze_literal_count(root, cache=cache))
        issues.extend(analyze_skill_notation(root))
        issues.extend(analyze_frontmatter(root))
        issues.extend(analyze_resolver_matrix_coverage(root, cache=cache))

        if 'script_call_drift' in active_rules:
            issues.extend(analyze_script_call_drift(root))

        if 'argument_naming' in active_rules:
            issues.extend(analyze_argument_naming(root))

        return issues
