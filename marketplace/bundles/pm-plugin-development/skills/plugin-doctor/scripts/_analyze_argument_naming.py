#!/usr/bin/env python3
"""Argument-naming rule cluster — notation/subcommand/flag/Canonical-Forms cross-check.

This module implements the ``ARGUMENT_NAMING_*`` rule cluster used by
plugin-doctor to detect drift between marketplace prose (SKILL.md, agent
markdown, recipe markdown, standards) and the actual argparse declarations
of the scripts those documents reference. The cluster also cross-checks the
"Canonical Forms" table in
``marketplace/bundles/plan-marshall/skills/dev-general-practices/standards/argument-naming.md``
against the same argparse declarations.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_verb_chains.py`` and ``scan_argparse_safety``:

- pure static analysis (no subprocess execution, no module imports of target scripts);
- AST-walk of script source to enumerate registered subparsers and flags;
- regex-driven extraction of executor invocations from markdown sources.

Findings have severity=error and fixable=False, matching the
``DISPLAY_DETAIL_*`` finding shape used elsewhere in the plugin-doctor
codebase. Each finding carries ``rule_id``, ``file``, ``line``, plus
rule-specific ``details`` keys (notation/subcommand/flag/etc.).

Activation
----------
This rule cluster is unconditionally active across all marketplace markdown.
See lesson ``2026-04-29-23-002`` for the rationale (three recurrences of
stale-flag drift in skill workflows within ~3 days drove the move from a
gated transitional period to default-on enforcement).

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
- ``build_script_index(registered_notations, marketplace_root)``: AST-walks
  every registered script and returns a dict keyed by notation with
  ``{subcommand: {flags: set[str]}}`` plus a top-level ``flags`` set for
  flags declared on the root parser.

Rule IDs registered
-------------------
- ``ARGUMENT_NAMING_NOTATION_INVALID``
- ``ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN``
- ``ARGUMENT_NAMING_FLAG_UNKNOWN``
- ``ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT``
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Rule IDs
# =============================================================================

RULE_NOTATION_INVALID = 'ARGUMENT_NAMING_NOTATION_INVALID'
RULE_SUBCOMMAND_UNKNOWN = 'ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN'
RULE_FLAG_UNKNOWN = 'ARGUMENT_NAMING_FLAG_UNKNOWN'
RULE_CANONICAL_FORMS_DRIFT = 'ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT'


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


def _resolve_script_path(notation: str, marketplace_root: Path) -> Path | None:
    """Map ``bundle:skill:script`` to an absolute script path under marketplace.

    Returns ``None`` when the file does not exist. Source-of-truth lookup
    targets the marketplace tree directly; the executor's cached path is
    intentionally ignored so the analyzer remains independent of cache state.
    """
    bundle, skill, script = notation.split(':', 2)
    candidate = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts' / f'{script}.py'
    if candidate.is_file():
        return candidate
    # Some scripts live in nested script directories (e.g. shared/extension).
    # Fall back to a recursive glob within the skill's scripts dir.
    scripts_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts'
    if scripts_dir.is_dir():
        for nested in scripts_dir.rglob(f'{script}.py'):
            if nested.is_file():
                return nested
    return None


# =============================================================================
# Argparse tree extraction (root parser + subparsers + flags)
# =============================================================================


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _attr_receiver_name(call: ast.Call) -> str | None:
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name):
        return func.value.id
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None


def _extract_flag_names_from_add_argument(call: ast.Call) -> list[str]:
    """Extract long-flag names (``--foo``) from an ``add_argument(...)`` call.

    Both positional flag args (``add_argument('--foo', '-f', ...)``) are
    inspected; only long flags are kept (short flags like ``-f`` are
    intentionally excluded — they are not subject to the canonical-forms
    convention).
    """
    flags: list[str] = []
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            value = arg.value
            if value.startswith('--'):
                flags.append(value[2:])
    return flags


def build_script_index(
    registered_notations: set[str],
    marketplace_root: Path,
) -> dict[str, _ScriptEntry]:
    """AST-walk every registered script and build the (subcommand, flag) index.

    Returns a dict keyed by notation. Missing scripts (notation registered
    but file missing) are silently skipped — they will surface via the
    notation-validity rule when prose references them.
    """
    index: dict[str, _ScriptEntry] = {}
    for notation in registered_notations:
        script_path = _resolve_script_path(notation, marketplace_root)
        if script_path is None:
            continue
        entry = _build_entry_from_script(script_path)
        if entry is not None:
            index[notation] = entry
    return index


def _build_entry_from_script(script_path: Path) -> _ScriptEntry | None:
    """AST-walk a single script and return its argparse summary, or ``None``."""
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError:
        return None

    # Track every parser variable. The first ``ArgumentParser`` assignment
    # is treated as the root; subsequent ``add_parser`` assignments are
    # tracked individually so flag extraction can attribute each
    # ``add_argument`` call to the right subparser.
    parsers: dict[str, str | None] = {}  # var_name -> subcommand_name (None for root)
    subparsers_handles: dict[str, str] = {}  # handle_var -> owning_parser_var
    root_var: str | None = None

    # First pass: discover root parser, subparser handles, and add_parser
    # assignments. Sort by lineno to keep traversal deterministic.
    assigns = sorted(
        (n for n in ast.walk(tree) if isinstance(n, ast.Assign)),
        key=lambda a: (a.lineno, a.col_offset),
    )

    for assign in assigns:
        if not isinstance(assign.value, ast.Call):
            continue
        call = assign.value
        name = _call_func_name(call)
        if name is None:
            continue

        targets = [t.id for t in assign.targets if isinstance(t, ast.Name)]
        if not targets:
            continue

        if name == 'ArgumentParser':
            for var in targets:
                parsers[var] = None  # root parser
                if root_var is None:
                    root_var = var
            continue

        if name == 'add_subparsers':
            owner = _attr_receiver_name(call)
            if owner is None or owner not in parsers:
                continue
            for var in targets:
                subparsers_handles[var] = owner
            continue

        if name == 'add_parser':
            handle = _attr_receiver_name(call)
            if handle is None or handle not in subparsers_handles:
                continue
            sub_name = _first_string_arg(call)
            if not sub_name:
                continue
            for var in targets:
                parsers[var] = sub_name
            continue

    # Second pass: bucket every ``add_argument`` call by the parser variable
    # it was invoked on. Walk the AST again and look at attribute receivers.
    subcommands: dict[str, set[str]] = {}
    root_flags: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != 'add_argument':
            continue
        receiver = _attr_receiver_name(node)
        if receiver is None or receiver not in parsers:
            continue
        flags = _extract_flag_names_from_add_argument(node)
        if not flags:
            continue
        sub_name = parsers[receiver]
        if sub_name is None:
            root_flags.update(flags)
        else:
            subcommands.setdefault(sub_name, set()).update(flags)

    # Ensure every subcommand has at least an empty flag set — the
    # subcommand exists even if it declares no flags.
    for sub_name in parsers.values():
        if sub_name is not None:
            subcommands.setdefault(sub_name, set())

    return _ScriptEntry(subcommands=subcommands, root_flags=root_flags)


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
            for sub in ('standards', 'references', 'recipes'):
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
       (Some scripts have legitimate snake_case names like ``manage_status`` —
       the registry is the source of truth.)
    2. The third segment exactly repeats the second (``foo:foo`` shape).
    3. The notation is not present in ``registered_notations``.
    """
    findings: list[dict] = []
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
                {
                    'rule_id': RULE_NOTATION_INVALID,
                    'type': RULE_NOTATION_INVALID,
                    'file': str(inv.file),
                    'line': inv.line,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Notation `{notation}` is not registered in the executor (reason: {details["reason"]})'
                    ),
                    'details': details,
                }
            )
    return findings


