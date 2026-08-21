#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Canonical-block enum-drift analyzer for the ``canonical-enum-choices-drift`` rule.

This module detects drift between a documented ``{a|b|c}`` enum in a skill's
``## Canonical invocations`` block (the hand-maintained mirror) and the live
argparse ``choices=`` of the flag that enum describes (the machine-derivable
source of truth).

Why the canonical block is an oracle, not commentary
----------------------------------------------------
A ``## Canonical invocations`` block is read as SOURCE OF TRUTH by the
``manage-invocation-invalid`` analyzer and by every consuming skill that xrefs
it by name. A block that documents ``--category {bug|improvement}`` while the
script's ``choices=`` accepts four values is therefore an INCORRECT ORACLE: a
reader who meets the two omitted values and follows the documented contract
would classify them as invented under this project's *"never invent script
subcommands/flags"* rule, and would be wrong. The divergence is usually not
authored — it is left behind when a ``choices=`` set widens and the block that
listed the old members is not re-checked.

Declared-versus-derived — the distinction that makes this correct
-----------------------------------------------------------------
The authority side reads the flag's argparse ``choices=`` and NOTHING else. A
script may ALSO hand-list the same values in an argparse ``description=`` string
or a prose sentence; those are mirrors that can drift and are never consulted
here. ``choices=`` is the derived truth whether it is written as a literal
tuple, a bare constant name (``choices=FINDING_TYPES``), or a wrapper
(``choices=list(VALID_CATEGORIES)``) — this module resolves the constant to its
value set rather than reading whatever prose restates it. A guard that could not
tell the two apart would manufacture false positives on every correctly-written
script; reading ``choices=`` only is what settles it.

Fail-closed on uncertainty (normative)
--------------------------------------
Every path that cannot reach a confident authority resolves to SKIP — no
finding — never to a guessed comparison. There are SEVEN such paths, one per
member of :data:`UNRESOLVED_CAUSES`, and each is counted by
:func:`derive_coverage`. They are listed in full under § *Declared coverage*
below; the four that most often need stating up front are:

- the owning script file is missing or unparseable
  (``notation_unresolved`` / ``script_unparseable``);
- the documented flag is never declared with ``choices=`` on a parser this walk
  fully modelled — ``no_choices_declared``. Its two live members are
  ``untrusted-ingestion validate --schema`` and ``manage-config finalize-steps
  set-lane --lane``; re-derive them rather than copying this pair forward. ⛔ Do
  NOT reach for ``--promoted {true|false}`` as the example: it reads as one, and
  it is filed under ``authority_incomplete``. It was named here for a round
  after the census moved it, which is the failure the ⛔ below was written to
  stop;
- the same ``(subcommand_path, flag)`` is declared TWICE with conflicting sets
  (ambiguous — there is no single authority to compare against), which includes
  a script mixing the declarative dict-spec and an explicit ``add_argument``
  with different sets. Note the scope: two SUBCOMMANDS declaring different sets
  for the same flag name is not this case and is not skipped. The authority is
  keyed by path, so ``add --kind`` and ``remove --kind`` resolve independently
  and are each compared. This entry read "more than one distinct set across the
  script" until round 6, which was true before the authority was path-scoped and
  false after;
- a ``choices=`` constant cannot be resolved to a concrete string set
  (cross-module reference whose defining module is absent or ambiguous) — these
  last two are both ``choices_unresolvable``.

⛔ The three NOT listed here are the largest ones:
``parser_surface_not_derived`` (43 sites), ``authority_incomplete`` (18) and
``single_member_ambiguous`` (1) — 62 of the 71 unresolved sites. This list said
"Every path … :" over four bullets for several rounds, which told a reader of the
normative section that the skip set was four items when most skips were not in
it. Do not shorten it back: an incomplete list under an exhaustive lead-in is
the same defect this analyzer reports.

A skip can never produce a false positive. The only cost is a false negative on
an unresolvable site, which the asymmetric-error rule accepts: over-rejecting a
valid, correctly-documented call is the failure this project keeps hitting, and
this guard refuses it by construction.

Two shapes are commonly mistaken for entries in this list and are not:

* ``--type TYPE`` — a bare metavar with no braces and no pipe matches neither
  enum pattern, so it never enters the population and reaches no skip;
* the braced template slot ``{phase}`` in ``--scope {phase}.{role}|plan|...`` —
  this one IS collected and IS in the population, under
  ``single_member_ambiguous`` below. It was filtered at collection for one
  round; that was a silent narrowing and this sentence went on describing it
  for a round after it stopped.

Positive-population assertion
-----------------------------
:func:`derive_population` returns every documented enum site the sweep examined,
each tagged with whether its authority resolved and whether it diverged. The
size of that population — and that it contains a known-good member — is asserted
by the test suite, because a guard whose glob matches zero files is
indistinguishable from a guard whose every match passed unless the population is
shown to be non-empty. A count of blocks examined is a VOLUME; the divergent
count is the coverage number, and the two are reported separately.

Pattern alignment
-----------------
Mirrors ``_analyze_provides_method_table.py`` / ``_analyze_literal_count.py``:
pure static analysis (AST + regex + pathlib), stdlib-only, no subprocess, no
import of any target script, no mutation. The authority is derived statically
because ``.plan/execute-script.py`` (the live ``--help`` surface the
argument-naming cluster probes) is git-ignored and absent from a fresh clone,
while this guard must run identically in a fresh clone, in CI, and locally.

Findings have the shape::

    {
        'type': 'canonical-enum-choices-drift',
        'rule_id': 'canonical-enum-choices-drift',
        'rule': 'analyze_canonical_enum_drift',
        'file': '<absolute SKILL.md path>',
        'line': <int, 1-based line of the documented enum>,
        'severity': 'error',
        'fixable': False,
        'description': '<human-readable drift description>',
        'details': {
            'notation': '<bundle:skill:script>',
            'flag': '--flag',
            'documented': [...],   # the enum members in the canonical block
            'choices': [...],      # the live argparse choices=
            'missing_from_doc': [...],
            'not_in_choices': [...],
            'population_size': <int>,  # enum sites examined in this sweep
            'unresolved_notation_fraction': <float>,  # share NOT compared
            'unresolved_notation_blind_spots': <int>,  # of those, real gaps
            'unresolved_notation_causes': {<cause>: <int>},
        },
    }

Declared coverage — what a clean sweep does NOT check
-----------------------------------------------------
A finding count answers "how many documented enums are wrong". It does not
answer "how many were CHECKED", and here the two are far apart: a documented
enum is compared only when the flag's live ``choices=`` resolves to a concrete
set, and roughly HALF the population resolves to nothing. Those sites are
examined-but-skipped — neither a pass nor a failure — so a clean result means
*"every enum I could resolve matches"*, never *"every documented enum matches"*.

The gap is DECLARED rather than silent: every finding publishes
``unresolved_notation_fraction`` and ``unresolved_notation_causes``, and
:func:`derive_coverage` over :func:`derive_population` is the same figure on a
clean run (the only state a passing gate is ever in).

The fail-closed conditions that leave a site unresolved, each a deliberate
refusal to invent an authority:

* ``notation_unresolved`` — the documented notation resolves to no script path
  in this tree (an unregistered or renamed notation).
