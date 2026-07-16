#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
doctor-marketplace.py - Batch marketplace analysis and fixing.

Provides automated batch operations across the entire marketplace:
- list-components: Enumerate components (agents, commands, skills, scripts);
  runs no rules — use quality-gate for linting
- analyze: Batch analyze all components for issues (includes the
  hardcoded-model-on-canonical rule introduced by the role-variants plan;
  see plugin-doctor/standards/doctor-agents.md)
- fix: Apply safe fixes automatically across marketplace
- report: Generate comprehensive report for LLM review
- quality-gate: Run pure-static-analysis rules as a build gate
  (exit 1 on findings; intended for invocation from `quality-gate` build
  target). Accepts an optional `--paths` filter to scope the findings to
  specific component paths while running the same invariant rule set.

This is Phase 1 of the hybrid doctor workflow. It handles deterministic
operations that can be fully automated. Phase 2 (LLM) handles semantic
analysis and complex fixes.

Output: TOON to stdout.

Usage:
    python3 doctor-marketplace.py list-components [--bundles NAMES] [--paths PATH [PATH ...]]
    python3 doctor-marketplace.py analyze [--bundles NAMES] [--type TYPE] [--name NAME]
    python3 doctor-marketplace.py fix [--bundles NAMES] [--type TYPE] [--name NAME] [--dry-run]
    python3 doctor-marketplace.py report [--bundles NAMES] [--output FILE]
    python3 doctor-marketplace.py quality-gate [--paths PATH [PATH ...]] [--marketplace-root DIR]
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from _analyze_manage_invocation import (
    _NOTATION_RE,
    _resolve_executor,
    analyze_manage_invocation_markdown,
    check_missing_canonical_blocks,
    derive_script_tree,
)
from _analyze_shared import (
    is_rule_suppressed,
    load_default_suppression_config,
    load_project_suppression_config,
)
from _analyze_test_conventions import (
    analyze_subprocess_pythonpath,
    analyze_unique_fixture_basenames,
    analyze_validator_regex_vs_corpus,
)
from _analyze_triage_fix_not_done_surface import analyze_triage_fix_not_done_surface
from _analyze_triage_read_surface import analyze_triage_read_surface
from _analyze_verify_step_contract import analyze_verify_step_contract
from _cmd_apply import apply_single_fix, load_templates
from _cmd_extension import validate_extension_contracts
from _doctor_analysis import analyze_component
from _doctor_report import generate_report
from _doctor_shared import (
    categorize_all_issues,
    discover_components,
    ensure_report_dir,
    find_bundle_for_file,
    find_bundles,
    find_marketplace_root,
    get_report_dir,
    get_report_filename,
    resolve_component_paths,
)
from _rule_registry import optin_rule_names
from _runner import CorpusContext, RuleRunner
from file_ops import output_toon, safe_main

SCRIPT_DIR = Path(__file__).parent


# =============================================================================
# Opt-in rule registry (--rules flag for analyze)
# =============================================================================
#
# Named rules in this registry are gated OFF by default and only run when the
# caller explicitly opts in via ``--rules <name>[,<name>...]`` on the
# ``analyze`` subcommand. The two boolean aliases ``--enable-argument-naming``
# and ``--enable-verb-chain`` desugar into the corresponding ``--rules`` token.
# Absence of any opt-in keeps the rule silent (no findings, no warnings) —
# matching the prior env-var-off default and avoiding noise on every run.
#
# This replaces the prior env-var gate, which violated the
# ``persona-plan-marshall-agent`` hard rule against ``VAR=val cmd`` invocations.
#
# The opt-in set is derived from the central rule registry
# (``_rule_registry.optin_rule_names``), which collects the ``opt_in=True``
# descriptors declared by the analyzer modules
# (``argument_naming`` / ``verb_chain`` / ``script_call_drift``). Computed once
# at module import, after the analyzer imports above, so the whole descriptor
# population is loadable by the time the registry is built.

_OPTIN_RULE_NAMES = optin_rule_names()


def _parse_rules_flag(rules_value: str | None) -> frozenset[str]:
    """Parse a ``--rules`` argument into a normalised set of rule names.

    Accepts ``None`` or empty string (returns empty set), a single name, or
    comma-separated names. Unknown names are dropped from the active set but
    a warning is emitted to stderr naming each rejected token alongside the
    accepted registry — silent drops mask user typos in a diagnostic tool
    where the caller may believe a rule is active when it has been silently
    dropped. Valid tokens in the same invocation continue to activate.
    """
    if not rules_value:
        return frozenset()
    tokens = {tok.strip() for tok in rules_value.split(',') if tok.strip()}
    unknown = sorted(tokens - _OPTIN_RULE_NAMES)
    if unknown:
        accepted = ', '.join(sorted(_OPTIN_RULE_NAMES))
        rejected = ', '.join(unknown)
        print(
            f'WARNING: unknown --rules token(s) ignored: {rejected}. '
            f'Accepted opt-in rules: {accepted}.',
            file=sys.stderr,
        )
    return frozenset(tokens & _OPTIN_RULE_NAMES)


