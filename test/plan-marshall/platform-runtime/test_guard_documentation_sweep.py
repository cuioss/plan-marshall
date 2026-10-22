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
    wrapper_table,
)
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

_BOOTSTRAP_PLUGIN = get_script_path('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py')

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

#: Shell wrapper words that may stand in front of the interpreter without being
#: the invocation's program. DERIVED from the shared wrapper table
#: (``standards/r5-wrappers.json``, the D1 data file) so a wrapper the guards
#: strip is also a wrapper the sweep looks behind — ``stdbuf`` in particular used
#: to be missing here while both guards stripped it.
_WRAPPER_WORDS = frozenset(wrapper_table().get('wrappers', {}))

#: Non-executor runners whose own invocation runs the command that follows. A
#: ``uv run python -c …`` line and a ``./pw verify`` line are exactly the forms
#: the guards refuse, so they are candidates even though neither starts with an
#: interpreter.
_NON_EXECUTOR_RUNNERS = frozenset({'uv', './pw', 'pw'})

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
    #: True when the invocation sits on a COMMENT line of a fenced block — a
    #: command turned into a comment to escape the sweep. Never excused: that is
    #: the defect, not a disposition.
    commented: bool = False

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
    """Whether *command* is a documented invocation the sweep must check.

    An interpreter-led line is a candidate; so is a wrapper-led line once the
    wrapper is stripped (``bash -c "python3 -c …"``, ``env ./pw verify``), a
    ``uv run`` line, a ``./pw`` line, and a comment line that carries any of
    those (a command turned into a comment to escape the sweep).
    """
    tokens = _tokens(command)
    if not tokens:
        return False
    if _is_interpreter(tokens[0]):
        return True
    first = _basename(tokens[0]).lower()
    if first in _NON_EXECUTOR_RUNNERS or tokens[0] in _NON_EXECUTOR_RUNNERS:
        return True
    if first in _WRAPPER_WORDS:
        stripped = _HOOK._r5_stripped_tokens(command)
        if stripped:
            program = _basename(stripped[0]).lower()
            if _is_interpreter(stripped[0]) or program in _NON_EXECUTOR_RUNNERS:
                return True
            if stripped[0] in _NON_EXECUTOR_RUNNERS:
                return True
        if any(_is_interpreter(token) for token in tokens[1:]):
            return True
        if any(token in _NON_EXECUTOR_RUNNERS for token in tokens[1:]):
            return True
    return False


#: Fenced-block languages whose ``#`` lines are a shell COMMENT rather than source
#: code. A ``python`` / ``javascript`` / ``json`` fence carries code, so a ``#``
#: line there is a comment in that language (or a shebang) and never a shell
#: command turned into a comment.
_SHELL_FENCE_LANGUAGES = frozenset({'', 'bash', 'sh', 'shell', 'console', 'zsh', 'text'})


def collect_candidates_from(named_paths: list[tuple[Path, str]]) -> tuple[list[Candidate], int]:
    """Return ``(candidates, fenced lines examined)`` for explicit *named_paths*.

    ``named_paths`` pairs a file with the name to report it under, so a test
    fixture can be swept through the SAME extractor the corpus uses without
    living inside the scanned roots.
    """
    candidates: list[Candidate] = []
    fenced_lines = 0
    for path, rel in named_paths:
        text = path.read_text(encoding='utf-8')
        for block in iter_fenced_blocks(text):
            shell_fence = block.language.lower() in _SHELL_FENCE_LANGUAGES
            for offset, raw in enumerate(block.body.splitlines()):
                stripped = raw.strip()
                if not stripped:
                    continue
                fenced_lines += 1
                if stripped.startswith('#'):
                    if not shell_fence:
                        continue
                    commented = stripped.lstrip('#').strip()
                    command = _strip_prompt(commented)
                    if _is_candidate(command):
                        candidates.append(
                            Candidate(
                                path=rel,
                                line=block.line + offset,
                                command=command,
                                commented=True,
                            )
                        )
                    continue
                command = _strip_prompt(stripped)
                if _is_candidate(command):
                    candidates.append(Candidate(path=rel, line=block.line + offset, command=command))
    return candidates, fenced_lines


def collect_candidates() -> tuple[list[Candidate], int]:
    """Return ``(candidates, fenced lines examined)`` over the scanned corpus.

    A COMMENT line of a SHELL fence is no longer skipped: a candidate-shaped
    command sitting on a ``#`` line there is collected with ``commented=True`` and
    reported when a guard refuses it, because turning a refused invocation into a
    comment is exactly how a documented command escapes this sweep. A comment
    inside a ``python`` / ``javascript`` / ``json`` fence is that language's own
    code and is left alone.
    """
    return collect_candidates_from([(path, str(path.relative_to(REPO_ROOT))) for path in _scan_files()])