* ``script_unparseable`` — the script was found but its AST could not be read.
* ``parser_surface_not_derived`` — the script parsed, but the documented
  subcommand's parser was never MODELLED here. A real blind spot, and the
  LARGEST one. The reasons vary and are worth not collapsing:

  - a parser built by an IMPORTED helper (``script-shared``'s build-CLI factory
    and the declarative front-ends around it), so the file the notation names
    carries no ``ArgumentParser()`` at all;
  - a subparser registered from a LOOP variable
    (``for t in KINDS: sub.add_parser(t)``), whose verb name is not a literal,
    so the path exists at runtime and not in this walk.

  Both are live in this tree. A parser merely PASSED INTO a helper is NOT one of
  them, and was wrongly listed here once: the caller's own ``add_parser`` models
  the PATH, so the surface IS derived and only the authority is missing. Such a
  site lands in ``authority_incomplete``, which holds 18 sites across seven
  notations — ``manage-execution-manifest`` (9), ``manage-tasks`` (2),
  ``phase_handshake`` (3), and one each on ``manage-findings``,
  ``manage-references``, ``manage-status`` and ``collect-fragments``. The
  ``phase_handshake --phase`` sites are the worked example (an imported
  ``add_phase_arg(parser)`` declares their ``choices=``), not the whole set: this
  sentence named them as the only three instances for one round, having been
  written from the three sites that MOTIVATED the fix rather than from the census
  the fix produced.

  What the cause asserts is only that the surface was not modelled. Do not
  restate it as "the choices are in another module": that is true of some of
  these sites, false of others, and unknowable for the ones whose flag declares
  no ``choices=`` anywhere.
* ``authority_incomplete`` — this walk could not read the whole of the module's
  ``choices=`` authority for the site, so it declines to call the authority
  absent. Two shapes reach it:

  - a ``choices=`` declared on a receiver that cannot be attributed to a parser
    path, because an enclosing function parameter of the same name shadows it;
  - a parser handed to a call in ARGUMENT position — typically an imported
    helper that declares the flag. There is no exclusion list: argparse's own
    calls take the parser as the RECEIVER and so never reach this test, which is
    a structural property rather than a set of names to maintain. The path it
    marks incomplete is that parser's, so only sites on that path are affected.

  Declining to attribute an authority is NOT establishing its absence, so no
  site in this bucket can support the reading below. A blind spot.
* ``no_choices_declared`` — the subcommand's parser WAS modelled, the module's
  authority is complete, and it declares no ``choices=`` for this flag. This rule's authority is ``choices=`` and nothing
  else (see the declared-vs-derived note above), so here the authority is
  established as ABSENT rather than merely unestablished, and there is nothing
  for the rule to compare the documented enum against.

  ⛔ That is a statement about this rule's authority, NOT about the flag. The
  bucket holds 2 sites, and BOTH are constrained somewhere this rule does not
  read: ``untrusted-ingestion validate --schema`` by a lookup that rejects an
  unknown key, and ``manage-config finalize-steps set-lane --lane`` by a handler
  that validates and names the route for a rejected value (its ``add_argument``
  says so outright — the omission of ``choices=`` there is deliberate). Their
  documented enums are real claims, simply enforced elsewhere by design. Do not
  describe this bucket as "free-form values" or as "no enum claim to contradict"
  — both were written here once and both are false of it.

  ⛔ Re-derive these examples whenever the census changes. This list named
  ``manage-tasks update --status`` and ``manage-execution-manifest record-step
  --phase`` for one round AFTER the commit that moved both of them into
  ``authority_incomplete`` — worked examples pointing at sites the same change
  had just relocated.

  It is kept apart from ``parser_surface_not_derived`` because the two differ in
  KIND: authority established-absent versus authority not established. Reading
  the second as the first turns the largest gap into reassurance, which is the
  failure this whole rule exists to catch, committed by the rule's own figure.
* ``single_member_ambiguous`` — the documented group parses to ONE member, which
  the notation cannot distinguish between a template slot (``--scope
  {phase}.{role}|plan|...`` yields ``{phase}``) and a truncated enum (``{bug}``
  against a live ``choices=['bug','improvement']`` — this rule's own headline
  drift shape). Not compared, and COUNTED as a blind spot because it may be a
  real claim. One live site, the template slot above.

  This was a silent drop at collection for one round, defended by a comment
  saying a one-member group "carries no drift signal anyway". The truncated-enum
  case refutes that, and a sweep that examines a token, declines to judge it, and
  publishes no figure for it is the exact failure this census exists to prevent.
* ``choices_unresolvable`` — the parser was modelled and declares a ``choices=``
  this resolver cannot reduce to a concrete member set. A blind spot: a real enum
  claim went unverified. ⛔ An imported constant is NOT the case: the resolver
  follows ``_import_sources`` into the defining module, including a re-export
  hop (see :class:`_Resolver`), and that hop is what resolves
  ``manage-lessons add --category`` from ``constants.LESSON_CATEGORIES``. This
  bullet claimed the opposite — "an import hop, deliberately out of scope … and
  stops there" — while ``rule-provenance.md`` claimed the reverse, so the two
  shipped documents contradicted each other and execution refuted this one.
  The live causes, re-derived over the seven members, are: a list of ``Name``
  elements (``choices=[KIND_BUILD, KIND_CHANGE, KIND_JOB]``), a set-union
  ``BinOp`` (``A | B``), and a function CALL (``_registry_bot_kinds()``) — a
  value that does not exist until run time. A conflicting re-declaration of the
  same ``(path, flag)`` also lands here, by design.

The actionable number is published rather than left to a reader who would have
to know which causes count: on a finding as
``details.unresolved_notation_blind_spots``, and on :func:`derive_coverage` as
``blind_spots``. Both are the sum over :data:`UNRESOLVED_BLIND_SPOT_CAUSES`.

Public API
----------
- ``analyze_canonical_enum_drift(marketplace_root, cache=None)``: entry point.
- ``derive_population(marketplace_root, cache=None)``: every examined enum site
  (the positive-population surface).
- ``derive_coverage(population)``: the resolved / unresolved split of that
  population, with a count per fail-closed cause.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

try:  # pragma: no cover - import shape varies by runner vs. direct test load
    from _dep_index import AstCache
except ImportError:  # pragma: no cover
    AstCache = None  # type: ignore[assignment,misc]

RULE_ID = 'canonical-enum-choices-drift'
RULE_NAME = 'analyze_canonical_enum_drift'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)

# The ``## Canonical invocations`` section heading (level-2 exactly).
_CANONICAL_HEADING_RE = re.compile(r'^##\s+Canonical invocations\s*$')

# The executor invocation that opens each canonical form, e.g.
# ``python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add``.
# The 3-part notation locates the owning script; the trailing text yields the
# subcommand path (the positional verbs before the first flag) that scopes the
# choices authority — a flag's choices depend on WHICH subparser declares it.
_NOTATION_RE = re.compile(
    r'\.plan/execute-script\.py\s+'
    r'(?P<notation>[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+)'
    r'(?P<rest>.*)$'
)

# A subcommand verb token in the invocation's positional chain — lowercase
# kebab, never a flag. Collection stops at the first token that is not one.
_VERB_TOKEN_RE = re.compile(r'^[a-z][a-z0-9\-]*$')

# A documented ``--flag {a|b|c}`` enum token. The brace group is argparse's own
# metavar rendering of a choices-constrained option; a bare ``{a,b,c}`` not
# preceded by a flag (or a ``(--a | --b)`` mutually-exclusive group) never
# matches, so only genuine per-flag enum claims are collected.
#
# Neither pattern carries a member minimum. A one-member body is collected like
# any other and is separated in :func:`derive_population`, which files it under
# ``single_member_ambiguous`` rather than comparing it. This comment named
# :func:`_enum_sites_in_skill` for one round after the test moved out of it.
_ENUM_TOKEN_RE = re.compile(
    r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9\-]*)\s+\{(?P<members>[^{}]+)\}'
)

# The BRACE-LESS enum form, ``--flag a|b|c``. At least one pipe is required, so a
# lone metavar (``--flag VALUE``) is not read as a one-member enum. Members carry
# no whitespace, braces or pipes, which also keeps the braced form above out of
# this pattern's reach (its members begin with ``{``).
#
# Members are restricted to identifier characters rather than to "anything but a
# pipe". The usage convention wraps an optional flag in SQUARE BRACKETS —
# ``[--mode local_and_remote|local_only]`` — and a permissive member class
# swallows the closing bracket into the last member, manufacturing a drift
# finding out of punctuation. A brace-less enum whose members fall outside this
# class simply does not match, which is the fail-closed direction.
#
# A member list in which ANY member starts with ``--`` is rejected in code rather
# than in the pattern: that shape is a mutually-exclusive GROUP (``--flag --a|--b``
# or a documented either/or), not an enum over one flag's values, and reading it as
# one would compare a flag's choices against a list of other flags' names.
_BRACELESS_ENUM_TOKEN_RE = re.compile(
    r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9\-]*)'
    r'\s+(?P<members>[A-Za-z0-9_.\-]+(?:\|[A-Za-z0-9_.\-]+)+)'
)

