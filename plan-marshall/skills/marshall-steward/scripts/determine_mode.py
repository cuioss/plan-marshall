#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Plan-marshall helper script for mode detection and documentation checks.

Subcommands:
    mode                          Determine wizard vs menu mode based on existing files
    check-docs                    Check if project docs need .plan/temp documentation
    fix-docs                      Deterministically fix missing documentation content
    check-structure               Check if the per-module project-architecture layout exists
    check-worktree-plan-local     Refuse-or-scaffold guard: ensure a worktree owns its
                                  own .plan/local before executor generation, so it cannot
                                  contaminate the main checkout's .plan/execute-script.py
    check-working-prefixes        Detect absence or drift of project.working_prefixes
                                  against the canonical default (non-clobbering)

Note: check-docs and check-structure overlap with menu-healthcheck steps 2 and 5.
The healthcheck runs these same checks via the menu path; this script provides
direct CLI access for the wizard flow and first-run bootstrap (before the
executor exists).

Usage:
    python3 determine_mode.py mode
    python3 determine_mode.py check-docs
    python3 determine_mode.py fix-docs
    python3 determine_mode.py check-structure
    python3 determine_mode.py check-worktree-plan-local --repo-root PATH [--scaffold]
    python3 determine_mode.py check-working-prefixes

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

    check-worktree-plan-local subcommand:
        status	ok
        repo_root	/path/to/main-checkout
        plan_local	/path/to/main-checkout/.plan/local
        is_worktree	false

        status	refuse
        repo_root	/path/to/.plan/local/worktrees/my-plan
        plan_local	/path/to/.plan/local/worktrees/my-plan/.plan/local
        is_worktree	true
        detail	Worktree ... lacks its own .plan/local — refusing ...

        status	scaffolded
        repo_root	/path/to/.plan/local/worktrees/my-plan
        plan_local	/path/to/.plan/local/worktrees/my-plan/.plan/local
        is_worktree	true

    check-working-prefixes subcommand:
        status	ok

        status	missing
        detail	absent
        missing_keys	working_prefixes

        status	missing
        detail	drift
        missing_keys	working_prefixes
