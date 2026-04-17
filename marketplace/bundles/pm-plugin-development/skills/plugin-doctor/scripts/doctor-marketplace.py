#!/usr/bin/env python3
"""
doctor-marketplace.py - Batch marketplace analysis and fixing.

Provides automated batch operations across the entire marketplace:
- scan: Discover all components (agents, commands, skills, scripts)
- analyze: Batch analyze all components for issues
- fix: Apply safe fixes automatically across marketplace
- report: Generate comprehensive report for LLM review

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
from datetime import UTC, datetime
from pathlib import Path

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

    marketplace_root = find_marketplace_root()
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
    marketplace_root = find_marketplace_root()
    if not marketplace_root:
        return {'status': 'error', 'error': 'not_found', 'message': 'Marketplace directory not found'}

    bundles = find_bundles(marketplace_root, parse_csv_filter(args.bundles))
    component_list = collect_filtered_components(bundles, parse_csv_filter(args.type), parse_csv_filter(args.name))

    all_analysis = []
    total_issues = 0

    for component in component_list:
        result = analyze_component(component)
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
    marketplace_root = find_marketplace_root()
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


def cmd_report(args) -> dict:
    """Generate comprehensive report for LLM review."""
    marketplace_root = find_marketplace_root()
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
    marketplace_root = find_marketplace_root()
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

    # scan subcommand
    p_scan = subparsers.add_parser('scan', help='Scan marketplace components', allow_abbrev=False)
    scan_source = p_scan.add_mutually_exclusive_group()
    scan_source.add_argument('--bundles', help='Comma-separated list of bundle names to scan')
    scan_source.add_argument('--paths', nargs='+', help='Explicit component paths to scan (mutually exclusive with --bundles)')
    p_scan.set_defaults(func=cmd_scan)

    # analyze subcommand
    p_analyze = subparsers.add_parser('analyze', help='Analyze all components for issues', allow_abbrev=False)
    p_analyze.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_analyze.add_argument('--type', help='Component types to analyze (agents,commands,skills)')
    p_analyze.add_argument('--name', help='Comma-separated component names to filter (e.g., phase-4-plan)')
    p_analyze.set_defaults(func=cmd_analyze)

    # fix subcommand
    p_fix = subparsers.add_parser('fix', help='Apply safe fixes across marketplace', allow_abbrev=False)
    p_fix.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_fix.add_argument('--type', help='Component types to fix (agents,commands,skills)')
    p_fix.add_argument('--name', help='Comma-separated component names to filter (e.g., phase-4-plan)')
    p_fix.add_argument('--dry-run', action='store_true', help='Preview fixes without applying')
    p_fix.set_defaults(func=cmd_fix)

    # report subcommand
    p_report = subparsers.add_parser('report', help='Generate comprehensive report', allow_abbrev=False)
    p_report.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_report.add_argument('--output', '-o', help='Output directory for report')
    p_report.set_defaults(func=cmd_report)

    # validate-contracts subcommand
    p_contracts = subparsers.add_parser('validate-contracts', help='Validate extension point contract compliance', allow_abbrev=False)
    p_contracts.add_argument('--extension-type', help='Filter by extension type (triage,outline,recipe,build,credential)')
    p_contracts.add_argument('--skill', help='Filter by specific skill (bundle:skill or skill-name)')
    p_contracts.set_defaults(func=cmd_validate_contracts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
