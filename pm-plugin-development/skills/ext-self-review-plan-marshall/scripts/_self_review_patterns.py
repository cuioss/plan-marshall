#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Compiled detection regexes and constant tuples for self-review candidate surfacing.

Module-level compiled patterns and constant token tuples shared across the
self-review diff-plumbing and detector modules. Importers pull these by flat
name (e.g. ``from _self_review_patterns import _RE_CALL``).
"""

import re

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
