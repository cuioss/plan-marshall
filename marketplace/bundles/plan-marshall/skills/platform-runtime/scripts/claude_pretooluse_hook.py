#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Conditional PreToolUse enforcement leaf for Claude Code.

Registered (opt-in) as a matcher-less ``hooks.PreToolUse`` entry. It blocks six
mechanically-checkable hard-rule violation families. R1-R5 are enforced when the
call originates inside a plan-marshall plan context, when the checkout carries a
runbook-lane marker, or in EVERY session of this repository; outside that scope
(and on every error path) they emit nothing and the hook exits 0 (fail OPEN), so
a consumer repository's ordinary Python work is untouched outside a plan context.
**R6 is not context-gated** — a raw ``git commit`` into a 6-finalize plan worktree
is refused from any session, named from every commit form (``-C``,
``--git-dir``/``--work-tree``, ``GIT_DIR``, a resolved ``-c alias``).

ALL payload parsing, field access, and the context-gate predicate are delegated
to the shared ``pretooluse_gate`` module — this leaf adds NO field-name knowledge
of its own. The only logic it owns is the R1-R6 rule matchers and the
``permissionDecision: deny`` envelope layered on top:

- **R1 shell-construct compound** — a Bash command containing an UNQUOTED and
  UNESCAPED ``&&``, ``;``, ``|``, ``&``, newline, ``for``/``while`` loop, ``$(...)``
  command substitution, or a leading ``VAR=val cmd`` inline env-var assignment.
  The recognised families are enumerated by ``_R1_FAMILIES``. An operator
  confined to a quoted argument is data, not an operator, and does not trip the
  rule; a command substitution still trips it inside DOUBLE quotes, where the
  shell still executes it.
- **R2 Bash file-ops** — a Bash command whose program is ``cat`` / ``grep`` /
  ``head`` / ``tail`` / ``find`` / ``ls``, or ``git`` whose subcommand (after any
  global options) is ``grep``.
- **R3 generated-executor edit** — an Edit/Write whose path is the generated
  ``.plan/execute-script.py``.
- **R4 hard-coded build** — a Bash command invoking ``./pw`` or a bare ``mvn`` /
  ``npm`` / ``gradle``.
- **R5 direct interpreter call** — a Bash command invoking an interpreter
  (``python`` / ``python3`` / ``pypy`` / ``pypy3`` / a versioned spelling such as
  ``python3.12``, case-insensitively) as ``-c``, a script path, a bare ``-``
  (STDIN) or a ``-<``/``->`` redirection, or ``-m`` with any module. R5 BINDS
  inside a plan context (Signal 1 or Signal 2) and in EVERY session of THIS
  repository; in a consumer repository outside a plan context it does not refuse
  a consumer's ordinary Python work. Admissions: the ``python3
  .plan/execute-script.py`` executor permit (the RELATIVE form admitted only from
  the repository root — a leading ``cd``, an ``env -C``/``--chdir``/``sudo -D``
  directory change and the shell workdir are resolved first — or an ABSOLUTE form
  resolving to ``{repository root}/.plan/execute-script.py``); the shared
  allow-list of documented non-executor invocations read from
  ``standards/r5-allowlist.json``, whose REPOSITORY-RELATIVE entries are matched
  EXACTLY against the invocation's script path resolved against the repository
  root; and that file's BUNDLE-RELATIVE entries, matched EXACTLY against the
  resolver's deployed path for the entry. Neither form is ever a basename or a
  suffix, so a copy of an allow-listed script outside the repository, or under a
  non-deployed directory, never matches. The wrapper prefixes come from ONE
  shared data file, [`r5-wrappers.json`](r5-wrappers.json): a path-qualified
  ``/usr/bin/env`` strips like ``env``, an option cluster like ``env -iu FOO`` is
  walked letter by letter, ``timeout`` / ``flock`` / ``chrt`` / ``taskset``
  consume their leading positional, ``env -S``, a shell's ``-c`` and ``watch`` /
  ``parallel`` splice their command string back into the walk, and
  ``find … -exec`` is walked from the program it runs. The allow set is otherwise
  executor-only, so every ``-m`` form refuses.
- **R6 raw finalize commit** — a raw ``git commit`` while the enclosing plan, in
  phase ``6-finalize``. The plan is NAMED from every commit form: the
  ``--work-tree`` value, the composed ``git -C`` target, the plan a ``--git-dir``
  / ``GIT_DIR`` admin directory points at (``…/worktrees/{plan}``), then the
  payload ``cwd``, then the project root (never "the first plan found"); its
  phase is read from that plan's own ``status.json`` field ``current_phase`` —
  the worktree-resident record first (the live one during phase 5+), then the
  main-anchored record. A subcommand defined with ``-c alias.NAME=…`` is resolved
  to its body; a shell-expansion alias body and any directory value that still
  carries an unexpanded variable are UNRESOLVABLE and refused fail-closed inside
  the enforced scope. R6 is NOT context-gated. Every plan commit must pass
  through the gate-bearing ``git-workflow commit`` verb; outside ``6-finalize`` a
  raw commit is untouched.

Control flow:

1. Parse stdin via ``gate.parse`` (empty/malformed → emit nothing, exit 0).
2. Evaluate the scope: ``gate.context_gate(payload)`` (``Signal1 OR Signal2``) OR
   the runbook-lane marker OR this project IS the plan-marshall source
   repository. Inside it, run the R1-R5 matchers; on the FIRST match, append one
   ``guard.log`` audit line (best-effort) and emit the deny envelope with a
   one-line redirect reason.
3. Run the R6 raw-finalize-commit rule unconditionally — it is NOT
   context-gated — and on a match audit and deny.
4. No match → emit nothing, exit 0.

The whole leaf is best-effort/no-raise: any internal error degrades to a silent
no-op (emit nothing, exit 0).

Usage (invoked by Claude Code's PreToolUse hook mechanism, not directly):
    echo '{"tool_name": "Bash", "tool_input": {"command": "cat x"},
           "cwd": "/repo/.plan/local/worktrees/p"}' \\
        | python3 claude_pretooluse_hook.py
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import posixpath
import re
import shlex
import sys
import time
from collections.abc import Callable
from typing import Any, NamedTuple

import pretooluse_gate as gate
from command_forms import STEWARD_COMMAND, SYNC_HARNESSES_COMMAND

# =============================================================================
# Rule-matcher constants — enforcement-only knowledge that lives in this leaf.
# (Payload-field knowledge lives in pretooluse_gate; these constants describe
# what counts as a violation, not how to read the payload.)
# =============================================================================

#: Tool name whose ``command`` string the Bash-family matchers (R1/R2/R4)
#: inspect.
_BASH_TOOL = 'Bash'

#: Tool names whose ``file_path`` the R3 generated-executor matcher inspects.
_FILE_EDIT_TOOLS = ('Edit', 'Write')

#: Generated executor path R3 forbids editing. Matched on the path tail so an
#: absolute or worktree-relative path both trip the rule.
_GENERATED_EXECUTOR_TAIL = '.plan/execute-script.py'

#: R1 — the view an individual family's marker is tested against, named because
#: the two marker classes are neutralized by DIFFERENT quoting. A shell OPERATOR
#: is inert inside single AND double quotes, so it is tested against the fully
#: masked ``operator_view``. A command SUBSTITUTION is literal inside single
#: quotes but still LIVE inside double quotes (``echo "$(rm -rf /)"`` really does
#: substitute), so it is tested against ``substitution_view``, which masks
#: single-quoted spans only. See :func:`_quote_masked_views`.
_R1_OPERATOR_VIEW = 'operator'
_R1_SUBSTITUTION_VIEW = 'substitution'

#: R1 — the two shell quote characters whose spans mask their contents.
_R1_QUOTE_CHARS = ("'", '"')

#: R1 — the inert character every masked character is rewritten to. It must
#: carry no meaning for any R1 check: it is not a shell metacharacter, not a
#: newline, not whitespace (so it cannot manufacture the word boundary the loop
#: or leading-assignment patterns look for), and not ``=``.
_R1_QUOTED_PLACEHOLDER = 'Q'

#: R1 — loop-keyword pattern (``for`` / ``while`` as a leading shell keyword).
_R1_LOOP_RE = re.compile(r'(?:^|[;&|]|\bdo\b)\s*(?:for|while)\b')

#: R1 — leading ``VAR=val cmd`` inline env-var assignment (an assignment token
#: followed by whitespace and a command word).
_R1_LEADING_ASSIGNMENT_RE = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*=\S*\s+\S')


def _r1_contains(marker: str) -> Callable[[str], bool]:
    """Return a predicate testing whether *marker* appears in a masked view."""
    return lambda view: marker in view


def _r1_matches(pattern: re.Pattern[str]) -> Callable[[str], bool]:
    """Return a predicate testing whether *pattern* is found in a masked view."""
    return lambda view: pattern.search(view) is not None


