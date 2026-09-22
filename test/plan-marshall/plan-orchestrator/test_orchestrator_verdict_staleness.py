#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression for content-scoped re-grounding verdict staleness.

`test_orchestrator_corpus.py` pins the derivation at two seams with both git
calls stubbed: the PURE classifier over its five reachable basis values, and the
payload disclosure over a synthetic row distribution. This module exercises the
same public seam (`cmd_corpus_verdicts`) against a REAL temporary git repository
carrying a REAL staged spec corpus, so the git plumbing, the `epic_spec_parser`
resolution and the payload assembly are exercised TOGETHER rather than stubbed —
a verification scope no stubbed control reaches, and one that would still have
passed had the stub agreed with a seam the production path never calls.

The motivating case is the first test below and it is a regression in the strict
sense: it fails against the retired `head.startswith(checked_at)` derivation.
Since the orchestrator ledger became git-tracked, a sibling epic's
`.plan/orchestrator/**` commit advances HEAD continuously, so that expression
reported `stale: true` for every row in the corpus and the flag discriminated
nothing. Here that exact commit is landed for real and the untouched declared
surface must come back `stale: false`.

Coverage, one arm per reachable basis:

- **`declared_surface_unchanged`** — the motivating case, plus the matched
  positive control that lands the same advance while touching a declared path.
- **`declared_surface_touched`** — asserted with the matched path named as
  evidence on the row, so the stale reading is substantiated rather than claimed,
  and once more through a DIRECTORY declaration so containment matching is proven
  against a real diff rather than only against a synthetic path list.
- **`surface_not_declarative`** — the fail-closed arm, driven over the three
  non-`declarative` derivation statuses a verdict row can actually carry
  (`derived`, `prose`, `absent`), each paired against the `declarative` control
  in the same payload. The fourth non-`declarative` status, `unreadable`, is
  **structurally unreachable at row level** — an unreadable spec is reported in
  `unreadable[]` and contributes no row at all — and that is asserted here
  explicitly rather than left as a silent gap in the population; the classifier's
  own `unreadable` arm is covered in `test_orchestrator_corpus.py`, which
  parametrizes over the whole declared indeterminate set.
- **`tree_diff_unavailable`** — an anchor sha git can no longer resolve, proving
  the failed command is read as *not compared* rather than as an empty difference.
- **`head_unchanged`** — the anchor stamped AT the live HEAD.

Every arm additionally asserts the admission outcome, pinning that `stale` stayed
reported-only: `_admits` reads neither field, so no arm may move `admits` or
`blocking_count`.

