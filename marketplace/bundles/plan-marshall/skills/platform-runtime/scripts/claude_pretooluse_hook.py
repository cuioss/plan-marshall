#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Conditional PreToolUse enforcement leaf for Claude Code.

Registered (opt-in) as a matcher-less ``hooks.PreToolUse`` entry. It blocks six
mechanically-checkable hard-rule violation families, but ONLY when the call
originates inside a plan-marshall plan context. Outside that context — and on
every error path — it emits nothing and exits 0, so a hook bug can never block
the user (fail OPEN).

ALL payload parsing, field access, and the context-gate predicate are delegated
to the shared ``pretooluse_gate`` module — this leaf adds NO field-name knowledge
of its own. The only logic it owns is the R1-R6 rule matchers and the
``permissionDecision: deny`` envelope layered on top:

- **R1 shell-construct compound** — a Bash command containing an UNQUOTED and
  UNESCAPED ``&&``, ``;``, ``&``, newline, ``for``/``while`` loop, ``$(...)``
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
  (``python`` / ``python3`` / a versioned spelling such as ``python3.12``,
  case-insensitively) as ``-c``, a script path, or ``-m`` with any module,
  except the ``python3 .plan/execute-script.py`` executor permit (which may be
  an absolute path), and except the shared allow-list of documented
  non-executor invocations read from ``standards/r5-allowlist.json``. Wrapper
  prefixes (``command``/``env``/``sudo``/``timeout``/``nice``/``nohup``/``time``/
  ``xargs``, including ``env -S``) are stripped first, so a wrapper cannot hide
  the interpreter. The allow set is otherwise executor-only, so every ``-m``
  form refuses.
- **R6 raw finalize commit** — a raw ``git commit`` while the enclosing plan is
  in phase ``6-finalize``. Every plan commit must pass through the gate-bearing
  ``git-workflow commit`` verb; outside ``6-finalize`` a raw commit is
  untouched.

Control flow:

1. Parse stdin via ``gate.parse`` (empty/malformed → emit nothing, exit 0).
2. Apply ``gate.context_gate(payload)`` (``Signal1 OR Signal2``) — false → emit
   nothing, exit 0 (fail OPEN).
3. Run the matchers against ``gate.tool_name(payload)`` /
   ``gate.tool_input(payload)``; on the FIRST match, append one ``guard.log``
   audit line (best-effort) and emit the deny envelope with a one-line redirect
   reason. No match → emit nothing, exit 0.

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
import pathlib
import re
import shlex
import sys
from collections.abc import Callable
from typing import Any

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
    ('background', _R1_OPERATOR_VIEW, _r1_contains('&')),
    ('newline', _R1_OPERATOR_VIEW, _r1_contains('\n')),
    ('substitution', _R1_SUBSTITUTION_VIEW, _r1_contains('$(')),
    ('backtick', _R1_SUBSTITUTION_VIEW, _r1_contains('`')),
    ('loop_keyword', _R1_OPERATOR_VIEW, _r1_matches(_R1_LOOP_RE)),
    ('leading_assignment', _R1_OPERATOR_VIEW, _r1_matches(_R1_LEADING_ASSIGNMENT_RE)),
)

#: R2 — Bash file-operation programs that have dedicated Read/Glob/Grep tools.
_R2_FILE_OPS = ('cat', 'grep', 'head', 'tail', 'find', 'ls')

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
#: API. ``./pw`` is matched as a literal; ``mvn`` / ``npm`` / ``gradle`` as bare
#: leading programs or path-prefixed executables (e.g. ``/usr/local/bin/mvn``).
_R4_BUILD_PROGRAMS = ('mvn', 'npm', 'gradle')

