#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for claude_pretooluse_hook.py — the conditional PreToolUse enforcement leaf.

The leaf is a stdin->stdout hook script, so it is exercised both via subprocess (a
fresh interpreter, exactly as Claude Code would invoke it — proving the whole
fail-open + deny-envelope contract end to end) and via direct import of its pure
``evaluate`` function (proving each R1-R4 matcher and the gate-delegation behaviour
without subprocess overhead).

The shared ``pretooluse_gate`` module is imported directly (sibling-import
scaffolding) so the tests can build realistic in-context fixtures from the gate's
own field-name constants and prove the hook delegates parse/accessors/gate to the
shared module rather than carrying its own field-name copies.

Coverage:
  - Gate fail-open when neither signal fires (emit nothing, exit 0).
  - Signal-1-only enforcement (sub-agent identity carries the execution-context
    marker) and Signal-2-only enforcement (worktree cwd).
  - Each of R1-R4 producing a ``permissionDecision: deny`` with the expected
    redirect-reason substring when the gate is satisfied.
  - Each rule NOT firing on a benign in-context call.
  - Malformed / empty stdin -> no output, exit 0; never raises.
  - Absent Signal-1 field -> falls back to Signal 2 alone.
  - The hook delegates parse/accessors/gate to the shared module (matchers only).
"""

from __future__ import annotations

import json

# PLAIN import, deliberately — matching ``test_pretooluse_gate.py``, whose typed
# probes need mypy to see the real module. The name must be bound the same way in
# both suites or the loader would register a copy beside the plainly-imported one.
import pretooluse_gate as gate
import pytest

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path(
    "plan-marshall", "platform-runtime", "claude_pretooluse_hook.py"
)

hook = load_script_module('plan-marshall', 'platform-runtime', 'claude_pretooluse_hook.py')


# =============================================================================
# Helpers
# =============================================================================

#: A realistic bundle-qualified sub-agent identity that carries the
#: execution-context marker (Signal 1), as confirmed against real payloads.
_SUB_AGENT_IDENTITY = "plan-marshall:execution-context-level-4"


def _worktree_cwd() -> str:
    """A cwd resolving under the plan-worktree path segment (Signal 2)."""
    return f"/home/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan"


def _signal1_payload(tool_name: str, tool_input: dict) -> dict:
    """Payload satisfying the gate via Signal 1 only (sub-agent identity)."""
    return {
        gate.SUB_AGENT_IDENTITY_FIELD: _SUB_AGENT_IDENTITY,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _signal2_payload(tool_name: str, tool_input: dict) -> dict:
    """Payload satisfying the gate via Signal 2 only (worktree cwd)."""
    return {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _bash(command: str) -> dict:
    return {"command": command}


def _run(payload_json: str):
    """Run the enforcement leaf via subprocess with the given stdin JSON."""
    return run_script(SCRIPT_PATH, input_data=payload_json)


def _decision(stdout: str) -> dict:
    """Parse the deny envelope's hookSpecificOutput from leaf stdout."""
    output: dict = json.loads(stdout)["hookSpecificOutput"]
    return output


# =============================================================================
# Gate fail-open — neither signal fires
# =============================================================================


def test_emits_nothing_when_neither_signal_fires() -> None:
    payload = {"tool_name": "Bash", "tool_input": _bash("cat foo"), "cwd": "/tmp"}
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    assert result.stdout == ""


def test_evaluate_none_when_gate_unsatisfied_even_on_violation() -> None:
    # A clear R2 violation but no signal -> fail OPEN, no deny.
    payload = {"tool_name": "Bash", "tool_input": _bash("grep x file")}
    assert hook.evaluate(payload) is None


# =============================================================================
# Signal-1-only and Signal-2-only enforcement
# =============================================================================


def test_signal1_only_enforces() -> None:
    payload = _signal1_payload("Bash", _bash("cat foo"))
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    assert _decision(result.stdout)["permissionDecision"] == "deny"


def test_signal2_only_enforces() -> None:
    payload = _signal2_payload("Bash", _bash("cat foo"))
    assert hook.evaluate(payload) == hook._R2_REASON


