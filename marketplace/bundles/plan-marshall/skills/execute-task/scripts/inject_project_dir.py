#!/usr/bin/env python3
"""Forward `--project-dir` to Bucket B executor invocations.

This helper rewrites `python3 .plan/execute-script.py {notation} run ...`
commands so that Bucket B notations (build / CI / Sonar / PR-doctor) always
carry `--project-dir {worktree_path}` when a plan runs in an isolated git
worktree. Bucket A `manage-*` notations are cwd-agnostic and are returned
unchanged, as are non-executor commands and any command that already contains
`--project-dir`.

See `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the
authoritative Bucket A/B split.

Usage (programmatic)::

    from inject_project_dir import inject_project_dir

    rewritten, injected = inject_project_dir(command, worktree_path)

Usage (CLI)::

    python3 inject_project_dir.py run \\
        --command "python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args 'module-tests'" \\
        --worktree-path /path/to/worktree
"""

import argparse
import shlex
import sys

from toon_parser import serialize_toon  # type: ignore[import-not-found]

_BUCKET_B_NOTATIONS: frozenset[str] = frozenset(
    {
        "plan-marshall:build-maven:maven",
        "plan-marshall:build-gradle:gradle",
        "plan-marshall:build-npm:npm",
        "plan-marshall:build-python:python_build",
        "plan-marshall:tools-integration-ci:ci",
        "plan-marshall:workflow-integration-git:git",
        "plan-marshall:workflow-integration-sonar:sonar",
        "plan-marshall:workflow-pr-doctor:pr-doctor",
    }
)

_EXECUTOR_MARKERS: tuple[str, ...] = (
    ".plan/execute-script.py",
    "execute-script.py",
)

_PROJECT_DIR_FLAG: str = "--project-dir"


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


def inject_project_dir(command: str, worktree_path: str) -> tuple[str, bool]:
    """Forward --project-dir to Bucket B execute-script invocations.

    Args:
        command: The original shell command string to inspect and possibly
            rewrite. Parsed with :func:`shlex.split`.
        worktree_path: Absolute path to the active git worktree root. Inserted
            verbatim as the value for ``--project-dir`` when injection
            applies.

    Returns:
        A tuple ``(rewritten_command, injected)``. ``injected`` is ``True``
        only when the command was actually modified. Bucket A ``manage-*``
        notations, non-Bucket-B notations, non-executor commands, and any
        command that already contains ``--project-dir`` return the original
        command string unchanged with ``injected=False``.
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

    if _PROJECT_DIR_FLAG in tokens:
        return command, False

    # Executor contract: `{notation} run ...`. Only inject when `run` appears
    # immediately after the notation; other subcommands (e.g., help) are
    # out-of-scope for project-dir forwarding.
    run_index = notation_index + 1
    if run_index >= len(tokens) or tokens[run_index] != "run":
        return command, False

    # Insert `--project-dir {worktree_path}` immediately after `run`.
    rewritten_tokens = (
        tokens[: run_index + 1]
        + [_PROJECT_DIR_FLAG, worktree_path]
        + tokens[run_index + 1 :]
    )
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
    rewritten, injected = inject_project_dir(args.command, args.worktree_path)
    print(
        serialize_toon(
            {
                "status": "success",
                "injected": injected,
                "rewritten_command": rewritten,
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single `run` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            "Forward --project-dir to Bucket B execute-script invocations. "
            "Leaves Bucket A and non-executor commands unchanged."
        )
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Rewrite a single command and print the result to stdout",
    )
    run_parser.add_argument(
        "--command",
        required=True,
        help="The original shell command string to inspect and possibly rewrite",
    )
    run_parser.add_argument(
        "--worktree-path",
        required=True,
        dest="worktree_path",
        help="Absolute path to the active git worktree root",
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
