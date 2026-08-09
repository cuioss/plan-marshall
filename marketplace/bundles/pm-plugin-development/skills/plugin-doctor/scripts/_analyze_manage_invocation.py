#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Generalized manage-* invocation analyzer for plugin-doctor.

This module implements two rules:

1. ``manage-invocation-invalid`` (severity: error) — detects token-tree
   mismatches between markdown invocations of in-scope script-bearing
   skills and the scripts' actual argparse declarations. For each
   invocation found in markdown bodies, the analyzer extracts the
   ``(subcommand, sub_verb, flags)`` tuple and validates it against the
   script's canonical argparse surface, emitting one finding per mismatch:

   - Unknown top-level subcommand.
   - Unknown sub-verb under a subcommand that declares sub-subparsers.
   - Unknown flag (``--{flag}``) under the resolved leaf parser.
   - Missing required flag declared by the resolved leaf parser.

   Findings carry ``details.canonical_hint`` with the closest correct form.

2. ``missing-canonical-block`` (severity: warning) — emitted when a
   script-owning SKILL.md (from the auto-derived in-scope set) lacks a
   ``## Canonical invocations`` section. The section is the documented
   source-of-truth contract; missing it leaves authors with no in-skill
   reference when writing prose that invokes the script.

Surface derivation — the shared help-derived accept-set
-------------------------------------------------------
This analyzer no longer owns a surface derivation. The recursive ``--help``
walk, the four parse anchors, the in-process memo, and the content-hash-keyed
on-disk cache under ``.plan/temp/plugin-doctor-help-cache/`` were all lifted
into ``plan-marshall:script-shared``'s ``argparse_surface`` module — the single
derivation of "what does this script accept?" in the tree, shared with the
executor generator so the edit-time rule and the dispatch-time rejection cannot
disagree. See that module's docstring for the mechanism, the asymmetric-error
rule, the fail-closed-on-uncertainty invariant, and the cache design.

Everything below the derivation is unchanged and stays here, because it is
rule-specific rather than surface-specific: the markdown invocation extraction,
the router-verb model, the universal executor-injected flag allowlist, the
ancestor flag union, and the finding shapes.

Two capabilities the consolidation adds to this rule for free: alias awareness
(a documented alias spelling is in the accepted set because argparse renders it
flat in the choice list) and coverage of parsers assembled in an imported
module (the ``tools-integration-ci:ci`` shape, whose parser is built in
``ci_base.py``).

Public API
----------
- ``discover_in_scope_scripts(marketplace_root)``: auto-derive the in-scope
  ``_ScriptDescriptor`` set from the bundle tree.
- ``derive_script_tree(notation, executor)``: cached ``--help`` derivation
  of one script's canonical surface.
- ``build_script_index(marketplace_root)``: notation -> ``_ScriptTree``
  index for every in-scope script (empty when no executor is reachable).
- ``analyze_manage_invocation_markdown(content, file_path, script_index)``:
  scan a single markdown body for invocation mismatches.
- ``scan_skill_for_manage_invocation(skill_dir, script_index)``: per-skill
  scanner used by ``_doctor_analysis.analyze_component``.
- ``scan_manage_invocation(marketplace_root)``: marketplace-wide scanner
  combining both rules.
- ``check_missing_canonical_blocks(marketplace_root)``: standalone helper
  that emits ``missing-canonical-block`` findings for in-scope SKILL.md
  files.
- ``RULE_MANAGE_INVOCATION_INVALID`` / ``RULE_MISSING_CANONICAL_BLOCK``:
  the canonical rule keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor
from argparse_surface import (
    ParserNode,
    ScriptSurface,
    build_surface_index,
    content_hash,
    derive_surface,
    parse_choice_list,
    parse_help_node,
    parse_required_flags,
    resolve_executor,
    run_help,
    script_path_for_notation,
    split_help_sections,
    strip_ansi,
    strip_grouping_constructs,
)

# =============================================================================
# Rule IDs
# =============================================================================

RULE_MANAGE_INVOCATION_INVALID = 'manage-invocation-invalid'
RULE_MISSING_CANONICAL_BLOCK = 'missing-canonical-block'

RULE_DESCRIPTORS = [
    RuleDescriptor(
        rule_id=RULE_MANAGE_INVOCATION_INVALID,
        severity='error',
        category='structural',
        scope='corpus-relational',
    ),
    RuleDescriptor(
        rule_id=RULE_MISSING_CANONICAL_BLOCK,
        severity='warning',
        category='style',
        scope='corpus-relational',
    ),
]

# Long flags that are ALWAYS accepted on any leaf, regardless of where (or
# whether) they appear in the probed ``--help`` surface. Two distinct origins:
#
#   - ``audit-plan-id`` is injected and consumed by the executor wrapper
#     (``.plan/execute-script.py``) BEFORE the target script's argparse runs, so
#     it never appears in any node's ``--help`` even though every doc call that
#     audits a plan passes it. Flagging it is always a false positive.
#   - ``project-dir`` / ``plan-id`` are declared on the ROOT parser of many
#     scripts (or injected by the executor for worktree binding) and are valid on
#     every subcommand by argparse's parent-flag propagation, but a script may
#     render them only in the root ``--help`` (not in a subcommand's options
#     block). The ancestor-union below already accepts root-declared flags; the
#     allowlist is the belt-and-suspenders guarantee for the executor-injected
#     case where the flag is in NO node's surface.
#
# This allowlist is read-side only — it never mutates the cached surface tree.
_UNIVERSAL_FLAG_ALLOWLIST: frozenset[str] = frozenset(
    {'audit-plan-id', 'project-dir', 'plan-id'}
)

