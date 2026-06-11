#!/usr/bin/env python3
"""
Manage the per-plan execution manifest (compose, read, validate).

The manifest is the single source of truth for which Phase 5 verification
steps and Phase 6 finalize steps fire for a given plan. Phases 5 and 6 read
the manifest and dispatch — they no longer carry per-doc skip logic.

Storage: TOON format at .plan/local/plans/{plan_id}/execution.toon
Output: TOON format for API responses

Usage:
    python3 manage-execution-manifest.py compose --plan-id EXAMPLE-PLAN \\
        --change-type bug_fix --track simple --scope-estimate surgical
    python3 manage-execution-manifest.py read --plan-id EXAMPLE-PLAN
    python3 manage-execution-manifest.py validate --plan-id EXAMPLE-PLAN
"""

import argparse
import json
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _references_core import (  # type: ignore[import-not-found]
    compute_plan_branch_diff,
    resolve_base_ref,
)
from constants import FILE_REFERENCES, FILE_STATUS  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    get_executor_path,
    get_marshal_path,
    get_plan_dir,
    output_toon,
    output_toon_error,
    read_json,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from marketplace_bundles import (  # type: ignore[import-not-found]
    resolve_bundles_root,
    resolve_skills_root,
)
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

MANIFEST_FILENAME = 'execution.toon'
MANIFEST_VERSION = 1

VALID_CHANGE_TYPES = (
    'analysis',
    'feature',
    'enhancement',
    'bug_fix',
    'tech_debt',
    'verification',
)

VALID_SCOPE_ESTIMATES = (
    'none',
    'surgical',
    'single_module',
    'multi_module',
    'broad',
)

VALID_TRACKS = ('simple', 'complex')

# Documentation file suffixes recognized generically by the change-footprint
# classifier. Documentation has NO build-system owner — it is not a buildable
# unit and not a build_map route role — so doc recognition is an
# extension-agnostic file-suffix fact rather than a build-extension classify
# claim. Any changed path ending in one of these suffixes is tagged with the
# ``documentation`` footprint role independently of (and BEFORE) the
# build-extension classify_paths() iteration. The build extensions still supply
# production / test / config recognition; this generic rule is the sole source of
# documentation recognition. The vocabulary mirrors the suffixes the retired
# pm-documents Axis-B classifier used (``.md`` / ``.adoc`` / ``.asciidoc``).
_DOC_SUFFIXES: tuple[str, ...] = ('.md', '.adoc', '.asciidoc')


def _is_documentation_path(path: str) -> bool:
    """Return True when ``path`` is a documentation file by suffix.

    The generic, extension-agnostic documentation predicate consumed by
    :func:`_classify_paths_via_extensions`. Documentation has no build-system
    owner, so doc recognition is a pure file-suffix fact — a path is
    documentation iff it ends in one of :data:`_DOC_SUFFIXES`.
    """
    return path.endswith(_DOC_SUFFIXES)

# record-step contract. The execution log records per-step execution outcome
# plus token attribution into a new ``execution_log[]`` section of the
# manifest, written by the ``record-step`` subcommand. Phases are the bare
# phase keys the orchestrator emits at step-dispatch time; outcomes name
# whether the step ran, was skipped, or errored.
VALID_RECORD_PHASES = ('5-execute', '6-finalize')
VALID_RECORD_OUTCOMES = ('executed', 'skipped', 'error')
EXECUTION_LOG_KEY = 'execution_log'

# Default candidate step sets when callers don't pass --phase-5-steps / --phase-6-steps.
# These are bare step IDs (post boundary-normalization shape) that resolve to
# standards files at marketplace/bundles/plan-marshall/skills/phase-5-execute/
# standards/{name}.md. Each declares its ``role:`` frontmatter field, consumed
# by ``_role_of`` below for structural role-based intersection in the 7-row
# decision matrix.
DEFAULT_PHASE_5_STEPS = ('quality_check', 'build_verify')
DEFAULT_PHASE_6_STEPS = (
    'finalize-step-simplify',
    'finalize-step-whole-tree-gate',
    'commit-push',
    'create-pr',
    'ci-verify',
    'automated-review',
    'sonar-roundtrip',
    'lessons-capture',
    'branch-cleanup',
    'record-metrics',
    'archive-plan',
)

# Path to the phase-5-execute standards directory, used by ``_role_of`` to
# resolve a candidate step ID to its source file and read the ``role:``
# frontmatter field. ``resolve_skills_root`` identity-walks to the owning
# bundle's ``skills`` directory (no index arithmetic), and we descend into the
# sibling phase-5-execute skill's standards directory.
_PHASE_5_STANDARDS_DIR = resolve_skills_root(Path(__file__)) / 'phase-5-execute' / 'standards'


def _strip_default_prefix(step: str) -> str:
    """Return the bare step name regardless of the optional ``default:`` prefix."""
    return step[len('default:') :] if step.startswith('default:') else step


def _role_of(step_id: str, cache: dict[str, str | None]) -> str | None:
    """Resolve a phase-5 candidate step ID to its ``role:`` frontmatter value.

    The composer intersects phase-5 candidates by role rather than by literal
    step ID. For each candidate, we resolve the step's source file (e.g.,
    ``quality_check`` → ``marketplace/bundles/plan-marshall/skills/phase-5-execute/
    standards/quality_check.md``) and read the ``role:`` field from the YAML
    frontmatter.

    Returns ``None`` for:

    - External steps (``project:`` or ``bundle:skill``) — no role-file concept.
    - Built-in steps whose source file is missing.
    - Files without a ``role:`` frontmatter field (plugin-doctor's
      ``MISSING_ROLE_FIELD`` analyzer catches this drift at edit time).

    Results are cached per compose call to avoid re-reading the same file when
    a candidate appears in multiple intersection sites.
    """
    if step_id in cache:
        return cache[step_id]

    # External steps (project:foo or bundle:skill) have no role file — they
    # are dispatched as PROJECT/SKILL steps, not built-in default steps.
    if ':' in step_id and not step_id.startswith('default:'):
        cache[step_id] = None
        return None

    bare = _strip_default_prefix(step_id)
    path = _PHASE_5_STANDARDS_DIR / f'{bare}.md'
    if not path.is_file():
        cache[step_id] = None
        return None

    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        cache[step_id] = None
        return None

    # Minimal YAML frontmatter parsing: scan the first ``---``-fenced block
    # for a ``role:`` key. We avoid pulling in PyYAML to keep the script's
    # dependency surface narrow; the frontmatter shape is constrained by
    # plugin-doctor and the test suite.
    role: str | None = None
    if text.startswith('---'):
        lines = text.splitlines()
        for line in lines[1:]:
            if line.strip() == '---':
                break
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if ':' in stripped:
                key, _, value = stripped.partition(':')
                if key.strip() == 'role':
                    candidate = value.strip().strip('"').strip("'")
                    if candidate:
                        role = candidate
                    break
    cache[step_id] = role
    return role


# =============================================================================
# File Operations
# =============================================================================


def get_manifest_path(plan_id: str) -> Path:
    """Return the absolute path to the execution manifest for ``plan_id``."""
    return get_plan_dir(plan_id) / MANIFEST_FILENAME


def write_manifest(plan_id: str, manifest: dict[str, Any]) -> None:
    """Atomically write the manifest as TOON to its plan path."""
    path = get_manifest_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, serialize_toon(manifest))


def read_manifest(plan_id: str) -> dict[str, Any] | None:
    """Read and parse the manifest, returning ``None`` if missing."""
    path = get_manifest_path(plan_id)
    if not path.exists():
        return None
    return parse_toon(path.read_text(encoding='utf-8'))


# =============================================================================
# Decision Engine (seven-row matrix from standards/decision-rules.md)
# =============================================================================


def _split_csv(value: str | None, default: tuple[str, ...]) -> list[str]:
    if value is None or value == '':
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _decide(
    change_type: str,
    track: str,
    scope_estimate: str,
    recipe_key: str | None,
    affected_files_count: int,
    phase_5_candidates: list[str],
    phase_6_candidates: list[str],
    task_queue_active: bool = False,
) -> tuple[dict[str, Any], str]:
    """Apply the seven-row decision matrix.

    Returns the manifest body (under ``phase_5`` / ``phase_6`` keys) plus the
    name of the rule that fired (one of the seven rule keys defined in
    standards/decision-rules.md).

    Rows 2, 3, 5, 6 intersect phase-5 candidates by the ``role:`` frontmatter
    field of each candidate's source standards file rather than by literal
    step ID. The intersection mechanism is structural: candidates declare
    their role explicitly (e.g., ``role: quality-gate``) and the matrix
    matches against a set of role names. See ``_role_of`` and
    ``standards/decision-rules.md`` § Role-Field Intersection.

    Rule 1's ``early_terminate`` predicate also requires ``task_queue_active``
    to be ``False``. When the implementation task queue carries any pending or
    in-progress task, Rule 1 falls through to Rule 7 (default) so phase-5
    iterates the queue normally. Without this guard, an analysis-only plan
    that produces zero affected files but still queues at least one
    deliverable task would short-circuit before TASK-001 runs and skip the
    Step 2.5 worktree materialization as a cascade.
    """

    # Per-compose role-lookup cache: avoid re-reading a candidate's source file
    # when it appears in multiple intersection sites.
    role_cache: dict[str, str | None] = {}

    # Rule 1: early_terminate — analysis without affected files AND no pending
    # / in-progress tasks. Phase 5 is skipped entirely; Phase 6 still runs
    # lessons capture so the analysis doesn't leak insights silently. When the
    # task queue is non-empty, fall through to Rule 7 (default) so phase-5
    # iterates the queue normally — see ``task_queue_active`` rationale above.
    if change_type == 'analysis' and affected_files_count == 0 and not task_queue_active:
        body = {
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [s for s in phase_6_candidates if s in {'lessons-capture', 'archive-plan'}],
            },
        }
        return body, 'early_terminate_analysis'

    # Rule 2: recipe path — recipe-driven plans get a slim manifest. The
    # recipe-lesson-cleanup recipe (deliverable 7) sets scope_estimate=surgical
    # so the surgical-style cascades still apply downstream; here we only need
    # to drop the legacy ``ci-wait`` step ID (defensively, against project
    # marshal.json files that still list it as a candidate). Review gates a
    # project opted into (``automated-review`` / ``sonar-roundtrip``) are
    # NEVER silently suppressed by the planner — the recipe label is exactly
    # the case where the bots' job is to catch what humans miss.
    if recipe_key:
        phase_6_steps = [s for s in phase_6_candidates if s not in {'ci-wait'}]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [
                    s for s in phase_5_candidates if _role_of(s, role_cache) in {'quality-gate', 'module-tests'}
                ],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        return body, 'recipe'

    # Rule 3: docs-only — surgical scope plus no test/code expectations. Skip
    # build verification entirely; keep capture + commit + PR + branch cleanup.
    # Only the legacy ``ci-wait`` step ID is subtracted (defensively, against
    # project marshal.json files that still list it). Review gates a project
    # opted into are NEVER silently suppressed by the planner.
    if (
        scope_estimate in ('surgical', 'single_module')
        and change_type in ('tech_debt', 'enhancement')
        and affected_files_count > 0
        and _looks_docs_only(phase_5_candidates, role_cache)
    ):
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [s for s in phase_6_candidates if s not in {'ci-wait'}],
            },
        }
        return body, 'docs_only'

    # Rule 4: tests-only — verification change_type with affected files. Run
    # the module-tests step but skip quality-gate; full Phase 6.
    if change_type == 'verification' and affected_files_count > 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if _role_of(s, role_cache) == 'module-tests'],
            },
            'phase_6': {'steps': list(phase_6_candidates)},
        }
        return body, 'tests_only'

    # Rule 5: surgical + bug_fix / tech_debt — Q-Gate bypass already applies
    # at outline time (deliverable 4). Here the only subtraction is the
    # legacy ``ci-wait`` step ID (defensively, against project marshal.json
    # files that still list it). Review gates a project opted into
    # (``automated-review`` / ``sonar-roundtrip``) are NEVER silently
    # suppressed by the planner — surgical bug_fix / tech_debt is exactly
    # the case where the bots' job is to catch what humans miss.
    if scope_estimate == 'surgical' and change_type in ('bug_fix', 'tech_debt'):
        phase_6_steps = [s for s in phase_6_candidates if s not in {'ci-wait'}]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [
                    s for s in phase_5_candidates if _role_of(s, role_cache) in {'quality-gate', 'module-tests'}
                ],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        rule = f'surgical_{change_type}'
        return body, rule

    # Rule 6: verification change_type without affected files — same shape as
    # rule 1's Phase 6 minimum, but Phase 5 still runs whatever was passed.
    if change_type == 'verification' and affected_files_count == 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': list(phase_5_candidates),
            },
            'phase_6': {
                'steps': [s for s in phase_6_candidates if s in {'lessons-capture', 'archive-plan'}],
            },
        }
        return body, 'verification_no_files'

    # Rule 7 (default): code-shaped feature / enhancement / large change. Full
    # verification + full finalize. This is the safe baseline the request
    # called the "default code-shaped feature" row.
    body = {
        'phase_5': {
            'early_terminate': False,
            'verification_steps': list(phase_5_candidates),
        },
        'phase_6': {'steps': list(phase_6_candidates)},
    }
    return body, 'default'