def _resolve_active_rules(args) -> frozenset[str]:
    """Resolve the active opt-in rule set from ``--rules`` + alias flags.

    The two aliases ``--enable-argument-naming`` and ``--enable-verb-chain``
    desugar into ``argument_naming`` / ``verb_chain`` tokens that union with
    whatever ``--rules`` already names. Order does not matter — the result
    is a set.
    """
    active = set(_parse_rules_flag(getattr(args, 'rules', None)))
    if getattr(args, 'enable_argument_naming', False):
        active.add('argument_naming')
    if getattr(args, 'enable_verb_chain', False):
        active.add('verb_chain')
    return frozenset(active)


# =============================================================================
# Fix application (inlined from _doctor_fixes.py)
# =============================================================================


def apply_safe_fixes(issues: list[dict], marketplace_root: Path, script_dir: Path, dry_run: bool = False) -> dict:
    """Apply all safe fixes to files."""
    applied: list[dict] = []
    failed: list[dict] = []
    skipped: list[dict] = []
    results: dict = {'applied': applied, 'failed': failed, 'skipped': skipped, 'dry_run': dry_run}

    templates = load_templates(script_dir)

    # Group issues by file to avoid conflicts
    by_file: dict[str, list[dict]] = {}
    for issue in issues:
        file_path = issue.get('file', '')
        if file_path:
            by_file.setdefault(file_path, []).append(issue)

    for file_path, file_issues in by_file.items():
        path = Path(file_path)
        if not path.exists():
            for issue in file_issues:
                results['failed'].append({'issue': issue, 'error': f'File not found: {file_path}'})
            continue

        bundle_dir = find_bundle_for_file(path, marketplace_root)
        if not bundle_dir:
            for issue in file_issues:
                results['failed'].append({'issue': issue, 'error': 'Could not determine bundle directory'})
            continue

        for issue in file_issues:
            if dry_run:
                results['skipped'].append({'issue': issue, 'reason': 'dry_run'})
                continue

            try:
                rel_path = str(path.relative_to(bundle_dir))
            except ValueError:
                rel_path = str(path)

            fix_data = {'type': issue.get('type'), 'file': rel_path, 'details': issue.get('details', {})}
            result = apply_single_fix(fix_data, bundle_dir, templates)

            if result.get('success'):
                results['applied'].append({'issue': issue, 'result': result})
            else:
                results['failed'].append({'issue': issue, 'error': result.get('error', 'Unknown error')})

    return results


# =============================================================================
# Shared helpers
# =============================================================================


def parse_csv_filter(value: str | None) -> set[str] | None:
    """Parse a comma-separated string into a filter set, or None if empty."""
    if not value:
        return None
    return {v.strip() for v in value.split(',') if v.strip()}


def _resolve_marketplace_root(args) -> Path | dict:
    """Resolve the marketplace root for a verb, containing bad-input errors.

    Returns the resolved ``Path`` to the ``bundles/`` directory on success, or
    a structured ``{status: error}`` dict on failure. Callers branch on
    ``isinstance(result, dict)`` to short-circuit with the error envelope.
    """
    try:
        root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_marketplace_root', 'message': str(e)}
    if not root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}
    return root


def collect_filtered_components(
    bundles: list[Path],
    type_filter: set[str] | None,
    name_filter: set[str] | None,
) -> list[dict]:
    """Discover and filter components across bundles by type and name."""
    result = []
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        component_list = []
        if not type_filter or 'agent' in type_filter or 'agents' in type_filter:
            component_list.extend(components['agents'])
        if not type_filter or 'command' in type_filter or 'commands' in type_filter:
            component_list.extend(components['commands'])
        if not type_filter or 'skill' in type_filter or 'skills' in type_filter:
            component_list.extend(components['skills'])
        if name_filter:
            component_list = [c for c in component_list if c.get('name') in name_filter]
        for c in component_list:
            c['_bundle_name'] = bundle_dir.name
        result.extend(component_list)
    return result


# =============================================================================
# Declarative suppression (Granularity-2 driver integration)
# =============================================================================
#
# The six marketplace-wide content scanners each carry a ``rule_id`` field on
# their findings. The driver consults the three-layer suppression substrate
# (default config < project config < per-file frontmatter, see
# ``_analyze_shared.is_rule_suppressed``) before extending ``all_issues`` so a
# project-level ``.plan/plugin-doctor.yml`` exemption — or a per-file
# ``plugin-doctor-disable`` frontmatter key — drops the named rule's findings.
#
# The default-config layer is already applied inside each analyzer (it absorbed
# the formerly-hardcoded ``_is_allowlisted()`` tables), so re-checking it here is
# idempotent; the new behavior this layer adds is the project-config and
# frontmatter granularities.

_SUPPRESSIBLE_RULE_IDS = frozenset(
    {
        'no-historical-prose-in-skills',
        'no-lesson-id-in-skill-prose',
        'prose-verb-chain-consistency',
        'allowed-tools-body-drift',
        'skill-self-declared-rule-violation',
        'resolver-matrix-coverage',
    }
)


def _rel_to_bundles(abs_file: str, marketplace_root: Path) -> str | None:
    """Return the finding file's path relative to ``marketplace_root`` (bundles/).

    Returns ``None`` when the file resolves outside the bundles tree (e.g. a
    project-local ``.claude/skills/**`` file) — such files have no bundles-
    relative prefix, so the path-prefix config layers cannot match them and only
    the file-scoped frontmatter layer applies.
    """
    try:
        return str(Path(abs_file).resolve().relative_to(marketplace_root.resolve()))
    except (OSError, ValueError):
        return None