Each arrangement is guarded for non-vacuity through `corpus surfaces`: a fixture
whose declared surface silently failed to resolve would make every
`surface_not_declarative` assertion below pass for the wrong reason, and the same
guard is what proves the `declarative` arms really are declarative.
"""

import argparse
import copy
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from file_ops import cwd_checkout_root

from conftest import load_script_module, parse_ns

#: The orchestrator script's address, as module-level string constants so every
#: ``parse_ns`` call below stays statically resolvable. The module is registered
#: under the same explicit name its sibling suites use, so this file joins that
#: one registration rather than publishing a second one for the same source.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script')

cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
cmd_corpus_surfaces = _orch.cmd_corpus_surfaces

SURFACE_DECLARATIVE = _orch.SURFACE_DECLARATIVE
SURFACE_DERIVED = _orch.SURFACE_DERIVED
SURFACE_PROSE = _orch.SURFACE_PROSE
SURFACE_ABSENT = _orch.SURFACE_ABSENT
SURFACE_UNREADABLE = _orch.SURFACE_UNREADABLE
SURFACE_INDETERMINATE_STATES = _orch.SURFACE_INDETERMINATE_STATES

STALENESS_BASES = _orch.STALENESS_BASES
STALENESS_HEAD_UNCHANGED = _orch.STALENESS_HEAD_UNCHANGED
STALENESS_SURFACE_UNCHANGED = _orch.STALENESS_SURFACE_UNCHANGED
STALENESS_SURFACE_TOUCHED = _orch.STALENESS_SURFACE_TOUCHED
STALENESS_SURFACE_NOT_DECLARATIVE = _orch.STALENESS_SURFACE_NOT_DECLARATIVE
STALENESS_DIFF_UNAVAILABLE = _orch.STALENESS_DIFF_UNAVAILABLE

SLUG = 'fixture-staleness-epic'
PRODUCER = f'{SLUG}/cleanup'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: A path the fixture repository really carries and the declarative spec really
#: declares, and one it carries but never declares — so every negative control is
#: a non-empty difference that simply misses the declaration, never an empty one.
DECLARED_FILE = 'src/module.py'
UNDECLARED_FILE = 'docs/notes.md'

#: The directory containing :data:`DECLARED_FILE`, declared as a directory entry
#: so containment matching is exercised against a real tree difference.
DECLARED_DIRECTORY = 'src/'

#: A syntactically valid anchor that names no object in the fixture repository.
#: Forty lowercase hex characters, so it passes the verdict grammar and is
#: refused by git rather than by the parser — which is the path under test.
UNRESOLVABLE_SHA = '0' * 40

#: The directory ``file_ops.cwd_checkout_root`` recognises a checkout root by.
#: Written relative so it composes onto the fixture repository, and kept as a
#: named constant because the fixture creates it for a reason the bare literal
#: does not carry — see :func:`epic_repo`.
LOCAL_STATE_MARKER = '.plan/local'


# =============================================================================
# Parser-derived argument namespaces
# =============================================================================
#
# Both hoisted namespaces are built by the orchestrator's OWN parser, so each
# carries every default the production CLI applies rather than only the fields a
# test author remembered. ``parse_ns`` re-executes the script module on every
# call, so they live at module scope and the per-call builder derives from the
# base through :func:`_variant` instead of parsing again. ``register=False`` so
# neither can displace the explicitly-named registration above.


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base."""
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_VERDICTS_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'corpus',
    'verdicts',
    '--slug',
    SLUG,
    register=False,
)

_SURFACES_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'corpus',
    'surfaces',
    '--slug',
    SLUG,
    register=False,
)

_SET_VERDICT_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'corpus',
    'set-verdict',
    '--slug',
    SLUG,
    '--plan',
    'PLAN-01',
    '--claim-index',
    '0',
    '--verdict',
    'corroborated',
    '--checked-at',
    'abc1234',
    '--by',
    PRODUCER,
    '--rescoped',
    'n/a',
    '--evidence',
    'held at this sha',
    register=False,
)