def _read_task_queue_active(plan_id: str) -> bool:
    """Return ``True`` when the plan has at least one pending or in-progress task.

    Reads ``TASK-*.json`` files from ``get_plan_dir(plan_id) / 'tasks'`` and
    checks the ``status`` field on each. The check is intentionally direct
    file I/O — invoking ``manage-tasks list`` as a subprocess would couple
    composer behaviour to the executor and would add cross-script logging
    noise. Returns ``False`` when the tasks directory is missing (no plan
    structure yet) or contains no parseable task files; the composer treats
    that as "no work queued, the analysis-only short-circuit is safe to
    fire". This predicate is the gate that keeps Rule 1 from short-circuiting
    plans where deliverables exist but affected_files happens to be empty at
    compose time.
    """
    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    if not tasks_dir.is_dir():
        return False
    active_statuses = {'pending', 'in_progress'}
    for task_path in tasks_dir.glob('TASK-*.json'):
        try:
            data = read_json(task_path, default=None)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        status = data.get('status')
        if isinstance(status, str) and status in active_statuses:
            return True
    return False


def _read_recipe_source(plan_id: str) -> str | None:
    """Resolve the recipe / lesson provenance surrogate from status metadata.

    ``phase-1-init`` seeds ``status.metadata.plan_source`` with the raw lesson
    id for lesson-derived plans (Step 5b.5) or the literal string ``"recipe"``
    for recipe-routed plans (Step 5c, which also sets ``recipe_key``). Either
    value is the Row 2 recipe signal.

    The composer reads this surrogate directly so recipe / lesson provenance no
    longer depends on the ``phase-4-plan`` agent remembering to forward
    ``--recipe-key`` from ``manage-status read`` — the gap the archived-plan
    audit surfaced as recipe→default drift (lesson/recipe plans composing the
    ``default`` rule because the flag was omitted). This mirrors the audit's own
    surrogate (``audit-archived-plan-retrospectives/scripts/audit.py``
    ``collect_inputs``: a non-empty ``plan_source`` is treated as ``recipe_key``
    for matrix purposes). An explicit ``--recipe-key`` argument still takes
    precedence at the call site in :func:`cmd_compose`.

    Returns the trimmed provenance string, or ``None`` when ``status.json`` is
    absent or its metadata carries no ``plan_source`` / ``recipe_key``.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return None
    # Best-effort: a malformed status.json must degrade to "no provenance"
    # rather than crash compose. read_json returns its default only for a
    # missing file, so a corrupt-but-present file raises here — mirror the
    # OSError / JSONDecodeError guard used by _read_task_queue_active and
    # _read_ci_provider in this module.
    try:
        status = read_json(status_path, default={})
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(status, dict):
        return None
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return None
    for field in ('plan_source', 'recipe_key'):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_bundle_change_paths(plan_id: str) -> list[str]:
    """Read the union of bundle change paths from references.json + solution outline.

    The composer runs from `phase-4-plan` Step 8b — at outline/plan time, BEFORE
    Phase 5 has committed any changes. ``references.json::affected_files`` is the
    canonical pre-execute source when populated by upstream phases. The legacy
    ``modified_files`` key is no longer written by current plans (the persisted
    ledger was removed; the footprint is derived on demand from the worktree);
    it is unioned in here only as a back-compat fallback for older plans that
    still carry it.

    For plans where ``references.json::affected_files`` is unset (the common
    pre-execute shape produced by current phase-3-outline / phase-4-plan flows),
    the composer falls back to the deliverable-level ``Affected files:`` blocks
    in ``solution_outline.md``. This closes the empirical gap where a
    deliverable listed bundle source paths but ``references.json`` did not
    surface them, so the predicate had nothing to match against.

    Reading all three sources and unioning their entries means the rule fires:

    - on the first compose (via ``affected_files`` in references OR the
      solution outline fallback);
    - on any older plan that still carries the legacy ``modified_files`` key.

    Returns an empty list when none of the sources can be read — the rule
    simply does not fire in that case.
    """
    seen: set[str] = set()
    union: list[str] = []

    references_path = get_plan_dir(plan_id) / FILE_REFERENCES
    if references_path.exists():
        payload = read_json(references_path, default={})
        if isinstance(payload, dict):
            for field in ('affected_files', 'modified_files'):
                entries = payload.get(field)
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, str):
                        continue
                    normalized = entry.strip()
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    union.append(normalized)

    # Fallback: harvest deliverable-level Affected files from the solution
    # outline. Cross-skill import via PYTHONPATH (set by the executor and the
    # test conftest). Any import or parse failure is swallowed silently — the
    # rule simply skips the fallback in that case.
    for entry in _read_solution_outline_affected_files(plan_id):
        if entry not in seen:
            seen.add(entry)
            union.append(entry)

    return union


def _read_solution_outline_affected_files(plan_id: str) -> list[str]:
    """Best-effort read of deliverable-level ``Affected files:`` from the outline.

    Imports ``_plan_parsing`` (sibling skill ``manage-solution-outline``) to
    parse the document and extract per-deliverable ``affected_files`` lists,
    then flattens them into a single ordered, de-duplicated list. Returns an
    empty list when the outline is missing, malformed, or the import is not
    on ``sys.path``. The composer treats missing data as "rule does not fire".
    """
    outline_path = get_plan_dir(plan_id) / 'solution_outline.md'
    if not outline_path.exists():
        return []
    try:
        # Local import: keeps cmd_compose's import surface narrow and lets
        # the fallback degrade gracefully when _plan_parsing is unavailable.
        from _plan_parsing import (  # type: ignore[import-not-found]
            extract_deliverables,
            parse_document_sections,
        )
    except ImportError:
        return []
    try:
        content = outline_path.read_text(encoding='utf-8')
        sections = parse_document_sections(content)
        deliverables_section = sections.get('deliverables') if isinstance(sections, dict) else None
        if not isinstance(deliverables_section, str):
            return []
        deliverables = extract_deliverables(deliverables_section)
    except (OSError, ValueError, AttributeError):
        return []

    seen: set[str] = set()
    flat: list[str] = []
    for d in deliverables:
        if not isinstance(d, dict):
            continue
        files = d.get('affected_files')
        if not isinstance(files, list):
            continue
        for f in files:
            if isinstance(f, str) and f and f not in seen:
                seen.add(f)
                flat.append(f)
    return flat


def _looks_docs_only(phase_5_candidates: list[str], role_cache: dict[str, str | None]) -> bool:
    """Heuristic: docs-only plans don't request module-tests or coverage.

    The composer treats any candidate set whose declared roles include
    neither ``module-tests`` nor ``coverage`` as a docs-only signal. Real
    code-shaped plans always include at least one candidate whose ``role:``
    frontmatter is ``module-tests`` (typically ``default:build_verify``).

    Uses the per-compose role cache to avoid re-reading frontmatter files.
    """
    roles = {_role_of(s, role_cache) for s in phase_5_candidates}
    return 'module-tests' not in roles and 'coverage' not in roles


def _classify_paths_via_extensions(
    paths: list[str],
    plan_id: str | None = None,
    extensions: list[Any] | None = None,
) -> tuple[str, list[str]]:
    """Classify a path list into a plan-wide change-footprint bucket.

    Two-stage classifier:

    1. **Generic documentation recognition (extension-agnostic).** Any path
       ending in a :data:`_DOC_SUFFIXES` suffix (``.md`` / ``.adoc`` /
       ``.asciidoc``) is tagged with the ``documentation`` footprint role
       directly, BEFORE and independent of the build-extension iteration.
       Documentation has no build-system owner — it is not a buildable unit and
       not a build_map route role — so doc recognition is a pure file-suffix fact
       owned here, not a build-extension claim. Documentation paths are removed
       from the set handed to the build extensions, so a build extension never
       claims (or contests) a doc path and a doc path is never tagged
       ``unknown``.

    2. **Build-extension recognition (production / test / config).** The
       remaining non-doc paths flow to every discovered build extension (Axis-B:
       ``build-pyproject`` / ``build-maven`` / ``build-gradle`` / ``build-npm``)
       via ``classify_paths()``. Multi-extension overlap is resolved by
       longest-glob-wins (highest ``classify_path_specificity`` wins; alphabetical
       domain-key tie-break). Non-doc paths no build extension claims are tagged
       ``unknown`` and emit a ``[STATUS]`` decision-log warning.

    The per-path roles (the generic ``documentation`` tags plus the build
    extensions' production / test / config claims) are then collapsed into one of
    six plan-wide bucket values.

    File classification for production / test / config flows from the
    build-system-owned ``BuildExtensionBase`` subclasses, NOT the language domain
    extensions — the latter own Axis-A (skill-loading) only and expose no
    ``classify_paths``. Documentation recognition flows from neither: it is the
    generic suffix rule above.

    Args:
        paths: Plan-wide union of every deliverable's ``affected_files``.
        plan_id: When supplied AND at least one path is unclaimed, the
            aggregator emits a ``[STATUS]`` warning naming each unclaimed
            path under this plan id. Omit during unit tests.
        extensions: Optional pre-resolved list of build-extension instances. When
            ``None`` the aggregator calls
            :func:`extension_discovery.discover_build_extensions` and uses
            every loaded build-extension module. The override is intended for the
            fake-extension test fixture in
            ``test/plan-marshall/manage-execution-manifest/_fixtures.py``.

    Returns:
        A 2-tuple ``(bucket, unclaimed_paths)`` where ``bucket`` is one of
        the six plan-wide vocabulary values
        (``production_only`` / ``test_only`` / ``documentation_only`` /
        ``mixed_code`` / ``mixed_with_docs`` / ``unknown``) and
        ``unclaimed_paths`` is the list of paths no extension claimed (empty
        when bucket is anything other than ``unknown``).

    The aggregator returns ``documentation_only`` for an empty path list as
    the conservative default (no affected files means no holistic Python
    verification is needed).

    See ``manage-execution-manifest/standards/decision-rules.md`` §
    "Overlap resolution policy" and § "Unclaimed paths" for the full
    contract documentation. See
    ``extension-api/standards/extension-contract.md`` § classify_paths()
    for the per-extension contract.
    """
    if not paths:
        return 'documentation_only', []

    # Stage 1 — generic, extension-agnostic documentation recognition. Any path
    # ending in a documentation suffix is the ``documentation`` footprint role,
    # owned by nobody (no build owner for docs). These paths are split out so the
    # build extensions never see them: a doc path is never claimed/contested by
    # an extension and never tagged ``unknown``.
    per_path_role: dict[str, str] = {}
    code_paths: list[str] = []
    for path in paths:
        if _is_documentation_path(path):
            per_path_role[path] = 'documentation'
        else:
            code_paths.append(path)

    # Resolve the active extension set. The lazy import avoids a circular
    # dependency on extension_discovery during module import; the test
    # fixture passes ``extensions`` explicitly so we never hit this branch
    # during unit tests.
    if extensions is None:
        try:
            from extension_discovery import discover_build_extensions  # type: ignore[import-not-found]
        except ImportError:
            extensions = []
        else:
            discovered = discover_build_extensions()
            extensions = [ext.get('module') for ext in discovered if ext.get('module') is not None]

    # Stage 2 — build-extension recognition over the non-doc paths only. Collect
    # per-extension claims. Each entry is (extension_instance, domain_key, role,
    # path).
    Claim = tuple[Any, str, str, str]
    raw_claims: list[Claim] = []
    for ext in extensions:
        try:
            claims = ext.classify_paths(list(code_paths))
            domain_key = _safe_domain_key(ext)
            for role, claimed_paths in claims.items():
                for path in claimed_paths:
                    raw_claims.append((ext, domain_key, role, path))
        except Exception:
            continue

    # Resolve overlaps per-path: highest specificity wins; alphabetical
    # tie-break on domain_key.
    claims_by_path: dict[str, list[Claim]] = {}
    for claim in raw_claims:
        claims_by_path.setdefault(claim[3], []).append(claim)
    for path, path_claims in claims_by_path.items():
        scored: list[tuple[int, str, str]] = []
        for ext, domain_key, role, _ in path_claims:
            try:
                specificity = int(ext.classify_path_specificity(path, role))
            except Exception:
                specificity = 0
            scored.append((specificity, domain_key, role))
        # Sort by (-specificity, domain_key) — higher specificity first,
        # alphabetical tie-break.
        scored.sort(key=lambda item: (-item[0], item[1]))
        per_path_role[path] = scored[0][2]

    # Identify unclaimed paths (non-doc paths no build extension claimed) and
    # emit a warning when the caller passed plan_id.
    unclaimed = [p for p in code_paths if p not in per_path_role]
    if unclaimed:
        if plan_id:
            _emit_decision_log(
                plan_id,
                f'(plan-marshall:manage-execution-manifest:classify) '
                f'[STATUS] Unclaimed paths tagged unknown: {unclaimed}',
            )
        return 'unknown', unclaimed

    # Collapse per-path roles into the six-bucket plan-wide vocabulary.
    # config role does NOT influence the plan-wide bucket — config changes
    # ride with whatever production/test/docs surface they accompany.
    roles_present = {role for role in per_path_role.values() if role != 'config'}
    has_prod = 'production' in roles_present
    has_test = 'test' in roles_present
    has_docs = 'documentation' in roles_present

    if has_docs and (has_prod or has_test):
        return 'mixed_with_docs', []
    if has_prod and has_test:
        return 'mixed_code', []
    if has_prod:
        return 'production_only', []
    if has_test:
        return 'test_only', []
    if has_docs:
        return 'documentation_only', []
    # Only config claims (no production/test/docs) — treat as documentation_only
    # under the conservative default (config-only changes do not warrant
    # holistic Python verification).
    return 'documentation_only', []


def _safe_domain_key(ext: Any) -> str:
    """Return the extension's first domain key, or empty string on failure.

    Used as the alphabetical tie-breaker in overlap resolution. Failure to
    resolve the key produces an empty string so the tie-break degrades
    gracefully.
    """
    try:
        domains = ext.get_skill_domains()
        if domains:
            return str(domains[0].get('domain', {}).get('key', '') or '')
    except Exception:
        pass
    return ''


# =============================================================================
# Decision Logging
# =============================================================================


def _resolve_executor() -> Path | None:
    """Locate ``.plan/execute-script.py`` via the canonical cwd-relative resolver.

    Delegates to ``file_ops.get_executor_path`` (the ADR-002 uniform cwd rule:
    the executor lives under the ``.plan`` dir of whichever checkout the working
    directory is in) instead of walking up from ``__file__``. The composer is
    dispatched from the plugin cache (``~/.claude/plugins/cache/...``), which
    lives OUTSIDE the project tree, so a ``__file__`` walk never found the
    executor — silently breaking the ``execution_tier`` routing that
    subprocesses ``architecture resolve`` through it. Returns ``None`` when the
    plan root is unresolvable or the executor file is absent (e.g. an exotic
    test fixture), which the caller treats as "non-build / unroutable".
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        return None
    return executor if executor.is_file() else None


def _emit_decision_log(plan_id: str, message: str) -> None:
    """Best-effort decision-log emission via a direct in-process write.

    Logging is non-load-bearing — manifest content is the contract — so any
    import or write error is swallowed silently.

    The entry is written through ``plan_logging.log_entry`` directly rather than
    shelling back out to ``.plan/execute-script.py``. The composer is dispatched
    from the plugin cache (``~/.claude/plugins/cache/...``), which lives outside
    the project tree, so the former ``_resolve_executor`` walk up from
    ``__file__`` never resolved the executor and silently dropped every compose
    decision-log line — the ``unloggable`` regression the archived-plan audit
    surfaced. The direct write resolves the plan dir via the same
    ``file_ops.get_base_dir()`` the manifest write uses, so the line always
    lands in the plan's own ``logs/decision.log`` alongside ``execution.toon``.
    ``plan_logging`` is on ``PYTHONPATH`` (the executor injects every skill's
    scripts dir; the test conftest does the same).
    """
    try:
        from plan_logging import log_entry  # type: ignore[import-not-found]

        log_entry('decision', plan_id, 'INFO', message)
    except Exception:
        return


def _log_decision(plan_id: str, rule: str, body: dict[str, Any]) -> None:
    """Emit one ``decision.log`` entry for the rule that fired.

    The composer must produce one entry per applied rule per plan run, per the
    request example. We invoke ``manage-logging decision`` via the executor so
    the entry lands in the canonical decision log location.
    """
    phase_5 = body.get('phase_5', {})
    phase_6 = body.get('phase_6', {})
    p5_steps = phase_5.get('verification_steps', [])
    p6_steps = phase_6.get('steps', [])
    early = phase_5.get('early_terminate', False)
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
        f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
        f'phase_6.steps={p6_steps}'
    )
    _emit_decision_log(plan_id, message)