def filter_suppressed_findings(
    findings: list[dict],
    marketplace_root: Path,
    default_cfg: dict[str, list[str]],
    project_cfg: dict[str, list[str]],
) -> list[dict]:
    """Drop findings suppressed by the three-layer suppression substrate.

    Only findings whose ``rule_id`` is in ``_SUPPRESSIBLE_RULE_IDS`` are subject
    to suppression; every other finding passes through unchanged. A finding
    without a ``file`` is never suppressed (no path to anchor a layer against).
    The per-file frontmatter layer reads each file's content once, cached by
    absolute path to avoid re-reading shared files across findings.
    """
    if not findings:
        return findings

    content_cache: dict[str, str] = {}

    def _content_for(abs_file: str) -> str:
        cached = content_cache.get(abs_file)
        if cached is not None:
            return cached
        try:
            text = Path(abs_file).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            text = ''
        content_cache[abs_file] = text
        return text

    kept: list[dict] = []
    for finding in findings:
        rule_id = finding.get('rule_id')
        abs_file = finding.get('file')
        if rule_id not in _SUPPRESSIBLE_RULE_IDS or not abs_file:
            kept.append(finding)
            continue
        rel = _rel_to_bundles(abs_file, marketplace_root)
        if is_rule_suppressed(
            rule_id,
            abs_file,
            rel if rel is not None else '',
            _content_for(abs_file),
            default_cfg,
            project_cfg,
        ):
            continue
        kept.append(finding)
    return kept


def _load_suppression_configs(marketplace_root: Path) -> tuple[dict, dict]:
    """Load the default + project suppression configs for a driver invocation.

    The project config (``.plan/plugin-doctor.yml``) is resolved relative to the
    invocation root, which is the repo root (parent of ``marketplace/``):
    ``marketplace_root`` is ``<repo>/marketplace/bundles``, so the invocation
    root is two levels up.
    """
    default_cfg = load_default_suppression_config()
    invocation_root = marketplace_root.parent.parent
    project_cfg = load_project_suppression_config(invocation_root)
    return default_cfg, project_cfg


# =============================================================================
# Subcommands
# =============================================================================


def _list_components_paths(paths: list[str]) -> dict:
    """Enumerate explicitly provided component paths (runs no rules)."""
    resolved = resolve_component_paths(paths)
    if not resolved:
        return {
            'status': 'success',
            'mode': 'paths',
            'total_components': 0,
            'components': [],
            'message': 'No valid paths resolved',
        }

    components_list = []
    for resolved_path, component_type in resolved:
        entry: dict = {
            'path': str(resolved_path),
            'type': component_type,
        }
        # For skills, add name from directory
        if component_type == 'skill':
            skill_dir = resolved_path if resolved_path.is_dir() else resolved_path.parent
            entry['name'] = skill_dir.name
        elif component_type in ('agent', 'command'):
            # For agents/commands, use stem of the markdown file or directory
            if resolved_path.is_file():
                entry['name'] = resolved_path.stem
            else:
                # Try to find the markdown file
                md_files = list(resolved_path.glob('*.md'))
                entry['name'] = md_files[0].stem if md_files else resolved_path.name
        else:
            entry['name'] = resolved_path.stem if resolved_path.is_file() else resolved_path.name

        components_list.append(entry)

    return {
        'status': 'success',
        'mode': 'paths',
        'total_components': len(components_list),
        'components': components_list,
    }


def cmd_list_components(args) -> dict:
    """Enumerate marketplace components (runs no rules; use quality-gate to lint)."""
    # --paths mode: resolve explicit paths, skip marketplace discovery
    if hasattr(args, 'paths') and args.paths:
        return _list_components_paths(args.paths)

    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    bundles_list = []
    total_components = 0
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        bundle_total = sum(len(v) for v in components.values())
        total_components += bundle_total

        bundles_list.append(
            {
                'name': bundle_dir.name,
                'path': str(bundle_dir),
                'agents': len(components['agents']),
                'commands': len(components['commands']),
                'skills': len(components['skills']),
                'scripts': len(components['scripts']),
                'total': bundle_total,
            }
        )

    return {
        'status': 'success',
        'marketplace_root': str(marketplace_root),
        'total_bundles': len(bundles),
        'total_components': total_components,
        'bundles': bundles_list,
    }


