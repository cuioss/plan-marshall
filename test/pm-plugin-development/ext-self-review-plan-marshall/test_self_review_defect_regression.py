#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression pinning the two PR #1067 defects the self-review missed (D4).

``pre-submission-self-review`` ran twice at the #1067 HEAD, examined 117
candidates, and reported ``self-review clean: no check matched`` — yet PR #1067
shipped two Major defects (findings ``8da924`` and ``3e04a8``, both resolution
``fixed``) that are mechanically detectable. This module pins BOTH against the
REAL pre-fix code, so a detector that ever stops firing on the real defect fails
here.

* **Case (a)** — the ``discover_derivation_resolvers()`` shape at its pre-fix
  revision is flagged by ``_detect_duplicate_claimable_keys`` (D1): a resolver id
  appended behind a bare ``if not resolver_id`` falsiness check with no
  membership test, so two resolvers answering the same id collapse into one
  producer identity.
* **Case (b)** — the ``merge_resolver_edges()`` shape at its pre-fix revision is
  flagged by ``_detect_discard_without_report`` (D2): three ``continue`` branches
  drop candidates without appending to the ``notes`` report channel — a vacuous
  ``status: ok`` / zero-edge / empty-notes report.

The pre-fix and post-fix bodies below are the REAL code, transcribed from the
#1067 feature branch (``git fetch origin refs/pull/1067/head``): the introducing
commit is ``2896e18``, the fix is ``c4ff227``, and ``14d4e3d`` (= ``c4ff227^``)
is the last commit carrying the defect. They are checked-in LITERALS, never
resolved from a git object at test time — the #1067 branch was squash-merged into
``c6b501e`` and its intermediate commits are garbage-collection candidates, so a
git-resolving fixture would pass today and silently stop testing anything once the
object is pruned. This mirrors the rule-19 worked-example fixture discipline
(``SKILL.md`` § Tests).