def _log_commit_push_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``commit_push_disabled`` pre-filter."""
    message = '(plan-marshall:manage-execution-manifest:compose) commit-push omitted — commit_and_push=false'
    _emit_decision_log(plan_id, message)


def _log_candidate_source(plan_id: str, phase_key: str, source: str) -> None:
    """Emit a decision-log entry naming which input source produced the candidate list.

    ``source`` is either ``'marshal.json'`` (preferred path — full prefixes
    preserved) or ``'csv_fallback'`` (no marshal.json available; the
    composer fell back to the ``--phase-{5,6}-steps`` CSV).
    """
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) {phase_key} candidate source: {source}'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_push_quality_gate_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``pre_push_quality_gate_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — '
        'no build_map globs or no footprint match'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_submission_self_review_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``pre_submission_self_review_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-submission-self-review omitted — empty footprint'
    )
    _emit_decision_log(plan_id, message)


def _log_simplify_omitted(plan_id: str, change_type: str, affected_files_count: int) -> None:
    """Emit the decision-log entry for the ``simplify_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — '
        f'change_type={change_type} affected_files_count={affected_files_count}'
    )
    _emit_decision_log(plan_id, message)


def _log_whole_tree_gate_omitted(
    plan_id: str, compatibility: str, change_type: str, affected_files_count: int
) -> None:
    """Emit the decision-log entry for the ``whole_tree_gate_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) finalize-step-whole-tree-gate omitted — '
        f'compatibility={compatibility} change_type={change_type} affected_files_count={affected_files_count}'
    )
    _emit_decision_log(plan_id, message)


def _log_bot_enforcement_guard_fired(plan_id: str, provider: str) -> None:
    """Emit the decision-log entry for the ``bot_enforcement_guard`` violation.

    Logged before the composition error is raised on the safety-net path
    (currently unreachable; see ``_apply_bot_enforcement_guard``). Retained
    so that any future logic which detects a non-remediable violation has a
    canonical decision-log entry to emit.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard fired — '
        f'ci_provider={provider}, automated-review missing from phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


def _log_bot_enforcement_guard_remediated(plan_id: str, provider: str) -> None:
    """Emit the decision-log entry for the ``bot_enforcement_guard`` remediation.

    Logged whenever the guard appends ``automated-review`` back into
    ``phase_6.steps`` so the manifest's reconstruction-from-rules-alone
    remains auditable.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard remediated — '
        f'ci_provider={provider}, automated-review re-added to phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


def _log_bot_enforcement_placement_violation(plan_id: str, diagnostic: str) -> None:
    """Emit the decision-log entry for the placement-validator rejection.

    Logged whenever the compose-time placement validator detects that
    ``automated-review`` sits at an index later than at least one
    plan-mutating step (``archive-plan``, ``record-metrics``, ``branch-cleanup``,
    or ``plan-marshall:plan-retrospective``). The diagnostic string carries
    both step names and indexes for downstream auditing.
    """
    message = f'(plan-marshall:manage-execution-manifest:compose) bot-enforcement placement violation — {diagnostic}'
    _emit_decision_log(plan_id, message)


# =============================================================================
# Pre-Filter Helpers
# =============================================================================


def _read_marshal_phase_steps(phase_key: str) -> list[str] | None:
    """Read ``plan.{phase_key}.steps`` from marshal.json.

    ``phase_key`` is the marshal.json key (e.g. ``'phase-5-execute'`` or
    ``'phase-6-finalize'``). Returns the list of full step references as
    declared in marshal.json (prefixes preserved), or ``None`` when the
    marshal file is missing, the keys are absent, or the value is not a list.

    The composer prefers this source over the agent-supplied
    ``--phase-{5,6}-steps`` CSV because marshal.json is the authoritative
    project-level declaration: it preserves ``default:`` / ``project:`` /
    ``bundle:skill`` prefixes that agent-built CSVs have historically
    stripped, producing manifests with bare names the dispatcher then mis-
    routed as built-in steps.
    """
    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return None
    try:
        data = read_json(marshal_path, default={})
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    plan = data.get('plan')
    if not isinstance(plan, dict):
        return None
    phase = plan.get(phase_key)
    if not isinstance(phase, dict):
        return None
    steps = phase.get('steps')
    if not isinstance(steps, list):
        return None
    return [s for s in steps if isinstance(s, str) and s]


def _resolve_footprint(plan_id: str) -> list[str]:
    """Derive the live plan footprint for ``plan_id`` on demand.

    Reads ``status.metadata.worktree_path`` to locate the worktree, then derives
    the footprint live via ``compute_plan_branch_diff`` (``{base}...HEAD`` ∪
    porcelain). Returns an empty list when no worktree is resolvable — which is
    the normal case during early compose at phase-4-plan, *before* phase-5
    materialises the worktree. The activation pre-filters treat an empty
    footprint as "no matches" and omit the gated step, preserving the prior
    behaviour where an absent/empty ledger omitted the self-review and
    pre-push-quality-gate steps.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return []
    status = read_json(status_path, default={})
    if not isinstance(status, dict):
        return []
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return []
    worktree_path = metadata.get('worktree_path', '')
    if not isinstance(worktree_path, str) or not worktree_path:
        return []
    worktree = Path(worktree_path)
    if not worktree.is_dir():
        return []

    refs_path = get_plan_dir(plan_id) / FILE_REFERENCES
    refs = read_json(refs_path, default={})
    if not isinstance(refs, dict):
        refs = {}
    base_ref = resolve_base_ref(None, refs)
    try:
        footprint = compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError:
        return []
    return sorted(footprint)


def _apply_commit_push_disabled(phase_6_candidates: list[str], commit_and_push: bool) -> tuple[list[str], bool]:
    """Pre-filter: drop ``commit-push`` when ``commit_and_push is False``.

    Also drops ``pre-push-quality-gate`` and ``pre-submission-self-review``
    because both gates are only meaningful when a downstream push exists.
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired.
    """
    if commit_and_push:
        return phase_6_candidates, False
    fired = False
    filtered: list[str] = []
    for step in phase_6_candidates:
        if step in {'commit-push', 'pre-push-quality-gate', 'pre-submission-self-review'}:
            fired = True
            continue
        filtered.append(step)
    return filtered, fired


def _apply_pre_push_quality_gate_inactive(phase_6_candidates: list[str], plan_id: str) -> tuple[list[str], bool]:
    """Pre-filter: drop ``pre-push-quality-gate`` when the build decision says so.

    Activation is the centralized build-necessity decision owned by
    ``extension_base.should_execute_build`` — the single home for the
    "is a build necessary?" verdict the four former consumer sites each
    re-derived. The decision is a pure function of the ``build.map``
    globs and the live plan footprint: it returns ``decision: build`` when the
    footprint touches a registered build glob, and ``decision: not_necessary``
    (with a log-friendly ``reason``) when the build_map registers no globs, the
    footprint is empty, or the footprint intersects no build glob.

    When the verdict is ``not_necessary``, ``pre-push-quality-gate`` is removed
    from ``phase_6_candidates``. The pre-filter is a no-op when
    ``pre-push-quality-gate`` is already absent (e.g., already filtered by
    ``_apply_commit_push_disabled``). Returns the filtered list plus a flag
    indicating whether the pre-filter fired (i.e., the step was active in the
    input but inactive after the check).
    """
    if 'pre-push-quality-gate' not in phase_6_candidates:
        return phase_6_candidates, False

    from extension_base import should_execute_build  # type: ignore[import-not-found]

    verdict = should_execute_build('quality-gate', plan_id)
    if verdict.get('decision') != 'build':
        return [s for s in phase_6_candidates if s != 'pre-push-quality-gate'], True

    # Build is necessary — keep the step.
    return phase_6_candidates, False


def _apply_pre_submission_self_review_inactive(phase_6_candidates: list[str], plan_id: str) -> tuple[list[str], bool]:
    """Pre-filter: drop ``pre-submission-self-review`` when activation conditions fail.

    Activation requires the live plan footprint to be non-empty. Unlike
    ``pre-push-quality-gate`` (which gates on the ``build.map``
    globs), this step has no glob gate — the four cognitive checks it targets
    (symmetric pairs, regex over-fit, wording, duplication) apply to any code or
    doc change. During early compose (phase-4-plan, before the worktree is
    materialised) the footprint is empty, so the step is omitted; it is
    re-evaluated against the live footprint on any later re-compose.

    The pre-filter is a no-op when ``pre-submission-self-review`` is already
    absent (e.g., already filtered by ``_apply_commit_push_disabled``).
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired.
    """
    if 'pre-submission-self-review' not in phase_6_candidates:
        return phase_6_candidates, False

    footprint = _resolve_footprint(plan_id)
    if not footprint:
        return [s for s in phase_6_candidates if s != 'pre-submission-self-review'], True

    return phase_6_candidates, False


# Code-touching change types that gate ``finalize-step-simplify`` activation.
# Branch-prefix reconciliation: ``fix`` → ``bug_fix``, ``chore`` → ``tech_debt``,
# ``feature`` → ``feature``. ``analysis`` / ``enhancement`` / ``verification`` are
# excluded. See standards/decision-rules.md § Pre-Filter: simplify_inactive.
_SIMPLIFY_CHANGE_TYPES = frozenset({'feature', 'bug_fix', 'tech_debt'})


