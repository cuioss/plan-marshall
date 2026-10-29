#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-merge findings gate that owns the merge dispatch for ``default:branch-cleanup``.

The pre-merge blocking-findings gate used to be an instruction: run
``phase_handshake findings-check``, parse its ``status``, and only then issue the
merge verb. Neither merge verb required that call, so a skipped or misread check
still merged — and the later archive refusal then stranded a plan whose change
was already on the base branch.

This script turns the instruction into a mechanism. It is the ONLY merge-shaped
dispatch ``branch-cleanup`` issues: it evaluates the blocking-findings invariant
for phase ``6-finalize`` and issues the routed merge verb only when that
evaluation proved the store clean. The merge is therefore unreachable without
the check having run and passed.

* **One verdict vocabulary.** The verdict comes from
  ``_handshake_commands.cmd_findings_check`` called in-process — the very handler
  behind ``phase_handshake findings-check`` — so this gate and that verb cannot
  disagree about what a pending actionable finding is, nor about the fail-closed
  ``query_failed`` reading of an unevaluable count. Like that verb, the gate
  writes no handshake row.
* **The CI merge verbs stay plan-agnostic.** ``ci pr safe-merge`` and
  ``ci pr merge-queue`` carry no plan state; ``--plan-id`` is consumed here, for
  the findings check alone, and is never forwarded to the CI router.

Return shape (CLI emits TOON; programmatic callers consume the dict directly):

* the gate refused — ``status: error`` carrying the findings verdict verbatim
  (``error: blocking_findings_present`` with ``blocking_count`` /
  ``blocking_types`` / ``per_type``, ``error: query_failed``, or any other
  refusal the verdict source returns) plus ``dispatched: false``. The merge
  runner was never invoked;
* the gate passed — the routed verb's payload verbatim plus
  ``findings_gate: clean`` and ``dispatched: true``. Branch on the verb's own
  ``status`` from here, exactly as on a direct verb call.

A malformed invocation (an unknown ``--route``, a ``safe-merge`` route without
``--strategy``, or a safe-merge-only flag on the ``merge-queue`` route) is refused
before the findings check runs, also with ``dispatched: false``. Every such
refusal carries ``refusal_category: invocation`` (:data:`REFUSAL_CATEGORY_FIELD` /
:data:`INVOCATION_REFUSAL`), whatever its ``error`` code, so a caller tells an
invocation refusal (the findings store was never read) from a store-verdict
refusal by that one field instead of by enumerating error codes. A store-verdict
refusal and a dispatched payload never carry the field.

**The same dispatch also proves REQUIRED-BOT PARTICIPATION.** A clean findings
store says nothing about whether a required reviewer ever saw the merge
candidate: a bot that never reviewed files no comment, so a pending-finding count
is structurally blind to it. The barrier in ``branch-cleanup.md`` asks the
:mod:`review_completeness` predicate that question, but the barrier is a step body
a run can skip. ``merge`` therefore asks it too, with the roster read from the
execution manifest's ``plan-marshall:automatic-review`` step params —
:func:`_check_participation` runs the provider producer and then the very
predicate the barrier runs, over the very roster it runs it with. A gap is refused
as :data:`MERGE_PARTICIPATION_UNPROVEN` unless a HEAD-bound authorization over
:data:`REVIEW_BARRIER_GAP_CLASS` covers it, in which case the merge proceeds and
the payload names the kind that was relied on, so the step record can say so.
**A state nobody could READ is never authorizable** — the refusal carries an
``authorizable`` discriminator, and only a KNOWN gap with named bots reaches the
grant lookup. An EMPTY roster is never read as a pass either: the verdict states
whether the roster was READ, and a roster nobody could read is a refusal rather
than a vacuous quorum.

Two further subcommands keep the merge path's WORDING in this script rather than
in an agent's hands:

* ``record-merge`` writes the ``branch-cleanup`` step record. A merge that
  proceeded past a reported gap renders :data:`GAP_RECORDED_TEMPLATE`; a clean
  merge renders the clause composition of :data:`CLEAN_MERGE_TEMPLATE`. Both are
  bounded by :data:`MERGE_DISPLAY_DETAIL_MAX_CHARS`.
* ``consequence-text`` renders the pre-enqueue option sentence from the
  ``final_merge_without_asking`` knob's value, so every merge-path question says
  truthfully whether a second question follows.

Exit code is ``0`` on every outcome above; the verdict travels in the TOON.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:pre_merge_gate \\
      merge --plan-id {plan_id} --pr-number {pr_number} --route {route} \\
      --project-dir {worktree_path} [--strategy S] [--delete-branch] [--admin-merge-on-stuck-state]

The findings check and the merge runner are injectable seams so the go/no-go
logic is testable without a findings store, an executor, or a CI provider.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _handshake_commands import cmd_findings_check
from file_ops import get_executor_path
from toon_parser import parse_toon, serialize_toon

#: The phase whose blocking-findings invariant gates the merge.
FINDINGS_PHASE = '6-finalize'

#: The closed set of merge verbs this gate may dispatch, as ``--route`` values.
#: ``ci pr merge`` and ``ci pr auto-merge`` are deliberately absent: they are not
#: reachable from ``branch-cleanup`` under any condition.
ROUTES: tuple[str, ...] = ('safe-merge', 'merge-queue')

#: The ``--strategy`` values ``ci pr safe-merge`` accepts.
STRATEGIES: tuple[str, ...] = ('squash', 'merge', 'rebase')

#: The payload field that marks a refusal by its category rather than its code.
REFUSAL_CATEGORY_FIELD = 'refusal_category'

#: The :data:`REFUSAL_CATEGORY_FIELD` value every invocation refusal carries — the
#: invocation was malformed and was refused before the findings store was read.
INVOCATION_REFUSAL = 'invocation'

_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'
_MANAGE_STATUS_NOTATION = 'plan-marshall:manage-status:manage-status'
_MANIFEST_NOTATION = 'plan-marshall:manage-execution-manifest:manage-execution-manifest'
_COMPLETENESS_NOTATION = 'plan-marshall:automatic-review:review_completeness'

#: The phase whose step records carry gate heads.
HEAD_BINDING_PHASE = '6-finalize'

#: Refusal code for a merge candidate a head-dependent gate record never saw.
MERGE_HEAD_NOT_GATED = 'merge_candidate_not_gated'

#: Refusal code for a merge candidate whose REQUIRED-bot participation is not
#: proven. One code for every participation refusal — an unproven bot, a roster
#: nobody could read, an empty roster, a producer that answered nothing — because
#: the payload's ``reason`` names which one it was and its ``authorizable``
#: discriminator decides the disposition: a KNOWN gap with named bots is what a
#: HEAD-bound authorization can cover, while a state nobody could READ is not
#: authorizable at all.
MERGE_PARTICIPATION_UNPROVEN = 'merge_participation_unproven'

#: The gap class the pre-merge review barrier reports, and the only class that
#: covers a participation gap. A recorded authorization over it admits the merge
#: and is thereafter named in the step record.
REVIEW_BARRIER_GAP_CLASS = 'review-barrier-gap'

#: The step whose param object carries the configured review-bot roster.
ROSTER_STEP_ID = 'plan-marshall:automatic-review'

#: The finalize step whose terminal record carries the merge wording.
MERGE_STEP_ID = 'branch-cleanup'

