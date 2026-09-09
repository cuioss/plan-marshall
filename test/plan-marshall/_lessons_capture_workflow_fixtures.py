#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``lessons capture workflow`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""

from pathlib import Path

from conftest import get_skill_dir

# Annotated because ``conftest`` is deliberately untyped to mypy (see pyproject's
# ``ignore_missing_imports`` override for it), so the accessor's return would
# otherwise be ``Any`` and every reader below would return ``Any`` as ``str``.
_BUNDLE_ROOT: Path = get_skill_dir('plan-marshall', 'phase-6-finalize')


_WORKFLOW_PATH = _BUNDLE_ROOT / 'workflow' / 'lessons-capture.md'


_DISPATCHER_PATH = _BUNDLE_ROOT / 'SKILL.md'


def _read_workflow() -> str:
    """Read the workflow body once per test for substring assertions."""
    return _WORKFLOW_PATH.read_text(encoding='utf-8')


def _read_dispatcher() -> str:
    """Read the phase-6-finalize SKILL.md dispatcher once per test."""
    return _DISPATCHER_PATH.read_text(encoding='utf-8')
