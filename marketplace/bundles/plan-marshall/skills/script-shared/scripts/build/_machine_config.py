#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Machine-global build configuration (the build-slot cap's single home).

This module is the single reader/writer of the machine-global
``machine-config.json`` under ``~/.plan-marshall/marshalld/`` — the same
``marshalld/`` state directory that holds ``registry.json``, whose module
(:mod:`_build_server_registry`) this one deliberately mirrors in shape. It sits
in the home-root tier's reserved marshalld slot (ADR-008), so it introduces no
new tier member class.

It exists because the build-slot cap has exactly two consumers that must agree:
the marshalld scheduler (:mod:`_marshalld_scheduler`, constructed by
:mod:`marshalld`) and the in-process fallback admission
(``manage-locks/scripts/build_queue.py``). Both admit against the ONE
machine-global ``build-queue.json``, so a cap resolved per caller from that
caller's own repository config is a cap two callers can disagree on while
contending for the same slots. Resolving it here — from one machine-global file,
through one function — is what makes the budget single-valued host-wide.

**Cwd independence is the point, not a side effect.** The previous resolvers read
``build.queue.max_slots`` from the cwd-relative ``marshal.json``. ``marshalld``
double-forks and ``chdir('/')``, so its walk-up found no repository at all and
the cap silently degraded to the default — indistinguishable from a deliberately
configured 5. :func:`resolve_max_slots` consults neither the cwd nor any
repository, so that degradation path is gone; ADR-002 is satisfied by moving the
daemon off the cwd-relative resolver rather than re-ordering around it.

**Every resolution states its source.** :func:`resolve_max_slots` returns a
:class:`CapResolution`, never a bare int, so a caller can always tell a
configured value from a fallback: an unreadable or invalid file falls back to
:data:`DEFAULT_MAX_SLOTS` but is reported as ``unreadable`` / ``invalid``, never
as ``machine_config`` or ``default``. The function never raises — cap resolution
sits on the admission path of every build, so it degrades rather than failing a
build.

Config layout (``machine-config.json``)::

    {
      "version": 1,
      "build": {
        "queue": {
          "max_slots": 5
        }
      }
    }

The key path mirrors ``marshal.json``'s ``build.queue.max_slots`` exactly, so a
message about the cap names an identical path whichever file it came from.

**Concurrency correctness.** Writes go through
:func:`file_ops.atomic_write_file` (temp file + ``os.replace``), so a concurrent
reader observes either the old or the new file and never a torn one. The read
path takes no lock: it is a single atomic-replace-consistent read, performed
OUTSIDE the build queue's ``rmw_json`` critical section exactly where the
previous per-caller resolver ran, so it opens no new check-then-act window
against the queue. See the TOCTOU / check-then-act menu in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.

Usage:
    from _machine_config import (
        CapResolution, DEFAULT_MAX_SLOTS, machine_config_path,
        resolve_max_slots, write_max_slots,
    )

    resolution = resolve_max_slots()
    scheduler = Scheduler(max_slots=resolution.value)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from file_ops import atomic_write_file
from marketplace_paths import ensure_home_root, home_root

# =============================================================================
# Constants and path resolution
# =============================================================================

MACHINE_CONFIG_VERSION = 1
"""Schema version stamped into a freshly-written machine config."""

DEFAULT_MAX_SLOTS = 5
"""The single default build-slot cap (the machine-CPU concurrency bound).

This is the ONE definition of the default, imported by every consumer rather
than copied into each. A per-consumer copy is what lets two admission paths
drift apart on what "unconfigured" means while they contend for the same slots,
so the cap default is defined here and nowhere else.
"""

_MACHINE_CONFIG_SUBDIR = 'marshalld'
_MACHINE_CONFIG_FILENAME = 'machine-config.json'

_DIR_MODE = 0o700
"""State-directory mode — owner-only (machine-global state is not world-listable)."""

_FILE_MODE = 0o600
"""Config file mode — owner read/write only."""

SOURCE_MACHINE_CONFIG = 'machine_config'
"""The cap was read from the machine-global config as a valid positive int."""

SOURCE_DEFAULT = 'default'
"""No cap is configured — the file or the key is absent."""

SOURCE_INVALID = 'invalid'
"""The key is present but holds a value that cannot be a cap."""

