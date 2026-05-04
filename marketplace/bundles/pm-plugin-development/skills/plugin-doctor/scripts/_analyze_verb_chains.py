#!/usr/bin/env python3
"""AST-based verb-chain scanner for the ``prose-verb-chain-consistency`` rule.

This module implements a lightweight static analyzer that detects stale
script-verb references in plugin skill prose. For every fenced bash block
found in ``SKILL.md`` and ``standards/*.md`` within a skill directory, it
extracts ``python3 .plan/execute-script.py {bundle}:{skill}:{script} {verb}
[{sub_verb}...]`` invocations and verifies each observed verb chain against
the referenced script's registered argparse subparser tree.

Pattern alignment
-----------------
The analyzer mirrors the existing ``argparse_safety`` rule in
``_doctor_analysis.py`` — a lightweight AST walk over script source with:

- no subprocess execution (no ``--help`` fallback)
- no runtime ``import`` of the target script
- no mutation of any file

Detection flow
--------------
1. Enumerate fenced ``bash`` blocks in ``SKILL.md`` and ``standards/*.md``.
2. Parse each fenced block line-by-line, extracting
   ``(bundle, skill, script)`` notation and the trailing verb tokens.
3. Resolve the notation to a script file path under
   ``{marketplace_root}/bundles/{bundle}/skills/{skill}/scripts/{script}.py``.
4. AST-walk the script to build a nested dict modelling the registered
   subparser tree (``add_subparsers`` / ``add_parser('name', ...)``).
5. Walk each observed verb chain against the tree; the first token that
   does not match a registered subparser path is reported as the first
   unknown segment.
6. Honor ``<!-- doctor-ignore: verb-check -->`` markers placed on any line
   preceding a fenced block, provided only whitespace-only lines appear
   between the marker and the opening fence.

Findings have the shape::

    {
        'rule_id': 'prose-verb-chain-consistency',
        'file': '<absolute markdown path>',
        'line': <int, 1-based line of the offending verb token>,
        'script_notation': 'bundle:skill:script',
        'verb_chain': ['verb', 'sub_verb', ...],
        'first_unknown_segment': 'stale_verb',
    }

Public API
----------
- ``analyze_verb_chains(skill_dir)``: entry point — scans one skill dir.
- ``extract_invocations(markdown_path)``: parses fenced bash blocks.
- ``build_subparser_tree(script_path)``: AST-walks a script file.
- ``match_chain(tree, chain)``: validates a verb chain against a tree.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = 'prose-verb-chain-consistency'

# Marker that suppresses the verb-check for the immediately following
# fenced bash block. Comparison is literal (whitespace around the
# HTML comment is allowed, but the inner text must match exactly).
_IGNORE_MARKER = '<!-- doctor-ignore: verb-check -->'

# Fences recognised for bash blocks. ``sh`` and bare ```` ``` ```` are
# intentionally excluded — skill authors use ``bash`` consistently for
# executable snippets, and the narrower scope avoids false positives from
# illustrative blocks that happen to mention ``execute-script.py``.
_BASH_FENCE_OPEN = re.compile(r'^\s*```\s*bash\s*$')
_FENCE_CLOSE = re.compile(r'^\s*```\s*$')

# Matches a single invocation line. Captures (bundle, skill, script, rest).
# ``rest`` contains everything after the notation, including verb tokens,
# flags, and any trailing continuation backslashes. The regex deliberately
# anchors on ``python3 .plan/execute-script.py`` to avoid matching other
# Python invocations.
_INVOCATION_RE = re.compile(
    r'^\s*python3\s+\.plan/execute-script\.py\s+'
    r'(?P<bundle>[A-Za-z0-9_\-]+):'
    r'(?P<skill>[A-Za-z0-9_\-]+):'
    r'(?P<script>[A-Za-z0-9_\-]+)'
    r'(?P<rest>.*)$'
)


# =============================================================================
# Data classes
# =============================================================================


@dataclass(frozen=True)
class Invocation:
    """A single executor invocation observed in a markdown fenced block."""

    markdown_path: Path
    line: int
    bundle: str
    skill: str
    script: str
    verb_chain: tuple[str, ...]

    @property
    def script_notation(self) -> str:
        return f'{self.bundle}:{self.skill}:{self.script}'


@dataclass(frozen=True)
class MatchResult:
    """Outcome of matching a verb chain against a subparser tree."""

    matched: bool
    matched_depth: int
    first_unknown_segment: str | None


# =============================================================================
# Markdown parsing
# =============================================================================


def _strip_line_continuation(rest: str, next_lines: list[str], start_idx: int) -> tuple[str, int]:
    """Join continuation lines (trailing ``\\``) into a single logical line.

    Returns the fully joined ``rest`` string and the index of the last
    consumed line (inclusive). ``next_lines`` is the list of *remaining*
    lines in the fenced block starting at ``start_idx``.
    """
    joined = rest.rstrip()
    consumed = start_idx
    while joined.endswith('\\'):
        joined = joined[:-1].rstrip()
        next_idx = consumed + 1
        if next_idx >= len(next_lines):
            break
        # Continuation lines have their own leading whitespace; collapse
        # to a single space for verb-chain parsing.
        joined = joined + ' ' + next_lines[next_idx].strip()
        consumed = next_idx
    return joined, consumed


def _extract_verb_chain(rest: str) -> tuple[str, ...]:
    """Extract the positional verb chain from the tail of an invocation.

    Stops at the first token that looks like a flag (starts with ``-``),
    a shell redirect/pipe, a variable assignment (``KEY=value`` at
    start), a comment, or an empty token. Verb tokens must be identifier-
    like (letters, digits, underscore, hyphen); anything else terminates
    the chain.
    """
    # Strip inline comments (cheap best-effort; full shell-aware parsing
    # is out of scope — authors don't mix ``#`` into verb lines).
    if '#' in rest:
        # Only treat ``#`` as a comment when preceded by whitespace so we
        # don't mangle URLs or quoted values. Iterate tokens instead.
        pass

    tokens = rest.split()
    chain: list[str] = []
    for tok in tokens:
        # Stop conditions — none of these are verbs.
        if tok.startswith('-'):
            break
        if tok.startswith(('|', '>', '<', '&', ';', '$', '`', '"', "'")):
            break
        if tok == '#' or tok.startswith('#'):
            break
        if '=' in tok:
            # Likely an env assignment (``FOO=bar``) or flag (``--x=y``).
            # Flags are caught above; env assignments terminate the chain.
            break
        # Must be an identifier-like token. Allow letters, digits,
        # underscore, and hyphen — matches the argparse convention for
        # subcommand names (plus CUI-style kebab case).
        if not re.fullmatch(r'[A-Za-z0-9_\-]+', tok):
            break
        chain.append(tok)
    return tuple(chain)


def _find_ignore_marker_before(lines: list[str], fence_idx: int) -> bool:
    """Return ``True`` if an ignore marker precedes the fence at ``fence_idx``.

    The marker must appear on a line before the fence with only
    whitespace-only lines (if any) between it and the opening fence.
    """
    idx = fence_idx - 1
    while idx >= 0:
        stripped = lines[idx].strip()
        if not stripped:
            idx -= 1
            continue
        return stripped == _IGNORE_MARKER
    return False


def extract_invocations(markdown_path: Path) -> list[Invocation]:
    """Parse fenced bash blocks in ``markdown_path`` and extract invocations.

    Non-bash fences are ignored entirely. Blocks preceded by a
    ``<!-- doctor-ignore: verb-check -->`` marker (on a line preceding the
    opening fence, with only whitespace-only lines between) are skipped.

    Returns an empty list for unreadable files.
    """
    try:
        text = markdown_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    invocations: list[Invocation] = []

    idx = 0
    while idx < len(lines):
        if not _BASH_FENCE_OPEN.match(lines[idx]):
            idx += 1
            continue

        fence_idx = idx
        # Locate the closing fence.
        close_idx = fence_idx + 1
        while close_idx < len(lines) and not _FENCE_CLOSE.match(lines[close_idx]):
            close_idx += 1

        if _find_ignore_marker_before(lines, fence_idx):
            idx = close_idx + 1
            continue

        # Walk the fenced content, honoring backslash line continuations.
        block_lines = lines[fence_idx + 1 : close_idx]
        inner_idx = 0
        while inner_idx < len(block_lines):
            raw = block_lines[inner_idx]
            match = _INVOCATION_RE.match(raw)
            if match:
                rest = match.group('rest') or ''
                joined_rest, last_consumed_inner = _strip_line_continuation(rest, block_lines, inner_idx)
                chain = _extract_verb_chain(joined_rest)
                invocations.append(
                    Invocation(
                        markdown_path=markdown_path,
                        # Convert fenced-block index to 1-based file line.
                        line=fence_idx + 1 + inner_idx + 1,
                        bundle=match.group('bundle'),
                        skill=match.group('skill'),
                        script=match.group('script'),
                        verb_chain=chain,
                    )
                )
                inner_idx = last_consumed_inner + 1
            else:
                inner_idx += 1

        idx = close_idx + 1

    return invocations


# =============================================================================
# AST subparser tree
# =============================================================================


def _call_func_name(node: ast.Call) -> str | None:
    """Extract the callable's short name from an ``ast.Call``.

    Handles both ``ArgumentParser(...)`` (``ast.Name``) and
    ``argparse.ArgumentParser(...)`` / ``subparsers.add_parser(...)``
    (``ast.Attribute``) call shapes.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    """Return the first positional ``str`` argument of ``node``, or ``None``."""
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None