#: The declared ceiling on a ``--display-detail`` (``branch-cleanup.md``
#: § "Length discipline"). Both renderings below are checked against it here, so
#: an over-long rendering is refused at the write site rather than shipped.
MERGE_DISPLAY_DETAIL_MAX_CHARS = 80

#: The wording a merge that proceeded past a reported gap renders, as specified by
#: ``branch-cleanup.md`` Branch E. ``{kind}`` is the authorization kind actually
#: relied on.
GAP_RECORDED_TEMPLATE = 'merged under {kind}, gap recorded'

#: The wording a clean merge renders, as specified by ``branch-cleanup.md``
#: Branch A: a rebase clause, a merge clause, and the cleanup outcome.
CLEAN_MERGE_TEMPLATE = '{rebase_clause}, {merge_clause}, cleanup complete'

#: ``action`` -> rebase clause. ``None`` is the merge-queue path, which never
#: rebases, so its absence is the honest clause rather than a missing value.
REBASE_CLAUSES: dict[str | None, str] = {
    'rebased': 'rebased onto base',
    'noop': 'already current with base',
    None: 'rebase deferred to queue',
}

#: ``merge_mechanism`` -> merge clause. The queue clause deliberately does not say
#: "merged": the platform merged and this step corroborated the landing.
MERGE_CLAUSES: dict[str, str] = {
    'pr_safe_merge': 'merged directly',
    'merge_queue': 'queue-merged, corroborated',
}

#: The pre-enqueue sentence for ``final_merge_without_asking == true``: no further
#: question is asked about this answer. It deliberately does NOT claim the merge happens
#: the instant the option is chosen — other gates may still act on the tree (the review
#: barrier above all), so "no second question" is the fact this sentence owns.
MERGE_CONSEQUENCE_WITHOUT_ASKING = 'No second question follows: the merge is not confirmed again before it proceeds.'

#: The pre-enqueue sentence for ``final_merge_without_asking == false``: the
#: Pre-Merge Confirmation Gate asks again before anything merges.
MERGE_CONSEQUENCE_WITH_ASKING = 'A confirmation question follows: the PR is merged only after you confirm it.'

