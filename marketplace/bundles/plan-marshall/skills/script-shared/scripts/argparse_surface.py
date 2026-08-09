#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared, help-derived, alias-aware derivation of a script's argparse accept-set.

This is the SINGLE derivation of "what does this script accept?" in the tree.
Two consumers read it and neither carries its own copy:

- ``pm-plugin-development:plugin-doctor`` — the ``ARGUMENT_NAMING_*`` cluster
  and the ``manage-invocation-invalid`` rule, at edit time.
- ``plan-marshall:tools-script-executor`` — the executor generator, which
  embeds the derived surfaces so the executor can reject an invalid invocation
  before it spawns anything.

Mechanism — live ``--help``, never an AST walk
---------------------------------------------
The surface of one script is derived by running that script with ``--help``,
then recursing into each discovered verb (``{script} {verb} --help``, and
deeper for nested verb trees such as ``manage-config plan phase-3-outline
get``). The script's own argparse instance renders the answer, so a parser
assembled in an IMPORTED module is covered exactly like a parser built inline.

A static ``add_parser`` AST walk cannot do this. It is blind to subcommands
registered through a ``for`` loop, through a helper function, or through a
parser built in another module, and blind to ``aliases=`` entirely. That
mechanism produced 1323 false positives in ``plan-marshall`` alone before it
was abandoned; it is deliberately NOT retained here as a fallback, because a
too-small accept-set is strictly more dangerous than no accept-set — it
rejects valid calls.

Four parse anchors
------------------
=========================== ================================ ==========================
Anchor                      Rendered by argparse as          Used for
=========================== ================================ ==========================
Choice list                 ``{prepare-add,...,read,get}``   acceptance set (exact)
Per-verb listing line       ``read (get)``                   canonical/alias grouping
Long-option tokens          ``--plan-id PLAN_ID``            flag set (over-approx.)
Section headers             ``options:`` etc.                structural evidence
=========================== ================================ ==========================

**Aliases** are recovered two-tier by design. The choice list is the
acceptance oracle and carries aliases FLAT — argparse populates the subparser
action's ``choices`` from its name-to-parser map, which holds every alias as a
key — so acceptance needs no alias reasoning at all. The ``read (get)``
grouping line is rendered only when ``add_parser`` was given ``help=``, so it
is optional enrichment used solely to phrase a corrective. The dangerous
inversion (an alias in the grouping line but absent from the acceptance set)
cannot occur, because the grouping line is never read to NARROW the set.

Asymmetric-error rule (normative)
---------------------------------
Every parse ambiguity resolves in the direction that WIDENS the accept-set or
ABANDONS the node — never in the direction that narrows it. Concretely:

- Flags are harvested as every ``--long-token`` anywhere in the output rather
  than scoped to the ``options:`` section, because a flag declared in a custom
  argument group renders under that group's own title and a section-scoped scan
  would silently omit it and reject a valid call. Over-collecting a flag only
  ever accepts more.
- The choice list is read from the ``positional arguments:`` section AND the
  usage line, and the two are UNIONED. argparse wraps the usage line but never
  wraps an action's invocation string, so the section is the more reliable
  source; unioning them cannot lose a name either way.
- Confidence is POSITIVE, not residual: a node is confident only when the
  required structural evidence is FOUND. Help output with no recognisable
  argparse structure yields :class:`NotDerivable` — never an empty-but-confident
  surface.

Fail-closed-on-uncertainty invariant (normative)
------------------------------------------------
A script whose help output cannot be parsed into a confident surface must be
treated by every consumer as "no surface" — it spawns / is skipped exactly as
today and is NEVER rejected. Every uncertainty path routes to
:class:`NotDerivable`: non-zero exit from ``--help``, empty output, timeout, no
recognisable structure, depth/node cap reached, or total-budget exhaustion.

Uncertainty is granular, so a partial result is never promoted into a whole
one. A node whose child listing is unconfident carries
``children_confident=False``, which stops verb-path validation at that node; a
node whose flag set is unknown carries ``flags_confident=False``, which skips
flag validation while leaving verb validation intact where the listing WAS
confident.

Caching
-------
Probing ``--help`` spawns a subprocess per parser node, so derivation is cached
on two levels, keyed by the script file's content hash:

