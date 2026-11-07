#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The task-start baseline and the script-emitted ``[ARTIFACT]`` channel.

``[OUTCOME]`` was moved into ``manage-tasks finalize-step`` because a
caller-side emission is LOST whenever an execution-context is re-dispatched and
the original agent's working context is discarded before it fires. The
``[ARTIFACT]`` channel sat one paragraph below it in the same standard and was
still PROSE-INSTRUCTED, so it inherited exactly the loss the move was made to
stop. This module is that channel's script-owned half.

⛔ **The diff base had no writer.** A content sweep for ``task_start_sha`` at the
time of this change returned 6 hits over 3 files, ALL of them documentation — no
script read or wrote it, so the standard's "record the SHA at the task's
``in_progress`` transition" instruction named a field nothing produced. Adding a
script-emitted line on top of an absent base would have shipped an inert channel:
script-owned, and still never firing. The writer therefore lands here, in the
same change as the emission, and :func:`capture_task_start_sha` is what makes the
emission reachable at all.

**What the base is, and what it therefore bounds.** The base is the worktree HEAD
observed the first time ``manage-tasks`` sees a task move to ``in_progress``.
Commits fire at the per-deliverable chain tail, so HEAD does not move while a
deliverable's tasks run: the SHA is stable and correct as a starting point. The
consequence a reader must know is that two tasks of the SAME deliverable share
one base, so the later task's artifact list is a SUPERSET — it re-reports the
earlier task's files. That is a property of a SHA base under per-deliverable
commits, not a defect in the diff, and it is stated rather than hidden.

**The baseline is a validated object id at both ends.** It is persisted only
when it is well-formed and refused when it is not (:func:`is_object_id`), because
the read side passes it to ``git diff`` as an unseparated argument — a persisted
``--output=/path`` was consumed by git as an OPTION and redirected the diff
(CWE-88). The refusal is REPORTED rather than silently skipped, so a corrupted
record does not present as a task that changed nothing.

**Why the diff is against the WORKING TREE, not ``HEAD``.** The standard's
``git diff {base} HEAD`` form is empty for the whole window this channel covers:
a task's edits are uncommitted until the chain-tail commit, so a base..HEAD
comparison at task close sees nothing. The diff here is ``git diff {base}`` —
base commit against the working tree — plus the untracked-file walk, because a
newly created file is untracked and appears in NEITHER form until it is staged.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from file_ops import cwd_checkout_root
from plan_logging import log_entry

#: The task-record field holding the baseline SHA. Written by
#: :func:`capture_task_start_sha`, read by :func:`emit_artifact_lines`.
TASK_START_SHA_FIELD = 'task_start_sha'

#: A well-formed git object id: hex only, between git's abbreviation floor (7)
#: and a full SHA-256 (64). The bound is a strict ALLOWLIST, and that is what
#: closes the argument-injection sink (CWE-88): the persisted baseline flows into
#: ``git diff --name-status -M {base_sha}`` as an unseparated argument, so a
#: recorded value such as ``--output=/path`` was consumed by git as an OPTION and
#: redirected the diff. The value is plan-local state rather than remote input,
#: but it is an unvalidated value reaching a subprocess argument sink and the
#: guard is cheap.
#:
#: An end-of-options delimiter is deliberately NOT layered on top. A string this
#: pattern admits cannot begin with ``-`` — the sink is already closed — and
#: ``--end-of-options`` predates neither every git this project may run on nor a
#: silent ``None`` return from :func:`_git` if it is rejected, which would turn a
#: hardening measure into a silently empty artifact list.
_OBJECT_ID_RE = re.compile(r'\A[0-9a-fA-F]{7,64}\Z')

#: The caller prefix's first two segments. The third is the numeric task id — a
#: documented exception to the two-segment ``(bundle:skill)`` convention, so a
#: log reader can attribute each file change to the task that produced it
#: without cross-referencing timestamps. See
#: ``phase-5-execute/standards/workflow.md`` § "Task Completion Emission".
ARTIFACT_CALLER_SKILL = 'plan-marshall:phase-5-execute'