def test_absent_signal1_falls_back_to_signal2() -> None:
    # No sub-agent identity field at all; Signal 2 alone satisfies the gate.
    payload = {
        "cwd": _worktree_cwd(),
        "tool_name": "Bash",
        "tool_input": _bash("ls -la"),
    }
    assert hook.evaluate(payload) == hook._R2_REASON


# =============================================================================
# R1 — shell-construct compound
# =============================================================================


def test_r1_denies_a_compound_reached_through_signal_1() -> None:
    """R1 fires the same when the gate was satisfied by the identity, not the cwd.

    Every other R1 case below arrives through Signal 2, so this is the one that
    pins rule matching as independent of WHICH signal opened the gate — the
    gate is consulted once, and the matcher never sees which arm answered.
    """
    assert hook.evaluate(_signal1_payload("Bash", _bash("a && b"))) == hook._R1_REASON


def test_r1_denies_the_while_spelling_of_the_loop_family() -> None:
    """``while`` denies as ``for`` does — the second spelling of one family.

    The per-family control table below carries exactly one row per family, so
    the loop family's second keyword has no row to live in. It is asserted here
    instead of being left to the assumption that one keyword implies the other.
    """
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("while true; do echo x; done")))
        == hook._R1_REASON
    )


def test_r1_not_fired_on_plain_command() -> None:
    # A single command with no shell construct does not trip R1 (and is not a
    # file-op or hard-coded build, so no rule fires).
    assert hook.evaluate(_signal2_payload("Bash", _bash("python3 script.py"))) is None


# -----------------------------------------------------------------------------
# R1 — quoting awareness
#
# A shell metacharacter that OPERATES and one that is DATA are the same
# character; only the quoting separates them. The controls below are MATCHED
# PAIRS, one per metacharacter family: the denied member proves the fix opened
# no bypass, and the allowed member proves the false positive is gone. Pairing
# them per family is what makes the no-bypass claim enumerated rather than
# sampled — a suite carrying only the allowed halves would pass equally against
# a matcher that had been gutted into always returning None.
# -----------------------------------------------------------------------------

#: ``(family, still_denied_unquoted, now_allowed_quoted)`` — one row per R1
#: metacharacter family. The family names are asserted against ``_R1_FAMILIES``,
#: the registry the matcher itself iterates, so a family added to the rule
#: without a control pair here fails loudly instead of going untested. The
#: command PAIRS remain hand-written — only a human can say what the quoted and
#: unquoted forms of a family look like — but the POPULATION they must cover is
#: derived, which is the half that used to drift.
_R1_QUOTING_CONTROLS = (
    ("and_chain", "a && b", 'git commit -m "fix && polish"'),
    ("semicolon", "a; b", 'git commit -m "fix: a; then b"'),
    ("background", "server &", 'echo "tom & jerry"'),
    ("newline", "a\nb", 'printf "line one\nline two"'),
    ("substitution", "echo $(date)", "echo 'cost is $(x)'"),
    ("backtick", "echo `date`", "echo 'a `literal` word'"),
    ("loop_keyword", "for f in *; do echo $f; done", 'echo "for each item"'),
    ("leading_assignment", "FOO=bar python3 x.py", 'echo "FOO=bar python3 x.py"'),
)

#: Parametrize ids for the two per-family control legs below, read off the table
#: itself so a family added to it is named in the report without a second edit.
_R1_FAMILY_IDS = [family for family, _denied, _allowed in _R1_QUOTING_CONTROLS]


def test_r1_quoting_control_population_is_derived_from_the_matcher_registry() -> None:
    """The control population is the matcher's OWN family registry, not a copy.

    This previously compared the control table against a hand-written ``expected``
    set literal in this same test. Both sides were hand-maintained, so the check
    could not detect the one thing it existed to detect — an ADDITION to the real
    population. A new R1 family could ship with no control pair and this stayed
    green. Deriving the expected side from ``hook._R1_FAMILIES``, the tuple
    ``_match_r1_shell_construct`` actually iterates, closes that: a family the
    matcher recognises but this table does not cover now fails here.

    Both populations are published in the failure message, and the registry is
    asserted non-empty first — a set-equality check over two empty populations
    passes while proving nothing.
    """
    registry = [family for family, _view, _predicate in hook._R1_FAMILIES]
    controls = [family for family, _denied, _allowed in _R1_QUOTING_CONTROLS]

    assert registry, "R1 family registry is empty — the comparison below is vacuous"
    assert len(registry) == len(set(registry)), f"duplicate family in registry {registry}"
    assert len(controls) == len(set(controls)), f"duplicate family in controls {controls}"
    assert set(controls) == set(registry), (
        f"{len(controls)} control rows for {len(registry)} matcher families; "
        f"uncovered={sorted(set(registry) - set(controls))}, "
        f"unknown={sorted(set(controls) - set(registry))}"
    )