#: Documents whose RECOVERY commands sit in PROSE rather than in a fenced block.
#: A recovery instruction a reader copies is a documented invocation wherever it
#: is written, so these files are swept line by line.
_PROSE_SCAN_FILES = ('marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md',)

#: A backticked script path in prose — the shape a recovery instruction names.
_PROSE_SCRIPT_RE = re.compile(r'`([^`]+\.py)`')

#: A ``{NAME}`` placeholder inside such a path.
_PROSE_PLACEHOLDER_RE = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')

#: The deployed-cache placeholder a consumer recovery path stands behind. It is
#: resolved to the NEWEST deployed version directory the resolver would select.
_DEPLOYED_CACHE_PLACEHOLDER = 'newest_cache'


def _newest_deployed_root() -> str | None:
    """The newest nested deployed version directory carrying the recovery script."""
    import pathlib

    recovery_entry = 'skills/tools-script-executor/scripts/generate_executor.py'
    for root in _HOOK._deployed_bundle_roots():
        nested = pathlib.Path(root) / 'plan-marshall'
        version = _HOOK._newest_version_dir(nested, '.claude-plugin/plugin.json', recovery_entry)
        if version is not None:
            return str(version)
    return None


def _resolve_prose_path(raw: str) -> str | None:
    """Resolve a prose script path, or ``None`` when it cannot be resolved.

    ``{newest_cache}`` resolves to the newest deployed version directory (``None``
    when nothing is deployed on this machine — then there is no consumer path to
    check); a named template resolves through the shared map; any other
    placeholder leaves the path unresolved, which SKIPS it rather than checking a
    guessed path.
    """
    resolved = raw
    for match in _PROSE_PLACEHOLDER_RE.finditer(raw):
        name = match.group(1)
        if name == _DEPLOYED_CACHE_PLACEHOLDER:
            root = _newest_deployed_root()
            if root is None:
                return None
            resolved = resolved.replace(match.group(0), root)
        elif name in _RESOLVED_PATH_TEMPLATES:
            resolved = resolved.replace(match.group(0), _RESOLVED_PATH_TEMPLATES[name])
        else:
            return None
    return resolved


def _fenced_line_numbers(text: str) -> set[int]:
    """Every line number covered by a fenced block in *text*."""
    covered: set[int] = set()
    for block in iter_fenced_blocks(text):
        count = len(block.body.splitlines())
        covered.update(range(block.line, block.line + count + 1))
    return covered


def collect_prose_candidates() -> list[Candidate]:
    """Return the PROSE recovery invocations from :data:`_PROSE_SCAN_FILES`."""
    candidates: list[Candidate] = []
    for rel in _PROSE_SCAN_FILES:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        fenced = _fenced_line_numbers(text)
        for offset, raw in enumerate(text.splitlines()):
            line_no = offset + 1
            if line_no in fenced:
                continue
            for match in _PROSE_SCRIPT_RE.finditer(raw):
                raw_path = match.group(1)
                # Only a path carrying a PLACEHOLDER is a deployed-form
                # prescription. A bare path in prose is a mention (often of a
                # command the text says must NOT be run), not a command.
                if _PROSE_PLACEHOLDER_RE.search(raw_path) is None:
                    continue
                resolved = _resolve_prose_path(raw_path)
                if resolved is None:
                    continue
                candidates.append(Candidate(path=rel, line=line_no, command=f'python3 {resolved} run'))
    return candidates


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


#: The bundle whose deployed paths the named placeholders also stand for.
_BUNDLE_NAME = 'plan-marshall'

#: Per-entry memoisation of the resolver's deployed answers (one subprocess each).
_DEPLOYED_CACHE: dict[str, list[str]] = {}


def _bundle_relative(repo_relative: str) -> str | None:
    """Return *repo_relative*'s bundle-relative spelling, or ``None``."""
    prefix = f'marketplace/bundles/{_BUNDLE_NAME}/'
    if not repo_relative.startswith(prefix):
        return None
    return repo_relative[len(prefix) :]