_ENUM_TOKEN_PATTERNS = (_ENUM_TOKEN_RE, _BRACELESS_ENUM_TOKEN_RE)

# Builtins that wrap a single sequence without changing its member set, so a
# ``choices=list(FOO)`` / ``choices=sorted(FOO)`` resolves to ``FOO``'s members.
_SEQUENCE_WRAPPERS = frozenset({'list', 'tuple', 'set', 'frozenset', 'sorted'})

# Recursion bound for constant/alias/import following — a defensive cap against a
# pathological alias cycle, well above any real ``choices=`` reference chain.
_MAX_RESOLVE_DEPTH = 8

# Factories returning an object whose ``add_argument`` declares onto the PARENT
# parser. A flag declared on one of these is, to argparse, declared on the parser
# — so the returned variable inherits the parser's subcommand paths.
_PARSER_GROUP_FACTORIES = frozenset({'add_mutually_exclusive_group', 'add_argument_group'})


# Why a site was examined but not compared. Published per site and aggregated by
# :func:`derive_coverage`, so a clean sweep states the share of its population it
# could not check AND what stopped it.
UNRESOLVED_NOTATION = 'notation_unresolved'
UNRESOLVED_SCRIPT_UNPARSEABLE = 'script_unparseable'
# These are kept APART because they carry different risk. Where the parser was
# modelled, its authority is complete, and no ``choices=`` is declared for the
# flag, the rule's authority is ESTABLISHED and found absent. Every other cause
# leaves it UNESTABLISHED. Merged into one bucket a reader cannot tell whether a
# large unresolved share is mostly established-absent or mostly unread.
#
# ⛔ Established-absent is not harmless: the flag may still be constrained by a
# check in the handler, which this rule does not read by design.
UNRESOLVED_PARSER_NOT_DERIVED = 'parser_surface_not_derived'
UNRESOLVED_AUTHORITY_INCOMPLETE = 'authority_incomplete'
UNRESOLVED_NO_CHOICES_DECLARED = 'no_choices_declared'
UNRESOLVED_CHOICES_UNRESOLVABLE = 'choices_unresolvable'
# A one-member brace group: a template slot or a truncated enum, and the notation
# does not say which. Examined, deliberately not compared, and COUNTED — dropping
# it at collection was a silent narrowing of the very figure this census exists
# to publish.
UNRESOLVED_SINGLE_MEMBER = 'single_member_ambiguous'

# Every cause, in report order. ``derive_coverage`` emits a COMPLETE census over
# this tuple — a cause with no occurrences is reported as ``0`` rather than
# omitted, so an absent cause is never indistinguishable from one folded into a
# neighbour.
UNRESOLVED_CAUSES = (
    UNRESOLVED_NOTATION,
    UNRESOLVED_SCRIPT_UNPARSEABLE,
    UNRESOLVED_PARSER_NOT_DERIVED,
    UNRESOLVED_AUTHORITY_INCOMPLETE,
    UNRESOLVED_NO_CHOICES_DECLARED,
    UNRESOLVED_CHOICES_UNRESOLVABLE,
    UNRESOLVED_SINGLE_MEMBER,
)

# The causes where the rule's authority could not be ESTABLISHED — a documented
# enum the sweep was unable to check against anything. ``no_choices_declared`` is
# deliberately NOT among them: there the authority was established and is absent,
# which is a different state from not knowing.
#
# ⛔ Not among them is not the same as harmless. A flag with no ``choices=`` may
# still be constrained elsewhere in the script, where this rule does not look by
# design — see the cause description in the module docstring. The partition is
# about what the RULE established, not about what the flag accepts, and getting
# it wrong is worse than not publishing it: a coverage figure that mislabels its
# own gap reads as reassurance.
UNRESOLVED_BLIND_SPOT_CAUSES = frozenset(
    {
        UNRESOLVED_NOTATION,
        UNRESOLVED_SCRIPT_UNPARSEABLE,
        UNRESOLVED_PARSER_NOT_DERIVED,
        UNRESOLVED_AUTHORITY_INCOMPLETE,
        UNRESOLVED_CHOICES_UNRESOLVABLE,
        UNRESOLVED_SINGLE_MEMBER,
    }
)


@dataclass(frozen=True)
class EnumSite:
    """One documented ``--flag {a|b|c}`` enum occurrence in a canonical block.

    ``resolved`` is True when the flag's live ``choices=`` was derived to a
    concrete set; ``diverged`` is True only when ``resolved`` and the documented
    member set differs from the live choices. An unresolved site is neither a
    pass nor a failure — it is examined-but-skipped, and is counted in the
    population so a clean sweep can never be confused with an empty one.

    ``unresolved_cause`` names WHICH fail-closed condition skipped the site
    (``None`` when it resolved), so the unexamined share of a clean sweep is
    attributable rather than a single opaque number. The causes are the
    ``UNRESOLVED_*`` constants.
    """

    skill_md: Path
    line: int
    notation: str
    subcommand: tuple[str, ...]
    flag: str
    documented: frozenset[str]
    choices: frozenset[str] | None
    resolved: bool
    diverged: bool
    unresolved_cause: str | None = None


# =============================================================================
# Canonical-block parsing (the mirror side)
# =============================================================================


def _canonical_section_lines(text: str) -> list[tuple[int, str]]:
    """Return the ``(1-based line, raw)`` lines of the ``## Canonical invocations``
    section, bounded by the next level-2 heading. Empty when the section is absent.
    """
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    in_section = False
    for idx, raw in enumerate(lines, start=1):
        if _CANONICAL_HEADING_RE.match(raw):
            in_section = True
            continue
        if in_section and raw.startswith('## ') and not _CANONICAL_HEADING_RE.match(raw):
            break
        if in_section:
            out.append((idx, raw))
    return out


def _extract_subcommand_path(rest: str) -> tuple[str, ...]:
    """Return the positional verb chain from the text after the notation token.

    Collects leading whitespace-separated tokens that are bare verbs
    (``finalize-steps set-lane``), stopping at the first token that is a flag,
    a line-continuation, a placeholder, or anything else — those mark the end of
    the subcommand path and the start of arguments.
    """
    path: list[str] = []
    for token in rest.strip().split():
        if _VERB_TOKEN_RE.match(token):
            path.append(token)
        else:
            break
    return tuple(path)


def _enum_sites_in_skill(
    skill_md: Path,
) -> list[tuple[int, str, tuple[str, ...], str, frozenset[str]]]:
    """Extract ``(line, notation, subcommand_path, flag, members)`` per enum.

    Each documented enum is attributed to the fenced code block it sits in — the
    executor invocation that opened that block gives both the owning-script
    notation and the subcommand path that scopes the flag's choices authority.
    Enum tokens outside any code block, or in a block with no resolvable
    notation, are ignored: without a notation there is no script to compare to.
    """
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    section = _canonical_section_lines(text)
    if not section:
        return []

    sites: list[tuple[int, str, tuple[str, ...], str, frozenset[str]]] = []
    in_fence = False
    block_notation: str | None = None
    block_path: tuple[str, ...] = ()
    for line, raw in section:
        stripped = raw.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            block_notation = None
            block_path = ()
            continue
        if not in_fence:
            continue
        # Every line is searched for a notation, not only the first one that
        # matches: a single fence routinely documents SEVERAL invocations, and
        # latching on the first one scoped every enum below it to that first
        # invocation's subcommand — so a correctly-documented second invocation
        # was compared against the wrong flag's choices. A line carrying no
        # notation (a continuation line, or an enum on its own line) keeps the
        # invocation above it, which is the attribution the reader sees.
        notation_match = _NOTATION_RE.search(raw)
        if notation_match:
            block_notation = notation_match.group('notation')
            block_path = _extract_subcommand_path(notation_match.group('rest'))
        if block_notation is None:
            # An enum ABOVE the block's first invocation line has no invocation
            # to attribute it to, so there is no script to compare it against.
            continue
        for pattern in _ENUM_TOKEN_PATTERNS:
            for match in pattern.finditer(raw):
                members = _split_enum_members(match.group('members'))
                if not members or any(m.startswith('--') for m in members):
                    # The SECOND collection-time drop counted by no cause (the
                    # first is the notation-less enum above). An empty split, or
                    # a body whose members are themselves flags, is a flag list
                    # rather than an enum claim. Zero live sites carry either
                    # shape — but a declined token with no figure is exactly what
                    # this rule reports, so both are disclosed in rule-catalog.md
                    # rather than left implicit here.
                    continue
                sites.append(
                    (line, block_notation, block_path, match.group('flag'), members)
                )
    return sites


