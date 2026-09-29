#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Generate and manage execute-script.py with embedded script mappings.

Usage:
    python3 generate_executor.py generate [--force] [--dry-run] [--marketplace] [--marketplace-root PATH] [--target TARGET]
    python3 generate_executor.py verify [--target TARGET]
    python3 generate_executor.py bootstrap [--marketplace] [--marketplace-root PATH] [--target TARGET]
    python3 generate_executor.py drift [--marketplace] [--marketplace-root PATH] [--target TARGET]
    python3 generate_executor.py preflight [--marketplace] [--marketplace-root PATH] [--target TARGET]
    python3 generate_executor.py paths [--target TARGET]
    python3 generate_executor.py cleanup [--max-age-days N]

Subcommands:
    generate    Generate executor with script mappings
    verify      Verify existing executor is valid
    bootstrap   Sanctioned direct-path bootstrap (see below)
    drift       Compare executor mappings with current marketplace state
    preflight   Report the preconditions a regeneration depends on
    paths       Verify all mapped paths exist
    cleanup     Clean up old logs

Direct-path bootstrap:
    A fresh clone has no ``<root>/.plan/execute-script.py`` yet, so no
    executor-mediated call can create it — ``bootstrap`` is the sanctioned
    first call, and it is detection-gated rather than unconditional.
    :func:`cmd_bootstrap` owns that gate: which states regenerate, and the
    ``action: not_needed`` refusal.

The executor is always written directly to ``<root>/.plan/execute-script.py``
(the tracked ``.plan/`` directory inside the main git checkout). There is no
shim-to-external-executor split — every documented call site
(``python3 .plan/execute-script.py …``) runs the real executor directly.

Self-checking, atomic regeneration:
    ``generate`` is fail-safe by construction — it never overwrites a working
    executor with a malformed one, and never reports success while writing a
    surfaces-less one. Five deterministic guards run BEFORE any
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
    marketplace layout; (5) a **fail-open guard** refuses a regeneration that
    emits zero surfaces where the previous executor either carried some or could
    not be read at all (a silently stripped surface set would leave the
    pre-spawn validator inert, and an unreadable previous cannot prove none are
    being stripped). Guards 1-3
    are shape checks on the content; guard 4 compares the emitted path families
    against each other; guard 5 is a semantic check on the derivation outcome.
    Only a content that passes all five is committed, and the
    commit is **atomic** — written to a sibling temp path and ``os.replace``-d
    onto the real executor, so a partial or broken write can never leave a
    corrupt executor in place. Every regen caller (the meta upgrade path, the
    consumer upgrade path, and the finalize ``sync-plugin-cache`` path) inherits
    this protection because it lives inside the generator itself.

Context Detection:
    By default, operates in plugin-cache context (~/.claude/plugins/cache/plan-marshall/).
    Use --marketplace flag for marketplace development context (marketplace/bundles/).

    The ``--marketplace-root PATH`` flag pins marketplace discovery to an
    explicit anchor directory, overriding the ``PM_MARKETPLACE_ROOT`` env var
    and the cwd-based fallback. It is declared on the four verbs that ANCHOR a
    discovery (``generate``, ``bootstrap``, ``drift``, ``preflight``); the verbs
    that read a discovered tree without choosing where to look (``verify``,
    ``paths``) inherit the anchor from their environment and cwd. Run a
    subcommand's ``--help`` for the flag set that verb actually accepts, rather
    than reading a verb list from here.

    ``--target`` is registered on ALL SIX target-resolving verbs (``generate``,
    ``verify``, ``bootstrap``, ``drift``, ``preflight``, ``paths``) with one
    shared accept-set and one shared help text, and every one of them resolves
    its ``{target, marketplace-root}`` context through
    ``target_context.resolve_context``. There is no per-verb default and no
    verb-private reader of ``marshal.json``: the cascade is env signal first
    (``ANTIGRAVITY_AGENT`` / ``OPENCODE`` / ``OPENCODE_PID`` /
    ``CLAUDE_CODE_SESSION_ID``), then ``runtime.target`` from the nearest
    ``marshal.json``, then a REPORTED fallback. The tier that produced the
    answer rides every payload that follows a resolution — the success
    payloads of ``generate``, ``verify``, ``drift``, ``paths`` and
    ``preflight``, the coverage-error payloads of ``generate`` and ``drift``,
    and ``bootstrap``'s ``generated`` payload — as
    ``target_source`` beside the resolved ``target``, so "resolved to opencode"
    and "fell back to claude" are never the same observation. ``bootstrap``'s
    ``not_needed`` payloads carry neither: that path resolves no target.

    ``PM_MARKETPLACE_ROOT`` promotes itself above the deployed-bundle cache
    (cache-first scope) only while nothing else has declared the context — no
    ``--target`` was given, and no env or ``marshal.json`` tier resolved one;
    ``target_context.resolve_context`` folds it into the verb's anchor only on
    that fallback tier. It is still consulted by marketplace discovery itself
    (``--marketplace``, and the cache-first leg when no cache exists), where it
    ranks ahead of the cwd walk-up on every tier. The flag takes precedence
    when both are supplied. Use this when invoking the script from
    a worktree or alternate checkout where Path.cwd() would otherwise resolve
    to the wrong marketplace tree.

Fail-closed discovery:
    Script discovery can return a mapping that is short of what the tree holds
    — empty when the scan found nothing, truncated when the glob fallback's
    narrower rules dropped scripts — and neither failure is visible in the
    returned dict. ``generate`` therefore refuses to write an executor from an
    under-covered scan, and ``drift`` reports the same condition as an error
    rather than as a removal list; both publish the enumerated count, the
    discovered count and the named exclusion rules that produced the verdict.
    Generation also refuses to substitute a logging-module directory that does
    not exist, and refuses to emit its ``# (none detected)`` shared-module
    degradation unless discovery coverage was established. A resolver failure
    is a distinct third outcome everywhere, never a vacuous clean one (ADR-009,
    ADR-019).

Runtime Side-effects:
    The generated executor performs NO session-to-plan binding write. The
    per-session active-plan cache at
    ``~/.cache/plan-marshall/sessions/{session_id}/active-plan`` is owned by
    platform-runtime: ``session_binding`` hosts the pure read/write/GC policy,
    the ``session bind`` operation dispatches it, and the manage-status
    phase-state-write drive seam fires it. This is the runtime home D3 was told
    to find; the executor instead consumes the binding through the
    platform-runtime terminal-title reader (cluster-01 ``session render-title``)
    so the main orchestration tab (cwd = repo root) renders
    ``pm:{phase}[:{short_description}]`` instead of falling through to the
    active-command segment. No generator-time substitution is required.

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
from typing import NamedTuple, TypedDict

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
# The SINGLE argparse accept-set derivation, shared with plugin-doctor's
# edit-time rules. The generator embeds what it derives; the doctor reads the
# same module at edit time. One derivation, two consumers, nothing to drift.
import argparse_surface as surface_api  # noqa: E402
import deployed_layout  # noqa: E402
from command_forms import SYNC_PLUGIN_CACHE_COMMAND  # noqa: E402
from file_ops import get_base_dir as _get_plan_base_dir  # noqa: E402
from file_ops import get_tracked_config_dir as _get_tracked_config_dir  # noqa: E402
from marketplace_bundles import (  # noqa: E402
    build_pythonpath,
    collect_script_dirs,
    extract_bundle_name,
    find_bundles,
    resolve_bundle_path,
)
from marketplace_paths import MARKETPLACE_BUNDLES_PATH  # noqa: E402
from marketplace_paths import get_base_path as _shared_get_base_path  # noqa: E402
from marketplace_paths import get_bundle_cache_roots as _shared_get_bundle_cache_roots  # noqa: E402
from marketplace_paths import get_project_skill_roots as _shared_get_project_skill_roots  # noqa: E402

# The single target/context resolver. Every target-resolving verb routes
# through ``resolve_context`` below rather than reading ``marshal.json`` itself,
# so the six verbs cannot reach different answers on one machine. The bootstrap
# loop above already front-loads ``script-shared/scripts`` onto ``sys.path``,
# which is where this lives.
from target_context import TargetContext, resolve_context, resolve_target  # noqa: E402


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


def get_base_path(
    use_marketplace: bool = False, marketplace_root: Path | None = None, target: str | None = None
) -> Path:
    """Determine base path based on context.

    By default (use_marketplace=False), tries plugin-cache first, then marketplace.
    Delegates to shared marketplace_paths module.

    Args:
        use_marketplace: If True, force marketplace context (development mode).
            If False (default), tries plugin-cache first then marketplace.
        marketplace_root: Optional explicit override anchor for marketplace
            discovery. Normally the value ``resolve_context`` validated out of
            ``--marketplace-root``, or ``PM_MARKETPLACE_ROOT`` when — and only
            when — the target fell through to the fallback tier; forwarded
            verbatim to
            :func:`script_shared.marketplace_paths.get_base_path` and applied
            to the marketplace-aware scopes (``marketplace``, ``cache-first``).
            See :func:`script_shared.marketplace_paths.find_marketplace_path`
            for the three-step resolution order.
        target: The runtime target this call operates under, forwarded to the
            shared resolver so the target-dependent scopes (``cache-first`` and
            ``plugin-cache`` cache legs, ``global``, ``project``) resolve for
            THAT target rather than the ambient cascade's answer. In the
            ``cache-first`` scope a non-``None`` target also keeps an ambient
            ``PM_MARKETPLACE_ROOT`` from outranking the cache (see
            ``marketplace_paths._env_anchor_is_last_resort``).
    """
    scope = 'marketplace' if use_marketplace else 'cache-first'
    return _shared_get_base_path(scope, marketplace_root=marketplace_root, target=target)


def resolve_verb_context(args: argparse.Namespace) -> TargetContext:
    """Resolve the ``{target, marketplace-root}`` context for a verb's argv.

    The one place a verb's ``--target`` / ``--marketplace-root`` flags become a
    resolved context, so all six target-resolving verbs (``generate``,
    ``verify``, ``bootstrap``, ``drift``, ``preflight``, ``paths``) read the
    same flags through the same cascade and reach the same conclusion on the
    same machine. ``getattr`` with a ``None`` default is deliberate: a verb
    that registers ``--target`` but not ``--marketplace-root`` (``verify`` and
    ``paths``) must still reach this function rather than growing its own
    bespoke resolution. Read a verb's own ``--help`` for the flag set it
    actually registers.

    Args:
        args: The parsed verb namespace.

    Returns:
        The resolved :class:`target_context.TargetContext`.

    Raises:
        ValueError: when a supplied ``--target`` or ``--marketplace-root`` is
            not a usable value. The containment check belongs at the shared
            resolver (ADR-016), so the refusal surfaces here and every verb
            reports it the same way.
    """
    return resolve_context(
        target=getattr(args, 'target', None),
        marketplace_root=getattr(args, 'marketplace_root', None),
    )


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
    """Get path to logging scripts directory based on context.

    The skill is named through the shared layout vocabulary rather than by
    spelling ``'skills/{skill}/scripts'`` here: that string is a LAYOUT
    spelling, and a root that deploys the flat shape has no ``skills/{skill}``
    component to carry it — only a dash-namespaced ``{bundle}-{skill}``
    directory. ``marketplace_bundles.resolve_bundle_path`` (a
    ``deployed_layout`` consumer) reconciles the two, so a single skill name here
    resolves against either shape.
    """
    return _resolve_plan_marshall_path(base_path, deployed_layout.skill_scripts_subpath('manage-logging'))


def get_shared_module_dirs(base_path: Path) -> list[Path]:
    """Get paths to shared module directories that must be on sys.path at executor level.

    Shared modules are skills whose scripts are imported by other scripts (e.g., plan_logging
    imports input_validation) but have no executable script notation in the SCRIPTS mapping.
    These directories must be added to sys.path before any executor-level imports.

    The skill names are the single source; each is turned into a layout subpath by
    ``deployed_layout``, so the shared-module set resolves against a nested root
    and a flat deployed root alike. That set is the one the emitted executor
    puts on ``sys.path`` before its own imports, so a root whose shape this
    cannot read produces an executor that cannot import the shared modules at
    all — which is why the empty result is gated on the discovery-coverage
    verdict rather than emitted as ``# (none detected)``.
    """
    dirs = []
    for skill in SHARED_MODULE_SKILLS:
        resolved = _resolve_plan_marshall_path(base_path, deployed_layout.skill_scripts_subpath(skill))
        if resolved.is_dir():
            dirs.append(resolved.resolve())
    return dirs