def _apply_simplify_inactive(
    phase_6_candidates: list[str],
    change_type: str,
    affected_files_count: int,
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``finalize-step-simplify`` when its activation gate fails.

    The gate activates the step (keeps it) whenever BOTH:

    1. ``change_type ∈ {feature, bug_fix, tech_debt}`` — the three code-touching
       change types; and
    2. ``affected_files_count > 0``.

    When either condition fails, ``finalize-step-simplify`` is removed from
    ``phase_6_candidates``. The cognitive simplification pass uses no language
    detection — it is domain-agnostic by construction (it applies to any code
    or doc change in scope), so the gate consults only ``change_type`` and
    ``affected_files_count``.

    The pre-filter is a no-op when ``finalize-step-simplify`` is already absent
    from the candidate set (e.g., a project marshal.json that never lists it).
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired (i.e., the step was active in the input but dropped after the check).
    """
    if 'finalize-step-simplify' not in phase_6_candidates:
        return phase_6_candidates, False

    if change_type in _SIMPLIFY_CHANGE_TYPES and affected_files_count > 0:
        # Gate passes — keep the step.
        return phase_6_candidates, False

    return [s for s in phase_6_candidates if s != 'finalize-step-simplify'], True


# Code-bearing change types that gate ``finalize-step-whole-tree-gate``
# activation. Broader than ``_SIMPLIFY_CHANGE_TYPES`` because the whole-tree
# survivor sweep is meaningful for ``enhancement`` deletions too; ``analysis``
# (no code change) and ``verification`` (tests only, deletes nothing) are
# excluded. See standards/decision-rules.md § Pre-Filter: whole_tree_gate_inactive.
_WHOLE_TREE_GATE_CHANGE_TYPES = frozenset({'tech_debt', 'feature', 'enhancement', 'bug_fix'})


def _read_compatibility() -> str:
    """Read ``plan.phase-2-refine.compatibility`` from marshal.json.

    Returns ``'breaking'`` when the file is missing, the keys are absent, or the
    value is not a non-empty string — matching ``DEFAULT_PLAN_REFINE['compatibility']``,
    so a fresh project (or one that never overrode the knob) resolves to the
    default the rest of the pipeline assumes. The composer reads marshal.json
    straight through, mirroring ``_read_drop_review_on_scope_gate``.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.exists():
        return 'breaking'
    try:
        data = read_json(marshal_path, default={})
    except (OSError, json.JSONDecodeError):
        return 'breaking'
    if not isinstance(data, dict):
        return 'breaking'
    plan = data.get('plan')
    if not isinstance(plan, dict):
        return 'breaking'
    refine = plan.get('phase-2-refine')
    if not isinstance(refine, dict):
        return 'breaking'
    value = refine.get('compatibility')
    if isinstance(value, str) and value.strip():
        return value.strip()
    return 'breaking'


def _apply_whole_tree_gate_inactive(
    phase_6_candidates: list[str],
    compatibility: str,
    change_type: str,
    affected_files_count: int,
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``finalize-step-whole-tree-gate`` when its gate fails.

    The whole-tree completeness gate exists to catch survivors of deletions a
    clean-slate/breaking plan was meant to remove, so the gate activates the
    step (keeps it) whenever ALL of:

    1. ``compatibility == 'breaking'`` — a ``deprecation`` / ``smart_and_ask``
       plan deliberately keeps old surfaces alongside new ones, so a surviving
       reference is expected, not a defect;
    2. ``change_type ∈ {tech_debt, feature, enhancement, bug_fix}`` — the
       code-bearing change types; ``analysis`` / ``verification`` delete
       nothing; and
    3. ``affected_files_count > 0``.

    When any condition fails, ``finalize-step-whole-tree-gate`` is removed from
    ``phase_6_candidates``. The pre-filter is a no-op when the step is already
    absent from the candidate set (e.g., a project marshal.json that never lists
    it). Returns the filtered list plus a flag indicating whether the pre-filter
    fired (i.e., the step was active in the input but dropped after the check).
    """
    if 'finalize-step-whole-tree-gate' not in phase_6_candidates:
        return phase_6_candidates, False

    if (
        compatibility == 'breaking'
        and change_type in _WHOLE_TREE_GATE_CHANGE_TYPES
        and affected_files_count > 0
    ):
        # Gate passes — keep the step.
        return phase_6_candidates, False

    return [s for s in phase_6_candidates if s != 'finalize-step-whole-tree-gate'], True


# Scope-gated phase-6 subtraction sets. Each entry lists the step references the
# scope_gated_finalize pre-filter drops, expressed as match-sets that cover both
# the bare and prefixed forms a candidate list may carry. The candidate list is
# boundary-normalized by ``_strip_default_prefix`` before pre-filters run, so the
# optional ``default:`` prefix is already gone; ``project:`` and ``bundle:skill``
# prefixes are preserved verbatim, so the surgical set lists both forms. See
# standards/decision-rules.md § Pre-Filter: scope_gated_finalize.
#
# ``automated-review`` is deliberately NOT in either implicit set: the
# bot-enforcement guard re-adds it on GitHub/GitLab plans, so dropping it via
# the implicit scope gate would be a silently-undone no-op. The only path that
# suppresses ``automated-review`` is the explicit ``drop_review_on_scope_gate``
# opt-in (see ``_apply_scope_gated_finalize``).
_SCOPE_GATED_SURGICAL_DROP = frozenset(
    {
        'plan-retrospective',
        'plan-marshall:plan-retrospective',
        'finalize-step-pre-submission-self-review',
        'project:finalize-step-pre-submission-self-review',
        'finalize-step-plugin-doctor',
        'project:finalize-step-plugin-doctor',
    }
)
_SCOPE_GATED_SINGLE_MODULE_DROP = frozenset(
    {
        'plan-retrospective',
        'plan-marshall:plan-retrospective',
    }
)
_SCOPE_GATED_OVERRIDE_DROP = frozenset({'automated-review', 'default:automated-review'})


def _read_drop_review_on_scope_gate() -> bool:
    """Read ``plan.phase-6-finalize.drop_review_on_scope_gate`` from marshal.json.

    Returns ``False`` when the file is missing, the keys are absent, or the
    value is not a boolean ``True``. The escape hatch defaults to off: only an
    explicit ``true`` in marshal.json activates the additional
    ``automated-review`` suppression in the scope_gated_finalize pre-filter.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.exists():
        return False
    data = read_json(marshal_path, default={})
    if not isinstance(data, dict):
        return False
    plan = data.get('plan')
    if not isinstance(plan, dict):
        return False
    phase_6 = plan.get('phase-6-finalize')
    if not isinstance(phase_6, dict):
        return False
    return phase_6.get('drop_review_on_scope_gate') is True


def _apply_scope_gated_finalize(
    phase_6_candidates: list[str],
    scope_estimate: str,
    drop_review_on_scope_gate: bool,
) -> tuple[list[str], list[str]]:
    """Pre-filter: drop heavyweight phase-6 review/audit steps by scope.

    Subtractions:

    - ``scope_estimate == 'surgical'`` → drop ``plan-marshall:plan-retrospective``,
      ``project:finalize-step-pre-submission-self-review``, and
      ``project:finalize-step-plugin-doctor`` (both bare and prefixed forms).
    - ``scope_estimate == 'single_module'`` → drop only
      ``plan-marshall:plan-retrospective``.
    - Any other scope value → no implicit subtraction.

    ``automated-review`` is NEVER subtracted by the implicit scope gate (the
    bot-enforcement guard would re-add it, making the subtraction a no-op).
    When ``drop_review_on_scope_gate`` is ``True`` AND the plan is itself
    scope-gated (``scope_estimate in ('surgical', 'single_module')``), the gate
    additionally drops ``automated-review`` — the only path that suppresses the
    bot-review gate, explicitly opted into via marshal.json. The override is
    scoped, not global: on non-scope-gated plans (``multi_module`` / ``broad`` /
    ``none``) the override is inert, so flipping the project-wide knob can never
    silently disable bot review on a large plan.

    Consistent with the composer's "rows and pre-filters only ever narrow the
    candidate list" architecture, this pre-filter runs before the seven-row
    matrix and the bot-enforcement guard. Returns the filtered candidate list
    plus the list of step references that were dropped (for per-subtraction
    decision-log emission). The dropped list preserves the candidate's verbatim
    form so the decision log names exactly what was removed.
    """
    if scope_estimate == 'surgical':
        drop_set: frozenset[str] = _SCOPE_GATED_SURGICAL_DROP
    elif scope_estimate == 'single_module':
        drop_set = _SCOPE_GATED_SINGLE_MODULE_DROP
    else:
        drop_set = frozenset()

    if drop_review_on_scope_gate and scope_estimate in ('surgical', 'single_module'):
        drop_set = drop_set | _SCOPE_GATED_OVERRIDE_DROP

    if not drop_set:
        return phase_6_candidates, []

    kept: list[str] = []
    dropped: list[str] = []
    for step in phase_6_candidates:
        if step in drop_set:
            dropped.append(step)
        else:
            kept.append(step)
    return kept, dropped


def _log_scope_gated_finalize_subtraction(plan_id: str, scope_estimate: str, dropped_step: str) -> None:
    """Emit one decision-log entry per scope_gated_finalize subtraction."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction — '
        f'scope_estimate={scope_estimate}, dropped {dropped_step} from phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# plan.phase-6-finalize run-at-all selection (post-matrix transform)
# =============================================================================
#
# The four finalize run-at-all gates (`plan.phase-6-finalize.<gate>`) drive
# a post-matrix transform that forces each gate's finalize step in (`always`),
# out (`never`), or defers to the existing decision machinery (`auto`, the
# default no-op). Each gate maps to exactly one finalize step ID:
#
#   self_review   → finalize-step-pre-submission-self-review
#   qgate         → pre-push-quality-gate (the finalize blocking-findings re-capture)
#   plugin_doctor → finalize-step-plugin-doctor
#   simplify      → finalize-step-simplify (holistic post-implementation sweep)
#
# `simplify` is the symmetric peer of the other three gates: `auto` defers to
# the `simplify_inactive` pre-filter that already decided the step at matrix
# time, `always` re-adds it even when that pre-filter dropped it, and `never`
# forces it out.
#
# The transform NEVER touches `automated-review`: the bot-review invariant
# (enforced by `_apply_bot_enforcement_guard`) is orthogonal and is preserved
# verbatim — the four finalize gates are the only
# finalize steps this transform may add or drop. Run-at-all values are validated
# at set time by `manage-config`'s `validate_run_at_all`; the composer
# defensively treats any non-`{always,never}` value (including `auto` and a
# malformed value) as defer.
#
# Step IDs are matched against both the bare form and every prefixed form a
# candidate list may carry. Candidate lists are `default:`-namespace-normalized
# at intake (`_strip_default_prefix`), but `project:` / `bundle:skill` prefixes
# are preserved verbatim, so the match-sets below list every form. The `always`
# re-insertion uses the canonical `project:`-prefixed form for the two
# finalize-step skills (their authoritative manifest shape) and the bare form
# for `pre-push-quality-gate` (a built-in `default:` step, normalized bare).

# Gate → (match-set, canonical insertion form). The match-set covers every
# prefixed/bare form a candidate list may carry; the insertion form is the
# canonical identifier `always` re-adds when the step is absent.
_CEREMONY_FINALIZE_STEP_MAP: dict[str, tuple[frozenset[str], str]] = {
    'self_review': (
        frozenset(
            {
                'finalize-step-pre-submission-self-review',
                'project:finalize-step-pre-submission-self-review',
            }
        ),
        'project:finalize-step-pre-submission-self-review',
    ),
    'qgate': (
        frozenset({'pre-push-quality-gate'}),
        'pre-push-quality-gate',
    ),
    'plugin_doctor': (
        frozenset(
            {
                'finalize-step-plugin-doctor',
                'project:finalize-step-plugin-doctor',
            }
        ),
        'project:finalize-step-plugin-doctor',
    ),
    'simplify': (
        frozenset({'finalize-step-simplify'}),
        'finalize-step-simplify',
    ),
}

# The run-at-all gate fields for the finalize section, in canonical order.
_CEREMONY_FINALIZE_GATES = ('self_review', 'qgate', 'plugin_doctor', 'simplify')

# Canonical default for every finalize gate when marshal.json omits the block.
_CEREMONY_FINALIZE_DEFAULT = 'auto'


def _read_finalize_gates() -> dict[str, str]:
    """Resolve the four ``plan.phase-6-finalize`` run-at-all gate values.

    Reads ``marshal.json``'s ``plan.phase-6-finalize`` block directly (the
    composer reads marshal.json straight through, like the planning-lane
    router), merging the canonical ``auto`` default under any absent gate. Each
    gate (``self_review`` / ``qgate`` / ``plugin_doctor`` / ``simplify``) is a
    flat phase-local knob — read via
    ``manage-config plan phase-6-finalize get --field <gate>``.

    Returns a ``{gate: value}`` dict for the four finalize gates; values are
    always one of the configured values (or the ``auto`` default). The caller
    treats any value other than ``always`` / ``never`` as defer.
    """
    resolved: dict[str, str] = dict.fromkeys(_CEREMONY_FINALIZE_GATES, _CEREMONY_FINALIZE_DEFAULT)

    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.exists():
        return resolved
    try:
        data = read_json(marshal_path, default={})
    except (OSError, json.JSONDecodeError):
        return resolved
    if not isinstance(data, dict):
        return resolved
    plan_block = data.get('plan')
    if not isinstance(plan_block, dict):
        return resolved
    finalize = plan_block.get('phase-6-finalize')
    if not isinstance(finalize, dict):
        return resolved

    for gate in _CEREMONY_FINALIZE_GATES:
        value = finalize.get(gate)
        if isinstance(value, str) and value:
            resolved[gate] = value

    return resolved


def _ceremony_finalize_insert_index(phase_6_steps: list[str]) -> int:
    """Resolve the insertion position for an ``always``-forced finalize step.

    A ceremony finalize step must run before the plan-mutating tail
    (``archive-plan`` / ``record-metrics`` / ``branch-cleanup`` /
    ``plan-marshall:plan-retrospective``) so the gate is honoured before the
    plan directory is moved or the branch cleaned up. Returns the index of the
    first plan-mutating step, or the end of the list when no anchor is present.
    """
    plan_mutating = {
        'archive-plan',
        'record-metrics',
        'branch-cleanup',
        'plan-marshall:plan-retrospective',
    }
    for index, step in enumerate(phase_6_steps):
        if step in plan_mutating:
            return index
    return len(phase_6_steps)


def _apply_ceremony_finalize_selection(
    phase_6_steps: list[str],
    gates: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Force ceremony finalize gates in (``always``) / out (``never``) in-place.

    For each of the three finalize gates:

    - ``never`` → drop every match-set form of the gate's step from
      ``phase_6_steps`` (a no-op when already absent).
    - ``always`` → ensure the gate's canonical step is present, inserting it
      before the plan-mutating tail when absent (a no-op when any match-set form
      is already present).
    - any other value (``auto`` / malformed) → defer (no-op).

    ``automated-review`` is NEVER touched — the gate map contains only the three
    ceremony finalize steps, so the bot-review invariant is structurally
    preserved.

    Mutates ``phase_6_steps`` in place. Returns ``(forced_in, forced_out)`` —
    two lists of ``{'gate': ..., 'step': ...}`` dicts naming each gate that
    actually changed the list, for per-change decision-log emission.
    """
    forced_in: list[dict[str, str]] = []
    forced_out: list[dict[str, str]] = []

    for gate in _CEREMONY_FINALIZE_GATES:
        value = gates.get(gate, _CEREMONY_FINALIZE_DEFAULT)
        match_set, canonical = _CEREMONY_FINALIZE_STEP_MAP[gate]

        if value == 'never':
            present = [s for s in phase_6_steps if s in match_set]
            if present:
                phase_6_steps[:] = [s for s in phase_6_steps if s not in match_set]
                forced_out.append({'gate': gate, 'step': present[0]})
        elif value == 'always':
            if not any(s in match_set for s in phase_6_steps):
                insert_index = _ceremony_finalize_insert_index(phase_6_steps)
                phase_6_steps.insert(insert_index, canonical)
                forced_in.append({'gate': gate, 'step': canonical})
        # else: defer (auto / malformed) — no-op.

    return forced_in, forced_out


def _log_ceremony_finalize_selection(
    plan_id: str,
    gate: str,
    value: str,
    step: str,
) -> None:
    """Emit one decision-log entry per ceremony-finalize forced in/out change."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
        f'finalize.{gate}={value}, {"added" if value == "always" else "dropped"} {step} '
        f'{"to" if value == "always" else "from"} phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


def _read_ci_provider() -> str | None:
    """Return the CI provider identifier (``github``, ``gitlab``) from marshal.json.

    The provider is resolved from the ``providers[]`` entry where
    ``category == 'ci'``, mapping skill name to a short identifier:

    * ``plan-marshall:workflow-integration-github`` -> ``github``
    * ``plan-marshall:workflow-integration-gitlab`` -> ``gitlab``

    Returns ``None`` when the marshal file is missing, no CI provider is
    declared, or the resolved value is neither ``github`` nor ``gitlab``.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.is_file():
        return None
    try:
        data = read_json(marshal_path)
    except (OSError, json.JSONDecodeError):
        return None
    providers = data.get('providers')
    if not isinstance(providers, list):
        return None
    for entry in providers:
        if not isinstance(entry, dict):
            continue
        if entry.get('category') != 'ci':
            continue
        skill_name = entry.get('skill_name', '')
        if not isinstance(skill_name, str):
            continue
        if skill_name == 'plan-marshall:workflow-integration-github':
            return 'github'
        if skill_name == 'plan-marshall:workflow-integration-gitlab':
            return 'gitlab'
    return None


def _apply_bot_enforcement_guard(phase_6_steps: list[str], plan_id: str) -> str | None:
    """Composition-time defense-in-depth: keep ``automated-review`` on GitHub/GitLab plans.

    PR-review bots are effectively mandatory whenever the plan finalizes
    through GitHub or GitLab. If the seven-row matrix or any pre-filter has
    dropped ``automated-review`` AND the project's CI provider is GitHub or
    GitLab, this guard remediates by appending ``automated-review`` back into
    ``phase_6_steps`` (in-place) and emits a decision-log entry so the
    manifest's reconstruction-from-rules-alone remains auditable. The guard is
    remediation rather than assertion because Row 5 of the seven-row matrix
    legitimately drops ``automated-review`` for ``surgical+{bug_fix,
    tech_debt}`` plans, and an assertion-style guard would deadlock
    every such plan that finalizes through GitHub or GitLab.

    The guard is retained after the deadlock fix as defense-in-depth: any
    future pre-filter, rule addition, or recipe interaction that drops
    ``automated-review`` on a GitHub/GitLab plan will be caught and
    remediated by the same code path.

    Returns ``None`` for the no-op path (non-GitHub/GitLab CI) and for the
    remediated path (``automated-review`` was missing and has been re-added).
    Returns the offending CI provider identifier (``github`` or ``gitlab``)
    only on a non-remediable violation — currently unreachable; retained as
    a safety net for future logic that may detect a violation it cannot
    auto-fix, which the caller translates into a ``bot_enforcement_violation``
    error TOON.
    """
    provider = _read_ci_provider()
    if provider not in {'github', 'gitlab'}:
        return None
    # ``phase_6_steps`` is the matrix output. Its entries are bare names —
    # ``cmd_compose`` boundary-normalized the candidate list before the matrix
    # ran. Compare bare strings without per-site stripping.
    if 'automated-review' in phase_6_steps:
        return None
    insert_index = _bot_enforcement_insert_index(phase_6_steps)
    phase_6_steps.insert(insert_index, 'automated-review')
    _log_bot_enforcement_guard_remediated(plan_id, provider)
    return None


def _bot_enforcement_insert_index(phase_6_steps: list[str]) -> int:
    """Resolve the canonical insertion position for ``automated-review``.

    The remediation must place ``automated-review`` somewhere it can run before
    plan-mutating steps (notably ``archive-plan``, which moves the plan
    directory). ``phase_6_steps`` carries boundary-normalized bare default
    names (plus possibly the project-prefixed early sync step), so anchor
    lookups compare plain strings without per-site stripping. Resolution
    order:

    1. Immediately after ``create-pr`` (its natural neighbour in the
       candidate ordering — review runs against the freshly-opened PR).
    2. Else immediately before the first plan-mutating step
       (``archive-plan``, ``record-metrics``,
       ``plan-marshall:plan-retrospective``, ``branch-cleanup``).
    3. Else at the end of the list (no anchors found).
    """
    for index, step in enumerate(phase_6_steps):
        if step == 'create-pr':
            return index + 1
    plan_mutating = {
        'archive-plan',
        'record-metrics',
        'branch-cleanup',
        'plan-marshall:plan-retrospective',
    }
    for index, step in enumerate(phase_6_steps):
        if step in plan_mutating:
            return index
    return len(phase_6_steps)


def _validate_automated_review_placement(phase_6_steps: list[str]) -> str | None:
    """Compose-time placement check for ``automated-review`` ordering.

    Defense-in-depth complement to ``_apply_bot_enforcement_guard``. The
    remediation guard ensures ``automated-review`` is *present* on
    GitHub/GitLab plans, but a future pre-filter, recipe interaction, or
    candidate ordering glitch could leave it *misplaced* — sitting at an
    index later than a plan-mutating step (``archive-plan``,
    ``record-metrics``, ``branch-cleanup``, or
    ``plan-marshall:plan-retrospective``). Such a manifest would dispatch
    the review bot only after the plan directory has already been moved or
    the branch cleaned up, defeating the lesson the guard exists to enforce.

    Comparison runs against bare names: by the time this validator is
    invoked, ``cmd_compose`` has already boundary-normalized
    ``phase_6_candidates`` and the matrix output preserves the same shape.
    Both the bare ``automated-review`` name and its
    ``default:automated-review`` form are detected so future callers cannot
    silently slip past the check by re-prefixing.

    Returns a diagnostic string naming both the offending
    ``automated-review`` index and the first plan-mutating anchor that
    precedes it. Returns ``None`` when the order is valid (or when
    ``automated-review`` is absent — the remediation guard is responsible
    for presence; this validator is concerned only with ordering).
    """
    plan_mutating = {
        'archive-plan',
        'record-metrics',
        'branch-cleanup',
        'plan-marshall:plan-retrospective',
    }

    review_index: int | None = None
    for index, step in enumerate(phase_6_steps):
        if step in {'automated-review', 'default:automated-review'}:
            review_index = index
            break
    if review_index is None:
        return None

    # The violation is the inverse of the desired order: a plan-mutating
    # anchor at an index *less* than ``review_index`` means the review bot
    # fires AFTER the plan directory has been moved or the branch cleaned
    # up. Return the earliest such anchor so the diagnostic names the
    # first ordering breach.
    for index, step in enumerate(phase_6_steps):
        if index >= review_index:
            break
        if step in plan_mutating:
            return f'automated-review at index {review_index} must precede {step} at index {index}'
    return None


# =============================================================================
# execution_tier Routing (per-task verification command classification)
# =============================================================================
#
# Each plan task carries a ``verification.commands`` list whose entries are
# already in resolved form — they are the exact strings dispatched at
# phase-5-execute time. The composer classifies each command via
# ``architecture resolve`` to obtain the four ``execution_tier`` fields
# emitted by that script:
#
# * ``execution_tier == 'orchestrator'`` — the command's adaptive bash
#   timeout has exceeded the host platform's 600s Bash-tool ceiling, so the
#   command MUST run from orchestrator tier rather than a sub-agent's Bash
#   call. The composer maps the build verb (``quality-gate`` / ``verify`` /
#   ``module-tests`` / ``coverage``) to the matching phase-5 step ID,
#   appends it (deduped) to ``phase_5.verification_steps``, and removes the
#   command from the task's verification list. The task may end up with an
#   empty ``verification.commands`` list if every command routed to
#   orchestrator — that is the correct outcome.
# * ``execution_tier == 'per_task'`` — the command fits inside the Bash
#   ceiling. The composer writes ``bash_timeout_seconds`` into the
#   verification entry alongside ``commands`` so the dispatched sub-agent
#   reads the numeric timeout directly. The command itself stays in the
#   task.
# * No ``execution_tier`` field in the resolve TOON — non-build executable
#   (raw shell, ``grep``, ``manage-*`` notation). Behave as today: leave
#   the command in the task, no ``bash_timeout_seconds`` annotation.
#
# Re-entrant by construction: every invocation re-derives the routing from
# the live ``architecture resolve`` output and rewrites both the manifest's
# ``phase_5.verification_steps`` (de-duped) and the task files (per-task
# ``bash_timeout_seconds`` re-written, orchestrator commands re-pruned).
# A previous compose that left a task with empty ``verification.commands``
# is re-noted but the empty state is the canonical "all orchestrator"
# signal.

# Build verb → phase-5 step ID mapping. The four canonical verbs are the
# ones registered by every build skill's ``_CONFIG`` (verify / quality-gate /
# coverage / module-tests). Verbs not in this map are left to the consumer
# (the composer skips routing for unmapped verbs, preserving today's
# behaviour).
_VERB_TO_PHASE_5_STEP: dict[str, str] = {
    'quality-gate': 'default:quality_check',
    'verify': 'default:build_verify',
    'module-tests': 'default:build_verify',
    'coverage': 'default:coverage_check',
}


def _parse_verification_command(cmd: str) -> tuple[str, str] | None:
    """Extract ``(verb, command_args)`` from a Bucket B build verification command.

    Accepts the canonical shape::

        python3 .plan/execute-script.py {build_notation} run --command-args "{args}"

    where ``{args}`` typically reads as ``"<verb> [module]"`` (e.g.
    ``"verify plan-marshall"``). Returns ``(verb, command_args)`` on a
    successful parse, ``None`` for any non-build invocation (raw shell,
    grep, Bucket A ``manage-*`` notations, malformed quoting, etc.). The
    verb is always the first whitespace-separated token of ``command_args``.

    The parse is intentionally permissive on the trailing module/profile
    arguments — only ``verb`` is needed to map to a phase-5 step ID; the
    ``command_args`` payload is forwarded verbatim to ``architecture
    resolve`` when the composer subprocesses it.
    """
    if not cmd:
        return None
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return None
    # Locate the executor token (allow ``python3`` / ``python`` prefix variations).
    script_index: int | None = None
    for i, tok in enumerate(tokens):
        if tok.endswith('.plan/execute-script.py') or tok.endswith('execute-script.py'):
            script_index = i
            break
    if script_index is None:
        return None
    # Notation immediately follows the script path; the four Bucket B build
    # notations are the only ones that emit execution_tier fields on resolve.
    notation_index = script_index + 1
    if notation_index >= len(tokens):
        return None
    notation = tokens[notation_index]
    if not notation.startswith('plan-marshall:build-'):
        return None
    # Subcommand ``run``.
    sub_index = notation_index + 1
    if sub_index >= len(tokens) or tokens[sub_index] != 'run':
        return None
    # ``--command-args`` (accept ``--command-args VAL`` and ``--command-args=VAL``).
    command_args: str | None = None
    i = sub_index + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--command-args':
            if i + 1 < len(tokens):
                command_args = tokens[i + 1]
            break
        if tok.startswith('--command-args='):
            command_args = tok[len('--command-args=') :]
            break
        i += 1
    if command_args is None or not command_args.strip():
        return None
    verb = command_args.strip().split()[0]
    return verb, command_args


def _verb_to_phase_5_step(verb: str) -> str | None:
    """Return the phase-5 step ID for a build verb, or ``None`` when unmapped."""
    return _VERB_TO_PHASE_5_STEP.get(verb)


def _resolve_command_tier(cmd: str, plan_id: str) -> dict[str, Any] | None:
    """Subprocess ``architecture resolve`` for a verification command's verb.

    Calls the executor with ``--audit-plan-id`` so resolve runs in the
    correct project_dir context, parses the TOON output via ``parse_toon``,
    and returns the resolve dict. Returns ``None`` on any failure — the
    composer treats ``None`` as "non-build / unresolvable" and leaves the
    command unrouted.

    The composer subprocesses ``architecture resolve`` rather than
    importing its internals because the resolve flow is the canonical
    cross-bundle entry point per the "Build commands: resolve via
    architecture" hard rule, and the augmented TOON shape (the four
    ``execution_tier`` fields) is exactly the resolve script's
    contract — re-deriving them here would duplicate logic.
    """
    parsed = _parse_verification_command(cmd)
    if parsed is None:
        return None
    verb, command_args = parsed
    # Module: second whitespace-separated token of command_args, when present.
    parts = command_args.strip().split()
    module = parts[1] if len(parts) >= 2 else None

    executor = _resolve_executor()
    if executor is None:
        return None
    argv: list[str] = [
        sys.executable,
        str(executor),
        'plan-marshall:manage-architecture:architecture',
        'resolve',
        '--command',
        verb,
        '--audit-plan-id',
        plan_id,
    ]
    if module:
        argv.extend(['--module', module])
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        parsed_toon = parse_toon(proc.stdout)
    except Exception:
        return None
    if not isinstance(parsed_toon, dict) or parsed_toon.get('status') != 'success':
        return None
    return parsed_toon


def _route_task_verification_commands(plan_id: str, body: dict[str, Any]) -> int:
    """Walk plan tasks; route verification commands by ``execution_tier``.

    For each ``TASK-*.json`` under ``{plan_dir}/tasks/``:

    - Skip the task when it has no ``verification.commands`` list.
    - Classify each command via ``_resolve_command_tier``.
    - ``orchestrator`` → map the verb to its phase-5 step ID, append
      (de-duped) to ``body['phase_5']['verification_steps']``, and drop the
      command from the task's ``verification.commands``.
    - ``per_task`` → set ``verification.bash_timeout_seconds`` on the task
      (overwriting any prior value so re-compose is deterministic). When
      multiple ``per_task`` commands share a task, the maximum
      ``bash_timeout_seconds`` wins — the dispatched sub-agent honours the
      most-demanding command.
    - No tier (non-build / unresolvable) → leave the command in place, no
      annotation.

    The function mutates ``body`` in place and rewrites each task's JSON
    file when its verification dict changed. Returns the count of task
    files mutated for downstream logging.
    """
    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    if not tasks_dir.is_dir():
        return 0

    phase_5 = body.setdefault('phase_5', {})
    verification_steps = phase_5.setdefault('verification_steps', [])
    if not isinstance(verification_steps, list):
        verification_steps = list(verification_steps)
        phase_5['verification_steps'] = verification_steps
    # De-dup helper: track membership for O(1) lookup while preserving order.
    seen_steps: set[str] = set(verification_steps)

    mutated_tasks = 0
    for task_path in sorted(tasks_dir.glob('TASK-*.json')):
        try:
            task = read_json(task_path, default=None)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(task, dict):
            continue
        verification = task.get('verification')
        if not isinstance(verification, dict):
            continue
        commands = verification.get('commands')
        if not isinstance(commands, list) or not commands:
            continue

        kept_commands: list[Any] = []
        per_task_timeout: int | None = None
        changed = False
        for raw in commands:
            if not isinstance(raw, str):
                kept_commands.append(raw)
                continue
            resolve_toon = _resolve_command_tier(raw, plan_id)
            tier = resolve_toon.get('execution_tier') if isinstance(resolve_toon, dict) else None
            if tier == 'orchestrator':
                parsed = _parse_verification_command(raw)
                if parsed is None:
                    # Defensive: classifier said orchestrator but we cannot
                    # extract the verb. Leave the command in place so the
                    # mapping mismatch is observable in the next compose.
                    kept_commands.append(raw)
                    continue
                verb, _ = parsed
                step_id = _verb_to_phase_5_step(verb)
                if step_id is None:
                    # Unmapped verb (e.g. a custom build target). Leave the
                    # command per-task so the existing flow handles it.
                    kept_commands.append(raw)
                    continue
                if step_id not in seen_steps:
                    verification_steps.append(step_id)
                    seen_steps.add(step_id)
                changed = True
                continue
            if tier == 'per_task':
                bash_timeout = resolve_toon.get('bash_timeout_seconds') if isinstance(resolve_toon, dict) else None
                if isinstance(bash_timeout, int):
                    if per_task_timeout is None or bash_timeout > per_task_timeout:
                        per_task_timeout = bash_timeout
                kept_commands.append(raw)
                continue
            # No tier or unresolvable → leave the command in place.
            kept_commands.append(raw)

        if kept_commands != commands:
            verification['commands'] = kept_commands
            changed = True
        # Always write the timeout when at least one per_task command was
        # classified — repeat composes converge on the same value.
        existing_timeout = verification.get('bash_timeout_seconds')
        if per_task_timeout is not None:
            if existing_timeout != per_task_timeout:
                verification['bash_timeout_seconds'] = per_task_timeout
                changed = True
        else:
            # No per_task commands survived: strip any stale annotation so
            # re-composes after a tier shift do not leave the field behind.
            if 'bash_timeout_seconds' in verification:
                del verification['bash_timeout_seconds']
                changed = True

        if changed:
            task['verification'] = verification
            task_path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
            mutated_tasks += 1

    return mutated_tasks


def _log_execution_tier_routing(plan_id: str, mutated_tasks: int, phase_5_steps: list[str]) -> None:
    """Emit one decision-log entry summarising the execution_tier routing pass.

    Logged regardless of whether any task was mutated so the routing is
    observable from ``decision.log`` for every compose call. The entry
    names both the count of touched tasks and the final phase-5 step list
    so retrospective audits can correlate manifest content with task-file
    mutations.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) execution_tier routing — '
        f'mutated_tasks={mutated_tasks}, phase_5.verification_steps={phase_5_steps}'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_compose(args: argparse.Namespace) -> dict[str, Any] | None:
    """Compose and write the execution manifest."""
    plan_id = require_valid_plan_id(args)

    if args.change_type not in VALID_CHANGE_TYPES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_change_type',
            'message': f'Invalid change_type: {args.change_type!r}. Must be one of {list(VALID_CHANGE_TYPES)}',
        }
    if args.scope_estimate not in VALID_SCOPE_ESTIMATES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_scope_estimate',
            'message': f'Invalid scope_estimate: {args.scope_estimate!r}. Must be one of {list(VALID_SCOPE_ESTIMATES)}',
        }
    if args.track not in VALID_TRACKS:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_track',
            'message': f'Invalid track: {args.track!r}. Must be one of {list(VALID_TRACKS)}',
        }

    raw_commit_and_push = getattr(args, 'commit_and_push', None)
    if raw_commit_and_push is None:
        commit_and_push = True
    elif isinstance(raw_commit_and_push, bool):
        commit_and_push = raw_commit_and_push
    elif str(raw_commit_and_push).lower() in ('true', 'false'):
        commit_and_push = str(raw_commit_and_push).lower() == 'true'
    else:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_commit_and_push',
            'message': f'Invalid commit_and_push: {raw_commit_and_push!r}. Must be one of [true, false]',
        }

    # Source of truth for the candidate step lists: marshal.json
    # ``plan.phase-{5,6}-{execute,finalize}.steps``. The agent-supplied
    # ``--phase-{5,6}-steps`` CSV is a fallback for callers without a
    # marshal.json (notably tests). marshal.json is preferred because the
    # agent has historically built CSVs that strip ``project:`` and
    # ``bundle:skill`` prefixes, producing manifests with bare names that
    # the phase-6-finalize dispatcher then mis-routes as built-in steps.
    # See lesson reference in ``_read_marshal_phase_steps``.
    marshal_phase_5 = _read_marshal_phase_steps('phase-5-execute')
    marshal_phase_6 = _read_marshal_phase_steps('phase-6-finalize')
    phase_5_source = 'marshal.json' if marshal_phase_5 is not None else 'csv_fallback'
    phase_6_source = 'marshal.json' if marshal_phase_6 is not None else 'csv_fallback'
    if marshal_phase_5 is not None:
        phase_5_candidates = list(marshal_phase_5)
    else:
        phase_5_candidates = _split_csv(args.phase_5_steps, DEFAULT_PHASE_5_STEPS)
    if marshal_phase_6 is not None:
        phase_6_candidates = list(marshal_phase_6)
    else:
        phase_6_candidates = _split_csv(args.phase_6_steps, DEFAULT_PHASE_6_STEPS)

    # Boundary normalization: callers (notably marshal.json) may pass step IDs
    # with the optional ``default:`` prefix; the seven-row matrix, the pre-filter
    # helpers, the bundle-self-modification matcher, and the bot-enforcement
    # guard all compare against bare names. Normalize once at the boundary so
    # every downstream site can use plain `s in {...}` / `s == 'foo'` checks
    # without per-site `_strip_default_prefix` calls. Normalizing at the
    # boundary covers every comparison site, not just the cascade-rule sites.
    # External step prefixes (``project:``, ``bundle:skill``) are preserved
    # verbatim so the dispatcher can route them as PROJECT / SKILL steps.
    phase_5_candidates = [_strip_default_prefix(s) for s in phase_5_candidates]
    phase_6_candidates = [_strip_default_prefix(s) for s in phase_6_candidates]

    # Pre-filters run before the seven-row matrix. They are orthogonal to the
    # row matrix's change-type / scope / recipe inputs and operate on the
    # candidate list. The order is fixed and documented in
    # standards/decision-rules.md:
    #   1. commit_push_disabled — drop commit-push (and pre-push-quality-gate
    #      and pre-submission-self-review) when no push will occur.
    #   2. pre_push_quality_gate_inactive — drop pre-push-quality-gate when
    #      build.map carries no globs or no live-footprint entry
    #      matches a build_map glob.
    #   3. pre_submission_self_review_inactive — drop pre-submission-self-review
    #      when the live footprint is empty.
    #   4. simplify_inactive — drop finalize-step-simplify when
    #      change_type ∉ {feature, bug_fix, tech_debt} OR affected_files_count == 0.
    #   5. whole_tree_gate_inactive — drop finalize-step-whole-tree-gate unless
    #      compatibility == breaking AND change_type ∈ {tech_debt, feature,
    #      enhancement, bug_fix} AND affected_files_count > 0.
    # Each pre-filter returns (filtered_candidates, fired_flag); we log a
    # dedicated decision-log line per fired pre-filter in addition to the row
    # log line emitted by _log_decision below.
    phase_6_candidates, commit_push_omitted = _apply_commit_push_disabled(phase_6_candidates, commit_and_push)
    phase_6_candidates, pre_push_quality_gate_omitted = _apply_pre_push_quality_gate_inactive(
        phase_6_candidates, plan_id
    )
    phase_6_candidates, pre_submission_self_review_omitted = _apply_pre_submission_self_review_inactive(
        phase_6_candidates, plan_id
    )

    affected_files_count = max(0, int(args.affected_files_count or 0))
    # Recipe / lesson provenance: an explicit --recipe-key wins; otherwise read
    # status.metadata.plan_source directly so lesson/recipe-derived plans fire
    # Row 2 even when the phase-4-plan agent omitted the flag. See
    # _read_recipe_source and standards/decision-rules.md § Row 2.
    recipe_key = args.recipe_key or _read_recipe_source(plan_id)
    task_queue_active = _read_task_queue_active(plan_id)

    # Pre-filter 4 (simplify_inactive) consults change_type + affected_files_count,
    # both resolved above; it runs after the three candidate-narrowing pre-filters
    # and before the seven-row matrix per standards/decision-rules.md.
    phase_6_candidates, simplify_omitted = _apply_simplify_inactive(
        phase_6_candidates, args.change_type, affected_files_count
    )

    # Pre-filter 5 (whole_tree_gate_inactive) drops finalize-step-whole-tree-gate
    # unless the plan is clean-slate/breaking and code-bearing: compatibility ==
    # breaking AND change_type ∈ {tech_debt, feature, enhancement, bug_fix} AND
    # affected_files_count > 0. The whole-tree survivor sweep only makes sense on
    # a breaking plan — deprecation / smart_and_ask plans deliberately keep old
    # surfaces, so a surviving reference there is expected, not a defect.
    # compatibility is read from marshal.json (plan.phase-2-refine.compatibility,
    # default breaking). It runs after simplify_inactive and before
    # scope_gated_finalize per standards/decision-rules.md.
    compatibility = _read_compatibility()
    phase_6_candidates, whole_tree_gate_omitted = _apply_whole_tree_gate_inactive(
        phase_6_candidates, compatibility, args.change_type, affected_files_count
    )

    # Pre-filter 6 (scope_gated_finalize) drops heavyweight phase-6 review/audit
    # steps by scope: surgical drops the three non-guarded steps, single_module
    # drops only plan-retrospective, and the drop_review_on_scope_gate escape
    # hatch additionally drops automated-review. It runs after the other
    # pre-filters and before the seven-row matrix and the bot-enforcement guard,
    # so it only ever narrows the candidate list. automated-review is dropped
    # ONLY via the explicit override — never by the implicit scope gate — so the
    # bot-enforcement invariant stays intact by default. See
    # standards/decision-rules.md § Pre-Filter: scope_gated_finalize.
    drop_review_on_scope_gate = _read_drop_review_on_scope_gate()
    phase_6_candidates, scope_gated_dropped = _apply_scope_gated_finalize(
        phase_6_candidates, args.scope_estimate, drop_review_on_scope_gate
    )

    body, rule = _decide(
        change_type=args.change_type,
        track=args.track,
        scope_estimate=args.scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_candidates=phase_5_candidates,
        phase_6_candidates=phase_6_candidates,
        task_queue_active=task_queue_active,
    )

    # execution_tier routing runs AFTER the seven-row matrix and BEFORE
    # the bot-enforcement guard. It walks plan tasks, classifies each
    # ``verification.commands`` entry via ``architecture resolve``, and
    # branches on ``execution_tier``:
    #
    # * ``orchestrator`` → append the mapped phase-5 step ID to
    #   ``body['phase_5']['verification_steps']`` (de-duped) and drop the
    #   command from the task's verification list.
    # * ``per_task`` → write ``bash_timeout_seconds`` into the task's
    #   verification dict alongside ``commands``.
    #
    # Non-build / unresolvable commands pass through unchanged. The pass is
    # idempotent across re-composes — every call rewrites both the manifest
    # and the touched task files from the live ``architecture resolve``
    # output. The adaptive-timeout infrastructure design carries the
    # recurrence signature and orchestrator-tier rationale.
    mutated_tasks = _route_task_verification_commands(plan_id, body)
    _log_execution_tier_routing(plan_id, mutated_tasks, list(body['phase_5'].get('verification_steps', [])))

    # plan.phase-6-finalize run-at-all selection runs AFTER the seven-row
    # matrix (and execution_tier routing) and BEFORE the bot-enforcement guard.
    # It forces each of the four finalize gates' steps in (`always`) or out
    # (`never`) on the matrix-produced `phase_6.steps`, deferring to the existing
    # machinery on `auto` (the default). `always` is the only path that can
    # re-add a step the scope_gated_finalize pre-filter dropped — which is the
    # point: the operator-set `always` overrides the implicit scope gate. The
    # transform never touches `automated-review`, so running it before the
    # bot-enforcement guard leaves the bot-review invariant intact. The gate
    # values are flat phase-local knobs read directly from
    # `plan.phase-6-finalize.<gate>`. See
    # standards/decision-rules.md § plan.phase-6-finalize Selection.
    ceremony_finalize_gates = _read_finalize_gates()
    ceremony_forced_in, ceremony_forced_out = _apply_ceremony_finalize_selection(
        body['phase_6']['steps'], ceremony_finalize_gates
    )

    # Bot-enforcement guard runs AFTER the seven-row matrix and BEFORE manifest
    # persistence. On GitHub/GitLab plans where `automated-review` is missing
    # from `phase_6.steps`, the guard remediates in-place (appends the step and
    # emits a decision-log line) and returns None. The error branch below is
    # retained as a safety net for any future logic that detects a non-
    # remediable violation; in current code it is unreachable.
    final_phase_6_steps = body['phase_6']['steps']
    bot_guard_fired_provider = _apply_bot_enforcement_guard(final_phase_6_steps, plan_id)
    if bot_guard_fired_provider is not None:
        _log_bot_enforcement_guard_fired(plan_id, bot_guard_fired_provider)
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'bot_enforcement_violation',
            'message': (
                'automated-review must remain in the manifest for GitHub/GitLab plans — '
                'guard could not auto-remediate; investigate manifest composition'
            ),
            'ci_provider': bot_guard_fired_provider,
        }

    # Compose-time placement validator (defense-in-depth): even when
    # ``automated-review`` is present, reject the manifest if it sits at an
    # index later than any plan-mutating
    # step (``archive-plan``, ``record-metrics``, ``branch-cleanup``,
    # ``plan-marshall:plan-retrospective``). Such a layout would dispatch the
    # PR-review bot only after the plan directory has been moved or the
    # branch cleaned up, defeating the bot-enforcement guard's intent. The
    # check runs after the remediation guard so it sees the final ordering.
    placement_diagnostic = _validate_automated_review_placement(final_phase_6_steps)
    if placement_diagnostic is not None:
        _log_bot_enforcement_placement_violation(plan_id, placement_diagnostic)
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'bot_enforcement_violation',
            'message': placement_diagnostic,
        }

    manifest = {
        'manifest_version': MANIFEST_VERSION,
        'plan_id': plan_id,
        **body,
    }
    write_manifest(plan_id, manifest)
    _log_candidate_source(plan_id, 'phase-5-execute', phase_5_source)
    _log_candidate_source(plan_id, 'phase-6-finalize', phase_6_source)
    if commit_push_omitted:
        _log_commit_push_omitted(plan_id)
    if pre_push_quality_gate_omitted:
        _log_pre_push_quality_gate_omitted(plan_id)
    if pre_submission_self_review_omitted:
        _log_pre_submission_self_review_omitted(plan_id)
    if simplify_omitted:
        _log_simplify_omitted(plan_id, args.change_type, affected_files_count)
    if whole_tree_gate_omitted:
        _log_whole_tree_gate_omitted(plan_id, compatibility, args.change_type, affected_files_count)
    for dropped_step in scope_gated_dropped:
        _log_scope_gated_finalize_subtraction(plan_id, args.scope_estimate, dropped_step)
    for change in ceremony_forced_in:
        _log_ceremony_finalize_selection(plan_id, change['gate'], 'always', change['step'])
    for change in ceremony_forced_out:
        _log_ceremony_finalize_selection(plan_id, change['gate'], 'never', change['step'])
    _log_decision(plan_id, rule, body)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'created': True,
        'manifest_version': MANIFEST_VERSION,
        'phase_5': {
            'early_terminate': body['phase_5']['early_terminate'],
            'verification_steps_count': len(body['phase_5']['verification_steps']),
        },
        'phase_6': {
            'steps_count': len(body['phase_6']['steps']),
        },
        'rule_fired': rule,
        'commit_and_push': commit_and_push,
        'commit_push_omitted': commit_push_omitted,
        'pre_push_quality_gate_omitted': pre_push_quality_gate_omitted,
        'pre_submission_self_review_omitted': pre_submission_self_review_omitted,
        'simplify_omitted': simplify_omitted,
        'whole_tree_gate_omitted': whole_tree_gate_omitted,
        'compatibility': compatibility,
        'scope_gated_finalize_dropped': scope_gated_dropped,
        'drop_review_on_scope_gate': drop_review_on_scope_gate,
        'ceremony_finalize_gates': ceremony_finalize_gates,
        'ceremony_finalize_forced_in': [c['step'] for c in ceremony_forced_in],
        'ceremony_finalize_forced_out': [c['step'] for c in ceremony_forced_out],
    }


def cmd_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read and return the manifest as TOON-friendly dict."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    return {
        'status': 'success',
        'plan_id': plan_id,
        **manifest,
    }


def _log_record_step(plan_id: str, entry: dict[str, Any]) -> None:
    """Emit one decision-log line per recorded execution-log row.

    Written in-process via ``_emit_decision_log`` (the same helper the
    composer uses), so the line lands in the plan's own ``logs/decision.log``
    alongside ``execution.toon``. The line names the step, phase, outcome,
    and the token-attribution triple so a retrospective can correlate
    per-step execution metadata with the manifest without re-parsing the
    ``execution_log`` section.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:record-step) '
        f'Recorded {entry["step_id"]} phase={entry["phase"]} outcome={entry["outcome"]} — '
        f'total_tokens={entry["total_tokens"]}, tool_uses={entry["tool_uses"]}, '
        f'duration_ms={entry["duration_ms"]}'
    )
    _emit_decision_log(plan_id, message)


