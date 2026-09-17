#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""CLI cluster — coverage, body sweep, disjointness."""


from __future__ import annotations

import sys
from pathlib import Path

_HELPER_DIR = Path(__file__).resolve().parent
if str(_HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(_HELPER_DIR))

import _exit_code_convention_derivation_causes as _causes
import _exit_code_convention_derivation_messages as derivation

# ---------------------------------------------------------------------------
# Fixture fragments — each is one property, composed into documents below
# ---------------------------------------------------------------------------

#: The covered form every CONSUMING document carries: a reference to the
#: canonical standard, restating no clause.
XREF_CONVENTION = """\
## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this
document — of EVERY notation, not only `manage-*` — is stated once in
[`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md);
it is not restated here.
"""

#: The covered form the CANONICAL standard carries: the contract stated in full,
#: with a disposition for every exit-code condition.
FULL_CONTRACT_CONVENTION = """\
## Exit-code convention for every script call

- **`exit_code == 0` AND `status: success`**: parse the returned TOON.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable
  `status` at all**: NOT a usable value — STOP.
- **`exit_code != 0`**: STOP.
"""

#: A convention scoped to `manage-*` calls. It carries the exit-zero clause but
#: governs only `manage-*`, which is exactly the gap this plan closes: a `ci`
#: caller reading this document is told nothing.
NARROW_CONVENTION = """\
## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following contract.

- **`exit_code == 0`**: parse the returned TOON. **`exit 0` does NOT imply the
  operation succeeded** — branch on the TOON `status` field.
- **`exit_code != 0`**: STOP.
"""

#: An executable `ci` invocation — a non-`manage-*` skill segment, so a document
#: carrying it is retained by rule (c).
CI_INVOCATION = """\
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view --pr-number 1
```
"""

#: The same `ci` call spread over continuation lines, with the notation itself on
#: a continuation rather than beside the executor token.
CI_INVOCATION_CONTINUED = """\
```bash
python3 .plan/execute-script.py \\
  plan-marshall:tools-integration-ci:ci pr view \\
  --pr-number 1
```
"""

#: The same notation named in prose only. Not fenced, not invoked.
CI_PROSE_MENTION = """\
The `plan-marshall:tools-integration-ci:ci` notation routes provider operations,
and a caller runs it through `python3 .plan/execute-script.py` like any other
script. See the CI skill for the argument surface.
"""

#: A `manage-*` invocation whose `--message` argument quotes a `ci` notation. The
#: quoted notation is a mention inside another call's argument, never an
#: invocation, so this document must not be retained on it.
MANAGE_ONLY_INVOCATION_QUOTING_CI = """\
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging work \\
  --plan-id X --level INFO --message "dispatched plan-marshall:tools-integration-ci:ci"
```
"""

#: A document whose only invocation is a `manage-*` skill.
MANAGE_ONLY_INVOCATION = """\
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \\
  --plan-id X --file references.json
```
"""


def _write(root: Path, relative: str, *parts: str) -> Path:
    """Write a fixture document under ``{root}/marketplace/{relative}``."""
    path = root / 'marketplace' / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Fixture\n\n' + '\n'.join(parts), encoding='utf-8')
    return path


def _all_paths(result: derivation.Derivation) -> set[str]:
    return set(result.widened) | set(result.narrow) | set(result.none)


# ---------------------------------------------------------------------------
# Retention — rule (b) invocation-vs-mention, and rule (c) non-`manage-*`
# ---------------------------------------------------------------------------


def test_the_three_classes_are_disjoint_and_total(tmp_path):
    """Every retained document lands in exactly one class, and they sum to the population."""
    _write(tmp_path, 'bundles/b/skills/w/SKILL.md', XREF_CONVENTION, CI_INVOCATION)
    _write(tmp_path, 'bundles/b/skills/n/SKILL.md', NARROW_CONVENTION, CI_INVOCATION)
    _write(tmp_path, 'bundles/b/skills/x/SKILL.md', CI_INVOCATION)
    _write(tmp_path, 'bundles/b/skills/dropped/SKILL.md', MANAGE_ONLY_INVOCATION)

    result = derivation.derive(tmp_path)

    assert len(result.widened) == 1
    assert len(result.narrow) == 1
    assert len(result.none) == 1
    assert result.population_size == 3, (
        f'population_size {result.population_size} disagrees with the three class sizes '
        f'({len(result.widened)}, {len(result.narrow)}, {len(result.none)}).'
    )
    assert len(_all_paths(result)) == 3, 'A document appears in more than one class.'
    assert result.coverage.files_scanned == 4, (
        'The manage-*-only document must still be scanned — it is dropped by rule (c), not excluded from coverage.'
    )


# ---------------------------------------------------------------------------
# Coverage — an unreadable file is named, never silently dropped
# ---------------------------------------------------------------------------