# =============================================================================
# Subcommand validity rule
# =============================================================================


def scan_subcommand(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Detect invented subcommand tokens following a registered notation."""
    findings: list[dict] = []
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
                {
                    'rule_id': RULE_SUBCOMMAND_UNKNOWN,
                    'type': RULE_SUBCOMMAND_UNKNOWN,
                    'file': str(inv.file),
                    'line': inv.line,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Subcommand `{inv.subcommand}` not declared on `{inv.notation}` '
                        f'(known: {sorted(entry.subcommands)})'
                    ),
                    'details': {
                        'notation': inv.notation,
                        'subcommand': inv.subcommand,
                        'known_subcommands': sorted(entry.subcommands),
                    },
                }
            )
    return findings


# =============================================================================
# Flag validity rule
# =============================================================================


def scan_flag(
    marketplace_root: Path,
    script_index: dict[str, _ScriptEntry],
) -> list[dict]:
    """Detect invented ``--flag`` tokens against a script's argparse declarations."""
    findings: list[dict] = []
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
                    {
                        'rule_id': RULE_FLAG_UNKNOWN,
                        'type': RULE_FLAG_UNKNOWN,
                        'file': str(inv.file),
                        'line': inv.line,
                        'severity': 'error',
                        'fixable': False,
                        'description': (
                            f'Flag `--{flag}` not declared on `{inv.notation} {scope_label}` (known: {sorted(allowed)})'
                        ),
                        'details': {
                            'notation': inv.notation,
                            'subcommand': inv.subcommand,
                            'flag': flag,
                            'known_flags': sorted(allowed),
                        },
                    }
                )
    return findings


