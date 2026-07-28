#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression pinning the PR #1013 unreachable-guard defect.

This module is deliberately NOT a second copy of the ``_detect_scan_derived_keys``
unit cases (those live in ``test_self_review.py``). It exercises the **composed
surface path** — the real ``self_review.py surface`` subcommand over a git
fixture — and pins the historical defect that motivated the check:

* **Case (a)** — the #1013 pre-fix *scanning* form of ``_split_bundle_version``,
  together with the ``_check_emitted_path_provenance`` guard it feeds, IS
  surfaced as a ``scan_derived_keys`` candidate. The same case asserts the
  complementary negative as a REAL assertion (never a docstring claim): **none**
  of the eighteen pre-existing candidate lists surfaces it. Without that half,
  a green case (a) would not distinguish "the new check closes the gap" from
  "a sibling detector happened to flag the same hunk anyway".
* **Case (b)** — the shipped post-fix *anchored* form surfaces NO
  ``scan_derived_keys`` candidate, so the fix produces no false positive.
* **The reachability argument, executed.** Both forms are reproduced verbatim
  from ``standards/unreachable-guard-detection.md`` § 4 and run against the two
  real inputs on which the scanning form mis-splits — a bundle whose own name
  begins with ``N.N`` (``1.0-my-bundle``) and a version-shaped ANCESTOR
  directory above the cache root. The pre-fix form collapses both to a single
  key, which is what makes the guard's ``len(versions) > 1`` refusal
  unsatisfiable; the post-fix form discriminates, which restores it. This turns
  the gate document's reachability argument into an executed check rather than
  a prose claim.

Gate provenance: ``standards/unreachable-guard-detection.md`` selected framing
(b), predicate-over-parsed-structure. The honest-fallback branch was NOT taken,
so the cases below assert real surfacing behaviour rather than a
human-attention fallback.
"""

import re  # noqa: I001
import subprocess
from pathlib import Path

from conftest import get_script_path, run_script

# =============================================================================
# The #1013 forms, verbatim from standards/unreachable-guard-detection.md § 4
# =============================================================================

#: The version-directory pattern #1013 added. Reproduced verbatim from § 2(c).
_VERSION_DIR_NAME_RE = re.compile(r'^\d+\.\d+')


def _split_bundle_version_pre_fix(path: str) -> tuple[str, str] | None:
    """The pre-fix SCANNING form (§ 4 "Pre-fix form (scanning)"), verbatim."""
    parts = Path(path).parts
    for index, part in enumerate(parts):
        if index > 0 and _VERSION_DIR_NAME_RE.match(part):
            return parts[index - 1], part
    return None


def _split_bundle_version_post_fix(path: str, base_path: Path) -> tuple[str, str] | None:
    """The post-fix ANCHORED form (§ 4 "Post-fix form (anchored)"), verbatim body."""
    try:
        relative = Path(path).resolve().relative_to(Path(base_path).resolve())
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 2 or not _VERSION_DIR_NAME_RE.match(parts[1]):
        return None
    return parts[0], parts[1]


def _guard_refuses(splits: list[tuple[str, str] | None]) -> bool:
    """Guard 4's refusal predicate (§ 4 "The reachability argument"), verbatim shape."""
    by_bundle: dict[str, set[str]] = {}
    for split in splits:
        if split is None:
            continue
        bundle, version = split
        by_bundle.setdefault(bundle, set()).add(version)
    return any(len(versions) > 1 for versions in by_bundle.values())


# =============================================================================
# The two discriminating inputs (§ 4 "The reachability argument")
# =============================================================================

#: A bundle whose OWN directory name begins with ``N.N`` — the supported naming
#: convention ``find_bundles`` documents as ``1.0-my-bundle``.
_BUNDLE_NAME_CACHE_ROOT = Path('/srv/cache')
_BUNDLE_NAME_PATHS = (
    '/srv/cache/1.0-my-bundle/0.1.100/skills/a/SKILL.md',
    '/srv/cache/1.0-my-bundle/0.1.200/skills/b/SKILL.md',
)

#: A version-shaped ANCESTOR directory sitting ABOVE the cache root.
_ANCESTOR_CACHE_ROOT = Path('/srv/1.0-workspace/cache')
_ANCESTOR_PATHS = (
    '/srv/1.0-workspace/cache/plain-bundle/0.1.100/skills/a/SKILL.md',
    '/srv/1.0-workspace/cache/plain-bundle/0.1.200/skills/b/SKILL.md',
)

