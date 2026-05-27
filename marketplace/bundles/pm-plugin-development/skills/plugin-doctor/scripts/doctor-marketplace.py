#!/usr/bin/env python3
"""
doctor-marketplace.py - Batch marketplace analysis and fixing.

Provides automated batch operations across the entire marketplace:
- scan: Discover all components (agents, commands, skills, scripts)
- analyze: Batch analyze all components for issues (includes the
  hardcoded-model-on-canonical rule introduced by the role-variants plan;
  see plugin-doctor/standards/doctor-agents.md)
- fix: Apply safe fixes automatically across marketplace
- report: Generate comprehensive report for LLM review
- quality-gate: Run pure-static-analysis rules as a build gate
  (exit 1 on findings; intended for invocation from `quality-gate` build target)

This is Phase 1 of the hybrid doctor workflow. It handles deterministic
operations that can be fully automated. Phase 2 (LLM) handles semantic
analysis and complex fixes.

Output: TOON to stdout.

Usage:
    python3 doctor-marketplace.py scan [--bundles NAMES] [--paths PATH [PATH ...]]
    python3 doctor-marketplace.py analyze [--bundles NAMES] [--type TYPE] [--name NAME]
    python3 doctor-marketplace.py fix [--bundles NAMES] [--type TYPE] [--name NAME] [--dry-run]
    python3 doctor-marketplace.py report [--bundles NAMES] [--output FILE]
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from _analyze_argument_naming import analyze_argument_naming
from _analyze_historical_prose_in_skills import analyze_historical_prose_in_skills
from _analyze_lesson_id_in_skill_prose import analyze_lesson_id_in_skill_prose
from _analyze_role_field import analyze_role_field
from _analyze_script_call_drift import analyze_script_call_drift
from _analyze_shell_substitution_in_skills import analyze_shell_substitution_in_skills
from _analyze_test_conventions import (
    analyze_subprocess_pythonpath,
    analyze_unique_fixture_basenames,
    analyze_validator_regex_vs_corpus,
)
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
# This replaces the prior env-var gate (removed per lesson
# ``2026-05-08-19-003``) which violated the ``dev-agent-behavior-rules`` hard
# rule against ``VAR=val cmd`` invocations.

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


def _scan_paths(paths: list[str]) -> dict:
    """Scan explicitly provided component paths."""
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


def cmd_scan(args) -> dict:
    """Scan marketplace and list all components."""
    # --paths mode: resolve explicit paths, skip marketplace discovery
    if hasattr(args, 'paths') and args.paths:
        return _scan_paths(args.paths)

    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

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
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

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

    # Marketplace-wide shell-substitution-in-skills rule. Unconditionally
    # active (not gated by --rules) because it enforces a hard rule from
    # dev-agent-behavior-rules and the analyzer is cheap (regex over markdown).
    shell_substitution_issues = analyze_shell_substitution_in_skills(marketplace_root)
    all_issues.extend(shell_substitution_issues)
    total_issues += len(shell_substitution_issues)

    # Marketplace-wide no-lesson-id-in-skill-prose rule. Unconditionally
    # active — strips narrative lesson-ID citations from skill prose while
    # exempting structural-provenance contexts and the lesson-domain
    # allowlist. Analyzer is regex-cheap.
    lesson_id_issues = analyze_lesson_id_in_skill_prose(marketplace_root)
    all_issues.extend(lesson_id_issues)
    total_issues += len(lesson_id_issues)

    # Marketplace-wide no-historical-prose-in-skills rule. Unconditionally
    # active — detects historical/transitional narrative (driving-lesson
    # prefixes, back-references, earlier-proposal descriptions, seed-failure
    # citations, plan-authorship annotations, guard-introduction prose) in
    # skill markdown. Skills must document present-tense rules, not history.
    historical_prose_issues = analyze_historical_prose_in_skills(marketplace_root)
    all_issues.extend(historical_prose_issues)
    total_issues += len(historical_prose_issues)

    # Phase-5 step standards files MUST declare a ``role:`` frontmatter field
    # so the manage-execution-manifest composer's role-based intersection
    # (Rows 2/3/4/5) can resolve candidates correctly. Unconditionally active;
    # path-scoped to plan-marshall/skills/phase-5-execute/standards/*.md so
    # the analyzer's cost is bounded to a handful of files.
    role_field_issues = analyze_role_field(marketplace_root)
    all_issues.extend(role_field_issues)
    total_issues += len(role_field_issues)

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
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

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
                                    quality-gate per lesson
                                    ``2026-04-29-23-002``; ``--rules``
                                    opt-in only applies to the ``analyze``
                                    subcommand)
      - analyze_shell_substitution_in_skills (forbidden ``$(`` patterns in
                                    plan-marshall skill markdown — enforces
                                    the dev-agent-behavior-rules "no shell
                                    constructs" hard rule per lesson
                                    ``2026-05-15-13-001``)
    """
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

    # quality-gate is intentionally marketplace-wide — bundle filtering would
    # break the "real marketplace must produce zero findings" invariant the
    # gate exists to enforce. No --bundles flag is exposed.
    all_issues: list[dict] = []
    rule_summaries: list[dict] = []

    argparse_findings = scan_argparse_safety(marketplace_root)
    all_issues.extend(argparse_findings)
    rule_summaries.append({'rule': 'scan_argparse_safety', 'findings': len(argparse_findings)})

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

    naming_findings = analyze_argument_naming(marketplace_root)
    all_issues.extend(naming_findings)
    rule_summaries.append({'rule': 'analyze_argument_naming', 'findings': len(naming_findings)})

    shell_substitution_findings = analyze_shell_substitution_in_skills(marketplace_root)
    all_issues.extend(shell_substitution_findings)
    rule_summaries.append(
        {'rule': 'analyze_shell_substitution_in_skills', 'findings': len(shell_substitution_findings)}
    )

    lesson_id_findings = analyze_lesson_id_in_skill_prose(marketplace_root)
    all_issues.extend(lesson_id_findings)
    rule_summaries.append(
        {'rule': 'analyze_lesson_id_in_skill_prose', 'findings': len(lesson_id_findings)}
    )

    historical_prose_findings = analyze_historical_prose_in_skills(marketplace_root)
    all_issues.extend(historical_prose_findings)
    rule_summaries.append(
        {'rule': 'analyze_historical_prose_in_skills', 'findings': len(historical_prose_findings)}
    )

    role_field_findings = analyze_role_field(marketplace_root)
    all_issues.extend(role_field_findings)
    rule_summaries.append({'rule': 'analyze_role_field', 'findings': len(role_field_findings)})

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
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

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
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

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