def _split_enum_members(raw_members: str) -> frozenset[str]:
    """Split a ``{a|b|c}`` (or comma-separated) metavar body into a member set.

    Pipes are the canonical-block convention; a comma-separated body is accepted
    too. Each member is stripped of whitespace and backticks.

    This function does NOT decide what is an enum claim — it only splits. A
    metavar body yields its own text as one member (``'TYPE'`` → ``{'TYPE'}``),
    not the empty set, and nothing REJECTS it: a one-member result is collected
    and filed under ``single_member_ambiguous`` by :func:`derive_population`.
    Every clause of that has been stated wrongly here at some point — first the
    empty set, then a rejection that had already moved elsewhere.
    """
    body = raw_members.strip()
    parts = body.split('|') if '|' in body else body.split(',')
    members = {p.strip().strip('`').strip() for p in parts}
    members.discard('')
    return frozenset(members)


# =============================================================================
# Argparse authority resolution (the derived side)
# =============================================================================


def _script_path_for_notation(notation: str, marketplace_root: Path) -> Path | None:
    """Resolve ``bundle:skill:script`` to its on-disk ``scripts/{script}.py`` file."""
    try:
        bundle, skill, script = notation.split(':', 2)
    except ValueError:
        return None
    candidate = marketplace_root / bundle / 'skills' / skill / 'scripts' / f'{script}.py'
    return candidate if candidate.is_file() else None


