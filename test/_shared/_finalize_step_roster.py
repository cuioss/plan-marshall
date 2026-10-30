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

Every guard that needs the roster wants the one this revision ships, so this
module keeps a record only when its document is BOTH inside ``PROJECT_ROOT`` and
tracked by git. The first filter drops another machine's install; the second
drops an untracked local scratch skill, which would otherwise join the roster and
fail the closure assertion against the unchanged dispatch document.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from extension_discovery import find_implementors

from conftest import PROJECT_ROOT

FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'


def _in_checkout(record_path: str) -> bool:
    """Whether a discovered step document lives inside this checkout."""
    return Path(record_path).is_relative_to(PROJECT_ROOT)


def _tracked(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the records whose document this revision tracks.

    A ``git ls-files`` that cannot run fails OPEN — the untracked filter is a
    determinism refinement, and dropping the whole population on a git error would
    turn every guard below vacuous.
    """
    if not records:
        return records
    paths = [Path(str(record['path'])) for record in records]
    relative = [str(path.relative_to(PROJECT_ROOT)) for path in paths]
    # `git -C` still honours a caller's GIT_DIR / GIT_INDEX_FILE, which would make
    # this read a different repository or index. Strip them so the question really
    # is "does THIS checkout track this file". A missing `git` is a launch error
    # before the return-code fallback, so it fails open here too.
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'}
    }
    try:
        completed = subprocess.run(
            ['git', '-C', str(PROJECT_ROOT), 'ls-files', '--', *relative],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError:
        return records
    if completed.returncode != 0:
        return records
    tracked = {(PROJECT_ROOT / line).resolve() for line in completed.stdout.splitlines() if line}
    return [record for record, path in zip(records, paths, strict=True) if path.resolve() in tracked]


def in_checkout_finalize_records() -> list[dict[str, Any]]:
    """Discovered finalize-step records whose documents this checkout tracks."""
    records = [record for record in find_implementors(FINALIZE_STEP_EXT_POINT) if _in_checkout(str(record['path']))]
    return _tracked(records)


def in_checkout_step_documents() -> dict[str, list[Path]]:
    """Map each checkout step id to the document path(s) discovery found for it."""
    documents: dict[str, list[Path]] = {}
    for record in in_checkout_finalize_records():
        documents.setdefault(str(record['name']), []).append(Path(str(record['path'])))
    return documents


def in_checkout_finalize_steps() -> list[str]:
    """The step ids whose documents this checkout tracks, in discovery order.

    Returns:
        One step id per tracked implementor — ``default:*`` for built-ins,
        ``<bundle>:<skill>`` for bundle-optional steps and ``project:<skill-dir>``
        for project steps. Cache copies, flat deployments and untracked local
        scratch skills are excluded so the population is identical on every
        machine.
    """
    return [str(record['name']) for record in in_checkout_finalize_records()]