def _deployed_paths(repo_relative: str) -> list[str]:
    """Return the DEPLOYED path(s) ``bootstrap_plugin resolve`` names for a script.

    ``repo_relative`` is either the repository-relative path
    (``marketplace/bundles/plan-marshall/skills/…``) or the bundle-relative
    spelling already (``skills/…``). A named placeholder stands for the documented
    script in BOTH spellings: the repository-relative path every checkout has, and
    the deployed bundle path a consumer checkout has. The deployed answer is the
    RESOLVER's, never a reconstructed path — an entry the resolver cannot place
    yields no deployed candidate (there is nothing to check on this machine).
    """
    entry = repo_relative if repo_relative.startswith('skills/') else _bundle_relative(repo_relative)
    if entry is None:
        return []
    if entry in _DEPLOYED_CACHE:
        return _DEPLOYED_CACHE[entry]
    resolved: list[str] = []
    try:
        result = run_script(
            _BOOTSTRAP_PLUGIN,
            'resolve',
            '--bundle',
            _BUNDLE_NAME,
            '--path',
            entry,
        )
        if result.returncode == 0:
            payload = parse_toon(result.stdout)
            path = payload.get('resolved_path')
            if isinstance(path, str) and path:
                resolved.append(path)
    except Exception:  # pragma: no cover - a resolver failure is "nothing deployed"
        resolved = []
    _DEPLOYED_CACHE[entry] = resolved
    return resolved


