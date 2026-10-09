# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared fixture builders for the ``cleanup restart-check`` test modules.

Every restart-check module arranges the same scaffolded fixture epic under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree — and
reads the verb through the same loaded orchestrator module, so the builders
live here once.

Two seams are doubled, and both for the same reason: a verdict that depends on
the developer's machine is not a test result.

- The ``worktree`` signal observes the real repository through the module's
  single git seam, so a test that needs a determinate worktree verdict
  substitutes :func:`_git_stub` for it.
- The ``registry_parity`` signal reads the plugin registry, the executor and
  the cache at the locations ``plugin_registry`` states.
  :func:`install_parity_stores` builds those three stores under a fixture tree
  and redirects the three location functions to it, so no test reads the
  operator's own registry or cache.
"""

import argparse
import copy
import json
from pathlib import Path
from typing import Any, NamedTuple

import plugin_registry
from _ledger_fixtures import write_ledger

from conftest import get_script_path, load_script_module, parse_ns

#: The orchestrator script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script')

_inbox = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, '_orchestrator_inbox.py', 'orchestrator_inbox_for_restart_check')

cmd_cleanup_restart_check = _orch.cmd_cleanup_restart_check
READINESS_ORDER = _orch.READINESS_ORDER
READY = _orch.READY
NOT_READY = _orch.NOT_READY
INDETERMINATE = _orch.READINESS_INDETERMINATE
INBOX_SUBDIR = _orch.INBOX_SUBDIR

SLUG = 'fixture-restart-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
CLEAN_SHA = '1234567890abcdef1234567890abcdef12345678'

#: Every signal the verb reports. All of them are scored and take part in the floor.
OWNED_SIGNALS = ('phase', 'running_plans', 'corpus_reconciliation', 'inbox', 'worktree', 'registry_parity')

#: The version the default parity stores agree on, with one older and one newer
#: neighbour. ``OLDER_VERSION`` sorts before it numerically and after it
#: lexically, so a lexical comparison would read the pair the wrong way round.
PARITY_VERSION = '0.1.1069'
OLDER_VERSION = '0.1.999'
NEWER_VERSION = '0.1.1070'
PARITY_BUNDLE = 'plan-marshall'


# =============================================================================
# Parser-derived argument namespaces
# =============================================================================
#
# The ``cleanup restart-check`` namespace is built by the orchestrator's OWN
# parser, so it carries every default the production CLI applies — including the
# ``command`` / ``cleanup_action`` discriminators the hand-built namespace never
# had. ``parse_ns`` re-executes the script module on every call, so it is hoisted
# to module scope and the two rejection cases derive their slug through
# :func:`_variant` instead of parsing again. ``register=False`` so it cannot
# displace the explicitly-named registration above.


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_RESTART_CHECK_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'cleanup',
    'restart-check',
    '--slug',
    SLUG,
    register=False,
)


# =============================================================================
# Epic fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, status: str = 'shipped') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _status_doc(rows: list, phase: str = 'orchestrating') -> dict:
    return {
        'kind': 'orchestrator',
        'title': 'Fixture Restart Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }


def _write_status(plan_context, rows: list, phase: str = 'orchestrating') -> Path:
    """Seed a per-concern kind=orchestrator ledger into the isolated store; return its root."""
    root = _epic_dir(plan_context)
    write_ledger(root, _status_doc(rows, phase))
    return root


def _write_spec(plan_context, name: str) -> Path:
    """Write one readable staged spec so the corpus has a real population."""
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Fixture spec\n\n## Claim Labels\n\n- OBSERVED: a claim\n', encoding='utf-8')
    return path


def _write_broken_spec(plan_context, name: str) -> Path:
    """Write a spec whose bytes are not decodable — an UNREADABLE observation."""
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xff\xfe not valid utf-8 \xff')
    return path


def _make_inbox(plan_context, queued: int = 0, archived: int = 0) -> Path:
    """Materialize a PRESENT inbox/ carrying ``queued`` and ``archived`` messages.

    Message names follow the channel's own ``{sender}-{NNN}.md`` grammar, so the
    counts the verb derives come from real messages rather than from stray files
    the counter would ignore. Queued messages are valid live envelopes, so they
    read as drainable work rather than as invalid rows.
    """
    inbox: Path = _epic_dir(plan_context) / INBOX_SUBDIR
    inbox.mkdir(parents=True, exist_ok=True)
    for index in range(queued):
        text = _inbox.compose_envelope(
            sender_type='plan',
            sender_id='fixture-plan',
            epic=SLUG,
            kind='landing',
            payload_body='queued\n',
        )
        (inbox / f'fixture-plan-{index + 1:03d}.md').write_text(text, encoding='utf-8')
    if archived:
        archive = inbox / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        for index in range(archived):
            (archive / f'fixture-plan-{index + 900:03d}.md').write_text('done\n', encoding='utf-8')
    return inbox


def _make_finished_inbox(plan_context) -> Path:
    """Materialize an inbox holding only a valid stream-end marker.

    The marker is valid and closed, with no live and no invalid row, so the
    drainable reading reports the FINISHED zero.
    """
    inbox: Path = _epic_dir(plan_context) / INBOX_SUBDIR
    inbox.mkdir(parents=True, exist_ok=True)
    text = _inbox.compose_envelope(
        sender_type='plan',
        sender_id='fixture-plan',
        epic=SLUG,
        kind='finding',
        payload_body='closed\n',
        lifecycle=_inbox.LIFECYCLE_STREAM_END,
    )
    (inbox / 'fixture-plan-001.md').write_text(text, encoding='utf-8')
    return inbox


def _make_blocked_inbox(plan_context, malformed: int = 2) -> Path:
    """Materialize an inbox holding only malformed messages.

    Each file matches the channel's ``{sender}-{NNN}.md`` grammar but carries
    no valid envelope, so every row is invalid with no live row — the BLOCKED
    zero the drain declines.
    """
    inbox: Path = _epic_dir(plan_context) / INBOX_SUBDIR
    inbox.mkdir(parents=True, exist_ok=True)
    for index in range(malformed):
        (inbox / f'fixture-plan-{index + 1:03d}.md').write_text('queued\n', encoding='utf-8')
    return inbox


def _git_stub(head: str = CLEAN_SHA, porcelain: str = '', unreadable: str | None = None):
    """Build a double for the module's single git seam.

    The seam takes a read-only OPERATION NAME, not argv — the operation-to-argv
    table in the module is the sole authority for what git is asked to do — so
    the double is keyed on the same names and is checked against the module's
    live table by ``test_the_stub_covers_every_declared_read_operation``.

    ``unreadable`` names the operation that must report as UNOBSERVABLE
    (``(None, reason)``), which is how the worktree signal's indeterminate arm is
    reached without depending on the host repository's state.
    """

    def _read(operation: str) -> tuple:
        if unreadable is not None and operation == unreadable:
            return None, f'git {operation} exited 128'
        if operation == 'head-sha':
            return head, ''
        return porcelain, ''

    return _read


def _ready_epic(plan_context, monkeypatch) -> None:
    """Materialize an epic on which EVERY signal read from the epic tree is ``ready``.

    This is the baseline every degraded control mutates exactly one signal away
    from, so each control isolates the signal it names. The ``registry_parity``
    signal is ``ready`` through :func:`install_parity_stores`, which each module
    applies to every test.
    """
    _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
    _write_spec(plan_context, 'PLAN-01-alpha.md')
    _write_spec(plan_context, 'PLAN-02-beta.md')
    _make_inbox(plan_context, queued=0, archived=2)
    monkeypatch.setattr(_orch, '_git_read', _git_stub())


def _run() -> dict:
    result: dict = cmd_cleanup_restart_check(_RESTART_CHECK_ARGS)
    return result


def _signal_row(result: dict, name: str) -> dict:
    rows: list[dict] = [row for row in result['signals'] if row['signal'] == name]
    assert len(rows) == 1, f'expected exactly one {name!r} row, got {len(rows)}'
    return rows[0]


def _verdicts(result: dict) -> dict:
    return {row['signal']: row['verdict'] for row in result['signals']}


# =============================================================================
# Parity store builders
# =============================================================================


class ParityStores(NamedTuple):
    """Where the three fixture stores live, plus the home directory that holds two of them."""

    home: Path
    registry: Path
    cache_root: Path
    executor: Path


def registry_entry(version: str, *, scope: str = 'user', bundle: str = PARITY_BUNDLE) -> dict:
    """One scope entry in the shape the plugin manager writes."""
    return {'scope': scope, 'installPath': f'/fixture/cache/plan-marshall/{bundle}/{version}', 'version': version}


def write_registry(stores: ParityStores, plugins: dict) -> None:
    """Write a registry holding exactly ``plugins``."""
    stores.registry.parent.mkdir(parents=True, exist_ok=True)
    stores.registry.write_text(json.dumps({'version': 2, 'plugins': plugins}), encoding='utf-8')


def pin_registry(stores: ParityStores, *versions: str) -> None:
    """Pin the plan-marshall bundle at ``versions``, one scope entry per version."""
    scopes = ('user', 'project', 'local')
    entries = [registry_entry(version, scope=scopes[index]) for index, version in enumerate(versions)]
    write_registry(stores, {f'{PARITY_BUNDLE}@plan-marshall': entries})


def write_executor(stores: ParityStores, body: str) -> None:
    """Write an executor file holding exactly ``body``."""
    stores.executor.parent.mkdir(parents=True, exist_ok=True)
    stores.executor.write_text(body, encoding='utf-8')


def set_executor_version(stores: ParityStores, version: str) -> None:
    """Write an executor that states ``version``."""
    write_executor(stores, f"#!/usr/bin/env python3\nMARSHALL_VERSION = '{version}'\n")


def add_cache_version(stores: ParityStores, version: str, bundle: str = PARITY_BUNDLE) -> None:
    """Add one version directory to ``bundle``'s cache directory."""
    (stores.cache_root / bundle / version).mkdir(parents=True, exist_ok=True)


