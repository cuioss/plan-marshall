#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic core for the unified change-ledger primitive.

Notation: imported as a module (PYTHONPATH) — ``from _ledger_core import
append_entry, read_entries, build_record, change_record, resolve_ledger_path``.
NOT an executor entry point.

This module is the single read/write/construct surface for the one append-only
change-ledger (``.plan/work/change-ledger.jsonl``), and the rewrite-remap that
maps ``kind=change`` rows of rewritten commits onto their rewritten
counterparts. The ledger is the unified ``worktree_sha``-stamped record of
working-tree transitions; it subsumes the former "build-registry" idea entirely
(there is NO separate ``builds.jsonl``).
Both writers — the executor dispatch-boundary ``kind=build`` writer and the
phase-5 ``kind=change`` writer — and both readers — the ``query`` verb and the
``pre-commit-verify-freshness`` gate — go through this core so entries are
shaped identically and parsed identically. The rewrite-remap writes through the
same :func:`append_entry`, so it is a third writer, never a second write path.

**Tracked-config-dir resolution, NOT plan-scoped.** The ledger resolves via
:func:`file_ops.get_tracked_config_dir` (modeled on ``manage-locks``), so it
serves plan-less orchestrator builds just as well as plan-scoped task builds.
A plan-less build is recorded under the ``NO_PLAN`` sentinel, never as
``plan_id: null``: ``plan_id`` is a required ``str`` on both
:func:`build_record` and :func:`job_record`, so every row is attributable.

**Pure-append concurrency.** :func:`append_entry` writes exactly one
``json.dumps(record) + '\\n'`` line per call with a single ``open(..., 'a')``.
On the small per-record size this is atomic enough for a POSIX append, and
:func:`read_entries` tolerates (skips) malformed lines, so no lock is
introduced. The shape is deliberately pure-append — no read-modify-write, no
find-and-update — so no check-then-act window exists and the cooperative-lock
class does not apply. (See the TOCTOU / check-then-act mitigation menu in
``ref-code-quality/standards/code-organization.md`` — the pure-append
shape avoids the window entirely.)
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from file_ops import get_tracked_config_dir, now_utc_iso

KIND_BUILD = 'build'
KIND_CHANGE = 'change'
KIND_JOB = 'job'

# The statuses a build WRAPPER may claim for itself in its stdout TOON — the
# wrapper's own vocabulary (see script-shared/scripts/build/_build_shared.py).
# The executor dispatch boundary compares a payload's `status` against THIS set
# and no wider one, so a wrapper can never mint a derived-only verdict below.
#
# `killed` is claimable for the same reason `timeout` is: both are FIRST-HAND
# observations by the process that reaped the child. Excluding it forced every
# inner kill — a build child
# killed while the wrapper survived — to be emitted as `error`, i.e. as a red
# build, which is the collapse the truthful-signals work removes. Admitting it
# opens no fail-open hole: `killed` fails every gate `error` fails, so the change
# only ADDS information that consumers were previously denied.
WRAPPER_CLAIMABLE_BUILD_STATUSES = frozenset({'success', 'error', 'timeout', 'killed'})

# The status ONLY the executor dispatch boundary derives; a wrapper claiming it
# is not believed, because it records the ABSENCE of the very evidence a claim
# would be. `unknown` marks an exit-0 dispatch whose payload carried no claimable
# status — the outcome is undetermined, and deriving `success` there would be a
# confident green over a signal that was never read.
#
# `killed` is ALSO derived at the boundary (from a negative returncode of the
# dispatched script itself — the outer kill, where the wrapper did not survive to
# report anything), so it is produced on both sides. It is not listed here
# because this set means "not claimable by a wrapper", not "derivable".
DERIVED_ONLY_BUILD_STATUSES = frozenset({'unknown'})

# The full truthful build-outcome vocabulary carried by every kind=build entry's
# `status` field: the wrapper-claimable statuses plus the boundary-derived ones.
# The freshness gate requires status == 'success', so every other member —
# `unknown` included — fails it closed; exit_code is retained as orthogonal
# diagnostic detail.
BUILD_STATUSES = WRAPPER_CLAIMABLE_BUILD_STATUSES | DERIVED_ONLY_BUILD_STATUSES