def test_r1_every_registry_family_predicate_fires_on_its_own_denied_control() -> None:
    """Each registry entry is LIVE — its predicate fires on its own control.

    Set equality alone would still pass if an entry had been gutted: a family
    whose predicate never matches, or one wired to the wrong view, keeps its name
    in the registry and satisfies the population check while enforcing nothing.
    Driving each predicate against its own denied control, through the same view
    the entry names, is what makes the registry's membership mean something.
    """
    denied_by_family = {family: denied for family, denied, _allowed in _R1_QUOTING_CONTROLS}
    for family, view_name, predicate in hook._R1_FAMILIES:
        command = denied_by_family[family]
        views = hook._quote_masked_views(command)
        assert views is not None, f"{family}: {command!r} yielded no masked views"
        operator_view, substitution_view = views
        view = (
            operator_view
            if view_name == hook._R1_OPERATOR_VIEW
            else substitution_view
        )
        assert predicate(view), f"{family}: predicate did not fire on {command!r}"


@pytest.mark.parametrize(
    ("family", "denied"),
    [(family, denied) for family, denied, _allowed in _R1_QUOTING_CONTROLS],
    ids=_R1_FAMILY_IDS,
)
def test_r1_still_denies_the_unquoted_form_of_each_family(family: str, denied: str) -> None:
    """No bypass was opened: each family's unquoted compound still denies."""
    payload = _signal2_payload("Bash", _bash(denied))

    assert hook.evaluate(payload) == hook._R1_REASON, f"{family}: {denied!r}"


@pytest.mark.parametrize(
    ("family", "allowed"),
    [(family, allowed) for family, _denied, allowed in _R1_QUOTING_CONTROLS],
    ids=_R1_FAMILY_IDS,
)
def test_r1_allows_the_quoted_form_of_each_family(family: str, allowed: str) -> None:
    """The false positive is gone: a metacharacter that is DATA no longer denies.

    Fails against the pre-fix matcher, which scanned the raw command string and
    denied every one of these legitimate single commands.
    """
    payload = _signal2_payload("Bash", _bash(allowed))

    assert hook.evaluate(payload) is None, f"{family}: {allowed!r}"


#: Substitution markers that are LIVE inside double quotes. This is the
#: asymmetry that stops the quoting fix from becoming a bypass: single quotes
#: make ``$(...)`` and a backtick span literal, double quotes do NOT — the shell
#: still executes them — so only the single-quoted form is allowed.
_R1_LIVE_INSIDE_DOUBLE_QUOTES = ['echo "$(rm -rf /)"', 'echo "a `date` b"']

_R1_LIVE_INSIDE_DOUBLE_QUOTES_IDS = [
    'dollar-paren-substitution-still-executes',
    'backtick-span-still-executes',
]


@pytest.mark.parametrize(
    "command", _R1_LIVE_INSIDE_DOUBLE_QUOTES, ids=_R1_LIVE_INSIDE_DOUBLE_QUOTES_IDS
)
def test_r1_denies_substitution_inside_double_quotes(command: str) -> None:
    """A substitution the shell would still run denies even though it is quoted."""
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) == hook._R1_REASON, command


def test_r1_malformed_quoting_falls_back_to_detection() -> None:
    """An unterminated quote degrades to the pre-existing scan, never to a bypass."""
    payload = _signal2_payload("Bash", _bash('echo "unterminated ; still denied'))
    assert hook.evaluate(payload) == hook._R1_REASON


