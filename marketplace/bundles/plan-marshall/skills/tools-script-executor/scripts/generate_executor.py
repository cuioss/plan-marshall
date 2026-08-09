#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Generate and manage execute-script.py with embedded script mappings.

Usage:
    python3 generate_executor.py generate [--force] [--dry-run] [--marketplace] [--marketplace-root PATH]
    python3 generate_executor.py verify
    python3 generate_executor.py drift [--marketplace] [--marketplace-root PATH]
    python3 generate_executor.py paths
    python3 generate_executor.py cleanup [--max-age-days N]

Subcommands:
    generate    Generate executor with script mappings
    verify      Verify existing executor is valid
    drift       Compare executor mappings with current marketplace state
    paths       Verify all mapped paths exist
    cleanup     Clean up old logs

The executor is always written directly to ``<root>/.plan/execute-script.py``
(the tracked ``.plan/`` directory inside the main git checkout). There is no
shim-to-external-executor split — every documented call site
(``python3 .plan/execute-script.py …``) runs the real executor directly.

Self-checking, atomic regeneration:
    ``generate`` is fail-safe by construction — it never overwrites a working
    executor with a malformed one. After the template is read and all
    placeholders are substituted, four deterministic guards run BEFORE any
    write: (1) a **format handshake** asserts the template's
    ``TEMPLATE_FORMAT_VERSION`` marker equals the generator's
    ``_SUPPORTED_TEMPLATE_FORMAT_VERSION`` constant (a skew is refused loudly
    with a re-sync instruction); (2) a **residue guard** rejects any surviving
    ``{{...}}`` placeholder token (template/generator placeholder-set
    disagreement); (3) a **py_compile self-check** compiles the substituted
    content in memory and, on ``SyntaxError``, returns ``status: error`` rather
    than writing; (4) a **provenance guard** refuses a content whose emitted
    paths carry more than one plugin-cache version dir for a single bundle (an
    internally version-split executor), no-opping in the version-less
    marketplace layout. Guards 1-3 are shape checks; guard 4 is the only one that
    compares the emitted path families against each other.
    Only a content that passes all four is committed, and the
    commit is **atomic** — written to a sibling temp path and ``os.replace``-d
    onto the real executor, so a partial or broken write can never leave a
    corrupt executor in place. Every regen caller (the meta upgrade path, the
    consumer upgrade path, and the finalize ``sync-plugin-cache`` path) inherits
    this protection because it lives inside the generator itself.

Context Detection:
    By default, operates in plugin-cache context (~/.claude/plugins/cache/plan-marshall/).
    Use --marketplace flag for marketplace development context (marketplace/bundles/).

    The ``--marketplace-root PATH`` flag (honored by ``generate`` and ``drift``)
    pins marketplace discovery to an explicit anchor directory, overriding the
    script-relative walk and cwd-based fallback. Equivalent to setting the
    ``PM_MARKETPLACE_ROOT`` environment variable; the flag takes precedence
    when both are supplied. Use this when invoking the script from a worktree
    or alternate checkout where Path.cwd() would otherwise resolve to the
    wrong marketplace tree.

Runtime Side-effects:
    The generated executor writes the resolved plan_id (from ``--plan-id`` or
    ``--audit-plan-id``) to the per-session active-plan cache at
    ``~/.cache/plan-marshall/sessions/{session_id}/active-plan`` on every
    invocation carrying one of those flags. The cache feeds the per-target
    terminal-title reader (cluster-01 ``session render-title``) so the main
    orchestration tab (cwd = repo root) renders ``pm:{phase}[:{short_description}]``
    instead of falling through to the active-command segment. The write is
    fire-and-forget — any
    I/O error is silently swallowed and the executor's exit code, stdout, and
    stderr are unaffected. The helper (``_write_active_plan``) lives entirely
    in the template; no generator-time substitution is required.

Executor-guard backstop decision (ADR-002):
    Under the move-based, cwd-pinned hermetic worktree model (ADR-002), the
    executor is per-tree DERIVED state, NOT a moved slot: main's
    ``.plan/execute-script.py`` stays present and untouched throughout phase-5+,
    and each worktree gets its OWN executor, generated at phase-5 move-in by
    ``prepare_execute.py`` invoking this generator with ``--marketplace-root``
    and the subprocess cwd pinned to the worktree (so the cwd-relative output
    path lands inside the worktree, never on main). On-main regeneration after a
    plan changes the marketplace script set is a project-level, meta-project-only
    finalize step (``finalize-step-sync-plugin-cache``, run after the cache sync)
    — NOT a responsibility of ``integrate_into_main`` (which performs the
    plan-dir move-back only). Because the worktree-bound generation pins cwd to
    the worktree, it never clobbers main's executor.

    DECISION: no runtime worktree-write refusal guard is added to this generator.
    A secondary runtime guard inside ``generate_executor.py`` was evaluated and
    REJECTED as redundant — the caller-owned cwd-pinning already lands each tree's
    output in the correct ``.plan/``, so the guard would add no residual
    defense-in-depth value while enlarging the surface. Per
    ``compatibility: breaking`` and the ``lean`` simplicity setting, the smaller
    surface is preferred. The ``--marketplace-root`` / ``PM_MARKETPLACE_ROOT``
    anchor (documented above) survives as the explicit escape hatch for a
    non-cwd-pinned caller that must pin discovery to an alternate marketplace
    tree; it is not a guard.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Bootstrap sys.path — this script may run before the executor sets up PYTHONPATH
# (called directly during wizard Step 4 to generate the executor).
# Resolve shared library paths relative to this script's location in the plugin tree:
#   skills/tools-script-executor/scripts/ → skills/{lib}/scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPTS_DIR.parent.parent
for _lib in ('ref-toon-format', 'tools-file-ops', 'script-shared'):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    # Unconditionally front-load the generator's OWN (script-relative) lib path:
    # remove any existing occurrence, then insert at position 0. A plain
    # "insert only when absent" guard leaves the generator's path behind an
    # inherited PYTHONPATH entry pointing at an older-version script-shared dir,
    # which then shadows the generator's own imports. Front-loading unconditionally
    # makes the generator's own version resolve first regardless of inherited
    # PYTHONPATH priority.
    if _lib_path in sys.path:
        sys.path.remove(_lib_path)
    sys.path.insert(0, _lib_path)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Repo-local tracked config directory name. The executor lives at
# ``{PLAN_DIR_NAME}/execute-script.py`` inside the main git checkout.
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Script-relative paths (resolved at runtime)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Shared path resolution (from script-shared)
from marketplace_bundles import (  # noqa: E402, I001
    build_pythonpath,
    collect_script_dirs,
    live_version_dirs,
    resolve_bundle_path,
    select_live_version_dir,
)
from marketplace_paths import get_base_path as _shared_get_base_path  # noqa: E402, I001
from file_ops import get_base_dir as _get_plan_base_dir  # noqa: E402, I001
from file_ops import get_tracked_config_dir as _get_tracked_config_dir  # noqa: E402, I001

# The SINGLE argparse accept-set derivation, shared with plugin-doctor's
# edit-time rules. The generator embeds what it derives; the doctor reads the
# same module at edit time. One derivation, two consumers, nothing to drift.
import argparse_surface as surface_api  # noqa: E402, I001


# Runtime-resolved locations. The executor lives at <root>/.plan/execute-script.py
# via get_tracked_config_dir(); state/logs live under get_base_dir() which is
# <root>/.plan/local/ (honouring PLAN_BASE_DIR for tests).
def executor_path() -> Path:
    """Real executor path: <root>/.plan/execute-script.py."""
    return _get_tracked_config_dir() / 'execute-script.py'


def state_path() -> Path:
    return _get_plan_base_dir() / 'marshall-state.toon'


def logs_dir() -> Path:
    return _get_plan_base_dir() / 'logs'


# ============================================================================
# PATH RESOLUTION (delegates to shared modules)
# ============================================================================


def get_base_path(use_marketplace: bool = False, marketplace_root: Path | None = None) -> Path:
    """Determine base path based on context.

    By default (use_marketplace=False), tries plugin-cache first, then marketplace.
    Delegates to shared marketplace_paths module.

    Args:
        use_marketplace: If True, force marketplace context (development mode).
            If False (default), tries plugin-cache first then marketplace.
        marketplace_root: Optional explicit override anchor for marketplace
            discovery. Forwarded verbatim to
            :func:`script_shared.marketplace_paths.get_base_path` and applied
            to the marketplace-aware scopes (``marketplace``, ``cache-first``).
            See :func:`script_shared.marketplace_paths.find_marketplace_path`
            for the four-step resolution order.
    """
    scope = 'marketplace' if use_marketplace else 'cache-first'
    return _shared_get_base_path(scope, marketplace_root=marketplace_root)


def _resolve_bundle_path(base_path: Path, bundle_name: str, subpath: str) -> Path:
    """Resolve path within a bundle, handling versioned cache structure."""
    return resolve_bundle_path(base_path, bundle_name, subpath)


def _resolve_plan_marshall_path(base_path: Path, subpath: str) -> Path:
    """Resolve path within plan-marshall bundle."""
    return resolve_bundle_path(base_path, 'plan-marshall', subpath)


def get_inventory_script(base_path: Path) -> Path:
    """Get path to inventory script based on context."""
    return resolve_bundle_path(
        base_path, 'pm-plugin-development', 'skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py'
    )


def get_templates_dir(base_path: Path) -> Path:
    """Resolve the executor template dir as a script-relative sibling of THIS generator.

    Unlike every other path helper in this module, this deliberately IGNORES
    ``base_path`` (the newest cache-version dir returned by
    ``get_base_path(scope=cache-first)``) and resolves the templates directory
    relative to the *executing* generator file: ``SCRIPT_DIR.parent / 'templates'``
    — mirroring the ``_SCRIPTS_DIR`` / ``_SKILLS_DIR`` bootstrap pattern used for
    the shared-library ``sys.path`` inserts at the top of this module.

    Why script-relative and NOT newest-version: the template is substituted into
    the executor by whichever generator version is actually running. Resolving the
    template against the newest cache version instead lets an OLD pinned generator
    (e.g. 0.1.1105) substitute against a NEWER template (e.g. 0.1.1116), producing
    a version-mismatched, SyntaxError-bricked executor — the ``TEMPLATE_FORMAT_VERSION``
    handshake only protects transitions where the executing generator already
    carries the handshake code, so a pre-fix generator stays unprotected. Binding
    the template to the executing generator guarantees the two always match and
    closes that mixed-version class structurally rather than only detecting it
    after the fact.

    This is the *inverse* of ``get_shared_module_dirs()`` (and the #888/#889/#894
    ``Path(__file__)`` resolver-class fix), which correctly STAYS newest-version:
    that governs the executor's OWN runtime ``sys.path`` bootstrap / GC-prune
    self-heal contract, where cache-newest-walk IS the fix. Here cache-newest-walk
    is the bug. The distinction is "resolve by role, not by flipping the resolver
    globally": ``base_path`` is retained in the signature for call-site
    compatibility but is intentionally unused.
    """
    return SCRIPT_DIR.parent / 'templates'


