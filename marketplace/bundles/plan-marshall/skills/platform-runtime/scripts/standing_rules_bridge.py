#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The standing-rules bridge shared by the OpenCode and Antigravity runtimes.

Both harnesses deliver the repository's standing rules by writing a bridge file
that CARRIES the ``CLAUDE.md`` baseline and records the baseline's SHA-256, so an
agent reads the rules from the bridge file alone and drift is a content
comparison. Everything here is harness-independent; the runtime supplies the
only two things that differ — its bridge path (``.opencode/rules`` versus
``.agents/rules``) and the harness label in the bridge heading.

Reader/writer separation is load-bearing and is why these live in one module
rather than in each runtime: two copies of the writer drift apart, and the copy
that is not exercised by the other harness's tests is the one that rots.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

#: Version of the standing-rules bridge format written by project setup. Bumped
#: only when the bridge file layout changes; drift detection compares the marker
#: embedded in the bridge file against this constant.
BRIDGE_VERSION = 1

#: Baseline source the bridge copies from. ``CLAUDE.md`` stays authoritative —
#: the bridge is current only while it matches this source.
BASELINE = 'CLAUDE.md'

#: Marker embedded in every bridge file so drift detection can tell a current
#: bridge from a stale or foreign one without parsing rule prose.
BRIDGE_MARKER = f'bridge-version: {BRIDGE_VERSION}'

#: Filename of the bridge-owned standing-rules file. It is deliberately distinct
#: from the installed target rules shipped by ``install.sh --emit-rules``, so a
#: setup write can never land in the installed file.
BRIDGE_RULES_FILENAME = 'plan-marshall-standing-rules.md'

#: Filename of the installed target rules shipped by ``install.sh --emit-rules``.
INSTALLED_RULES_FILENAME = 'plan-marshall-target-rules.md'

#: Pattern matching a bridge stub a previous setup left in the installed target
#: rules. Only the bridge marker spells ``bridge-version`` followed by a colon
#: and a digit; the rule prose carries the bare words, so prose can never
#: false-positive a clobber report.
MARKER_PATTERN = re.compile(r'bridge-version\s*:\s*\d')

#: The content hash the bridge records for the baseline it was generated from.
#: Drift is decided by comparing this hash to the CURRENT baseline, never by
#: mtime: a checkout, a rebase or a ``touch`` moves mtime without changing a
#: rule, and an mtime-only verdict would flag drift on every one of them.
SOURCE_HASH_PATTERN = re.compile(r'^source-sha256:\s*([0-9a-f]{64})$', re.MULTILINE)


class BridgeWrite(NamedTuple):
    """What one bridge write did.

    ``written`` reports that a write happened; ``replaced`` reports that it
    replaced an EXISTING file that differed from what was written; ``failed``
    reports that the write was attempted and the filesystem refused it. The
    second and third fields are the writer's OWN write-time observations, so a
    change made to the bridge between the drift read and the write cannot hide a
    heal behind a stale pre-check, and a refused write cannot read as a clean
    setup.
    """

    written: bool
    replaced: bool
    failed: bool = False


class SetupReport(NamedTuple):
    """What one setup's bridge reconcile found and did — the payload a setup reports.

    ``drift`` is the setup's verdict, not the pre-heal read: a bridge this setup
    rewrote was drifted by definition, and a write the filesystem refused means
    the reconcile did not happen.
    """

    written: bool
    drift: bool
    reason: str


def baseline_text(project_dir: Path, baseline: str = BASELINE) -> str | None:
    """Return the standing-rules baseline's text, or ``None`` when unreadable.

    Unreadable covers BOTH a file the process cannot read (``OSError``) and a
    file whose bytes are not UTF-8 (``UnicodeDecodeError``): each leaves nothing
    to bridge, so the caller keeps the existing bridge instead of failing.
    """
    try:
        return (project_dir / baseline).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None


def bridge_body(label: str, carried: str | None, baseline: str = BASELINE) -> str:
    """Render the bridge file for *carried* baseline text.

    The bridge CARRIES the baseline's rules — it is generated from the baseline,
    so a harness agent reads them without a second source of truth — and records
    the baseline's SHA-256 so drift is a content comparison. With no readable
    baseline there is nothing to carry and the bridge stays a marker plus a
    pointer, which is still an honest statement of what was bridged.
    """
    if carried is None:
        return (
            f'# Plan Marshall standing rules ({label} bridge {BRIDGE_MARKER})\n\n'
            f'Standing rules bridged from {baseline} at project setup. '
            'No readable baseline was present, so this file carries no rules yet; '
            're-run setup once the baseline exists.\n'
        )
    digest = hashlib.sha256(carried.encode('utf-8')).hexdigest()
    return (
        f'# Plan Marshall standing rules ({label} bridge {BRIDGE_MARKER})\n\n'
        f'source: {baseline}\n'
        f'source-sha256: {digest}\n\n'
        f'<!-- Generated from {baseline}; edit the baseline, not this file. -->\n\n'
        f'{carried}'
    )