# =============================================================================
# Candidate-list vocabulary
# =============================================================================

#: The candidate list this plan added. Everything else predates it.
_NEW_LIST = 'scan_derived_keys'

#: The eighteen candidate lists that predate the reachability check. The
#: complementary negative in case (a) sweeps ALL of them, so a sibling detector
#: incidentally flagging the same hunk cannot be mistaken for the new check
#: doing its job.
_PRE_EXISTING_LISTS = (
    'regexes',
    'user_facing_strings',
    'markdown_sections',
    'symmetric_pairs',
    'flag_guard_pairs',
    'contract_sources',
    'schema_bearing_files',
    'keep_markers',
    'protected_identifiers',
    'producer_consumer',
    'source_of_truth',
    'same_document_consistency',
    'description_vs_body',
    'unguarded_boundaries',
    'count_prose',
    'touched_claims',
    'advertised_form_help_strings',
    'ordinal_references',
)

# =============================================================================
# Fixture sources — the diff the surfacer reads
# =============================================================================

#: Committed in the BASE commit, so the compiled pattern is OUT of the surfaced
#: diff. Keeping it out is load-bearing: an added ``re.compile`` literal would
#: be surfaced by the pre-existing ``regexes`` list and would contaminate the
#: complementary negative below.
_PATTERNS_MODULE = "import re\n\n_VERSION_DIR_NAME_RE = re.compile(r'^\\d+\\.\\d+')\n"

#: Case (a): the pre-fix scanning derivation plus the guard it feeds. No
#: docstrings, no regex literals, no argparse, no I/O boundary — so any hit on a
#: pre-existing list would be a real hit on this derivation, not fixture noise.
_PRE_FIX_SOURCE = (
    'from pathlib import Path\n'
    '\n'
    'from patterns import _VERSION_DIR_NAME_RE\n'
    '\n'
    '\n'
    'def _split_bundle_version(path):\n'
    '    parts = Path(path).parts\n'
    '    for index, part in enumerate(parts):\n'
    '        if index > 0 and _VERSION_DIR_NAME_RE.match(part):\n'
    '            return parts[index - 1], part\n'
    '    return None\n'
    '\n'
    '\n'
    'def _check_emitted_path_provenance(paths):\n'
    '    by_bundle = {}\n'
    '    for emitted in paths:\n'
    '        split = _split_bundle_version(emitted)\n'
    '        if split is None:\n'
    '            continue\n'
    '        bundle, version = split\n'
    '        by_bundle.setdefault(bundle, set()).add(version)\n'
    '    for bundle, versions in by_bundle.items():\n'
    '        if len(versions) > 1:\n'
    '            return bundle\n'
    '    return None\n'
)

#: Case (b): the shipped anchored derivation, feeding the identical guard.
_POST_FIX_SOURCE = (
    'from pathlib import Path\n'
    '\n'
    'from patterns import _VERSION_DIR_NAME_RE\n'
    '\n'
    '\n'
    'def _split_bundle_version(path, base_path):\n'
    '    try:\n'
    '        relative = Path(path).resolve().relative_to(Path(base_path).resolve())\n'
    '    except ValueError:\n'
    '        return None\n'
    '    parts = relative.parts\n'
    '    if len(parts) < 2 or not _VERSION_DIR_NAME_RE.match(parts[1]):\n'
    '        return None\n'
    '    return parts[0], parts[1]\n'
    '\n'
    '\n'
    'def _check_emitted_path_provenance(paths, base_path):\n'
    '    by_bundle = {}\n'
    '    for emitted in paths:\n'
    '        split = _split_bundle_version(emitted, base_path)\n'
    '        if split is None:\n'
    '            continue\n'
    '        bundle, version = split\n'
    '        by_bundle.setdefault(bundle, set()).add(version)\n'
    '    for bundle, versions in by_bundle.items():\n'
    '        if len(versions) > 1:\n'
    '            return bundle\n'
    '    return None\n'
)