FindingsCheck = Callable[[str], dict[str, Any]]
MergeRunner = Callable[[list[str]], dict[str, Any]]
StatusReader = Callable[[str], dict[str, Any] | None]
HeadReader = Callable[[str], str | None]
ParticipationCheck = Callable[[str, int, str], dict[str, Any]]
AuthorizationCheck = Callable[[str, str], dict[str, Any]]
MarkDoneRunner = Callable[[list[str]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Seams (overridable in tests)
# ---------------------------------------------------------------------------


def _check_findings(plan_id: str) -> dict[str, Any]:
    """Evaluate the blocking-findings invariant for :data:`FINDINGS_PHASE`.

    Calls the ``phase_handshake findings-check`` handler in-process, so the
    verdict vocabulary is that verb's own.
    """
    return cmd_findings_check(argparse.Namespace(plan_id=plan_id, phase=FINDINGS_PHASE))


def _read_plan_status(plan_id: str) -> dict[str, Any] | None:
    """Return the plan's status payload, or ``None`` when it cannot be read.

    Goes through the executor (``manage-status read``) — the plan-context resolution
    is that skill's own, so a plan whose directory moved into its worktree is still
    found. ``None`` is the declared unknown, never an empty plan.
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        # ``get_executor_path`` raises when no plan root resolves; an unresolvable
        # executor is the declared unknown here, never a crash inside the gate.
        return None
    if executor is None:
        return None
    try:
        completed = subprocess.run(
            [sys.executable, str(executor), _MANAGE_STATUS_NOTATION, 'read', '--plan-id', plan_id],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if not (completed.stdout or '').strip():
        return None
    try:
        parsed = parse_toon(completed.stdout)
    except Exception:
        return None
    if parsed.get('status') != 'success':
        return None
    plan = parsed.get('plan')
    return plan if isinstance(plan, dict) else None


def _resolve_local_head(project_dir: str) -> str | None:
    """Return the local HEAD of ``project_dir``, or ``None`` when git cannot answer.

    The local HEAD IS the merge candidate on the immediate-merge route; the queue
    route merges the platform's merge commit, whose content is this tree. An
    unreadable HEAD is answered ``None`` and never as a mismatch.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', project_dir, 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    out = (completed.stdout or '').strip()
    return out.splitlines()[0].strip() if completed.returncode == 0 and out else None


def _head_binding_refusal(
    plan_id: str,
    project_dir: str,
    *,
    status_reader: StatusReader | None = None,
    head_reader: HeadReader | None = None,
) -> dict[str, Any] | None:
    """Refuse a merge candidate that any head-dependent gate record did not see.

    MEMBERSHIP IS DERIVED FROM THE RECORD, not listed here: a finalize step is
    head-dependent exactly when it persisted ``head_at_completion`` (the ext-point
    contract makes that field mandatory for such a step and meaningless for the
    others), so the field's PRESENCE is the population. A record with no SHA was
    never anchored to a tree and is not consulted — the dispatcher's own re-entry
    check owns that verdict.

    Three unknown answers pass rather than refuse, and none is a claim that the
    binding is sound: an unreadable plan status, an unreadable local HEAD, and a
    record set that carries no head at all. Each is named in the payload of a
    refusal only when an actual mismatch exists.

    The PLAN-LB-26 case this closes: gates stamped ``3db65fc05`` while the PR head
    merged was ``74e6bfda``. Nothing compared them, so the merge shipped a tree no
    gate had seen.
    """
    status = (status_reader or _read_plan_status)(plan_id)
    head = (head_reader or _resolve_local_head)(project_dir)
    if not head or not isinstance(status, dict):
        return None
    metadata = status.get('metadata')
    steps = metadata.get('phase_steps') if isinstance(metadata, dict) else None
    phase_steps = steps.get(HEAD_BINDING_PHASE) if isinstance(steps, dict) else None
    if not isinstance(phase_steps, dict):
        return None
    offending: list[dict[str, str]] = []
    for step_id in sorted(phase_steps):
        record = phase_steps[step_id]
        if not isinstance(record, dict):
            continue
        recorded = record.get('head_at_completion')
        if not recorded:
            continue
        recorded_sha = str(recorded).strip()
        if recorded_sha != head:
            offending.append({'step': step_id, 'recorded_head': recorded_sha, 'head': head})
    if not offending:
        return None
    return {
        'status': 'error',
        'error': MERGE_HEAD_NOT_GATED,
        'plan_id': plan_id,
        'phase': HEAD_BINDING_PHASE,
        'head': head,
        'steps': offending,
        'dispatched': False,
        'message': (
            'The merge candidate is not the HEAD the head-dependent gates validated '
            f'({", ".join(item["step"] for item in offending)}). Re-run those steps on '
            'the current tree. A merge authorization does NOT cover this gap: it '
            'authorizes a review or CI gap, never a tree the gates never examined.'
        ),
    }


#: The bound on every NON-merge verb this module runs. Generous for a provider fetch and
#: a store query, and deliberately finite: the participation chain runs while the
#: cross-plan merge mutex is held, so a network read that never returns would pin the
#: critical section indefinitely. The merge verb itself stays UNBOUNDED — it bounds its
#: own readiness poll (``--poll-timeout``) and a local timeout there would cut a
#: legitimate wait short.
_VERB_TIMEOUT_SECONDS = 300


def _run_verb(
    notation: str,
    argv: list[str],
    *,
    silent_error: str,
    unparseable_error: str,
    timeout: float | None = _VERB_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run one executor-mapped verb and return its parsed TOON.

    The single executor seam every cross-skill call in this module goes through, so
    the findings store, the roster, the provider producer, the participation
    predicate, the authorization check and the step-record write all reach their
    verb by the same route — never by a direct script path.

    Three failures are reported as error payloads under the caller's own code rather
    than as a verdict from the verb: output that was not produced, output that is not
    TOON, and a call that could not run at all (an unresolvable executor, a failed
    spawn, or a timeout). A silent provider is not a passing provider, and a traceback
    reaching the caller instead of a payload would leave it with no ``dispatched``
    field to branch on.
    """
    try:
        executor = get_executor_path()
        completed = subprocess.run(
            [sys.executable, str(executor), notation, *argv],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        return {
            'status': 'error',
            'error': silent_error,
            'message': f'{notation} could not run: {exc}',
        }
    stdout = completed.stdout or ''
    if not stdout.strip():
        return {
            'status': 'error',
            'error': silent_error,
            'message': (
                f'{notation} {" ".join(argv)} produced no output (exit_code={completed.returncode}): '
                f'{completed.stderr.strip() or "no stderr"}'
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {
            'status': 'error',
            'error': unparseable_error,
            'message': f'{notation} {" ".join(argv)} output not parseable as TOON: {exc}',
        }


def _run_ci(ci_args: list[str]) -> dict[str, Any]:
    """Run ``ci`` with ``ci_args`` through the executor and return its parsed TOON.

    UNBOUNDED on purpose: ``pr safe-merge`` bounds its own readiness poll
    (``--poll-timeout``), and ``pr merge-queue`` returns once the enqueue is issued, so a
    local timeout here could cut a legitimate wait short. A verb that produced no output
    is reported as an error payload rather than as a merge outcome.
    """
    return _run_verb(
        _CI_NOTATION,
        ci_args,
        silent_error='merge_verb_no_output',
        unparseable_error='merge_verb_unparseable',
        timeout=None,
    )


#: The ``marshal.json`` ``providers[]`` entry category this module resolves the
#: provider from — the same slot ``tools-integration-ci``'s router reads.
_PROVIDER_CATEGORY = 'ci'
_PROVIDER_SKILL_PREFIX = 'workflow-integration-'


def _find_marshal_path(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` (default: the current directory) to ``marshal.json``.

    Mirrors the CI router's own resolution — including its ROOT, which every caller
    here passes as the tree the merge is being dispatched for, so a dispatch whose
    cwd is elsewhere still resolves the project's own provider rather than another
    checkout's. A project configured for GitLab resolves GitLab.
    """
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / '.plan' / 'marshal.json'
        if candidate.is_file():
            return candidate
    return None


def _provider_pr_notation(project_dir: str | None = None) -> str | None:
    """Return the configured CI provider's PR-producer notation, or ``None``.

    The provider key is DERIVED from the ``category: ci`` entry's ``skill_name``
    (the same derivation the CI router applies), so a project on another provider
    reaches its own producer instead of this one's. ``None`` means the provider
    could not be resolved at all — a refusal reason, never a default.
    """
    start = Path(project_dir) if project_dir else None
    marshal_path = _find_marshal_path(start)
    if marshal_path is None:
        return None
    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    providers = config.get('providers') if isinstance(config, dict) else None
    for entry in providers or []:
        if not isinstance(entry, dict) or entry.get('category') != _PROVIDER_CATEGORY:
            continue
        skill_name = str(entry.get('skill_name') or '')
        name = skill_name.split(':')[-1]
        if not name.startswith(_PROVIDER_SKILL_PREFIX):
            continue
        provider = name[len(_PROVIDER_SKILL_PREFIX) :]
        if provider:
            return f'plan-marshall:{_PROVIDER_SKILL_PREFIX}{provider}:{provider}_pr'
    return None


def _pairs(records: Any, value_key: str) -> list[str]:
    """Render ``[{bot_kind, <value_key>}, …]`` records as ``bot:value`` pairs.

    The producer emits participation as records; :mod:`review_completeness` consumes
    them as ``bot_kind:value`` pair tokens. This is the one conversion site, so the
    two shapes cannot drift apart silently on one flag while agreeing on another.
    """
    rendered: list[str] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        bot = str(record.get('bot_kind') or '').strip()
        value = str(record.get(value_key) or '').strip()
        if bot and value:
            rendered.append(f'{bot}:{value}')
    return rendered


def _bot_kinds(records: Any) -> list[str]:
    """Render a bot-record list (or a bare token list) as bot kinds."""
    kinds: list[str] = []
    for record in records or []:
        if isinstance(record, dict):
            bot = str(record.get('bot_kind') or '').strip()
        else:
            bot = str(record).strip()
        if bot:
            kinds.append(bot)
    return kinds


def _roster_runner(plan_id: str) -> dict[str, Any]:
    """The step-params read the shared roster contract is computed from.

    Kept as the module's own ``_run_verb`` seam (rather than the shared reader's
    subprocess fallback) so a caller that stubs this module's executor seam stubs the
    roster read too — one seam, and the shared reader owns the parsing and the
    unreadable/empty distinction.
    """
    return _run_verb(
        _MANIFEST_NOTATION,
        [
            'step-params',
            'get',
            '--plan-id',
            plan_id,
            '--phase',
            HEAD_BINDING_PHASE,
            '--step-id',
            ROSTER_STEP_ID,
        ],
        silent_error='roster_unreadable',
        unparseable_error='roster_unreadable',
    )


def _read_roster(plan_id: str) -> dict[str, Any]:
    """Read the configured review-bot roster, through the ONE fail-closed reader.

    ``review_completeness.read_roster`` owns the read (and the unreadable-vs-empty
    distinction); this function only adapts its record to the shape the participation
    chain consumes. Two readers of the same step params would be two sources of truth
    for one contract, and they would eventually disagree about what an empty roster
    means — the exact conflation the distinction exists to remove.

    ``{'read': True, 'required_bots': [...], 'optional_bots': [...]}`` when the
    snapshot was read, ``{'read': False, 'reason': …}`` otherwise. ``read`` says
    whether the CONFIGURATION could be observed at all, which is a different question
    from what it says: a read roster configuring no REQUIRED bot is answered
    ``read: True`` with an empty list, and :func:`_check_participation` decides what to
    do with that (it refuses it — nobody decided the empty quorum).
    """
    import review_completeness

    record = review_completeness.read_roster(plan_id, runner=_roster_runner)
    if record.get('status') != 'success':
        return {
            'read': False,
            'reason': record.get('reason')
            or f'the configured review-bot roster could not be read from the {ROSTER_STEP_ID} step params',
        }
    return {
        'read': True,
        'required_bots': record.get('required_bots') or [],
        'optional_bots': record.get('optional_bots') or [],
    }


def _check_participation(plan_id: str, pr_number: int, project_dir: str) -> dict[str, Any]:
    """Ask the barrier's own participation predicate about the merge candidate.

    The chain is the barrier's, run in-process instead of by a step body: read the
    configured roster, re-run the provider producer against the current head, then
    feed the producer's observations to ``review_completeness check`` under that
    roster. Both sites therefore apply one predicate over one roster, so they cannot
    disagree about what participation MEANS; two overlays differ deliberately and are
    named in ``branch-cleanup.md`` — the dispatch passes ``--triage-ran``, and it
    supplies no ``not_triggered`` / ``declined`` overlay because those are read from
    verbs it does not call. Every failure in the chain is an error verdict carrying a
    ``reason``, never a pass and never a ``0``:

    * an unreadable roster, and a roster that was read but configures no REQUIRED
      bot — an empty roster is a decision nobody made, and reading it as a vacuous
      quorum is exactly the silent pass this gate exists to remove;
    * an unresolved provider, and a producer that failed or that could not resolve
      the merge candidate (``merge_candidate_sha_resolved`` is not ``true``) — the
      question was not answered;
    * a producer return carrying no participation arm at all, which is the provider
      capability gap rather than a clean run;
    * a predicate that did not answer.

    ``--triage-ran`` is passed unconditionally: this runs at the merge dispatch, by
    which point triage has run, so a still-pending required finding is a real
    incompleteness rather than the awaiting-triage state of the FIND-only step.
    """
    roster = _read_roster(plan_id)
    if not roster['read']:
        return {'status': 'error', 'error': 'roster_unreadable', 'roster_read': False, 'reason': roster['reason']}
    required = roster['required_bots']
    optional = roster['optional_bots']
    if not required:
        return {
            'status': 'error',
            'error': 'roster_empty',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                f'the {ROSTER_STEP_ID} roster was read and configures no REQUIRED reviewer, so '
                'there is no participation quorum to prove — an empty roster is not a pass'
            ),
        }

    notation = _provider_pr_notation(project_dir)
    if notation is None:
        return {
            'status': 'error',
            'error': 'provider_unresolved',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': 'no CI provider could be resolved from marshal.json providers[], so the review-bot participation could not be read',
        }

    fetched = _run_verb(
        notation,
        [
            # The routing flags precede the verb: the executor's router resolves the
            # plan's worktree from a PRE-verb ``--plan-id``, which is what makes the
            # producer read the tree being merged rather than whatever checkout the
            # dispatch process happens to sit in. The post-verb copy is the producer's
            # own argument.
            '--plan-id',
            plan_id,
            'fetch_findings',
            '--pr-number',
            str(pr_number),
            '--plan-id',
            plan_id,
            *(['--required-bots', ','.join(required)] if required else []),
            *(['--optional-bots', ','.join(optional)] if optional else []),
        ],
        silent_error='participation_unreadable',
        unparseable_error='participation_unreadable',
    )
    if fetched.get('status') != 'success':
        return {
            'status': 'error',
            'error': 'participation_unreadable',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                f'the provider producer did not answer ({fetched.get("error") or "unknown"}); '
                'an unread participation state is not a pass'
            ),
        }
    if 'participated_bots' not in fetched:
        return {
            'status': 'error',
            'error': 'participation_arm_unavailable',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                'the provider producer returned no participation arm, so no required bot could be '
                'proven a participant on this head'
            ),
        }
    if fetched.get('fetch_complete') is not True:
        # A CAPPED connection makes the producer's observation sets partial: a required bot
        # whose review sat in the truncated page appears in NO participation list, so the
        # predicate would classify it ``absent`` and this gate would read that as a KNOWN,
        # authorizable gap. An incomplete fetch is not an observation, so it is UNKNOWN —
        # the same class as a silent producer, never a gap somebody can rule past.
        return {
            'status': 'error',
            'error': 'participation_unreadable',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                'the provider producer returned an INCOMPLETE fetch (fetch_complete is not true), so its '
                'participation sets are partial and an omitted bot would read as absent'
            ),
        }
    if fetched.get('merge_candidate_sha_resolved') is not True:
        return {
            'status': 'error',
            'error': 'participation_unreadable',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                'the provider producer could not resolve the merge candidate, so its participation '
                'observations are about no tree'
            ),
        }

    argv = [
        'check',
        '--plan-id',
        plan_id,
        '--required-bots',
        ','.join(required),
    ]
    if optional:
        argv += ['--optional-bots', ','.join(optional)]
    participated = _pairs(fetched.get('participated_bots'), 'evidence_kind')
    if participated:
        argv += ['--participated-bots', ','.join(participated)]
    stale = _pairs(fetched.get('stale_participation_bots'), 'evidence_kind')
    if stale:
        argv += ['--stale-participation-bots', ','.join(stale)]
    refused = _bot_kinds(fetched.get('refused_bots'))
    if refused:
        argv += ['--refused-bots', ','.join(refused)]
    unrecognised = _bot_kinds(fetched.get('unrecognised_refusal'))
    if unrecognised:
        argv += ['--unrecognised-refusal-bots', ','.join(unrecognised)]
    causes = _pairs(fetched.get('refused_causes'), 'cause')
    if causes:
        argv += ['--refused-causes', ','.join(causes)]
    caps = _pairs(fetched.get('refused_size_caps'), 'cap')
    if caps:
        argv += ['--refusal-size-caps', ','.join(caps)]
    argv.append('--triage-ran')

    checked = _run_verb(
        _COMPLETENESS_NOTATION,
        argv,
        silent_error='predicate_unreadable',
        unparseable_error='predicate_unreadable',
    )
    if checked.get('status') != 'success':
        return {
            'status': 'error',
            'error': 'predicate_unreadable',
            'roster_read': True,
            'required_bots': required,
            'optional_bots': optional,
            'reason': (
                f'the participation predicate did not answer ({checked.get("error") or "unknown"}); '
                'an unknown verdict is never a pass'
            ),
        }
    return {
        'status': 'success',
        'participation_complete': checked.get('participation_complete') is True,
        'roster_read': True,
        'required_bots': required,
        'optional_bots': optional,
        'unproven_bots': list(checked.get('unproven_bots') or []),
        'bot_states': list(checked.get('bot_states') or []),
        'proves': checked.get('proves'),
        # The predicate can answer ``participation_complete: false`` with every bot a
        # proofed participant — that is a required finding still ``pending`` once triage
        # has run (see ``review_completeness``). Name it here, so a refusal built from
        # this verdict never reports "no reason" beside an empty ``unproven_bots``.
        'reason': _incomplete_reason(checked),
    }