#: The skills whose scripts are imported by other scripts but carry no
#: executable notation of their own; see :func:`get_shared_module_dirs`.
SHARED_MODULE_SKILLS: tuple[str, ...] = (
    'tools-file-ops',
    'tools-input-validation',
    'ref-toon-format',
    'script-shared',
    'manage-change-ledger',
)


def shared_module_skill_label(scripts_dir: Path) -> str:
    """Return the skill name a resolved shared-module ``scripts/`` dir belongs to.

    On a nested tree that is the directory's parent name. On a flat deployment
    the parent is the dash-joined ``{bundle}-{skill}``, which the executor's
    self-heal cannot match to a skill, so the flat name is mapped back to the
    shared skill it was joined from — by JOINING each candidate, never by
    splitting the directory name.
    """
    parent = scripts_dir.parent.name
    for skill in SHARED_MODULE_SKILLS:
        if parent in (skill, deployed_layout.flat_skill_dir_name('plan-marshall', skill)):
            return skill
    return parent


# ============================================================================
# SCRIPT DISCOVERY
# ============================================================================


def marketplace_root_for_base(base_path: Path) -> Path | None:
    """Return the marketplace anchor that ``base_path``'s bundles dir sits under.

    ``marketplace_paths.find_marketplace_path`` composes every anchor — the
    explicit ``--marketplace-root`` value and the ``PM_MARKETPLACE_ROOT`` env
    var alike — by joining ``marketplace/bundles`` onto it, so the anchor a
    consumer must be handed is the directory CONTAINING ``marketplace/``. For a
    base at ``<root>/marketplace/bundles`` that is ``<root>``.

    Returns ``None`` for a base that is not inside a marketplace tree: a
    plugin-cache root has no marketplace anchor to offer, and handing the
    inventory an anchor it cannot use would be worse than handing it none.

    Derived by locating the ``marketplace/bundles`` segment in the resolved path
    rather than by counting parents, so a base several levels deeper (a version
    dir inside a cache that itself lives in a checkout) still resolves to the
    right anchor.
    """
    base_str = str(base_path.resolve())
    marker = f'/{MARKETPLACE_BUNDLES_PATH}'
    idx = base_str.rfind(marker)
    if idx < 0:
        return None
    return Path(base_str[:idx])


def discover_scripts(base_path: Path) -> dict[str, str]:
    """
    Discover all scripts from bundles using inventory script.

    The resolved ``base_path`` is PROPAGATED to the scan through the
    ``PM_MARKETPLACE_ROOT`` env anchor whenever it sits inside a marketplace
    tree. Without that, the subprocess resolved its own base from its own
    environment and cwd, so a run with ``--marketplace-root <worktree>``
    scanned whatever tree the ambient resolution found while the caller
    believed it had scanned the worktree — and the discovery-coverage verdict
    would then be comparing two different trees. The scan is additionally
    BOUND to ``base_path`` through ``--base-path``, so the plugin-cache leg
    scans exactly the tree the caller resolved rather than whatever the
    subprocess's AMBIENT target cache is — an explicit ``--target`` that
    differed from the ambient one used to make the two sides of the coverage
    comparison read two different installations.

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

    marketplace_root = marketplace_root_for_base(base_path)
    if marketplace_root is not None:
        env['PM_MARKETPLACE_ROOT'] = str(marketplace_root)

    # Run inventory scan
    result = subprocess.run(
        [
            'python3',
            str(inventory_script),
            '--scope',
            scope,
            '--base-path',
            str(base_path),
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
                # Skip private modules and test files. Test files are matched
                # PRECISELY by the ``test_`` prefix / ``_test`` suffix convention:
                # a bare ``'test' in name`` substring also drops legitimate
                # entrypoints whose name merely CONTAINS ``test`` (``latest.py``,
                # ``attestation.py``, ``contest.py``), silently stripping real
                # scripts from the fallback-discovered map.
                stem = script_file.stem
                if script_file.name.startswith('_') or stem.startswith('test_') or stem.endswith('_test'):
                    continue

                # Use three-part notation: bundle:skill:script
                notation = deployed_layout.script_notation(bundle_name, skill_name, script_file)
                abs_path = str(script_file.resolve())
                mappings[notation] = abs_path

    # A flat deployed root's children are the skill root, not bundles, so the
    # nested walk above contributes nothing there; the shared flat walk does.
    for flat_script in deployed_layout.flat_script_inventory(base_path).scripts:
        mappings.setdefault(flat_script.notation, str(flat_script.path.resolve()))

    return mappings


# ============================================================================
# DISCOVERY COVERAGE
# ============================================================================
# ``discover_scripts`` shells out to the inventory scan; ``discover_scripts_fallback``
# globs the tree. Either can return a mapping that is short of what the tree
# actually holds — an empty one when the scan found nothing, a truncated one
# when the fallback's narrower globbing rules silently dropped scripts — and
# neither failure is visible in the returned dict. Historically both were
# accepted and then LAUNDERED into a fact about the world: ``cmd_drift`` turned a
# resolver failure into "every executor mapping is removed", and ``cmd_generate``
# emitted an executor built from whatever the scan happened to return.
#
# The coverage verdict below closes that. It enumerates the same tree
# INDEPENDENTLY (directly off the filesystem, sharing only the bundle-discovery
# primitives the inventory scan itself uses) and compares the two, so the
# threshold is derived from the filesystem rather than asserted as a constant,
# and both an empty and a truncated scan fail with the discrepancy in the
# payload.

#: The named exclusion categories, reported on every verdict so a reader can
#: tell a legitimate skip from a genuine shortfall. Each maps a category key to
#: the rule that excludes it — the rule is stated here, next to the count, not
#: inferred from a number.
#:
#: No category names a ``__pycache__`` artefact: the candidate set is already
#: ``*.py``/``*.sh`` UNDER a ``scripts/`` directory, so such an artefact is never a
#: candidate and a rule for it would exclude nothing — a documented condition the
#: enumeration can never reach, indistinguishable from a rule never implemented.
DISCOVERY_EXCLUSION_RULES: dict[str, str] = {
    'private_module': "script files whose name starts with '_' (PEP-8 internal module, not a CLI entrypoint)",
    'unattributed_flat_skill': (
        'flat {bundle}-{skill} directories carrying scripts/ whose SKILL.md records no bundle identity '
        '(not emitted by a plan-marshall flat target, or deployed before the identity was recorded) — '
        'their notation cannot be derived, so they are counted here rather than guessed'
    ),
}


class DiscoveryCoverage(TypedDict):
    """The enumerated-versus-discovered verdict for one script-discovery result.

    ``coverage_ok`` is the single boolean every caller branches on.
    ``missing_notations`` is the diagnosable core of the verdict: the notations
    the independent enumeration found that the scan did not report. It is capped
    at :data:`_MISSING_NOTATION_SAMPLE` entries so a wholly empty scan against a
    large tree cannot turn the error payload into a second discovery report.
    """

    coverage_ok: bool
    scripts_enumerated: int
    scripts_expected: int
    scripts_discovered: int
    exclusions: dict[str, int]
    missing_notations: list[str]


#: How many missing notations an error payload names before truncating. The
#: count fields carry the magnitude; the sample only has to make the failure
#: locatable.
_MISSING_NOTATION_SAMPLE = 20

#: The verdict a caller that never assessed coverage is treated as carrying:
#: coverage NOT established. Used only to give the refusal a payload that says
#: so, rather than a payload that looks like a measured zero.
_UNASSESSED_COVERAGE: DiscoveryCoverage = {
    'coverage_ok': False,
    'scripts_enumerated': 0,
    'scripts_expected': 0,
    'scripts_discovered': 0,
    'exclusions': dict.fromkeys(DISCOVERY_EXCLUSION_RULES, 0),
    'missing_notations': [],
}


def enumerate_script_notations(base_path: Path) -> tuple[set[str], set[str], dict[str, int]]:
    """Enumerate the notations the inventory scan should yield for ``base_path``.

    An INDEPENDENT derivation of the same set ``discover_scripts`` obtains from
    the inventory subprocess: same bundle-discovery primitives
    (:func:`marketplace_bundles.find_bundles` / ``extract_bundle_name``, which is
    what the scan itself uses), same walk over ``<bundle>/skills/**/scripts/**``
    for ``.py``/``.sh``, same ``{bundle}:{skill}:{stem}`` notation — but read
    straight off the filesystem instead of through a subprocess and a JSON
    round-trip. "Independent" is a claim about the MECHANISM, and it is the one
    that matters: a comparison is only evidence if the two sides can fail
    separately, and a subprocess that dies, times out or returns a partial
    payload cannot fail the same way a direct walk does.

    The comparison quantity is the set of DISTINCT notations, not the number of
    files. Two files can legitimately share a notation (``foo.py`` and
    ``foo.sh`` in one skill; ``scripts/foo.py`` and ``scripts/sub/foo.py``), and
    the discovered mapping is keyed by notation, so counting files would report
    a shortfall for a tree that is in fact fully covered.

    Both deployed layouts are enumerated. The FLAT leg goes through
    :func:`deployed_layout.flat_script_inventory` — the same walk the inventory
    scan uses for a flat root — and every notation on either leg is built by
    :func:`deployed_layout.script_notation`, so the two sides of the comparison
    share one derivation rule. A flat directory whose ``SKILL.md`` records no
    bundle identity cannot be named and is counted under
    ``unattributed_flat_skill`` instead.

    Args:
        base_path: The resolved bundles/cache root to enumerate.

    Returns:
        ``(notations, excluded_paths, exclusion_counts)`` — the notations a
        complete scan must yield, the paths deliberately skipped, and the
        per-category skip counts drawn from :data:`DISCOVERY_EXCLUSION_RULES`.
    """
    notations: set[str] = set()
    excluded: set[str] = set()
    counts: dict[str, int] = dict.fromkeys(DISCOVERY_EXCLUSION_RULES, 0)

    for bundle_dir in find_bundles(base_path):
        bundle_name = extract_bundle_name(bundle_dir)
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        candidates = sorted(skills_dir.rglob('scripts/**/*.sh')) + sorted(skills_dir.rglob('scripts/**/*.py'))
        for script_file in candidates:
            if deployed_layout.is_private_script(script_file):
                excluded.add(str(script_file))
                counts['private_module'] += 1
                continue
            if not script_file.is_file():
                continue
            # The skill name is the parent of the nearest ancestor named
            # ``scripts``, so a script in a sub-directory
            # (``scripts/build/x.py``) attributes to the same skill as one
            # directly in ``scripts/``.
            skill_dir = script_file.parent
            while skill_dir.name != 'scripts' and skill_dir != skills_dir:
                skill_dir = skill_dir.parent
            notations.add(deployed_layout.script_notation(bundle_name, skill_dir.parent.name, script_file))

    flat = deployed_layout.flat_script_inventory(base_path)
    notations.update(script.notation for script in flat.scripts)
    excluded.update(str(path) for path in flat.private)
    counts['private_module'] += len(flat.private)
    excluded.update(str(path) for path in flat.unattributed)
    counts['unattributed_flat_skill'] += len(flat.unattributed)

    return notations, excluded, counts


