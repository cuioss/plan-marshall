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

Consequences of the promotion, both intended:

- **Alias awareness.** The choice list argparse renders carries alias
  spellings flat alongside canonical names, so an alias invocation is simply
  in the accepted set.
- **Flag sensitivity is deliberately lower.** The shared derivation
  over-approximates a node's flag set (every ``--long-token`` anywhere in the
  output) and this adapter widens further, unioning each subcommand's whole
  subtree with the root parser's flags. That is the safe direction — fewer
  findings, no false findings — but it IS a real sensitivity change from the
  exact AST set, so the four canonical argparse-rejection recurrence
  signatures are pinned as positive controls in this cluster's tests.

Findings have severity=error and fixable=False, matching the
``DISPLAY_DETAIL_*`` finding shape used elsewhere in the plugin-doctor
codebase. Each finding carries ``rule_id``, ``file``, ``line``, plus
rule-specific ``details`` keys (notation/subcommand/flag/etc.).

Activation
----------
This rule cluster is unconditionally active across all marketplace markdown.
Recurring stale-flag drift in skill workflows motivated default-on
enforcement rather than a gated transitional period.

Public API
----------
- ``analyze_argument_naming(marketplace_root)``: entry point — returns
  findings for the four rule IDs combined.
- ``scan_notation(marketplace_root, registered_notations)``: detects
  ``ARGUMENT_NAMING_NOTATION_INVALID``.
- ``scan_subcommand(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``.
- ``scan_flag(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_FLAG_UNKNOWN``.
- ``scan_canonical_forms(marketplace_root, script_index)``: detects
  ``ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT``.
- ``load_registered_notations(executor_path)``: regex-parses the executor's
  ``SCRIPTS = { ... }`` literal and returns the set of registered notations.
- ``build_script_index(registered_notations, marketplace_root)``: thin adapter
  over the shared ``argparse_surface`` derivation, flattening each script's
  verb tree to ``{subcommand: set[flags]}`` plus a ``root_flags`` set.

Rule IDs registered
-------------------
- ``ARGUMENT_NAMING_NOTATION_INVALID``
- ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``
- ``ARGUMENT_NAMING_FLAG_UNKNOWN``
- ``ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT``
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor
from argparse_surface import (
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

# Opt-in cluster descriptor. The four ARGUMENT_NAMING_* rules are produced by a
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
_INVOCATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<notation>[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+)'
    r'(?:\s+(?P<subcommand>[a-z][A-Za-z0-9_\-]*))?'
    r'(?P<rest>.*)$'
)

# Loose token splitter used to enumerate ``--flag`` occurrences in the
# trailing portion of an invocation. Matches identifier-style flags;
# rejects placeholder shapes like ``--{plan-id}``.
_FLAG_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9_\-]*)\b')

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
    rest: str  # trailing portion of the line for flag extraction


@dataclass
class _ScriptEntry:
    """Argparse summary for one registered script.

    ``subcommands`` maps each registered subcommand name to the set of
    declared ``--flag`` names on that subparser. ``root_flags`` holds
    flags declared directly on the root ``ArgumentParser``.
    """

    subcommands: dict[str, set[str]]
    root_flags: set[str]


# =============================================================================
# Notation registry helpers
# =============================================================================


def load_registered_notations(executor_path: Path) -> set[str]:
    """Parse the executor's ``SCRIPTS = { ... }`` block and return its keys.

    Uses a line-by-line regex rather than full Python parsing so the
    function works against the generated executor without importing it.
    Returns an empty set if the file is missing or unreadable.
    """
    try:
        text = executor_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return set()

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
    return notations


# =============================================================================
# Accept-set index — thin adapter over the shared help-derived derivation
# =============================================================================


