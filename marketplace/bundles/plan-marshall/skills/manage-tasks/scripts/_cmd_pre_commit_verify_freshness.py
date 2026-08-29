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
is **neither notation-blind nor scope-blind**, and those are the two deliberate
narrowings. Matching on ``kind``/``status``/``worktree_sha`` alone asserts that a
row EXISTS; it never asks whether the row is evidence of a build THIS project
performs, nor whether that build actually COVERED the change. Both gaps produced
real false-greens — a row naming a build the project has no module for, and a
single-directory 573-test run standing for a whole-tree change while two
whole-tree runs against the same sha had timed out and failed. Every row that
clears the primary predicate is therefore cross-checked on both dimensions:
against the build notations the project's architecture resolves to, and against
the canonical + scope the row itself records. See :mod:`_freshness_crosscheck`
for the two three-valued verdicts, the joint selection that makes a row citable
only when it satisfies both, the split fail-direction, and the recorded refusal
of a doc-only carve-out. Both checks remain build-TOOL-agnostic: a
Maven/Gradle/npm build satisfies the gate whenever the architecture resolves that
notation and its recorded canonical and scope cover the change.

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
                     matching ``worktree_sha`` exists AND one such entry is
                     citable on BOTH cross-check dimensions; a successful build
                     that covers this change has been observed against the
                     current on-disk state, so the gate is permitted to pass.
                     ``notation_cross_check`` records whether the evidence was
                     ``corroborated`` or merely ``unverified`` and
                     ``scope_cross_check`` whether it was ``covered`` or merely
                     ``undetermined`` — neither pair is ever folded, so a pass on
                     unaudited evidence is legible as such, and ``row_scopes``
                     names what each candidate row actually recorded.
- ``stale``        — the ledger has entries but none is citable: either none is a
                     successful build against the current working-tree sha, or
                     every such build names a notation this project's
                     architecture does not resolve, or every such build is
                     narrower than the change, or the attributable rows and the
                     covering rows are disjoint. The gate MUST fail closed. The
                     verdict carries a ``reason`` naming WHY, because the routes
                     need different remedies and this gate must not assert a
                     cause it did not establish: ``worktree_mutated`` /
                     ``build_error`` / ``build_timeout`` / ``build_killed`` /
                     ``build_indeterminate`` (see ``_stale_reason`` below), plus
                     ``notation_unrelated`` / ``notation_absent`` /
                     ``build_scope_narrow`` /
                     ``no_row_both_attributable_and_adequate`` from the
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
    COVERED,
    REASON_REQUIRED_COVERAGE_UNKNOWN,
    RequiredCoverage,
    cross_check_candidates,
    load_analysis_vocabulary,
    required_coverage,
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

    One message for every route cannot be honest, because CAUSE and REMEDY differ
    per route and they differ independently. Only ``worktree_mutated`` involves a
    mutation at all, so any message asserting one states a cause the gate did not
    establish. And re-running the build is the right remedy for ``build_timeout``
    and ``build_indeterminate`` while being actively wrong for ``build_error``
    (fix the reported failures first) and for ``build_killed`` (the blind retry
    the no-blind-retry rule forbids). A ``killed`` row for the CURRENT sha is the
    sharpest case: the tree was not mutated, a build was observed and was killed,
    so a mutation message would name a cause that did not occur AND prescribe the
    one action that rule forbids.

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
    entries in file order — **not** its physical line number. ``read_entries``
    skips three kinds of line: blank ones, unparseable ones, and lines that are
    valid JSON but not objects. Any of the three shifts the two apart, so a
    divergence is NOT by itself evidence of corruption — a stray newline
    produces it too. The parsed index is nonetheless the one an auditor needs,
    because it addresses the row this gate actually read.

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


