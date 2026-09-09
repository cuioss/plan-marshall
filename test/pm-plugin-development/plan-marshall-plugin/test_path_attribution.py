#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-plugin-development Axis-D attributor: the project-local artifact claim.

The plugin-development domain owns the ``.claude`` project-local tree — skills,
commands, and the ``settings.json`` harness config alike. These tests cover:

- **D1** (the claim): ``claim_paths()`` returns the bare-root ``('.claude',
  'pm-plugin-development')`` and the extension opts into ``PathAttributionBase``.
- **D3** (consistency across the whole tree): every path under the REAL ``.claude``
  tree resolves to ``pm-plugin-development`` through the live seam, and a sibling
  sharing the string prefix (``.claudex``) does not. The check ENUMERATES the tree
  and publishes the population size it walked, rather than probing a fixed path list —
  a fixed-list probe would pass against a partially-claimed tree. The population is
  the TRACKED corpus (``git ls-files .claude``), not a live filesystem walk, so the
  published count does not move with ``__pycache__`` or a developer's untracked
  ``settings.local.json``; and it is published through ``record_property``, a channel
  a PASSING run surfaces, rather than asserted back out of the test's own stdout.
- **D4** (not-covered vs covered-no-matches): the seam's ``attributor_count`` residue
  distinguishes "no attributor ran" (an absence of capability) from "N attributors ran
  and none claimed this path" (a real, positive answer) — the coverage contract that
  keeps a ``module: null`` non-vacuous, reused rather than reinvented. Asserted as a
  negative-control pair.

