#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provider-agnostic CI router.

Resolves the CI provider by scanning providers[] in marshal.json for
category=ci and deriving the provider key from skill_name. Delegates to the
matching provider script ({provider}_ops.py). All arguments are passed through.

Usage:
    python3 ci.py [--project-dir PATH] pr create --title "Title" --plan-id EXAMPLE-PLAN
    python3 ci.py [--project-dir PATH] pr view
    python3 ci.py [--project-dir PATH] ci status --pr-number 123
    python3 ci.py [--project-dir PATH] issue create --title "Bug" --plan-id EXAMPLE-PLAN
    python3 ci.py [--plan-id ID] org list-repos --org cuioss
    python3 ci.py [--plan-id ID] repo file read --repo cuioss/example --path .github/project.yml

The ``org`` verbs and ``repo file read`` / ``repo label list`` are read-only and
can reach repositories other than the routed checkout: the ``org`` verbs and
``repo file read`` name their target explicitly (``--org`` / ``--repo``), while
``repo label list`` takes an optional ``--repo`` and defaults to the routed
checkout. They take no verb-level ``--plan-id``: a
``--plan-id`` for them is the router flag and goes BEFORE the verb.

Top-level flags (consumed by the router before provider dispatch):
    --project-dir PATH   Run every gh/glab subprocess with ``cwd=PATH``. Required
                         when invoking from a checkout whose HEAD is not the
                         branch the caller wants to operate on — e.g., phase-6-finalize
                         finalize running from the main checkout against a
                         worktree-isolated plan branch. When omitted, subprocesses
                         inherit the Python process cwd (current behaviour).

Provider-agnostic verbs (handled by the router, no provider dispatch):
    barrier              Concurrent finalize-wait barrier coordinator —
                         per-signal-proceed + bounded re-settle over the
                         {CI, review, sonar} signals off one settled HEAD.
                         Pure computation; needs no CI provider and no worktree
                         resolution. See ``_ci_barrier.py`` and
                         ``phase-6-finalize/SKILL.md`` § "Wait-region".

The provider is determined automatically from marshal.json configuration.
This eliminates the need for eval or jq in skill instructions.

Output: TOON format (from provider script)
"""

import importlib
import sys
from pathlib import Path

from ci_base import (
    BODY_CONSUMER_VERBS,
    extract_project_dir,
    extract_routing_args,
    output_error,
    resolve_ci_provider,
    safe_main,
    set_default_cwd,
)
from command_forms import STEWARD_COMMAND

# ``extract_project_dir`` is kept as a re-export for backward compatibility
# with tests and external callers that imported it from ``ci`` directly.
# New code should prefer ``extract_routing_args`` which also consumes
# ``--plan-id`` and enforces the two-state contract.
__all__ = ['extract_project_dir', 'extract_routing_args']


def get_provider() -> str | None:
    """Find CI provider from marshal.json.

    Scans providers[] for the entry with category=ci and derives the provider
    key from its skill_name. The resolution itself lives in
    :func:`ci_base.resolve_ci_provider`, so this router and every consumer that must
    know the provider before reading (the runbook lane's review gate included) read
    ONE implementation rather than a copy each.
    """
    return resolve_ci_provider(Path.cwd())


def _router_plan_id_value(argv: list[str]) -> str | None:
    """Return the first ``--plan-id`` value in ``argv``, or ``None``.

    Reads both ``--plan-id VALUE`` and ``--plan-id=VALUE`` spellings. Used to
    recover the router-consumed value when a body-consumer verb declares its
    own required ``--plan-id`` after the verb: the router strips the pre-verb
    occurrence for worktree resolution, leaving the subparser reporting it
    missing. Re-injecting the recovered value after the verb makes the
    router position work instead of rejecting with a misleading missing-flag
    error.
    """
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == '--plan-id':
            if i + 1 < len(argv) and not argv[i + 1].startswith('-'):
                return argv[i + 1]
            return None
        if token.startswith('--plan-id='):
            value = token.split('=', 1)[1]
            return value or None
        i += 1
    return None


# Verbs that declare their own required ``--plan-id`` after the verb (body
# consumers). When the router consumed a pre-verb ``--plan-id`` and the
# remaining argv carries one of these verbs without its own ``--plan-id``,
# the consumed value is re-injected so the router position is accepted.
# Imported from `ci_base` beside `add_body_consumer_args` so the reinjection
# set cannot drift from the parser registrations it mirrors.
_BODY_CONSUMER_VERBS = BODY_CONSUMER_VERBS


def main() -> int:
    # Provider-agnostic barrier coordinator — intercepted BEFORE provider
    # routing because it computes over caller-supplied signal state and needs
    # no CI provider, no worktree resolution, and no gh/glab subprocess. Keeping
    # it ahead of extract_routing_args also keeps it usable when no CI provider
    # is configured (the barrier is a pure state machine, not a provider call).
    argv = sys.argv[1:]
    if argv and argv[0] == 'barrier':
        from _ci_barrier import run_barrier_cli

        return run_barrier_cli(argv[1:])

    # Remember the router-position ``--plan-id`` before it is stripped, so a
    # body-consumer verb that declares its own required ``--plan-id`` can be
    # re-injected below instead of reporting a misleading missing-flag error.
    router_plan_id = _router_plan_id_value(argv)
    # Consume top-level router flags (--project-dir and --plan-id) before
    # delegating to the provider module. sys.argv is rewritten in place so the
    # downstream provider parser sees only its own arguments. The two flags
    # implement the two-state contract: --plan-id auto-resolves via
    # manage-status; --project-dir is the explicit override; both together
    # is a hard error (handled inside extract_routing_args).
    project_dir, remaining = extract_routing_args(argv)
    # Forward the router-consumed ``--plan-id`` to body-consumer verbs that
    # declare their own: a pre-verb ``--plan-id`` was swallowed for worktree
    # resolution and the subparser would otherwise report it missing even
    # though the caller supplied it. Appending the recovered value makes the
    # router position accepted consistently across read and body-consumer verbs.
    if (
        router_plan_id is not None
        and not any(t == '--plan-id' or t.startswith('--plan-id=') for t in remaining)
        and any(v in remaining for v in _BODY_CONSUMER_VERBS)
    ):
        remaining = [*remaining, '--plan-id', router_plan_id]
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    provider = get_provider()
    if not provider:
        return output_error('router', f'CI provider not configured. Run {STEWARD_COMMAND} first.')

    # Dynamic import via executor PYTHONPATH — provider scripts use
    # {provider}_ops.py naming convention to avoid module collisions
    module_name = f'{provider}_ops'
    try:
        provider_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return output_error('router', f'No provider module found: {module_name}')

    return provider_module.main()  # type: ignore[no-any-return]


if __name__ == '__main__':
    safe_main(main)()