def write_bridge(
    project_dir: Path,
    bridge: Path,
    label: str,
    baseline: str = BASELINE,
) -> BridgeWrite:
    """Write the bridge file that carries the baseline's standing rules.

    Returns what the write did. The bridge owns its own file; the installed
    target rules shipped by ``install.sh --emit-rules`` are never written here,
    so a setup cannot replace the full rules with a stub.

    The two "no text" cases are DIFFERENT and must not be collapsed:

    * A MISSING baseline has nothing to carry, so the bridge becomes the
      marker-only stub — a bridge that still carried rules from a deleted
      baseline would present stale rules as current.
    * A PRESENT but unreadable baseline leaves an existing bridge untouched:
      replacing it with the stub would delete rules the operator still has on
      disk for a transient read failure.

    The equality check is over BYTES: replacement decoding would call an
    invalid-UTF-8 body current whenever the baseline itself carries U+FFFD, and
    the malformed bridge would stay on disk.
    """
    baseline_path = project_dir / baseline
    carried = baseline_text(project_dir, baseline)
    if carried is None and baseline_path.is_file() and bridge.is_file():
        return BridgeWrite(written=False, replaced=False)
    desired = bridge_body(label, carried, baseline).encode('utf-8')
    try:
        # A symlinked bridge path is never taken as an owned, current bridge —
        # even when its target already matches — because a later change to that
        # target would change the workspace rules without changing the path.
        if bridge.is_file() and not bridge.is_symlink() and bridge.read_bytes() == desired:
            return BridgeWrite(written=False, replaced=False)
        replaced = bridge.is_file()
        bridge.parent.mkdir(parents=True, exist_ok=True)
        # Stage the bytes under a uniquely created name beside the bridge and
        # REPLACE the path: a partial write can never leave a damaged bridge, a
        # planted symlink at the staging name cannot be written through, and a
        # symlinked bridge path becomes the bridge file itself.
        handle, staging_name = tempfile.mkstemp(dir=bridge.parent, prefix=f'.{bridge.name}.', suffix='.tmp')
        staging = Path(staging_name)
        try:
            with os.fdopen(handle, 'wb') as stream:
                stream.write(desired)
            staging.chmod(0o644)
            staging.replace(bridge)
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
        return BridgeWrite(written=True, replaced=replaced)
    except OSError:
        return BridgeWrite(written=False, replaced=False, failed=True)


def drift_status(
    project_dir: Path,
    bridge: Path,
    label: str,
    baseline: str = BASELINE,
) -> dict[str, Any]:
    """Detect drift of the standing-rules bridge against its baseline.

    Drift is decided by CONTENT: the ``source-sha256`` the bridge recorded is
    compared with the current baseline's hash. ``baseline_changed`` means the
    rules moved; a timestamp change alone is ``in_sync``. A bridge with the
    marker but no recorded hash predates content tracking and is reported as
    ``source_hash_missing`` rather than assumed current. A baseline that exists
    but cannot be decoded is ``baseline_unreadable`` — drift whatever the bridge
    holds, because the rules exist and are not being read — and bridge bytes that
    are not UTF-8 are ``bridge_unreadable``; neither raises. With no baseline
    file at all, a bridge that still carries rules is ``drift`` (the writer
    replaces it with the stub) while the marker-only stub the writer produces is
    current.
    """
    baseline_path = project_dir / baseline
    baseline_present = baseline_path.is_file()
    carried = baseline_text(project_dir, baseline) if baseline_present else None
    if not baseline_present:
        if not bridge.is_file():
            return {'drift': False, 'needs_bridge': True, 'reason': 'baseline_missing'}
        try:
            bridge_bytes = bridge.read_bytes()
        except OSError:
            return {'drift': True, 'needs_bridge': False, 'reason': 'baseline_missing'}
        # A stub carries no rules, so a deleted baseline loses nothing and the
        # bridge is current; a bridge that still carries rules is stale — the
        # writer replaces it with the stub, which is drift.
        return {
            'drift': bridge_bytes != bridge_body(label, None, baseline).encode('utf-8'),
            'needs_bridge': False,
            'reason': 'baseline_missing',
        }
    if carried is None:
        # The baseline exists and the rules are there, but this process cannot
        # read them: the bridge is uncertifiable whatever it holds.
        return {
            'drift': True,
            'needs_bridge': not bridge.is_file(),
            'reason': 'baseline_unreadable',
        }
    if not bridge.is_file():
        return {'drift': False, 'needs_bridge': True, 'reason': 'bridge_missing'}
    try:
        text = bridge.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {'drift': True, 'needs_bridge': False, 'reason': 'bridge_unreadable'}
    if BRIDGE_MARKER not in text:
        return {'drift': True, 'needs_bridge': False, 'reason': 'marker_mismatch'}
    recorded = SOURCE_HASH_PATTERN.search(text)
    if recorded is None:
        return {'drift': True, 'needs_bridge': False, 'reason': 'source_hash_missing'}
    if recorded.group(1) != hashlib.sha256(carried.encode('utf-8')).hexdigest():
        return {'drift': True, 'needs_bridge': False, 'reason': 'baseline_changed'}
    return {'drift': False, 'needs_bridge': False, 'reason': 'in_sync'}


def setup(
    project_dir: Path,
    bridge: Path,
    label: str,
    baseline: str = BASELINE,
) -> SetupReport:
    """Heal the bridge and report what the setup found and did.

    The drift status is read BEFORE the heal: a setup that rewrites the bridge
    has just found it drifted, and reporting the post-write ``in_sync`` would
    tell the operator nothing needed attention. The writer's own observations
    then add the two cases that pre-heal read cannot see — a body-only edit
    whose recorded hash still matches (``bridge_body_replaced``), and a write the
    filesystem refused (``bridge_write_failed``, which is the dominant fact
    because the reconcile did not happen whatever the pre-heal verdict was).
    """
    drift = drift_status(project_dir, bridge, label, baseline)
    write = write_bridge(project_dir, bridge, label, baseline)
    setup_drift = drift['drift'] or write.replaced
    reason = drift['reason']
    if write.replaced and reason == 'in_sync':
        reason = 'bridge_body_replaced'
    if write.failed:
        setup_drift = True
        reason = 'bridge_write_failed'
    return SetupReport(written=write.written, drift=setup_drift, reason=reason)