def _incomplete_reason(checked: dict[str, Any]) -> str | None:
    """Describe WHY the predicate did not prove participation, or ``None`` when it did."""
    if checked.get('participation_complete') is True:
        return None
    unproven = [str(bot) for bot in (checked.get('unproven_bots') or [])]
    if unproven:
        return (
            'the predicate leaves '
            + ('one required reviewer' if len(unproven) == 1 else f'{len(unproven)} required reviewers')
            + ' unproven'
        )
    return (
        'the predicate reports an incomplete required review with no unproven reviewer: a required '
        'finding is still pending after triage'
    )


def _read_merge_authorization(plan_id: str, head: str) -> dict[str, Any]:
    """Read the HEAD-bound authorizations admissible at ``head`` for the barrier gap."""
    return _run_verb(
        _MANAGE_STATUS_NOTATION,
        [
            'merge-authorization',
            'check',
            '--plan-id',
            plan_id,
            '--head',
            head,
            '--gap-class',
            REVIEW_BARRIER_GAP_CLASS,
        ],
        silent_error='authorization_unreadable',
        unparseable_error='authorization_unreadable',
    )


def _participation_verdict(
    plan_id: str,
    pr_number: int,
    project_dir: str,
    *,
    head: str | None,
    participation_check: ParticipationCheck | None = None,
    authorization_check: AuthorizationCheck | None = None,
) -> dict[str, Any]:
    """Decide whether the merge may proceed past the participation gate.

    Returns ``{'allowed': bool, …}``. ``allowed`` is true in exactly two cases, and
    the two are recorded differently because they are different facts:

    * the predicate proved participation — ``authorization_kind`` is ``None``;
    * the predicate REPORTED A GAP and a HEAD-bound authorization over
      :data:`REVIEW_BARRIER_GAP_CLASS` is admissible at ``head`` — then
      ``authorization_kind`` names the kind relied on, which is what the step record
      renders.

    The second case is reachable only from a KNOWN gap with bot states. An UNKNOWN —
    an unreadable roster, an empty roster, an unresolved provider, a producer that did
    not answer or could not resolve the candidate, a predicate that did not answer — is
    ``authorizable: False`` and is refused with no grant consulted at all. That
    asymmetry is the spec's standing constraint and the doc's own rule: an authorization
    covers a review gap somebody can name, never a state nobody could read. Reading the
    two alike is exactly the fail-open this gate exists to remove — a single grant
    recorded earlier for another purpose would otherwise admit a merge with zero
    participation proof.

    The operator's standing ruling — a quota-limited required bot whose qualifying
    review of this head is on record — needs no grant and lands in the FIRST case:
    ``review_completeness`` classifies current-head participation ABOVE an observed
    refusal, so such a bot resolves ``participated`` / ``participated_but_empty``,
    while a bot that never reviewed anything resolves ``absent`` and a bot whose
    review predates this head resolves ``participated_stale``. Both of the latter
    are members of the predicate's unproven set and are refused here.
    """
    verdict = (participation_check or _check_participation)(plan_id, pr_number, project_dir)
    if verdict.get('status') == 'success' and verdict.get('participation_complete') is True:
        return {
            'allowed': True,
            'roster_read': True,
            'participation_complete': True,
            'unproven_bots': [],
            'bot_states': list(verdict.get('bot_states') or []),
            'required_bots': list(verdict.get('required_bots') or []),
            'authorization_kind': None,
            'authorizable': False,
            'code': None,
            'detail': None,
            'authorization': None,
        }

    # The refusal's machine code and its human detail are kept apart on purpose: the
    # code names WHICH participation question went unanswered, the detail says what was
    # seen, and a caller can route on the first without parsing the second.
    known_gap = verdict.get('status') == 'success'
    code = 'participation_unproven' if known_gap else str(verdict.get('error') or 'participation_unreadable')
    detail = verdict.get('reason')

    authorization: dict[str, Any] | None = None
    authorization_kind: str | None = None
    if known_gap and head:
        authorization = (authorization_check or _read_merge_authorization)(plan_id, head)
        kinds = [str(kind) for kind in (authorization.get('admissible_kinds') or [])]
        if authorization.get('status') == 'success' and authorization.get('any_admissible') is True and kinds:
            authorization_kind = kinds[0]

    return {
        'allowed': authorization_kind is not None,
        'roster_read': bool(verdict.get('roster_read')),
        'participation_complete': False,
        'unproven_bots': list(verdict.get('unproven_bots') or []),
        'bot_states': list(verdict.get('bot_states') or []),
        'required_bots': list(verdict.get('required_bots') or []),
        'authorization_kind': authorization_kind,
        'authorizable': known_gap,
        'code': code,
        'detail': detail,
        'authorization': authorization,
    }


