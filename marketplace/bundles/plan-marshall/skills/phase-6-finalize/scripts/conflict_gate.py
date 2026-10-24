#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Conflict-severity gate for ``default:branch-cleanup``: the question, and what it authorizes.

The Conflict-Severity Classifier already answers *how bad is the rebase*. What it
never decided is what the step DOES with that answer — and the gap was observed:
a run whose classifier reported ``overlap_with_content_conflict … needs_user``
told the operator "No rebase or force-push will happen — the merge queue rebases
and re-tests", then asked them to wait for a queue the PR could not enter. The
conflict surfaced much later and was hand-resolved, rebased and force-pushed
without a second question. Two untruths rode one prompt: the question did not
state the conflict it was asking about, and its answer authorized nothing while
the work happened anyway.

This script makes both mechanical. It is the ONLY composer of the pre-rebase
gate question, and it owns the authorization vocabulary the push consults:

``gate``
    Decide the gate from the classifier verdict and render the prompt. A
    ``needs_user`` verdict produces a question that NAMES the conflicting files
    and the base, and forbids the merge-queue wait outright
    (``queue_wait: forbidden``): on the content-conflict path a queue wait asks
    the operator to wait for something that cannot rebase their conflict, which
    is precisely the prompt that was answered "yes" while the rebase happened
    elsewhere. A content-conflict verdict with no conflicting files to name is
    refused (``conflict_files_required``) — a question that cannot state the
    conflict is not the question this gate exists to produce.

``push-authorization``
    Decide whether a rebase or a force-push is authorized by the option the
    operator actually selected. Authorization comes from the OPTION, never from a
    truthy answer: each option declares the actions its own label names, and an
    answer that resolves to no gate option, or to one that does not name the
    requested action, is refused. A free-text "ok" therefore authorizes nothing.
    The pre-push quality gate then runs on the rebased head before the push.

Return shape (CLI emits TOON; programmatic callers consume the dict directly)::

    status: success
    decision: auto_proceed | needs_user
    question_required: true | false
    state: open | merged
    base: <base branch>
    use_merge_queue: true | false
    threshold: <auto_rebase_threshold value>
    classification: <classifier verdict>
    conflicting_files[N]: [<repo-relative paths>]
    plan_actions[N]: [rebase | force-push | ci-wait | ci-snapshot | local-cleanup]
    queue_wait: permitted | forbidden
    prompt_header: <AskUserQuestion header>            # question_required only
    prompt_question: <one-line question>               # question_required only
    prompt_description: <BlockScalar body>             # question_required only
    options[N]{label,description,authorizes}: ...      # question_required only

``push-authorization`` returns::

    status: success
    action: rebase | force-push
    authorized: true
    matched_option: <the option label the answer resolved to>

and refuses with ``error: push_not_authorized`` (or ``unknown_action`` /
``invalid_answer``) carrying ``authorized: false`` and, where one resolved,
``matched_option`` plus ``option_authorizes[]`` — so the refusal names what the
answer DID authorize rather than only what it did not.

Exit code is ``0`` on every verdict; the verdict travels in the TOON.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:conflict_gate \\
      gate --classification overlap_with_content_conflict --decision needs_user \\
      --conflicts "src/a.py,tests/test_a.py" --base main --threshold no_overlap_only \\
      --use-merge-queue false --state open

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:conflict_gate \\
      push-authorization --answer "Rebase and force-push, resolving the conflicts" --action force-push
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from input_validation import add_boolean_arg
from toon_parser import BlockScalar, serialize_toon

#: The classifier's closed verdict vocabulary (``baseline-reconcile``).
CLASSIFICATIONS: tuple[str, ...] = ('no_overlap', 'overlap_no_content_conflict', 'overlap_with_content_conflict')

#: The gate decision the classifier threshold produces.
DECISIONS: tuple[str, ...] = ('auto_proceed', 'needs_user')

