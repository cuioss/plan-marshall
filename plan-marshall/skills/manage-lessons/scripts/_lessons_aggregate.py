#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure signal-grouping helpers for the ``aggregate`` verb.

Co-located helper module for ``manage-lessons.py``. Holds the deterministic,
side-effect-free pieces of the read-only aggregate classifier: the lesson-id /
recurrence regexes, the signal-tier constants, and the grouping/primary-pick/
composition helpers. See ``references/aggregate-analysis.md`` for the
authoritative classifier specification.

The datetime-free and non-patched portions of the aggregate section live here.
The clock-independent-but-patch-coupled pieces (``_derive_standards_dir``, which
reads the test-patched ``find_marketplace_path``) and the corpus loader /
``cmd_aggregate`` dispatch stay in the entry module.
"""

import re

# Regex matching the lesson-id pattern ``YYYY-MM-DD-HH-NNN`` exactly.
LESSON_ID_REGEX = re.compile(r'\b\d{4}-\d{2}-\d{2}-\d{2}-\d{3}\b')

# Recurrence H2 regex used to count appended dedup-merge sections in a body.
RECURRENCE_H2_REGEX = re.compile(r'(?m)^## Recurrence —')

# Maximum size of merged_body_preview in characters.
AGGREGATE_PREVIEW_CHARS = 400

# Signal priority labels (highest first). Used both for tier-detection during
# grouping and for ordering the headline command list.
SIGNAL_CROSS_REF = 'cross-ref'
SIGNAL_SHARED_COMPONENT = 'shared-component'
SIGNAL_SHARED_STANDARDS_DIR = 'shared-standards-dir'
SIGNAL_SHARED_WORKFLOW_BOUNDARY = 'shared-workflow-boundary'

SIGNAL_PRIORITY: tuple[str, ...] = (
    SIGNAL_CROSS_REF,
    SIGNAL_SHARED_COMPONENT,
    SIGNAL_SHARED_STANDARDS_DIR,
    SIGNAL_SHARED_WORKFLOW_BOUNDARY,
)


def _derive_workflow_boundary(component: str) -> str:
    """Derive the workflow-boundary label from a component value.

    The workflow boundary is the ``{bundle}:{skill}`` pair stripped of any
    task-number suffix (e.g., ``plan-marshall:phase-5-execute:5`` →
    ``plan-marshall:phase-5-execute``). Returns the component verbatim when
    no trailing numeric suffix is present, or the empty string for unparseable
    values.
    """
    if not component:
        return ''
    parts = component.split(':')
    if len(parts) < 2:
        return ''
    # Drop a trailing purely-numeric segment if present.
    if len(parts) >= 3 and parts[-1].isdigit():
        parts = parts[:-1]
    return ':'.join(parts[:2]) if len(parts) >= 2 else ''


def _extract_cross_refs(lesson_id: str, body: str) -> set[str]:
    """Extract lesson-id cross references from a body, excluding self-refs."""
    if not body:
        return set()
    matches = set(LESSON_ID_REGEX.findall(body))
    matches.discard(lesson_id)
    return matches


def _group_by_signals(lessons: list[dict]) -> list[dict]:
    """Build groups using the strongest-wins priority order.

    Walks signal tiers in priority order. Within each tier, members are
    placed into buckets keyed by the tier's signal value (cross-ref groups
    by alphabetically-smallest member id; shared-component groups by the
    component value; etc.). A lesson placed at a higher tier is not
    eligible for a weaker tier. Multi-member groups only — singletons are
    dropped.
    """
    by_id = {lesson['id']: lesson for lesson in lessons}
    placed: dict[str, dict] = {}  # lesson_id -> {group_id, signal}
    # Keyed by (signal, group_key) tuple so the same string value can serve as
    # a group key at multiple tiers without collision.
    groups: dict[tuple[str, str], dict] = {}

    # ---- Tier 1: cross-ref ----
    # A cross-ref pair links two lessons when either body cites the other's
    # id. Connected components form a group.
    adjacency: dict[str, set[str]] = {lid: set() for lid in by_id}
    for lid, lesson in by_id.items():
        for ref in lesson['cross_refs']:
            if ref in by_id:
                adjacency[lid].add(ref)
                adjacency[ref].add(lid)

    visited: set[str] = set()
    for lid in sorted(by_id):
        if lid in visited:
            continue
        # BFS the component containing lid.
        component_members: set[str] = set()
        queue = [lid]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            component_members.add(cur)
            for neighbour in adjacency[cur]:
                if neighbour not in visited:
                    queue.append(neighbour)
        if len(component_members) < 2:
            continue
        # Place all members at the cross-ref tier.
        group_key = sorted(component_members)[0]  # alphabetically smallest member id
        groups[(SIGNAL_CROSS_REF, group_key)] = {
            'key': group_key,
            'signal': SIGNAL_CROSS_REF,
            'members': component_members,
        }
        for member in component_members:
            placed[member] = {'group_key': group_key, 'signal': SIGNAL_CROSS_REF}

    # Helper: attempt to add lesson at a given tier with a given key.
    def _try_place(lesson_id: str, group_key: str, signal: str) -> None:
        if lesson_id in placed:
            return
        existing = groups.get((signal, group_key))
        if existing is None:
            groups[(signal, group_key)] = {
                'key': group_key,
                'signal': signal,
                'members': {lesson_id},
            }
        else:
            existing['members'].add(lesson_id)

    # ---- Tier 2: shared-component ----
    component_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        comp = lesson['component']
        if not comp:
            continue
        component_buckets.setdefault(comp, []).append(lid)
    for comp, members in component_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, comp, SIGNAL_SHARED_COMPONENT)
        # Mark as placed only if the bucket actually formed a group.
        bucket_group = groups.get((SIGNAL_SHARED_COMPONENT, comp))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': comp,
                    'signal': SIGNAL_SHARED_COMPONENT,
                }

    # ---- Tier 3: shared-standards-dir ----
    standards_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        sdir = lesson['standards_dir']
        if not sdir:
            continue
        standards_buckets.setdefault(sdir, []).append(lid)
    for sdir, members in standards_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, sdir, SIGNAL_SHARED_STANDARDS_DIR)
        bucket_group = groups.get((SIGNAL_SHARED_STANDARDS_DIR, sdir))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': sdir,
                    'signal': SIGNAL_SHARED_STANDARDS_DIR,
                }

    # ---- Tier 4: shared-workflow-boundary ----
    boundary_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        boundary = lesson['workflow_boundary']
        if not boundary:
            continue
        boundary_buckets.setdefault(boundary, []).append(lid)
    for boundary, members in boundary_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, boundary, SIGNAL_SHARED_WORKFLOW_BOUNDARY)
        bucket_group = groups.get((SIGNAL_SHARED_WORKFLOW_BOUNDARY, boundary))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': boundary,
                    'signal': SIGNAL_SHARED_WORKFLOW_BOUNDARY,
                }

    # Filter to multi-member groups only (drop singletons that may have
    # leaked through helper bookkeeping).
    return [
        {
            'key': info['key'],
            'signal': info['signal'],
            'members': sorted(info['members']),
        }
        for info in groups.values()
        if len(info['members']) >= 2
    ]


def _pick_primary(group_member_ids: list[str], by_id: dict[str, dict]) -> str:
    """Apply the primary-pick rule from ``aggregate-analysis.md``.

    Order: highest cross-ref-fan-in (count of OTHER members citing this
    lesson) → highest recurrence-count → lowest lesson id ascending.
    """
    member_set = set(group_member_ids)

    def fan_in(lid: str) -> int:
        return sum(
            1
            for other in member_set
            if other != lid and lid in by_id[other]['cross_refs']
        )

    # Sort by (-fan_in, -recurrence, id ascending) — ascending wins are first.
    ranked = sorted(
        group_member_ids,
        key=lambda lid: (-fan_in(lid), -by_id[lid]['recurrence_count'], lid),
    )
    return ranked[0]


def _absorbed_reason(
    absorbed_id: str,
    primary_id: str,
    signal: str,
    by_id: dict[str, dict],
    group_key: str,
) -> str:
    """Compose the absorbed-row ``reason`` field per the doc contract."""
    if signal == SIGNAL_CROSS_REF:
        return f'cross-ref to {primary_id}'
    if signal == SIGNAL_SHARED_COMPONENT:
        return f'shared component {by_id[absorbed_id]["component"]}'
    if signal == SIGNAL_SHARED_STANDARDS_DIR:
        return f'shared standards-dir {group_key}'
    if signal == SIGNAL_SHARED_WORKFLOW_BOUNDARY:
        return f'shared workflow-boundary {group_key}'
    return signal


def _compose_merged_body(primary: dict, absorbed: list[dict]) -> str:
    """Compose the would-be merged body verbatim per the doc template."""
    sections = [primary['body'].rstrip()]
    for member in absorbed:
        sections.append(
            f'## Sub-task: {member["title"]} ({member["id"]})\n\n'
            f'{member["body"].rstrip()}'
        )
    return '\n\n'.join(sections)


def _truncate_preview(text: str, limit: int) -> str:
    """Truncate ``text`` to at most ``limit`` characters on a code-point boundary.

    Python string slicing already operates on code-point boundaries, so a
    plain ``text[:limit]`` is safe here. The helper is kept as a named
    boundary for the doc contract (``first ~400 chars`` rule).
    """
    if len(text) <= limit:
        return text
    return text[:limit]