def _participation_refusal(plan_id: str, head: str | None, verdict: dict[str, Any]) -> dict[str, Any]:
    """Render the refusal for a participation gap that no authorization covers.

    The payload states whether the ROSTER WAS READ separately from whether the bots
    participated, so "nobody could read the roster" and "the roster was read and
    these bots did not review" are distinguishable by a caller and by an operator. It
    also states ``authorizable``: a KNOWN gap with named bots is where a HEAD-bound
    authorization can apply, and an UNKNOWN is not — the remedy for that one is to make
    the participation state readable, never to rule past it.
    """
    unproven = verdict['unproven_bots']
    detail = verdict.get('detail') or 'no reason was reported'
    authorizable = bool(verdict.get('authorizable'))
    remedy = (
        f'A required reviewer is never demoted, and the only ruling that covers its silence is a '
        f'recorded HEAD-bound merge authorization over {REVIEW_BARRIER_GAP_CLASS}.'
        if authorizable
        else 'No merge authorization covers this: a participation state nobody could read is not a '
        'review gap, so the gate must be made readable (roster, provider, producer, or predicate) '
        'before this merge can proceed.'
    )
    payload: dict[str, Any] = {
        'status': 'error',
        'error': MERGE_PARTICIPATION_UNPROVEN,
        'plan_id': plan_id,
        'phase': FINDINGS_PHASE,
        'head': head,
        'reason': verdict['code'],
        'authorizable': authorizable,
        'roster_read': verdict['roster_read'],
        'required_bots': verdict['required_bots'],
        'unproven_bots': unproven,
        'bot_states': verdict['bot_states'],
        'dispatched': False,
        'message': (
            'Required review-bot participation is not proven on the merge candidate'
            + (f' ({", ".join(unproven)})' if unproven else '')
            + f'. {detail}. Refusing to merge; {remedy}'
        ),
    }
    authorization = verdict.get('authorization')
    if isinstance(authorization, dict):
        payload['authorization'] = {
            'gap_class': REVIEW_BARRIER_GAP_CLASS,
            'any_authorized': authorization.get('any_authorized'),
            'any_admissible': authorization.get('any_admissible'),
            'authorized_kinds': list(authorization.get('authorized_kinds') or []),
            'inadmissible_kinds': list(authorization.get('inadmissible_kinds') or []),
            'lapsed_kinds': list(authorization.get('lapsed_kinds') or []),
        }
    elif head is None:
        payload['authorization'] = {
            'gap_class': REVIEW_BARRIER_GAP_CLASS,
            'checked': False,
            'reason': 'the merge candidate HEAD could not be resolved, so no HEAD-bound authorization could be read',
        }
    return payload


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def build_merge_args(
    route: str,
    *,
    project_dir: str,
    pr_number: int,
    strategy: str | None = None,
    delete_branch: bool = False,
    admin_merge_on_stuck_state: bool = False,
) -> list[str]:
    """Return the ``ci`` argument vector for ``route``.

    ``--project-dir`` is the router-level flag and precedes the ``pr`` verb.
    The safe-merge pass-through flags are forwarded on the ``safe-merge`` route
    only; the ``merge-queue`` enqueue takes the PR number alone.
    """
    args = ['--project-dir', project_dir, 'pr', route, '--pr-number', str(pr_number)]
    if route == 'safe-merge':
        args += ['--strategy', str(strategy)]
        if delete_branch:
            args.append('--delete-branch')
        if admin_merge_on_stuck_state:
            args.append('--admin-merge-on-stuck-state')
    return args


