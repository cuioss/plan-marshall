#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-commit verify-freshness command handler for manage-tasks.py.

Closes the necessary-vs-sufficient gap between ``loop-exit-guard``
(queue-empty proof) and the pre-push state (worktree-actually-verified
proof). The command answers a single deterministic question:

    Does the unified change-ledger contain a ``kind=build`` entry with
    ``status == 'success'`` whose ``worktree_sha`` equals the CURRENT
    working-tree currency hash?

That question is only worth asking when a build was necessary in the first
place. Build necessity is NOT re-derived here: the gate consults the single
build/no-build authority (``extension_base.should_execute_build``, the
``manage-config build-decision`` verb) with NO canonical command — it asks the
plan-wide "does anything in this footprint need a build?" question and MUST NOT
pick a representative command. A ``not_necessary`` verdict returns ``fresh``
carrying the verdict's own ``reason`` verbatim, so the gate never invents a
reason vocabulary of its own; a ``build`` verdict falls through to the ledger
scan below unchanged. See ADR-004 § "Amendment: ``build-decision`` is the sole
build/no-build authority".

A ``kind=build`` entry is stamped by the executor dispatch boundary after every
build-EXECUTING invocation, carrying the truthful build ``status`` (``success``
/ ``error`` / ``timeout`` / ``killed`` / ``unknown``) and the working-tree
``worktree_sha`` captured at build time. ``unknown`` is the boundary's verdict
for an exit-0 dispatch whose payload carried no wrapper-claimable status; like
every other non-``success`` member of the vocabulary it never satisfies the
``status == 'success'`` match below, so an unreadable payload fails the gate
closed instead of minting a false-fresh row. The boundary predicate is a conjunction -- a notation
under a ``build-*`` skill AND the build-executing subcommand (``run``) -- so a
query verb under a build wrapper, and a bare ``--help`` dispatch carrying no
subcommand, stamp NO row. That narrowing is what this gate depends on: a query
exits 0 without building anything, so a row stamped for it would make the scan
below answer ``fresh`` for a working tree that was never built.
The gate recomputes the current working-tree sha and
looks for a matching successful build entry. Matching on ``status`` rather than
``exit_code`` is load-bearing: the build wrapper exits 0 on timeout (the
outcome is modeled in its stdout TOON, not the exit code), so an ``exit_code``
predicate would launder a build that never finished into a false ``fresh``.
A row lacking ``status`` never matches — the gate fails closed to ``stale``.
The scan stays **tier-agnostic and plan-agnostic**: it never filters on
``plan_id``, so an orchestrator-driven global-tier build recorded under the
``NO_PLAN`` sentinel satisfies the gate exactly as a plan-scoped build does. It
is **no longer notation-blind**, and that is the one deliberate narrowing.
Matching on ``kind``/``status``/``worktree_sha`` alone asserts that a row
EXISTS; it never asks whether the row is evidence of a build THIS project
performs, and the gate has been satisfied by a row naming a build the project
has no module for. Every row that clears the primary predicate is therefore
cross-checked against the build notations the project's architecture actually
resolves to — see :mod:`_freshness_crosscheck` for the three-valued verdict, the
split fail-direction, and the recorded refusal of a doc-only carve-out. The
check remains build-TOOL-agnostic: a Maven/Gradle/npm build satisfies the gate
whenever the architecture resolves that notation for this project.

The matched evidence is NAMED in the decision record — the row's ``notation``,
its position in the ledger, its ``plan_id`` and its timestamp — so a reader can
see WHICH row satisfied the gate instead of taking the verdict on trust. That
alone converts a silent wrong-reason pass into a visible one, independently of
whether the cross-check could be performed.

The primitive is the *working-tree* currency, NOT the committed ``HEAD``. This
is a pre-commit gate: at gate time the plan's edits are still uncommitted, so a
``git rev-parse HEAD`` primitive would match trivially regardless of any
uncommitted change between build and gate (a false-positive ``fresh``). The
working-tree sha folds in the staged + unstaged + untracked-not-ignored state,
so an uncommitted edit after a clean-tree build changes the sha and the gate
correctly reports ``stale``.

Outcomes:

