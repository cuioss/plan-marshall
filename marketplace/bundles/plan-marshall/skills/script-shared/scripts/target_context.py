# SPDX-License-Identifier: FSL-1.1-ALv2
"""
The single target/context resolver for every marketplace verb.

Before this module there were two independent readers of "which target is
active", and they disagreed:

* ``generate_executor.read_marshal_target`` read ``.plan/marshal.json`` only,
  and returned the literal ``'claude'`` for an absent file, an unreadable file,
  a malformed file and a missing ``runtime.target`` key alike — four distinct
  conditions collapsed into one indistinguishable answer.
* ``marketplace_paths._read_runtime_target`` implemented a wider cascade
  (env → config → default) but answered its own parse failures with the very
  default its no-``runtime.target`` and no-``marshal.json`` paths returned.

On a repository whose ``marshal.json`` carries no ``runtime.target``, both
readers answer ``claude`` on a machine whose only deployment is OpenCode, so
the generated executor embeds the Claude resolver and the flat ``skills/`` tree
is never consulted. This module is the one implementation both of them now
delegate to, so the answer and the *reason* for the answer are produced once.

Two exports carry the contract:

``resolve_target()``
    The target plus the cascade tier that produced it — ``env`` |
    ``marshal_json`` | ``fallback``. The tier is what makes a fallback
    distinguishable from a genuine ``env``-tier resolution of the same string
    (ADR-015: an absent identity is a stated sentinel, never an assumed one).
    When the tier is ``fallback``, ``reason`` names WHICH absence it was
    (``marshal_json_absent`` / ``marshal_json_unreadable`` /
    ``marshal_json_malformed`` / ``runtime_target_absent``), so four
    previously indistinguishable conditions stay distinguishable here rather
    than being re-collapsed downstream.

``resolve_context()``
    The ``{target, marketplace_root}`` pair the executor verbs share, plus the
    ``target_source`` that produced the target. The caller-supplied
    ``marketplace_root`` is validated HERE, at the shared resolver, rather than
    at each of the six entry points that route one through it — four of them
    register a ``--marketplace-root`` flag, and the other two reach the pair
    through the same ``None``-defaulted attribute (ADR-016: containment of a
    caller-supplied identifier belongs at the shared resolver, not at each entry
    point).

``marketplace_paths`` re-exports ``PLAN_DIR_NAME`` from here and delegates its
own ``_read_runtime_target`` / ``detect_target_from_env`` /
``_default_runtime_target`` to this module, so ``PLAN_DIR_NAME`` keeps its
single definition while the import direction stays acyclic (this module imports
nothing from ``marketplace_paths``; its one lazy import of
``platform_runtime`` is deferred inside the function, exactly as
``marketplace_paths`` already deferred it).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final, TypedDict

# The plan-dir segment name. THE single definition in the foundation: the
# ``marshal.json`` walk below composes it, and ``marketplace_paths`` re-exports
# it for the readers that already import it from there.
PLAN_DIR_NAME: Final[str] = os.environ.get('PLAN_DIR_NAME', '.plan')

# The environment variable carrying an explicit marketplace anchor. Named here
# because the resolver that reads it is here; ``PM_MARKETPLACE_ROOT`` is a
# LAST-RESORT override (see :func:`resolve_marketplace_root`) and never an
# input to the target cascade.
MARKETPLACE_ROOT_ENV: Final[str] = 'PM_MARKETPLACE_ROOT'

# ---------------------------------------------------------------------------
# Cascade tier identifiers — the values ``target_source`` can carry.
# ---------------------------------------------------------------------------

#: A platform-injected environment variable named the target.
SOURCE_ENV: Final[str] = 'env'
#: ``runtime.target`` in the nearest ``marshal.json`` named the target.
SOURCE_MARSHAL_JSON: Final[str] = 'marshal_json'
#: No tier produced a target; :func:`default_target` supplied the sentinel.
SOURCE_FALLBACK: Final[str] = 'fallback'
#: The CALLER named the target explicitly (an ``--target`` flag). Only
#: :func:`resolve_context` can report this: :func:`resolve_target` takes no
#: explicit target, so it can never reach the tier that bypasses the cascade.
SOURCE_EXPLICIT: Final[str] = 'explicit'

#: Every tier :func:`resolve_target` can report, in cascade order.
TARGET_SOURCES: Final[tuple[str, ...]] = (SOURCE_ENV, SOURCE_MARSHAL_JSON, SOURCE_FALLBACK)

#: The ``reason`` values a ``fallback``-tier resolution can carry. Each names a
#: DISTINCT condition that the pre-resolver code collapsed into one answer.
REASON_MARSHAL_ABSENT: Final[str] = 'marshal_json_absent'
REASON_MARSHAL_UNREADABLE: Final[str] = 'marshal_json_unreadable'
REASON_MARSHAL_MALFORMED: Final[str] = 'marshal_json_malformed'
REASON_RUNTIME_TARGET_ABSENT: Final[str] = 'runtime_target_absent'

#: Fallback identifier used when the ``platform_runtime`` registry cannot be
#: imported (a bootstrap-path call site where only the pure-stdlib foundation
#: is on ``sys.path``). Derived lazily from ``platform_runtime._DEFAULT_TARGET``
#: whenever the registry IS reachable, so the two modules resolve the same
#: default from one source and a silent divergence is structurally impossible.
_DEFAULT_TARGET_SENTINEL: Final[str] = 'claude'


class ResolvedTarget(TypedDict):
    """The resolved runtime target plus the tier and reason that produced it.

    ``reason`` is ``''`` for every non-``fallback`` tier — there is nothing to
    explain about a tier that actually found a target — and one of the
    ``REASON_*`` values when the cascade fell through.
    """

    target: str
    target_source: str
    reason: str


class TargetContext(ResolvedTarget):
    """The ``{target, marketplace-root}`` pair the executor verbs share.

    ``marketplace_root`` is the validated anchor, or ``None`` when the caller
    supplied none and no last-resort env anchor applies — which is the signal
    the consumers read to fall through to cwd walk-up discovery.
    """

    marketplace_root: Path | None


def default_target() -> str:
    """Return the registry's default target identifier.

    Reads ``platform_runtime._DEFAULT_TARGET`` so the fallback follows the
    target registration block rather than repeating its choice of default, and
    returns the ``'claude'`` sentinel when the registry cannot be imported (a
    bootstrap-path call site, where only the pure-stdlib foundation is on
    ``sys.path``). The import is deferred for that reason AND to keep this
    module importable from ``marketplace_paths`` without a cycle.
    """
    try:
        from platform_runtime import _DEFAULT_TARGET as _target
    except (ImportError, ModuleNotFoundError):
        return _DEFAULT_TARGET_SENTINEL
    return _target


def detect_target_from_env() -> str | None:
    """Detect the runtime target from platform-injected environment variables.

    The single implementation of the platform-env target contract, and the
    first tier of :func:`resolve_target`. Antigravity injects
    ``ANTIGRAVITY_AGENT=1`` into every subprocess; OpenCode injects
    ``OPENCODE=1`` (or ``OPENCODE_PID``); Claude Code injects
    ``CLAUDE_CODE_SESSION_ID``. These ambient signals resolve the target before
    any config or filesystem probe, eliminating the chicken-and-egg problem on
    first run.

    ``marketplace_paths.detect_target_from_env`` delegates here and
    ``marketplace_paths._detect_target_from_env`` delegates to that, so the
    documented back-compatible entry points survive with one implementation
    behind them.

    Returns:
        Target string (``'antigravity'``, ``'opencode'`` or ``'claude'``), or
        ``None`` when no platform env signal is present.
    """
    if os.environ.get('ANTIGRAVITY_AGENT'):
        return 'antigravity'
    if os.environ.get('OPENCODE') or os.environ.get('OPENCODE_PID'):
        return 'opencode'
    if os.environ.get('CLAUDE_CODE_SESSION_ID'):
        return 'claude'
    return None


def find_marshal_json(cwd: Path | None = None) -> Path | None:
    """Return the nearest ``.plan/marshal.json`` at or above ``cwd``, else ``None``.

    The locate half of the ``marshal.json`` tier, split out so the walk is
    written once and the read half can report WHY a resolution fell through.

    Args:
        cwd: Directory to start the upward walk from. Defaults to
            ``Path.cwd()``.
    """
    start = cwd if cwd is not None else Path.cwd()
    try:
        resolved = start.resolve()
    except OSError:
        resolved = start
    for parent in (resolved, *resolved.parents):
        candidate = parent / PLAN_DIR_NAME / 'marshal.json'
        if candidate.is_file():
            return candidate
    return None


def _read_marshal_runtime_target(candidate: Path) -> tuple[str | None, str]:
    """Return ``(target, reason)`` read from the ``marshal.json`` at ``candidate``.

    ``target`` is ``None`` — with a non-empty ``reason`` — for each of the four
    distinct conditions that used to collapse into the same answer: the file
    vanished between the locate and the read (``marshal_json_absent``), it could
    not be read (``marshal_json_unreadable``), it is not JSON or not an object
    (``marshal_json_malformed``), or it carries no usable ``runtime.target``
    (``runtime_target_absent``).
    """
    try:
        raw = candidate.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None, REASON_MARSHAL_ABSENT
    except (OSError, UnicodeDecodeError):
        return None, REASON_MARSHAL_UNREADABLE

    try:
        data = json.loads(raw)
    except ValueError:
        return None, REASON_MARSHAL_MALFORMED

    if not isinstance(data, dict):
        return None, REASON_MARSHAL_MALFORMED

    runtime = data.get('runtime')
    if isinstance(runtime, dict):
        target = runtime.get('target')
        if isinstance(target, str) and target:
            return target, ''

    return None, REASON_RUNTIME_TARGET_ABSENT


def resolve_target(cwd: Path | None = None) -> ResolvedTarget:
    """Resolve the active runtime target and the cascade tier that produced it.

    The cascade, in order:

    1. **Env** — ``ANTIGRAVITY_AGENT`` → ``'antigravity'``, ``OPENCODE`` /
       ``OPENCODE_PID`` → ``'opencode'``, ``CLAUDE_CODE_SESSION_ID`` →
       ``'claude'`` (``target_source: env``).
    2. **marshal.json** — ``runtime.target`` from the nearest
       ``<ancestor>/.plan/marshal.json`` (``target_source: marshal_json``).
    3. **Fallback** — :func:`default_target` (``target_source: fallback``),
       with ``reason`` naming which of the four fall-through conditions it was.

    Args:
        cwd: Directory the ``marshal.json`` walk starts from. Defaults to
            ``Path.cwd()``. The env tier ignores it — the env signal is
            ambient, so there is nothing to anchor.

    Returns:
        A :class:`ResolvedTarget` — ``target`` is never empty, and
        ``target_source`` is never a value the caller had to assume.
    """
    env_target = detect_target_from_env()
    if env_target:
        return {'target': env_target, 'target_source': SOURCE_ENV, 'reason': ''}

    candidate = find_marshal_json(cwd)
    if candidate is not None:
        target, reason = _read_marshal_runtime_target(candidate)
        if target:
            return {'target': target, 'target_source': SOURCE_MARSHAL_JSON, 'reason': ''}
        return {'target': default_target(), 'target_source': SOURCE_FALLBACK, 'reason': reason}

    return {'target': default_target(), 'target_source': SOURCE_FALLBACK, 'reason': REASON_MARSHAL_ABSENT}


def resolve_marketplace_root(marketplace_root: str | Path | None) -> Path | None:
    """Validate and normalise a marketplace anchor, or return ``None``.

    Containment lives here (ADR-016): the executor verbs that register a
    ``--marketplace-root`` each would otherwise have to re-decide what a
    usable anchor is, and the four copies would eventually disagree about it.
    The two verbs without the flag have nothing to re-decide and pass a
    validated ``None`` through.

    The boundary is the anchor's own well-formedness, not a sandbox the anchor
    must sit inside. An operator legitimately pins an absolute checkout
    anywhere on the machine (``/Users/x/alt-checkout``), so "must be under the
    repo" would refuse a correct input; what must never be accepted is an input
    that does not name a directory or that walks out of the directory it names.
    A supplied value is therefore refused when it is not a path at all, when it
    is empty or whitespace, when it carries a NUL byte, when any segment is a
    ``..`` traversal, or when it names the filesystem root rather than a
    directory under it. The same traversal rejection
    ``marketplace_paths.main_anchored_store_owns_bundle`` applies to a
    caller-supplied bundle name, for the same reason. ``.`` is a valid anchor
    and is left valid: it names the working directory.

    Existence is deliberately NOT required. The anchor may name a checkout that
    has not been created yet, and the consumer that joins
    ``marketplace/bundles`` onto it already raises a diagnosable
    ``FileNotFoundError``; refusing here too would duplicate that message in a
    second place.

    Args:
        marketplace_root: The caller's explicit anchor, or ``None`` to consult
            the last-resort ``PM_MARKETPLACE_ROOT`` env anchor.

    Returns:
        The normalised path, or ``None`` when neither an explicit value nor the
        env anchor applies.

    Raises:
        ValueError: when a supplied value is not a well-formed, non-traversing
            directory path.
    """
    if marketplace_root is None:
        env_root = os.environ.get(MARKETPLACE_ROOT_ENV)
        if not env_root:
            return None
        marketplace_root = env_root

    if not isinstance(marketplace_root, (str, Path)):
        raise ValueError(f'marketplace_root must be a path, got {type(marketplace_root).__name__}')

    text = str(marketplace_root)
    if not text.strip():
        raise ValueError('marketplace_root must be a non-empty path')
    if '\x00' in text:
        raise ValueError('marketplace_root must not contain a NUL byte')

    path = Path(text).expanduser()
    if '..' in path.parts:
        raise ValueError(f'marketplace_root must not contain a ".." traversal segment, got {text!r}')
    # ``path.parts`` is empty for a bare ``.`` (a valid anchor naming the
    # working directory) and holds only the root marker for ``/``. Only the
    # latter names no directory under itself.
    if path.parts and all(part in ('/', '//') for part in path.parts):
        raise ValueError(f'marketplace_root must name a directory, not a filesystem root, got {text!r}')
    return path


def resolve_context(
    target: str | None = None,
    marketplace_root: str | Path | None = None,
    cwd: Path | None = None,
) -> TargetContext:
    """Resolve the ``{target, marketplace-root}`` pair a verb operates under.

    The one entry point every target-resolving verb routes through
    (``generate``, ``verify``, ``bootstrap``, ``drift``, ``preflight``,
    ``paths``), so all six reach the same conclusion on the same machine with
    no environment override required.

    Args:
        target: An explicitly named target (a ``--target`` flag). When given it
            outranks the whole cascade and the result carries
            ``target_source: 'explicit'``.
        marketplace_root: An explicit anchor, validated by
            :func:`resolve_marketplace_root`. When ``None``, the
            ``PM_MARKETPLACE_ROOT`` env anchor applies ONLY as a last resort:
            when the target itself fell through to the ``fallback`` tier. A
            declared target (``explicit``, ``env`` or ``marshal_json``) is a
            declared context, so the env var is NOT folded into the returned
            anchor and cannot re-anchor the verb — the same rule
            ``marketplace_paths._env_anchor_is_last_resort`` applies to a direct
            ``get_base_path`` call. Folding it in unconditionally turned the env
            var into an explicit anchor that outranked every declared target.
        cwd: Directory the ``marshal.json`` walk starts from; forwarded to
            :func:`resolve_target` and ignored when ``target`` is explicit.

    Returns:
        A :class:`TargetContext`.

    Raises:
        ValueError: when ``target`` is an empty or whitespace-only string, or
            when ``marketplace_root`` is not a contained, usable path. Both are
            caller-input refusals and belong to the caller to surface.
    """
    if target is not None:
        if not target.strip():
            raise ValueError('target must be a non-empty target name')
        resolved: ResolvedTarget = {'target': target, 'target_source': SOURCE_EXPLICIT, 'reason': ''}
    else:
        resolved = resolve_target(cwd=cwd)

    if marketplace_root is None and resolved['target_source'] != SOURCE_FALLBACK:
        # A declared target outranks the last-resort env anchor: return no
        # anchor rather than promoting PM_MARKETPLACE_ROOT to an explicit one.
        anchor = None
    else:
        anchor = resolve_marketplace_root(marketplace_root)

    return {
        'target': resolved['target'],
        'target_source': resolved['target_source'],
        'reason': resolved['reason'],
        'marketplace_root': anchor,
    }