def merge_step_detail(kind: str | None) -> str:
    """Render the ``branch-cleanup`` step detail for the merge that landed.

    ``branch-cleanup.md`` Branch E specifies the gap-bearing form and Branch A the
    clean one; this function is what makes each happen, so the wording is not
    retyped by an agent on the way past. ``kind`` is the authorization kind actually
    relied on — ``None`` renders the clean form, and a set value always renders the
    gap-bearing form, so the two cannot be produced for one call. WHICH one a run asks
    for is decided by the merge result (``merge_authorization_kind``); this function
    renders the answer, it does not choose it.
    """
    if kind is None:
        return ''
    token = str(kind).strip()
    if not token:
        raise ValueError('an authorization kind, when supplied, must be a non-empty token')
    if not all(' ' <= character <= '~' for character in token):
        raise ValueError(
            f'the authorization kind {token!r} is not printable ASCII, so the fixed-width record cannot hold it'
        )
    return GAP_RECORDED_TEMPLATE.format(kind=token)


def clean_merge_step_detail(action: str | None, merge_mechanism: str) -> str:
    """Render the clean-merge step detail from the facts the run actually recorded.

    Both axes are rendered as CLAUSES rather than interpolated raw: a raw
    ``merged via {merge_mechanism}`` reads as "this step merged it via the queue" and
    so claims for the queue path a merge this step never performed. An absent
    ``action`` is the merge-queue path, which never rebases — its clause says so
    rather than fabricating a rebase.
    """
    if action not in REBASE_CLAUSES:
        raise ValueError(f'--action must be one of rebased/noop or absent, got {action!r}')
    clause = MERGE_CLAUSES.get(str(merge_mechanism))
    if clause is None:
        raise ValueError(f'--merge-mechanism must be one of {sorted(MERGE_CLAUSES)}, got {merge_mechanism!r}')
    return CLEAN_MERGE_TEMPLATE.format(rebase_clause=REBASE_CLAUSES[action], merge_clause=clause)


def merge_consequence_text(final_merge_without_asking: bool) -> str:
    """Render the pre-enqueue sentence for the ``final_merge_without_asking`` value.

    The knob decides whether the question being asked is followed by ANOTHER one, so
    the option text has to say which it is. Generating it here — rather than
    authoring one sentence per call site — is what stops a site from rendering the
    text the other value would contradict.
    """
    return MERGE_CONSEQUENCE_WITHOUT_ASKING if final_merge_without_asking else MERGE_CONSEQUENCE_WITH_ASKING


def _checked_detail(detail: str) -> str:
    """Return ``detail`` or refuse it as over the declared ceiling.

    Measured on the RENDERED string, never on a template: the bound in
    ``branch-cleanup.md`` § "Length discipline" is a property of what is written to
    the step record.
    """
    if not detail:
        raise ValueError('the rendered step detail is empty')
    if len(detail) > MERGE_DISPLAY_DETAIL_MAX_CHARS:
        raise ValueError(
            f'the rendered step detail is {len(detail)} characters, over the '
            f'{MERGE_DISPLAY_DETAIL_MAX_CHARS}-character bound: {detail!r}'
        )
    return detail


#: The facts a ``branch-cleanup`` landed-merge record MUST carry. The verb refuses a
#: record missing any of them: a landed merge that does not say how it landed, that it
#: merged, and whether cleanup is owed is exactly the prose-only record the structured
#: facts replaced.
_REQUIRED_MERGE_FACTS: tuple[str, ...] = ('merge_mechanism', 'merge_state', 'cleanup_owed', 'work_performed')


def build_record_merge_args(
    *,
    plan_id: str,
    display_detail: str,
    facts: list[str],
    head_at_completion: str | None = None,
) -> list[str]:
    """Return the ``manage-status mark-step-done`` argument vector for Branch A/E.

    The FACT set is the caller's — this verb records the honest subset the branch
    observed, and does not invent one — while the DISPLAY DETAIL is derived here from
    those same facts. That split is the whole point of Branch A/E: the rendering is a
    function of what was recorded, so it cannot assert a rebase or a merge the record
    does not support.
    """
    args = [
        'mark-step-done',
        '--plan-id',
        plan_id,
        '--phase',
        HEAD_BINDING_PHASE,
        '--step',
        MERGE_STEP_ID,
        '--outcome',
        'done',
    ]
    for fact in facts:
        args += ['--fact', fact]
    args += ['--display-detail', display_detail]
    if head_at_completion:
        args += ['--head-at-completion', head_at_completion]
    return args


def _mark_step_done(argv: list[str]) -> dict[str, Any]:
    """Write the step record through the executor — the production mark-done seam."""
    return _run_verb(
        _MANAGE_STATUS_NOTATION,
        argv,
        silent_error='step_record_not_written',
        unparseable_error='step_record_not_written',
    )


def _fact_map(facts: list[str]) -> dict[str, str]:
    """Parse ``KEY=VALUE`` fact tokens into a map, refusing a malformed one."""
    parsed: dict[str, str] = {}
    for fact in facts:
        key, separator, value = str(fact).partition('=')
        if not separator or not key.strip():
            raise ValueError(f'--fact expects KEY=VALUE, got {fact!r}')
        parsed[key.strip()] = value.strip()
    return parsed


def record_merge(
    plan_id: str,
    *,
    facts: list[str],
    grant_kind: str | None = None,
    head_at_completion: str | None = None,
    mark_done_runner: MarkDoneRunner | None = None,
) -> dict[str, Any]:
    """Write the ``branch-cleanup`` step record, wording included.

    A merge that proceeded past a reported gap MUST say so: Branch E replaces
    Branch A on exactly those paths, because Branch A's rendering describes an
    ordinary rebase-and-merge and reads like a passed gate. This function is the
    mechanism behind that rule — the doc keeps the specification, the script
    produces the string from the facts it was handed.

    Refusals are invocation-shaped (``refusal_category: invocation``): a malformed fact,
    a record missing ``merge_mechanism`` / ``merge_state`` / ``cleanup_owed`` /
    ``work_performed``, a ``merge_state`` other than ``merged``, an unknown mechanism or
    action (so no clause exists), an action contradicting its route — a queue record
    carrying one, or a direct record omitting the rebase facts every direct route
    observes — and an over-long rendering. Every rule binds BOTH renderings, so a
    granted record cannot smuggle in a fact the clean one would reject. Nothing is
    written in any of them.
    """

    def _refuse(error: str, message: str) -> dict[str, Any]:
        return {
            'status': 'error',
            'error': error,
            REFUSAL_CATEGORY_FIELD: INVOCATION_REFUSAL,
            'plan_id': plan_id,
            'step': MERGE_STEP_ID,
            'message': message,
        }

    try:
        recorded = _fact_map(facts)
    except ValueError as exc:
        return _refuse('facts_malformed', str(exc))

    missing = [key for key in _REQUIRED_MERGE_FACTS if key not in recorded]
    if missing:
        return _refuse(
            'facts_incomplete',
            f'a landed-merge record must carry {", ".join(_REQUIRED_MERGE_FACTS)}; missing {", ".join(missing)}',
        )
    if recorded['merge_state'] != 'merged':
        return _refuse(
            'merge_state_not_landed',
            f'this verb records a LANDED merge, so merge_state must be merged; got {recorded["merge_state"]!r}',
        )
    # The VALUES, not only the keys: this verb records a landed merge whose cleanup is
    # complete, so a payload asserting otherwise would write a record that contradicts
    # itself (and whose clean wording claims a cleanup the facts deny). The doc fixes both
    # values at this site; enforcing them here is what makes that a mechanism.
    if recorded['cleanup_owed'] != 'false':
        return _refuse(
            'cleanup_owed_not_cleared',
            f'a landed-merge record for this step has its cleanup complete, so cleanup_owed must be '
            f'false; got {recorded["cleanup_owed"]!r}',
        )
    if recorded['work_performed'] != 'true':
        return _refuse(
            'work_performed_not_recorded',
            f'a landed-merge record did perform its work, so work_performed must be true; '
            f'got {recorded["work_performed"]!r}',
        )

    merge_mechanism = recorded['merge_mechanism']
    action = recorded.get('action')
    # Route/action coherence is checked for BOTH renderings: the facts a branch asks to
    # be recorded must be able to be true whichever wording it selects, so Branch E is
    # not exempt from them.
    if action is not None and merge_mechanism == 'merge_queue':
        return _refuse(
            'action_on_queue_route',
            'the merge-queue route never rebases, so an action fact would record a rebase this '
            'path cannot have performed',
        )
    if action is None and merge_mechanism == 'pr_safe_merge':
        # The mirror case, and the one that used to render a FALSE clause: a direct merge
        # always reached the rebase (the default path and the ``queue_wait: forbidden``
        # reroute alike), so an absent action would claim "rebase deferred to queue" on a
        # path that never enqueued. Refuse rather than narrate a rebase that did not
        # happen.
        return _refuse(
            'action_required_on_direct_route',
            'a direct merge reached the rebase, so its record must carry the action and '
            'upstream_commit_count facts it observed',
        )
    if action is not None and 'upstream_commit_count' not in recorded:
        return _refuse(
            'upstream_count_required_with_action',
            'a recorded rebase action must carry the upstream_commit_count read from the same payload',
        )

    try:
        # The vocabulary is validated for BOTH renderings: an unknown mechanism or action
        # names no clause, so a granted record carrying one would be written unexamined.
        clean_detail = clean_merge_step_detail(action, merge_mechanism)
        display_detail = _checked_detail(merge_step_detail(grant_kind) if grant_kind is not None else clean_detail)
    except ValueError as exc:
        return _refuse('display_detail_invalid', str(exc))

    args = build_record_merge_args(
        plan_id=plan_id,
        display_detail=display_detail,
        facts=list(facts),
        head_at_completion=head_at_completion,
    )
    payload = (mark_done_runner or _mark_step_done)(args)
    return {**payload, 'display_detail': display_detail, 'merge_authorization_kind': grant_kind}


