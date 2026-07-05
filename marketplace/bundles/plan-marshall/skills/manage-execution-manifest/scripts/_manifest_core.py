#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Constants and file-operation helpers for the execution manifest.

Extracted verbatim from ``manage-execution-manifest.py``: the manifest
constants (change-type / scope / track / record vocabularies, default candidate
step sets, canonical-verify role table) and the TOON read/write boundary
(:func:`read_manifest` / :func:`write_manifest` plus their step-params
normalization). Pure, log-free, and patched by no test; the hyphenated entry
re-exports every name it and the test suite reference.
"""

from pathlib import Path
from typing import Any

from file_ops import atomic_write_file, get_plan_dir
from toon_parser import parse_toon, serialize_toon

# =============================================================================
# Constants
# =============================================================================

MANIFEST_FILENAME = 'execution.toon'
MANIFEST_VERSION = 1

# Default number of phase-5 execution envelopes the orchestrator dispatches when
# the composer is not given an explicit ``--envelope-count``. ``1`` reproduces
# the pre-existing single-envelope behaviour: one budget-bounded
# ``execution-context`` envelope greedily drives the task loop until the queue
# is empty or a TASK-boundary re-dispatch point fires (token-budget sentinel,
# ``triage_required``, or ``baseline_drift``). The field is the orchestrator's
# read-side signal for how many envelopes to plan for; a manifest composed
# before this field existed simply has no ``phase_5.envelope_count`` key, and
# every reader treats an absent value as this same default.
DEFAULT_ENVELOPE_COUNT = 1

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
# These are bare step IDs (post boundary-normalization shape). The phase-5
# defaults are parameterized canonical-verify IDs in their bare
# ``verify:{canonical}`` form (the ``default:`` prefix is stripped at the compose
# boundary); their matrix ``role:`` is resolved purely in-code by ``_role_of``
# below (via the ``_CANONICAL_TO_ROLE`` table, keyed on the trailing canonical
# segment) for structural role-based intersection in the 7-row decision matrix.
# There are no longer any legacy fixed-name IDs and no per-step
# ``standards/{name}.md`` role-files to read.
DEFAULT_PHASE_5_STEPS = ('verify:quality-gate', 'verify:module-tests')
DEFAULT_PHASE_6_STEPS = (
    'finalize-step-simplify',
    'finalize-step-security-audit',
    'push',
    'create-pr',
    'ci-verify',
    'automated-review',
    'sonar-roundtrip',
    'lessons-capture',
    'adr-propose',
    'branch-cleanup',
    'record-metrics',
    'archive-plan',
)


def _strip_default_prefix(step: str) -> str:
    """Return the bare step name regardless of the optional ``default:`` prefix."""
    return step[len('default:') :] if step.startswith('default:') else step


# Canonical-verify step prefix. A step ID of the shape
# ``default:verify:{canonical}`` (or its bare ``verify:{canonical}`` form) is
# the single parameterized canonical-verify step — the matrix role is derived
# from the trailing ``{canonical}`` segment rather than from a per-canonical
# role-file. See ``phase-5-execute/standards/canonical_verify.md``.
_CANONICAL_VERIFY_PREFIX = 'verify:'

# Canonical command segment → matrix ``role:`` value. This is the composer's
# copy of the canonical→role table documented in
# ``phase-5-execute/standards/canonical_verify.md`` § "derived role". Both
# ``verify`` and ``module-tests`` map to the ``module-tests`` role (running the
# full module-test suite); ``quality-gate`` maps to ``quality-gate``;
# ``coverage`` maps to ``coverage``; whole-tree gates map to their own roles.
_CANONICAL_TO_ROLE: dict[str, str] = {
    'quality-gate': 'quality-gate',
    'verify': 'module-tests',
    'module-tests': 'module-tests',
    'coverage': 'coverage',
    'integration-tests': 'integration',
    'e2e': 'e2e',
}


def _role_of(step_id: str, cache: dict[str, str | None]) -> str | None:
    """Resolve a phase-5 candidate step ID to its matrix ``role:`` value.

    The composer intersects phase-5 candidates by role rather than by literal
    step ID. Resolution is purely in-code via the ``_CANONICAL_TO_ROLE`` table —
    no role-file is ever read (the ``phase-5-execute/standards/{name}.md``
    role-files were deleted). Every built-in verify step is a parameterized
    canonical-verify step (``default:verify:{canonical}`` or the bare
    ``verify:{canonical}`` form); the role is derived from the trailing
    ``{canonical}`` segment via the ``_CANONICAL_TO_ROLE`` table. A single
    parameterized step backs every canonical, and the canonical is the parameter
    that selects the role.

    Returns ``None`` for:

    - External steps (``project:`` or ``bundle:skill``) — no role concept.
    - Canonical-verify steps whose ``{canonical}`` segment is unrecognized.
    - Any other bare name that is not a ``verify:{canonical}`` form (preserving
      the "missing data → step is never role-selected" convention).

    Results are cached per compose call to avoid re-resolving the same step
    when a candidate appears in multiple intersection sites.
    """
    if step_id in cache:
        return cache[step_id]

    bare = _strip_default_prefix(step_id)

    # Canonical-verify steps: ``default:verify:{canonical}`` (bare:
    # ``verify:{canonical}``). The role is derived from the trailing canonical
    # segment by table lookup.
    if bare.startswith(_CANONICAL_VERIFY_PREFIX):
        canonical = bare[len(_CANONICAL_VERIFY_PREFIX) :]
        derived_role = _CANONICAL_TO_ROLE.get(canonical)
        cache[step_id] = derived_role
        return derived_role

    # External steps (project:foo or bundle:skill) have no role — they are
    # dispatched as PROJECT/SKILL steps, not built-in default steps. Any other
    # bare name (no longer any legacy fixed-name ID) is never role-selected.
    cache[step_id] = None
    return None


# =============================================================================
# File Operations
# =============================================================================


def get_manifest_path(plan_id: str) -> Path:
    """Return the absolute path to the execution manifest for ``plan_id``."""
    return get_plan_dir(plan_id) / MANIFEST_FILENAME


def _denormalize_step_params_for_write(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``manifest`` with ownerless ``step_params`` collapsed to ``null``.

    The write-side mirror of :func:`_normalize_step_params_block`: an ownerless
    step (its param value is an empty dict ``{}`` or ``None``) is written as
    ``None`` (serialized as ``null``) so the manifest TOON never carries a noisy
    empty ``{}`` block — regardless of which write path produced the in-memory
    manifest (compose snapshot, or a ``step-params set`` round-trip that read the
    normalized ``{}`` back). A param-owning step keeps its nested object. The
    input ``manifest`` is never mutated; only the ``phase_5`` / ``phase_6``
    sections that actually carry a ``step_params`` block are shallow-copied.
    """
    out = dict(manifest)
    for section_key in ('phase_5', 'phase_6'):
        section = out.get(section_key)
        if not isinstance(section, dict):
            continue
        step_params = section.get('step_params')
        if not isinstance(step_params, dict):
            continue
        collapsed = {
            step_id: (params if isinstance(params, dict) and params else None)
            for step_id, params in step_params.items()
        }
        section_copy = dict(section)
        section_copy['step_params'] = collapsed
        out[section_key] = section_copy
    return out