def cmd_analyze(args) -> dict:
    """Analyze all components for issues."""
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    bundles = find_bundles(marketplace_root, parse_csv_filter(args.bundles))
    component_list = collect_filtered_components(bundles, parse_csv_filter(args.type), parse_csv_filter(args.name))

    # Resolve opt-in rules from ``--rules`` and alias flags. The set is the
    # single source of truth for which rule clusters dispatch — propagated
    # down into ``analyze_component`` for per-component clusters (verb_chain)
    # and used directly for marketplace-wide clusters (argument_naming).
    active_rules = _resolve_active_rules(args)

    all_analysis = []
    total_issues = 0

    for component in component_list:
        result = analyze_component(component, active_rules=active_rules)
        result['bundle'] = component['_bundle_name']
        all_analysis.append(result)
        total_issues += result.get('issue_count', 0)

    # Categorize all issues
    all_issues = []
    for result in all_analysis:
        all_issues.extend(result.get('issues', []))

    # The marketplace-wide rule set is dispatched once through the single-pass
    # runner: it builds the parse-once AST corpus and preserves the canonical
    # emission order and the two opt-in active_rules gates (script_call_drift,
    # argument_naming). The per-component analyze_component loop above, the
    # suppression filter, and the categorize step below stay in this command.
    marketplace_issues = RuleRunner(
        CorpusContext.build(marketplace_root)
    ).run_analyze_marketplace_rules(active_rules=active_rules)
    all_issues.extend(marketplace_issues)
    total_issues += len(marketplace_issues)

    # Granularity-2 driver integration: drop findings from the six content
    # scanners that the project config (`.plan/plugin-doctor.yml`) or a per-file
    # `plugin-doctor-disable` frontmatter key suppresses. The filter is rule-id
    # scoped (`_SUPPRESSIBLE_RULE_IDS`), so every other finding is untouched.
    default_cfg, project_cfg = _load_suppression_configs(marketplace_root)
    all_issues = filter_suppressed_findings(all_issues, marketplace_root, default_cfg, project_cfg)
    total_issues = len(all_issues)

    categorized = categorize_all_issues(all_issues)

    return {
        'status': 'success',
        'total_components': len(all_analysis),
        'total_issues': total_issues,
        'safe_fixes': len(categorized['safe']),
        'risky_fixes': len(categorized['risky']),
        'unfixable': len(categorized['unfixable']),
        'analysis': all_analysis,
        'categorized_safe': categorized['safe'],
        'categorized_risky': categorized['risky'],
        'categorized_unfixable': categorized['unfixable'],
    }


def cmd_fix(args) -> dict:
    """Apply safe fixes across marketplace."""
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    bundles = find_bundles(marketplace_root, parse_csv_filter(args.bundles))
    component_list = collect_filtered_components(bundles, parse_csv_filter(args.type), parse_csv_filter(args.name))

    # First analyze to find issues
    all_issues = []
    for component in component_list:
        result = analyze_component(component)
        all_issues.extend(result.get('issues', []))

    # Categorize and get safe fixes only
    categorized = categorize_all_issues(all_issues)
    safe_issues = categorized['safe']

    if not safe_issues:
        return {
            'status': 'no_fixes_needed',
            'message': 'No safe fixes to apply',
            'dry_run': args.dry_run,
            'total_issues': len(all_issues),
            'risky_issues': len(categorized['risky']),
            'unfixable_issues': len(categorized['unfixable']),
        }

    # Apply safe fixes
    fix_results = apply_safe_fixes(safe_issues, marketplace_root, SCRIPT_DIR, args.dry_run)

    return {
        'status': 'completed' if not fix_results['failed'] else 'error',
        'dry_run': args.dry_run,
        'total_safe_issues': len(safe_issues),
        'applied': len(fix_results['applied']),
        'failed': len(fix_results['failed']),
        'skipped': len(fix_results['skipped']),
        'details_applied': fix_results['applied'],
        'details_failed': fix_results['failed'],
        'details_skipped': fix_results['skipped'],
        'risky_issues': len(categorized['risky']),
        'unfixable_issues': len(categorized['unfixable']),
    }


def _resolve_scope_dirs(paths: list[str]) -> list[Path]:
    """Resolve `--paths` strings to absolute, existing directories.

    A supplied path may be a directory (the skill dir) or a file; in both
    cases the containing directory is the scope unit. Non-existent paths are
    dropped silently — `quality-gate --paths` over a deleted directory simply
    scopes to nothing rather than erroring.
    """
    scope_dirs: list[Path] = []
    for path_str in paths:
        resolved = Path(path_str).resolve()
        if not resolved.exists():
            continue
        scope_dirs.append(resolved if resolved.is_dir() else resolved.parent)
    return scope_dirs


def _finding_in_scope(finding: dict, scope_dirs: list[Path]) -> bool:
    """True when the finding's `file` resolves under one of the scope dirs.

    Findings without a `file` key (or with an unresolvable one) are treated as
    out-of-scope so a path-filtered run never leaks an unanchored finding.
    """
    file_value = finding.get('file')
    if not file_value:
        return False
    try:
        finding_path = Path(file_value).resolve()
    except (OSError, ValueError):
        return False
    return any(
        finding_path == scope_dir or scope_dir in finding_path.parents
        for scope_dir in scope_dirs
    )


