#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Compiled detection regexes and constant tuples for self-review candidate surfacing.

Module-level compiled patterns and constant token tuples shared across the
self-review diff-plumbing and detector modules. Importers pull these by flat
name (e.g. ``from _self_review_patterns import _RE_CALL``).
"""

import re
from typing import NamedTuple

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

# Scan-derived-key (unreachable-guard) detection.
# The scan-versus-anchor shape: a key derived by first-match over an unbounded
# decomposition instead of by indexing that decomposition at a position anchored
# on a known root. See standards/unreachable-guard-detection.md for the gate
# verdict that selected this framing, the two rejected framings, and the
# reachability argument — the rationale is NOT restated here.

# A sequence decomposition binding: ``NAME = <expr>.parts`` or
# ``NAME = <expr>.split(...)``. Group ``name`` captures the bound sequence
# variable, which the scan loop below must iterate for the shape to hold.
_SEQUENCE_DECOMPOSITION = re.compile(
    r'^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*.*?(?:\.parts\b|\.split\s*\()'
)
# A scan loop over a decomposed sequence: ``for part in parts:`` or
# ``for index, part in enumerate(parts):``. Group ``seq`` captures the iterated
# sequence name so it can be matched against a decomposition binding.
_SCAN_LOOP = re.compile(
    r'^\s*for\s+[A-Za-z_][A-Za-z0-9_,\s]*?\s+in\s+(?:enumerate\s*\(\s*)?'
    r'(?P<seq>[A-Za-z_][A-Za-z0-9_]*)'
)
# A pattern-match test inside the scan loop — either a bare ``re.match``/
# ``re.search``/``re.fullmatch`` or the same method on a module-level compiled
# pattern constant (``_VERSION_DIR_NAME_RE.match(...)``). This is what makes the
# selection a *pattern* first-match rather than an ordinary sequence search.
_PATTERN_MATCH_TEST = re.compile(
    r'\b(?:re|_?[A-Z][A-Z0-9_]*)\s*\.\s*(?:match|search|fullmatch)\s*\('
)
# The first-match exit: a ``return`` or ``break`` inside the loop body. Without
# it the loop is a full traversal, not a first-match selection, and the
# collapse-to-one-key failure mode does not arise.
_FIRST_MATCH_EXIT = re.compile(r'^\s*(?:return\b|break\b)')
# Identity consumption of a derived key — the three shapes that treat a value as
# an identity rather than as data: grouping it into a keyed map
# (``setdefault``), testing the cardinality of the resulting key set (``len``),
# or comparing it for equality. Used only to compute the ``key_consumed`` flag
# that rides on a surfaced candidate; it never gates the candidate.
_IDENTITY_CONSUMPTION = re.compile(
    r'\.setdefault\s*\(|\blen\s*\(|==|!='
)

# Worked-example-vs-clause detection.
# A clause section states a normative rule and then demonstrates it with a
# BAD/GOOD worked-example pair. The candidate class compares the predicate the
# clause REQUIRES against the predicate its GOOD example actually BRANCHES ON,
# and fires only when the two disagree. See
# ``SKILL.md`` § Detection Rules rule 19 for the firing condition and the
# decided disposition of each relational case.

# A fenced-block delimiter line. Group 1 captures the info string (language tag)
# on an opening fence; a closing fence carries none. Fence state also suppresses
# heading detection, so a ``# GOOD`` comment inside a shell fence is never
# mistaken for a markdown H1.
_FENCE_DELIMITER = re.compile(r'^\s*```(\w*)\s*$')

# The GOOD / BAD marker comments labelling the two halves of a worked example.
# The ``//`` (pseudocode / C-style), ``#`` (shell / Python), and ``<!--``
# (markdown) comment leaders are recognized, with optional non-alphanumeric
# decoration between the leader and the marker word so a decorated form
# (``// ✅ GOOD``, ``# --- BAD``) still resolves. The marker word is
# UPPERCASE-only, so ordinary prose carrying "good" never matches. Group
# ``claim`` captures the marker comment's own claim text after the
# em-dash / en-dash / hyphen / colon separator.
_MARKER_LEAD = r'^\s*(?://|#|<!--)\s*[^\w\s]*\s*'
_MARKER_TAIL = r'\b\s*[—–:-]?\s*(?P<claim>.*)$'
_GOOD_MARKER = re.compile(_MARKER_LEAD + 'GOOD' + _MARKER_TAIL)
_BAD_MARKER = re.compile(_MARKER_LEAD + 'BAD' + _MARKER_TAIL)

# A branch keyword opening a tested expression inside a worked example. The
# expression body is extracted by a balanced-paren scan rather than by a regex
# over the body, because a predicate carrying its own call parentheses
# (``if (unmapped.notEmpty())``) defeats any non-greedy paren regex.
_BRANCH_KEYWORD = re.compile(r'(?<![A-Za-z0-9_])(?:el)?(?:if|while)(?![A-Za-z0-9_])')

# A line comment inside a worked-example block, stripped before branch scanning
# so prose in a trailing ``// ...`` annotation never reads as a branch.
_BLOCK_LINE_COMMENT = re.compile(r'//.*$')

# The two normative directive shapes a clause uses to name the predicate its
# worked example must branch on. ``_BRANCH_ON_DIRECTIVE`` matches the explicit
# "branch on X" form; ``_READ_CHECK_DIRECTIVE`` matches an imperative or
# ``MUST``-prefixed "Read X" / "check X". Group ``object`` captures the
# directive's object phrase, stopped at the first clause-ending punctuation so a
# following independent clause never leaks into the required predicate.
#
# Neither pattern admits the ``-ing`` participle ("Branching on ``x`` instead
# would reinstate the defect"): that form appears in post-hoc commentary NAMING
# the rejected predicate, so admitting it would read the forbidden field as the
# required one.
_BRANCH_ON_DIRECTIVE = re.compile(r'(?i)\bbranch(?:es|ed)?\s+on\b(?P<object>[^.;:,]*)')
_READ_CHECK_DIRECTIVE = re.compile(
    r'(?:^|[.;]\s+|\bMUST\s+|\bmust\s+)(?:Read|read|Check|check)\b(?P<object>[^.;:,]*)',
    re.MULTILINE,
)

# The contrast pivot inside a clause heading. Everything BEFORE it states what
# the clause REQUIRES; everything after states what it forbids. Only the
# required half seeds the required predicate, and only when the directive's own
# object is anaphoric ("branch on that").
_HEADING_CONTRAST_PIVOT = re.compile(r'(?i),\s*(?:never|not|rather than|instead of)\b')

# A bare identifier run inside a predicate phrase or expression. Underscores and
# dots are separators, so ``CLAIMABLE_STATUSES`` and ``outcome.status`` each
# decompose into their component words.
_IDENT_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9]*')

# camelCase / PascalCase decomposition of a single identifier run, so
# ``exitCode`` contributes ``exit`` and ``code`` independently.
_CAMEL_SEGMENT = re.compile(r'[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+')

#: Minimum length for a predicate token to participate in the comparison. Short
#: function words carry no discriminating power and would make the prefix match
#: below fire on almost any pair.
_MIN_PREDICATE_TOKEN_LEN = 4

#: Function words and normative auxiliaries that name no predicate. A directive
#: object consisting ONLY of these is anaphoric ("branch on that"), which is the
#: signal to fall back to the clause heading's required half.
_PREDICATE_STOPWORDS: frozenset[str] = frozenset(
    {
        'that',
        'this',
        'these',
        'those',
        'them',
        'they',
        'their',
        'from',
        'with',
        'into',
        'been',
        'were',
        'first',
        'then',
        'only',
        'must',
        'should',
        'shall',
        'never',
        'always',
        'require',
        'requires',
        'required',
        'value',
        'values',
        'own',
        'itself',
    }
)


# =============================================================================
# Candidate-list registry
# =============================================================================


class CandidateList(NamedTuple):
    """One candidate list in the surfacer's emitted vocabulary.

    ``key`` is the payload and ``counts`` key; ``label`` is the human name used
    in derived help prose; ``in_total`` records whether the list's cardinality is
    summed into ``counts.total``.
    """

    key: str
    label: str
    in_total: bool


#: The canonical candidate-list vocabulary — the single code-side source of
#: truth for the surfacer's emitted key set, its ``counts.total`` formula, and
#: the help prose that enumerates it. Adding a list here is what makes it appear
#: in all three, so an emitter addition cannot drift from the derived count.
#:
#: ``in_total`` is False for the four review-anchor lists (``contract_sources``,
#: ``schema_bearing_files``, ``count_prose``, ``advertised_form_help_strings``)
#: and for ``protected_identifiers``, a derived index over ``keep_markers``.
#: The prose rationale is owned by
#: ``plan-marshall:extension-api/standards/ext-point-self-review-surfacing.md``
#: § Output Schema and is NOT restated here.
CANDIDATE_LISTS: tuple[CandidateList, ...] = (
    CandidateList('regexes', 'regexes', True),
    CandidateList('user_facing_strings', 'user-facing strings', True),
    CandidateList('markdown_sections', 'markdown sections', True),
    CandidateList('symmetric_pairs', 'symmetric pairs', True),
    CandidateList('flag_guard_pairs', 'flag-guard pairs', True),
    CandidateList('contract_sources', 'contract sources', False),
    CandidateList('schema_bearing_files', 'schema-bearing files', False),
    CandidateList('keep_markers', 'keep markers', True),
    CandidateList('protected_identifiers', 'protected identifiers', False),
    CandidateList('producer_consumer', 'producer-consumer pairs', True),
    CandidateList('source_of_truth', 'source-of-truth duplicates', True),
    CandidateList(
        'same_document_consistency', 'same-document normative directives', True
    ),
    CandidateList('description_vs_body', 'description-vs-body frontmatter', True),
    CandidateList('unguarded_boundaries', 'lone-unguarded-boundary calls', True),
    CandidateList('count_prose', 'stale count-prose', False),
    CandidateList('touched_claims', 'near-identical-hunk touched claims', True),
    CandidateList(
        'advertised_form_help_strings', 'advertised-form help strings', False
    ),
    CandidateList('ordinal_references', 'same-document ordinal references', True),
    CandidateList('scan_derived_keys', 'scan-derived keys', True),
    CandidateList('worked_example_pairs', 'worked-example clause pairs', True),
)


def candidate_list_prose() -> str:
    """Return the registry's labels as a comma-separated enumeration for help prose."""
    return ', '.join(spec.label for spec in CANDIDATE_LISTS)