"""

import argparse
import json
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
from marketplace_paths import iter_project_skill_dirs  # type: ignore[import-not-found]  # noqa: E402

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
    module containing ``enriched.json`` (an LLM-curated stub seeded by
    ``architecture discover``). The ``_project.json`` ``modules`` index is
    authoritative — orphan or half-written per-module directories are
    ignored. The layout is considered to exist when ``_project.json``
    parses successfully and at least one module from its index has a
    readable ``enriched.json`` on disk.

    Note: ``derived.json`` is intentionally NOT used as a marker. Derived
    module data (paths, packages, dependencies, file inventories) is
    ephemeral under the on-demand crawl model — see
    ``manage-architecture/scripts/_architecture_core.py`` — and is not
    written by normal operation.

    Args:
        plan_dir: Path to the .plan directory

    Returns:
        Tuple of (status, path, valid_modules_count) where status is
        'exists' or 'missing' and valid_modules_count is the number of
        per-module entries from ``_project.json["modules"]`` whose
        ``enriched.json`` file is present on disk.
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
        enriched_path = arch_dir / module_name / 'enriched.json'
        if enriched_path.is_file():
            valid_count += 1

    if valid_count == 0:
        return 'missing', arch_dir, 0
    return 'exists', arch_dir, valid_count


_WORKTREE_SEGMENT = '/.plan/local/worktrees/'


def is_worktree_repo_root(repo_root: Path) -> bool:
    """Return ``True`` when ``repo_root`` is a plan-marshall worktree checkout.

    A worktree checkout lives under ``.plan/local/worktrees/`` in the main
    checkout's tree. The detection is purely path-based (mirroring the
    wizard-flow signal): the resolved repo-top-level path contains the
    ``/.plan/local/worktrees/`` segment. The main checkout never does.
    """
    return _WORKTREE_SEGMENT in str(repo_root.resolve()).replace('\\', '/') + '/'


def check_worktree_plan_local(repo_root: Path, scaffold: bool) -> tuple[str, Path]:
    """Refuse-or-scaffold guard for worktree executor generation.

    Before marshall-steward generates an executor from a worktree
    (``generate_executor --marketplace-root <REPO_ROOT>``), the worktree MUST
    own its own ``.plan/local`` directory. Without it, the executor-gen path
    climbs to the *main* checkout's ``.plan/local`` (the nearest ancestor
    containing it) and contaminates main's ``.plan/execute-script.py`` — the
    exact failure this guard prevents.

    Behaviour:

    - ``repo_root`` is NOT a worktree (main checkout): return ``('ok', plan_local)``
      unconditionally — the guard only governs worktree generation.
    - ``repo_root`` IS a worktree and ``<repo_root>/.plan/local`` exists: return
      ``('ok', plan_local)``.
    - ``repo_root`` IS a worktree and ``<repo_root>/.plan/local`` is absent:
        * ``scaffold=False`` → return ``('refuse', plan_local)`` so the caller
          aborts before writing main's executor.
        * ``scaffold=True`` → create ``<repo_root>/.plan/local`` (parents
          included) and return ``('scaffolded', plan_local)``.

    Args:
        repo_root: Resolved repo top-level path (the wizard's ``REPO_ROOT``).
        scaffold: When ``True``, create the missing ``.plan/local`` instead of
            refusing.

    Returns:
        Tuple of (status, plan_local_path) where status is one of
        ``'ok'``, ``'refuse'``, or ``'scaffolded'``.
    """
    plan_local = repo_root / '.plan' / 'local'

    if not is_worktree_repo_root(repo_root):
        return 'ok', plan_local

    if plan_local.is_dir():
        return 'ok', plan_local

    if scaffold:
        plan_local.mkdir(parents=True, exist_ok=True)
        return 'scaffolded', plan_local

    return 'refuse', plan_local


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


def cmd_check_worktree_plan_local(args: argparse.Namespace) -> dict:
    """Handle the 'check-worktree-plan-local' subcommand.

    Implements the refuse-or-scaffold guard so worktree executor generation
    cannot contaminate the main checkout's ``.plan/execute-script.py``.
    """
    repo_root = Path(args.repo_root)
    status, plan_local = check_worktree_plan_local(repo_root, args.scaffold)

    result: dict = {
        'status': status,
        'repo_root': str(repo_root),
        'plan_local': str(plan_local),
        'is_worktree': is_worktree_repo_root(repo_root),
    }
    if status == 'refuse':
        result['detail'] = (
            f'Worktree {repo_root} lacks its own .plan/local — refusing executor '
            f'generation to avoid contaminating the main checkout. Re-run with '
            f'--scaffold to create {plan_local} first.'
        )
    return result


def _canonical_built_in_finalize_steps() -> list[str]:
    """Return the canonical default-on built-in finalize-step ids, in order.

    Sources the set from the reusable
    ``extension_discovery.find_implementors`` discovery query — the SOLE
    finalize-step discovery path (membership is DECLARED on each step doc via
    ``implements: ...ext-point-finalize-step`` and DISCOVERED through the query;
    there is no hand-maintained constant). The built-in seed is the subset of
    discovered implementors carrying ``default_on: true``, sorted by ``order``
    then ``name`` for a deterministic result. Degrades to an empty list when the
    query cannot be imported (the caller treats that as "nothing to detect" so
    the wizard never crashes on an unexpected import topology).
    """
    try:
        from _config_defaults import FINALIZE_STEP_EXT_POINT  # type: ignore[import-not-found]
        from extension_discovery import find_implementors  # type: ignore[import-not-found]
    except ImportError:
        return []

    default_on = sorted(
        (
            rec
            for rec in find_implementors(FINALIZE_STEP_EXT_POINT)
            if rec.get('default_on') and rec.get('source') == 'built-in'
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [rec['name'] for rec in default_on if rec.get('name')]


def _extract_step_ids(steps: object) -> list[str] | None:
    """Extract finalize-step ids from a ``phase-6-finalize.steps`` value.

    The canonical serial form is a KEYED-MAP — a dict mapping each step id to
    its (possibly empty) config object, with ``{}`` for a config-less step. A
    legacy list-of-id-strings is also accepted for backward compatibility.
    Returns the list of step ids (the dict keys, or the list verbatim), or
    ``None`` when the value is neither a dict nor a list, signalling
    "cannot compare" to callers. Without this normalization the detection
    helpers were blind to the keyed-map form: an ``isinstance(..., list)``
    guard treated every keyed-map ``steps`` block as "cannot compare" and
    silently reported no missing steps.
    """
    if isinstance(steps, dict):
        return list(steps.keys())
    if isinstance(steps, list):
        return steps
    return None


def detect_missing_default_finalize_steps(plan_dir: Path) -> list[str]:
    """Compare ``marshal.json::plan["phase-6-finalize"]["steps"]`` against the
    canonical built-in finalize-step set and return any built-ins missing from
    the project's array.

    The canonical built-in set is discovered via the reusable
    ``extension_discovery.find_implementors`` query (the ``default_on: true``
    finalize-step implementors), not a hand-maintained constant — see
    :func:`_canonical_built_in_finalize_steps`.

    Returns an empty list when:

    - ``marshal.json`` is absent (nothing to compare against)
    - the project's ``phase-6-finalize.steps`` already includes every built-in
    - the discovery query cannot be imported (the helper degrades gracefully
      so the wizard never crashes on an unexpected import topology)
    """
    marshal_path = plan_dir / 'marshal.json'
    if not marshal_path.exists():
        return []
    try:
        data = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []

    plan_section = data.get('plan', {}) if isinstance(data, dict) else {}
    finalize = plan_section.get('phase-6-finalize', {}) if isinstance(plan_section, dict) else {}
    existing = _extract_step_ids(finalize.get('steps')) if isinstance(finalize, dict) else None
    if existing is None:
        return []

    return [step for step in _canonical_built_in_finalize_steps() if step not in existing]


def _read_finalize_steps(plan_dir: Path) -> list[str] | None:
    """Return the finalize-step ids from ``marshal.json`` or ``None``.

    Reads ``plan["phase-6-finalize"]["steps"]`` and normalizes it to a list of
    step ids via :func:`_extract_step_ids` — the canonical keyed-map form
    yields its keys; a legacy list yields itself. ``None`` signals "cannot
    compare" — marshal.json is absent, unparseable, or the steps value is
    neither a keyed-map nor a list. Callers treat ``None`` as "nothing to
    detect" so the wizard never crashes on an unexpected topology.
    """
    marshal_path = plan_dir / 'marshal.json'
    if not marshal_path.exists():
        return None
    try:
        data = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    plan_section = data.get('plan', {}) if isinstance(data, dict) else {}
    finalize = plan_section.get('phase-6-finalize', {}) if isinstance(plan_section, dict) else {}
    return _extract_step_ids(finalize.get('steps')) if isinstance(finalize, dict) else None


def discover_shipped_project_finalize_steps(project_root: Path) -> list[str]:
    """Discover the ``project:`` finalize-step skills the repo ships.

    A project-local finalize-step skill lives at
    ``<project_root>/<skill-root>/finalize-step-<name>/SKILL.md`` (the skill
    root is resolved per target via the platform-runtime layout op). Each such
    skill is referenced from ``phase-6-finalize.steps`` as
    ``project:finalize-step-<name>``. This helper enumerates the shipped
    skills and returns the corresponding ``project:`` step notations, sorted
    for determinism.

    Returns an empty list when no project-local-skill root exists (a consumer
    project that ships no project-local finalize steps).
    """
    notations: list[str] = []
    seen: set[str] = set()
    for child in iter_project_skill_dirs(base=project_root):
        if not child.name.startswith('finalize-step-') or child.name in seen:
            continue
        if not (child / 'SKILL.md').is_file():
            continue
        seen.add(child.name)
        notations.append(f'project:{child.name}')
    return sorted(notations)


def detect_missing_project_finalize_steps(plan_dir: Path, project_root: Path) -> list[str]:
    """Return the shipped ``project:`` finalize steps absent from the steps array.

    Compares the ``project:`` finalize-step skills the repo ships (discovered
    from the target's project-local-skill ``finalize-step-*`` roots) against
    ``marshal.json::plan["phase-6-finalize"]["steps"]`` and returns any shipped
    ``project:`` step missing from that array — the steward surfaces these so a
    re-run on the meta-project does not silently drop its hand-maintained
    project-local finalize steps.

    Returns an empty list when marshal.json is absent/unparseable, the steps
    value is neither a keyed-map nor a list, or the project ships no
    ``project:`` finalize steps (the consumer-project case).
    """
    existing = _read_finalize_steps(plan_dir)
    if existing is None:
        return []
    shipped = discover_shipped_project_finalize_steps(project_root)
    return [step for step in shipped if step not in existing]


def cmd_check_missing_finalize_steps(args: argparse.Namespace) -> dict:
    """Handle the 'check-missing-finalize-steps' subcommand.

    Detects two classes of absence:

    - built-in ``default:`` steps newly added to the discovered default-on
      finalize-step set (via ``extension_discovery.find_implementors``) that an
      existing project's marshal.json predates, and
    - ``project:`` finalize steps the repo ships (under the target's
      project-local-skill roots) that are absent from
      ``phase-6-finalize.steps`` — the meta-project case
      where re-running the steward must not silently drop hand-maintained
      project-local steps.

    The two detection sets are reported independently so callers can tell a
    drifted built-in from a dropped project-local step. ``status: missing``
    fires when EITHER set is non-empty.
    """
    plan_dir = Path(args.plan_dir)
    project_root = Path(getattr(args, 'project_root', None) or '.')
    missing_default = detect_missing_default_finalize_steps(plan_dir)
    missing_project = detect_missing_project_finalize_steps(plan_dir, project_root)

    if missing_default or missing_project:
        result: dict = {
            'status': 'missing',
            'missing_count': len(missing_default) + len(missing_project),
        }
        if missing_default:
            result['missing_default_finalize_steps'] = ','.join(missing_default)
        if missing_project:
            result['missing_project_finalize_steps'] = ','.join(missing_project)
        return result
    return {'status': 'ok', 'missing_count': 0}


def detect_working_prefixes_drift(plan_dir: Path) -> dict:
    """Compare ``marshal.json::project["working_prefixes"]`` against the canonical
    ``DEFAULT_PROJECT["working_prefixes"]`` list and classify the project's state.

    Returns a structured result ``{'outcome': ..., 'missing_keys': [...]}`` where
    ``outcome`` is one of:

    - ``'absent'`` — the ``working_prefixes`` key is entirely missing from the
      ``project`` block (``missing_keys == ['working_prefixes']``).
    - ``'drift'`` — the key is present but is not a list OR lacks a default
      entry (``missing_keys == ['working_prefixes']``).
    - ``'ok'`` — the key is present and every default entry is included
      (operator *additions* / supersets are honoured and never flagged).

    Degrades gracefully to ``{'outcome': 'ok', 'missing_keys': []}`` when:

    - ``marshal.json`` is absent or unparseable (nothing to compare against)
    - the canonical ``DEFAULT_PROJECT`` cannot be imported (the helper never
      crashes the wizard on an unexpected import topology)
    """
    ok_result: dict = {'outcome': 'ok', 'missing_keys': []}

    marshal_path = plan_dir / 'marshal.json'
    if not marshal_path.exists():
        return ok_result
    try:
        data = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return ok_result

    try:
        from _config_defaults import DEFAULT_PROJECT  # type: ignore[import-not-found]
    except ImportError:
        return ok_result

    default_entries = DEFAULT_PROJECT.get('working_prefixes', [])
    if not isinstance(default_entries, list):
        return ok_result

    project_section = data.get('project', {}) if isinstance(data, dict) else {}
    if not isinstance(project_section, dict):
        project_section = {}

    if 'working_prefixes' not in project_section:
        return {'outcome': 'absent', 'missing_keys': ['working_prefixes']}

    live_entries = project_section.get('working_prefixes')
    if not isinstance(live_entries, list):
        # Present but malformed (not a list) — treat as drift.
        return {'outcome': 'drift', 'missing_keys': ['working_prefixes']}

    # Non-clobbering: a superset (operator additions) is fine; only a MISSING
    # default entry is drift.
    if any(entry not in live_entries for entry in default_entries):
        return {'outcome': 'drift', 'missing_keys': ['working_prefixes']}

    return ok_result


def cmd_check_working_prefixes(args: argparse.Namespace) -> dict:
    """Handle the 'check-working-prefixes' subcommand.

    Surfaces ``project.working_prefixes`` absence or drift against the canonical
    default so the wizard can prompt the operator to add/update it. The
    detection is non-clobbering — a current or operator-customized (superset)
    list returns ``status: ok`` and is never flagged.
    """
    result = detect_working_prefixes_drift(Path(args.plan_dir))
    outcome = result['outcome']
    if outcome == 'absent':
        return {'status': 'missing', 'detail': 'absent', 'missing_keys': 'working_prefixes'}
    if outcome == 'drift':
        return {'status': 'missing', 'detail': 'drift', 'missing_keys': ','.join(result['missing_keys'])}
    return {'status': 'ok'}


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

    # check-worktree-plan-local subcommand
    worktree_parser = subparsers.add_parser(
        'check-worktree-plan-local',
        help=(
            'Refuse-or-scaffold guard for worktree executor generation — ensures a '
            'worktree owns its own .plan/local before generate_executor runs, so it '
            "cannot contaminate the main checkout's .plan/execute-script.py."
        ),
        allow_abbrev=False,
    )
    worktree_parser.add_argument(
        '--repo-root',
        type=str,
        required=True,
        help='Resolved repo top-level path (the wizard REPO_ROOT) to guard.',
    )
    worktree_parser.add_argument(
        '--scaffold',
        action='store_true',
        help='Create the missing .plan/local instead of refusing.',
    )

    # check-missing-finalize-steps subcommand
    missing_parser = subparsers.add_parser(
        'check-missing-finalize-steps',
        help=(
            'Detect finalize steps absent from an existing marshal.json — '
            'newly-added built-in defaults AND project: steps the repo ships '
            '(under .claude/skills/) that were dropped from phase-6-finalize.steps.'
        ),
        allow_abbrev=False,
    )
    missing_parser.add_argument(
        '--plan-dir',
        type=str,
        default='.plan',
        help='Directory containing marshal.json (default: .plan)',
    )
    missing_parser.add_argument(
        '--project-root',
        type=str,
        default='.',
        help=(
            'Project root used to discover shipped project: finalize-step '
            'skills under .claude/skills/ (default: .)'
        ),
    )

    # check-working-prefixes subcommand
    working_prefixes_parser = subparsers.add_parser(
        'check-working-prefixes',
        help=(
            'Detect absence or drift of project.working_prefixes against the canonical '
            'default — surfaces missing/drifted branch-prefix config so the wizard can prompt.'
        ),
        allow_abbrev=False,
    )
    working_prefixes_parser.add_argument(
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
    elif args.command == 'check-worktree-plan-local':
        result = cmd_check_worktree_plan_local(args)
    elif args.command == 'check-missing-finalize-steps':
        result = cmd_check_missing_finalize_steps(args)
    elif args.command == 'check-working-prefixes':
        result = cmd_check_working_prefixes(args)
    else:
        parser.print_help()
        return 1

    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