#: R1 — THE authoritative family registry: one ``(name, view, predicate)`` entry
#: per marker family the rule recognises. :func:`_match_r1_shell_construct`
#: ITERATES this tuple and does nothing else, so the registry is the rule's
#: single population rather than a parallel description of it. That is what lets
#: the test suite derive its control-pair population from here and fail loudly on
#: a family that has no control pair — a registry the matcher merely sat beside
#: would be one more hand-maintained mirror, which is exactly the drift this
#: shape exists to prevent.
#:
#: Order is irrelevant to behaviour: every family yields the same ``_R1_REASON``,
#: so the first match short-circuits with a verdict no ordering can change.
_R1_FAMILIES: tuple[tuple[str, str, Callable[[str], bool]], ...] = (
    ('and_chain', _R1_OPERATOR_VIEW, _r1_contains('&&')),
    ('semicolon', _R1_OPERATOR_VIEW, _r1_contains(';')),
    ('pipe', _R1_OPERATOR_VIEW, _r1_contains('|')),
    ('background', _R1_OPERATOR_VIEW, _r1_contains('&')),
    ('newline', _R1_OPERATOR_VIEW, _r1_contains('\n')),
    ('substitution', _R1_SUBSTITUTION_VIEW, _r1_contains('$(')),
    ('backtick', _R1_SUBSTITUTION_VIEW, _r1_contains('`')),
    ('loop_keyword', _R1_OPERATOR_VIEW, _r1_matches(_R1_LOOP_RE)),
    ('leading_assignment', _R1_OPERATOR_VIEW, _r1_matches(_R1_LEADING_ASSIGNMENT_RE)),
)

#: R2 — Bash file-operation programs that have dedicated Read/Glob/Grep tools.
#: Read on the UN-STRIPPED program, so ``sudo cat foo`` names ``sudo`` and is not
#: an R2 file-op (R2's wrapper boundary is pinned by
#: ``test_r1_r2_r4_matchers_do_not_strip_wrappers``).
_R2_FILE_OPS = ('cat', 'grep', 'head', 'tail', 'find', 'ls')

#: R2 — SHELL SPAWNS. A shell that re-executes a string can carry any bypass
#: (``bash -c "python3 -c ..."``), so this class is refused exactly as the
#: OpenCode guard's mutation class refuses ``sh`` / ``bash`` / ``source``. Unlike
#: the file-op class, a spawn is ALSO read after R5 wrapper stripping, so
#: ``env bash -c "python3 -c ..."`` cannot hide behind a wrapper.
_R2_SHELL_SPAWNS = ('sh', 'bash', 'source')

#: R2 — ``git`` global options that consume a SEPARATE following token as their
#: value. Only the detached spellings need naming: ``_git_subcommand`` skips any
#: other option structurally (see its docstring), but a detached value option is
#: the one shape where the token AFTER the option must also be stepped over so
#: the value is never mistaken for the subcommand.
_R2_GIT_VALUE_OPTIONS = (
    '-C',
    '-c',
    '--git-dir',
    '--work-tree',
    '--namespace',
    '--super-prefix',
    '--config-env',
    '--exec-path',
    '--attr-source',
)

#: R4 — hard-coded build invocations that must be resolved via the architecture
#: API. ``./pw`` is matched as a literal; ``mvn`` / ``npm`` / ``gradle`` / ``uv``
#: as bare leading programs or path-prefixed executables (e.g.
#: ``/usr/local/bin/mvn``). ``uv`` joins the set so the hook covers
#: ``uv run python -c ...`` exactly as the OpenCode guard's ``BARE_BUILD_TOOLS``
#: does.
_R4_BUILD_PROGRAMS = ('mvn', 'npm', 'gradle', 'uv')

#: Per-rule one-line redirect reasons surfaced as ``permissionDecisionReason``.
_R1_REASON = (
    "plan-marshall: one command per Bash call — no UNQUOTED '&&', ';', '&', "
    'newline, for/while, $(...), or leading VAR=val; use separate Bash calls or '
    'dedicated tools. A metacharacter inside a quoted argument is fine.'
)
_R2_REASON = (
    'plan-marshall: use the Read/Glob/Grep tools, not Bash, for file '
    'operations (cat/grep/head/tail/find/ls, sh/bash/source, git grep). For a '
    'content sweep run: architecture search --content --pattern P.'
)
_R3_REASON = (
    'plan-marshall: never edit the generated .plan/execute-script.py — '
    f'regenerate it via {SYNC_HARNESSES_COMMAND} + {STEWARD_COMMAND}.'
)
_R4_REASON = (
    'plan-marshall: never hard-code build commands (./pw, mvn, npm, gradle) — '
    'resolve via plan-marshall:manage-architecture:architecture resolve.'
)
_R5_REASON = (
    'plan-marshall: direct python interpreter calls (python -c, script paths, '
    'python -m) bypass the executor — route builds and checks via '
    'python3 .plan/execute-script.py and .plan state via manage-* verbs or '
    'the Read/Edit/Write tools.'
)
_R6_REASON = (
    'plan-marshall: a raw git commit is refused in phase 6-finalize — commit '
    'through python3 .plan/execute-script.py '
    'plan-marshall:workflow-integration-git:git-workflow commit (the gate-bearing '
    'path), which sanctions an open loop-back fix task, a review-rubric '
    'section-6 record, or a step id of the composed phase-6 manifest.'
)


def _first_word(command: str) -> str:
    """Return the first whitespace-delimited token of *command*, lowercased.

    Best-effort: returns ``""`` when *command* is empty or whitespace-only.
    """
    stripped = command.strip()
    if not stripped:
        return ''
    return stripped.split()[0].lower()


def _program_name(command: str) -> str:
    """Return the normalized executable name from the first command token.

    Strips any leading path component so that ``/bin/cat``, ``/usr/bin/cat``,
    and ``cat`` all resolve to ``"cat"``.  The special ``./pw`` token is
    preserved as-is so the R4 literal check continues to work.
    """
    token = _first_word(command)
    if not token or token == './pw':
        return token
    # Strip path prefix (e.g. /usr/bin/cat -> cat) but keep bare names intact.
    return token.rsplit('/', 1)[-1]