# Router-level verbs handled by a script's ``main()`` BEFORE argparse subparser
# dispatch, so they never appear in the script's ``--help`` choices group and
# the ``--help``-derived surface cannot see them. These are a legitimate pattern
# (a provider-agnostic verb intercepted ahead of provider routing so it works
# with no provider configured), NOT a documentation defect — validating them
# against the introspected subcommand set is a false positive. Keyed by
# ``bundle:skill:script`` notation → a ``{verb_name: _RouterVerb}`` map that
# MODELS each router verb's own flag surface (long flags + required subset).
#
# The verb name being registered admits it as a valid first positional (the
# ``--help``-derived surface cannot see it), but its flags ARE validated against
# the modeled surface below rather than accepted wholesale — a misspelled or
# unknown flag on a router verb is a real defect and must be flagged, exactly as
# for a ``--help``-derived subcommand. The model is hand-maintained because the
# verb's argparse lives in a helper module the standard child-probe never reaches.
#
# ``ci barrier`` is the provider-agnostic finalize-wait barrier coordinator —
# intercepted at the top of ``tools-integration-ci/scripts/ci.py::main()`` before
# provider dispatch, implemented in the ``_ci_barrier.py`` helper. Its argparse
# (``run_barrier_cli``) declares ``--settled-head`` (required) and ``--signal``
# (required, repeatable).


@dataclass(frozen=True)
class _RouterVerb:
    """The modeled flag surface of one router-level verb.

    ``flags`` is the verb's full long-flag surface (without ``--``);
    ``required_flags`` is the subset argparse declares ``required=True``. These
    are validated with the SAME unknown-flag / missing-required machinery as a
    ``--help``-derived leaf, so a misspelled flag on a router verb is caught
    rather than accepted wholesale.
    """

    flags: frozenset[str] = frozenset()
    required_flags: frozenset[str] = frozenset()


_ROUTER_VERBS: dict[str, dict[str, _RouterVerb]] = {
    'plan-marshall:tools-integration-ci:ci': {
        'barrier': _RouterVerb(
            flags=frozenset({'settled-head', 'signal'}),
            required_flags=frozenset({'settled-head', 'signal'}),
        ),
    },
}

# =============================================================================
# In-scope derivation
# =============================================================================

# Skill directory names that are NEVER in-scope even though they may carry a
# ``scripts/`` directory with an argparse entry point. The exclusions cover:
#   - shared helper modules consumed only via PYTHONPATH,
#   - file-ops / input-validation base modules,
#   - reference / runtime skills with no user-facing CLI contract,
#   - ``manage-findings`` (covered by its own dedicated analyzer
#     ``_analyze_manage_findings_invocation.py``).
_EXCLUDED_SKILLS: frozenset[str] = frozenset(
    {
        'script-shared',
        'tools-file-ops',
        'tools-input-validation',
        'ref-toon-format',
        'platform-runtime',
        'manage-findings',
    }
)

# A script is considered to publish an argparse CLI surface when its source
# references ``ArgumentParser`` (or the ``argparse`` module). Scripts that do
# not are pure libraries and are skipped — there is nothing to invoke.
_ARGPARSE_MARKERS: tuple[str, ...] = ('ArgumentParser', 'argparse')


@dataclass(frozen=True)
class _ScriptDescriptor:
    """Identifies one in-scope script-bearing skill and its on-disk location.

    ``notation`` is the ``bundle:skill:script`` triple keyed by the script
    file *stem* (not the skill name), so a skill whose entry-point filename
    differs from the skill name resolves correctly. ``script_relpath`` and
    ``skill_dir_relpath`` are relative to ``{marketplace_root}/marketplace``
    (i.e. they begin with ``bundles/``).
    """

    notation: str
    script_relpath: str  # e.g. 'bundles/.../scripts/foo.py'
    skill_dir_relpath: str  # the owning skill directory


def _bundles_dir(marketplace_root: Path) -> Path | None:
    """Resolve the ``bundles`` directory under either supported layout.

    Accepts both ``{root}/marketplace/bundles`` (the canonical repo layout)
    and ``{root}/bundles`` (an installation that places ``bundles`` at the
    root). Returns ``None`` when neither exists.
    """
    candidate = marketplace_root / 'marketplace' / 'bundles'
    if candidate.is_dir():
        return candidate
    candidate = marketplace_root / 'bundles'
    if candidate.is_dir():
        return candidate
    return None


def _script_declares_argparse(script_path: Path) -> bool:
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return False
    return any(marker in source for marker in _ARGPARSE_MARKERS)