Every executable line of each fixture is verbatim from that revision; only the
long production docstrings are elided (a one-line note stands in), because the
defect is a property of the CODE, not the prose. The negative controls — the
detector is SILENT on the shipped post-fix form and on the sibling function —
prove the failing direction is real: a detector never seen to NOT fire is not
known to discriminate.
"""

from self_review import (  # noqa: I001
    _detect_discard_without_report,
    _detect_duplicate_claimable_keys,
)

# =============================================================================
# Real #1067 code — verbatim executable lines, docstrings elided
# =============================================================================

#: discover_derivation_resolvers() at 14d4e3d — the PRE-FIX defect (finding 8da924).
#: ``resolvers.append({... 'id': resolver_id ...})`` behind a bare ``if not
#: resolver_id`` check, with NO membership test → duplicate ids collapse.
DISCOVER_RESOLVERS_PREFIX = '''\
def discover_derivation_resolvers() -> list[dict[str, Any]]:
    """Pre-fix (14d4e3d): resolver id appended behind a bare falsiness check."""
    from extension_base import DerivationResolverBase

    candidates: list[tuple[str, Any]] = []
    for ext in discover_all_extensions():
        module = ext.get('module')
        if module is not None:
            candidates.append((ext.get('bundle', 'unknown'), module))
    for ext in discover_build_extensions():
        module = ext.get('module')
        if module is not None:
            candidates.append((ext.get('skill', 'unknown'), module))

    resolvers: list[dict[str, Any]] = []
    for origin, module in candidates:
        if not isinstance(module, DerivationResolverBase):
            continue
        try:
            resolver_id = module.derivation_resolver_id()
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] derivation_resolver_id() failed for {origin}: {e}',
            )
            continue
        if not resolver_id:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] Skipping derivation resolver from {origin}: empty resolver id',
            )
            continue
        resolvers.append({'origin': origin, 'id': resolver_id, 'module': module})

    resolvers.sort(key=lambda rec: rec['id'])
    return resolvers
'''

#: discover_derivation_resolvers() at c6b501e (merged #1067) — the POST-FIX form.
#: ``origin_by_id.get(resolver_id)`` + ``origin_by_id[resolver_id] = origin`` is
#: the membership/dedup guard that must suppress D1.
DISCOVER_RESOLVERS_POSTFIX = '''\
def discover_derivation_resolvers() -> list[dict[str, Any]]:
    """Post-fix (c6b501e): identity validated as a non-empty string AND deduped."""
    from extension_base import DerivationResolverBase

    candidates: list[tuple[str, Any]] = []
    for ext in discover_all_extensions():
        module = ext.get('module')
        if module is not None:
            candidates.append((ext.get('bundle', 'unknown'), module))
    for ext in discover_build_extensions():
        module = ext.get('module')
        if module is not None:
            candidates.append((ext.get('skill', 'unknown'), module))

    resolvers: list[dict[str, Any]] = []
    origin_by_id: dict[str, str] = {}
    for origin, module in candidates:
        if not isinstance(module, DerivationResolverBase):
            continue
        try:
            resolver_id = module.derivation_resolver_id()
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] derivation_resolver_id() failed for {origin}: {e}',
            )
            continue
        if not isinstance(resolver_id, str) or not resolver_id.strip():
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] Skipping derivation resolver from {origin}: resolver id must be a '
                f'non-empty string, got {resolver_id!r}',
            )
            continue
        resolver_id = resolver_id.strip()
        claimed_by = origin_by_id.get(resolver_id)
        if claimed_by is not None:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] Skipping derivation resolver from {origin}: resolver id '
                f'{resolver_id!r} is already claimed by {claimed_by}',
            )
            continue
        origin_by_id[resolver_id] = origin
        resolvers.append({'origin': origin, 'id': resolver_id, 'module': module})

    resolvers.sort(key=lambda rec: rec['id'])
    return resolvers
'''

#: merge_resolver_edges() at 14d4e3d — the PRE-FIX defect (finding 3e04a8). Three
#: ``continue`` branches drop candidates without appending to ``notes``.
MERGE_EDGES_PREFIX = '''\
def merge_resolver_edges(
    resolvers: list[dict[str, Any]],
    derived_by_name: dict,
    enriched_by_name: dict,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pre-fix (14d4e3d): merge-side drops carry no notes[] — a vacuous zero."""
    known_modules = set(derived_by_name)
    producers_by_pair: dict[tuple[str, str], set[str]] = {}
    reports: list[dict[str, Any]] = []

    for record in resolvers:
        resolver_id = record.get('id', '')

        try:
            raw_edges, raw_notes = record['module'].derive_edges(derived_by_name, enriched_by_name)
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] derive_edges() failed for derivation resolver {resolver_id}: {e}',
            )
            reports.append(
                {
                    'id': resolver_id,
                    'edge_count': 0,
                    'status': _STATUS_ERROR,
                    'notes': [f'derive_edges() raised: {e}'],
                }
            )
            continue

        notes = _coerce_notes(raw_notes)
        contributed: set[tuple[str, str]] = set()
        for candidate in raw_edges or []:
            pair = _coerce_pair(candidate)
            if pair is None:
                continue
            source, target = pair
            if source == target:
                continue
            if source not in known_modules or target not in known_modules:
                continue
            contributed.add(pair)
            producers_by_pair.setdefault(pair, set()).add(resolver_id)

        reports.append(
            {
                'id': resolver_id,
                'edge_count': len(contributed),
                'status': _STATUS_OK,
                'notes': notes,
            }
        )

    edges = [
        {'from': source, 'to': target, 'producers': sorted(producers_by_pair[(source, target)])}
        for source, target in sorted(producers_by_pair)
    ]
    return edges, reports
