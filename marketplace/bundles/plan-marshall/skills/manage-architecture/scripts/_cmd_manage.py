#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Manage command handlers for architecture script.

Handles: discover, init, derived, derived-module

Persistence model: per-module on-disk layout under
``.plan/project-architecture/`` consisting of a top-level ``_project.json``
plus per-module ``enriched.json`` files. ``derived.json`` is ephemeral —
computed on demand by ``crawl_module_derived``; ``api_discover`` no longer
writes it to disk. ``api_discover()`` still writes via the tmp+swap protocol
so an interrupted discover run never leaves a half-written tree behind.
"""

import argparse
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import _descriptor_delta as delta
from _architecture_core import (
    GENERATION_FIELD,
    LEGACY_CONCEPT_TYPE,
    DataNotFoundError,
    InvalidConceptTypeError,
    ModuleNotFoundInProjectError,
    _write_json,
    crawl_all_modules,
    error_result_module_not_found,
    get_data_dir,
    get_module_enriched_path,
    get_project_meta_path,
    get_tmp_data_dir,
    iter_modules,
    load_module_enriched,
    load_module_enriched_or_empty,
    load_project_meta,
    migrate_key_packages,
    require_project_meta_result,
    save_module_enriched,
    save_project_meta,
    stamp_concept_document,
    swap_data_dir,
    sync_module_index,
    unknown_generation,
)
from constants import (
    DIR_PER_MODULE_ENRICHED,
    FILE_PROJECT_META,
)

# =============================================================================
# Files-Inventory Post-Processor
# =============================================================================

# Per-category cap. Above this number, a category list is replaced by the
# elision shape ``{"elided": <count>, "sample": [<stride-sampled paths>]}``.
# The cap is 2000 (raised from 500 — this repo's ``test`` category alone
# exceeds 500, which is what put the elision horizon inside everyday queries).
# The ``sample`` is a DISTRIBUTED STRIDE over the sorted list, never a
# contiguous alphabetical prefix, so it spans the full sorted range and carries
# no contiguous blind spot. The AUTHORITATIVE protection against a confident
# false negative is the reader-side self-scan in
# ``_cmd_client_handlers._resolve_module_inventory`` (deliverable 1); this cap
# and its strided sample are defense-in-depth only, never the guarantee.
_FILES_CATEGORY_CAP = 2000
_FILES_ELISION_SAMPLE_SIZE = 100

# Universal ignore set — directory names that are never useful in an
# inventory regardless of whether the project ships a ``.gitignore``.
_FILES_ALWAYS_IGNORED_DIRS = frozenset(
    {
        '.git',
        '__pycache__',
        'node_modules',
        'target',
        '.venv',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        '.idea',
        '.pyprojectx',
        'htmlcov',
    }
)

# Hidden files allowed in the inventory despite the dotfile-skip rule.
_FILES_DOTFILE_ALLOWLIST = frozenset({'.gitignore', '.editorconfig'})

# Marketplace-specific category list. Modules outside ``marketplace/bundles/``
# fall back to the generic set (``build_file``, ``doc``, ``script``, ``source``,
# ``test``). Every category either classifier may emit is declared once in
# ``_architecture_core.FILE_CATEGORIES``.
_FILES_BUILD_FILES = frozenset({'pyproject.toml', 'package.json', 'pom.xml', 'plugin.json'})
_FILES_GENERIC_SOURCE_EXTS = frozenset(
    {'.py', '.java', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.kt', '.c', '.cpp', '.h', '.hpp', '.cs'}
)
_FILES_GENERIC_SCRIPT_EXTS = frozenset({'.sh', '.bash', '.zsh'})
# Bounded, declared doc-extension set for the generic peer. Deliberately NOT a
# residual rule — see :func:`_classify_generic` for why generic mode stays
# extension-driven while the marketplace peer is extension-free.
_FILES_GENERIC_DOC_EXTS = frozenset({'.md', '.adoc', '.asciidoc'})

_MARKETPLACE_BUNDLE_PREFIX = 'marketplace/bundles/'


def _gitignore_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile one ``.gitignore`` pattern to a regex that matches POSIX-style paths.

    The matcher is intentionally minimal — enough to handle the patterns the
    repo's own ``.gitignore`` and typical bundle ``.gitignore`` files use:
    leading ``/`` anchors to the gitignore file's directory, ``**/`` matches
    any number of intermediate path segments, ``*`` matches within a segment,
    ``?`` matches one non-separator char, trailing ``/`` is handled by the
    caller (dir-only flag).
    """
    anchored = pattern.startswith('/')
    if anchored:
        pattern = pattern[1:]
    has_slash = '/' in pattern  # mid-pattern slash also anchors

    parts: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == '*':
            if i + 1 < n and pattern[i + 1] == '*':
                # `**` — match across path separators.
                if i + 2 < n and pattern[i + 2] == '/':
                    parts.append('(?:.*/)?')
                    i += 3
                else:
                    parts.append('.*')
                    i += 2
            else:
                parts.append('[^/]*')
                i += 1
        elif c == '?':
            parts.append('[^/]')
            i += 1
        else:
            parts.append(re.escape(c))
            i += 1
    body = ''.join(parts)
    if anchored or has_slash:
        regex = f'^{body}(?:/.*)?$'
    else:
        regex = f'(?:^|.*/){body}(?:/.*)?$'
    return re.compile(regex)


