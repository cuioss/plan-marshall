#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic candidate surfacing for the pre-submission-self-review finalize step.

Reads the worktree's diff against the base branch, scans added lines in modified
files, and emits eighteen candidate lists (regexes, user-facing strings, markdown
sections, symmetric-pair functions, flag-guard pairs, contract sources,
schema-bearing files, keep-identifier markers, protected identifiers,
producer-consumer pairs,
source-of-truth duplicates, same-document normative directives, description-vs-body
frontmatter, lone-unguarded-boundary calls, stale count-prose, near-identical-hunk
touched claims, advertised-form help strings, same-document ordinal references) as
TOON for the LLM cognitive review pass to consume.

Storage: stateless — reads the worktree diff and derives the plan footprint
live from the worktree (``compute-footprint``: ``{base}...HEAD`` ∪ porcelain).
Output: TOON to stdout.

Usage:
    python3 self_review.py surface --plan-id EXAMPLE-PLAN --project-dir /path/to/worktree
"""

import argparse
import re
import subprocess
from pathlib import Path
from typing import Any

from _references_core import (  # type: ignore[import-not-found]
    compute_plan_branch_diff,
)
from file_ops import (  # type: ignore[import-not-found]
    output_toon,
    output_toon_error,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from resolve_project_dir import (  # type: ignore[import-not-found]
    WorktreeResolutionError,
    emit_worktree_error,
    resolve_project_dir,
)

# =============================================================================
# Detection regexes
# =============================================================================

# Added-line marker (stripped before content scanning)
_ADDED_LINE = re.compile(r'^\+(?!\+\+)(.*)$')

# Diff hunk header (records the post-image starting line number)
_HUNK_HEADER = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')

# Diff file header (records the post-image path)
_FILE_HEADER = re.compile(r'^\+\+\+ b/(.+)$')

# Regex/glob detection
_RE_CALL = re.compile(
    r'\bre\.(?:compile|match|search|findall|sub|fullmatch|finditer)'
    r"\s*\(\s*(?:r|f|rf|fr)?(['\"])(.+?)\1"
)
# fnmatch's pattern is the SECOND positional arg (path is first); accept any
# string literal inside the call's argument list — first quoted run wins.
_FNMATCH_CALL = re.compile(r"\bfnmatch\.(?:fnmatch|filter)\s*\([^)]*?(['\"])([^'\"]*)\1")
_RAW_REGEX_LITERAL = re.compile(r"\br(['\"])([^'\"]*[\^$.*+?\[\](){}|\\][^'\"]*)\1")

# User-facing string detection
_DEF_OR_CLASS = re.compile(r'^\s*(def|class)\s+\w+')
_TRIPLE_QUOTE = re.compile(r"""^\s*(['"]{3})(.*)$""")
_PRINT_CALL = re.compile(r"\bprint\s*\(\s*(?:r|f|rf|fr)?(['\"])(.*?)\1")
_ARGPARSE_FIELD = re.compile(r"\b(description|help|epilog)\s*=\s*(?:r|f|rf|fr)?(['\"])(.*?)\2")
_RAISE_MESSAGE = re.compile(r"\braise\s+\w+(?:Error|Exception)\s*\(\s*(?:r|f|rf|fr)?(['\"])(.*?)\1")
_MD_HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
_MD_BULLET = re.compile(r'^\s*[-*]\s+(.+?)\s*$')

# Symmetric-pair detection
_DEF_NAME = re.compile(r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
_PAIR_TOKENS: list[tuple[str, str]] = [
    ('save', 'load'),
    ('init', 'restore'),
    ('push', 'pop'),
    ('acquire', 'release'),
    ('open', 'close'),
    ('start', 'stop'),
]

# Flag-guard-pair detection
# Recognizes argument-presence guards over a `--flag` token in added .py lines:
# membership tests (`'--flag' in args`), substring tests (`'--flag' in argv`),
# and startswith checks (`arg.startswith('--flag')`). For each guarded flag the
# detector classifies which flag *forms* the guard covers — the bare token
# guards the space-separated form (`--flag value`); the `--flag=` prefix guards
# the equals form (`--flag=value`).
#
# Group 1 captures the guarded `--flag` token from a quoted literal that is the
# left operand of an `in` membership/substring test. The optional trailing `=`
# (group 2) marks the equals-form variant.
_FLAG_MEMBERSHIP_GUARD = re.compile(
    r"""(['"])(--[A-Za-z][A-Za-z0-9_-]*)(=?)\1\s+in\b"""
)
# Group 1 captures the guarded `--flag` token passed to a `.startswith(...)`
# check; the optional trailing `=` (group 2) marks the equals-form variant.
_FLAG_STARTSWITH_GUARD = re.compile(
    r"""\.startswith\s*\(\s*(['"])(--[A-Za-z][A-Za-z0-9_-]*)(=?)\1"""
)

# Keep-identifier marker detection
# Shape: <!-- self-review: keep <identifier> -->
# - whitespace around `self-review:` and the identifier is tolerant
# - the identifier is a single whitespace-free token; the regex stops at the
#   first whitespace or at the closing `-->` sentinel (the `(?=...)` lookahead
#   ensures the token boundary is the marker terminator, not part of the id)
_KEEP_MARKER = re.compile(
    r'<!--\s*self-review:\s*keep\s+(\S+?)\s*-->'
)

# Doc-prose script-contract reference detection.
# An ``execute-script.py`` invocation that names a script via the three-part
# ``{bundle}:{skill}:{script}`` notation. Group 1/2 capture the bundle and skill
# segments; the script segment is captured to anchor the match but is not needed
# for SKILL.md resolution (SKILL.md lives at the skill-directory root).
_EXECUTE_SCRIPT_NOTATION = re.compile(
    r'execute-script\.py\s+([a-z0-9][a-z0-9-]*):([a-z0-9][a-z0-9-]*):[a-z0-9][a-z0-9_-]*'
)
# A TOON-field reference: a ``{field}`` interpolation token (e.g. ``{status}``,
# ``{error}``) where ``field`` is a bare identifier. This is the content signal
# that the doc prose is talking about a sibling script's output-contract field.
_TOON_FIELD_TOKEN = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')

# Producer-consumer detection.
# A producer assigns a value into a dict-keyed slot of the script's output —
# the dominant shape is ``output['key'] = ...`` / ``output["key"] = ...`` (a
# subscript assignment whose value is later expected to be consumed by a
# downstream branch). Group 1 captures the produced key.
_PRODUCER_SUBSCRIPT_ASSIGN = re.compile(
    r"""^\s*\w+\[(['"])([A-Za-z_][A-Za-z0-9_]*)\1\]\s*="""
)
# A consumer reads a value back out of a dict-keyed slot — either via a
# subscript read (``something['key']`` not on the LHS of an assignment) or via
# ``.get('key'...)``. Both shapes name the consumed key in group 2.
_CONSUMER_SUBSCRIPT_READ = re.compile(
    r"""\[(['"])([A-Za-z_][A-Za-z0-9_]*)\1\]"""
)
_CONSUMER_GET_READ = re.compile(
    r"""\.get\s*\(\s*(['"])([A-Za-z_][A-Za-z0-9_]*)\1"""
)

# Source-of-truth-consistency detection.
# A module-level (or simply assigned) constant binding of the shape
# ``NAME = <literal>`` where NAME is an UPPER_SNAKE_CASE identifier. Group 1
# captures the constant name; group 2 the literal RHS (trimmed). The same
# constant assigned a *different* literal in two diff files is a SoT drift.
_CONSTANT_ASSIGN = re.compile(
    r"""^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*$"""
)

# Same-document-consistency detection.
# A normative directive line in a ``.md`` body — a line carrying one of the
# RFC-2119-style normative keywords. Group 1 captures the keyword that fired so
# the cognitive review can group competing directives.
_NORMATIVE_DIRECTIVE = re.compile(
    r'\b(MUST NOT|MUST|SHALL NOT|SHALL|NEVER|ALWAYS|REQUIRED|FORBIDDEN)\b'
)

# Description-vs-body-consistency detection.
# A frontmatter ``description:`` (or ``summary:``) key at the head of a ``.md``
# document. Group 1 names the key that fired; group 2 captures the value text.
_FRONTMATTER_DESCRIPTION = re.compile(
    r'^(description|summary)\s*:\s*(.+?)\s*$'
)

# Lone-unguarded-boundary detection (Facet 1).
# Recognizes an added ``.py`` line that opens a subprocess or file-I/O boundary
# call. ``subprocess.*`` calls (run/Popen/check_output/call/check_call) and the
# file-I/O calls (``open(``, ``Path.read_text``/``write_text``/``read_bytes``/
# ``write_bytes``) are the in-scope boundaries. Network calls (``socket.``,
# ``urllib.``, ``http.client.``) are deliberately OUT of scope and not matched.
_SUBPROCESS_BOUNDARY = re.compile(
    r'\bsubprocess\.(run|Popen|check_output|call|check_call)\s*\('
)
_FILE_IO_BOUNDARY = re.compile(
    r'(?:\bopen\s*\(|\.(?:read_text|write_text|read_bytes|write_bytes)\s*\()'
)
# ``check=True`` keyword that guards a subprocess call against a silent failure.
_CHECK_TRUE_KWARG = re.compile(r'\bcheck\s*=\s*True\b')
# A line that opens a ``try:`` block — the enclosing-guard signal for Facet 1.
_TRY_OPENER = re.compile(r'^\s*try\s*:')
# A function/class definition header — the function-boundary signal that resets
# the "are we inside a try block?" state for Facet 1.
_DEF_OR_CLASS_HEADER = re.compile(r'^\s*(?:async\s+def|def|class)\s+\w+')

# Count-prose-staleness detection (Facet 2).
# A digit OR an English number word immediately adjacent to one of the
# cardinality nouns. The cognitive review re-checks the number's correctness
# after a sibling file in the same skill directory changed.
_NUMBER_WORDS = (
    'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty'
)
_CARDINALITY_NOUNS = 'operations?|fields?|steps?|rules?|commands?'
# Number (digit or word) directly before a cardinality noun: ``twelve fields``,
# ``5 rules``, ``nine checks`` are matched; a digit not adjacent to a noun is not.
_COUNT_PROSE = re.compile(
    rf'(?i)\b(?:\d+|{_NUMBER_WORDS})\s+(?:{_CARDINALITY_NOUNS})\b'
)

# Same-document ordinal-reference detection.
# An ordinal cross-reference inside a ``.md`` body — a textual pointer at a
# numbered list item or step BY ITS POSITION. Three forms are recognized, each
# capturing the referenced ordinal number in a named group ``n``:
#   * ``item N`` / ``step N`` / ``point N`` (a form noun directly before a digit);
#   * a bare parenthesized ordinal ``(N)`` (a digit alone inside parentheses).
# These are the references that silently go stale when a numbered list is
# reordered or has an item inserted — the cognitive review re-checks them
# against the enclosing ordered-list block.
_ORDINAL_NOUN_REFERENCE = re.compile(
    r'(?i)\b(?:item|step|point)\s+(?P<n>\d+)\b'
)
_ORDINAL_PAREN_REFERENCE = re.compile(
    r'(?<![\w.])\((?P<n>\d+)\)'
)
# An ordered-list item line in a ``.md`` body: optional leading indentation
# followed by ``N.`` (a digit run, a literal dot, then whitespace). Group ``n``
# captures the item's ordinal so the enclosing block can be located by number.
_ORDERED_LIST_ITEM = re.compile(
    r'^(?P<indent>\s*)(?P<n>\d+)\.\s'
)

# Near-identical-hunk touched-claim detection (Facet 3).
# Tokenizer that splits a line into word/identifier/number/punctuation tokens.
# Two lines that tokenize identically except for exactly one differing token are
# a single-token swap — the ``+`` line is surfaced so the cognitive pass
# re-verifies the REST of the line's claims, not just the swapped token.
_TOKENIZE = re.compile(r'\w+|[^\w\s]')

# Advertised-form-help-string detection.
# An argparse field whose ``help=`` string advertises MORE THAN ONE accepted
# input form (e.g. "Issue number or URL", "path or ref"). The canonical signal
# is a disjunction (`` or ``) inside the help text adjacent to a form noun —
# URL/path/ref/name/identifier — paired with a bare number/identifier form. The
# regex captures the ``help`` argument's quoted value AND, when present on the
# same call, the ``dest=``/long-flag that names the argparse destination so the
# raw-pass cross-reference can target the right attribute.
#
# Group 1: the long ``--flag`` name (when the add_argument call names one).
# Group 2: the quote char of the help string.
# Group 3: the help string value.
_HELP_FIELD = re.compile(
    r"\bhelp\s*=\s*(?:r|f|rf|fr)?(['\"])(.*?)\1"
)
# The long-flag token of an add_argument call — e.g. ``'--issue'`` or
# ``"--issue-ref"``. Group 1 captures the dest-deriving flag (dashes mapped to
# underscores yields the argparse ``dest``).
_ADD_ARGUMENT_FLAG = re.compile(
    r"""['"]--([A-Za-z][A-Za-z0-9_-]*)['"]"""
)
# An explicit ``dest='name'`` keyword on an add_argument call. Group 2 captures
# the destination attribute name verbatim (overrides the flag-derived dest).
_DEST_KWARG = re.compile(
    r"""\bdest\s*=\s*(['\"])([A-Za-z_][A-Za-z0-9_]*)\1"""
)
# A multi-form advertisement marker inside a help string: a `` or `` disjunction
# adjacent to one of the form nouns (URL/path/ref/name/identifier/id). Matched
# case-insensitively. The presence of this marker is what distinguishes a
# multi-form help ("Issue number or URL") from a single-form help ("Issue
# number").
_MULTI_FORM_MARKER = re.compile(
    r'(?i)\bor\b.*\b(?:url|uri|path|ref|name|identifier|id|slug|number)\b'
    r'|\b(?:url|uri|path|ref|name|identifier|id|slug|number)\b.*\bor\b'
)
# Tokens that normalize an externally-supplied value into a single canonical
# form — when a handler routes ``args.<dest>`` through one of these before use,
# the advertised forms are reconciled and no candidate is surfaced.
_NORMALIZATION_TOKENS = re.compile(
    r'\b(?:normali[sz]e|parse|resolve|canonical|extract|to_url|to_id|'
    r'from_url|split|strip|rstrip|lstrip|replace|urlparse|sub)\b'
)


# =============================================================================
# Helpers
# =============================================================================


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit characters, adding ellipsis when shortened."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + '...'


def _run_git(project_dir: Path, *args: str) -> tuple[int, str, str]:
    """Run a git command via ``git -C {project_dir} ...`` and return (returncode, stdout, stderr)."""
    cmd = ['git', '-C', str(project_dir), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, proc.stdout, proc.stderr


def _resolve_footprint(project_dir: Path, base_branch: str) -> list[str]:
    """Derive the plan footprint live from the worktree.

    Computes the on-demand footprint via ``compute_plan_branch_diff``
    (``{base}...HEAD`` ∪ porcelain) read straight from ``project_dir``. Returns
    repo-relative paths, or an empty list on a git error — an empty footprint
    means "do not filter the surfaced diff", preserving the prior behaviour when
    no scope was resolvable.
    """
    try:
        footprint = compute_plan_branch_diff(project_dir, base_branch)
    except subprocess.CalledProcessError:
        return []
    return sorted(footprint)


def _verify_base_branch(project_dir: Path, base_branch: str) -> bool:
    """Return True if the base branch ref resolves inside the project dir."""
    rc, _, _ = _run_git(project_dir, 'rev-parse', '--verify', base_branch)
    return rc == 0


def _diff_hunks(project_dir: Path, base_branch: str) -> str:
    """Return the post-image diff of the working tree against the merge-base.

    The diff TARGET is the **working tree** (not ``HEAD``) precisely BECAUSE
    ``pre-submission-self-review`` runs BEFORE ``commit-push`` — the changes
    under review are typically uncommitted (staged AND unstaged), so they must
    still be surfaced. This preserves the documented pre-commit timing contract.

    The diff ANCHOR is the **merge-base** of ``base_branch`` and ``HEAD``
    (``git merge-base {base_branch} HEAD``), NOT the base-branch tip. Diffing
    against the merge-base excludes commits that arrived on the branch FROM
    ``base_branch`` via an absorb merge — those commits sit at or below the
    merge-base and so fall outside the diff range, removing absorbed-merge
    pollution from the surfaced review surface.

    This is deliberately NEITHER of the two rejected alternatives:

    * NOT a naive ``{base_branch}...HEAD`` three-dot diff — that diffs HEAD (not
      the working tree) against the merge-base, dropping the uncommitted
      pre-submission changes the review exists to surface.
    * NOT the old naive two-dot ``git diff {base_branch}`` against an advanced
      base tip — when the base tip has been absorbed into the branch, that diff
      re-includes the absorbed-upstream content.

    On a merge-base resolution failure (non-zero rc or empty output), falls back
    to the prior two-dot ``git diff {base_branch}`` so the function never returns
    an empty surface on a transient git failure. The existing fail-safe
    ``return ''`` is preserved only for the case where the diff itself fails.
    """
    mb_rc, mb_out, _ = _run_git(project_dir, 'merge-base', base_branch, 'HEAD')
    merge_base = mb_out.strip() if mb_rc == 0 else ''
    anchor = merge_base or base_branch
    rc, out, _ = _run_git(project_dir, 'diff', '--unified=3', anchor)
    if rc != 0:
        return ''
    return out


def _read_post_image(project_dir: Path, repo_relative_path: str) -> list[str]:
    """Return the worktree's current contents of repo_relative_path as a list of lines."""
    full = project_dir / repo_relative_path
    if not full.is_file():
        return []
    try:
        return full.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Diff parsing
# =============================================================================


def _iter_added_lines(diff_text: str) -> list[tuple[str, int, str]]:
    """Yield ``(file_path, post_image_line_no, content)`` for each added line in the diff."""
    out: list[tuple[str, int, str]] = []
    current_file: str | None = None
    post_line = 0
    for raw in diff_text.splitlines():
        m_file = _FILE_HEADER.match(raw)
        if m_file is not None:
            current_file = m_file.group(1)
            post_line = 0
            continue
        m_hunk = _HUNK_HEADER.match(raw)
        if m_hunk is not None:
            post_line = int(m_hunk.group(1))
            continue
        if current_file is None:
            continue
        if raw.startswith('+++') or raw.startswith('---'):
            continue
        if raw.startswith('+'):
            content = raw[1:]
            out.append((current_file, post_line, content))
            post_line += 1
            continue
        if raw.startswith('-'):
            continue
        if raw.startswith(' '):
            post_line += 1
            continue
        if raw.startswith('\\'):
            continue
    return out


def _iter_changed_line_pairs(diff_text: str) -> list[tuple[str, int, str, str]]:
    """Yield ``(file_path, post_image_line_no, removed, added)`` for adjacent
    ``-``/``+`` pairs within a hunk.

    A pair is a removed line immediately followed by an added line in the same
    hunk. The ``post_image_line_no`` is the added line's post-image line number.
    Unpaired ``+`` lines (an addition not preceded by a removal) and unpaired
    ``-`` lines (a removal not followed by an addition) are ignored — only the
    one-for-one swap shape Facet 3 cares about is yielded. ``_iter_added_lines``
    is intentionally left untouched (other detectors depend on its added-only
    shape); this helper is the removed-line-aware companion.
    """
    out: list[tuple[str, int, str, str]] = []
    current_file: str | None = None
    post_line = 0
    pending_removed: str | None = None
    for raw in diff_text.splitlines():
        m_file = _FILE_HEADER.match(raw)
        if m_file is not None:
            current_file = m_file.group(1)
            post_line = 0
            pending_removed = None
            continue
        m_hunk = _HUNK_HEADER.match(raw)
        if m_hunk is not None:
            post_line = int(m_hunk.group(1))
            pending_removed = None
            continue
        if current_file is None:
            continue
        if raw.startswith('+++') or raw.startswith('---'):
            continue
        if raw.startswith('-'):
            pending_removed = raw[1:]
            continue
        if raw.startswith('+'):
            content = raw[1:]
            if pending_removed is not None:
                out.append((current_file, post_line, pending_removed, content))
            pending_removed = None
            post_line += 1
            continue
        if raw.startswith(' '):
            pending_removed = None
            post_line += 1
            continue
        if raw.startswith('\\'):
            continue
        pending_removed = None
    return out


# =============================================================================
# Detectors
# =============================================================================


def _detect_regexes(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for path, lineno, content in added:
        if not (path.endswith('.py') or path.endswith('.md')):
            continue
        for m in _RE_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _FNMATCH_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _RAW_REGEX_LITERAL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
    return out


def _detect_user_facing_strings(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev_def_or_class = False
    for path, lineno, content in added:
        if path.endswith('.md'):
            m_h = _MD_HEADING.match(content)
            if m_h is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_heading',
                        'text': _truncate(m_h.group(2), 200),
                    }
                )
                prev_def_or_class = False
                continue
            m_b = _MD_BULLET.match(content)
            if m_b is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_bullet',
                        'text': _truncate(m_b.group(1), 200),
                    }
                )
                prev_def_or_class = False
                continue
            prev_def_or_class = False
            continue
        if not path.endswith('.py'):
            prev_def_or_class = False
            continue
        if _DEF_OR_CLASS.match(content):
            prev_def_or_class = True
            continue
        if prev_def_or_class:
            m_t = _TRIPLE_QUOTE.match(content)
            if m_t is not None:
                tail = m_t.group(2)
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'docstring',
                        'text': _truncate(tail, 200),
                    }
                )
                prev_def_or_class = False
                continue
        prev_def_or_class = False
        for m in _PRINT_CALL.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'print',
                    'text': _truncate(m.group(2), 200),
                }
            )
        for m in _ARGPARSE_FIELD.finditer(content):
            field = m.group(1)
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': f'argparse_{field}',
                    'text': _truncate(m.group(3), 200),
                }
            )
        for m in _RAISE_MESSAGE.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'raise_message',
                    'text': _truncate(m.group(2), 200),
                }
            )
    return out