def _scoped_manage_invocation(
    marketplace_root: Path, scope_dirs: list[Path]
) -> list[dict]:
    """Run the manage-invocation cluster scoped to `scope_dirs`.

    Unlike the marketplace-wide `scan_manage_invocation`, this NEVER calls
    `build_script_index` (which eagerly derives the `--help` surface of every
    in-scope script via a thread pool — the expensive path the gate's budget
    note warns about). Instead it:

      1. reads only the markdown files under the supplied scope dirs,
      2. extracts the executor notations REFERENCED in those files (reusing
         `_NOTATION_RE`),
      3. derives each distinct referenced notation's surface once via the
         cache-backed `derive_script_tree`,
      4. validates the scoped markdown against that small index, and
      5. runs `check_missing_canonical_blocks` filtered to the scoped SKILL.md
         files only.

    When the executor is unreachable the index is empty and the invocation
    rule emits nothing, preserving the no-false-positive contract.
    """
    executor = _resolve_executor(marketplace_root)
    if executor is None:
        return []

    # Enumerate the scoped markdown files (SKILL.md + standards/references/etc).
    md_files: list[Path] = []
    for scope_dir in scope_dirs:
        if scope_dir.is_dir():
            md_files.extend(sorted(scope_dir.rglob('*.md')))
    # Dedup while preserving order (overlapping scope dirs may share files).
    seen: set[Path] = set()
    unique_md: list[Path] = []
    for md in md_files:
        if md in seen:
            continue
        seen.add(md)
        unique_md.append(md)

    # Collect distinct referenced notations across the scoped files.
    file_contents: list[tuple[Path, str]] = []
    referenced: set[str] = set()
    for md in unique_md:
        try:
            content = md.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        file_contents.append((md, content))
        for line in content.splitlines():
            match = _NOTATION_RE.search(line)
            if match:
                referenced.add(
                    f"{match.group('bundle')}:{match.group('skill')}:{match.group('script')}"
                )

    # Derive only the referenced notations' surfaces (never the whole index).
    script_index: dict = {}
    for notation in sorted(referenced):
        tree = derive_script_tree(notation, executor)
        if tree is not None:
            script_index[notation] = tree

    findings: list[dict] = []
    if script_index:
        for md, content in file_contents:
            findings.extend(
                analyze_manage_invocation_markdown(content, str(md), script_index)
            )

    # missing-canonical-block for scoped SKILL.md files only. The whole-tree
    # `check_missing_canonical_blocks` is filtered down to the scope dirs so a
    # scoped gate does not flag SKILL.md files outside the touched paths.
    for block_finding in check_missing_canonical_blocks(marketplace_root):
        if _finding_in_scope(block_finding, scope_dirs):
            findings.append(block_finding)

    return findings


