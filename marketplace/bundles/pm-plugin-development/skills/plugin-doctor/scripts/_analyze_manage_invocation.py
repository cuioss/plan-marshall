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

Surface derivation — live ``--help`` ground truth
-------------------------------------------------
The canonical surface for each script is derived from the script's **live
``--help`` interface**, NOT from an AST walk. AST extraction was abandoned
because it could not see subcommands or flags registered through anything
other than literal ``subparsers.add_parser('name')`` /
``parser.add_argument('--flag')`` calls. Real scripts register their surface
through ``for`` loops (``manage-logging`` registers ``work`` / ``decision``
by iterating a list), helper functions (``manage-status`` registers ~20
subcommands via a ``_register`` helper), and shared-flag helpers
(``--plan-id`` / ``--task-number`` added to every subcommand via a common
helper). All of these are INVISIBLE to literal-``add_parser`` AST
extraction, which produced 1323 false positives in plan-marshall alone.

``--help`` renders the real, fully-registered argparse surface regardless of
how the parsers were built, so it is the ground truth.

Cached surface (performance)
----------------------------
Probing ``--help`` requires spawning a subprocess per parser node. A naive
"spawn ``--help`` for every notation on every scan" design caused the test
harness to time out (30s ``subprocess.TimeoutExpired`` against the real
marketplace). The analyzer therefore CACHES each derived surface to disk,
keyed by the script file's content hash:

- ``derive_script_tree(notation, executor)`` first consults an in-process
  memo, then an on-disk cache entry keyed by ``sha256(script_source)``.
- A cache entry is regenerated only when the script's content hash changes
  (i.e. the surface could actually have drifted). Otherwise the cached
  surface is returned with no subprocess at all.
- The on-disk cache lives under ``.plan/temp/plugin-doctor-help-cache/`` so
  it is covered by the standard temp-write permission and never pollutes
  the source tree.

This keeps ``--help`` as ground truth while keeping repeated scans (and the
test harness) fast — no per-scan subprocess storms, no 30s timeouts.

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

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# =============================================================================
# Rule IDs
# =============================================================================

RULE_MANAGE_INVOCATION_INVALID = 'manage-invocation-invalid'
RULE_MISSING_CANONICAL_BLOCK = 'missing-canonical-block'

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


@dataclass
class _LeafParser:
    """One argparse parser node — flags plus any nested subparser children.

    A node is the surface of a single parser at some depth in the argparse
    tree. ``flags`` / ``required_flags`` are its long-flag surface. ``children``
    maps each registered sub-verb name to its own ``_LeafParser`` node; an
    empty ``children`` marks a true leaf (no further subparser dispatch).

    The tree is N-level recursive: argparse permits arbitrarily deep subparser
    chains (e.g. ``manage-config plan phase-5-execute set --field X --value Y``
    is three positional levels deep), and a model that stops at two levels
    mis-resolves the leaf and flags every flag on the third level as unknown —
    the 138-false-positive failure this recursion fixes.
    """

    flags: set[str] = field(default_factory=set)
    required_flags: set[str] = field(default_factory=set)
    children: dict[str, _LeafParser] = field(default_factory=dict)

    def has_children(self) -> bool:
        return bool(self.children)


