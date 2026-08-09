# SPDX-License-Identifier: FSL-1.1-ALv2
"""Whole-source-tree guard: the character-set prefix-strip idiom stays retired.

``str.lstrip`` takes a SET OF CHARACTERS, not a prefix. Calling it with ``'./'``
therefore removes EVERY leading ``.`` and ``/`` rather than one exact ``./``
prefix — rewriting ``.claude/x`` into ``claude/x`` and ``../other/x`` into
``other/x``. Each such call silently resolved one in-tree path into a DIFFERENT
in-tree path instead of failing, so the component that got discovered, emitted,
or classified was not the one the descriptor named.

The supported replacement is ``removeprefix('./')`` plus an explicit refusal of
any ``..`` segment. This module is the conformance guard that the idiom does not
come back anywhere under ``marketplace/``.

**The assertion is population-derived.** ``scan_for_retired_idiom`` returns the
offender list AND the number of files it actually read, and the whole-tree test
asserts the population is non-empty BEFORE asserting the offender list is empty.
Without that, a mis-rooted or empty walk would produce an empty offender list
and the guard would pass while having examined nothing — the failure mode where
a green check certifies only its own vacuity.

This file lives under ``test/`` while the scan is rooted at ``marketplace/``, so
the idiom literals below are never matched by the guard itself.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_DIR = PROJECT_ROOT / 'marketplace'

#: Both spellings of the retired idiom. A single-quoted source file and a
#: double-quoted one are the same defect, so scanning for only one spelling
#: would leave half the population unguarded.
RETIRED_IDIOMS = ("lstrip('./')", 'lstrip("./")')

#: Directory names that never hold project-owned source.
EXCLUDED_DIR_NAMES = frozenset(
    {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.venv', 'node_modules'}
)


def scan_for_retired_idiom(root: Path) -> tuple[list[str], int]:
    """Scan project-owned ``.py`` files under ``root`` for the retired idiom.

    Read failures are deliberately NOT swallowed: a file that cannot be read is
    a file that might carry the idiom and was never checked, which is a coverage
    gap rather than a clean result. Letting it raise fails the guard loudly
    instead of shrinking the population behind a green assertion.

    Args:
        root: Directory to walk. A non-existent directory yields an empty
            population, which the caller's population assertion then catches.

    Returns:
        ``(offenders, scanned_count)`` — ``offenders`` are the paths of files
        containing either spelling; ``scanned_count`` is how many files were
        read. The count is returned alongside the list precisely so a caller can
        prove the scan had something to examine.
    """
    offenders: list[str] = []
    scanned = 0
    if not root.is_dir():
        return offenders, scanned

    for path in sorted(root.rglob('*.py')):
        if EXCLUDED_DIR_NAMES.intersection(path.parts):
            continue
        scanned += 1
        content = path.read_text(encoding='utf-8')
        if any(idiom in content for idiom in RETIRED_IDIOMS):
            offenders.append(str(path))

    return offenders, scanned


# ---------------------------------------------------------------------------
# The whole-source-tree conformance assertion
# ---------------------------------------------------------------------------


def test_retired_idiom_has_zero_occurrences_under_marketplace():
    """No file under ``marketplace/`` may use the character-set prefix strip."""
    offenders, scanned = scan_for_retired_idiom(MARKETPLACE_DIR)

    # Population first: an empty offender list is only meaningful once the walk
    # is known to have read something.
    assert scanned > 0, (
        f'Scanned 0 files under {MARKETPLACE_DIR} — the guard examined nothing, '
        'so its clean result is vacuous. Check PROJECT_ROOT resolution.'
    )
    assert offenders == [], (
        f'The retired prefix-strip idiom reappeared in {len(offenders)} file(s) '
        f'(of {scanned} scanned). Use removeprefix("./") plus a ".." refusal '
        f'instead: {offenders}'
    )


def test_scanned_population_covers_the_bundles_tree():
    """The population is large enough to be the real marketplace tree.

    Guards against a walk that resolves to a technically-non-empty but wrong
    directory — the population assertion above would pass on a single file.
    """
    _offenders, scanned = scan_for_retired_idiom(MARKETPLACE_DIR)

    assert scanned > 100, f'Only {scanned} files scanned — too few to be the marketplace tree'


# ---------------------------------------------------------------------------
# Positive controls — the detector actually fires
# ---------------------------------------------------------------------------


def test_detector_fires_on_single_quoted_spelling(tmp_path):
    """A file carrying the single-quoted idiom is reported as an offender."""
    offender = tmp_path / 'offender.py'
    offender.write_text("ref = value.lstrip('./')\n", encoding='utf-8')

    offenders, scanned = scan_for_retired_idiom(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_fires_on_double_quoted_spelling(tmp_path):
    """The double-quoted spelling is caught too — both forms are the same defect."""
    offender = tmp_path / 'offender.py'
    offender.write_text('ref = value.lstrip("./")\n', encoding='utf-8')

    offenders, scanned = scan_for_retired_idiom(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_accepts_the_supported_replacement(tmp_path):
    """Negative control: ``removeprefix('./')`` is not flagged.

    Without this, a detector matching something broader (e.g. any ``lstrip`` or
    any ``'./'``) would satisfy both positive controls while failing every
    correctly-fixed file.
    """
    clean = tmp_path / 'clean.py'
    clean.write_text(
        "rel = ref.removeprefix('./')\nif '..' in rel.split('/'):\n    rel = None\n",
        encoding='utf-8',
    )

    offenders, scanned = scan_for_retired_idiom(tmp_path)

    assert scanned == 1
    assert offenders == []


def test_scan_reports_zero_population_for_a_missing_root(tmp_path):
    """A non-existent root yields a zero population, never a false clean pass.

    This is what makes the population assertion in the whole-tree test load
    bearing: a mis-rooted walk reports 0 rather than silently returning an
    empty offender list that reads as success.
    """
    offenders, scanned = scan_for_retired_idiom(tmp_path / 'does-not-exist')

    assert offenders == []
    assert scanned == 0


def test_excluded_directories_are_not_scanned(tmp_path):
    """Cache directories are skipped, so stale compiled copies cannot trip the guard."""
    cached = tmp_path / '__pycache__' / 'stale.py'
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text("ref = value.lstrip('./')\n", encoding='utf-8')

    offenders, scanned = scan_for_retired_idiom(tmp_path)

    assert offenders == []
    assert scanned == 0