def cmd_quality_gate(args) -> dict:
    """Run pure-static-analysis invariant rules across the marketplace as a build gate.

    Runs only the marketplace-wide rules whose violations are currently enforced
    by the pytest suite as "real marketplace must produce zero findings"
    invariants (i.e., the rules that fail CI when violated). All rules in this
    set operate on the marketplace tree without pytest fixtures, network access,
    or mutating I/O, so they are cheap enough to run on every fast iteration.

    Per-component advisory rules (`analyze_component`'s `check_*` cluster) are
    intentionally NOT included — they emit informational findings on the real
    marketplace today and are not enforced as build-failing invariants.

    Rule set:
      - scan_argparse_safety       (AST: ArgumentParser/add_parser missing
                                    allow_abbrev=False — enforced by
                                    test_argparse_safety.py
                                    test_real_marketplace_has_zero_findings)
      - validate_extension_contracts (extension-point contract compliance —
                                      enforced by test_plugin_doctor_extension.py
                                      test_contract_validation_real_marketplace)
      - analyze_argument_naming    (notation/subcommand/flag/canonical-forms
                                    cluster — unconditionally active in
                                    quality-gate; ``--rules`` opt-in only
                                    applies to the ``analyze`` subcommand)
      - analyze_shell_substitution_in_skills (forbidden ``$(`` patterns in
                                    plan-marshall skill markdown — enforces
                                    the persona-plan-marshall-agent "no shell
                                    constructs" hard rule)
      - analyze_skill_relative_temp_path (relative ``.plan/temp/...`` path
                                    consumed by ``git -C ... commit -F`` in
                                    plan-marshall skill markdown — the harness
                                    ``Write`` resolves the relative path against
                                    the main checkout while ``git -C`` resolves
                                    it against the worktree, so the round-trip
                                    references two different files)
      - scan_manage_invocation     (manage-invocation-invalid +
                                    missing-canonical-block: documented script
                                    invocations validated against each
                                    script-bearing skill's argparse surface,
                                    and script-bearing SKILL.md files required
                                    to publish a ``## Canonical invocations``
                                    section — the build-failing regression net
                                    against argparse-rejection drift)
      - scan_finalize_step_token   (finalize-step-token-mismatch: a finalize-step
                                    skill's documented ``mark-step-done --step``
                                    token under ``--phase 6-finalize`` must match
                                    its fully-qualified manifest step_id, else the
                                    recorded phase_steps key drifts and the
                                    phase_steps_complete handshake loops forever)
      - scan_step_configurable_contract (step-configurable-contract: a finalize-step
                                    body doc whose ``configurable:`` frontmatter
                                    block is present but malformed — missing a
                                    required sub-field (key/default/description),
                                    wrong type, empty description, duplicate key,
                                    or any declaration that fails the central D1
                                    contract parser; ownerless docs are skipped)
      - analyze_agentfile_line_budget (agentfile-line-count-over-budget: an
                                    always-on agentfile (``CLAUDE.md`` /
                                    ``AGENTS.md``) whose line count exceeds the
                                    budget — build-failing under quality-gate;
                                    rubric owned by
                                    plan-marshall:ref-agentfile-hygiene)
      - analyze_agentfile_directory_tree (agentfile-directory-tree-present: a
                                    fenced directory-tree drawing inside an
                                    always-on agentfile — build-failing under
                                    quality-gate)

    Note: ``analyze_bash_chain_shapes_in_skills`` and
    ``analyze_tmp_redirect_in_skills`` are NOT included in quality-gate because
    the existing marketplace tree pre-dates these rules and would require a
    large upfront cleanup sweep.  They are unconditionally active in ``analyze``
    mode and can be run explicitly via ``doctor-marketplace.py analyze``.

    ``--paths`` scoping
    -------------------
    With ``--paths {dir}...`` the SAME invariant rule set runs, but the
    file-scopeable findings are filtered to those whose ``file`` resolves under
    a supplied path. No flag = today's marketplace-wide behavior, byte-for-byte
    unchanged. Two rules behave specially under ``--paths``:

      - ``validate_extension_contracts`` ALWAYS runs whole-tree and its findings
        are included UNFILTERED — extension-contract compliance has no
        meaningful per-path subset, and a scoped finalize gate should still
        catch a broken extension contract the change introduced.
      - the manage-invocation cluster runs via a referenced-notation index
        (``derive_script_tree`` per distinct referenced notation), never the
        eager ``build_script_index`` — keeping the scoped manage-invocation
        check cheap. ``missing-canonical-block`` is filtered to scoped SKILL.md
        files only.
    """
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    paths = getattr(args, 'paths', None)
    scope_dirs = _resolve_scope_dirs(paths) if paths else []

    # quality-gate is intentionally NOT bundle-filtered — bundle filtering would
    # break the "real marketplace must produce zero findings" invariant the
    # gate exists to enforce. No --bundles flag is exposed. The optional --paths
    # filter scopes the FINDINGS (a strict subset), not the rule set.
    all_issues: list[dict] = []
    rule_summaries: list[dict] = []

    # File-scopeable rules: each emits file-anchored findings, so running them
    # marketplace-wide and filtering by `file` produces a strict subset under
    # --paths. The filter is the identity when `scope_dirs` is empty.
    def _scoped(findings: list[dict]) -> list[dict]:
        if not scope_dirs:
            return findings
        return [f for f in findings if _finding_in_scope(f, scope_dirs)]

    # Granularity-2 driver integration: load the suppression configs once, then
    # drop suppressed findings from the suppressible content scanners. `_scoped`
    # narrows to the --paths subset; `_suppressed` then removes any finding the
    # project config / per-file frontmatter exempts. The default-config layer is
    # already applied inside each analyzer, so re-checking it here is idempotent —
    # the project-config and frontmatter granularities are what this adds.
    default_cfg, project_cfg = _load_suppression_configs(marketplace_root)

    def _suppressed(findings: list[dict]) -> list[dict]:
        return filter_suppressed_findings(_scoped(findings), marketplace_root, default_cfg, project_cfg)

    # The marketplace-wide invariant rule set is dispatched once through the
    # single-pass runner: it builds the parse-once AST corpus and preserves the
    # canonical emission order, the per-rule _scoped/_suppressed wrapping, and
    # every rule_summaries label (including the provides-method-table-drift /
    # literal-count-drift rule-name labels and the two-entry markdown-mirror
    # split). The scope/suppression closures and the scoped manage-invocation
    # resolver are injected so their definitions stay in this module.
    runner = RuleRunner(CorpusContext.build(marketplace_root))
    all_issues, rule_summaries = runner.run_quality_gate(
        scope_dirs=scope_dirs,
        scoped=_scoped,
        suppressed=_suppressed,
        scoped_manage_invocation=_scoped_manage_invocation,
    )

    # find/triage-flow containment guards (D7). Wired here rather than inside the
    # runner so the runner's byte-identical pre-D5 dispatch table stays untouched;
    # both are file-anchored file-local rules, so `_scoped` produces the correct
    # --paths subset.
    #   - triage-reads-top-level-only: a triage surface (triage.md /
    #     verification-feedback.md / ext-triage-{domain}) must never read the
    #     `raw_input.*` quarantine namespace — triage reads top-level fields only.
    #   - verify-step-canonicals-required: every ext-point-build-verify-step
    #     implementor must declare a non-empty `canonicals:` list.
    #   - triage-fix-not-done-contract: the triage.md Step 3c FIX action body must
    #     carry the not-done/loop_back/STOP directive triad and must not mark its
    #     fix task done inline (execution + commit are owned by phase-5-execute
    #     re-entered by the loop_back).
    for label, findings in (
        (
            'analyze_triage_fix_not_done_surface',
            analyze_triage_fix_not_done_surface(marketplace_root),
        ),
        ('analyze_triage_read_surface', analyze_triage_read_surface(marketplace_root)),
        ('analyze_verify_step_contract', analyze_verify_step_contract(marketplace_root)),
    ):
        scoped_findings = _scoped(findings)
        all_issues.extend(scoped_findings)
        rule_summaries.append({'rule': label, 'findings': len(scoped_findings)})

    # script-call-drift is intentionally NOT in quality-gate — it probes
    # --help via subprocess for every documented notation/verb pair, which
    # is too expensive for the build gate. Invoke via
    # ``analyze --rules script_call_drift`` for explicit drift sweeps.

    return {
        'status': 'fail' if all_issues else 'pass',
        'total_issues': len(all_issues),
        'rules_run': rule_summaries,
        'issues': all_issues,
    }