@dataclass
class _ScriptTree:
    """The full canonical argparse surface for one script.

    ``root`` is the parser node for the root (flags declared on the top-level
    parser before subparser dispatch, plus the top-level subcommands as
    ``root.children``).

    ``subcommands`` is a convenience view over ``root.children`` preserving the
    two-level API used by callers and tests: each top-level subcommand maps to
    either a ``_LeafParser`` (flat) or a ``dict[sub_verb, leaf]`` (nested).
    Deeper levels are reachable via ``root.children[...].children[...]`` and the
    N-level ``resolve_path`` walk.
    """

    root: _LeafParser = field(default_factory=_LeafParser)

    @property
    def subcommands(self) -> dict[str, _LeafParser | dict[str, _LeafParser]]:
        view: dict[str, _LeafParser | dict[str, _LeafParser]] = {}
        for name, child in self.root.children.items():
            if child.has_children():
                view[name] = dict(child.children)
            else:
                view[name] = child
        return view

    def known_subcommands(self) -> set[str]:
        return set(self.root.children.keys())

    def get_leaf(
        self, subcommand: str | None, sub_verb: str | None
    ) -> _LeafParser | None:
        """Resolve a parser node by (subcommand, sub_verb) — two-level API.

        Returns ``None`` when the pair does not resolve. ``subcommand=None``
        targets the root parser. A second positional under a *flat* subcommand
        is treated as a positional argument (the flat node is returned so flag
        validation can still run). Nested subcommands require a registered
        sub_verb. Use ``resolve_path`` for N-level (3+) resolution.
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
    ) -> tuple[_LeafParser | None, str | None, list[str]]:
        """Walk the tree along ``positionals`` as far as registered children go.

        Returns ``(node, unknown_token, chain)``:

        - ``node`` — the deepest resolved parser node whose flags should be
          validated, or ``None`` when a positional names an unregistered child;
        - ``unknown_token`` — the first positional that failed to resolve
          (``None`` on full resolution);
        - ``chain`` — the positional tokens consumed as the subcommand path.

        Per level: if the current node has children, the next positional MUST
        name one (else ``unknown_token`` is set and ``node`` is ``None``); if
        the current node is a flat leaf, remaining positionals are positional
        args and the walk stops there (flag validation still runs).
        """
        node = self.root
        chain: list[str] = []
        for token in positionals:
            if not node.has_children():
                break
            child = node.children.get(token)
            if child is None:
                return None, token, chain
            chain.append(token)
            node = child
        return node, None, chain

    # -- serialization (for the on-disk cache) ------------------------------

    def to_dict(self) -> dict:
        return {'root': _leaf_to_dict(self.root)}

    @classmethod
    def from_dict(cls, data: dict) -> _ScriptTree:
        return cls(root=_leaf_from_dict(data.get('root', {})))


def _leaf_to_dict(leaf: _LeafParser) -> dict:
    return {
        'flags': sorted(leaf.flags),
        'required_flags': sorted(leaf.required_flags),
        'children': {
            name: _leaf_to_dict(child) for name, child in leaf.children.items()
        },
    }


def _leaf_from_dict(data: dict) -> _LeafParser:
    return _LeafParser(
        flags=set(data.get('flags', [])),
        required_flags=set(data.get('required_flags', [])),
        children={
            name: _leaf_from_dict(child)
            for name, child in data.get('children', {}).items()
        },
    )


# =============================================================================
# ``--help`` parsing
# =============================================================================

# The choices set rendered in an argparse usage line / positional block,
# e.g. ``{create,read,transition}``. Captures the comma-separated names.
_CHOICES_RE = re.compile(r'\{([^{}]+)\}')

# A long flag as it appears in the ``options:`` block, anchored to the
# leading two-space indent argparse uses for option entries.
_OPTION_FLAG_RE = re.compile(r'^\s{2,}(--[A-Za-z][A-Za-z0-9_\-]*)')

# A long flag anywhere (used when scanning the usage line for required-ness).
_USAGE_FLAG_RE = re.compile(r'(?<![A-Za-z0-9])--([A-Za-z][A-Za-z0-9_\-]*)')


def _split_help_sections(help_text: str) -> tuple[str, list[str]]:
    """Split ``--help`` output into (usage_block, body_lines).

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


def _parse_subcommand_choices(help_text: str) -> list[str]:
    """Return the top-level subcommand names from ``--help`` output.

    A script publishes subcommands iff its usage line contains a
    ``{a,b,c} ...`` choices group whose trailing ``...`` marks a subparser
    dispatch. The choices set is the literal, fully-registered set of
    subcommands regardless of how they were registered (loop / helper /
    literal).
    """
    usage_block, _ = _split_help_sections(help_text)
    # The subparser choices group is the one immediately followed by ``...``
    # in the usage line. Find each ``{...}`` and check whether ``...`` trails.
    for match in _CHOICES_RE.finditer(usage_block):
        tail = usage_block[match.end():].lstrip()
        if tail.startswith('...'):
            names = [n.strip() for n in match.group(1).split(',')]
            return [n for n in names if n]
    return []


def _parse_leaf_flags(help_text: str) -> _LeafParser:
    """Parse the flag surface of a single leaf parser from its ``--help``.

    - ``flags``: every long flag rendered in the ``options:`` block, minus
      the always-present ``--help``.
    - ``required_flags``: the subset that appears un-bracketed in the usage
      line (argparse wraps optional flags in ``[...]``).
    """
    usage_block, body = _split_help_sections(help_text)

    flags: set[str] = set()
    for line in body:
        m = _OPTION_FLAG_RE.match(line)
        if m:
            name = m.group(1)[2:]
            if name != 'help':
                flags.add(name)

    required = _parse_required_flags(usage_block)
    # Only flags that are actually declared count as required.
    required &= flags
    return _LeafParser(flags=flags, required_flags=required)