def _resolve_required_coverage(plan_id: str) -> tuple[RequiredCoverage | None, str | None]:
    """Derive what a build must have covered to be evidence for THIS change.

    Assembles the three inputs the pure derivation needs — the live plan
    footprint, the ``build.map`` globs and the registered-module set — through
    the SAME in-process seams ``build-pyproject``'s ``resolve-test-scope`` handler
    uses, so the coverage requirement this gate enforces and the scope a build is
    told to run against are computed from one derivation rather than two that can
    drift. Every import is deferred for the reason the rest of this module defers
    its cross-skill imports: no hard top-level dependency on another skill's
    scripts dir.

    ⛔ Every inability returns ``(None, reason)``, never a permissive
    :class:`RequiredCoverage`. An unresolvable footprint rendered as an empty one
    would require nothing of any row and re-open the false-green this whole
    dimension exists to close; an empty MODULE set rendered as "no modules needed"
    would do the same for the scope half. ``None`` routes the coverage dimension
    to ``undetermined``, which passes with the inability recorded — the gate is
    not made stricter by an input nobody measured, and not made weaker either.

    Args:
        plan_id: The plan whose live footprint bounds the requirement.

    Returns:
        ``(required, reason)``. Exactly one side is informative.
    """
    vocabulary, vocabulary_reason = load_analysis_vocabulary()
    if vocabulary is None:
        return None, vocabulary_reason
    try:
        from _test_scope_divergence import resolve_test_scope
        from extension_base import _read_build_map_globs, _resolve_plan_footprint
        from marketplace_bundles import extract_bundle_name, find_bundles
        from marketplace_paths import find_marketplace_path
    except Exception:  # noqa: BLE001 — an import can fail as more than ImportError
        return None, REASON_REQUIRED_COVERAGE_UNKNOWN

    try:
        footprint = _resolve_plan_footprint(plan_id)
        globs = _read_build_map_globs(None)
        bundles_root = find_marketplace_path(None)
        registered = (
            frozenset(extract_bundle_name(d) for d in find_bundles(bundles_root))
            if bundles_root is not None
            else frozenset()
        )
    except OSError:
        return None, REASON_REQUIRED_COVERAGE_UNKNOWN

    # An unresolvable footprint and an unenumerable module set are both
    # "the requirement could not be measured", NOT "nothing is required".
    if footprint is None or not registered:
        return None, REASON_REQUIRED_COVERAGE_UNKNOWN

    resolution = resolve_test_scope(footprint, globs, registered)
    return (
        required_coverage(
            footprint,
            resolution.scoped_modules,
            resolution.divergence_possible,
            vocabulary,
        ),
        None,
    )