def get_logging_scripts_dir(base_path: Path) -> Path:
    """Get path to logging scripts directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/manage-logging/scripts')


def get_shared_module_dirs(base_path: Path) -> list[Path]:
    """Get paths to shared module directories that must be on sys.path at executor level.

    Shared modules are skills whose scripts are imported by other scripts (e.g., plan_logging
    imports input_validation) but have no executable script notation in the SCRIPTS mapping.
    These directories must be added to sys.path before any executor-level imports.
    """
    shared_skills = [
        'skills/tools-file-ops/scripts',
        'skills/tools-input-validation/scripts',
        'skills/ref-toon-format/scripts',
        'skills/script-shared/scripts',
        'skills/manage-change-ledger/scripts',
    ]
    dirs = []
    for subpath in shared_skills:
        resolved = _resolve_plan_marshall_path(base_path, subpath)
        if resolved.is_dir():
            dirs.append(resolved.resolve())
    return dirs


# ============================================================================
# SCRIPT DISCOVERY
# ============================================================================


def discover_scripts(base_path: Path) -> dict[str, str]:
    """
    Discover all scripts from bundles using inventory script.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        dict mapping notation to absolute path
    """
    inventory_script = get_inventory_script(base_path)

    if not inventory_script.exists():
        print(f'Error: Inventory script not found: {inventory_script}', file=sys.stderr)
        sys.exit(2)

    # Determine scope based on path
    scope = 'marketplace' if 'marketplace' in str(base_path) else 'plugin-cache'

    # Build PYTHONPATH to enable cross-skill imports (e.g., toon_parser)
    pythonpath = build_pythonpath(base_path)
    env = os.environ.copy()
    if pythonpath:
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{pythonpath}{os.pathsep}{existing}' if existing else pythonpath

    # Run inventory scan
    result = subprocess.run(
        [
            'python3',
            str(inventory_script),
            '--scope',
            scope,
            '--resource-types',
            'scripts',
            '--direct-result',
            '--format',
            'json',
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        print(f'Error running inventory scan: {result.stderr}', file=sys.stderr)
        sys.exit(2)

    inventory = json.loads(result.stdout)

    # Build notation mappings
    mappings = {}

    bundles_raw = inventory.get('bundles', [])
    # Handle both dict (keyed by name) and list formats from inventory
    if isinstance(bundles_raw, dict):
        bundles = list(bundles_raw.values())
    else:
        bundles = bundles_raw

    for bundle in bundles:
        for script in bundle.get('scripts', []):
            notation = script.get('notation', '')
            path_formats = script.get('path_formats', {})
            abs_path = path_formats.get('absolute', '')

            if notation and abs_path:
                mappings[notation] = abs_path

    return mappings


def discover_scripts_fallback(base_path: Path) -> dict[str, str]:
    """
    Fallback script discovery using glob patterns.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        dict mapping notation to absolute path
    """
    mappings = {}

    for bundle_dir in base_path.iterdir():
        if not bundle_dir.is_dir():
            continue

        bundle_name = bundle_dir.name
        skills_dir = bundle_dir / 'skills'

        if not skills_dir.exists():
            continue

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            scripts_dir = skill_dir / 'scripts'

            if not scripts_dir.exists():
                continue

            # Find the main script (usually {skill_name}.py or similar)
            for script_file in scripts_dir.glob('*.py'):
                # Skip __init__.py and test files
                if script_file.name.startswith('_') or 'test' in script_file.name.lower():
                    continue

                # Use three-part notation: bundle:skill:script
                notation = f'{bundle_name}:{skill_name}:{script_file.stem}'
                abs_path = str(script_file.resolve())
                mappings[notation] = abs_path

    return mappings


def discover_local_scripts(cwd: Path | None = None) -> dict[str, str]:
    """
    Discover scripts from .claude/skills/*/scripts/ in project root.

    Uses 'default-bundle:{skill}:{script}' notation — an internal key
    for collision avoidance in the SCRIPTS dict. This is not user-facing;
    the user-facing notation for project-level skills is 'project:{skill}'.

    Args:
        cwd: Working directory to search from. Defaults to Path.cwd().

    Returns:
        dict mapping notation to absolute path
    """
    if cwd is None:
        cwd = Path.cwd()

    local_skills = cwd / '.claude' / 'skills'
    if not local_skills.is_dir():
        return {}

    mappings: dict[str, str] = {}

    for skill_dir in local_skills.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue

        skill_name = skill_dir.name
        scripts_dir = skill_dir / 'scripts'

        if not scripts_dir.exists():
            continue

        # Find .py files (skip private modules starting with _)
        for script_file in scripts_dir.glob('*.py'):
            if script_file.name.startswith('_'):
                continue
            if script_file.is_file():
                notation = f'default-bundle:{skill_name}:{script_file.stem}'
                abs_path = str(script_file.resolve())
                mappings[notation] = abs_path

    return mappings


# ============================================================================
# TARGET-AWARE RESOLVER GENERATION
# ============================================================================

# Known OpenCode skill discovery roots in priority order (first match wins).
# Each root is searched for ``{bundle}-{skill}/scripts/{script}.py`` because
# the OpenCode dual-emit layout uses dash-namespaced directory names to avoid
# hierarchy collisions in flat config directories.
_OPENCODE_DISCOVERY_ROOTS = [
    # Env-var override (highest priority; evaluated at runtime)
    '$OPENCODE_CONFIG_DIR/skills',
    # Project-local roots (checked relative to cwd)
    '.opencode/skills',
    '.claude/skills',
    '.agents/skills',
    # User-global roots
    '~/.config/opencode/skills',
    '~/.claude/skills',
    '~/.agents/skills',
]

# Template for the Claude target-aware resolver.
# Resolves ``{bundle}:{skill}:{script}`` by globbing the plugin cache.
# The bundle component is intentionally ignored for Claude because the plugin
# cache layout is ``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``
# (single-bundle installation); the bundle in the notation is used to generate
# suggestions only.
_CLAUDE_RESOLVER_TEMPLATE = '''\
def _resolve_notation_by_target(notation: str) -> str | None:
    """Claude target: resolve notation via plugin-cache glob.

    Walks ``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``,
    collects EVERY version dir that carries the candidate script, and returns the
    LIVE one under the same liveness-and-ordering policy the generation-time
    selector applies: a ``.orphaned_at`` mark disqualifies a candidate EXCEPT on
    the newest-on-disk (retention-pinned) version dir, whose mark is ignored
    outright; the numerically-newest surviving candidate wins; and when every
    candidate is marked, the newest candidate overall is returned.  Selecting the
    live newest (rather than the first ``iterdir`` match) stops a stale version
    dir left on disk from shadowing the current scripts.  When the currently-
    pinned version dir is pruned, a later invocation re-resolves at runtime to the
    newest surviving version dir.  The ``bundle`` component of the notation is not
    used for path construction (the Claude plugin cache is a flat, single-bundle
    install) but may be useful for logging.

    DELIBERATE POLICY DUPLICATE — tracked authority:
    ``marketplace_bundles.select_live_version_dir``.  This body is substituted
    verbatim into the generated executor, which is bootstrap-free by construction:
    it must resolve notations BEFORE any marketplace module is importable, so it
    cannot import the selector without recreating the chicken-and-egg the executor
    exists to break.  Both sides consume the same input set — the on-disk version
    dirs and their ``.orphaned_at`` markers — so the copy is behaviourally
    identical rather than approximate, and no manifest pin is needed on either
    side.  This is the single sanctioned copy: any change to the selector's policy
    MUST be mirrored here, and a test pins the two to the same verdict in every
    marker state.

    EXISTENCE-ONLY MARKER INVARIANT — binding at this site, not merely inherited.
    The ``.orphaned_at`` predicate below consults only whether the marker is
    PRESENT; its content is never read, parsed, or compared here.  The field has a
    foreign co-producer — Claude Code's own plugin GC writes the same filename with
    a raw epoch-ms payload, while ``_mark_superseded_version_dirs`` writes ISO-8601
    UTC — so a content-dependent rule would bind the resolver to a format this
    repository does not own and cannot version.  This site declares the invariant
    itself rather than pointing at the selector, because this is the location the
    mirroring mandate above makes a policy change land on: a mirrored change that
    arrived without the invariant restated here would have nothing local to check
    it against.

    Args:
        notation: Three-part notation ``{bundle}:{skill}:{script}``.

    Returns:
        Absolute path string of the live version dir's script, or ``None``
        when no match is found.
    """
    import re

    def _version_key(name: str) -> tuple[int, ...]:
        # Same digit-run semantics as marketplace_bundles._version_sort_key:
        # '0.1.1069' -> (0, 1, 1069); '0.1-BETA' -> (0, 1).  A name with no
        # digits yields the empty tuple (sorts lowest).
        return tuple(int(part) for part in re.findall(r'\\d+', name))

    parts = notation.split(':')
    if len(parts) != 3:
        return None
    _bundle, skill, script = parts
    try:
        cache_root = Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
        if not cache_root.is_dir():
            return None
        version_dirs = [d for d in cache_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if not version_dirs:
            return None
        pinned = max(version_dirs, key=lambda d: _version_key(d.name))
        candidates = []
        for version_dir in version_dirs:
            candidate = version_dir / 'skills' / skill / 'scripts' / f'{script}.py'
            if candidate.is_file():
                candidates.append((version_dir, candidate))
        if candidates:
            live = [
                pair
                for pair in candidates
                if pair[0] == pinned or not (pair[0] / '.orphaned_at').exists()
            ]
            _dir, selected = max(live or candidates, key=lambda pair: _version_key(pair[0].name))
            return str(selected.resolve())
    except (OSError, ValueError, RuntimeError):
        pass
    return None
'''

# Template for the OpenCode target-aware resolver.
# Resolves ``{bundle}:{skill}:{script}`` by walking 7 standard OpenCode roots,
# using the dash-namespaced ``{bundle}-{skill}`` directory layout emitted by the
# OpenCode build target. Paths are always converted to absolute form before
# return to sidestep cwd ambiguity (anomalyco/opencode#9077).
_OPENCODE_RESOLVER_TEMPLATE = '''\
def _resolve_notation_by_target(notation: str) -> str | None:
    """OpenCode target: resolve notation via 7-root walk.

    Searches each OpenCode skill discovery root in priority order for
    ``{bundle}-{skill}/scripts/{script}.py`` (dash-namespaced layout per
    OpenCode dual-emit convention).  The first match is returned as an
    absolute path (anomalyco/opencode#9077).

    Roots searched in order:
      1. $OPENCODE_CONFIG_DIR/skills/     (env-var override)
      2. .opencode/skills/               (project-local)
      3. .claude/skills/                 (project-local cross-compat)
      4. .agents/skills/                 (project-local)
      5. ~/.config/opencode/skills/      (user-global)
      6. ~/.claude/skills/               (user-global cross-compat)
      7. ~/.agents/skills/               (user-global)

    Args:
        notation: Three-part notation ``{bundle}:{skill}:{script}``.

    Returns:
        Absolute path string, or ``None`` when no match is found.
    """
    parts = notation.split(':')
    if len(parts) != 3:
        return None
    bundle, skill, script = parts
    dir_name = f'{bundle}-{skill}'
    script_file = f'{script}.py'

    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None

    _env_config_dir = os.environ.get('OPENCODE_CONFIG_DIR', '')
    roots = [
        (str(Path(_env_config_dir) / 'skills') if _env_config_dir else ''),
        '.opencode/skills',
        '.claude/skills',
        '.agents/skills',
        str(home / '.config' / 'opencode' / 'skills'),
        str(home / '.claude' / 'skills'),
        str(home / '.agents' / 'skills'),
    ]

    for root in roots:
        if not root:
            continue
        try:
            candidate = Path(root) / dir_name / 'scripts' / script_file
            if candidate.is_file():
                return str(candidate.resolve())
        except (OSError, ValueError):
            continue

    return None
'''


def read_marshal_target(cwd: Path | None = None) -> str:
    """Read ``runtime.target`` from ``.plan/marshal.json``.

    Walks up from ``cwd`` (or ``Path.cwd()``) to find the nearest
    ``.plan/marshal.json``, then extracts ``runtime.target``.

    Args:
        cwd: Starting directory for the upward walk.  Defaults to
            ``Path.cwd()``.

    Returns:
        Target string (e.g. ``"claude"`` or ``"opencode"``), or the
        fallback ``"claude"`` when the file is absent, malformed, or the
        ``runtime.target`` key is missing.
    """
    import json as _json

    if cwd is None:
        cwd = Path.cwd()

    for parent in [cwd, *cwd.parents]:
        candidate = parent / PLAN_DIR_NAME / 'marshal.json'
        if candidate.is_file():
            try:
                data = _json.loads(candidate.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    runtime = data.get('runtime')
                    if isinstance(runtime, dict):
                        target = runtime.get('target')
                        if isinstance(target, str) and target:
                            return target
            except (OSError, ValueError):
                pass
            # File found but unreadable / missing key — use default
            return 'claude'

    # No marshal.json found — default to claude
    return 'claude'


def generate_target_aware_resolver_code(target: str) -> str:
    """Return the Python source for the ``_resolve_notation_by_target`` function.

    The body of the generated executor's ``resolve_notation`` function calls
    ``_resolve_notation_by_target`` as a dynamic fallback when a notation is
    absent from the embedded SCRIPTS dict.  The implementation differs by
    target:

    - ``claude``:  glob-based resolver using the Claude plugin-cache
      (``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``).
    - ``opencode``:  7-root walk using the OpenCode dash-namespaced directory
      layout (``{bundle}-{skill}/scripts/{script}.py``).

    Unknown targets fall back to the Claude resolver.

    Args:
        target: Runtime target string (e.g. ``"claude"`` or ``"opencode"``).

    Returns:
        Python source code string (no leading/trailing blank lines).
    """
    if target == 'opencode':
        return _OPENCODE_RESOLVER_TEMPLATE.strip()
    # Default / unknown target → Claude resolver
    return _CLAUDE_RESOLVER_TEMPLATE.strip()


# ============================================================================
# GENERATION
# ============================================================================


def generate_mappings_code(mappings: dict[str, str]) -> str:
    """Generate Python code for script mappings dict."""
    lines = []
    for notation, path in sorted(mappings.items()):
        lines.append(f'    "{notation}": "{path}",')
    return '\n'.join(lines)


# The template format version this generator knows how to fill. The template
# carries a matching ``# TEMPLATE_FORMAT_VERSION: N`` marker; the two are the
# explicit decoupling contract for every placeholder shape (SCRIPT_MAPPINGS,
# SCRIPT_SURFACES, SHARED_MODULE_DIRS, TARGET_AWARE_RESOLVER, …). Any change to
# a placeholder's emitted structure MUST bump BOTH this constant and the
# template marker in lockstep. A version skew is refused loudly (no write)
# rather than emitting a structurally-mismatched executor — the
# SyntaxError-executor-on-format-skew defect class.
#
# v2: adds the SCRIPT_SURFACES placeholder (per-notation argparse accept-sets).
# v3: each SCRIPT_SURFACES node additionally carries ``flag_arity`` (how many
#     argv tokens a long flag binds as its value), which the executor's pre-spawn
#     walk needs to tell a flag's VALUE from the next verb.
_SUPPORTED_TEMPLATE_FORMAT_VERSION = 3

# Matches the template's ``# TEMPLATE_FORMAT_VERSION: N`` marker comment.
_TEMPLATE_FORMAT_VERSION_RE = re.compile(r'^#\s*TEMPLATE_FORMAT_VERSION:\s*(\d+)\s*$', re.MULTILINE)

# Matches any residual ``{{...}}`` placeholder token that survived substitution.
_UNSUBSTITUTED_PLACEHOLDER_RE = re.compile(r'\{\{[^{}]*\}\}')

# Matches a plugin-cache version-directory name (``0.1.1194``, ``0.1-BETA``) —
# the same shape ``marketplace_bundles`` treats as a version dir.
_VERSION_DIR_NAME_RE = re.compile(r'^\d+\.\d+')


def _split_bundle_version(path: str, base_path: Path) -> tuple[str, str] | None:
    """Return ``(bundle, version_dir)`` for a path inside a versioned cache layout.

    A plugin-cache path is ``{base}/{bundle}/{version}/skills/...``, so the split is
    anchored on the known cache root: the path is relativized against ``base_path``
    and the first two segments ARE the bundle and its version dir. Anchoring is
    load-bearing — scanning for the first version-shaped segment anywhere in the
    path mis-splits on two real inputs: a version-shaped ANCESTOR directory above
    the cache root (``/srv/1.0-workspace/cache/{bundle}/{version}/…``) and a bundle
    whose own name starts with ``N.N`` (``1.0-my-bundle``, the supported naming
    convention ``find_bundles`` gates on ``bundle_dir.parent != base_path``). Either
    returns the wrong key and silently defeats the provenance guard.

    Returns ``None`` when the path lies outside ``base_path`` (a project-local
    ``.claude/skills`` script) or when its bundle segment carries no version dir —
    the marketplace layout, where the provenance guard has nothing to compare.
    """
    try:
        relative = Path(path).resolve().relative_to(Path(base_path).resolve())
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 2 or not _VERSION_DIR_NAME_RE.match(parts[1]):
        return None
    return parts[0], parts[1]


def _check_emitted_path_provenance(emitted_paths: list[str], base_path: Path) -> dict | None:
    """Return an error dict when any bundle's emitted paths span >1 version dir.

    Guard 4. The generator composes the executor from two independently-resolved
    path families — the notation→path ``mappings`` (discovered through
    ``find_bundles``) and the ``sys.path`` / PYTHONPATH entries (resolved through
    ``resolve_bundle_path`` and ``collect_script_dirs``). A single selector now
    makes them agree by construction; this guard is the fail-closed proof of that
    agreement at the write boundary, extending ADR-009's fail-closed principle
    from status reads to a generation write: never report success for an artifact
    whose internal consistency was never checked.

    No-ops (returns ``None``) when the emitted paths carry no version-dir segment,
    which is the marketplace layout.

    Args:
        emitted_paths: Every path the generated executor will embed.
        base_path: The cache root the emitted paths are anchored on — the same
            bundles directory the generation resolved every path family from.

    Returns:
        ``None`` when every bundle contributes exactly one version dir, else a
        ``{'status': 'error', 'error': ...}`` dict naming the bundle and the
        conflicting version dirs.
    """
    by_bundle: dict[str, set[str]] = {}
    for path in emitted_paths:
        split = _split_bundle_version(path, base_path)
        if split is None:
            continue
        bundle, version = split
        by_bundle.setdefault(bundle, set()).add(version)

    for bundle in sorted(by_bundle):
        versions = by_bundle[bundle]
        if len(versions) > 1:
            conflicting = ', '.join(sorted(versions))
            return {
                'status': 'error',
                'error': (
                    f"Version-split executor refused: bundle '{bundle}' contributes emitted paths "
                    f'from more than one version dir ({conflicting}). The generated executor would '
                    f'carry script mappings and import paths from different versions of the same '
                    f'bundle. No executor was written and any pre-existing executor was left '
                    f'untouched. Remedy: run the marshall-steward upgrade flow\'s '
                    f'cache-retention-sweep sub-step '
                    f'(plan-marshall:marshall-steward:cache_retention sweep) to prune the '
                    f'superseded version dirs, then regenerate.'
                ),
            }
    return None


# ============================================================================
# ARGPARSE ACCEPT-SET DERIVATION (SCRIPT_SURFACES)
# ============================================================================

_SURFACE_DERIVATION_BUDGET_ENV = 'PM_SURFACE_BUDGET_SECONDS'
_DEFAULT_SURFACE_BUDGET_SECONDS = 180.0


def _surface_derivation_config() -> surface_api.DerivationConfig:
    """Bounds for generation-time derivation, with an operator budget override.

    Deliberately tighter than the module defaults on the two axes that matter
    here: a per-invocation timeout small enough that one hanging import cannot
    stall a regeneration, and a total wall-clock budget after which the
    remaining scripts simply contribute no entry.

    ``PM_SURFACE_BUDGET_SECONDS`` overrides that budget. It exists because the
    budget is the one bound whose right value is environment-dependent: a cold
    first build wants the full allowance, while a caller that needs only the
    notation mappings refreshed (a CI path, an anchoring check) should not pay
    for a full accept-set derivation. Setting it to ``0`` disables derivation
    outright, which is a SAFE configuration rather than a broken one — a
    surface-less executor dispatches exactly as it did before the map existed
    (see the fail-closed-on-uncertainty invariant). An unparseable or negative
    value falls back to the default rather than failing the generation.
    """
    budget = _DEFAULT_SURFACE_BUDGET_SECONDS
    raw = os.environ.get(_SURFACE_DERIVATION_BUDGET_ENV)
    if raw is not None:
        try:
            parsed = float(raw)
        except ValueError:
            parsed = budget
        if parsed >= 0:
            budget = parsed
    return surface_api.DerivationConfig(
        timeout_seconds=10.0,
        max_depth=6,
        max_nodes=256,
        total_budget_seconds=budget,
    )

# The four counts every ``generate`` result carries, zeroed. Published even on
# the paths that derive nothing (a dry run, a probe-write failure) so the shape
# of the result never depends on which branch produced it — a caller reading
# ``surfaces_derived`` always finds it.
_EMPTY_SURFACE_STATS: dict[str, int] = {
    'scripts_registered': 0,
    'surfaces_derived': 0,
    'surfaces_reused': 0,
    'surfaces_not_derivable': 0,
}

# Locates the ``SCRIPT_SURFACES = {`` … ``}`` literal in a previously generated
# executor so its entries can be reused by digest. Text-scanned rather than
# imported: reading the previous artifact must not execute it.
_SURFACES_BLOCK_START = 'SCRIPT_SURFACES = {'


def _dir_digest(directory: Path) -> str:
    """Digest every ``*.py`` in ``directory`` (non-recursive), by name and bytes.

    Non-recursive on purpose: the executor's PYTHONPATH exposes a scripts dir
    and its immediate subdirectories, and the aggregate is combined with the
    other injected dirs by :func:`_shared_dirs_digest`, so a nested package's
    contents reach the digest through its own entry rather than through a deep
    walk of every sibling.
    """
    hasher = hashlib.sha256()
    if not directory.is_dir():
        return hasher.hexdigest()
    for path in sorted(directory.glob('*.py')):
        hasher.update(path.name.encode('utf-8'))
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b'<unreadable>')
    return hasher.hexdigest()


def _shared_dirs_digest(shared_dirs: list[Path]) -> str:
    """One digest over every injected shared-module directory.

    Computed ONCE per generation and folded into every script's digest, so an
    edit to an imported shared module invalidates every dependent surface. This
    over-invalidates — a change to one shared module re-derives all scripts —
    which costs time only. Under-invalidating would cost correctness, so the
    digest is deliberately coarse.
    """
    hasher = hashlib.sha256()
    for directory in sorted(shared_dirs):
        hasher.update(directory.as_posix().encode('utf-8'))
        hasher.update(_dir_digest(directory).encode('utf-8'))
    return hasher.hexdigest()


def compute_surface_digest(script_path: str, shared_digest: str) -> str:
    """Digest the inputs that can change one script's argparse surface.

    Four contributors: the script's own bytes, every ``*.py`` beside it (its
    skill's other modules — the ``ci.py`` / ``ci_base.py`` relationship, where
    the parser is assembled in a sibling), the shared-module aggregate, and the
    derivation's own ``CACHE_VERSION``. A surface whose digest still matches is
    reused verbatim on the next regeneration, which is what keeps a routine
    ``preflight`` at its current cost: an unchanged script set performs ZERO
    help invocations.

    The ``CACHE_VERSION`` contributor is what makes a change to the SURFACE
    SCHEMA invalidate every entry. Without it, widening a node (a new
    ``flag_arity`` map, say) leaves every unchanged script reusing an entry
    derived under the old schema, so the executor keeps the shape the fix was
    meant to replace and the fix appears to do nothing until a script happens to
    change. Schema currency is an input to the surface exactly as script content
    is.
    """
    path = Path(script_path)
    hasher = hashlib.sha256()
    try:
        hasher.update(path.read_bytes())
    except OSError:
        hasher.update(b'<unreadable>')
    hasher.update(_dir_digest(path.parent).encode('utf-8'))
    hasher.update(shared_digest.encode('utf-8'))
    hasher.update(f'surface-schema-v{surface_api.CACHE_VERSION}'.encode())
    return hasher.hexdigest()


def read_previous_surfaces(executor: Path) -> dict[str, dict]:
    """Read the ``SCRIPT_SURFACES`` map out of a previously generated executor.

    Text-scanned and ``ast.literal_eval``-ed rather than imported: the previous
    executor is an artifact to be read, not code to be run, and importing it
    would execute its bootstrap. Any failure — absent file, absent block,
    malformed literal, an executor generated before this map existed — returns
    an empty dict, which simply means "nothing to reuse" and costs a full
    re-derivation.
    """
    if not executor.is_file():
        return {}
    try:
        text = executor.read_text(encoding='utf-8')
    except OSError:
        return {}
    start = text.find(_SURFACES_BLOCK_START)
    if start < 0:
        return {}
    open_brace = start + len(_SURFACES_BLOCK_START) - 1
    end = text.find('\n}', open_brace)
    if end < 0:
        return {}
    literal = text[open_brace:end + 2]
    try:
        parsed = ast.literal_eval(literal)
    except (ValueError, SyntaxError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        notation: entry
        for notation, entry in parsed.items()
        if isinstance(notation, str) and isinstance(entry, dict)
    }


def derive_script_surfaces(
    mappings: dict[str, str],
    probe_executor: Path,
    previous: dict[str, dict],
    shared_dirs: list[Path],
) -> tuple[dict[str, dict], dict[str, int]]:
    """Derive (or reuse) an argparse accept-set for every registered notation.

    Reuse first: an entry in ``previous`` whose recorded ``digest`` still
    matches the freshly computed one is carried over untouched and never
    re-probed. Everything else is derived through ``probe_executor`` by the
    shared module.

    A notation with no confident surface contributes NO entry. That is the
    fail-closed-on-uncertainty invariant at the generation boundary: the
    dispatch-time check treats an absent notation as "assert nothing, spawn as
    before", so omitting is always safe while emitting a partial surface would
    let a real verb be rejected.

    Returns ``(surfaces, stats)`` where ``stats`` carries the four counts the
    command publishes. They are reported rather than merely computed because a
    regeneration that quietly derived nothing is otherwise indistinguishable
    from one that derived everything — both exit ``status: success``.
    """
    shared_digest = _shared_dirs_digest(shared_dirs)
    digests = {
        notation: compute_surface_digest(script_path, shared_digest)
        for notation, script_path in sorted(mappings.items())
    }

    surfaces: dict[str, dict] = {}
    to_derive: list[str] = []
    for notation, digest in digests.items():
        carried = previous.get(notation)
        if isinstance(carried, dict) and carried.get('digest') == digest:
            surfaces[notation] = carried
            continue
        to_derive.append(notation)

    reused = len(surfaces)
    derived = 0
    if to_derive:
        # Thread OUR digest through as the shared module's cache key. Its own
        # default key is narrower (the script plus its siblings, not the shared
        # module dirs), so leaving it to key itself would let a shared-module
        # edit invalidate the entry here while its cache still served the
        # surface derived before that edit — a re-derivation that quietly
        # returns the stale answer. One invalidation model, both layers.
        index = surface_api.build_surface_index(
            to_derive,
            probe_executor,
            config=_surface_derivation_config(),
            cache_keys=digests,
        )
        for notation, result in index.items():
            if not surface_api.is_derivable(result):
                continue
            surfaces[notation] = {
                'digest': digests[notation],
                'surface': result.to_dict(),
            }
            derived += 1

    stats = {
        'scripts_registered': len(mappings),
        'surfaces_derived': derived,
        'surfaces_reused': reused,
        'surfaces_not_derivable': len(mappings) - len(surfaces),
    }
    return surfaces, stats


def _canonical(value: object) -> object:
    """Return ``value`` with every nested dict key-sorted, for stable ``repr``.

    Python dicts preserve insertion order and ``repr`` follows it, so sorting on
    the way in is what makes the emitted literal byte-stable across runs with
    identical inputs.
    """
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def generate_surfaces_code(surfaces: dict[str, dict]) -> str:
    """Generate the ``SCRIPT_SURFACES`` dict body, one notation per line.

    Mirrors :func:`generate_mappings_code`'s deterministic sorted-key emission
    so a regeneration over an unchanged script set produces a byte-identical
    executor — which is what makes an executor diff a real signal rather than
    per-run churn.
    """
    lines = []
    for notation in sorted(surfaces):
        lines.append(f'    "{notation}": {_canonical(surfaces[notation])!r},')
    return '\n'.join(lines)


def parse_template_format_version(template: str) -> int | None:
    """Parse the ``# TEMPLATE_FORMAT_VERSION: N`` marker from template text.

    Args:
        template: The raw template file contents.

    Returns:
        The integer version declared by the marker, or ``None`` when the marker
        is absent or malformed.
    """
    match = _TEMPLATE_FORMAT_VERSION_RE.search(template)
    if match:
        return int(match.group(1))
    return None


def generate_executor(
    mappings: dict[str, str],
    base_path: Path,
    dry_run: bool = False,
    target: str | None = None,
) -> dict:
    """
    Generate execute-script.py with embedded mappings.

    Four deterministic guards protect the executor, and their ORDER is load
    bearing in two different ways.

    Guard 1 runs ahead of the accept-set derivation, which costs one ``--help``
    subprocess per parser node under a wall-clock budget. A version skew refuses
    without writing anything, so spending the derivation first would burn that
    whole budget to reach a conclusion available from a string comparison. (A
    dry run returns earlier still: it derives nothing and writes nothing, so
    there is nothing for the handshake to protect.)

    Guards 2-4 then run before THE EXECUTOR is written, so a malformed
    generation can never overwrite a working executor. One write does precede
    them, and it is not the executor: derivation dispatches its ``--help``
    probes through a throwaway PROBE executor — a sibling temp file carrying the
    content about to be written minus its surfaces, unlinked on every exit path
    — so the probes see the script set being generated rather than the previous
    one. The real executor is untouched until every guard has passed.

    1. **Format handshake** — the template's ``TEMPLATE_FORMAT_VERSION`` marker
       must equal :data:`_SUPPORTED_TEMPLATE_FORMAT_VERSION`; a skew returns a
       ``status: error`` dict and writes nothing.
    2. **Residue guard** — any surviving ``{{...}}`` placeholder token (a
       placeholder the generator did not fill, or one a newer template
       introduced) returns a ``status: error`` dict and writes nothing.
    3. **py_compile self-check** — the substituted content is compiled in memory;
       a ``SyntaxError`` returns a ``status: error`` dict leaving any pre-existing
       executor byte-identical.
    4. **Provenance guard + atomic write** — every emitted path (the ``mappings``
       values, the shared-module dirs, the logging dir, and the collected script
       dirs) is grouped by owning bundle, splitting each path against the known
       ``base_path`` cache root; a bundle contributing paths from more
       than one plugin-cache version dir returns a ``status: error`` dict naming
       the bundle and the conflicting version dirs, again leaving any pre-existing
       executor byte-identical. The guard no-ops in the version-less marketplace
       layout. A content passing all four guards is written to a sibling temp path
       and ``os.replace``-d onto the real executor so a partial write can never
       leave a corrupt executor in place.

    Args:
        mappings: Script notation to path mappings
        base_path: Path to bundles directory for resolving template/logging paths
        dry_run: If True, show what would be generated without writing
        target: Platform target (e.g. ``"claude"`` or ``"opencode"``).  When
            ``None``, the target is read from ``marshal.json`` via
            :func:`read_marshal_target`.

    Returns:
        A ``{'status': 'success'}`` dict on success (carrying ``dry_run: True``
        for a preview run), or a ``{'status': 'error', 'error': ...}`` dict
        naming the failure when a guard trips or the template is absent.
    """
    templates_dir = get_templates_dir(base_path)
    executor_template = templates_dir / 'execute-script.py.template'

    if not executor_template.exists():
        return {'status': 'error', 'error': f'Template not found: {executor_template}'}

    template = executor_template.read_text()
    mappings_code = generate_mappings_code(mappings)

    # Resolve platform target for target-aware resolver injection.
    resolved_target = target if target is not None else read_marshal_target()
    resolver_code = generate_target_aware_resolver_code(resolved_target)

    # logging module location (unified logging skill)
    logging_scripts_dir = get_logging_scripts_dir(base_path)
    logging_dir = logging_scripts_dir.resolve().as_posix()

    # Shared module directories (must be on sys.path before executor-level imports).
    # Emitted as ``(skill, pinned_dir)`` pairs so the template bootstrap can self-heal a
    # GC-pruned pinned version to the newest surviving plugin-cache version dir. The skill
    # name is the parent dir name of each resolved ``.../skills/{skill}/scripts`` path.
    shared_dirs = get_shared_module_dirs(base_path)
    shared_module_lines = (
        '\n'.join(f"    ('{d.parent.name}', '{d.as_posix()}')," for d in shared_dirs)
        if shared_dirs
        else '    # (none detected)'
    )

    # Collect ALL script directories (including subdirectories of skills like script-shared
    # that have no registered scripts but contain importable modules).
    # These are injected as extra PYTHONPATH entries so subprocess-invoked scripts can
    # import from organized subdirectory layouts (e.g., script-shared/scripts/build/).
    all_script_dirs = collect_script_dirs(base_path)
    extra_dirs_code = ', '.join(f"'{d}'" for d in sorted({Path(d).resolve().as_posix() for d in all_script_dirs}))

    # Provisioning stamps: the version and script-set fingerprint the executor
    # was generated at, read from the installed dist-manifest.json (emitted by
    # the target generator). A fresh install has no manifest yet — the empty
    # sentinel is substituted, never an error, so the executor still generates.
    manifest = read_installed_manifest(base_path, target=resolved_target)
    generated_version = str(manifest.get('version', '') or '')
    mappings_fingerprint = str(manifest.get('executor_scripts_fingerprint', '') or '')

    def _substitute(surfaces_code: str) -> str:
        content = template.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
        content = content.replace('{{SCRIPT_SURFACES}}', surfaces_code)
        content = content.replace('{{LOGGING_DIR}}', logging_dir)
        content = content.replace('{{SHARED_MODULE_DIRS}}', shared_module_lines)
        content = content.replace('{{EXTRA_SCRIPT_DIRS}}', extra_dirs_code)
        content = content.replace('{{PLAN_DIR_NAME}}', PLAN_DIR_NAME)
        content = content.replace('{{TARGET_AWARE_RESOLVER}}', resolver_code)
        content = content.replace('{{EXECUTOR_TARGET}}', resolved_target)
        content = content.replace('{{GENERATED_VERSION}}', generated_version)
        content = content.replace('{{MAPPINGS_FINGERPRINT}}', mappings_fingerprint)
        return content

    if dry_run:
        # No derivation on a preview run: deriving surfaces spawns a ``--help``
        # child per parser node, which is real work a dry run must not do. The
        # preview shows the executor's shape, not its accept-sets.
        print('=== execute-script.py ===')
        print(_substitute('')[:2000])
        print('... (truncated)')
        return {
            'status': 'success',
            'dry_run': True,
            # A COPY, matching the OSError degradation path below and the CLI
            # consumer: the module-level default is shared, and handing it out
            # by reference makes the next in-place aggregation corrupt every
            # later caller's baseline.
            'surface_stats': dict(_EMPTY_SURFACE_STATS),
        }

    # Guard 1 — format handshake: refuse a template whose declared format
    # version the generator does not support (never write a file).
    #
    # FIRST, ahead of the derivation below. The guard is a string comparison
    # against a marker already in hand and it writes nothing when it trips,
    # while derivation spawns a ``--help`` child per parser node under a
    # multi-minute budget. Running the cheap refusal after the expensive work
    # would spend the whole budget to reach a conclusion available up front.
    template_version = parse_template_format_version(template)
    if template_version != _SUPPORTED_TEMPLATE_FORMAT_VERSION:
        return {
            'status': 'error',
            'error': (
                f'Template format skew: {executor_template} declares '
                f'TEMPLATE_FORMAT_VERSION={template_version!r} but this generator supports '
                f'{_SUPPORTED_TEMPLATE_FORMAT_VERSION}. Re-sync so the template and generator '
                f'are the same version (run /sync-plugin-cache, then regenerate) before '
                f'regenerating the executor. Existing executor left untouched.'
            ),
        }

    real_executor = executor_path()

    # Derive the argparse accept-sets against a PROBE executor — the very
    # content about to be written, minus its surfaces. The alternative,
    # probing through the previous executor, would derive surfaces for the OLD
    # script set (a notation added in this same generation would resolve
    # through no mapping at all). Writing the probe first and the real executor
    # last keeps the single atomic commit intact: the probe is a throwaway
    # sibling temp file, deleted on every exit path.
    real_executor.parent.mkdir(parents=True, exist_ok=True)
    probe_executor = real_executor.with_name(real_executor.name + '.probe.tmp')
    try:
        probe_executor.write_text(_substitute(''), encoding='utf-8')
        surfaces, surface_stats = derive_script_surfaces(
            mappings,
            probe_executor,
            read_previous_surfaces(real_executor),
            shared_dirs,
        )
    except OSError as exc:
        # Derivation is an enhancement, never a precondition: an executor with
        # no surfaces dispatches exactly as it did before this map existed. A
        # probe-write failure therefore degrades to no surfaces rather than
        # failing the generation and leaving the caller with a stale executor.
        print(f'Warning: surface derivation skipped ({exc})', file=sys.stderr)
        surfaces, surface_stats = {}, dict(_EMPTY_SURFACE_STATS)
        surface_stats['scripts_registered'] = len(mappings)
        surface_stats['surfaces_not_derivable'] = len(mappings)
    finally:
        try:
            probe_executor.unlink(missing_ok=True)
        except OSError:
            pass

    content = _substitute(generate_surfaces_code(surfaces))

    # Guard 2 — residue guard: refuse any surviving {{...}} placeholder token
    # (a placeholder the generator did not fill, or one a newer template
    # introduced) the same loud way (never write a file).
    residue = _UNSUBSTITUTED_PLACEHOLDER_RE.search(content)
    if residue is not None:
        return {
            'status': 'error',
            'error': (
                f'Unsubstituted placeholder residue in generated content: {residue.group(0)!r}. '
                f'The template and generator disagree on the placeholder set; no executor was '
                f'written and any existing executor was left untouched.'
            ),
        }

    # Guard 3 — py_compile self-check: compile the substituted content in memory
    # before it is ever written. A SyntaxError means the generation is malformed;
    # return an error and preserve the existing executor untouched.
    try:
        compile(content, str(real_executor), 'exec')
    except SyntaxError as exc:
        return {
            'status': 'error',
            'error': (
                f'Generated executor failed py_compile self-check ({exc}); refusing to write a '
                f'malformed executor. Any pre-existing executor was left untouched.'
            ),
        }

    # Guard 4 — provenance guard: refuse a content whose emitted paths carry more
    # than one version dir for a single bundle (an internally version-split
    # executor). Shape checks 1-3 cannot see this class; only comparing the path
    # families against each other can.
    emitted_paths = [
        *mappings.values(),
        *(d.as_posix() for d in shared_dirs),
        logging_dir,
        *all_script_dirs,
    ]
    provenance_error = _check_emitted_path_provenance(emitted_paths, base_path)
    if provenance_error is not None:
        return provenance_error

    # Atomic write: write to a sibling temp path and os.replace() it onto the
    # real executor so a partial/broken write can never leave a corrupt executor
    # in place.
    real_executor.parent.mkdir(parents=True, exist_ok=True)
    tmp_executor = real_executor.with_name(real_executor.name + '.tmp')
    try:
        tmp_executor.write_text(content, encoding='utf-8')
        os.replace(tmp_executor, real_executor)
    finally:
        # No-op on the success path (os.replace already consumed the tmp file);
        # only unlinks a stray tmp file when write_text or os.replace raised
        # before completing the swap. Swallow cleanup OSError so a cleanup
        # failure never masks the original exception.
        try:
            tmp_executor.unlink(missing_ok=True)
        except OSError:
            pass
    return {'status': 'success', 'surface_stats': surface_stats}


def compute_checksum(mappings: dict[str, str]) -> str:
    """Compute checksum of mappings for change detection."""
    content = json.dumps(mappings, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def _relativize_script_path(abs_path: str, base_resolved: Path) -> str:
    """Return ``abs_path`` as a base-relative POSIX path (machine-portable).

    Strips the machine-specific absolute prefix so the same script set produces
    an identical value regardless of where the checkout lives on disk. Falls
    back to a ``/skills/``-marker strip when the path is not under
    ``base_resolved`` (e.g. a project-local script), so no absolute prefix ever
    leaks into the fingerprint.
    """
    p = Path(abs_path)
    try:
        return p.resolve().relative_to(base_resolved).as_posix()
    except ValueError:
        s = p.as_posix()
        idx = s.rfind('/skills/')
        if idx >= 0:
            return s[idx + 1 :]  # 'skills/...'
        return p.name


def compute_executor_scripts_fingerprint(mappings: dict[str, str], base_path: Path) -> str:
    """Machine-portable fingerprint of the executor's script set.

    Relativizes every ``discover_scripts`` notation→path mapping to a
    base-relative path before hashing with :func:`compute_checksum`. Two
    consequences make this the right staleness signal for the dist-manifest:

    - **Machine-portable** — two checkouts with an identical script layout under
      different absolute roots yield a byte-identical fingerprint, so a
      per-machine absolute-path leak can never make the fingerprint churn.
    - **Content-insensitive** — editing a script's body changes neither its
      notation nor its relative path, so the fingerprint moves only when a
      script is added, removed, moved, or renamed.

    Consumed by the target generator (``marketplace/targets/generate.py``) to
    stamp ``executor_scripts_fingerprint`` into ``dist-manifest.json``.

    Args:
        mappings: notation → absolute path mapping from :func:`discover_scripts`.
        base_path: The bundles/cache root the paths were discovered under; used
            as the relativization anchor.

    Returns:
        8-char hex fingerprint (same machinery as :func:`compute_checksum`).
    """
    base_resolved = base_path.resolve()
    relative: dict[str, str] = {
        notation: _relativize_script_path(abs_path, base_resolved) for notation, abs_path in mappings.items()
    }
    return compute_checksum(relative)


def update_state(script_count: int, checksum: str, logs_cleaned: int) -> None:
    """Update marshall-state.toon with generation metadata."""
    timestamp = datetime.now(UTC).isoformat()
    content = f"""status\tgenerated\tscript_count\tchecksum\tlogs_cleaned
success\t{timestamp}\t{script_count}\t{checksum}\t{logs_cleaned}
"""
    target = state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def cleanup_old_logs(max_age_days: int = 7) -> int:
    """
    Clean up old global logs.

    Returns:
        Number of logs deleted
    """
    import time

    deleted = 0
    cutoff = time.time() - (max_age_days * 86400)

    target_logs = logs_dir()
    if not target_logs.exists():
        return 0

    for log_file in target_logs.glob('script-execution-*.log'):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except Exception:
            pass

    return deleted


# ============================================================================
# VERIFICATION
# ============================================================================


def verify_executor(base_path: Path | None = None) -> tuple[bool, int]:
    """
    Verify existing executor is valid.

    Args:
        base_path: Optional path to bundles directory for logging module verification.
                   If None, tries to auto-detect.

    Returns:
        (is_valid, script_count)
    """
    real_executor = executor_path()
    if not real_executor.exists():
        print(f'Error: Executor not found: {real_executor}', file=sys.stderr)
        return False, 0

    # Resolve base_path if not provided
    if base_path is None:
        try:
            base_path = get_base_path(use_marketplace=False)
        except FileNotFoundError as e:
            print(f'Error: {e}', file=sys.stderr)
            return False, 0

    logging_scripts_dir = get_logging_scripts_dir(base_path)
    logging_module = logging_scripts_dir / 'plan_logging.py'

    if not logging_module.exists():
        print(f'Error: Logging module not found: {logging_module}', file=sys.stderr)
        return False, 0

    # Try to import and validate using importlib.util for hyphenated filename
    try:
        import_code = f"""
import importlib.util
spec = importlib.util.spec_from_file_location('executor', '{real_executor}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(len(module.SCRIPTS))
"""
        result = subprocess.run(['python3', '-c', import_code.strip()], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'Error validating executor: {result.stderr}', file=sys.stderr)
            return False, 0

        script_count = int(result.stdout.strip())
        print(f'Executor valid: {script_count} scripts mapped')

    except Exception as e:
        print(f'Error validating executor: {e}', file=sys.stderr)
        return False, 0

    # Verify logging module (include shared module dirs for transitive imports)
    shared_dirs = get_shared_module_dirs(base_path)
    path_inserts = '; '.join(f"sys.path.insert(0, '{d}')" for d in shared_dirs)
    if path_inserts:
        path_inserts += '; '
    try:
        result = subprocess.run(
            [
                'python3',
                '-c',
                f"import sys; {path_inserts}sys.path.insert(0, '{logging_scripts_dir}'); from plan_logging import log_script_execution; print('OK')",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f'Error validating logging module: {result.stderr}', file=sys.stderr)
            return False, 0

        print('Logging module valid')

    except Exception as e:
        print(f'Error validating logging module: {e}', file=sys.stderr)
        return False, 0

    return True, script_count


def get_executor_mappings() -> dict[str, str]:
    """
    Extract mappings from current executor.

    Returns:
        dict mapping notation to absolute path, or empty dict on error
    """
    try:
        real_executor = executor_path()
        import_code = f"""
import importlib.util
import json
spec = importlib.util.spec_from_file_location('executor', '{real_executor}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(module.SCRIPTS))
"""
        result = subprocess.run(['python3', '-c', import_code.strip()], capture_output=True, text=True)
        if result.returncode != 0:
            return {}

        mappings: dict[str, str] = json.loads(result.stdout.strip())
        return mappings

    except Exception:
        return {}


def check_paths_exist(mappings: dict[str, str]) -> tuple[list, list]:
    """
    Check if all mapped paths exist.

    Returns:
        (existing_notations, missing_tuples) where missing_tuples is [(notation, path), ...]
    """
    existing = []
    missing = []

    for notation, path in mappings.items():
        if Path(path).exists():
            existing.append(notation)
        else:
            missing.append((notation, path))

    return existing, missing


# ============================================================================
# INSTALLED-MANIFEST / VERSION STALENESS
# ============================================================================


def find_installed_manifest_path(base_path: Path | None = None, target: str = 'claude') -> Path | None:
    """Locate the installed ``dist-manifest.json``, or ``None`` when absent.

    The manifest is emitted by the target generator at the target output root
    (meta-project: ``target/{target}/``). On a meta-project install it is
    copied into the plugin-cache tree; on a marketplace install it stays at the
    marketplace clone root (``.../plugins/marketplaces/<marketplace>/``) and is
    NOT copied into ``.../plugins/cache/<marketplace>/``. Search order:

    1. ``$PM_DIST_MANIFEST`` — explicit override (tests + alternate installs).
    2. The meta-project target tree (``<repo>/target/{target}/dist-manifest.json``)
       when ``base_path`` points inside a ``marketplace/bundles`` checkout.
    3. ``base_path/dist-manifest.json`` and its parent (cache / target root).
    4. The marketplace clone root: when ``base_path`` resolves inside a
       plugin-cache layout (``.../plugins/cache/<marketplace>/...``), the
       ``/plugins/cache/<marketplace>`` segment is mapped to
       ``/plugins/marketplaces/<marketplace>`` and ``dist-manifest.json`` is
       appended — where a marketplace install actually keeps its manifest.

    Args:
        base_path: The resolved bundles/cache root, or ``None`` when it could
            not be resolved (fresh install).
        target: The resolved platform target (``claude`` or ``opencode``) whose
            manifest to look up under the meta-project target tree. Defaults to
            ``claude`` for callers that have no resolved target in hand.

    Returns:
        Path to an existing manifest file, or ``None``.
    """
    env_manifest = os.environ.get('PM_DIST_MANIFEST')
    if env_manifest:
        candidate = Path(env_manifest)
        return candidate if candidate.is_file() else None

    candidates: list[Path] = []
    if base_path is not None:
        marker = '/marketplace/bundles'
        base_str = str(base_path)
        idx = base_str.find(marker)
        if idx >= 0:
            repo_root = Path(base_str[:idx])
            candidates.append(repo_root / 'target' / target / 'dist-manifest.json')
        candidates.append(base_path / 'dist-manifest.json')
        candidates.append(base_path.parent / 'dist-manifest.json')
        # (4) Marketplace clone root: a plugin-cache install keeps the manifest
        # at ``.../plugins/marketplaces/<marketplace>/`` rather than inside the
        # cache tree, so map the ``/plugins/cache/<marketplace>`` segment to
        # ``/plugins/marketplaces/<marketplace>`` and append ``dist-manifest.json``.
        cache_marker = '/plugins/cache/'
        cache_idx = base_str.find(cache_marker)
        if cache_idx >= 0:
            prefix = base_str[:cache_idx]
            remainder = base_str[cache_idx + len(cache_marker):]
            marketplace_name = remainder.split('/', 1)[0]
            # Defense in depth: a segment of '.'/'..' (or one carrying a path
            # separator) would let the mapped path climb outside
            # `plugins/marketplaces/` — reject it the same way
            # `marketplace_paths.main_anchored_store_owns_bundle` rejects a
            # malformed bundle-name segment, rather than trusting the derived
            # substring verbatim.
            is_safe_segment = (
                marketplace_name
                and marketplace_name not in ('.', '..')
                and '/' not in marketplace_name
                and '\\' not in marketplace_name
            )
            if is_safe_segment:
                candidates.append(
                    Path(prefix) / 'plugins' / 'marketplaces' / marketplace_name / 'dist-manifest.json'
                )

    # Highest-version-wins selection over the existing candidates: a stale
    # cache-root manifest must never shadow a newer clone-root manifest just
    # because it appears earlier in the candidate list. Read each existing
    # candidate's ``version`` and return the path whose version is the maximum;
    # ties (equal version) resolve to the earlier candidate, preserving the
    # clone-root-authoritative ordering intent. An empty candidate set (or
    # all-unresolvable) still returns ``None`` (→ ``unknown`` downstream) — the
    # fail-closed behaviour is unchanged.
    best_path: Path | None = None
    best_version: tuple[int, ...] | None = None
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        version = str(data.get('version', '') or '') if isinstance(data, dict) else ''
        candidate_version = _version_tuple(version)
        if best_version is None or candidate_version > best_version:
            best_path = candidate
            best_version = candidate_version
    return best_path


def read_installed_manifest(base_path: Path | None = None, target: str = 'claude') -> dict:
    """Read the installed ``dist-manifest.json``, returning ``{}`` when absent.

    A fresh install (and this repo before the first target build) has no
    manifest; callers treat ``{}`` as the ``unknown`` sentinel and proceed
    without error.

    Args:
        base_path: Forwarded to :func:`find_installed_manifest_path`.
        target: Forwarded to :func:`find_installed_manifest_path`.

    Returns:
        The parsed manifest dict, or ``{}`` when the file is absent or
        unreadable.
    """
    path = find_installed_manifest_path(base_path, target=target)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted ``0.1.N`` version into an int tuple for ordered compare.

    Comparison is a full int-tuple compare (no zero-padding), so ``0.1.9`` sorts
    below ``0.1.10`` and a future ``0.2`` base bump orders correctly. An empty
    or ``unknown`` sentinel yields the empty tuple, which compares as the lowest
    possible version — a fresh/unstamped surface is therefore never treated as
    newer than a real published version.

    Args:
        version: A dotted version string, or the empty/``unknown`` sentinel.

    Returns:
        The int tuple of the leading numeric components.
    """
    if not version or version == 'unknown':
        return ()
    parts: list[int] = []
    for segment in version.split('.'):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts)


def read_executor_version() -> str:
    """Read the embedded ``MARSHALL_VERSION`` from the generated executor.

    Returns ``unknown`` when the executor is absent, unreadable, or carries an
    empty stamp (fresh install / pre-versioning executor).
    """
    real_executor = executor_path()
    if not real_executor.is_file():
        return 'unknown'
    try:
        text = real_executor.read_text(encoding='utf-8')
    except (OSError, ValueError):
        return 'unknown'
    match = re.search(r"^MARSHALL_VERSION\s*=\s*'([^']*)'", text, re.MULTILINE)
    if match and match.group(1):
        return match.group(1)
    return 'unknown'


def read_marshal_provisioned_version(cwd: Path | None = None) -> str:
    """Read ``system.provisioned_version`` from ``.plan/marshal.json``.

    Walks up from ``cwd`` (or ``Path.cwd()``) to the nearest
    ``.plan/marshal.json`` and extracts the stamped provisioning version.
    Returns ``unknown`` when the file, the ``system`` block, or the field is
    absent (fresh install, or config seeded before provisioning stamps
    existed).

    Args:
        cwd: Starting directory for the upward walk. Defaults to ``Path.cwd()``.

    Returns:
        The provisioned version string, or ``unknown``.
    """
    if cwd is None:
        cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / PLAN_DIR_NAME / 'marshal.json'
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    system = data.get('system')
                    if isinstance(system, dict):
                        value = system.get('provisioned_version')
                        if isinstance(value, str) and value:
                            return value
            except (OSError, ValueError):
                pass
            return 'unknown'
    return 'unknown'


# ============================================================================
# COMMANDS
# ============================================================================


def cmd_generate(args: argparse.Namespace) -> dict:
    """Generate executor with embedded script mappings."""
    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace, marketplace_root=args.marketplace_root)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    # Resolve target for the target-aware resolver.
    # Explicit --target flag takes precedence; fall back to marshal.json.
    target: str | None = getattr(args, 'target', None)
    resolved_target = target if target else read_marshal_target()
    print(f'Target: {resolved_target}')

    # Discover marketplace scripts
    print('Discovering marketplace scripts...')
    try:
        mappings = discover_scripts(base_path)
    except Exception as e:
        print(f'Falling back to glob discovery: {e}', file=sys.stderr)
        mappings = discover_scripts_fallback(base_path)

    marketplace_count = len(mappings)
    print(f'Found {marketplace_count} marketplace scripts')

    # Discover project-local scripts
    print('Discovering project-local scripts...')
    local_mappings = discover_local_scripts()
    local_count = len(local_mappings)
    if local_count > 0:
        mappings.update(local_mappings)
        print(f'Found {local_count} local scripts')

    print(f'Total: {len(mappings)} scripts ({marketplace_count} marketplace, {local_count} local)')

    if args.dry_run:
        print('\n=== Script Mappings ===')
        for notation, path in sorted(mappings.items()):
            print(f'  {notation} -> {path}')
        print()

    # Generate executor (uses logging skill from plan-marshall/logging).
    # The generator now self-checks the substituted content (format handshake,
    # placeholder-residue guard, py_compile) and writes atomically; a failed
    # self-check surfaces here as the command's status: error (non-zero exit via
    # the safe_main contract), preserving any pre-existing working executor.
    print('Generating executor...')
    gen_result = generate_executor(mappings, base_path, dry_run=args.dry_run, target=resolved_target)
    if gen_result.get('status') != 'success':
        return gen_result

    # The four accept-set counts, published rather than merely computed. A
    # regeneration that quietly derived NOTHING — a broken probe, an exhausted
    # budget, a shared-module edit that invalidated everything and then failed —
    # exits ``status: success`` exactly like a healthy one, so the only way to
    # tell them apart is to read the numbers. ``surfaces_not_derivable`` is the
    # residual (registered minus emitted), so the three buckets always sum to
    # ``scripts_registered``.
    surface_stats = gen_result.get('surface_stats') or dict(_EMPTY_SURFACE_STATS)

    if args.dry_run:
        print('\nDry run complete. No files written.')
        return {
            'status': 'success',
            'scripts_discovered': len(mappings),
            'executor_target': resolved_target,
            'dry_run': True,
            **surface_stats,
        }

    # Cleanup old logs
    logs_cleaned = cleanup_old_logs()
    if logs_cleaned > 0:
        print(f'Cleaned up {logs_cleaned} old log files')

    # Update state
    checksum = compute_checksum(mappings)
    update_state(len(mappings), checksum, logs_cleaned)

    result: dict = {
        'status': 'success',
        'scripts_discovered': len(mappings),
        'executor_generated': str(executor_path()),
        'executor_target': resolved_target,
        'logs_cleaned': logs_cleaned,
        **surface_stats,
    }

    return result


def cmd_verify(args: argparse.Namespace) -> dict:
    """Verify existing executor."""
    valid, count = verify_executor()
    if valid:
        return {'status': 'success', 'script_count': count}
    else:
        return {'status': 'error', 'error': 'Verification failed'}


def _flip_notation_separators(segment: str) -> str:
    """Return ``segment`` with hyphens and underscores swapped.

    ``manage_status`` ↔ ``manage-status``. Used to detect the
    rename-without-sweep signature: a notation referenced by callers whose
    third segment differs from the registered (filename-derived) form only
    in hyphen/underscore separators.
    """
    return ''.join(
        '_' if ch == '-' else '-' if ch == '_' else ch for ch in segment
    )


_NOTATION_REFERENCE_RE = re.compile(
    r'execute-script\.py\s+'
    r'([A-Za-z0-9][A-Za-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_-]*)'
)


def _collect_referenced_notations(base_path: Path) -> set[str]:
    """Scan marketplace markdown / scripts for executor notation references.

    Returns the set of three-part notations that appear after a
    ``execute-script.py`` token anywhere under ``base_path``. These are the
    notations callers actually invoke; comparing them against the registered
    (filename-derived) mappings surfaces a half-done entrypoint rename.
    """
    referenced: set[str] = set()
    if not base_path.is_dir():
        return referenced
    for pattern in ('*.md', '*.py'):
        for path in base_path.rglob(pattern):
            try:
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                continue
            for match in _NOTATION_REFERENCE_RE.finditer(text):
                referenced.add(match.group(1))
    return referenced


def _detect_notation_drift(
    registered: dict[str, str],
    base_path: Path,
) -> list[tuple[str, str]]:
    """Detect referenced notations whose filename-derived form drifted.

    For each notation referenced by callers that is NOT in the registered
    mappings, check whether the hyphen/underscore-flipped third segment IS
    registered. A match is the rename-without-sweep signature: the script
    file was renamed (changing its filename-derived notation) but callers
    still reference the old third segment.

    Returns a list of ``(referenced_notation, registered_notation)`` pairs.
    """
    drift: list[tuple[str, str]] = []
    referenced = _collect_referenced_notations(base_path)
    for notation in sorted(referenced):
        if notation in registered:
            continue
        parts = notation.split(':')
        if len(parts) != 3:
            continue
        bundle, skill, script = parts
        flipped = _flip_notation_separators(script)
        if flipped == script:
            continue
        candidate = f'{bundle}:{skill}:{flipped}'
        if candidate in registered:
            drift.append((notation, candidate))
    return drift


def cmd_drift(args: argparse.Namespace) -> dict:
    """Compare executor mappings with current bundles state."""
    executor_mappings = get_executor_mappings()

    if not executor_mappings:
        return {'status': 'error', 'error': 'Could not read executor mappings'}

    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace, marketplace_root=args.marketplace_root)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    # Get current bundles state using discover_scripts()
    try:
        current_mappings = discover_scripts(base_path)
    except SystemExit:
        print('Warning: Could not read bundles state', file=sys.stderr)
        current_mappings = {}

    # Find differences
    executor_set = set(executor_mappings.keys())
    current_set = set(current_mappings.keys())

    added = current_set - executor_set
    removed = executor_set - current_set
    changed = []

    for notation in executor_set & current_set:
        if executor_mappings[notation] != current_mappings.get(notation):
            changed.append(notation)

    # Notation-drift detection: a script whose filename-derived notation has
    # changed (an entrypoint rename) leaves callers referencing the old third
    # segment. Warn on stderr rather than silently registering only the
    # filename-derived form.
    notation_drift = _detect_notation_drift(current_mappings, base_path)
    for referenced, registered in notation_drift:
        print(
            f'Warning: notation drift — `{referenced}` is referenced by '
            f'callers but only `{registered}` is registered (filename-derived). '
            f'A renamed entrypoint script silently changed its public '
            f'notation; sweep callers to the registered form.',
            file=sys.stderr,
        )

    drift_status = 'drift' if (added or removed or changed or notation_drift) else 'ok'
    return {
        'status': 'success',
        'drift_status': drift_status,
        'executor_scripts': len(executor_mappings),
        'bundles_scripts': len(current_mappings),
        'added': len(added),
        'removed': len(removed),
        'changed': len(changed),
        'notation_drift': len(notation_drift),
    }


def cmd_paths(args: argparse.Namespace) -> dict:
    """Verify all mapped paths exist."""
    mappings = get_executor_mappings()

    if not mappings:
        return {'status': 'error', 'error': 'Could not read executor mappings'}

    existing, missing = check_paths_exist(mappings)

    return {
        'status': 'success',
        'paths_status': 'missing' if missing else 'ok',
        'total': len(mappings),
        'existing': len(existing),
        'missing': len(missing),
    }


def cmd_cleanup(args: argparse.Namespace) -> dict:
    """Clean up old global logs."""
    deleted = cleanup_old_logs(max_age_days=args.max_age_days)
    return {'status': 'success', 'deleted': deleted}


def _carries_skills_tree(version_dir: Path) -> bool:
    """Eligibility predicate: this version dir carries a ``skills/`` tree.

    The ONLY thing this module contributes to the version-dir decision. Liveness
    (the ``.orphaned_at`` marker semantics) and ordering belong to
    ``marketplace_bundles.select_live_version_dir`` / ``live_version_dirs``, so
    ``_detect_multi_version_pollution``, ``_retention_pinned_versions`` and
    ``_mark_superseded_version_dirs`` agree with the resolvers by construction.
    """
    return (version_dir / 'skills').is_dir()


def _live_version_dirs(bundle_dir: Path) -> list[Path]:
    """Return the LIVE version dirs directly under ``bundle_dir``.

    A thin view over the shared policy: the version dirs carrying a ``skills/``
    tree that ``marketplace_bundles.live_version_dirs`` treats as live — unmarked,
    or the retention-pinned newest-on-disk dir whose ``.orphaned_at`` mark is
    ignored outright. Shared by :func:`_detect_multi_version_pollution` (which
    counts them) and :func:`_mark_superseded_version_dirs` (which marks every
    non-newest, non-pinned one). Returns ``[]`` on an unreadable ``bundle_dir``.
    """
    return live_version_dirs(bundle_dir, _carries_skills_tree)


def _retention_pinned_versions(base_path: Path | None, bundle_dir: Path) -> set[str]:
    """Return the version names the retention policy pins for ``bundle_dir``.

    A pinned version MUST NEVER be marked ``.orphaned_at``. The pins mirror THREE
    OF THE FOUR *dir-naming* arms of the ``marshall-steward``
    ``cache_retention sweep`` keep-union — the arms that name one specific
    directory rather than applying a threshold to all of them: the newest dir on
    disk (what the resolver selects), the version named by ``marshal.json``'s
    ``system.provisioned_version``, and the version named by the installed
    ``dist-manifest.json``. The fourth dir-naming arm — the version dir the sweep
    is itself executing from — is deliberately NOT mirrored: self-deletion is the
    sweep's own hazard, not the marker-writer's. The union's remaining two arms
    (newest-``N``, younger-than-``D``-days) are thresholds and pin nothing.

    The label is ``dir-naming``, not ``non-count``: the ``younger-than-D-days``
    arm is an age threshold rather than a count, so "non-count" would admit it
    and yield a third arity for the same phrase. The canonical statement of the
    keep-union and of this pin-vs-keep-set distinction lives in
    ``manage-config/standards/data-model.md`` § "Plugin-cache retention
    semantics"; this docstring must agree with it member-for-member.

    Pinning these is what makes marker saturation structurally impossible: the dir
    the resolver selects is pinned unconditionally, so at least one live version
    dir always survives per bundle. Without the pin, a run whose newest dir was
    already marked promotes an OLDER dir to "newest live" and marks the rest, and
    the cascade converges on zero live dirs — which renders
    :func:`_detect_multi_version_pollution` vacuous and forces
    ``marketplace_bundles.find_bundles`` into its degraded all-orphaned fallback.
    The disk arm is read from ``select_live_version_dir`` itself rather than
    re-derived here, so the pin names exactly the dir the resolvers select.

    Args:
        base_path: The resolved bundles/cache root, or ``None``.
        bundle_dir: The bundle whose version dirs are being partitioned.

    Returns:
        The set of pinned version-directory names (possibly empty).
    """
    pinned: set[str] = set()
    selected = select_live_version_dir(bundle_dir, _carries_skills_tree)
    if selected is not None:
        pinned.add(selected.name)
    provisioned = read_marshal_provisioned_version()
    if provisioned and provisioned != 'unknown':
        pinned.add(provisioned)
    manifest_version = str(read_installed_manifest(base_path).get('version', '') or '')
    if manifest_version:
        pinned.add(manifest_version)
    return pinned


def _detect_multi_version_pollution(base_path: Path | None) -> list[str]:
    """Return the bundle names exposing more than one LIVE version dir on disk.

    In the plugin-cache layout a bundle resolves as
    ``{base}/{bundle}/{version}/skills/``. A bundle carrying MORE THAN ONE
    version dir (each with a ``skills/`` tree) pollutes PYTHONPATH with multiple
    versions of the same scripts — the exact condition ``collect_script_dirs``'
    newest-only selection guards against at discovery time. Surfacing the
    on-disk pollution lets the preflight regenerate the executor (which then
    embeds only the newest version's paths). Returns the sorted list of polluted
    bundle names (empty when the tree is clean or ``base_path`` is unresolved).

    A version dir carrying the ``.orphaned_at`` deferral marker is EXCLUDED from
    the count: it is a superseded dir already offered to the ``marshall-steward``
    ``cache-retention-sweep`` sub-step, so it is not live pollution. This is what
    makes the pollution signal CLEAR after a prior preflight marked the
    superseded dirs — the second consecutive preflight sees exactly one live
    (unmarked) version dir per bundle and reports ``executor_action: fresh``
    instead of regenerating on every run.

    The count cannot be rendered vacuous by marker saturation, and the guarantee
    is now structural rather than merely procedural: the shared selector ignores a
    ``.orphaned_at`` mark on the retention-pinned dir outright (see
    ``marketplace_bundles.select_live_version_dir``), so that dir stays live even
    if a legacy pass marked it, and every bundle with a version dir on disk
    contributes at least one. :func:`_mark_superseded_version_dirs` additionally
    never writes a mark onto a pinned version (see
    :func:`_retention_pinned_versions`).
    """
    if base_path is None or not base_path.is_dir():
        return []
    polluted: list[str] = []
    try:
        for bundle_dir in base_path.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
                continue
            if len(_live_version_dirs(bundle_dir)) > 1:
                polluted.append(bundle_dir.name)
    except OSError:
        pass
    return sorted(polluted)


def _mark_superseded_version_dirs(base_path: Path | None, polluted_bundles: list[str]) -> None:
    """Mark the superseded (non-pinned) version dirs of each polluted bundle.

    For every polluted bundle, stamp every live version dir with the
    ``.orphaned_at`` deferral marker EXCEPT the versions the retention policy pins
    (see :func:`_retention_pinned_versions`: the dir the shared selector resolves
    to — which ``collect_script_dirs`` embeds after a regen — plus the
    ``marshal.json``-provisioned and the manifest-named versions). Pinning is what
    makes marker saturation structurally impossible;
    without it the marker converges on "every dir marked, none live", which
    renders the pollution detector vacuous and forces
    ``marketplace_bundles.find_bundles`` permanently into its degraded
    all-orphaned fallback.

    This does NOT delete anything: the actual removal defers to the
    ``marshall-steward`` ``cache-retention-sweep`` sub-step (the union-keep
    ``cache_retention sweep`` verb), sidestepping the check-then-``rmtree``
    TOCTOU / delete-live-dir hazard (a superseded dir may still be on a running
    process's PYTHONPATH). That sweep applies the same pins independently, so a
    marked dir is never removed merely because it carries the marker — the marker
    is advisory there, never a keep-or-delete oracle. Marking is what clears the
    pollution signal for the NEXT preflight — a marked dir is excluded by
    ``_detect_multi_version_pollution``, so the following run sees one live
    version dir per bundle and no longer regenerates.

    The marker content is a fresh ISO-8601 UTC timestamp. The write is idempotent
    by construction — an already-marked dir is not live (the shared liveness view
    excludes marked dirs) unless it is pinned, and a pinned dir is never marked,
    so the clock is never reset on a dir that was already marked.

    **``.orphaned_at`` has a second, foreign producer — this repository does not
    own the field exclusively.** Claude Code's own plugin GC writes the same
    filename into the same version dirs with a raw epoch-ms payload, so TWO
    producers write ONE field in TWO encodings and either encoding may be found on
    any dir. Three consequences follow, and this writer changes none of them:

    1. Our encoding stays ISO-8601 UTC. It is deliberately not converted to
       epoch-ms to match the co-producer.
    2. No file under ``~/.claude/plugins/cache/`` is normalised or rewritten by us.
       A foreign-written epoch-ms marker is left exactly as found.
    3. The split is inert because BOTH sanctioned readers consult the marker's
       EXISTENCE only, never its content. There are two, and each states the
       invariant at its own site rather than deferring to the other:
       ``marketplace_bundles._partition_version_dirs`` (the selector) and the
       ``.orphaned_at`` predicate inside :data:`_CLAUDE_RESOLVER_TEMPLATE`, which is
       substituted verbatim into the generated ``.plan/execute-script.py``. The
       template is a deliberate policy duplicate of the selector — its docstring
       mandates mirroring — so the invariant has to hold at both, and a change to
       either must be carried to the other by hand.
    """
    if base_path is None:
        return
    marker_ts = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    for bundle_name in polluted_bundles:
        bundle_dir = base_path / bundle_name
        if not bundle_dir.is_dir():
            continue
        live_dirs = _live_version_dirs(bundle_dir)
        if len(live_dirs) <= 1:
            continue
        pinned = _retention_pinned_versions(base_path, bundle_dir)
        for version_dir in live_dirs:
            if version_dir.name in pinned:
                continue
            try:
                (version_dir / '.orphaned_at').write_text(marker_ts, encoding='utf-8')
            except OSError:
                continue


def cmd_preflight(args: argparse.Namespace) -> dict:
    """Deterministic executor / config staleness + multi-version pollution check.

    Compares the executor's embedded ``MARSHALL_VERSION`` and
    ``marshal.json``'s ``system.provisioned_version`` against the installed
    ``dist-manifest.json``'s ``changed_at`` versions, and acts per the two
    asymmetric ownership rules:

    - **Executor is safe derived state (ADR-002).** When it is stale
      (``executor_version < executor_changed_at_version``) the verb regenerates
      it in place and reports ``executor_action: regenerated``; otherwise
      ``executor_action: fresh``.
    - **``marshal.json`` holds user decisions.** It is never auto-mutated —
      config-seed staleness (``marshal_version < config_changed_at_version``) is
      reported advisory-only as ``marshal_status: stale`` for the caller to
      route the user to ``/marshall-steward``; a resolvable, non-stale manifest
      reports ``marshal_status: fresh``.

    - **Fail CLOSED on an unresolvable manifest.** When the installed
      ``dist-manifest.json`` cannot be resolved (``read_installed_manifest``
      returned ``{}``, so ``installed_version == 'unknown'``), no version-based
      staleness verdict can be substantiated. Rather than report a vacuous
      ``fresh`` it can neither confirm nor deny, the verb reports
      ``marshal_status: unknown`` and emits a legible warning to stderr (also
      surfaced in the return's ``warning`` field). The verdict never claims a
      freshness it cannot prove.

    - **Multi-version PYTHONPATH pollution is safe derived state too.** When
      more than one LIVE version dir per bundle is discoverable in the
      plugin-cache context the verb regenerates the executor in place (reported
      through ``executor_action: regenerated``) — the regenerated executor
      embeds only the newest version's paths (``collect_script_dirs``'
      newest-only selection), so a stale version dir left on disk can no longer
      shadow the current scripts. The regen is skipped when version-staleness
      already regenerated in the same run. It then marks the superseded
      (non-newest, non-retention-pinned) version dirs with the ``.orphaned_at``
      deferral marker so the NEXT preflight sees exactly one live version dir per
      bundle and reports ``fresh`` (no regenerated-every-run loop); the actual
      removal defers to the ``marshall-steward`` ``cache-retention-sweep``
      sub-step rather than an immediate ``rmtree`` (which would race a live
      process's PYTHONPATH).

    A fresh install with no manifest resolves ``installed_version`` to the
    ``unknown`` sentinel, so the verb fails closed and reports
    ``marshal_status: unknown`` with a warning rather than a vacuous ``fresh``.

    Returns:
        A single seven-field TOON dict: ``status``, ``executor_action``
        (``fresh`` | ``regenerated``), ``marshal_status`` (``fresh`` | ``stale``
        | ``unknown``), ``installed_version``, ``executor_version``,
        ``marshal_version``, and ``warning`` (the fail-closed message when
        ``marshal_status`` is ``unknown``, else the empty string).
    """
    try:
        base_path: Path | None = get_base_path(
            use_marketplace=getattr(args, 'marketplace', False),
            marketplace_root=getattr(args, 'marketplace_root', None),
        )
    except FileNotFoundError:
        base_path = None

    # Resolve the target the same way cmd_generate does — an explicit --target
    # flag wins; otherwise fall back to marshal.json — so a stale-executor
    # regeneration and the manifest lookup below both look at the SAME target's
    # published dist-manifest.json rather than always defaulting to claude.
    resolved_target: str = getattr(args, 'target', None) or read_marshal_target()

    manifest = read_installed_manifest(base_path, target=resolved_target)
    installed_version = str(manifest.get('version', '') or 'unknown')
    executor_changed_at = str(manifest.get('executor_changed_at_version', '') or '')
    config_changed_at = str(manifest.get('config_changed_at_version', '') or '')

    executor_version = read_executor_version()
    marshal_version = read_marshal_provisioned_version()

    # Executor staleness → safe in-place regeneration (derived state per ADR-002).
    executor_action = 'fresh'
    if executor_changed_at and _version_tuple(executor_version) < _version_tuple(executor_changed_at):
        regen = cmd_generate(args)
        if regen.get('status') != 'success':
            return {
                'status': 'error',
                'error': f'preflight executor regeneration failed: {regen.get("error", "unknown error")}',
            }
        executor_action = 'regenerated'
        # Re-read the freshly stamped version so the report reflects the regen.
        executor_version = read_executor_version()

    # Multi-version PYTHONPATH pollution → safe in-place regeneration. Regenerating
    # re-embeds only the newest version dir's paths (collect_script_dirs' newest-only
    # selection), so an older version dir left on disk can no longer shadow the
    # current scripts. Skip the redundant regen when staleness already regenerated.
    polluted_bundles = _detect_multi_version_pollution(base_path)
    if polluted_bundles:
        # Regenerate the executor once so it embeds only the newest version's
        # paths. Skip the redundant regen when version-staleness already
        # regenerated in the same run.
        if executor_action != 'regenerated':
            regen = cmd_generate(args)
            if regen.get('status') != 'success':
                return {
                    'status': 'error',
                    'error': f'preflight pollution regeneration failed: {regen.get("error", "unknown error")}',
                }
            executor_action = 'regenerated'
            # Re-read the freshly stamped version so the report reflects the regen.
            executor_version = read_executor_version()
        # Mark the superseded (non-newest, non-retention-pinned) version dirs with
        # the deferral marker so the NEXT preflight sees one live version dir per
        # bundle and does not regenerate again. This fires whenever pollution is
        # detected — including when version-staleness already regenerated above —
        # so the pollution signal always clears rather than re-triggering a regen
        # on every run. Removal defers to the marshall-steward
        # cache-retention-sweep sub-step.
        _mark_superseded_version_dirs(base_path, polluted_bundles)

    # Config-seed staleness → advisory only (marshal.json is never auto-mutated).
    marshal_status = 'fresh'
    if config_changed_at and _version_tuple(marshal_version) < _version_tuple(config_changed_at):
        marshal_status = 'stale'

    # Fail CLOSED on an unresolvable manifest. read_installed_manifest returned
    # {} (installed_version is the 'unknown' sentinel), so no version-based
    # staleness verdict can be substantiated. Never report a vacuous 'fresh' the
    # verb can neither confirm nor deny: report the dedicated 'unknown' verdict
    # and emit a legible warning (surfaced both on stderr and in the return).
    warning = ''
    if installed_version == 'unknown':
        marshal_status = 'unknown'
        warning = (
            'installed dist-manifest.json could not be resolved; version-based '
            'staleness cannot be determined (marshal_status=unknown)'
        )
        print(f'WARNING: {warning}', file=sys.stderr)

    return {
        'status': 'success',
        'executor_action': executor_action,
        'marshal_status': marshal_status,
        'installed_version': installed_version,
        'executor_version': executor_version,
        'marshal_version': marshal_version,
        'warning': warning,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate execute-script.py with embedded script mappings',
        epilog=(
            'By default uses plugin-cache context. Use --marketplace for development. '
            'Use --marketplace-root PATH (or set PM_MARKETPLACE_ROOT) to pin marketplace '
            'discovery to an explicit anchor when running from a worktree or alternate '
            'checkout. The flag takes precedence over the env var.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # generate subcommand
    gen_parser = subparsers.add_parser('generate', help='Generate executor with script mappings', allow_abbrev=False)
    gen_parser.add_argument('--force', action='store_true', help='Force regeneration')
    gen_parser.add_argument('--dry-run', action='store_true', help='Show what would be generated')
    gen_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    gen_parser.add_argument(
        '--marketplace-root',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Explicit marketplace anchor directory (must contain marketplace/bundles). '
            'Overrides PM_MARKETPLACE_ROOT, the script-relative walk, and cwd-based discovery.'
        ),
    )
    gen_parser.add_argument(
        '--target',
        default=None,
        choices=['claude', 'opencode'],
        metavar='TARGET',
        help=(
            'Platform target for the embedded target-aware resolver (claude or opencode). '
            'Overrides the value read from .plan/marshal.json. '
            'When omitted, the target is read from marshal.json (defaulting to claude).'
        ),
    )
    gen_parser.set_defaults(func=cmd_generate)

    # verify subcommand
    verify_parser = subparsers.add_parser('verify', help='Verify existing executor', allow_abbrev=False)
    verify_parser.set_defaults(func=cmd_verify)

    # drift subcommand
    drift_parser = subparsers.add_parser('drift', help='Compare with current bundles state', allow_abbrev=False)
    drift_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    drift_parser.add_argument(
        '--marketplace-root',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Explicit marketplace anchor directory (must contain marketplace/bundles). '
            'Overrides PM_MARKETPLACE_ROOT, the script-relative walk, and cwd-based discovery.'
        ),
    )
    drift_parser.set_defaults(func=cmd_drift)

    # paths subcommand
    paths_parser = subparsers.add_parser('paths', help='Verify all mapped paths exist', allow_abbrev=False)
    paths_parser.set_defaults(func=cmd_paths)

    # cleanup subcommand
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old logs', allow_abbrev=False)
    cleanup_parser.add_argument('--max-age-days', type=int, default=7, help='Max age in days (default: 7)')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # preflight subcommand — deterministic executor/config staleness check.
    # Regenerates the executor in place when stale (safe derived state, ADR-002)
    # and reports config-seed staleness advisory-only. The generation flags are
    # accepted because a stale executor triggers an in-place cmd_generate.
    preflight_parser = subparsers.add_parser(
        'preflight',
        help='Check executor/config staleness against the installed dist-manifest',
        allow_abbrev=False,
    )
    preflight_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    preflight_parser.add_argument(
        '--marketplace-root',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Explicit marketplace anchor directory (must contain marketplace/bundles). '
            'Overrides PM_MARKETPLACE_ROOT, the script-relative walk, and cwd-based discovery.'
        ),
    )
    preflight_parser.add_argument(
        '--target',
        default=None,
        choices=['claude', 'opencode'],
        metavar='TARGET',
        help=(
            'Platform target used when a stale executor is regenerated. '
            'Overrides the value read from .plan/marshal.json.'
        ),
    )
    preflight_parser.set_defaults(func=cmd_preflight, dry_run=False)

    args = parser.parse_args()
    result = args.func(args)

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    from file_ops import safe_main

    safe_main(main)()