def discover_in_scope_scripts(
    marketplace_root: Path,
) -> tuple[_ScriptDescriptor, ...]:
    """Auto-derive the in-scope script set from the bundle tree.

    A script is in-scope when ALL of the following hold:

    - it is a top-level ``*.py`` file under a skill's ``scripts/`` directory,
    - its filename does not start with ``_`` (underscore-prefixed modules are
      helpers, not entry points),
    - it declares an argparse CLI surface,
    - its owning skill is not in ``_EXCLUDED_SKILLS``.

    The notation is keyed off the script file *stem*, so a skill whose
    entry-point filename differs from the skill name (e.g. ``plan-doctor`` ->
    ``plan_doctor.py``) is keyed as ``plan-marshall:plan-doctor:plan_doctor``.

    Results are sorted by notation for deterministic output. Returns an empty
    tuple when no ``bundles`` directory exists.
    """
    bundles_dir = _bundles_dir(marketplace_root)
    if bundles_dir is None:
        return ()

    descriptors: list[_ScriptDescriptor] = []
    for bundle_dir in sorted(p for p in bundles_dir.iterdir() if p.is_dir()):
        bundle = bundle_dir.name
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill = skill_dir.name
            if skill in _EXCLUDED_SKILLS:
                continue
            scripts_dir = skill_dir / 'scripts'
            if not scripts_dir.is_dir():
                continue
            for script_file in sorted(scripts_dir.glob('*.py')):
                stem = script_file.stem
                if stem.startswith('_'):
                    continue
                if not _script_declares_argparse(script_file):
                    continue
                notation = f'{bundle}:{skill}:{stem}'
                script_relpath = f'bundles/{bundle}/skills/{skill}/scripts/{script_file.name}'
                skill_dir_relpath = f'bundles/{bundle}/skills/{skill}'
                descriptors.append(
                    _ScriptDescriptor(
                        notation=notation,
                        script_relpath=script_relpath,
                        skill_dir_relpath=skill_dir_relpath,
                    )
                )

    descriptors.sort(key=lambda d: d.notation)
    return tuple(descriptors)


# =============================================================================
# Canonical-surface data model
# =============================================================================


# The surface model is the shared one. These aliases keep this module's
# historical private names working for its own body and its tests; they are
# the SAME classes, not parallel definitions.
_LeafParser = ParserNode
_ScriptTree = ScriptSurface


# =============================================================================
# ``--help`` parsing — re-exported from the shared derivation
# =============================================================================

# The pure parsers live in ``argparse_surface`` and are re-bound here under the
# names this module's tests already use. Same functions, one implementation.
_split_help_sections = split_help_sections
_parse_subcommand_choices = parse_choice_list
_parse_leaf_flags = parse_help_node
_parse_required_flags = parse_required_flags
_strip_grouping_constructs = strip_grouping_constructs


# =============================================================================
# Live ``--help`` probing with caching
# =============================================================================

# The probe, the recursion, the in-process memo, and the content-hash-keyed
# on-disk cache all live in ``argparse_surface`` now. These bindings keep the
# names this module's own body, its tests, and ``doctor-marketplace.py`` import.
_resolve_executor = resolve_executor
_script_path_for_notation = script_path_for_notation
_content_hash = content_hash
_run_help = run_help
_strip_ansi = strip_ansi


def derive_script_tree(notation: str, executor: Path) -> _ScriptTree | None:
    """Cached ``--help`` derivation of one script's canonical surface.

    Thin adapter over :func:`argparse_surface.derive_surface`. The shared
    function returns an explicit ``NotDerivable`` marker naming WHY it could not
    derive a confident surface; this rule needs only the binary answer, so the
    marker is mapped to ``None``. Callers treat ``None`` as "no surface" and
    skip validation for that notation — never as a false positive.
    """
    surface = derive_surface(notation, executor)
    return surface if isinstance(surface, ScriptSurface) else None


def build_script_index(marketplace_root: Path) -> dict[str, _ScriptTree]:
    """Build a notation -> canonical-surface index for every in-scope script.

    Thin adapter over :func:`argparse_surface.build_surface_index`. When no
    executor is reachable the index is empty — the surface cannot be probed, so
    no findings are emitted (no false positives). Notations whose surface is not
    derivable are dropped for the same reason: a missing entry means "no ground
    truth here", which every consumer below already treats as "emit nothing".
    """
    executor = _resolve_executor(marketplace_root)
    if executor is None:
        return {}
    descriptors = discover_in_scope_scripts(marketplace_root)
    if not descriptors:
        return {}
    surfaces = build_surface_index([d.notation for d in descriptors], executor)
    return {
        notation: surface
        for notation, surface in surfaces.items()
        if isinstance(surface, ScriptSurface)
    }


# =============================================================================
# Markdown invocation extraction
# =============================================================================

# Match any executor invocation whose triple aligns with one of the in-scope
# script notations. Captures the bundle/skill/script segments plus the
# trailing portion so the consumer can tokenize positional / flag args.
_NOTATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<bundle>[A-Za-z0-9_\-]+):'
    r'(?P<skill>[A-Za-z0-9_\-]+):'
    r'(?P<script>[A-Za-z0-9_\-]+)'
    r'(?P<rest>.*)$'
)

# Positional token extractor — strips a single leading whitespace run and
# matches the next alphanumeric-or-hyphen identifier. Stops at flag tokens.
_NEXT_POSITIONAL_RE = re.compile(r'\s+(?P<tok>[A-Za-z][A-Za-z0-9_\-]*)')

# Long-flag token extractor. Anchored to a non-identifier boundary to avoid
# matching numeric ranges or matches inside identifiers.
_FLAG_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9_\-]*)\b')


