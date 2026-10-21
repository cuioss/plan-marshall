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
* **Resolved.** A line whose script token is a path placeholder (``{NAME}``,
  ``${NAME}`` or a brace-less ``$NAME`` such as ``"$DOCTOR_SCRIPT"``) is not
  skipped: a NAMED placeholder is RESOLVED to the documented path it stands for,
  and a GENERIC one (``{SCRIPT_FILE}``) is resolved against the AUTHORITATIVE
  shared allow-list (once per entry), then the resolved command is checked. An
  unmapped placeholder is an OFFENDER, so a placeholder can never dodge the sweep.* **Template.** A line carrying optional-argument usage notation
  (``[--scope global|project|all]``) is reported apart and never folded into the
  pass: no path is hidden behind an argument bracket.
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
#: candidate site, or it is stale and fails the test. Kept to the one site the
#: scan proved cannot be dispositioned as a resolved path: a prose fence listing
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
    'DOCTOR_SCRIPT': 'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py',
}

#: GENERIC placeholders — a name standing for "whatever path the preceding step
#: resolved", used by exactly one documented bootstrap example. A generic
#: placeholder is NOT mapped to a fixed script: it is resolved against the
#: AUTHORITATIVE shared allow-list data, once per repository-relative entry, so
#: the documented generic direct call is checked for EVERY allow-listed script
#: and the placeholder can never become a second, drifting admission list.
_GENERIC_SCRIPT_PLACEHOLDERS: frozenset[str] = frozenset({'SCRIPT_FILE'})