def resolve_ledger_path() -> Path:
    """Resolve the single change-ledger path under the tracked-config dir.

    ``<tracked-config-dir>/work/change-ledger.jsonl``. NOT plan-scoped — one
    ledger per repository working tree, covering plan-less orchestrator builds.
    """
    return get_tracked_config_dir() / 'work' / 'change-ledger.jsonl'


def append_entry(record: dict[str, Any], path: Path | None = None) -> None:
    """Append exactly one JSONL line for ``record``. Pure-append.

    Creates the ``work/`` parent directory if absent, then writes one
    ``json.dumps(record) + '\\n'`` line with a single ``open(path, 'a')``. No
    read-modify-write, no in-place mutation.
    """
    ledger_path = path if path is not None else resolve_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + '\n'
    with open(ledger_path, 'a', encoding='utf-8') as handle:
        handle.write(line)


def read_entries(path: Path | None = None) -> list[dict[str, Any]]:
    """Read the change-ledger JSONL file, skipping malformed lines.

    Returns the parsed entries in file order, or ``[]`` when the ledger is
    absent. This is the library reader the gate imports directly rather than
    shelling out to the ``query`` verb.
    """
    ledger_path = path if path is not None else resolve_ledger_path()
    if not ledger_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with open(ledger_path, encoding='utf-8') as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    entries.append(parsed)
    except OSError:
        pass
    return entries


