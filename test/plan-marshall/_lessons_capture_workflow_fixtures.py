#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``lessons capture workflow`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from pathlib import Path

_BUNDLE_ROOT = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
)


_WORKFLOW_PATH = _BUNDLE_ROOT / 'workflow' / 'lessons-capture.md'


_DISPATCHER_PATH = _BUNDLE_ROOT / 'SKILL.md'


def _read_workflow() -> str:
    """Read the workflow body once per test for substring assertions."""
    return _WORKFLOW_PATH.read_text(encoding='utf-8')


def _read_dispatcher() -> str:
    """Read the phase-6-finalize SKILL.md dispatcher once per test."""
    return _DISPATCHER_PATH.read_text(encoding='utf-8')