def _resolve_script_template(command: str) -> list[tuple[str, str | None]]:
    """Return the ``(command_to_check, unresolved_name)`` pair(s) for a line.

    A line with no script placeholder yields itself. A line whose script token is
    a NAMED resolved-path placeholder yields the command with the documented
    repository-relative path substituted AND, when the resolver names one, the
    command with its DEPLOYED path substituted — so a consumer-form line is
    checked, not silently accepted. A line whose script token is a GENERIC
    placeholder yields one command per allow-list entry, in both spellings, so a
    generic "the path resolved above" call is checked against the real data
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
            for deployed in _deployed_paths(entry):
                deployed_command = _substitute_placeholder(command, name, deployed)
                if deployed_command is not None:
                    resolved.append((deployed_command, None))
        for entry in _HOOK._r5_allowlist_bundle_entries():
            for deployed in _deployed_paths(entry):
                deployed_command = _substitute_placeholder(command, name, deployed)
                if deployed_command is not None:
                    resolved.append((deployed_command, None))
        if resolved:
            return resolved
        return _resolved_pair(command, name)
    mapped = _RESOLVED_PATH_TEMPLATES.get(name)
    if mapped is None:
        return _resolved_pair(command, name)
    replaced: list[tuple[str, str | None]] = []
    substituted = _substitute_placeholder(command, name, mapped)
    if substituted is not None:
        replaced.append((substituted, None))
    for deployed in _deployed_paths(mapped):
        deployed_command = _substitute_placeholder(command, name, deployed)
        if deployed_command is not None:
            replaced.append((deployed_command, None))
    return replaced or _resolved_pair(command, name)


def _exclusion_for(candidate: Candidate) -> str | None:
    for path, fragment, reason in _EXCLUSIONS:
        if path == candidate.path and fragment in candidate.command:
            return reason
    return None


def test_shared_allowlist_data_file_exists() -> None:
    """The one shared allow-list data file both harnesses read must exist."""
    path = guard_allowlist_path()
    assert path.is_file(), f'shared R5 allow-list is missing: {path}'


def _mentions_interpreter(command: str) -> bool:
    """Whether *command* prescribes an interpreter invocation at all.

    A ``./pw`` line is a candidate (it is refused by R4), but it prescribes no
    interpreter, so it is not this sweep's defect. A line that hides an
    interpreter behind a wrapper or a runner — ``bash -c "python3 -c x"``,
    ``uv run python -c x`` — does, and is.
    """
    if any(_is_interpreter(token) for token in _tokens(command)):
        return True
    stripped = _HOOK._r5_stripped_tokens(command)
    return bool(stripped) and _is_interpreter(stripped[0])


def _classify(
    checks: list[tuple[Candidate, str, str | None]],
    outcomes: list,
) -> tuple[list[str], list[str], list[str], set[int], list[str]]:
    """Disposition every check.

    Returns ``(offenders, templates, excused, matched_exclusions, non_interpreter)``
    — ``non_interpreter`` holds the candidate-shaped lines that prescribe no
    interpreter at all (a bare ``./pw`` build line), which are checked but are not
    this sweep's defect.
    """
    offenders: list[str] = []
    templates: list[str] = []
    excused: list[str] = []
    non_interpreter: list[str] = []
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
        if candidate.commented:
            # Commenting a REFUSED command out does not stop the document from
            # prescribing it — and it is exactly how a documented invocation
            # escapes a sweep that reads only uncommented lines.
            offenders.append(
                f'{candidate.site}: {candidate.command}\n'
                '    a refused documented invocation turned into a COMMENT — the command it '
                'prescribes is still prescribed, so this is not a disposition'
            )
            continue
        if not _mentions_interpreter(check_command):
            non_interpreter.append(f'{candidate.site}: {candidate.command}')
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
        checked_as = '' if check_command == candidate.command else f'\n    checked as: {check_command}'
        offenders.append(f'{candidate.site}: {candidate.command}{checked_as}\n    refused by ' + '; '.join(guards))
    return offenders, templates, excused, matched_exclusions, non_interpreter


def _expand(candidates: list[Candidate]) -> list[tuple[Candidate, str, str | None]]:
    """One or more checks per candidate (a placeholder can resolve to several)."""
    return [
        (candidate, command, unresolved)
        for candidate in candidates
        for command, unresolved in _resolve_script_template(candidate.command)
    ]


def test_no_documented_invocation_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (e): every documented interpreter invocation survives both guards."""
    candidates, fenced_lines = collect_candidates()
    candidates = candidates + collect_prose_candidates()

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
    checks = _expand(candidates)
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for _c, command, _u in checks])

    offenders, templates, excused, matched_exclusions, non_interpreter = _classify(checks, outcomes)

    stale = [
        f'{path}: {fragment!r} (reason: {reason})'
        for index, (path, fragment, reason) in enumerate(_EXCLUSIONS)
        if index not in matched_exclusions
    ]

    assert not stale, f'{len(stale)} stale exclusion(s) match no candidate site:\n  ' + '\n  '.join(stale)
    assert not offenders, (
        f'{len(offenders)} documented invocation(s) refused by a guard '
        f'(out of {len(candidates)} candidates; {len(templates)} template(s), {len(excused)} excused, '
        f'{len(non_interpreter)} non-interpreter build line(s)):\n  ' + '\n  '.join(offenders)
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
    assert named, 'a named placeholder must resolve'
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
    assert len(generic) >= len(entries), 'a generic placeholder resolves once per allow-list entry (and spelling)'
    assert all(one_unresolved is None for _command, one_unresolved in generic)
    resolved_commands = {command for command, _one in generic}
    for entry in entries:
        assert any(entry in command for command in resolved_commands), (
            f'the generic placeholder must expand over the repository-relative entry {entry!r}'
        )
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

    bundle_entries = _HOOK._r5_allowlist_bundle_entries()
    assert bundle_entries, 'the shared allow-list must carry bundle-relative entries too'
    assert not any('python3 "skills/' in command for command in resolved_commands), (
        'a bundle-relative entry must be expanded to its DEPLOYED path, never emitted raw'
    )

    unmapped = _resolve_script_template('python3 "{NOT_A_KNOWN_PATH}" run')
    assert unmapped == [('python3 "{NOT_A_KNOWN_PATH}" run', 'NOT_A_KNOWN_PATH')]


# =============================================================================
# D4 — the forms this defect class lives in
# =============================================================================


def test_sweep_wrapper_words_come_from_the_shared_table() -> None:
    """The sweep looks behind exactly the wrappers the guards strip (D1's table)."""
    table = wrapper_table().get('wrappers', {})
    assert table, 'the shared wrapper table is empty'
    assert _WRAPPER_WORDS == frozenset(table), 'the sweep wrapper words drifted from the shared table'
    assert 'stdbuf' in _WRAPPER_WORDS, 'stdbuf is the wrapper this sweep used to miss'
    assert 'ionice' in _WRAPPER_WORDS, 'the D1 wrappers must join the sweep too'


@pytest.mark.parametrize(
    'command',
    [
        'bash -c "python3 -c x"',
        'env bash -c "python3 -c x"',
        'uv run python -c x',
        'env ./pw verify',
        './pw verify',
        'stdbuf -o0 python3 -c x',
    ],
    ids=['bash-c', 'env-bash-c', 'uv-run', 'env-pw', 'pw', 'stdbuf'],
)
def test_the_sweep_detects_the_forms_the_defect_class_lives_in(command: str) -> None:
    """``bash -c``, ``uv run`` and ``./pw`` lines are candidates, not invisible."""
    assert _is_candidate(command), f'{command!r} must be a swept candidate'


def test_a_commented_command_is_flagged_not_skipped() -> None:
    """A command turned into a comment to escape the sweep is an OFFENDER."""
    from _guard_node_harness import GuardOutcome

    candidate = Candidate(path='fixture.md', line=3, command='python3 -c "print(1)"', commented=True)
    offenders, _templates, _excused, _matched, _non = _classify(
        [(candidate, candidate.command, None)], [GuardOutcome(True, '[plan-marshall-guard] R5: refused')]
    )
    assert offenders, 'a commented invocation must be reported'
    assert 'COMMENT' in offenders[0]


def test_a_fixture_doc_with_bash_c_and_uv_run_is_reported(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """A fixture doc prescribing ``bash -c "python3 -c …"`` and ``uv run python -c …``.

    Both lines are collected by the REAL extractor and land in the offender list
    through the REAL guard/hook run — not at the ``_is_candidate`` level.
    """
    fixture = tmp_path / 'fixture.md'
    fixture.write_text(
        '# Fixture\n\n```bash\nbash -c "python3 -c x"\nuv run python -c x\n```\n',
        encoding='utf-8',
    )
    candidates, _fenced = collect_candidates_from([(fixture, 'fixture.md')])
    assert len(candidates) == 2, f'both forms must be collected; got {[c.command for c in candidates]!r}'

    harness = build_harness(tmp_path_factory.mktemp('sweep-fixture'))
    checks = _expand(candidates)
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for _c, command, _u in checks])
    offenders, _templates, _excused, _matched, _non = _classify(checks, outcomes)
    assert len(offenders) == 2, f'both lines must be reported; offenders={offenders!r}'