def _bash_command(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """Return the Bash ``command`` string, or ``None`` for a non-Bash call.

    Returns ``None`` when *tool_name* is not ``Bash`` or the ``command`` value is
    absent / not a non-empty string.
    """
    if tool_name != _BASH_TOOL:
        return None
    value = tool_input.get('command')
    if isinstance(value, str) and value:
        return value
    return None


def _quote_masked_views(command: str) -> tuple[str, str] | None:
    """Return ``(operator_view, substitution_view)`` for *command*, or ``None``.

    A shell metacharacter that OPERATES and one that is DATA are the same
    character — only the quoting tells them apart. ``git commit -m "fix: a; b"``
    is one command while ``a ; b`` is two, and a raw substring scan cannot
    distinguish them. Masking the quoted spans first leaves exactly the operative
    characters visible.

    TWO views, because the two R1 marker classes are neutralized by DIFFERENT
    quoting — collapsing them into one view would be wrong in one direction or
    the other:

    * ``operator_view`` masks single- AND double-quoted spans. A shell operator
      (``&&``, ``;``, ``&``, a newline, a loop keyword, a leading assignment)
      is inert inside either quote kind.
    * ``substitution_view`` masks single-quoted spans ONLY. Command substitution
      stays LIVE inside double quotes — ``echo "$(rm -rf /)"`` really does
      substitute — so masking double quotes for ``$(`` and a backtick would open
      exactly the bypass this rule exists to prevent.

    A BACKSLASH ESCAPE is resolved before any quote-state transition, in
    unquoted context and inside a double-quoted span alike (inside a
    single-quoted span bash treats a backslash as an ordinary literal, so the
    escape is not applied there). Handling the escape only inside double quotes
    would be wrong in BOTH directions:

    * A bypass, the load-bearing half. In unquoted context an unresolved
      backslash lets the FOLLOWING quote character change the span state, so
      ``echo \\'a; b\\'`` opens a single-quoted span, masks the ``;`` and closes
      cleanly — yet bash reads the escaped quotes as literal data and the ``;``
      as a live separator, making that TWO commands. Resolving the escape first
      keeps the span state untouched and leaves the ``;`` visible.
    * A false positive. Writing the raw escaped pair into ``substitution_view``
      leaves an escaped marker intact there, so ``echo "\\`date\\`"`` — literal
      data to bash — matched the substitution families and denied. Both
      characters are therefore masked in BOTH views: an escaped character is
      never an operator and never a substitution opener.

    Length and layout are PRESERVED character-for-character, because two R1
    checks depend on structure a token-level view destroys: an unquoted newline
    is a command separator, and ``shlex`` consumes it as ordinary whitespace,
    which would turn the newline check into a permanent pass. That is why the
    span mask is computed here instead of by reusing ``shlex.split`` the way
    :func:`_git_subcommand` does. The escape branch honours the same invariant —
    it consumes two characters and emits two.

    Malformed quoting (a span that never closes) returns ``None``, and the caller
    then scans the RAW command — the same degradation :func:`_git_subcommand`
    applies on ``shlex``'s ``ValueError``. Falling back to the pre-existing
    detection keeps a lexing ambiguity a false positive at worst, never a silent
    bypass.

    Pure and single-pass: one scan of the command, no regex compilation, no
    filesystem access, no subprocess. This runs on every tool call.
    """
    operator_view: list[str] = []
    substitution_view: list[str] = []
    quote: str | None = None
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if quote != "'" and char == '\\' and index + 1 < length:
            # A backslash escapes the next character in UNQUOTED context and
            # inside a double-quoted span alike; only within a single-quoted
            # span is it an ordinary literal, which is what the guard excludes.
            # Resolving the escape BEFORE any quote-state transition is what
            # keeps an escaped quote from opening or closing a span, and both
            # characters are masked in BOTH views because an escaped character
            # is never an operator and never a substitution opener.
            operator_view.append(_R1_QUOTED_PLACEHOLDER * 2)
            substitution_view.append(_R1_QUOTED_PLACEHOLDER * 2)
            index += 2
            continue
        if quote is None:
            span = char if char in _R1_QUOTE_CHARS else None
            quote = span
        else:
            span = quote
            if char == quote:
                quote = None
        operator_view.append(_R1_QUOTED_PLACEHOLDER if span else char)
        substitution_view.append(_R1_QUOTED_PLACEHOLDER if span == "'" else char)
        index += 1
    if quote is not None:
        return None
    return ''.join(operator_view), ''.join(substitution_view)


def _match_r1_shell_construct(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """R1 — Bash command containing an UNQUOTED shell-construct compound marker.

    The family population is ``_R1_FAMILIES`` and this function does nothing but
    iterate it, so that registry is the rule rather than a description of it —
    a family cannot be added to the matcher without appearing in the population
    the tests derive their control pairs from.

    Each family names the view from :func:`_quote_masked_views` in which its own
    marker class is inert when quoted, so a metacharacter confined to a quoted
    argument — a ``;`` in a commit body, an ``&&`` in a log message — is data and
    does not deny the call. Every unquoted compound still denies, and command
    substitution inside DOUBLE quotes still denies too, because it still executes
    there.

    On malformed quoting no mask is available and every family runs against the
    RAW command, preserving the pre-existing detection rather than degrading into
    a bypass.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    views = _quote_masked_views(command)
    operator_view, substitution_view = (command, command) if views is None else views
    view_by_name = {
        _R1_OPERATOR_VIEW: operator_view,
        _R1_SUBSTITUTION_VIEW: substitution_view,
    }
    for _family, view_name, predicate in _R1_FAMILIES:
        if predicate(view_by_name[view_name]):
            return _R1_REASON
    return None


def _git_subcommand(command: str) -> str:
    """Return ``git``'s subcommand token, skipping any global options.

    ``git`` accepts global options BEFORE the subcommand, so the subcommand is
    not reliably ``tokens[1]``. Testing that position directly would be a vacuous
    guard — ``git -C . grep x``, ``git -c k=v grep x`` and ``git --no-pager grep
    x`` all walk straight past it.

    The option walk is STRUCTURAL, not an allowlist: ANY token starting with
    ``-`` is treated as an option and skipped. Recognising only a named set of
    spellings is itself a vacuous guard, because every one of ``git -C. grep x``
    (attached short value), ``git -cvar=val grep x``, ``git -p grep x`` and
    ``git --bare grep x`` is valid ``git`` yet fails a membership test, leaving
    the option token itself returned as the subcommand and the R2 block bypassed.
    Only the DETACHED value-taking options (``_R2_GIT_VALUE_OPTIONS``) need
    naming, since they alone consume a separate FOLLOWING token; attached
    (``-C.``) and inline (``--git-dir=...``) forms are self-contained and skip as
    a single token.

    The split is SHELL-LEXICAL (``shlex``), not whitespace. A detached value
    option can carry a quoted value containing spaces — ``git -C "repo dir"
    grep x`` — and a naive ``str.split()`` tears that value into two tokens, so
    the ``index += 2`` skip lands mid-value and returns ``dir"`` as the
    subcommand, bypassing the R2 block for a real ``git grep``. Lexical
    splitting resolves the quoting first, so the value is one token and the
    skip arithmetic stays true. Malformed quoting (an unbalanced quote makes
    ``shlex`` raise) falls back to the whitespace split rather than returning
    early: the fallback preserves the pre-existing detection for every
    unquoted shape instead of turning a lexer error into a silent bypass.

    Pure token arithmetic after the split: no regex compilation, no filesystem
    access, no subprocess — this runs on every tool call, so the hot path stays
    cheap. Returns ``""`` when the tokens run out before a subcommand appears.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in _R2_GIT_VALUE_OPTIONS:
            index += 2  # the option plus the separate value token it consumes
            continue
        if token.startswith('-'):
            index += 1  # any other option spelling is self-contained
            continue
        return token.lower()
    return ''


def _match_r2_file_ops(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """R2 — Bash command whose program is a file-op with a dedicated tool.

    Covers both the bare file-op programs and ``git grep``, which reads file
    bodies exactly as ``grep`` does and therefore joins the EXISTING R2 family
    rather than opening a new one — the rule family count stays four.
    Non-``grep`` git subcommands are untouched: ``git status``, ``git diff``,
    ``git log`` and friends are not file-ops and must keep working.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    program = _program_name(command)
    if program in _R2_FILE_OPS or program in _R2_SHELL_SPAWNS:
        return _R2_REASON
    # A shell spawn is read a SECOND time after R5 wrapper stripping, so a
    # wrapper prefix (`env bash -c "python3 -c ..."`) cannot hide it. The
    # file-op class keeps its un-stripped read (see ``_R2_FILE_OPS``).
    stripped = _r5_stripped_tokens(command)
    stripped_program = _strip_matched_quotes(stripped[0]).rsplit('/', 1)[-1] if stripped else ''
    if stripped_program in _R2_SHELL_SPAWNS:
        return _R2_REASON
    if program == 'git' and _git_subcommand(command) == 'grep':
        return _R2_REASON
    return None


def _match_r3_generated_executor(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """R3 — Edit/Write whose target path is the generated executor."""
    if tool_name not in _FILE_EDIT_TOOLS:
        return None
    path = tool_input.get('file_path')
    if not isinstance(path, str) or not path:
        return None
    normalized = path.replace('\\', '/')
    if normalized == _GENERATED_EXECUTOR_TAIL or normalized.endswith('/' + _GENERATED_EXECUTOR_TAIL):
        return _R3_REASON
    return None


def _match_r4_hardcoded_build(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """R4 — Bash command invoking ./pw or a bare mvn/npm/gradle/uv.

    The program is read BOTH un-stripped (``./pw`` is matched as a literal) and
    after R5 wrapper stripping, mirroring the OpenCode guard's first-token check
    on its wrapper-stripped ``commandTokens``: ``env uv run python -c ...`` is
    refused here exactly as the guard refuses it.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    first = _first_word(command)
    stripped = _r5_stripped_tokens(command)
    stripped_first = _strip_matched_quotes(stripped[0]) if stripped else ''
    stripped_program = stripped_first.rsplit('/', 1)[-1] if stripped_first else ''
    if (
        first == './pw'
        or stripped_first == './pw'
        or stripped_program == 'pw'
        or _program_name(command) in _R4_BUILD_PROGRAMS
        or stripped_program in _R4_BUILD_PROGRAMS
    ):
        return _R4_REASON
    return None


#: The ONE shared wrapper table both harnesses read — the sibling of
#: ``r5-allowlist.json``. A wrapper is a prefix program whose own invocation RUNS
#: the command that follows it (``env python3 -c x`` still runs the interpreter),
#: so R5 strips it (with its options, option values and inline ``NAME=value``
#: assignments) before the program check. The table declares, per wrapper, the
#: value-consuming options (``values`` for the full token, ``value_letters`` for a
#: letter inside a short cluster such as ``-iu FOO``), the number of leading
#: positional arguments the wrapper consumes (``leading_positionals``), and the
#: options whose value is itself a COMMAND STRING to re-lex (``splice``). It is
#: matched by BASENAME, so ``/usr/bin/env`` strips exactly like ``env``. Neither
#: implementation carries a second literal list: a wrapper added to the data file
#: is stripped on both harnesses and one removed from it is stripped on neither.
_R5_WRAPPER_TABLE_NAME = 'r5-wrappers.json'

#: The wrapper table's location relative to the skill root, resolved exactly like
#: the allow-list's.
_R5_WRAPPER_RELATIVE = ('standards', _R5_WRAPPER_TABLE_NAME)

#: Leading ``NAME=value`` assignment, transparent to the shell.
_R5_ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


def _wrapper_table_path() -> pathlib.Path:
    """Return the path to the shared R5 wrapper table data file.

    Resolved relative to this script's own skill (``standards/`` beside
    ``scripts/``), exactly as a deployed tree carries it — independent of the
    allow-list override seam, so a fixture that redirects the allow-list still
    reads the real wrapper table.
    """
    return pathlib.Path(__file__).resolve().parent.parent.joinpath(*_R5_WRAPPER_RELATIVE)


def _wrapper_table() -> dict[str, Any]:
    """Return the parsed shared wrapper table, or an EMPTY table flagged missing.

    ``missing`` makes :func:`_match_r5_interpreter_call` fail CLOSED: without the
    table no wrapper can be stripped, so a command that names an interpreter
    anywhere is refused rather than admitted through a prefix.

    Read on each call rather than cached, so a test can point the path at a
    fixture table without an invalidation step.
    """
    try:
        data = json.loads(_wrapper_table_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'wrappers': {}, 'find_exec': (), 'missing': True}
    wrappers = data.get('wrappers') if isinstance(data, dict) else None
    if not isinstance(wrappers, dict) or not wrappers:
        return {'wrappers': {}, 'find_exec': (), 'missing': True}
    find_exec = data.get('find_exec_options')
    return {
        'wrappers': wrappers,
        'find_exec': tuple(str(option) for option in find_exec) if isinstance(find_exec, list) else (),
        'missing': False,
    }


def _wrapper_basename(token: str) -> str:
    """Return a wrapper token's program name (quotes and path qualification gone)."""
    return _strip_matched_quotes(token).replace('\\', '/').rsplit('/', 1)[-1]


def _consume_wrapper_option(spec: dict[str, Any], token: str, tokens: list[str], index: int) -> tuple[bool, str, int]:
    """Step over ONE wrapper option, per the shared table.

    Returns ``(is_splice, value, consumed)``: ``consumed`` is how many tokens the
    option takes (1 = the option alone, 2 = the option plus its following value),
    and ``is_splice`` is set when the option's value is a COMMAND STRING that must
    be re-lexed and walked (a shell's ``-c``, ``env -S``, ``script -c``). A short
    CLUSTER (``-iu FOO``) is walked letter by letter, so a value-taking letter is
    honoured wherever it sits in the cluster.
    """
    values = spec.get('values') or []
    value_letters = set(spec.get('value_letters') or [])
    splice_opts = spec.get('splice') or []
    splice_longs = {option for option in splice_opts if option.startswith('--')}
    splice_letters = {
        option[1] for option in splice_opts if len(option) == 2 and option[0] == '-' and not option.startswith('--')
    }
    next_value = tokens[index + 1] if index + 1 < len(tokens) else ''
    if token.startswith('--'):
        base, separator, attached = token.partition('=')
        if base in splice_longs:
            return True, (attached if separator else next_value), (1 if separator else 2)
        if base in values:
            return False, '', (1 if separator else 2)
        return False, '', 1
    letters = token[1:]
    for position, letter in enumerate(letters):
        if letter in splice_letters:
            rest = letters[position + 1 :]
            if rest:
                return True, rest, 1
            return True, next_value, 2
        if letter in value_letters:
            return False, '', (1 if letters[position + 1 :] else 2)
    return False, '', (2 if token in values else 1)


def _r5_stripped_tokens(command: str) -> list[str]:
    """Return shell-lexical tokens of *command* minus R5-transparent prefixes.

    Shell-lexical (``shlex``) like the other R5 helpers, falling back to the
    whitespace split on malformed quoting rather than returning early, then
    walked by :func:`_strip_wrapper_tokens`. A ``find … -exec`` program hidden
    behind a wrapper (``env find . -exec python3 -c x {} +``) is spliced AFTER the
    wrapper walk, so the wrapper prefix cannot hide it.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    stripped = _strip_wrapper_tokens(tokens)
    if stripped and _wrapper_basename(stripped[0]) == 'find':
        table = _wrapper_table()
        for position, token in enumerate(stripped):
            if token in table['find_exec']:
                return _strip_wrapper_tokens(stripped[position + 1 :])
    return stripped


def _spliced_segments(value: str) -> list[str]:
    """Split a spliced COMMAND STRING into shell segments (quote-aware).

    A wrapper's multi-command string (``zsh -c "cd /tmp; python3 -c x"``) must be
    walked segment by segment — the interpreter is behind a ``cd`` and a
    separator inside the string, not at its first word.
    """
    segments: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == '\\' and not in_single:
            current.append(char)
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            current.append(char)
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            current.append(char)
            continue
        if not in_single and not in_double and char in ';&|\n':
            segments.append(''.join(current))
            current = []
            continue
        current.append(char)
    segments.append(''.join(current))
    return [segment.strip() for segment in segments if segment.strip()]


def _is_interpreter_program_token(token: str) -> bool:
    """Whether *token* names an interpreter program (basename, case-insensitive)."""
    return _PYTHON_PROGRAM_RE.match(_wrapper_basename(token).lower()) is not None


def _strip_wrapper_tokens(tokens: list[str]) -> list[str]:
    """Strip leading wrappers/assignments from *tokens* (the R5 prefix walk).

    ``env -S <string>`` and a shell's ``-c <string>`` SPLICE the string back
    through the splitter, because the wrapper runs that string as the command. A
    wrapper's ``leading_positionals`` (timeout's DURATION, flock's lock file,
    chrt's priority, taskset's mask) are consumed before the walked command. A
    ``find … -exec <program>`` invocation is walked from the program after the
    find-exec option, sourced from the same table's ``find_exec_options``.
    """
    table = _wrapper_table()
    if tokens and _wrapper_basename(tokens[0]) == 'find':
        for index, token in enumerate(tokens):
            if token in table['find_exec']:
                return _strip_wrapper_tokens(tokens[index + 1 :])
    wrappers = table['wrappers']
    index = 0
    total = len(tokens)
    while index < total:
        token = tokens[index]
        if _R5_ASSIGNMENT_RE.match(token):
            index += 1
            continue
        spec = wrappers.get(_wrapper_basename(token))
        if not isinstance(spec, dict):
            break
        index += 1
        spliced: str | None = None
        while index < total:
            option = tokens[index]
            if _R5_ASSIGNMENT_RE.match(option):
                index += 1
                continue
            if not (option.startswith('-') and len(option) > 1):
                break
            is_splice, value, consumed = _consume_wrapper_option(spec, option, tokens, index)
            index += consumed
            if is_splice:
                spliced = value
                break
        if spliced is not None:
            for segment in _spliced_segments(spliced):
                try:
                    segment_tokens = shlex.split(segment)
                except ValueError:
                    segment_tokens = segment.split()
                walked = _strip_wrapper_tokens([*segment_tokens, *tokens[index:]])
                if walked and _is_interpreter_program_token(walked[0]):
                    return walked
            segments = _spliced_segments(spliced)
            first = segments[0] if segments else spliced
            try:
                first_tokens = shlex.split(first)
            except ValueError:
                first_tokens = first.split()
            return _strip_wrapper_tokens([*first_tokens, *tokens[index:]])
        if spec.get('splice_positional') and index < total:
            # `watch '<command>'` / `parallel '<command>'` run their first
            # positional as a shell command, so it is spliced and walked.
            value = _strip_matched_quotes(tokens[index])
            for segment in _spliced_segments(value):
                try:
                    segment_tokens = shlex.split(segment)
                except ValueError:
                    segment_tokens = segment.split()
                walked = _strip_wrapper_tokens([*segment_tokens, *tokens[index + 1 :]])
                if walked and _is_interpreter_program_token(walked[0]):
                    return walked
            segments = _spliced_segments(value)
            first = segments[0] if segments else value
            try:
                first_tokens = shlex.split(first)
            except ValueError:
                first_tokens = first.split()
            return _strip_wrapper_tokens([*first_tokens, *tokens[index + 1 :]])
        remaining = int(spec.get('leading_positionals') or 0)
        while remaining > 0 and index < total and not tokens[index].startswith('-'):
            index += 1
            remaining -= 1
    return tokens[index:]


def _is_executor_permit(command: str, root: str | None, cwd: str | None) -> bool:
    """Return True when *command* is the exempt executor invocation.

    Compared after R5 wrapper stripping, so a wrapper-prefixed executor call
    (``env python3 .plan/execute-script.py ...``) stays exempt exactly as the
    guard exempts it. The RELATIVE form ``.plan/execute-script.py`` is the
    canonical documented invocation and is admitted only when the command's
    EFFECTIVE working directory IS the repository root: a leading ``cd``, an
    ``env -C`` / ``--chdir`` directory change and the payload ``cwd`` are
    resolved first, so the same relative path run from anywhere else is refused.
    (``git -C`` is not a shell directory change: it moves git's own working
    directory for that one invocation, never the directory a following program
    runs in.) An ABSOLUTE form is admitted only when it RESOLVES to
    ``{repository root}/.plan/execute-script.py`` (relative to the shell *cwd*
    when needed), so ``python3 /tmp/x/.plan/execute-script.py`` is refused —
    never admitted by suffix. Used only by the R5 matcher.
    """
    stripped = _r5_stripped_tokens(command)
    if len(stripped) < 2:
        return False
    program = _strip_matched_quotes(stripped[0]).rsplit('/', 1)[-1].lower()
    if program != 'python3':
        return False
    second = _strip_matched_quotes(stripped[1]).replace('\\', '/')
    if second == '.plan/execute-script.py':
        effective = _effective_cwd(command, cwd or root)
        if not effective or not root:
            return False
        return _real_path(effective) == _real_path(root)
    if not second.startswith('/'):
        return False
    repo_root = (root or cwd or '').replace('\\', '/').rstrip('/')
    if not repo_root:
        return False
    return posixpath.normpath(second) == repo_root + '/.plan/execute-script.py'


def _real_path(value: str) -> str:
    """Return *value* as a realpath, falling back to its normalized form."""
    try:
        return str(pathlib.Path(value).resolve())
    except OSError:
        return posixpath.normpath(value)


def _effective_cwd(command: str, base: str | None) -> str:
    """The command's EFFECTIVE working directory.

    The shell's own cwd with a leading ``cd`` and every ``env -C`` / ``--chdir`` /
    ``sudo -D`` / ``--directory`` directory change applied in order. The wrapper
    chain is walked with the SHARED table, so a directory change is found wherever
    it sits among a wrapper's options (``env -u FOO -C /tmp/x …``,
    ``sudo -u bob -D /tmp/x …``). Empty when no base is known, which no caller
    treats as "the repository root".
    """
    if not base:
        return ''
    current = base.replace('\\', '/').rstrip('/')
    if not current.startswith('/'):
        return ''
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    index = 0
    while index < len(tokens):
        token = _strip_matched_quotes(tokens[index])
        if _R5_ASSIGNMENT_RE.match(token):
            index += 1
            continue
        if token == 'cd':
            value = _strip_matched_quotes(tokens[index + 1]) if index + 1 < len(tokens) else ''
            if not value:
                return ''
            current = _resolve_against(current, value)
            index += 2
            continue
        wrapper = _wrapper_basename(token)
        spec = _wrapper_table()['wrappers'].get(wrapper)
        if not isinstance(spec, dict):
            break
        index += 1
        while index < len(tokens):
            option = _strip_matched_quotes(tokens[index])
            if _R5_ASSIGNMENT_RE.match(option):
                index += 1
                continue
            if not (option.startswith('-') and len(option) > 1):
                break
            is_directory_option = (
                option in ('-C', '--chdir')
                or option.startswith('--chdir=')
                or (wrapper == 'sudo' and (option in ('-D', '--directory') or option.startswith('--directory=')))
                or (wrapper == 'env' and option.startswith('-C') and len(option) > 2)
            )
            if is_directory_option:
                value = option.split('=', 1)[1] if '=' in option else ''
                if not value and option.startswith('-C') and len(option) > 2 and not option.startswith('--'):
                    value = option[2:]
                if not value:
                    value = _strip_matched_quotes(tokens[index + 1]) if index + 1 < len(tokens) else ''
                if value:
                    current = _resolve_against(current, value)
            _is_splice, _value, consumed = _consume_wrapper_option(spec, option, tokens, index)
            index += consumed
            if _is_splice:
                break
    return current


def _resolve_against(base: str, value: str) -> str:
    """Resolve *value* against *base* into a normalized posix path."""
    if value.startswith('/'):
        return posixpath.normpath(value)
    return posixpath.normpath(f'{base}/{value}')


#: Interpreter program name, including a versioned spelling (``python3.12``).
#: Matched after lowercasing, mirroring the guard's ``isPythonInterpreter``.
_PYTHON_PROGRAM_RE = re.compile(r'^(python|pypy)(\d+(\.\d+)*)?$')

#: The shared allow-list data file both harnesses read. Resolved relative to the
#: script so the deployed Claude hook finds the skill's ``standards/`` directory.
_R5_ALLOWLIST_RELATIVE = ('standards', 'r5-allowlist.json')

#: The base allow-list used when no data file can be read — deliberately narrow.
_R5_ALLOWLIST_BASE = ('marketplace/targets/sync.py',)


def _r5_allowlist_path() -> pathlib.Path:
    """Return the path to the shared R5 allow-list data file."""
    return pathlib.Path(__file__).resolve().parent.parent.joinpath(*_R5_ALLOWLIST_RELATIVE)


def _r5_allowlist_entries() -> tuple[str, ...]:
    """Return the allow-list entries, falling back to the base table when absent.

    Read on each call rather than cached, so a test can point the path at a
    missing file and observe the base-table fallback without an invalidation
    step. The file is read only for an interpreter invocation, never on the
    hot path for other tools.
    """
    path = pathlib.Path(_r5_allowlist_path())
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return _R5_ALLOWLIST_BASE
    entries = data.get('entries') if isinstance(data, dict) else None
    if isinstance(entries, dict) and entries:
        return tuple(str(key) for key in entries)
    if isinstance(entries, list) and entries:
        return tuple(str(entry) for entry in entries)
    return _R5_ALLOWLIST_BASE


#: The repository-relative marker that says "this project IS the plan-marshall
#: source repository" — its project-local copy of the shared allow-list data
#: file. In this repository R5 binds in EVERY session; in a consumer repository
#: it binds only inside a plan context.
_R5_REPO_MARKER = 'marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json'


def _r5_allowlist_bundle_entries() -> tuple[str, ...]:
    """Return the BUNDLE-RELATIVE allow-list entries, or an empty tuple.

    These are the nested-layout spellings (``skills/{skill}/scripts/x.py``) whose
    DEPLOYED form — ``{deployed bundle root}/{entry}`` — R5 admits. Kept in the
    same one data file so the guard and the hook read one population.
    """
    path = pathlib.Path(_r5_allowlist_path())
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ()
    entries = data.get('bundle_entries') if isinstance(data, dict) else None
    if isinstance(entries, dict) and entries:
        return tuple(str(key) for key in entries)
    return ()


def _repo_root_from_hook_location() -> str | None:
    """The plan-marshall repository root the running hook belongs to, or ``None``.

    A hook dispatched from the repository's own source tree carries the
    ``.../marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/``
    ancestor chain; a hook deployed in a plugin cache or a consumer install does
    not. Used ONLY to answer "is this repository" when the payload names no
    project directory of its own.
    """
    suffix = ('marketplace', 'bundles', 'plan-marshall', 'skills', 'platform-runtime', 'scripts')
    parts = pathlib.Path(__file__).resolve().parts
    for start in range(len(parts) - len(suffix), -1, -1):
        if parts[start : start + len(suffix)] == suffix:
            return str(pathlib.Path(*parts[:start]))
    return None


def _is_this_repository(payload: dict[str, Any]) -> bool:
    """Whether this call runs against the plan-marshall source repository.

    The SESSION's project directory (``CLAUDE_PROJECT_DIR``, falling back to the
    payload ``cwd``) decides when the payload names one; the running hook's own
    location is only the FALLBACK for a payload that names no project directory.
    A consumer session on a machine that also carries the source tree is judged
    by its own project directory, never by where the hook file happens to live —
    while a payload with no project directory at all (a bare test/probe call)
    still inherits the location's stricter scope.
    """
    project = _allow_list_root(payload)
    roots = (project,) if project else (_repo_root_from_hook_location(),)
    for root in roots:
        if root and pathlib.Path(root).joinpath(*_R5_REPO_MARKER.split('/')).is_file():
            return True
    return False


def _deployed_bundle_roots() -> tuple[str, ...]:
    """The deployed bundle-cache roots, from the SHARED layout resolver.

    The roots are not a hard-coded list here: they come from
    ``deployed_layout.all_bundle_cache_roots`` — the same shared module the
    ``platform_runtime layout bundle-cache-root`` verb delegates to, reading the
    same ``standards/deployed-layout.json`` data file. A machine may carry more
    than one harness, so the union across targets is used. Every root is
    realpath'd, so a symlinked tree is never trusted lexically, and a root the
    resolver does not name is never a candidate. When the shared module is
    unreachable the data file is read directly (same data, no second list); when
    neither can be read the result is EMPTY, which refuses every deployed script
    rather than trusting an unknown tree.
    """
    standards_dir = _standards_dir()
    try:
        import deployed_layout
    except ImportError:
        return _layout_roots_from_data()
    try:
        return tuple(
            str(pathlib.Path(root).resolve()) for root in deployed_layout.all_bundle_cache_roots(standards_dir)
        )
    except Exception:
        return ()


def _layout_roots_from_data() -> tuple[str, ...]:
    """Expand the shared layout data file without the shared module (fallback)."""
    targets = _load_layout_data().get('targets')
    if not isinstance(targets, dict):
        return ()
    roots: list[str] = []
    for templates in targets.values():
        for template in templates if isinstance(templates, list) else []:
            if not isinstance(template, dict):
                continue
            append = str(template.get('append') or '')
            home = os.environ.get('HOME') or str(pathlib.Path.home())
            if 'env' in template:
                base = os.environ.get(str(template['env']), '')
            elif 'xdg' in template:
                base = os.environ.get('XDG_CONFIG_HOME') or str(pathlib.Path(home) / '.config')
            elif 'home' in template:
                base = home
            else:
                continue
            if not base:
                continue
            root = str(pathlib.Path(base).joinpath(*append.split('/'))) if append else str(pathlib.Path(base))
            root = str(pathlib.Path(root).resolve())
            if root not in roots:
                roots.append(root)
    return tuple(roots)


def _standards_dir() -> pathlib.Path:
    """The skill's ``standards/`` directory — where the shared data files live."""
    return pathlib.Path(__file__).resolve().parent.parent / 'standards'