def install_parity_stores(tree: Path, monkeypatch) -> ParityStores:
    """Build the three parity stores under ``tree``, in parity, and point the reader at them.

    The registry and the cache sit where ``plugin_registry`` looks beneath a
    home directory, so a subprocess given ``HOME={stores.home}`` reads the same
    two files through the real location functions. In-process, the three
    location functions are replaced instead of ``HOME``: the suite's pollution
    guard reads the developer's real home directory around a test, and a
    redirected ``HOME`` would move that reading.
    """
    home = tree / 'home'
    plugins = home / '.claude' / 'plugins'
    stores = ParityStores(
        home=home,
        registry=plugins / 'installed_plugins.json',
        cache_root=plugins / 'cache' / 'plan-marshall',
        executor=tree / 'checkout' / '.plan' / 'execute-script.py',
    )
    pin_registry(stores, PARITY_VERSION)
    set_executor_version(stores, PARITY_VERSION)
    add_cache_version(stores, PARITY_VERSION)
    monkeypatch.setattr(plugin_registry, 'default_registry_path', lambda: stores.registry)
    monkeypatch.setattr(plugin_registry, 'default_cache_root', lambda: stores.cache_root)
    monkeypatch.setattr(plugin_registry, 'default_executor_path', lambda project_root: stores.executor)
    return stores
