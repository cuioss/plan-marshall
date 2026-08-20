#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage status main dispatch`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

In-process tests for the manage-status.py CLI dispatcher (``main``).

The existing manage-status suites drive the per-command handlers directly
(``cmd_create``, ``cmd_metadata``, …) or invoke the script through a
subprocess. Neither path attributes coverage to the dispatcher body in
``manage-status.py`` — the argparse construction, the ``func``-dispatch, the
``transition`` exit-code contract, and the ``_loop_back_target_type`` argparse
``type=`` validator. These tests call ``main()`` in-process (after setting
``sys.argv``) so coverage lands on the dispatcher source, while still asserting
real behaviour: exit codes, the emitted TOON status, and routing payloads.

``main()`` is wrapped by ``@safe_main``, which calls ``sys.exit(main())``;
every dispatch therefore raises ``SystemExit`` whose ``.code`` is the script's
integer return.
"""


import json
import sys

import pytest

from conftest import load_script_module

# Load the dispatcher module in-process (unique module name) so coverage is
# attributed to manage-status.py rather than to a subprocess.
_ms = load_script_module('plan-marshall', 'manage-status', 'manage-status.py', 'inproc_manage_status_main')


_PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


def _run(monkeypatch, capsys, argv):
    """Invoke ``main()`` with ``argv`` and return (exit_code, stdout, stderr)."""
    monkeypatch.setattr(sys, 'argv', ['manage-status.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _ms.main()
    captured = capsys.readouterr()
    code = exc.value.code if exc.value.code is not None else 0
    return code, captured.out, captured.err


def _parse(out):
    from toon_parser import parse_toon

    return parse_toon(out)


# =============================================================================
# metadata / title-token / update-phase / progress
# =============================================================================

def _pin_stale_snapshot(monkeypatch, snapshot):
    """Make every ``require_status`` read return *snapshot* verbatim.

    Reproduces the interleaving deterministically: a full-document writer holds
    a snapshot read taken BEFORE a concurrent ``title-token set`` committed, and
    performs its own write AFTER. Without a guarded write seam the writer would
    restore the snapshot's ``title_token`` (here, its absence) over the live
    record. ``require_status`` resolves ``read_status`` through the module
    global, so patching it there is what the phase writers actually see.
    """
    import _status_core

    monkeypatch.setattr(
        _status_core, 'read_status', lambda _plan_id: json.loads(json.dumps(snapshot))
    )