def _git(root: Path, *argv: str) -> str | None:
    """Run one git command under ``root`` and return stdout, or ``None``.

    Every failure mode — git absent, not a repository, an unknown base SHA — is
    a ``None``. The artifact channel is an AUDIT trail: it must never take the
    task-closing call down, and it must never emit a line it could not derive.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', str(root), *argv],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _checkout_root() -> Path:
    """The tree the diff runs against — the pinned worktree during phase-5+."""
    return Path(cwd_checkout_root())


def is_object_id(value: object) -> bool:
    """Return True when ``value`` is a well-formed git object id.

    The one predicate both ends of the baseline field are held to: nothing that
    fails it is persisted by :func:`capture_task_start_sha`, and nothing that
    fails it reaches a git argument in :func:`artifact_messages`. Validating on
    BOTH sides is deliberate — a record can be hand-edited, or written by a
    version predating the write-side guard, so the read side cannot assume the
    write side ran.
    """
    return isinstance(value, str) and bool(_OBJECT_ID_RE.match(value.strip()))


def capture_task_start_sha(task: dict) -> str | None:
    """Record the worktree HEAD on ``task`` as the task's baseline, once.

    Idempotent by construction: a task that already carries a baseline keeps it,
    so a re-entry (a second ``finalize-step``, a repeated
    ``update --status in_progress``) cannot move the base forward and silently
    shrink the artifact list to the edits made after the re-entry.

    Returns the SHA now on the task (existing or newly captured), or ``None``
    when HEAD could not be resolved OR did not resolve to a well-formed object id
    — in which case NOTHING is written, because a task carrying no baseline is an
    honestly-unknown state and a fabricated one would produce a confident, wrong
    artifact list.

    ⛔ An EXISTING value is returned only when it is well-formed. A malformed one
    is neither returned nor overwritten: overwriting would move the base forward
    and silently shrink the artifact list, and returning it would hand a caller a
    value :func:`artifact_messages` is going to refuse. The refusal belongs at
    the read, where it is reported.
    """
    existing = task.get(TASK_START_SHA_FIELD)
    if isinstance(existing, str) and existing.strip():
        return existing.strip() if is_object_id(existing) else None
    head = _git(_checkout_root(), 'rev-parse', 'HEAD')
    if head is None or not is_object_id(head):
        return None
    sha = head.strip()
    task[TASK_START_SHA_FIELD] = sha
    return sha


def _message(task_number: int, body: str) -> str:
    return f'[ARTIFACT] ({ARTIFACT_CALLER_SKILL}:{task_number}) {body}'


def artifact_messages(task_number: int, base_sha: str, root: Path | None = None) -> list[str]:
    """Derive one ``[ARTIFACT]`` message per path changed since ``base_sha``.

    The status-code mapping is the one
    ``phase-5-execute/standards/workflow.md`` publishes:

    =============  ==========================================
    Status         Message
    =============  ==========================================
    ``A`` / ``M``  ``Wrote {path}``
    ``D``          ``Deleted {path}``
    ``R*``         ``Renamed {old} -> {new}`` (exactly ONE line — never a
                   delete plus a write, which would leave the audit trail
                   ambiguous about the operation's intent)
    ``C*``         ``Wrote {new}`` (treated as an add)
    =============  ==========================================

    An untracked file is reported as ``Wrote``: it is a file the task created,
    and it appears in no ``git diff`` output until it is staged.

    Returns an empty list when the diff is empty — an empty artifact list is a
    valid outcome (a pre-implemented task, a verification-profile task), and its
    absence from the log is itself the signal.

    Raises:
        ValueError: when ``base_sha`` is not a well-formed git object id (see
            :data:`_OBJECT_ID_RE`). A malformed baseline is REJECTED rather than
            silently skipped: skipping it would render a corrupted record as the
            same empty list an honest no-change task produces, which is the
            could-not-look-versus-nothing-to-look-at conflation this whole module
            exists to avoid. No git command runs on this path.
    """
    if not is_object_id(base_sha):
        raise ValueError(
            f'task_start_sha is not a well-formed git object id: {base_sha!r} — '
            'refusing to pass it to git as an argument'
        )
    root = root or _checkout_root()
    messages: list[str] = []

    # `-M` makes rename detection explicit rather than dependent on the caller's
    # git configuration, so the R-branch below is reachable deterministically.
    # The base is compared against the WORKING TREE (no second revision), which
    # is the only form that sees a task's edits before the chain-tail commit.
    name_status = _git(root, 'diff', '--name-status', '-M', base_sha)
    if name_status is None:
        return []
    for line in name_status.splitlines():
        fields = line.split('\t')
        if len(fields) < 2 or not fields[0]:
            continue
        code = fields[0]
        if code.startswith('R') and len(fields) >= 3:
            messages.append(_message(task_number, f'Renamed {fields[1]} -> {fields[2]}'))
        elif code.startswith('C') and len(fields) >= 3:
            messages.append(_message(task_number, f'Wrote {fields[2]}'))
        elif code.startswith('D'):
            messages.append(_message(task_number, f'Deleted {fields[1]}'))
        else:
            messages.append(_message(task_number, f'Wrote {fields[1]}'))

    untracked = _git(root, 'ls-files', '--others', '--exclude-standard')
    if untracked:
        for path in untracked.splitlines():
            if path.strip():
                messages.append(_message(task_number, f'Wrote {path.strip()}'))

    return messages


def emit_artifact_lines(plan_id: str, task_number: int, task: dict) -> list[str]:
    """Emit the task's ``[ARTIFACT]`` work-log lines and return them.

    Emits nothing — and returns an empty list — when the task carries no
    baseline. That is the honest state for a task whose ``in_progress``
    transition ``manage-tasks`` never observed (an externally hand-edited task
    record, or a run predating this field); reporting an artifact list derived
    from a guessed base would be worse than reporting none.

    A MALFORMED baseline is a third state and is reported rather than shared with
    the absent one: :func:`artifact_messages` refuses it before any git call, and
    the refusal is written to the work log as an ERROR naming the rejected value,
    so a corrupted record is VISIBLE instead of presenting as a task that changed
    nothing. The task-closing call still returns normally — the artifact channel
    is an audit trail and must never take it down.
    """
    base_sha = task.get(TASK_START_SHA_FIELD)
    if not isinstance(base_sha, str) or not base_sha.strip():
        return []
    try:
        messages = artifact_messages(task_number, base_sha.strip())
    except ValueError as exc:
        log_entry(
            'work',
            plan_id,
            'ERROR',
            f'[ARTIFACT] ({ARTIFACT_CALLER_SKILL}:{task_number}) refused — {exc}',
        )
        return []
    for message in messages:
        log_entry('work', plan_id, 'INFO', message)
    return messages
