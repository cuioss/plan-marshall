#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Done-when (e): no documented interpreter invocation is refused by either guard.

A documented example is a promise — a reader copies it and runs it. When the
example is a direct ``python``/``python3`` invocation the enforcement guards
refuse, the document is prescribing a command that cannot survive its own
guardrail. This test extracts every interpreter invocation the corpus
documents, feeds each one through BOTH guards by REAL EXECUTION (the OpenCode
plugin under ``node``, and the Claude hook's ``evaluate``), and fails on any
invocation neither guard allows.

Population and dispositions
---------------------------

* **Population.** Every non-comment line of every fenced code block in the
  scanned roots (``marketplace/``, ``.claude/``, ``.opencode/``, ``doc/`` plus
  the root ``AGENTS.md`` / ``CLAUDE.md``), restricted to markdown and AsciiDoc.
  A line is a *candidate* when its first token is an interpreter (or a shell
  wrapper in front of one).  The population is DERIVED from the corpus, never
  declared, and both floors below are asserted so an empty scan fails rather
  than reading as clean.
* **Allowed.** Neither guard refuses the line — the healthy case.
* **Template.** The line carries usage notation that cannot run verbatim — a
  ``{placeholder}`` second token, a shell-variable second token
  (``"$DOCTOR_SCRIPT"``), or an optional-argument bracket
  (``[--scope global|project|all]``).  Such a line is reported apart and never
  folded into the pass: the allow-list covers the SUBSTITUTED form, not the
  notation.
* **Excluded.** A curated ``(path, line-fragment, reason)`` entry that still
  matches a live candidate site.  An entry matching nothing is STALE and fails
  the test, so an exclusion cannot outlive the line it excused.
* **Offender.** Refused and neither a template nor excluded — the defect this
  test exists to find.

The guards run with the plan-context gate SATISFIED, so a refusal is the
strictest verdict a documented line could meet.  Signal 1 (the sub-agent
identity) is used rather than a worktree cwd so no scratch log write is
implied; the node scratch root itself is ephemeral.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

import pytest
from _documented_example_scan import iter_fenced_blocks
from _guard_node_harness import (
    SUB_AGENT_AGENT,
    build_harness,
    guard_allowlist_path,
    shell_event,
)

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='sweep_pretooluse_hook',
    register=False,
)

#: Repo root, resolved from this file's location (``test/plan-marshall/platform-runtime/``).
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Scanned roots, relative to the repository root.
_SCAN_ROOTS = ('marketplace', '.claude', '.opencode', 'doc')

#: Scanned file suffixes.
_SCAN_SUFFIXES = ('.md', '.adoc')

#: Root-level files scanned in addition to the roots above.
_ROOT_FILES = ('AGENTS.md', 'CLAUDE.md')

#: Shell wrappers that may stand in front of the interpreter without being the
#: invocation's program. Used ONLY for candidate detection, deliberately
#: independent of either guard's own wrapper table so the population is stable
#: across an implementation change.
_WRAPPER_WORDS = frozenset({'command', 'env', 'sudo', 'timeout', 'nice', 'nohup', 'time', 'xargs', 'exec', 'setsid'})

#: ``(path, fragment, reason)`` exclusion entries. Each must still match a live
#: candidate site, or it is stale and fails the test. Kept to the one site the
#: scan proved cannot be dispositioned as a template: a prose fence listing
#: illustrative relative-path spellings, not a runnable repository invocation.
_EXCLUSIONS: tuple[tuple[str, str, str], ...] = (
    (
        'marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/core-principles.md',
        'python scripts/processor.py input.txt',
        'illustrative relative-path example in a prose fence, not a runnable repository invocation',
    ),
)

#: Population floors. A scan that resolves fewer than these is an UNRESOLVED
#: scan, never a clean one.
_MIN_FENCED_LINES = 500
_MIN_CANDIDATES = 15

#: A lowercase interpreter token: ``python``, ``python3``, ``python3.12``.
#: Case-SENSITIVE on purpose: a prose fence line that merely begins with the
#: word ``Python`` (a diagram label) is not an invocation, while a documented
#: ``python3`` line is. The uppercase-program case is pinned by the parity
#: corpus instead.
_LOWER_INTERPRETER_RE = re.compile(r'^python(\d+(?:\.\d+)*)?$')

#: Template notation on a documented line — a ``{placeholder}`` second token, a
#: shell-variable second token (``"$DOCTOR_SCRIPT"``), or an optional-argument
#: bracket (``[--scope global|project|all]``). A line carrying one is usage
#: notation that is not runnable verbatim, so a guard refusal of it reports the
#: notation rather than a defect.
_SECOND_TOKEN_TEMPLATE_RE = re.compile(
    r'(?:\$?\{[^{}]*\})|(?:\$[A-Za-z_][A-Za-z0-9_]*)|(?:\$\{[A-Za-z_][A-Za-z0-9_]*\})'
)
_OPTIONAL_NOTATION_RE = re.compile(r'\[\s*-')


@dataclass(frozen=True)
class Candidate:
    """One documented interpreter invocation and where it was found."""

    path: str
    line: int
    command: str

    @property
    def site(self) -> str:
        return f'{self.path}:{self.line}'