def _invocation_refusal(
    plan_id: str,
    route: str,
    *,
    strategy: str | None,
    delete_branch: bool,
    admin_merge_on_stuck_state: bool,
) -> dict[str, Any] | None:
    """Refuse an invocation whose flags do not fit its route, before any check runs.

    Every refusal is built by one constructor that stamps
    ``refusal_category: invocation``, so any refusal code this function gains
    carries the category without its consumers having to name the new code.
    """

    def _refuse(error: str, message: str) -> dict[str, Any]:
        return {
            'status': 'error',
            'error': error,
            REFUSAL_CATEGORY_FIELD: INVOCATION_REFUSAL,
            'plan_id': plan_id,
            'route': route,
            'dispatched': False,
            'message': message,
        }

    if route not in ROUTES:
        return _refuse('unknown_route', f'--route must be one of {list(ROUTES)}, got {route!r}')
    if route == 'safe-merge' and not strategy:
        return _refuse(
            'strategy_required',
            'the safe-merge route requires --strategy; nothing was checked and nothing was merged',
        )
    if route == 'merge-queue' and (strategy or delete_branch or admin_merge_on_stuck_state):
        return _refuse(
            'flag_not_applicable_to_route',
            '--strategy, --delete-branch and --admin-merge-on-stuck-state apply to the safe-merge '
            'route only; the merge-queue enqueue takes the PR number alone and the platform owns '
            'the merge method and the head-branch deletion. Nothing was checked and nothing was merged',
        )
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _findings_refusal(plan_id: str, findings_check: FindingsCheck | None) -> dict[str, Any] | None:
    """Return the refusal for a store that is not proven clean, or ``None``.

    One evaluator for both readings the dispatch performs — before the participation
    chain and again after it — so the two can never grade the same store differently.
    """
    verdict = (findings_check or _check_findings)(plan_id)
    if verdict.get('status') != 'success':
        # blocking_findings_present, query_failed, or any other refusal the
        # verdict source returns: the payload travels verbatim, nothing merges.
        # The invocation category is never forwarded — the store WAS read here.
        store_refusal = {k: v for k, v in verdict.items() if k != REFUSAL_CATEGORY_FIELD}
        return {**store_refusal, 'dispatched': False}
    if verdict.get('blocking_count') != 0:
        # A success envelope that does not carry a measured zero is not a clean
        # store. Fail closed rather than read an absent count as zero.
        return {
            'status': 'error',
            'error': 'findings_verdict_unrecognised',
            'plan_id': plan_id,
            'phase': FINDINGS_PHASE,
            'blocking_count': verdict.get('blocking_count'),
            'dispatched': False,
            'message': (
                'findings-check returned status: success without blocking_count: 0, so the store '
                'was not proven clean; refusing to merge'
            ),
        }
    return None