def _detect_markdown_sections(added: list[tuple[str, int, str]], project_dir: Path) -> list[dict[str, Any]]:
    """Emit one entry per added/edited heading, with sibling list (peer headings under same parent)."""
    md_files: dict[str, set[int]] = {}
    for path, lineno, content in added:
        if not path.endswith('.md'):
            continue
        if _MD_HEADING.match(content) is None:
            continue
        md_files.setdefault(path, set()).add(lineno)

    out: list[dict[str, Any]] = []
    for md_path, edited_lines in md_files.items():
        post_image = _read_post_image(project_dir, md_path)
        # Build a list of (line_no, depth, heading, parent_path) for every heading in the file.
        headings: list[dict[str, Any]] = []
        ancestor_stack: list[tuple[int, str]] = []  # (depth, heading)
        for idx, line in enumerate(post_image, start=1):
            m = _MD_HEADING.match(line)
            if m is None:
                continue
            depth = len(m.group(1))
            text = m.group(2)
            while ancestor_stack and ancestor_stack[-1][0] >= depth:
                ancestor_stack.pop()
            parent = ancestor_stack[-1][1] if ancestor_stack else ''
            headings.append({'line': idx, 'depth': depth, 'heading': text, 'parent': parent})
            ancestor_stack.append((depth, text))
        # For each edited heading, gather siblings under same parent at same depth.
        for h in headings:
            if h['line'] not in edited_lines:
                continue
            siblings = [
                other['heading']
                for other in headings
                if other is not h and other['depth'] == h['depth'] and other['parent'] == h['parent']
            ]
            out.append(
                {
                    'file': md_path,
                    'line': h['line'],
                    'heading': _truncate(h['heading'], 120),
                    'siblings': '; '.join(_truncate(s, 80) for s in siblings),
                }
            )
    return out