def test_r1_malformed_quoting_without_a_metacharacter_still_passes() -> None:
    """The fallback is a re-scan, not a blanket denial of malformed quoting."""
    payload = _signal2_payload("Bash", _bash('python3 x.py "unterminated'))
    assert hook.evaluate(payload) is None


def test_r1_allows_the_real_world_commit_message_shape() -> None:
    """The reported field failure: a conventional commit body carrying a colon-list.

    This exact shape — a single ``git commit`` whose message contains ``;`` —
    was denied before the fix while being a legitimate one-command call.
    """
    command = 'git commit -m "fix(x): correct a thing; refs #1"'
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) is None


def test_r1_quote_masked_views_preserve_length() -> None:
    """Both views stay character-aligned with the command.

    Length preservation is what keeps the newline check meaningful — a
    token-level view would drop an unquoted newline as whitespace and turn that
    check into a permanent pass.
    """
    command = 'echo "a; b" \'c && d\' e'
    views = hook._quote_masked_views(command)
    assert views is not None, "well-formed quoting must yield masked views, not the malformed-quoting None"
    operator_view, substitution_view = views
    assert len(operator_view) == len(command)
    assert len(substitution_view) == len(command)


def test_r1_quote_masked_views_report_malformed_quoting() -> None:
    """An unterminated span is reported as None rather than guessed at."""
    assert hook._quote_masked_views('echo "unterminated') is None


# -----------------------------------------------------------------------------
# R1 — backslash escapes
#
# A backslash resolves BEFORE any quote-state transition, in unquoted context
# and inside a double-quoted span alike; inside a single-quoted span bash reads
# it as an ordinary literal. Resolving it only inside double quotes was wrong in
# BOTH directions at once — a bypass unquoted and a false positive quoted — so
# the controls below come in matched pairs. A suite carrying only one half of
# each pair would pass against a matcher gutted in the other direction.
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    ["echo \\'a; b\\'", 'echo \\"a; b\\"'],
    ids=['escaped-single-quote', 'escaped-double-quote'],
)
def test_r1_denies_escaped_quote_that_must_not_open_a_span(command: str) -> None:
    """The bypass: an escaped quote is DATA, so the separator behind it is LIVE.

    ``echo \\'a; b\\'`` is TWO commands to bash (``echo \\'a`` and ``b\\'``) —
    the escaped quotes are literal characters, so nothing quotes the ``;``.
    Before the fix a backslash in unquoted context was appended verbatim and the
    quote that FOLLOWED it opened a span; for the single-quoted form the span
    then closed cleanly at the trailing ``\\'``, the scan terminated, and the
    live ``;`` was masked out of the operator view — R1 allowed a compound
    command. Both quote characters are covered because the span-opening defect
    belongs to the escape handling, not to one quote style: the double-quoted
    form reached the same verdict only by accident, via the unterminated-span
    fallback to the raw command.
    """
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) == hook._R1_REASON, command


@pytest.mark.parametrize(
    "command",
    ['echo "\\`date\\`"', 'echo "\\$(date)"'],
    ids=['escaped-backtick-is-literal', 'escaped-dollar-is-literal'],
)
def test_r1_allows_escaped_substitution_marker_inside_double_quotes(command: str) -> None:
    """The false positive: an escaped marker is literal data, not a substitution.

    Inside a double-quoted span bash reads a backslash-escaped backtick as a
    literal backtick and ``\\$`` as a literal dollar, so neither command below
    substitutes anything. The pre-fix escape branch copied the RAW two
    characters into ``substitution_view``, leaving the marker intact there, so
    both denied on the ``substitution`` / ``backtick`` families. The matched
    positive is
    ``test_r1_denies_substitution_inside_double_quotes``: an UNescaped
    substitution in the same position still executes, and still denies.
    """
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) is None, command


def test_r1_single_quoted_span_treats_backslash_as_a_literal() -> None:
    """Inside single quotes a backslash escapes NOTHING — the span still closes.

    ``echo 'a\\'`` is one complete command whose single argument is ``a\\``: the
    backslash is an ordinary character and the quote after it CLOSES the span.
    Applying the escape there would swallow that closing quote, leave the span
    unterminated, and force the command onto the raw-command fallback — so the
    guard excluding the single-quoted state is load-bearing. Asserting the views
    EXIST is what pins it; asserting only that the call is allowed would pass
    even on the fallback, since this command carries no metacharacter either way.
    """
    command = "echo 'a\\'"
    assert hook._quote_masked_views(command) is not None
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) is None


