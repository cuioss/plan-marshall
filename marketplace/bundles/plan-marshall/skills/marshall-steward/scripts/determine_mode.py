#!/usr/bin/env python3
"""
Plan-marshall helper script for mode detection and documentation checks.

Subcommands:
    mode                          Determine wizard vs menu mode based on existing files
    check-docs                    Check if project docs need .plan/temp documentation
    fix-docs                      Deterministically fix missing documentation content
    check-structure               Check if the per-module project-architecture layout exists
    seed-blocking-finding-types   Idempotently seed default phase-boundary
                                  blocking-finding partitions into marshal.json

Note: check-docs and check-structure overlap with menu-healthcheck steps 2 and 5.
The healthcheck runs these same checks via the menu path; this script provides
direct CLI access for the wizard flow and first-run bootstrap (before the
executor exists).

Usage:
    python3 determine_mode.py mode
    python3 determine_mode.py check-docs
    python3 determine_mode.py fix-docs
    python3 determine_mode.py check-structure
    python3 determine_mode.py seed-blocking-finding-types

Output (TOON format):
    mode subcommand:
        mode	wizard
        reason	executor_missing

    check-docs subcommand:
        status	ok
        missing_count	0

        status	needs_update
        missing_count	2
        plan_temp	CLAUDE.md,agents.md
        file_ops	CLAUDE.md

    fix-docs subcommand:
        status	ok
        fixed_count	0

        status	fixed
        fixed_count	2
        fixes	plan_temp:CLAUDE.md,file_ops:CLAUDE.md

    check-structure subcommand:
        status	exists
        path	.plan/project-architecture
        modules_count	3

        status	missing
        path	.plan/project-architecture
        modules_count	0

    seed-blocking-finding-types subcommand:
        status	success
        seed_status	seeded
        seeded_count	6
        skipped_count	0
        seeded	phase-1-init,phase-2-refine,phase-3-outline,phase-4-plan,phase-5-execute,phase-6-finalize

        status	success
        seed_status	unchanged
        seeded_count	0
        skipped_count	6
        skipped	phase-1-init,phase-2-refine,phase-3-outline,phase-4-plan,phase-5-execute,phase-6-finalize

        status	success
        seed_status	missing_marshal
        seeded_count	0
        skipped_count	0
"""

import argparse
import sys
from pathlib import Path

# Bootstrap sys.path — this script runs before the executor sets up PYTHONPATH.
# Step 1: locate script-shared/scripts via identity walk so we can import the
# shared anchor helper. Step 2: use resolve_skills_root to derive _SKILLS_DIR.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from marketplace_bundles import resolve_skills_root  # type: ignore[import-not-found]  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format',):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

# Content checks applied to project documentation files.
# Each check has a key, the files it applies to, and a substring marker
# to search for (plain string match, not regex).
CONTENT_CHECKS: list[dict[str, str | int | list[str]]] = [
    {
        'key': 'plan_temp',
        'files': ['CLAUDE.md', 'agents.md'],
        'pattern': '.plan/temp',
    },
    {
        'key': 'file_ops',
        'files': ['CLAUDE.md'],
        'pattern': 'use Glob, Read, Grep',
    },
]

# Verbatim content blocks appended by fix-docs when a check is missing.
# Keys must match CONTENT_CHECKS keys. Values are the exact text to append.
FIX_CONTENT: dict[str, str] = {
    'plan_temp': (
        '\n## Temporary Files\n'
        '\n'
        'Use `.plan/temp/` for ALL temporary and generated files '
        '(covered by `Write(.plan/**)` permission — avoids permission prompts).\n'
    ),
    'file_ops': (
        '\n## Tool Usage\n'
        '\n'
        '- Use proper tools (Edit, Read, Write) instead of shell commands (echo, cat)\n'
        '- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead\n'
    ),
}


def determine_mode(plan_dir: Path) -> tuple[str, str]:
    """
    Determine operational mode based on existing files.

    Both files live in the repo-local ``.plan/`` directory: marshal.json
    is tracked, and ``execute-script.py`` is the repo-local shim that
    marshall-steward writes alongside the real global executor. The shim
    is the authoritative bootstrap marker — if it exists, the system has
    been initialized for this checkout.

    Args:
        plan_dir: Path to the repo-local ``.plan/`` directory.

    Returns:
        Tuple of (mode, reason) where mode is 'wizard' or 'menu'
    """
    executor_exists = (plan_dir / 'execute-script.py').exists()
    marshal_exists = (plan_dir / 'marshal.json').exists()

    if not executor_exists:
        return 'wizard', 'executor_missing'
    elif not marshal_exists:
        return 'wizard', 'marshal_missing'
    else:
        return 'menu', 'both_exist'