# =============================================================================
# Canonical Forms cross-check
# =============================================================================


def _canonical_forms_path(marketplace_root: Path) -> Path:
    return (
        marketplace_root
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'dev-general-practices'
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
    findings: list[dict] = []
    md_path = _canonical_forms_path(marketplace_root)
    if not md_path.is_file():
        return findings

    for line, form in _parse_canonical_forms(md_path):
        tokens = form.split()
        if len(tokens) < 2:
            continue
        shorthand, sub, *rest = tokens
        notation = _resolve_shorthand_to_notation(shorthand, script_index)
        if notation is None:
            findings.append(
                {
                    'rule_id': RULE_CANONICAL_FORMS_DRIFT,
                    'type': RULE_CANONICAL_FORMS_DRIFT,
                    'file': str(md_path),
                    'line': line,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Canonical Forms row references unknown script `{shorthand}` — no registered notation matches'
                    ),
                    'details': {
                        'shorthand': shorthand,
                        'form': form,
                        'reason': 'shorthand_unresolved',
                    },
                }
            )
            continue

        entry = script_index[notation]
        if sub not in entry.subcommands:
            findings.append(
                {
                    'rule_id': RULE_CANONICAL_FORMS_DRIFT,
                    'type': RULE_CANONICAL_FORMS_DRIFT,
                    'file': str(md_path),
                    'line': line,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Canonical Forms row prescribes `{shorthand} {sub}` '
                        f'but argparse for `{notation}` declares no such subcommand '
                        f'(known: {sorted(entry.subcommands)})'
                    ),
                    'details': {
                        'shorthand': shorthand,
                        'notation': notation,
                        'subcommand': sub,
                        'known_subcommands': sorted(entry.subcommands),
                        'form': form,
                        'reason': 'subcommand_drift',
                    },
                }
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
                {
                    'rule_id': RULE_CANONICAL_FORMS_DRIFT,
                    'type': RULE_CANONICAL_FORMS_DRIFT,
                    'file': str(md_path),
                    'line': line,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Canonical Forms row prescribes `--{flag}` for '
                        f'`{shorthand} {sub}` but argparse declares it as '
                        f'{sorted(allowed)}'
                    ),
                    'details': {
                        'shorthand': shorthand,
                        'notation': notation,
                        'subcommand': sub,
                        'flag': flag,
                        'known_flags': sorted(allowed),
                        'form': form,
                        'reason': 'flag_drift',
                    },
                }
            )
    return findings


# =============================================================================
# Public entry point
# =============================================================================


def analyze_argument_naming(marketplace_root: Path) -> list[dict]:
    """Run the full argument-naming rule cluster against ``marketplace_root``.

    Unconditionally active. See lesson ``2026-04-29-23-002`` for the rationale
    behind moving from a gated transitional period to default-on enforcement.

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
