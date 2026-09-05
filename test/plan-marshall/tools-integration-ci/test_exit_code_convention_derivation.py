#!/usr/bin/env python3
# ruff: noqa: I001, E402
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the exit-code-convention derivation helper.

Every case here drives fixture documents written to ``tmp_path`` rather than the
live tree. That separation is deliberate: this module pins the helper's
*discrimination logic* — which documents it retains and how it classifies them —
while the population guard beside it asserts over the real derived set. A unit
test written against the live tree would fail for two unrelated reasons at once
and could not tell them apart.

Each fixture exhibits exactly one property under test, so a failure names the
branch that broke rather than a document that happens to combine several.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HELPER_DIR = Path(__file__).resolve().parent
if str(_HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(_HELPER_DIR))

import _exit_code_convention_derivation as derivation  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture fragments — each is one property, composed into documents below
# ---------------------------------------------------------------------------

#: A convention that reaches every notation AND carries the exit-zero clause.
WIDENED_CONVENTION = """\
## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation,
**not only `manage-*`** — carries the following contract.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON.
  A zero exit is not evidence the operation succeeded.
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


def test_fenced_invocation_is_retained(tmp_path):
    """An executable `ci` invocation inside a fenced block enters the population."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == {'marketplace/bundles/b/skills/s/SKILL.md'}, (
        f'A fenced `ci` invocation was not retained. Population: {result.population_size}, '
        f'coverage: scanned={result.coverage.files_scanned}, unreadable={result.coverage.unreadable}.'
    )


def test_bare_prose_mention_is_not_retained(tmp_path):
    """The same notation named in prose is a mention, not an invocation.

    The matched positive control is :func:`test_fenced_invocation_is_retained`:
    the notation is identical in both, so the only difference driving the
    outcome is whether it sits inside a fenced command block.
    """
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_PROSE_MENTION)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == set(), (
        f'A bare prose mention of a `ci` notation was retained as an invocation: '
        f'{sorted(_all_paths(result))}. Only fenced command lines invoke.'
    )
    assert result.coverage.files_scanned == 1, (
        'The document was not scanned at all, so the empty population above says nothing '
        'about the prose-vs-invocation discrimination.'
    )


def test_backslash_continued_invocation_is_read_as_one_call(tmp_path):
    """A notation on a continuation line still belongs to the executor call."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_INVOCATION_CONTINUED)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == {'marketplace/bundles/b/skills/s/SKILL.md'}, (
        'A backslash-continued invocation was not read as one call, so the notation on the '
        'continuation line was missed and the document was dropped.'
    )


def test_notation_quoted_in_another_calls_argument_is_not_an_invocation(tmp_path):
    """A `ci` notation quoted inside a `manage-*` call's `--message` does not retain.

    The notation is the executor's first positional; anything later on the line
    is an argument. Reading any notation-shaped token would retain this document
    on a log message, which is a mention.
    """
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', MANAGE_ONLY_INVOCATION_QUOTING_CI)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == set(), (
        f'A `ci` notation quoted inside a manage-* call argument retained the document: '
        f'{sorted(_all_paths(result))}. Only the executor first positional is an invocation.'
    )


def test_manage_only_document_is_dropped_by_retention_rule_c(tmp_path):
    """A document invoking only `manage-*` skills never enters the population."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', MANAGE_ONLY_INVOCATION)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == set(), (
        f'A manage-*-only document was retained: {sorted(_all_paths(result))}. Rule (c) retains '
        'only documents invoking at least one non-manage-* skill segment.'
    )
    assert result.coverage.files_scanned == 1, (
        'The document was not scanned, so the empty population is unmeasured rather than a '
        'measured drop by rule (c).'
    )


def test_retention_needs_only_one_non_manage_notation(tmp_path):
    """A document mixing `manage-*` and `ci` calls is retained on the `ci` one."""
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', MANAGE_ONLY_INVOCATION, CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert _all_paths(result) == {'marketplace/bundles/b/skills/s/SKILL.md'}, (
        'A document invoking both manage-* and ci was dropped; rule (c) requires only one '
        'non-manage-* notation.'
    )


# ---------------------------------------------------------------------------
# Classification — the three outcomes, each from a document exhibiting it
# ---------------------------------------------------------------------------


def test_document_with_widened_convention_classifies_widened(tmp_path):
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', WIDENED_CONVENTION, CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert result.widened == ('marketplace/bundles/b/skills/s/SKILL.md',), (
        f'A convention reaching every notation and carrying the exit-zero clause was not '
        f'classified widened. narrow={result.narrow}, none={result.none}.'
    )


def test_document_with_manage_scoped_convention_classifies_narrow(tmp_path):
    """A `manage-*`-scoped convention is `narrow` even though it states the exit-zero rule.

    This is the discrimination the whole plan turns on: the clause is present but
    the scope does not reach the `ci` call the same document issues.
    """
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', NARROW_CONVENTION, CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert result.narrow == ('marketplace/bundles/b/skills/s/SKILL.md',), (
        f'A manage-*-scoped convention was not classified narrow. widened={result.widened}, '
        f'none={result.none}.'
    )


def test_document_without_convention_heading_classifies_none(tmp_path):
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert result.none == ('marketplace/bundles/b/skills/s/SKILL.md',), (
        f'A document with no exit-code convention heading was not classified none. '
        f'widened={result.widened}, narrow={result.narrow}.'
    )


def test_convention_heading_inside_a_fenced_block_is_not_the_documents_own(tmp_path):
    """A convention quoted inside a code fence is an example, not a heading."""
    fenced_example = '```markdown\n' + WIDENED_CONVENTION + '```\n'
    _write(tmp_path, 'bundles/b/skills/s/SKILL.md', fenced_example, CI_INVOCATION)

    result = derivation.derive(tmp_path)

    assert result.none == ('marketplace/bundles/b/skills/s/SKILL.md',), (
        f'A convention heading shown inside a code fence was read as the document\'s own. '
        f'widened={result.widened}, narrow={result.narrow}.'
    )


def test_the_three_classes_are_disjoint_and_total(tmp_path):
    """Every retained document lands in exactly one class, and they sum to the population."""
    _write(tmp_path, 'bundles/b/skills/w/SKILL.md', WIDENED_CONVENTION, CI_INVOCATION)
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
        'The manage-*-only document must still be scanned — it is dropped by rule (c), not '
        'excluded from coverage.'
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