def assess_discovery_coverage(base_path: Path, discovered: dict[str, str]) -> DiscoveryCoverage:
    """Compare a discovery result against an independent enumeration of the tree.

    The single verdict every consumer of a discovery result branches on —
    ``cmd_generate`` refuses to generate on a failing verdict, ``cmd_drift``
    refuses to report a removal list on one, and ``generate_executor`` refuses
    to emit its ``# (none detected)`` shared-module degradation on one.

    Args:
        base_path: The resolved bundles/cache root the scan ran against.
        discovered: The notation → path mapping the scan returned.

    Returns:
        The :class:`DiscoveryCoverage` verdict. ``coverage_ok`` is ``True`` when
        the enumeration found no notation the scan failed to report. A NESTED
        tree that is genuinely empty (nothing enumerated, nothing discovered)
        passes, and the counts travel with it so a reader can tell it from a
        truncated scan. A FLAT root with nothing attributable does NOT pass: a
        flat base is only reached as a target's deployed cache, so an empty
        attributable population there means the deployment could not be read
        (every skill unattributed, or none deployed) — the vacuous 0/0 this
        guard exists to refuse, not a measured absence.
    """
    enumerated, _excluded, counts = enumerate_script_notations(base_path)
    missing = sorted(enumerated - set(discovered))
    unreadable_flat_root = not enumerated and bool(deployed_layout.skill_roots(base_path))
    return {
        'coverage_ok': not missing and not unreadable_flat_root,
        'scripts_enumerated': len(enumerated),
        'scripts_expected': len(enumerated),
        'scripts_discovered': len(discovered),
        'exclusions': counts,
        'missing_notations': missing[:_MISSING_NOTATION_SAMPLE],
    }


def coverage_error_payload(
    error: str,
    detail: str,
    coverage: DiscoveryCoverage,
    **extra: object,
) -> dict:
    """Build the ``status: error`` payload a failing coverage verdict publishes.

    The enumerated count, the discovered count and the declared exclusion rules
    all ride the payload (ADR-019: an audit separates what it could not evaluate
    from what it evaluated and found wanting). A failure with only a message
    would leave the reader to re-derive the discrepancy by hand, which is the
    work the verdict already did.
    """
    return {
        'status': 'error',
        'error': error,
        'detail': detail,
        'scripts_enumerated': coverage['scripts_enumerated'],
        'scripts_expected': coverage['scripts_expected'],
        'scripts_discovered': coverage['scripts_discovered'],
        'exclusion_rules': DISCOVERY_EXCLUSION_RULES,
        'excluded_counts': coverage['exclusions'],
        'missing_notations': coverage['missing_notations'],
        **extra,
    }