'''

#: merge_resolver_edges() at c6b501e (merged #1067) — the POST-FIX form. Each
#: drop appends a ``merge:``-prefixed note to ``notes`` before ``continue``.
MERGE_EDGES_POSTFIX = '''\
def merge_resolver_edges(
    resolvers: list[dict[str, Any]],
    derived_by_name: dict,
    enriched_by_name: dict,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Post-fix (c6b501e): every merge-side drop appends its own note first."""
    known_modules = set(derived_by_name)
    producers_by_pair: dict[tuple[str, str], set[str]] = {}
    reports: list[dict[str, Any]] = []

    for record in resolvers:
        resolver_id = record.get('id', '')

        try:
            raw_edges, raw_notes = record['module'].derive_edges(derived_by_name, enriched_by_name)
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] derive_edges() failed for derivation resolver {resolver_id}: {e}',
            )
            reports.append(
                {
                    'id': resolver_id,
                    'edge_count': 0,
                    'status': _STATUS_ERROR,
                    'notes': [f'derive_edges() raised: {e}'],
                }
            )
            continue

        notes = _coerce_notes(raw_notes)
        contributed: set[tuple[str, str]] = set()
        for candidate in raw_edges or []:
            pair = _coerce_pair(candidate)
            if pair is None:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped malformed candidate {candidate!r} — '
                    f'not a two-element pair of module-name strings'
                )
                continue
            source, target = pair
            if source == target:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped self-edge ({source} -> {target}) — '
                    f'a module does not depend on itself'
                )
                continue
            unknown = [name for name in (source, target) if name not in known_modules]
            if unknown:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped edge ({source} -> {target}) — '
                    f'unknown module endpoint(s): {", ".join(unknown)}'
                )
                continue
            contributed.add(pair)
            producers_by_pair.setdefault(pair, set()).add(resolver_id)

        reports.append(
            {
                'id': resolver_id,
                'edge_count': len(contributed),
                'status': _STATUS_OK,
                'notes': notes,
            }
        )

    edges = [
        {'from': source, 'to': target, 'producers': sorted(producers_by_pair[(source, target)])}
        for source, target in sorted(producers_by_pair)
    ]
    return edges, reports
'''


def _as_added(source: str, path: str = 'extension_discovery.py'):
    """Convert fixture source to the detector's ``(path, lineno, content)`` form."""
    return [(path, i, line) for i, line in enumerate(source.splitlines(), start=1)]


# =============================================================================
# Case (a) — D1 flags the real discover_derivation_resolvers() pre-fix defect
# =============================================================================


class TestDiscoverResolversDuplicateKeyRegression:
    """D1 pins finding 8da924: the duplicate-claimable resolver id."""

    def test_prefix_is_flagged(self):
        out = _detect_duplicate_claimable_keys(_as_added(DISCOVER_RESOLVERS_PREFIX))
        # Exactly the resolvers.append insertion is surfaced — the real defect.
        appends = [e for e in out if e['collection'] == 'resolvers']
        assert len(appends) == 1, f'expected the resolvers.append flagged, got {out}'
        hit = appends[0]
        assert hit['key'] == 'resolver_id'
        assert hit['form'] == 'append'

    def test_postfix_is_silent(self):
        # The shipped fix adds ``origin_by_id.get(resolver_id)`` + the subscript
        # claim — the membership guard that suppresses the class. Neither the
        # append nor the new subscript may surface.
        out = _detect_duplicate_claimable_keys(_as_added(DISCOVER_RESOLVERS_POSTFIX))
        assert out == [], f'post-fix must be silent, got {out}'

    def test_prefix_positive_and_postfix_negative_over_same_shape(self):
        # The matched control: the ONLY structural difference between the two
        # fixtures is the dedup guard, so a green pair proves D1 keys on that
        # guard rather than on some incidental token.
        pre = _detect_duplicate_claimable_keys(_as_added(DISCOVER_RESOLVERS_PREFIX))
        post = _detect_duplicate_claimable_keys(_as_added(DISCOVER_RESOLVERS_POSTFIX))
        assert len(pre) == 1 and post == []


# =============================================================================
# Case (b) — D2 flags the real merge_resolver_edges() pre-fix defect
# =============================================================================


class TestMergeEdgesDiscardWithoutReportRegression:
    """D2 pins finding 3e04a8: merge-side drops with no notes[] report path."""

    def test_prefix_is_flagged(self):
        out = _detect_discard_without_report(_as_added(MERGE_EDGES_PREFIX))
        # All three merge-side drops (malformed / self-edge / unknown endpoint)
        # are bare ``continue`` branches with no note — three silent-drop entries.
        assert len(out) == 3, f'expected the three unreported drops, got {out}'
        assert {e['channel'] for e in out} == {'notes'}
        assert {e['discard'] for e in out} == {'continue'}

    def test_postfix_is_silent(self):
        # The shipped fix appends a ``merge:`` note in each branch before the
        # ``continue`` — no branch is bare, so nothing surfaces.
        out = _detect_discard_without_report(_as_added(MERGE_EDGES_POSTFIX))
        assert out == [], f'post-fix must be silent, got {out}'

    def test_prefix_positive_and_postfix_negative_over_same_shape(self):
        pre = _detect_discard_without_report(_as_added(MERGE_EDGES_PREFIX))
        post = _detect_discard_without_report(_as_added(MERGE_EDGES_POSTFIX))
        assert len(pre) == 3 and post == []


# =============================================================================
# Cross-class separation — each defect is its OWN class, never the other's
# =============================================================================


class TestDefectClassSeparation:
    """The two shapes are disjoint: D1 owns the discover defect, D2 the merge one."""

    def test_d2_silent_on_discover_prefix(self):
        # discover_derivation_resolvers owns no report channel, so the
        # discard-without-report class never fires on it.
        assert _detect_discard_without_report(_as_added(DISCOVER_RESOLVERS_PREFIX)) == []

    def test_d1_silent_on_merge_prefix(self):
        # merge_resolver_edges validates nothing about resolver_id as an identity
        # (``record.get('id', '')`` with no ``if not`` guard), so the
        # duplicate-claimable-key class never fires on its reports.append.
        assert _detect_duplicate_claimable_keys(_as_added(MERGE_EDGES_PREFIX)) == []