#: The PR state the gate is asked about. ``merged`` has no rebase to prepare and
#: therefore no conflict to route.
STATES: tuple[str, ...] = ('open', 'merged')

#: The verdict that forces a question: a genuine content conflict.
CONTENT_CONFLICT = 'overlap_with_content_conflict'

#: The only decision that asks. ``auto_proceed`` bypasses the prompt.
NEEDS_USER = 'needs_user'

#: The actions an option can authorize, and the closed set this script decides.
AUTHORIZABLE_ACTIONS: tuple[str, ...] = ('rebase', 'force-push')

#: ``queue_wait`` values. ``forbidden`` means no merge-queue wait may follow this
#: gate; ``permitted`` means the run is on the ordinary auto-proceed route.
QUEUE_WAIT_PERMITTED = 'permitted'
QUEUE_WAIT_FORBIDDEN = 'forbidden'

# Error codes.
ERROR_INVALID_DECISION = 'invalid_decision'
ERROR_INVALID_CLASSIFICATION = 'invalid_classification'
ERROR_CONFLICT_FILES_REQUIRED = 'conflict_files_required'
ERROR_UNKNOWN_ACTION = 'unknown_action'
ERROR_INVALID_ANSWER = 'invalid_answer'
ERROR_PUSH_NOT_AUTHORIZED = 'push_not_authorized'

#: The label prefix every conflict-gate option carries. Prefix rather than a
#: bare token so the rendered option reads as an action, not as machine output.
_CONFLICT_HEADER = 'Branch Cleanup — Content conflict'
_MERGED_HEADER = 'Branch Cleanup — Local'

#: The option population for a ``needs_user`` content-conflict gate. Each entry
#: names exactly the actions its label names; ``authorizes`` is the machine half
#: of that correspondence and is what ``push-authorization`` reads.
_CONFLICT_OPTIONS: tuple[dict[str, Any], ...] = (
    {
        'label': 'Rebase and force-push, resolving the conflicts',
        'description': (
            'Rebases onto the base in the worktree, resolves the listed conflicting files, runs '
            'the pre-push quality gate on the rebased head, then force-pushes with lease. CI runs '
            'on the rebased head afterwards.'
        ),
        'authorizes': ['rebase', 'force-push'],
    },
    {
        'label': 'Resolve the conflicts myself, then re-run finalize',
        'description': (
            'Nothing is rebased or pushed now. The listed files are yours to resolve; re-run '
            'finalize afterwards and this gate asks again against the then-current base.'
        ),
        'authorizes': [],
    },
    {
        'label': 'Stop — leave the branch and PR as they stand',
        'description': (
            'No rebase, no push and no merge-queue wait. The branch, the pull request and your '
            'checkout are left exactly as they are.'
        ),
        'authorizes': [],
    },
)

#: The option population for the ``state == merged`` local-cleanup confirmation.
_MERGED_OPTIONS: tuple[dict[str, Any], ...] = (
    {
        'label': 'Yes, clean up the local branch',
        'description': 'Switches to the base branch, pulls latest, and deletes the merged local branch.',
        'authorizes': ['local-cleanup'],
    },
    {
        'label': 'No, skip',
        'description': 'Nothing is cleaned up. The branch and your checkout are left as they stand.',
        'authorizes': [],
    },
)

#: Why a queue wait is refused on the ``needs_user`` path. Rendered beside the
#: verdict so the refusal is explained, not merely stated.
_QUEUE_WAIT_FORBIDDEN_REASON = (
    'a merge-queue wait asks the operator to wait for a queue that cannot rebase a content '
    'conflict — the conflict is the operator\u2019s decision, so it is asked before any rebase, '
    'push or queue wait'
)

_WHITESPACE_RE = re.compile(r'\s+')


def _normalize_answer(answer: str) -> str:
    """Normalize an answer for label matching: case-folded, whitespace-collapsed.

    Labels reach the caller through a prompt UI, so an answer may differ in
    case or in the exact run of spaces. Nothing else is normalized: a paraphrase
    is NOT the option, and matching one would authorize an action the operator
    never selected.
    """
    return _WHITESPACE_RE.sub(' ', answer).strip().casefold()