@safe_main
def cmd_validate_contracts(args) -> dict:
    """Validate extension point contract compliance."""
    marketplace_root = find_marketplace_root(getattr(args, 'marketplace_root', None))
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

    return validate_extension_contracts(
        marketplace_root,
        extension_type=args.extension_type,
        skill_filter=args.skill,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Batch marketplace analysis and fixing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
Examples:
  # Scan entire marketplace
  %(prog)s scan

  # Scan specific bundles
  %(prog)s scan --bundles pm-dev-java,plan-marshall

  # Scan explicit component paths
  %(prog)s scan --paths marketplace/bundles/plan-marshall/skills/phase-4-plan

  # Scan multiple paths (marketplace and project-local)
  %(prog)s scan --paths marketplace/bundles/plan-marshall/skills/phase-4-plan .claude/skills/my-skill

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

    # scan subcommand
    p_scan = subparsers.add_parser('scan', help='Scan marketplace components', allow_abbrev=False)
    scan_source = p_scan.add_mutually_exclusive_group()
    scan_source.add_argument('--bundles', help='Comma-separated list of bundle names to scan')
    scan_source.add_argument(
        '--paths', nargs='+', help='Explicit component paths to scan (mutually exclusive with --bundles)'
    )
    p_scan.add_argument('--marketplace-root', dest='marketplace_root', help=marketplace_root_help)
    p_scan.set_defaults(func=cmd_scan)

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
        help='Run pure-static-analysis rules as a build gate (exit 1 on findings, marketplace-wide only)',
        allow_abbrev=False,
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
    sys.exit(main())
