#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Notation cross-check for the ``pre-commit-verify-freshness`` gate.

Notation: imported as a module (PYTHONPATH) — ``from _freshness_crosscheck
import cross_check_candidates``. NOT an executor entry point.

The gate's primary predicate answers *"is there a successful ``kind=build`` row
against the current working-tree sha?"*. That predicate asserts a row EXISTS; it
never asks whether the row is evidence of a build **this project performs**. The
two are not the same question, and the gap between them is not theoretical: the
gate has been satisfied by a row naming a package-manager build the project has
no module for, written into the shared ledger by something other than a real
build of this tree. The verdict happened to be right; the evidence did not
support it. A gate that is right for the wrong reason produces no failure to
learn from, so it can stay wrong indefinitely.

This module closes that gap by comparing each candidate row's ``notation``
against the set of build notations the project's architecture actually resolves
to (``manage-architecture``'s ``resolve_project_build_notations``). The
comparison target is deliberately the ARCHITECTURE, not the ledger: comparing
ledger rows against other ledger rows would let a polluted ledger corroborate
itself.

Three-valued verdict, never collapsed
=====================================

:data:`CORROBORATED`
    The row's notation is one the architecture resolves. The evidence is
    auditable and related; the gate may pass on it.

:data:`REFUTED`
    The architecture resolved a non-empty notation set and **no** candidate row's
    notation is in it — including the case where no candidate carries a usable
    notation at all (missing, empty, or not a string). It is the whole candidate
    list that is refuted, never a single row: one corroborating row is enough to
    pass. No candidate can then be evidence of a build of this project, and the
    gate MUST fail closed.

:data:`UNVERIFIED`
    The notation set could not be established (the crawl raised, or resolved no
    build notation anywhere). Nothing is known about the row's relatedness.

The fail-direction, and why it splits
=====================================

An uncross-checkable match must not *silently* pass; that leaves two candidate
directions, and this module takes a different one for each of the two ways a
cross-check can decline to corroborate — because they are different facts:

* **A refutation is positive knowledge** ("the architecture resolves maven and
  nothing else; this row says npm"), so it **fails closed**. This is the defect
  class the gate exists to close, and admitting it with a warning would leave the
  false-green in place while merely annotating it.
* **An inability to resolve is the absence of knowledge**, so it **passes with
  the inability recorded in the decision record** (``notation_cross_check:
  unverified`` plus a ``notation_cross_check_reason``). Failing closed here would
  block every legitimate pre-commit transition in a working tree whose
  architecture has not been discovered — a project mid-onboarding, a fresh
  clone, a synthetic fixture tree — none of which is evidence of anything wrong.
  The gate's PRIMARY predicate has already been satisfied at that point; refusing
  on a supplementary check that could not run trades a false-green for a
  false-red on strictly less evidence.

⛔ The two are never folded together. ``unverified`` is a stated sentinel, not a
quiet ``corroborated``: it always reaches the decision record, so "passed
uncross-checked" is visible to a reader rather than indistinguishable from
"passed cross-checked" (ADR-015 — an absent identity is a stated sentinel, and
every presence guard is a meaning guard).

A doc-only carve-out was considered and REFUSED
===============================================

The obvious way to spend less on this check is to exempt a footprint that
touched only markdown. That is refused here on a hard constraint, and the
refusal is recorded in the shipped source rather than only in a run report,
because an unexplained absence invites the next author to add it.

**Markdown under the bundle tree is a build input in this repository.** Tests
read and assert on the BODIES of bundle documents — ``test/plan-marshall/
test_triage_loop_back_target.py`` parses ``marketplace/bundles/plan-marshall/
skills/plan-marshall/workflow/triage.md`` and fails when its classification
table changes — so a markdown-only edit can turn the suite red exactly as a
``*.py`` edit can. A doc-only freshness exemption would therefore hand back a
``fresh`` verdict for a tree whose tests were never run against it, which is the
whole defect class this module exists to close, re-entering through the
exemption. Build necessity is not this module's question in any case: it is
owned by the single ``build-decision`` authority the gate consults BEFORE the
ledger scan (see the caller's module docstring), and that authority reads the
project's own ``build.map`` globs rather than a hard-coded notion of which
suffixes matter.

Why this is a second check and not a change to the evidence model
=================================================================

The obvious objection to this module is that it adds a second special-case check
beside an existing one, when the recurring complaint about the ledger is that its
**evidence model** is under-specified — most sharply that a consumer reads the
gate's ``fresh`` as *"tests are fresh"* while its predicate only says *"some build
succeeded"*, which a compile-only build satisfies. If the model were the problem,
the fix would belong in the row, not in a reader.

**The row already carries more than the gate reads — checked, not assumed.**
``_ledger_core.build_record`` records ``notation``, and it also records ``args``
(the executor argv, stamped on every build-class dispatch as
``' '.join(script_args)``) and ``command`` (the line the wrapper reported running).
The gate historically read none of the three. This module makes it read
``notation``.

⚠ **That is not the same as saying the row is sufficient for a TIER claim, and the
difference is why the tier question is left alone.** ``args`` is joined
**without quoting**, so a module-scoped ``run --command-args "verify plan-marshall"``
is stamped as ``run --command-args verify plan-marshall`` and re-parsing it cannot
tell that canonical apart from a whole-project ``verify`` — the argument boundary
is gone. ``command`` is sourced from the wrapper's stdout payload and is ``None``
whenever that payload was unreadable, which includes every killed build. So the
row holds *evidence about* which canonical ran, not a field a consumer can read a
tier off cleanly. Whether that evidence is enough, or whether the producer must
stamp the canonical explicitly, is a real open question — and answering it is
exactly the model-level work this module is NOT doing.

⛔ **The tier question is deliberately NOT answered here, and this is a scope
boundary, not a claim that the boundary is free.** Two costs make it its own
change rather than a rider on this one. First, it would change what the gate
*means*, and the documents do not currently agree on what that is: this skill's
own contract says "a successful build was observed against this tree", while
``phase-6-finalize/standards/push.md`` says freshness "verifies that the most
recent ``verify`` run actually observed this version of the code" and
``phase-6-finalize/SKILL.md`` says it validates "that a ``verify`` was actually
performed". ⭐ **That disagreement is the tier defect, stated in prose** — the
consumer-facing docs already promise the stronger claim the predicate does not
make, which is why closing it needs a deliberate ruling rather than a patch here.
Second, it needs a per-build-system decision on which canonicals count as
test-running, and getting that wrong in the strict direction produces the
mirror-image false signal: a legitimate transition refused because the footprint
only ever warranted a compile.

Structural stale verdicts are NOT this module's business
========================================================

A tree mutated after its last build is correctly ``stale``: the stamp was never
wrong, the commit invalidated it. Nothing here re-stamps, relaxes the sha
comparison, or otherwise softens that verdict — a candidate only reaches this
module once it has ALREADY matched on ``kind``, ``status`` and ``worktree_sha``,
so a mutated tree has no candidates and never gets here.
"""

from __future__ import annotations

from typing import Any

#: The row's notation is one the project's architecture resolves.
CORROBORATED = 'corroborated'
#: The architecture resolved a notation set that does not contain the row's.
REFUTED = 'refuted'
#: The notation set could not be established; relatedness is unknown.
UNVERIFIED = 'unverified'

#: ``notation_cross_check_reason`` when the resolver was reached and could not
#: produce a usable set — it raised while running, or it returned something that
#: is not a set of notations at all. Both are faults in the resolution rather
#: than in reaching it, which is what separates this from
#: :data:`REASON_RESOLVER_UNIMPORTABLE`.
REASON_RESOLUTION_FAILED = 'architecture_resolution_failed'
#: ``notation_cross_check_reason`` when the resolver could not even be IMPORTED.
#: Distinct from :data:`REASON_RESOLUTION_FAILED` because the two are different
#: facts with different owners: an un-crawlable project is a legitimate quiet
#: pass, while an unimportable resolver means THIS CHECK IS BROKEN — a deployment
#: or ``PYTHONPATH`` fault that will report ``unverified`` on every row forever.
#: Both pass the gate (neither is a refutation), so folding them would cost
#: nothing at the gate and everything to a reader trying to find out why the
#: cross-check never corroborates anything.
REASON_RESOLVER_UNIMPORTABLE = 'architecture_resolver_unimportable'
#: ``notation_cross_check_reason`` when the resolver ran but resolved no build notation.
REASON_NO_NOTATIONS_RESOLVED = 'architecture_resolved_no_build_notations'
#: ``notation_cross_check_reason`` when every candidate row carried no notation.
REASON_NOTATION_ABSENT = 'notation_absent'
#: ``notation_cross_check_reason`` when candidate notations are all unresolved by the architecture.
REASON_NOTATION_UNRELATED = 'notation_unrelated'


def resolve_expected_notations(project_dir: str) -> tuple[frozenset[str], str | None]:
    """Resolve the project's build-notation set, or say why it could not be.

    Wraps ``manage-architecture``'s ``resolve_project_build_notations`` so the
    gate never has to distinguish "the crawl raised" from "the crawl ran and
    found nothing" at the call site. The cross-skill import is in-function, the
    same discipline the caller uses for its ``build-decision`` consult: this
    command module keeps no hard top-level dependency on another skill's scripts
    dir, so it stays importable when ``manage-architecture`` is not on the path.

    Args:
        project_dir: Project root to resolve against — the gate's already
            resolved worktree root.

    Returns:
        ``(notations, reason)``. Exactly one side is informative: a non-empty
        ``notations`` with ``reason is None``, or an empty ``notations`` with a
        non-``None`` reason naming which inability occurred. An empty set is
        NEVER returned as a refutation-grade answer — see the module docstring.

        The three inabilities are named apart rather than folded, because they
        have different owners: :data:`REASON_RESOLVER_UNIMPORTABLE` is a fault in
        THIS check's own deployment (the resolver could not even be reached),
        :data:`REASON_RESOLUTION_FAILED` is a fault in the resolution itself (it
        raised while running, or returned a value that is not a set of
        notations), and :data:`REASON_NO_NOTATIONS_RESOLVED` is the ordinary
        un-crawled project.
        All three pass the gate, so the distinction buys nothing there and
        everything for a reader asking why nothing ever corroborates.
    """
    try:
        from _cmd_client_query import resolve_project_build_notations
    except Exception:  # noqa: BLE001 — see below: an import can fail as more than ImportError
        # NOT just ``ImportError``. Importing this module executes another
        # skill's module body, and that body can raise anything: today
        # ``_cmd_client_build`` resolves its bundles root at module scope via
        # ``marketplace_paths.resolve_bundles_root``, which raises ``RuntimeError``
        # by design "so import-time misconfiguration fails loudly". Loudly is
        # right for a build tool and wrong here — it escaped this function
        # entirely, past the guard below, and gave the gate's callers a traceback
        # instead of a TOON ``status``. Every failure raised WHILE importing is a
        # deployment or PYTHONPATH fault, which is exactly what
        # REASON_RESOLVER_UNIMPORTABLE names, so all of them map to it.
        return frozenset(), REASON_RESOLVER_UNIMPORTABLE
    try:
        notations = resolve_project_build_notations(project_dir)
    except Exception:  # noqa: BLE001 — any resolver failure is an inability, not a refutation
        return frozenset(), REASON_RESOLUTION_FAILED
    # Defence against a FUTURE resolver, not a live hazard: today
    # ``resolve_project_build_notations`` has a single ``return frozenset(...)``,
    # so it cannot hand back a non-container. A second return that could would
    # pass the truthiness test below and then raise TypeError from the ``in``
    # comparison in cross_check_candidates — OUTSIDE this try, escaping the gate.
    # The guard belongs here rather than at the comparison because this is the
    # function whose job is to turn every inability into a named reason.
    if not isinstance(notations, (frozenset, set)):
        return frozenset(), REASON_RESOLUTION_FAILED
    if not notations:
        return frozenset(), REASON_NO_NOTATIONS_RESOLVED
    return notations, None


def _candidate_notation(entry: dict[str, Any]) -> str:
    """Return ``entry``'s notation as a string, or ``''`` when it carries none."""
    notation = entry.get('notation')
    return notation if isinstance(notation, str) else ''


def cross_check_candidates(
    candidates: list[dict[str, Any]],
    project_dir: str,
) -> dict[str, Any]:
    """Cross-check already-matching build rows against the resolved notation set.

    ``candidates`` are the rows that ALREADY satisfy the gate's primary
    predicate (``kind == 'build'``, ``status == 'success'``,
    ``worktree_sha == current``), in ledger file order. This function decides
    which of them — if any — may be cited as the evidence for a ``fresh``
    verdict.

    The whole candidate list is examined rather than only the first match, and
    that is load-bearing for precision in the passing direction: a project that
    legitimately builds with several notations can have an unrelated row sitting
    ahead of a related one in file order, and returning on the first match would
    refuse a plan whose real evidence is two lines further down. A single
    corroborated candidate is enough; only a list in which NONE corroborates is
    a refusal.

    Selection among corroborated candidates is by file order (the first one),
    matching the pre-cross-check behaviour of the gate's scan. The ledger is
    pure-append, so file order is write order.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order. MUST be
            non-empty — the caller handles the no-candidate case as ``stale``
            before reaching here, and this function has no honest verdict for an
            empty list: ``refuted`` would assert "no row carries a notation"
            about zero rows, and ``unverified`` would hand the caller a
            ``chosen`` index addressing nothing.
        project_dir: Project root the architecture is resolved against.

    Returns:
        A dict carrying ``verdict`` (:data:`CORROBORATED` / :data:`REFUTED` /
        :data:`UNVERIFIED`), ``chosen`` (the POSITION in ``candidates`` of the
        cited row, or ``None`` on :data:`REFUTED`), ``expected_notations`` (the
        sorted resolved set), ``candidate_notations`` (the sorted distinct
        notations the candidates carried, with a row carrying none contributing
        nothing), and ``reason`` (``None`` on :data:`CORROBORATED`, otherwise the
        naming constant).

        ``chosen`` is a position rather than the row object so the caller can map
        it back to its own addressing (a ledger index) without either side
        depending on object identity. Handing back the dict instead would force
        the caller to recover the position by ``id()`` — sound only while this
        function returns one of the very objects it was passed, which is not a
        property its signature promises.

    Raises:
        ValueError: If ``candidates`` is empty. A precondition violation is a
            programming error and is failed fast rather than answered with
            whichever verdict the code happens to reach first.
    """
    if not candidates:
        raise ValueError(
            'cross_check_candidates requires at least one candidate row; the '
            'no-candidate case is the caller\'s stale route, not a cross-check verdict'
        )

    expected, resolution_reason = resolve_expected_notations(project_dir)
    candidate_notations = sorted({n for n in map(_candidate_notation, candidates) if n})

    if resolution_reason is not None:
        return {
            'verdict': UNVERIFIED,
            'chosen': 0,
            'expected_notations': [],
            'candidate_notations': candidate_notations,
            'reason': resolution_reason,
        }

    for position, entry in enumerate(candidates):
        if _candidate_notation(entry) in expected:
            return {
                'verdict': CORROBORATED,
                'chosen': position,
                'expected_notations': sorted(expected),
                'candidate_notations': candidate_notations,
                'reason': None,
            }

    return {
        'verdict': REFUTED,
        'chosen': None,
        'expected_notations': sorted(expected),
        'candidate_notations': candidate_notations,
        # A row with no notation at all and a row naming an unresolved build are
        # both refusals, but they need different remedies — one says "this row
        # was not written by the dispatch boundary", the other says "this row is
        # from a build this project does not perform" — so they are named apart
        # rather than folded into one message.
        'reason': REASON_NOTATION_UNRELATED if candidate_notations else REASON_NOTATION_ABSENT,
    }