def _assign_targets(node: ast.Assign) -> list[str]:
    """Return simple ``ast.Name`` targets of an assignment, as strings."""
    names: list[str] = []
    for target in node.targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
    return names


@dataclass
class _ParserNode:
    """Intermediate record used while building the subparser tree."""

    # Variable name this parser was assigned to (e.g. ``parser``, ``p_refs``).
    var_name: str
    # Child verb → ``_ParserNode`` mapping (populated as we walk the file).
    children: dict[str, _ParserNode] = field(default_factory=dict)


def _collect_assignments(tree: ast.AST) -> list[ast.Assign]:
    """Return all top-level and nested ``ast.Assign`` statements in order."""
    found: list[ast.Assign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            found.append(node)
    # ``ast.walk`` preserves source order for same-depth nodes only
    # approximately; sort by ``lineno`` to ensure deterministic traversal.
    found.sort(key=lambda a: (a.lineno, a.col_offset))
    return found


def _collect_parser_statements(tree: ast.AST) -> list[ast.Assign | ast.Expr]:
    """Return parser-relevant statements in deterministic source order.

    Yields both ``ast.Assign`` nodes (the historical path — captures
    ``parser = ArgumentParser(...)``, ``subparsers = parser.add_subparsers(...)``,
    ``p_verb = subparsers.add_parser('verb', ...)``) AND bare ``ast.Expr``
    nodes whose value is a ``.add_parser('verb', ...)`` ``ast.Call`` whose
    result is discarded (lesson 2026-05-02-10-001 — bare-call form is
    functionally equivalent to the assigned form when the parser needs no
    further configuration).

    Sorted by ``(lineno, col_offset)`` so a bare ``add_parser`` call that
    appears between two assignments is processed in source order, ensuring
    deterministic verb registration even across mixed call shapes.
    """
    found: list[ast.Assign | ast.Expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            found.append(node)
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if _call_func_name(call) == 'add_parser':
                found.append(node)
    found.sort(key=lambda a: (a.lineno, a.col_offset))
    return found


def build_subparser_tree(script_path: Path) -> dict:
    """AST-walk ``script_path`` and return its registered subparser tree.

    The returned dict is nested: each key is a registered verb name and
    each value is a dict of that verb's own sub-verbs (empty when the
    verb is a leaf). Example::

        {
            'add': {},
            'remove': {},
            'get': {
                'field': {},
            },
        }

    The walker recognises two call shapes:

    - ``argparse.ArgumentParser(...)`` / ``ArgumentParser(...)`` assigned
      to a variable → root parser.
    - ``<var>.add_subparsers(...)`` → marks ``<var>`` as the owner of a
      subparser group; the assigned target becomes a "subparsers" handle.
    - ``<subparsers_handle>.add_parser('name', ...)`` → registers child
      verb ``name`` under ``<var>``. Both the assigned form
      (``p_name = subparsers.add_parser('name', ...)``) and the bare
      form (``subparsers.add_parser('name', ...)``) are recognised —
      see lesson 2026-05-02-10-001; the bare form is functionally
      equivalent when the returned parser needs no further configuration.

    Returns an empty dict for unreadable or unparseable files, or for
    scripts that do not use argparse subparsers.
    """
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {}

    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError:
        return {}

    # Map variable name → _ParserNode (any parser-bearing variable).
    parsers: dict[str, _ParserNode] = {}
    # Map subparsers-handle variable → owning parser variable.
    # e.g. ``subparsers = parser.add_subparsers(...)`` registers
    # ``subparsers`` → ``parser``.
    subparsers_handles: dict[str, str] = {}

    for stmt in _collect_parser_statements(tree):
        # Bare-Expr ``.add_parser('verb', ...)`` whose result is discarded
        # — lesson 2026-05-02-10-001. Functionally equivalent to the
        # assigned form for parsers that take no further configuration.
        if isinstance(stmt, ast.Expr):
            call = stmt.value
            assert isinstance(call, ast.Call)  # guaranteed by collector
            bare_handle = _attr_receiver_name(call)
            if bare_handle is None or bare_handle not in subparsers_handles:
                continue
            bare_verb = _first_string_arg(call)
            if not bare_verb:
                continue
            bare_owner_var = subparsers_handles[bare_handle]
            bare_owner = parsers.get(bare_owner_var)
            if bare_owner is None:
                continue
            # No assignment target → register the child verb but don't
            # bind a new parser variable (the result was discarded, so
            # no further nesting can attach to it via the variable path).
            bare_owner.children[bare_verb] = _ParserNode(var_name='')
            continue

        assign = stmt
        if not isinstance(assign.value, ast.Call):
            continue
        call = assign.value
        name = _call_func_name(call)
        if name is None:
            continue

        targets = _assign_targets(assign)
        if not targets:
            continue

        if name in ('ArgumentParser',):
            # Root parser. ``argparse.ArgumentParser(...)`` and plain
            # ``ArgumentParser(...)`` both resolve to ``attr/id ==
            # 'ArgumentParser'`` via ``_call_func_name``.
            for var in targets:
                parsers[var] = _ParserNode(var_name=var)
            continue

        if name == 'add_subparsers':
            # ``<var>.add_subparsers(...)`` — the receiver is the owning
            # parser, and the assignment target becomes the handle used
            # for subsequent ``.add_parser(...)`` calls.
            owner_var = _attr_receiver_name(call)
            if owner_var is None or owner_var not in parsers:
                continue
            for var in targets:
                subparsers_handles[var] = owner_var
            continue

        if name == 'add_parser':
            # ``<handle>.add_parser('verb_name', ...)`` — the receiver
            # must be a known subparsers handle.
            handle_var = _attr_receiver_name(call)
            if handle_var is None or handle_var not in subparsers_handles:
                continue
            verb_name = _first_string_arg(call)
            if not verb_name:
                continue
            owner_var = subparsers_handles[handle_var]
            owner = parsers.get(owner_var)
            if owner is None:
                continue
            child = _ParserNode(var_name=targets[0])
            owner.children[verb_name] = child
            # Register the child as a parser so it can host its own
            # nested subparsers (supports arbitrary depth).
            for var in targets:
                parsers[var] = child
            continue

    # Choose the root parser. Heuristic: the first ``ArgumentParser``
    # assignment wins. Scripts in this marketplace use a single root
    # parser; if there's more than one, the first definition is the
    # authoritative public surface.
    root = _pick_root_parser(tree, parsers)
    if root is None:
        return {}

    return _node_to_dict(root)


def _attr_receiver_name(call: ast.Call) -> str | None:
    """Return the receiver variable name for ``x.method(...)`` calls."""
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    value = func.value
    if isinstance(value, ast.Name):
        return value.id
    return None


def _pick_root_parser(tree: ast.AST, parsers: dict[str, _ParserNode]) -> _ParserNode | None:
    """Pick the root ``_ParserNode`` — the first ``ArgumentParser`` assignment.

    Uses ``_collect_assignments`` (sorted by ``lineno``/``col_offset``) to
    guarantee deterministic source-order traversal. ``ast.walk`` alone does
    not guarantee source order across the tree, so selecting "the first"
    ArgumentParser assignment requires the explicit sort.
    """
    for node in _collect_assignments(tree):
        if not isinstance(node.value, ast.Call):
            continue
        if _call_func_name(node.value) != 'ArgumentParser':
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in parsers:
                return parsers[target.id]
    return None


def _node_to_dict(node: _ParserNode) -> dict:
    """Recursively convert a ``_ParserNode`` into a nested dict of verbs."""
    return {verb: _node_to_dict(child) for verb, child in node.children.items()}


# =============================================================================
# Chain matching
# =============================================================================


def match_chain(tree: dict, chain: list[str] | tuple[str, ...]) -> MatchResult:
    """Match an observed verb ``chain`` against a subparser ``tree``.

    An empty ``chain`` matches trivially (top-level invocations that
    pass no verb are valid for scripts without subparsers, or represent
    a script's default help path). A non-empty chain matches only when
    every segment is registered as a child of the previous level.

    The ``first_unknown_segment`` points to the earliest segment that
    could not be resolved; the segments before it form the longest
    matched prefix, whose length is reported as ``matched_depth``.

    When ``tree`` is empty (e.g., the script uses no subparsers) and
    ``chain`` is non-empty, the first segment is considered unknown —
    callers may choose to treat this as "no subparsers to validate
    against" and skip the finding, but this module reports it honestly
    so the caller can decide per-rule policy.
    """
    if not chain:
        return MatchResult(matched=True, matched_depth=0, first_unknown_segment=None)

    cursor: dict = tree
    depth = 0
    for segment in chain:
        if not isinstance(cursor, dict) or segment not in cursor:
            return MatchResult(
                matched=False,
                matched_depth=depth,
                first_unknown_segment=segment,
            )
        cursor = cursor[segment]
        depth += 1
    return MatchResult(matched=True, matched_depth=depth, first_unknown_segment=None)


# =============================================================================
# Public entry point
# =============================================================================


def _find_marketplace_root(skill_dir: Path) -> Path | None:
    """Walk up from ``skill_dir`` until a ``bundles`` parent is found.

    Returns the ``marketplace`` root (the parent of ``bundles``) or
    ``None`` if the layout does not match. Layout is:
    ``.../marketplace/bundles/{bundle}/skills/{skill}/``.
    """
    current = skill_dir.resolve()
    for ancestor in [current, *current.parents]:
        if ancestor.name == 'bundles' and ancestor.parent.name == 'marketplace':
            return ancestor.parent
    return None


def _resolve_notation(
    bundle: str,
    skill: str,
    script: str,
    marketplace_root: Path,
) -> Path | None:
    """Map ``bundle:skill:script`` to an absolute script path.

    Returns ``None`` when the file does not exist — callers typically
    skip such invocations rather than flagging a finding, because the
    notation itself may be invalid (a separate concern handled by
    ``validate.py references``).
    """
    candidate = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts' / f'{script}.py'
    if candidate.is_file():
        return candidate
    return None


def _markdown_targets(skill_dir: Path) -> list[Path]:
    """Return the markdown files subject to verb-chain scanning.

    Scope: ``SKILL.md`` and ``standards/*.md`` only. Other directories
    (``references/``, ``templates/``, ``workflows/``) are out of scope
    for this rule.
    """
    targets: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)

    standards_dir = skill_dir / 'standards'
    if standards_dir.is_dir():
        for md in sorted(standards_dir.glob('*.md')):
            if md.is_file():
                targets.append(md)

    return targets


def analyze_verb_chains(skill_dir: Path) -> list[dict]:
    """Scan ``skill_dir`` for stale script-verb references in prose.

    Enumerates every invocation in ``SKILL.md`` and ``standards/*.md``,
    resolves each referenced script via its notation, AST-walks the
    resolved script to build a subparser tree, and reports any verb
    chain whose segments are not all registered as subparsers.

    Invocations that reference a script whose file cannot be resolved
    are silently skipped — they represent either a stale notation (out
    of scope here; handled by the executor itself) or a script outside
    the current marketplace tree. The rule does not attempt runtime
    subprocess execution.

    Returns a list of finding dicts. The list is empty for a clean
    skill directory, a directory with no markdown targets, or one
    whose markdown references resolve cleanly.
    """
    marketplace_root = _find_marketplace_root(skill_dir)
    if marketplace_root is None:
        return []

    findings: list[dict] = []
    # Cache subparser trees so a script referenced from multiple files
    # (or multiple times in the same file) is parsed only once.
    tree_cache: dict[Path, dict] = {}

    for md_path in _markdown_targets(skill_dir):
        for inv in extract_invocations(md_path):
            script_path = _resolve_notation(inv.bundle, inv.skill, inv.script, marketplace_root)
            if script_path is None:
                continue

            if script_path not in tree_cache:
                tree_cache[script_path] = build_subparser_tree(script_path)
            subparser_tree = tree_cache[script_path]

            # A script with no subparsers accepts no verb chain. If the
            # caller passed verbs, treat the first one as unknown.
            if not subparser_tree and not inv.verb_chain:
                continue

            result = match_chain(subparser_tree, list(inv.verb_chain))
            if result.matched:
                continue

            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(inv.markdown_path),
                    'line': inv.line,
                    'script_notation': inv.script_notation,
                    'verb_chain': list(inv.verb_chain),
                    'first_unknown_segment': result.first_unknown_segment,
                }
            )

    return findings