def cmd_record_step(args: argparse.Namespace) -> dict[str, Any] | None:
    """Append a per-step execution-log row to the manifest.

    Records per-step execution outcome plus token attribution into the
    manifest's ``execution_log[]`` section (created on first record). Each
    invocation appends exactly one row — re-invocation appends another row
    deterministically (the section is an ordered append log, not a keyed
    map), so repeated dispatch of the same step records every attempt. The
    manifest is written atomically and one decision-log line is emitted per
    record.

    Token-attribution fields (``total_tokens`` / ``tool_uses`` /
    ``duration_ms``) default to ``0`` when the caller omits them — a skipped
    step legitimately consumes no tokens, and a step dispatched without a
    ``<usage>`` tag reports zeros rather than a missing column.
    """
    plan_id = require_valid_plan_id(args)

    if args.phase not in VALID_RECORD_PHASES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase!r}. Must be one of {list(VALID_RECORD_PHASES)}',
        }
    if args.outcome not in VALID_RECORD_OUTCOMES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_outcome',
            'message': f'Invalid outcome: {args.outcome!r}. Must be one of {list(VALID_RECORD_OUTCOMES)}',
        }

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    entry = {
        'step_id': args.step_id,
        'phase': args.phase,
        'outcome': args.outcome,
        'total_tokens': max(0, int(args.total_tokens or 0)),
        'tool_uses': max(0, int(args.tool_uses or 0)),
        'duration_ms': max(0, int(args.duration_ms or 0)),
        'timestamp': datetime.now(UTC).isoformat(),
    }

    execution_log = manifest.get(EXECUTION_LOG_KEY)
    if not isinstance(execution_log, list):
        execution_log = []
    execution_log.append(entry)
    manifest[EXECUTION_LOG_KEY] = execution_log
    write_manifest(plan_id, manifest)

    _log_record_step(plan_id, entry)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'recorded': True,
        'step_id': entry['step_id'],
        'phase': entry['phase'],
        'outcome': entry['outcome'],
        'total_tokens': entry['total_tokens'],
        'tool_uses': entry['tool_uses'],
        'duration_ms': entry['duration_ms'],
        'timestamp': entry['timestamp'],
        'execution_log_count': len(execution_log),
    }