def _options_for(state: str) -> tuple[dict[str, Any], ...]:
    """The option population for one gate state."""
    return _MERGED_OPTIONS if state == 'merged' else _CONFLICT_OPTIONS


def _planned_actions(use_merge_queue: bool, state: str) -> list[str]:
    """What the run would actually perform on the auto-proceed route.

    The two routes differ by design: the merge queue rebases and re-tests, so the
    local rebase and force-push are skipped and only a CI snapshot is taken; the
    immediate-merge route performs both. Local cleanup is uniform.
    """
    if state == 'merged':
        return ['local-cleanup']
    if use_merge_queue:
        return ['ci-snapshot', 'local-cleanup']
    return ['rebase', 'force-push', 'ci-wait', 'local-cleanup']


def _invalid(plan_id: str | None, error: str, message: str) -> dict[str, Any]:
    payload: dict[str, Any] = {'status': 'error', 'error': error, 'message': message}
    if plan_id:
        payload['plan_id'] = plan_id
    return payload


def _description_lines(
    state: str,
    base: str,
    conflicts: list[str],
    head_branch: str | None,
    pr_url: str | None,
) -> list[str]:
    """Compose the question's description, naming the conflict and its files."""
    lines: list[str] = []
    if pr_url:
        lines.append(f'**PR**: {pr_url}')
    if head_branch:
        lines.append(f'**Branch**: {head_branch} → {base}')
    else:
        lines.append(f'**Base**: {base}')
    if state == 'merged':
        lines.append('**PR state**: merged — there is nothing to merge; this confirms local cleanup only.')
        return lines
    if conflicts:
        lines.append(f'**Content conflict against {base}** ({len(conflicts)} file(s)):')
        lines.extend(f'  - {path}' for path in conflicts)
        lines.append('')
        lines.append(
            'These files cannot be merged mechanically. No rebase or force-push happens before you '
            'choose, and nothing is queued: the options below say exactly what each one does.'
        )
    else:
        lines.append('**Overlap against the base** — no content conflict was reported, but the')
        lines.append('rebase threshold asks before proceeding.')
    return lines


def evaluate_gate(
    classification: str,
    decision: str,
    conflicts: list[str],
    base: str,
    threshold: str,
    use_merge_queue: bool,
    state: str,
    head_branch: str | None = None,
    pr_url: str | None = None,
) -> dict[str, Any]:
    """Decide the pre-rebase gate and render its prompt.

    Pure over its inputs: the classifier verdict is supplied by the caller, so
    this function's decision is reproducible from the verdict alone and needs no
    git probe of its own.
    """
    if classification not in CLASSIFICATIONS:
        return _invalid(
            None,
            ERROR_INVALID_CLASSIFICATION,
            f'--classification must be one of {list(CLASSIFICATIONS)}, got: {classification!r}',
        )
    if decision not in DECISIONS:
        return _invalid(None, ERROR_INVALID_DECISION, f'--decision must be one of {list(DECISIONS)}, got: {decision!r}')
    if state not in STATES:
        return _invalid(None, ERROR_INVALID_DECISION, f'--state must be one of {list(STATES)}, got: {state!r}')

    question_required = state == 'merged' or decision == NEEDS_USER
    if question_required and state != 'merged' and classification == CONTENT_CONFLICT and not conflicts:
        return _invalid(
            None,
            ERROR_CONFLICT_FILES_REQUIRED,
            (
                'A content conflict forces a question that states the conflict, and no conflicting '
                'file was supplied. Pass --conflicts with the classifier\u2019s conflict list: a prompt '
                'that cannot name the files is the untruth this gate exists to remove.'
            ),
        )

    payload: dict[str, Any] = {
        'status': 'success',
        'decision': decision,
        'question_required': question_required,
        'state': state,
        'base': base,
        'use_merge_queue': use_merge_queue,
        'threshold': threshold,
        'classification': classification,
        'conflicting_files': conflicts,
    }

    if not question_required:
        payload['plan_actions'] = _planned_actions(use_merge_queue, state)
        payload['queue_wait'] = QUEUE_WAIT_PERMITTED
        return payload

    payload['plan_actions'] = []
    payload['queue_wait'] = QUEUE_WAIT_FORBIDDEN
    payload['queue_wait_reason'] = _QUEUE_WAIT_FORBIDDEN_REASON
    if state == 'merged':
        payload['prompt_header'] = _MERGED_HEADER
        payload['prompt_question'] = f'Clean up the local branch for the already-merged pull request? (based on {base})'
    elif classification == CONTENT_CONFLICT:
        payload['prompt_header'] = _CONFLICT_HEADER
        payload['prompt_question'] = f'Resolve the content conflict with {base} before proceeding?'
    else:
        payload['prompt_header'] = 'Branch Cleanup — Rebase'
        payload['prompt_question'] = f'Rebase onto {base} before proceeding? (the overlap threshold asks)'
    payload['prompt_description'] = BlockScalar(
        '\n'.join(_description_lines(state, base, conflicts, head_branch, pr_url))
    )
    payload['options'] = [dict(option) for option in _options_for(state)]
    return payload


