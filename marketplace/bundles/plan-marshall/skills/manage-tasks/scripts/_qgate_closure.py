#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Closure checks for the phase-4-plan mechanical Q-Gate.

**Existence and closure are different questions, and only the first was ever
asked.** ``_cmd_qgate_mechanical._check_files_exist`` confirms that each
declared path RESOLVES on disk; nothing confirms that the declared SET contains
everything it must. A plan whose every declared path exists can still be
missing the one path that matters, and the omission is invisible by
construction: the gap is precisely what never entered the write-set, so no
downstream check that reads the write-set can see it.

Three closures are computed here, matching the three ways a derived set goes
incomplete:

``projection``
    Every path a deliverable declares it will CHANGE is projected into at least
    one step of a task belonging to that deliverable. A declared write path no
    task will touch means the task set does not cover the deliverable's own
    declared write-set — a sweep declared and never run.

``referrer``
    Every non-verification task step target is declared by its parent
    deliverable. ``phase-4-plan/SKILL.md`` § Step 5 already states this as an
    invariant ("Source each step's ``intent`` from the parent deliverable's
    ``affected_files[N].intent``") and nothing checked it. A step target absent
    from every declared set is a path in no write-set — the exact shape the
    retrospective recall check is structurally unable to report, because a path
    that appears in no declaration cannot be missing from one.

``claim_vs_index``
    Every declared GLOB is expanded against the tree and reconciled against the
    enumerated declaration. The ``{declared scope wide, write-set narrow}`` pair
    is machine-comparable — a declared glob against an enumerated file list —
    and an out-of-constraint hit is a scope contradiction to resolve
    explicitly, never a silent narrowing.

**Population is published, not implied.** Each check returns the population it
actually scanned, and a population gap flips ``population_complete`` to False
so a zero finding count over an unscanned set can never be read as a clean
verdict. A glob that matches nothing looks identical to a glob that matches
everything, and the only thing that separates them is the count of what was
examined.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _plan_parsing import deliverable_write_set

#: Glob metacharacters that make a declared bullet a PATTERN rather than a path.
#: ``[`` is deliberately excluded: a character class is legal glob syntax but is
#: vanishingly rare in a declared scope and common in prose, and misreading a
#: prose bracket as a pattern would manufacture findings.
_GLOB_METACHARACTERS = ('*', '?')

#: Hard ceiling on how many filesystem matches one declared glob contributes.
#: A pattern like ``**/*`` can enumerate the whole tree; bounding it keeps the
#: Q-Gate cheap. The bound is DISCLOSED (``enumeration_truncated``) rather than
#: applied silently — a truncated sweep that reports like a complete one is the
#: failure this module exists to prevent.
_MAX_GLOB_MATCHES = 2000

#: How many un-enumerated glob hits one finding names before it summarises the
#: rest. The finding always states the TOTAL, so the cap shortens the message
#: without understating the contradiction.
_MAX_HITS_NAMED = 20

_VERIFICATION_PROFILE = 'verification'


def _as_int(value: Any) -> int | None:
    """Return ``value`` as an int, or ``None`` when it is not one.

    Task records come off disk as JSON, so a field that should be a number may
    be absent, null, or a string. Returning ``None`` rather than raising keeps
    the malformed case a POPULATION fact the caller discloses, instead of an
    exception that would abort the whole closure pass over one bad record.
    """
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_declared_path(path: str) -> str:
    """Return a declared path in the one spelling the closure comparison uses.

    Declared paths and step targets are both repo-relative strings authored by
    hand, so ``./x/y.py`` and ``x/y.py`` name the same file and must compare
    equal. Only leading ``./`` segments and trailing separators are removed —
    no resolution against the filesystem, since a closure comparison must work
    for a ``write-new`` target that does not exist yet.
    """
    stripped = path.strip()
    while stripped.startswith('./'):
        stripped = stripped[2:]
    return stripped.rstrip('/')


def is_glob(path: str) -> bool:
    """Return True when a declared bullet is a pattern rather than a literal path."""
    return any(char in path for char in _GLOB_METACHARACTERS)


def declared_paths(deliverable: dict[str, Any]) -> set[str]:
    """Return every path a deliverable declares, across all three headings.

    The union of ``affected_files``, ``survey_scope`` and ``mutation_scope``,
    regardless of intent — this is the deliverable's declared SURFACE (what it
    said it would look at or touch), which is the right denominator for the
    referrer closure. The narrower write-set is what
    :func:`deliverable_write_set` returns and what the projection closure uses.
    """
    paths: set[str] = set()
    for field in ('affected_files', 'survey_scope', 'mutation_scope'):
        for entry in deliverable.get(field, []) or []:
            if not isinstance(entry, dict):
                continue
            raw = entry.get('path')
            if isinstance(raw, str) and raw.strip():
                paths.add(normalize_declared_path(raw))
    return paths


def _step_targets(task: dict[str, Any]) -> list[str]:
    """Return the normalized step targets of one task, in declaration order."""
    targets: list[str] = []
    for step in task.get('steps', []) or []:
        if not isinstance(step, dict):
            continue
        raw = (step.get('target') or '').strip()
        if raw:
            targets.append(normalize_declared_path(raw))
    return targets


def compute_projection_gaps(
    deliverable: dict[str, Any], tasks_for_deliverable: list[dict[str, Any]]
) -> list[str]:
    """Return declared write paths that no task of this deliverable targets.

    Pure and I/O-free so the closure can be exercised directly, without a plan
    directory. A deliverable whose write-set is empty yields no gaps — there is
    nothing to project — which is a measured zero, not an unexamined one; the
    caller distinguishes the two through the published population.
    """
    projected: set[str] = set()
    for task in tasks_for_deliverable:
        projected.update(_step_targets(task))
    write_set = {normalize_declared_path(p) for p in deliverable_write_set(deliverable)}
    # A declared GLOB is reconciled by the claim-vs-index closure, which can
    # expand it; the projection closure compares literal paths and would report
    # every pattern as unprojected.
    return sorted(p for p in write_set if p not in projected and not is_glob(p))


def compute_referrer_gaps(task: dict[str, Any], declared: set[str]) -> list[str]:
    """Return step targets of one task that its parent deliverable never declared.

    Pure and I/O-free. Membership is **literal string equality**, and that is the
    whole of the rule: a declared glob is neither expanded nor pattern-matched
    against, so a step target that a declared pattern *would* match is still
    reported. The step is the point at which a pattern must have become a
    concrete enumerated path, so "a glob somewhere in the deliverable might
    cover this" is exactly the unreconciled ``{declared scope wide, write-set
    narrow}`` pair rather than a reason to stay silent — the pair is the
    reconciliation check's subject, not a licence for this one to fall quiet.

    Literal equality is also what makes a declared glob harmless here rather
    than requiring a filter: a pattern string can only match a step target that
    is that same pattern string, which a concrete target never is.
    """
    return sorted({t for t in _step_targets(task) if t not in declared})


def expand_declared_glob(pattern: str, repo_root: Path) -> tuple[list[str], bool, bool]:
    """Expand one declared glob against the tree.

    Returns ``(matches, truncated, expandable)``:

    - ``matches`` — repo-relative paths of matching FILES, sorted, capped at
      :data:`_MAX_GLOB_MATCHES`.
    - ``truncated`` — True when the cap was reached, so the caller can disclose
      that the enumeration is a lower bound rather than the whole set.
    - ``expandable`` — False when the pattern could not be expanded at all (an
      absolute pattern, or one ``pathlib`` rejects). An unexpandable pattern is
      NOT an empty match set: it is an unmeasured one, and the caller must not
      let it read as "the glob matched nothing".
    """
    if pattern.startswith('/') or pattern.startswith('~'):
        return [], False, False
    matches: list[str] = []
    truncated = False
    try:
        for found in repo_root.glob(pattern):
            if not found.is_file():
                continue
            if len(matches) >= _MAX_GLOB_MATCHES:
                truncated = True
                break
            matches.append(found.relative_to(repo_root).as_posix())
    except (ValueError, NotImplementedError, OSError):
        return [], False, False
    return sorted(matches), truncated, True


def check_declared_set_closure(
    tasks: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Compute the projection and referrer closures over the plan.

    Returns ``(gaps, population)``. Each gap is a
    ``{'kind', 'title', 'detail', 'file_path'}`` record the caller turns into a
    Q-Gate finding — this function emits nothing itself, so the whole closure is
    testable without a findings store.

    ``population`` publishes what was actually examined:
    ``deliverables_scanned``, ``declared_paths_scanned``,
    ``step_targets_scanned``, ``tasks_scanned``, ``unmapped_tasks`` and
    ``population_complete``. ``population_complete`` is False when any
    non-verification task names a deliverable the outline does not contain, so
    an empty gap list computed over an incomplete population can never be read
    as closure.
    """
    by_number = {int(d['number']): d for d in deliverables if str(d.get('number', '')).isdigit()}
    tasks_by_deliverable: dict[int, list[dict[str, Any]]] = {}
    unmapped_tasks: list[int] = []
    tasks_scanned = 0
    step_targets_scanned = 0

    for task in tasks:
        if (task.get('profile') or '').strip() == _VERIFICATION_PROFILE:
            continue
        tasks_scanned += 1
        step_targets_scanned += len(_step_targets(task))
        number = _as_int(task.get('deliverable'))
        if number is None or number not in by_number:
            unmapped_tasks.append(_as_int(task.get('number')) or 0)
            continue
        tasks_by_deliverable.setdefault(number, []).append(task)

    gaps: list[dict[str, str]] = []
    declared_paths_scanned = 0

    for number in sorted(by_number):
        deliverable = by_number[number]
        declared = declared_paths(deliverable)
        declared_paths_scanned += len(declared)
        owned = tasks_by_deliverable.get(number, [])

        for path in compute_projection_gaps(deliverable, owned):
            gaps.append(
                {
                    'kind': 'projection',
                    'title': (
                        f'declared_set_closure: deliverable {number} declares '
                        f'{path!r} as a write but no task targets it'
                    ),
                    'detail': (
                        f'Deliverable {number} {deliverable.get("title", "?")!r} declares '
                        f'{path!r} in its write-set, and no step of any task assigned to '
                        f'that deliverable names it as a target. The declared set is not '
                        f'projected onto the task set: either add a step that writes '
                        f'{path!r}, or remove the path from the declaration. A declared '
                        f'path nobody will touch is a sweep declared and never run — the '
                        f'file exists, so the files_exist check passes, and the omission '
                        f'is invisible to every later gate.'
                    ),
                    'file_path': path,
                }
            )

        for task in owned:
            for target in compute_referrer_gaps(task, declared):
                gaps.append(
                    {
                        'kind': 'referrer',
                        'title': (
                            f'declared_set_closure: TASK-{int(task["number"]):03d} targets '
                            f'{target!r}, which deliverable {number} never declares'
                        ),
                        'detail': (
                            f'TASK-{int(task["number"]):03d} {task.get("title", "?")!r} '
                            f'declares step target {target!r}, which appears in no '
                            f'declaration of its parent deliverable {number} — not in '
                            f'Affected files, not in Files to survey, not in Files '
                            f'expected to mutate. Task steps are sourced from the '
                            f"deliverable's declared file list, so a target outside it "
                            f'means the declared set is incomplete. Add {target!r} to the '
                            f'deliverable with the intent the step carries, or correct the '
                            f'step. A path in no declared set is invisible to the '
                            f'retrospective recall check by construction: recall measures '
                            f'against the declaration, so a path the declaration never '
                            f'named can never be reported as missing from it.'
                        ),
                        'file_path': target,
                    }
                )

    population = {
        'deliverables_scanned': len(by_number),
        'declared_paths_scanned': declared_paths_scanned,
        'tasks_scanned': tasks_scanned,
        'step_targets_scanned': step_targets_scanned,
        'unmapped_tasks': sorted(unmapped_tasks),
        'population_complete': not unmapped_tasks,
    }
    return gaps, population


def check_declared_scope_reconciliation(
    deliverables: list[dict[str, Any]],
    repo_root: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Reconcile every declared GLOB against the file list it expands to.

    This is the ``{declared scope wide, write-set narrow}`` detector, and it is
    mechanical: a declared glob is expanded against the tree and every match
    that the deliverable does not also enumerate is reported as a scope
    contradiction. The resolution is the author's — widen the declaration with
    a recorded authorisation, or narrow the declared scope and record the
    un-swept surface as a deliberate documented exclusion — but the
    contradiction itself is no longer a judgement call.

    Returns ``(gaps, population)``. ``population`` publishes
    ``globs_declared``, ``globs_expanded``, ``globs_unexpandable``,
    ``matches_enumerated``, ``enumeration_truncated`` and
    ``population_complete``. ``population_complete`` is False when any declared
    glob could not be expanded or when an expansion hit the match ceiling: a
    pattern that was never expanded contributes zero hits exactly as a pattern
    that genuinely matches nothing does, and the two must not be reported alike.
    """
    gaps: list[dict[str, str]] = []
    globs_declared = 0
    globs_expanded = 0
    globs_unexpandable = 0
    matches_enumerated = 0
    enumeration_truncated = False

    for deliverable in deliverables:
        number = deliverable.get('number')
        declared = declared_paths(deliverable)
        literal_declared = {p for p in declared if not is_glob(p)}
        patterns = sorted(p for p in declared if is_glob(p))
        globs_declared += len(patterns)

        for pattern in patterns:
            matches, truncated, expandable = expand_declared_glob(pattern, repo_root)
            enumeration_truncated = enumeration_truncated or truncated
            if not expandable:
                globs_unexpandable += 1
                gaps.append(
                    {
                        'kind': 'unexpandable_glob',
                        'title': (
                            f'declared_scope_reconciliation: deliverable {number} declares '
                            f'glob {pattern!r}, which could not be expanded'
                        ),
                        'detail': (
                            f'Deliverable {number} declares the pattern {pattern!r}, which '
                            f'could not be expanded against the repository (absolute, or '
                            f'rejected by the path matcher). An unexpandable pattern is an '
                            f'UNMEASURED scope, not an empty one — it contributes zero hits '
                            f'exactly as a pattern matching nothing does. Replace it with a '
                            f'repo-relative pattern or with the enumerated paths themselves.'
                        ),
                        'file_path': pattern,
                    }
                )
                continue
            globs_expanded += 1
            matches_enumerated += len(matches)
            unenumerated = [m for m in matches if m not in literal_declared]
            if not unenumerated:
                continue
            named = unenumerated[:_MAX_HITS_NAMED]
            remainder = len(unenumerated) - len(named)
            listed = ', '.join(repr(path) for path in named)
            if remainder > 0:
                listed += f' (+{remainder} more, not named here)'
            truncation_note = (
                ' The expansion hit the match ceiling, so this hit list is a LOWER BOUND '
                'on the contradiction, not its full extent.'
                if truncated
                else ''
            )
            gaps.append(
                {
                    'kind': 'claim_vs_index',
                    'title': (
                        f'declared_scope_reconciliation: deliverable {number} declares scope '
                        f'{pattern!r} but enumerates {len(unenumerated)} fewer file(s)'
                    ),
                    'detail': (
                        f'Deliverable {number} {deliverable.get("title", "?")!r} declares the '
                        f'scope {pattern!r}, which expands to {len(matches)} file(s) in the '
                        f'tree. {len(unenumerated)} of them appear in no declared list of this '
                        f'deliverable: {listed}. This is the '
                        f'{{declared scope wide, write-set narrow}} pair — the declared sweep '
                        f'was never reconciled against what it actually matches. Resolve it '
                        f'explicitly: widen the enumeration to include the hits, or narrow the '
                        f'declared scope and record the un-swept surface as a deliberate '
                        f'documented exclusion. Leaving the pair standing freezes a write-set '
                        f'that the declaration itself says is too small.{truncation_note}'
                    ),
                    'file_path': pattern,
                }
            )

    population = {
        'globs_declared': globs_declared,
        'globs_expanded': globs_expanded,
        'globs_unexpandable': globs_unexpandable,
        'matches_enumerated': matches_enumerated,
        'enumeration_truncated': enumeration_truncated,
        'population_complete': globs_unexpandable == 0 and not enumeration_truncated,
    }
    return gaps, population
