#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Forward `--plan-id` to Bucket B executor invocations.

This helper rewrites `python3 .plan/execute-script.py {notation} run ...`
commands so that Bucket B notations (build / CI / Sonar / PR-doctor) always
carry `--plan-id {plan_id}` when a plan runs in an isolated git worktree.
Injecting `--plan-id` (rather than `--project-dir {worktree_path}`) lets the
Bucket B script auto-resolve the worktree path itself via its
`--plan-id`/`--project-dir` two-state contract.

Bucket A `manage-*` notations are cwd-agnostic and are returned unchanged, as
are non-executor commands, any command that already contains `--plan-id` (no
double injection), and any command that already contains `--project-dir` (a
legacy explicit override is respected untouched).

See `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the
authoritative Bucket A/B split.

Usage (programmatic)::

    from inject_project_dir import inject_project_dir

    rewritten, injected = inject_project_dir(command, plan_id)

Usage (CLI)::

    python3 inject_project_dir.py run \\
        --command "python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args 'module-tests'" \\
        --plan-id my-plan-id
"""

import argparse
import shlex
import sys

from toon_parser import serialize_toon

_BUCKET_B_NOTATIONS: frozenset[str] = frozenset(
    {
        'plan-marshall:build-maven:maven',
        'plan-marshall:build-gradle:gradle',
        'plan-marshall:build-npm:npm',
        'plan-marshall:build-pyproject:pyproject_build',
        'plan-marshall:tools-integration-ci:ci',
        'plan-marshall:workflow-integration-git:git',
        'plan-marshall:workflow-integration-sonar:sonar',
        'plan-marshall:workflow-pr-doctor:pr-doctor',
    }
)

_EXECUTOR_MARKERS: tuple[str, ...] = (
    '.plan/execute-script.py',
    'execute-script.py',
)

_PROJECT_DIR_FLAG: str = '--project-dir'
_PLAN_ID_FLAG: str = '--plan-id'


def _find_notation_index(tokens: list[str]) -> int | None:
    """Return the index of the {notation} token in an execute-script argv.

    The executor is invoked as::

        python3 .plan/execute-script.py {notation} run ...

    so the notation lives immediately after the executor path token. Returns
    ``None`` when the command does not invoke the executor (e.g., ``./pw``
    calls, direct ``pytest`` calls, or any command without
    ``.plan/execute-script.py``).
    """
    for index, token in enumerate(tokens):
        if any(token.endswith(marker) for marker in _EXECUTOR_MARKERS):
            notation_index = index + 1
            if notation_index < len(tokens):
                return notation_index
            return None
    return None


def inject_project_dir(command: str, plan_id: str) -> tuple[str, bool]:
    """Forward --plan-id to Bucket B execute-script invocations.

    The function name is retained as the stable module entry point — it is the
    ``inject_project_dir`` notation referenced by ``execute-task`` and the
    executor mappings. Despite the legacy name, the current contract injects
    ``--plan-id`` (NOT ``--project-dir``); see the module docstring above for
    why plan-id forwarding replaced the former worktree-path injection.

    Args:
        command: The original shell command string to inspect and possibly
            rewrite. Parsed with :func:`shlex.split`.
        plan_id: Plan identifier inserted verbatim as the value for
            ``--plan-id`` when injection applies. The Bucket B script resolves
            the worktree path itself from this flag via its two-state contract.

    Returns:
        A tuple ``(rewritten_command, injected)``. ``injected`` is ``True``
        only when the command was actually modified. Bucket A ``manage-*``
        notations, non-Bucket-B notations, non-executor commands, any
        command that already contains ``--project-dir`` (legacy explicit
        override respected), and any command that already contains
        ``--plan-id`` (no double injection) return the original command
        string unchanged with ``injected=False``.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        # Unparseable quoting — pass through untouched rather than corrupt.
        return command, False

    if not tokens:
        return command, False

    notation_index = _find_notation_index(tokens)
    if notation_index is None:
        return command, False

    notation = tokens[notation_index]
    if notation not in _BUCKET_B_NOTATIONS:
        return command, False

    # A command that already carries an explicit --project-dir is a legacy
    # override; respect it untouched rather than layering --plan-id on top
    # (the two are mutually exclusive on the target script).
    if _PROJECT_DIR_FLAG in tokens or any(t.startswith(f'{_PROJECT_DIR_FLAG}=') for t in tokens):
        return command, False

    # No-double-injection guard: a command that already supplies --plan-id is
    # returned unchanged — the target script's two-state contract already
    # resolves the worktree path itself.
    if _PLAN_ID_FLAG in tokens or any(t.startswith(f'{_PLAN_ID_FLAG}=') for t in tokens):
        return command, False

    # Executor contract: `{notation} run ...`. Only inject when `run` appears
    # immediately after the notation; other subcommands (e.g., help) are
    # out-of-scope for plan-id forwarding.
    run_index = notation_index + 1
    if run_index >= len(tokens) or tokens[run_index] != 'run':
        return command, False

    # Insert `--plan-id {plan_id}` immediately after `run`.
    rewritten_tokens = tokens[: run_index + 1] + [_PLAN_ID_FLAG, plan_id] + tokens[run_index + 1 :]
    return shlex.join(rewritten_tokens), True


#: Refusal code emitted when a Bucket-B invocation is attempted while the
#: worktree flag is unset and ``use_worktree`` is true. The flag is persisted
#: by ``prepare_execute``; this seam is a read-only guard. No script gate
#: binds a free agent's Edit tool — the refusal lives here, paired with
#: detection docs naming that residual.
WORKTREE_NOT_MATERIALIZED = 'worktree_not_materialized'


def is_bucket_b_notation(notation: str) -> bool:
    """Return True when ``notation`` is a Bucket-B executor invocation."""
    return notation in _BUCKET_B_NOTATIONS


def refusal_needed(notation: str, *, use_worktree: bool, worktree_materialized: bool | None) -> bool:
    """Return True when the invocation must be refused.

    Refusal fires exactly when the notation is Bucket-B, the plan runs with
    ``use_worktree`` true, and the materialized flag is explicitly False. An
    unknown flag (``None``) never refuses — the guard is fail-open on unknown
    so pre-flag callers keep their current behaviour; only an explicit unset
    refuses.
    """
    return bool(use_worktree) and worktree_materialized is False and is_bucket_b_notation(notation)


def guarded_inject(
    command: str,
    plan_id: str,
    *,
    use_worktree: bool = True,
    worktree_materialized: bool | None = None,
) -> dict[str, object]:
    """Inject with the worktree-materialized admission check applied.

    Returns a TOON-shaped payload: ``status: success`` carrying
    ``injected``/``rewritten_command`` on the pass path, or ``status: error``
    with ``error: worktree_not_materialized`` on the refusal path. The pure
    :func:`inject_project_dir` above is unchanged and stays the injection
    primitive; this wrapper is the dispatch/invocation seam phase-5 calls.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {'status': 'success', 'injected': False, 'rewritten_command': command}
    notation_index = _find_notation_index(tokens)
    notation = tokens[notation_index] if notation_index is not None else ''
    if refusal_needed(notation, use_worktree=use_worktree, worktree_materialized=worktree_materialized):
        return {
            'status': 'error',
            'error': WORKTREE_NOT_MATERIALIZED,
            'plan_id': plan_id,
            'message': (
                f'Bucket-B invocation refused for plan {plan_id}: worktree not materialized '
                '(use_worktree=true while worktree_materialized is unset). '
                'Materialize via prepare_execute before dispatch.'
            ),
        }
    rewritten, injected = inject_project_dir(command, plan_id)
    return {'status': 'success', 'injected': injected, 'rewritten_command': rewritten}


def cmd_run(args: argparse.Namespace) -> int:
    """CLI wrapper: rewrite a single command and print structured TOON output.

    Output contract (TOON):

    * ``status`` — ``success`` on the pass path, ``error`` with
      ``error: worktree_not_materialized`` on the refusal path.
    * ``injected`` — boolean; ``true`` only when the command was actually
      rewritten (pass path only).
    * ``rewritten_command`` — the (possibly unchanged) command string the
      caller should execute (pass path only).

    Callers parse the TOON and drive conditional logging off ``injected``.
    Exit code is ``0`` on success. The optional ``--worktree-materialized``
    flag carries the prepare_execute-persisted state: ``true``/``false``;
    omitted means unknown and preserves the pre-flag behaviour.
    """
    materialized: bool | None = None
    raw = getattr(args, 'worktree_materialized', None)
    if raw == 'true':
        materialized = True
    elif raw == 'false':
        materialized = False
    result = guarded_inject(
        args.command,
        args.plan_id,
        use_worktree=getattr(args, 'use_worktree', True),
        worktree_materialized=materialized,
    )
    print(serialize_toon(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single `run` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Forward --plan-id to Bucket B execute-script invocations. '
            'Leaves Bucket A and non-executor commands unchanged.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command_name', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Rewrite a single command and print the result to stdout',
        allow_abbrev=False,
    )
    run_parser.add_argument(
        '--command',
        required=True,
        help='The original shell command string to inspect and possibly rewrite',
    )
    run_parser.add_argument(
        '--plan-id',
        required=True,
        dest='plan_id',
        help='Plan identifier injected as the value for --plan-id',
    )
    run_parser.add_argument(
        '--use-worktree',
        dest='use_worktree',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Whether the plan runs with use_worktree=true (default: true)',
    )
    run_parser.add_argument(
        '--worktree-materialized',
        dest='worktree_materialized',
        choices=('true', 'false'),
        default=None,
        help='prepare_execute-persisted materialization state; omitted means unknown (no refusal)',
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())