# =============================================================================
# Real-repository fixture
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _commit_all(repo: Path, message: str) -> str:
    """Stage the whole tree and commit it, returning the new HEAD sha."""
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '--quiet', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def epic_repo(tmp_path: Path, monkeypatch) -> Path:
    """A real git repository whose orchestrator store lives inside it.

    The store is placed under the repository's own ``.plan/`` (via
    ``PLAN_BASE_DIR``, the isolation seam ``file_ops.get_base_dir`` honours) for
    one load-bearing reason: the motivating scenario is a commit touching
    ``.plan/orchestrator/**`` and nothing else, and that commit can only be REAL
    if the ledger is tracked by the repository the diff is taken in.

    ``cwd`` is moved into the repository because every git call the derivation
    makes runs there, and because the declared paths resolve against the
    checkout root the cwd sits in.

    :data:`LOCAL_STATE_MARKER` is created for that second reason and is NOT
    incidental scaffolding. ``file_ops.cwd_checkout_root`` — the resolver both
    ``corpus surfaces`` and the verdict row builder resolve the repository root
    through — returns the nearest ancestor of ``cwd`` that carries it, and the
    orchestrator store this fixture builds lives on the git-tracked
    ``.plan/orchestrator/`` tier instead, so the marker is the one thing the tmp
    repository would otherwise lack. Without it the walk continues PAST the
    fixture and terminates at whichever real checkout happens to be an ancestor
    of ``tmp_path`` — which this repository's in-repo pytest basetemp guarantees
    there is one of. Every declared path then resolves against that foreign root,
    ``src/`` does not exist there, and the parser classes the spec ``prose``: the
    non-vacuity guard below fires and every ``declarative`` arm asserts nothing.
    It is an empty directory, so git tracks nothing for it and the ledger-only
    advance the motivating case turns on stays ledger-only.
    """
    if shutil.which('git') is None:
        pytest.skip('git is not available')
    repo = tmp_path / 'repo'
    (repo / 'src').mkdir(parents=True)
    (repo / 'docs').mkdir(parents=True)
    (repo / LOCAL_STATE_MARKER).mkdir(parents=True)
    (repo / 'src' / 'module.py').write_text('VALUE = 1\n', encoding='utf-8')
    (repo / 'docs' / 'notes.md').write_text('seed notes\n', encoding='utf-8')
    _git(repo, 'init', '--quiet')
    _git(repo, 'config', 'user.email', 'test@example.invalid')
    _git(repo, 'config', 'user.name', 'Test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    monkeypatch.setenv('PLAN_BASE_DIR', str(repo / '.plan'))
    monkeypatch.chdir(repo)
    # Fail loudly rather than silently: a future basetemp or cwd change that
    # re-opens the wrong-root path would otherwise surface far downstream as a
    # surface that classes `prose`, and the diagnosis would have to be traced
    # back through the parser a second time.
    assert Path(cwd_checkout_root()).resolve() == repo.resolve(), (
        'the declared surface must resolve against the fixture repository, not against a real checkout above tmp_path'
    )
    _commit_all(repo, 'seed the fixture tree')
    return repo


def _epic_dir(repo: Path) -> Path:
    return repo / '.plan' / 'orchestrator' / SLUG


def _write_status(repo: Path, plan_ids: list) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Staleness Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': [
            {
                'id': plan_id,
                'slug': plan_id.lower(),
                'workstream': 'WS-01',
                'status': 'staged',
                'plan_marshall_plan_id': '',
                'pr': '',
                'landing': '',
            }
            for plan_id in plan_ids
        ],
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(repo) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


#: The one claim every fixture spec carries. Unstamped on disk — the verdict is
#: written through the production emitter so the round trip is real.
_CLAIM = '- HYPOTHESIS: a clause — confirm/refute at `src/module.py` § `f` (verify-at-outline)'


def _surface(*paths: str) -> list:
    """Render an ``## Expected Surface`` body declaring ``paths``."""
    return [f'- OBSERVED: `{path}` — `f`' for path in paths]


#: A surface the single reader classes ``derived`` — it declares itself a
#: function of other plans' surfaces. The token is matched case-sensitively by
#: the reader, which is why it is written in the corpus's uppercase emphasis.
_DERIVED_SURFACE = ['- DERIVED: the union of whatever the sibling plans in this workstream declare']

#: A surface the single reader classes ``prose`` — present, and resolving to no
#: path entry: ``a.py`` carries no ``/`` segment, so no entry is rooted.
_PROSE_SURFACE = ['- OBSERVED: `a.py` — `f`']