def _parse_required_flags(usage_block: str) -> set[str]:
    """Return long flags that argparse renders as individually required.

    A flag is individually required iff it appears in the usage line OUTSIDE
    any grouping construct. argparse uses two grouping constructs:

    - ``[...]`` — optional flags / optional groups;
    - ``(...)`` — a *required mutually-exclusive group* (e.g.
      ``(--set KEY=VALUE | --get FIELD | --list)``). Exactly one member is
      required, but NO individual member is — so flagging any of them as a
      missing required flag is a false positive (the canonical
      ``metadata --set k=v`` shape tripped exactly this).

    Stripping every balanced ``[...]`` AND ``(...)`` group leaves only the
    bare, individually-required tokens; any ``--flag`` remaining there is
    required.
    """
    stripped = _strip_grouping_constructs(usage_block)
    required = {m.group(1) for m in _USAGE_FLAG_RE.finditer(stripped)}
    required.discard('help')
    return required


def _strip_grouping_constructs(text: str) -> str:
    """Remove balanced ``[...]`` and ``(...)`` groups (nesting-aware).

    Characters inside any grouping construct are dropped; everything else is
    kept. The two bracket families are tracked with a single depth counter
    because argparse never interleaves them in a way that would require
    independent tracking — a ``(...)`` group only ever nests ``[...]`` and
    vice versa, never a mismatched close. Unbalanced trailing openers consume
    to end-of-string.
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


# =============================================================================
# Live ``--help`` probing with caching
# =============================================================================

_HELP_TIMEOUT_SECONDS = 15

# Concurrency cap for surface derivation. The work is subprocess-bound (each
# worker blocks on a ``--help`` child), so the cap may exceed the CPU count
# without starving compute; the ceiling keeps the number of simultaneously
# spawned child processes well within OS limits. The same cap bounds both the
# script-level fan-out (``build_script_index``) and the per-level subcommand
# fan-out (``_derive_node``).
_MAX_DERIVE_WORKERS = min(16, (os.cpu_count() or 4) * 2)

# Global ceiling on concurrently-running ``--help`` subprocesses. Derivation
# parallelizes on two independent axes — across scripts and across a node's
# subcommands — using separate short-lived pools (never one shared bounded
# pool), which is deadlock-free because no worker ever blocks waiting for a
# task in its own pool. This semaphore is acquired only around the actual
# subprocess in ``_run_help`` (a leaf operation that always completes and
# releases), so it caps real process concurrency without reintroducing the
# nested-pool wait-on-self hazard.
_HELP_SEMAPHORE = threading.BoundedSemaphore(_MAX_DERIVE_WORKERS)

# In-process memo: keyed by (notation, content_hash) -> _ScriptTree.
# Survives for the lifetime of the process so repeated scans within one
# analyze pass never re-probe the same surface.
_TREE_MEMO: dict[tuple[str, str], _ScriptTree] = {}


def _content_hash(script_path: Path) -> str | None:
    try:
        data = script_path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _resolve_executor(marketplace_root: Path) -> Path | None:
    """Locate a ``.plan/execute-script.py`` executor relative to the root.

    Candidates, in order:
      - ``{marketplace_root}/.plan/execute-script.py``
      - ``{marketplace_root.parent}/.plan/execute-script.py``

    The second candidate covers callers that pass the inner ``marketplace``
    directory (which directly contains ``bundles/``) as the root.
    """
    for base in (marketplace_root, marketplace_root.parent):
        candidate = base / '.plan' / 'execute-script.py'
        if candidate.is_file():
            return candidate
    return None


def _cache_dir(executor: Path) -> Path:
    """The on-disk cache directory, anchored next to the executor.

    The executor always lives at ``{root}/.plan/execute-script.py``; the
    cache lives at ``{root}/.plan/temp/plugin-doctor-help-cache/`` so it is
    covered by the standard ``.plan/**`` temp-write permission.
    """
    plan_dir = executor.parent
    return plan_dir / 'temp' / 'plugin-doctor-help-cache'


def _cache_path(executor: Path, notation: str, content_hash: str) -> Path:
    safe = notation.replace(':', '__')
    return _cache_dir(executor) / f'{safe}.{content_hash}.json'


def _read_cache(cache_path: Path) -> _ScriptTree | None:
    try:
        data = json.loads(cache_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    try:
        return _ScriptTree.from_dict(data)
    except (KeyError, TypeError):
        return None


def _write_cache(cache_path: Path, tree: _ScriptTree) -> None:
    import tempfile

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            'w', dir=str(cache_path.parent), delete=False, encoding='utf-8'
        ) as tf:
            json.dump(tree.to_dict(), tf, sort_keys=True)
            tmp = Path(tf.name)
        os.replace(str(tmp), str(cache_path))
        tmp = None
    except OSError:
        # The cache is a pure optimization — a write failure must never break
        # the analysis. Skip silently.
        pass
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _run_help(executor: Path, notation: str, *positionals: str) -> str | None:
    """Run ``{executor} {notation} {positionals...} --help`` and return stdout.

    Returns ``None`` when the probe fails (non-zero exit, timeout, missing
    interpreter). The synthetic test executor and the real executor both
    forward the target's ``--help`` output verbatim on stdout.
    """
    cmd = [sys.executable, str(executor), notation, *positionals, '--help']
    try:
        with _HELP_SEMAPHORE:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_HELP_TIMEOUT_SECONDS,
            )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    if not result.stdout or 'usage:' not in result.stdout:
        return None
    return result.stdout


# Hard ceiling on recursion depth — argparse subparser chains never approach
# this in practice; the bound only guards against a pathological/self-referential
# --help that would otherwise spawn subprocesses without end.
_MAX_TREE_DEPTH = 6


def _derive_tree_uncached(executor: Path, notation: str) -> _ScriptTree | None:
    """Probe ``--help`` recursively and build the full N-level surface.

    One subprocess for the top-level surface, then one per subcommand at every
    depth — recursing as long as a node's ``--help`` renders a ``{...} ...``
    subparser choices group. This is the cache-miss path; cache hits never
    reach it. The whole derived tree is cached as a unit, so the recursion cost
    is paid once per script-content-hash.
    """
    top_help = _run_help(executor, notation)
    if top_help is None:
        return None
    root = _derive_node(executor, notation, [], top_help, depth=0)
    return _ScriptTree(root=root)


def _derive_node(
    executor: Path,
    notation: str,
    path: list[str],
    help_text: str,
    *,
    depth: int,
) -> _LeafParser:
    """Build one parser node from its ``--help``, recursing into children.

    ``path`` is the positional chain from the root to this node (empty for the
    root). ``help_text`` is this node's already-probed ``--help`` output. Each
    registered child is probed with ``{notation} {path...} {child} --help`` and
    recursively expanded.
    """
    node = _parse_leaf_flags(help_text)
    if depth >= _MAX_TREE_DEPTH:
        return node

    child_names = _parse_subcommand_choices(help_text)
    if not child_names:
        return node

    def _derive_child(child_name: str) -> tuple[str, _LeafParser]:
        child_help = _run_help(executor, notation, *path, child_name)
        if child_help is None:
            # Could not probe the child — register it as a flat leaf with no
            # flag surface so the child name itself is not falsely flagged as
            # unknown, but its flags cannot be validated.
            return child_name, _LeafParser()
        return child_name, _derive_node(
            executor,
            notation,
            [*path, child_name],
            child_help,
            depth=depth + 1,
        )

    # Probe a node's subcommands concurrently. Without this, a deeply-nested
    # script (e.g. ``manage-config plan phase-{phase} {get|set}``) serializes
    # dozens of ``--help`` subprocesses and alone overruns the build gate's
    # budget — it then never completes, never caches, and re-derives on every
    # scan. Each node gets its own short-lived pool; recursion nests pools
    # along the tree depth, but the global ``_HELP_SEMAPHORE`` (acquired only
    # around the leaf subprocess) caps real process concurrency, and no worker
    # blocks on a task in its own pool, so the fan-out is deadlock-free.
    workers = min(len(child_names), _MAX_DERIVE_WORKERS)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for child_name, child_node in pool.map(_derive_child, child_names):
            node.children[child_name] = child_node
    return node


def derive_script_tree(notation: str, executor: Path) -> _ScriptTree | None:
    """Cached ``--help`` derivation of one script's canonical surface.

    Resolution order:
      1. in-process memo keyed by ``(notation, content_hash)``;
      2. on-disk cache keyed by the same hash;
      3. live ``--help`` probe (cache miss), then populate both caches.

    The content hash is computed from the script file resolved relative to
    the executor's repository root. When the script file cannot be located,
    derivation falls back to probing without a hash key (memoized by
    notation alone for the process lifetime) — the surface is still derived
    from live ``--help``, only the on-disk cache is skipped.

    Returns ``None`` when the surface cannot be probed (unreachable notation,
    non-zero exit, timeout). Callers treat ``None`` as "no surface" and skip
    validation for that notation — never as a false positive.
    """
    script_path = _script_path_for_notation(notation, executor)
    content_hash = _content_hash(script_path) if script_path is not None else None

    if content_hash is not None:
        memo_key = (notation, content_hash)
        cached = _TREE_MEMO.get(memo_key)
        if cached is not None:
            return cached

        cache_path = _cache_path(executor, notation, content_hash)
        on_disk = _read_cache(cache_path)
        if on_disk is not None:
            _TREE_MEMO[memo_key] = on_disk
            return on_disk

        tree = _derive_tree_uncached(executor, notation)
        if tree is None:
            return None
        _TREE_MEMO[memo_key] = tree
        _write_cache(cache_path, tree)
        return tree

    # No locatable script file — derive live, skip the on-disk cache. The memo
    # key MUST incorporate the executor path, NOT the notation alone: a single
    # process may probe several DISTINCT scripts that all resolve through the
    # SAME notation but different executors (the test suite maps one synthetic
    # ``_SYN_NOTATION`` to a different script per ``tmp_path`` executor). Keying
    # by ``(notation, '')`` made the first-derived tree poison every later
    # probe of the same notation — the cross-fixture memo collision that turned
    # ``qgate``/``other`` and the loop-registered surfaces into the first
    # fixture's ``foo``/``bar``. Folding the executor path into the key
    # disambiguates them; production callers always have a content hash and
    # never reach this branch.
    memo_key = (notation, f'executor::{executor}')
    cached = _TREE_MEMO.get(memo_key)
    if cached is not None:
        return cached
    tree = _derive_tree_uncached(executor, notation)
    if tree is None:
        return None
    _TREE_MEMO[memo_key] = tree
    return tree


def _script_path_for_notation(notation: str, executor: Path) -> Path | None:
    """Resolve the on-disk script file for a notation, for content hashing.

    Searches both supported layouts relative to the executor's repository
    root (``{root}`` is the executor's ``.plan`` parent). Returns ``None``
    when the file cannot be found — derivation then skips the on-disk cache.
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


def build_script_index(marketplace_root: Path) -> dict[str, _ScriptTree]:
    """Build a notation -> canonical-surface index for every in-scope script.

    The surface is derived via the cached ``--help`` probe against the
    executor discovered relative to ``marketplace_root``. When no executor is
    reachable the index is empty — the surface cannot be probed, so no
    findings are emitted (no false positives). Notations whose ``--help`` is
    unreachable are silently dropped.

    Derivation runs concurrently across scripts: each ``derive_script_tree``
    call is independent (distinct notation -> distinct memo key, on-disk cache
    file, and probe subprocesses), and the per-script ``--help`` probes are
    subprocess-bound (the worker blocks on I/O, releasing the GIL). A cold-cache
    marketplace-wide scan otherwise serializes hundreds of ``--help``
    subprocesses and overruns the build gate's budget; fanning the scripts out
    keeps the wall-clock bounded by the slowest single script, not their sum.
    Parallelism is applied only at the script level — subcommand recursion
    inside a single tree stays serial, so the bounded pool never waits on
    itself (no nested-pool deadlock).
    """
    executor = _resolve_executor(marketplace_root)
    if executor is None:
        return {}
    descriptors = discover_in_scope_scripts(marketplace_root)
    if not descriptors:
        return {}

    def _derive(desc: _ScriptDescriptor) -> tuple[str, _ScriptTree | None]:
        return desc.notation, derive_script_tree(desc.notation, executor)

    workers = min(len(descriptors), _MAX_DERIVE_WORKERS)
    index: dict[str, _ScriptTree] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for notation, tree in pool.map(_derive, descriptors):
            if tree is not None:
                index[notation] = tree
    return index


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