def authorize_push(answer: str, action: str, state: str = 'open') -> dict[str, Any]:
    """Decide whether ``answer`` authorizes ``action``.

    The answer must resolve to a gate option, and that option's ``authorizes``
    list must contain the action. Both halves are required: an answer that
    matches no option is not a selection, and an option that does not name the
    action never authorized it — "stop" resolves to a real option and still
    authorizes no push.
    """
    if action not in AUTHORIZABLE_ACTIONS:
        return _invalid(
            None,
            ERROR_UNKNOWN_ACTION,
            f'--action must be one of {list(AUTHORIZABLE_ACTIONS)}, got: {action!r}',
        )
    if not answer or not answer.strip():
        return _invalid(
            None,
            ERROR_INVALID_ANSWER,
            '--answer is required: the authorization comes from the option the operator selected, not from a blank.',
        )

    normalized = _normalize_answer(answer)
    for option in _options_for(state):
        if _normalize_answer(str(option['label'])) != normalized:
            continue
        authorizes = list(option.get('authorizes') or [])
        if action in authorizes:
            return {
                'status': 'success',
                'action': action,
                'authorized': True,
                'matched_option': option['label'],
                'option_authorizes': authorizes,
            }
        return {
            'status': 'error',
            'error': ERROR_PUSH_NOT_AUTHORIZED,
            'action': action,
            'authorized': False,
            'matched_option': option['label'],
            'option_authorizes': authorizes,
            'message': (
                f'The selected option {option["label"]!r} authorizes {authorizes or "no action"} — not '
                f'{action!r}. Nothing is rebased or pushed on this answer: ask the question again and '
                'let the operator select an option that names the action.'
            ),
        }

    authorizing = [str(option['label']) for option in _options_for(state) if action in (option.get('authorizes') or [])]
    return {
        'status': 'error',
        'error': ERROR_PUSH_NOT_AUTHORIZED,
        'action': action,
        'authorized': False,
        'matched_option': None,
        'authorizing_options': authorizing,
        'message': (
            f'The answer {answer!r} resolves to no gate option, so it authorizes nothing. An '
            f'authorization for {action!r} is one of: {authorizing}. A free-text answer is not a '
            'selection and never authorizes a rebase or a push.'
        ),
    }


def _split_conflicts(raw: str | None) -> list[str]:
    """Split a comma-separated conflict list, dropping empty entries and duplicates."""
    if not raw:
        return []
    seen: dict[str, None] = {}
    for token in raw.split(','):
        path = token.strip()
        if path:
            seen.setdefault(path, None)
    return list(seen)