_FENCED_SCHEMA_BLOCK = re.compile(r'^```(json|toon)\b', re.MULTILINE)


def _find_skill_dir(modified_path: Path, project_dir: Path) -> Path | None:
    """Walk up from a modified file looking for a directory that contains SKILL.md.

    Returns the skill directory or None when the modified file is not nested
    inside a skill. The walk is bounded by ``project_dir`` so we never escape
    the worktree.
    """
    current = modified_path.parent if modified_path.is_file() else modified_path
    while True:
        try:
            current.relative_to(project_dir)
        except ValueError:
            return None
        if (current / 'SKILL.md').is_file():
            return current
        if current == project_dir or current.parent == current:
            return None
        current = current.parent


def _collect_skill_contract_sources(skill_dir: Path) -> list[Path]:
    """Return SKILL.md plus every standards/*.md inside the skill directory."""
    sources: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        sources.append(skill_md)
    standards_dir = skill_dir / 'standards'
    if standards_dir.is_dir():
        sources.extend(sorted(standards_dir.glob('*.md')))
    return sources


def _collect_schema_bearing_within_radius(
    modified_path: Path, project_dir: Path, radius: int
) -> list[tuple[Path, str]]:
    """Find *.md files reachable within ``radius`` directory levels of the
    modified file whose content contains a fenced JSON or TOON block.

    Walks up at most ``radius`` parents from the modified file's parent
    directory (bounded by ``project_dir``) to choose an anchor, then
    recursively collects every *.md file in the anchor's subtree. ``radius=0``
    restricts the scan to the modified file's own parent directory only.

    Returns a list of (path, format) tuples where format is 'json' or 'toon'.
    """
    if not modified_path.is_file():
        return []
    anchor = modified_path.parent
    for _ in range(radius):
        if anchor == project_dir or anchor.parent == anchor:
            break
        try:
            anchor.parent.relative_to(project_dir)
        except ValueError:
            break
        anchor = anchor.parent

    out: list[tuple[Path, str]] = []
    try:
        if radius == 0:
            md_iter = sorted(anchor.glob('*.md'))
        else:
            md_iter = sorted(anchor.rglob('*.md'))
    except OSError:
        return []

    for md in md_iter:
        try:
            text = md.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        m = _FENCED_SCHEMA_BLOCK.search(text)
        if m is not None:
            out.append((md, m.group(1)))
    return out


def _doc_referenced_skill_sources(
    md_added: list[tuple[int, str]], project_dir: Path
) -> list[str]:
    """Return repo-relative SKILL.md paths referenced by a doc's added lines.

    A doc *references* a sibling script's output contract when its added lines
    contain BOTH an ``execute-script.py`` invocation via ``{bundle}:{skill}:{script}``
    notation AND a TOON-field reference (a ``{field}`` interpolation token such as
    ``{status}`` or ``{error}``). The two signals need not appear on the same
    added line — the doc as a whole (its added hunk content) must satisfy both.

    For each distinct ``{bundle}:{skill}`` notation found, the referenced
    script's ``SKILL.md`` resolves to
    ``marketplace/bundles/{bundle}/skills/{skill}/SKILL.md``. A path is emitted
    only when that ``SKILL.md`` exists on disk under ``project_dir`` (a dangling
    notation surfaces nothing). The returned list is sorted and deduplicated.
    """
    has_toon_field = any(_TOON_FIELD_TOKEN.search(content) for _, content in md_added)
    if not has_toon_field:
        return []

    rel_sources: set[str] = set()
    for _, content in md_added:
        for m in _EXECUTE_SCRIPT_NOTATION.finditer(content):
            bundle, skill = m.group(1), m.group(2)
            rel = f'marketplace/bundles/{bundle}/skills/{skill}/SKILL.md'
            if (project_dir / rel).is_file():
                rel_sources.add(rel)
    return sorted(rel_sources)