def test_r1_allows_escaped_newline_line_continuation() -> None:
    """An escaped newline JOINS the lines into one command, so it is no separator.

    A direct consequence of resolving the escape in unquoted context: bash reads
    a backslash before a newline as a line continuation, so the two source lines
    are a single command and the newline check must not fire. The matched
    negative is ``test_r1_denies_newline`` — a BARE unquoted newline is a real
    command separator and still denies.
    """
    command = "python3 x.py \\\n  --flag value"
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) is None


def test_r1_quote_masked_views_preserve_length_across_escapes() -> None:
    """The escape branch consumes two characters and emits two, in BOTH views.

    Character-for-character alignment is the invariant the newline and
    leading-assignment checks rely on; an escape branch emitting one character
    for two would shift every later column and silently weaken them. The
    command below exercises an escape in unquoted context and inside a
    double-quoted span, so a regression in either arm changes a length.
    """
    command = 'echo \\;a "b\\`c" \\$d'
    views = hook._quote_masked_views(command)
    assert views is not None, "well-formed quoting must yield masked views"
    operator_view, substitution_view = views
    assert len(operator_view) == len(command)
    assert len(substitution_view) == len(command)


# =============================================================================
# R2 — Bash file-ops
# =============================================================================


@pytest.mark.parametrize(
    "program",
    ["cat", "grep", "head", "tail", "find", "ls"],
    ids=["cat", "grep", "head", "tail", "find", "ls"],
)
def test_r2_denies_each_file_op(program: str) -> None:
    """Each shell file-op program denies on its own, as its own reported row."""
    payload = _signal2_payload("Bash", _bash(f"{program} something"))

    assert hook.evaluate(payload) == hook._R2_REASON


def test_r2_not_fired_on_substring_program() -> None:
    # A program whose name merely contains a file-op substring is not a file-op.
    assert hook.evaluate(_signal2_payload("Bash", _bash("category --help"))) is None


# -----------------------------------------------------------------------------
# R2 — the `git grep` arm
#
# `git grep` reads file bodies exactly as bare `grep` does, so it joins the
# EXISTING R2 family. The positive controls below all place the subcommand
# somewhere other than tokens[1], which is precisely what a naive
# `tokens[1] == "grep"` check walks past — testing only `git grep foo` would pass
# against that vacuous guard. The negative controls are what make the boundary
# real: a suite carrying only positives would equally pass against an
# implementation that blocks every `git` invocation.
# -----------------------------------------------------------------------------


#: ``git grep`` invocations that must all deny, whatever stands between the
#: program and its subcommand. Three option classes are represented, and the
#: reason each class is here differs:
#:
#: * the plain and simply-prefixed forms, where nothing intervenes at all;
#: * a value-taking global option, which consumes its VALUE and must not have
#:   that value read as the subcommand;
#: * option SHAPES the walker never names by spelling. These are the regression
#:   rows: when the walk recognised only a named allowlist, each of them
#:   returned its own option token as the subcommand (``"-c."``, ``"-p"``,
#:   ``"--bare"``), the ``== "grep"`` test missed, and ``git grep`` was let
#:   through. None of them appears in ``_R2_GIT_VALUE_OPTIONS``, which is
#:   precisely why a table drawn from that tuple could not have found the gap.
_R2_GIT_GREP_DENIED = [
    "git grep foo",
    "git -C . grep foo",
    "git --no-pager grep foo",
    "/usr/bin/git grep foo",
    "git -c core.pager=cat grep foo",
    "git --git-dir=/repo/.git grep foo",
    "git --work-tree /repo grep foo",
    "git --literal-pathspecs grep foo",
    "git -C. grep foo",
    "git -cvar=val grep foo",
    "git -p grep foo",
    "git --bare grep foo",
    "git --no-optional-locks grep foo",
    "git -C. -p --bare grep foo",
]