SOURCE_UNREADABLE = 'unreadable'
"""The file exists but could not be read, parsed, or is not a JSON object."""


def machine_config_dir() -> Path:
    """Return the marshalld state directory under the machine-global home root."""
    return home_root() / _MACHINE_CONFIG_SUBDIR


def machine_config_path() -> Path:
    """Return the path to the machine-global ``machine-config.json``."""
    return machine_config_dir() / _MACHINE_CONFIG_FILENAME


def ensure_machine_config_dir() -> Path:
    """Create the marshalld state directory ``0o700`` and return it.

    Routes the home-root creation through :func:`marketplace_paths.ensure_home_root`
    (which creates ``~/.plan-marshall`` ``0o700`` and repairs a wider mode), then
    creates the ``marshalld`` subdirectory ``0o700``. Both steps are idempotent
    and repair an existing directory whose mode is wider than ``0o700``.

    Returns:
        The resolved marshalld state directory path.
    """
    ensure_home_root()
    directory = machine_config_dir()
    directory.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    if (directory.stat().st_mode & 0o777) != _DIR_MODE:
        os.chmod(directory, _DIR_MODE)
    return directory


# =============================================================================
# Cap resolution
# =============================================================================


@dataclass(frozen=True)
class CapResolution:
    """One resolution of the machine-global build-slot cap.

    Attributes:
        value: The cap to admit against — always a positive int, because every
            non-``machine_config`` source falls back to
            :data:`DEFAULT_MAX_SLOTS`.
        source: Where ``value`` came from: :data:`SOURCE_MACHINE_CONFIG`,
            :data:`SOURCE_DEFAULT`, :data:`SOURCE_INVALID`, or
            :data:`SOURCE_UNREADABLE`. A caller that needs to know whether the
            cap was actually configured reads THIS, never ``value`` alone — the
            fallback value is byte-identical to a configured 5.
        path: The machine-global config path the resolution consulted, reported
            whether or not the file exists so a message can name where the cap
            would be set.
        detail: Why a non-nominal source was reached — the offending value for
            :data:`SOURCE_INVALID`, the underlying error for
            :data:`SOURCE_UNREADABLE`. ``None`` for
            :data:`SOURCE_MACHINE_CONFIG` and :data:`SOURCE_DEFAULT`, which
            need no explanation.
    """

    value: int
    source: str
    path: str
    detail: str | None = None