def _load_validator_registry(registry_path: str | None) -> list[dict]:
    """Load the Rule 3 validator registry from a JSON file, defaulting to empty.

    The standard documents the registry schema in
    `standards/doctor-test-conventions.md` (`## Rule 3 — Validator Registry`).
    Until consumers populate the markdown table or pass an explicit JSON
    file, the registry is empty and Rule 3 is a no-op.
    """
    if not registry_path:
        return []
    path = Path(registry_path)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    cleaned: list[dict] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if not all(k in entry for k in ('validator_path', 'regex_constant', 'list_command')):
            continue
        cleaned.append(
            {
                'validator_path': str(entry['validator_path']),
                'regex_constant': str(entry['regex_constant']),
                'list_command': str(entry['list_command']),
            }
        )
    return cleaned


def cmd_test_conventions(args) -> dict:
    """Run the test-tree convention rules across the configured test root.

    See ``standards/doctor-test-conventions.md`` for rule definitions and
    severity. Exits non-zero on any error finding (build-failing).
    """
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    project_root = marketplace_root.parent
    test_root_arg = getattr(args, 'test_root', None)
    test_root = Path(test_root_arg).resolve() if test_root_arg else (project_root / 'test').resolve()

    all_issues: list[dict] = []
    rule_summaries: list[dict] = []

    rule1_findings = analyze_unique_fixture_basenames(test_root)
    all_issues.extend(rule1_findings)
    rule_summaries.append({'rule': 'unique-fixture-basenames', 'findings': len(rule1_findings)})

    rule2_findings = analyze_subprocess_pythonpath(test_root)
    all_issues.extend(rule2_findings)
    rule_summaries.append({'rule': 'subprocess-pythonpath', 'findings': len(rule2_findings)})

    registry = _load_validator_registry(getattr(args, 'registry', None))
    rule3_findings = analyze_validator_regex_vs_corpus(registry, project_root=project_root)
    all_issues.extend(rule3_findings)
    rule_summaries.append({'rule': 'identifier-validator-corpus', 'findings': len(rule3_findings)})

    return {
        'status': 'fail' if all_issues else 'pass',
        'test_root': str(test_root),
        'total_issues': len(all_issues),
        'rules_run': rule_summaries,
        'issues': all_issues,
    }


def cmd_report(args) -> dict:
    """Generate comprehensive report for LLM review."""
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    # Scan
    scan_results = {'total_bundles': len(bundles), 'total_components': 0}

    # Analyze all
    all_analysis = []
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        total = sum(len(v) for v in components.values())
        scan_results['total_components'] += total

        for comp_type in ['agents', 'commands', 'skills']:
            for component in components[comp_type]:
                result = analyze_component(component)
                result['bundle'] = bundle_dir.name
                all_analysis.append(result)

    # Generate report
    report = generate_report(scan_results, all_analysis)

    # Determine output directory and filename
    timestamp = datetime.now(UTC).strftime('%Y%m%d-%H%M%S')

    # Determine scope for filename
    if len(bundles) == 1:
        # Single bundle - use bundle name
        scope = bundles[0].name
    elif bundle_filter:
        # Multiple specific bundles - join names (limit length)
        scope = '-'.join(sorted(bundle_filter)[:3])
        if len(bundle_filter) > 3:
            scope += f'-and-{len(bundle_filter) - 3}-more'
    else:
        # All bundles
        scope = 'marketplace'

    if args.output:
        report_dir = Path(args.output)
    else:
        report_dir = get_report_dir()

    json_filename = get_report_filename(timestamp, scope)

    # Create directory and write JSON report
    ensure_report_dir(report_dir)
    json_path = report_dir / json_filename
    findings_filename = f'{timestamp}-{scope}-findings.md'

    output_json = json.dumps(report, indent=2)
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(output_json)

    # Output success message
    return {
        'status': 'success',
        'report_dir': str(report_dir),
        'report_file': str(json_path),
        'findings_file': str(report_dir / findings_filename),
        'summary': report['summary'],
        'next_step': 'LLM should read report_file and create findings.md with analysis',
    }


# =============================================================================
# Main
# =============================================================================


