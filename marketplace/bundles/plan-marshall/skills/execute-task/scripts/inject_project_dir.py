#!/usr/bin/env python3
"""Forward `--plan-id` to Bucket B executor invocations.

This helper rewrites `python3 .plan/execute-script.py {notation} run ...`
commands so that Bucket B notations (build / CI / Sonar / PR-doctor) always
carry `--plan-id {plan_id}` when a plan runs in an isolated git worktree.
Injecting `--plan-id` (rather than `--project-dir {worktree_path}`) routes the
executor's two-tier audit-log entry to the plan-scoped
`.plan/local/plans/{plan_id}/logs/script-execution.log` — the log the
`pre-commit-verify-freshness` gate reads — and lets the Bucket B script
auto-resolve the worktree path itself via its `--plan-id`/`--project-dir`
two-state contract.

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

from toon_parser import serialize_toon  # type: ignore[import-not-found]

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
            the worktree path itself from this flag via its two-state contract,
            and the executor routes the audit-log entry to the plan-scoped log.

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


def cmd_run(args: argparse.Namespace) -> int:
    """CLI wrapper: rewrite a single command and print structured TOON output.

    Output contract (TOON):

    * ``status`` — always ``success`` on exit code 0.
    * ``injected`` — boolean; ``true`` only when the command was actually
      rewritten.
    * ``rewritten_command`` — the (possibly unchanged) command string the
      caller should execute.

    Callers parse the TOON and drive conditional logging off ``injected``.
    Exit code is ``0`` on success.
    """
    rewritten, injected = inject_project_dir(args.command, args.plan_id)
    print(
        serialize_toon(
            {
                'status': 'success',
                'injected': injected,
                'rewritten_command': rewritten,
            }
        )
    )
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
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())
