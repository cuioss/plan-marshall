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
* **Resolved.** A line whose script token is a brace-delimited placeholder
  (``{GENERATE_EXECUTOR}``) is not skipped: the placeholder is RESOLVED to the
  documented path it stands for and the resolved command is checked. An unmapped
  placeholder is an OFFENDER, so a placeholder can never dodge the sweep.
* **Template.** A line whose script token is a brace-less shell variable
  (``"$DOCTOR_SCRIPT"``) is ordinary usage notation the reader substitutes; it is
  reported apart and never folded into the pass.
* **Excluded.** A curated ``(path, line-fragment, reason)`` entry that still
  matches a live candidate site.  An entry matching nothing is STALE and fails
  the test, so an exclusion cannot outlive the line it excused.
* **Offender.** Refused and neither a template nor excluded — the defect this
  test exists to find.

The guards run with the plan-context gate SATISFIED, so a refusal is the
strictest verdict a documented line could meet for the gated rules. Signal 1
(the sub-agent identity) is used rather than a worktree cwd so no scratch log
write is implied; the node scratch root itself is ephemeral. R5 binds inside a
plan context AND in every session of this repository — which the node scratch
root is (it carries the repository marker) and which the hook's own location is
— so its verdict follows from the resolved command either way.
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
#: candidate site, or it is stale and fails the test. Kept to sites the scan
#: proved cannot be dispositioned as a resolved path: illustrative relative-path
#: spellings, an anti-pattern, and a generic placeholder — none of them a
#: prescribed command with a real script path.
_EXCLUSIONS: tuple[tuple[str, str, str], ...] = (
    (
        'marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/core-principles.md',
        'python scripts/processor.py input.txt',
        'illustrative relative-path example in a prose fence, not a runnable repository invocation',
    ),
    (
        'marketplace/bundles/plan-marshall/skills/tools-file-ops/SKILL.md',
        'python3 {script} --lesson-file {lesson.file}',
        'anti-pattern illustration inside a python fence, explicitly labelled BAD — not a prescribed command',
    ),
    (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md',
        'python3 "{SCRIPT_FILE}" <args>',
        'generic placeholder for an arbitrary resolved script path, not a resolved-path template',
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

#: The documented RESOLVED-PATH placeholders the corpus uses as a script token,
#: mapped to the repository-relative path each stands for. A documented line
#: whose script token is one of these is RESOLVED to the mapped path and CHECKED
#: through both guards — a placeholder is never a way to dodge the sweep. The
#: mapped paths are the admittable forms (the allow-listed scripts), so a
#: resolved line passes exactly when the real command would.
_RESOLVED_PATH_TEMPLATES: dict[str, str] = {
    'GENERATE_EXECUTOR': (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
    ),
    'resolved_generate_executor_path': (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
    ),
    'DETERMINE_MODE': 'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py',
    'GITIGNORE_SETUP': 'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py',
    'PERMISSION_FIX': 'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
    'BOOTSTRAP': 'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py',
    'BOOTSTRAP_PLUGIN': 'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py',
}

#: A brace-delimited path placeholder as the WHOLE script token: ``{NAME}`` or
#: ``${NAME}``. A brace-less ``$NAME`` is ordinary shell-variable usage (the
#: reader substitutes their own value), not a documented resolved path, so it
#: stays a TEMPLATE rather than an unresolved offender.
_BRACE_PLACEHOLDER_RE = re.compile(r'\$?\{([A-Za-z_][A-Za-z0-9_]*)\}')
_SHELL_VARIABLE_RE = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*')

#: Optional-argument usage notation (``[--scope global|project|all]``). The ``|``
#: inside the bracket is shell pipe to R1, so such a line is usage notation, not
#: a runnable command — reported apart, never folded into the pass. It is NOT a
#: resolved-path template: no path is hidden behind it.
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


def _script_placeholder_name(command: str) -> str | None:
    """Return the placeholder NAME a documented line uses as its script token.

    The script token is the second shell-lexical token after R5 wrapper stripping
    (the hook's own reader, so the two agree on what the script is). ``None`` when
    that token is absent or is not a brace-delimited placeholder.
    """
    tokens = _HOOK._r5_stripped_tokens(command)
    if len(tokens) < 2:
        return None
    token = _unquote(tokens[1].strip())
    match = _BRACE_PLACEHOLDER_RE.fullmatch(token)
    return match.group(1) if match else None


def _is_shell_variable_template(command: str) -> bool:
    """Whether the script token is a brace-less ``$NAME`` shell variable.

    Such a line is ordinary shell-variable usage the reader substitutes, not a
    documented resolved path, so it stays a TEMPLATE rather than an offender.
    """
    tokens = _HOOK._r5_stripped_tokens(command)
    if len(tokens) < 2:
        return False
    return _SHELL_VARIABLE_RE.fullmatch(_unquote(tokens[1].strip())) is not None


def _resolve_script_template(command: str) -> tuple[str, str | None]:
    """Return ``(command_to_check, unresolved_name)`` for a documented line.

    When the script token is a brace-delimited placeholder, it is substituted
    with the documented resolved path and the RESOLVED command is returned for
    checking. An UNMAPPED placeholder returns the original command with its name
    as ``unresolved_name`` — the caller reports it as an unresolved template,
    which FAILS, so a placeholder can never dodge the check. A line with no
    brace placeholder is returned unchanged with ``None``.
    """
    name = _script_placeholder_name(command)
    if name is None:
        return command, None
    mapped = _RESOLVED_PATH_TEMPLATES.get(name)
    if mapped is None:
        return command, name
    for pattern in (re.compile(r'\$\{' + re.escape(name) + r'\}'), re.compile(r'\{' + re.escape(name) + r'\}')):
        if pattern.search(command):
            return pattern.sub(mapped, command, count=1), None
    return command, name


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
    checked = [_resolve_script_template(candidate.command) for candidate in candidates]
    events = [shell_event(command, agent=SUB_AGENT_AGENT) for command, _unresolved in checked]
    outcomes = harness.run(events)

    offenders: list[str] = []
    templates: list[str] = []
    excused: list[str] = []
    matched_exclusions: set[int] = set()

    for candidate, (check_command, unresolved), outcome in zip(candidates, checked, outcomes, strict=True):
        payload = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': check_command}}
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
        if unresolved is not None:
            offenders.append(
                f'{candidate.site}: {candidate.command}\n    unresolved resolved-path template '
                f'"{{{unresolved}}}" — map it to its documented path or drop the placeholder'
            )
            continue
        if _is_shell_variable_template(check_command) or _OPTIONAL_NOTATION_RE.search(check_command):
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


def test_a_resolved_path_template_is_checked_not_skipped(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): a brace-delimited path template is RESOLVED and CHECKED.

    The sweep no longer skips a ``{PLACEHOLDER}`` script token: it resolves the
    placeholder to the documented path and feeds the RESOLVED command through both
    guards, so a documented template cannot dodge the check. An UNMAPPED
    placeholder is reported unresolved rather than skipped.
    """
    resolved, unresolved = _resolve_script_template('python3 "{GENERATE_EXECUTOR}" generate')
    assert unresolved is None, 'a mapped placeholder must resolve, never be reported unresolved'
    assert 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py' in resolved

    hook_reason = _HOOK.evaluate(
        {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': resolved}}
    )
    assert hook_reason is None, f'the resolved command must be admitted by the hook; reason={hook_reason!r}'

    harness = build_harness(tmp_path_factory.mktemp('guard-template'))
    blocked, message = harness.blocks(shell_event(resolved, agent=SUB_AGENT_AGENT))
    assert not blocked, f'the resolved command must be admitted by the guard; message={message!r}'

    _command, name = _resolve_script_template('python3 "{NOT_A_KNOWN_PATH}" run')
    assert name == 'NOT_A_KNOWN_PATH', 'an unmapped placeholder must be reported unresolved, never skipped'