#: The deployed-layout data file the resolver and both guards read (the
#: allow-list's sibling).
_LAYOUT_DATA_NAME = 'deployed-layout.json'


def _bundle_entry_candidates(entry: str, roots: tuple[str, ...]) -> list[str]:
    """Every absolute path a bundle-relative *entry* can be deployed at.

    The nested shape is ``{root}/plan-marshall/{version}/{entry}`` for the
    resolver's VERSION directory — the newest sibling carrying the bundle marker,
    never an arbitrary directory under the bundle — plus the unversioned
    ``{root}/plan-marshall/{entry}``; the flat shape reconstructs the skill's
    dash-namespaced directory name as ``{root}/plan-marshall-{skill}/{rest}``.
    The three layout spellings come from the shared ``deployed-layout.json``.
    """
    parts = entry.split('/')
    if len(parts) < 2 or parts[0] != 'skills':
        return []
    skill = parts[1]
    rest = parts[2:]
    flat_prefix, nested_dir, version_marker = _bundle_layout_spellings()
    flat_name = f'{flat_prefix}{skill}'
    candidates: list[str] = []
    for root in roots:
        base = pathlib.Path(root.replace('\\', '/'))
        candidates.append(str(base.joinpath(flat_name, *rest)))
        nested = base / nested_dir
        candidates.append(str(nested.joinpath(*entry.split('/'))))
        version_dir = _newest_version_dir(nested, version_marker, entry)
        if version_dir is not None:
            candidates.append(str(version_dir.joinpath(*entry.split('/'))))
    return candidates


