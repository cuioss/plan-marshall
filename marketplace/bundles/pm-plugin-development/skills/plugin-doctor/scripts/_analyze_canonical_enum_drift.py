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
finding — never to a guessed comparison:

- the owning script file is missing or unparseable;
- the documented flag is never declared with ``choices=`` (a placeholder metavar
  like ``--type TYPE`` makes NO enum claim, so there is nothing to diverge, and a
  free-form flag such as ``--promoted`` documented as ``{true|false}`` has no
  ``choices=`` authority to compare against);
- the flag resolves to MORE THAN ONE distinct ``choices=`` set across the script
  (ambiguous — which subcommand's set is the doc mirroring?);
- a ``choices=`` constant cannot be resolved to a concrete string set
  (cross-module reference whose defining module is absent or ambiguous).

A skip can never produce a false positive. The only cost is a false negative on
an unresolvable site, which the asymmetric-error rule accepts: over-rejecting a
valid, correctly-documented call is the failure this project keeps hitting, and
this guard refuses it by construction.

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
        },
    }

Public API
----------
- ``analyze_canonical_enum_drift(marketplace_root, cache=None)``: entry point.
- ``derive_population(marketplace_root, cache=None)``: every examined enum site
  (the positive-population surface).
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
_ENUM_TOKEN_RE = re.compile(
    r'(?<![A-Za-z0-9])--(?P<flag>[A-Za-z][A-Za-z0-9\-]*)\s+\{(?P<members>[^{}]+)\}'
)

# Builtins that wrap a single sequence without changing its member set, so a
# ``choices=list(FOO)`` / ``choices=sorted(FOO)`` resolves to ``FOO``'s members.
_SEQUENCE_WRAPPERS = frozenset({'list', 'tuple', 'set', 'frozenset', 'sorted'})

# Recursion bound for constant/alias/import following — a defensive cap against a
# pathological alias cycle, well above any real ``choices=`` reference chain.
_MAX_RESOLVE_DEPTH = 8


@dataclass(frozen=True)
class EnumSite:
    """One documented ``--flag {a|b|c}`` enum occurrence in a canonical block.

    ``resolved`` is True when the flag's live ``choices=`` was derived to a
    concrete set; ``diverged`` is True only when ``resolved`` and the documented
    member set differs from the live choices. An unresolved site is neither a
    pass nor a failure — it is examined-but-skipped, and is counted in the
    population so a clean sweep can never be confused with an empty one.
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
        if block_notation is None:
            notation_match = _NOTATION_RE.search(raw)
            if notation_match:
                block_notation = notation_match.group('notation')
                block_path = _extract_subcommand_path(notation_match.group('rest'))
        if block_notation is None:
            # Enum lines before the notation line in a block cannot be attributed;
            # in practice the notation is always the block's first line.
            continue
        for match in _ENUM_TOKEN_RE.finditer(raw):
            members = _split_enum_members(match.group('members'))
            if members:
                sites.append(
                    (line, block_notation, block_path, match.group('flag'), members)
                )
    return sites


def _split_enum_members(raw_members: str) -> frozenset[str]:
    """Split a ``{a|b|c}`` (or comma-separated) metavar body into a member set.

    Pipes are the canonical-block convention; a comma-separated body is accepted
    too. Each member is stripped of whitespace and backticks. An empty result
    (e.g. a placeholder metavar body) yields the empty set, which the caller
    treats as "no enum claim here".
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
    flag whose choices differ per subcommand — or which is free-form in one
    subcommand and constrained in another — is never conflated (the
    ``manage-tasks`` ``--status`` case: ``list`` constrains it, ``update`` does
    not). A value of ``None`` means the ``choices=`` could not be resolved to a
    concrete set (fail-closed); an entry is absent when the flag has no
    ``choices=`` on that parser, which the caller treats as "no enum claim to
    check". A conflicting re-declaration of the same ``(path, flag)`` resolves to
    ``None``.
    """
    parser_paths = _build_parser_path_sets(tree)
    resolved: dict[tuple[tuple[str, ...], str], frozenset[str] | None] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_add_argument(node):
            continue
        receiver = _receiver_name(node)
        if receiver is None or receiver not in parser_paths:
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
    population: list[EnumSite] = []

    for skill_md in _skill_md_files(marketplace_root):
        for line, notation, subcommand, flag, documented in _enum_sites_in_skill(skill_md):
            script_path = _script_path_for_notation(notation, marketplace_root)
            choices: frozenset[str] | None = None
            if script_path is not None:
                if notation not in authority_cache:
                    tree = get_tree(script_path)
                    authority_cache[notation] = (
                        _authority_by_subcommand_flag(tree, resolver)
                        if tree is not None
                        else {}
                    )
                # ``.get`` returns None for both "no choices on this parser" and
                # "choices present but unresolvable" — both are fail-closed skips.
                choices = authority_cache[notation].get((subcommand, flag))
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
        sweep examined — so a clean-but-nonzero result proves coverage.
    """
    population = derive_population(marketplace_root, cache=cache)
    population_size = len(population)
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
                },
                extra={'rule': RULE_NAME},
            )
        )
    return [f.to_dict() for f in findings]