def _strip_quoted_substrings(text: str) -> str:
    """Remove single- and double-quoted substrings from ``text``.

    Shell-style quoting is honored: characters inside matched quotes are
    replaced with spaces so the resulting string preserves column offsets
    while suppressing any ``--flag``-like content that lives inside a quoted
    argument value (e.g. ``--message "release: --not-a-flag"``). Backslash
    escapes inside quotes are respected. Unterminated quotes consume the
    remainder of the line.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ('"', "'"):
            quote = ch
            out.append(' ')  # preserve column for the opening quote
            i += 1
            while i < n and text[i] != quote:
                if text[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append(' ')
                i += 1
            if i < n:
                out.append(' ')  # closing quote
                i += 1
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def _join_continuation_lines(content: str) -> list[tuple[int, str]]:
    """Collapse backslash-continued lines into logical lines.

    Returns a list of ``(start_line_no, joined_text)`` tuples preserving the
    original 1-based line number where each logical line begins. A trailing
    backslash (optionally followed by whitespace) at the end of a physical
    line splices the next line onto the current logical line with a single
    space separator.
    """
    physical = content.splitlines()
    result: list[tuple[int, str]] = []
    i = 0
    while i < len(physical):
        start_line_no = i + 1
        line = physical[i]
        stripped = line.rstrip()
        while stripped.endswith('\\'):
            line = stripped[:-1]
            i += 1
            if i >= len(physical):
                break
            line = line + ' ' + physical[i].lstrip()
            stripped = line.rstrip()
        result.append((start_line_no, line))
        i += 1
    return result


# Long-flag token at the current scan position: leading whitespace run, then
# ``--name``. Used to skip a leading run of top-level routing/global flags that
# argparse consumes BEFORE the subcommand positional (``--project-dir X``,
# ``--plan-id Y``, ``--audit-plan-id Z``).
_LEADING_FLAG_RE = re.compile(r'\s+--[A-Za-z][A-Za-z0-9_\-]*')

# Any non-flag, non-whitespace value token at the current scan position: a
# leading whitespace run, then a run of non-whitespace NOT beginning with ``-``.
# Matches identifiers AND non-identifier values a routing flag may carry —
# ``{WORKTREE}`` templates, ``/abs/paths``, ``key=value`` — so the value token
# of ``--project-dir {WORKTREE}`` is consumed wholesale rather than leaving the
# template stranded as a stray positional.
_VALUE_TOKEN_RE = re.compile(r'\s+(?P<val>[^\s\-][^\s]*)')


def _skip_leading_routing_flags(rest: str) -> int:
    """Return the scan offset past any leading ``--flag value`` run in ``rest``.

    A top-level routing/global flag (``--project-dir``, ``--plan-id``,
    ``--audit-plan-id``) is consumed by the executor/router argparse layer
    BEFORE the subcommand positional. argparse always requires the subcommand —
    the first bare positional — to follow any top-level optionals, so a leading
    flag token can never BE the subcommand.

    The skip rule (per the executor router idiom, whose global flags all take a
    value): while the next token is a ``--flag``, consume it AND its one
    following value token, unless that following token is itself a ``--flag``
    (the flag was a bare switch) or there is no further token. Stop at the first
    bare positional token — that is the subcommand.

    Returning the post-skip offset lets ``_extract_positional_tokens`` begin
    where the real subcommand chain starts, so an invocation that places a
    routing flag before the subcommand (``ci --project-dir X pr prepare-comment``)
    resolves the same ``pr prepare-comment`` chain as the flag-free form. A
    genuinely wrong sub-verb after the routing flag still fails resolution and
    is reported — the routing flag is skipped, the real subcommand is THEN
    validated.
    """
    pos = 0
    while True:
        flag_match = _LEADING_FLAG_RE.match(rest, pos)
        if not flag_match:
            break
        pos = flag_match.end()
        # Consume the flag's value token unless the next token is another flag
        # (this flag was a bare switch) or the line ended.
        if _LEADING_FLAG_RE.match(rest, pos) is not None:
            continue
        value_match = _VALUE_TOKEN_RE.match(rest, pos)
        if value_match is None:
            break
        pos = value_match.end()
    return pos


def _extract_positional_tokens(rest: str, max_positionals: int = 8) -> list[str]:
    """Extract the leading run of positional tokens from ``rest``.

    A leading run of top-level routing/global flags (``--project-dir X``,
    ``--plan-id Y``) is skipped first so the FIRST extracted positional is the
    real subcommand even when a routing flag precedes it. See
    ``_skip_leading_routing_flags``.

    Stops at the first flag token (``-`` prefix) AFTER the subcommand chain
    starts, or end-of-line. The default cap is generous (8) because argparse
    subparser chains can be three or more positionals deep
    (``plan phase-5-execute set``); the tree walk consumes only as many as
    resolve along registered children and treats the rest as positional
    arguments, so over-collecting here is harmless.
    """
    tokens: list[str] = []
    pos = _skip_leading_routing_flags(rest)
    while pos < len(rest) and len(tokens) < max_positionals:
        match = _NEXT_POSITIONAL_RE.match(rest, pos)
        if not match:
            break
        tokens.append(match.group('tok'))
        pos = match.end()
        peek = rest[pos:].lstrip()
        if peek.startswith('-'):
            break
    return tokens


def _extract_flag_tokens(rest: str) -> list[str]:
    """Extract every long-flag token (without ``--``) from ``rest``.

    Quoted substrings are stripped first so flag-like text inside string
    argument values does not produce false positives.
    """
    return [
        m.group('flag')
        for m in _FLAG_TOKEN_RE.finditer(_strip_quoted_substrings(rest))
    ]


# First flag token on a line: whitespace immediately followed by ``-``. The
# positional region is everything before it (or the whole line when no flag).
_FIRST_FLAG_RE = re.compile(r'\s-')

# Usage-template / placeholder syntax that marks a line as a NON-concrete
# invocation: ``{plan_id}`` / ``<subcommand>`` placeholders, argparse usage
# brackets and alternation (``[--flag X | --plan-id Y]``), and the literal
# ``...`` ellipsis ("and the rest of the args"). A concrete consumer call —
# the only thing the manage-invocation rule should validate — never carries
# these in its subcommand/sub-verb region; they appear only in templated
# examples and in the ``## Canonical invocations`` usage strings, which are
# the spec rather than a call to validate.
_TEMPLATE_SYNTAX_RE = re.compile(r'[{}<>\[\]|]|\.\.\.')


def _positional_region_is_templated(rest: str) -> bool:
    """True when the positional region uses usage-template / placeholder syntax.

    The positional region is the slice of ``rest`` before the first flag token.
    Template syntax there means the subcommand / sub-verb chain is not a
    concrete call and cannot be resolved against the canonical tree:

    - ``{...}`` / ``<...>`` placeholders — ``manage-config plan {phase} get``,
      ``extension_discovery {command} {args}``;
    - usage brackets / alternation — ``profiles [--project-dir | --plan-id] list``
      (the leading optional-global-flag group of a ``## Canonical invocations``
      usage string);
    - the literal ``...`` ellipsis — ``manage-adr ...`` in enforcement prose.

    Validating any of these produces false ``subcommand_unknown`` /
    ``sub_verb_unknown`` / ``required_flag_missing`` findings, so the caller
    skips the invocation entirely. Template syntax inside flag *values* (after
    the first flag, e.g. ``--set k={worktree_path}``) is deliberately NOT
    covered — those invocations still get full subcommand and flag validation.
    """
    flag_match = _FIRST_FLAG_RE.search(rest)
    region = rest[: flag_match.start()] if flag_match else rest
    return bool(_TEMPLATE_SYNTAX_RE.search(region))


# =============================================================================
# Finding construction helpers
# =============================================================================


def _build_finding(
    *,
    rule_id: str,
    file_path: str,
    line: int,
    severity: str,
    description: str,
    details: dict,
) -> dict:
    return Finding(
        type=rule_id,
        file=file_path,
        line=line,
        severity=severity,
        fixable=False,
        rule_id=rule_id,
        description=description,
        details=details,
    ).to_dict()


def _canonical_hint_for_subcommand(
    notation: str,
    known_subcommands: set[str],
) -> str:
    return (
        f'Use a registered top-level subcommand for `{notation}`: '
        f'{sorted(known_subcommands)}'
    )


def _canonical_hint_for_sub_verb(
    notation: str,
    subcommand: str,
    known_sub_verbs: set[str],
) -> str:
    return (
        f'Use a registered sub-verb under `{notation} {subcommand}`: '
        f'{sorted(known_sub_verbs)}'
    )


def _canonical_hint_for_flag(
    notation: str,
    subcommand: str | None,
    sub_verb: str | None,
    known_flags: set[str],
) -> str:
    chain_parts = [notation]
    if subcommand:
        chain_parts.append(subcommand)
    if sub_verb:
        chain_parts.append(sub_verb)
    chain = ' '.join(chain_parts)
    return f'Use a declared flag for `{chain}`: {sorted(known_flags)}'


def _canonical_hint_for_missing_required(
    notation: str,
    subcommand: str | None,
    sub_verb: str | None,
    missing: set[str],
) -> str:
    chain_parts = [notation]
    if subcommand:
        chain_parts.append(subcommand)
    if sub_verb:
        chain_parts.append(sub_verb)
    chain = ' '.join(chain_parts)
    return f'Add missing required flag(s) for `{chain}`: {sorted(missing)}'


# =============================================================================
# Per-line invocation analysis
# =============================================================================


class ScriptIndex(Protocol):
    """Read-only notation -> ``_ScriptTree`` lookup surface.

    Both the eager ``dict[str, _ScriptTree]`` returned by
    ``build_script_index`` and any lazy index satisfy this protocol
    structurally, so every consumer can accept either implementation.
    """

    def __contains__(self, notation: object) -> bool: ...

    def get(self, notation: str) -> _ScriptTree | None: ...


def _node_at_chain(tree: _ScriptTree, chain: list[str]) -> _LeafParser | None:
    """Resolve the parser node reached by following ``chain`` from the root."""
    node = tree.root
    for token in chain:
        child = node.children.get(token)
        if child is None:
            return None
        node = child
    return node


def _ancestor_union_flags(tree: _ScriptTree, chain: list[str]) -> set[str]:
    """Union the flag surfaces of every parser node from the root to the leaf.

    A flag is valid at the resolved leaf if it is declared on the leaf OR on
    ANY ancestor along the resolution path — the root parser included. argparse
    propagates flags two ways the per-leaf ``--help`` surface does not always
    re-render:

    - ``parents=[common_parser]`` copies a flag's action into the child parser;
      most argparse versions DO re-render these in the child's ``--help``, but a
      flag added to the ROOT parser before subparser dispatch (e.g. a top-level
      ``--plan-id`` / ``--project-dir``) is honored on every subcommand yet
      rendered ONLY in the root ``--help`` options block.

    The per-leaf validation therefore mis-flags root-declared and parent-only
    flags as unknown — the 106-false-positive failure this union fixes. Walking
    the resolved chain and unioning each prefix node's ``flags`` set restores
    argparse's actual acceptance semantics. The union is read-side only — the
    cached tree is never mutated.
    """
    union: set[str] = set(tree.root.flags)
    node = tree.root
    for token in chain:
        child = node.children.get(token)
        if child is None:
            break
        union |= child.flags
        node = child
    return union


def _validate_router_verb(
    *,
    notation: str,
    verb: str,
    spec: _RouterVerb,
    declared_flags: list[str],
    file_path: str,
    line: int,
) -> list[dict]:
    """Validate a router verb's flags against its modeled surface.

    Router verbs are intercepted before argparse dispatch, so their flag surface
    is not in any ``--help`` node — it is modeled in ``_ROUTER_VERBS``. This
    reuses the SAME unknown-flag / missing-required finding shapes as the
    ``--help``-derived leaf path, plus the universal executor/router-injected
    allowlist (``--plan-id`` / ``--project-dir`` / ``--audit-plan-id`` are
    consumed by the router before the verb, so they are always acceptable).
    The router verb occupies the ``subcommand`` slot in finding details.
    """
    findings: list[dict] = []
    known_flags = set(spec.flags) | _UNIVERSAL_FLAG_ALLOWLIST
    used_flags = set(declared_flags)

    for flag in sorted(used_flags - known_flags):
        findings.append(
            _build_finding(
                rule_id=RULE_MANAGE_INVOCATION_INVALID,
                file_path=file_path,
                line=line,
                severity='error',
                description=(
                    f'`{notation} {verb}` invocation uses unregistered flag '
                    f'`--{flag}` (registered: {sorted(known_flags)})'
                ),
                details={
                    'notation': notation,
                    'subcommand': verb,
                    'sub_verb': None,
                    'flag': flag,
                    'reason': 'flag_unknown',
                    'canonical_hint': _canonical_hint_for_flag(
                        notation, verb, None, known_flags
                    ),
                    'known_flags': sorted(known_flags),
                },
            )
        )

    missing_required = sorted(spec.required_flags - used_flags)
    if missing_required:
        findings.append(
            _build_finding(
                rule_id=RULE_MANAGE_INVOCATION_INVALID,
                file_path=file_path,
                line=line,
                severity='error',
                description=(
                    f'`{notation} {verb}` invocation is missing required '
                    f'flag(s) {missing_required} (required: '
                    f'{sorted(spec.required_flags)})'
                ),
                details={
                    'notation': notation,
                    'subcommand': verb,
                    'sub_verb': None,
                    'missing': missing_required,
                    'reason': 'required_flag_missing',
                    'canonical_hint': _canonical_hint_for_missing_required(
                        notation, verb, None, set(missing_required)
                    ),
                    'required_flags': sorted(spec.required_flags),
                },
            )
        )

    return findings


def _analyze_one_invocation(
    *,
    notation: str,
    rest: str,
    file_path: str,
    line: int,
    script_index: ScriptIndex,
) -> list[dict]:
    """Validate one ``rest`` payload against the script's canonical surface.

    Returns a list of findings (possibly empty). A single line may trip
    multiple failure modes (e.g. unknown flag AND missing required); each is
    reported independently. An unknown subcommand / sub-verb short-circuits
    flag validation on that line.
    """
    findings: list[dict] = []
    tree = script_index.get(notation)
    if tree is None:
        return findings

    # A templated positional region (a ``{...}`` / ``<...>`` placeholder where a
    # subcommand or sub-verb would be) cannot be resolved against the canonical
    # tree — the placeholder stands for a real value the author left unbound.
    # Skip the whole invocation rather than emit spurious subcommand/sub-verb/
    # required-flag findings against an unresolvable chain.
    if _positional_region_is_templated(rest):
        return findings

    positionals = _extract_positional_tokens(rest)
    declared_flags = _extract_flag_tokens(rest)

    # Router-level verbs (handled in main() before argparse dispatch) are valid
    # even though the ``--help``-derived surface cannot see them. When the first
    # positional is a registered router verb for this notation, admit the verb
    # itself but STILL validate its flags against the modeled surface — a
    # misspelled or unknown flag on a router verb is a real defect, not something
    # to accept wholesale.
    router_verbs = _ROUTER_VERBS.get(notation, {})
    if positionals and positionals[0] in router_verbs:
        return _validate_router_verb(
            notation=notation,
            verb=positionals[0],
            spec=router_verbs[positionals[0]],
            declared_flags=declared_flags,
            file_path=file_path,
            line=line,
        )

    # When the script declares no subcommands, positional tokens after the
    # notation are not subcommands — validate flags against the root parser.
    if positionals and not tree.known_subcommands():
        positionals = []

    node, unknown_token, chain = tree.resolve_path(positionals)

    # ``subcommand`` / ``sub_verb`` are the first two chain elements — retained
    # in finding details for the documented two-level payload shape.
    subcommand: str | None = chain[0] if chain else None
    sub_verb: str | None = chain[1] if len(chain) >= 2 else None

    if unknown_token is not None:
        # A positional named an unregistered child at some level. ``chain`` is
        # the resolved prefix; ``unknown_token`` is the first token that failed.
        # Depth 0 (no resolved prefix) → unknown top-level subcommand; deeper
        # → unknown sub-verb under the resolved parent.
        if not chain:
            findings.append(
                _build_finding(
                    rule_id=RULE_MANAGE_INVOCATION_INVALID,
                    file_path=file_path,
                    line=line,
                    severity='error',
                    description=(
                        f'`{notation}` invocation uses unregistered '
                        f'subcommand `{unknown_token}` (registered: '
                        f'{sorted(tree.known_subcommands())})'
                    ),
                    details={
                        'notation': notation,
                        'subcommand': unknown_token,
                        'reason': 'subcommand_unknown',
                        'canonical_hint': _canonical_hint_for_subcommand(
                            notation, tree.known_subcommands()
                        ),
                        'known_subcommands': sorted(tree.known_subcommands()),
                    },
                )
            )
        else:
            parent = _node_at_chain(tree, chain)
            known_children = set(parent.children.keys()) if parent else set()
            parent_chain = ' '.join(chain)
            findings.append(
                _build_finding(
                    rule_id=RULE_MANAGE_INVOCATION_INVALID,
                    file_path=file_path,
                    line=line,
                    severity='error',
                    description=(
                        f'`{notation} {parent_chain}` invocation uses '
                        f'unregistered sub-verb `{unknown_token}` '
                        f'(registered: {sorted(known_children)})'
                    ),
                    details={
                        'notation': notation,
                        'subcommand': subcommand,
                        'sub_verb': unknown_token if sub_verb is None else sub_verb,
                        'reason': 'sub_verb_unknown',
                        'canonical_hint': _canonical_hint_for_sub_verb(
                            notation, parent_chain, known_children
                        ),
                        'known_sub_verbs': sorted(known_children),
                    },
                )
            )
        return findings

    if node is None:
        return findings

    # A resolved node that still has children means the positional chain stopped
    # short of a leaf — the next sub-verb is missing. This is the canonical
    # "``qgate`` with no sub-verb" case the tests assert.
    if node.has_children():
        known_children = set(node.children.keys())
        parent_chain = ' '.join(chain) if chain else notation
        findings.append(
            _build_finding(
                rule_id=RULE_MANAGE_INVOCATION_INVALID,
                file_path=file_path,
                line=line,
                severity='error',
                description=(
                    f'`{notation} {parent_chain}` invocation uses '
                    f'unregistered sub-verb `<missing>` '
                    f'(registered: {sorted(known_children)})'
                ),
                details={
                    'notation': notation,
                    'subcommand': subcommand,
                    'sub_verb': None,
                    'reason': 'sub_verb_unknown',
                    'canonical_hint': _canonical_hint_for_sub_verb(
                        notation, parent_chain, known_children
                    ),
                    'known_sub_verbs': sorted(known_children),
                },
            )
        )
        return findings

    leaf = node
    # A flag is KNOWN if it is declared on the resolved leaf, on ANY ancestor
    # along the resolution chain (root parser included — argparse propagates
    # parent / root flags to every subcommand), or in the universal allowlist
    # (executor-injected flags that appear in no node's ``--help``). Validating
    # against the leaf's own ``flags`` set alone mis-flags parent-inherited and
    # executor-injected flags as unknown — the 106-false-positive failure this
    # union + allowlist fixes. ``required_flags`` (below) stays leaf-only:
    # missing-required detection MUST NOT inherit an ancestor's required flags.
    known_flags = (
        _ancestor_union_flags(tree, chain) | leaf.flags | _UNIVERSAL_FLAG_ALLOWLIST
    )
    used_flags = set(declared_flags)

    unknown_flags = sorted(used_flags - known_flags)
    for flag in unknown_flags:
        findings.append(
            _build_finding(
                rule_id=RULE_MANAGE_INVOCATION_INVALID,
                file_path=file_path,
                line=line,
                severity='error',
                description=(
                    f'`{notation}` invocation uses unregistered flag '
                    f'`--{flag}` (registered: {sorted(known_flags)})'
                ),
                details={
                    'notation': notation,
                    'subcommand': subcommand,
                    'sub_verb': sub_verb,
                    'flag': flag,
                    'reason': 'flag_unknown',
                    'canonical_hint': _canonical_hint_for_flag(
                        notation, subcommand, sub_verb, known_flags
                    ),
                    'known_flags': sorted(known_flags),
                },
            )
        )

    missing_required = sorted(leaf.required_flags - used_flags)
    if missing_required:
        findings.append(
            _build_finding(
                rule_id=RULE_MANAGE_INVOCATION_INVALID,
                file_path=file_path,
                line=line,
                severity='error',
                description=(
                    f'`{notation}` invocation is missing required flag(s) '
                    f'{missing_required} (required: '
                    f'{sorted(leaf.required_flags)})'
                ),
                details={
                    'notation': notation,
                    'subcommand': subcommand,
                    'sub_verb': sub_verb,
                    'missing': missing_required,
                    'reason': 'required_flag_missing',
                    'canonical_hint': _canonical_hint_for_missing_required(
                        notation, subcommand, sub_verb, set(missing_required)
                    ),
                    'required_flags': sorted(leaf.required_flags),
                },
            )
        )

    return findings


# =============================================================================
# Public entry points
# =============================================================================


def analyze_manage_invocation_markdown(
    content: str,
    file_path: str,
    script_index: ScriptIndex,
) -> list[dict]:
    """Scan a markdown body and emit findings for manage-* invocation mismatches.

    The scan operates on *logical* lines — physical lines are first joined
    across backslash continuations so flags written on subsequent lines are
    honored as part of the same invocation. Each notation occurrence is
    validated independently against ``script_index``. Unknown notations (not
    in the index) are skipped. The function is total: an empty body or a body
    with no invocations returns an empty list.
    """
    findings: list[dict] = []
    for line_no, joined in _join_continuation_lines(content):
        match = _NOTATION_RE.search(joined)
        if not match:
            continue
        bundle = match.group('bundle')
        skill = match.group('skill')
        script = match.group('script')
        rest = match.group('rest') or ''
        notation = f'{bundle}:{skill}:{script}'
        if notation not in script_index:
            continue
        findings.extend(
            _analyze_one_invocation(
                notation=notation,
                rest=rest,
                file_path=file_path,
                line=line_no,
                script_index=script_index,
            )
        )
    return findings


def _skill_md_targets(skill_dir: Path) -> list[Path]:
    """Enumerate the markdown files this analyzer scans within one skill dir."""
    targets: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)
    for sub in ('standards', 'references', 'workflow', 'recipes'):
        sub_dir = skill_dir / sub
        if sub_dir.is_dir():
            targets.extend(sorted(sub_dir.glob('*.md')))
    return targets


def scan_skill_for_manage_invocation(
    skill_dir: Path,
    script_index: ScriptIndex,
) -> list[dict]:
    """Per-skill scanner — runs the markdown analyzer over one skill dir."""
    findings: list[dict] = []
    if not skill_dir.is_dir():
        return findings
    for md_file in _skill_md_targets(skill_dir):
        try:
            content = md_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(
            analyze_manage_invocation_markdown(content, str(md_file), script_index)
        )
    return findings


# =============================================================================
# missing-canonical-block rule
# =============================================================================

_CANONICAL_BLOCK_HEADING = re.compile(
    r'^##\s+Canonical\s+invocations\s*$', re.IGNORECASE | re.MULTILINE
)


def _has_canonical_block(skill_md_path: Path) -> bool:
    try:
        content = skill_md_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return False
    return bool(_CANONICAL_BLOCK_HEADING.search(content))


def check_missing_canonical_blocks(marketplace_root: Path) -> list[dict]:
    """Emit a finding for every in-scope SKILL.md lacking ``## Canonical invocations``.

    The in-scope set is auto-derived from the bundle tree. The rule is
    warning-severity: the canonical-block convention is the documented
    source-of-truth contract, but absence does not break runtime — it merely
    leaves authors without an in-skill reference.
    """
    findings: list[dict] = []
    seen_skill_dirs: set[Path] = set()
    for desc in discover_in_scope_scripts(marketplace_root):
        skill_md = marketplace_root / 'marketplace' / desc.skill_dir_relpath / 'SKILL.md'
        if not skill_md.is_file():
            skill_md = marketplace_root / desc.skill_dir_relpath / 'SKILL.md'
        if not skill_md.is_file():
            continue
        # Dedup — a single skill dir may own multiple notation triples.
        if skill_md.parent in seen_skill_dirs:
            continue
        seen_skill_dirs.add(skill_md.parent)
        if _has_canonical_block(skill_md):
            continue
        findings.append(
            _build_finding(
                rule_id=RULE_MISSING_CANONICAL_BLOCK,
                file_path=str(skill_md),
                line=1,
                severity='warning',
                description=(
                    f'SKILL.md owns an in-scope script (`{desc.notation}`) '
                    f'but lacks a `## Canonical invocations` section'
                ),
                details={
                    'notation': desc.notation,
                    'reason': 'missing_canonical_block',
                    'canonical_hint': (
                        'Add a `## Canonical invocations` section to '
                        f'{desc.skill_dir_relpath}/SKILL.md — one '
                        '`### subcommand` heading per registered argparse '
                        'top-level subcommand'
                    ),
                },
            )
        )
    return findings


# =============================================================================
# Marketplace-wide aggregator
# =============================================================================


def scan_manage_invocation(marketplace_root: Path) -> list[dict]:
    """Run both manage-invocation rules across the entire marketplace.

    Combines findings from the markdown invocation analyzer (per-bundle sweep
    of all SKILL.md / standards / references / workflow / recipes markdown
    files) and the missing-canonical-block check (per in-scope SKILL.md).

    The invocation analyzer requires a derived surface index; when no
    executor is reachable the index is empty and the invocation rule emits
    nothing (no false positives). The missing-canonical-block rule is purely
    static and runs regardless.
    """
    findings: list[dict] = []
    bundles_dir = _bundles_dir(marketplace_root)
    script_index = build_script_index(marketplace_root)
    if bundles_dir is not None and script_index:
        for md_file in sorted(bundles_dir.rglob('*.md')):
            try:
                content = md_file.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                continue
            findings.extend(
                analyze_manage_invocation_markdown(content, str(md_file), script_index)
            )
    findings.extend(check_missing_canonical_blocks(marketplace_root))
    return findings