``.claude/**`` is a dotfile tree the crawl never inventories, so the Axis-D seam is the
SOLE resolution route for it; ``project_local_module_for_path`` IS that route (rung 3 of
``which-module``), which is why these tests drive it directly. The end-to-end
``which-module`` reader is pinned in
``test/plan-marshall/manage-architecture/test_which_module_plan_claim.py``.

See ``plan-marshall:extension-api/standards/ext-point-path-attribution.md`` for the contract.
"""

import subprocess

from extension_base import ExtensionBase, PathAttributionBase

from conftest import PROJECT_ROOT, load_script_module, load_skill_module


def _load_pm_plugin_dev_extension():
    """Load the pm-plugin-development Extension by ``(bundle, skill, file)`` identity.

    Every bundle shares the ``extension`` basename, so a bare import would collide;
    the pm-documents attributor test loads its Extension the same way.
    """
    return load_skill_module('pm-plugin-development', 'plan-marshall-plugin', 'extension.py', 'pm_plugin_dev_extension')


Extension = _load_pm_plugin_dev_extension().Extension

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)

project_local_module_for_path = _architecture_core.project_local_module_for_path

#: The module name pm-plugin-development's attributor claims.
_PM_PLUGIN_DEV = 'pm-plugin-development'

#: A known-module set that CONTAINS ``pm-plugin-development`` so the live merge keeps
#: the ``.claude`` claim (the module-existence guard admits it). ``plan-marshall`` is
#: included so the ``.plan`` sibling claim survives alongside it.
_KNOWN_WITH_PM = [_PM_PLUGIN_DEV, 'plan-marshall']


def _seam():
    """The raw ``(discover, merge, lookup)`` triple — no process-lifetime memo."""
    return _architecture_core._load_path_attribution_seam()


# --------------------------------------------------------------------------- #
# D1 — the claim, at the attributor
# --------------------------------------------------------------------------- #


def test_extension_opts_into_path_attribution():
    ext = Extension()
    assert isinstance(ext, ExtensionBase)
    assert isinstance(ext, PathAttributionBase)


def test_attributor_id():
    assert Extension().path_attributor_id() == _PM_PLUGIN_DEV


def test_claims_the_bare_claude_root():
    claims, notes = Extension().claim_paths()
    assert claims == [('.claude', _PM_PLUGIN_DEV)]
    assert notes == []


# --------------------------------------------------------------------------- #
# D3 — consistency across the whole REAL .claude tree, by enumeration
# --------------------------------------------------------------------------- #


def _tracked_claude_paths() -> list[str]:
    """Return the repo-relative ``.claude`` paths git TRACKS, sorted.

    The population is taken from the index rather than from a live
    ``rglob``/``iterdir`` over the working tree. A filesystem walk also picks up
    ``__pycache__`` directories and a developer's untracked
    ``.claude/settings.local.json``, so the count it publishes moves with local
    state that has nothing to do with the claim under test — and two runs on the
    same commit legitimately disagree. The tracked corpus is the same set on every
    checkout of a given commit.

    No assertion weakens as a result: every entry the walk would have added is a
    ``.claude`` path, which resolves through the same claim as every tracked one.
    """
    result = subprocess.run(
        ['git', 'ls-files', '.claude'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line.strip())


def test_every_path_under_the_real_claude_tree_resolves_to_pm_plugin_development(record_property):
    """Walk the tracked ``.claude`` corpus; every file resolves to the one owner.

    This ENUMERATES the population rather than sampling a fixed probe list. A check
    that probed ``.claude/skills/x`` and ``.claude/commands/y`` would pass against a
    partially-claimed tree, so the assertion that bites walks every path the tree
    actually holds and PUBLISHES the count it walked (D3's "publishes its count").

    The count is published through ``record_property``. The previous form printed it
    and then asserted its own ``print`` back out of ``capsys``, with ``len(files)``
    interpolated on BOTH sides of the comparison — an oracle derived from its own
    subject, which cannot fail while the ``print`` is present and says nothing about
    the claim. ``record_property`` also survives a passing run, which a bare ``print``
    does not: ``capsys.readouterr()`` drains the buffer, so even ``-s`` showed nothing.
    """
    tracked = _tracked_claude_paths()

    # A zero-path corpus would pass vacuously — assert the population is real first.
    assert tracked, 'git ls-files .claude returned no tracked paths'

    mismatches = []
    for rel in tracked:
        owner = project_local_module_for_path(rel, _KNOWN_WITH_PM)
        if owner != _PM_PLUGIN_DEV:
            mismatches.append((rel, owner))

    assert not mismatches, f'paths under .claude not owned by {_PM_PLUGIN_DEV}: {mismatches}'
    # Publish the population the enumeration actually covered.
    record_property('claude_tracked_paths_walked', len(tracked))
    record_property('claude_tree_owner', _PM_PLUGIN_DEV)


def test_each_top_level_claude_subtree_resolves_uniformly():
    """The founding inconsistency is closed: skills AND commands AND settings agree.

    The problem was that ``.claude/skills`` resolved to a module while its sibling
    ``.claude/commands`` resolved to ``null`` — one tree, two answers. Assert every
    top-level entry now resolves to the SAME owner, derived from the filesystem
    rather than a fixed list.
    """
    claude_root = PROJECT_ROOT / '.claude'
    entries = sorted(claude_root.iterdir())
    assert entries, f'no entries under {claude_root}'
    for entry in entries:
        rel = entry.relative_to(PROJECT_ROOT).as_posix()
        # A directory resolves via a representative nested path; a file resolves directly.
        probe = f'{rel}/probe' if entry.is_dir() else rel
        assert project_local_module_for_path(probe, _KNOWN_WITH_PM) == _PM_PLUGIN_DEV, probe


def test_claim_does_not_leak_past_the_claude_prefix():
    """``.claudex`` shares the leading characters but does not nest inside ``.claude``."""
    assert project_local_module_for_path('.claudex/thing', _KNOWN_WITH_PM) is None


def test_claim_is_inert_without_the_pm_plugin_development_module():
    """The module-existence guard drops the claim in a project lacking the module.

    A consumer project has no ``pm-plugin-development`` module, so the claim naming it
    is filtered out and every ``.claude`` path answers ``null`` there — exactly as
    ``plan-marshall``'s former ``.claude/skills`` claim was already dropped, so no
    consumer-project behaviour changes.
    """
    assert project_local_module_for_path('.claude/skills/x', ['plan-marshall']) is None


# --------------------------------------------------------------------------- #
# D4 — not-covered vs covered-no-matches (the negative control)
# --------------------------------------------------------------------------- #


def test_uncovered_path_differs_from_covered_no_matches():
    """Negative control: an uncovered path (no attributor ran) is a DIFFERENT result
    from a covered-but-unclaimed path (N attributors ran, none claimed).

    Both answer ``module: null``; the ``attributor_count`` residue is what tells them
    apart — the same coverage contract Tier 1's ``resolver_count`` and the content
    reader's ``files_scanned`` carry (reused here, not reinvented). Without the count,
    a caller cannot distinguish "the index looked and found no owner" from "the index
    does not cover this path", and falls back to a whole-tree scan on a real answer.
    """
    discover, merge, lookup = _seam()

    # An unclaimed path: ``.github`` is a dotfile tree the crawl never inventories and
    # no attributor claims, so it is owned by nobody either way.
    unclaimed = '.github/workflows/verify.yml'

    # Covered, no matches: the live attributors ran; none owns ``.github``.
    covered_claims, covered_reports = merge(discover(), _KNOWN_WITH_PM)
    assert lookup(unclaimed, covered_claims) is None
    assert len(covered_reports) > 0  # attributor_count: N — the capability ran

    # Not covered: zero attributors, so nothing looked at all.
    not_covered_claims, not_covered_reports = merge([], _KNOWN_WITH_PM)
    assert lookup(unclaimed, not_covered_claims) is None
    assert not_covered_reports == []  # attributor_count: 0 — absence of capability

    # The pair is the point: identical ``module: null``, DIFFERENT attributor_count.
    assert len(covered_reports) != len(not_covered_reports)


def test_covered_and_claimed_path_still_resolves_under_the_same_seam():
    """The positive control alongside the negatives: a ``.claude`` path DOES resolve.

    Distinguishing "not covered" from "covered, no matches" is necessary but not
    sufficient — the claim itself must land. A ``.claude`` path resolves to
    ``pm-plugin-development`` while the ``.github`` sibling stays ``null``, through the
    one seam, so the three outcomes (owned / covered-unowned / uncovered) are all
    distinguishable.
    """
    discover, merge, lookup = _seam()
    claims, reports = merge(discover(), _KNOWN_WITH_PM)
    assert lookup('.claude/commands/foo.md', claims) == _PM_PLUGIN_DEV
    assert lookup('.github/workflows/verify.yml', claims) is None
    assert len(reports) > 0
