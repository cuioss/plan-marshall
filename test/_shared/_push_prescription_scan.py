# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared scan for `git push` PRESCRIPTIONS in a finalize-step document.

``default:push`` is a pure push barrier: it carries no commit logic, asserts a
clean tree, and ships the converged branch. A step ordered BELOW it that pushes
on its own pushes the same branch a second time, outside the single-push
contract the barrier exists to hold. Two independent suites need to know
whether a step doc prescribes such a push — the ``architecture-refresh``
narrative contract (one document, the matched positive control for the step
that used to push) and the finalize edge-ordering derivation (every discovered
step doc ordered below the barrier, the population-level negative control).
This module is the single implementation of that scan so the two suites cannot
disagree about what counts as a prescription.

**A prescription is a command, not a mention.** These documents describe the
push they must not perform — "this step does NOT push", "the order-11
``default:push`` barrier ships this commit" — so a substring search for
``push`` reports a doc that correctly refuses to push as one that prescribes
one. The scan therefore looks only at lines inside fenced code blocks, which is
where every executable instruction in a step doc lives, and skips commented
lines inside those fences, since a comment marking the ABSENCE of a push
(``# no push — the order-11 default:push barrier ships this commit``) must not
read as a push.

Every entry point returns the size of the population it examined alongside its
findings, so a caller can fail a scan that resolved nothing rather than
reporting a vacuous clean result.
"""

from __future__ import annotations

import re

#: A git invocation carrying a ``push`` word. Deliberately spelling-agnostic
#: rather than keyed to one literal: ``git push``,
#: ``git -C {worktree_path} push``, and ``git push --force-with-lease`` are all
#: prescriptions of the same forbidden act, and pinning a single spelling would
#: let the next one through.
PUSH_INVOCATION = re.compile(r'\bgit\b[^\n]*\bpush\b')

#: Fenced-code-block delimiter. The language tag (```bash / ```text / ```) is
#: irrelevant — only the fence state matters.
_FENCE = '```'


def fenced_command_lines(text: str) -> list[str]:
    """Return every line inside a fenced code block, comments excluded.

    Comment lines are dropped because a step doc records the absence of a push
    as a comment inside its pseudo-code, and that record is the opposite of a
    prescription.
    """
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(_FENCE):
            in_fence = not in_fence
            continue
        if in_fence and not line.lstrip().startswith('#'):
            lines.append(line)
    return lines


def scan_push_prescriptions(text: str) -> tuple[list[str], int]:
    """Return ``(push-prescribing lines, fenced command lines examined)``.

    The second element is the guard's published population. A document whose
    fences resolved no command lines yields ``(…, 0)``: the caller MUST treat
    that as an unresolved scan, not as a clean one.
    """
    commands = fenced_command_lines(text)
    offenders = [line.strip() for line in commands if PUSH_INVOCATION.search(line)]
    return offenders, len(commands)
