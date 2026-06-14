#!/usr/bin/env python3
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

from _analyze_allowed_tools_drift import analyze_allowed_tools_drift
from _analyze_argument_naming import analyze_argument_naming
from _analyze_bash_chain_shapes_in_skills import analyze_bash_chain_shapes_in_skills
from _analyze_bash_fence_inline_code_exemption import (
    analyze_bash_fence_inline_code_exemption,
)
from _analyze_declared_vs_disk import analyze_declared_vs_disk
from _analyze_finalize_step_token import scan_finalize_step_token
from _analyze_frontmatter import analyze_frontmatter
from _analyze_historical_prose_in_skills import analyze_historical_prose_in_skills
from _analyze_lesson_id_in_skill_prose import analyze_lesson_id_in_skill_prose
from _analyze_manage_invocation import (
    _NOTATION_RE,
    _resolve_executor,
    analyze_manage_invocation_markdown,
    check_missing_canonical_blocks,
    derive_script_tree,
    scan_manage_invocation,
)
from _analyze_markdown_link_bare_filename import analyze_markdown_link_bare_filename
from _analyze_plugin_json import analyze_plugin_json_orphans
from _analyze_resolver_matrix_coverage import analyze_resolver_matrix_coverage
from _analyze_role_field import analyze_role_field
from _analyze_script_call_drift import analyze_script_call_drift
from _analyze_self_declared_rule_compliance import analyze_self_declared_rule_compliance
from _analyze_shell_substitution_in_skills import analyze_shell_substitution_in_skills
from _analyze_simplicity import scan_simplicity
from _analyze_skill_notation import analyze_skill_notation
from _analyze_test_conventions import (
    analyze_subprocess_pythonpath,
    analyze_unique_fixture_basenames,
    analyze_validator_regex_vs_corpus,
)
from _analyze_tmp_redirect_in_skills import analyze_tmp_redirect_in_skills
from _analyze_workflow_doc_toon_error_field import analyze_workflow_doc_toon_error_field
from _cmd_apply import apply_single_fix, load_templates
from _cmd_extension import validate_extension_contracts
from _doctor_analysis import analyze_component, scan_argparse_safety
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
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]

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
# ``dev-agent-behavior-rules`` hard rule against ``VAR=val cmd`` invocations.