_R2_GIT_GREP_DENIED_IDS = [
    'no-options-at-all',
    'detached-short-value',
    'listed-long-flag',
    'absolute-path-to-git',
    'attached-long-value-via-c',
    'attached-long-value-via-git-dir',
    'detached-long-value-via-work-tree',
    'listed-long-flag-taking-no-value',
    'attached-short-value',
    'attached-short-value-inline-config-pair',
    'unlisted-short-flag',
    'unlisted-long-flag',
    'unlisted-negated-long-flag',
    'several-unlisted-shapes-stacked',
]


@pytest.mark.parametrize("command", _R2_GIT_GREP_DENIED, ids=_R2_GIT_GREP_DENIED_IDS)
def test_r2_denies_git_grep_behind_every_option_shape(command: str) -> None:
    """The subcommand still resolves to ``grep``, so the file-op still denies."""
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_git_option_skip_is_structural_not_an_allowlist() -> None:
    """No named-option tuple may be the sole thing standing between git and grep.

    Guards the property directly rather than sampling spellings: an option shape
    invented here (one that cannot be in any allowlist) must still resolve to the
    real subcommand. A future edit that narrows the walk back to a membership
    test fails this even if it re-adds every spelling the suite above names.
    """
    assert hook._git_subcommand("git --a-flag-nobody-listed grep foo") == "grep"
    assert hook._git_subcommand("git -Zqx grep foo") == "grep"


#: The matched negative controls for the deny table above. Without them an
#: implementation that simply blocked every ``git`` call would satisfy every
#: positive row, so these are what make the boundary real rather than sampled.
#: The first four are ordinary git usage; the last four repeat the SAME option
#: shapes as the regression rows above in front of a non-grep subcommand, so
#: skipping every dash-token structurally is shown not to swallow the
#: subcommand slot along with the options.
_R2_GIT_ALLOWED = [
    "git status",
    "git log --oneline -5",
    "git diff --name-only HEAD",
    "git rev-parse HEAD",
    "git -C. status",
    "git -p log --oneline",
    "git --bare rev-parse HEAD",
    "git -cvar=val diff --name-only",
]

_R2_GIT_ALLOWED_IDS = [
    'plain-status',
    'plain-log',
    'plain-diff',
    'plain-rev-parse',
    'attached-short-value-then-status',
    'unlisted-short-flag-then-log',
    'unlisted-long-flag-then-rev-parse',
    'inline-config-pair-then-diff',
]


@pytest.mark.parametrize("command", _R2_GIT_ALLOWED, ids=_R2_GIT_ALLOWED_IDS)
def test_r2_not_fired_on_non_grep_git_subcommands(command: str) -> None:
    """Ordinary git usage keeps working — these resolve to no file-op."""
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) is None, command


def test_r2_detached_value_option_does_not_mistake_its_value_for_grep() -> None:
    """A detached value token is consumed, never read as the subcommand.

    ``-C grep`` names a DIRECTORY called ``grep``; the subcommand is ``status``.
    This is the trap the structural dash-skip alone would not catch, and it is
    why the detached value options still need naming.
    """
    assert hook._git_subcommand("git -C grep status") == "status"
    assert hook.evaluate(_signal2_payload("Bash", _bash("git -C grep status"))) is None


@pytest.mark.parametrize(
    "command",
    ['git -C "repo dir" grep needle', "git -C 'repo dir' grep needle"],
    ids=['double-quoted-path-value', 'single-quoted-path-value'],
)
def test_r2_denies_git_grep_behind_a_quoted_detached_value(command: str) -> None:
    """A quoted value containing a space must not tear the skip arithmetic.

    ``git -C "repo dir" grep x`` is a real ``git grep`` file-op. Under a
    whitespace split the quoted value becomes two tokens, so the ``-C`` skip
    lands mid-value and the subcommand resolves to ``dir"`` — R2 misses the
    file-op entirely. Shell-lexical splitting keeps the value one token. Both
    quote styles are covered because either spelling is valid shell.
    """
    assert hook._git_subcommand(command) == "grep", command

    payload = _signal2_payload("Bash", _bash(command))
    assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_quoted_detached_value_still_allows_non_grep_subcommand() -> None:
    """The negative control for the quoted-value fix — matched pair.

    The same quoted-path shape with a benign subcommand must stay allowed, so
    the fix is proven to resolve the subcommand rather than to blanket-deny any
    command carrying a quoted token.
    """
    command = 'git -C "repo dir" status'
    assert hook._git_subcommand(command) == "status"
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) is None