def _read_machine_config(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read and parse the machine config, distinguishing absent from unreadable.

    :func:`file_ops.read_json` is deliberately NOT used here: it collapses "the
    file is not there" and "the file is there and broken" into one default
    return, and telling those two apart is this module's whole contract — an
    unreadable file must never be reported as ``default``.

    Args:
        path: The machine-global config path.

    Returns:
        ``(payload, None)`` when the file parsed to a JSON object;
        ``(None, None)`` when the file does not exist; ``(None, detail)`` when
        the file exists but could not be read, could not be parsed, or did not
        hold a JSON object, where ``detail`` names the reason.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f'cannot read {path}: {exc}'
    try:
        payload = json.loads(text)
    except ValueError as exc:
        return None, f'cannot parse {path}: {exc}'
    if not isinstance(payload, dict):
        return None, f'{path} does not hold a JSON object (found {type(payload).__name__})'
    return payload, None


def resolve_max_slots() -> CapResolution:
    """Resolve the machine-global build-slot cap, naming its source.

    Consults ONLY the machine-global ``machine-config.json`` — never the cwd,
    never a repository's ``marshal.json`` — so the result is identical for every
    caller on the host and is unaffected by a process having moved its working
    directory (the daemon's post-``double_fork`` ``chdir('/')``).

    The source partition is total, and each non-nominal member keeps its own
    identity rather than collapsing into the default:

    * :data:`SOURCE_MACHINE_CONFIG` — ``build.queue.max_slots`` holds a positive
      ``int``. A ``bool`` is rejected here even though it is an ``int``
      subclass, so ``true`` never resolves to a cap of 1.
    * :data:`SOURCE_DEFAULT` — the file is absent, or the key is not present in
      it. Nothing is configured, which is a legitimate state.
    * :data:`SOURCE_INVALID` — the key IS present but holds a non-``int``, a
      ``bool``, or a non-positive ``int``. The value cannot be a cap, so
      :data:`DEFAULT_MAX_SLOTS` is admitted against instead and ``detail``
      names the offending value.
    * :data:`SOURCE_UNREADABLE` — the file exists but could not be read, could
      not be parsed, or does not hold a JSON object. A cap may well be
      configured in it and simply be unreachable, so this is reported as its own
      state and ``detail`` names the error.

    Never raises: cap resolution sits on the admission path of every build, so
    an unexpected filesystem or decoding failure degrades to a reported fallback
    rather than failing the build.

    Returns:
        The :class:`CapResolution` for this host. ``value`` is always positive.
    """
    try:
        path = machine_config_path()
    except Exception as exc:  # home-root resolution is the only raise site left
        return CapResolution(
            value=DEFAULT_MAX_SLOTS,
            source=SOURCE_UNREADABLE,
            path='',
            detail=f'cannot resolve the machine-global config path: {exc}',
        )

    path_str = str(path)
    payload, unreadable_detail = _read_machine_config(path)
    if unreadable_detail is not None:
        return CapResolution(
            value=DEFAULT_MAX_SLOTS,
            source=SOURCE_UNREADABLE,
            path=path_str,
            detail=unreadable_detail,
        )
    if payload is None:
        return CapResolution(value=DEFAULT_MAX_SLOTS, source=SOURCE_DEFAULT, path=path_str)

    # A non-dict `build` or `queue` block puts the key out of reach, which is
    # the same observable state as the key being absent: nothing is configured.
    build = payload.get('build')
    if not isinstance(build, dict):
        return CapResolution(value=DEFAULT_MAX_SLOTS, source=SOURCE_DEFAULT, path=path_str)
    queue = build.get('queue')
    if not isinstance(queue, dict):
        return CapResolution(value=DEFAULT_MAX_SLOTS, source=SOURCE_DEFAULT, path=path_str)
    if 'max_slots' not in queue:
        return CapResolution(value=DEFAULT_MAX_SLOTS, source=SOURCE_DEFAULT, path=path_str)

    raw = queue.get('max_slots')
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return CapResolution(
            value=DEFAULT_MAX_SLOTS,
            source=SOURCE_INVALID,
            path=path_str,
            detail=f'build.queue.max_slots is not a positive integer: {raw!r}',
        )
    return CapResolution(value=raw, source=SOURCE_MACHINE_CONFIG, path=path_str)


# =============================================================================
# Cap write
# =============================================================================


def write_max_slots(value: int) -> CapResolution:
    """Persist ``build.queue.max_slots`` machine-wide, preserving sibling keys.

    The existing file is read first and rewritten with only the cap replaced, so
    any other key it carries survives the write. An existing file that cannot be
    read or parsed is REPLACED rather than merged into — there is no readable
    prior state to preserve, and refusing here would leave a corrupt file
    unfixable through the only verb that writes this file.

    The write is atomic (temp file + ``os.replace`` via
    :func:`file_ops.atomic_write_file`), so a concurrent reader sees the old or
    the new file and never a partial one. Concurrent writers are
    last-writer-wins, each write individually atomic.

    Args:
        value: The cap to store — a positive ``int``. A ``bool`` is rejected
            even though it is an ``int`` subclass.

    Returns:
        The :class:`CapResolution` describing the stored state, re-resolved from
        disk so the caller reports what was actually persisted rather than what
        it intended to persist.

    Raises:
        ValueError: when ``value`` is not a positive, non-``bool`` ``int``.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f'max_slots must be a positive integer, got {value!r}')

    ensure_machine_config_dir()
    path = machine_config_path()
    payload, _unreadable_detail = _read_machine_config(path)
    if payload is None:
        payload = {}

    payload['version'] = MACHINE_CONFIG_VERSION
    build = payload.get('build')
    if not isinstance(build, dict):
        build = {}
        payload['build'] = build
    queue = build.get('queue')
    if not isinstance(queue, dict):
        queue = {}
        build['queue'] = queue
    queue['max_slots'] = value

    atomic_write_file(path, json.dumps(payload, indent=2))
    if (path.stat().st_mode & 0o777) != _FILE_MODE:
        os.chmod(path, _FILE_MODE)
    return resolve_max_slots()