# =============================================================================
# Fixture plumbing
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _fixture_repo(tmp_path: Path, generator_source: str) -> Path:
    """A repo whose feature-branch diff is exactly ``gen.py``.

    The compiled pattern lives in the BASE commit so the surfaced diff carries
    only the derivation under test.
    """
    repo = tmp_path / 'repo'
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')
    (repo / 'patterns.py').write_text(_PATTERNS_MODULE)
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', 'base')
    _git(repo, 'checkout', '-b', 'feature')
    (repo / 'gen.py').write_text(generator_source)
    _git(repo, 'add', 'gen.py')
    return repo


def _surface(repo: Path) -> dict:
    script = get_script_path(
        'pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py'
    )
    result = run_script(
        script,
        'surface',
        '--plan-id',
        'reachability-regression-plan',
        '--project-dir',
        str(repo),
        '--base-branch',
        'main',
    )
    assert result.success, f'surface failed: stderr={result.stderr}'
    data: dict = result.toon()
    return data


def _list_entries(data: dict, key: str) -> list:
    entries = data.get(key) or []
    return list(entries)


# =============================================================================
# Case (a) — the pre-fix scanning form IS surfaced, by the new list ALONE
# =============================================================================


class TestPreFixScanningFormIsSurfaced:
    """Request item D4(a): the #1013 pre-fix form reaches a true positive."""

    def test_pre_fix_form_surfaces_a_scan_derived_key_candidate(self, tmp_path):
        data = _surface(_fixture_repo(tmp_path, _PRE_FIX_SOURCE))

        entries = _list_entries(data, _NEW_LIST)

        assert entries, (
            'The #1013 pre-fix scanning derivation surfaced NO scan_derived_keys '
            'candidate — the check cannot reach a true positive on the very '
            'instance it was selected to catch'
        )
        assert int(data['counts'][_NEW_LIST]) == len(entries)

    def test_surfaced_candidate_names_the_deriving_function_and_sequence(self, tmp_path):
        data = _surface(_fixture_repo(tmp_path, _PRE_FIX_SOURCE))

        named = [e for e in _list_entries(data, _NEW_LIST) if e['name'] == '_split_bundle_version']

        assert len(named) == 1, (
            f'Expected exactly one candidate naming _split_bundle_version. '
            f'Got: {_list_entries(data, _NEW_LIST)}'
        )
        assert named[0]['file'] == 'gen.py'
        assert named[0]['sequence'] == 'parts', (
            'The candidate must name the decomposed sequence the scan iterates'
        )

    def test_guard_in_the_same_diff_sets_key_consumed(self, tmp_path):
        # #1013 shipped the consuming guard in the SAME commit, so the Tier-2
        # identity-consumption flag must resolve true here. (Its false value is
        # a narrowing signal, never a suppression — see the gate doc § 1.)
        data = _surface(_fixture_repo(tmp_path, _PRE_FIX_SOURCE))

        named = [e for e in _list_entries(data, _NEW_LIST) if e['name'] == '_split_bundle_version']
        assert named, 'Candidate not surfaced — the flag assertion would be vacuous'

        # The TOON round-trip may render the boolean as a string, so compare on
        # the normalised rendering rather than on Python identity.
        assert str(named[0]['key_consumed']).lower() == 'true', (
            '_check_emitted_path_provenance groups the derived key with '
            'setdefault and tests len() on the resulting set, so the '
            'identity-consumption flag must resolve true'
        )

    def test_no_pre_existing_candidate_list_surfaces_the_pre_fix_form(self, tmp_path):
        # The complementary negative, as a REAL assertion. If a sibling detector
        # also flagged this hunk, a green case (a) would not attribute the
        # reachability to the new check.
        data = _surface(_fixture_repo(tmp_path, _PRE_FIX_SOURCE))

        populated = {
            key: _list_entries(data, key)
            for key in _PRE_EXISTING_LISTS
            if _list_entries(data, key)
        }

        assert not populated, (
            f'A pre-existing candidate list surfaced the #1013 pre-fix form, so '
            f'case (a) would not attribute the true positive to the new '
            f'reachability check: {populated}'
        )

    def test_pre_existing_list_sweep_covers_every_key_the_surfacer_emits(self, tmp_path):
        # Guards the sweep above against silent under-coverage: a candidate list
        # added later but never added to _PRE_EXISTING_LISTS would slip past the
        # complementary negative unnoticed.
        data = _surface(_fixture_repo(tmp_path, _PRE_FIX_SOURCE))

        emitted = set(data['counts']) - {'total'}
        swept = set(_PRE_EXISTING_LISTS) | {_NEW_LIST}

        assert emitted == swept, (
            f'The candidate-list vocabulary drifted from this regression. '
            f'Emitted but not swept: {sorted(emitted - swept)}. '
            f'Swept but not emitted: {sorted(swept - emitted)}.'
        )