def _scan_files() -> list[Path]:
    files: set[Path] = set()
    for root in _SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for suffix in _SCAN_SUFFIXES:
            files.update(sorted(base.rglob('*' + suffix)))
    for name in _ROOT_FILES:
        candidate = REPO_ROOT / name
        if candidate.is_file():
            files.add(candidate)
    return sorted(files)


def _strip_prompt(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('$ '):
        return stripped[2:].strip()
    return stripped


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _unquote(token: str) -> str:
    if len(token) >= 2 and ((token[0] == '"' and token[-1] == '"') or (token[0] == "'" and token[-1] == "'")):
        return token[1:-1]
    return token


def _basename(token: str) -> str:
    return _unquote(token).rsplit('/', 1)[-1]


def _is_interpreter(token: str) -> bool:
    return _LOWER_INTERPRETER_RE.match(_basename(token)) is not None


def _is_candidate(command: str) -> bool:
    tokens = _tokens(command)
    if not tokens:
        return False
    first = _basename(tokens[0]).lower()
    if _is_interpreter(tokens[0]):
        return True
    if first in _WRAPPER_WORDS:
        return any(_is_interpreter(token) for token in tokens[1:])
    return False


def collect_candidates() -> tuple[list[Candidate], int]:
    """Return ``(candidates, fenced lines examined)`` over the scanned corpus."""
    candidates: list[Candidate] = []
    fenced_lines = 0
    for path in _scan_files():
        rel = str(path.relative_to(REPO_ROOT))
        text = path.read_text(encoding='utf-8')
        for block in iter_fenced_blocks(text):
            for offset, raw in enumerate(block.body.splitlines()):
                stripped = raw.strip()
                if not stripped:
                    continue
                fenced_lines += 1
                if stripped.startswith('#'):
                    continue
                command = _strip_prompt(stripped)
                if _is_candidate(command):
                    candidates.append(Candidate(path=rel, line=block.line + offset, command=command))
    return candidates, fenced_lines


def _is_template(command: str) -> bool:
    tokens = _HOOK._r5_stripped_tokens(command)
    second = _unquote(tokens[1].strip()) if len(tokens) >= 2 else ''
    if second and _SECOND_TOKEN_TEMPLATE_RE.fullmatch(second):
        return True
    return _OPTIONAL_NOTATION_RE.search(command) is not None


def _exclusion_for(candidate: Candidate) -> str | None:
    for path, fragment, reason in _EXCLUSIONS:
        if path == candidate.path and fragment in candidate.command:
            return reason
    return None


def test_shared_allowlist_data_file_exists() -> None:
    """The one shared allow-list data file both harnesses read must exist."""
    path = guard_allowlist_path()
    assert path.is_file(), f'shared R5 allow-list is missing: {path}'


def test_no_documented_invocation_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (e): every documented interpreter invocation survives both guards."""
    candidates, fenced_lines = collect_candidates()

    assert fenced_lines >= _MIN_FENCED_LINES, (
        f'scan resolved only {fenced_lines} fenced lines (floor {_MIN_FENCED_LINES}) — the extractor looked at '
        'nothing, so "no offender" would be vacuous'
    )
    assert len(candidates) >= _MIN_CANDIDATES, (
        f'scan found only {len(candidates)} interpreter candidates (floor {_MIN_CANDIDATES}) — the detector is '
        'looking at nothing'
    )

    scratch = tmp_path_factory.mktemp('guard-sweep')
    harness = build_harness(scratch)
    events = [shell_event(candidate.command, agent=SUB_AGENT_AGENT) for candidate in candidates]
    outcomes = harness.run(events)

    offenders: list[str] = []
    templates: list[str] = []
    excused: list[str] = []
    matched_exclusions: set[int] = set()

    for candidate, outcome in zip(candidates, outcomes, strict=True):
        payload = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': candidate.command}}
        hook_reason = _HOOK.evaluate(payload)
        refused = outcome.blocked or hook_reason is not None
        if not refused:
            continue
        reason = _exclusion_for(candidate)
        if reason is not None:
            excused.append(f'{candidate.site}: {candidate.command}  # excused: {reason}')
            matched_exclusions.update(
                index
                for index, (path, fragment, _r) in enumerate(_EXCLUSIONS)
                if path == candidate.path and fragment in candidate.command
            )
            continue
        if _is_template(candidate.command):
            templates.append(f'{candidate.site}: {candidate.command}')
            continue
        guards = []
        if outcome.blocked:
            guards.append(f'guard.js: {outcome.message}')
        if hook_reason is not None:
            guards.append(f'hook: {hook_reason}')
        offenders.append(f'{candidate.site}: {candidate.command}\n    refused by ' + '; '.join(guards))

    stale = [
        f'{path}: {fragment!r} (reason: {reason})'
        for index, (path, fragment, reason) in enumerate(_EXCLUSIONS)
        if index not in matched_exclusions
    ]

    assert not stale, f'{len(stale)} stale exclusion(s) match no candidate site:\n  ' + '\n  '.join(stale)
    assert not offenders, (
        f'{len(offenders)} documented invocation(s) refused by a guard '
        f'(out of {len(candidates)} candidates; {len(templates)} template(s), {len(excused)} excused):\n  '
        + '\n  '.join(offenders)
    )