_OPTIN_RULE_NAMES = frozenset({'argument_naming', 'verb_chain', 'script_call_drift'})


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

    # Marketplace-wide argparse_safety scan (lightweight AST check).
    # Runs on every analyze invocation — findings are file-scoped, not
    # component-scoped, so they live alongside per-component issues rather
    # than nested under any single component entry.
    argparse_issues = scan_argparse_safety(marketplace_root)
    all_issues.extend(argparse_issues)
    total_issues += len(argparse_issues)

    # Marketplace-wide SIMPLICITY_* rule cluster (five static detectors).
    # Unconditionally active — the detectors are the mechanical enforcement
    # layer for the dev-general-code-quality "minimum viable code" posture and
    # are cheap (one AST walk + regex pass per script). Rules 1-3 are risky
    # (fixable=False, confirm); rules 4-5 are safe (fixable=True, auto-apply).
    simplicity_issues = scan_simplicity(marketplace_root)
    all_issues.extend(simplicity_issues)
    total_issues += len(simplicity_issues)

    # Marketplace-wide shell-substitution-in-skills rule. Unconditionally
    # active (not gated by --rules) because it enforces a hard rule from
    # dev-agent-behavior-rules and the analyzer is cheap (regex over markdown).
    shell_substitution_issues = analyze_shell_substitution_in_skills(marketplace_root)
    all_issues.extend(shell_substitution_issues)
    total_issues += len(shell_substitution_issues)

    # Marketplace-wide bash-chain-shapes-in-skills rule. Unconditionally
    # active — detects compound Bash command sequences (&&, ;, trailing &)
    # inside fenced bash/sh blocks in plan-marshall skill markdown.  Enforces
    # the dev-agent-behavior-rules "Bash: one command per call" hard rule.
    bash_chain_issues = analyze_bash_chain_shapes_in_skills(marketplace_root)
    all_issues.extend(bash_chain_issues)
    total_issues += len(bash_chain_issues)

    # Marketplace-wide tmp-redirect-in-skills rule. Unconditionally active —
    # detects > / >> redirects targeting /tmp/ or /var/tmp/ inside fenced
    # bash/sh blocks in plan-marshall skill markdown.  Enforces the project
    # policy that temporary files must live under .plan/temp/.
    tmp_redirect_issues = analyze_tmp_redirect_in_skills(marketplace_root)
    all_issues.extend(tmp_redirect_issues)
    total_issues += len(tmp_redirect_issues)

    # Marketplace-wide WORKFLOW_DOC_TOON_ERROR_FIELD rule. Unconditionally
    # active — flags the non-canonical ``error_type`` key inside fenced
    # ``toon`` workflow/agent error blocks in plan-marshall skill markdown.
    # The canonical error-envelope discriminator field is ``error`` (see
    # plan-marshall workflow/planning.md). Also wired into quality-gate
    # below — the normalization sweep guarantees zero residual findings.
    workflow_toon_error_field_issues = analyze_workflow_doc_toon_error_field(marketplace_root)
    all_issues.extend(workflow_toon_error_field_issues)
    total_issues += len(workflow_toon_error_field_issues)

    # Marketplace-wide MARKDOWN_LINK_BARE_FILENAME rule. Unconditionally active —
    # flags bare ``.md`` filename tokens in skill/agent/command prose (sibling
    # standards docs must be navigable relative markdown links, never an
    # unclickable ``name.md`` token) plus parent-path-missing relative links in
    # ``standards/`` files. Scans *.md under each bundle's
    # {skills,agents,commands} tree. Non-fixable guard with no suppression
    # mechanism. Also wired into quality-gate below.
    markdown_link_bare_filename_issues = analyze_markdown_link_bare_filename(marketplace_root)
    all_issues.extend(markdown_link_bare_filename_issues)
    total_issues += len(markdown_link_bare_filename_issues)

    # Marketplace-wide bash-fence-inline-code-exemption rule. Unconditionally
    # active — reintroduction guard that flags any analyzer module scanning
    # inside a bash/sh fence (defines _BASH_FENCE_INFO_STRINGS) that also
    # carries a markdown inline-code exemption (_INLINE_CODE_RE /
    # _inline_code_spans). Inside a bash fence backticks are command
    # substitution, not markdown inline-code, so the two are mutually exclusive
    # in a single analyzer.
    bash_fence_inline_code_issues = analyze_bash_fence_inline_code_exemption(marketplace_root)
    all_issues.extend(bash_fence_inline_code_issues)
    total_issues += len(bash_fence_inline_code_issues)

    # Marketplace-wide no-lesson-id-in-skill-prose rule. Unconditionally
    # active — strips narrative lesson-ID citations from skill prose while
    # exempting structural-provenance contexts and the lesson-domain
    # allowlist. Scans *.md AND *.py under each bundle's
    # {skills,agents,commands} tree PLUS the project-local .claude/skills/**
    # tree (the analyzer derives the .claude/skills path internally from
    # marketplace_root, so this call site needs only the bundles root).
    # Analyzer is regex-cheap.
    lesson_id_issues = analyze_lesson_id_in_skill_prose(marketplace_root)
    all_issues.extend(lesson_id_issues)
    total_issues += len(lesson_id_issues)

    # Marketplace-wide allowed-tools-body-drift rule. Unconditionally active —
    # flags any skill/agent/command whose body invokes a tool absent from a
    # declared, non-empty allowed-tools/tools frontmatter list. Skills that
    # omit the declaration entirely are NOT flagged (the "inherit all tools"
    # default; the fabricated unsupported-skill-tools-field rule stays retired).
    # Scans *.md under each bundle's {skills,agents,commands} tree PLUS the
    # project-local .claude/skills/** tree (derived internally from
    # marketplace_root). Analyzer is regex-cheap.
    allowed_tools_drift_issues = analyze_allowed_tools_drift(marketplace_root)
    all_issues.extend(allowed_tools_drift_issues)
    total_issues += len(allowed_tools_drift_issues)

    # Marketplace-wide skill-self-declared-rule-violation rule. Unconditionally
    # active — flags a SKILL.md that declares a flat-numbering / no-sub-numbering
    # rule in its own body yet uses sub-numbered (1a/3a/5a-style) step headings
    # in that same body. Self-referential: a file that uses sub-numbering
    # WITHOUT declaring such a rule is NOT flagged (not a global numbering ban).
    # Scans SKILL.md under each bundle's {skills,agents,commands} tree PLUS the
    # project-local .claude/skills/** tree (derived internally from
    # marketplace_root). Analyzer is regex-cheap.
    self_declared_rule_issues = analyze_self_declared_rule_compliance(marketplace_root)
    all_issues.extend(self_declared_rule_issues)
    total_issues += len(self_declared_rule_issues)

    # Marketplace-wide no-historical-prose-in-skills rule. Unconditionally
    # active — detects historical/transitional narrative (driving-lesson
    # prefixes, back-references, earlier-proposal descriptions, seed-failure
    # citations, plan-authorship annotations, guard-introduction prose) in
    # skill markdown. Skills must document present-tense rules, not history.
    historical_prose_issues = analyze_historical_prose_in_skills(marketplace_root)
    all_issues.extend(historical_prose_issues)
    total_issues += len(historical_prose_issues)

    # The manage-invocation rule cluster (manage-invocation-invalid +
    # missing-canonical-block) is intentionally NOT run here. It derives each
    # script's canonical surface from the script's live ``--help`` output (one
    # subprocess per parser node) — far heavier than analyze's other AST/regex
    # rules. Running it on every per-component ``analyze`` pass cold-derives the
    # whole marketplace surface and overruns the test harness's per-call
    # subprocess budget. The rule is the marketplace-wide authoritative gate and
    # runs only under ``cmd_quality_gate`` (which CI invokes as its own step with
    # the appropriate budget). ``test_analyze_does_not_run_manage_invocation_cluster``
    # guards against re-introducing it here.

    # Phase-5 step standards files MUST declare a ``role:`` frontmatter field
    # so the manage-execution-manifest composer's role-based intersection
    # (Rows 2/3/4/5) can resolve candidates correctly. Unconditionally active;
    # path-scoped to plan-marshall/skills/phase-5-execute/standards/*.md so
    # the analyzer's cost is bounded to a handful of files.
    role_field_issues = analyze_role_field(marketplace_root)
    all_issues.extend(role_field_issues)
    total_issues += len(role_field_issues)

    # Marketplace-wide reference-resolution rule cluster. Unconditionally
    # active — each analyzer is a cheap json/regex/filesystem pass over the
    # bundle tree, and each catches a class of declared-vs-discoverable drift
    # that resolves to a dead reference at runtime:
    #   - declared-component-vs-disk: plugin.json declares a component whose
    #     file is missing on disk (forward manifest check).
    #   - plugin-json-orphan-component: an on-disk user-invocable skill / agent
    #     / command is not declared in its bundle's plugin.json (reverse
    #     manifest check; advisory warning severity).
    #   - skill-notation-unresolved: a `Skill: {bundle}:{skill}` directive
    #     references a skill directory that does not exist.
    #   - recipe-missing-implements: a recipe-* skill omits / diverges from the
    #     `implements: …ext-point-recipe` frontmatter recipe discovery needs.
    declared_vs_disk_issues = analyze_declared_vs_disk(marketplace_root)
    all_issues.extend(declared_vs_disk_issues)
    total_issues += len(declared_vs_disk_issues)

    plugin_json_orphan_issues = analyze_plugin_json_orphans(marketplace_root)
    all_issues.extend(plugin_json_orphan_issues)
    total_issues += len(plugin_json_orphan_issues)

    skill_notation_issues = analyze_skill_notation(marketplace_root)
    all_issues.extend(skill_notation_issues)
    total_issues += len(skill_notation_issues)

    frontmatter_issues = analyze_frontmatter(marketplace_root)
    all_issues.extend(frontmatter_issues)
    total_issues += len(frontmatter_issues)

    # Marketplace-wide resolver-matrix-coverage rule. Unconditionally active —
    # AST scan over scripts is cheap and the rule emits ``tip``-severity
    # findings only (advisory, not build-failing). Detects N-input skip-on-
    # miss resolvers (>=3 tiers) whose test files lack a full
    # ``tier x {hit, miss}`` parametrize matrix. See
    # ``_analyze_resolver_matrix_coverage.py`` for the detection contract.
    resolver_matrix_issues = analyze_resolver_matrix_coverage(marketplace_root)
    all_issues.extend(resolver_matrix_issues)
    total_issues += len(resolver_matrix_issues)

    # Marketplace-wide script-call-drift rule. Gated OFF by default — opt in
    # via ``--rules script_call_drift``. The analyzer probes --help via
    # subprocess for every documented notation/verb pair, which costs many
    # process spawns on the full marketplace and is unsuitable for unconditional
    # runs. Replaces the removed runtime SUBCOMMANDS pre-flight validator
    # with dev-time drift detection.
    if 'script_call_drift' in active_rules:
        script_call_drift_issues = analyze_script_call_drift(marketplace_root)
        all_issues.extend(script_call_drift_issues)
        total_issues += len(script_call_drift_issues)

    # Marketplace-wide argument-naming rule cluster (notation/subcommand/
    # flag/Canonical-Forms cross-check). Gated OFF by default; opt in via
    # ``--rules argument_naming`` or the ``--enable-argument-naming`` alias.
    # Absence of the flag keeps the cluster silent (no findings, no warnings).
    if 'argument_naming' in active_rules:
        argument_naming_issues = analyze_argument_naming(marketplace_root)
        all_issues.extend(argument_naming_issues)
        total_issues += len(argument_naming_issues)

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
                                    the dev-agent-behavior-rules "no shell
                                    constructs" hard rule)
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

    argparse_findings = _scoped(scan_argparse_safety(marketplace_root))
    all_issues.extend(argparse_findings)
    rule_summaries.append({'rule': 'scan_argparse_safety', 'findings': len(argparse_findings)})

    # validate_extension_contracts ALWAYS runs whole-tree and is NEVER filtered,
    # even under --paths — extension-contract compliance has no per-path subset,
    # and a scoped gate must still catch a broken extension contract.
    contract_result = validate_extension_contracts(marketplace_root.parent)
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
    rule_summaries.append({'rule': 'validate_extension_contracts', 'findings': len(contract_errors)})

    naming_findings = _scoped(analyze_argument_naming(marketplace_root))
    all_issues.extend(naming_findings)
    rule_summaries.append({'rule': 'analyze_argument_naming', 'findings': len(naming_findings)})

    shell_substitution_findings = _scoped(analyze_shell_substitution_in_skills(marketplace_root))
    all_issues.extend(shell_substitution_findings)
    rule_summaries.append(
        {'rule': 'analyze_shell_substitution_in_skills', 'findings': len(shell_substitution_findings)}
    )

    # WORKFLOW_DOC_TOON_ERROR_FIELD — flags the non-canonical ``error_type`` key
    # inside fenced ``toon`` workflow/agent error blocks in plan-marshall skill
    # markdown. Quality-gate-active: the normalization sweep that established the
    # canonical ``error`` discriminator eliminated every fenced-TOON ``error_type``
    # key, so the post-sweep tree produces zero residual findings.
    workflow_toon_error_field_findings = _scoped(
        analyze_workflow_doc_toon_error_field(marketplace_root)
    )
    all_issues.extend(workflow_toon_error_field_findings)
    rule_summaries.append(
        {
            'rule': 'analyze_workflow_doc_toon_error_field',
            'findings': len(workflow_toon_error_field_findings),
        }
    )

    # MARKDOWN_LINK_BARE_FILENAME — flags bare ``.md`` filename tokens in
    # skill/agent/command prose plus parent-path-missing relative links in
    # ``standards/`` files. Quality-gate-active: runs unconditionally as a build
    # gate. Findings carry absolute file paths, so _scoped's path filter applies
    # under --paths.
    markdown_link_bare_filename_findings = _scoped(
        analyze_markdown_link_bare_filename(marketplace_root)
    )
    all_issues.extend(markdown_link_bare_filename_findings)
    rule_summaries.append(
        {
            'rule': 'analyze_markdown_link_bare_filename',
            'findings': len(markdown_link_bare_filename_findings),
        }
    )

    # bash-chain-shapes and tmp-redirect are intentionally NOT in quality-gate —
    # the existing marketplace tree pre-dates these rules and contains legitimate
    # documented examples of the forbidden patterns inside bash fences.  Adding
    # them to quality-gate would require a large upfront cleanup sweep before the
    # rules could enforce.  Invoke via ``analyze`` for explicit drift sweeps;
    # new code written after this plan is checked by the analyze path.

    # Scans *.md and *.py under each bundle's {skills,agents,commands} tree
    # PLUS the project-local .claude/skills/** tree (derived internally from
    # marketplace_root). Findings carry absolute file paths, so _scoped's
    # path filter applies uniformly to both trees under --paths.
    lesson_id_findings = _scoped(analyze_lesson_id_in_skill_prose(marketplace_root))
    all_issues.extend(lesson_id_findings)
    rule_summaries.append(
        {'rule': 'analyze_lesson_id_in_skill_prose', 'findings': len(lesson_id_findings)}
    )

    # allowed-tools-body-drift — flags body-invoked tools absent from a
    # declared non-empty allowed-tools/tools frontmatter list. Scans *.md under
    # each bundle's {skills,agents,commands} tree PLUS the project-local
    # .claude/skills/** tree (derived internally). Findings carry absolute file
    # paths, so _scoped's path filter applies uniformly under --paths.
    allowed_tools_drift_findings = _scoped(analyze_allowed_tools_drift(marketplace_root))
    all_issues.extend(allowed_tools_drift_findings)
    rule_summaries.append(
        {'rule': 'analyze_allowed_tools_drift', 'findings': len(allowed_tools_drift_findings)}
    )

    # skill-self-declared-rule-violation — flags a SKILL.md that declares a
    # flat-numbering / no-sub-numbering rule in its body yet uses sub-numbered
    # step headings in that same body. Self-referential (a file that uses
    # sub-numbering without declaring such a rule is not flagged). Scans
    # SKILL.md under each bundle's {skills,agents,commands} tree PLUS the
    # project-local .claude/skills/** tree (derived internally). Findings carry
    # absolute file paths, so _scoped's path filter applies uniformly under --paths.
    self_declared_rule_findings = _scoped(analyze_self_declared_rule_compliance(marketplace_root))
    all_issues.extend(self_declared_rule_findings)
    rule_summaries.append(
        {
            'rule': 'analyze_self_declared_rule_compliance',
            'findings': len(self_declared_rule_findings),
        }
    )

    historical_prose_findings = _scoped(analyze_historical_prose_in_skills(marketplace_root))
    all_issues.extend(historical_prose_findings)
    rule_summaries.append(
        {'rule': 'analyze_historical_prose_in_skills', 'findings': len(historical_prose_findings)}
    )

    # finalize-step-token-mismatch — flags a finalize-step skill whose documented
    # mark-step-done --step token (under --phase 6-finalize) diverges from the
    # skill's fully-qualified manifest step_id. Scans bundle SKILL.md files in
    # OPTIONAL_BUNDLE_FINALIZE_STEPS plus the project-local
    # .claude/skills/finalize-step-*/SKILL.md tree (derived internally). Findings
    # carry absolute file paths, so _scoped's path filter applies uniformly under
    # --paths.
    finalize_step_token_findings = _scoped(scan_finalize_step_token(marketplace_root))
    all_issues.extend(finalize_step_token_findings)
    rule_summaries.append(
        {'rule': 'scan_finalize_step_token', 'findings': len(finalize_step_token_findings)}
    )

    role_field_findings = _scoped(analyze_role_field(marketplace_root))
    all_issues.extend(role_field_findings)
    rule_summaries.append({'rule': 'analyze_role_field', 'findings': len(role_field_findings)})

    # manage-invocation rule cluster — validates documented script invocations
    # against each script-bearing skill's live argparse surface derived from
    # ``--help`` (manage-invocation-invalid) and flags script-bearing SKILL.md
    # files lacking a ``## Canonical invocations`` section
    # (missing-canonical-block). The surface is derived dynamically via
    # subprocesses and cached to disk, making it highly accurate and cheap
    # enough to run on every analyze pass. The in-scope set is derived from the
    # bundle tree, so it is a build-failing regression net against future
    # argparse-rejection drift.
    # ``find_marketplace_root`` returns the ``bundles/`` directory, but the
    # manage-invocation helpers expect the marketplace root (parent of
    # ``bundles/``) so their layout probing and executor discovery resolve —
    # the same ``.parent`` conversion already used for
    # ``validate_extension_contracts`` above.
    if scope_dirs:
        # Scoped: derive only the notations the scoped docs reference (never the
        # eager whole-marketplace build_script_index).
        manage_invocation_findings = _scoped_manage_invocation(marketplace_root.parent, scope_dirs)
    else:
        manage_invocation_findings = scan_manage_invocation(marketplace_root.parent)
    all_issues.extend(manage_invocation_findings)
    rule_summaries.append(
        {'rule': 'scan_manage_invocation', 'findings': len(manage_invocation_findings)}
    )

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
