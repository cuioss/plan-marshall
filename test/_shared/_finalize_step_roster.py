# SPDX-License-Identifier: FSL-1.1-ALv2
"""The finalize-step roster as THIS checkout's tracked trees declare it.

``extension_discovery.find_implementors`` is the right population source for the
finalize-step guards — it is the same discovery the product consumes — but it
scans the running machine as well as the checkout: the plugin cache roots, flat
deployment roots, and the target's project-local skill roots. A developer with a
cached or installed finalize step that this checkout does not ship would then
change a test's population, which is the same class of environment coupling the
hermeticity work removed (it just moves from ``.plan/marshal.json`` to
``~/.claude/plugins``).

Every guard that needs the roster wants the one the checkout ships, so this
module filters the discovery to records whose document lives inside
``PROJECT_ROOT``. A doc under ``marketplace/`` (built-in or bundle-optional) and a
doc under ``.claude/skills/`` (project step) both qualify; a plugin-cache or
flat-deployment copy does not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from extension_discovery import find_implementors

from conftest import PROJECT_ROOT

FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'


def _in_checkout(record_path: str) -> bool:
    """Whether a discovered step document lives inside this checkout."""
    return Path(record_path).is_relative_to(PROJECT_ROOT)


def in_checkout_finalize_records() -> list[dict[str, Any]]:
    """Discovered finalize-step records whose documents live inside the checkout."""
    return [record for record in find_implementors(FINALIZE_STEP_EXT_POINT) if _in_checkout(str(record['path']))]


def in_checkout_step_documents() -> dict[str, list[Path]]:
    """Map each checkout step id to the document path(s) discovery found for it.

    A project step may live under any target's project-local skill root
    (``.claude/skills``, ``.opencode/skills``, ``.agents/skills``), so a caller that
    re-derives the path from the step id alone misses every root but its guess. The
    discovered path is the authority.
    """
    documents: dict[str, list[Path]] = {}
    for record in in_checkout_finalize_records():
        documents.setdefault(str(record['name']), []).append(Path(str(record['path'])))
    return documents


def in_checkout_finalize_steps() -> list[str]:
    """The step ids whose documents this checkout ships, in discovery order.

    Returns:
        One step id per implementor found under ``PROJECT_ROOT`` — ``default:*``
        for built-ins, ``<bundle>:<skill>`` for bundle-optional steps and
        ``project:<skill-dir>`` for project steps. Cache and flat-deployment
        copies outside the checkout are excluded so the population is identical
        on every machine.
    """
    return [str(record['name']) for record in in_checkout_finalize_records()]