def test_a_deployed_form_doc_line_is_reported_end_to_end(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A doc line prescribing a deployed-form command R5 refuses is reported.

    The line is collected by the real extractor, expanded to BOTH its
    repository-relative and its deployed spelling, and classified after a real
    guard/hook run: the repository-relative spelling passes, the deployed one
    (under a directory that is not a deploy root) is reported.
    """
    deployed = (
        tmp_path / 'not-a-deployed-root' / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    )
    deployed.parent.mkdir(parents=True)
    deployed.write_text('# planted\n', encoding='utf-8')
    fixture = tmp_path / 'fixture.md'
    fixture.write_text('# Fixture\n\n```bash\npython3 "{GENERATE_EXECUTOR}" generate\n```\n', encoding='utf-8')
    monkeypatch.setattr(
        'test_guard_documentation_sweep._deployed_paths',
        lambda repo_relative: [str(deployed)],
        raising=True,
    )

    candidates, _fenced = collect_candidates_from([(fixture, 'fixture.md')])
    checks = _expand(candidates)
    assert any(str(deployed) in command for _c, command, _u in checks), 'the deployed spelling must be checked'
    harness = build_harness(tmp_path_factory.mktemp('sweep-deployed'))
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for _c, command, _u in checks])
    offenders, _templates, _excused, _matched, _non = _classify(checks, outcomes)
    assert any(str(deployed) in offender for offender in offenders), (
        f'the refused deployed form must be reported; offenders={offenders!r}'
    )
    assert not any('marketplace/bundles' in offender for offender in offenders), (
        'the repository-relative spelling is admitted and must not be reported'
    )


def test_upgrade_flow_prose_recovery_is_swept(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The consumer recovery command in ``upgrade-flow.md`` PROSE is part of the swept set.

    The line names the deployed path as ``{newest_cache}/skills/…``; with a
    deployed cache present the placeholder resolves to the newest version
    directory and the resulting command is checked — and admitted, because it is
    exactly the deployed spelling the allow-list names.
    """
    home = tmp_path_factory.mktemp('sweep-home')
    version = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'plan-marshall' / '1.0.0'
    marker = version / '.claude-plugin' / 'plugin.json'
    marker.parent.mkdir(parents=True)
    marker.write_text('{"name": "plan-marshall"}\n', encoding='utf-8')
    script = version / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    script.parent.mkdir(parents=True)
    script.write_text('# deployed\n', encoding='utf-8')
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home / '.config'))

    prose = collect_prose_candidates()
    recovery = [
        candidate
        for candidate in prose
        if candidate.path.endswith('upgrade-flow.md') and 'generate_executor.py' in candidate.command
    ]
    assert recovery, f'upgrade-flow.md prose recovery command not swept; sites={[c.site for c in prose]!r}'
    assert 'newest_cache' not in recovery[0].command, 'the placeholder must be resolved before checking'
    assert (
        _HOOK.evaluate(
            {
                'agent_type': SUB_AGENT_AGENT,
                'tool_name': 'Bash',
                'tool_input': {'command': recovery[0].command},
                'cwd': str(REPO_ROOT),
            }
        )
        is None
    ), 'the deployed recovery command must be admitted by the hook'