def _detect_contract_sources(
    modified_files: list[str],
    project_dir: Path,
    radius: int,
    added: list[tuple[str, int, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (contract_sources, schema_bearing_files).

    ``contract_sources``: one entry per modified file that has any contract
    source. Sources come from two unioned origins:

    * **directory-structural** — when the modified file is nested inside a skill
      directory, every SKILL.md and standards/*.md in that skill;
    * **doc-prose script reference** (``.md`` files only) — when the doc's added
      lines reference a sibling script's output contract (an
      ``execute-script.py`` invocation via ``{bundle}:{skill}:{script}`` notation
      AND a TOON-field token such as ``{status}``), the referenced script's
      SKILL.md. See ``_doc_referenced_skill_sources``.

    The ``sources`` field is a ``; ``-joined, sorted, deduplicated string of the
    unioned repo-relative paths.

    ``schema_bearing_files``: a flat, deduplicated list of *.md files within
    ``radius`` directory levels of any modified file whose content contains a
    fenced JSON or TOON block. Entries reflect the dominant fence format.
    """
    contract_entries: list[dict[str, Any]] = []
    schema_seen: dict[Path, str] = {}

    # Group added lines by modified .md file so each doc's reference scan sees
    # only its own added hunk content. When ``added`` is None (callers that do
    # not pass diff content), the content-aware augmentation is simply inert.
    md_added_by_file: dict[str, list[tuple[int, str]]] = {}
    for added_path, added_lineno, added_content in added or []:
        if added_path.endswith('.md'):
            md_added_by_file.setdefault(added_path, []).append((added_lineno, added_content))

    for rel in modified_files:
        modified_path = (project_dir / rel).resolve()
        try:
            modified_path.relative_to(project_dir)
        except ValueError:
            continue

        union_sources: set[str] = set()

        skill_dir = _find_skill_dir(modified_path, project_dir)
        if skill_dir is not None:
            structural = _collect_skill_contract_sources(skill_dir)
            union_sources.update(str(p.relative_to(project_dir)) for p in structural)

        if rel.endswith('.md'):
            union_sources.update(
                _doc_referenced_skill_sources(md_added_by_file.get(rel, []), project_dir)
            )

        if union_sources:
            contract_entries.append(
                {
                    'file': rel,
                    'sources': '; '.join(sorted(union_sources)),
                }
            )

        for path, fmt in _collect_schema_bearing_within_radius(modified_path, project_dir, radius):
            schema_seen.setdefault(path, fmt)

    schema_entries = [
        {'file': str(p.relative_to(project_dir)), 'format': fmt} for p, fmt in sorted(schema_seen.items())
    ]
    return contract_entries, schema_entries


def _detect_keep_markers(
    added: list[tuple[str, int, str]], project_dir: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    """Scan added lines for ``<!-- self-review: keep <id> -->`` markers.

    Returns ``(candidates, protected_identifiers)``:

    - ``candidates``: one entry per recognized marker. Each entry carries
      ``identifier``, ``file``, ``line``, and ``kind``. ``kind`` is
      ``keep_protected`` when the identifier is still grep-able in the
      file's post-image (outside the marker line itself), or
      ``keep_violation`` when the consolidation removed the protected
      token and the marker is now orphaned.
    - ``protected_identifiers``: the deduplicated, sorted set of every
      identifier whose marker resolved to ``keep_protected``. The LLM
      cognitive review consumes this list to refuse consolidations that
      drop a protected token.

    The marker line itself is excluded from the grep-ability check, so the
    marker token's presence in its own comment never counts as evidence
    that the protected identifier still exists.
    """
    # Group markers by file so each post-image is read at most once.
    by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        for m in _KEEP_MARKER.finditer(content):
            identifier = m.group(1)
            by_file.setdefault(path, []).append((lineno, identifier))

    candidates: list[dict[str, Any]] = []
    protected: set[str] = set()

    for path, markers in by_file.items():
        post_image = _read_post_image(project_dir, path)
        # Exclude ALL lines containing a keep marker so no marker comment's
        # own copy of the identifier (whether added in this diff or pre-existing)
        # can mask a removal.  Using line-number exclusion was insufficient
        # because it only covered markers added in the current diff, not
        # pre-existing markers that also carry the identifier text.
        non_marker_lines = [
            line
            for line in post_image
            if not _KEEP_MARKER.search(line)
        ]
        non_marker_blob = '\n'.join(non_marker_lines)

        for lineno, identifier in markers:
            # Use word-boundary guards to avoid false-positive substring matches
            # (e.g. identifier 'body' matching inside 'nobody' or 'method_body').
            pattern = re.compile(
                r'(?<![a-zA-Z0-9_-])' + re.escape(identifier) + r'(?![a-zA-Z0-9_-])'
            )
            still_present = bool(pattern.search(non_marker_blob))
            kind = 'keep_protected' if still_present else 'keep_violation'
            candidates.append(
                {
                    'file': path,
                    'line': lineno,
                    'identifier': identifier,
                    'kind': kind,
                }
            )
            if still_present:
                protected.add(identifier)

    return candidates, sorted(protected)


def _load_test_tree_blob(project_dir: Path) -> str:
    """Read every ``*.py`` file under ``{project_dir}/test`` once and return a
    single newline-joined blob of their contents.

    This is the read-once index that lets ``_symmetric_pair_has_test`` answer
    repeated membership queries without re-walking the test tree or re-reading
    files per call. A missing ``test/`` directory, a walk failure, or an
    unreadable file contributes nothing — the corresponding content is simply
    absent from the blob, preserving the original per-file fail-soft behaviour.
    The scan is read-only and stdlib-only.
    """
    test_root = project_dir / 'test'
    if not test_root.is_dir():
        return ''
    try:
        test_files = sorted(test_root.rglob('*.py'))
    except OSError:
        return ''
    chunks: list[str] = []
    for test_file in test_files:
        try:
            chunks.append(test_file.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            continue
    return '\n'.join(chunks)


def _name_in_test_blob(name: str, test_blob: str) -> bool:
    """Return True when ``name`` occurs in ``test_blob`` on a word boundary.

    The word-boundary guard mirrors the identifier-first discipline used by
    ``_detect_keep_markers``: the same ``(?<![a-zA-Z0-9_-])`` /
    ``(?![a-zA-Z0-9_-])`` lookarounds avoid false-positive substring hits
    (e.g. ``save_state`` matching inside ``save_state_v2``). An empty blob
    (missing test tree, unreadable files, or no test sources) yields ``False``.
    """
    if not test_blob:
        return False
    pattern = re.compile(
        r'(?<![a-zA-Z0-9_-])' + re.escape(name) + r'(?![a-zA-Z0-9_-])'
    )
    return bool(pattern.search(test_blob))


def _symmetric_pair_has_test(name: str, project_dir: Path) -> bool:
    """Return True when the worktree's ``test/`` tree references ``name``.

    Searches every ``*.py`` file under ``{project_dir}/test`` for a
    word-boundary occurrence of the function name. ``test_present=false`` is
    the Tier-2 missing-test signal; a missing ``test/`` directory, an
    unreadable file, or no match yields ``False``. The scan is read-only and
    stdlib-only.

    This is the single-query entry point. It builds the test-tree blob via
    ``_load_test_tree_blob`` and delegates the word-boundary match to
    ``_name_in_test_blob``. Hot paths that issue many membership queries
    (e.g. ``_detect_symmetric_pairs``) MUST build the blob once via
    ``_load_test_tree_blob`` and call ``_name_in_test_blob`` directly to
    avoid re-reading the test tree per call.
    """
    return _name_in_test_blob(name, _load_test_tree_blob(project_dir))


def _detect_symmetric_pairs(added: list[tuple[str, int, str]], project_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Build the test-tree blob once for the whole detection pass so each
    # candidate's test_present query is an in-memory regex search rather than
    # a fresh O(M) walk + read of the test tree (eliminates the O(N*M) disk
    # I/O that re-reading per candidate would cause).
    test_blob = _load_test_tree_blob(project_dir)
    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _DEF_NAME.match(content)
        if m is None:
            continue
        name = m.group(1)
        parts = name.split('_')
        partner_name: str | None = None
        for tok_a, tok_b in _PAIR_TOKENS:
            if tok_a in parts:
                idx = parts.index(tok_a)
                swapped = list(parts)
                swapped[idx] = tok_b
                partner_name = '_'.join(swapped)
                break
            if tok_b in parts:
                idx = parts.index(tok_b)
                swapped = list(parts)
                swapped[idx] = tok_a
                partner_name = '_'.join(swapped)
                break
        if partner_name is None:
            continue
        out.append(
            {
                'file': path,
                'line': lineno,
                'name': name,
                'partner': partner_name,
                'test_present': _name_in_test_blob(name, test_blob),
            }
        )
    return out


def _detect_flag_guard_pairs(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect argument-presence guards over a ``--flag`` token and classify the
    flag *forms* each guard covers.

    Scans added ``.py`` lines for membership/substring guards
    (``'--flag' in args``) and ``startswith`` guards
    (``arg.startswith('--flag')``). The bare ``--flag`` token guards the
    space-separated form (``--flag value``); the ``--flag=`` prefix guards the
    equals form (``--flag=value``).

    Aggregates per ``(file, flag)``: when a flag is guarded only by its bare
    token the coverage is ``space``; only by its ``--flag=`` prefix it is
    ``equals``; when both appear in the same file it is ``both``. The ``line``
    field records the first guard occurrence for the flag in the file. The
    aggregation is what lets the cognitive review compare form coverage across
    two sibling guards in the same change — a ``both``/single-form asymmetry is
    the flag-form-coverage defect class.
    """
    # Per (file, flag): track covered forms and the first occurrence line.
    coverage: dict[tuple[str, str], set[str]] = {}
    first_line: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []

    def _record(path: str, lineno: int, flag: str, has_equals: bool) -> None:
        key = (path, flag)
        if key not in coverage:
            coverage[key] = set()
            first_line[key] = lineno
            order.append(key)
        coverage[key].add('equals' if has_equals else 'space')

    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        for m in _FLAG_MEMBERSHIP_GUARD.finditer(content):
            _record(path, lineno, m.group(2), bool(m.group(3)))
        for m in _FLAG_STARTSWITH_GUARD.finditer(content):
            _record(path, lineno, m.group(2), bool(m.group(3)))

    out: list[dict[str, Any]] = []
    for key in order:
        forms = coverage[key]
        if forms == {'space', 'equals'}:
            forms_covered = 'both'
        elif forms == {'equals'}:
            forms_covered = 'equals'
        else:
            forms_covered = 'space'
        path, flag = key
        out.append(
            {
                'file': path,
                'line': first_line[key],
                'flag': flag,
                'forms_covered': forms_covered,
            }
        )
    return out


def _detect_producer_consumer(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect produced output keys that have no consumer in the same diff.

    A *producer* is a subscript assignment into an output dict
    (``output['key'] = ...``) in an added ``.py`` line. A *consumer* is any
    added ``.py`` line that READS that key back — a subscript read
    (``foo['key']`` that is NOT itself a producer assignment) or a
    ``.get('key')`` call. For each produced key with no consumer anywhere in
    the added lines the detector emits a candidate so the cognitive review can
    decide whether the dangling producer is a real defect (a value emitted but
    never read by any downstream branch).

    Each entry carries ``file``, ``line`` (the producer line), ``key``, and
    ``consumed`` (always ``false`` for an emitted candidate — only unconsumed
    producers are surfaced). The ``consumed`` field keeps the entry shape
    self-describing for the LLM consumer.
    """
    # Collect every produced key (first producer line wins) and every consumed
    # key across the whole added-line set. A key produced in one file and
    # consumed in another still counts as consumed — the producer-consumer
    # relation is diff-global, not per-file.
    produced: dict[str, tuple[str, int]] = {}
    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _PRODUCER_SUBSCRIPT_ASSIGN.match(content)
        if m is not None:
            key = m.group(2)
            produced.setdefault(key, (path, lineno))

    consumed: set[str] = set()
    for path, _lineno, content in added:
        if not path.endswith('.py'):
            continue
        # A producer line is not its own consumer: the LHS subscript on a
        # producer line (``output['k'] = ...``) must not register ``k`` as
        # consumed. Resolve the producer's own key once, then skip exactly that
        # key on the producer line — any OTHER key read on the same line still
        # counts as a consumption.
        producer_match = _PRODUCER_SUBSCRIPT_ASSIGN.match(content)
        producer_key = producer_match.group(2) if producer_match is not None else None
        for m in _CONSUMER_SUBSCRIPT_READ.finditer(content):
            read_key = m.group(2)
            if read_key == producer_key:
                continue
            consumed.add(read_key)
        for m in _CONSUMER_GET_READ.finditer(content):
            consumed.add(m.group(2))

    out: list[dict[str, Any]] = []
    for key in sorted(produced):
        if key in consumed:
            continue
        path, lineno = produced[key]
        out.append({'file': path, 'line': lineno, 'key': key, 'consumed': False})
    return out


def _detect_source_of_truth(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect a constant duplicated across two diff files with divergent values.

    Scans added ``.py`` lines for ``NAME = <literal>`` bindings where ``NAME``
    is an UPPER_SNAKE_CASE identifier (the conventional source-of-truth
    constant shape). When the SAME constant name is assigned in two or more
    distinct files within the diff AND the assigned literals are NOT all
    identical, the duplicate is a source-of-truth drift candidate — the diff
    changed the value in one declared SoT location but not the other.

    Each entry carries ``name`` (the constant), ``files`` (a ``; ``-joined,
    sorted list of the files declaring it), and ``values`` (a ``; ``-joined,
    sorted list of the distinct literal RHS values). Only constants with a
    cross-file value divergence are surfaced; a constant assigned the same
    value in two files, or a constant in a single file, is not a defect.
    """
    # Per constant name: map file -> set of literal RHS values declared there.
    by_name: dict[str, dict[str, set[str]]] = {}
    for path, _lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _CONSTANT_ASSIGN.match(content)
        if m is None:
            continue
        name = m.group(1)
        value = m.group(2)
        by_name.setdefault(name, {}).setdefault(path, set()).add(value)

    out: list[dict[str, Any]] = []
    for name in sorted(by_name):
        files = by_name[name]
        if len(files) < 2:
            continue
        all_values: set[str] = set()
        for value_set in files.values():
            all_values.update(value_set)
        if len(all_values) < 2:
            continue
        out.append(
            {
                'name': name,
                'files': '; '.join(sorted(files)),
                'values': '; '.join(_truncate(v, 80) for v in sorted(all_values)),
            }
        )
    return out


def _detect_same_document_consistency(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect added normative directives in a ``.md`` body for contradiction review.

    Scans added ``.md`` lines for RFC-2119-style normative keywords (``MUST``,
    ``MUST NOT``, ``SHALL``, ``SHALL NOT``, ``NEVER``, ``ALWAYS``, ``REQUIRED``,
    ``FORBIDDEN``). Each added normative directive is surfaced so the cognitive
    review can compare it against sibling directives ALREADY in the same
    document — a new normative rule that contradicts an existing one in the
    same file is the same-document-consistency defect (Mode 2: the surface MUST
    carry a candidate, never an empty surface, when a normative line is added).

    Each entry carries ``file``, ``line``, ``keyword`` (the normative keyword
    that fired), and ``text`` (the directive line, truncated).
    """
    out: list[dict[str, Any]] = []
    for path, lineno, content in added:
        if not path.endswith('.md'):
            continue
        m = _NORMATIVE_DIRECTIVE.search(content)
        if m is None:
            continue
        out.append(
            {
                'file': path,
                'line': lineno,
                'keyword': m.group(1),
                'text': _truncate(content.strip(), 200),
            }
        )
    return out


def _detect_description_vs_body(
    added: list[tuple[str, int, str]], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect a ``.md`` whose frontmatter description and body both changed.

    A frontmatter ``description:`` (or ``summary:``) line summarizes the
    document's model; the body implements it. When the diff touches a ``.md``
    file's body AND that file carries a frontmatter ``description``/``summary``
    key in its post-image, the description may now describe a model the body no
    longer implements (Mode 1 recurrence — the phase-3 frontmatter case where a
    deleted machinery left a stale description behind).

    The detector surfaces one candidate per modified ``.md`` file that (a) has
    at least one added body line (any added line below the closing frontmatter
    delimiter) AND (b) carries a frontmatter ``description``/``summary`` key in
    its post-image. The entry carries ``file``, ``line`` (the frontmatter
    description line in the post-image), ``key`` (``description`` or
    ``summary``), and ``description`` (the description value, truncated) so the
    cognitive review can read the description against the changed body.
    """
    # Group added lines per .md file.
    md_added_files: dict[str, list[int]] = {}
    for path, lineno, _content in added:
        if path.endswith('.md'):
            md_added_files.setdefault(path, []).append(lineno)

    out: list[dict[str, Any]] = []
    for md_path in sorted(md_added_files):
        post_image = _read_post_image(project_dir, md_path)
        if not post_image:
            continue
        # Resolve the frontmatter block: it opens with a ``---`` on line 1 and
        # closes at the next ``---``. The description key must live inside it.
        if not post_image or post_image[0].strip() != '---':
            continue
        fm_close = None
        for idx in range(1, len(post_image)):
            if post_image[idx].strip() == '---':
                fm_close = idx
                break
        if fm_close is None:
            continue
        desc_line_no: int | None = None
        desc_key: str | None = None
        desc_value: str | None = None
        for idx in range(1, fm_close):
            m = _FRONTMATTER_DESCRIPTION.match(post_image[idx])
            if m is not None:
                desc_line_no = idx + 1  # 1-based
                desc_key = m.group(1)
                desc_value = m.group(2)
                break
        if desc_line_no is None or desc_key is None or desc_value is None:
            continue
        # Require at least one added line in the document body (below the
        # closing frontmatter delimiter) — a pure frontmatter-only edit does
        # not surface a body-vs-description candidate.
        body_close_line = fm_close + 1  # 1-based line number of the closing ---
        has_body_edit = any(ln > body_close_line for ln in md_added_files[md_path])
        if not has_body_edit:
            continue
        out.append(
            {
                'file': md_path,
                'line': desc_line_no,
                'key': desc_key,
                'description': _truncate(desc_value, 200),
            }
        )
    return out


def _detect_unguarded_boundaries(
    added: list[tuple[str, int, str]], project_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Detect an added subprocess/file-I/O boundary call with no guard (Facet 1).

    Scans added ``.py`` lines for a boundary call and surfaces it when BOTH
    hold:

    1. the call is unguarded — for a ``subprocess.*`` call, ``check=True`` is
       absent on the same line; a file-I/O call (``open(``,
       ``Path.read_text``/``write_text``/``read_bytes``/``write_bytes``) is
       always treated as unguarded by criterion 1 since it has no ``check``
       kwarg; AND
    2. there is no enclosing ``try`` block in the same function — tracked by a
       per-file walk that opens an "inside try" window at a ``try:`` opener and
       closes it at the next def/class header.

    When ``project_dir`` is provided the function reads the full post-image of
    each changed ``.py`` file and walks every line to build accurate
    try-block / function-boundary state.  This ensures that pre-existing
    ``try`` blocks and ``def``/``class`` headers — which are absent from the
    diff's ``added`` lines — are correctly accounted for.  When the file is not
    present on disk (e.g. in unit tests without a ``project_dir``), the
    function falls back to scanning only the ``added`` lines, which preserves
    the original behaviour for test scenarios.

    Network calls (``socket.``, ``urllib.``, ``http.client.``) are out of scope
    and never matched (their absence from the boundary regexes is the exclusion).
    The existing sibling-envelope unguarded-pair detection is a separate concern
    and is not re-implemented here.

    Each entry carries ``file``, ``line``, ``boundary`` (the matched call kind),
    and ``guarded`` (always ``False`` for a surfaced entry).
    """
    out: list[dict[str, Any]] = []

    # Group added lines by file so we can process each file independently.
    added_by_file: dict[str, dict[int, str]] = {}
    for path, lineno, content in added:
        if path.endswith('.py'):
            added_by_file.setdefault(path, {})[lineno] = content

    for path, added_lines in added_by_file.items():
        post_image = _read_post_image(project_dir, path) if project_dir is not None else []

        if post_image:
            # Walk the full post-image so that pre-existing try blocks and
            # def/class headers outside the diff are properly tracked.
            inside_try = False
            for idx, line in enumerate(post_image, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if _DEF_OR_CLASS_HEADER.match(line):
                    inside_try = False
                    continue
                if _TRY_OPENER.match(line):
                    inside_try = True
                    continue
                if idx not in added_lines:
                    continue
                content = added_lines[idx]
                sub_match = _SUBPROCESS_BOUNDARY.search(content)
                if sub_match is not None:
                    guarded = inside_try or bool(_CHECK_TRUE_KWARG.search(content))
                    if not guarded:
                        out.append(
                            {
                                'file': path,
                                'line': idx,
                                'boundary': f'subprocess.{sub_match.group(1)}',
                                'guarded': False,
                            }
                        )
                    continue
                if _FILE_IO_BOUNDARY.search(content) is not None:
                    if not inside_try:
                        io_match = _FILE_IO_BOUNDARY.search(content)
                        token = io_match.group(0).rstrip('(') if io_match is not None else 'file_io'
                        out.append(
                            {
                                'file': path,
                                'line': idx,
                                'boundary': token.lstrip('.'),
                                'guarded': False,
                            }
                        )
        else:
            # Fallback: no post-image available — scan only the added lines.
            # A def/class header resets the window (a try cannot span a
            # function boundary), so the "enclosing try in the SAME function"
            # rule is honoured within the diff-only subset.
            inside_try = False
            for lineno, content in sorted(added_lines.items()):
                stripped = content.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if _DEF_OR_CLASS_HEADER.match(content):
                    inside_try = False
                    continue
                if _TRY_OPENER.match(content):
                    inside_try = True
                    continue
                sub_match = _SUBPROCESS_BOUNDARY.search(content)
                if sub_match is not None:
                    guarded = inside_try or bool(_CHECK_TRUE_KWARG.search(content))
                    if not guarded:
                        out.append(
                            {
                                'file': path,
                                'line': lineno,
                                'boundary': f'subprocess.{sub_match.group(1)}',
                                'guarded': False,
                            }
                        )
                    continue
                if _FILE_IO_BOUNDARY.search(content) is not None:
                    if not inside_try:
                        io_match = _FILE_IO_BOUNDARY.search(content)
                        token = io_match.group(0).rstrip('(') if io_match is not None else 'file_io'
                        out.append(
                            {
                                'file': path,
                                'line': lineno,
                                'boundary': token.lstrip('.'),
                                'guarded': False,
                            }
                        )
    return out


def _detect_count_prose(
    modified_files: list[str], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect count-prose in SKILL.md siblings of modified files (Facet 2).

    For each modified file nested inside a skill directory (reuse
    ``_find_skill_dir``), scan every ``SKILL.md`` in that same skill directory
    for count-prose — a digit OR an English number word immediately adjacent to
    one of the cardinality nouns (``operation``, ``field``, ``step``, ``rule``,
    ``command``). The cognitive review re-checks that the surfaced number is
    still correct after a sibling file in the directory changed.

    Each entry carries ``file`` (the SKILL.md path), ``line`` (the matched line
    number, 1-based), and ``text`` (the truncated matched line). Deduplicated
    per ``(file, line)``.
    """
    skill_dirs: set[Path] = set()
    for rel in modified_files:
        modified_path = (project_dir / rel).resolve()
        try:
            modified_path.relative_to(project_dir)
        except ValueError:
            continue
        skill_dir = _find_skill_dir(modified_path, project_dir)
        if skill_dir is not None:
            skill_dirs.add(skill_dir)

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for skill_dir in sorted(skill_dirs):
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel_md = str(skill_md.relative_to(project_dir))
        for idx, line in enumerate(text.splitlines(), start=1):
            if _COUNT_PROSE.search(line) is None:
                continue
            key = (rel_md, idx)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': rel_md, 'line': idx, 'text': _truncate(line.strip(), 200)})
    return out


def _ordered_list_blocks(post_image: list[str]) -> list[dict[str, Any]]:
    """Return every contiguous ordered-list block in a ``.md`` post-image.

    A block is a maximal run of consecutive ``N.`` ordered-list item lines
    (interruptions by a blank line or a non-item line close the block). Each
    returned entry carries ``start`` (the 1-based post-image line of the block's
    first item), ``items`` (a mapping from each item's ordinal number to its
    1-based post-image line), and ``lines`` (the set of 1-based post-image lines
    the block spans, used to test whether the diff touched the block).

    The detector references blocks by the ordinal NUMBER appearing in an
    ``item N`` reference, so a block whose first item is renumbered after an
    insertion still resolves by the current item number present in the block.
    """
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    n_lines = len(post_image)
    for i in range(n_lines):
        idx = i + 1  # 1-based line number
        line = post_image[i]
        m = _ORDERED_LIST_ITEM.match(line)
        if m is not None:
            ordinal = int(m.group('n'))
            if current is None:
                current = {'start': idx, 'items': {}, 'lines': set()}
            current['items'].setdefault(ordinal, idx)
            current['lines'].add(idx)
            continue
        if line.strip() == '':
            # A blank line within an ordered list is tolerated only when it is
            # immediately followed by another item line; treat it as part of the
            # block by recording the line but not closing the block yet.
            if current is not None:
                next_item = next(
                    (post_image[j] for j in range(i + 1, n_lines)
                     if post_image[j].strip() != ''),
                    None,
                )
                if next_item is not None and _ORDERED_LIST_ITEM.match(next_item):
                    current['lines'].add(idx)
                else:
                    blocks.append(current)
                    current = None
            continue
        if current is not None:
            blocks.append(current)
            current = None
    if current is not None:
        blocks.append(current)
    return blocks


def _detect_ordinal_references(
    added: list[tuple[str, int, str]], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect same-document ordinal cross-references into a touched ordered list.

    Scans added ``.md`` lines for an ordinal reference — ``item N`` / ``step N``
    / ``point N`` or a bare parenthesized ``(N)`` — that points at a numbered
    list item BY ITS POSITION. The reference is surfaced as a candidate only
    when, in the same document's post-image, the ordered-list block containing
    item ``N`` was ITSELF touched by the diff (at least one of the block's lines
    is among this file's added lines). That conjunction is the staleness signal:
    inserting or reordering a numbered-list item shifts the ordinals its
    positional cross-references point at, so any ordinal reference into a list
    the same change just edited is a re-verification candidate.

    Each entry carries ``file``, ``line`` (the reference's post-image line),
    ``text`` (the truncated reference line), and ``list_line`` (the 1-based
    post-image line of the referenced ordered-list block — the line of item
    ``N`` when it resolves, else the block's first item line). Deduplicated per
    ``(file, line, ordinal)``.
    """
    # Group added .md lines per file so each file's post-image is read once and
    # the touched-line set is scoped to that file.
    md_added_by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        if path.endswith('.md'):
            md_added_by_file.setdefault(path, []).append((lineno, content))

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for md_path in sorted(md_added_by_file):
        post_image = _read_post_image(project_dir, md_path)
        if not post_image:
            continue
        blocks = _ordered_list_blocks(post_image)
        added_lines = {ln for ln, _ in md_added_by_file[md_path]}

        for lineno, content in md_added_by_file[md_path]:
            for m in _ORDINAL_NOUN_REFERENCE.finditer(content):
                _record_ordinal_reference(
                    out, seen, blocks, added_lines, md_path, lineno, content, int(m.group('n'))
                )
            for m in _ORDINAL_PAREN_REFERENCE.finditer(content):
                _record_ordinal_reference(
                    out, seen, blocks, added_lines, md_path, lineno, content, int(m.group('n'))
                )
    return out


def _record_ordinal_reference(
    out: list[dict[str, Any]],
    seen: set[tuple[str, int, int]],
    blocks: list[dict[str, Any]],
    added_lines: set[int],
    md_path: str,
    lineno: int,
    content: str,
    ordinal: int,
) -> None:
    """Surface one ordinal reference when its referenced list block was touched.

    Resolves the ordered-list block containing item ``ordinal``; fires only when
    that block's line span intersects ``added_lines`` (the diff touched the
    list). Appends a deduplicated candidate to ``out`` carrying ``list_line``,
    the post-image line of item ``ordinal`` (or the block's first item line as a
    fallback). A reference whose ordinal resolves to no ordered-list block, or
    to a block the diff did not touch, surfaces nothing.
    """
    matches = [b for b in blocks if ordinal in b['items']]
    if not matches:
        return
    touched_matches = [b for b in matches if (b['lines'] & added_lines)]
    if not touched_matches:
        return
    target = min(
        touched_matches,
        key=lambda b: abs(b['items'].get(ordinal, b['start']) - lineno),
    )
    key = (md_path, lineno, ordinal)
    if key in seen:
        return
    seen.add(key)
    list_line = target['items'].get(ordinal, target['start'])
    out.append(
        {
            'file': md_path,
            'line': lineno,
            'text': _truncate(content.strip(), 200),
            'list_line': list_line,
        }
    )


def _detect_touched_claims(
    pairs: list[tuple[str, int, str, str]],
) -> list[dict[str, Any]]:
    """Detect near-identical ``-``/``+`` hunk pairs (Facet 3).

    For each adjacent removed/added line pair, tokenize both lines and fire when
    they differ by approximately one token: the two token sequences are equal in
    length AND differ in exactly one position. The ``+`` line is surfaced as a
    ``touched_claim`` candidate so the cognitive pass re-verifies the REST of the
    line's claims, not just the swapped token. A whitespace-only difference
    (identical token sequences) and a many-token difference are both excluded.

    Each entry carries ``file``, ``line`` (the ``+`` line's post-image line
    number), and ``text`` (the truncated ``+`` line).
    """
    out: list[dict[str, Any]] = []
    for path, lineno, removed, added in pairs:
        removed_tokens = _TOKENIZE.findall(removed)
        added_tokens = _TOKENIZE.findall(added)
        if len(removed_tokens) != len(added_tokens):
            continue
        differing = sum(
            1 for a, b in zip(removed_tokens, added_tokens, strict=True) if a != b
        )
        if differing != 1:
            continue
        out.append({'file': path, 'line': lineno, 'text': _truncate(added, 200)})
    return out


def _raw_pass_line_for_dest(
    file_lines: list[tuple[int, str]], dest: str
) -> tuple[int, str] | None:
    """Find a raw-value pass-through of ``args.<dest>`` among ``file_lines``.

    A *raw pass-through* is a use of the argparse destination attribute that
    forwards the externally-supplied value WITHOUT routing it through a
    normalization call first — ``str(args.<dest>)``, a bare ``args.<dest>``
    read, or an f-string interpolation ``{args.<dest>}``. A line that ALSO
    carries a normalization token (``normalize``/``parse``/``urlparse``/...) is
    NOT a raw pass — the value is reconciled there, so it is skipped.

    Returns the first ``(line, content)`` raw-pass occurrence, or ``None`` when
    no raw pass-through of ``args.<dest>`` exists in the candidate scope.
    """
    # Match args.<dest> (attribute access) NOT immediately followed by another
    # identifier char, so ``args.issue`` does not match ``args.issue_url``.
    access = re.compile(
        r'\bargs\.' + re.escape(dest) + r'(?![A-Za-z0-9_])'
    )
    for lineno, content in file_lines:
        if access.search(content) is None:
            continue
        if _NORMALIZATION_TOKENS.search(content) is not None:
            # The value is normalized on this line — not a raw pass-through.
            continue
        return lineno, content
    return None


def _resolve_dest_from_line(content: str) -> str | None:
    """Resolve the argparse dest from a single ``add_argument`` line.

    An explicit ``dest='name'`` kwarg wins; otherwise the long ``--flag`` token
    is mapped to a dest by replacing dashes with underscores. Returns ``None``
    when neither token is present on the line.
    """
    m_dest = _DEST_KWARG.search(content)
    if m_dest is not None:
        return m_dest.group(2)
    m_flag = _ADD_ARGUMENT_FLAG.search(content)
    if m_flag is not None:
        return m_flag.group(1).replace('-', '_')
    return None


def _resolve_dest_from_post_image(
    post_image: list[str], help_lineno: int
) -> str | None:
    """Resolve the dest by reconstructing a multi-line ``add_argument`` call.

    ``help_lineno`` is the 1-based post-image line of the ``help=`` string.
    The walk scans backwards from that line (inclusive) until it reaches the
    line carrying the opening ``add_argument(`` call, accumulating each line's
    flag/dest token along the way. The first resolvable token wins (an explicit
    ``dest=`` on any scanned line takes priority over a ``--flag``, matching the
    single-line precedence). Returns ``None`` when the call's opening cannot be
    located within ``_MAX_CALL_LOOKBACK`` lines or carries no flag/dest token.
    """
    if help_lineno < 1 or help_lineno > len(post_image):
        return None
    idx = help_lineno - 1  # 0-based index into post_image
    flag_dest: str | None = None
    steps = 0
    while idx >= 0 and steps <= _MAX_CALL_LOOKBACK:
        line = post_image[idx]
        m_dest = _DEST_KWARG.search(line)
        if m_dest is not None:
            # Explicit dest= on any line of the call wins immediately.
            return m_dest.group(2)
        if flag_dest is None:
            m_flag = _ADD_ARGUMENT_FLAG.search(line)
            if m_flag is not None:
                flag_dest = m_flag.group(1).replace('-', '_')
        if _ADD_ARGUMENT_OPEN.search(line) is not None:
            # Reached the call's opening line — stop the backward walk.
            return flag_dest
        idx -= 1
        steps += 1
    return None


# The opening token of an ``add_argument`` call. Used as the backward-walk
# terminator when reconstructing a multi-line call from the post-image.
_ADD_ARGUMENT_OPEN = re.compile(r'\.add_argument\s*\(')

# Upper bound on how many lines the backward walk inspects before giving up.
# A single ``add_argument`` call almost never spans more than a handful of
# lines; the cap guards against scanning the whole file when the opening token
# is somehow absent.
_MAX_CALL_LOOKBACK = 40


def _detect_advertised_form_help_strings(
    added: list[tuple[str, int, str]],
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Detect a multi-form ``help=`` string whose handler passes the raw value.

    An argparse ``help`` string that advertises more than one accepted input
    form (e.g. "Issue number or URL") promises the handler will accept every
    advertised form. When the handler then forwards the raw ``args.<dest>``
    value WITHOUT a normalization call (``str(args.issue)``, a bare
    ``args.issue`` read, or an f-string interpolation of it), the advertised
    contract drifts from the handler behaviour — only the form the raw value
    happens to be in actually works.

    For each added ``.py`` line that carries a multi-form ``help=`` string on an
    ``add_argument`` call, the detector resolves the argparse destination (from
    an explicit ``dest=`` kwarg, else from the long ``--flag`` with dashes
    mapped to underscores) and searches the SAME file's added lines for a raw
    pass-through of ``args.<dest>``. A candidate is surfaced only when both the
    multi-form help AND a raw-pass site are present in the diff with no
    intervening normalization on the raw-pass line.

    When ``help=`` sits on a continuation line of a multi-line ``add_argument``
    call, the ``--flag`` / ``dest=`` token lives on a preceding line that may
    not be present in the diff. In that case same-line dest resolution fails. To
    recover, the caller may pass ``project_dir``: the detector then walks
    backwards through the file's post-image from the ``help=`` line to the
    opening ``add_argument(`` and resolves the dest from the reconstructed call
    context. With ``project_dir=None`` (e.g. unit tests, or when the post-image
    is unavailable) the detector falls back to diff-only same-line resolution.

    Each entry carries ``file``, ``line`` (the help-string line), ``arg`` (the
    resolved destination), ``help_text`` (the truncated help string), and
    ``raw_pass_line`` (the post-image line number of the raw pass-through). The
    detector mirrors the review-anchor exclusion of ``contract_sources`` /
    ``schema_bearing_files`` / ``count_prose``: it is NOT summed into
    ``counts.total``.
    """
    # Group added .py lines per file so the raw-pass search is scoped to the
    # same file as the help string (a handler's argument definition and its
    # usage live in one module).
    py_lines_by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        if path.endswith('.py'):
            py_lines_by_file.setdefault(path, []).append((lineno, content))

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    post_image_cache: dict[str, list[str]] = {}
    for path, file_lines in py_lines_by_file.items():
        for lineno, content in file_lines:
            m_help = _HELP_FIELD.search(content)
            if m_help is None:
                continue
            help_text = m_help.group(2)
            if _MULTI_FORM_MARKER.search(help_text) is None:
                continue
            # Resolve the argparse destination: explicit dest= wins, else the
            # long --flag with dashes mapped to underscores. Both tokens may
            # sit on the same diff line as the help string.
            dest = _resolve_dest_from_line(content)
            if dest is None and project_dir is not None:
                # The flag/dest token is on a preceding line of a multi-line
                # add_argument call that is absent from the diff. Reconstruct
                # the call context from the file's post-image and retry.
                if path not in post_image_cache:
                    post_image_cache[path] = _read_post_image(project_dir, path)
                dest = _resolve_dest_from_post_image(
                    post_image_cache[path], lineno
                )
            if dest is None:
                continue
            raw_pass = _raw_pass_line_for_dest(file_lines, dest)
            if raw_pass is None:
                continue
            key = (path, lineno, dest)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'arg': dest,
                    'help_text': _truncate(help_text, 200),
                    'raw_pass_line': raw_pass[0],
                }
            )
    return out


# =============================================================================
# Subcommand: surface
# =============================================================================


def _cmd_surface(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)

    # Routing: when --project-dir is supplied, use it verbatim (escape hatch).
    # When omitted, auto-resolve via manage-status get-worktree-path. Both
    # paths are funneled through resolve_project_dir so the two-state
    # contract is enforced consistently — note that self_review legitimately
    # needs --plan-id for modified-files lookup as well, so an explicit
    # --project-dir alongside is allowed here only as a tie-break (the
    # helper would normally reject the pair via MutuallyExclusiveArgsError;
    # we resolve manually instead).
    if args.project_dir is not None:
        project_dir = Path(args.project_dir).resolve()
    else:
        try:
            resolved = resolve_project_dir(plan_id, None, default=None)
        except WorktreeResolutionError as exc:
            output_toon(emit_worktree_error(plan_id, exc))
            return 2
        project_dir = Path(resolved).resolve()
    base_branch = args.base_branch or 'main'

    if not project_dir.is_dir():
        output_toon_error(
            'project_dir_invalid',
            f'project-dir does not exist or is not a directory: {project_dir}',
        )
        return 1

    rc_check, _, stderr_check = _run_git(project_dir, 'rev-parse', '--git-dir')
    if rc_check != 0:
        output_toon_error(
            'git_unavailable',
            f'git -C {project_dir} rev-parse failed: {stderr_check.strip()}',
        )
        return 1

    if not _verify_base_branch(project_dir, base_branch):
        output_toon_error(
            'base_branch_not_found',
            f'base branch {base_branch!r} does not resolve inside {project_dir}',
        )
        return 1

    modified_files = _resolve_footprint(project_dir, base_branch)

    diff_text = _diff_hunks(project_dir, base_branch)
    added = _iter_added_lines(diff_text)

    if modified_files:
        allowed = set(modified_files)
        added = [(p, ln, c) for (p, ln, c) in added if p in allowed]

    regexes = _detect_regexes(added)
    user_facing = _detect_user_facing_strings(added)
    md_sections = _detect_markdown_sections(added, project_dir)
    sym_pairs = _detect_symmetric_pairs(added, project_dir)
    flag_guard_pairs = _detect_flag_guard_pairs(added)
    contract_sources, schema_bearing = _detect_contract_sources(
        modified_files, project_dir, args.contract_radius, added
    )
    keep_markers, protected_identifiers = _detect_keep_markers(added, project_dir)
    producer_consumer = _detect_producer_consumer(added)
    source_of_truth = _detect_source_of_truth(added)
    same_document = _detect_same_document_consistency(added)
    description_vs_body = _detect_description_vs_body(added, project_dir)
    unguarded_boundaries = _detect_unguarded_boundaries(added, project_dir)
    count_prose = _detect_count_prose(modified_files, project_dir)
    changed_pairs = _iter_changed_line_pairs(diff_text)
    if modified_files:
        allowed = set(modified_files)
        changed_pairs = [pr for pr in changed_pairs if pr[0] in allowed]
    touched_claims = _detect_touched_claims(changed_pairs)
    advertised_form_help_strings = _detect_advertised_form_help_strings(
        added, project_dir
    )
    ordinal_references = _detect_ordinal_references(added, project_dir)

    output = {
        'status': 'success',
        'plan_id': plan_id,
        'project_dir': str(project_dir),
        'base_branch': base_branch,
        'counts': {
            'regexes': len(regexes),
            'user_facing_strings': len(user_facing),
            'markdown_sections': len(md_sections),
            'symmetric_pairs': len(sym_pairs),
            'flag_guard_pairs': len(flag_guard_pairs),
            'contract_sources': len(contract_sources),
            'schema_bearing_files': len(schema_bearing),
            'keep_markers': len(keep_markers),
            'protected_identifiers': len(protected_identifiers),
            'producer_consumer': len(producer_consumer),
            'source_of_truth': len(source_of_truth),
            'same_document_consistency': len(same_document),
            'description_vs_body': len(description_vs_body),
            'unguarded_boundaries': len(unguarded_boundaries),
            'count_prose': len(count_prose),
            'touched_claims': len(touched_claims),
            'advertised_form_help_strings': len(advertised_form_help_strings),
            'ordinal_references': len(ordinal_references),
            # ``count_prose`` and ``advertised_form_help_strings`` are
            # review-anchor lists (like ``contract_sources`` and
            # ``schema_bearing_files``) and are excluded from ``total``; the
            # line-level lists ``unguarded_boundaries``, ``touched_claims``, and
            # ``ordinal_references`` flag a specific added line and are included.
            'total': (
                len(regexes)
                + len(user_facing)
                + len(md_sections)
                + len(sym_pairs)
                + len(flag_guard_pairs)
                + len(keep_markers)
                + len(producer_consumer)
                + len(source_of_truth)
                + len(same_document)
                + len(description_vs_body)
                + len(unguarded_boundaries)
                + len(touched_claims)
                + len(ordinal_references)
            ),
        },
        'regexes': regexes,
        'user_facing_strings': user_facing,
        'markdown_sections': md_sections,
        'symmetric_pairs': sym_pairs,
        'flag_guard_pairs': flag_guard_pairs,
        'contract_sources': contract_sources,
        'schema_bearing_files': schema_bearing,
        'keep_markers': keep_markers,
        'protected_identifiers': protected_identifiers,
        'producer_consumer': producer_consumer,
        'source_of_truth': source_of_truth,
        'same_document_consistency': same_document,
        'description_vs_body': description_vs_body,
        'unguarded_boundaries': unguarded_boundaries,
        'count_prose': count_prose,
        'touched_claims': touched_claims,
        'advertised_form_help_strings': advertised_form_help_strings,
        'ordinal_references': ordinal_references,
    }
    output_toon(output)
    return 0


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Surface candidate lists for pre-submission self-review.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_surface = sub.add_parser(
        'surface',
        help='Emit eighteen candidate lists (regexes, user-facing strings, markdown sections, symmetric pairs, flag-guard pairs, contract sources, schema-bearing files, keep markers, protected identifiers, producer-consumer pairs, source-of-truth duplicates, same-document normative directives, description-vs-body frontmatter, lone-unguarded-boundary calls, stale count-prose, near-identical-hunk touched claims, advertised-form help strings, same-document ordinal references) from the worktree diff as TOON.',
        allow_abbrev=False,
    )
    add_plan_id_arg(p_surface)
    p_surface.add_argument(
        '--project-dir',
        required=False,
        default=None,
        help=(
            'Absolute path to the active git worktree (Bucket B). Optional — '
            'when omitted, the worktree path is auto-resolved from --plan-id '
            'via manage-status get-worktree-path. Supplying both is allowed '
            'here because --plan-id also drives modified-files lookup; the '
            'mutual-exclusivity check applies only to routing.'
        ),
    )
    p_surface.add_argument(
        '--base-branch',
        default='main',
        help='Base branch for diff computation (default: main).',
    )
    p_surface.add_argument(
        '--contract-radius',
        type=int,
        default=3,
        help='Directory levels to walk up when collecting schema-bearing markdown files (default: 3).',
    )
    p_surface.set_defaults(func=_cmd_surface)
    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)
    return int(args.func(args))


if __name__ == '__main__':
    main()