def cmd_validate_contracts(args) -> dict:
    """Validate extension point contract compliance."""
    result = _resolve_marketplace_root(args)
    if isinstance(result, dict):
        return result
    marketplace_root = result

    return validate_extension_contracts(
        marketplace_root.parent,
        extension_type=args.extension_type,
        skill_filter=args.skill,
    )


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Batch marketplace analysis and fixing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
Examples:
  # Enumerate entire marketplace
  %(prog)s list-components

  # Enumerate specific bundles
  %(prog)s list-components --bundles pm-dev-java,plan-marshall

  # Enumerate explicit component paths
  %(prog)s list-components --paths marketplace/bundles/plan-marshall/skills/phase-4-plan

  # Enumerate multiple paths (marketplace and project-local)
  %(prog)s list-components --paths marketplace/bundles/plan-marshall/skills/phase-4-plan .claude/skills/my-skill

  # Run the quality gate marketplace-wide
  %(prog)s quality-gate

  # Run the quality gate scoped to a touched skill
  %(prog)s quality-gate --paths marketplace/bundles/plan-marshall/skills/phase-4-plan --marketplace-root marketplace

  # Analyze all components
  %(prog)s analyze

  # Analyze only agents and commands
  %(prog)s analyze --type agents,commands

  # Analyze a single skill by name
  %(prog)s analyze --bundles plan-marshall --type skills --name phase-4-plan

  # Preview safe fixes (dry run)
  %(prog)s fix --dry-run

  # Apply safe fixes
  %(prog)s fix

  # Generate report for LLM review
  %(prog)s report --output .plan/temp/my-report
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    marketplace_root_help = (
        'Override the marketplace root directory (parent of bundles/). '
        'Use the worktree path (e.g., /abs/.plan/local/worktrees/{plan_id}/marketplace) '
        'when verifying edits inside an isolated plan worktree before merge-back. '
        'NOT bundles/ itself.'
    )

    # list-components subcommand
    p_list_components = subparsers.add_parser(
        'list-components',
        help='Enumerate components (runs no rules; use quality-gate for linting)',
        allow_abbrev=False,
    )
    list_components_source = p_list_components.add_mutually_exclusive_group()
    list_components_source.add_argument('--bundles', help='Comma-separated list of bundle names to enumerate')
    list_components_source.add_argument(
        '--paths', nargs='+', help='Explicit component paths to enumerate (mutually exclusive with --bundles)'
    )
    p_list_components.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_list_components.set_defaults(func=cmd_list_components)

    # analyze subcommand
    p_analyze = subparsers.add_parser('analyze', help='Analyze all components for issues', allow_abbrev=False)
    p_analyze.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_analyze.add_argument('--type', help='Component types to analyze (agents,commands,skills)')
    p_analyze.add_argument('--name', help='Comma-separated component names to filter (e.g., phase-4-plan)')
    p_analyze.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_analyze.add_argument(
        '--rules',
        help=(
            'Comma-separated list of opt-in rule names to activate. Known names: '
            'argument_naming, verb_chain. Absence keeps these rule clusters off.'
        ),
    )
    p_analyze.add_argument(
        '--enable-argument-naming',
        dest='enable_argument_naming',
        action='store_true',
        help='Alias for `--rules argument_naming` (activates the argument-naming rule cluster).',
    )
    p_analyze.add_argument(
        '--enable-verb-chain',
        dest='enable_verb_chain',
        action='store_true',
        help='Alias for `--rules verb_chain` (activates the verb-chain rule cluster).',
    )
    p_analyze.set_defaults(func=cmd_analyze)

    # fix subcommand
    p_fix = subparsers.add_parser('fix', help='Apply safe fixes across marketplace', allow_abbrev=False)
    p_fix.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_fix.add_argument('--type', help='Component types to fix (agents,commands,skills)')
    p_fix.add_argument('--name', help='Comma-separated component names to filter (e.g., phase-4-plan)')
    p_fix.add_argument('--dry-run', action='store_true', help='Preview fixes without applying')
    p_fix.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_fix.set_defaults(func=cmd_fix)

    # report subcommand
    p_report = subparsers.add_parser('report', help='Generate comprehensive report', allow_abbrev=False)
    p_report.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_report.add_argument('--output', '-o', help='Output directory for report')
    p_report.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_report.set_defaults(func=cmd_report)

    # quality-gate subcommand
    p_quality_gate = subparsers.add_parser(
        'quality-gate',
        help='Run pure-static-analysis rules as a build gate (exit 1 on findings)',
        allow_abbrev=False,
    )
    p_quality_gate.add_argument(
        '--paths',
        nargs='+',
        dest='paths',
        help=(
            'Optional explicit component paths to scope the findings to. The SAME '
            'invariant rule set runs; file-anchored findings are filtered to those '
            'under a supplied path. No flag = marketplace-wide (byte-for-byte '
            'unchanged). NOTE: validate_extension_contracts ALWAYS runs whole-tree '
            'and is included unfiltered even under --paths.'
        ),
    )
    p_quality_gate.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_quality_gate.set_defaults(func=cmd_quality_gate)

    # test-conventions subcommand
    p_test_conventions = subparsers.add_parser(
        'test-conventions',
        help='Run test-tree convention rules (exit 1 on findings)',
        allow_abbrev=False,
    )
    p_test_conventions.add_argument(
        '--test-root', dest='test_root', default='test', help='Path to the test tree (default: test/)'
    )
    p_test_conventions.add_argument(
        '--registry',
        dest='registry',
        default=None,
        help='Path to a JSON registry of (validator_path, regex_constant, list_command) entries for Rule 3',
    )
    p_test_conventions.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_test_conventions.set_defaults(func=cmd_test_conventions)

    # validate-contracts subcommand
    p_contracts = subparsers.add_parser(
        'validate-contracts', help='Validate extension point contract compliance', allow_abbrev=False
    )
    p_contracts.add_argument(
        '--extension-type', help='Filter by extension type (triage,outline,recipe,build,credential)'
    )
    p_contracts.add_argument('--skill', help='Filter by specific skill (bundle:skill or skill-name)')
    p_contracts.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_contracts.set_defaults(func=cmd_validate_contracts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result = args.func(args)
    output_toon(result)
    if args.command == 'quality-gate' and result.get('status') == 'fail':
        return 1
    if args.command == 'test-conventions' and result.get('status') == 'fail':
        return 1
    if result.get('status') == 'error':
        return 1
    return 0


if __name__ == '__main__':
    main()  # @safe_main wrapper calls sys.exit internally
