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

**A surviving per-repo key never takes effect, and says so.**
:func:`read_per_repo_max_slots` reads a repository's demoted
``build.queue.max_slots`` for the sole purpose of REPORTING it, never of
resolving a cap from it. :func:`per_repo_max_slots_warning` renders that report:
the per-repo path and value, the machine-global value/source/path actually in
effect, and the one-step fix. The two are deliberately separate from
:func:`resolve_max_slots`, which never consults a repository at all — the cap and
the report about a stale key are different questions, and fusing them is how a
per-repo value creeps back into the admitted budget.

**Concurrency correctness.** Writes go through
:func:`file_ops.atomic_write_file` (temp file + ``os.replace``), so a concurrent
reader observes either the old or the new file and never a torn one. Both
writers — :func:`write_max_slots` and :func:`write_max_slots_if_unset` —
additionally serialize on ONE ``O_EXCL`` guard file
(``machine-config.json.lock``, with the stale-guard reclaim ``_locks_core`` uses),
because :func:`write_max_slots_if_unset` is a check-then-act: its "is the cap
unset?" test and its write must not be separable, or two repositories migrating
concurrently would both observe ``default``, both write, and one would report a
successful migration whose value had already been overwritten. The guarded
re-resolve inside :func:`write_max_slots_if_unset` is what closes that window.
Deliberately NOT routed through :func:`_locks_core.rmw_json`: its read treats a
missing OR CORRUPT file as ``{}``, which would let a conditional write overwrite
an unreadable file a caller must refuse on — the very distinction this module
exists to preserve. Concurrent :func:`write_max_slots` calls remain
last-writer-wins, each write individually atomic.

The read path takes no lock: it is a single atomic-replace-consistent read,
performed OUTSIDE the build queue's ``rmw_json`` critical section exactly where
the previous per-caller resolver ran, so it opens no new check-then-act window
against the queue. See the TOCTOU / check-then-act menu in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.

Usage:
    from _machine_config import (
        CapResolution, DEFAULT_MAX_SLOTS, MachineConfigPostCommitError,
        machine_config_path, per_repo_max_slots_warning,
        read_per_repo_max_slots, resolve_max_slots, write_max_slots,
        write_max_slots_if_unset,
    )

    resolution = resolve_max_slots()
    scheduler = Scheduler(max_slots=resolution.value)
"""

from __future__ import annotations

import errno
import json
import os
import re
import time
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

# Guard-file spin parameters for the write serialization, mirroring
# `_locks_core`'s idiom (a fixed small backoff over a bounded budget, with a
# stale guard reclaimed so a crashed writer cannot wedge the file permanently).
# The values are deliberately the same magnitudes: a cap write is an equally
# short critical section, and two coordination guards on one host that time out
# differently is a difference with no reason behind it.
_GUARD_BACKOFF_SECONDS = 0.01
_GUARD_TIMEOUT_SECONDS = 30.0
_GUARD_STALE_SECONDS = 60.0
_GUARD_SUFFIX = '.lock'

WARNING_PER_REPO_MAX_SLOTS_NOT_IN_EFFECT = 'per_repo_max_slots_not_in_effect'
"""Warning ``code`` for a surviving per-repo ``build.queue.max_slots`` key.

The code — not the message text — is what consumers deduplicate on, so it is a
named constant rather than a literal repeated at each emission site.
"""

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


def machine_config_guard_path() -> Path:
    """Return the write-serialization guard path beside the machine config.

    ONE guard for BOTH writers (:func:`write_max_slots` and
    :func:`write_max_slots_if_unset`), because they contend for the same file and
    a guard each would serialize neither against the other.
    """
    path = machine_config_path()
    return path.with_name(f'{path.name}{_GUARD_SUFFIX}')


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
# Per-repo demotion (report only — never a cap source)
# =============================================================================

MIGRATE_COMMAND = 'python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server config migrate'
"""The one-step fix the not-in-effect warning names. A single definition, because
a command an operator is told to run must be copy-pasteable and identical
wherever it is quoted."""

_SET_COMMAND = (
    'python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server config set --max-slots N'
)


_CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1f\x7f]')
"""C0 control characters plus DEL — the bytes that break a single-line envelope.