def _bundle_layout_spellings() -> tuple[str, str, str]:
    """``(flat_skill_prefix, nested_bundle_dir, version_marker)`` from the shared data."""
    data = _load_layout_data()
    return (
        str(data.get('flat_skill_prefix') or 'plan-marshall-'),
        str(data.get('nested_bundle_dir') or 'plan-marshall'),
        str(data.get('version_marker') or '.claude-plugin/plugin.json'),
    )


def _load_layout_data() -> dict[str, Any]:
    """Return the shared deployed-layout data file, or ``{}`` when unreadable."""
    try:
        data = json.loads((_standards_dir() / _LAYOUT_DATA_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _newest_version_dir(nested: pathlib.Path, marker: str, entry: str) -> pathlib.Path | None:
    """The resolver's VERSION directory for *entry*, or ``None``.

    Delegates to the SHARED ``deployed_layout.newest_version_dir`` — the same
    newest-marker-carrying-directory-that-contains-the-entry rule
    ``bootstrap_plugin.resolve_bundle_path`` applies — so the hook, the resolver
    and the guard select one version, not three. Falls back to an equivalent
    local selection only when the shared module is unreachable.
    """
    try:
        import deployed_layout
    except ImportError:
        deployed_layout = None  # type: ignore[assignment]
    if deployed_layout is not None:
        return deployed_layout.newest_version_dir(nested, marker, entry)
    if not nested.is_dir():
        return None
    candidates = [
        child
        for child in nested.iterdir()
        if child.is_dir() and (child / marker).is_file() and (child / entry).exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda child: _version_sort_key(child.name))


def _version_sort_key(name: str) -> tuple[tuple[int, int | str], ...]:
    """Numeric-segment version ordering (``1.0.10`` after ``1.0.9``)."""
    key: list[tuple[int, int | str]] = []
    for part in name.replace('-', '.').split('.'):
        key.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(key)


def _resolved_script_path(raw: str, root: str | None, cwd: str | None) -> str:
    """Resolve a script token to its absolute posix path, or ``''``.

    A relative token is joined with the shell *cwd* (falling back to the project
    *root*), so the deployed-form comparison sees the same absolute path the
    shell would execute.
    """
    token = _strip_matched_quotes(raw).replace('\\', '/')
    if not token:
        return ''
    if token.startswith('/'):
        return posixpath.normpath(token)
    base = (cwd or root or '').replace('\\', '/').rstrip('/')
    if not base.startswith('/'):
        return ''
    return posixpath.normpath(f'{base}/{token}')


def _is_deployed_allow_listed(absolute_path: str, entries: tuple[str, ...], roots: tuple[str, ...]) -> bool:
    """Whether *absolute_path* is a deployed bundle script on the bundle allow-list.

    Compared after ``realpath`` on BOTH sides: a symlink pointing out of a
    deployed root resolves elsewhere and is refused, and a same-named script under
    a NON-deployed directory never matches.
    """
    if not absolute_path or not absolute_path.startswith('/'):
        return False
    try:
        normalized = str(pathlib.Path(absolute_path).resolve())
    except OSError:
        return False
    # The SCRIPT is realpath'd; every candidate is built lexically from an
    # already-realpath'd root. A symlink pointing out of a deployed root
    # therefore resolves to its target and never equals the expected deployed
    # path, while a same-named script under a non-deployed directory never
    # matches at all.
    for entry in entries:
        for candidate in _bundle_entry_candidates(entry, roots):
            if posixpath.normpath(candidate) == normalized:
                return True
    return False


def _repo_relative_path(raw: str, root: str | None, cwd: str | None = None) -> str | None:
    """Resolve *raw* to its repository-relative path, or ``None`` when outside.

    A RELATIVE token is joined with *cwd* (the shell's working directory) first,
    so a token that would execute a copy OUTSIDE the repository — e.g. a
    same-named script under the shell's cwd — resolves outside *root* and is
    refused. The joined (or absolute) token is then made relative to *root* and
    refused when it does not lie under it. The result is matched EXACTLY against
    an allow-list entry, so a basename — or a copy of an allow-listed script
    outside the repository — never matches. Mirrors the guard's
    ``repoRelativePath``.
    """
    token = _strip_matched_quotes(raw).replace('\\', '/')
    if not token:
        return None
    if not token.startswith('/'):
        base = (cwd or '').replace('\\', '/').rstrip('/')
        if base:
            token = posixpath.normpath(f'{base}/{token}')
    normalized_root = (root or '').replace('\\', '/').rstrip('/')
    if token.startswith('/'):
        if not normalized_root:
            return None
        prefix = normalized_root + '/'
        if not token.startswith(prefix):
            return None
        token = token[len(prefix) :]
    parts: list[str] = []
    for segment in token.split('/'):
        if segment in ('', '.'):
            continue
        if segment == '..':
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(segment)
    return '/'.join(parts) if parts else None


def _allow_list_root(payload: dict[str, Any]) -> str | None:
    """The repository root the allow-list resolves against.

    ``CLAUDE_PROJECT_DIR`` pins the session's project directory independently of
    the shell's working directory, so a command cannot move the root by running
    from elsewhere; the payload ``cwd`` is the fallback.
    """
    return os.environ.get('CLAUDE_PROJECT_DIR') or gate.cwd(payload)


def _is_allow_listed(command: str, root: str | None, cwd: str | None) -> bool:
    """Whether *command*'s second stripped token resolves to an allow-list entry.

    Matched EXACTLY on the token's repository-relative path, resolved against the
    repository root *root* (the relative token joined with the shell *cwd* first).
    Never a basename and never a suffix: a copy of an allow-listed script outside
    the repository resolves to ``None`` and is refused. Mirrors the guard's
    ``isAllowListed``.
    """
    stripped = _r5_stripped_tokens(command)
    if len(stripped) < 2:
        return False
    relative = _repo_relative_path(stripped[1], root, cwd)
    if relative is None:
        return False
    return relative in _r5_allowlist_entries()


def _second_token(command: str) -> str:
    """Return the second shell-lexical token of *command*, or empty.

    Compared after R5 wrapper stripping, so the token after the real program
    is returned even when wrappers prefix the invocation. Used only by the
    R5 matcher.
    """
    stripped = _r5_stripped_tokens(command)
    if len(stripped) < 2:
        return ''
    return stripped[1]


def _strip_matched_quotes(token: str) -> str:
    """Strip one pair of matched surrounding quotes from *token*.

    Mirrors the guard's ``normalizeToken`` quote handling so a quote-wrapped
    interpreter (``"python3" -c ...``) is judged the same on both harnesses.
    Used only by the R5 matcher — the shared ``_program_name`` keeps its
    existing callers' behavior.
    """
    s = token.strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s


#: Single-letter python flags that consume a value. Only ``c`` and ``m``
#: execute code; ``W`` and ``X`` take values but do not. A short-flag cluster
#: (``-uc``, ``-Wc``) is judged by its FIRST value-taking flag — ``-uc``
#: refuses because that flag is ``c``, ``-Wc`` passes this helper because its
#: first value-taking flag is ``W``. Used only by the R5 matcher.
_R5_VALUE_TAKING_SINGLE = frozenset({'c', 'm', 'W', 'X'})


def _is_c_m_cluster(text: str) -> bool:
    """Whether *text* is a short-flag cluster executing via ``c`` or ``m``.

    Covers the attached forms (``-cCODE``, ``-mMODULE``) and combined short
    flags (``-uc``) the exact-token check misses: a single-dash token whose
    first value-taking flag is ``c`` or ``m``. Long options (``--`` prefix),
    the bare ``-`` and flag-only tails return False. Used only by R5.
    """
    if not text.startswith('-') or text.startswith('--'):
        return False
    if len(text) < 2:
        return False
    for ch in text[1:]:
        if ch in _R5_VALUE_TAKING_SINGLE:
            return ch in ('c', 'm')
    return False


def _match_r5_interpreter_call(
    tool_name: str | None,
    tool_input: dict[str, Any],
    root: str | None = None,
    cwd: str | None = None,
) -> str | None:
    """R5 — direct python interpreter call bypassing the executor.

    The program check runs on the wrapper-stripped tokens (``command`` /
    ``env`` / ``sudo`` prefixes and ``NAME=value`` assignments removed), so a
    wrapper-prefixed interpreter call is judged the same as the bare form —
    the same stripping the guard applies before its own first-token checks.
    An interpreter option in second position (``-u``, ``-W``, ``-X``,
    ``-B``, ``-E``, ``-I``, ``--``, bare ``-``) does not hide what follows:
    every later token is scanned with the same fail-closed rule. R1 matches
    against the unstripped command; R2's shell-spawn class and R4's build class
    also read the stripped program, so a wrapper cannot hide a shell spawn or a
    build tool from them. *root* is the
    repository root the allow-list match resolves against (the payload ``cwd``).
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    if _wrapper_table()['missing']:
        # Fail CLOSED: without the shared wrapper table no wrapper can be
        # stripped, so refuse any command that names an interpreter anywhere.
        try:
            raw = shlex.split(command)
        except ValueError:
            raw = command.split()
        if any(_PYTHON_PROGRAM_RE.match(_wrapper_basename(token).lower()) for token in raw):
            return _R5_REASON
    if _is_executor_permit(command, root, cwd):
        return None
    stripped = _r5_stripped_tokens(command)
    first = stripped[0].strip().lower() if stripped else ''
    program = _strip_matched_quotes(first.rsplit('/', 1)[-1] if first else '')
    if not _PYTHON_PROGRAM_RE.match(program):
        return None
    second = _strip_matched_quotes(_second_token(command).strip())
    if not second:
        return None
    if _is_allow_listed(command, root, cwd):
        return None
    if _is_deployed_allow_listed(
        _resolved_script_path(_second_token(command), root, cwd),
        _r5_allowlist_bundle_entries(),
        _deployed_bundle_roots(),
    ):
        return None
    if second in ('-c', '-m'):
        return _R5_REASON
    if _is_c_m_cluster(second):
        return _R5_REASON
    if _has_flag_prefixed_bypass(stripped):
        return _R5_REASON
    # A bare `-` reads the program from STDIN, and a `-<`/`->` token is a
    # redirection into it — all bypass the executor exactly as `-c` does.
    if second == '-' or second.startswith('-<') or second.startswith('->'):
        return _R5_REASON
    if second.startswith('-'):
        return None
    return _R5_REASON


def _has_flag_prefixed_bypass(stripped: list[str]) -> bool:
    """Whether a token past the interpreter flag hides a bypass.

    Mirrors the guard's flag-prefix scan over the wrapper-stripped tokens:
    any ``-c``, ``-m``, lone ``-``/``--``, or non-flag token past the
    second position is a bypass. Flag-only tails and the bare interpreter
    still pass. Used only by the R5 matcher.
    """
    for token in stripped[2:]:
        text = _strip_matched_quotes(token.strip())
        if not text:
            continue
        if text in ('-c', '-m', '-', '--'):
            return True
        if text.startswith('-<') or text.startswith('->'):
            return True
        if _is_c_m_cluster(text):
            return True
        if not text.startswith('-'):
            return True
    return False


#: Phase the raw-commit rule guards, mirroring git-workflow's
#: ``_SOURCE_COMMIT_GATE_PHASE``. Outside it a raw ``git commit`` is untouched.
_SOURCE_COMMIT_GATE_PHASE = '6-finalize'


def _worktree_root_from_path(candidate: str | None) -> tuple[pathlib.Path, str] | None:
    """Return ``(worktree_root, plan_id)`` a path names, or ``None``.

    A plan worktree path carries ``.../.plan/local/worktrees/{plan_id}``; the
    plan id is the segment right after ``worktrees`` and the ROOT is the path
    prefix through that segment — so a path in a SUBDIRECTORY of the worktree
    still yields the worktree root. When a path carries more than one such
    segment, the INNERMOST (last) names the plan.
    """
    if not candidate:
        return None
    normalized = candidate.replace('\\', '/')
    marker = '/.plan/local/worktrees/'
    at = normalized.rfind(marker)
    if at == -1:
        return None
    plan_id = normalized[at + len(marker) :].split('/', 1)[0]
    if not plan_id:
        return None
    return pathlib.Path(normalized[: at + len(marker) + len(plan_id)]), plan_id


def _plan_id_from_worktree_path(candidate: str | None) -> str:
    """Return the plan id a path names, or ``""``."""
    info = _worktree_root_from_path(candidate)
    return '' if info is None else info[1]


def _main_anchored_status_path(plan_id: str) -> pathlib.Path | None:
    """Resolve ``plans/{plan_id}/status.json`` MAIN-ANCHORED, or ``None``.

    Uses the sanctioned ``marketplace_paths.resolve_main_anchored_path`` — the
    SAME resolver the other ``git-workflow`` verbs use. The hook is dispatched
    through ``.plan/execute-script.py`` (see
    ``claude_runtime._ENFORCEMENT_HOOK_COMMAND``), so the executor's PYTHONPATH
    already covers the sibling skill's scripts directory and the import needs no
    bootstrap. ``None`` when no main checkout resolves, so R6 does not fire.
    """
    try:
        import marketplace_paths
    except ImportError:
        return None
    try:
        return marketplace_paths.resolve_main_anchored_path(f'plans/{plan_id}/status.json')
    except RuntimeError:
        return None


class _GitCommitInfo(NamedTuple):
    """What a ``git commit`` command says about the plan it is aimed at.

    ``cwd_target`` is git's composed ``-C`` target, ``work_tree`` and ``git_dir``
    are the ``--work-tree`` / ``--git-dir`` (or ``GIT_WORK_TREE`` / ``GIT_DIR``)
    values, and ``unresolvable`` is set when one of them cannot be resolved (an
    unexpanded shell variable in a `-C` target) or when a subcommand alias cannot
    be turned into a plain subcommand — both refuse fail-closed.
    """

    is_commit: bool
    cwd_target: str | None
    work_tree: str | None
    git_dir: str | None
    unresolvable: bool


#: A directory value that still carries a shell expansion is UNRESOLVABLE: the
#: guard cannot know where the commit would land, so R6 refuses fail-closed.
_UNRESOLVABLE_DIR_RE = re.compile(r'[$`]')


def _is_unresolvable_dir(value: str | None) -> bool:
    """Whether a directory value still carries an unexpanded shell expansion."""
    if not value:
        return False
    return _UNRESOLVABLE_DIR_RE.search(value) is not None


def _plan_id_from_git_dir(value: str) -> str:
    """The plan id a git admin directory names (``.git/worktrees/{plan}``), or ``''``."""
    normalized = value.replace('\\', '/').rstrip('/')
    marker = '/worktrees/'
    at = normalized.rfind(marker)
    if at == -1:
        return ''
    if normalized.endswith('/worktrees'):
        return ''
    return normalized[at + len(marker) :].split('/')[0]


def _plan_phase(payload: dict[str, Any], commit_info: _GitCommitInfo | None = None) -> str | None:
    """Read the enclosing plan's phase from its own ``status.json``.

    The plan is NAMED, in priority order, by the ``--work-tree`` value, then the
    composed ``git -C`` target (the persona-mandated ``git -C {WORKTREE} commit``
    form, resolved against the shell cwd), then the plan a ``--git-dir`` /
    ``GIT_DIR`` admin directory points at (``.git/worktrees/{plan}``), then the
    payload ``cwd``, then the project root — never "the first plan found". The
    record is the WORKTREE-RESIDENT one first — the live one during phase 5+,
    where ``prepare_execute`` moves the plan directory into the worktree — then
    the main-anchored live record. ``None`` when no candidate names a plan
    worktree, or no readable record resolves — the raw-commit rule then does not
    fire.
    """
    cwd = gate.cwd(payload)
    project_root = _allow_list_root(payload)
    candidates: list[tuple[pathlib.Path, str]] = []
    if commit_info is not None:
        for value in (commit_info.work_tree, commit_info.cwd_target):
            named = _worktree_root_from_path(_resolve_target_path(value, cwd or project_root))
            if named is not None:
                candidates.append(named)
        if commit_info.git_dir:
            plan_id = _plan_id_from_git_dir(commit_info.git_dir)
            if plan_id and project_root:
                candidates.append((pathlib.Path(project_root) / '.plan' / 'local' / 'worktrees' / plan_id, plan_id))
    for value in (cwd, project_root):
        named = _worktree_root_from_path(value)
        if named is not None:
            candidates.append(named)
    if not candidates:
        return None
    for worktree_root, plan_id in candidates:
        status_candidates: list[pathlib.Path | None] = [
            worktree_root / '.plan' / 'local' / 'plans' / plan_id / 'status.json',
            _main_anchored_status_path(plan_id),
        ]
        for status_path in status_candidates:
            if status_path is None:
                continue
            try:
                data = json.loads(status_path.read_text(encoding='utf-8'))
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                return None
            phase = data.get('current_phase') if isinstance(data, dict) else None
            if isinstance(phase, str) and phase:
                return phase
            return None
    return None


def _resolve_target_path(target: str | None, base: str | None) -> str | None:
    """Resolve a possibly-relative target path against *base*, or ``None``."""
    if not target:
        return None
    normalized = target.replace('\\', '/')
    if normalized.startswith('/'):
        return posixpath.normpath(normalized)
    normalized_base = (base or '').replace('\\', '/').rstrip('/')
    if not normalized_base.startswith('/'):
        return None
    return posixpath.normpath(f'{normalized_base}/{normalized}')


def _git_commit_target(command: str) -> _GitCommitInfo:
    """Return what a ``git commit`` command says about the plan it targets.

    Names the plan from EVERY commit form the harness can express: git's ``-C``
    global option (attached ``-C.`` form included; successive values COMPOSE,
    because git applies each in order against the running target), the
    ``--git-dir`` / ``--work-tree`` options in both detached and ``=`` form, and
    the ``GIT_DIR`` / ``GIT_WORK_TREE`` environment assignments that precede the
    program. A subcommand defined with ``-c alias.NAME=…`` is RESOLVED to its
    body's first word; a shell-expansion body (``!…``) and any directory value
    that still carries ``$``/a backtick are UNRESOLVABLE, so R6 refuses
    fail-closed rather than guessing the plan.
    """
    try:
        raw = shlex.split(command)
    except ValueError:
        raw = command.split()
    stripped = _r5_stripped_tokens(command)
    if not stripped or _strip_matched_quotes(stripped[0]).replace('\\', '/').rsplit('/', 1)[-1].lower() != 'git':
        return _GitCommitInfo(False, None, None, None, False)
    git_at = next(
        (
            position
            for position, token in enumerate(raw)
            if _strip_matched_quotes(token).replace('\\', '/').rsplit('/', 1)[-1].lower() == 'git'
        ),
        None,
    )
    if git_at is None:
        # A wrapper's spliced command string (`watch 'git commit -m x'`) has no raw
        # `git` token: the stripped program IS the git invocation, so walk from it.
        raw = stripped
        git_at = 0
    environment: dict[str, str] = {}
    for token in raw[:git_at]:
        name, separator, value = _strip_matched_quotes(token).partition('=')
        if separator and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            environment[name] = value
    git_dir = environment.get('GIT_DIR')
    work_tree = environment.get('GIT_WORK_TREE')
    unresolvable = _is_unresolvable_dir(git_dir) or _is_unresolvable_dir(work_tree)
    aliases: dict[str, str] = {}
    cwd_target: str | None = None
    index = git_at + 1
    subcommand: str | None = None
    while index < len(raw):
        token = _strip_matched_quotes(raw[index])
        if token == '-C':
            value = _strip_matched_quotes(raw[index + 1]) if index + 1 < len(raw) else ''
            cwd_target = value if cwd_target is None or value.startswith('/') else f'{cwd_target}/{value}'
            unresolvable = unresolvable or _is_unresolvable_dir(value)
            index += 2
            continue
        if token.startswith('-C') and not token.startswith('--') and len(token) > 2:
            value = token[2:]
            cwd_target = value if cwd_target is None or value.startswith('/') else f'{cwd_target}/{value}'
            unresolvable = unresolvable or _is_unresolvable_dir(value)
            index += 1
            continue
        matched_target_option = False
        for prefix in ('--git-dir', '--work-tree'):
            if token == prefix or token.startswith(prefix + '='):
                if '=' in token:
                    value = token.split('=', 1)[1]
                    index += 1
                else:
                    value = _strip_matched_quotes(raw[index + 1]) if index + 1 < len(raw) else ''
                    index += 2
                if prefix == '--git-dir':
                    git_dir = value
                else:
                    work_tree = value
                unresolvable = unresolvable or _is_unresolvable_dir(value)
                matched_target_option = True
                break
        if matched_target_option:
            continue
        if token == '-c' or (token.startswith('-c') and not token.startswith('--')):
            if token == '-c':
                value = _strip_matched_quotes(raw[index + 1]) if index + 1 < len(raw) else ''
                index += 2
            else:
                value = token[2:]
                index += 1
            alias_name, separator, body = value.partition('=')
            if separator and alias_name.startswith('alias.'):
                aliases[alias_name[len('alias.') :]] = body
            continue
        if token.startswith('-'):
            index += 2 if token in _R2_GIT_VALUE_OPTIONS else 1
            continue
        subcommand = token.lower()
        break
    if subcommand is None:
        return _GitCommitInfo(False, cwd_target, work_tree, git_dir, unresolvable)
    if subcommand in aliases:
        body = aliases[subcommand]
        if body.startswith('!') or _is_unresolvable_dir(body):
            # The alias body cannot be reduced to a plain subcommand, so whether
            # this is a commit is unknown: refuse fail-closed.
            return _GitCommitInfo(True, cwd_target, work_tree, git_dir, True)
        else:
            try:
                parts = shlex.split(body)
            except ValueError:
                parts = body.split()
            subcommand = parts[0].lower() if parts else ''
    return _GitCommitInfo(subcommand == 'commit', cwd_target, work_tree, git_dir, unresolvable)


def _match_r6_raw_finalize_commit(
    payload: dict[str, Any], tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R6 — a raw ``git commit`` while the enclosing plan is in ``6-finalize``.

    Refuses the raw form so every plan commit passes through the gate-bearing
    ``git-workflow commit`` verb. A commit in any other phase, a non-``git``
    program, and a non-``commit`` subcommand all pass through. Runs after the
    R1-R5 chain, so a command R1-R5 already refuse keeps its own rule label.
    Wrapper prefixes are stripped, matching the guard's ``gitCommitTarget``.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    info = _git_commit_target(command)
    if not info.is_commit:
        return None
    if info.unresolvable:
        # An unresolvable target is refused fail-closed ONLY inside the enforced
        # scope; an unrelated consumer's `git -C "$dir" commit` is not this rule's
        # business.
        scoped = gate.context_gate(payload) or _is_lane_run(payload) or _is_this_repository(payload)
        return _R6_REASON if scoped else None
    if _plan_phase(payload, info) != _SOURCE_COMMIT_GATE_PHASE:
        return None
    return _R6_REASON


#: Ordered ``(rule name, matcher)`` chain — the first matcher returning a reason
#: wins. The name is stamped into the ``guard.log`` audit line, matching the
#: OpenCode guard's ``rule=Rn`` field. R5 is NOT here: it runs when the gate is
#: satisfied OR this project IS the plan-marshall source repository. R6 is NOT
#: here either: it runs unconditionally.
_RULES: tuple[tuple[str, Callable[[str | None, dict[str, Any]], str | None]], ...] = (
    ('R1', _match_r1_shell_construct),
    ('R2', _match_r2_file_ops),
    ('R3', _match_r3_generated_executor),
    ('R4', _match_r4_hardcoded_build),
)


def _utc_iso_millis() -> str:
    """Return the current UTC time as ``YYYY-MM-DDTHH:MM:SS.mmmZ``.

    Matches the JavaScript guard's ``new Date().toISOString()`` shape so the two
    harnesses write identically formatted audit lines.
    """
    now = datetime.datetime.now(datetime.UTC)
    return now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{now.microsecond // 1000:03d}Z'


def _append_guard_log(payload: dict[str, Any], rule: str, detail: str) -> None:
    """Append one ``<cwd>/.plan/temp/guard.log`` line for a refusal (best-effort).

    The line is the same shape the OpenCode guard writes. A refusal with no
    ``cwd`` writes nothing — there is no path to key the log on. Any I/O failure
    is swallowed so logging can never mask the deny envelope (fail-open).
    """
    current = gate.cwd(payload)
    if not current:
        return
    try:
        log_dir = pathlib.Path(current) / '.plan' / 'temp'
        log_dir.mkdir(parents=True, exist_ok=True)
        tool = gate.tool_name(payload) or ''
        session = gate.session_id(payload) or '?'
        line = f'{_utc_iso_millis()} | tool={tool} | rule={rule} | session={session} | call=? | {detail}'
        with (log_dir / 'guard.log').open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')
    except OSError:
        pass


def _refusal_detail(payload: dict[str, Any]) -> str:
    """The command (or file path) a refusal is about, for the audit line."""
    tool_input = gate.tool_input(payload)
    command = tool_input.get('command')
    if isinstance(command, str) and command:
        return command
    file_path = tool_input.get('file_path')
    if isinstance(file_path, str) and file_path:
        return file_path
    return ''


#: A runbook-lane marker older than this no longer binds anything.
_LANE_MARKER_MAX_AGE_SECONDS = 24 * 60 * 60


def _is_lane_run(payload: dict[str, Any]) -> bool:
    """Whether this checkout carries a LIVE runbook-lane marker.

    Signal 3 of the plan-context predicate: a runbook-lane run issues every call
    with the MAIN checkout as its working directory, so neither Signal 1 (the
    lane runs in the main context) nor Signal 2 (no worktree path in the cwd)
    fires, and a consumer repository would be left unbound. The lane writes
    ``.plan/temp/rb-<plan>/progress.md`` before any implementation work. The
    marker is never removed, so it binds only while it is FRESH
    (:data:`_LANE_MARKER_MAX_AGE_SECONDS`); a stale one would otherwise bind
    R1-R5 in a consumer checkout forever.
    """
    root = _allow_list_root(payload) or gate.cwd(payload)
    if not root:
        return False
    temp_dir = pathlib.Path(root) / '.plan' / 'temp'
    try:
        entries = list(temp_dir.iterdir())
    except OSError:
        return False
    now = time.time()
    for entry in entries:
        if not entry.name.startswith('rb-'):
            continue
        marker = entry / 'progress.md'
        try:
            if now - marker.stat().st_mtime <= _LANE_MARKER_MAX_AGE_SECONDS:
                return True
        except OSError:
            continue
    return False


def evaluate(payload: dict[str, Any]) -> str | None:
    """Return the deny reason for the first matched rule, or ``None``.

    Scope: ``gate.context_gate(payload)`` (``Signal1 OR Signal2``) OR the
    runbook-lane marker OR this project IS the plan-marshall source repository.
    Inside that scope the R1-R5 matchers run in order; a consumer repository
    outside a plan context is left untouched (fail OPEN), so its ordinary work is
    never refused. **R6** is not context-gated: the raw-finalize commit rule fires
    in every session, named from every commit form, and only its UNRESOLVABLE
    fail-closed branch is limited to the enforced scope. A match also appends one
    ``guard.log`` audit line (best-effort — logging never changes the verdict).

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The ``permissionDecisionReason`` string when a rule denies the call, or
        ``None`` when no rule matches.
    """
    tool_name = gate.tool_name(payload)
    tool_input = gate.tool_input(payload)
    gated = gate.context_gate(payload) or _is_lane_run(payload)
    # R1-R4 bind when the gate is satisfied OR this project IS the plan-marshall
    # source repository. The OpenCode guard applies them unconditionally, so
    # gating them here left a ROOT session of this repository admitted for forms
    # the guard refuses — the parity divergence D3 closes. A consumer repository
    # outside a plan context is still untouched (the two-tier permission map
    # governs it).
    if gated or _is_this_repository(payload):
        for rule_name, rule in _RULES:
            reason = rule(tool_name, tool_input)
            if reason is not None:
                _append_guard_log(payload, rule_name, _refusal_detail(payload))
                return reason
    # R5 binds inside a plan context and in EVERY session of THIS repository; in
    # a consumer repository outside a plan context it does not refuse a
    # consumer's ordinary Python work.
    if gated or _is_this_repository(payload):
        reason = _match_r5_interpreter_call(tool_name, tool_input, _allow_list_root(payload), gate.cwd(payload))
        if reason is not None:
            _append_guard_log(payload, 'R5', _refusal_detail(payload))
            return reason
    # R6 is NOT context-gated: a main-context session committing into a
    # 6-finalize worktree is refused too, exactly as the OpenCode guard refuses.
    reason = _match_r6_raw_finalize_commit(payload, tool_name, tool_input)
    if reason is not None:
        _append_guard_log(payload, 'R6', _refusal_detail(payload))
        return reason
    return None


def _deny_envelope(reason: str) -> dict[str, Any]:
    """Build the Claude Code PreToolUse ``deny`` envelope carrying *reason*."""
    return {
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': reason,
        }
    }


def main() -> int:
    """Read stdin, deny on a gated rule match, else emit nothing — always exit 0.

    Best-effort/no-raise throughout: any unexpected error degrades to a silent
    no-op so a hook bug can never block a tool call.
    """
    try:
        raw = sys.stdin.read()
        payload = gate.parse(raw)
        reason = evaluate(payload)
        if reason is not None:
            sys.stdout.write(json.dumps(_deny_envelope(reason)))
            sys.stdout.flush()
    except Exception:
        # Whole-leaf fail-open contract: any error path emits nothing and exits 0
        # so the user is never blocked by a hook bug.
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