# =============================================================================
# Loadability Check (validate-loadable)
# =============================================================================

# Paths to the phase-6-finalize standards + workflow directories, resolved
# relative to this script's location in the marketplace source tree. Built-in
# step docs may live under either directory: orchestrator-style steps that the
# dispatcher reads inline live under ``standards/``; ext-point implementor
# workflows (LLM-judgement workflows dispatched as a unit via
# ``execution-context``) live under ``workflow/``. The loadability check
# searches both, ``workflow/`` first.
_PHASE_6_SKILL_DIR = resolve_skills_root(Path(__file__)) / 'phase-6-finalize'
_PHASE_6_WORKFLOW_DIR = _PHASE_6_SKILL_DIR / 'workflow'
_PHASE_6_STANDARDS_DIR = _PHASE_6_SKILL_DIR / 'standards'

# Repository-root anchor used to render the standards path as a project-relative
# string in the script output. ``resolve_bundles_root`` identity-walks to the
# ``marketplace/bundles`` root (no index arithmetic); its grandparent is the
# repo root, so rendered paths start with `marketplace/bundles/…` and match the
# documented contract.
_REPO_ROOT = resolve_bundles_root(Path(__file__)).parent.parent


def _is_external_step(step_id: str) -> bool:
    """Return True when ``step_id`` is a project/skill (external) step.

    External steps carry a colon (``project:foo`` or ``bundle:skill``).
    Bare names and ``default:``-prefixed names are built-in.
    """
    if step_id.startswith('default:'):
        return False
    return ':' in step_id