def _module_level_assignments(tree: ast.Module) -> dict[str, ast.expr]:
    """Map each module-level ``NAME = value`` / ``NAME: T = value`` to its value node."""
    assigns: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigns[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                assigns[node.target.id] = node.value
    return assigns


def _import_sources(tree: ast.Module) -> dict[str, str]:
    """Map each name imported via ``from MODULE import NAME`` to ``MODULE``.

    Only bare (non-relative) module imports are recorded; a dotted module keeps
    its last component, which is enough to locate the shared marketplace module.
    ``import X as Y`` (plain import) is not a name-binding this resolver follows.
    """
    sources: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if node.level:  # relative import — not resolvable by bare module search
            continue
        module = node.module.split('.')[-1]
        for alias in node.names:
            bound = alias.asname or alias.name
            # Only follow a straight re-export (``import NAME``); an aliased
            # import (``import NAME as OTHER``) is not followed to keep the
            # symbol identity unambiguous.
            if alias.asname is None:
                sources[bound] = module
    return sources


def _locate_module_files(module: str, marketplace_root: Path) -> list[Path]:
    """Find on-disk ``{module}.py`` files under any bundle's ``scripts/`` tree."""
    files: list[Path] = []
    for pattern in (
        f'*/skills/*/scripts/{module}.py',
        f'*/skills/*/scripts/*/{module}.py',
    ):
        files.extend(sorted(marketplace_root.glob(pattern)))
    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[Path] = []
    for path in files:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


class _Resolver:
    """Static resolver for a ``choices=`` expression to its concrete string set.

    Holds the ``AstCache``-backed parse memo and the marketplace root so a
    ``choices=CONST`` reference can be followed into the module that defines the
    constant — including a re-export hop (``manage-findings`` imports
    ``FINDING_TYPES`` from ``_findings_core``, which imports it from
    ``constants``). Every unresolved path returns ``None`` (fail-closed).
    """

    def __init__(self, marketplace_root: Path, get_tree) -> None:
        self._root = marketplace_root
        self._get_tree = get_tree

    def resolve_expr(
        self, node: ast.expr, tree: ast.Module, depth: int
    ) -> frozenset[str] | None:
        if depth > _MAX_RESOLVE_DEPTH:
            return None
        literal = _string_sequence(node)
        if literal is not None:
            return literal
        inner = _unwrap_sequence_call(node)
        if inner is not None:
            return self.resolve_expr(inner, tree, depth + 1)
        if isinstance(node, ast.Name):
            return self.resolve_name(node.id, tree, depth + 1)
        return None

    def resolve_name(
        self, name: str, tree: ast.Module, depth: int
    ) -> frozenset[str] | None:
        if depth > _MAX_RESOLVE_DEPTH:
            return None
        assigns = _module_level_assignments(tree)
        if name in assigns:
            return self.resolve_expr(assigns[name], tree, depth + 1)
        module = _import_sources(tree).get(name)
        if module is None:
            return None
        resolved: set[frozenset[str]] = set()
        for module_path in _locate_module_files(module, self._root):
            module_tree = self._get_tree(module_path)
            if module_tree is None:
                continue
            value = self.resolve_name(name, module_tree, depth + 1)
            if value is not None:
                resolved.add(value)
        # A unique resolution across candidate modules is authoritative; an
        # ambiguous one (two modules define the name differently) fails closed.
        return next(iter(resolved)) if len(resolved) == 1 else None


def _string_sequence(node: ast.expr) -> frozenset[str] | None:
    """Return the member set of a literal list/tuple/set of string constants."""
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return None
    members: set[str] = set()
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            members.add(elt.value)
        else:
            # A non-string-literal element (a splat, a call, a nested name) makes
            # the literal set indeterminate — fail closed rather than under-count.
            return None
    return frozenset(members)


def _unwrap_sequence_call(node: ast.expr) -> ast.expr | None:
    """Return the sole argument of a ``list()/tuple()/set()/frozenset()/sorted()`` call."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return None
    if node.func.id not in _SEQUENCE_WRAPPERS:
        return None
    if len(node.args) != 1 or node.keywords:
        return None
    return node.args[0]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _receiver_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id
    return None


def _string_list_kw(node: ast.Call, name: str) -> list[str]:
    """Return the string constants of a ``name=[...]`` / ``name=(...)`` keyword."""
    value = _keyword_value(node, name)
    if not isinstance(value, (ast.List, ast.Tuple)):
        return []
    return [e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def _build_parser_path_sets(tree: ast.Module) -> dict[str, set[tuple[str, ...]]]:
    """Map each parser variable to the set of subcommand paths that reach it.

    A ``ArgumentParser()`` variable maps to ``{()}`` (the root, no subcommand).
    ``sub = parser.add_subparsers()`` records ``sub``'s owning parser;
    ``p = sub.add_parser('verb', aliases=['v'])`` gives ``p`` the owner's paths
    each extended by ``verb`` AND every alias, so a canonical block documenting
    either spelling resolves. Nesting composes: a parser reached by
    ``finalize-steps`` then ``set-lane`` maps to ``{('finalize-steps','set-lane')}``.
    Assignments are processed in source order so an owner is known before its
    children are registered.
    """
    parser_paths: dict[str, set[tuple[str, ...]]] = {}
    subparsers_owner: dict[str, str] = {}
    scope_params = _enclosing_params(tree)

    assigns: list[ast.Assign] = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
    assigns.sort(key=lambda a: (a.lineno, a.col_offset))
    for stmt in assigns:
        if not isinstance(stmt.value, ast.Call):
            continue
        call = stmt.value
        name = _call_name(call)
        targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        if not targets:
            continue
        if name == 'ArgumentParser':
            for var in targets:
                parser_paths.setdefault(var, set()).add(())
        elif name == 'add_subparsers':
            owner = _receiver_name(call)
            if owner is not None and owner in parser_paths:
                for var in targets:
                    subparsers_owner[var] = owner
        elif name == 'add_parser':
            subs_var = _receiver_name(call)
            if subs_var is None or subs_var not in subparsers_owner:
                continue
            owner = subparsers_owner[subs_var]
            owner_paths = parser_paths.get(owner, set())
            verb = _first_string_arg(call)
            if verb is None:
                continue
            spellings = [verb, *_string_list_kw(call, 'aliases')]
            new_paths = {
                owner_path + (spelling,)
                for owner_path in owner_paths
                for spelling in spellings
            }
            for var in targets:
                parser_paths.setdefault(var, set()).update(new_paths)
        elif name in _PARSER_GROUP_FACTORIES:
            # ``g = p.add_mutually_exclusive_group()`` / ``add_argument_group()``
            # returns a GROUP that adds arguments to ``p``. Argparse treats a
            # flag declared on the group as declared on the parser, so the group
            # variable must inherit the parser's paths — otherwise every
            # ``g.add_argument(..., choices=...)`` has a receiver this walk does
            # not recognise, and the flag's authority is silently never read.
            # That is not a missing authority: it is one walked past, which the
            # coverage census would then report as "the parser declares no
            # choices for this flag".
            #
            # The inheritance is SCOPE-GATED. Where the owner name is shadowed by
            # an enclosing function's parameter, its module-level paths are not
            # this owner's (see :func:`_shadowed_receivers`), so passing them on
            # would launder a shadowed receiver into a confident path — the one
            # outcome the shadowing guard promises is impossible, reached through
            # the group rather than directly. Fail closed: the group inherits
            # nothing, and :func:`_shadowed_receivers` reports its name shadowed
            # too, so the module's authority reads INCOMPLETE.
            owner = _receiver_name(call)
            if owner is not None and owner in parser_paths and owner not in scope_params[id(stmt)]:
                for var in targets:
                    parser_paths.setdefault(var, set()).update(parser_paths[owner])
    return parser_paths


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None


def _authority_by_subcommand_flag(
    tree: ast.Module, resolver: _Resolver
) -> dict[tuple[tuple[str, ...], str], frozenset[str] | None]:
    """Map ``(subcommand_path, flag)`` to the resolved ``choices=`` set.

    The key is the subcommand path of the parser the flag is declared on, so a
    flag which declares ``choices=`` on one subcommand's parser and not
    another's — is never conflated (the ``manage-tasks`` ``--status`` case:
    ``list`` declares them, ``update`` does not and validates in its handler
    instead, so this rule has no authority to compare against there). A value of ``None`` means the ``choices=`` could not be resolved to a
    concrete set (fail-closed); an entry is ABSENT in four distinct states, which this
    map cannot tell apart: the script was unparseable, the parser surface was
    never modelled, the module's authority could not be fully read, or the flag
    genuinely declares no ``choices=``. The caller separates them — that
    separation is the whole point of the cause census — and treats NONE of them
    as "no enum claim to check", the reading this sentence carried and which is
    the exact defect the census was built to remove. A conflicting re-declaration of the same ``(path, flag)`` resolves to
    ``None``.
    """
    parser_paths = _build_parser_path_sets(tree)
    # The declarative dict-spec form is resolved FIRST, so a later
    # ``add_argument(..., choices=...)`` for the same (path, flag) meets an
    # occupied key. It does NOT win: an AGREEING re-declaration is a no-op, and a
    # DIFFERING one takes the conflict branch below and resolves the key to
    # ``None`` — ``choices_unresolvable``, the fail-closed reading, since a
    # script that mixes the two forms with different sets gives this walk no
    # single authority. "Is the one that wins" stood here for several rounds and
    # is false in the only case where it is testable.
    resolved: dict[tuple[tuple[str, ...], str], frozenset[str] | None] = dict(
        _declarative_authority(tree, resolver)
    )
    shadowed = _shadowed_receivers(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_add_argument(node):
            continue
        receiver = _receiver_name(node)
        if receiver is None or receiver not in parser_paths:
            continue
        # Fail closed on a receiver bound by an enclosing function's parameter —
        # the module-level name of the same spelling is a different parser.
        if receiver in shadowed.get(id(node), ()):
            continue
        flag = _long_flag_name(node)
        if flag is None:
            continue
        choices_node = _keyword_value(node, 'choices')
        if choices_node is None:
            continue
        members = resolver.resolve_expr(choices_node, tree, 0)
        for path in parser_paths[receiver]:
            key = (path, flag)
            if key in resolved and resolved[key] != members:
                resolved[key] = None
            else:
                resolved[key] = members
    return resolved


def _dict_key(node: ast.Dict, key: str) -> ast.expr | None:
    """Return the value node for a literal string ``key`` in a dict display."""
    for key_node, value_node in zip(node.keys, node.values, strict=False):
        if isinstance(key_node, ast.Constant) and key_node.value == key:
            return value_node
    return None


def _dict_spec_string(node: ast.Dict, key: str) -> str | None:
    value = _dict_key(node, key)
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _declarative_authority(
    tree: ast.Module, resolver: _Resolver
) -> dict[tuple[tuple[str, ...], str], frozenset[str] | None]:
    """Resolve ``choices`` declared in the DECLARATIVE dict-spec parser form.

    Several scripts build their parser from a data structure rather than from
    ``add_parser`` / ``add_argument`` calls::

        subcommands=[
            {'name': 'append', 'args': [
                {'flags': ['--kind'], 'choices': [KIND_BUILD, KIND_CHANGE]},
            ]},
        ]

    The AST walk that reads ``add_argument(..., choices=...)`` cannot see any of
    it — there is no call to walk — so every documented enum on such a script
    resolved to "no authority" and was silently never compared. That is the same
    unread-population failure this rule exists to catch, inside the rule.

    The spec is a SAME-FILE parse: the dicts are literals in the module under
    analysis, so no import hop is involved and the members go through the same
    ``_Resolver`` the call form uses. Nesting composes through a ``subcommands``
    key, so a nested verb path resolves exactly as ``add_parser`` nesting does.
    """
    resolved: dict[tuple[tuple[str, ...], str], frozenset[str] | None] = {}
    for here, spec in _walk_declarative_specs(tree):
        args = _dict_key(spec, 'args')
        if not isinstance(args, (ast.List, ast.Tuple)):
            continue
        for arg in args.elts:
            if not isinstance(arg, ast.Dict):
                continue
            choices_node = _dict_key(arg, 'choices')
            if choices_node is None:
                continue
            flags_node = _dict_key(arg, 'flags')
            if not isinstance(flags_node, (ast.List, ast.Tuple)):
                continue
            members = resolver.resolve_expr(choices_node, tree, 0)
            for flag_node in flags_node.elts:
                if not isinstance(flag_node, ast.Constant) or not isinstance(flag_node.value, str):
                    continue
                if not flag_node.value.startswith('--'):
                    continue
                key = (here, flag_node.value[2:])
                if key in resolved and resolved[key] != members:
                    resolved[key] = None
                else:
                    resolved[key] = members
    return resolved


def _walk_declarative_specs(tree: ast.Module) -> list[tuple[tuple[str, ...], ast.Dict]]:
    """Every ``(subcommand_path, spec_dict)`` in the declarative parser form.

    Split out from :func:`_declarative_authority` because the two questions it
    serves are different and must not be conflated: which paths the spec MODELS,
    and which of them declare ``choices``. Deriving the first from the second —
    which is what reading the authority map's keys does — silently drops every
    subcommand whose args are all free-form, and those then look like parsers
    that were never seen at all. That is the blind-spot mis-attribution this
    module's coverage census exists to avoid, and it shipped once: a dict-spec
    verb declaring nothing but ``help`` was counted as a parser nobody had
    modelled, in the very census written to stop that conflation.
    """
    found: list[tuple[tuple[str, ...], ast.Dict]] = []

    def visit(spec: ast.Dict, path: tuple[str, ...]) -> None:
        name = _dict_spec_string(spec, 'name')
        if not name:
            # A spec whose ``name`` is absent or is not a literal string models a
            # verb this walk cannot name. Appending ``path`` here would inject the
            # PARENT path — for a top-level entry, the root ``()`` — and a root
            # path in the modelled set makes a site whose parser was never
            # reached read as ``no_choices_declared``: the mis-attribution this
            # whole census exists to prevent, arriving through the back door.
            # Recurse for nested entries, but contribute no path of our own.
            nested_only = _dict_key(spec, 'subcommands')
            if isinstance(nested_only, (ast.List, ast.Tuple)):
                for child in nested_only.elts:
                    if isinstance(child, ast.Dict):
                        visit(child, path)
            return
        here = path + (name,)
        found.append((here, spec))
        nested = _dict_key(spec, 'subcommands')
        if isinstance(nested, (ast.List, ast.Tuple)):
            for child in nested.elts:
                if isinstance(child, ast.Dict):
                    visit(child, here)

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == 'subcommands':
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for child in node.value.elts:
                    if isinstance(child, ast.Dict):
                        visit(child, ())
    return found


def _derived_subcommand_paths(tree: ast.Module) -> set[tuple[str, ...]]:
    """Every subcommand path this module's parser surface was actually MODELLED at.

    The discriminator between "this flag declares no ``choices=``" and "this
    module's parser was never modelled". Both leave the authority key absent, and
    conflating them is the worse direction: a script whose parser is built by an
    IMPORTED helper yields no ``ArgumentParser()`` assignment here, so every one
    of its documented enums looks like a flag the rule established nothing to
    check against, when in fact the rule never reached the parser at all.
    """
    paths: set[tuple[str, ...]] = set()
    for path_set in _build_parser_path_sets(tree).values():
        paths |= path_set
    paths |= {path for path, _spec in _walk_declarative_specs(tree)}
    return paths


def _paths_with_incomplete_authority(tree: ast.Module) -> set[tuple[str, ...]]:
    """Subcommand paths whose parser was handed to a call this walk cannot model.

    A parser variable passed as an ARGUMENT — ``add_phase_arg(capture)``,
    ``_add_init_args(p_init)`` — may have flags (and ``choices=``) declared on it
    by the callee. The callee is frequently in another module, and following the
    hop is deliberately out of scope, so the authority for that path is
    INCOMPLETE: an absent key is not evidence that no ``choices=`` was declared.

    This is the general form of a defect found three rounds running by auditing
    only the notation's own FILE — a scope that structurally cannot see an
    imported helper. ``plan-marshall:plan-marshall:phase_handshake`` is the live
    subject: three ``--phase`` sites were reported as "the parser declares no
    choices", while ``input_validation.add_phase_arg`` declares
    ``choices=PHASES`` matching the documented set exactly.

    Argparse's own construction surface needs no exclusion, and carried a
    useless one once. ``parser.add_argument(...)``, ``sub.add_parser('v')`` and
    ``parser.parse_args()`` all take the parser as the RECEIVER, and only
    ARGUMENTS are inspected here — so no argparse call ever reaches this scan
    with a parser in an argument position. A name-based skip for them was
    therefore inert: deleting it left the whole-tree census byte-identical, and
    the test written to pin it passed with the guard gone, because no fixture
    could contain a call the skip would suppress. Removed rather than kept as
    reassurance.

    The one argparse shape that DOES pass a parser by argument is
    ``parents=[base]``, where the parser sits inside a list rather than at
    argument position, so it does not reach here either. That is a separate,
    unclosed gap: a child parser built with ``parents=`` inherits the parent's
    actions, and this walk attributes the parent's ``choices=`` to the PARENT's
    paths only. No live site uses it, and the census does not currently name it.
    """
    parser_paths = _build_parser_path_sets(tree)
    incomplete: set[tuple[str, ...]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for arg in (*node.args, *(kw.value for kw in node.keywords)):
            if isinstance(arg, ast.Name) and arg.id in parser_paths:
                incomplete |= parser_paths[arg.id]
    return incomplete


def _has_unattributed_choices(tree: ast.Module) -> bool:
    """True when this module declares ``choices=`` the path walk could not attribute.

    A ``choices=`` on a receiver shadowed by an enclosing function's parameter is
    skipped fail-closed (see :func:`_shadowed_receivers`), which leaves its key
    absent from the authority map — indistinguishable, on key presence alone,
    from a flag that declares no choices. Declining to attribute an authority is
    NOT establishing its absence, so a module in this state cannot support the
    ``no_choices_declared`` reading for any of its sites.
    """
    shadowed = _shadowed_receivers(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_add_argument(node):
            continue
        if _keyword_value(node, 'choices') is None:
            continue
        receiver = _receiver_name(node)
        if receiver is not None and receiver in shadowed.get(id(node), ()):
            return True
    return False


def _shadowed_receivers(tree: ast.Module) -> dict[int, set[str]]:
    """Map each ``add_argument`` call's id to the names SHADOWED where it sits.

    ``_build_parser_path_sets`` walks assignments module-wide and ignores scope,
    so a module-level ``parser = ArgumentParser()`` makes the NAME ``parser``
    resolve to the root path everywhere — including inside
    ``def _add_init_args(parser): parser.add_argument(..., choices=...)``, where
    the name is a PARAMETER bound to whichever subparser the caller passed.

    Attributing that helper's ``choices=`` to the root is wrong twice over: the
    real subcommand's authority is never recorded (so its documented enum reads
    as "declares no choices"), and a root-level flag of the same name would be
    compared against a subcommand's choices — a finding manufactured out of a
    scope confusion, which is the one outcome this rule promises is impossible.

    Resolving which parser the caller passed would need call-graph analysis. This
    fails CLOSED instead: a receiver shadowed by an enclosing function's
    parameter is treated as unresolvable, so the site is reported as an
    unexamined member of the population rather than compared against the wrong
    authority.

    A name bound to a GROUP built off a shadowed owner is reported shadowed too
    (:func:`_group_vars_off_shadowed_owner`). The group is not itself a
    parameter, so the direct test does not reach it, and without that the guard
    is defeated by one indirection — ``grp = parser.add_mutually_exclusive_group()``
    inside ``def _extra(parser)`` — which is a live-capable shape, not a
    hypothetical: both halves of :data:`_PARSER_GROUP_FACTORIES` reach it.
    """
    scope_params = _enclosing_params(tree)
    scope_funcs = _enclosing_functions(tree)
    laundering = _group_vars_off_shadowed_owner(tree, scope_params, scope_funcs)
    return {
        id(node): set(scope_params[id(node)])
        | {group for group, func in laundering if func in scope_funcs[id(node)]}
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_add_argument(node)
    }


def _enclosing_params(tree: ast.Module) -> dict[int, frozenset[str]]:
    """Map every node's id to the function-parameter names in scope AT that node.

    One walk serves both the direct shadowing test and the scope gate on group
    inheritance, so the two cannot drift apart on what "shadowed here" means.

    Every key is present: this walk recurses with ``ast.iter_child_nodes``, which
    reaches exactly the nodes ``ast.walk`` reaches, and every caller keys off a
    node from an ``ast.walk`` of the same tree. A ``dict`` subclass defaulting
    unseen ids to the empty set was written here once; it described a state that
    cannot arise, ``__missing__`` fired zero times over the whole marketplace,
    and deleting it left the suite green. Plain ``dict`` — a missing key is a
    real bug and should raise, not be papered over with a permissive default.
    """
    params_at: dict[int, frozenset[str]] = {}

    def walk(node: ast.AST, names: frozenset[str]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            params = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
            if args.vararg:
                params.add(args.vararg.arg)
            if args.kwarg:
                params.add(args.kwarg.arg)
            names = names | params
        params_at[id(node)] = names
        for child in ast.iter_child_nodes(node):
            walk(child, names)

    walk(tree, frozenset())
    return params_at


def _enclosing_functions(tree: ast.Module) -> dict[int, tuple[int, ...]]:
    """Map every node's id to the ids of the functions ENCLOSING it, outermost first.

    A local binding is visible only inside the function that makes it, so this is
    the scope a laundered group name has. Keying laundering by name alone made it
    module-wide; keying it by ``(name, owner_name)`` narrowed it to "any function
    with a parameter of that name", which is still not the binding's scope —
    a second helper binding the same group name off a shadowed parser discarded a
    correctly-attributed group's authority in an unrelated function.
    """
    chains: dict[int, tuple[int, ...]] = {}

    def walk(node: ast.AST, chain: tuple[int, ...]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chain = chain + (id(node),)
        chains[id(node)] = chain
        for child in ast.iter_child_nodes(node):
            walk(child, chain)

    walk(tree, ())
    return chains


def _group_vars_off_shadowed_owner(
    tree: ast.Module,
    scope_params: dict[int, frozenset[str]],
    scope_funcs: dict[int, tuple[int, ...]],
) -> set[tuple[str, int]]:
    """``(group_name, enclosing_function_id)`` per group built off a SHADOWED owner.

    The FUNCTION is carried, not the owner name, because the binding it describes
    is function-local and that is the only scope in which the name means this
    group. Two narrower keyings shipped before this one and both leaked:

    * bare group NAMES — module-wide. One helper binding ``grp`` marked the name
      shadowed at every ``add_argument`` in the file, discarding the resolved
      authority of a correctly-attributed module-level
      ``grp = p_add.add_argument_group('g')``.
    * ``(group_name, owner_name)`` — narrowed to "any function with a parameter
      of that name", which is not the binding's scope either. With ``grp``
      laundered in ``def _b(parser)``, an unrelated ``def _c(parser)`` calling
      the module-level ``grp.add_argument(..., choices=...)`` had its authority
      discarded, because the pair matched on the NAME ``parser`` rather than on
      the binding.

    Both are the same failure: a guard against false positives manufacturing a
    false negative. Keying on the binding's own function ends the family.

    ``grp = parser.add_mutually_exclusive_group()`` inside
    ``def _extra(parser): ...`` binds ``grp`` to a group of whatever parser the
    caller passed — not of the module-level ``parser``. Without this, ``grp`` is
    an ordinary unshadowed name, so a ``grp.add_argument(..., choices=...)``
    would be attributed to the module-level parser's path: the shadowing guard
    defeated by one indirection. Treating ``grp`` as shadowed keeps the module's
    authority INCOMPLETE, which is the fail-closed reading.
    """
    laundered: set[tuple[str, int]] = set()
    for stmt in ast.walk(tree):
        if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.Call):
            continue
        if _call_name(stmt.value) not in _PARSER_GROUP_FACTORIES:
            continue
        owner = _receiver_name(stmt.value)
        if owner is None or owner not in scope_params[id(stmt)]:
            continue
        enclosing = scope_funcs[id(stmt)]
        if not enclosing:
            # An owner that is a parameter implies an enclosing function, so this
            # is unreachable; a module-level binding cannot be laundered.
            continue
        laundered.update(
            (t.id, enclosing[-1]) for t in stmt.targets if isinstance(t, ast.Name)
        )
    return laundered


def _is_add_argument(node: ast.Call) -> bool:
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == 'add_argument'


def _long_flag_name(node: ast.Call) -> str | None:
    """Return the ``--long`` flag name (without dashes) of an ``add_argument`` call."""
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if arg.value.startswith('--'):
                return arg.value[2:]
    return None


def _keyword_value(node: ast.Call, name: str) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


# =============================================================================
# Population derivation + finding emission
# =============================================================================


def _skill_md_files(marketplace_root: Path) -> list[Path]:
    try:
        return sorted(marketplace_root.glob('*/skills/*/SKILL.md'))
    except OSError:
        return []


def derive_population(marketplace_root: Path, cache=None) -> list[EnumSite]:
    """Return every documented enum site the sweep examines, resolved or not.

    This is the positive-population surface: its length is the number of enum
    sites examined (a volume), and the members flagged ``diverged`` are the
    coverage number. A clean sweep is a non-empty population with zero
    ``diverged`` — distinguishable from a sweep that examined nothing.
    """
    get_tree = cache.get_tree if cache is not None else _fallback_get_tree()
    resolver = _Resolver(marketplace_root, get_tree)
    # Memoize per-script authority so a script documenting many enums parses once.
    authority_cache: dict[
        str, dict[tuple[tuple[str, ...], str], frozenset[str] | None]
    ] = {}
    # Whether each notation's script parsed at all — the discriminator between
    # "the script could not be read" and "the script was read and declares no
    # resolvable choices for this flag". Both leave ``choices`` at ``None``.
    parsed_cache: dict[str, bool] = {}
    # The subcommand paths each notation's parser surface was modelled at — the
    # discriminator between "no choices declared" and "parser never seen".
    paths_cache: dict[str, set[tuple[str, ...]]] = {}
    # Whether each notation's script declares a ``choices=`` the walk could not
    # attribute to a parser path — if so, an absent key is not evidence of
    # absence for any site on that script.
    incomplete_cache: dict[str, bool] = {}
    # Per-PATH incompleteness: the parser for these subcommands was handed to a
    # call this walk cannot model, so an absent authority key is not evidence.
    incomplete_paths_cache: dict[str, set[tuple[str, ...]]] = {}
    population: list[EnumSite] = []

    for skill_md in _skill_md_files(marketplace_root):
        for line, notation, subcommand, flag, documented in _enum_sites_in_skill(skill_md):
            script_path = _script_path_for_notation(notation, marketplace_root)
            choices: frozenset[str] | None = None
            cause: str | None = UNRESOLVED_NOTATION
            if len(documented) < 2:
                # A one-member group is genuinely AMBIGUOUS — a template slot
                # (``--scope {phase}.{role}|plan|...`` yields ``{phase}``, a slot
                # for a phase NAME) or a truncated enum (``{bug}`` against a live
                # ``choices=['bug','improvement']``, which is this rule's own
                # headline drift shape). Nothing in the notation tells them
                # apart, so it is not compared.
                #
                # It stays IN the population under its own cause rather than
                # being dropped at collection. Dropping it was a SILENT
                # narrowing — the token was examined, the sweep declined to
                # judge it, and no published figure said so. That is this
                # analyzer's own subject committed by the analyzer, and it was
                # defended in a comment claiming a one-member group "carries no
                # drift signal anyway", which the truncated-enum case refutes.
                # Counted as a blind spot, because it may be a real claim.
                cause = UNRESOLVED_SINGLE_MEMBER
            elif script_path is not None:
                if notation not in authority_cache:
                    tree = get_tree(script_path)
                    parsed_cache[notation] = tree is not None
                    if tree is not None:
                        authority_cache[notation] = _authority_by_subcommand_flag(tree, resolver)
                        paths_cache[notation] = _derived_subcommand_paths(tree)
                        incomplete_cache[notation] = _has_unattributed_choices(tree)
                        incomplete_paths_cache[notation] = _paths_with_incomplete_authority(tree)
                    else:
                        authority_cache[notation] = {}
                        paths_cache[notation] = set()
                        incomplete_cache[notation] = False
                        incomplete_paths_cache[notation] = set()
                authority = authority_cache[notation]
                key = (subcommand, flag)
                # Three fail-closed skips all leave ``choices`` at None, and they
                # are told apart in this order:
                #   * the script did not parse at all;
                #   * it parsed but this subcommand's parser was never MODELLED
                #     — the dominant case being a parser built by an imported
                #     helper, which yields no ``ArgumentParser()`` here. A real
                #     blind spot: the rule never reached the parser, so it
                #     established nothing either way;
                #   * the parser WAS modelled, the module's authority is
                #     complete, and the key is simply absent — the only one of
                #     these that means the rule's authority is ESTABLISHED and
                #     found absent.
                # Reading the second as the third is the failure this rule exists
                # to catch, committed by the rule's own coverage figure.
                choices = authority.get(key)
                if not parsed_cache[notation]:
                    cause = UNRESOLVED_SCRIPT_UNPARSEABLE
                elif subcommand not in paths_cache[notation]:
                    cause = UNRESOLVED_PARSER_NOT_DERIVED
                elif key not in authority:
                    cause = (
                        UNRESOLVED_AUTHORITY_INCOMPLETE
                        if incomplete_cache[notation]
                        or subcommand in incomplete_paths_cache[notation]
                        else UNRESOLVED_NO_CHOICES_DECLARED
                    )
                else:
                    cause = UNRESOLVED_CHOICES_UNRESOLVABLE
            resolved = choices is not None
            diverged = resolved and documented != choices
            population.append(
                EnumSite(
                    skill_md=skill_md,
                    line=line,
                    notation=notation,
                    subcommand=subcommand,
                    flag=flag,
                    documented=documented,
                    choices=choices,
                    resolved=resolved,
                    diverged=diverged,
                    unresolved_cause=None if resolved else cause,
                )
            )
    return population


def _fallback_get_tree():
    """Return a standalone parse-once ``get_tree`` when no ``AstCache`` is supplied."""
    memo: dict[str, ast.Module | None] = {}

    def get_tree(path: Path) -> ast.Module | None:
        key = str(path)
        if key in memo:
            return memo[key]
        try:
            source = path.read_text(encoding='utf-8')
            tree: ast.Module | None = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            tree = None
        memo[key] = tree
        return tree

    return get_tree


def derive_coverage(population: list[EnumSite]) -> dict:
    """Summarise what a sweep over ``population`` actually compared.

    A finding count answers "how many enums were wrong". It cannot answer "how
    many were CHECKED", and for this rule the two are far apart: roughly half the
    documented enum sites resolve to no authority and are examined-but-skipped.
    Without this, a clean sweep reads as "every documented enum matches" when it
    means "every enum I could resolve matches, and I could not resolve half of
    them".

    Returns ``population_size``, ``resolved``, ``unresolved``,
    ``unresolved_fraction`` (rounded to three places, ``0.0`` over an empty
    population) and ``unresolved_causes`` — a COMPLETE census over
    :data:`UNRESOLVED_CAUSES`, so the gap is attributable rather than a single
    opaque number and a cause with no occurrences reads as ``0`` rather than as
    an absence a reader must interpret.

    ``blind_spots`` is the sum over :data:`UNRESOLVED_BLIND_SPOT_CAUSES` — every
    cause EXCEPT ``no_choices_declared``, which is the only one where the rule's
    authority was ESTABLISHED and found absent rather than left unestablished.
    That partition is the load-bearing part, and getting it wrong is worse than
    not publishing it: a coverage figure that files "the parser was never seen"
    under "nothing to check" reports its largest gap as reassurance.

    It is a statement about this rule's authority, not about the flags: a site in
    ``no_choices_declared`` may still be constrained by a check this rule does
    not read.
    """
    total = len(population)
    unresolved_sites = [site for site in population if not site.resolved]
    causes: dict[str, int] = dict.fromkeys(UNRESOLVED_CAUSES, 0)
    for site in unresolved_sites:
        cause = site.unresolved_cause or UNRESOLVED_CHOICES_UNRESOLVABLE
        causes[cause] = causes.get(cause, 0) + 1
    return {
        'population_size': total,
        'resolved': total - len(unresolved_sites),
        'unresolved': len(unresolved_sites),
        'unresolved_fraction': round(len(unresolved_sites) / total, 3) if total else 0.0,
        'blind_spots': sum(
            count for cause, count in causes.items() if cause in UNRESOLVED_BLIND_SPOT_CAUSES
        ),
        'unresolved_causes': causes,
    }


def analyze_canonical_enum_drift(marketplace_root: Path, cache=None) -> list[dict]:
    """Scan every canonical block for a documented enum diverging from live choices.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).
    cache:
        Optional shared :class:`AstCache` so scripts parse at most once per pass.

    Returns
    -------
    list[dict]
        One finding dict per diverging enum site (see module docstring shape).
        Every finding publishes ``population_size`` — the count of enum sites the
        sweep examined — plus ``unresolved_notation_fraction``,
        ``unresolved_notation_blind_spots`` and ``unresolved_notation_causes``:
        the share of that population the sweep could not resolve an authority
        for, how much of that share is a real gap, and what stopped it. A clean run
        carries no findings and therefore no figures, which is why the RUNNER
        publishes the population size on the rule summary — see
        :func:`analyze_canonical_enum_drift_with_population`. Reference prose
        claimed the per-finding keys made a clean sweep state its coverage; on a
        clean tree there are no findings to carry them, so that was exactly
        backwards until the runner was wired.
    """
    return _findings_from_population(derive_population(marketplace_root, cache=cache))


def _findings_from_population(population: list[EnumSite]) -> list[dict]:
    """Build the finding list for an already-derived population.

    Shared by :func:`analyze_canonical_enum_drift` and its
    ``_with_population`` sibling so the two cannot produce different findings
    from the same tree.
    """
    population_size = len(population)
    coverage = derive_coverage(population)
    findings: list[Finding] = []
    for site in population:
        if not site.diverged or site.choices is None:
            continue
        missing_from_doc = sorted(site.choices - site.documented)
        not_in_choices = sorted(site.documented - site.choices)
        sub = ' '.join(site.subcommand)
        target = f'{site.notation} {sub}'.strip()
        findings.append(
            Finding(
                type=RULE_ID,
                file=str(site.skill_md),
                line=site.line,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'Canonical block documents `--{site.flag} '
                    f'{{{"|".join(sorted(site.documented))}}}` for `{target}`, '
                    f'but the live argparse `choices=` is '
                    f'{{{"|".join(sorted(site.choices))}}} — the documented enum is a '
                    f'stale oracle (canonical-enum-choices-drift). '
                    + (f'Missing from doc: {missing_from_doc}. ' if missing_from_doc else '')
                    + (f'Not in choices: {not_in_choices}.' if not_in_choices else '')
                ).strip(),
                details={
                    'notation': site.notation,
                    'subcommand': sub,
                    'flag': f'--{site.flag}',
                    'documented': sorted(site.documented),
                    'choices': sorted(site.choices),
                    'missing_from_doc': missing_from_doc,
                    'not_in_choices': not_in_choices,
                    'population_size': population_size,
                    'unresolved_notation_fraction': coverage['unresolved_fraction'],
                    'unresolved_notation_blind_spots': coverage['blind_spots'],
                    'unresolved_notation_causes': coverage['unresolved_causes'],
                },
                extra={'rule': RULE_NAME},
            )
        )
    return [f.to_dict() for f in findings]


def analyze_canonical_enum_drift_with_population(
    marketplace_root: Path, cache=None
) -> tuple[list[dict], int]:
    """Return ``(findings, population_size)`` from a SINGLE derivation.

    The runner publishes the examined population on its rule summaries, and a
    clean tree is the only state a passing gate is ever in — so without this the
    rule's summary on a green run is ``{'rule': ..., 'findings': 0}``, a clean
    result over a population the reader is told nothing about. That is this
    analyzer's own subject, and two reference documents asserted the opposite
    ("a clean sweep states what it could not check") while the gate said nothing.

    One derivation, not two: re-deriving the roster to get the number is a second
    chance to disagree with the one the findings came from. Mirrors
    ``analyze_shim_marker_with_population``.
    """
    population = derive_population(marketplace_root, cache=cache)
    return _findings_from_population(population), len(population)