def discover_local_scripts(cwd: Path | None = None) -> dict[str, str]:
    """
    Discover project-local scripts from the active target's skill roots.

    The roots come from ``marketplace_paths.get_project_skill_roots()`` — the
    platform-runtime ``layout skill-roots`` op — rather than a hardcoded
    ``.claude/skills`` literal, so a non-Claude target discovers from its own
    roots. Roots are probed in list order against ``cwd`` (``~``-anchored
    roots are expanded); the first existing root that data is consumed from
    wins, and a target with no resolvable roots yields an empty mapping.

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

    roots = _shared_get_project_skill_roots()
    if not roots:
        return {}

    mappings: dict[str, str] = {}

    for root in roots:
        local_skills = Path(root).expanduser() if root.startswith('~') else cwd / root
        if not local_skills.is_dir():
            continue

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
                    if notation not in mappings:
                        mappings[notation] = str(script_file.resolve())

    return mappings


# ============================================================================
# TARGET-AWARE RESOLVER GENERATION
# ============================================================================
# The generated executor resolves a notation it has no embedded mapping for by
# walking the layout ITS TARGET actually deploys. There are exactly TWO such
# shapes, and the template below for each target probes every one of them that
# target can encounter, so the emitted resolver agrees with the deployed tree
# whichever of the two the machine carries:
#
# 1. The NESTED shape — ``{bundle}/skills/{skill}/scripts/{script}.py``. This is
#    the marketplace source tree (``marketplace/bundles/{bundle}/skills/...``)
#    and the Claude plugin cache (``.../cache/plan-marshall/<version>/skills/
#    {skill}/scripts/...``, which is nested and single-bundle, so the ``bundle``
#    component of the notation is not part of the path there).
# 2. The FLAT deployed shape — ``skills/{bundle}-{skill}/scripts/{script}.py``,
#    the dash-namespaced directory naming the OpenCode and Antigravity targets
#    deploy, used so a flat config directory needs no hierarchy.
#
# Probe order is NESTED first, in every template: a live ``marketplace/bundles``
# checkout at or above the executor file wins over any deployed copy, which
# mirrors the tree-first ordering :func:`generate_mappings_code` already emits
# for the embedded mapping. The Claude template used to walk the plugin cache
# only, and the Antigravity template the flat roots only, so on a machine whose
# deployment was the shape the template did not model, the resolver found
# nothing at all while reporting no error. Each template carries the NESTED
# tree-first leg; the FLAT leg is carried only by the two targets that deploy
# it, because a Claude installation has no flat root to find.

# Template for the Claude target-aware resolver.
# Resolves ``{bundle}:{skill}:{script}`` tree-first against a live
# ``marketplace/bundles`` checkout, then by globbing the plugin cache.
# The bundle component is intentionally ignored for the plugin-cache leg
# because the cache layout is
# ``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``
# (single-bundle installation); the bundle in the notation is used to generate
# suggestions only.
_CLAUDE_RESOLVER_TEMPLATE = '''\
def _resolve_notation_by_target(notation: str) -> str | None:
    """Claude target: resolve notation tree-first, then via plugin-cache glob.

    Two shapes, probed in this order:

      0. ``marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``
         in a live checkout at or above THIS executor file (the NESTED shape).
         Anchoring on the executor file rather than cwd ties the tree to the
         artifact being run, and probing it first means a regen on a developer
         machine resolves to tree code even with a stale cache present — the
         same tree-first rule the embedded mapping is emitted under.
      1. ``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``
         (the deployed NESTED shape). Every version dir carrying the candidate
         is collected and the NUMERICALLY-NEWEST is returned.  Selecting the
         newest (rather than the first ``iterdir`` match) stops a stale older
         version dir left on disk from shadowing the current scripts.  When the
         currently-selected version dir is pruned, a later invocation
         re-resolves at runtime to the newest surviving version dir carrying the
         script.  The ``bundle`` component of the notation is not used for path
         construction on THIS leg (the Claude plugin cache is a single-bundle
         install) but may be useful for logging.

    The plugin-cache ``.orphaned_at`` marker is NOT consulted.  The field has a
    foreign co-producer — Claude Code's own plugin GC writes the same filename on
    its own schedule — so it is a variable this repository neither owns nor can
    version, and newest-wins needs no currency signal from it: a sync only ever
    adds a *newer* version dir.  This agrees with
    ``marketplace_bundles.select_live_version_dir`` by construction (both return
    the newest eligible dir), but the resolver reaches that agreement on its own
    terms rather than by importing the selector: the generated executor is
    bootstrap-free and must resolve notations BEFORE any marketplace module is
    importable, so the newest-wins body is duplicated here deliberately.

    Args:
        notation: Three-part notation ``{bundle}:{skill}:{script}``.

    Returns:
        Absolute path string of the resolved script, or ``None`` when no match
        is found.
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
    bundle, skill, script = parts

    try:
        _executor_file = Path(__file__).resolve()
    except (OSError, ValueError, NameError):
        _executor_file = None
    if _executor_file is not None:
        _rel = Path('marketplace') / 'bundles' / bundle / 'skills' / skill / 'scripts' / f'{script}.py'
        for _parent in [_executor_file.parent, *_executor_file.parents]:
            try:
                _candidate = _parent / _rel
                if _candidate.is_file():
                    return str(_candidate.resolve())
            except (OSError, ValueError):
                continue

    try:
        cache_root = Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
        if not cache_root.is_dir():
            return None
        version_dirs = [d for d in cache_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if not version_dirs:
            return None
        candidates = []
        for version_dir in version_dirs:
            candidate = version_dir / 'skills' / skill / 'scripts' / f'{script}.py'
            if candidate.is_file():
                candidates.append((version_dir, candidate))
        if candidates:
            _dir, selected = max(candidates, key=lambda pair: _version_key(pair[0].name))
            return str(selected.resolve())
    except (OSError, ValueError, RuntimeError):
        pass
    return None
'''

# Template for the OpenCode target-aware resolver.
# Resolves ``{bundle}:{skill}:{script}`` tree-first, then by walking 7 standard
# OpenCode roots, using the dash-namespaced ``{bundle}-{skill}`` directory
# layout emitted by the OpenCode build target. Paths are always converted to
# absolute form before return to sidestep cwd ambiguity (anomalyco/opencode#9077).
# User-global roots stay in the walk but behind the live tree, so a stale
# user-global copy can never shadow tree code.
_OPENCODE_RESOLVER_TEMPLATE = '''\
def _resolve_notation_by_target(notation: str) -> str | None:
    """OpenCode target: resolve notation tree-first, then via 7-root walk.

    A live ``marketplace/bundles`` checkout above THIS executor file wins
    over every deployed copy: the tree probe runs BEFORE the OpenCode skill
    discovery roots, so a regen on an OpenCode machine resolves every
    notation to tree code with a stale cache present.  Anchoring on the
    executor file (rather than cwd) ties the tree to the artifact being run —
    an executor generated into ``<checkout>/.plan/`` always sees its own
    checkout — while a deployed executor with no checkout above it falls
    through to the dash-namespaced ``{bundle}-{skill}/scripts/{script}.py``
    roots below (project-local first, user-global last — the user-global
    roots are deprioritised behind the tree, never ahead of it).  The first
    match is returned as an absolute path (anomalyco/opencode#9077).

    Roots searched in order:
      0. marketplace/bundles tree above this executor file (tree-first probe)
      1. $OPENCODE_CONFIG_DIR/skills/     (env-var override)
      2. .opencode/skills/               (project-local)
      3. .claude/skills/                 (project-local cross-compat)
      4. .agents/skills/                 (project-local)
      5. ~/.config/opencode/skills/      (user-global, deprioritised)
      6. ~/.claude/skills/               (user-global cross-compat, deprioritised)
      7. ~/.agents/skills/               (user-global, deprioritised)

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
        _executor_file = Path(__file__).resolve()
    except (OSError, ValueError, NameError):
        _executor_file = None
    if _executor_file is not None:
        _rel = Path('marketplace') / 'bundles' / bundle / 'skills' / skill / 'scripts' / script_file
        for _parent in [_executor_file.parent, *_executor_file.parents]:
            try:
                _candidate = _parent / _rel
                if _candidate.is_file():
                    return str(_candidate.resolve())
            except (OSError, ValueError):
                continue

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


# Template for the Antigravity target-aware resolver.
# Resolves ``{bundle}:{skill}:{script}`` tree-first against a live
# ``marketplace/bundles`` checkout, then by walking standard Antigravity roots
# using the dash-namespaced ``{bundle}-{skill}`` directory layout emitted by the
# Antigravity build target. Paths are always converted to absolute form before
# return to sidestep cwd ambiguity.
_ANTIGRAVITY_RESOLVER_TEMPLATE = '''\
def _resolve_notation_by_target(notation: str) -> str | None:
    """Antigravity target: resolve notation tree-first, then via root walk.

    Two shapes, probed in this order:

      0. ``marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``
         in a live checkout at or above THIS executor file (the NESTED shape).
         This is the FIRST leg of this function, and this function runs at
         position 3 of ``resolve_notation`` — after the embedded direct hit and
         the prefix shim. So on an Antigravity executor a live embedded path
         still wins, exactly as on Claude; only the OpenCode executor promotes
         tree code ahead of the embedded checks, via its own leg-0 probe
         outside this function.
      1. ``{bundle}-{skill}/scripts/{script}.py`` under the Antigravity skill
         discovery roots (the deployed FLAT shape). The first match is returned
         as an absolute path.

    Roots searched in order:
      1. $GEMINI_CONFIG_DIR/plugins/plan-marshall/skills/  (env-var override)
      2. .agents/skills/                                   (project-local)
      3. .agents/plugins/plan-marshall/skills/             (project-local plugin)
      4. ~/.gemini/config/plugins/plan-marshall/skills/    (user-global plugin)
      5. ~/.gemini/antigravity/skills/                     (user-global cross-compat)
      6. ~/.gemini/config/skills/                          (user-global skills)
      7. .claude/skills/                                   (project-local cross-compat)

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
        _executor_file = Path(__file__).resolve()
    except (OSError, ValueError, NameError):
        _executor_file = None
    if _executor_file is not None:
        _rel = Path('marketplace') / 'bundles' / bundle / 'skills' / skill / 'scripts' / script_file
        for _parent in [_executor_file.parent, *_executor_file.parents]:
            try:
                _candidate = _parent / _rel
                if _candidate.is_file():
                    return str(_candidate.resolve())
            except (OSError, ValueError):
                continue

    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None

    _env_config_dir = os.environ.get('GEMINI_CONFIG_DIR', '')
    roots = [
        (str(Path(_env_config_dir) / 'plugins' / 'plan-marshall' / 'skills') if _env_config_dir else ''),
        '.agents/skills',
        '.agents/plugins/plan-marshall/skills',
        str(home / '.gemini' / 'config' / 'plugins' / 'plan-marshall' / 'skills'),
        str(home / '.gemini' / 'antigravity' / 'skills'),
        str(home / '.gemini' / 'config' / 'skills'),
        '.claude/skills',
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


def generate_target_aware_resolver_code(target: str) -> str:
    """Return the Python source for the ``_resolve_notation_by_target`` function.

    The body of the generated executor's ``resolve_notation`` function calls
    ``_resolve_notation_by_target`` as a dynamic fallback when a notation is
    absent from the embedded SCRIPTS dict.  Every implementation opens with the
    NESTED ``{bundle}/skills/{skill}/scripts/{script}.py`` tree-first probe (a
    live checkout at or above the executor file), then diverges: the two flat
    targets add their own dash-namespaced deployed roots, while ``claude`` stops
    at the nested plugin cache because a Claude installation has no flat root to
    find.  The emitted resolver therefore agrees with whichever layout the
    target actually ships.  They differ only in the roots searched after the
    shared tree-first leg:

    - ``claude``:  the plugin-cache newest-version-dir walk
      (``~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py``).
    - ``antigravity``:  7-root walk using the Antigravity dash-namespaced
      directory layout (``{bundle}-{skill}/scripts/{script}.py``).
    - ``opencode``:  7-root walk using the OpenCode dash-namespaced directory
      layout (``{bundle}-{skill}/scripts/{script}.py``).

    Unknown targets fall back to the Claude resolver.

    Args:
        target: Runtime target string (e.g. ``"claude"``, ``"antigravity"``, or ``"opencode"``).

    Returns:
        Python source code string (no leading/trailing blank lines).
    """
    if target == 'opencode':
        return _OPENCODE_RESOLVER_TEMPLATE.strip()
    if target == 'antigravity':
        return _ANTIGRAVITY_RESOLVER_TEMPLATE.strip()
    # Default / unknown target → Claude resolver
    return _CLAUDE_RESOLVER_TEMPLATE.strip()


# ============================================================================
# GENERATION
# ============================================================================


def generate_mappings_code(mappings: dict[str, str]) -> str:
    """Generate Python code for script mappings dict.

    Tree-first ordering: entries whose path lives in the marketplace source
    tree (``/marketplace/bundles/``) emit before deployed-cache copies, each
    family alphabetical by notation. A single alphabetical ``sorted()`` puts a
    deployed copy ahead of the tree, so a stale cache entry shadows the live
    source in every consumer that reads the emission in order.
    """
    lines = []
    tree_items = sorted((n, p) for n, p in mappings.items() if _is_tree_script_dir(p))
    cache_items = sorted((n, p) for n, p in mappings.items() if not _is_tree_script_dir(p))
    for notation, path in tree_items + cache_items:
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
# v4: adds the CACHE_RECOVERY_ROOTS placeholder (runtime-resolved bundle cache
#     roots injected per target for the bootstrap's pruned-version self-heal).
_SUPPORTED_TEMPLATE_FORMAT_VERSION = 4

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
                    f"untouched. Remedy: run the marshall-steward upgrade flow's "
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
# COUPLED to ``test/conftest.py``'s ``_ensure_executor_present``, which
# bootstraps a missing executor by subprocessing ``generate_executor.py
# generate`` under ``timeout=300``. That timeout MUST stay strictly above this
# budget with margin, because this budget bounds accept-set derivation ALONE:
# script discovery, probe writing and the atomic write all run AFTER it is
# spent, so a bootstrap timeout at or below 180.0 kills a generation the
# generator itself still considers within budget. The two numbers are one
# decision recorded in two places — the mirror comment at that call site names
# this constant and its 180.0 value, so moving either number without the other
# leaves one of the two comments wrong.
_DEFAULT_SURFACE_BUDGET_SECONDS = 180.0


# Depth account (D2 positive account).
#
# The margin below was established by a HAND COUNT over the tree at authoring
# time — nothing here re-derives it at runtime, so a verb chain that grows
# deeper later widens no bound on its own. The deepest chain counted is four levels
# beneath the script (``manage-config plan <phase> step <get|set>`` — plan=1,
# phase=2, step=3, leaf verb=4), so the bound carries a margin of two. The
# already-closed symbol is the fail-closed depth cap in ``argparse_surface`` —
# see its own fail-closed-on-uncertainty invariant for the mechanism, which is
# deliberately not restated here. Its consequence is the one this account rests
# on: an insufficient depth leaves a verb path UNVALIDATED rather than producing
# a narrowed accept-set that would reject a real invocation. No derivation fix is
# owed; this account is the deliverable.
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
    outright. On a fresh or surface-less previous that is a SAFE configuration —
    a surface-less executor dispatches exactly as it did before the map existed
    (the fail-closed-on-uncertainty invariant). Against a previous executor that
    ALREADY carried surfaces, a zero-surface generation is the regression the
    fail-open guard in :func:`generate_executor` now refuses, so ``0`` is not
    universally safe once surfaces exist. An unparseable or negative value falls
    back to the default rather than failing the generation.
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

# The distinctive stdout prefix of the surface-stats line. A single token a
# consumer greps for, so the emission is asserted on a VALUE rather than
# inferred from a line's absence.
_SURFACE_STATS_LINE_PREFIX = 'surface-stats:'


def format_surface_stats_line(stats: dict[str, int]) -> str:
    """Render the four accept-set counts as one greppable stdout line.

    **Emission contract (normative — not a mere convenience).** This line is
    emitted UNCONDITIONALLY on every real regeneration, including the all-zero
    case, and a consumer establishes the derivation outcome by reading its
    VALUES. It must never establish that outcome by noticing the line is
    missing, because *an absence nothing consumes is not a signal*: the exact
    failure this line closes is a regeneration that derived nothing yet exited
    ``status: success``, distinguishable from a healthy one ONLY by a line that
    was not there to read. A signal that lives in an absence is no signal at
    all, so the counts are always present — at the value ``0`` when nothing was
    derived — and the fail-open guard (see :func:`generate_executor`) turns that
    zero into a loud non-zero exit rather than leaving it for a consumer to
    infer.

    Args:
        stats: The four-count surface-stats mapping (the shape of
            :data:`_EMPTY_SURFACE_STATS`).

    Returns:
        A single line, prefixed by :data:`_SURFACE_STATS_LINE_PREFIX`, naming
        every count by key so the emission carries a value per bucket.
    """
    return (
        f'{_SURFACE_STATS_LINE_PREFIX} '
        f'scripts_registered={stats["scripts_registered"]} '
        f'surfaces_derived={stats["surfaces_derived"]} '
        f'surfaces_reused={stats["surfaces_reused"]} '
        f'surfaces_not_derivable={stats["surfaces_not_derivable"]}'
    )


# Locates the ``SCRIPT_SURFACES = {`` … ``}`` literal in a previously generated
# executor so its entries can be reused by digest. Text-scanned rather than
# imported: reading the previous artifact must not execute it.
_SURFACES_BLOCK_START = 'SCRIPT_SURFACES = {'


def _dir_digest(directory: Path) -> str:
    """Digest every ``*.py`` under ``directory`` RECURSIVELY, by path and bytes.

    Recursive because the two sets involved are not the same set. The executor's
    PYTHONPATH exposes each scripts dir AND its immediate subdirectories
    (``collect_script_dirs``), so a nested module is importable; but the list
    handed to :func:`_shared_dirs_digest` is ``get_shared_module_dirs`` — five
    fixed TOP-LEVEL ``.../scripts`` dirs with no nested entry at all. A
    non-recursive walk therefore leaves every nested shared module importable
    yet INVISIBLE to the digest: editing ``script-shared/scripts/build/``'s CLI
    module changes the argparse surface of the five registered build scripts
    that import it while every digest stays put, so the generator reuses a stale
    ``SCRIPT_SURFACES`` entry and the executor can pre-spawn-reject an
    invocation that is now valid. There is no "own entry" for a nested package
    to reach the digest through.

    Each file contributes its path RELATIVE to ``directory`` (POSIX-normalised)
    rather than its bare name, so the digest is stable across checkouts that
    place the same tree at a different absolute prefix while still
    distinguishing ``build/cli.py`` from ``query/cli.py``. ``__pycache__`` is
    skipped: it is build residue, not source.
    """
    hasher = hashlib.sha256()
    if not directory.is_dir():
        return hasher.hexdigest()
    for path in sorted(directory.rglob('*.py')):
        if '__pycache__' in path.parts:
            continue
        hasher.update(path.relative_to(directory).as_posix().encode('utf-8'))
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b'<unreadable>')
    return hasher.hexdigest()


def _shared_dirs_digest(shared_dirs: list[Path]) -> str:
    """One digest over every injected shared-module directory, nested files included.

    Computed ONCE per generation and folded into every script's digest, so an
    edit to an imported shared module invalidates every dependent surface. The
    list handed in is ``get_shared_module_dirs`` — the five top-level shared
    ``scripts`` dirs, carrying NO nested entry — so nested coverage rests
    entirely on :func:`_dir_digest` walking recursively. The two functions are
    one mechanism, not two independent ones; narrowing either re-opens the
    stale-surface-on-nested-edit hole.

    This over-invalidates — a change to one shared module re-derives all scripts
    — which costs time only. Under-invalidating would cost correctness, so the
    digest is deliberately coarse.
    """
    hasher = hashlib.sha256()
    for directory in sorted(shared_dirs):
        hasher.update(directory.as_posix().encode('utf-8'))
        hasher.update(_dir_digest(directory).encode('utf-8'))
    return hasher.hexdigest()


def compute_surface_digest(script_path: str, shared_digest: str) -> str:
    """Digest the inputs that can change one script's argparse surface.

    Four contributors: the script's own bytes, every ``*.py`` under its own
    directory (its skill's other modules — the ``ci.py`` / ``ci_base.py``
    relationship, where the parser is assembled in a sibling — nested packages
    included, per :func:`_dir_digest`), the shared-module aggregate, and the
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

    Cross-directory assembly rides the same key through
    ``surface_api.extra_surface_deps``: a script whose parser is assembled in
    another skill's directory (``ci.py`` delegating to the provider
    front-ends) folds those files in here, so the carried entry is reused only
    while the delegated surface is unchanged. Without it the generator reuses
    a stale entry and the executor pre-spawn-rejects an invocation that is
    now valid — the same hole :func:`argparse_surface.content_hash` closes
    for the shared on-disk cache, via the same declaration.
    """
    path = Path(script_path)
    hasher = hashlib.sha256()
    try:
        hasher.update(path.read_bytes())
    except OSError:
        hasher.update(b'<unreadable>')
    hasher.update(_dir_digest(path.parent).encode('utf-8'))
    for rel_key, dep_path in surface_api.extra_surface_deps(path):
        hasher.update(rel_key.encode('utf-8'))
        try:
            hasher.update(dep_path.read_bytes())
        except OSError:
            hasher.update(b'<unreadable>')
    hasher.update(shared_digest.encode('utf-8'))
    hasher.update(f'surface-schema-v{surface_api.CACHE_VERSION}'.encode())
    return hasher.hexdigest()


#: Closed vocabulary for :attr:`PreviousSurfaces.outcome`.
#:
#: The partition that matters is MEASURED vs NOT MEASURED, not empty vs
#: non-empty. ``absent`` and ``no_block`` are measurements that legitimately
#: yield no surfaces; ``unreadable`` is the absence of a measurement wearing the
#: same empty mapping.
#:
#: - ``absent`` — no executor file exists (a fresh install / first build). It
#:   verifiably carried no surfaces.
#: - ``no_block`` — the file was read in full and carries no ``SCRIPT_SURFACES``
#:   block at all (an executor generated before the map existed). It too
#:   verifiably carried no surfaces.
#: - ``read`` — the block was found and parsed, and EVERY entry was well-shaped.
#:   :attr:`PreviousSurfaces.surfaces` is what it held, which is legitimately
#:   empty when the literal was ``{}``.
#: - ``unreadable`` — the file EXISTS but its surfaces could not be established:
#:   the read raised, or the block was found but its literal would not parse /
#:   did not parse to a dict / held an entry whose key is not a ``str`` or whose
#:   value is not a ``dict``. Nothing was measured, so the empty mapping is not
#:   evidence that the previous executor carried nothing.
#:
#: ⛔ A partly-understood map is ``unreadable``, not a ``read`` of the entries
#: that happened to parse. Dropping the offenders and reporting ``read`` returns
#: an empty mapping under a measured outcome, which is byte-identical to a
#: previous executor that genuinely carried none — and that is the citation the
#: fail-open guard would then accept as proof that nothing is being stripped.
PREVIOUS_SURFACE_OUTCOMES: frozenset[str] = frozenset({'absent', 'no_block', 'read', 'unreadable'})


class PreviousSurfaces(NamedTuple):
    """What the previous executor's ``SCRIPT_SURFACES`` map was found to hold.

    Replaces a bare ``dict[str, dict]`` return because that shape could not
    express the one distinction its consumer depends on. The fail-open guard
    (guard 5, :func:`generate_executor`) asks *"did the previous executor carry
    surfaces this generation is about to strip?"* — and a bare ``{}`` answered
    both "no, it verifiably carried none" and "unknown, it could not be read"
    identically. The guard read the second as the first and passed an unreadable
    previous straight through, writing a surfaces-less executor: precisely the
    fail-open it exists to refuse, reintroduced through its own input.

    Attributes:
        surfaces: The parsed notation → entry map. Empty on every outcome except
            a ``read`` that found entries.
        outcome: One of :data:`PREVIOUS_SURFACE_OUTCOMES`.
        detail: Human-readable provenance naming the file and the failure, for
            the refusal message. Empty when nothing went wrong.
    """

    surfaces: dict[str, dict]
    outcome: str
    detail: str


def read_previous_surfaces(executor: Path) -> PreviousSurfaces:
    """Read the ``SCRIPT_SURFACES`` map out of a previously generated executor.

    Text-scanned and ``ast.literal_eval``-ed rather than imported: the previous
    executor is an artifact to be read, not code to be run, and importing it
    would execute its bootstrap.

    Every return says WHICH state produced it (see
    :data:`PREVIOUS_SURFACE_OUTCOMES`), because the failure modes and the
    genuinely-empty ones are not interchangeable to the caller. For REUSE they
    are — all four yield no entry to carry over and cost a full re-derivation —
    but for the fail-open guard they are opposites: an unreadable previous
    cannot be cited as proof that no surfaces are being stripped.
    """
    if not executor.is_file():
        return PreviousSurfaces({}, 'absent', '')
    try:
        text = executor.read_text(encoding='utf-8')
    except OSError as exc:
        return PreviousSurfaces({}, 'unreadable', f'{executor} could not be read: {exc}')
    start = text.find(_SURFACES_BLOCK_START)
    if start < 0:
        return PreviousSurfaces({}, 'no_block', '')
    open_brace = start + len(_SURFACES_BLOCK_START) - 1
    end = text.find('\n}', open_brace)
    if end < 0:
        return PreviousSurfaces(
            {},
            'unreadable',
            f'{executor} carries a {_SURFACES_BLOCK_START!r} marker with no terminating brace',
        )
    literal = text[open_brace : end + 2]
    try:
        parsed = ast.literal_eval(literal)
    except (ValueError, SyntaxError) as exc:
        return PreviousSurfaces({}, 'unreadable', f'{executor} SCRIPT_SURFACES literal would not parse: {exc}')
    if not isinstance(parsed, dict):
        return PreviousSurfaces(
            {},
            'unreadable',
            f'{executor} SCRIPT_SURFACES parsed to {type(parsed).__name__}, not a dict',
        )
    # Reject the WHOLE map when any entry is wrong-shaped, rather than filtering
    # the offenders out and returning 'read'. A silent filter makes a corrupt
    # previous executor indistinguishable from one that legitimately carried no
    # surfaces — and that is exactly the citation the fail-open guard must never
    # accept: with every entry dropped, the guard reads "verifiably carried none",
    # passes, and writes an executor with no pre-spawn validation. The outcome
    # this function exists to separate is MEASURED vs NOT MEASURED, and a map it
    # could only partly understand was not measured.
    malformed = [
        repr(notation)
        for notation, entry in parsed.items()
        if not isinstance(notation, str) or not isinstance(entry, dict)
    ]
    if malformed:
        return PreviousSurfaces(
            {},
            'unreadable',
            (
                f'{executor} SCRIPT_SURFACES holds {len(malformed)} wrong-shaped '
                f'entr{"y" if len(malformed) == 1 else "ies"} '
                f'(expected str key and dict value): {", ".join(sorted(malformed))}'
            ),
        )
    return PreviousSurfaces(dict(parsed), 'read', '')


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
    regeneration that quietly derived nothing must be distinguishable from one
    that derived everything: the counts feed the fail-open guard in
    :func:`generate_executor` — which refuses a zero-surface regeneration against
    a non-empty previous rather than reporting success — and the unconditional
    surface-stats line, so the outcome is a value a consumer reads rather than a
    status the two outcomes would otherwise share.
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


def _is_tree_script_dir(path: str) -> bool:
    """Return True when ``path`` lives in the marketplace source tree.

    The tree layout carries ``/marketplace/bundles/``; deployed copies (the
    Claude versioned plugin cache, the OpenCode flat ``plan-marshall-<skill>/``
    skills dir) never do. The same marker the generated executor's
    ``PM_MARKETPLACE_ROOT`` rewrite hook already matches on.
    """
    return '/marketplace/bundles/' in path


def _sort_script_dirs_tree_first(dirs: list[str]) -> list[str]:
    """Sort script dirs with marketplace/tree roots before deployed-cache roots.

    A single alphabetical ``sorted()`` puts ``~/.config/...`` (and the Claude
    cache) ahead of ``.../git/...``, so a deployed copy of a shared module
    (e.g. ``_manifest_validation``) shadows the tree copy and its
    ``Path(__file__)``-anchored ``resolve_bundles_root`` — which only knows
    nested layouts — raises at import time. Partition instead: tree dirs
    alphabetically first, then everything else alphabetically. Deterministic
    and stable for single-family inputs (all-tree or all-cache).
    """
    tree = sorted(d for d in dirs if _is_tree_script_dir(d))
    cache = sorted(d for d in dirs if not _is_tree_script_dir(d))
    return tree + cache


def _resolve_tree_bases(base_path: Path) -> list[Path]:
    """Resolve marketplace-tree bundles roots usable as the single generation source.

    Two candidates, in priority order: ``base_path`` itself when it already
    carries a ``plan-marshall/skills`` tree (i.e. generation runs against the
    live marketplace checkout), then the shared ``marketplace`` bundles root
    (the cwd-anchored checkout the shared resolver finds). An empty list means
    no tree is resolvable — the caller retains the cache entrypoint, cache
    import paths, and cache surface dependencies together.
    """
    candidates: list[Path] = []
    try:
        if (base_path / 'plan-marshall' / 'skills').is_dir():
            candidates.append(base_path)
    except (OSError, ValueError):
        pass
    try:
        candidates.append(_shared_get_base_path('marketplace'))
    except (FileNotFoundError, ValueError):
        pass
    return candidates


def _rewrite_mappings_to_tree(mappings: dict[str, str], base_path: Path) -> dict[str, str]:
    """Rewrite discovered mappings to marketplace tree paths where they exist.

    A regen on an OpenCode machine runs with a stale deployed cache present, so
    cache-first discovery hands back cache paths for notations the live tree
    also carries. Rewriting each non-tree value to its tree equivalent (when
    that file exists) makes the emitted executor resolve every notation to
    tree code. Notations with no tree equivalent (project-local
    ``default-bundle`` entries, genuinely cache-only scripts) keep their
    discovered path. Never raises: an unresolvable tree base returns the
    input unchanged.
    """
    candidates = _resolve_tree_bases(base_path)

    if not candidates:
        return dict(mappings)

    rewritten: dict[str, str] = {}
    for notation, path in mappings.items():
        if _is_tree_script_dir(path):
            rewritten[notation] = path
            continue
        parts = notation.split(':')
        if len(parts) != 3:
            rewritten[notation] = path
            continue
        bundle, skill, script = parts
        if bundle == 'default-bundle':
            rewritten[notation] = path
            continue
        replaced = False
        for tree_base in candidates:
            candidate = tree_base / bundle / 'skills' / skill / 'scripts' / f'{script}.py'
            try:
                if candidate.is_file():
                    rewritten[notation] = candidate.resolve().as_posix()
                    replaced = True
                    break
            except (OSError, ValueError):
                continue
        if not replaced:
            rewritten[notation] = path
    return rewritten


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
    coverage: DiscoveryCoverage | None = None,
) -> dict:
    """
    Generate execute-script.py with embedded mappings.

    Five deterministic guards protect the executor, and their ORDER is load
    bearing in two different ways.

    Guard 1 runs ahead of the accept-set derivation, which costs one ``--help``
    subprocess per parser node under a wall-clock budget. A version skew refuses
    without writing anything, so spending the derivation first would burn that
    whole budget to reach a conclusion available from a string comparison. (A
    dry run returns earlier still: it derives nothing and writes nothing, so
    there is nothing for the handshake to protect.)

    Guard 5 runs immediately AFTER the derivation, on its outcome; guards 2-4
    then run before THE EXECUTOR is written, so a malformed generation can never
    overwrite a working executor. One write does precede them, and it is not the
    executor: derivation dispatches its ``--help`` probes through a throwaway
    PROBE executor — a sibling temp file carrying the content about to be written
    minus its surfaces, unlinked on every exit path — so the probes see the
    script set being generated rather than the previous one. The real executor
    is untouched until every guard has passed.

    Once the derivation outcome is known, the four accept-set counts are emitted
    as an UNCONDITIONAL surface-stats line (see :func:`format_surface_stats_line`
    for the "an absence nothing consumes is not a signal" contract) — on the
    fail-open refusal and the success return alike, carrying identical counts.

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
       layout. A content passing all guards is written to a sibling temp path
       and ``os.replace``-d onto the real executor so a partial write can never
       leave a corrupt executor in place.
    5. **Fail-open guard** — a SEMANTIC check on the derivation outcome rather
       than the content shape. When this generation emits ZERO surfaces (neither
       derived nor reused) AND EITHER the previous executor carried some OR its
       surfaces could not be established at all, it returns a ``status: error``
       dict (carrying ``surface_stats`` and ``previous_surfaces_outcome``) and
       writes nothing, leaving the still-validating previous executor in place. A
       surfaces-less executor dispatches with no pre-spawn validation, so a green
       regeneration that quietly stripped the whole set would leave the guard
       inert while every signal reads healthy. The two refusing inputs are
       distinct and BOTH are required: a previous that verifiably had no surfaces
       (a fresh install, a pre-map executor — :data:`PREVIOUS_SURFACE_OUTCOMES`
       ``absent`` / ``no_block``) is not a regression and passes through, whereas
       an ``unreadable`` previous proves nothing and must not be read as that
       same zero.

    Args:
        mappings: Script notation to path mappings
        base_path: Path to bundles directory for resolving template/logging paths
        dry_run: If True, show what would be generated without writing
        target: Platform target (e.g. ``"claude"`` or ``"opencode"``).  When
            ``None``, it is resolved from the env tier or ``marshal.json`` via
            :func:`target_context.resolve_target`.
        coverage: The discovery-coverage verdict for ``mappings``, from
            :func:`assess_discovery_coverage`.  It gates the one degradation
            below that would otherwise be emitted as a fact: a
            ``# (none detected)`` shared-module block is only honest when the
            discovery that produced the mappings is known to be complete.  A
            ``None`` verdict is treated as NOT established, so a caller that
            has not assessed coverage cannot reach the degradation.

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
    # Tree-first emission: prefer the live marketplace tree over a stale
    # deployed cache for every notation the tree carries, so a regen on an
    # OpenCode machine emits tree code even when discovery hit the cache.
    mappings = _rewrite_mappings_to_tree(mappings, base_path)
    mappings_code = generate_mappings_code(mappings)

    # Single-source-tree rule: the entrypoint rewrite above sources entrypoints
    # from the tree whenever one resolves, so the import paths (logging dir,
    # shared module dirs, collected script dirs) and the surface-dependency
    # digests (hashed from those same shared dirs downstream) must follow the
    # SAME tree together — otherwise a tree entrypoint imports older cache
    # modules. With no resolvable tree the cache entrypoint is retained above,
    # and the cache import paths below match it.
    tree_bases = _resolve_tree_bases(base_path)
    import_base = tree_bases[0] if tree_bases else base_path

    # Resolve platform target for target-aware resolver injection. The caller
    # resolves it through the shared resolver; only a direct programmatic call
    # that supplied none falls back to the cascade here, and it falls back to
    # the SAME resolver rather than to a private marshal.json reader.
    resolved_target = target if target is not None else resolve_target()['target']
    resolver_code = generate_target_aware_resolver_code(resolved_target)

    # logging module location (unified logging skill). EXISTENCE-CHECKED: the
    # generated executor imports ``plan_logging`` from this path before it can
    # log anything, so substituting a path that does not exist emits an executor
    # whose very first operation fails. Generation refuses instead.
    logging_scripts_dir = get_logging_scripts_dir(import_base)
    if not logging_scripts_dir.is_dir():
        return {
            'status': 'error',
            'error': 'logging_module_dir_missing',
            'detail': (
                f'the logging module directory {logging_scripts_dir} does not exist; the generated '
                f'executor imports plan_logging from it, so no executor can be emitted for this base'
            ),
            'logging_dir': str(logging_scripts_dir),
        }
    logging_dir = logging_scripts_dir.resolve().as_posix()

    # Shared module directories (must be on sys.path before executor-level imports).
    # Emitted as ``(skill, pinned_dir)`` pairs so the template bootstrap can self-heal a
    # GC-pruned pinned version to the newest surviving plugin-cache version dir. The skill
    # name comes from shared_module_skill_label (a flat dir's parent is ``{bundle}-{skill}``).
    shared_dirs = get_shared_module_dirs(import_base)
    if not shared_dirs and (coverage is None or not coverage['coverage_ok']):
        # ``# (none detected)`` is a claim about the world — "there are no shared
        # module dirs here" — and the shared-module discovery runs through the
        # same bundle walk the script discovery does. When the discovery
        # coverage could not be established, an empty result is indistinguishable
        # from a truncated scan, so the claim is refused rather than emitted.
        return coverage_error_payload(
            'shared_module_dirs_unresolved',
            'no shared-module directories resolved and script-discovery coverage could not be '
            'established, so "(none detected)" cannot be claimed as a fact',
            coverage if coverage is not None else _UNASSESSED_COVERAGE,
        )
    shared_module_lines = (
        '\n'.join(f"    ('{shared_module_skill_label(d)}', '{d.as_posix()}')," for d in shared_dirs)
        if shared_dirs
        else '    # (none detected)'
    )

    # Cache-recovery roots for the template's pruned-version self-heal, resolved at
    # generation time through the same runtime op the target-aware resolver family uses.
    # The executor cannot import the shared resolver before its own bootstrap is done, so
    # the recovered roots travel with the generated file. A target with no versioned cache
    # (OpenCode) contributes no root and the recovery honestly finds nothing.
    recovery_roots = _shared_get_bundle_cache_roots()
    cache_recovery_lines = (
        # repr() (not manual quotes) so a root path containing a quote cannot
        # emit invalid generated Python and trip the unsubstituted-placeholder
        # guard on regeneration.
        '\n'.join(f'    {root!r},' for root in recovery_roots) if recovery_roots else '    # (no cache roots resolved)'
    )

    # Collect ALL script directories (including subdirectories of skills like script-shared
    # that have no registered scripts but contain importable modules).
    # These are injected as extra PYTHONPATH entries so subprocess-invoked scripts can
    # import from organized subdirectory layouts (e.g., script-shared/scripts/build/).
    # Sourced from the same single tree as the entrypoints and shared dirs above.
    #
    # ``collect_script_dirs`` enumerates BOTH deployed shapes (it is a
    # ``deployed_layout`` consumer), so this list is populated against a flat
    # root as well as a nested one. That matters more here than anywhere else:
    # these are the PYTHONPATH entries the generated executor hands to every
    # subprocess it spawns, so an empty list on a flat root would ship an
    # executor that cannot import a single shared module — while the generation
    # itself reported success.
    all_script_dirs = collect_script_dirs(import_base)
    resolved_dirs = [Path(d).resolve().as_posix() for d in all_script_dirs]
    extra_dirs_code = ', '.join(f"'{d}'" for d in _sort_script_dirs_tree_first(sorted(set(resolved_dirs))))

    # Provisioning stamps: the version and script-set fingerprint the executor
    # was generated at, read from the installed dist-manifest.json (emitted by
    # the target generator). A fresh install has no manifest yet — the empty
    # sentinel is substituted, never an error, so the executor still generates.
    manifest = read_installed_manifest(base_path, target=resolved_target)
    generated_version = str(manifest.get('version', '') or '')
    mappings_fingerprint = str(manifest.get('executor_scripts_fingerprint', '') or '')

    # Template-content stamp: SHA-256 of the template file bytes. The bootstrap
    # verb compares it against the live template to detect template-content
    # staleness (a template fix shipped without a version bump). Computed over
    # the raw bytes so an encoding-only difference still counts as a change.
    template_sha256 = hashlib.sha256(executor_template.read_bytes()).hexdigest()

    def _substitute(surfaces_code: str) -> str:
        content = template.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
        content = content.replace('{{SCRIPT_SURFACES}}', surfaces_code)
        content = content.replace('{{LOGGING_DIR}}', logging_dir)
        content = content.replace('{{SHARED_MODULE_DIRS}}', shared_module_lines)
        content = content.replace('{{CACHE_RECOVERY_ROOTS}}', cache_recovery_lines)
        content = content.replace('{{EXTRA_SCRIPT_DIRS}}', extra_dirs_code)
        content = content.replace('{{PLAN_DIR_NAME}}', PLAN_DIR_NAME)
        content = content.replace('{{TARGET_AWARE_RESOLVER}}', resolver_code)
        content = content.replace('{{EXECUTOR_TARGET}}', resolved_target)
        content = content.replace('{{GENERATED_VERSION}}', generated_version)
        content = content.replace('{{MAPPINGS_FINGERPRINT}}', mappings_fingerprint)
        content = content.replace('{{TEMPLATE_SHA256}}', template_sha256)
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
                f'are the same version (run {SYNC_PLUGIN_CACHE_COMMAND}, then regenerate) before '
                f'regenerating the executor. Existing executor left untouched.'
            ),
        }

    real_executor = executor_path()

    # Read the OUTGOING surfaces once, before the probe/derivation below, and
    # keep the count: the fail-open guard downstream compares "how many surfaces
    # the last executor carried" against "how many this generation emits", and
    # the previous executor is untouched until the atomic write at the very end,
    # so this read sees the outgoing state whatever the derivation does. The
    # read reports its OUTCOME alongside the map, because the guard must be able
    # to tell a previous that verifiably carried nothing from one it could not
    # read at all.
    previous = read_previous_surfaces(real_executor)
    previous_surfaces = previous.surfaces

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
            previous_surfaces,
            shared_dirs,
        )
    except OSError as exc:
        # A probe-write failure degrades to NO surfaces rather than raising here.
        # Against a fresh/empty previous that is harmless — a surfaces-less
        # executor dispatches exactly as it did before this map existed. Against
        # a previous that already carried surfaces it is a total collapse, which
        # the fail-open guard below then turns into a loud refusal (no write, the
        # still-validating previous executor preserved) — so this degradation is
        # never the silent stale-executor it once was.
        print(f'Warning: surface derivation skipped ({exc})', file=sys.stderr)
        surfaces, surface_stats = {}, dict(_EMPTY_SURFACE_STATS)
        surface_stats['scripts_registered'] = len(mappings)
        surface_stats['surfaces_not_derivable'] = len(mappings)
    finally:
        try:
            probe_executor.unlink(missing_ok=True)
        except OSError:
            pass

    # Emit the surface-stats line UNCONDITIONALLY, at the single point where the
    # derivation outcome is known, so it appears on BOTH the fail-open refusal
    # below and the eventual success return — carrying identical counts. See
    # format_surface_stats_line for the normative "an absence nothing consumes
    # is not a signal" contract this closes.
    print(format_surface_stats_line(surface_stats))

    # Guard 5 — fail-open guard: refuse a regeneration that emits ZERO surfaces
    # (neither derived nor reused) where the previous executor carried some. A
    # surfaces-less executor dispatches without any pre-spawn validation, so a
    # green regeneration that quietly stripped the whole surface set leaves the
    # guard inert while every signal reads healthy — the exact recurrence this
    # deliverable closes. This is a SEMANTIC guard on the derivation outcome,
    # unlike the shape guards 1-4: it fails loudly (non-zero exit) and writes
    # nothing, so the previous — still-validating — executor is left in place
    # for the caller to regenerate against a working budget. A previous state
    # that itself had no surfaces (a fresh install, a first build) is not a
    # regression and passes through with an all-zero stats line.
    emitted_surface_count = surface_stats['surfaces_derived'] + surface_stats['surfaces_reused']

    # The unreadable-previous half of the same guard. An executor that EXISTS
    # but whose surfaces could not be established is not evidence that no
    # surfaces are being stripped — it is the absence of evidence either way, and
    # reading it as the fresh-install zero is how a fail-open guard fails open
    # through its own input. Refuse on the same terms as the counted case: only
    # when this generation would emit zero, since a generation that DOES emit
    # surfaces strips nothing regardless of what the previous held.
    if previous.outcome == 'unreadable' and emitted_surface_count == 0:
        return {
            'status': 'error',
            'error': (
                f'Fail-open regeneration refused: this generation emitted 0 surfaces '
                f'(neither derived nor reused) and the previous executor could not be read, '
                f'so whether it carried surfaces this write would strip is UNKNOWN '
                f'({previous.detail}). A surfaces-less executor dispatches with no pre-spawn '
                f'validation, and an unreadable previous cannot be cited as proof that none '
                f'are being lost. No executor was written and the previous one was left '
                f'untouched. Remedy: repair or remove the unreadable executor, and resolve '
                f'why this generation derived no surfaces — an exhausted '
                f'{_SURFACE_DERIVATION_BUDGET_ENV}, a broken probe, or an unreadable/failing '
                f'script set (see any warning above) — then re-run generate.'
            ),
            'surface_stats': surface_stats,
            'previous_surfaces_outcome': previous.outcome,
        }

    if previous_surfaces and emitted_surface_count == 0:
        return {
            'status': 'error',
            'error': (
                f'Fail-open regeneration refused: the previous executor carried '
                f'{len(previous_surfaces)} derived surface(s) but this generation emitted '
                f'0 (neither derived nor reused). A surfaces-less executor dispatches with '
                f'no pre-spawn validation, so writing it would silently disable the guard. '
                f'No executor was written and the previous one was left untouched. Remedy: '
                f'resolve why this generation derived no surfaces — an exhausted '
                f'{_SURFACE_DERIVATION_BUDGET_ENV}, a broken probe, or an unreadable/failing '
                f'script set (see any warning above) — then re-run generate.'
            ),
            'surface_stats': surface_stats,
            'previous_surfaces_outcome': previous.outcome,
        }

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

    # Try to import and validate using importlib.util for hyphenated filename.
    # The executor path is passed as an argv token (read via ``sys.argv[1]``),
    # NOT interpolated into the ``-c`` source — a checkout path containing a
    # quote or backslash would otherwise break the generated program.
    try:
        import_code = """