def _resolve_standards_path(step_id: str) -> Path:
    """Resolve the doc file path for a built-in ``step_id``.

    Strips the optional ``default:`` prefix. Searches ``workflow/`` first,
    then falls back to ``standards/``. Returns the first matching path; if
    neither exists, returns the ``workflow/`` path (so the caller's missing-
    file error message reports the preferred location).
    """
    bare = _strip_default_prefix(step_id)
    workflow_path = _PHASE_6_WORKFLOW_DIR / f'{bare}.md'
    if workflow_path.is_file():
        return workflow_path
    standards_path = _PHASE_6_STANDARDS_DIR / f'{bare}.md'
    if standards_path.is_file():
        return standards_path
    return workflow_path


def _render_standards_rel_path(absolute: Path) -> str:
    """Render ``absolute`` as a repo-root-relative POSIX string.

    Falls back to the absolute string when ``absolute`` is outside the repo.
    """
    try:
        return absolute.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(absolute)


def _read_frontmatter_order(path: Path) -> int | None:
    """Read the integer ``order:`` frontmatter key from a markdown file.

    Mirrors the minimal frontmatter parser used by ``_role_of`` — scans the
    first ``---``-fenced block for an ``order:`` key and returns its value
    coerced to ``int``. Returns ``None`` when the file is missing, has no
    frontmatter block, lacks an ``order:`` key, or the value is not an
    integer. PyYAML is intentionally avoided to keep the dependency surface
    narrow; the frontmatter shape is constrained by plugin-doctor and the
    test suite.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None
    if not text.startswith('---'):
        return None
    for line in text.splitlines()[1:]:
        if line.strip() == '---':
            break
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        if key.strip() != 'order':
            continue
        candidate = value.strip().strip('"').strip("'")
        try:
            return int(candidate)
        except ValueError:
            return None
    return None


def _resolve_step_order(step_id: str) -> int | None:
    """Resolve a step's frontmatter ``order`` integer from its source file.

    Resolution is broader than loadability: it covers ``project:`` steps too,
    because real ordering inversions can occur among project-local steps.

    - Built-in steps (bare or ``default:``-prefixed): resolve the standards /
      workflow doc via ``_resolve_standards_path`` and read its ``order:``
      frontmatter.
    - ``project:``-prefixed steps: resolve ``.claude/skills/{bare-name}/SKILL.md``
      relative to the repo root and read its ``order:`` frontmatter.
    - Other external steps (``bundle:skill``): no resolvable project-local
      source file — return ``None``.

    Returns ``None`` when no source file exists or no ``order:`` key is
    present. Steps that resolve to ``None`` are skipped by the ascending-order
    check (they neither break nor satisfy ascending order).
    """
    if step_id.startswith('project:'):
        bare = step_id[len('project:') :]
        skill_path = _REPO_ROOT / '.claude' / 'skills' / bare / 'SKILL.md'
        return _read_frontmatter_order(skill_path)
    if _is_external_step(step_id):
        # bundle:skill external steps have no project-local source file.
        return None
    return _read_frontmatter_order(_resolve_standards_path(step_id))


def _check_ascending_order(steps: list[Any]) -> str | None:
    """Assert ``steps`` resolve to non-decreasing frontmatter ``order`` values.

    Walks the step list in position order, resolving each step's ``order``
    via ``_resolve_step_order``. Steps whose ``order`` resolves to ``None``
    are skipped (they do not participate in the ascending assertion). An
    inversion is a step whose resolved ``order`` is strictly less than the
    maximum resolved ``order`` seen so far at an earlier list position.

    Returns an actionable diagnostic naming the inverted pair on the first
    inversion, or ``None`` when the resolvable subsequence is non-decreasing.
    The message phrasing matches the request: it names the later-positioned
    step (with the smaller order) and the earlier-positioned step (with the
    larger order) that it appears before.
    """
    max_order: int | None = None
    max_step: str | None = None
    for entry in steps:
        if not isinstance(entry, str):
            continue
        order = _resolve_step_order(entry)
        if order is None:
            continue
        if max_order is not None and order < max_order:
            return (
                f'step `{entry}` (order={order}) appears after '
                f'step `{max_step}` (order={max_order}) — phase_6.steps must be '
                f'in ascending frontmatter `order`'
            )
        if max_order is None or order > max_order:
            max_order = order
            max_step = entry
    return None


def _check_step_loadable(step_id: str) -> dict[str, Any]:
    """Single-step loadability check.

    Returns a dict with ``step_id``, ``standards_path``, ``loadable`` and an
    optional ``message`` (canonical actionable phrasing on failure).
    External steps are short-circuited to ``loadable: true`` with an empty
    standards_path because their loadability is owned by the host plugin
    cache, not the marketplace standards tree.
    """
    if _is_external_step(step_id):
        return {
            'step_id': step_id,
            'standards_path': '',
            'loadable': True,
        }
    bare = _strip_default_prefix(step_id)
    absolute_path = _resolve_standards_path(step_id)
    rel_path = _render_standards_rel_path(absolute_path)
    if absolute_path.is_file():
        return {
            'step_id': bare,
            'standards_path': rel_path,
            'loadable': True,
        }
    message = (
        f'step `{bare}` referenced by `marshal.json` is missing standards file '
        f'`{rel_path}` — the plan likely deleted the file without sweeping `marshal.json`'
    )
    return {
        'step_id': bare,
        'standards_path': rel_path,
        'loadable': False,
        'message': message,
    }


def cmd_validate_loadable(args: argparse.Namespace) -> dict[str, Any] | None:
    """Verify standards-file loadability for `phase_6.steps` entries.

    Three modes (mutually exclusive):

    - ``--step-id ID``: validate one step. Returns the per-step dict directly.
    - ``--all``: walk every entry in ``manifest.phase_6.steps`` and return a
      ``results[]`` table plus ``unloadable_count``.
    - ``--check-seed``: read ``plan.phase-6-finalize.steps`` directly from
      ``marshal.json`` (independent of the composed ``execution.toon``) and run
      the ascending-order guard against the seed. Catches a seed-order
      inversion before manifest composition.

    Built-in steps resolve to ``phase-6-finalize/standards/{name}.md`` in the
    marketplace source tree (the cache layout is a deployment concern;
    resolving against the source tree keeps tests and production on the same
    code path). External steps short-circuit to ``loadable: true``.
    """
    plan_id = require_valid_plan_id(args)

    step_id = getattr(args, 'step_id', None)
    use_all = bool(getattr(args, 'all', False))
    check_seed = bool(getattr(args, 'check_seed', False))

    selected = [bool(step_id is not None), use_all, check_seed]
    if sum(selected) != 1:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_arguments',
            'message': (
                'validate-loadable requires exactly one of '
                '--step-id, --all, or --check-seed'
            ),
        }

    if check_seed:
        seed_steps = _read_marshal_phase_steps('phase-6-finalize')
        if seed_steps is None:
            return {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'seed_unreadable',
                'message': (
                    'could not read plan.phase-6-finalize.steps from marshal.json '
                    f'({get_marshal_path()})'
                ),
            }
        order_message = _check_ascending_order(seed_steps)
        if order_message is not None:
            return {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'seed_order_inversion',
                'message': order_message,
                'step_count': len(seed_steps),
            }
        return {
            'status': 'success',
            'plan_id': plan_id,
            'step_count': len(seed_steps),
        }

    if step_id is not None:
        result = _check_step_loadable(step_id)
        return {
            'status': 'success',
            'plan_id': plan_id,
            **result,
        }

    # --all path: read manifest, walk phase_6.steps.
    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_6, dict):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': 'phase_6 section missing or not a mapping',
        }
    steps = phase_6.get('steps', [])
    if not isinstance(steps, list):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': 'phase_6.steps must be a list',
        }

    results: list[dict[str, Any]] = []
    for entry in steps:
        if isinstance(entry, str):
            results.append(_check_step_loadable(entry))
            continue
        # Non-string manifest entries are corruption — surface them as
        # unloadable so the caller sees them in `results[]` and the
        # `unloadable_count` totals the defect, instead of silently
        # dropping the entry from validation.
        offending_type = type(entry).__name__
        results.append({
            'step_id': str(entry),
            'standards_path': '',
            'loadable': False,
            'message': (
                f'manifest step entry has non-string type `{offending_type}` '
                f'(value: {entry!r}) — manifest is corrupt; only str step IDs are valid'
            ),
        })
    unloadable_count = sum(1 for r in results if not r['loadable'])

    # Ascending-order guard: assert phase_6.steps resolve to non-decreasing
    # frontmatter ``order`` values. The check is additive to (and independent
    # of) the loadability walk above — order resolution covers ``project:``
    # steps too, because the real inversions occur among project-local steps.
    # An out-of-order pair flips ``status`` to ``error`` while preserving the
    # existing ``unloadable_count`` / ``results[]`` payload, so loadability
    # failures and order failures are both surfaced.
    order_message = _check_ascending_order(steps)
    if order_message is not None:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'order_inversion',
            'message': order_message,
            'unloadable_count': unloadable_count,
            'results': results,
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'unloadable_count': unloadable_count,
        'results': results,
    }


def cmd_validate(args: argparse.Namespace) -> dict[str, Any] | None:
    """Validate manifest schema and (optionally) step IDs against candidate sets."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    errors: list[str] = []

    # Schema checks.
    if manifest.get('manifest_version') != MANIFEST_VERSION:
        errors.append(
            f'manifest_version mismatch: expected {MANIFEST_VERSION}, got {manifest.get("manifest_version")!r}'
        )
    if manifest.get('plan_id') != plan_id:
        errors.append(f'plan_id mismatch: expected {plan_id!r}, got {manifest.get("plan_id")!r}')

    phase_5 = manifest.get('phase_5')
    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_5, dict):
        errors.append('phase_5 section missing or not a mapping')
        phase_5 = {}
    if not isinstance(phase_6, dict):
        errors.append('phase_6 section missing or not a mapping')
        phase_6 = {}

    if 'early_terminate' not in phase_5 or not isinstance(phase_5.get('early_terminate'), bool):
        errors.append('phase_5.early_terminate missing or not a bool')
    p5_steps = phase_5.get('verification_steps', [])
    if not isinstance(p5_steps, list):
        errors.append('phase_5.verification_steps must be a list')
        p5_steps = []
    p6_steps = phase_6.get('steps', [])
    if not isinstance(p6_steps, list):
        errors.append('phase_6.steps must be a list')
        p6_steps = []

    # Step-ID checks (only when caller passes candidate sets).
    p5_unknown: list[str] = []
    p6_unknown: list[str] = []
    if args.phase_5_steps is not None:
        allowed_5 = set(_split_csv(args.phase_5_steps, ()))
        p5_unknown = [s for s in p5_steps if s not in allowed_5]
        if p5_unknown:
            errors.append(f'phase_5.verification_steps contains unknown IDs: {p5_unknown}')
    if args.phase_6_steps is not None:
        allowed_6 = set(_split_csv(args.phase_6_steps, ()))
        p6_unknown = [s for s in p6_steps if s not in allowed_6]
        if p6_unknown:
            errors.append(f'phase_6.steps contains unknown IDs: {p6_unknown}')

    if errors:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': '; '.join(errors),
            'phase_5_unknown_steps_count': len(p5_unknown),
            'phase_5_unknown_steps': p5_unknown,
            'phase_6_unknown_steps_count': len(p6_unknown),
            'phase_6_unknown_steps': p6_unknown,
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'valid': True,
        'phase_5_unknown_steps_count': 0,
        'phase_6_unknown_steps_count': 0,
    }


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Manage the per-plan execution manifest', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    compose_parser = subparsers.add_parser('compose', help='Compose and write execution.toon', allow_abbrev=False)
    add_plan_id_arg(compose_parser)
    compose_parser.add_argument('--change-type', required=True, help='Change type (one of VALID_CHANGE_TYPES)')
    compose_parser.add_argument('--track', required=True, help='Outline track: simple|complex')
    compose_parser.add_argument(
        '--scope-estimate', required=True, help='scope_estimate (none|surgical|single_module|multi_module|broad)'
    )
    compose_parser.add_argument('--recipe-key', default=None, help='Recipe key (e.g. lesson_cleanup) when applicable')
    compose_parser.add_argument(
        '--affected-files-count', type=int, default=0, help='Count of affected files from the outline'
    )
    compose_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated candidate Phase 5 step IDs')
    compose_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated candidate Phase 6 step IDs')
    compose_parser.add_argument(
        '--commit-and-push',
        default=None,
        help='Resolved commit_and_push from phase-5-execute config (true|false). '
        'When omitted defaults to true. When false, commit-push (and pre-push-quality-gate '
        'and pre-submission-self-review) is omitted from phase_6.steps.',
    )

    read_parser = subparsers.add_parser('read', help='Read execution.toon as TOON', allow_abbrev=False)
    add_plan_id_arg(read_parser)

    record_step_parser = subparsers.add_parser(
        'record-step',
        help='Append a per-step execution-log row (outcome + token attribution) to execution.toon',
        allow_abbrev=False,
    )
    add_plan_id_arg(record_step_parser)
    record_step_parser.add_argument('--step-id', required=True, help='Step identifier being recorded')
    record_step_parser.add_argument(
        '--phase', required=True, help='Phase the step ran in (one of VALID_RECORD_PHASES: 5-execute|6-finalize)'
    )
    record_step_parser.add_argument(
        '--outcome', required=True, help='Execution outcome (one of VALID_RECORD_OUTCOMES: executed|skipped|error)'
    )
    record_step_parser.add_argument('--total-tokens', type=int, default=0, help='Total tokens attributed to the step')
    record_step_parser.add_argument('--tool-uses', type=int, default=0, help='Tool-use count attributed to the step')
    record_step_parser.add_argument('--duration-ms', type=int, default=0, help='Wall-clock duration in milliseconds')

    validate_parser = subparsers.add_parser('validate', help='Validate execution.toon', allow_abbrev=False)
    add_plan_id_arg(validate_parser)
    validate_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated allowed Phase 5 step IDs')
    validate_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated allowed Phase 6 step IDs')

    validate_loadable_parser = subparsers.add_parser(
        'validate-loadable',
        help='Verify standards-file presence for phase_6.steps entries',
        allow_abbrev=False,
    )
    add_plan_id_arg(validate_loadable_parser)
    validate_loadable_group = validate_loadable_parser.add_mutually_exclusive_group(required=True)
    validate_loadable_group.add_argument(
        '--step-id',
        default=None,
        help='Validate a single step (bare name or default:-prefixed)',
    )
    validate_loadable_group.add_argument(
        '--all',
        action='store_true',
        help='Validate every entry in manifest.phase_6.steps',
    )
    validate_loadable_group.add_argument(
        '--check-seed',
        action='store_true',
        help=(
            'Read plan.phase-6-finalize.steps directly from marshal.json and '
            'assert ascending frontmatter order (detects seed-order inversion '
            'before manifest composition)'
        ),
    )

    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)

    handlers = {
        'compose': cmd_compose,
        'read': cmd_read,
        'record-step': cmd_record_step,
        'validate': cmd_validate,
        'validate-loadable': cmd_validate_loadable,
    }
    handler = handlers[args.command]
    result = handler(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