def _subtree_flags(node: ParserNode) -> set[str]:
    """Union the flag surfaces of ``node`` and every descendant.

    Widening, per the asymmetric-error rule. This index is flat — it keys only
    on the FIRST positional — while argparse chains can be three levels deep
    (``manage-config plan phase-5-execute set --field X``). Attributing only the
    first-level node's own flags would report ``--field`` as unknown on a
    perfectly valid call. Unioning the subtree accepts a flag that is really
    declared two levels down, which over-accepts and never over-rejects.
    """
    flags = set(node.flags)
    for child in node.children.values():
        flags |= _subtree_flags(child)
    return flags


def _entry_from_surface(surface: ScriptSurface) -> _ScriptEntry:
    """Flatten a derived surface into this cluster's two-level index shape.

    ``subcommands`` keys are every accepted top-level spelling — canonical
    names AND alias spellings, exactly as the choice list renders them — which
    is what makes a documented alias invocation resolve instead of reporting an
    unknown subcommand. Each value is the subcommand's subtree flag union
    widened with the root parser's own flags, because argparse honours a
    root-declared flag (``--plan-id``, ``--project-dir``) on every subcommand
    while rendering it only in the root's help.
    """
    root_flags = set(surface.root.flags)
    subcommands = {
        name: root_flags | _subtree_flags(child)
        for name, child in surface.root.children.items()
    }
    return _ScriptEntry(subcommands=subcommands, root_flags=root_flags)


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


def _extract_invocations(markdown_path: Path) -> list[_Invocation]:
    """Parse markdown lines and emit one ``_Invocation`` per executor token."""
    try:
        text = markdown_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    out: list[_Invocation] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        match = _INVOCATION_RE.search(raw)
        if not match:
            continue
        sub = match.group('subcommand')
        # Argparse subcommands cannot start with a hyphen (those are flags).
        # The regex already constrains this, but skip noise from prose
        # continuations to be safe.
        out.append(
            _Invocation(
                file=markdown_path,
                line=idx,
                notation=match.group('notation'),
                subcommand=sub if sub else None,
                rest=match.group('rest') or '',
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
    """Detect invented subcommand tokens following a registered notation."""
    findings: list[Finding] = []
    for md in _markdown_targets(marketplace_root):
        for inv in _extract_invocations(md):
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
            if inv.subcommand in entry.subcommands:
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
            entry = script_index.get(inv.notation)
            if entry is None:
                continue
            allowed: set[str]
            if inv.subcommand is None:
                allowed = entry.root_flags
                scope_label = '<root>'
            else:
                # Subcommand may be unknown; in that case, the subcommand
                # rule reports — we still avoid false flag findings by
                # falling back to root flags.
                sub_allowed = entry.subcommands.get(inv.subcommand)
                if sub_allowed is None:
                    continue
                allowed = sub_allowed
                scope_label = inv.subcommand

            for match in _FLAG_TOKEN_RE.finditer(inv.rest):
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
        if sub not in entry.subcommands:
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

        allowed = entry.subcommands[sub]
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
# Public entry point
# =============================================================================


def analyze_argument_naming(marketplace_root: Path) -> list[dict]:
    """Run the full argument-naming rule cluster against ``marketplace_root``.

    Unconditionally active — default-on enforcement rather than a gated
    transitional period, because stale-flag drift recurred in skill workflows.

    Returns a flat list of finding dicts (one per detected drift). Use
    ``rule_id`` to differentiate rule clusters.
    """
    executor_path = marketplace_root.parent / '.plan' / 'execute-script.py'
    registered = load_registered_notations(executor_path)
    if not registered:
        # No executor or empty registry — cluster has no ground truth and
        # would produce false positives. Treat as a no-op.
        return []

    script_index = build_script_index(registered, marketplace_root)

    findings: list[dict] = []
    findings.extend(scan_notation(marketplace_root, registered))
    findings.extend(scan_subcommand(marketplace_root, script_index))
    findings.extend(scan_flag(marketplace_root, script_index))
    findings.extend(scan_canonical_forms(marketplace_root, script_index))
    return findings