import importlib.util
import sys
spec = importlib.util.spec_from_file_location('executor', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(len(module.SCRIPTS))
"""
        result = subprocess.run(
            ['python3', '-c', import_code.strip(), str(real_executor)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f'Error validating executor: {result.stderr}', file=sys.stderr)
            return False, 0

        script_count = int(result.stdout.strip())
        print(f'Executor valid: {script_count} scripts mapped')

    except Exception as e:
        print(f'Error validating executor: {e}', file=sys.stderr)
        return False, 0

    # Verify logging module (include shared module dirs for transitive imports).
    # Every directory is passed as an argv token and inserted onto sys.path by
    # the probe, so a path containing a quote or backslash cannot corrupt the
    # ``-c`` source. argv order mirrors the previous interpolation: the shared
    # dirs first, then the logging dir last (so the logging dir lands first on
    # sys.path).
    shared_dirs = get_shared_module_dirs(base_path)
    probe = (
        'import sys\n'
        'for _p in sys.argv[1:]:\n'
        '    sys.path.insert(0, _p)\n'
        'from plan_logging import log_script_execution\n'
        "print('OK')\n"
    )
    try:
        result = subprocess.run(
            ['python3', '-c', probe, *(str(d) for d in shared_dirs), str(logging_scripts_dir)],
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
        # The executor path is passed via argv (``sys.argv[1]``), never
        # interpolated into the ``-c`` source, so a checkout path carrying a
        # quote or backslash cannot break the generated program.
        import_code = """
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location('executor', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(module.SCRIPTS))
"""
        result = subprocess.run(
            ['python3', '-c', import_code.strip(), str(real_executor)],
            capture_output=True,
            text=True,
        )
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
            for fname in ('dist-manifest.json', 'plugin.json', 'opencode.json'):
                candidates.append(repo_root / 'target' / target / fname)
        for fname in ('dist-manifest.json', 'plugin.json', 'opencode.json'):
            candidates.append(base_path / fname)
            candidates.append(base_path.parent / fname)
        # (4) Marketplace clone root: a plugin-cache install keeps the manifest
        # at ``.../plugins/marketplaces/<marketplace>/`` rather than inside the
        # cache tree, so map the ``/plugins/cache/<marketplace>`` segment to
        # ``/plugins/marketplaces/<marketplace>`` and append ``dist-manifest.json``.
        cache_marker = '/plugins/cache/'
        cache_idx = base_str.find(cache_marker)
        if cache_idx >= 0:
            prefix = base_str[:cache_idx]
            remainder = base_str[cache_idx + len(cache_marker) :]
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
                candidates.append(Path(prefix) / 'plugins' / 'marketplaces' / marketplace_name / 'dist-manifest.json')

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


def read_executor_template_sha() -> str:
    """Read the embedded ``TEMPLATE_SHA256`` from the generated executor.

    Returns the empty string when the executor is absent, unreadable, or
    carries an empty stamp (an executor generated before the stamp existed).
    The empty string is the ``unknown`` sentinel for template staleness: an
    unstampable executor can be neither fresh nor stale, so callers report
    ``template_status: unknown`` rather than a vacuous ``fresh``.
    """
    real_executor = executor_path()
    if not real_executor.is_file():
        return ''
    try:
        text = real_executor.read_text(encoding='utf-8')
    except (OSError, ValueError):
        return ''
    match = re.search(r"^TEMPLATE_SHA256\s*=\s*'([^']*)'", text, re.MULTILINE)
    if match and match.group(1):
        return match.group(1)
    return ''


def current_template_sha256() -> str:
    """SHA-256 of the live executor template bytes.

    Resolved script-relative to the executing generator (see
    :func:`get_templates_dir`), so the hash always describes the template this
    generator would substitute — never a newer cached copy. Returns the empty
    string when the template file is absent or unreadable — the same
    ``unknown`` sentinel :func:`read_executor_template_sha` uses, so the
    comparison degrades to ``unknown`` rather than to a false ``stale``.
    """
    template_file = get_templates_dir(SCRIPT_DIR) / 'execute-script.py.template'
    try:
        return hashlib.sha256(template_file.read_bytes()).hexdigest()
    except OSError:
        return ''


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
    """Generate executor with embedded script mappings.

    Fails CLOSED on an under-covered discovery. The scan below can return a
    mapping that is short of what the tree holds — empty when the scan found
    nothing, truncated when the glob fallback's narrower rules dropped scripts —
    and neither failure is visible in the returned dict. The coverage verdict
    from :func:`assess_discovery_coverage` is what makes the difference
    refusable, and it is checked before anything is written: the enumerated
    count, the discovered count, the declared exclusion rules and the missing
    notations all ride the error payload so the shortfall is diagnosable without
    re-running the scan by hand (ADR-019).
    """
    # One shared context resolution: the same ``--target`` /
    # ``--marketplace-root`` cascade every target-resolving verb runs.
    try:
        ctx = resolve_verb_context(args)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_context', 'detail': str(e)}

    resolved_target: str = ctx['target']
    marketplace_root = ctx['marketplace_root']

    # Resolve base path
    try:
        base_path = get_base_path(
            use_marketplace=args.marketplace,
            marketplace_root=marketplace_root,
            target=resolved_target,
        )
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    print(f'Target: {resolved_target} (source: {ctx["target_source"]})')

    # Discover marketplace scripts
    print('Discovering marketplace scripts...')
    try:
        mappings = discover_scripts(base_path)
    except (Exception, SystemExit) as e:
        # discover_scripts signals "inventory unavailable" via sys.exit(2) — a
        # SystemExit, which is a BaseException, NOT an Exception — so a bare
        # ``except Exception`` never reached the glob fallback for exactly the
        # failure the fallback exists to cover. Catch SystemExit alongside
        # Exception so an inventory-not-found (or inventory-scan-failure) falls
        # back to glob discovery instead of aborting the whole regeneration.
        # The fallback is NOT trusted blindly: it is handed to the same coverage
        # verdict as the scan, and its known-narrower globbing rules (``.py``
        # only, top-level only, tests dropped) will fail that verdict on a real
        # tree. That is the intended outcome — an empty and a truncated scan are
        # the same defect class, and neither may reach a written executor.
        print(f'Falling back to glob discovery: {e}', file=sys.stderr)
        mappings = discover_scripts_fallback(base_path)

    marketplace_count = len(mappings)
    print(f'Found {marketplace_count} marketplace scripts')

    # Discovery-coverage guard. The comparison is against the MARKETPLACE
    # mappings only — ``discover_local_scripts`` contributes ``default-bundle:``
    # notations from a different tree entirely and is not part of what the
    # enumeration covers.
    coverage = assess_discovery_coverage(base_path, mappings)
    if not coverage['coverage_ok']:
        return coverage_error_payload(
            'discovery_coverage_incomplete',
            f'script discovery is short of the {coverage["scripts_enumerated"]} notations the tree '
            f'holds ({coverage["scripts_discovered"]} discovered, '
            f'{len(coverage["missing_notations"])}+ missing); refusing to generate an executor from '
            f'an under-covered scan',
            coverage,
            executor_target=resolved_target,
            target_source=ctx['target_source'],
        )
    print(
        f'Discovery coverage verified: {coverage["scripts_discovered"]} of '
        f'{coverage["scripts_expected"]} enumerated notations'
    )

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
    # The generator self-checks the substituted content (format handshake,
    # placeholder-residue guard, py_compile) and writes atomically; a failed
    # self-check surfaces here as the command's status: error, preserving any
    # pre-existing working executor. The verdict rides the PAYLOAD, not the exit
    # code: ``main()`` prints the TOON and returns 0 for every expected error, as
    # the output contract requires, so a caller reads ``status`` rather than
    # branching on the exit status.
    print('Generating executor...')
    gen_result = generate_executor(
        mappings,
        base_path,
        dry_run=args.dry_run,
        target=resolved_target,
        coverage=coverage,
    )
    if gen_result.get('status') != 'success':
        # The fail-open guard's error result carries surface_stats — flatten
        # them to the top level so the counts reach the TOON output on the error
        # path exactly as they do on success. The counts are the evidence a
        # consumer asserts on: without them here, the very outcome the guard
        # exists to make loud would surface as a bare error with no numbers.
        stats = gen_result.pop('surface_stats', None)
        if stats:
            gen_result.update(stats)
        return gen_result

    # The four accept-set counts, published rather than merely computed. A
    # regeneration that quietly derived NOTHING — a broken probe, an exhausted
    # budget, a shared-module edit that invalidated everything and then failed —
    # no longer slips through as a healthy ``status: success`` when the previous
    # executor carried surfaces: the fail-open guard above turns that case into a
    # ``status: error`` (whose counts the branch above flattens), and a
    # fresh/empty previous deriving zero still succeeds with all-zero counts. On
    # every path the counts ride the result, so the outcome is read from a value
    # rather than inferred from the status. ``surfaces_not_derivable`` is the
    # residual (registered minus emitted), so the three buckets always sum to
    # ``scripts_registered``.
    surface_stats = gen_result.get('surface_stats') or dict(_EMPTY_SURFACE_STATS)

    if args.dry_run:
        print('\nDry run complete. No files written.')
        return {
            'status': 'success',
            'scripts_discovered': len(mappings),
            'executor_target': resolved_target,
            'target_source': ctx['target_source'],
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
        'target_source': ctx['target_source'],
        'logs_cleaned': logs_cleaned,
        **surface_stats,
    }

    return result


def cmd_verify(args: argparse.Namespace) -> dict:
    """Verify the existing executor against the resolved target's context.

    The verb resolves its ``{target, marketplace-root}`` context through the
    shared resolver like every other target-resolving verb, and hands the
    resolved base to :func:`verify_executor` rather than letting it
    auto-detect. Verification is not target-neutral: the logging-module import
    probe runs against the base's ``manage-logging`` directory, so a verb that
    auto-detected while ignoring ``--target`` would verify one target's layout
    and report the result as if it were the requested one's.
    """
    try:
        ctx = resolve_verb_context(args)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_context', 'detail': str(e)}

    try:
        base_path = get_base_path(
            use_marketplace=getattr(args, 'marketplace', False),
            marketplace_root=ctx['marketplace_root'],
            target=ctx['target'],
        )
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    valid, count = verify_executor(base_path)
    if valid:
        return {
            'status': 'success',
            'script_count': count,
            'target': ctx['target'],
            'target_source': ctx['target_source'],
        }
    else:
        return {'status': 'error', 'error': 'Verification failed'}


def cmd_bootstrap(args: argparse.Namespace) -> dict:
    """Sanctioned direct-path bootstrap for fresh-clone / stale-cache cases.

    This verb regenerates only when no executor exists yet to mediate it
    (fresh clone), the existing one fails verification (corrupt/stale cache),
    or its embedded template hash no longer matches the live template
    (template-content staleness — a template fix shipped without a version
    bump, e.g. the post-merge stale-executor incident). An executor that is
    present, valid, and template-fresh is refused with ``action: not_needed``
    (the caller must use the executor-mediated ``generate`` instead).

    Template comparison is four-valued: ``fresh`` (hashes match),
    ``stale`` (both hashes known and differ), ``unknown`` (either side
    unstampable — a pre-stamp executor or an unreadable template), and
    ``uncompared`` (no hash comparison was attempted — the executor was
    absent, or it failed structural verification — while the live template
    hash was resolvable). None of ``unknown``/``uncompared`` drives a
    regeneration on its own; both ride the verdict the presence check or
    the verification half already reached.
    """
    live_sha = current_template_sha256()
    real_executor = executor_path()

    def _regenerate(reason: str, template_status: str, **extra: object) -> dict:
        """Run the single generation path every regeneration reason shares."""
        regen = cmd_generate(args)
        if regen.get('status') != 'success':
            return {
                'status': 'error',
                'error': f'bootstrap failed: {regen.get("error", "unknown error")}',
                'action': 'failed',
                'reason': reason,
                'template_status': template_status,
            }
        return {
            'status': 'success',
            'action': 'generated',
            'reason': reason,
            'template_status': template_status,
            'target': regen.get('executor_target', ''),
            'target_source': regen.get('target_source', ''),
            **extra,
        }

    if not real_executor.is_file():
        return _regenerate(
            'executor_absent',
            'unknown' if not live_sha else 'uncompared',
            executor=str(real_executor),
        )
    valid, script_count = verify_executor()
    if not valid:
        return _regenerate(
            'executor_invalid',
            'unknown' if not live_sha else 'uncompared',
            script_count=script_count,
        )
    embedded_sha = read_executor_template_sha()
    if not live_sha or not embedded_sha:
        return {
            'status': 'success',
            'action': 'not_needed',
            'reason': 'executor_fresh',
            'template_status': 'unknown',
            'warning': (
                'template staleness could not be determined '
                '(executor predates the TEMPLATE_SHA256 stamp or the live '
                'template is unreadable); verified-valid executor left untouched'
            ),
        }
    if embedded_sha != live_sha:
        return _regenerate('template_stale', 'stale')
    return {
        'status': 'success',
        'action': 'not_needed',
        'reason': 'executor_fresh',
        'template_status': 'fresh',
    }


def _flip_notation_separators(segment: str) -> str:
    """Return ``segment`` with hyphens and underscores swapped.

    ``manage_status`` ↔ ``manage-status``. Used to detect the
    rename-without-sweep signature: a notation referenced by callers whose
    third segment differs from the registered (filename-derived) form only
    in hyphen/underscore separators.
    """
    return ''.join('_' if ch == '-' else '-' if ch == '_' else ch for ch in segment)


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
    """Compare executor mappings with the current bundles state.

    THREE outcomes, never two:

    1. **A comparison** — the scan succeeded and its coverage against an
       independent enumeration of the tree is complete, so ``added`` /
       ``removed`` / ``changed`` are facts.
    2. **A resolver failure** — ``discover_scripts`` raised, or the coverage
       verdict fails. The verb returns ``status: error`` naming the failure and
       the coverage it COULD establish. It never substitutes an empty mapping:
       ``removed = executor_set - set()`` would report every executor mapping as
       removed, under ``status: success``, for a condition that says nothing at
       all about what was removed. That laundering is the defect this verb's
       third outcome exists to close.
    3. **A genuinely empty current set** — the scan succeeded AND the
       enumeration found nothing either. Only this may yield an empty current
       set, and it carries the enumerated-versus-discovered counts precisely so
       it is distinguishable from a truncated scan by a reader who did not watch
       the scan run.
    """
    executor_mappings = get_executor_mappings()

    if not executor_mappings:
        return {'status': 'error', 'error': 'Could not read executor mappings'}

    try:
        ctx = resolve_verb_context(args)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_context', 'detail': str(e)}
    resolved_target: str = ctx['target']

    # Resolve base path
    try:
        base_path = get_base_path(
            use_marketplace=args.marketplace,
            marketplace_root=ctx['marketplace_root'],
            target=resolved_target,
        )
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    # Outcome 2a — the scan itself failed. Report the failure and whatever
    # coverage the independent enumeration can still establish, so the reader
    # can tell "I could not look" from "I looked and found nothing".
    try:
        current_mappings = discover_scripts(base_path)
    except (Exception, SystemExit) as e:
        print(f'Error: could not read bundles state: {e}', file=sys.stderr)
        return coverage_error_payload(
            'bundles_state_unresolvable',
            f'script discovery failed ({type(e).__name__}: {e}); no removal verdict can be '
            f'substantiated, and an empty current set is NOT substituted for one',
            assess_discovery_coverage(base_path, {}),
            executor_scripts=len(executor_mappings),
            executor_target=resolved_target,
            target_source=ctx['target_source'],
        )

    coverage = assess_discovery_coverage(base_path, current_mappings)

    # Outcome 2b — the scan returned, but it is short of the tree. Same verdict:
    # an error, not a removal list.
    if not coverage['coverage_ok']:
        return coverage_error_payload(
            'bundles_state_under_covered',
            f'script discovery returned {coverage["scripts_discovered"]} of '
            f'{coverage["scripts_enumerated"]} enumerated notations; a truncated scan cannot '
            f'substantiate a removal list',
            coverage,
            executor_scripts=len(executor_mappings),
            executor_target=resolved_target,
            target_source=ctx['target_source'],
        )

    # Outcome 1 or 3 — the scan succeeded with established coverage. An empty
    # current set here is a measurement, and the counts below are what make it
    # readable as one.
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
        # The coverage counts ride every successful verdict, not only the
        # empty-set one: a reader seeing ``bundles_scripts: 0`` needs the
        # enumerated count beside it to know that zero is a measurement of an
        # empty tree rather than the residue of a scan that found nothing it
        # could not report.
        'scripts_enumerated': coverage['scripts_enumerated'],
        'scripts_discovered': coverage['scripts_discovered'],
        'target': resolved_target,
        'target_source': ctx['target_source'],
    }


def cmd_paths(args: argparse.Namespace) -> dict:
    """Verify every path the executor maps actually exists.

    The verb resolves its ``{target, marketplace-root}`` context through the
    shared resolver like every other target-resolving verb, so a caller can
    compare this verdict against another verb's on the same machine and get the
    same answer. The check itself is over the executor's EMBEDDED mappings, so
    the target does not change WHAT is inspected — resolving it is what stops
    ``paths`` from being the one verb whose "current" means something else.
    """
    try:
        ctx = resolve_verb_context(args)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_context', 'detail': str(e)}

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
        'target': ctx['target'],
        'target_source': ctx['target_source'],
    }


def cmd_cleanup(args: argparse.Namespace) -> dict:
    """Clean up old global logs."""
    deleted = cleanup_old_logs(max_age_days=args.max_age_days)
    return {'status': 'success', 'deleted': deleted}


def cmd_preflight(args: argparse.Namespace) -> dict:
    """Deterministic executor / config staleness check.

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

    Multiple plugin-cache version dirs no longer trigger a preflight
    regeneration or any marker write: the executor resolves bundle script paths
    at run time (``_resolve_notation_by_target`` and the shared
    ``select_live_version_dir`` both pick the numerically-newest version dir), so
    a stale version dir left on disk can never shadow the current scripts and
    there is nothing for the preflight to contain. Pruning the superseded dirs is
    the ``marshall-steward`` ``cache_retention sweep``'s union-keep job.

    A fresh install with no manifest resolves ``installed_version`` to the
    ``unknown`` sentinel, so the verb fails closed and reports
    ``marshal_status: unknown`` with a warning rather than a vacuous ``fresh``.

    Returns:
        A single nine-field TOON dict: ``status``, ``executor_action``
        (``fresh`` | ``regenerated``), ``marshal_status`` (``fresh`` | ``stale``
        | ``unknown``), ``installed_version``, ``executor_version``,
        ``marshal_version``, ``warning`` (the fail-closed message when
        ``marshal_status`` is ``unknown``, else the empty string), and the
        ``target`` / ``target_source`` pair the verb resolved.
    """
    try:
        ctx = resolve_verb_context(args)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_context', 'detail': str(e)}
    resolved_target: str = ctx['target']

    try:
        base_path: Path | None = get_base_path(
            use_marketplace=getattr(args, 'marketplace', False),
            marketplace_root=ctx['marketplace_root'],
            target=resolved_target,
        )
    except FileNotFoundError:
        base_path = None

    # The target is resolved through the SAME shared resolver cmd_generate uses,
    # so a stale-executor regeneration and the manifest lookup below both look
    # at the SAME target's published dist-manifest.json rather than one of them
    # defaulting to claude.

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
        'target': resolved_target,
        'target_source': ctx['target_source'],
    }


# ============================================================================
# MAIN
# ============================================================================

#: The target accept-set, ONE list shared by every target-resolving verb. It is
#: a module constant rather than a literal repeated per ``add_argument`` so a
#: new target is added in one place: a verb whose list lagged the others would
#: reject a target its siblings accept, which is exactly the "this verb
#: disagrees with that one" failure the shared resolver exists to remove.
TARGET_CHOICES = ['claude', 'opencode', 'antigravity']

#: The ``--target`` help text, likewise shared verbatim by all six verbs. Three
#: different texts for the same flag on three verbs meant ``--help`` was a
#: per-verb answer to "what does --target do here", and the answers disagreed
#: about whether the value came from ``marshal.json`` or from the environment
#: cascade. It now says one thing, and the thing is true of all six.
TARGET_FLAG_HELP = (
    'Platform target this verb operates under (claude, opencode, or antigravity). '
    'Overrides the value the shared resolver would otherwise derive from the '
    'platform environment signals and .plan/marshal.json; when omitted, all six '
    'verbs resolve the same target on the same machine.'
)


def add_target_argument(parser: argparse.ArgumentParser) -> None:
    """Register the shared ``--target`` flag on a verb's subparser.

    Every target-resolving verb calls this, so the flag's name, its accept-set
    and its help text are identical on all six by construction rather than by
    six copies agreeing. The entity-noun-first spelling is deliberate and
    propagated verbatim: ``--target`` names the entity, and no ``--platform`` /
    ``--target-name`` / ``--target-dir`` variant is introduced alongside it.
    """
    parser.add_argument(
        '--target',
        default=None,
        choices=TARGET_CHOICES,
        metavar='TARGET',
        help=TARGET_FLAG_HELP,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the module's argparse parser (extracted so tests can parse
    production argv without dispatching a verb)."""
    parser = argparse.ArgumentParser(
        description='Generate execute-script.py with embedded script mappings',
        epilog=(
            'By default uses plugin-cache context. Use --marketplace for development. '
            'Use --marketplace-root PATH (or set PM_MARKETPLACE_ROOT) to pin marketplace '
            'discovery to an explicit anchor when running from a worktree or alternate '
            'checkout. The flag takes precedence over the env var. In the default '
            'cache-first context the env var outranks the plugin cache only when no '
            '--target was given and no target was resolved from the environment signals '
            'or .plan/marshal.json; marketplace discovery itself (--marketplace, or no '
            'cache present) still consults it ahead of the working directory.'
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
            'Overrides PM_MARKETPLACE_ROOT and cwd-based discovery.'
        ),
    )
    add_target_argument(gen_parser)
    gen_parser.set_defaults(func=cmd_generate)

    # verify subcommand
    verify_parser = subparsers.add_parser('verify', help='Verify existing executor', allow_abbrev=False)
    add_target_argument(verify_parser)
    verify_parser.set_defaults(func=cmd_verify)

    # bootstrap subcommand — a sanctioned direct-path entry point (fresh clone /
    # corrupt executor / stale template). Refuses a fresh executor.
    bootstrap_parser = subparsers.add_parser(
        'bootstrap',
        help='Sanctioned direct-path bootstrap: generate only when the executor is absent, invalid, or template-stale',
        allow_abbrev=False,
    )
    bootstrap_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    bootstrap_parser.add_argument(
        '--marketplace-root',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Explicit marketplace anchor directory (must contain marketplace/bundles). '
            'Overrides PM_MARKETPLACE_ROOT and cwd-based discovery.'
        ),
    )
    add_target_argument(bootstrap_parser)
    # cmd_generate dereferences args.dry_run directly, so the bootstrap
    # namespace must carry it — mirroring the preflight precedent below.
    # Without this default every bootstrap run that reaches regeneration
    # (absent, invalid, or template-stale executor) raises AttributeError
    # instead of generating.
    bootstrap_parser.set_defaults(func=cmd_bootstrap, dry_run=False)

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
            'Overrides PM_MARKETPLACE_ROOT and cwd-based discovery.'
        ),
    )
    add_target_argument(drift_parser)
    drift_parser.set_defaults(func=cmd_drift)

    # paths subcommand
    paths_parser = subparsers.add_parser('paths', help='Verify all mapped paths exist', allow_abbrev=False)
    add_target_argument(paths_parser)
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
            'Overrides PM_MARKETPLACE_ROOT and cwd-based discovery.'
        ),
    )
    add_target_argument(preflight_parser)
    preflight_parser.set_defaults(func=cmd_preflight, dry_run=False)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = args.func(args)

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    from file_ops import safe_main

    safe_main(main)()