def test_git_subcommand_falls_back_to_whitespace_split_on_bad_quoting() -> None:
    """Malformed quoting degrades to the whitespace split, never to a bypass.

    An unbalanced quote makes ``shlex`` raise. Returning ``""`` there would turn
    a lexer error into a silent R2 bypass, so the fallback preserves the
    pre-existing whitespace-split detection instead.
    """
    assert hook._git_subcommand('git -C "unbalanced grep needle') == "grep"


def test_r2_not_fired_on_git_log_grep_option() -> None:
    """`git log --grep=fix` is a COMMIT-MESSAGE search, and stays allowed.

    The trap a sloppy substring check breaks: the string ``grep`` appears in the
    command, but it is an option to ``log``, not the subcommand, and searching
    commit messages is not a file-content operation. This is the single most
    discriminating negative control in the arm.
    """
    payload = _signal2_payload("Bash", _bash("git log --grep=fix"))
    assert hook.evaluate(payload) is None


def test_r2_not_fired_on_bare_git() -> None:
    """A `git` call with no subcommand resolves to no subcommand, so it passes."""
    assert hook.evaluate(_signal2_payload("Bash", _bash("git"))) is None


def test_r2_reason_names_the_sanctioned_content_search_replacement() -> None:
    """The redirect must name the replacement, not just refuse the call.

    Blocking `git grep` is only legitimate because a sanctioned content-search
    path exists; the reason string is where the caller learns it.
    """
    assert "architecture search --content" in hook._R2_REASON


# =============================================================================
# R3 — generated-executor edit
# =============================================================================


#: ``(tool name, file path, the verdict R3 must reach)``. The rule is about the
#: PATH, not the tool, so the two denying rows use different write tools and
#: different path spellings — relative and absolute — to show neither is what
#: decides. The third row is the matched negative: the same tool against an
#: ordinary source path stays allowed, so R3 is proven to name the generated
#: executor rather than to refuse writes at large.
_R3_CASES = [
    ("Edit", ".plan/execute-script.py", hook._R3_REASON),
    ("Write", "/home/dev/project/.plan/execute-script.py", hook._R3_REASON),
    ("Edit", "marketplace/bundles/plan-marshall/foo.py", None),
]

_R3_IDS = [
    'edit-of-the-executor-by-relative-path',
    'write-to-the-executor-by-absolute-path',
    'edit-of-an-ordinary-source-file-is-allowed',
]


@pytest.mark.parametrize(("tool_name", "file_path", "expected"), _R3_CASES, ids=_R3_IDS)
def test_r3_guards_the_generated_executor(
    tool_name: str, file_path: str, expected: str | None
) -> None:
    """A write aimed at the generated executor denies; any other path does not."""
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
    }

    assert hook.evaluate(payload) == expected


# =============================================================================
# R4 — hard-coded build
# =============================================================================


#: Hard-coded build invocations R4 refuses. ``./pw`` is matched as a literal
#: (its ``./`` prefix is part of the name), the other three as bare program
#: names — two spellings of one rule, so both are represented.
_R4_DENIED_COMMANDS = ["./pw verify", "mvn build", "npm build", "gradle build"]

_R4_DENIED_IDS = ['pw-wrapper-literal', 'mvn', 'npm', 'gradle']


@pytest.mark.parametrize("command", _R4_DENIED_COMMANDS, ids=_R4_DENIED_IDS)
def test_r4_denies_hard_coded_build_invocations(command: str) -> None:
    """Each hard-coded build program denies, as its own reported row."""
    payload = _signal2_payload("Bash", _bash(command))

    assert hook.evaluate(payload) == hook._R4_REASON


def test_r4_not_fired_on_resolved_build() -> None:
    # The architecture-resolved executor call is a plain python3 invocation and
    # trips no rule.
    cmd = "python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run"
    assert hook.evaluate(_signal2_payload("Bash", _bash(cmd))) is None


# =============================================================================
# Deny envelope shape (subprocess, end-to-end)
# =============================================================================