def check_structure(plan_dir: Path) -> tuple[str, Path, int]:
    """
    Check if the per-module project-architecture layout exists.

    The per-module layout consists of a top-level ``_project.json`` (the
    source of truth for "which modules exist") plus one subdirectory per
    module containing ``derived.json`` and ``enriched.json``. The
    ``_project.json`` ``modules`` index is authoritative — orphan or
    half-written per-module directories are ignored. The layout is
    considered to exist when ``_project.json`` parses successfully and at
    least one module from its index has a readable ``derived.json``.

    Args:
        plan_dir: Path to the .plan directory

    Returns:
        Tuple of (status, path, valid_modules_count) where status is
        'exists' or 'missing' and valid_modules_count is the number of
        per-module entries from ``_project.json["modules"]`` whose
        ``derived.json`` file is present on disk.
    """
    import json

    arch_dir = plan_dir / 'project-architecture'
    project_path = arch_dir / '_project.json'

    if not project_path.is_file():
        return 'missing', arch_dir, 0

    try:
        project_data = json.loads(project_path.read_text())
    except (json.JSONDecodeError, OSError):
        return 'missing', arch_dir, 0

    modules = project_data.get('modules')
    if not isinstance(modules, dict) or not modules:
        return 'missing', arch_dir, 0

    valid_count = 0
    for module_name in modules:
        derived_path = arch_dir / module_name / 'derived.json'
        if derived_path.is_file():
            valid_count += 1

    if valid_count == 0:
        return 'missing', arch_dir, 0
    return 'exists', arch_dir, valid_count


# ---------------------------------------------------------------------------
# Default phase-boundary blocking-finding partition.
#
# Each entry maps a marshal.json phase slot (`plan.phase-{phase}`) to the list
# of finding types whose presence in `pending` resolution should refuse the
# phase boundary advance. The handshake invariant
# `pending_findings_blocking_count` reads this slot at capture time.
#
# The partition mirrors the design contract documented in
# `plan-marshall/references/phase-handshake.md`:
#
#   - Block at every phase boundary: build-error, test-failure, lint-issue,
#     sonar-issue, qgate.
#   - Block only inside `6-finalize`: pr-comment (PR review feedback is only
#     meaningful once a PR exists, which happens during finalize).
#   - Never block: long-lived knowledge types (insight, tip, best-practice,
#     improvement) — these accumulate across plans and should not gate an
#     active boundary.
#
# Projects override by editing `marshal.json` directly. The seed only writes
# when the phase slot does not yet contain a `blocking_finding_types` key,
# so re-running the wizard never clobbers user customisations.
# ---------------------------------------------------------------------------

# Global block list — applied to every plan phase except where a phase-specific
# partition supersedes it. The handshake's guarded-boundary set determines
# *where* a non-empty count actually refuses to persist; the partition itself
# determines *which* types contribute to the count.
_GLOBAL_BLOCKING_TYPES = [
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'qgate',
]

# pr-comment is only relevant during 6-finalize (after the PR exists), so the
# global list is augmented only at that phase.
_FINALIZE_BLOCKING_TYPES = _GLOBAL_BLOCKING_TYPES + ['pr-comment']

# Per-phase default partition. Phases not listed below inherit
# `_GLOBAL_BLOCKING_TYPES`. The map is the source of truth for the seed; the
# wizard step writes into `marshal.json["plan"][phase]["blocking_finding_types"]`
# only when that key is absent (idempotent).
_DEFAULT_BLOCKING_PARTITION: dict[str, list[str]] = {
    'phase-1-init': list(_GLOBAL_BLOCKING_TYPES),
    'phase-2-refine': list(_GLOBAL_BLOCKING_TYPES),
    'phase-3-outline': list(_GLOBAL_BLOCKING_TYPES),
    'phase-4-plan': list(_GLOBAL_BLOCKING_TYPES),
    'phase-5-execute': list(_GLOBAL_BLOCKING_TYPES),
    'phase-6-finalize': list(_FINALIZE_BLOCKING_TYPES),
}