def _write_spec(repo: Path, name: str, surface_lines: list | None) -> Path:
    """Write one fixture spec, or one carrying NO ``## Expected Surface`` heading.

    ``surface_lines=None`` omits the heading rather than emptying it — the
    variable the ``absent`` derivation status turns on. A present-but-unresolvable
    section is a different fact and is written by passing
    :data:`_PROSE_SURFACE`.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        'Fixture objective.',
        '',
        '## Claim Labels',
        '',
        _CLAIM,
    ]
    if surface_lines is not None:
        lines += ['', '## Expected Surface', '', *surface_lines]
    path = _epic_dir(repo) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _stamp(plan: str, checked_at: str) -> None:
    """Stamp one verdict through the production emitter, failing loudly on refusal.

    Returns nothing on purpose: the arrangement wants the bullet on disk, and a
    refusal — an out-of-range ordinal, a spec the matcher did not find — would
    otherwise leave every assertion downstream reading a spec with no verdict at
    all, which reports ``count: 0`` rather than a wrong basis.
    """
    result = cmd_corpus_set_verdict(_variant(_SET_VERDICT_ARGS, plan=plan, checked_at=checked_at))
    assert result['status'] == 'success', f'the fixture verdict was refused: {result}'


def _surface_states() -> dict:
    """The derivation status the single reader assigns each fixture spec.

    The non-vacuity guard every arrangement below runs: a declared surface that
    silently failed to resolve would make a ``surface_not_declarative`` assertion
    pass for the wrong reason, and would make a ``declared_surface_unchanged`` one
    unreachable while the test still reported the basis it expected. Takes no
    repository argument — the verb resolves the store through the same
    cwd-relative resolver the derivation under test uses.
    """
    result = cmd_corpus_surfaces(_SURFACES_ARGS)
    assert result['status'] == 'success', result
    return {row['spec']: row['derivation_status'] for row in result['specs']}


def _rows_by_spec(payload: dict) -> dict:
    return {row['spec']: row for row in payload['claims']}


# =============================================================================
# The motivating case and its matched control
# =============================================================================


class TestUnrelatedCommitsLeaveAnUntouchedSurfaceCurrent:
    """The regression: an unrelated advance must not mark an untouched surface stale."""

    SPEC = 'PLAN-01-alpha.md'

    def _arrange(self, repo: Path, surface_lines: list) -> str:
        _write_status(repo, ['PLAN-01'])
        _write_spec(repo, self.SPEC, surface_lines)
        anchor = _git(repo, 'rev-parse', 'HEAD')
        _stamp('PLAN-01', anchor)
        assert _surface_states() == {self.SPEC: SURFACE_DECLARATIVE}, (
            'the fixture surface did not resolve, so this arm would assert nothing'
        )
        return anchor

    def test_a_plan_ledger_only_commit_leaves_the_row_current(self, epic_repo):
        # The motivating scenario, landed for real: the ONLY thing between the
        # anchor and HEAD is the epic ledger itself — the shape a sibling epic's
        # `.plan/orchestrator/**` commit takes. The retired raw-HEAD expression
        # reported `stale: true` here for every row in the corpus.
        anchor = self._arrange(epic_repo, _surface(DECLARED_FILE))
        head = _commit_all(epic_repo, 'stage the epic ledger')
        assert head != anchor, 'HEAD did not actually advance, so the arm is vacuous'
        changed = _git(epic_repo, 'diff', '--name-only', anchor, head).splitlines()
        assert changed and all(path.startswith('.plan/orchestrator/') for path in changed), (
            f'the advance must touch the ledger and nothing else, got {changed}'
        )

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert payload['head_sha'] == head
        assert row['stale'] is False
        assert row['staleness_basis'] == STALENESS_SURFACE_UNCHANGED
        assert row['staleness_matched_paths'] == ''
        assert row['admits'] is True
        assert payload['stale_count'] == 0
        assert payload['blocking_count'] == 0

    def test_a_commit_touching_the_declared_file_is_stale_and_names_its_evidence(self, epic_repo):
        # Matched positive control: the SAME arrangement and the SAME ledger
        # commit, with one declared file additionally changed. Only the CONTENT of
        # the difference differs, so the pair isolates the derivation.
        anchor = self._arrange(epic_repo, _surface(DECLARED_FILE))
        (epic_repo / DECLARED_FILE).write_text('VALUE = 2\n', encoding='utf-8')
        head = _commit_all(epic_repo, 'stage the ledger and edit the declared file')
        changed = _git(epic_repo, 'diff', '--name-only', anchor, head).splitlines()
        assert DECLARED_FILE in changed, 'the declared file must really be in the difference'

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is True
        assert row['staleness_basis'] == STALENESS_SURFACE_TOUCHED
        assert row['staleness_matched_paths'] == DECLARED_FILE, (
            'the row must name the path that substantiates the stale reading'
        )
        assert payload['stale_count'] == 1
        assert row['admits'] is True, 'staleness must not reach the admission outcome'
        assert payload['blocking_count'] == 0

    def test_an_undeclared_file_in_the_same_commit_does_not_make_it_stale(self, epic_repo):
        # The second half of the pair above: the difference is non-empty and the
        # edit is real, it simply misses the declaration. Without this arm the
        # `unchanged` reading is equally consistent with a diff that saw nothing.
        anchor = self._arrange(epic_repo, _surface(DECLARED_FILE))
        (epic_repo / UNDECLARED_FILE).write_text('revised notes\n', encoding='utf-8')
        head = _commit_all(epic_repo, 'stage the ledger and edit an undeclared file')
        changed = _git(epic_repo, 'diff', '--name-only', anchor, head).splitlines()
        assert UNDECLARED_FILE in changed
        assert DECLARED_FILE not in changed

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is False
        assert row['staleness_basis'] == STALENESS_SURFACE_UNCHANGED

    def test_a_directory_declaration_resolves_by_containment(self, epic_repo):
        # A `directory` entry contains everything beneath it. Exercised against a
        # REAL diff rather than a synthetic path list, because the entry has to
        # survive the single reader's resolution before containment can apply.
        self._arrange(epic_repo, _surface(DECLARED_DIRECTORY))
        (epic_repo / DECLARED_FILE).write_text('VALUE = 3\n', encoding='utf-8')
        _commit_all(epic_repo, 'edit a file beneath the declared directory')

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is True
        assert row['staleness_basis'] == STALENESS_SURFACE_TOUCHED
        assert row['staleness_matched_paths'] == DECLARED_FILE
        assert row['admits'] is True

    def test_an_anchor_at_the_live_head_settles_before_any_comparison(self, epic_repo):
        # The anchor names the tree HEAD points at, so no difference exists to
        # compare — the branch decided before the surface or the diff is consulted.
        _write_status(epic_repo, ['PLAN-01'])
        _write_spec(epic_repo, self.SPEC, _surface(DECLARED_FILE))
        head = _commit_all(epic_repo, 'stage the epic ledger')
        _stamp('PLAN-01', head)

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is False
        assert row['staleness_basis'] == STALENESS_HEAD_UNCHANGED
        assert row['admits'] is True


# =============================================================================
# Abbreviated-anchor resolution (PR #1585 review finding 5d8900)
# =============================================================================


class TestAbbreviatedAnchorResolution:
    """``checked_at`` admits a 7-40 hex abbreviation; the caller resolves it to a
    full sha before the classifier ever sees it. A genuine abbreviation of HEAD
    must still settle ``head_unchanged``, and an abbreviation git cannot resolve
    must never fall through to ``head_unchanged`` by a bare prefix accident — it
    must report ``tree_diff_unavailable``, the basis that already means "nothing
    was compared", so no seventh member joins the closed six-value vocabulary.
    """

    SPEC = 'PLAN-01-alpha.md'

    def test_an_abbreviated_anchor_of_head_still_resolves_to_head_unchanged(self, epic_repo):
        _write_status(epic_repo, ['PLAN-01'])
        _write_spec(epic_repo, self.SPEC, _surface(DECLARED_FILE))
        head = _commit_all(epic_repo, 'stage the epic ledger')
        _stamp('PLAN-01', head[:8])

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is False
        assert row['staleness_basis'] == STALENESS_HEAD_UNCHANGED
        assert row['admits'] is True

    def test_an_unresolvable_abbreviation_reports_diff_unavailable_not_head_unchanged(self, epic_repo):
        # A syntactically valid short abbreviation naming no object in the
        # fixture repository — the shape the naive prefix test could have
        # misread as `head_unchanged` had the anchor never been resolved first.
        _write_status(epic_repo, ['PLAN-01'])
        _write_spec(epic_repo, self.SPEC, _surface(DECLARED_FILE))
        _commit_all(epic_repo, 'stage the epic ledger')
        _stamp('PLAN-01', 'abc1234')

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = _rows_by_spec(payload)[self.SPEC]

        assert row['stale'] is True
        assert row['staleness_basis'] == STALENESS_DIFF_UNAVAILABLE
        assert row['admits'] is True


# =============================================================================
# The fail-closed arms
# =============================================================================


#: The non-`declarative` derivation statuses a VERDICT ROW can carry, each with
#: the surface body that produces it. ``unreadable`` is deliberately absent and
#: its absence is asserted, not assumed — see
#: :meth:`TestFailClosedFallback.test_the_arm_population_accounts_for_every_indeterminate_status`.
_FALLBACK_CASES = (
    (SURFACE_DERIVED, _DERIVED_SURFACE),
    (SURFACE_PROSE, _PROSE_SURFACE),
    (SURFACE_ABSENT, None),
)

_FALLBACK_IDS = (SURFACE_DERIVED, SURFACE_PROSE, SURFACE_ABSENT)


class TestFailClosedFallback:
    """A surface that cannot be compared reports stale with the basis that says so."""

    FALLBACK_SPEC = 'PLAN-01-fallback.md'
    CONTROL_SPEC = 'PLAN-02-control.md'

    def _arrange(self, repo: Path, surface_lines: list | None) -> None:
        """One fallback spec and one `declarative` control, in ONE payload.

        The pair is what makes the fail-closed reading attributable to the
        derivation status: on its own, a `stale: true` fallback is equally
        consistent with a derivation that reports every row stale.
        """
        _write_status(repo, ['PLAN-01', 'PLAN-02'])
        _write_spec(repo, self.FALLBACK_SPEC, surface_lines)
        _write_spec(repo, self.CONTROL_SPEC, _surface(DECLARED_FILE))
        anchor = _git(repo, 'rev-parse', 'HEAD')
        _stamp('PLAN-01', anchor)
        _stamp('PLAN-02', anchor)
        _commit_all(repo, 'stage the epic ledger')

    def test_the_arm_population_accounts_for_every_indeterminate_status(self):
        # Derived rather than asserted: the parametrization below covers three of
        # the four non-`declarative` statuses, and the fourth is accounted for by
        # name here rather than quietly missing. `unreadable` cannot reach a
        # verdict row at all — the spec is reported in `unreadable[]` and
        # contributes none — which the sibling test proves on disk.
        covered = {state for state, _ in _FALLBACK_CASES}

        assert len(_FALLBACK_CASES) == len(_FALLBACK_IDS)
        assert covered | {SURFACE_UNREADABLE} == set(SURFACE_INDETERMINATE_STATES), (
            f'{len(SURFACE_INDETERMINATE_STATES)} indeterminate status(es), {len(covered) + 1} accounted for'
        )

    @pytest.mark.parametrize(('expected_status', 'surface_lines'), _FALLBACK_CASES, ids=_FALLBACK_IDS)
    def test_an_uncomparable_surface_is_stale_with_the_named_basis(self, epic_repo, expected_status, surface_lines):
        self._arrange(epic_repo, surface_lines)
        assert _surface_states() == {
            self.FALLBACK_SPEC: expected_status,
            self.CONTROL_SPEC: SURFACE_DECLARATIVE,
        }, 'the fixture surfaces did not resolve to the statuses this arm turns on'

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        rows = _rows_by_spec(payload)

        assert rows[self.FALLBACK_SPEC]['stale'] is True
        assert rows[self.FALLBACK_SPEC]['staleness_basis'] == STALENESS_SURFACE_NOT_DECLARATIVE
        assert rows[self.FALLBACK_SPEC]['staleness_matched_paths'] == ''
        # The matched control: same payload, same advance, comparable surface.
        assert rows[self.CONTROL_SPEC]['stale'] is False
        assert rows[self.CONTROL_SPEC]['staleness_basis'] == STALENESS_SURFACE_UNCHANGED
        assert payload['stale_count'] == 1
        # Staleness stayed reported-only on BOTH rows.
        assert all(row['admits'] for row in payload['claims'])
        assert payload['blocking_count'] == 0

    def test_an_unreadable_spec_contributes_no_row_rather_than_a_fallback_one(self, epic_repo):
        # Why `unreadable` is absent from the parametrization above, pinned on
        # disk: the spec never reaches the row builder, so the state is reported in
        # `unreadable[]` instead of wearing a staleness basis.
        _write_status(epic_repo, ['PLAN-01'])
        broken = _epic_dir(epic_repo) / 'plans' / 'PLAN-01-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe not valid utf-8 \xff')
        _commit_all(epic_repo, 'stage the epic ledger')

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)

        assert payload['unreadable'] == [{'spec': 'PLAN-01-broken.md', 'error': 'unreadable'}]
        assert payload['specs_total'] == 1
        assert payload['specs_scanned'] == 0
        assert payload['count'] == 0
        assert payload['stale_count'] == 0

    def test_an_unresolvable_anchor_is_not_read_as_an_empty_difference(self, epic_repo):
        # git refuses the anchor outright, so nothing was compared. Reading the
        # failed command's empty output as "nothing changed" is the exact
        # conflation the fail-closed basis exists to remove.
        _write_status(epic_repo, ['PLAN-01'])
        _write_spec(epic_repo, 'PLAN-01-alpha.md', _surface(DECLARED_FILE))
        _stamp('PLAN-01', UNRESOLVABLE_SHA)
        _commit_all(epic_repo, 'stage the epic ledger')
        with pytest.raises(subprocess.CalledProcessError):
            _git(epic_repo, 'rev-parse', '--verify', f'{UNRESOLVABLE_SHA}^{{commit}}')

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)
        row = payload['claims'][0]

        assert row['checked_at'] == UNRESOLVABLE_SHA
        assert row['stale'] is True
        assert row['staleness_basis'] == STALENESS_DIFF_UNAVAILABLE
        assert row['staleness_matched_paths'] == ''
        assert row['admits'] is True
        assert payload['blocking_count'] == 0


# =============================================================================
# Payload-level disclosure over the real corpus
# =============================================================================


class TestRealCorpusDisclosure:
    def test_every_row_carries_a_basis_and_the_tally_sums_to_the_population(self, epic_repo):
        # One payload holding two different bases, so the tally is exercised over a
        # real distribution rather than a single-valued one.
        _write_status(epic_repo, ['PLAN-01', 'PLAN-02'])
        _write_spec(epic_repo, 'PLAN-01-alpha.md', _surface(DECLARED_FILE))
        _write_spec(epic_repo, 'PLAN-02-beta.md', _PROSE_SURFACE)
        anchor = _git(epic_repo, 'rev-parse', 'HEAD')
        _stamp('PLAN-01', anchor)
        _stamp('PLAN-02', anchor)
        _commit_all(epic_repo, 'stage the epic ledger')

        payload = cmd_corpus_verdicts(_VERDICTS_ARGS)

        assert payload['count'] == 2, 'the row population did not materialize'
        assert [row['staleness_basis'] for row in payload['staleness_basis_tally']] == list(STALENESS_BASES)
        assert sum(row['count'] for row in payload['staleness_basis_tally']) == payload['count']
        assert {row['staleness_basis'] for row in payload['claims']} == {
            STALENESS_SURFACE_UNCHANGED,
            STALENESS_SURFACE_NOT_DECLARATIVE,
        }
        assert payload['stale_count'] == sum(1 for row in payload['claims'] if row['stale'])
        assert 'ADR-019' in payload['governing_authority']