def test_deny_envelope_shape() -> None:
    payload = _signal2_payload("Bash", _bash("cat foo"))
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    decision = _decision(result.stdout)
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert isinstance(decision["permissionDecisionReason"], str)
    assert decision["permissionDecisionReason"]


# =============================================================================
# Never blocks on malformed / empty stdin
# =============================================================================


def test_exits_zero_and_silent_on_empty_stdin() -> None:
    result = _run("")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exits_zero_and_silent_on_malformed_stdin() -> None:
    result = _run("not json {{{")
    assert result.returncode == 0
    assert result.stdout == ""


def test_evaluate_never_raises_on_non_dict_payload() -> None:
    # gate.parse returns {} for non-object input, but defensively prove evaluate
    # tolerates a {} payload (gate unsatisfied -> None).
    assert hook.evaluate({}) is None


# =============================================================================
# Delegation to the shared gate (matchers only — no field-name copies)
# =============================================================================


def test_gate_decision_matches_shared_module() -> None:
    # A payload the shared gate rules out-of-context must NOT enforce, even with
    # an otherwise-matching violation -> proves the hook calls context_gate.
    payload = {"tool_name": "Bash", "tool_input": _bash("cat foo"), "cwd": "/tmp"}
    assert gate.context_gate(payload) is False
    assert hook.evaluate(payload) is None


def test_marker_value_satisfies_signal1() -> None:
    # The bundle-qualified identity carries the gate's execution-context marker.
    assert gate.EXECUTION_CONTEXT_MARKER in _SUB_AGENT_IDENTITY
    payload = _signal1_payload("Read", {"file_path": "x"})
    # Read is a benign non-matching tool: gate satisfied, but no rule fires.
    assert hook.evaluate(payload) is None


# =============================================================================
# _program_name — path-prefix normalization
# =============================================================================


#: ``(command, the program name it normalizes to)``. Two rows strip an absolute
#: path prefix, so a path-prefixed program cannot walk past a rule that names it
#: bare. The rest are the shapes that must be left ALONE: a bare name is already
#: normalized; ``./pw`` is matched as a literal by R4, so stripping its prefix
#: would disarm that rule; and an empty command has no program to name.
_PROGRAM_NAME_CASES = [
    ("/usr/bin/cat", "cat"),
    ("/bin/grep", "grep"),
    ("cat", "cat"),
    ("./pw", "./pw"),
    ("", ""),
]

_PROGRAM_NAME_IDS = [
    'absolute-path-prefix-stripped',
    'bin-path-prefix-stripped',
    'bare-name-unchanged',
    'pw-literal-kept-with-its-prefix',
    'empty-command-yields-no-program',
]


@pytest.mark.parametrize(("command", "expected"), _PROGRAM_NAME_CASES, ids=_PROGRAM_NAME_IDS)
def test_program_name_normalization(command: str, expected: str) -> None:
    """A command normalizes to the program name the rules match against."""
    assert hook._program_name(command) == expected


# =============================================================================
# R2/R4 — path-prefixed bypass prevention
# =============================================================================


#: ``(path-prefixed command, the rule that must still fire)``. Spelling a
#: program by its absolute path is the obvious way to walk past a rule that
#: names it bare, so both rules that match on a program name carry rows here.
_PATH_PREFIXED_BYPASS_CASES = [
    ("/usr/bin/cat file.txt", hook._R2_REASON),
    ("/bin/grep pattern file", hook._R2_REASON),
    ("/usr/local/bin/mvn verify", hook._R4_REASON),
    ("/usr/bin/npm install", hook._R4_REASON),
]

_PATH_PREFIXED_BYPASS_IDS = [
    'r2-path-prefixed-cat',
    'r2-path-prefixed-grep',
    'r4-path-prefixed-mvn',
    'r4-path-prefixed-npm',
]


@pytest.mark.parametrize(
    ("command", "expected_reason"),
    _PATH_PREFIXED_BYPASS_CASES,
    ids=_PATH_PREFIXED_BYPASS_IDS,
)
def test_a_path_prefixed_program_does_not_bypass_its_rule(
    command: str, expected_reason: str
) -> None:
    """An absolute path in front of the program leaves the rule's verdict intact."""
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) == expected_reason