def seed_blocking_finding_types(plan_dir: Path) -> tuple[str, list[str], list[str]]:
    """Idempotently seed default `blocking_finding_types` partitions into marshal.json.

    Walks every phase slot in :data:`_DEFAULT_BLOCKING_PARTITION` and writes
    the configured list into `marshal.json["plan"][phase]["blocking_finding_types"]`
    **only when that key is absent** in the existing file. Phase slots that
    already declare the key are left untouched — the seed never clobbers a
    user customisation. Phase slots that are missing entirely are created
    with the partition as their sole field; later config writes merge over
    that minimal slot via the standard `manage-config` set path.

    The function is the wizard's bridge between "marshal.json was just
    initialised" and "the phase-handshake invariant has the data it needs to
    enforce the blocking-finding gate". It runs once per first-run wizard
    invocation; subsequent invocations skip every phase whose slot already
    contains the key (status `unchanged`).

    Args:
        plan_dir: Path to the repo-local ``.plan/`` directory containing
                  ``marshal.json``. The script never writes elsewhere.

    Returns:
        Tuple of ``(status, seeded_phases, skipped_phases)`` where:

        - ``status`` is ``seeded`` when at least one phase was written,
          ``unchanged`` when every phase already had the key, or
          ``missing_marshal`` when ``marshal.json`` does not exist.
        - ``seeded_phases`` lists the phase slots whose key was newly
          written (in declaration order).
        - ``skipped_phases`` lists the phase slots whose key was already
          present (in declaration order).
    """
    import json as _json

    marshal_path = plan_dir / 'marshal.json'
    if not marshal_path.is_file():
        return 'missing_marshal', [], []

    try:
        config = _json.loads(marshal_path.read_text())
    except (OSError, _json.JSONDecodeError):
        return 'missing_marshal', [], []

    if not isinstance(config, dict):
        return 'missing_marshal', [], []

    plan_section = config.setdefault('plan', {})
    if not isinstance(plan_section, dict):
        # Defensive: an unexpectedly-shaped 'plan' section gets replaced
        # with a fresh dict so the seed can proceed without losing the
        # outer config.
        plan_section = {}
        config['plan'] = plan_section

    seeded: list[str] = []
    skipped: list[str] = []

    for phase, blocking_types in _DEFAULT_BLOCKING_PARTITION.items():
        phase_section = plan_section.get(phase)
        if not isinstance(phase_section, dict):
            phase_section = {}
            plan_section[phase] = phase_section

        if 'blocking_finding_types' in phase_section:
            skipped.append(phase)
            continue

        # Write a defensive copy so future seeds cannot mutate the
        # canonical default partition through the saved JSON object.
        phase_section['blocking_finding_types'] = list(blocking_types)
        seeded.append(phase)

    if not seeded:
        return 'unchanged', [], skipped

    marshal_path.write_text(_json.dumps(config, indent=2) + '\n')
    return 'seeded', seeded, skipped


def count_section_bullets(content: str, section_heading: str) -> int:
    """
    Count top-level bulleted lines under a Markdown section heading.

    Locates the line containing ``section_heading`` (matched as a substring,
    so the heading-level prefix `##`/`###` does not need to be specified by
    callers), then counts subsequent lines that begin with ``- `` until the
    next Markdown heading line (`# `, `## `, `### `, etc.) or end-of-file.

    Only first-level bullets count: continuation lines and nested items
    (lines beginning with whitespace) are ignored.

    Args:
        content: Full text of the document.
        section_heading: Substring that uniquely identifies the section
            heading line (e.g., ``Workflow Discipline (Hard Rules)``).

    Returns:
        Number of top-level bullets found, or 0 when the section is absent.
    """
    lines = content.splitlines()
    in_section = False
    bullet_count = 0

    for line in lines:
        stripped = line.lstrip()
        if not in_section:
            # Find the section heading. Require it to be a heading line (#-prefixed)
            # so we don't false-match the literal substring inside body prose.
            if stripped.startswith('#') and section_heading in line:
                in_section = True
            continue

        # We're inside the target section. Stop on the next heading line.
        if stripped.startswith('#') and ' ' in stripped[: stripped.find(' ') + 1]:
            # A heading line begins with one-or-more `#` followed by a space.
            hashes = len(stripped) - len(stripped.lstrip('#'))
            if hashes >= 1 and stripped[hashes : hashes + 1] == ' ':
                break

        # Count only top-level bullets: line begins with `- ` (no leading
        # whitespace).
        if line.startswith('- '):
            bullet_count += 1

    return bullet_count