- ``fresh`` (+ the verdict's ``reason``) — the build-decision verdict is
                     ``not_necessary``: no build was ever required for this
                     footprint, so no ``kind=build`` entry could legally exist
                     and none is demanded. The short-circuit fires BEFORE the
                     ledger scan and forwards the authority's own reason text.
- ``fresh``        — a ``kind=build`` entry with ``status == 'success'`` and a
                     matching ``worktree_sha`` exists AND the notation
                     cross-check did not refute it; a successful build has been
                     observed against the current on-disk state, so the gate is
                     permitted to pass. ``notation_cross_check`` records whether
                     the evidence was ``corroborated`` or merely ``unverified``
                     — the two are never folded together, so a pass on
                     unaudited evidence is legible as such.
- ``stale``        — either the ledger has entries but none is a successful
                     build against the current working-tree sha, or every such
                     build names a notation this project's architecture does not
                     resolve. The gate MUST fail closed. The verdict carries a
                     ``reason`` naming WHY, because the routes need different
                     remedies and this gate must not assert a cause it did not
                     establish: ``worktree_mutated`` / ``build_error`` /
                     ``build_timeout`` / ``build_killed`` /
                     ``build_indeterminate`` (see ``_stale_reason`` below), plus
                     ``notation_unrelated`` / ``notation_absent`` from the
                     cross-check.
- ``undecidable``  — no positive freshness proof can be established. Two
                     sub-reasons: ``no_registry`` (the ledger file is absent or
                     empty) and ``head_unresolvable`` (the working-tree sha
                     cannot be computed — a non-git directory or a repo with no
                     commit). The gate MUST fail closed in both cases.

The full failure-mode contract — including the ``--force`` orchestrator
escape and the cross-references to phase-5-execute Step 12a and
phase-6-finalize ``push`` — is documented in
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness".
"""

from pathlib import Path

from _freshness_crosscheck import (
    CORROBORATED,
    REFUTED,
    cross_check_candidates,
)
from _ledger_core import (
    KIND_BUILD,
    read_entries,
    resolve_ledger_path,
)
from file_ops import WorktreeResolutionError, resolve_plan_context
from worktree_sha import compute_worktree_sha

# Per observed build ``status``, the ``stale`` reason and the remedy sentence.
#
# The gate's PASS/FAIL behaviour does not consult this table at all — only
# ``status == 'success'`` ever permits the gate, and every entry below is a
# refusal. What the table decides is what the refusal SAYS, and that is not
# cosmetic: the caller acts on it. A build that timed out and a build the harness
# killed both need "the tree is fine, the build did not finish"; a build that
# genuinely failed needs "fix the code"; and a killed build must NOT be
# blind-retried, which is the opposite of what the historical single message
# prescribed for all four.
_STALE_BY_STATUS: dict[str, tuple[str, str]] = {
    'error': (
        'build_error',
        'The most recent build against this working-tree state FAILED. The tree '
        'was observed; the build reported errors. Fix the reported failures and '
        're-run the build.',
    ),
    'timeout': (
        'build_timeout',
        'The most recent build against this working-tree state TIMED OUT — it '
        'exceeded its own outer budget and was terminated by this stack. It is '
        'NOT a failing build and NOT evidence of a code defect: no verdict was '
        'ever reported. Re-run the build, and diagnose the budget if it recurs.',
    ),
    'killed': (
        'build_killed',
        'The most recent build against this working-tree state was EXTERNALLY '
        'KILLED — externally killed, not flaky, do not blind-retry. It is NOT a '
        'failing build and NOT a timeout: no budget fired and no verdict was '
        'reported. Establish why the build was killed before re-running it.',
    ),
    'unknown': (
        'build_indeterminate',
        'The most recent build against this working-tree state reported an '
        'INDETERMINATE outcome — the dispatch boundary could not read a verdict '
        'from it. It supports no conclusion in either direction and must not be '
        'read as a pass or as a failure. Re-run the build to obtain a readable '
        'verdict.',
    ),
}

_STALE_MUTATED = (
    'worktree_mutated',
    'No kind=build entry of ANY status was stamped against this working-tree '
    'state, so no build has observed it — the worktree has been mutated since '
    'the last observed build. Re-dispatch a build before retrying.',
)


def _stale_reason(entries: list[dict], current_sha: str) -> tuple[str, str, str | None]:
    """Derive the ``stale`` reason from what the ledger actually holds.

    The historical gate emitted one message for every route to ``stale``:
    "the worktree has been mutated since the last observed build ... re-dispatch
    a build before retrying." That sentence asserts a CAUSE the gate never
    established, and prescribes a remedy that is wrong for three of the four
    routes. When the ledger holds a ``killed`` row for the CURRENT sha the tree
    was not mutated at all — a build was observed and was killed — so the gate
    was reporting a mutation that did not happen and prescribing exactly the
    blind retry the no-blind-retry rule forbids.

    Discrimination is by presence, then by status:

    * No ``kind=build`` row at all for ``current_sha`` → the tree really did move
      past every observed build (or was never built): ``worktree_mutated``.
    * A row exists for ``current_sha`` but none is ``success`` → the tree WAS
      observed; report the LAST such row's own status (:data:`_STALE_BY_STATUS`).
      A status outside the known vocabulary is reported as
      ``build_indeterminate`` rather than folded into a neighbour — an
      unresolvable case is its own answer.

    "Last" means **last in file order**, not latest by timestamp. The ledger is
    pure-append (``_ledger_core.append_entry`` writes one line per call and never
    rewrites), so file order IS write order and the two coincide. This is stated
    rather than assumed because the distinction would matter the moment the
    ledger stopped being append-only, and because ``timestamp_iso`` is present on
    every row and would look like the obvious key to sort on. Sorting on it would
    be strictly worse: it has one-second resolution, so two builds against the
    same tree within a second would order arbitrarily.

    Args:
        entries: All ledger entries, in file order.
        current_sha: The recomputed working-tree currency hash.

    Returns:
        ``(reason, message, observed_status)``. ``observed_status`` is ``None``
        on TWO routes, and the caller omits the field for both: the
        ``worktree_mutated`` route, where no row was observed at all, and the
        ``build_indeterminate`` sub-case where a row WAS observed but carried no
        readable ``status`` string. Reporting a status there would mean
        inventing one — the row's defining property is that it has none — so the
        field's absence is itself the honest answer, and ``reason`` still
        distinguishes the two routes.
    """
    matching = [
        entry
        for entry in entries
        if entry.get('kind') == KIND_BUILD and entry.get('worktree_sha') == current_sha
    ]
    if not matching:
        reason, message = _STALE_MUTATED
        return reason, message, None

    observed = matching[-1].get('status')
    key = observed if isinstance(observed, str) else None
    reason, message = _STALE_BY_STATUS.get(key or '', _STALE_BY_STATUS['unknown'])
    return reason, message, key


def _evidence_fields(index: int, entry: dict) -> dict:
    """Name the evidence row so a reader can find it, not merely trust it.

    ``matched_entry_index`` is the row's position among the ledger's PARSED
    entries in file order — not its physical line number. ``read_entries``
    skips malformed lines, so the two diverge exactly when the ledger has been
    corrupted; the parsed index is the one that addresses the row this gate
    actually read, which is what an auditor needs.

    Args:
        index: The row's index among the parsed ledger entries.
        entry: The ledger row itself.

    Returns:
        The evidence-identifying fields for the decision record.
    """
    return {
        'matched_entry_index': index,
        'matched_notation': entry.get('notation', ''),
        'matched_plan_id': entry.get('plan_id', ''),
        'timestamp_iso': entry.get('timestamp_iso', ''),
    }


def _verdict_for_candidates(
    candidates: list[tuple[int, dict]],
    *,
    plan_id: str,
    current_sha: str,
    worktree_root: Path,
    ledger_path: Path,
) -> dict:
    """Cross-check the matching build rows and render the decision record.

    ``candidates`` have already satisfied the primary predicate, so the only
    question left is whether any of them is evidence of a build THIS project
    performs. The three-valued answer comes from :mod:`_freshness_crosscheck`
    and is never collapsed:

    * ``corroborated`` → ``fresh``, citing the corroborated row.
    * ``unverified``   → ``fresh``, citing the first row AND recording that the
      cross-check could not run. The pass is permitted (the primary predicate
      holds and an inability to resolve is not evidence of anything wrong) but
      it is never silent.
    * ``refuted``      → ``stale``. The architecture resolved a notation set and
      no candidate is in it, so every candidate is evidence of some build other
      than one of this project's — the false-green this gate exists to close.

    Args:
        candidates: ``(parsed_index, entry)`` pairs in ledger file order.
        plan_id: The plan the gate was invoked for.
        current_sha: The recomputed working-tree currency hash.
        worktree_root: The resolved worktree root, echoed into the record.
        ledger_path: The ledger the rows were read from, echoed into the record.

    Returns:
        The gate's ``fresh`` or ``stale`` verdict dict.
    """
    index_by_id = {id(entry): index for index, entry in candidates}
    outcome = cross_check_candidates([entry for _, entry in candidates], str(worktree_root))
    verdict = outcome['verdict']

    if verdict == REFUTED:
        return {
            'status': 'stale',
            'plan_id': plan_id,
            'reason': outcome['reason'],
            'worktree_sha': current_sha,
            'notation_cross_check': REFUTED,
            'expected_notations': outcome['expected_notations'],
            'candidate_notations': outcome['candidate_notations'],
            'worktree_root': str(worktree_root),
            'ledger_path': str(ledger_path),
            'message': (
                f'A kind=build entry with status=success matches the current '
                f'working-tree sha ({current_sha}), but no such entry names a build '
                f'this project performs: the architecture resolves '
                f'{outcome["expected_notations"]} and the matching rows carry '
                f'{outcome["candidate_notations"] or "no notation at all"}. The row is '
                f'not evidence that THIS tree was built, so the gate MUST fail closed. '
                f'Re-dispatch a real build of this project, and establish where the '
                f'unrelated row came from before trusting the ledger again.'
            ),
        }

    entry = outcome['entry']
    result = {
        'status': 'fresh',
        'plan_id': plan_id,
        'worktree_sha': current_sha,
        **_evidence_fields(index_by_id[id(entry)], entry),
        'notation_cross_check': verdict,
        'expected_notations': outcome['expected_notations'],
        'worktree_root': str(worktree_root),
        'ledger_path': str(ledger_path),
    }
    if verdict == CORROBORATED:
        result['message'] = (
            f'A successful kind=build entry matches the current working-tree sha '
            f'({current_sha}), and its notation is one this project\'s architecture '
            f'resolves. Gate permitted on corroborated evidence.'
        )
    else:
        result['notation_cross_check_reason'] = outcome['reason']
        result['message'] = (
            f'A successful kind=build entry matches the current working-tree sha '
            f'({current_sha}), so the gate is permitted — but its notation could NOT '
            f'be cross-checked against this project\'s resolved build commands '
            f'({outcome["reason"]}). The evidence is unaudited: it has not been shown '
            f'unrelated, and it has not been shown related either.'
        )
    return result


def _build_necessity_verdict(plan_id: str) -> dict:
    """Return the COMMAND-FREE build-necessity verdict for ``plan_id``.

    Delegates to the single authority with ``canonical_command=None``: this gate
    asks whether ANY build was needed for the plan's live footprint, which is a
    plan-wide question, so it passes no command and MUST NOT choose a
    representative one. The returned dict carries ``decision`` and — on
    ``not_necessary`` — the authority's own ``reason``, which the caller forwards
    verbatim rather than inventing an exemption vocabulary.

    The import is in-function so this command module keeps no hard top-level
    dependency on another skill's scripts dir (the same discipline the
    ``manage-config`` build-decision wrapper uses). A verdict that cannot be
    obtained degrades to ``build``, which routes the caller into the ledger scan
    — the fail-closed direction.
    """
    try:
        from extension_base import should_execute_build

        verdict = should_execute_build(None, plan_id)
    except Exception:  # noqa: BLE001 — an unobtainable verdict must fail closed
        return {'decision': 'build'}
    if not isinstance(verdict, dict):
        return {'decision': 'build'}
    return verdict


def cmd_pre_commit_verify_freshness(args) -> dict:
    """Handle ``pre-commit-verify-freshness`` subcommand.

    See module docstring for the contract; the algorithm is laid out in
    deliverable 4 of the plan ``solution_outline.md``.
    """
    plan_id: str = args.plan_id

    # Build-necessity short-circuit: when the single authority rules that this
    # footprint needs no build, no kind=build ledger entry could ever legally be
    # stamped for it, so demanding one is an impossible demand rather than a
    # gate. Exempt BEFORE the ledger scan and forward the verdict's own reason.
    verdict = _build_necessity_verdict(plan_id)
    if verdict.get('decision') == 'not_necessary':
        return {
            'status': 'fresh',
            'plan_id': plan_id,
            'reason': verdict.get('reason', ''),
            'message': (
                'build-decision ruled a build not_necessary for this footprint, so no '
                'kind=build entry can exist and none is required. Gate permitted without '
                'a ledger scan.'
            ),
        }

    # ``ensure=False`` keeps this a routing lookup: a freshness check must not
    # materialize or existence-check the plan. A plan running against the main
    # checkout still needs a freshness gate, and the resolver supplies the
    # cwd-relative checkout root for that case; the ``Path.cwd()`` fallback
    # survives only for a genuinely unresolvable worktree, preserving the
    # previous non-fatal behaviour.
    try:
        worktree_root = Path(resolve_plan_context(plan_id, ensure=False).worktree_path)
    except WorktreeResolutionError:
        worktree_root = Path.cwd()
    current_sha = compute_worktree_sha(worktree_root)

    if current_sha is None:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'head_unresolvable',
            'worktree_root': str(worktree_root),
            'message': (
                f'Working-tree currency hash is undefined for {worktree_root} '
                f'(HEAD unresolvable — non-git directory or a repo with no '
                f'commit). No positive freshness proof exists; gate MUST fail '
                f'closed.'
            ),
        }

    ledger_path = resolve_ledger_path()
    entries = read_entries(ledger_path)

    if not entries:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'no_registry',
            'worktree_sha': current_sha,
            'worktree_root': str(worktree_root),
            'ledger_path': str(ledger_path),
            'message': (
                f'Change-ledger is absent or empty ({ledger_path}). No '
                f'kind=build entry exists to prove freshness; gate MUST fail '
                f'closed.'
            ),
        }

    # Collect EVERY successful build entry stamped against the current
    # working-tree sha, in file order. The primary predicate filters on kind,
    # status and worktree_sha — never plan_id — so it stays tier-agnostic.
    # Requiring status == 'success' (not exit_code == 0) is what closes the
    # first false-fresh hole: a timed-out build exits 0 but stamps
    # status: timeout, and a row lacking status never matches (fail-closed).
    #
    # Collecting the whole list rather than returning on the first hit is what
    # lets the notation cross-check below stay precise in the PASSING
    # direction: a project that legitimately builds with several notations can
    # carry an unrelated row ahead of a related one, and a first-match return
    # would refuse evidence that is two lines further down.
    candidates = [
        (index, entry)
        for index, entry in enumerate(entries)
        if entry.get('kind') == KIND_BUILD
        and entry.get('status') == 'success'
        and entry.get('worktree_sha') == current_sha
    ]

    if candidates:
        return _verdict_for_candidates(
            candidates,
            plan_id=plan_id,
            current_sha=current_sha,
            worktree_root=worktree_root,
            ledger_path=ledger_path,
        )

    # The gate has refused. WHY it refused is derived from the ledger rather
    # than assumed, so the caller is not told a mutation happened when a build
    # was observed and killed.
    reason, remedy, observed_status = _stale_reason(entries, current_sha)
    stale: dict = {
        'status': 'stale',
        'plan_id': plan_id,
        'reason': reason,
        'worktree_sha': current_sha,
        'worktree_root': str(worktree_root),
        'ledger_path': str(ledger_path),
        'message': (
            f'No successful kind=build entry matches the current working-tree '
            f'sha ({current_sha}). Gate MUST fail closed. {remedy}'
        ),
    }
    if observed_status is not None:
        stale['observed_status'] = observed_status
    return stale