Mirrors ``plan_logging._CONTROL_CHAR_PATTERN``: one character class, so the log
sink and the TOON sink strip the same set rather than each drawing its own line.
"""


def report_safe(value: Any) -> Any:
    """Render a foreign-sourced value safe to EMIT as a single-line TOON field.

    Every value this module and its consumers report about a *foreign* config —
    a repository's demoted ``build.queue.max_slots``, and a machine-global
    ``build-queue.json`` entry written by a DIFFERENT checkout — is read raw so
    the report can echo back what is actually written there. Raw is right for the
    read and wrong for the emission: ``serialize_toon`` quotes a string
    containing a newline but escapes nothing inside the quotes, so the value's
    second and later lines land in the document at column zero, where
    ``parse_toon`` reads them as SIBLING KEYS of the envelope. A value whose
    second line reads ``status: success`` does not merely get lost — it
    OVERWRITES the envelope's own ``status``, which is how a ``config migrate``
    refusal (``status: error``, both files untouched) can be reparsed as a
    completed migration, and a ``blocked`` admission as an ``admitted`` one.

    Stripping the control characters at the emission boundary is the containment
    move, not a validation one: the value is still reported, and nothing about it
    is coerced into a different type or silently accepted as a cap. A caller that
    must VALIDATE the value (``config migrate``, which copies it machine-wide)
    still does so against the raw read — this function is for the report only.

    Only a ``str`` needs it. Every other JSON type either cannot carry a control
    character (``int`` / ``float`` / ``bool`` / ``None``) or reaches
    ``_serialize_value``'s ``json.dumps`` path, which escapes one.

    Args:
        value: A value about to be placed in a reported TOON field.

    Returns:
        ``value`` unchanged for every non-``str`` type; the control-character-free
        string otherwise.
    """
    if isinstance(value, str):
        return _CONTROL_CHAR_PATTERN.sub('', value)
    return value


def read_per_repo_max_slots(marshal_path: str | Path) -> Any:
    """Return a repository's raw ``build.queue.max_slots``, or ``None`` if absent.

    This reader exists to REPORT a demoted key, never to resolve a cap from it —
    :func:`resolve_max_slots` consults no repository at all. It therefore returns
    the value **raw and unvalidated**: a caller reporting "your marshal.json sets
    this and it does nothing" must echo back what is actually written there,
    including a value that could never have been a valid cap. Validation belongs
    to whichever caller would COPY the value (see
    :func:`write_max_slots_if_unset`'s callers), not to the act of reading it.

    Raw means the value is foreign text until an emitter makes it safe. A caller
    that places it in a reported TOON field MUST route it through
    :func:`report_safe` first — a repository config is a file this process did
    not write, and an unescaped newline in it rewrites the envelope reporting it.
    A caller that VALIDATES the value (rather than reporting it) uses the raw
    read, which is why the sanitiser is not applied here.

    Args:
        marshal_path: The repository's ``marshal.json`` path — supplied by the
            caller (typically ``file_ops.get_marshal_path()``, the cwd-relative
            resolver, which is the correct resolver here precisely because the
            question IS about the caller's own repository).

    Returns:
        The raw value at ``build.queue.max_slots``, or ``None`` when the file is
        absent, unreadable, unparseable, not a JSON object, or simply does not
        carry the key. All of those collapse deliberately: there is no key to
        report, and a build's admission path is the wrong place to raise about a
        repository config it only wanted to describe.
    """
    try:
        text = Path(marshal_path).read_text(encoding='utf-8')
    except OSError:
        return None
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    build = payload.get('build')
    if not isinstance(build, dict):
        return None
    queue = build.get('queue')
    if not isinstance(queue, dict):
        return None
    return queue.get('max_slots')


def per_repo_max_slots_warning(
    marshal_path: str | Path,
    per_repo_value: Any,
    cap: CapResolution,
) -> dict[str, str]:
    """Build the ``per_repo_max_slots_not_in_effect`` warning for a demoted key.

    The message states all three things an operator needs in order to act
    without going to look anything up: what their repository says, what is
    ACTUALLY in effect (value, source and path — the source included because the
    cap value alone cannot distinguish a configured 5 from a fallback 5), and the
    exact commands that resolve it. A warning that named only "this key does
    nothing" would leave the operator to discover the machine-global home and its
    verbs on their own.

    The ``!r`` on ``per_repo_value`` is load-bearing and not a formatting
    preference: the value is foreign text from a repository config this process
    did not write, and ``repr`` escapes the control characters that would
    otherwise let it inject lines into the TOON envelope and the stderr stream
    this message is emitted on. Do not "simplify" it to a bare ``{}`` — see
    :func:`report_safe` for the sink this closes.

    Args:
        marshal_path: The repository config carrying the demoted key.
        per_repo_value: The raw value read by :func:`read_per_repo_max_slots`.
        cap: The machine-global resolution actually in effect.

    Returns:
        ``{'code': ..., 'message': ...}`` — ``code`` is
        :data:`WARNING_PER_REPO_MAX_SLOTS_NOT_IN_EFFECT`, the stable identity
        consumers deduplicate on.
    """
    return {
        'code': WARNING_PER_REPO_MAX_SLOTS_NOT_IN_EFFECT,
        'message': (
            f'{marshal_path} sets build.queue.max_slots={per_repo_value!r}, which is NOT in effect: '
            f'the build-slot cap is machine-global. The cap in effect is {cap.value} '
            f'(source={cap.source}, path={cap.path}). '
            f'To move this repository onto the machine-global cap in one step, run: {MIGRATE_COMMAND} — '
            f'or set the machine-global value yourself with `{_SET_COMMAND}` '
            f'and then delete build.queue.max_slots from {marshal_path}.'
        ),
    }


# =============================================================================
# Cap write
# =============================================================================


def _acquire_guard(guard_path: Path) -> int:
    """Acquire the ``O_EXCL`` write guard, returning the open fd.

    Mirrors :func:`_locks_core._acquire_guard` rather than importing it: that
    module belongs to ``manage-locks``, which sits ABOVE this one in the
    dependency order (``build_queue.py`` imports ``_machine_config``, so the
    reverse import would be a cycle through a layering inversion).

    Spins with a fixed small backoff until the guard is free or the budget
    elapses. A guard older than :data:`_GUARD_STALE_SECONDS` is reclaimed (a
    crashed writer left it behind) and the create is re-attempted; if a third
    process won the race in between, the create loses cleanly (``EEXIST``) and
    the spin continues.

    Raises:
        TimeoutError: when the guard cannot be acquired within the budget.
    """
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _GUARD_TIMEOUT_SECONDS
    while True:
        try:
            return os.open(str(guard_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        # The guard is held — reclaim it if stale, else spin.
        try:
            age = time.time() - guard_path.stat().st_mtime
        except OSError:
            age = 0.0
        if age > _GUARD_STALE_SECONDS:
            try:
                os.unlink(str(guard_path))
            except OSError:
                pass  # Someone else already reclaimed it — fall through to retry.
            continue
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f'could not acquire machine-config write guard {guard_path} within {_GUARD_TIMEOUT_SECONDS}s'
            )
        time.sleep(_GUARD_BACKOFF_SECONDS)


def _release_guard(fd: int, guard_path: Path) -> None:
    """Close and remove the write guard (always from a ``finally``)."""
    os.close(fd)
    try:
        os.unlink(str(guard_path))
    except OSError:
        pass


class MachineConfigPostCommitError(OSError):
    """The atomic replace COMMITTED; the post-commit housekeeping then failed.

    This type IS the commit evidence, and it is the only thing that carries it.
    A caller cannot infer whether the write landed from a plain ``OSError``: the
    write guard is released in :func:`write_max_slots_if_unset`'s ``finally``
    BEFORE the exception reaches the caller's ``except`` arm, so by the time the
    caller re-reads the machine side, another writer may have installed the same
    value — a concurrent ``config migrate``, or the ``config set --max-slots``
    that :func:`per_repo_max_slots_warning` itself prescribes. An equal
    post-state is therefore NOT proof of authorship, and a caller that reported
    one as proof claimed a commit it had never made.

    Only :func:`_write_cap_unguarded`'s post-replace housekeeping raises this,
    and only AFTER :func:`file_ops.atomic_write_file` returned — so its presence
    is positive, writer-provided evidence that the new cap is on disk. Every
    failure point ahead of the replace (the state-dir ``mkdir``, the ``O_EXCL``
    guard, the temp-file write inside ``atomic_write_file``) raises a plain
    ``OSError``/``TimeoutError``, which carries no such claim. Do NOT widen the
    wrapped region: a marker raised from a pre-replace point would assert a
    commit that never happened, which is the same untrue signal in the other
    direction.

    It subclasses ``OSError`` so an existing ``except OSError`` arm keeps
    catching it unchanged; a caller that needs the commit evidence tests for
    THIS type ahead of the generic arm.
    """


def _write_cap_unguarded(value: int) -> None:
    """Persist ``value`` to the machine config. Caller MUST hold the write guard.

    Split out so both writers share one payload-merge-and-commit path while the
    guard is acquired by each of them at its own scope — the conditional writer
    needs its re-resolve INSIDE the guard, which an all-in-one writer could not
    express.

    The existing file is read first and rewritten with only the cap replaced, so
    any other key it carries survives. An existing file that cannot be read or
    parsed is REPLACED rather than merged into — there is no readable prior state
    to preserve, and refusing here would leave a corrupt file unfixable through
    the only verb that writes it.

    Raises:
        MachineConfigPostCommitError: when the housekeeping AFTER the atomic
            replace fails. The cap is already on disk at that point, so the
            failure is re-raised under the marker type rather than as a bare
            ``OSError`` a caller could not tell apart from a pre-replace one.
    """
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
    # Everything below this line runs AFTER the atomic replace committed, so the
    # new cap is already on disk and a failure here is a DIFFERENT failure from
    # one raised above it. The two calls are wrapped — and nothing before
    # `atomic_write_file` is — so the marker type is raised if and only if the
    # write landed.
    try:
        if (path.stat().st_mode & 0o777) != _FILE_MODE:
            os.chmod(path, _FILE_MODE)
    except OSError as exc:
        raise MachineConfigPostCommitError(
            f'build.queue.max_slots={value} was COMMITTED to {path}, but the post-commit '
            f'housekeeping then failed: {exc}'
        ) from exc


def _validate_cap(value: int) -> None:
    """Reject anything that cannot be a cap, ``bool`` included.

    Raises:
        ValueError: when ``value`` is not a positive, non-``bool`` ``int``.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f'max_slots must be a positive integer, got {value!r}')


def write_max_slots_if_unset(value: int) -> tuple[CapResolution, bool]:
    """Write the cap machine-wide ONLY when nothing is configured there yet.

    This is the migration writer, and its whole value is that it does NOT
    overwrite. The "is it unset?" test therefore runs INSIDE the write guard,
    immediately before the write, against a fresh :func:`resolve_max_slots` — so
    a machine-global value committed by a concurrent ``config set`` / ``config
    migrate`` after the caller's own earlier resolve is observed here and
    preserved. A caller that tested outside the guard and wrote inside it would
    report a successful migration whose value had already been replaced, and
    would then delete its repository's key on the strength of that stale
    "unset" — the exact silent data loss this function exists to prevent.

    "Unset" means *only* :data:`SOURCE_DEFAULT` (the file or the key is absent).
    :data:`SOURCE_INVALID` and :data:`SOURCE_UNREADABLE` are NOT unset: the file
    exists and holds something. Writing over them would destroy a cap that may
    well be configured and merely unreachable, so both leave the file
    byte-identical and are reported back for the caller to refuse on. This is why
    the re-resolve goes through :func:`resolve_max_slots` and not through a
    missing-or-corrupt-reads-as-``{}`` helper, which would collapse exactly the
    three states that must stay distinct.

    Args:
        value: The cap to store — a positive ``int`` (``bool`` rejected).

    Returns:
        ``(resolution, wrote)`` where ``resolution`` is the POST-state read from
        disk — what is actually in effect now, whether or not this call is what
        put it there — and ``wrote`` says whether this call performed the write.
        Both are needed: ``wrote`` alone cannot tell a caller what the surviving
        value is, and the resolution alone cannot tell it whose value that is.

    Raises:
        ValueError: when ``value`` is not a positive, non-``bool`` ``int``.
        TimeoutError: when the write guard cannot be acquired.
        MachineConfigPostCommitError: when the write COMMITTED and its
            post-commit housekeeping then failed. It propagates unchanged — the
            guard ``finally`` below only releases and never swallows — because
            this type is the caller's only evidence that the cap landed. The
            guard is gone by the time the caller sees it, so a caller that
            re-read the machine side instead would be reading a state any other
            writer may have reached first.
    """
    _validate_cap(value)

    ensure_machine_config_dir()
    guard_path = machine_config_guard_path()
    fd = _acquire_guard(guard_path)
    try:
        existing = resolve_max_slots()
        if existing.source != SOURCE_DEFAULT:
            return existing, False
        _write_cap_unguarded(value)
        return resolve_max_slots(), True
    finally:
        _release_guard(fd, guard_path)


def write_max_slots(value: int) -> CapResolution:
    """Persist ``build.queue.max_slots`` machine-wide, preserving sibling keys.

    This is the UNCONDITIONAL writer — the operator's ``config set``, which is
    meant to replace whatever is there, including an invalid or unreadable value
    (it is the only verb that can repair one). Its conditional sibling
    :func:`write_max_slots_if_unset` is the migration writer that refuses to
    overwrite.

    The existing file is read first and rewritten with only the cap replaced, so
    any other key it carries survives the write. An existing file that cannot be
    read or parsed is REPLACED rather than merged into — there is no readable
    prior state to preserve, and refusing here would leave a corrupt file
    unfixable through the only verb that writes this file.

    The write is atomic (temp file + ``os.replace`` via
    :func:`file_ops.atomic_write_file`), so a concurrent reader sees the old or
    the new file and never a partial one. It takes the SAME write guard as
    :func:`write_max_slots_if_unset`, so it cannot land between that function's
    guarded re-resolve and its write; two concurrent ``config set`` calls remain
    last-writer-wins, which is the intended semantics for an unconditional set.

    Args:
        value: The cap to store — a positive ``int``. A ``bool`` is rejected
            even though it is an ``int`` subclass.

    Returns:
        The :class:`CapResolution` describing the stored state, re-resolved from
        disk so the caller reports what was actually persisted rather than what
        it intended to persist.

    Raises:
        ValueError: when ``value`` is not a positive, non-``bool`` ``int``.
        TimeoutError: when the write guard cannot be acquired.
        MachineConfigPostCommitError: when the write COMMITTED and its
            post-commit housekeeping then failed.
    """
    _validate_cap(value)

    ensure_machine_config_dir()
    guard_path = machine_config_guard_path()
    fd = _acquire_guard(guard_path)
    try:
        _write_cap_unguarded(value)
        return resolve_max_slots()
    finally:
        _release_guard(fd, guard_path)