def merge(
    plan_id: str,
    *,
    route: str,
    pr_number: int,
    project_dir: str,
    strategy: str | None = None,
    delete_branch: bool = False,
    admin_merge_on_stuck_state: bool = False,
    findings_check: FindingsCheck | None = None,
    merge_runner: MergeRunner | None = None,
    status_reader: StatusReader | None = None,
    head_reader: HeadReader | None = None,
    participation_check: ParticipationCheck | None = None,
    authorization_check: AuthorizationCheck | None = None,
) -> dict[str, Any]:
    """Issue the routed merge verb only when every pre-merge invariant is proven.

    Args:
        plan_id: Plan whose ``6-finalize`` findings store is evaluated. Not
            forwarded to the CI router.
        route: ``safe-merge`` or ``merge-queue`` (see :data:`ROUTES`).
        pr_number: PR to merge or enqueue.
        project_dir: Working tree the ``ci`` router binds to.
        strategy: ``safe-merge`` strategy; required on that route only.
        delete_branch: ``safe-merge`` pass-through.
        admin_merge_on_stuck_state: ``safe-merge`` pass-through.
        findings_check: Optional seam in place of :func:`_check_findings`.
            Signature: ``(plan_id) -> dict``.
        merge_runner: Optional seam in place of :func:`_run_ci`. Signature:
            ``(ci_args) -> dict``.
        participation_check: Optional seam in place of :func:`_check_participation`.
            Signature: ``(plan_id, pr_number) -> dict``.
        authorization_check: Optional seam in place of
            :func:`_read_merge_authorization`. Signature:
            ``(plan_id, head) -> dict``.

    Returns:
        The refusal payload plus ``dispatched: false``, or the routed verb's
        payload plus ``findings_gate: clean``, ``participation_gate`` (``complete``
        or ``authorized``) and ``dispatched: true``.
    """
    refusal = _invocation_refusal(
        plan_id,
        route,
        strategy=strategy,
        delete_branch=delete_branch,
        admin_merge_on_stuck_state=admin_merge_on_stuck_state,
    )
    if refusal is not None:
        return refusal

    refusal_from_store = _findings_refusal(plan_id, findings_check)
    if refusal_from_store is not None:
        return refusal_from_store

    # Head binding: the merge candidate must be the tree the head-dependent gates
    # validated. Runs before the participation gate because it is the cheaper verdict,
    # so a tree the gates never saw is named without paying for a provider read.
    #
    # The HEAD is resolved ONCE here and handed to the head-binding check through a
    # constant reader, because the participation gate below needs the same SHA for
    # its HEAD-bound authorization lookup: two independent resolutions could read two
    # different trees on a branch that moves between them, and an authorization
    # checked against a different tree than the one bound is exactly the unbound
    # consent the HEAD binding exists to remove.
    head = (head_reader or _resolve_local_head)(project_dir)
    head_refusal = _head_binding_refusal(
        plan_id,
        project_dir,
        status_reader=status_reader,
        head_reader=lambda _project_dir: head,
    )
    if head_refusal is not None:
        return head_refusal

    # Participation: a clean store says nothing about whether a required reviewer
    # ever saw this tree. The barrier asks that question too, but a run that skips
    # the barrier step skips it — so the merge dispatch asks it itself.
    participation = _participation_verdict(
        plan_id,
        pr_number,
        project_dir,
        head=head,
        participation_check=participation_check,
        authorization_check=authorization_check,
    )
    if not participation['allowed']:
        return _participation_refusal(plan_id, head, participation)

    # ⚠ The participation chain RUNS THE PROVIDER PRODUCER, and that producer files
    # ``pr-comment`` findings for comments it has not seen before. A comment that
    # landed between the store gate above and this read is therefore now IN the store,
    # and the gate that ran first never saw it. Re-read the store here, so the merge
    # dispatch remains the latest point a pending finding can stop the merge: without
    # this second read the producer would quietly widen the window the gate exists to
    # close. The read is a local store query, not a second provider call.
    refusal_after_participation = _findings_refusal(plan_id, findings_check)
    if refusal_after_participation is not None:
        return refusal_after_participation

    ci_args = build_merge_args(
        route,
        project_dir=project_dir,
        pr_number=pr_number,
        strategy=strategy,
        delete_branch=delete_branch,
        admin_merge_on_stuck_state=admin_merge_on_stuck_state,
    )
    payload = (merge_runner or _run_ci)(ci_args)
    result: dict[str, Any] = {
        **payload,
        'findings_gate': 'clean',
        'participation_gate': 'complete' if participation['authorization_kind'] is None else 'authorized',
        'dispatched': True,
    }
    if participation['authorization_kind'] is not None:
        result['merge_authorization_kind'] = participation['authorization_kind']
        result['merge_authorization_gap'] = REVIEW_BARRIER_GAP_CLASS
        result['unproven_bots'] = participation['unproven_bots']
    return result


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_merge(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`merge` — emits TOON and exits 0 on every outcome."""
    result = merge(
        args.plan_id,
        route=args.route,
        pr_number=args.pr_number,
        project_dir=args.project_dir,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        admin_merge_on_stuck_state=args.admin_merge_on_stuck_state,
    )
    print(serialize_toon(result))
    return 0


def cmd_record_merge(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`record_merge` — emits TOON and exits 0 on every outcome."""
    result = record_merge(
        args.plan_id,
        facts=list(args.facts or []),
        grant_kind=args.grant_kind,
        head_at_completion=args.head_at_completion,
    )
    print(serialize_toon(result))
    return 0


def cmd_consequence_text(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`merge_consequence_text` — emits the sentence as TOON."""
    final_merge_without_asking = args.final_merge_without_asking == 'true'
    print(
        serialize_toon(
            {
                'status': 'success',
                'final_merge_without_asking': final_merge_without_asking,
                'text': merge_consequence_text(final_merge_without_asking),
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with the merge-dispatch subcommands."""
    parser = argparse.ArgumentParser(
        description=(
            'Evaluate the 6-finalize blocking-findings, head-binding and required-bot '
            'participation invariants and, only when all three are proven, issue the routed '
            'merge verb (ci pr safe-merge or ci pr merge-queue). Also renders and writes the '
            'merge path wording the pre-merge questions and the step record carry.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)
    merge_parser = sub.add_parser(
        'merge',
        help='Gate the merge dispatch on a clean store, a gated head and proven participation',
        allow_abbrev=False,
    )
    merge_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    merge_parser.add_argument('--pr-number', required=True, type=int, dest='pr_number', help='PR number')
    merge_parser.add_argument(
        '--route',
        required=True,
        choices=ROUTES,
        help='Merge verb to dispatch on a clean store: safe-merge (immediate) or merge-queue (enqueue)',
    )
    merge_parser.add_argument(
        '--project-dir',
        required=True,
        dest='project_dir',
        help='Working tree the ci router binds to (forwarded as the router-level --project-dir)',
    )
    merge_parser.add_argument(
        '--strategy',
        choices=STRATEGIES,
        default=None,
        help='safe-merge route only (required there): merge strategy forwarded to ci pr safe-merge',
    )
    merge_parser.add_argument(
        '--delete-branch',
        action='store_true',
        dest='delete_branch',
        help='safe-merge route only: forwarded to ci pr safe-merge',
    )
    merge_parser.add_argument(
        '--admin-merge-on-stuck-state',
        action='store_true',
        dest='admin_merge_on_stuck_state',
        help='safe-merge route only: forwarded to ci pr safe-merge',
    )
    merge_parser.set_defaults(func=cmd_merge)

    record_parser = sub.add_parser(
        'record-merge',
        help='Write the branch-cleanup step record, naming an authorization when one was relied on',
        allow_abbrev=False,
    )
    record_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    record_parser.add_argument(
        '--fact',
        action='append',
        default=None,
        dest='facts',
        metavar='KEY=VALUE',
        help='A structured step fact to record, repeatable; the mandatory set is '
        'merge_mechanism / merge_state / cleanup_owed / work_performed',
    )
    record_parser.add_argument(
        '--grant-kind',
        default=None,
        dest='grant_kind',
        help='The merge authorization kind actually relied on; renders the gap-bearing detail',
    )
    record_parser.add_argument(
        '--head-at-completion',
        default=None,
        dest='head_at_completion',
        help='Forwarded to mark-step-done; omitted when this step is not head-dependent',
    )
    record_parser.set_defaults(func=cmd_record_merge)

    consequence_parser = sub.add_parser(
        'consequence-text',
        help='Render the pre-enqueue option sentence from the final_merge_without_asking knob',
        allow_abbrev=False,
    )
    consequence_parser.add_argument(
        '--final-merge-without-asking',
        required=True,
        choices=['true', 'false'],
        dest='final_merge_without_asking',
        help='The resolved final_merge_without_asking value the sentence must describe',
    )
    consequence_parser.set_defaults(func=cmd_consequence_text)
    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'CLEAN_MERGE_TEMPLATE',
    'FINDINGS_PHASE',
    'GAP_RECORDED_TEMPLATE',
    'INVOCATION_REFUSAL',
    'MERGE_CONSEQUENCE_WITHOUT_ASKING',
    'MERGE_CONSEQUENCE_WITH_ASKING',
    'MERGE_DISPLAY_DETAIL_MAX_CHARS',
    'MERGE_PARTICIPATION_UNPROVEN',
    'REFUSAL_CATEGORY_FIELD',
    'REVIEW_BARRIER_GAP_CLASS',
    'ROUTES',
    'STRATEGIES',
    'build_merge_args',
    'build_record_merge_args',
    'clean_merge_step_detail',
    'merge',
    'merge_consequence_text',
    'merge_step_detail',
    'record_merge',
]
