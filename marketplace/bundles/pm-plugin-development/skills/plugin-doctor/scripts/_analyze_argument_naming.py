#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Argument-naming rule cluster — notation/subcommand/flag/Canonical-Forms cross-check.

This module implements the ``ARGUMENT_NAMING_*`` rule cluster used by
plugin-doctor to detect drift between marketplace prose (SKILL.md, agent
markdown, recipe markdown, standards) and the actual argparse declarations
of the scripts those documents reference. The cluster also cross-checks the
"Canonical Forms" table in
``marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md``
against the same argparse declarations.

Surface derivation — the shared help-derived accept-set
-------------------------------------------------------
The cluster does NOT derive its own accept-set. ``build_script_index`` is a
thin adapter over ``plan-marshall:script-shared``'s ``argparse_surface``
module, the single derivation of "what does this script accept?" in the tree
(see that module's docstring for the mechanism, the four parse anchors, the
asymmetric-error rule, and the fail-closed-on-uncertainty invariant).

The module-private ``add_parser`` AST walk this cluster used to carry was
deleted rather than kept as a fallback. It was blind to ``aliases=`` — so it
reported a documented alias invocation (``manage-tasks get``,
``manage-status get``, ``manage-lessons read``) as an unknown subcommand — and
blind to any parser assembled in an imported module, which is exactly the
``tools-integration-ci:ci`` shape. A fallback would reinstate that too-small
accept-set, and a too-small accept-set is strictly more dangerous than no
accept-set because it rejects valid calls.

The argparse table is not the layer that accepts
-------------------------------------------------
The derivation answers "what does this script's argparse declare?", and for a
long time this cluster treated that as the same question as "what does this
invocation get away with?". It is not. Some flags are consumed by the
**executor / router layer that runs BEFORE the target script's argparse ever
sees argv**, so they appear in no node's ``--help`` and yet every documented
call carrying them works. Judging those against the argparse table alone
manufactures an ``ARGUMENT_NAMING_FLAG_UNKNOWN`` finding against a correct
invocation — the over-rejection direction the asymmetric-error rule above
forbids, and the same species as the router-consumed ``--project-dir`` blind
spot on ``tools-integration-ci:ci``.

The accept-set for that layer is NOT re-derived here. It is
:data:`argparse_surface.UNIVERSAL_FLAGS` — the single definition the executor's
own pre-spawn validator mirrors and the sibling ``manage-invocation-invalid``
rule already imports — so all three guards agree about what a script accepts.
It is unioned into the ACCEPTANCE surface only:

- ``_ScriptEntry.subcommands`` values and :attr:`_ScriptEntry.root_accept_flags`
  carry it, because those are what :func:`scan_flag` and
  :func:`scan_canonical_forms` judge a flag's EXISTENCE against;
- ``root_flags`` and ``subcommand_own_flags`` deliberately do NOT, because those
  two are the placement authority :func:`scan_router_flag_placement` reads, and
  the four universals do not share one placement behaviour. ``audit-plan-id`` is
  genuinely position-independent (``architecture which-module --path P
  --audit-plan-id X`` is accepted with the flag AFTER the verb), but ``plan-id``
  and ``project-dir`` are on many scripts ordinary root ``add_argument``
  declarations that argparse rejects after the verb. Widening the placement
  surface with the acceptance set would silence exactly the recurrence signatures
  the placement rule exists to catch — see that function's docstring for why the
  per-script ``root_flags`` membership test is the right discriminator instead.

Consequences of the promotion, both intended:

- **Alias awareness.** The choice list argparse renders carries alias
  spellings flat alongside canonical names, so an alias invocation is simply
  in the accepted set.
- **Flag sensitivity is deliberately lower.** The shared derivation
  over-approximates a node's flag set (every ``--long-token`` anywhere in the
  output) and this adapter widens further, unioning each subcommand's whole
  subtree with the root parser's flags. That is the safe direction — fewer
  findings, no false findings — but it IS a real sensitivity change from the
  exact AST set, so every canonical argparse-rejection recurrence signature is
  pinned as a positive control in this cluster's tests.

Findings have severity=error and fixable=False, matching the
``DISPLAY_DETAIL_*`` finding shape used elsewhere in the plugin-doctor
codebase. Each finding carries ``rule_id``, ``file``, ``line``, plus
rule-specific ``details`` keys (notation/subcommand/flag/etc.).

Activation
----------
This rule cluster is unconditionally active across all marketplace markdown.
Recurring stale-flag drift in skill workflows motivated default-on
enforcement rather than a gated transitional period.

A usage string is not a call
---------------------------
``_INVOCATION_RE`` resolves the verb slot with ``[a-z][A-Za-z0-9_\\-]*``, so a
line whose positional region holds usage-template syntax names no verb and comes
back with ``subcommand=None``. Every flag on the line was then judged against the
ROOT scope — and a pure subcommand-dispatching script legitimately declares
almost nothing there, so each flag read as invented. Three real shapes hit this:

- ``manage-plan-documents {type} create --summary ... --went_well ...``
- ``permission_doctor {command} {args}`` (addressed by ``--scope`` in the prose
  around it — a different clause of the same sentence, not an argument of the
  call)
- ``profiles [--project-dir PROJECT_DIR | --plan-id PLAN_ID] list [--module M]``

⛔ The cause is NOT an accept-set that came back empty for a script that declares
flags. ``permission_doctor`` and ``profiles`` were probed live and genuinely
declare no root long flags beyond the two-state ``--project-dir`` /
``--plan-id`` pair, so the derived surface was correct and the extractor was
wrong. :attr:`_Invocation.positional_region_is_templated` is therefore the guard,
ported from ``_analyze_manage_invocation``, which has carried it all along.

Such a site is COUNTED as a blind spot rather than dropped silently: it is an
enumerated invocation the cluster looked at and drew no verdict about, and a skip
that did not raise the figure would shrink the corpus quietly.

Absent substrate is an outcome, not a no-op
-------------------------------------------
The accept-set is derived from the generated executor at
``{repo}/.plan/execute-script.py``, and that file is git-ignored — a fresh clone
carries none. The cluster used to answer an unreadable or empty registry with
``return []``, which is byte-identical to the answer it gives a corpus it read
in full and found clean. A gate cannot tell those apart, so an absent substrate
read as a pass over 600-odd unexamined markdown files.

An unusable registry now emits :data:`RULE_SUBSTRATE_ABSENT` carrying the
``could_not_look`` outcome — the same third state, distinct from both pass and
fail, that ``_plugin_pin_trap`` models for its own three stores. The finding is
anchored at the BUNDLES root so ``cmd_quality_gate``'s ``_finding_is_tree_wide``
bypass keeps it under a ``--paths``-scoped run, exactly as the other
anti-vacuity guards are kept.

Coverage is published on every run, clean or not
------------------------------------------------
A finding count answers "how many invocations were wrong". It cannot answer
"how many were JUDGED", and on a clean tree — the only state a passing gate is
ever in — there is no finding left to carry the figure. The runner therefore
publishes two numbers on this rule's summary, derived by
``analyze_argument_naming_with_population`` in the SAME pass the findings come
from:

- ``population_size`` — every executor invocation the markdown corpus carries.
  This is what the cluster enumerated, and it needs no registry: enumeration is
  a read of the corpus, the registry is only the AUTHORITY the enumerated sites
  are judged against.
- ``blind_spots`` — the enumerated sites the cluster could not DECIDE. A
  notation that is absent from the registry is decided (it is reported as
  ``ARGUMENT_NAMING_NOTATION_INVALID``); a notation that IS registered but whose
  ``--help`` surface was dropped fail-closed, or whose verb listing or flag set
  came back unconfident, is not. Those sites were looked at and no verdict was
  drawn, which a bare zero hides.

The two figures share one unit — invocations — in every state the cluster can
be in, including the ``could_not_look`` state below, where they are EQUAL
because every enumerated site went undecided.

Public API
----------
- ``analyze_argument_naming(marketplace_root)``: entry point — returns
  findings for every rule ID in the cluster, combined.
- ``analyze_argument_naming_with_population(marketplace_root)``: the same
  single derivation, returning ``(findings, population_size, blind_spots)``.
- ``read_notation_registry(executor_path)``: reads the executor's notation
  registry AND why it is empty when it is (``NotationRegistry.status``).
- ``scan_notation(marketplace_root, registered_notations)``: detects
  ``ARGUMENT_NAMING_NOTATION_INVALID``.
