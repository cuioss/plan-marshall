"""Tests for _markers_search shared module."""

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

# Re-export for convenience
search_openrewrite_markers = _markers_search.search_openrewrite_markers
extract_recipe_name = _markers_search.extract_recipe_name
MARKER_PATTERN = _markers_search.MARKER_PATTERN
DEFAULT_SKIP_PATTERNS = _markers_search.DEFAULT_SKIP_PATTERNS
AUTO_SUPPRESS_RECIPES = _markers_search.AUTO_SUPPRESS_RECIPES


# =============================================================================
# Test: MARKER_PATTERN regex
# =============================================================================


class TestMarkerPattern:
    """Tests for the MARKER_PATTERN regex."""

    def test_matches_standard_marker(self):
        line = 'some code /*~~(TODO: SomeRecipe fix this)>*/ more code'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 1
        assert matches[0].group(1).strip() == 'SomeRecipe fix this'

    def test_matches_multiple_markers_on_same_line(self):
        line = '/*~~(TODO: RecipeA)>*/ gap /*~~(TODO: RecipeB)>*/'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 2

    def test_no_match_on_plain_todo(self):
        line = '// TODO: normal todo comment'
        matches = list(MARKER_PATTERN.finditer(line))
        assert len(matches) == 0

    def test_no_match_on_empty_line(self):
        matches = list(MARKER_PATTERN.finditer(''))
        assert len(matches) == 0


# =============================================================================
# Test: extract_recipe_name()
# =============================================================================


class TestExtractRecipeName:
    """Tests for extract_recipe_name()."""

    def test_extracts_recipe_suffix(self):
        assert extract_recipe_name('CuiLogRecordPatternRecipe do something') == 'CuiLogRecordPatternRecipe'

    def test_extracts_pattern_suffix(self):
        assert extract_recipe_name('SomePattern is applied') == 'SomePattern'

    def test_falls_back_to_first_word(self):
        assert extract_recipe_name('UnknownThing needs review') == 'UnknownThing'

    def test_strips_trailing_punctuation_on_fallback(self):
        # When no Recipe/Pattern suffix, falls back to first word with punctuation stripped
        assert extract_recipe_name('Fix: something broken') == 'Fix'

    def test_empty_message(self):
        assert extract_recipe_name('') == 'UnknownRecipe'

    def test_single_word_recipe(self):
        assert extract_recipe_name('InvalidExceptionUsageRecipe') == 'InvalidExceptionUsageRecipe'


# =============================================================================
# Test: DEFAULT_SKIP_PATTERNS
# =============================================================================


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


# =============================================================================
# Test: AUTO_SUPPRESS_RECIPES
# =============================================================================


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


# =============================================================================
# Test: search_openrewrite_markers() - source directory handling
# =============================================================================


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


# =============================================================================
# Test: search_openrewrite_markers() - Java file scanning
# =============================================================================