def check_docs(project_root: Path) -> tuple[str, list[dict[str, str]]]:
    """
    Check if project documentation files contain all required content.

    Checks multiple content patterns across documentation files.
    Each check has a key, target files, and a marker pattern.

    For checks that declare ``min_bullets`` and ``section_heading`` (e.g., the
    workflow_discipline check), additionally count bullets under the named
    section. When the section is present but the bullet count is below
    ``min_bullets``, surface an ``incomplete`` reason instead of the default
    ``content_missing`` reason. When the section is absent altogether the
    pattern check fires as before — drift detection only applies when the
    section is present-but-short.

    Args:
        project_root: Path to the project root

    Returns:
        Tuple of (status, list of missing check dicts with 'file', 'check',
        and 'reason' keys; entries with ``reason='incomplete'`` also include
        ``found`` and ``expected`` bullet counts)
    """
    missing: list[dict[str, str]] = []

    for check in CONTENT_CHECKS:
        pattern = str(check['pattern'])
        files = check['files']
        assert isinstance(files, list)
        min_bullets_raw = check.get('min_bullets')
        section_heading_raw = check.get('section_heading')
        for file_name in files:
            file_path = project_root / str(file_name)
            if not file_path.exists():
                continue  # Skip non-existent files — only check content in existing files
            content = file_path.read_text()
            if pattern not in content:
                missing.append({'file': str(file_name), 'check': str(check['key']), 'reason': 'content_missing'})
                continue

            # Pattern is present. If this check declares a bullet-count
            # expectation, evaluate drift: section present-but-short ->
            # 'incomplete'.
            if isinstance(min_bullets_raw, int) and isinstance(section_heading_raw, str):
                found = count_section_bullets(content, section_heading_raw)
                if found < min_bullets_raw:
                    missing.append(
                        {
                            'file': str(file_name),
                            'check': str(check['key']),
                            'reason': 'incomplete',
                            'found': str(found),
                            'expected': str(min_bullets_raw),
                        }
                    )

    if missing:
        return 'needs_update', missing
    else:
        return 'ok', []


def fix_docs(project_root: Path) -> tuple[str, list[str]]:
    """
    Deterministically fix missing documentation content.

    Runs check_docs to find missing content, then appends the exact
    verbatim text from FIX_CONTENT to the appropriate files.

    Args:
        project_root: Path to the project root

    Returns:
        Tuple of (status, list of fix descriptions like 'plan_temp:CLAUDE.md')
    """
    status, missing = check_docs(project_root)
    if status == 'ok':
        return 'ok', []

    fixes: list[str] = []
    for entry in missing:
        # Drift entries (section present-but-short) cannot be fixed by
        # appending — that would create a duplicate section. Leave the file
        # untouched and let the operator reconcile manually; the doctor
        # message surfaced by cmd_check_docs guides the edit.
        if entry.get('reason') == 'incomplete':
            continue

        check_key = entry['check']
        file_name = entry['file']
        content_block = FIX_CONTENT.get(check_key)
        if content_block is None:
            continue

        file_path = project_root / file_name
        if not file_path.exists():
            continue

        existing = file_path.read_text()
        # Ensure trailing newline before appending
        if existing and not existing.endswith('\n'):
            existing += '\n'
        file_path.write_text(existing + content_block)
        fixes.append(f'{check_key}:{file_name}')

    return 'fixed' if fixes else 'ok', fixes


def cmd_fix_docs(args: argparse.Namespace) -> dict:
    """Handle the 'fix-docs' subcommand."""
    project_root = Path(args.project_root)
    status, fixes = fix_docs(project_root)

    result: dict = {'status': 'success', 'fix_status': status, 'fixed_count': len(fixes)}
    if fixes:
        result['fixes'] = ','.join(fixes)
    return result


def cmd_mode(args: argparse.Namespace) -> dict:
    """Handle the 'mode' subcommand."""
    plan_dir = Path(args.plan_dir)
    mode, reason = determine_mode(plan_dir)

    return {'status': 'success', 'mode': mode, 'reason': reason}