- ``scan_subcommand(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``.
- ``scan_flag(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_FLAG_UNKNOWN``.
- ``scan_router_flag_placement(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED``.
- ``scan_canonical_forms(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT``.
- ``load_registered_notations(executor_path)``: regex-parses the executor's
  ``SCRIPTS = { ... }`` literal and returns the set of registered notations.
- ``build_script_index(registered_notations, marketplace_root)``: thin adapter
  over the shared ``argparse_surface`` derivation, flattening each script's
  verb tree to ``{subcommand: set[flags] | None}`` plus a ``root_flags`` set
  and a ``subcommands_confident`` marker. ``None`` in either flag position
  propagates the derivation's own ``flags_confident`` / ``children_confident``
  markers as "unknown surface, skip validation here" — see ``_ScriptEntry``.

Rule IDs registered
-------------------
- ``ARGUMENT_NAMING_NOTATION_INVALID``
- ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``
- ``ARGUMENT_NAMING_FLAG_UNKNOWN``
- ``ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED``
- ``ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT``
- ``ARGUMENT_NAMING_SUBSTRATE_ABSENT``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _analyze_manage_invocation import (
    FIRST_FLAG_RE,
    ROUTER_VERBS,
    TEMPLATE_SYNTAX_RE,
)
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor
from argparse_surface import (
    UNIVERSAL_FLAGS,
    ParserNode,
    ScriptSurface,
    build_surface_index,
    resolve_executor,
)

# =============================================================================
# Rule IDs
# =============================================================================

RULE_NOTATION_INVALID = 'ARGUMENT_NAMING_NOTATION_INVALID'
RULE_SUBCOMMAND_UNKNOWN = 'ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN'
RULE_FLAG_UNKNOWN = 'ARGUMENT_NAMING_FLAG_UNKNOWN'
RULE_CANONICAL_FORMS_DRIFT = 'ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT'
RULE_ROUTER_FLAG_MISPLACED = 'ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED'
RULE_SUBSTRATE_ABSENT = 'ARGUMENT_NAMING_SUBSTRATE_ABSENT'

# =============================================================================
# Substrate states — the could_not_look axis
# =============================================================================

#: The outcome name this cluster shares with ``_plugin_pin_trap``: a state that
#: is neither a pass nor a fail, because the run never got to look.
OUTCOME_COULD_NOT_LOOK = 'could_not_look'

#: Registry-substrate states. The two executor states are kept apart from
#: ``registry_empty`` for the reason ``_plugin_pin_trap`` keeps its four
#: ``EXECUTOR_*`` statuses apart: an executor that IS present and registers
#: nothing is a different defect from one that is not there at all, and
#: collapsing them files a demonstrated defect as a missing file.
SUBSTRATE_PRESENT = 'present'
SUBSTRATE_EXECUTOR_ABSENT = 'executor_absent'
SUBSTRATE_EXECUTOR_UNREADABLE = 'executor_unreadable'
SUBSTRATE_REGISTRY_EMPTY = 'registry_empty'

_SUBSTRATE_EXPLANATIONS: dict[str, str] = {
    SUBSTRATE_EXECUTOR_ABSENT: (
        'the generated executor does not exist, so the notation registry every '
        'invocation is judged against was never read'
    ),
    SUBSTRATE_EXECUTOR_UNREADABLE: (
        'the generated executor exists but could not be read or decoded, so the '
        'notation registry was never read'
    ),
    SUBSTRATE_REGISTRY_EMPTY: (
        'the generated executor was read but its SCRIPTS literal registers no '
        'notation, so the registry is empty'
    ),
}

REMEDY_SUBSTRATE = (
    'Regenerate the executor with the steward wizard (`/marshall-steward`), which '
    'rewrites `.plan/execute-script.py` from the plugin cache. The executor is '
    'git-ignored, so a fresh clone never carries one: run this gate from a '
    'bootstrapped checkout, or read the outcome as "this cluster could not report '
    'on this tree" — never as a clean one.'
)

# Opt-in cluster descriptor. The ARGUMENT_NAMING_* rules are produced by a
# single ``analyze_argument_naming`` pass gated atomically by the
# ``argument_naming`` --rules token, so the cluster is represented by ONE
# descriptor whose rule_id is that token; the registry derives the opt-in set
# as ``{d.rule_id for d in registry if d.opt_in}``.
RULE_DESCRIPTOR = RuleDescriptor(
    rule_id='argument_naming',
    severity='error',
    category='structural',
    scope='corpus-relational',
    opt_in=True,
    default_on=False,
    has_fixer=False,
)


# =============================================================================
# Regexes
# =============================================================================

# Notation token used in markdown prose. Captures the full 3-part notation
# plus the immediately following subcommand and the rest of the line for
# downstream flag extraction. The line-start anchor is intentionally
# permissive — code blocks may indent and prose may use inline backticks.
# Leading ROUTER-FLAG run, consumed before the verb is located. A router-scoped
# flag is declared on the root parser and therefore belongs BEFORE the verb, so
# a correctly-written invocation puts it there — and the pattern that required
# the token immediately after the notation to be the verb then read such a call
# as having NO subcommand, judged its flags against the root set alone, and
# reported the verb's own flags as unknown. Exactly backwards: the correct
# spelling was the one that got flagged.
#
# ``[VALUE]`` is consumed when the following token is not itself a flag. That
# rule cannot distinguish a BOOLEAN router flag from one taking a value, so
# ``--dry-run list`` reads ``list`` as the value and resolves to no subcommand —
# the same answer the pattern gave before this run, so the ambiguity costs no
# coverage that existed. Resolving it would need the root flag surface, which
# this extractor does not have (it runs before the index is consulted).
_ROUTER_FLAG_PREFIX = r'(?:\s+--[A-Za-z][A-Za-z0-9_\-]*(?:=\S+)?(?:\s+(?!-)\S+)?)*'

_INVOCATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<notation>[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+)'
    r'(?P<leading>' + _ROUTER_FLAG_PREFIX + r')'
    r'(?:\s+(?P<subcommand>[a-z][A-Za-z0-9_\-]*))?'
    r'(?P<rest>.*)$'
)

# Loose token splitter used to enumerate ``--flag`` occurrences in the
# trailing portion of an invocation. Matches identifier-style flags;
# rejects placeholder shapes like ``--{plan-id}``.
_FLAG_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9_\-]*)\b')

# ``FIRST_FLAG_RE`` (where the positional region ends) and ``TEMPLATE_SYNTAX_RE``
# (which lines are usage strings rather than calls) are imported from
# ``_analyze_manage_invocation`` above, alongside ``ROUTER_VERBS`` and for the
# same reason: the two rules scan the same corpus for the same shapes, so a
# divergence would make one of them report a usage string the other correctly
# skipped. Sharing the objects is what rules that out — a copy could only assert
# it.

# A quoted run is a VALUE, whatever it looks like. Scanning raw text made
# ``list --message "--plan-id p"`` report ``--plan-id`` as a misplaced router
# flag — an error finding against a correct invocation, which is the
# over-rejection this cluster's asymmetric-error rule refuses. Blanked rather
# than removed so every surviving match keeps its original offset.
_QUOTED_RUN_RE = re.compile(r'"[^"]*"|\'[^\']*\'')


def _without_quoted_values(text: str) -> str:
    """``text`` with the CONTENTS of quoted runs blanked, offsets preserved."""
    return _QUOTED_RUN_RE.sub(lambda m: m.group(0)[0] + ' ' * (len(m.group(0)) - 2) + m.group(0)[-1], text)

# Canonical Forms table parser — extracts the rightmost code-fenced cell.
# The table format is:
#     | Script | Operation | Canonical form |
#     | --- | --- | --- |
#     | `manage-tasks` | ... | `manage-tasks read --plan-id {id} --task-number {n}` |
_CANONICAL_FORMS_HEADING = re.compile(r'^##\s+Canonical Forms\s*$')
_CANONICAL_FORMS_ROW = re.compile(r'^\|[^|]*\|[^|]*\|\s*`(?P<form>[^`]+)`\s*\|\s*$')

# Notation regex restricted to the ``SCRIPTS = { ... }`` literal in the
# executor module. Captures notation keys only — paths are ignored.
_SCRIPTS_DICT_KEY = re.compile(r'^\s*"(?P<notation>[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+)":')

# kebab-case validation for notation segments. Only letters, digits, and
# hyphens are allowed; underscore in script-name positions is treated as
# snake_case and reported as a notation violation.
_KEBAB_SEGMENT = re.compile(r'^[A-Za-z][A-Za-z0-9\-]*$')


# =============================================================================
# Data classes
# =============================================================================


@dataclass(frozen=True)
class _Invocation:
    """A single ``python3 .plan/execute-script.py {notation} ...`` token."""

    file: Path
    line: int  # 1-based
    notation: str
    subcommand: str | None
    rest: str  # portion of the line AFTER the verb
    leading: str = ''  # router flags written BEFORE the verb

    @property
    def positional_region_is_templated(self) -> bool:
        """True when the verb slot holds usage-template syntax, not a real verb.

        A templated positional region means this line is a usage STRING, not a
        concrete call: ``{type} create``, ``permission_doctor {command} {args}``,
        ``profiles [--project-dir | --plan-id] list [--module MODULE]``. None of
        those resolves to a verb, so :attr:`subcommand` comes back ``None`` and
        every flag on the line would be judged against the ROOT scope — where a
        pure subcommand-dispatching script legitimately declares almost nothing,
        so each flag reads as invented. The finding is against a line that was
        never a call.

        The region examined is everything before the first flag token, matching
        ``_analyze_manage_invocation._positional_region_is_templated`` — template
        syntax inside a flag VALUE (``--set k={worktree_path}``) is deliberately
        NOT covered, so those invocations keep full validation.
        """
        region = self.leading + self.rest if self.subcommand is None else self.rest
        flag_match = FIRST_FLAG_RE.search(region)
        head = region[: flag_match.start()] if flag_match else region
        if self.subcommand is not None:
            head = f'{self.subcommand} {head}'
        return bool(TEMPLATE_SYNTAX_RE.search(head))

    @property
    def all_flag_text(self) -> str:
        """Every flag on the line, wherever it was written relative to the verb.

        The two portions are kept apart on the record rather than re-derived
        from a concatenation: re-running the leading-flag pattern over
        ``leading + rest`` would greedily swallow the post-verb flags too, and a
        misplaced flag would then be invisible to the rule that exists to find
        it.
        """
        return self.leading + self.rest


@dataclass
class _ScriptEntry:
    """Argparse summary for one registered script.

    ``subcommands`` maps each registered subcommand name to the set of
    declared ``--flag`` names on that subparser. ``root_flags`` holds
    flags declared directly on the root ``ArgumentParser``.

    ``None`` is the explicit "unknown surface" value in BOTH flag positions,
    carried through from the shared derivation's ``flags_confident`` /
    ``children_confident`` markers. It is not the same as an empty set: an
    empty set says "this scope declares no flags, so every ``--flag`` is
    drift", while ``None`` says "this scope's flag surface was never derived,
    so no flag can be judged". Consumers MUST skip flag validation on ``None``
    rather than treating it as an empty accept-set — a too-small accept-set
    rejects valid calls, which the module docstring names as strictly more
    dangerous than no accept-set at all.

    ``subcommands_confident`` is the separate verb-listing marker. ``False``
    means the child listing is incomplete, so a name absent from
    ``subcommands`` may still be accepted and verb validation must be skipped.
    The two markers stay independent for the reason the shared ``ParserNode``
    docstring gives: collapsing them would let an unknown flag set suppress
    verb validation that WAS confidently derived, and vice versa.

    ``subcommand_own_flags`` holds each subcommand's OWN subtree flags, WITHOUT
    the root widening applied to ``subcommands``. The two are needed separately
    because they answer different questions: ``subcommands`` answers "would
    argparse accept this flag somewhere on this call?" (deliberately widened, so
    the unknown-flag rule cannot manufacture a false finding), while
    ``subcommand_own_flags`` answers "does the VERB declare it?" — which is what
    makes a root-scoped flag written after the verb detectable at all. Judging
    placement against the widened union is why a misplaced router flag could
    never be reported: the union can only ever ADD flags.

    The ACCEPTANCE / PLACEMENT split runs one level deeper than that widening.
    ``subcommands`` and :attr:`root_accept_flags` additionally carry
    :data:`UNIVERSAL_FLAGS` — the executor/router layer's accept-set, invisible
    to every ``--help`` because it is consumed before the target script's
    argparse runs. ``root_flags`` and ``subcommand_own_flags`` do NOT, and must
    not: they are what :func:`scan_router_flag_placement` reads, and a
    router-consumed flag has no placement to get wrong (it is stripped from argv
    wherever it was written). Adding it there would trade one false finding for
    another rather than removing it.
    """

    subcommands: dict[str, set[str] | None]
    root_flags: set[str] | None
    subcommands_confident: bool = True
    subcommand_own_flags: dict[str, set[str] | None] = field(default_factory=dict)

    @property
    def root_accept_flags(self) -> set[str] | None:
        """The root scope's acceptance surface — derived flags plus the universals.

        ``None`` propagates unchanged: an underived root surface stays underived,
        because widening an unknown set with the universals would turn "no
        accept-set" into a four-element one and start rejecting valid calls.
        """
        if self.root_flags is None:
            return None
        return self.root_flags | set(UNIVERSAL_FLAGS)


# =============================================================================
# Notation registry helpers
# =============================================================================


@dataclass(frozen=True)
class NotationRegistry:
    """The executor-derived notation set, plus WHY it is empty when it is.

    An empty ``notations`` alone cannot say whether the registry was read and
    found empty or never read at all, and the cluster's whole accept-set hangs
    off it. :attr:`status` carries the discriminator, so a caller can report the
    absence instead of silently answering as though the corpus had been judged.
    """

    notations: frozenset[str]
    status: str
    executor_path: Path

    @property
    def usable(self) -> bool:
        """True when the registry is evidence about at least one notation."""
        return self.status == SUBSTRATE_PRESENT

    @property
    def unusable_because(self) -> str | None:
        """Why this registry is not an accept-set, or ``None`` when it is."""
        return None if self.usable else _SUBSTRATE_EXPLANATIONS[self.status]


def read_notation_registry(executor_path: Path) -> NotationRegistry:
    """Read the executor's ``SCRIPTS = { ... }`` block into a :class:`NotationRegistry`.

    Uses a line-by-line regex rather than full Python parsing so the function
    works against the generated executor without importing it. ``FileNotFoundError``
    is caught BEFORE its ``OSError`` base so an absent executor stays
    distinguishable from an unreadable one — the two call for different operator
    action (bootstrap the checkout vs. repair a corrupt file).
    """
    try:
        text = executor_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return NotationRegistry(frozenset(), SUBSTRATE_EXECUTOR_ABSENT, executor_path)
    except (OSError, UnicodeDecodeError):
        return NotationRegistry(frozenset(), SUBSTRATE_EXECUTOR_UNREADABLE, executor_path)

    notations: set[str] = set()
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block:
            if stripped.startswith('SCRIPTS') and '=' in stripped and '{' in stripped:
                in_block = True
            continue
        if stripped == '}':
            break
        match = _SCRIPTS_DICT_KEY.match(line)
        if match:
            notations.add(match.group('notation'))
    status = SUBSTRATE_PRESENT if notations else SUBSTRATE_REGISTRY_EMPTY
    return NotationRegistry(frozenset(notations), status, executor_path)


def load_registered_notations(executor_path: Path) -> set[str]:
    """Return the registered notation keys, dropping the substrate status.

    Kept as the plain-set accessor for callers that only need the accept-set.
    A caller that must distinguish "read and empty" from "never read" uses
    :func:`read_notation_registry` instead.
    """
    return set(read_notation_registry(executor_path).notations)


def _substrate_absent_finding(
    bundles_root: Path,
    registry: NotationRegistry,
    markdown_targets: int,
    population_size: int,
) -> dict:
    """The ``could_not_look`` finding emitted when the registry is not evidence.

    Anchored at ``bundles_root`` — the root ``cmd_quality_gate`` compares against
    in ``_finding_is_tree_wide`` — so a ``--paths``-scoped run keeps it. A
    file-anchored guard would be dropped by the scope filter, which is how the
    other anti-vacuity guards in this tree learned to anchor here.

    ``markdown_targets`` and ``population_size`` are published because they are
    the figures that make the outcome legible: the corpus the cluster WOULD have
    judged, counted in files and in invocation sites, none of which it did. A
    bare zero-findings result says nothing about either number.

    ``blind_spots`` equals ``population_size`` here, and the equality is the
    point: enumerating the corpus needs no registry, deciding it does, so on this
    path every site the cluster found is a site it could not rule on. The key
    carries the SAME unit — invocations — that it carries on a usable run, so a
    reader comparing two runs is comparing one quantity.
    """
    return Finding(
        type=RULE_SUBSTRATE_ABSENT,
        file=str(bundles_root),
        line=0,
        severity='error',
        fixable=False,
        rule_id=RULE_SUBSTRATE_ABSENT,
        description=(
            f'{OUTCOME_COULD_NOT_LOOK}: {registry.unusable_because} '
            f'({registry.executor_path}). {markdown_targets} markdown file(s) '
            f'carrying {population_size} executor invocation(s) were in scope and '
            'NONE were judged — this run is not a clean result. '
            + REMEDY_SUBSTRATE
        ),
        details={
            'outcome': OUTCOME_COULD_NOT_LOOK,
            'reason': registry.status,
            'substrate': str(registry.executor_path),
            'population_size': population_size,
            'blind_spots': population_size,
            'markdown_targets': markdown_targets,
            'remedy': REMEDY_SUBSTRATE,
        },
    ).to_dict()


# =============================================================================
# Accept-set index — thin adapter over the shared help-derived derivation
# =============================================================================


def _subtree_flags(node: ParserNode) -> set[str] | None:
    """Union the flag surfaces of ``node`` and every descendant, or ``None``.

    Widening, per the asymmetric-error rule. This index is flat — it keys only
    on the FIRST positional — while argparse chains can be three levels deep
    (``manage-config plan phase-5-execute set --field X``). Attributing only the
    first-level node's own flags would report ``--field`` as unknown on a
    perfectly valid call. Unioning the subtree accepts a flag that is really
    declared two levels down, which over-accepts and never over-rejects.

    Returns ``None`` — "this subtree's flag surface is unknown" — as soon as any
    reachable node disclaims either marker. ``flags_confident=False`` means that
    node's own flags were never derived, and ``children_confident=False`` means
    there may be unlisted descendants whose flags the union therefore misses.
    Both make the union an UNDER-approximation, and an under-approximated
    accept-set rejects valid calls, so the union is withdrawn rather than
    returned smaller. The live producer is
    ``argparse_surface._derive_node``'s unprobeable-child path, which registers
    a child whose own ``--help`` probe failed as a node with both markers false.
    """
    if not node.flags_confident or not node.children_confident:
        return None
    flags = set(node.flags)
    for child in node.children.values():
        child_flags = _subtree_flags(child)
        if child_flags is None:
            return None
        flags |= child_flags
    return flags


def _entry_from_surface(surface: ScriptSurface) -> _ScriptEntry:
    """Flatten a derived surface into this cluster's two-level index shape.

    ``subcommands`` keys are every accepted top-level spelling — canonical
    names AND alias spellings, exactly as the choice list renders them — which
    is what makes a documented alias invocation resolve instead of reporting an
    unknown subcommand. Each value is the subcommand's subtree flag union
    widened with the root parser's own flags.

    That widening is deliberate OVER-APPROXIMATION, and it is not a claim about
    argparse. Argparse does NOT honour a root-declared flag after the verb — the
    subparser owns everything from the verb onward, and a root flag written there
    is rejected. The union exists because the unknown-flag rule must never
    manufacture a finding out of a scope question: a flag that IS declared
    somewhere on the call is not an invented flag, and reporting it as one would
    be the false-positive direction this module's own docstring names as the more
    dangerous one. WHERE such a flag belongs is a separate question, answered
    against ``subcommand_own_flags`` by the router-flag-placement rule.

    :data:`UNIVERSAL_FLAGS` joins the same acceptance union for the same reason,
    one layer out: those flags are consumed by the executor/router BEFORE the
    target script's argparse runs, so they are declared by no node and would
    otherwise be reported as invented on every call that carries them. They are
    added ONLY here and in :attr:`_ScriptEntry.root_accept_flags` — never to
    ``root_flags`` or ``subcommand_own_flags``, which the placement rule reads.

    A key is retained even when its flag surface is unknown, with ``None`` as
    the value. Dropping the key instead would make the subcommand rule report
    the name as undeclared — a false finding manufactured out of the very
    uncertainty the marker exists to signal — because the choice list that
    named the child IS the confident acceptance oracle; only the child's own
    surface is missing. An unconfident root flag surface poisons every
    subcommand's value too, since each is widened with the root's flags.
    """
    root_flags = set(surface.root.flags) if surface.root.flags_confident else None
    subcommands: dict[str, set[str] | None] = {}
    subcommand_own_flags: dict[str, set[str] | None] = {}
    for name, child in surface.root.children.items():
        child_flags = _subtree_flags(child)
        subcommand_own_flags[name] = child_flags
        if root_flags is None or child_flags is None:
            subcommands[name] = None
        else:
            subcommands[name] = root_flags | child_flags | set(UNIVERSAL_FLAGS)
    return _ScriptEntry(
        subcommands=subcommands,
        root_flags=root_flags,
        subcommands_confident=surface.root.children_confident,
        subcommand_own_flags=subcommand_own_flags,
    )


def build_script_index(
    registered_notations: set[str],
    marketplace_root: Path,
) -> dict[str, _ScriptEntry]:
    """Build the ``notation -> _ScriptEntry`` index from the shared derivation.

    A notation whose surface is not derivable is OMITTED from the index. Every
    consumer below already treats a missing entry as "no ground truth, emit
    nothing", so omission is the fail-closed path: an unparseable ``--help``
    can never manufacture a finding. The same holds when no executor is
    reachable — the index is empty and the cluster is a no-op.
    """
    executor = resolve_executor(marketplace_root)
    if executor is None or not registered_notations:
        return {}
    index: dict[str, _ScriptEntry] = {}
    surfaces = build_surface_index(sorted(registered_notations), executor)
    for notation, surface in surfaces.items():
        if isinstance(surface, ScriptSurface):
            index[notation] = _entry_from_surface(surface)
    return index


# =============================================================================
# Markdown invocation extraction
# =============================================================================


def _markdown_targets(marketplace_root: Path) -> list[Path]:
    """Enumerate markdown files subject to argument-naming scanning.

    Scope:
    - SKILL.md
    - agents/*.md (component agents)
    - commands/*.md (component commands)
    - skills/*/standards/*.md
    - skills/*/recipes/*.md (rare; recipes are usually skill-level)
    - skills/*/references/*.md (referenced for invocation examples)
    - skills/*/workflow/*.md (workflow bodies — Bash invocations live here)
    """
    targets: list[Path] = []
    bundles_dir = marketplace_root / 'bundles'
    if not bundles_dir.is_dir():
        return targets

    for bundle_dir in sorted(bundles_dir.iterdir()):
        if not bundle_dir.is_dir():
            continue
        # agents/*.md and commands/*.md
        for sub in ('agents', 'commands'):
            sub_dir = bundle_dir / sub
            if sub_dir.is_dir():
                targets.extend(sorted(sub_dir.glob('*.md')))
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.is_file():
                targets.append(skill_md)
            for sub in ('standards', 'references', 'recipes', 'workflow'):
                sub_dir = skill_dir / sub
                if sub_dir.is_dir():
                    targets.extend(sorted(sub_dir.glob('*.md')))
    return targets


def _joined_lines(text: str) -> list[tuple[int, str]]:
    """``(first_physical_line, joined_text)`` with shell continuations folded.

    A canonical block routinely writes one command across several physical lines
    with a trailing backslash. Matching each physical line independently split
    those into an executor line carrying no flags and a continuation line
    carrying no executor token — so a misplaced router flag on the continuation
    was invisible and the rule reported CLEAN over a rejected invocation. The
    line number reported is the FIRST physical line, which is where a reader
    looks. ``_analyze_manage_invocation`` already folds continuations this way.
    """
    out: list[tuple[int, str]] = []
    pending: list[str] = []
    start = 0
    for idx, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.rstrip()
        if not pending:
            start = idx
        if stripped.endswith('\\'):
            pending.append(stripped[:-1])
            continue
        pending.append(raw)
        out.append((start, ''.join(pending)))
        pending = []
    if pending:
        out.append((start, ''.join(pending)))
    return out


def _extract_invocations(markdown_path: Path) -> list[_Invocation]:
    """Parse markdown lines and emit one ``_Invocation`` per executor token."""
    try:
        text = markdown_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    out: list[_Invocation] = []
    for idx, raw in _joined_lines(text):
        match = _INVOCATION_RE.search(raw)
        if not match:
            continue
        sub = match.group('subcommand')
        # The leading router flags are skipped when LOCATING the verb and are
        # recorded separately, so the flag scan can see every flag on the line
        # (``all_flag_text``) while the placement rule can still tell which side
        # of the verb each was written on.
        out.append(
            _Invocation(
                file=markdown_path,
                line=idx,
                notation=match.group('notation'),
                subcommand=sub if sub else None,
                rest=match.group('rest') or '',
                leading=match.group('leading') or '',
            )
        )
    return out


# =============================================================================
# Notation validity rule
# =============================================================================


def _notation_segments_kebab(notation: str) -> bool:
    """Return ``True`` iff every segment of ``notation`` is kebab-case."""
    parts = notation.split(':')
    if len(parts) != 3:
        return False
    return all(_KEBAB_SEGMENT.fullmatch(p) for p in parts)


def scan_notation(
    marketplace_root: Path,
    registered_notations: set[str],
) -> list[dict]:
    """Detect notation-invalid prose tokens.

    A notation is invalid when any of:
    1. A segment uses snake_case (underscores) where kebab-case is canonical
       AND the snake_case form is not present in ``registered_notations``.
       The registry is the source of truth.
    2. The third segment exactly repeats the second (``foo:foo`` shape).
    3. The notation is not present in ``registered_notations``.
    """
    findings: list[Finding] = []
    for md in _markdown_targets(marketplace_root):
        for inv in _extract_invocations(md):
            notation = inv.notation
            if notation in registered_notations:
                continue

            # Determine the failure mode for richer details.
            parts = notation.split(':')
            details: dict = {'notation': notation}
            if len(parts) == 3 and parts[1] == parts[2]:
                details['reason'] = 'third_segment_repeats_second'
            elif '_' in notation:
                details['reason'] = 'snake_case_not_registered'
            else:
                details['reason'] = 'not_registered'

            findings.append(
                Finding(
                    type=RULE_NOTATION_INVALID,
                    file=str(inv.file),
                    line=inv.line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_NOTATION_INVALID,
                    description=(
                        f'Notation `{notation}` is not registered in the executor (reason: {details["reason"]})'
                    ),
                    details=details,
                )
            )
    return [f.to_dict() for f in findings]


# =============================================================================
# Subcommand validity rule
# =============================================================================


def scan_subcommand(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Detect invented subcommand tokens following a registered notation.

    Two shapes are accepted that the ``--help``-derived choice list cannot show:
    a templated positional region (a usage string, not a call), and a ROUTER
    verb intercepted in the script's ``main()`` ahead of subparser dispatch. The
    latter is the verb-level counterpart of the router-CONSUMED flag — invisible
    for the same structural reason, and reported for the same wrong reason.
    """
    findings: list[Finding] = []
    for md in _markdown_targets(marketplace_root):
        for inv in _extract_invocations(md):
            if inv.positional_region_is_templated:
                # A usage string, not a call — the verb slot holds a placeholder.
                continue
            if inv.subcommand is None:
                continue
            entry = script_index.get(inv.notation)
            if entry is None:
                # Notation not in the index (script missing or notation
                # invalid). Notation rule will report — skip here.
                continue
            if not entry.subcommands:
                # Script declares no subparsers — any "subcommand" token
                # is actually a positional argument. Skip silently.
                continue
            if not entry.subcommands_confident:
                # The child listing is incomplete, so absence from the index
                # is not evidence of an invented verb. Skip.
                continue
            if inv.subcommand in entry.subcommands:
                continue
            if inv.subcommand in ROUTER_VERBS.get(inv.notation, {}):
                # A router-level verb, intercepted in the script's ``main()``
                # BEFORE argparse subparser dispatch, so it appears in no choice
                # list and the help-derived surface structurally cannot see it —
                # the verb-level twin of the router-CONSUMED flag case above.
                # ``ci barrier`` is the live instance. The model is imported from
                # ``_analyze_manage_invocation`` rather than copied, so the two
                # rules cannot disagree about which verbs exist.
                continue

            findings.append(
                Finding(
                    type=RULE_SUBCOMMAND_UNKNOWN,
                    file=str(inv.file),
                    line=inv.line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_SUBCOMMAND_UNKNOWN,
                    description=(
                        f'Subcommand `{inv.subcommand}` not declared on `{inv.notation}` '
                        f'(known: {sorted(entry.subcommands)})'
                    ),
                    details={
                        'notation': inv.notation,
                        'subcommand': inv.subcommand,
                        'known_subcommands': sorted(entry.subcommands),
                    },
                )
            )
    return [f.to_dict() for f in findings]


# =============================================================================
# Flag validity rule
# =============================================================================


def scan_flag(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Detect invented ``--flag`` tokens against a script's argparse declarations."""
    findings: list[Finding] = []
    for md in _markdown_targets(marketplace_root):
        for inv in _extract_invocations(md):
            if inv.positional_region_is_templated:
                # A usage string, not a call. Judging its flags against whatever
                # scope the unresolved verb slot fell back to is how a correct
                # ``{type} create --summary ...`` usage line got every one of its
                # flags reported as invented.
                continue
            entry = script_index.get(inv.notation)
            if entry is None:
                continue
            allowed: set[str]
            if inv.subcommand is None:
                # ``None`` root flags means the root's own flag surface was
                # never derived — no flag can be judged against it. The
                # ACCEPTANCE surface is read here (derived root flags plus the
                # executor/router universals), never the bare ``root_flags``
                # placement surface.
                root_allowed = entry.root_accept_flags
                if root_allowed is None:
                    continue
                allowed = root_allowed
                scope_label = '<root>'
            else:
                # ``None`` covers both "subcommand not in the index" (the
                # subcommand rule reports that) and "this subcommand's flag
                # surface is unknown". Either way there is no accept-set to
                # judge against, so emit nothing.
                sub_allowed = entry.subcommands.get(inv.subcommand)
                if sub_allowed is None:
                    continue
                allowed = sub_allowed
                scope_label = inv.subcommand

            for match in _FLAG_TOKEN_RE.finditer(_without_quoted_values(inv.all_flag_text)):
                flag = match.group('flag')
                if flag in allowed:
                    continue
                findings.append(
                    Finding(
                        type=RULE_FLAG_UNKNOWN,
                        file=str(inv.file),
                        line=inv.line,
                        severity='error',
                        fixable=False,
                        rule_id=RULE_FLAG_UNKNOWN,
                        description=(
                            f'Flag `--{flag}` not declared on `{inv.notation} {scope_label}` (known: {sorted(allowed)})'
                        ),
                        details={
                            'notation': inv.notation,
                            'subcommand': inv.subcommand,
                            'flag': flag,
                            'known_flags': sorted(allowed),
                        },
                    )
                )
    return [f.to_dict() for f in findings]


# =============================================================================
# Router-flag placement rule
# =============================================================================


def scan_router_flag_placement(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Detect a ROOT-declared flag documented AFTER the verb it does not belong to.

    Argparse gives the subparser everything from the verb onward, so a flag
    declared on the root parser and written after the verb is rejected at parse
    time. The unknown-flag rule cannot see it: that rule judges against the
    widened accept-set (:attr:`_ScriptEntry.subcommands`), and widening can only
    ever ADD flags, so a root flag is in every subcommand's set by construction.

    This rule asks the placement question instead, against the verb's OWN flags:
    a flag in ``root_flags`` and NOT in ``subcommand_own_flags[verb]`` is
    reported, with the fix naming the pre-verb position. Both surfaces must be
    confidently derived — ``None`` on either is "not established", and a
    placement claim over an underived surface would be the false finding the
    widening exists to prevent.

    Only ``inv.rest`` — the text AFTER the verb — is scanned. The router flags
    the extractor found before the verb are on ``inv.leading``, and they are
    exactly the correctly-placed ones this rule must stay silent about.

    ⛔ :data:`UNIVERSAL_FLAGS` is NOT exempted here, and must not be. That set is
    the ACCEPTANCE surface — "does this flag exist?" — and it is deliberately
    coarser than the placement question, because its four members do not share
    one placement behaviour:

    - ``audit-plan-id`` IS consumed by the executor before the target script's
      argparse runs, so it is stripped wherever it was written and no position is
      wrong (``architecture which-module --path P --audit-plan-id X`` is accepted
      with the flag after the verb);
    - ``plan-id`` / ``project-dir`` are, on many scripts, ORDINARY ``add_argument``
      declarations on the ROOT parser — and argparse rejects a root flag written
      after the verb (``architecture which-module --path P --plan-id X`` exits 2
      with ``unrecognized arguments``, and the executor's own note tells the
      author to move it ahead of the verb). Exempting them globally would silence
      the verb-scoped and router-scoped ``--plan-id`` / ``--project-dir``
      recurrence signatures this rule exists to catch.

    The ``flag not in entry.root_flags`` test below is the discriminator, and it
    is PER-SCRIPT rather than per-flag, which is what makes it right: a flag the
    router consumes before argparse appears in no node's ``--help``, so it is
    absent from ``root_flags`` and skipped automatically (the
    ``tools-integration-ci:ci`` ``--project-dir`` shape, consumed by
    ``extract_project_dir`` ahead of dispatch); a flag argparse really declares on
    the root IS in ``root_flags``, and its placement is judged. One test separates
    the two cases correctly on every script without a global list to maintain.
    """
    findings: list[Finding] = []
    for md in _markdown_targets(marketplace_root):
        for inv in _extract_invocations(md):
            if inv.positional_region_is_templated:
                # A usage string, not a call — its flag positions are illustrative.
                continue
            entry = script_index.get(inv.notation)
            if entry is None or inv.subcommand is None or entry.root_flags is None:
                continue
            own = entry.subcommand_own_flags.get(inv.subcommand)
            if own is None:
                continue
            for match in _FLAG_TOKEN_RE.finditer(_without_quoted_values(inv.rest)):
                flag = match.group('flag')
                if flag in own or flag not in entry.root_flags:
                    continue
                findings.append(
                    Finding(
                        type=RULE_ROUTER_FLAG_MISPLACED,
                        file=str(inv.file),
                        line=inv.line,
                        severity='error',
                        fixable=False,
                        rule_id=RULE_ROUTER_FLAG_MISPLACED,
                        description=(
                            f'Flag `--{flag}` is declared on the ROOT parser of '
                            f'`{inv.notation}`, not on `{inv.subcommand}`, so it must be '
                            f'written BEFORE the verb: '
                            f'`{inv.notation} --{flag} VALUE {inv.subcommand} ...`. '
                            'Argparse gives the subparser everything from the verb '
                            'onward, so a root flag written after it is rejected.'
                        ),
                        details={
                            'notation': inv.notation,
                            'subcommand': inv.subcommand,
                            'flag': flag,
                            'root_flags': sorted(entry.root_flags),
                            'subcommand_flags': sorted(own),
                        },
                    )
                )
    return [f.to_dict() for f in findings]


# =============================================================================
# Canonical Forms cross-check
# =============================================================================


def _canonical_forms_path(marketplace_root: Path) -> Path:
    return (
        marketplace_root
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'persona-plan-marshall-agent'
        / 'standards'
        / 'argument-naming.md'
    )


def _parse_canonical_forms(md_path: Path) -> list[tuple[int, str]]:
    """Parse the Canonical Forms table and return ``(line, form)`` rows.

    Each ``form`` is the rightmost column's content (without the surrounding
    backticks). Rows outside the ``## Canonical Forms`` section are ignored.
    Returns an empty list when the file or section is missing.
    """
    try:
        text = md_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    out: list[tuple[int, str]] = []
    in_section = False
    for idx, raw in enumerate(text.splitlines(), start=1):
        if _CANONICAL_FORMS_HEADING.match(raw):
            in_section = True
            continue
        if in_section and raw.startswith('## '):
            # Next section ends Canonical Forms.
            break
        if not in_section:
            continue
        match = _CANONICAL_FORMS_ROW.match(raw)
        if match:
            out.append((idx, match.group('form').strip()))
    return out


# Map a script-shorthand (used in the Canonical Forms table's third column,
# e.g. ``manage-tasks read``) to an executor notation. The Canonical Forms
# table elides the bundle/skill segments — we resolve them by searching the
# script index for a notation whose third segment matches the shorthand.
def _resolve_shorthand_to_notation(
    shorthand: str,
    script_index: dict[str, _ScriptEntry],
) -> str | None:
    """Resolve ``manage-tasks`` to ``plan-marshall:manage-tasks:manage-tasks``.

    Matches when the third segment of a registered notation equals ``shorthand``
    OR when the second segment equals ``shorthand`` (some scripts share name
    with their containing skill, e.g. ``architecture`` under ``manage-architecture``).
    Returns ``None`` if no match (or ambiguous match across bundles).
    """
    matches = [n for n in script_index if n.endswith(f':{shorthand}') or n.split(':')[1] == shorthand]
    if len(matches) == 1:
        return matches[0]
    # If multiple, prefer the one whose third segment equals the shorthand
    # exactly (the most precise match).
    exact = [m for m in matches if m.split(':')[2] == shorthand]
    if len(exact) == 1:
        return exact[0]
    return None


def scan_canonical_forms(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Cross-check every Canonical Forms row against argparse declarations.

    Each row of the form ``{script} {sub} --{flag1} {value1} --{flag2} ...``
    is parsed; the rule reports drift when:
    - the ``{script}`` shorthand cannot be resolved to a registered notation;
    - the ``{sub}`` is not a declared subcommand on that script;
    - any ``--{flag}`` is not declared on the resolved (script, sub).
    """
    findings: list[Finding] = []
    md_path = _canonical_forms_path(marketplace_root)
    if not md_path.is_file():
        return []

    for line, form in _parse_canonical_forms(md_path):
        tokens = form.split()
        if len(tokens) < 2:
            continue
        shorthand, sub, *rest = tokens
        notation = _resolve_shorthand_to_notation(shorthand, script_index)
        if notation is None:
            findings.append(
                Finding(
                    type=RULE_CANONICAL_FORMS_DRIFT,
                    file=str(md_path),
                    line=line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_CANONICAL_FORMS_DRIFT,
                    description=(
                        f'Canonical Forms row references unknown script `{shorthand}` — no registered notation matches'
                    ),
                    details={
                        'shorthand': shorthand,
                        'form': form,
                        'reason': 'shorthand_unresolved',
                    },
                )
            )
            continue

        entry = script_index[notation]
        if sub not in entry.subcommands and entry.subcommands_confident:
            findings.append(
                Finding(
                    type=RULE_CANONICAL_FORMS_DRIFT,
                    file=str(md_path),
                    line=line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_CANONICAL_FORMS_DRIFT,
                    description=(
                        f'Canonical Forms row prescribes `{shorthand} {sub}` '
                        f'but argparse for `{notation}` declares no such subcommand '
                        f'(known: {sorted(entry.subcommands)})'
                    ),
                    details={
                        'shorthand': shorthand,
                        'notation': notation,
                        'subcommand': sub,
                        'known_subcommands': sorted(entry.subcommands),
                        'form': form,
                        'reason': 'subcommand_drift',
                    },
                )
            )
            continue

        allowed = entry.subcommands.get(sub)
        if allowed is None:
            # Either the verb is absent from an unconfident child listing, or
            # its own flag surface was never derived. No accept-set, no
            # flag-drift verdict.
            continue
        for token in rest:
            if not token.startswith('--'):
                continue
            flag = token[2:]
            # Strip trailing ``={value}`` if present.
            if '=' in flag:
                flag = flag.split('=', 1)[0]
            if not flag or flag in allowed:
                continue
            findings.append(
                Finding(
                    type=RULE_CANONICAL_FORMS_DRIFT,
                    file=str(md_path),
                    line=line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_CANONICAL_FORMS_DRIFT,
                    description=(
                        f'Canonical Forms row prescribes `--{flag}` for '
                        f'`{shorthand} {sub}` but argparse declares it as '
                        f'{sorted(allowed)}'
                    ),
                    details={
                        'shorthand': shorthand,
                        'notation': notation,
                        'subcommand': sub,
                        'flag': flag,
                        'known_flags': sorted(allowed),
                        'form': form,
                        'reason': 'flag_drift',
                    },
                )
            )
    return [f.to_dict() for f in findings]


# =============================================================================
# Coverage — what the sweep enumerated, and what it could not decide
# =============================================================================


def _corpus_invocations(marketplace_root: Path) -> list[_Invocation]:
    """Every executor invocation the markdown corpus carries — the population.

    Enumeration deliberately does NOT consult the registry. The corpus is what
    the cluster looks at; the registry is the authority it judges what it saw
    against. Keeping the two apart is what lets an unusable-registry run still
    state how much it was looking at when it could not rule.
    """
    return [
        inv for md in _markdown_targets(marketplace_root) for inv in _extract_invocations(md)
    ]


def _invocation_is_blind_spot(
    inv: _Invocation,
    registered_notations: set[str],
    script_index: dict[str, _ScriptEntry],
) -> bool:
    """Return ``True`` when no verdict could be drawn about ``inv``.

    The branches mirror, one for one, the ``continue`` guards the five ``scan_*``
    rules take, because a blind spot IS a site those rules declined to rule on.
    Two of the declinations are NOT blind spots and are excluded here:

    - A notation absent from ``registered_notations`` is DECIDED — it is reported
      as :data:`RULE_NOTATION_INVALID`. Counting it would file the cluster's
      loudest verdict as a gap.
    - A script that declares no subparsers at all has nothing to check at the
      verb level, and its root flag surface still judges every flag on the line.

    What remains is the genuine residue: a templated positional region that names
    no concrete verb, a registered notation whose ``--help`` surface was dropped
    fail-closed by :func:`build_script_index`, an unconfident verb listing that
    makes absence no evidence, an underived flag surface (``None``) on the scope
    the invocation actually addresses, and a ROUTER verb.

    The router-verb shape is the one a *partial* decision hides. The verb itself
    IS decided — :func:`scan_subcommand` accepts it against :data:`ROUTER_VERBS`
    and moves on — but a router verb is by construction absent from
    ``entry.subcommands``, so :func:`scan_flag` and
    :func:`scan_router_flag_placement` each look the verb up, each get ``None``,
    and neither draws a flag verdict. The fall-through below returns
    ``not subcommands_confident``, which is ``False`` on the confident index a
    router verb reaches, so the withheld FLAG verdict was filed as a decision.
    ``ci barrier`` in ``tools-integration-ci/SKILL.md`` is the live instance.

    The templated case is checked AFTER the registry test, and the order is
    load-bearing. :func:`scan_notation` is deliberately NOT template-guarded — a
    notation is a notation whatever follows it — so a templated line whose
    notation is unregistered still gets a decision and is reported as
    :data:`RULE_NOTATION_INVALID`. Counting it here as well would file the
    cluster's loudest verdict as a gap, the same error the registry branch above
    exists to avoid. What the template guard withholds is only the VERB and FLAG
    verdicts, so only a REGISTERED notation on a templated line is undecided.

    Such a site is counted rather than dropped silently: a usage string IS an
    enumerated invocation the cluster looked at and drew no verb/flag verdict
    about, which is exactly what ``blind_spots`` reports. A skip that did not
    raise the figure would shrink the corpus quietly — the defect class this
    cluster exists to end.
    """
    if inv.notation not in registered_notations:
        return False
    if inv.positional_region_is_templated:
        return True
    entry = script_index.get(inv.notation)
    if entry is None:
        return True
    if inv.subcommand is None:
        return entry.root_flags is None
    if inv.subcommand not in entry.subcommands:
        if inv.subcommand in ROUTER_VERBS.get(inv.notation, {}):
            # Verb decided, flag verdict withheld — see the docstring. Checked
            # BEFORE the confidence fall-through, which would answer ``False``
            # here and report the gap as a ruling.
            return True
        return not entry.subcommands_confident
    return entry.subcommands[inv.subcommand] is None


# =============================================================================
# Public entry point
# =============================================================================


def analyze_argument_naming(marketplace_root: Path) -> list[dict]:
    """Run the full argument-naming rule cluster against ``marketplace_root``.

    Unconditionally active — default-on enforcement rather than a gated
    transitional period, because stale-flag drift recurred in skill workflows.

    Returns a flat list of finding dicts (one per detected drift). Use
    ``rule_id`` to differentiate rule clusters. The signature is held fixed so no
    consumer migrates; a caller that also wants the coverage figures calls
    :func:`analyze_argument_naming_with_population`, which is the SAME derivation
    rather than a second one that could disagree with it.
    """
    findings, _population_size, _blind_spots = analyze_argument_naming_with_population(
        marketplace_root
    )
    return findings


def analyze_argument_naming_with_population(
    marketplace_root: Path,
) -> tuple[list[dict], int, int]:
    """Return ``(findings, population_size, blind_spots)`` from ONE derivation.

    The single implementation of the cluster; :func:`analyze_argument_naming` is
    the projection that drops the two figures. Re-deriving the corpus to get the
    numbers would be a second chance to disagree with the run the findings came
    from — the failure mode ``analyze_canonical_enum_drift_with_population``
    names, and this cluster's subject matter besides.

    ``marketplace_root`` is the MARKETPLACE dir (the parent of ``bundles/``):
    the markdown corpus is derived as ``marketplace_root/'bundles'`` and the
    executor as ``marketplace_root.parent/'.plan'``. Passing the bundles dir
    instead resolves the executor to a path that does not exist, which is
    exactly the substrate absence the guard below reports.

    Both figures are WHOLE-TREE and are never narrowed by the runner's
    ``--paths`` scope: the cluster runs over the whole corpus and only its
    FINDINGS are scope-filtered, so a scope-narrowed population would describe a
    derivation that never happened.
    """
    executor_path = marketplace_root.parent / '.plan' / 'execute-script.py'
    registry = read_notation_registry(executor_path)
    population = _corpus_invocations(marketplace_root)
    if not registry.usable:
        # ⛔ NOT a no-op. Answering an unread registry with ``[]`` gives the
        # caller the same answer as a corpus read in full and found clean, so a
        # gate cannot tell the two apart — and the executor is git-ignored, so
        # the unread case is the DEFAULT in any fresh clone. The absence is
        # reported as its own outcome instead, over a population that IS
        # enumerated: every site is a blind spot, and saying how many there are
        # is the difference between "could not look" and "nothing to see".
        return (
            [
                _substrate_absent_finding(
                    marketplace_root / 'bundles',
                    registry,
                    len(_markdown_targets(marketplace_root)),
                    len(population),
                )
            ],
            len(population),
            len(population),
        )

    registered = set(registry.notations)
    script_index = build_script_index(registered, marketplace_root)

    findings: list[dict] = []
    findings.extend(scan_notation(marketplace_root, registered))
    findings.extend(scan_subcommand(marketplace_root, script_index))
    findings.extend(scan_flag(marketplace_root, script_index))
    findings.extend(scan_router_flag_placement(marketplace_root, script_index))
    findings.extend(scan_canonical_forms(marketplace_root, script_index))
    blind_spots = sum(
        1 for inv in population if _invocation_is_blind_spot(inv, registered, script_index)
    )
    return findings, len(population), blind_spots