def write_manifest(plan_id: str, manifest: dict[str, Any]) -> None:
    """Atomically write the manifest as TOON to its plan path.

    Ownerless ``step_params`` entries are collapsed to ``null`` at the write
    boundary (:func:`_denormalize_step_params_for_write`) so no empty ``{}``
    block is ever serialized, keeping every manifest-write path (compose +
    ``step-params set``) consistent with the no-empty-``{}`` contract.
    """
    path = get_manifest_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, serialize_toon(_denormalize_step_params_for_write(manifest)))


def _normalize_step_params_block(manifest: dict[str, Any]) -> None:
    """Coerce each ``step_params`` per-step value to ``{}`` when not a non-empty dict.

    The manifest persists as TOON, and an empty param object (``{}``) round-trips
    back from TOON as the empty string ``''`` on read. The step-params contract
    requires an ownerless step to read back as ``{}`` (an empty param object), not
    ``''``. This normalizes the read-side exposure for both phase sections in
    place: any per-step value that is not a dict (notably the ``''`` produced by
    the empty-dict TOON round-trip) becomes ``{}``. A step id MISSING from the
    snapshot is left absent — only present-but-empty values normalize.
    """
    for section_key in ('phase_5', 'phase_6'):
        section = manifest.get(section_key)
        if not isinstance(section, dict):
            continue
        step_params = section.get('step_params')
        if not isinstance(step_params, dict):
            section['step_params'] = {}
            continue
        section['step_params'] = {
            step_id: (params if isinstance(params, dict) else {})
            for step_id, params in step_params.items()
        }


def read_manifest(plan_id: str) -> dict[str, Any] | None:
    """Read and parse the manifest, returning ``None`` if missing.

    The parsed manifest is normalized at this read boundary so each
    ``step_params`` per-step value is a dict (``{}`` for ownerless steps),
    repairing the empty-dict→``''`` TOON round-trip. See
    :func:`_normalize_step_params_block`.
    """
    path = get_manifest_path(plan_id)
    if not path.exists():
        return None
    manifest = parse_toon(path.read_text(encoding='utf-8'))
    if isinstance(manifest, dict):
        _normalize_step_params_block(manifest)
    return manifest