def cmd_gate(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`evaluate_gate` — emits TOON, always returns 0."""
    conflicts = _split_conflicts(args.conflicts)
    payload = evaluate_gate(
        classification=args.classification,
        decision=args.decision,
        conflicts=conflicts,
        base=args.base,
        threshold=args.threshold,
        use_merge_queue=bool(args.use_merge_queue),
        state=args.state,
        head_branch=args.head_branch,
        pr_url=args.pr_url,
    )
    if args.plan_id:
        payload['plan_id'] = args.plan_id
    print(serialize_toon(payload))
    return 0


def cmd_push_authorization(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`authorize_push` — emits TOON, always returns 0."""
    payload = authorize_push(answer=args.answer, action=args.action, state=args.state)
    if args.plan_id:
        payload['plan_id'] = args.plan_id
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the parser with the ``gate`` and ``push-authorization`` verbs."""
    parser = argparse.ArgumentParser(
        description=(
            'Compose the branch-cleanup pre-rebase gate question from the conflict classifier verdict, '
            'and decide whether an operator answer authorizes a rebase or a force-push. The gate '
            'always names the conflicting files and the base, and forbids a merge-queue wait on the '
            'needs_user path.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    gate_parser = sub.add_parser('gate', help='Decide the pre-rebase gate and render its prompt', allow_abbrev=False)
    gate_parser.add_argument('--plan-id', default=None, dest='plan_id', help='Plan identifier (echoed for the log).')
    gate_parser.add_argument(
        '--classification',
        required=True,
        help=f'The classifier verdict: {", ".join(CLASSIFICATIONS)}.',
    )
    gate_parser.add_argument(
        '--decision',
        required=True,
        help=f'The threshold-derived gate decision: {", ".join(DECISIONS)}.',
    )
    gate_parser.add_argument(
        '--conflicts',
        default=None,
        help='Comma-separated conflicting paths from the classifier. Required for a content conflict.',
    )
    gate_parser.add_argument('--base', required=True, help='The base branch the rebase targets.')
    gate_parser.add_argument(
        '--threshold',
        required=True,
        help='The auto_rebase_threshold value the decision was derived from (echoed).',
    )
    gate_parser.add_argument('--state', choices=list(STATES), default='open', help='PR state. Defaults to open.')
    gate_parser.add_argument('--head-branch', dest='head_branch', default=None, help='Head branch (rendered only).')
    gate_parser.add_argument('--pr-url', dest='pr_url', default=None, help='PR URL (rendered only).')
    add_boolean_arg(
        gate_parser,
        'use-merge-queue',
        help_text='The use_merge_queue param value. Defaults to false (the immediate-merge route).',
    )
    gate_parser.set_defaults(func=cmd_gate)

    push_parser = sub.add_parser(
        'push-authorization',
        help='Decide whether the operator answer authorizes a rebase or a force-push',
        allow_abbrev=False,
    )
    push_parser.add_argument('--plan-id', default=None, dest='plan_id', help='Plan identifier (echoed for the log).')
    push_parser.add_argument(
        '--answer',
        required=True,
        help='The option label the operator selected, as returned by the prompt.',
    )
    push_parser.add_argument(
        '--action',
        required=True,
        help=f'The action the run is about to take: {", ".join(AUTHORIZABLE_ACTIONS)}.',
    )
    push_parser.add_argument('--state', choices=list(STATES), default='open', help='PR state. Defaults to open.')
    push_parser.set_defaults(func=cmd_push_authorization)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'AUTHORIZABLE_ACTIONS',
    'CLASSIFICATIONS',
    'CONTENT_CONFLICT',
    'DECISIONS',
    'NEEDS_USER',
    'QUEUE_WAIT_FORBIDDEN',
    'QUEUE_WAIT_PERMITTED',
    'STATES',
    'authorize_push',
    'evaluate_gate',
]