def _load_gitignore(path: Path) -> list[tuple[re.Pattern[str], bool, bool]]:
    """Read one ``.gitignore`` file into ``(regex, is_negation, dir_only)`` tuples."""
    if not path.exists() or path.is_symlink():
        return []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return []
    rules: list[tuple[re.Pattern[str], bool, bool]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        is_neg = line.startswith('!')
        if is_neg:
            line = line[1:]
        dir_only = line.endswith('/')
        if dir_only:
            line = line[:-1]
        if not line:
            continue
        try:
            regex = _gitignore_pattern_to_regex(line)
        except re.error:
            continue
        rules.append((regex, is_neg, dir_only))
    return rules


def _is_ignored_by_rules(
    rel_path: str,
    is_dir: bool,
    rules: list[tuple[re.Pattern[str], bool, bool]],
) -> bool:
    """Apply ``.gitignore`` rules with last-match-wins semantics."""
    ignored = False
    for regex, is_neg, dir_only in rules:
        if dir_only and not is_dir:
            continue
        if regex.match(rel_path):
            ignored = not is_neg
    return ignored


def _is_marketplace_bundle_module(module_data: dict[str, Any]) -> bool:
    """Decide whether a module's paths.module sits under ``marketplace/bundles/``.

    Marketplace-specific categories (``skill``/``agent``/``command``/...) only
    apply when the module's root is inside a marketplace bundle directory.
    """
    paths = module_data.get('paths') or {}
    module_rel = paths.get('module') or ''
    if not module_rel:
        return False
    # Normalise the path string — remove an exact leading ``./`` and use POSIX
    # separators. ``removeprefix`` rather than a character-set strip: the latter
    # takes a SET OF CHARACTERS, not a prefix, so it eats every leading ``.``
    # and ``/`` and would rewrite ``.plan/x`` into ``plan/x`` — a different path
    # that could then match the bundle prefix by accident.
    rel = Path(module_rel).as_posix().removeprefix('./')
    # A traversal segment is refused outright rather than normalised away: a
    # path that climbs out of the tree is not a marketplace bundle module, and
    # answering True for one would extend bundle-only classification to a file
    # outside ``marketplace/bundles/``.
    if '..' in rel.split('/'):
        return False
    return rel.startswith(_MARKETPLACE_BUNDLE_PREFIX) or rel == _MARKETPLACE_BUNDLE_PREFIX.rstrip('/')


def _classify_marketplace(rel_from_module: str, basename: str) -> str | None:
    """Return the marketplace category for ``rel_from_module`` or None to skip.

    ``rel_from_module`` is the file path relative to the module root, in POSIX
    form. ``basename`` is the final path component.
    """
    parts = rel_from_module.split('/')

    # skills/<skill>/SKILL.md
    if len(parts) >= 3 and parts[0] == 'skills' and basename == 'SKILL.md':
        return 'skill'

    # skills/<skill>/scripts/**/*.{py,sh}
    if (
        len(parts) >= 4
        and parts[0] == 'skills'
        and parts[2] == 'scripts'
        and (basename.endswith('.py') or basename.endswith('.sh'))
    ):
        return 'script'

    # skills/<skill>/standards/**/*.md
    if len(parts) >= 4 and parts[0] == 'skills' and parts[2] == 'standards' and basename.endswith('.md'):
        return 'standard'

    # skills/<skill>/templates/**/*
    if len(parts) >= 4 and parts[0] == 'skills' and parts[2] == 'templates':
        return 'template'

    # agents/<name>.md (immediate child)
    if len(parts) == 2 and parts[0] == 'agents' and basename.endswith('.md'):
        return 'agent'

    # commands/<name>.md (immediate child)
    if len(parts) == 2 and parts[0] == 'commands' and basename.endswith('.md'):
        return 'command'

    # build files anywhere
    if basename in _FILES_BUILD_FILES:
        return 'build_file'

    # doc files anywhere
    if basename.startswith('README') or basename.startswith('CHANGELOG'):
        return 'doc'

    # Residual: every remaining file under ``skills/<skill>/**`` is skill-owned
    # reference material. The rule is deliberately RESIDUAL ON BOTH AXES — it
    # names no sub-directory and tests no extension — so a seventh sub-directory
    # kind or a fifth file format cannot reopen the inventory blind spot. This
    # mirrors the ``skills/<skill>/templates/**`` rule above, which is likewise
    # extension-free. Placement is load-bearing: it must stay LAST so the
    # build-file and README/CHANGELOG tests above keep classifying those files
    # as ``build_file`` / ``doc`` even when they sit under a skill directory.
    if len(parts) >= 3 and parts[0] == 'skills':
        return 'skill_doc'

    return None


def _classify_generic(rel_from_module: str, basename: str) -> str | None:
    """Return the generic category for ``rel_from_module`` or None to skip.

    This peer stays EXTENSION-DRIVEN by design — unlike
    :func:`_classify_marketplace`, whose residual rule is extension-free. In an
    arbitrary project a file's path position carries no role guarantee, so an
    extension-free residual here would sweep binaries, lockfiles and generated
    artefacts into ``doc``. The generic peer therefore keeps a bounded, declared
    extension set.
    """
    if basename in _FILES_BUILD_FILES:
        return 'build_file'

    suffix = Path(basename).suffix.lower()
    if suffix in _FILES_GENERIC_DOC_EXTS:
        return 'doc'

    if suffix in _FILES_GENERIC_SCRIPT_EXTS:
        return 'script'
    if suffix in _FILES_GENERIC_SOURCE_EXTS:
        # Decide test-vs-source from path conventions.
        parts = rel_from_module.split('/')
        if any(p in {'test', 'tests', '__tests__'} for p in parts[:-1]):
            return 'test'
        if basename.startswith('test_') or basename.endswith('_test.py') or '.test.' in basename:
            return 'test'
        return 'source'
    return None


def _join_rel_path(parent: str, name: str) -> str:
    """Join a parent project-relative path with a child name.

    Returns POSIX-style paths so the regex matcher always sees ``a/b/c``
    regardless of host OS. Treats ``''`` and ``'.'`` as project-root
    sentinels — the join collapses to just ``name`` instead of ``./name``.
    """
    if parent in {'', '.'}:
        return name
    return (Path(parent) / name).as_posix()


def _walk_module_root(
    module_root: Path,
    project_path: Path,
    project_root_rules: list[tuple[re.Pattern[str], bool, bool]],
) -> list[tuple[str, str]]:
    """Walk ``module_root`` honouring gitignore. Return ``(rel_from_module, basename)``.

    Symlinks are skipped (both files and dirs). Dotfiles are skipped except
    for the allowlist (``.gitignore``, ``.editorconfig``). Always-ignored
    directories are skipped unconditionally. Per-directory ``.gitignore``
    files contribute additional rules below their owning directory.
    """
    if not module_root.exists() or not module_root.is_dir() or module_root.is_symlink():
        return []

    results: list[tuple[str, str]] = []

    # Stack of (current_dir, rules_in_effect, rel_from_project, rel_from_module).
    # Rules are accumulated as we descend so a child .gitignore augments the
    # parent set without mutating it. ``module_root`` and ``project_path`` are
    # already resolved by the caller (``_post_process_files``); resolving them
    # again here would be redundant.
    initial_rel = module_root.relative_to(project_path).as_posix()
    stack: list[tuple[Path, list[tuple[re.Pattern[str], bool, bool]], str]] = [
        (module_root, list(project_root_rules), initial_rel)
    ]

    while stack:
        current, rules_in, rel_from_project = stack.pop()
        # Augment rules with the current directory's .gitignore (if any).
        local_rules = _load_gitignore(current / '.gitignore')
        rules = rules_in + local_rules if local_rules else rules_in

        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue

        for entry in entries:
            name = entry.name
            if entry.is_symlink():
                continue
            if name.startswith('.') and name not in _FILES_DOTFILE_ALLOWLIST:
                # Hidden files/dirs — skip unless explicitly allowed.
                if name in _FILES_ALWAYS_IGNORED_DIRS:
                    continue
                # Generic dotfile — skip silently.
                if entry.is_dir():
                    continue
                continue
            if entry.is_dir():
                if name in _FILES_ALWAYS_IGNORED_DIRS:
                    continue
                child_rel_from_project = _join_rel_path(rel_from_project, name)
                if _is_ignored_by_rules(child_rel_from_project, True, rules):
                    continue
                stack.append((entry, rules, child_rel_from_project))
                continue
            # File entry.
            child_rel_from_project = _join_rel_path(rel_from_project, name)
            if _is_ignored_by_rules(child_rel_from_project, False, rules):
                continue
            try:
                rel_from_module = entry.relative_to(module_root).as_posix()
            except ValueError:
                # Symlink-like indirection escaped the module — skip defensively.
                continue
            results.append((rel_from_module, name))

    return results


def _apply_category_cap(paths: list[str]) -> list[str] | dict[str, Any]:
    """Apply the per-category cap. Below the cap return ``paths`` verbatim.

    Above the cap, return the elision shape whose ``sample`` is a DISTRIBUTED
    STRIDE over the sorted list — ``paths[::stride][:size]`` — rather than the
    contiguous alphabetical prefix. The stride preserves sorted order and the
    ``_FILES_ELISION_SAMPLE_SIZE`` length while spanning the full range, so the
    sample's first and last entries bracket the category and no contiguous
    horizon is created. This is defense-in-depth; the reader-side self-scan
    (``_cmd_client_handlers._resolve_module_inventory``) is the authoritative
    false-negative guard.
    """
    if len(paths) <= _FILES_CATEGORY_CAP:
        return paths
    stride = max(1, len(paths) // _FILES_ELISION_SAMPLE_SIZE)
    return {
        'elided': len(paths),
        'sample': paths[::stride][:_FILES_ELISION_SAMPLE_SIZE],
    }


def build_module_files_inventory(
    module_data: dict[str, Any],
    project_path: Path,
    project_root_rules: list[tuple[re.Pattern[str], bool, bool]],
) -> dict[str, list[str]]:
    """Return one module's UNCAPPED ``category -> sorted paths`` inventory.

    The per-module categorisation body of :func:`_post_process_files`, extracted
    so a reader that finds an elided category can re-run the SAME
    git-ignore-aware walk uncapped instead of trusting the writer's capped
    sample. Walks ``paths.module`` (and any ``paths.tests`` outside the module
    root for marketplace bundles), classifies every non-ignored file with the
    same marketplace-vs-generic decision, and returns the deterministically
    byte-wise-sorted map WITHOUT applying :func:`_apply_category_cap`.

    :func:`_post_process_files` applies the cap per category on top of this map;
    the reader seam ``_cmd_client_handlers._resolve_module_inventory`` consumes
    it uncapped for a self-scan. A module with no ``paths.module`` yields an
    empty dict. ``project_path`` and ``project_root_rules`` are resolved once by
    the caller and threaded through.
    """
    paths = module_data.get('paths') or {}
    module_rel = paths.get('module') or ''
    if not module_rel:
        return {}

    is_marketplace = _is_marketplace_bundle_module(module_data)

    # Resolve the module root and (if outside the root) any extra test dirs.
    module_root = (project_path / module_rel).resolve()
    roots: list[tuple[Path, bool]] = [(module_root, False)]
    seen_roots: set[Path] = {module_root}
    for tests_rel in paths.get('tests') or []:
        tests_path = (project_path / tests_rel).resolve()
        if tests_path in seen_roots:
            continue
        try:
            tests_path.relative_to(module_root)
            continue  # Already covered by walking module_root.
        except ValueError:
            pass
        roots.append((tests_path, True))
        seen_roots.add(tests_path)

    categorised: dict[str, list[str]] = {}
    for root, is_tests_root in roots:
        entries = _walk_module_root(root, project_path, project_root_rules)
        for rel_from_module, basename in entries:
            category: str
            inventory_path: str
            if is_tests_root:
                # Files reached via paths.tests outside the module root
                # are unconditionally tests, regardless of mode.
                category = 'test'
                # Use the project-relative path so callers can locate the
                # file unambiguously when it sits outside paths.module.
                inventory_path = root.relative_to(project_path).as_posix() + '/' + rel_from_module
            else:
                classified = (
                    _classify_marketplace(rel_from_module, basename)
                    if is_marketplace
                    else _classify_generic(rel_from_module, basename)
                )
                if classified is None:
                    continue
                category = classified
                inventory_path = (
                    Path(module_rel).as_posix().rstrip('/') + '/' + rel_from_module
                    if module_rel not in {'', '.'}
                    else rel_from_module
                )
            categorised.setdefault(category, []).append(inventory_path)

    # Sort each list deterministically; the caller (or the reader seam) decides
    # whether to cap. Byte-wise sort so output is byte-identical across OSes.
    return {category: sorted(categorised[category]) for category in sorted(categorised.keys())}


def _post_process_files(modules: dict[str, Any], project_dir: str = '.') -> None:
    """Populate ``module['files']`` for every module in-place.

    A thin per-module loop over :func:`build_module_files_inventory`: build the
    uncapped ``category -> sorted paths`` map, then apply
    :func:`_apply_category_cap` per category exactly as before. The writer's
    elision-shape output for every module is byte-identical to the
    pre-extraction behaviour — the extraction only exposes the uncapped walk so
    the reader-boundary self-scan seam can reuse it.
    """
    project_path = Path(project_dir).resolve()
    project_root_rules = _load_gitignore(project_path / '.gitignore')

    for _module_name, module_data in modules.items():
        inventory = build_module_files_inventory(module_data, project_path, project_root_rules)
        files_block: dict[str, list[str] | dict[str, Any]] = {}
        for category in sorted(inventory.keys()):
            files_block[category] = _apply_category_cap(inventory[category])
        module_data['files'] = files_block


# =============================================================================
# API Functions
# =============================================================================


def _empty_module_enrichment() -> dict[str, Any]:
    """Return the canonical empty-module enrichment dict.

    Shared between ``api_discover`` (which seeds per-module ``enriched.json``
    stubs at discovery time) and ``api_init`` (which fills in the same shape
    for legacy callers). Carries the required concept ``type`` (``module``); the
    ``generation`` header is stamped by the writer, not seeded here.
    """
    return {
        'type': LEGACY_CONCEPT_TYPE,
        'responsibility': '',
        'responsibility_reasoning': '',
        'purpose': '',
        'purpose_reasoning': '',
        'key_packages': {},
        'internal_dependencies': [],
        'key_dependencies': [],
        'key_dependencies_reasoning': '',
        'skills_by_profile': {},
        'skills_by_profile_reasoning': '',
        'tips': [],
        'insights': [],
        'best_practices': [],
    }


def _resolve_repo_root_name(project_path: Path) -> str:
    """Resolve the stable repository-root basename for project-identity seeding.

    Runs ``git rev-parse --git-common-dir`` rooted at ``project_path``. In a
    linked worktree the common git dir is the MAIN checkout's ``.git``, whose
    parent is the canonical repository root — so a first-run discover inside a
    worktree anchors the project name to the stable repo-root basename rather
    than the volatile worktree/plan-id basename. Falls back to
    ``project_path.name`` only when git is unavailable or the path is not
    inside a work tree (e.g. a non-git test-fixture tree).
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-common-dir'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return project_path.name
    if result.returncode != 0:
        return project_path.name
    common_dir = result.stdout.strip()
    if not common_dir:
        return project_path.name
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (project_path / common_path).resolve()
    # ``--git-common-dir`` points at the main checkout's ``.git``; its parent
    # is the canonical repository root.
    repo_root_name = common_path.parent.name
    return repo_root_name or project_path.name


def _package_bridge(module_name: str, modules: dict[str, dict[str, Any]]) -> dict[str, str]:
    """The module's dotted package name → bridge path map from its derived ``packages``."""
    derived_packages = (modules.get(module_name) or {}).get('packages')
    if not isinstance(derived_packages, dict):
        return {}
    return {
        name: entry['path']
        for name, entry in derived_packages.items()
        if isinstance(entry, dict) and isinstance(entry.get('path'), str) and entry['path']
    }


def _migrated_key_packages(
    document: dict[str, Any],
    module_name: str,
    modules: dict[str, dict[str, Any]],
    project_dir: str,
) -> tuple[dict[str, Any], list[str]]:
    """Return ``document`` with its ``key_packages`` keys migrated to repo-relative paths.

    ``discover`` is where the dotted→path migration can actually run: it holds
    both the concept document and the freshly-crawled derived data carrying the
    ``packages`` bridge, which is the only mapping from a legacy dotted
    identifier to a real path. :func:`migrate_key_packages` had no writer calling
    it before, so the migration never reached disk.

    An unavailable bridge is TOLERATED, never fatal. A module whose crawl carries
    no ``packages`` map (or a key the bridge does not cover) keeps its dotted key
    exactly as it was — the migration is an improvement to apply where the
    evidence supports it, and failing the whole discover write over a key that
    cannot be resolved would trade a cosmetic identity defect for a broken store.
    Unresolved keys are returned alongside the document (the caller reports them
    in its output) and are logged as a WARNING.

    Never mutates the caller's dict.

    Returns:
        A ``(document, unresolved_keys)`` pair.
    """
    key_packages = document.get('key_packages')
    if not isinstance(key_packages, dict) or not key_packages:
        return document, []

    derived_packages = (modules.get(module_name) or {}).get('packages')
    if not isinstance(derived_packages, dict):
        derived_packages = {}

    migrated, unresolved = migrate_key_packages(key_packages, derived_packages, project_dir)
    if unresolved:
        _log_unresolved_key_packages(module_name, unresolved)

    result = dict(document)
    result['key_packages'] = migrated
    return result, unresolved


def _log_unresolved_key_packages(module_name: str, unresolved: list[str]) -> None:
    """Report package keys the dotted→path migration could not resolve.

    Non-blocking by construction: the keys were KEPT under their original names,
    so the store is intact and the discover write proceeds. The WARNING exists so
    the retained legacy key is visible rather than silently permanent.
    """
    try:
        from plan_logging import log_entry

        log_entry(
            'script',
            None,
            'WARNING',
            f"[MIGRATION] module '{module_name}': key_packages entries kept under their "
            f'original non-resolving keys: {", ".join(sorted(unresolved))}',
        )
    except Exception:
        pass


def _read_pre_state(project_dir: str) -> delta.TreeState:
    """Read the descriptor tree as it stands on disk, before discover writes.

    Captures ``_project.json`` and every module ``enriched.json`` as raw bytes
    plus their parsed form. A file that does not parse keeps its bytes and has
    no parsed form, so the classifier can name it instead of the read failing.
    """
    meta_path = get_project_meta_path(project_dir)
    meta: dict[str, Any] | None = None
    meta_bytes: bytes | None = None
    if meta_path.is_file():
        meta_bytes = meta_path.read_bytes()
        meta = _parse_json_object(meta_bytes)

    documents: dict[str, dict[str, Any]] = {}
    document_bytes: dict[str, bytes] = {}
    data_dir = get_data_dir(project_dir)
    if data_dir.is_dir():
        for entry in sorted(data_dir.iterdir()):
            document_file = entry / DIR_PER_MODULE_ENRICHED
            if not entry.is_dir() or not document_file.is_file():
                continue
            raw = document_file.read_bytes()
            document_bytes[entry.name] = raw
            parsed = _parse_json_object(raw)
            if parsed is not None:
                documents[entry.name] = parsed
    return delta.TreeState(meta=meta, meta_bytes=meta_bytes, documents=documents, document_bytes=document_bytes)


def _parse_json_object(raw: bytes) -> dict[str, Any] | None:
    """Parse ``raw`` as a JSON object, or ``None`` when it is not one."""
    try:
        parsed = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _regenerate_document(
    existing: dict[str, Any],
    module_name: str,
    modules: dict[str, dict[str, Any]],
    project_dir: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Rebuild one module's concept document from the content already on disk.

    Returns ``(document, unresolved_key_package_keys)``, or ``(None, [])`` when
    the concept-model gate REFUSES the existing document's ``type``. That refusal
    is reported rather than raised: an unusable document is a condition the
    caller classifies against the pre-state, not one that aborts the whole
    discover call before any classification happens.

    The generation header is carried, never re-stamped: an existing document
    keeps its own header, and one with no header is back-filled with
    :func:`unknown_generation` so its unrecorded vintage is not restamped as
    generated against the current tree.
    """
    preserved = existing.get(GENERATION_FIELD)
    generation = preserved if isinstance(preserved, dict) and preserved else unknown_generation()
    migrated, unresolved = _migrated_key_packages(existing, module_name, modules, project_dir)
    try:
        document = stamp_concept_document(migrated, project_dir, generation=generation)
    except InvalidConceptTypeError:
        return None, []
    return document, sorted(unresolved)


def _carried_index_entry(pre_index: dict[str, Any], module_name: str) -> dict[str, Any]:
    """The ``_project.json`` index entry to keep for a module with no usable document.

    The entry is derived from its document, so nothing new can be derived for a
    module whose document this call could not consume. The entry the pre-state
    already carried is kept verbatim; a module the pre-state had no entry for
    gets an empty one. Deriving a fresh entry here would describe a document that
    was never read.
    """
    entry = pre_index.get(module_name)
    return copy.deepcopy(entry) if isinstance(entry, dict) else {}


def _stage_tree(tmp_dir: Path, staged: delta.StagedTree) -> None:
    """Write a staged tree under ``tmp_dir``: bytes verbatim, documents as JSON."""
    for relative_path, content in sorted(staged.items()):
        target = tmp_dir / relative_path
        if isinstance(content, bytes):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        else:
            _write_json(target, content)


def api_discover(
    project_dir: str = '.',
    force: bool = False,
    regenerate_description: bool = False,
    apply: str = delta.APPLY_ALL,
) -> dict[str, Any]:
    """Run extension API discovery and persist non-derived results per-module.

    Writes ``_project.json`` plus per-module ``enriched.json`` stubs into
    ``.plan/project-architecture.tmp/`` first, then atomically replaces the
    real ``.plan/project-architecture/`` directory via ``os.replace``.
    ``derived.json`` is NOT written — derived data is ephemeral and computed
    on demand by ``crawl_module_derived`` against the live worktree filesystem.
    ``enriched.json`` is seeded as an empty stub so downstream readers can
    treat it as present-by-default.

    Attribution: every call reads the on-disk pre-state first and classifies
    the regenerated tree against it via ``_descriptor_delta`` (the class table
    and verdict set live there). ``apply`` decides what is written:

    * ``all`` (the default) stages and swaps the full regenerated tree on every
      call, whatever the verdict;
    * ``plan`` / ``migration`` stage the pre-state plus only that kind of class.
      Nothing is staged on ``undecidable``, on ``no_baseline``, or when no class
      of the requested kind exists, and the swap is skipped when the projection
      equals the pre-state.

    The discovery + crawl pass still runs in-memory to populate
    ``_project.json``'s ``modules`` index; ``--force`` continues to regenerate
    that index (the index is the public on-disk record of "which modules
    were observed at the last discover invocation").

    Project-identity preservation: a forced rediscovery (e.g. the
    ``architecture-refresh`` finalize step, which runs ``discover --force``
    inside a worktree) must NOT overwrite the curated project ``name`` with the
    volatile worktree/plan-id basename, nor blank a curated ``description`` /
    ``description_reasoning``. Each identity field is resolved from a stable
    anchor: the existing ``_project.json`` when present, else the
    repository-root basename — never ``project_path.name``. Pass
    ``regenerate_description=True`` to opt back into blanking the description so
    a fresh LLM enrichment pass can re-author it.

    Args:
        project_dir: Project directory path
        force: Overwrite existing ``project-architecture/`` tree
        regenerate_description: When True, blank ``description`` /
            ``description_reasoning`` instead of preserving the existing values
        apply: ``all`` | ``plan`` | ``migration`` — which part of the
            regenerated tree is written (see above)

    Returns:
        Dict with status, modules_discovered, output_file (the new
        ``_project.json`` path), attribution (the verdict), applied
        (``all|plan|migration|none``), delta_classes, unclassified_fields,
        unresolved_key_packages, unresolved_key_packages_count and
        modules_examined
    """
    if apply not in delta.APPLY_MODES:
        return {
            'status': 'error',
            'error': 'invalid_apply',
            'message': f'Unknown --apply value {apply!r}. Accepted: {", ".join(delta.APPLY_MODES)}',
        }

    real_dir = get_data_dir(project_dir)
    project_meta_path = get_project_meta_path(project_dir)

    if project_meta_path.exists() and not force:
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'message': 'Use --force to overwrite',
        }

    # Read the on-disk pre-state BEFORE the crawl: the identity fields are
    # carried forward from it, and the regenerated tree is classified against
    # it. An absent or unreadable descriptor yields empty existing meta — the
    # first-run case.
    pre_state = _read_pre_state(project_dir)
    existing_meta: dict[str, Any] = pre_state.meta or {}

    # Crawl the live worktree filesystem to enumerate modules. A single
    # discover_project_modules call gives us both the module data and
    # extensions_used, avoiding the redundant second discovery pass that
    # crawl_all_modules + a follow-up discover_project_modules would cause.
    from extension_discovery import discover_project_modules

    project_path = Path(project_dir).resolve()
    discovery_result = discover_project_modules(project_path)
    modules: dict[str, dict[str, Any]] = discovery_result.get('modules', {}) or {}
    _post_process_files(modules, project_dir)
    extensions_used = discovery_result.get('extensions_used', [])

    # Resolve the project-identity fields from a stable anchor. ``name`` is the
    # existing curated name when present, otherwise the repo-root basename —
    # NEVER ``project_path.name`` (the worktree/plan-id basename under a forced
    # rediscovery). ``description`` / ``description_reasoning`` are preserved
    # unless the caller opted into regeneration.
    existing_name_raw = existing_meta.get('name')
    existing_name = existing_name_raw.strip() if isinstance(existing_name_raw, str) else ''
    resolved_name = existing_name or _resolve_repo_root_name(project_path)
    if regenerate_description:
        resolved_description = ''
        resolved_description_reasoning = ''
    else:
        description_raw = existing_meta.get('description')
        reasoning_raw = existing_meta.get('description_reasoning')
        resolved_description = description_raw if isinstance(description_raw, str) else ''
        resolved_description_reasoning = reasoning_raw if isinstance(reasoning_raw, str) else ''

    # Resolve each module's concept document, then derive its index entry from it.
    #
    # Every document goes through ``stamp_concept_document`` — the same invariant
    # gate ``save_module_enriched`` applies — so a document written here and one
    # written by the live-path writer carry an identical concept-model field set.
    # This path stages into the tmp tree it later swaps, so it places the returned
    # document itself rather than calling the live-path writer.
    #
    # The generation header is supplied rather than freshly stamped, because this
    # writer persists content it did not author:
    #
    #   * an existing document keeps its OWN header — preserved content must never
    #     be restamped as generated against the current tree;
    #   * an existing document with NO header is back-filled with
    #     ``unknown_generation()``. Its content is of unrecorded vintage, so the
    #     honest verdict is ``unknown``; stamping the current tree sha would
    #     manufacture a ``fresh`` verdict nothing established;
    #   * a fresh (first-seen) module IS authored here, so its empty stub takes a
    #     real current-tree stamp.
    #
    # The existing content comes from the tolerant pre-state read above, NOT from
    # a second read of the same file. Re-reading it through the strict loader is
    # what used to raise HERE — a present-but-unparseable document on a bare
    # ``json.load``, a refused ``type`` on the concept-model gate — before
    # ``classify_delta`` below could name it. That made the documented
    # ``undecidable`` / write-nothing outcome unreachable for such a document and
    # left the classifier's unreadable-document branch with no production input.
    # A document this call cannot consume is therefore recorded in
    # ``unusable_modules`` and carried through untouched: it is classified as
    # unreadable, and ``--apply all`` re-stages its original bytes rather than
    # blanking curated enrichment into an empty stub.
    module_documents: dict[str, dict[str, Any]] = {}
    module_index: dict[str, dict[str, Any]] = {}
    unresolved_key_packages: list[dict[str, str]] = []
    unusable_modules: set[str] = set()
    pre_index_raw = existing_meta.get('modules')
    pre_index: dict[str, Any] = pre_index_raw if isinstance(pre_index_raw, dict) else {}
    for module_name in sorted(modules.keys()):
        document: dict[str, Any] | None
        if module_name in pre_state.documents:
            document, unresolved = _regenerate_document(
                pre_state.documents[module_name], module_name, modules, project_dir
            )
            unresolved_key_packages.extend({'module': module_name, 'key': key} for key in unresolved)
        elif module_name in pre_state.document_bytes:
            # Present on disk but it did not parse — no parsed form exists to
            # rebuild from.
            document = None
        else:
            document = stamp_concept_document(_empty_module_enrichment(), project_dir)

        if document is None:
            unusable_modules.add(module_name)
            module_documents[module_name] = {}
            module_index[module_name] = _carried_index_entry(pre_index, module_name)
            continue

        module_documents[module_name] = document
        # The index entry is a read-side pre-flight surface: a consumer reads
        # _project.json alone to see each module's description and generation
        # header, deciding which concept documents to open and whether each is
        # stale — without opening any concept body.
        module_index[module_name] = {
            'description': document.get('responsibility', '') or '',
            GENERATION_FIELD: document.get(GENERATION_FIELD, {}),
        }

    # Build the project-meta document. The ``modules`` index is the record of
    # "which modules existed at last discover" AND the description/generation
    # pre-flight surface above. It is NOT the discovery gatekeeper: module
    # discovery crawls the live filesystem (``iter_modules``), so a module present
    # on disk but absent from this index is still discovered.
    project_meta: dict[str, Any] = {
        'name': resolved_name,
        'description': resolved_description,
        'description_reasoning': resolved_description_reasoning,
        'extensions_used': extensions_used,
        'modules': module_index,
    }

    # Classify the regenerated tree against the pre-state on every call, so the
    # attribution is reported whichever part is written.
    #
    # The classifier compares against the documents this call could actually
    # consume. A document whose ``type`` the concept gate refused parsed as JSON
    # but is no more usable than one that did not parse, so it is withheld from
    # the parsed view and reported the same way — as an unreadable document —
    # instead of as a field-by-field diff against a document never rebuilt.
    classification_state = delta.TreeState(
        meta=pre_state.meta,
        meta_bytes=pre_state.meta_bytes,
        documents={name: doc for name, doc in pre_state.documents.items() if name not in unusable_modules},
        document_bytes=pre_state.document_bytes,
    )
    report = delta.classify_delta(
        classification_state,
        project_meta,
        module_documents,
        {module_name: _package_bridge(module_name, modules) for module_name in modules},
    )

    # Decide what to stage. ``all`` stages the full regenerated tree regardless
    # of the verdict; ``plan`` / ``migration`` decide in memory and stage only
    # their projection, or nothing.
    staged: delta.StagedTree | None
    if apply == delta.APPLY_ALL:
        staged = {FILE_PROJECT_META: project_meta}
        # Per-module enriched.json only — derived.json is ephemeral under the
        # on-demand crawl model.
        for module_name in sorted(modules.keys()):
            if module_name in unusable_modules:
                # No document was rebuilt for this module, so its original bytes
                # are re-staged verbatim. Writing the empty stub instead would
                # blank curated enrichment on the strength of a read that failed.
                staged[delta.document_path(module_name)] = pre_state.document_bytes[module_name]
            else:
                staged[delta.document_path(module_name)] = module_documents[module_name]
    else:
        wanted = delta.ATTRIBUTION_PLAN if apply == delta.APPLY_PLAN else delta.ATTRIBUTION_MIGRATION
        build = delta.build_plan_projection if apply == delta.APPLY_PLAN else delta.build_migration_projection
        staged = None
        if report.verdict not in (delta.VERDICT_UNDECIDABLE, delta.VERDICT_NO_BASELINE) and report.has_attribution(
            wanted
        ):
            projection = build(classification_state, project_meta, module_documents, report)
            if not delta.projection_equals_pre_state(projection, classification_state):
                staged = projection

    applied = delta.APPLY_NONE
    if staged is not None:
        # Stage the new layout under .tmp/ so the swap is atomic, then swap it
        # into place.
        tmp_dir = get_tmp_data_dir(project_dir)
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        _stage_tree(tmp_dir, staged)
        swap_data_dir(tmp_dir, project_dir)
        applied = apply

    return {
        'status': 'success',
        'modules_discovered': len(modules),
        'output_file': str(real_dir / FILE_PROJECT_META),
        'attribution': report.verdict,
        'applied': applied,
        'delta_classes': report.delta_classes(),
        'unclassified_fields': [
            {'document': document, 'field': field_name} for document, field_name in report.unclassified_fields
        ],
        'unresolved_key_packages': unresolved_key_packages,
        'unresolved_key_packages_count': len(unresolved_key_packages),
        'modules_examined': report.modules_examined,
    }


def api_init(project_dir: str = '.', check: bool = False, force: bool = False, reset: bool = False) -> dict[str, Any]:
    """Initialize per-module ``enriched.json`` stubs, preserving existing enrichment by default.

    With the per-module layout, ``api_discover()`` already seeds empty stubs,
    so ``api_init`` is a re-seed / repair entry point. By default (and with
    ``--force``) it writes an empty stub only for modules whose
    ``enriched.json`` is MISSING, preserving every existing module's curated
    content byte-for-byte. The destructive blank-all — overwriting every
    module's ``enriched.json`` back to the empty stub — is gated behind an
    explicit ``reset`` and is honored together with ``--force`` (the intentional
    "reset enrichment" call-sites invoke ``init --force --reset``).

    Args:
        project_dir: Project directory path
        check: Only report status; do not write
        force: Re-seed only missing per-module ``enriched.json`` stubs,
            preserving existing enrichment
        reset: Blank every module's ``enriched.json`` back to the empty stub
            (destructive; honored together with ``force``)

    Returns:
        Dict with status and file info
    """
    project_meta_path = get_project_meta_path(project_dir)

    if check:
        if not project_meta_path.exists():
            return {'status': 'missing', 'file': str(project_meta_path)}
        try:
            module_names = iter_modules(project_dir)
        except DataNotFoundError as e:
            return {'status': 'error', 'error': str(e)}
        present = sum(1 for name in module_names if get_module_enriched_path(name, project_dir).exists())
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'modules_enriched': present,
        }

    if not project_meta_path.exists():
        return {
            'status': 'error',
            'error': "Project metadata missing. Run 'architecture.py discover' first.",
        }

    try:
        module_names = iter_modules(project_dir)
    except DataNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    # The destructive blank-all is gated on an explicit --reset and only takes
    # effect together with --force; a bare init (or plain --force) seeds only
    # missing stubs and preserves existing enrichment.
    reset = reset and force

    # Write through the SHARED live-path operation, not ``save_module_enriched``.
    # Every stub written here carries a fresh generation header, and writing the
    # document alone left ``_project.json``'s module index still describing the
    # provenance and description the document no longer carries — a repair that
    # silently desynchronised the pre-flight surface consumers read to decide
    # which documents are worth opening. The enrich verbs always carried the
    # index through; this path is the one that did not.
    #
    # The index write is batched into ONE ``_project.json`` write at the end
    # rather than one per module, so a whole-project reset does not rewrite the
    # index once per stub.
    #
    # The batch is flushed in a ``finally`` so the entries owed so far are
    # written even when the loop raises partway through. Without it, the stubs
    # already re-seeded carry a fresh generation header while ``_project.json``
    # keeps describing the description and provenance those documents no longer
    # carry — an index left behind by an aborted run is the staleness this
    # write-through exists to remove. ``_cmd_enrich._batched_index_sync`` flushes
    # its own owed entries on the way out for the same reason; this is the same
    # guarantee for the one live-path writer that batches without a context
    # manager. The ``if initialised:`` guard is kept, so a run that wrote nothing
    # still performs no ``_project.json`` write.
    initialised: list[str] = []
    try:
        for module_name in module_names:
            path = get_module_enriched_path(module_name, project_dir)
            if path.exists() and not reset:
                continue
            save_module_enriched(module_name, _empty_module_enrichment(), project_dir)
            initialised.append(module_name)
    finally:
        if initialised:
            sync_module_index(initialised, project_dir)

    return {
        'status': 'success',
        'modules_initialized': len(initialised),
        'output_file': str(project_meta_path),
    }


def api_get_derived(project_dir: str = '.') -> dict[str, Any]:
    """Get raw discovered data assembled across all modules.

    Re-assembles the legacy ``{project, modules, extensions_used}`` shape from
    the on-demand crawl. ``_project.json`` is still consulted for the
    ``project`` and ``extensions_used`` fields (they record the project's
    historical metadata), but the ``modules`` payload comes from the live
    filesystem crawl — no derived.json files are read from disk.
    """
    meta = load_project_meta(project_dir)
    modules = crawl_all_modules(project_dir)
    return {
        'project': {
            'name': meta.get('name', ''),
            'description': meta.get('description', ''),
            'description_reasoning': meta.get('description_reasoning', ''),
        },
        'modules': modules,
        'extensions_used': meta.get('extensions_used', []),
    }


def api_get_derived_module(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Get raw discovered data for a single module from the live crawl.

    Raises:
        ModuleNotFoundInProjectError: If the module is absent from the live
            filesystem crawl.
    """
    modules = crawl_all_modules(project_dir)
    if module_name not in modules:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', sorted(modules.keys()))
    return modules[module_name]


def list_modules(project_dir: str = '.') -> list[str]:
    """List module names from ``_project.json``."""
    return iter_modules(project_dir)


# =============================================================================
# CLI Handlers
# =============================================================================


def cmd_discover(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for discover command."""
    try:
        return api_discover(args.project_dir, args.force, args.regenerate_description, args.apply)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for init command."""
    try:
        return api_init(args.project_dir, args.check, args.force, args.reset)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for derived command."""
    try:
        derived = api_get_derived(args.project_dir)
        return {'status': 'success', **derived}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived_module(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for derived-module command."""
    try:
        module = api_get_derived_module(args.module, args.project_dir)
        return {'status': 'success', 'module_name': args.module, 'module': module}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = iter_modules(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# Imports kept at end of file but referenced above; left in place so the
# module-level public surface remains stable for tests that introspect
# ``_cmd_manage`` (e.g. patched callable lookups).
__all__ = [
    'api_discover',
    '_resolve_repo_root_name',
    'api_init',
    'api_get_derived',
    'api_get_derived_module',
    'list_modules',
    'cmd_discover',
    'cmd_init',
    'cmd_derived',
    'cmd_derived_module',
    '_post_process_files',
    'build_module_files_inventory',
]


# Suppress unused-import lint warnings — a few helpers are imported solely so
# downstream tests can ``from _cmd_manage import ...`` them without bouncing
# through ``_architecture_core``.
_ = (
    load_module_enriched,
    load_module_enriched_or_empty,
    save_project_meta,
)
