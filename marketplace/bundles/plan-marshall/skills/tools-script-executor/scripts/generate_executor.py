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
    resolve_bundle_path,
)
from marketplace_paths import get_base_path as _shared_get_base_path  # noqa: E402, I001
from file_ops import get_base_dir as _get_plan_base_dir  # noqa: E402, I001
from file_ops import get_tracked_config_dir as _get_tracked_config_dir  # noqa: E402, I001


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
    """Get path to templates directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/tools-script-executor/templates')


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
    NEWEST one by numeric version-tuple.  Returning the newest (rather than the
    first ``iterdir`` match) stops a stale, lexically-earlier version dir left on
    disk from shadowing the current scripts — the same multi-version-pollution
    class ``collect_script_dirs`` and ``resolve_bundle_path`` guard against with
    their newest-only ``max()`` selection.  When the currently-pinned version dir
    is pruned, a later invocation re-resolves at runtime to the newest surviving
    version dir.  The ``bundle`` component of the notation is not used for path
    construction (the Claude plugin cache is a flat, single-bundle install) but
    may be useful for logging.

    Args:
        notation: Three-part notation ``{bundle}:{skill}:{script}``.

    Returns:
        Absolute path string of the newest version dir's script, or ``None``
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
        candidates = []
        for version_dir in cache_root.iterdir():
            if not version_dir.is_dir() or version_dir.name.startswith('.'):
                continue
            candidate = version_dir / 'skills' / skill / 'scripts' / f'{script}.py'
            if candidate.is_file():
                candidates.append((version_dir.name, candidate))
        if candidates:
            _name, newest = max(candidates, key=lambda pair: _version_key(pair[0]))
            return str(newest.resolve())
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


def generate_executor(
    mappings: dict[str, str],
    base_path: Path,
    dry_run: bool = False,
    target: str | None = None,
) -> bool:
    """
    Generate execute-script.py with embedded mappings.

    Args:
        mappings: Script notation to path mappings
        base_path: Path to bundles directory for resolving template/logging paths
        dry_run: If True, show what would be generated without writing
        target: Platform target (e.g. ``"claude"`` or ``"opencode"``).  When
            ``None``, the target is read from ``marshal.json`` via
            :func:`read_marshal_target`.

    Returns:
        True if successful
    """
    templates_dir = get_templates_dir(base_path)
    executor_template = templates_dir / 'execute-script.py.template'

    if not executor_template.exists():
        print(f'Error: Template not found: {executor_template}', file=sys.stderr)
        return False

    template = executor_template.read_text()
    mappings_code = generate_mappings_code(mappings)

    # Resolve platform target for target-aware resolver injection.
    resolved_target = target if target is not None else read_marshal_target()
    resolver_code = generate_target_aware_resolver_code(resolved_target)

    # logging module location (unified logging skill)
    logging_scripts_dir = get_logging_scripts_dir(base_path)
    logging_dir = str(logging_scripts_dir.resolve())

    # Shared module directories (must be on sys.path before executor-level imports)
    shared_dirs = get_shared_module_dirs(base_path)
    shared_module_lines = (
        '\n'.join(f"sys.path.insert(0, '{d}')" for d in shared_dirs) if shared_dirs else '# (none detected)'
    )

    # Collect ALL script directories (including subdirectories of skills like script-shared
    # that have no registered scripts but contain importable modules).
    # These are injected as extra PYTHONPATH entries so subprocess-invoked scripts can
    # import from organized subdirectory layouts (e.g., script-shared/scripts/build/).
    all_script_dirs = collect_script_dirs(base_path)
    extra_dirs_code = ', '.join(f"'{d}'" for d in sorted({str(Path(d).resolve()) for d in all_script_dirs}))

    # Provisioning stamps: the version and script-set fingerprint the executor
    # was generated at, read from the installed dist-manifest.json (emitted by
    # the target generator). A fresh install has no manifest yet — the empty
    # sentinel is substituted, never an error, so the executor still generates.
    manifest = read_installed_manifest(base_path, target=resolved_target)
    generated_version = str(manifest.get('version', '') or '')
    mappings_fingerprint = str(manifest.get('executor_scripts_fingerprint', '') or '')

    content = template.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    content = content.replace('{{LOGGING_DIR}}', logging_dir)
    content = content.replace('{{SHARED_MODULE_DIRS}}', shared_module_lines)
    content = content.replace('{{EXTRA_SCRIPT_DIRS}}', extra_dirs_code)
    content = content.replace('{{PLAN_DIR_NAME}}', PLAN_DIR_NAME)
    content = content.replace('{{TARGET_AWARE_RESOLVER}}', resolver_code)
    content = content.replace('{{EXECUTOR_TARGET}}', resolved_target)
    content = content.replace('{{GENERATED_VERSION}}', generated_version)
    content = content.replace('{{MAPPINGS_FINGERPRINT}}', mappings_fingerprint)

    if dry_run:
        print('=== execute-script.py ===')
        print(content[:2000])
        print('... (truncated)')
        return True

    real_executor = executor_path()
    real_executor.parent.mkdir(parents=True, exist_ok=True)
    real_executor.write_text(content)
    return True


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
    (meta-project: ``target/{target}/``) and rides into the plugin cache on
    install. Search order:

    1. ``$PM_DIST_MANIFEST`` — explicit override (tests + alternate installs).
    2. The meta-project target tree (``<repo>/target/{target}/dist-manifest.json``)
       when ``base_path`` points inside a ``marketplace/bundles`` checkout.
    3. ``base_path/dist-manifest.json`` and its parent (cache / target root).

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

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


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

    # Generate executor (uses logging skill from plan-marshall/logging)
    print('Generating executor...')
    if not generate_executor(mappings, base_path, dry_run=args.dry_run, target=resolved_target):
        return {'status': 'error', 'error': 'Failed to generate executor'}

    if args.dry_run:
        print('\nDry run complete. No files written.')
        return {
            'status': 'success',
            'scripts_discovered': len(mappings),
            'executor_target': resolved_target,
            'dry_run': True,
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


def _detect_multi_version_pollution(base_path: Path | None) -> list[str]:
    """Return the bundle names exposing more than one version dir on disk.

    In the plugin-cache layout a bundle resolves as
    ``{base}/{bundle}/{version}/skills/``. A bundle carrying MORE THAN ONE
    version dir (each with a ``skills/`` tree) pollutes PYTHONPATH with multiple
    versions of the same scripts — the exact condition ``collect_script_dirs``'
    newest-only selection guards against at discovery time. Surfacing the
    on-disk pollution lets the preflight regenerate the executor (which then
    embeds only the newest version's paths). Returns the sorted list of polluted
    bundle names (empty when the tree is clean or ``base_path`` is unresolved).
    """
    if base_path is None or not base_path.is_dir():
        return []
    polluted: list[str] = []
    try:
        for bundle_dir in base_path.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
                continue
            try:
                version_dirs = [
                    d
                    for d in bundle_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.') and (d / 'skills').is_dir()
                ]
            except OSError:
                continue
            if len(version_dirs) > 1:
                polluted.append(bundle_dir.name)
    except OSError:
        pass
    return sorted(polluted)


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
      route the user to ``/marshall-steward``; otherwise ``marshal_status:
      fresh``.

    - **Multi-version PYTHONPATH pollution is safe derived state too.** When
      more than one version dir per bundle is discoverable in the plugin-cache
      context the verb regenerates the executor in place (reported through
      ``executor_action: regenerated``) — the regenerated executor embeds only
      the newest version's paths (``collect_script_dirs``' newest-only
      selection), so a stale version dir left on disk can no longer shadow the
      current scripts. The regen is skipped when version-staleness already
      regenerated in the same run.

    A fresh install with no manifest resolves both changed_at values to the
    empty sentinel, so nothing is stale and the verb is a no-op reporting
    ``fresh``.

    Returns:
        A single six-field TOON dict: ``status``, ``executor_action`` (``fresh``
        | ``regenerated``), ``marshal_status`` (``fresh`` | ``stale``),
        ``installed_version``, ``executor_version``, ``marshal_version``.
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
    if polluted_bundles and executor_action != 'regenerated':
        regen = cmd_generate(args)
        if regen.get('status') != 'success':
            return {
                'status': 'error',
                'error': f'preflight pollution regeneration failed: {regen.get("error", "unknown error")}',
            }
        executor_action = 'regenerated'
        # Re-read the freshly stamped version so the report reflects the regen.
        executor_version = read_executor_version()

    # Config-seed staleness → advisory only (marshal.json is never auto-mutated).
    marshal_status = 'fresh'
    if config_changed_at and _version_tuple(marshal_version) < _version_tuple(config_changed_at):
        marshal_status = 'stale'

    return {
        'status': 'success',
        'executor_action': executor_action,
        'marshal_status': marshal_status,
        'installed_version': installed_version,
        'executor_version': executor_version,
        'marshal_version': marshal_version,
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