1. an in-process memo keyed by ``(notation, content_hash)``;
2. an on-disk JSON cache under ``{root}/.plan/temp/plugin-doctor-help-cache/``,
   covered by the standard ``.plan/**`` temp-write permission.

The cache filename folds in :data:`CACHE_VERSION`, bumped whenever the
derivation logic changes in a way that invalidates prior entries. A derivation
that FAILS drops the entry rather than resurrecting a stale cached surface —
the very edit that broke the help may be the edit that changed the surface.

Bounding
--------
:class:`DerivationConfig` exposes the per-invocation timeout, the worker count,
the depth and node caps, and a total wall-clock budget as parameters, so the
generator and plugin-doctor bound themselves differently without a second
implementation.

Public API
----------
- :class:`ParserNode` — one argparse parser node (flags, required flags,
  children, alias grouping, per-node confidence).
- :class:`ScriptSurface` — the full surface for one script, with the N-level
  ``resolve_path`` walk and JSON (de)serialization.
- :class:`NotDerivable` — the explicit "no confident surface" result.
- :class:`DerivationConfig` — the bounding parameters.
- :func:`derive_surface` — cached derivation of one script's surface.
- :func:`build_surface_index` — notation -> surface index, derived in parallel.
- :func:`resolve_executor` — locate ``.plan/execute-script.py`` from a root.
- :func:`parse_help_node` / :func:`parse_choice_list` / :func:`parse_alias_groups`
  — the pure parsers, exposed for testing against synthetic help text.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeGuard

# =============================================================================
# Configuration
# =============================================================================

# Concurrency cap for surface derivation. The work is subprocess-bound (each
# worker blocks on a ``--help`` child), so the cap may exceed the CPU count
# without starving compute; the ceiling keeps the number of simultaneously
# spawned child processes well within OS limits.
DEFAULT_MAX_WORKERS = min(16, (os.cpu_count() or 4) * 2)

# Bumped whenever the derivation logic changes in a way that invalidates
# previously cached entries. Folded into the cache filename so stale entries
# become cache misses and are re-derived.
#
# v3: consolidation into this shared module — adds alias grouping, per-node
# confidence flags, whole-output flag harvesting (asymmetric-error rule), and
# the positional-arguments-section choice list.
CACHE_VERSION = 3


@dataclass(frozen=True)
class DerivationConfig:
    """Bounds on one derivation run.

    Every field is a bound, never a behaviour switch: tightening any of them
    can only turn a confident surface into :class:`NotDerivable`, never into a
    smaller-but-confident one. That is what lets the generator and plugin-doctor
    pick different values without disagreeing about what a script accepts.
    """

    timeout_seconds: float = 15.0
    max_workers: int = DEFAULT_MAX_WORKERS
    max_depth: int = 6
    max_nodes: int = 512
    total_budget_seconds: float | None = None
    # Fixed wide terminal for the child so argparse cannot wrap a construct
    # across lines. Deterministic rendering is a parse precondition, not a
    # cosmetic choice.
    help_columns: int = 400
    use_disk_cache: bool = True


DEFAULT_CONFIG = DerivationConfig()


# =============================================================================
# Surface model
# =============================================================================


@dataclass
class ParserNode:
    """One argparse parser node — flags plus any nested subparser children.

    ``flags`` / ``required_flags`` are this node's long-flag surface.
    ``children`` maps every registered child spelling — canonical names AND
    alias spellings alike, exactly as the choice list renders them — to its own
    node, so acceptance is a plain membership test. ``alias_of`` maps an alias
    spelling to its canonical spelling and exists ONLY to phrase correctives;
    it is never consulted to decide acceptance.

    The two confidence flags are independent on purpose. ``flags_confident``
    false means "this node's flag surface is unknown, skip flag validation";
    ``children_confident`` false means "this node's child listing is unknown,
    stop verb-path validation here". Collapsing them into one would let an
    unknown flag set suppress verb validation that WAS confidently derived.
    """

    flags: set[str] = field(default_factory=set)
    required_flags: set[str] = field(default_factory=set)
    children: dict[str, ParserNode] = field(default_factory=dict)
    alias_of: dict[str, str] = field(default_factory=dict)
    flags_confident: bool = True
    children_confident: bool = True

    def has_children(self) -> bool:
        return bool(self.children)

    def canonical_spelling(self, name: str) -> str:
        """Return the canonical spelling of child ``name`` (itself when canonical)."""
        return self.alias_of.get(name, name)

    def alias_group(self, canonical: str) -> list[str]:
        """Return the alias spellings registered for canonical child ``canonical``."""
        return sorted(a for a, c in self.alias_of.items() if c == canonical)


@dataclass
class ScriptSurface:
    """The full canonical argparse surface for one script.

    ``root`` is the parser node for the top-level parser: flags declared before
    subparser dispatch, plus the top-level subcommands as ``root.children``.
    Deeper levels are reachable through ``root.children[...].children[...]`` and
    the N-level :meth:`resolve_path` walk — argparse permits arbitrarily deep
    subparser chains (``manage-config plan phase-5-execute set --field X`` is
    three positional levels deep), and a model that stops at two levels
    mis-resolves the leaf and flags every third-level flag as unknown.
    """

    root: ParserNode = field(default_factory=ParserNode)

    @property
    def subcommands(self) -> dict[str, ParserNode | dict[str, ParserNode]]:
        """Two-level convenience view over ``root.children``."""
        view: dict[str, ParserNode | dict[str, ParserNode]] = {}
        for name, child in self.root.children.items():
            if child.has_children():
                view[name] = dict(child.children)
            else:
                view[name] = child
        return view

    def known_subcommands(self) -> set[str]:
        """Every accepted top-level spelling — canonical names and aliases alike."""
        return set(self.root.children.keys())

    def get_leaf(
        self, subcommand: str | None, sub_verb: str | None
    ) -> ParserNode | None:
        """Resolve a parser node by ``(subcommand, sub_verb)`` — two-level API.

        Returns ``None`` when the pair does not resolve. ``subcommand=None``
        targets the root parser. A second positional under a FLAT subcommand is
        a positional argument, so the flat node is returned and flag validation
        still runs. Use :meth:`resolve_path` for N-level (3+) resolution.
        """
        if subcommand is None:
            return self.root
        node = self.root.children.get(subcommand)
        if node is None:
            return None
        if not node.has_children():
            return node
        if sub_verb is None:
            return None
        return node.children.get(sub_verb)

    def resolve_path(
        self, positionals: list[str]
    ) -> tuple[ParserNode | None, str | None, list[str]]:
        """Walk the tree along ``positionals`` as far as registered children go.

        Returns ``(node, unknown_token, chain)``:

        - ``node`` — the deepest resolved node whose flags should be validated,
          or ``None`` when a positional names an unregistered child;
        - ``unknown_token`` — the first positional that failed to resolve
          (``None`` on full resolution);
        - ``chain`` — the positional tokens consumed as the subcommand path.

        Per level: when the current node has children, the next positional MUST
        name one — unless the node's child listing is not confident, in which
        case the walk stops rather than reporting an unknown token (fail-closed
        on uncertainty: an unconfident listing may simply be missing the name).
        When the current node is a flat leaf, remaining positionals are
        positional arguments and the walk stops there.
        """
        node = self.root
        chain: list[str] = []
        for token in positionals:
            if not node.has_children():
                break
            child = node.children.get(token)
            if child is None:
                if not node.children_confident:
                    break
                return None, token, chain
            chain.append(token)
            node = child
        return node, None, chain

    # -- serialization (on-disk cache and executor embedding) ----------------

    def to_dict(self) -> dict:
        return {'root': _node_to_dict(self.root)}

    @classmethod
    def from_dict(cls, data: dict) -> ScriptSurface:
        return cls(root=_node_from_dict(data.get('root', {})))


@dataclass(frozen=True)
class NotDerivable:
    """The explicit "no confident surface" result.

    Returned instead of an empty :class:`ScriptSurface` so a caller can never
    read "I could not derive this" as "this script accepts nothing". ``reason``
    names which uncertainty path fired, for diagnostics only — every reason has
    the same consequence: the consumer must skip validation for this notation.
    """

    notation: str
    reason: str


#: Reason codes carried by :class:`NotDerivable`.
REASON_HELP_FAILED = 'help_failed'
REASON_NO_STRUCTURE = 'no_structure'
REASON_BUDGET_EXHAUSTED = 'budget_exhausted'
REASON_SCRIPT_UNRESOLVED = 'script_unresolved'


def is_derivable(result: ScriptSurface | NotDerivable) -> TypeGuard[ScriptSurface]:
    """True when ``result`` is a usable surface rather than a not-derivable marker.

    Declared as a ``TypeGuard`` so a caller that checks it can then read the
    surface without a second ``isinstance`` — the type checker enforces that
    nobody reaches ``root`` / ``resolve_path`` on a not-derivable result.
    """
    return isinstance(result, ScriptSurface)


def _node_to_dict(node: ParserNode) -> dict:
    return {
        'flags': sorted(node.flags),
        'required_flags': sorted(node.required_flags),
        'alias_of': dict(sorted(node.alias_of.items())),
        'flags_confident': node.flags_confident,
        'children_confident': node.children_confident,
        'children': {
            name: _node_to_dict(child) for name, child in node.children.items()
        },
    }


def _node_from_dict(data: dict) -> ParserNode:
    return ParserNode(
        flags=set(data.get('flags', [])),
        required_flags=set(data.get('required_flags', [])),
        alias_of=dict(data.get('alias_of', {})),
        flags_confident=bool(data.get('flags_confident', True)),
        children_confident=bool(data.get('children_confident', True)),
        children={
            name: _node_from_dict(child)
            for name, child in data.get('children', {}).items()
        },
    )


# =============================================================================
# ``--help`` parsing (pure — no subprocess)
# =============================================================================

# A brace-delimited choices set, e.g. ``{create,read,transition}``.
_CHOICES_RE = re.compile(r'\{([^{}]+)\}')

# A long flag anywhere in the output. Deliberately unanchored: see the
# asymmetric-error rule — a flag declared in a custom argument group renders
# under that group's own title, and a section-scoped scan would omit it.
_ANY_LONG_FLAG_RE = re.compile(r'(?<![A-Za-z0-9])--([A-Za-z][A-Za-z0-9_\-]*)')

# The per-verb listing line argparse renders when ``add_parser`` was given
# ``help=`` AND ``aliases=``: ``    read (get)          Read a task``. The
# canonical name and its comma-separated alias list, at the start of a line.
_ALIAS_GROUP_RE = re.compile(
    r'^\s+(?P<canonical>[A-Za-z][A-Za-z0-9_\-]*)\s+'
    r'\((?P<aliases>[A-Za-z][A-Za-z0-9_\-]*(?:\s*,\s*[A-Za-z][A-Za-z0-9_\-]*)*)\)'
)

# Section headers argparse renders. Their presence is the positive structural
# evidence that this output is argparse help at all.
_SECTION_HEADERS: tuple[str, ...] = (
    'positional arguments:',
    'options:',
    'optional arguments:',
)

# ANSI CSI escape sequences — the SGR color codes Python 3.14 wraps around
# ``usage:``, subcommand choices, and ``--flag`` tokens in colorized argparse
# help. Stripped before parsing so a subprocess that ignores the color-
# suppression env pins cannot defeat the plain-text regexes.
_ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')


def strip_ansi(text: str) -> str:
    """Remove ANSI CSI escape sequences from ``text``."""
    return _ANSI_ESCAPE_RE.sub('', text)


def split_help_sections(help_text: str) -> tuple[str, list[str]]:
    """Split ``--help`` output into ``(usage_block, body_lines)``.

    The usage block is everything from the ``usage:`` line up to (but not
    including) the first blank line. The body is the remaining lines.
    """
    lines = help_text.splitlines()
    usage_lines: list[str] = []
    body_start = 0
    in_usage = False
    for i, line in enumerate(lines):
        if not in_usage and line.startswith('usage:'):
            in_usage = True
        if in_usage:
            if line.strip() == '':
                body_start = i
                break
            usage_lines.append(line)
        else:
            body_start = i + 1
    else:
        body_start = len(lines)
    return ' '.join(usage_lines), lines[body_start:]


def has_argparse_structure(help_text: str) -> bool:
    """True when ``help_text`` carries positive evidence of argparse help.

    Confidence is positive, not residual: a body with no ``usage:`` line and no
    recognised section header is not "an argparse parser that declares nothing",
    it is output this module does not understand.
    """
    if 'usage:' not in help_text:
        return False
    lowered = help_text.lower()
    return any(header in lowered for header in _SECTION_HEADERS)


def _positional_section_lines(body: list[str]) -> list[str]:
    """Return the lines of the ``positional arguments:`` section, if present."""
    collected: list[str] = []
    in_section = False
    for line in body:
        stripped = line.strip().lower()
        if stripped in _SECTION_HEADERS:
            in_section = stripped == 'positional arguments:'
            continue
        if in_section:
            collected.append(line)
    return collected


def parse_choice_list(help_text: str) -> list[str]:
    """Return every accepted child spelling from ``--help`` output.

    Two steps, in this order and NOT interchangeable:

    1. **Detect dispatch from the usage line.** A node publishes subcommands
       iff its usage line carries a ``{a,b,c} ...`` group whose trailing ``...``
       marks a subparser dispatch. That trailing ellipsis is the only reliable
       discriminator between a subparser action and a plain positional declared
       with ``choices=`` — both render as ``{a,b,c}`` in the positional section.
       When no dispatch is detected the node has NO children, full stop.
    2. **Widen the names from the positional section.** Once dispatch IS
       confirmed, any ``{a,b,c}`` group in the ``positional arguments:`` section
       contributes its names too.

    The asymmetric-error rule cuts BOTH ways here, which is why the two steps
    are asymmetric themselves. Widening the child NAME set within a confirmed
    dispatch is safe — it accepts more spellings. Widening the "does this node
    dispatch at all?" decision is NOT: a node wrongly given children starts
    demanding a registered sub-verb, and a plain ``choices=`` positional would
    then make every valid call look like an unknown sub-verb. So the detection
    stays on the strict marker and only the name set is widened.

    Aliases appear flat alongside canonical names, which is why acceptance
    needs no alias reasoning at all. Order is first-seen so the derived surface
    is deterministic across runs.
    """
    usage_block, body = split_help_sections(help_text)

    names: list[str] = []
    seen: set[str] = set()

    def _absorb(group: str) -> None:
        for raw in group.split(','):
            name = raw.strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)

    dispatches = False
    for match in _CHOICES_RE.finditer(usage_block):
        if usage_block[match.end():].lstrip().startswith('...'):
            dispatches = True
            _absorb(match.group(1))

    if not dispatches:
        return []

    for line in _positional_section_lines(body):
        for match in _CHOICES_RE.finditer(line):
            _absorb(match.group(1))

    return names


def parse_alias_groups(help_text: str) -> dict[str, str]:
    """Return ``{alias_spelling: canonical_spelling}`` from the per-verb listing.

    Read ONLY from the ``read (get)`` grouping lines, which argparse renders
    only when ``add_parser`` was given ``help=``. This is optional enrichment
    used to phrase a corrective — it is never consulted to decide acceptance, so
    its absence costs nothing but a less specific message.
    """
    _usage, body = split_help_sections(help_text)
    alias_of: dict[str, str] = {}
    for line in _positional_section_lines(body):
        match = _ALIAS_GROUP_RE.match(line)
        if match is None:
            continue
        canonical = match.group('canonical')
        for alias in match.group('aliases').split(','):
            spelling = alias.strip()
            if spelling and spelling != canonical:
                alias_of[spelling] = canonical
    return alias_of


def strip_grouping_constructs(text: str) -> str:
    """Remove balanced ``[...]`` and ``(...)`` groups (nesting-aware).

    Characters inside any grouping construct are dropped. The two bracket
    families share one depth counter because argparse never interleaves them in
    a way that would require independent tracking. Unbalanced trailing openers
    consume to end-of-string.
    """
    out: list[str] = []
    depth = 0
    for ch in text:
        if ch in '[(':
            depth += 1
        elif ch in '])':
            if depth > 0:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return ''.join(out)


def parse_required_flags(usage_block: str) -> set[str]:
    """Return long flags argparse renders as INDIVIDUALLY required.

    A flag is individually required iff it appears in the usage line outside any
    grouping construct. argparse uses two:

    - ``[...]`` — optional flags / optional groups;
    - ``(...)`` — a required mutually-exclusive group (``(--set K=V | --get F)``).
      Exactly one member is required but NO individual member is, so reporting
      any of them as missing is a false positive.

    Stripping every balanced ``[...]`` AND ``(...)`` leaves only the bare,
    individually-required tokens.
    """
    stripped = strip_grouping_constructs(usage_block)
    required = {m.group(1) for m in _ANY_LONG_FLAG_RE.finditer(stripped)}
    required.discard('help')
    return required


def parse_help_node(help_text: str) -> ParserNode:
    """Parse one parser node's own surface from its ``--help`` output.

    Children are NOT populated here — the caller recurses. Both confidence
    flags are set from positive structural evidence:

    - ``flags_confident`` — the output has recognisable argparse structure, so
      an empty flag set means "declares no long flags", not "could not tell";
    - ``children_confident`` — same evidence; an empty child list from a
      structurally-recognised help means "declares no subparsers".

    Flags are harvested from the WHOLE output (usage line and body alike) per
    the asymmetric-error rule: a flag declared in a custom argument group
    renders under that group's own title, and omitting it would reject a valid
    call. Over-collecting only ever accepts more.
    """
    structured = has_argparse_structure(help_text)
    usage_block, _body = split_help_sections(help_text)

    flags = {m.group(1) for m in _ANY_LONG_FLAG_RE.finditer(help_text)}
    flags.discard('help')

    required = parse_required_flags(usage_block) & flags

    return ParserNode(
        flags=flags,
        required_flags=required,
        flags_confident=structured,
        children_confident=structured,
    )


# =============================================================================
# Executor / script resolution and hashing
# =============================================================================


def resolve_executor(marketplace_root: Path) -> Path | None:
    """Locate a ``.plan/execute-script.py`` executor relative to ``marketplace_root``.

    Candidates, in order: ``{marketplace_root}/.plan/execute-script.py``, then
    ``{marketplace_root.parent}/.plan/execute-script.py``. The second covers
    callers that pass the inner ``marketplace`` directory (the one that directly
    contains ``bundles/``) as the root.
    """
    for base in (marketplace_root, marketplace_root.parent):
        candidate = base / '.plan' / 'execute-script.py'
        if candidate.is_file():
            return candidate
    return None


def script_path_for_notation(notation: str, executor: Path) -> Path | None:
    """Resolve the on-disk script file for ``notation``, for content hashing.

    Searches both supported layouts relative to the executor's repository root
    (``{root}`` is the executor's ``.plan`` parent). Returns ``None`` when the
    file cannot be found — derivation then skips the on-disk cache.
    """
    try:
        bundle, skill, script = notation.split(':', 2)
    except ValueError:
        return None
    root = executor.parent.parent  # {root}/.plan/execute-script.py -> {root}
    candidates = (
        root / 'marketplace' / 'bundles' / bundle / 'skills' / skill / 'scripts' / f'{script}.py',
        root / 'bundles' / bundle / 'skills' / skill / 'scripts' / f'{script}.py',
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def content_hash(script_path: Path) -> str | None:
    """Cache key covering ``script_path`` AND every ``*.py`` beside it.

    Deliberately NOT the script file alone. A script's argparse surface is
    frequently assembled in a SIBLING module — ``ci.py`` delegates its whole
    parser to ``ci_base.py`` — so a key over the entry point only goes stale
    exactly where the derivation is most valuable: edit the sibling, and a
    script-only key hands back a cached surface describing the parser that used
    to exist.

    Over-invalidating (an unrelated edit in the same directory re-derives)
    costs time. Under-invalidating costs correctness — a stale accept-set
    rejects a call that is now valid — so the key is deliberately coarse.

    Returns ``None`` only when the script file itself is unreadable, which is
    the signal to skip the on-disk cache entirely.
    """
    try:
        data = script_path.read_bytes()
    except OSError:
        return None
    hasher = hashlib.sha256()
    hasher.update(data)
    try:
        siblings = sorted(script_path.parent.glob('*.py'))
    except OSError:
        siblings = []
    for sibling in siblings:
        hasher.update(sibling.name.encode('utf-8'))
        try:
            hasher.update(sibling.read_bytes())
        except OSError:
            hasher.update(b'<unreadable>')
    return hasher.hexdigest()


# =============================================================================
# Caching
# =============================================================================

# In-process memo, keyed by ``(notation, cache_key)``. Survives for the process
# lifetime so repeated scans never re-probe the same surface.
_SURFACE_MEMO: dict[tuple[str, str], ScriptSurface] = {}


def clear_memo() -> None:
    """Drop the in-process memo. For tests that vary a script between probes."""
    _SURFACE_MEMO.clear()


def _cache_dir(executor: Path) -> Path:
    """The on-disk cache directory, anchored next to the executor.

    The executor always lives at ``{root}/.plan/execute-script.py``; the cache
    lives at ``{root}/.plan/temp/plugin-doctor-help-cache/`` so it is covered by
    the standard ``.plan/**`` temp-write permission and never pollutes the
    source tree.
    """
    return executor.parent / 'temp' / 'plugin-doctor-help-cache'


def _cache_path(executor: Path, notation: str, digest: str) -> Path:
    safe = notation.replace(':', '__')
    return _cache_dir(executor) / f'{safe}.v{CACHE_VERSION}.{digest}.json'


def _read_cache(cache_path: Path) -> ScriptSurface | None:
    try:
        data = json.loads(cache_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    try:
        return ScriptSurface.from_dict(data)
    except (KeyError, TypeError):
        return None


def _write_cache(cache_path: Path, surface: ScriptSurface) -> None:
    """Atomically write ``surface`` to ``cache_path``. Failures are swallowed.

    The cache is a pure optimization — a write failure must never break the
    analysis, so every OSError path is silent.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            'w', dir=str(cache_path.parent), delete=False, encoding='utf-8'
        ) as handle:
            json.dump(surface.to_dict(), handle, sort_keys=True)
            tmp = Path(handle.name)
        os.replace(str(tmp), str(cache_path))
        tmp = None
    except OSError:
        pass
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


# =============================================================================
# Live ``--help`` probing
# =============================================================================

# Global ceiling on concurrently-running ``--help`` subprocesses. Derivation
# parallelizes on two independent axes — across scripts and across a node's
# subcommands — using separate short-lived pools rather than one shared bounded
# pool, which is deadlock-free because no worker ever blocks waiting for a task
# in its own pool. This semaphore is acquired only around the actual subprocess
# (a leaf operation that always completes and releases), so it caps real process
# concurrency without reintroducing the nested-pool wait-on-self hazard.
_HELP_SEMAPHORE = threading.BoundedSemaphore(DEFAULT_MAX_WORKERS)


def _help_env(config: DerivationConfig) -> dict[str, str]:
    """Environment for a ``--help`` probe: colors off, terminal width pinned.

    Mirrors the executor front-door color pins so the probe emits plain text
    even when invoked directly. Python 3.14's ``can_colorize()`` consults
    ``PYTHON_COLORS``, then ``NO_COLOR``, then ``FORCE_COLOR``; ``NO_COLOR``
    overrides ``FORCE_COLOR`` and ``PYTHON_COLORS=0`` is the explicit override.
    ``COLUMNS`` is pinned wide so argparse cannot wrap a construct across lines
    — deterministic rendering is a parse precondition.
    """
    env = os.environ.copy()
    env['PYTHON_COLORS'] = '0'
    env['NO_COLOR'] = '1'
    env.pop('FORCE_COLOR', None)
    env['CLICOLOR'] = '0'
    env['CLICOLOR_FORCE'] = '0'
    env['PY_COLORS'] = '0'
    env['COLUMNS'] = str(config.help_columns)
    return env


def run_help(
    executor: Path,
    notation: str,
    *positionals: str,
    config: DerivationConfig = DEFAULT_CONFIG,
) -> str | None:
    """Run ``{executor} {notation} {positionals...} --help`` and return stdout.

    Returns ``None`` on every failure path — non-zero exit, timeout, missing
    interpreter, empty output, or output with no ``usage:`` line. Captured
    stdout is ANSI-stripped before the ``usage:`` check so colorized help never
    defeats the plain-text surface regexes.
    """
    cmd = [sys.executable, str(executor), notation, *positionals, '--help']
    try:
        with _HELP_SEMAPHORE:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                env=_help_env(config),
            )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    stdout = strip_ansi(result.stdout) if result.stdout else result.stdout
    if not stdout or 'usage:' not in stdout:
        return None
    return stdout


class _Budget:
    """Per-script node and wall-clock bounds, shared across the recursion.

    Both caps are checked at the same place — before spending a subprocess on a
    child — so exhaustion always resolves to "this node's child listing is not
    confident" rather than to a silently truncated accept-set.
    """

    def __init__(self, config: DerivationConfig) -> None:
        self._remaining_nodes = config.max_nodes
        self._deadline: float | None = (
            time.monotonic() + config.total_budget_seconds
            if config.total_budget_seconds is not None
            else None
        )
        self._lock = threading.Lock()
        self.exhausted = False

    def take_node(self) -> bool:
        """Claim budget for one more ``--help`` probe. False when exhausted."""
        with self._lock:
            if self._deadline is not None and time.monotonic() >= self._deadline:
                self.exhausted = True
                return False
            if self._remaining_nodes <= 0:
                self.exhausted = True
                return False
            self._remaining_nodes -= 1
            return True


def _derive_node(
    executor: Path,
    notation: str,
    path: list[str],
    help_text: str,
    *,
    depth: int,
    config: DerivationConfig,
    budget: _Budget,
) -> ParserNode:
    """Build one parser node from its ``--help``, recursing into children.

    ``path`` is the positional chain from the root to this node (empty for the
    root). Each registered child is probed with ``{notation} {path...} {child}
    --help`` and recursively expanded.

    Every abandonment path — depth cap, node/time budget, an unprobeable child —
    marks the affected node ``children_confident=False`` rather than returning a
    smaller confident listing. That is the asymmetric-error rule at the
    recursion boundary: a caller must not read a truncated walk as a complete
    accept-set.
    """
    node = parse_help_node(help_text)
    child_names = parse_choice_list(help_text)
    node.alias_of = parse_alias_groups(help_text)

    if not child_names:
        return node

    if depth >= config.max_depth:
        node.children_confident = False
        return node

    def _derive_child(child_name: str) -> tuple[str, ParserNode | None]:
        if not budget.take_node():
            return child_name, None
        child_help = run_help(executor, notation, *path, child_name, config=config)
        if child_help is None:
            return child_name, None
        return child_name, _derive_node(
            executor,
            notation,
            [*path, child_name],
            child_help,
            depth=depth + 1,
            config=config,
            budget=budget,
        )

    # Probe a node's subcommands concurrently. Without this, a deeply-nested
    # script (``manage-config plan phase-{phase} {get|set}``) serializes dozens
    # of ``--help`` subprocesses and alone overruns the build gate's budget.
    # Each node gets its own short-lived pool; recursion nests pools along the
    # tree depth, but ``_HELP_SEMAPHORE`` (held only around the leaf subprocess)
    # caps real process concurrency and no worker blocks on a task in its own
    # pool, so the fan-out is deadlock-free.
    workers = max(1, min(len(child_names), config.max_workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for child_name, child_node in pool.map(_derive_child, child_names):
            if child_node is None:
                # The child NAME is accepted (the choice list is the acceptance
                # oracle and it is confident here), but its own surface could
                # not be probed. Register it as a flat node whose flag set and
                # child listing are both unknown, so validation stops at it
                # instead of rejecting anything under it.
                node.children[child_name] = ParserNode(
                    flags_confident=False, children_confident=False
                )
                continue
            node.children[child_name] = child_node
    return node


def _derive_surface_uncached(
    executor: Path,
    notation: str,
    config: DerivationConfig,
) -> ScriptSurface | NotDerivable:
    """Probe ``--help`` recursively and build the full N-level surface."""
    budget = _Budget(config)
    if not budget.take_node():
        return NotDerivable(notation=notation, reason=REASON_BUDGET_EXHAUSTED)
    top_help = run_help(executor, notation, config=config)
    if top_help is None:
        return NotDerivable(notation=notation, reason=REASON_HELP_FAILED)
    if not has_argparse_structure(top_help):
        return NotDerivable(notation=notation, reason=REASON_NO_STRUCTURE)
    root = _derive_node(
        executor, notation, [], top_help, depth=0, config=config, budget=budget
    )
    return ScriptSurface(root=root)


def derive_surface(
    notation: str,
    executor: Path,
    *,
    config: DerivationConfig = DEFAULT_CONFIG,
    cache_key: str | None = None,
) -> ScriptSurface | NotDerivable:
    """Cached ``--help`` derivation of one script's canonical surface.

    Resolution order:

    1. in-process memo keyed by ``(notation, cache_key)``;
    2. on-disk cache keyed by the same key (skipped when
       ``config.use_disk_cache`` is false);
    3. live ``--help`` probe, then populate both caches.

    A derivation that FAILS returns :class:`NotDerivable` and writes nothing —
    a stale cached surface is never resurrected by a failed re-derivation,
    because the very edit that broke the help may be the edit that changed the
    surface.

    ``cache_key`` lets a caller whose own invalidation model is WIDER than this
    module's supply it, so the two cannot disagree about when a surface went
    stale. The executor generator does exactly that: its digest also covers the
    injected shared-module directories, and without threading that key through,
    a shared-module edit would invalidate the generator's entry while this
    module's cache kept handing back the surface derived before it. Omitting it
    falls back to :func:`content_hash` (the script plus its sibling modules).

    When the script file cannot be located and no ``cache_key`` was supplied,
    derivation still runs live but skips the on-disk cache. The memo key then
    folds in the EXECUTOR path rather than the notation alone: one process may
    probe several distinct scripts that all resolve through the same notation
    under different executors (the test suite maps one synthetic notation to a
    different script per ``tmp_path``), and keying by notation alone would let
    the first-derived surface poison every later probe.
    """
    if cache_key is not None:
        digest: str | None = cache_key
    else:
        script_file = script_path_for_notation(notation, executor)
        digest = content_hash(script_file) if script_file is not None else None

    if digest is not None:
        memo_key = (notation, digest)
        memoized = _SURFACE_MEMO.get(memo_key)
        if memoized is not None:
            return memoized

        cache_path = _cache_path(executor, notation, digest)
        if config.use_disk_cache:
            on_disk = _read_cache(cache_path)
            if on_disk is not None:
                _SURFACE_MEMO[memo_key] = on_disk
                return on_disk

        derived = _derive_surface_uncached(executor, notation, config)
        if not isinstance(derived, ScriptSurface):
            return derived
        _SURFACE_MEMO[memo_key] = derived
        if config.use_disk_cache:
            _write_cache(cache_path, derived)
        return derived

    memo_key = (notation, f'executor::{executor}')
    memoized = _SURFACE_MEMO.get(memo_key)
    if memoized is not None:
        return memoized
    derived = _derive_surface_uncached(executor, notation, config)
    if not isinstance(derived, ScriptSurface):
        return derived
    _SURFACE_MEMO[memo_key] = derived
    return derived


def build_surface_index(
    notations: list[str],
    executor: Path,
    *,
    config: DerivationConfig = DEFAULT_CONFIG,
    cache_keys: dict[str, str] | None = None,
) -> dict[str, ScriptSurface | NotDerivable]:
    """Derive surfaces for ``notations`` in parallel.

    ``cache_keys`` optionally supplies a per-notation cache key, forwarded to
    :func:`derive_surface` — see its docstring for why a caller with a wider
    invalidation model must thread its own key through rather than let the two
    caches disagree.

    Every notation gets an entry — a :class:`ScriptSurface` or an explicit
    :class:`NotDerivable`. Callers that want only usable surfaces filter with
    :func:`is_derivable`; callers that need to REPORT coverage (how many
    notations landed in each bucket) read both, which is why a not-derivable
    notation is never silently dropped here.

    Derivation runs concurrently across scripts: each call is independent
    (distinct notation → distinct memo key, cache file, and probe subprocesses)
    and the probes are subprocess-bound, so the worker blocks on I/O and
    releases the GIL. A cold marketplace-wide scan otherwise serializes
    hundreds of ``--help`` subprocesses; fanning the scripts out keeps the
    wall-clock bounded by the slowest single script, not their sum.
    """
    if not notations:
        return {}

    def _derive(notation: str) -> tuple[str, ScriptSurface | NotDerivable]:
        key = cache_keys.get(notation) if cache_keys else None
        return notation, derive_surface(notation, executor, config=config, cache_key=key)

    workers = max(1, min(len(notations), config.max_workers))
    index: dict[str, ScriptSurface | NotDerivable] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for notation, result in pool.map(_derive, notations):
            index[notation] = result
    return index