#: A path placeholder as the WHOLE script token: ``{NAME}``, ``${NAME}`` or a
#: brace-less ``$NAME``. All three are RESOLVED via :data:`_RESOLVED_PATH_TEMPLATES`
#: and the resolved command is checked; an unmapped one is an offender.
_BRACE_PLACEHOLDER_RE = re.compile(r'\$?\{([A-Za-z_][A-Za-z0-9_]*)\}')
_SHELL_VARIABLE_RE = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)')

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
    that token is absent or is not a ``{NAME}`` / ``${NAME}`` / ``$NAME`` path
    placeholder.
    """
    tokens = _HOOK._r5_stripped_tokens(command)
    if len(tokens) < 2:
        return None
    token = _unquote(tokens[1].strip())
    match = _BRACE_PLACEHOLDER_RE.fullmatch(token) or _SHELL_VARIABLE_RE.fullmatch(token)
    return match.group(1) if match else None


def _substitute_placeholder(command: str, name: str, replacement: str) -> str | None:
    """Substitute the ``{name}`` / ``${name}`` / ``$name`` placeholder, or ``None``."""
    for pattern in (
        re.compile(r'\$\{' + re.escape(name) + r'\}'),
        re.compile(r'\{' + re.escape(name) + r'\}'),
        re.compile(r'\$' + re.escape(name) + r'\b'),
    ):
        if pattern.search(command):
            return pattern.sub(replacement, command, count=1)
    return None


def _resolved_pair(command: str, unresolved: str | None) -> list[tuple[str, str | None]]:
    """Return a one-element ``(command, unresolved_name)`` result, typed narrowly."""
    return [(command, unresolved)]


def _resolve_script_template(command: str) -> list[tuple[str, str | None]]:
    """Return the ``(command_to_check, unresolved_name)`` pair(s) for a line.

    A line with no script placeholder yields itself. A line whose script token is
    a NAMED resolved-path placeholder yields the command with the documented path
    substituted. A line whose script token is a GENERIC placeholder yields one
    command per repository-relative entry of the AUTHORITATIVE shared allow-list,
    so a generic "the path resolved above" call is checked against the real data
    rather than a fixed surrogate. An UNMAPPED placeholder yields the original
    command with its name as ``unresolved_name`` — the caller reports it as an
    unresolved template, which FAILS, so a placeholder can never dodge the check.
    """
    name = _script_placeholder_name(command)
    if name is None:
        return _resolved_pair(command, None)
    if name in _GENERIC_SCRIPT_PLACEHOLDERS:
        resolved: list[tuple[str, str | None]] = []
        for entry in _HOOK._r5_allowlist_entries():
            substituted = _substitute_placeholder(command, name, entry)
            if substituted is not None:
                resolved.append((substituted, None))
        if resolved:
            return resolved
        return _resolved_pair(command, name)
    mapped = _RESOLVED_PATH_TEMPLATES.get(name)
    if mapped is None:
        return _resolved_pair(command, name)
    substituted = _substitute_placeholder(command, name, mapped)
    return _resolved_pair(substituted, None) if substituted is not None else _resolved_pair(command, name)


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
    # One candidate expands to one or more checks (a GENERIC placeholder resolves
    # once per allow-list entry), so the checks carry their candidate along.
    checks: list[tuple[Candidate, str, str | None]] = [
        (candidate, command, unresolved)
        for candidate in candidates
        for command, unresolved in _resolve_script_template(candidate.command)
    ]
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for _c, command, _u in checks])

    offenders: list[str] = []
    templates: list[str] = []
    excused: list[str] = []
    matched_exclusions: set[int] = set()

    for (candidate, check_command, unresolved), outcome in zip(checks, outcomes, strict=True):
        payload = {
            'agent_type': SUB_AGENT_AGENT,
            'tool_name': 'Bash',
            'tool_input': {'command': check_command},
            'cwd': str(REPO_ROOT),
        }
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
        if _OPTIONAL_NOTATION_RE.search(check_command):
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
    """Done-when (D1): a path template is RESOLVED from data and CHECKED.

    The sweep no longer skips a ``{PLACEHOLDER}`` script token: a NAMED placeholder
    resolves to the documented path it stands for, and a GENERIC one resolves
    against the AUTHORITATIVE shared allow-list (one command per entry) rather than
    a fixed surrogate — so neither can become a second, drifting admission list. An
    UNMAPPED placeholder is reported unresolved rather than skipped.
    """
    named = _resolve_script_template('python3 "{GENERATE_EXECUTOR}" generate')
    assert len(named) == 1, 'a named placeholder resolves to exactly one command'
    resolved, unresolved = named[0]
    assert unresolved is None, 'a mapped placeholder must resolve, never be reported unresolved'
    assert 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py' in resolved

    hook_reason = _HOOK.evaluate(
        {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': resolved}, 'cwd': str(REPO_ROOT)}
    )
    assert hook_reason is None, f'the resolved command must be admitted by the hook; reason={hook_reason!r}'

    harness = build_harness(tmp_path_factory.mktemp('guard-template'))
    blocked, message = harness.blocks(shell_event(resolved, agent=SUB_AGENT_AGENT))
    assert not blocked, f'the resolved command must be admitted by the guard; message={message!r}'

    entries = _HOOK._r5_allowlist_entries()
    assert entries, 'the shared allow-list must carry entries for the generic resolution to be substantive'
    generic = _resolve_script_template('python3 "{SCRIPT_FILE}" mode')
    assert len(generic) == len(entries), 'a generic placeholder resolves once per allow-list entry'
    assert all(one_unresolved is None for _command, one_unresolved in generic)
    for command, _one_unresolved in generic:
        assert command != 'python3 "{SCRIPT_FILE}" mode', f'the placeholder must be substituted: {command!r}'
        assert (
            _HOOK.evaluate(
                {
                    'agent_type': SUB_AGENT_AGENT,
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                    'cwd': str(REPO_ROOT),
                }
            )
            is None
        ), f'every allow-listed resolution must be admitted; command={command!r}'

    unmapped = _resolve_script_template('python3 "{NOT_A_KNOWN_PATH}" run')
    assert unmapped == [('python3 "{NOT_A_KNOWN_PATH}" run', 'NOT_A_KNOWN_PATH')]