#: Per-rule one-line redirect reasons surfaced as ``permissionDecisionReason``.
_R1_REASON = (
    "plan-marshall: one command per Bash call — no UNQUOTED '&&', ';', '&', "
    'newline, for/while, $(...), or leading VAR=val; use separate Bash calls or '
    'dedicated tools. A metacharacter inside a quoted argument is fine.'
)
_R2_REASON = (
    'plan-marshall: use the Read/Glob/Grep tools, not Bash, for file '
    'operations (cat/grep/head/tail/find/ls, git grep). For a content sweep '
    'run: architecture search --content --pattern P.'
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
    'section-6 record, or a settle-band step.'
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
    if program in _R2_FILE_OPS:
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
    """R4 — Bash command invoking ./pw or a bare mvn/npm/gradle."""
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    first = _first_word(command)
    if first == './pw' or _program_name(command) in _R4_BUILD_PROGRAMS:
        return _R4_REASON
    return None


#: Shell wrappers (``command`` / ``env`` / ``sudo`` / ``timeout`` / ``nice`` /
#: ``nohup`` / ``time`` / ``xargs``) and leading ``NAME=value`` assignments the
#: R5 matcher strips before its program check. Mirrors the opencode guard's
#: ``commandTokens`` stripping (``SHELL_WRAPPERS`` and the value-option tables
#: there) so a wrapper-prefixed interpreter call (``timeout 5 python3 -c ...``)
#: is judged the same on both harnesses. Used ONLY by the R5 matcher — R1, R2
#: and R4 keep their existing unstripped program checks.
_R5_SHELL_WRAPPERS = frozenset({'command', 'env', 'sudo', 'timeout', 'nice', 'nohup', 'time', 'xargs'})

#: Per-wrapper options that consume a following value token. Kept PER WRAPPER so
#: ``sudo -n`` (a non-interactive FLAG) does not swallow the interpreter behind
#: it, while ``nice -n 5`` and ``xargs -n 5`` do consume their value. Mirrors the
#: guard's ``WRAPPER_VALUE_OPTS``.
_R5_WRAPPER_VALUE_OPTS: dict[str, frozenset[str]] = {
    'command': frozenset(),
    'env': frozenset({'-u', '--unset', '-C', '--chdir'}),
    'sudo': frozenset({'-u', '--user', '-g', '--group', '-U', '--other-user', '-C', '--chdir', '--directory'}),
    'timeout': frozenset({'-s', '--signal', '-k', '--kill-after'}),
    'nice': frozenset({'-n', '--adjustment'}),
    'nohup': frozenset(),
    'time': frozenset(),
    'xargs': frozenset(
        {
            '-I',
            '-n',
            '-P',
            '-s',
            '-d',
            '-a',
            '-E',
            '-L',
            '-o',
            '-R',
            '-S',
            '--max-args',
            '--max-lines',
            '--max-chars',
            '--delimiter',
            '--arg-file',
            '--replace',
            '--max-procs',
            '--eof',
            '--arg-separator',
        }
    ),
}

#: Leading ``NAME=value`` assignment, transparent to the shell.
_R5_ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


def _r5_stripped_tokens(command: str) -> list[str]:
    """Return shell-lexical tokens of *command* minus R5-transparent prefixes.

    Drops leading shell wrappers (each with its options, option values and
    inline assignments) and leading ``NAME=value`` assignments, mirroring the
    guard's ``commandTokens`` walk. ``timeout`` additionally consumes its
    mandatory duration value; ``env -S``/``--split-string`` splices its string
    back through the splitter, because ``env -S`` runs that string as the
    command. Shell-lexical (``shlex``) like the other R5 helpers, falling back
    to the whitespace split on malformed quoting rather than returning early.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return _strip_wrapper_tokens(tokens)


def _strip_wrapper_tokens(tokens: list[str]) -> list[str]:
    """Strip leading wrappers/assignments from *tokens* (the R5 prefix walk).

    Factored out so the ``env -S`` splice can recurse on the spliced head
    without re-lexing the whole command.
    """
    index = 0
    total = len(tokens)
    while index < total:
        token = tokens[index]
        if _R5_ASSIGNMENT_RE.match(token):
            index += 1
            continue
        if token not in _R5_SHELL_WRAPPERS:
            break
        wrapper = token
        value_opts = _R5_WRAPPER_VALUE_OPTS.get(wrapper, frozenset())
        index += 1
        spliced: list[str] | None = None
        while index < total:
            option = tokens[index]
            if _R5_ASSIGNMENT_RE.match(option):
                index += 1
                continue
            if not (option.startswith('-') and len(option) > 1):
                break
            if wrapper == 'env' and (option.startswith('-S') or option.split('=', 1)[0] == '--split-string'):
                if '=' in option:
                    value = option.split('=', 1)[1]
                    index += 1
                elif option == '-S':
                    index += 1
                    value = tokens[index] if index < total else ''
                    index += 1
                else:
                    value = option[2:]
                    index += 1
                try:
                    spliced = shlex.split(value)
                except ValueError:
                    spliced = value.split()
                break
            base = option.split('=', 1)[0]
            index += 1
            if '=' not in option and base in value_opts and index < total and not tokens[index].startswith('-'):
                index += 1
        if spliced is not None:
            return _strip_wrapper_tokens([*spliced, *tokens[index:]])
        if wrapper == 'timeout' and index < total and not tokens[index].startswith('-'):
            index += 1
    return tokens[index:]


def _is_executor_permit(command: str) -> bool:
    """Return True when *command* is the exempt executor invocation.

    Compared after R5 wrapper stripping, so a wrapper-prefixed executor call
    (``env python3 .plan/execute-script.py ...``) stays exempt exactly as the
    guard exempts it, and the second token may be the executor's ABSOLUTE path
    (``/abs/repo/.plan/execute-script.py``) — the runbook lane invokes it by an
    absolute path. Used only by the R5 matcher.
    """
    stripped = _r5_stripped_tokens(command)
    if len(stripped) < 2:
        return False
    program = _strip_matched_quotes(stripped[0]).rsplit('/', 1)[-1].lower()
    if program != 'python3':
        return False
    second = _strip_matched_quotes(stripped[1]).replace('\\', '/')
    return second == '.plan/execute-script.py' or second.endswith('/.plan/execute-script.py')


#: Interpreter program name, including a versioned spelling (``python3.12``).
#: Matched after lowercasing, mirroring the guard's ``isPythonInterpreter``.
_PYTHON_PROGRAM_RE = re.compile(r'^python(\d+(\.\d+)*)?$')

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


def _is_allow_listed(command: str) -> bool:
    """Whether *command*'s second stripped token is on the shared allow-list.

    Matched exactly or as a path suffix, so an absolute or relative path ending
    in an entry resolves to it (``/abs/repo/marketplace/targets/sync.py`` matches
    ``marketplace/targets/sync.py``; ``/abs/.../generate_executor.py`` matches
    the bare ``generate_executor.py``). Mirrors the guard's ``isAllowListed``.
    """
    stripped = _r5_stripped_tokens(command)
    if len(stripped) < 2:
        return False
    second = _strip_matched_quotes(stripped[1]).replace('\\', '/')
    return any(second == entry or second.endswith('/' + entry) for entry in _r5_allowlist_entries())


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


def _match_r5_interpreter_call(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """R5 — direct python interpreter call bypassing the executor.

    The program check runs on the wrapper-stripped tokens (``command`` /
    ``env`` / ``sudo`` prefixes and ``NAME=value`` assignments removed), so a
    wrapper-prefixed interpreter call is judged the same as the bare form —
    the same stripping the guard applies before its own first-token checks.
    An interpreter option in second position (``-u``, ``-W``, ``-X``,
    ``-B``, ``-E``, ``-I``, ``--``, bare ``-``) does not hide what follows:
    every later token is scanned with the same fail-closed rule. R1, R2
    and R4 match against the unstripped command and are untouched.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    if _is_executor_permit(command):
        return None
    stripped = _r5_stripped_tokens(command)
    first = stripped[0].strip().lower() if stripped else ''
    program = _strip_matched_quotes(first.rsplit('/', 1)[-1] if first else '')
    if not _PYTHON_PROGRAM_RE.match(program):
        return None
    second = _strip_matched_quotes(_second_token(command).strip())
    if not second:
        return None
    if _is_allow_listed(command):
        return None
    if second in ('-c', '-m'):
        return _R5_REASON
    if _is_c_m_cluster(second):
        return _R5_REASON
    if _has_flag_prefixed_bypass(stripped):
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
        if _is_c_m_cluster(text):
            return True
        if not text.startswith('-'):
            return True
    return False


#: Phase the raw-commit rule guards, mirroring git-workflow's
#: ``_SOURCE_COMMIT_GATE_PHASE``. Outside it a raw ``git commit`` is untouched.
_SOURCE_COMMIT_GATE_PHASE = '6-finalize'


def _plan_phase(payload: dict[str, Any]) -> str | None:
    """Read the enclosing plan's phase from the first readable ``status.json``.

    Looks under ``<cwd>/.plan/local/plans/*/status.json`` and returns the first
    non-empty top-level ``phase``. ``None`` when there is no cwd, no plan state,
    or nothing readable — the raw-commit rule then does not fire.
    """
    current = gate.cwd(payload)
    if not current:
        return None
    base = pathlib.Path(current) / '.plan' / 'local' / 'plans'
    try:
        statuses = sorted(base.glob('*/status.json')) if base.is_dir() else []
    except OSError:
        return None
    for path in statuses:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        phase = data.get('phase') if isinstance(data, dict) else None
        if isinstance(phase, str) and phase:
            return phase
    return None


def _match_r6_raw_finalize_commit(
    payload: dict[str, Any], tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R6 — a raw ``git commit`` while the enclosing plan is in ``6-finalize``.

    Refuses the raw form so every plan commit passes through the gate-bearing
    ``git-workflow commit`` verb. A commit in any other phase, a non-``git``
    program, and a non-``commit`` subcommand all pass through. Runs after the
    R1-R5 chain, so a command R1-R5 already refuse keeps its own rule label.
    """
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    if _program_name(command).lower() != 'git':
        return None
    if _git_subcommand(command) != 'commit':
        return None
    if _plan_phase(payload) != _SOURCE_COMMIT_GATE_PHASE:
        return None
    return _R6_REASON


#: Ordered ``(rule name, matcher)`` chain — the first matcher returning a reason
#: wins. The name is stamped into the ``guard.log`` audit line, matching the
#: OpenCode guard's ``rule=Rn`` field.
_RULES: tuple[tuple[str, Callable[[str | None, dict[str, Any]], str | None]], ...] = (
    ('R1', _match_r1_shell_construct),
    ('R2', _match_r2_file_ops),
    ('R3', _match_r3_generated_executor),
    ('R4', _match_r4_hardcoded_build),
    ('R5', _match_r5_interpreter_call),
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


def evaluate(payload: dict[str, Any]) -> str | None:
    """Return the deny reason for the first matched rule, or ``None``.

    Applies the shared context gate first (``Signal1 OR Signal2``); when the gate
    is not satisfied, returns ``None`` (fail OPEN — no enforcement). When the gate
    is satisfied, runs the R1-R5 matchers in order and then the R6 raw-finalize
    commit rule against the shared gate's
    ``tool_name`` / ``tool_input`` accessors and returns the first matching rule's
    redirect reason, or ``None`` when no rule fires. A match also appends one
    ``guard.log`` audit line (best-effort — logging never changes the verdict).

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The ``permissionDecisionReason`` string when a rule denies the call, or
        ``None`` when the gate is unsatisfied or no rule matches.
    """
    if not gate.context_gate(payload):
        return None
    tool_name = gate.tool_name(payload)
    tool_input = gate.tool_input(payload)
    for rule_name, rule in _RULES:
        reason = rule(tool_name, tool_input)
        if reason is not None:
            _append_guard_log(payload, rule_name, _refusal_detail(payload))
            return reason
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
