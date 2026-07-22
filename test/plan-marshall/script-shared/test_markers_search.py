# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _markers_search shared module.

Every marker literal used by these tests is DERIVED from the checked-in
provenance fixture (``fixtures/cui-rewrite/MarkedSample.java``), never
hand-written. The fixture carries an unmodified marker emitted by the upstream
``cui-open-rewrite`` recipes — see ``fixtures/cui-rewrite/PROVENANCE.md``.

The derivation deliberately does NOT reuse ``MARKER_PATTERN`` (the module under
test): it scans the fixture with an independent, trivial delimiter walk, so a
regression in ``MARKER_PATTERN`` cannot silently rewrite the expectations.
"""

import importlib
import sys
import tempfile
from pathlib import Path

# Add script path for imports
_SCRIPT_DIR = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
)
sys.path.insert(0, str(_SCRIPT_DIR))

_markers_search = importlib.import_module('_markers_search')

search_openrewrite_markers = _markers_search.search_openrewrite_markers
extract_recipe_name = _markers_search.extract_recipe_name
MARKER_PATTERN = _markers_search.MARKER_PATTERN
DEFAULT_SKIP_PATTERNS = _markers_search.DEFAULT_SKIP_PATTERNS
AUTO_SUPPRESS_RECIPES = _markers_search.AUTO_SUPPRESS_RECIPES

FIXTURE_DIR = Path(__file__).resolve().parent / 'fixtures' / 'cui-rewrite'
FIXTURE_SAMPLE = FIXTURE_DIR / 'MarkedSample.java'
FIXTURE_PROVENANCE = FIXTURE_DIR / 'PROVENANCE.md'


def _read_fixture_marker() -> str:
    """Return the raw marker literal carried by the provenance fixture.

    Scans with a plain delimiter walk (first ``/*`` comment opener that starts a
    marker, up to the first following ``*/``) rather than with MARKER_PATTERN,
    so the expectations stay independent of the module under test.
    """
    text = FIXTURE_SAMPLE.read_text(encoding='utf-8')
    start = text.index('/*~~(')
    end = text.index('*/', start) + len('*/')
    return text[start:end]


#: The verbatim upstream marker, e.g. ``/*~~(TODO: ...)~~>*/``.
FIXTURE_MARKER = _read_fixture_marker()

#: Opening delimiter up to and including the message-opening paren.
MARKER_OPEN = FIXTURE_MARKER[: FIXTURE_MARKER.index('(') + 1]

#: Closing delimiter from the message-closing paren onwards.
MARKER_CLOSE = FIXTURE_MARKER[FIXTURE_MARKER.rindex(')') :]

#: The pre-fix delimiter this plan retired — the real one with its tildes dropped.
LEGACY_MARKER_CLOSE = MARKER_CLOSE.replace('~~', '')


def build_marker(message: str) -> str:
    """Build a marker carrying `message`, using the fixture-derived delimiters."""
    return f'{MARKER_OPEN}TODO: {message}{MARKER_CLOSE}'


class TestFixtureDerivation:
    """Guards on the fixture-derived constants the rest of this module builds on."""

    def test_fixture_marker_is_a_complete_comment(self):
        assert FIXTURE_MARKER.startswith('/*')
        assert FIXTURE_MARKER.endswith('*/')

    def test_open_and_close_delimiters_are_distinct_and_non_empty(self):
        assert MARKER_OPEN
        assert MARKER_CLOSE
        assert MARKER_OPEN != MARKER_CLOSE

    def test_close_delimiter_carries_tildes(self):
        # The retired form dropped them; the real one must not.
        assert '~~' in MARKER_CLOSE
        assert LEGACY_MARKER_CLOSE != MARKER_CLOSE

    def test_build_marker_round_trips_through_the_pattern(self):
        matches = list(MARKER_PATTERN.finditer(build_marker('SomeRecipe fix this')))
        assert len(matches) == 1
        assert matches[0].group(1).strip() == 'SomeRecipe fix this'


class TestProvenanceFixture:
    """Regression tests pinning the detector against the checked-in upstream marker."""

    def test_detector_finds_the_fixture_marker(self):
        result = search_openrewrite_markers(str(FIXTURE_DIR))
        assert result['status'] == 'success'
        assert result['data']['total_markers'] > 0

    def test_detected_raw_marker_is_the_verbatim_fixture_marker(self):
        result = search_openrewrite_markers(str(FIXTURE_DIR))
        raw_markers = [m['raw_marker'] for m in result['data']['markers']]
        assert FIXTURE_MARKER in raw_markers

    def test_legacy_delimiter_no_longer_matches(self):
        legacy = f'{MARKER_OPEN}TODO: SomeRecipe fix this{LEGACY_MARKER_CLOSE}'
        assert list(MARKER_PATTERN.finditer(legacy)) == []

    def test_provenance_document_records_every_required_field(self):
        provenance = FIXTURE_PROVENANCE.read_text(encoding='utf-8')
        assert 'cuioss/cui-open-rewrite' in provenance
        assert 'CuiLogRecordPatternRecipeTest.java' in provenance
        assert '081e18b86378ca1603cbe532f641ecd98f943bc9' in provenance
        assert 'CuiLogRecordPatternRecipe' in provenance


class TestMarkerPattern:
    """Tests for the MARKER_PATTERN regex."""

    def test_matches_standard_marker(self):
        line = f'some code {build_marker("SomeRecipe fix this")} more code'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 1
        assert matches[0].group(1).strip() == 'SomeRecipe fix this'

    def test_matches_multiple_markers_on_same_line(self):
        line = f'{build_marker("RecipeA")} gap {build_marker("RecipeB")}'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 2

    def test_no_match_on_plain_todo(self):
        line = '// TODO: normal todo comment'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 0

    def test_no_match_on_empty_line(self):
        matches = list(MARKER_PATTERN.finditer(''))
        assert len(matches) == 0


class TestExtractRecipeName:
    """Tests for extract_recipe_name()."""

    def test_extracts_recipe_suffix(self):
        assert extract_recipe_name('CuiLogRecordPatternRecipe do something') == 'CuiLogRecordPatternRecipe'

    def test_extracts_pattern_suffix(self):
        assert extract_recipe_name('SomePattern is applied') == 'SomePattern'

    def test_falls_back_to_first_word(self):
        assert extract_recipe_name('UnknownThing needs review') == 'UnknownThing'

    def test_strips_trailing_punctuation_on_fallback(self):
        assert extract_recipe_name('Fix: something broken') == 'Fix'

    def test_empty_message(self):
        assert extract_recipe_name('') == 'UnknownRecipe'

    def test_single_word_recipe(self):
        assert extract_recipe_name('InvalidExceptionUsageRecipe') == 'InvalidExceptionUsageRecipe'


class TestDefaultSkipPatterns:
    """Tests for DEFAULT_SKIP_PATTERNS constant."""

    def test_contains_build(self):
        assert 'build' in DEFAULT_SKIP_PATTERNS

    def test_contains_target(self):
        assert 'target' in DEFAULT_SKIP_PATTERNS

    def test_contains_gradle(self):
        assert '.gradle' in DEFAULT_SKIP_PATTERNS

    def test_contains_node_modules(self):
        assert 'node_modules' in DEFAULT_SKIP_PATTERNS


class TestAutoSuppressRecipes:
    """Tests for AUTO_SUPPRESS_RECIPES constant."""

    def test_contains_cui_logrecord(self):
        assert 'CuiLogRecordPatternRecipe' in AUTO_SUPPRESS_RECIPES

    def test_contains_invalid_exception(self):
        assert 'InvalidExceptionUsageRecipe' in AUTO_SUPPRESS_RECIPES

    def test_recipe_has_category_and_reason(self):
        for recipe_name, info in AUTO_SUPPRESS_RECIPES.items():
            assert 'category' in info, f'{recipe_name} missing category'
            assert 'reason' in info, f'{recipe_name} missing reason'


class TestSearchSourceDirectory:
    """Tests for source directory validation in search_openrewrite_markers()."""

    def test_nonexistent_source_dir_returns_error(self):
        result = search_openrewrite_markers('/nonexistent/path/that/does/not/exist')
        assert result['status'] == 'error'
        assert result['error'] == 'source_not_found'

    def test_empty_source_dir_returns_zero_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = search_openrewrite_markers(tmp)
            assert result['status'] == 'success'
            assert result['data']['total_markers'] == 0
            assert result['data']['files_affected'] == 0


class TestSearchJavaFiles:
    """Tests for Java file marker scanning."""

    def test_finds_marker_in_java_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_file = Path(tmp) / 'Example.java'
            java_file.write_text(f'public class Example {{\n    {build_marker("SomeRecipe fix this")} int x;\n}}\n')
            result = search_openrewrite_markers(tmp)
            assert result['status'] == 'success'
            assert result['data']['total_markers'] == 1
            assert result['data']['files_affected'] == 1

    def test_marker_details_are_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_file = Path(tmp) / 'Foo.java'
            raw = build_marker('MyRecipe refactor needed')
            java_file.write_text(f'package com.example;\n{raw}\n')
            result = search_openrewrite_markers(tmp)
            markers = result['data']['markers']
            assert len(markers) == 1
            marker = markers[0]
            assert marker['line'] == 2
            assert marker['recipe'] == 'MyRecipe'
            assert 'refactor needed' in marker['message']
            assert marker['raw_marker'] == raw

    def test_finds_multiple_markers_across_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'A.java').write_text(build_marker('RecipeA'))
            (Path(tmp) / 'B.java').write_text(build_marker('RecipeB'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 2
            assert result['data']['files_affected'] == 2

    def test_finds_multiple_markers_in_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = f'{build_marker("RecipeA")}\nsome code\n{build_marker("RecipeB")}\n'
            (Path(tmp) / 'Multi.java').write_text(content)
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 2
            assert result['data']['files_affected'] == 1

    def test_ignores_non_java_files_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'file.txt').write_text(build_marker('SomeRecipe'))
            (Path(tmp) / 'file.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 1


class TestSearchMultipleExtensions:
    """Tests for multi-extension support."""

    def test_kotlin_files_with_kt_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Main.kt').write_text(build_marker('KotlinRecipe'))
            result = search_openrewrite_markers(tmp, extensions='.kt')
            assert result['data']['total_markers'] == 1

    def test_java_and_kotlin_combined(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Foo.java').write_text(build_marker('JavaRecipe'))
            (Path(tmp) / 'Bar.kt').write_text(build_marker('KotlinRecipe'))
            result = search_openrewrite_markers(tmp, extensions='.java,.kt')
            assert result['data']['total_markers'] == 2

    def test_extension_without_dot_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Test.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp, extensions='java')
            assert result['data']['total_markers'] == 1


class TestSearchSkipPatterns:
    """Tests for directory skip patterns."""

    def test_skips_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / 'build'
            build_dir.mkdir()
            (build_dir / 'Generated.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / 'target'
            target_dir.mkdir()
            (target_dir / 'Compiled.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_gradle_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            gradle_dir = Path(tmp) / '.gradle'
            gradle_dir.mkdir()
            (gradle_dir / 'Cache.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_node_modules_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nm_dir = Path(tmp) / 'node_modules'
            nm_dir.mkdir()
            (nm_dir / 'Dep.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_nested_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / 'module' / 'target'
            nested.mkdir(parents=True)
            (nested / 'Output.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_custom_skip_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen_dir = Path(tmp) / 'generated'
            gen_dir.mkdir()
            (gen_dir / 'Gen.java').write_text(build_marker('SomeRecipe'))
            # Default patterns do not skip 'generated'
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 1
            # Custom pattern skips 'generated'
            result = search_openrewrite_markers(tmp, skip_patterns=('generated',))
            assert result['data']['total_markers'] == 0

    def test_does_not_skip_source_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / 'src' / 'main' / 'java'
            src_dir.mkdir(parents=True)
            (src_dir / 'App.java').write_text(build_marker('SomeRecipe'))
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 1


class TestRecipeCategorization:
    """Tests for recipe categorization (auto_suppress vs ask_user)."""

    def test_auto_suppress_recipe_categorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Log.java').write_text(build_marker('CuiLogRecordPatternRecipe check logging'))
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'auto_suppress'
            assert marker['category'] == 'logrecord'
            assert 'suppression_comment' in marker

    def test_invalid_exception_recipe_auto_suppressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Ex.java').write_text(build_marker('InvalidExceptionUsageRecipe check pattern'))
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'auto_suppress'
            assert marker['category'] == 'exception'

    def test_unknown_recipe_requires_user_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Unk.java').write_text(build_marker('SomeUnknownRecipe needs review'))
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'ask_user'
            assert marker['category'] == 'other'

    def test_by_category_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Mix.java').write_text(
                f'{build_marker("CuiLogRecordPatternRecipe log")}\n{build_marker("CustomThing check")}\n'
            )
            result = search_openrewrite_markers(tmp)
            data = result['data']
            assert data['auto_suppress_count'] == 1
            assert data['ask_user_count'] == 1
            assert len(data['by_category']['auto_suppress']) == 1
            assert len(data['by_category']['ask_user']) == 1


class TestRecipeSummary:
    """Tests for recipe_summary aggregation."""

    def test_recipe_summary_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'A.java').write_text(
                f'{build_marker("RecipeAlpha")}\n{build_marker("RecipeAlpha")}\n{build_marker("RecipeBeta")}\n'
            )
            result = search_openrewrite_markers(tmp)
            summary = result['data']['recipe_summary']
            assert summary['RecipeAlpha'] == 2
            assert summary['RecipeBeta'] == 1

    def test_empty_recipe_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = search_openrewrite_markers(tmp)
            assert result['data']['recipe_summary'] == {}


class TestSuppressionComment:
    """Tests for suppression_comment field in auto_suppress markers."""

    def test_suppression_comment_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'S.java').write_text(build_marker('CuiLogRecordPatternRecipe'))
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['suppression_comment'] == '// cui-rewrite:disable CuiLogRecordPatternRecipe'