def build_record(
    *,
    notation: str,
    plan_id: str,
    args: str | None,
    exit_code: int,
    status: str,
    worktree_sha: str | None,
    log_file: str | None,
    command: str | None = None,
    duration_seconds: float | None = None,
    outcome: dict[str, Any] | None = None,
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct a ``kind=build`` ledger record.

    Written by the executor dispatch boundary after every build-class
    invocation. ``status`` is the outcome of record — one of
    :data:`BUILD_STATUSES` (``success`` / ``error`` / ``timeout`` /
    ``killed`` / ``unknown``), derived truthfully at the dispatch boundary (a
    timed-out build carries ``status: timeout`` despite its exit code 0, and an
    exit-0 dispatch whose payload carried no claimable status carries
    ``status: unknown`` rather than a green it cannot substantiate).
    ``unknown`` alone is :data:`DERIVED_ONLY_BUILD_STATUSES` — the boundary
    produces it, a wrapper never claims it. ``killed`` arrives by either route
    and is first-hand on both: derived from a negative returncode when the
    dispatched script itself was signalled, claimed by the wrapper when it
    reaped a signalled build child and survived. ``exit_code``
    is retained as orthogonal diagnostic detail. Both are stamped against the
    working-tree ``worktree_sha`` at capture time. A build is NOT a commit, so
    this record does NOT carry ``commit_sha`` or ``changed_paths``.

    ``plan_id`` is a required ``str`` — every build is attributable. A build
    invoked outside any plan is recorded under the ``NO_PLAN`` sentinel; the
    caller resolves it before constructing the record, so no row can carry
    ``plan_id: null``.

    **``args`` and ``command`` are two distinct layers — neither substitutes
    for the other.** ``args`` is the EXECUTOR argv: the arguments the caller
    handed to ``.plan/execute-script.py`` (e.g.
    ``run --command-args "verify plan-marshall"``). ``command`` is what the
    build WRAPPER resolved that argv into and actually ran (e.g.
    ``./pw verify plan-marshall``). The mapping between them is the wrapper's
    own resolution — a build-tool switch or a routing decision changes
    ``command`` while ``args`` stays byte-identical — so a reader that needs
    "what did the operator ask for" reads ``args`` and one that needs "what
    actually ran" reads ``command``.

    ``command``, ``duration_seconds`` and ``outcome`` are all sourced from the
    wrapper's stdout TOON and are therefore OPTIONAL: they default to ``None``
    and stay ``None`` when the payload is absent or unparseable (a killed or
    crashed build), and for a hand-appended row that legitimately has no
    resolved command, no measured duration and no wrapper payload. ``outcome``
    is the wrapper's whole stdout TOON as a dict, retained verbatim so a
    reader gets the wrapper's own report (log file path, per-error rows)
    without re-reading the build log.

    **Secrets discipline — a DELIBERATE divergence from the build-server audit
    log, not an oversight.** ``build_server._audit_log`` refuses to record the
    resolved ``command``, ``exec_path``, ``project_path`` or any spec field on
    the ground that they may carry secrets; this record deliberately keeps
    ``command`` and the verbatim ``outcome``, both of which can. A resolved
    build command line can carry a registry credential or a ``-D`` token, and
    ``outcome``'s ``errors[]`` rows are lifted from the build log, which can
    echo anything the build printed. Three properties make that acceptable HERE
    and not there: the ledger is written to ``.plan/work/`` — inside the
    blanket ``.plan/*`` gitignore, so no row can reach a commit or a PR; the
    audit log's own consumers are cross-session and operator-facing whereas the
    ledger's are the freshness gate and local inspection; and the identical text
    is ALREADY co-resident in plaintext in the ``log_file`` this row points at,
    so the row discloses nothing to a reader who cannot already read that log.
    The one asymmetry a future change must respect: the build log ages out under
    the ``build_results_days`` retention target, while the ledger is append-only
    with no cleanup target, so the excerpt outlives the log it came from. Do NOT
    widen this record with a field sourced from anywhere other than the wrapper
    payload, and do NOT copy this exemption into a store that leaves the
    machine.
    """
    return {
        'kind': KIND_BUILD,
        'notation': notation,
        'plan_id': plan_id,
        'args': args,
        'command': command,
        'duration_seconds': duration_seconds,
        'outcome': outcome,
        'exit_code': exit_code,
        'status': status,
        'worktree_sha': worktree_sha,
        'log_file': log_file,
        'timestamp_iso': timestamp_iso if timestamp_iso is not None else now_utc_iso(),
    }


def change_record(
    *,
    deliverable_id: str,
    worktree_sha: str | None,
    commit_sha: str,
    changed_paths: list[str],
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct a ``kind=change`` ledger record.

    Written by the phase-5 execute loop after each deliverable completes and
    commits. ``commit_sha`` and ``changed_paths`` are git-sourced by the caller
    (from ``git diff-tree`` against the just-produced commit) — this constructor
    stores the caller-supplied list VERBATIM; it does NOT compute or re-derive
    changed paths. Self-computed / ``affected_files``-snapshotted paths are
    PROHIBITED at the call site.
    """
    return {
        'kind': KIND_CHANGE,
        'deliverable_id': deliverable_id,
        'commit_sha': commit_sha,
        'changed_paths': list(changed_paths),
        'worktree_sha': worktree_sha,
        'timestamp_iso': timestamp_iso if timestamp_iso is not None else now_utc_iso(),
    }


def job_record(
    *,
    job_id: str,
    plan_id: str,
    fingerprint: str,
    notation: str,
    worktree_sha: str | None,
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct a ``kind=job`` ledger record.

    Written by the ``build-server-client`` skill's ``submit`` verb at submit
    time, this record persists the daemon-assigned ``job_id`` into the plan's
    durable artifacts so a rebuilt or harness-reaped session can RE-ATTACH to an
    in-flight build from plan state alone — it re-issues ``wait`` against the
    recorded ``job_id`` rather than losing the running build. The ``fingerprint``
    is the idempotent-submit digest (plan + command + tree) the daemon's
    scheduler keys on, so a consumer can correlate a ledger row to a specific
    submission; ``notation`` is the executor notation that was dispatched.

    Unlike ``kind=build`` (a completed build outcome) this is a SUBMISSION
    record — the job may still be running — so it carries no ``exit_code`` or
    ``status``. The freshness gate ignores ``kind=job`` entirely (it consumes
    only ``kind=build``); ``kind=job`` rows exist for re-attach and audit.

    ``plan_id`` is a required ``str``, on the same never-null contract as
    :func:`build_record`: a plan-less submission is recorded under the
    ``NO_PLAN`` sentinel. The re-attach lookup matches on that same value, so
    a plan-less submit stays recoverable.
    """
    return {
        'kind': KIND_JOB,
        'job_id': job_id,
        'plan_id': plan_id,
        'fingerprint': fingerprint,
        'notation': notation,
        'worktree_sha': worktree_sha,
        'timestamp_iso': timestamp_iso if timestamp_iso is not None else now_utc_iso(),
    }


# ---------------------------------------------------------------------------
# Rewrite mapping — map the rows of rewritten commits onto their counterparts
# ---------------------------------------------------------------------------
#
# A history rewrite (rebase, amend, cherry-pick) gives every replayed commit a
# new SHA. The ledger is keyed by ``commit_sha`` and is pure-append, so a rewrite
# leaves every earlier ``kind=change`` row pointing at a commit that is no longer
# part of HEAD's history and the 5-execute end-marker guard reports the whole
# branch unrecorded. Remapping APPENDS one row per rewritten row that points at
# the rewritten SHA, preserving the original rows: append-only holds, and the
# history of the ledger stays a record of what happened rather than a rewritten
# copy of it.
#
# The mapping has two sources, both legitimate:
#
# * the rewrite knows what it did — a rebase reports its ``pre_sha`` / ``post_sha``
#   and a rewriting step can emit an explicit old-to-new map, which ``--map-file``
#   consumes; and
# * a rewrite performed OUTSIDE this tool (a manual amend, a cherry-pick) has no
#   emitted map, so the mapping is derived from the recorded rows themselves by
#   ``git patch-id``. Patch-id hashes the COMMIT'S PATCH, not its message, so a
#   rebased commit and a message-only amend both match their original. A patch
#   that changed during conflict resolution has no counterpart — it is reported
#   as ``unmapped`` and needs the explicit append path rather than a guessed
#   mapping.

#: The patch-id ``git patch-id`` reports for a commit with an empty diff. It is
#: shared by every empty commit, so it never identifies one, and matching on it
#: would pair unrelated empty commits.
EMPTY_PATCH_ID = '0000000000000000000000000000000000000000'


def _run_git(worktree_root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one ``git -C worktree_root`` command without raising on failure."""
    return subprocess.run(
        ['git', '-C', str(worktree_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_commit(worktree_root: str | Path, sha: str) -> str | None:
    """Resolve ``sha`` (full or abbreviated) to a full commit SHA, or ``None``.

    ``None`` means the object is not in this repository: a row written by a
    different worktree, a sha whose objects were garbage-collected. That is not a
    rewrite match, so callers must not treat it as one.
    """
    proc = _run_git(worktree_root, 'rev-parse', '--verify', '--quiet', f'{sha}^{{commit}}')
    if proc.returncode != 0:
        return None
    resolved = proc.stdout.strip()
    return resolved or None


def commit_is_ancestor(worktree_root: str | Path, sha: str) -> bool:
    """Return True when ``sha`` is reachable from HEAD."""
    return _run_git(worktree_root, 'merge-base', '--is-ancestor', sha, 'HEAD').returncode == 0


def _commit_patch_id(worktree_root: str | Path, sha: str) -> str | None:
    """Return the stable patch-id of one commit, or ``None`` when it has none.

    A commit with an empty diff (or an unreadable one) yields ``None`` rather
    than :data:`EMPTY_PATCH_ID`, because that value is shared by every empty
    commit and cannot identify one.
    """
    show = _run_git(worktree_root, 'show', '--pretty=format:', '--no-ext-diff', '-p', sha)
    if show.returncode != 0:
        return None
    patch = subprocess.run(
        ['git', 'patch-id', '--stable'],
        input=show.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    if patch.returncode != 0 or not patch.stdout.strip():
        return None
    patch_id = patch.stdout.split()[0]
    return None if patch_id == EMPTY_PATCH_ID else patch_id


def _rev_list(worktree_root: str | Path, rev_range: str) -> list[str]:
    """Return the commit SHAs in ``rev_range``, or ``[]`` when it cannot be read."""
    proc = _run_git(worktree_root, 'rev-list', rev_range)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _split_sha_pair(line: str) -> tuple[str, str] | None:
    """Split one ``old new`` / ``old:new`` / ``old=new`` map line."""
    for separator in (':', '='):
        if separator in line:
            old, _, new = line.partition(separator)
            if old.strip() and new.strip():
                return old.strip(), new.strip()
            return None
    parts = line.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    return None


def parse_sha_map_text(text: str) -> dict[str, str]:
    """Parse an old-to-new SHA map from JSON or line-oriented text.

    Accepts the JSON object ``--emit-map`` writes (``{"old": "new", ...}``), and
    the human form the rewriting step may hand-write: one pair per line, as
    ``old new``, ``old:new`` or ``old=new``. Blank lines and ``#`` comments are
    ignored. An unparseable line is skipped rather than guessed at — the map is
    an explicit assertion, so a line that does not name two SHAs cannot be
    honoured as one.
    """
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith('{'):
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError('a SHA map JSON document must be an object of old-to-new pairs')
        return {
            str(old).strip(): str(new).strip() for old, new in parsed.items() if str(old).strip() and str(new).strip()
        }
    mapping: dict[str, str] = {}
    for line in stripped.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith('#'):
            continue
        pair = _split_sha_pair(candidate)
        if pair is not None:
            mapping[pair[0]] = pair[1]
    return mapping


def remap_record(
    *,
    source: dict[str, Any],
    new_commit_sha: str,
    worktree_sha: str | None,
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct the mapped ``kind=change`` row for one rewritten commit.

    The source row is preserved field-for-field (``deliverable_id``,
    ``changed_paths`` and any other recorded fact), except for the identity and
    currency fields the remap replaces. ``remapped_from`` is the rewritten row's
    original ``commit_sha``, so the pair is recoverable from the appended row
    alone — a reader never has to diff two rows to learn what was rewritten.
    """
    record = {
        key: value
        for key, value in source.items()
        if key not in ('commit_sha', 'worktree_sha', 'timestamp_iso', 'remapped_from')
    }
    record['commit_sha'] = new_commit_sha
    record['worktree_sha'] = worktree_sha
    record['timestamp_iso'] = timestamp_iso if timestamp_iso is not None else now_utc_iso()
    record['remapped_from'] = str(source.get('commit_sha', '')).strip()
    return record


def _change_rows(path: Path | None) -> list[dict[str, Any]]:
    """Return the ``kind=change`` rows that carry a non-empty ``commit_sha``."""
    return [
        entry
        for entry in read_entries(path)
        if entry.get('kind') == KIND_CHANGE and isinstance(entry.get('commit_sha'), str) and entry['commit_sha'].strip()
    ]


def _derive_patch_id_map(
    worktree_root: str,
    resolved_rows: list[tuple[dict[str, Any], str]],
    old_head: str | None,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Derive ``(old_raw, old_full, new_full)`` pairs by stable patch-id.

    Returns the pairs plus the recorded SHAs left unmapped. An unmapped rewrite
    is a real outcome that needs the explicit append path, not a silent omission:
    a patch that changed during conflict resolution has no counterpart.
    """
    rewritten = [(row, full) for row, full in resolved_rows if not commit_is_ancestor(worktree_root, full)]

    candidate_shas: set[str] = set()
    if old_head is not None:
        old_head_full = resolve_commit(worktree_root, old_head)
        if old_head_full is not None:
            candidate_shas.update(_rev_list(worktree_root, f'{old_head_full}..HEAD'))
    else:
        for _row, full in rewritten:
            candidate_shas.update(_rev_list(worktree_root, f'{full}..HEAD'))

    new_by_patch: dict[str, str] = {}
    for candidate in sorted(candidate_shas):
        patch_id = _commit_patch_id(worktree_root, candidate)
        # A patch-id seen twice among the candidates is ambiguous: two commits can
        # carry the same patch (a cherry-pick replayed twice), and picking one
        # would guess. Such a commit is never recorded as a target.
        if patch_id is None:
            continue
        if patch_id in new_by_patch:
            new_by_patch[patch_id] = ''
        else:
            new_by_patch[patch_id] = candidate

    pairs: list[tuple[str, str, str]] = []
    unmapped: list[str] = []
    for row, full in rewritten:
        raw = str(row.get('commit_sha', '')).strip()
        patch_id = _commit_patch_id(worktree_root, full)
        new_full = new_by_patch.get(patch_id, '') if patch_id is not None else ''
        if new_full and new_full != full:
            pairs.append((raw, full, new_full))
        else:
            unmapped.append(raw)
    return pairs, unmapped


def remap_change_rows(
    *,
    worktree_root: str,
    worktree_sha: str | None,
    explicit_map: dict[str, str] | None = None,
    old_head: str | None = None,
    ledger_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Append mapped ``kind=change`` rows for rewritten commits.

    ``explicit_map`` (an old-to-new map the rewriting step emitted) is consumed
    verbatim; without it, the map is derived by stable patch-id from the rows
    whose recorded commit is no longer an ancestor of HEAD. ``old_head`` scopes
    the derivation to the commits a known rewrite replayed.

    A pair that is already recorded — a row whose ``remapped_from`` and
    ``commit_sha`` are exactly this pair — is skipped, so re-running the verb
    after an interrupted run appends nothing twice. Appending is therefore
    idempotent at the pair level even though the ledger itself stays pure-append.

    Returns ``remap_count`` (rows appended), ``mappings`` (the pairs applied, as
    ``old_commit_sha`` / ``new_commit_sha``), ``unmapped`` (recorded SHAs with no
    counterpart) and ``ledger_path``.
    """
    rows = _change_rows(ledger_path)
    resolved_rows: list[tuple[dict[str, Any], str]] = []
    unresolved: list[str] = []
    for row in rows:
        raw_sha = str(row.get('commit_sha', '')).strip()
        full = resolve_commit(worktree_root, raw_sha)
        if full is None:
            unresolved.append(raw_sha)
        else:
            resolved_rows.append((row, full))
    existing_pairs = {
        (str(row.get('remapped_from', '')).strip(), str(row.get('commit_sha', '')).strip())
        for row in rows
        if row.get('remapped_from')
    }
    by_full: dict[str, list[dict[str, Any]]] = {}
    for row, full in resolved_rows:
        by_full.setdefault(full, []).append(row)

    if explicit_map is not None:
        pairs: list[tuple[str, str, str]] = []
        unmapped: list[str] = []
        for old_raw, new_raw in explicit_map.items():
            old_full = resolve_commit(worktree_root, old_raw)
            new_full = resolve_commit(worktree_root, new_raw)
            if old_full is None:
                unresolved.append(old_raw.strip())
            elif new_full is None:
                unmapped.append(old_raw.strip())
            elif old_full != new_full:
                pairs.append((old_raw.strip(), old_full, new_full))
    else:
        pairs, unmapped = _derive_patch_id_map(worktree_root, resolved_rows, old_head)

    mappings: list[dict[str, str]] = []
    appended = 0
    for old_raw, old_full, new_full in pairs:
        if (old_raw, new_full) in existing_pairs:
            continue
        for source in by_full.get(old_full, []):
            record = remap_record(
                source=source,
                new_commit_sha=new_full,
                worktree_sha=worktree_sha,
            )
            if not dry_run:
                append_entry(record, ledger_path)
            appended += 1
            mappings.append({'old_commit_sha': old_raw, 'new_commit_sha': new_full})

    return {
        'status': 'success',
        'remap_count': appended,
        'mappings': mappings,
        'unmapped': unmapped,
        'unresolved': unresolved,
        'dry_run': dry_run,
        'ledger_path': str(ledger_path if ledger_path is not None else resolve_ledger_path()),
    }
