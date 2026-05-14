#!/usr/bin/env python3
"""Generalized manage-* invocation analyzer for plugin-doctor.

This module implements two rules:

1. ``manage-invocation-invalid`` (severity: error) — detects token-tree
   mismatches between markdown invocations of in-scope ``manage-*`` scripts
   and the scripts' actual argparse declarations. For each invocation found
   in markdown bodies, the analyzer extracts the ``(subcommand, sub_verb,
   flags)`` tuple and validates it against the script's canonical argparse
   tree, emitting one finding per mismatch:

   - Unknown top-level subcommand.
   - Unknown sub-verb under a subcommand that declares sub-subparsers.
   - Unknown flag (``--{flag}``) under the resolved leaf parser.
   - Missing required flag declared by the resolved leaf parser.

   Findings carry ``details.canonical_hint`` with the closest correct form.

2. ``missing-canonical-block`` (severity: warning) — emitted when a
   script-owning SKILL.md (from the in-scope 15-file list) lacks a
   ``## Canonical invocations`` section. The section is the documented
   source-of-truth contract published by D1 of the argparse-surface-drift
   remediation plan; missing it leaves authors with no in-skill reference
   when writing prose that invokes the script.

Pattern alignment
-----------------
The analyzer mirrors the ``_analyze_argument_naming.py`` and
``_analyze_manage_findings_invocation.py`` clusters:

- pure static analysis (no subprocess execution, no import of the target
  scripts);
- AST-based argparse extraction with deterministic traversal order;
- regex-driven extraction of executor invocations from markdown sources;
- findings are dicts with the standard
  ``rule_id``/``file``/``line``/``severity``/``fixable``/``details``
  shape consumed by ``_doctor_analysis.extract_issues_from_*``.

Scope
-----
The analyzer is intentionally scoped to a fixed, enumerable list of
``manage-*`` script families — the seven scripts whose argparse surfaces
are the most heavily referenced from skill prose and the most likely to
drift under LLM-authored edits. The whitelist is the
``IN_SCOPE_SCRIPTS`` constant below; out-of-scope notations are skipped
silently so the cluster does not raise false positives on bundles whose
authors have not yet adopted the canonical-block convention.

Public API
----------
- ``analyze_manage_invocation_markdown(content, file_path, script_index)``:
  scan a single markdown body for invocation mismatches.
- ``scan_skill_for_manage_invocation(skill_dir, script_index)``: per-skill
  scanner used by ``_doctor_analysis.analyze_component``.
- ``scan_manage_invocation(marketplace_root)``: marketplace-wide scanner
  combining both rules.
- ``check_missing_canonical_blocks(marketplace_root)``: standalone helper
  that emits ``missing-canonical-block`` findings for the enumerated
  script-owning SKILL.md files.
- ``build_script_tree(script_path)``: AST-based canonical-tree builder
  returning ``{subcommand: {sub_verb_or_none: {flags, required_flags}}}``.
- ``RULE_MANAGE_INVOCATION_INVALID`` / ``RULE_MISSING_CANONICAL_BLOCK``:
  the canonical rule keys.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# Rule IDs
# =============================================================================

RULE_MANAGE_INVOCATION_INVALID = 'manage-invocation-invalid'
RULE_MISSING_CANONICAL_BLOCK = 'missing-canonical-block'

# =============================================================================
# In-scope script enumeration
# =============================================================================

# The seven manage-* / workflow-integration script families whose markdown
# invocations are validated by this analyzer. Each entry maps a notation
# ``bundle:skill:script`` triple to the on-disk script path (relative to
# marketplace_root). The whitelist is intentionally explicit — adding a new
# family requires a deliberate edit so the cluster does not silently expand
# its scope on every bundle restructure.
#
# Notation triples are kebab-case as the executor registry keys them;
# script filenames may be either kebab- or snake-cased (manage-findings.py
# vs manage_status.py) — that asymmetry is preserved verbatim.

@dataclass(frozen=True)
class _ScriptDescriptor:
    """Identifies one in-scope manage-* script and its on-disk location."""

    notation: str  # bundle:skill:script (kebab-case third segment)
    script_relpath: str  # relative to marketplace_root, e.g. 'bundles/.../foo.py'
    skill_dir_relpath: str  # the owning skill directory, for missing-block checks


IN_SCOPE_SCRIPTS: tuple[_ScriptDescriptor, ...] = (
    _ScriptDescriptor(
        notation='plan-marshall:manage-status:manage_status',
        script_relpath='bundles/plan-marshall/skills/manage-status/scripts/manage_status.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-status',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-tasks:manage-tasks',
        script_relpath='bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-tasks',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-logging:manage-logging',
        script_relpath='bundles/plan-marshall/skills/manage-logging/scripts/manage-logging.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-logging',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-references:manage-references',
        script_relpath='bundles/plan-marshall/skills/manage-references/scripts/manage-references.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-references',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-config:manage-config',
        script_relpath='bundles/plan-marshall/skills/manage-config/scripts/manage-config.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-config',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:workflow-integration-git:git_workflow',
        script_relpath='bundles/plan-marshall/skills/workflow-integration-git/scripts/git_workflow.py',
        skill_dir_relpath='bundles/plan-marshall/skills/workflow-integration-git',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:workflow-integration-github:github_ops',
        script_relpath='bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py',
        skill_dir_relpath='bundles/plan-marshall/skills/workflow-integration-github',
    ),
    # Added to align coverage with the 14 SKILL.md files updated by D1
    # (manage-findings is intentionally excluded — covered by its own
    # dedicated analyzer ``_analyze_manage_findings_invocation.py``).
    _ScriptDescriptor(
        notation='plan-marshall:manage-architecture:architecture',
        script_relpath='bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-architecture',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-execution-manifest:manage-execution-manifest',
        script_relpath='bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-execution-manifest',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-files:manage-files',
        script_relpath='bundles/plan-marshall/skills/manage-files/scripts/manage-files.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-files',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-lessons:manage-lessons',
        script_relpath='bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-lessons',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-metrics:manage_metrics',
        script_relpath='bundles/plan-marshall/skills/manage-metrics/scripts/manage_metrics.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-metrics',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-plan-documents:manage-plan-documents',
        script_relpath='bundles/plan-marshall/skills/manage-plan-documents/scripts/manage-plan-documents.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-plan-documents',
    ),
    _ScriptDescriptor(
        notation='plan-marshall:manage-solution-outline:manage-solution-outline',
        script_relpath='bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py',
        skill_dir_relpath='bundles/plan-marshall/skills/manage-solution-outline',
    ),
)

# Notation map keyed by the third segment of the notation. The analyzer
# matches markdown invocations by the bundle:skill:script triple; this
# helper is the reverse lookup used by per-finding canonical-hint emission.
_NOTATION_BY_THIRD_SEGMENT: dict[str, _ScriptDescriptor] = {
    desc.notation.split(':')[-1]: desc for desc in IN_SCOPE_SCRIPTS
}

# =============================================================================
# AST-based argparse tree extraction
# =============================================================================


@dataclass
class _LeafParser:
    """The flag surface of a single leaf argparse parser.

    ``flags`` is the full set of declared long flag names (without the ``--``
    prefix). ``required_flags`` is the subset declared with ``required=True``.
    """

    flags: set[str] = field(default_factory=set)
    required_flags: set[str] = field(default_factory=set)


@dataclass
class _ScriptTree:
    """The full canonical argparse tree for one script.

    ``root`` is the leaf parser for the root (flags declared on the
    top-level parser before subparser dispatch).

    ``subcommands`` maps top-level subcommand names to either:
      - a ``_LeafParser`` (when the subcommand has no nested subparser);
      - a ``dict[sub_verb_name, _LeafParser]`` (when the subcommand declares
        its own ``add_subparsers``).
    """

    root: _LeafParser = field(default_factory=_LeafParser)
    subcommands: dict[str, _LeafParser | dict[str, _LeafParser]] = field(
        default_factory=dict
    )

    def known_subcommands(self) -> set[str]:
        return set(self.subcommands.keys())

    def get_leaf(
        self, subcommand: str | None, sub_verb: str | None
    ) -> _LeafParser | None:
        """Resolve a leaf parser by (subcommand, sub_verb).

        Returns ``None`` when the pair does not resolve. ``subcommand=None``
        targets the root parser.

        A second positional token under a *flat* subcommand is treated as a
        positional argument (e.g. ``architecture path SOURCE TARGET``), not
        as an unknown sub-verb — the leaf is returned so flag validation
        can still run. Nested-subparser subcommands continue to require a
        registered sub_verb.
        """
        if subcommand is None:
            return self.root
        entry = self.subcommands.get(subcommand)
        if entry is None:
            return None
        if isinstance(entry, _LeafParser):
            return entry
        # Nested mapping; sub_verb required.
        if sub_verb is None:
            return None
        return entry.get(sub_verb)


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _attr_receiver_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        return call.func.value.id
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def _extract_flag_names_from_add_argument(call: ast.Call) -> list[str]:
    """Return long-flag names declared by an ``add_argument`` call.

    Short flags (single-dash names) are excluded — the canonical-form
    convention covers long flags only. Positional argument names are also
    excluded. The flag name is returned without the leading ``--``.
    """
    names: list[str] = []
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            value = arg.value
            if value.startswith('--') and len(value) > 2:
                names.append(value[2:])
    return names


def _is_required_add_argument(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == 'required' and isinstance(kw.value, ast.Constant):
            return bool(kw.value.value)
    return False


def build_script_tree(script_path: Path) -> _ScriptTree | None:
    """AST-walk a single script and return its canonical argparse tree.

    Returns ``None`` when the script cannot be read or parsed. The traversal
    is two-pass:

    Pass 1 — discover every ``ArgumentParser`` / ``add_subparsers`` /
    ``add_parser`` / ``add_mutually_exclusive_group`` /
    ``add_argument_group`` assignment and build the parser-variable
    graph:

      - ``parser_kind[var]`` is ``'root' | 'sub' | 'subsub'`` identifying
        what kind of parser ``var`` refers to.
      - ``parser_name[var]`` is the subcommand or sub_verb name attached to
        that parser (``None`` for the root).
      - ``parser_owner[var]`` is the parent parser variable (for ``'subsub'``
        kinds, the variable name of the owning top-level subcommand parser).
      - ``subparsers_kind[handle]`` is ``'top' | 'nested'`` identifying
        whether the handle came from the root parser's ``add_subparsers``
        or from a subcommand parser's ``add_subparsers``.
      - ``subparsers_owner[handle]`` is the parser variable that owns the
        handle (root variable for top-level handles; subcommand parser
        variable for nested handles).
      - ``parser_alias[var]`` resolves a group handle returned by
        ``add_mutually_exclusive_group`` / ``add_argument_group`` to the
        parser variable that owns it; Pass 2 dereferences receivers
        through this map so group-level ``add_argument`` calls land on
        the parent leaf.

    Pass 2 — bucket every ``add_argument`` call by its receiver. Each call
    maps to a leaf parser via ``parser_kind``/``parser_name``/
    ``parser_owner`` after the receiver has been resolved through
    ``parser_alias``.
    """
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError:
        return None

    parser_kind: dict[str, str] = {}  # var -> 'root' | 'sub' | 'subsub'
    parser_name: dict[str, str | None] = {}  # var -> subcommand or sub_verb name (None for root)
    parser_owner: dict[str, str | None] = {}  # var -> owning subcommand parser var (for 'subsub')

    subparsers_kind: dict[str, str] = {}  # handle var -> 'top' | 'nested'
    subparsers_owner: dict[str, str] = {}  # handle var -> owning parser var

    # Aliases produced by ``add_mutually_exclusive_group`` and
    # ``add_argument_group``. Calls to ``alias.add_argument(...)`` are
    # bucketed as if they targeted the underlying parser variable so the
    # leaf inherits the group's flag declarations.
    parser_alias: dict[str, str] = {}  # alias var -> underlying parser var

    root_var: str | None = None

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
                parser_kind[var] = 'root'
                parser_name[var] = None
                parser_owner[var] = None
                if root_var is None:
                    root_var = var
            continue

        if name == 'add_subparsers':
            owner = _attr_receiver_name(call)
            if owner is None or owner not in parser_kind:
                continue
            handle_kind = 'top' if parser_kind[owner] == 'root' else 'nested'
            for var in targets:
                subparsers_kind[var] = handle_kind
                subparsers_owner[var] = owner
            continue

        if name == 'add_parser':
            handle = _attr_receiver_name(call)
            if handle is None or handle not in subparsers_kind:
                continue
            sub_name = _first_string_arg(call)
            if not sub_name:
                continue
            kind = subparsers_kind[handle]
            owner = subparsers_owner[handle]
            for var in targets:
                if kind == 'top':
                    parser_kind[var] = 'sub'
                    parser_name[var] = sub_name
                    parser_owner[var] = None
                else:
                    parser_kind[var] = 'subsub'
                    parser_name[var] = sub_name
                    parser_owner[var] = owner
            continue

        if name in ('add_mutually_exclusive_group', 'add_argument_group'):
            # ``group = parser.add_mutually_exclusive_group(...)`` — Pass 2
            # treats subsequent ``group.add_argument(...)`` calls as
            # additions to the underlying ``parser`` leaf so group-level
            # flag declarations are not silently dropped.
            owner = _attr_receiver_name(call)
            if owner is None:
                continue
            # Resolve transitively in case groups are nested.
            resolved = parser_alias.get(owner, owner)
            if resolved not in parser_kind:
                continue
            for var in targets:
                parser_alias[var] = resolved
            continue

    # Construct the canonical tree skeleton from discovered parsers.
    script_tree = _ScriptTree()
    # Track which top-level subcommands acquired nested subparsers so we can
    # detect collisions between 'sub' and 'subsub' under the same name.
    nested_subcommands: dict[str, dict[str, _LeafParser]] = {}
    flat_subcommands: dict[str, _LeafParser] = {}

    # First, register every top-level subcommand as flat by default.
    for var, kind in parser_kind.items():
        if kind == 'sub':
            sub_name = parser_name[var]
            if sub_name is not None and sub_name not in flat_subcommands:
                flat_subcommands[sub_name] = _LeafParser()

    # Then, register every sub-subcommand. Its owner variable maps back to
    # a 'sub' parser; the owning subcommand name becomes a nested entry.
    for var, kind in parser_kind.items():
        if kind == 'subsub':
            owner_var = parser_owner[var]
            if owner_var is None:
                continue
            owner_name = parser_name.get(owner_var)
            sub_verb_name = parser_name[var]
            if owner_name is None or sub_verb_name is None:
                continue
            nested_subcommands.setdefault(owner_name, {})
            nested_subcommands[owner_name].setdefault(sub_verb_name, _LeafParser())

    # Pass 2: bucket add_argument calls.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != 'add_argument':
            continue
        receiver = _attr_receiver_name(node)
        if receiver is None:
            continue
        # Resolve mutually-exclusive / argument-group aliases to their
        # underlying parser variable so group-level ``add_argument`` calls
        # land on the parent leaf.
        receiver = parser_alias.get(receiver, receiver)
        if receiver not in parser_kind:
            continue
        flags = _extract_flag_names_from_add_argument(node)
        if not flags:
            continue
        required = _is_required_add_argument(node)
        kind = parser_kind[receiver]
        if kind == 'root':
            script_tree.root.flags.update(flags)
            if required:
                script_tree.root.required_flags.update(flags)
        elif kind == 'sub':
            sub_name = parser_name[receiver]
            if sub_name is None:
                continue
            leaf = flat_subcommands.setdefault(sub_name, _LeafParser())
            leaf.flags.update(flags)
            if required:
                leaf.required_flags.update(flags)
        elif kind == 'subsub':
            owner_var = parser_owner[receiver]
            sub_verb_name = parser_name[receiver]
            if owner_var is None or sub_verb_name is None:
                continue
            owner_name = parser_name.get(owner_var)
            if owner_name is None:
                continue
            nested_subcommands.setdefault(owner_name, {})
            leaf = nested_subcommands[owner_name].setdefault(sub_verb_name, _LeafParser())
            leaf.flags.update(flags)
            if required:
                leaf.required_flags.update(flags)

    # Compose the tree: a subcommand is "nested" iff it appears in
    # nested_subcommands; otherwise it is a flat leaf.
    for sub_name, leaf in flat_subcommands.items():
        if sub_name in nested_subcommands:
            # Collision — the subcommand declared its own subparsers. The
            # nested mapping is the canonical form; any flags declared at
            # the sub level are propagated to every sub_verb as common
            # parent flags (matching argparse semantics).
            nested = nested_subcommands[sub_name]
            for sv_leaf in nested.values():
                sv_leaf.flags.update(leaf.flags)
                sv_leaf.required_flags.update(leaf.required_flags)
        else:
            script_tree.subcommands[sub_name] = leaf
    for sub_name, nested in nested_subcommands.items():
        script_tree.subcommands[sub_name] = dict(nested)

    return script_tree


def build_script_index(marketplace_root: Path) -> dict[str, _ScriptTree]:
    """Build a notation -> canonical-tree index for every in-scope script.

    Scripts that cannot be read or parsed are silently dropped — the
    analyzer is best-effort and downstream rules already cover missing
    scripts via the notation-validity cluster.
    """
    index: dict[str, _ScriptTree] = {}
    for desc in IN_SCOPE_SCRIPTS:
        script_path = marketplace_root / 'marketplace' / desc.script_relpath
        if not script_path.is_file():
            # Some installations place ``marketplace`` at the repository
            # root rather than as a child; accept either layout.
            script_path = marketplace_root / desc.script_relpath
        if not script_path.is_file():
            continue
        tree = build_script_tree(script_path)
        if tree is None:
            continue
        index[desc.notation] = tree
    return index


# =============================================================================
# Markdown invocation extraction
# =============================================================================

# Match any executor invocation whose triple aligns with one of the
# in-scope ``manage-*`` or ``workflow-integration-*`` scripts. The pattern
# captures the bundle/skill/script segments plus the trailing portion so
# the consumer can tokenize positional / flag args.
_NOTATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<bundle>[A-Za-z0-9_\-]+):'
    r'(?P<skill>[A-Za-z0-9_\-]+):'
    r'(?P<script>[A-Za-z0-9_\-]+)'
    r'(?P<rest>.*)$'
)

# Positional token extractor — strips a single leading whitespace run and
# matches the next alphanumeric-or-hyphen identifier. Stops at flag tokens
# (``-`` prefix), backslash line continuations, and end-of-line.
_NEXT_POSITIONAL_RE = re.compile(r'\s+(?P<tok>[A-Za-z][A-Za-z0-9_\-]*)')

# Long-flag token extractor. Anchored to a non-identifier boundary to
# avoid matching numeric ranges (``--100``) or inside identifiers.
_FLAG_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9_\-]*)\b')


def _strip_quoted_substrings(text: str) -> str:
    """Remove single- and double-quoted substrings from ``text``.

    Shell-style quoting is honored: characters inside matched quotes are
    replaced with spaces so the resulting string preserves column offsets
    while suppressing any ``--flag``-like content that lives inside a
    quoted argument value (e.g. ``--message "release: --not-a-flag"``).
    Backslash escapes inside quotes are respected. Unterminated quotes
    consume the remainder of the line.
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
                # Honor a backslash escape so ``\"`` and ``\'`` do not
                # prematurely close the quote.
                if text[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append(' ')
                i += 1
            if i < n:
                out.append(' ')  # closing quote
                i += 1
            # Unterminated quote: loop exits naturally.
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def _join_continuation_lines(content: str) -> list[tuple[int, str]]:
    """Collapse backslash-continued lines into logical lines.

    Returns a list of ``(start_line_no, joined_text)`` tuples preserving
    the original 1-based line number where each logical line begins.
    A trailing backslash (optionally followed by whitespace) at the end of
    a physical line splices the next line onto the current logical line
    with a single space separator. Findings emitted on a joined logical
    line are reported against the starting line number — the line a
    reader would scroll to first.
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


def _extract_positional_tokens(rest: str, max_positionals: int = 2) -> list[str]:
    """Extract up to ``max_positionals`` positional tokens from ``rest``.

    Stops at the first flag token (``-`` prefix) or end-of-line.
    """
    tokens: list[str] = []
    pos = 0
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
    """Extract every long-flag token (without the ``--`` prefix) from ``rest``.

    Quoted substrings are stripped first so flag-like text appearing
    inside string argument values does not produce false positives.
    """
    return [
        m.group('flag') for m in _FLAG_TOKEN_RE.finditer(_strip_quoted_substrings(rest))
    ]


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
    return {
        'rule_id': rule_id,
        'type': rule_id,
        'file': file_path,
        'line': line,
        'severity': severity,
        'fixable': False,
        'description': description,
        'details': details,
    }


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


def _analyze_one_invocation(
    *,
    notation: str,
    rest: str,
    file_path: str,
    line: int,
    script_index: dict[str, _ScriptTree],
) -> list[dict]:
    """Validate one ``rest`` payload against the script's canonical tree.

    Returns a list of findings (possibly empty). At most one finding per
    failure mode is emitted per line, but a single line may trip multiple
    failure modes (e.g. unknown sub-verb AND unknown flag); each is
    reported independently.
    """
    findings: list[dict] = []
    tree = script_index.get(notation)
    if tree is None:
        return findings

    positionals = _extract_positional_tokens(rest)
    declared_flags = _extract_flag_tokens(rest)

    subcommand: str | None = positionals[0] if positionals else None
    sub_verb: str | None = positionals[1] if len(positionals) >= 2 else None

    # When the script declares no subcommands, the leaf is the root parser
    # itself and any positional tokens after the notation are not
    # subcommands. Skip subcommand validation in that case.
    if subcommand is not None and not tree.known_subcommands():
        subcommand = None
        sub_verb = None

    if subcommand is not None:
        if subcommand not in tree.subcommands:
            findings.append(
                _build_finding(
                    rule_id=RULE_MANAGE_INVOCATION_INVALID,
                    file_path=file_path,
                    line=line,
                    severity='error',
                    description=(
                        f'`{notation}` invocation uses unregistered '
                        f'subcommand `{subcommand}` (registered: '
                        f'{sorted(tree.known_subcommands())})'
                    ),
                    details={
                        'notation': notation,
                        'subcommand': subcommand,
                        'reason': 'subcommand_unknown',
                        'canonical_hint': _canonical_hint_for_subcommand(
                            notation, tree.known_subcommands()
                        ),
                        'known_subcommands': sorted(tree.known_subcommands()),
                    },
                )
            )
            return findings

        entry = tree.subcommands[subcommand]
        if isinstance(entry, dict):
            # Nested subparser — sub_verb is required.
            if sub_verb is None or sub_verb not in entry:
                known_sub_verbs = set(entry.keys())
                findings.append(
                    _build_finding(
                        rule_id=RULE_MANAGE_INVOCATION_INVALID,
                        file_path=file_path,
                        line=line,
                        severity='error',
                        description=(
                            f'`{notation} {subcommand}` invocation uses '
                            f'unregistered sub-verb '
                            f'`{sub_verb if sub_verb is not None else "<missing>"}` '
                            f'(registered: {sorted(known_sub_verbs)})'
                        ),
                        details={
                            'notation': notation,
                            'subcommand': subcommand,
                            'sub_verb': sub_verb,
                            'reason': 'sub_verb_unknown',
                            'canonical_hint': _canonical_hint_for_sub_verb(
                                notation, subcommand, known_sub_verbs
                            ),
                            'known_sub_verbs': sorted(known_sub_verbs),
                        },
                    )
                )
                return findings

    # Resolve the leaf parser for flag validation.
    leaf = tree.get_leaf(subcommand, sub_verb)
    if leaf is None:
        return findings

    known_flags = leaf.flags
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
    script_index: dict[str, _ScriptTree],
) -> list[dict]:
    """Scan a markdown body and emit findings for manage-* invocation mismatches.

    The scan operates on *logical* lines — physical lines are first joined
    across backslash continuations so flags written on subsequent lines
    are honored as part of the same invocation. Each notation occurrence
    is validated independently against ``script_index``. Unknown
    notations (not in the whitelist) are skipped. The function is total:
    an empty content body or content with no invocations returns an
    empty list.
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
    script_index: dict[str, _ScriptTree],
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

    The set of in-scope SKILL.md files is the union of skill directories
    referenced by ``IN_SCOPE_SCRIPTS``. The rule is warning-severity: the
    canonical-block convention is the documented contract from D1 of the
    argparse-surface-drift remediation plan, but absence does not break
    runtime — it merely leaves authors without an in-skill reference.
    """
    findings: list[dict] = []
    seen_skill_dirs: set[Path] = set()
    for desc in IN_SCOPE_SCRIPTS:
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
                    f'SKILL.md owns an in-scope `manage-*` / '
                    f'`workflow-integration-*` script '
                    f'(`{desc.notation}`) but lacks a `## Canonical '
                    f'invocations` section'
                ),
                details={
                    'notation': desc.notation,
                    'reason': 'missing_canonical_block',
                    'canonical_hint': (
                        'Add a `## Canonical invocations` section to '
                        f'{desc.skill_dir_relpath}/SKILL.md per the D1 '
                        'spec — one `### subcommand` heading per registered '
                        'argparse top-level subcommand'
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

    Combines findings from the markdown invocation analyzer (per-bundle
    sweep of all SKILL.md / standards / references / workflow / recipes
    markdown files) and the missing-canonical-block check (per in-scope
    SKILL.md).
    """
    findings: list[dict] = []
    bundles_dir = marketplace_root / 'marketplace' / 'bundles'
    if not bundles_dir.is_dir():
        bundles_dir = marketplace_root / 'bundles'
    script_index = build_script_index(marketplace_root)
    if bundles_dir.is_dir():
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
