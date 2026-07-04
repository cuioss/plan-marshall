#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Central declarative rule registry for the plugin-doctor analyzers.

Each rule-bearing ``_analyze_*.py`` module exposes a module-level
``RULE_DESCRIPTOR`` (or a ``RULE_DESCRIPTORS`` list for modules that back more
than one distinct rule). This module imports every such module and collects
its descriptor(s) into a single registry. The opt-in rule set, the
active-rules gating, and the analyzer-name surface are all derived as pure
functions of this registry.

Descriptor semantics
--------------------
A :class:`RuleDescriptor` is additive metadata about a rule the analyzers
emit; it is orthogonal to the finding's own ``type``/``rule_id`` keys and does
NOT alter any analyzer's emitted output (the eight typeless analyzers keep
their current dict shape unchanged). The fields are:

- ``rule_id`` — the rule's identity in the registry. For most rules this is
  the finding ``rule_id`` the analyzer emits. For the three opt-in clusters
  (``argument_naming`` / ``verb_chain`` / ``script_call_drift``) it is the
  ``--rules`` opt-in token, since the whole cluster is gated atomically and the
  opt-in set is derived as ``{d.rule_id for d in registry if d.opt_in}``.
- ``severity`` — the dominant finding severity (``error`` / ``warning`` /
  ``info`` / ``tip``).
- ``category`` — the provenance class (``structural`` / ``content`` /
  ``style`` / ``safety``); see ``references/rule-provenance.md``.
- ``scope`` — ``file-local`` (the analyzer's verdict needs only the single
  file under inspection) vs ``corpus-relational`` (the verdict depends on the
  cross-file corpus: resolving notations against the script tree, comparing a
  table mirror against a derived set, checking a link target on disk, etc.).
  This is the field the single-pass runner dispatches on.
- ``opt_in`` — gated OFF by default; only runs when the caller passes the
  rule's token via ``--rules``.
- ``default_on`` — runs unconditionally when not opt-in.
- ``has_fixer`` — an apply/verify handler pair exists (see
  ``_doctor_shared.py::FIXABLE_ISSUE_TYPES``).

Import-cycle note
-----------------
:class:`RuleDescriptor` is defined at the top of this module, before any
analyzer import. Analyzer modules do ``from _rule_registry import
RuleDescriptor`` at their top, which only needs the class — they never call
:func:`get_registry`. The registry itself is built lazily on first access (not
at module import), so collecting the descriptors never re-enters a
mid-initialisation analyzer module.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

# Scope values — the field the single-pass runner dispatches on.
SCOPE_FILE_LOCAL = 'file-local'
SCOPE_CORPUS_RELATIONAL = 'corpus-relational'


@dataclass(frozen=True)
class RuleDescriptor:
    """Self-describing metadata for one plugin-doctor rule.

    See the module docstring for field semantics. The descriptor is additive
    metadata: it never alters the emitted finding shape.
    """

    rule_id: str
    severity: str
    category: str
    scope: str
    opt_in: bool = False
    default_on: bool = True
    has_fixer: bool = False


# Every module that contributes one or more descriptors, in stable sorted
# order. A module that does not (yet) define a descriptor contributes nothing —
# the collector tolerates its absence so the tree stays importable while the
# descriptors are rolled out module-by-module.
_DESCRIPTOR_MODULES: tuple[str, ...] = (
    '_analyze_agentfile_directory_tree',
    '_analyze_agentfile_line_budget',
    '_analyze_allowed_tools_drift',
    '_analyze_argument_naming',
    '_analyze_bash_chain_shapes_in_skills',
    '_analyze_bash_fence_inline_code_exemption',
    '_analyze_cmd_root_anchoring',
    '_analyze_coverage',
    '_analyze_crossfile',
    '_analyze_declared_vs_disk',
    '_analyze_executor_path_in_production',
    '_analyze_fail_closed_gate_reads',
    '_analyze_finalize_step_token',
    '_analyze_frontmatter',
    '_analyze_historical_prose_in_skills',
    '_analyze_lane_frontmatter',
    '_analyze_lesson_id_in_skill_prose',
    '_analyze_literal_count',
    '_analyze_manage_findings_invocation',
    '_analyze_manage_invocation',
    '_analyze_markdown',
    '_analyze_metadata_field_validity',
    '_analyze_notation_staleness',
    '_analyze_orphan_argparse_flags',
    '_analyze_persona_binding_resolves',
    '_analyze_persona_profile_uniqueness',
    '_analyze_phase2_refine_contract',
    '_analyze_plan_path_in_scripts',
    '_analyze_plugin_json',
    '_analyze_provides_method_table',
    '_analyze_resolution_branch_markers',
    '_analyze_resolver_matrix_coverage',
    '_analyze_role_field',
    '_analyze_script_call_drift',
    '_analyze_self_declared_rule_compliance',
    '_analyze_shell_active_tokens',
    '_analyze_shell_substitution_in_skills',
    '_analyze_simplicity',
    '_analyze_skill_mode',
    '_analyze_skill_notation',
    '_analyze_skill_relative_temp_path',
    '_analyze_step_configurable_contract',
    '_analyze_structure',
    '_analyze_sys_path_bootstrap',
    '_analyze_test_conventions',
    '_analyze_tmp_redirect_in_skills',
    '_analyze_verb_chains',
    '_analyze_workflow_doc_toon_error_field',
)


_REGISTRY: tuple[RuleDescriptor, ...] | None = None


def _descriptors_for_module(module_name: str) -> list[RuleDescriptor]:
    """Return the descriptor(s) a single module contributes (possibly none)."""
    module = importlib.import_module(module_name)
    items = getattr(module, 'RULE_DESCRIPTORS', None)
    if items is None:
        single = getattr(module, 'RULE_DESCRIPTOR', None)
        items = [single] if single is not None else []
    return list(items)


def _build_registry() -> tuple[RuleDescriptor, ...]:
    """Raise ``ValueError`` on a duplicate ``rule_id`` so a copy-paste descriptor
    collision fails loudly rather than silently shadowing.
    """
    collected: list[RuleDescriptor] = []
    seen: set[str] = set()
    for module_name in _DESCRIPTOR_MODULES:
        for descriptor in _descriptors_for_module(module_name):
            if descriptor.rule_id in seen:
                raise ValueError(f'duplicate rule_id in registry: {descriptor.rule_id}')
            seen.add(descriptor.rule_id)
            collected.append(descriptor)
    return tuple(collected)


def get_registry() -> tuple[RuleDescriptor, ...]:
    """Return the full descriptor registry, building it once on first access."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def optin_rule_names() -> frozenset[str]:
    """Derive the opt-in rule token set from the registry descriptors."""
    return frozenset(descriptor.rule_id for descriptor in get_registry() if descriptor.opt_in)