def test_unreadable_file_is_reported_rather_than_shrinking_the_population(tmp_path):
    """A file that cannot be decoded is named in coverage and excluded from the scan count."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_INVOCATION)
    undecodable = tmp_path / 'marketplace' / 'bundles' / 'b' / 'skills' / 's' / 'broken.md'
    undecodable.write_bytes(b'\xff\xfe not valid utf-8 \xff')

    result = derivation.derive(tmp_path)

    assert result.coverage.unreadable == ('marketplace/bundles/b/skills/s/broken.md',), (
        f'An undecodable document was not reported as unreadable: {result.coverage.unreadable}. '
        'It would instead have shrunk the population behind a clean-looking result.'
    )
    assert result.coverage.files_scanned == 1, (
        f'files_scanned {result.coverage.files_scanned} counts a file that could not be read.'
    )
    assert result.coverage.complete is False, (
        'Coverage reports complete despite an unreadable file, so an empty class from this walk '
        'would read as a measurement rather than a gap.'
    )


def test_coverage_is_complete_when_every_file_was_read(tmp_path):
    """Matched control: with nothing unreadable, coverage reports complete."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert result.coverage.unreadable == ()
    assert result.coverage.complete is True, (
        'Coverage reports incomplete on a fully readable tree, which would make every real '
        'derivation look like a coverage gap.'
    )


def test_empty_tree_is_not_reported_as_complete_coverage(tmp_path):
    """A walk that scanned nothing is a gap, not a clean empty population."""
    (tmp_path / 'marketplace').mkdir()

    result = derivation.derive(tmp_path)

    assert result.population_size == 0
    assert result.coverage.files_scanned == 0
    assert result.coverage.complete is False, (
        'A tree with no documents at all reported complete coverage, so a derivation pointed at '
        'the wrong root would pass vacuously.'
    )


# ---------------------------------------------------------------------------
# Body sweep — the contract is stated in exactly one place
# ---------------------------------------------------------------------------


def test_body_sweep_detects_a_reintroduced_verbatim_copy(tmp_path):
    """A second full statement is reported, which is what makes the guard bite.

    The matched negative control for the test above: the tree differs only in
    that one referencing document was replaced by a verbatim copy.
    """
    _write(tmp_path, 'bundles/b/skills/canon/standards/x.md', FULL_CONTRACT_CONVENTION)
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', FULL_CONTRACT_CONVENTION, CI_INVOCATION)

    sweep = derivation.sweep_convention_bodies(tmp_path)

    assert sweep.occurrences == 2, (
        f'A reintroduced verbatim copy was not counted — occurrences={sweep.occurrences}, '
        f'documents={list(sweep.documents)}. The single-body guard would pass on a duplicated tree.'
    )


def test_body_sweep_reports_an_unreadable_file_rather_than_a_clean_single_body(tmp_path):
    """An undecodable document is a file that might hold a second body.

    Without this, a tree with one readable statement and one unreadable file
    would report `occurrences == 1` and read as single-sourced.
    """
    _write(tmp_path, 'bundles/b/skills/canon/standards/x.md', FULL_CONTRACT_CONVENTION)
    undecodable = tmp_path / 'marketplace' / 'bundles' / 'b' / 'skills' / 'canon' / 'standards' / 'broken.md'
    undecodable.write_bytes(b'\xff\xfe not valid utf-8 \xff')

    sweep = derivation.sweep_convention_bodies(tmp_path)

    assert sweep.occurrences == 1
    assert sweep.coverage.unreadable == ('marketplace/bundles/b/skills/canon/standards/broken.md',), (
        f'The undecodable document was not named: {sweep.coverage.unreadable}.'
    )
    assert sweep.coverage.complete is False, (
        'The sweep reports complete coverage despite an unreadable file, so its single-body '
        'result would read as a measurement rather than a gap.'
    )


def test_body_sweep_and_derivation_walk_the_same_documents(tmp_path):
    """Both read one document set, so the count and the population are comparable.

    A sweep over a narrower walk could report a clean single body for a tree the
    population guard covered more of — the two numbers would then describe
    different trees while being published side by side.
    """
    _write(tmp_path, 'bundles/b/skills/canon/standards/x.md', FULL_CONTRACT_CONVENTION)
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', XREF_CONVENTION, CI_INVOCATION)
    _write(tmp_path, 'bundles/b/skills/dropped/SKILL.md', MANAGE_ONLY_INVOCATION)

    sweep = derivation.sweep_convention_bodies(tmp_path)
    result = derivation.derive(tmp_path)

    assert sweep.coverage.files_scanned == result.coverage.files_scanned, (
        f'The sweep scanned {sweep.coverage.files_scanned} documents and the derivation '
        f'{result.coverage.files_scanned} — the two describe different trees.'
    )