class TestSearchJavaFiles:
    """Tests for Java file marker scanning."""

    def test_finds_marker_in_java_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_file = Path(tmp) / 'Example.java'
            java_file.write_text('public class Example {\n    /*~~(TODO: SomeRecipe fix this)>*/ int x;\n}\n')
            result = search_openrewrite_markers(tmp)
            assert result['status'] == 'success'
            assert result['data']['total_markers'] == 1
            assert result['data']['files_affected'] == 1

    def test_marker_details_are_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_file = Path(tmp) / 'Foo.java'
            java_file.write_text('package com.example;\n/*~~(TODO: MyRecipe refactor needed)>*/\n')
            result = search_openrewrite_markers(tmp)
            markers = result['data']['markers']
            assert len(markers) == 1
            marker = markers[0]
            assert marker['line'] == 2
            assert marker['recipe'] == 'MyRecipe'
            assert 'refactor needed' in marker['message']
            assert marker['raw_marker'] == '/*~~(TODO: MyRecipe refactor needed)>*/'

    def test_finds_multiple_markers_across_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'A.java').write_text('/*~~(TODO: RecipeA)>*/')
            (Path(tmp) / 'B.java').write_text('/*~~(TODO: RecipeB)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 2
            assert result['data']['files_affected'] == 2

    def test_finds_multiple_markers_in_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = '/*~~(TODO: RecipeA)>*/\nsome code\n/*~~(TODO: RecipeB)>*/\n'
            (Path(tmp) / 'Multi.java').write_text(content)
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 2
            assert result['data']['files_affected'] == 1

    def test_ignores_non_java_files_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'file.txt').write_text('/*~~(TODO: SomeRecipe)>*/')
            (Path(tmp) / 'file.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 1


# =============================================================================
# Test: search_openrewrite_markers() - Kotlin / multi-extension support
# =============================================================================


class TestSearchMultipleExtensions:
    """Tests for multi-extension support."""

    def test_kotlin_files_with_kt_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Main.kt').write_text('/*~~(TODO: KotlinRecipe)>*/')
            result = search_openrewrite_markers(tmp, extensions='.kt')
            assert result['data']['total_markers'] == 1

    def test_java_and_kotlin_combined(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Foo.java').write_text('/*~~(TODO: JavaRecipe)>*/')
            (Path(tmp) / 'Bar.kt').write_text('/*~~(TODO: KotlinRecipe)>*/')
            result = search_openrewrite_markers(tmp, extensions='.java,.kt')
            assert result['data']['total_markers'] == 2

    def test_extension_without_dot_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Test.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp, extensions='java')
            assert result['data']['total_markers'] == 1


# =============================================================================
# Test: search_openrewrite_markers() - skip patterns
# =============================================================================


class TestSearchSkipPatterns:
    """Tests for directory skip patterns."""

    def test_skips_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / 'build'
            build_dir.mkdir()
            (build_dir / 'Generated.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / 'target'
            target_dir.mkdir()
            (target_dir / 'Compiled.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_gradle_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            gradle_dir = Path(tmp) / '.gradle'
            gradle_dir.mkdir()
            (gradle_dir / 'Cache.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_node_modules_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nm_dir = Path(tmp) / 'node_modules'
            nm_dir.mkdir()
            (nm_dir / 'Dep.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_skips_nested_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / 'module' / 'target'
            nested.mkdir(parents=True)
            (nested / 'Output.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 0

    def test_custom_skip_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen_dir = Path(tmp) / 'generated'
            gen_dir.mkdir()
            (gen_dir / 'Gen.java').write_text('/*~~(TODO: SomeRecipe)>*/')
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
            (src_dir / 'App.java').write_text('/*~~(TODO: SomeRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            assert result['data']['total_markers'] == 1


# =============================================================================
# Test: search_openrewrite_markers() - recipe categorization
# =============================================================================


class TestRecipeCategorization:
    """Tests for recipe categorization (auto_suppress vs ask_user)."""

    def test_auto_suppress_recipe_categorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Log.java').write_text('/*~~(TODO: CuiLogRecordPatternRecipe check logging)>*/')
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'auto_suppress'
            assert marker['category'] == 'logrecord'
            assert 'suppression_comment' in marker

    def test_invalid_exception_recipe_auto_suppressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Ex.java').write_text('/*~~(TODO: InvalidExceptionUsageRecipe check pattern)>*/')
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'auto_suppress'
            assert marker['category'] == 'exception'

    def test_unknown_recipe_requires_user_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Unk.java').write_text('/*~~(TODO: SomeUnknownRecipe needs review)>*/')
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['action'] == 'ask_user'
            assert marker['category'] == 'other'

    def test_by_category_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Mix.java').write_text(
                '/*~~(TODO: CuiLogRecordPatternRecipe log)>*/\n/*~~(TODO: CustomThing check)>*/\n'
            )
            result = search_openrewrite_markers(tmp)
            data = result['data']
            assert data['auto_suppress_count'] == 1
            assert data['ask_user_count'] == 1
            assert len(data['by_category']['auto_suppress']) == 1
            assert len(data['by_category']['ask_user']) == 1


# =============================================================================
# Test: search_openrewrite_markers() - recipe_summary
# =============================================================================


class TestRecipeSummary:
    """Tests for recipe_summary aggregation."""

    def test_recipe_summary_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'A.java').write_text(
                '/*~~(TODO: RecipeAlpha)>*/\n/*~~(TODO: RecipeAlpha)>*/\n/*~~(TODO: RecipeBeta)>*/\n'
            )
            result = search_openrewrite_markers(tmp)
            summary = result['data']['recipe_summary']
            assert summary['RecipeAlpha'] == 2
            assert summary['RecipeBeta'] == 1

    def test_empty_recipe_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = search_openrewrite_markers(tmp)
            assert result['data']['recipe_summary'] == {}


# =============================================================================
# Test: search_openrewrite_markers() - suppression_comment format
# =============================================================================


class TestSuppressionComment:
    """Tests for suppression_comment field in auto_suppress markers."""

    def test_suppression_comment_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'S.java').write_text('/*~~(TODO: CuiLogRecordPatternRecipe)>*/')
            result = search_openrewrite_markers(tmp)
            marker = result['data']['markers'][0]
            assert marker['suppression_comment'] == '// cui-rewrite:disable CuiLogRecordPatternRecipe'