def cmd_check_docs(args: argparse.Namespace) -> dict:
    """Handle the 'check-docs' subcommand."""
    project_root = Path(args.project_root)
    status, missing = check_docs(project_root)

    result: dict = {'status': 'success', 'check_status': status, 'missing_count': len(missing)}
    if missing:
        # Group by check key for easy consumption
        checks_by_key: dict[str, list[str]] = {}
        for entry in missing:
            key = entry['check']
            if key not in checks_by_key:
                checks_by_key[key] = []
            checks_by_key[key].append(entry['file'])
        for key, files in checks_by_key.items():
            result[key] = ','.join(files)

        # Surface human-readable doctor messages for 'incomplete' (drift)
        # entries so callers can distinguish absent sections from
        # present-but-short ones without re-parsing the structured payload.
        messages: list[str] = []
        for entry in missing:
            if entry.get('reason') != 'incomplete':
                continue
            label = entry['check'].replace('_', ' ').title()
            messages.append(
                f'{label} section present but incomplete '
                f'(found {entry.get("found", "?")} bullets, expected {entry.get("expected", "?")})'
            )
        if messages:
            result['messages'] = ' | '.join(messages)
    return result


def cmd_check_structure(args: argparse.Namespace) -> dict:
    """Handle the 'check-structure' subcommand."""
    plan_dir = Path(args.plan_dir)
    status, path, modules_count = check_structure(plan_dir)

    return {
        'status': 'success',
        'check_status': status,
        'path': str(path),
        'modules_count': modules_count,
    }


def cmd_seed_blocking_finding_types(args: argparse.Namespace) -> dict:
    """Handle the 'seed-blocking-finding-types' subcommand.

    Returns TOON-shaped dict with:

    - ``status``: always ``success`` for the script-level operation; the
      actual seed outcome is in ``seed_status``.
    - ``seed_status``: ``seeded`` (at least one phase written),
      ``unchanged`` (all phases already had the key), or
      ``missing_marshal`` (no marshal.json to seed).
    - ``seeded_count`` / ``skipped_count``: row counts for downstream
      formatting.
    - ``seeded`` / ``skipped``: comma-separated phase keys when non-empty
      so the wizard can surface the operator-facing detail without
      double-parsing.
    """
    plan_dir = Path(args.plan_dir)
    seed_status, seeded, skipped = seed_blocking_finding_types(plan_dir)

    result: dict = {
        'status': 'success',
        'seed_status': seed_status,
        'seeded_count': len(seeded),
        'skipped_count': len(skipped),
    }
    if seeded:
        result['seeded'] = ','.join(seeded)
    if skipped:
        result['skipped'] = ','.join(skipped)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan-marshall helper for mode detection and documentation checks',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # mode subcommand
    mode_parser = subparsers.add_parser('mode', help='Determine wizard vs menu mode', allow_abbrev=False)
    mode_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    # check-docs subcommand
    docs_parser = subparsers.add_parser(
        'check-docs', help='Check if project docs need .plan/temp documentation', allow_abbrev=False
    )
    docs_parser.add_argument('--project-root', type=str, default='.', help='Project root directory (default: .)')

    # fix-docs subcommand
    fix_parser = subparsers.add_parser(
        'fix-docs', help='Deterministically fix missing documentation content', allow_abbrev=False
    )
    fix_parser.add_argument('--project-root', type=str, default='.', help='Project root directory (default: .)')

    # check-structure subcommand
    structure_parser = subparsers.add_parser(
        'check-structure',
        help='Check if the per-module project-architecture layout exists',
        allow_abbrev=False,
    )
    structure_parser.add_argument('--plan-dir', type=str, default='.plan', help='Directory to check (default: .plan)')

    # seed-blocking-finding-types subcommand
    seed_parser = subparsers.add_parser(
        'seed-blocking-finding-types',
        help='Idempotently seed default phase-boundary blocking-finding partitions into marshal.json',
        allow_abbrev=False,
    )
    seed_parser.add_argument(
        '--plan-dir',
        type=str,
        default='.plan',
        help='Directory containing marshal.json (default: .plan)',
    )

    args = parser.parse_args()

    if args.command == 'mode':
        result = cmd_mode(args)
    elif args.command == 'check-docs':
        result = cmd_check_docs(args)
    elif args.command == 'fix-docs':
        result = cmd_fix_docs(args)
    elif args.command == 'check-structure':
        result = cmd_check_structure(args)
    elif args.command == 'seed-blocking-finding-types':
        result = cmd_seed_blocking_finding_types(args)
    else:
        parser.print_help()
        return 1

    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