# =============================================================================
# Case (b) — the post-fix anchored form is NOT surfaced
# =============================================================================


class TestPostFixAnchoredFormIsNotSurfaced:
    """Request item D4(b): the shipped fix produces no false positive."""

    def test_post_fix_form_surfaces_no_scan_derived_key_candidate(self, tmp_path):
        data = _surface(_fixture_repo(tmp_path, _POST_FIX_SOURCE))

        assert _list_entries(data, _NEW_LIST) == [], (
            'The shipped anchored derivation was surfaced as a scan-derived-key '
            'candidate — the check fires on the whole shape family instead of '
            'discriminating scan from anchor'
        )
        assert int(data['counts'][_NEW_LIST]) == 0

    def test_post_fix_fixture_is_not_vacuously_clean(self, tmp_path):
        # The anchored fixture keeps the SAME guard, the same decomposition
        # binding (`parts = relative.parts`) and the same compiled-pattern test.
        # Only the scan loop is gone. Without this the negative could pass merely
        # because the fixture lost the shape's other ingredients.
        source = _POST_FIX_SOURCE

        assert 'parts = relative.parts' in source
        assert '_VERSION_DIR_NAME_RE.match(' in source
        assert 'by_bundle.setdefault(bundle, set()).add(version)' in source
        assert 'for index, part in enumerate(parts):' not in source, (
            'The anchored fixture must differ from the scanning fixture in the '
            'scan loop specifically'
        )


# =============================================================================
# The reachability argument, executed against the two discriminating inputs
# =============================================================================


class TestGuardReachabilityOnTheDiscriminatingInputs:
    """The gate document's reachability argument, run rather than asserted in prose."""

    def test_pre_fix_collapses_a_bundle_whose_name_starts_with_a_version(self):
        splits = [_split_bundle_version_pre_fix(p) for p in _BUNDLE_NAME_PATHS]

        # Every path under `1.0-my-bundle` stops the scan at the bundle name
        # itself, so both paths yield the identical key.
        assert splits[0] == splits[1], (
            f'Expected the scanning form to collapse both paths to one key. '
            f'Got: {splits}'
        )
        assert not _guard_refuses(splits), (
            "Guard 4's refusal must be unsatisfiable under the pre-fix form — "
            'that unreachability IS the #1013 defect'
        )

    def test_pre_fix_collapses_a_version_shaped_ancestor_directory(self):
        splits = [_split_bundle_version_pre_fix(p) for p in _ANCESTOR_PATHS]

        assert splits[0] == splits[1], (
            f'Expected the scanning form to collapse on the version-shaped '
            f'ancestor directory. Got: {splits}'
        )
        assert not _guard_refuses(splits)

    def test_post_fix_discriminates_the_bundle_name_input(self):
        splits = [
            _split_bundle_version_post_fix(p, _BUNDLE_NAME_CACHE_ROOT)
            for p in _BUNDLE_NAME_PATHS
        ]

        assert splits == [('1.0-my-bundle', '0.1.100'), ('1.0-my-bundle', '0.1.200')]
        assert _guard_refuses(splits), (
            'The anchored form must make the refusal reachable again — two paths '
            'under one bundle now genuinely disagree on the version dir'
        )

    def test_post_fix_discriminates_the_ancestor_directory_input(self):
        splits = [
            _split_bundle_version_post_fix(p, _ANCESTOR_CACHE_ROOT) for p in _ANCESTOR_PATHS
        ]

        assert splits == [('plain-bundle', '0.1.100'), ('plain-bundle', '0.1.200')]
        assert _guard_refuses(splits)

    def test_post_fix_returns_none_outside_the_cache_root(self):
        # The anchored form's documented None cases: a path outside base_path,
        # and a bundle segment carrying no version dir.
        assert (
            _split_bundle_version_post_fix('/elsewhere/a/b/c.md', _BUNDLE_NAME_CACHE_ROOT)
            is None
        )
        assert (
            _split_bundle_version_post_fix(
                '/srv/cache/plain-bundle/skills/a.md', _BUNDLE_NAME_CACHE_ROOT
            )
            is None
        )