def _verdict_for_candidates(
    candidates: list[tuple[int, dict]],
    *,
    plan_id: str,
    current_sha: str,
    worktree_root: Path,
    ledger_path: Path,
) -> dict:
    """Cross-check the matching build rows and render the decision record.

    ``candidates`` have already satisfied the primary predicate, so two questions
    remain, and they are answered independently and reported separately:
    whether any row is evidence of a build THIS project performs (attribution),
    and whether any row records a build that actually COVERED this change
    (coverage). Both verdicts come from :mod:`_freshness_crosscheck` and neither
    is collapsed into the other.

    The gate passes only on a row that is citable on BOTH — the cross-check's
    ``chosen`` position, which is ``None`` whenever either dimension refused or
    the two admissible sets are disjoint. That joint condition is the fix for the
    observed false-green: a single-directory 573-test row is perfectly
    attributable, so an attribution-only selection cited it as ``corroborated``
    evidence for a whole-tree change.

    * ``chosen`` is not ``None`` → ``fresh``, citing that row and publishing both
      dimensions' verdicts. A dimension that could not judge is recorded as such
      (``notation_cross_check: unverified`` / ``scope_cross_check: undetermined``
      plus its reason), so a pass on unaudited evidence stays legible as one.
    * ``chosen`` is ``None`` → ``stale``, carrying the cross-check's
      ``joint_reason`` as the gate's own ``reason``.

    Args:
        candidates: ``(parsed_index, entry)`` pairs in ledger file order.
        plan_id: The plan the gate was invoked for.
        current_sha: The recomputed working-tree currency hash.
        worktree_root: The resolved worktree root, echoed into the record.
        ledger_path: The ledger the rows were read from, echoed into the record.

    Returns:
        The gate's ``fresh`` or ``stale`` verdict dict.
    """
    ledger_indices = [index for index, _ in candidates]
    required, coverage_reason = _resolve_required_coverage(plan_id)
    outcome = cross_check_candidates(
        [entry for _, entry in candidates],
        str(worktree_root),
        required,
        coverage_unavailable_reason=coverage_reason,
    )
    verdict = outcome['verdict']
    scope_verdict = outcome['scope_verdict']
    # ``chosen`` is a POSITION in the list handed to the cross-check, and that
    # list was built from ``candidates`` in order — so the same position indexes
    # both, and the row's ledger index is recovered without either side relying
    # on the identity of the dict that travelled across the boundary.
    chosen = outcome['chosen']

    if chosen is None:
        return {
            'status': 'stale',
            'plan_id': plan_id,
            'reason': outcome['joint_reason'],
            'worktree_sha': current_sha,
            'notation_cross_check': verdict,
            'scope_cross_check': scope_verdict,
            'expected_notations': outcome['expected_notations'],
            'candidate_notations': outcome['candidate_notations'],
            'row_scopes': outcome['row_scopes'],
            'worktree_root': str(worktree_root),
            'ledger_path': str(ledger_path),
            'message': (
                f'A kind=build entry with status=success matches the current '
                f'working-tree sha ({current_sha}), but none of them may be cited as '
                f'evidence for this change ({outcome["joint_reason"]}). Attribution: '
                f'the architecture resolves '
                f'{", ".join(outcome["expected_notations"]) or "no build notation"} and the '
                f'matching rows carry '
                f'{", ".join(outcome["candidate_notations"]) or "no notation at all"}. '
                f'Coverage: the matching rows recorded '
                f'{"; ".join(outcome["row_scopes"]) or "no readable build scope"}. The gate '
                f'MUST fail closed. Re-run a build whose canonical and scope cover this '
                f'change; if the refusal is an attribution one, establish where the '
                f'unattributable row came from before trusting the ledger again.'
            ),
        }

    result = {
        'status': 'fresh',
        'plan_id': plan_id,
        'worktree_sha': current_sha,
        **_evidence_fields(ledger_indices[chosen], candidates[chosen][1]),
        'notation_cross_check': verdict,
        'scope_cross_check': scope_verdict,
        'expected_notations': outcome['expected_notations'],
        'row_scopes': outcome['row_scopes'],
        'worktree_root': str(worktree_root),
        'ledger_path': str(ledger_path),
    }
    if verdict != CORROBORATED:
        result['notation_cross_check_reason'] = outcome['reason']
    if scope_verdict != COVERED:
        result['scope_cross_check_reason'] = outcome['scope_reason']

    audited = verdict == CORROBORATED and scope_verdict == COVERED
    if audited:
        result['message'] = (
            f'A successful kind=build entry matches the current working-tree sha '
            f'({current_sha}); its notation is one this project\'s architecture resolves, '
            f'and the canonical and scope it recorded cover this change. Gate permitted '
            f'on corroborated, coverage-adequate evidence.'
        )
    else:
        unaudited = ', '.join(
            part
            for part in (
                None if verdict == CORROBORATED else f'attribution ({outcome["reason"]})',
                None if scope_verdict == COVERED else f'coverage ({outcome["scope_reason"]})',
            )
            if part
        )
        result['message'] = (
            f'A successful kind=build entry matches the current working-tree sha '
            f'({current_sha}), so the gate is permitted — but it could NOT be checked on: '
            f'{unaudited}. The evidence is unaudited on those dimensions: it has not been '
            f'shown inadequate, and it has not been shown adequate either.'
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
