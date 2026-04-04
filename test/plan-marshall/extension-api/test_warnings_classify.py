"""Tests for _warnings_classify module — unified warning categorization with pluggable matching."""

import importlib
import sys
from pathlib import Path

# Add script path for imports
_SCRIPT_DIR = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'extension-api'
    / 'scripts'
)
sys.path.insert(0, str(_SCRIPT_DIR))

_wc = importlib.import_module('_warnings_classify')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _warn(message: str, wtype: str = 'other', severity: str = 'WARNING') -> dict:
    """Build a minimal warning dict."""
    return {'type': wtype, 'message': message, 'severity': severity}


# ---------------------------------------------------------------------------
# flatten_patterns
# ---------------------------------------------------------------------------


class TestFlattenPatterns:
    """Tests for flatten_patterns()."""

    def test_flat_list_returned_as_is(self):
        patterns = ['alpha', 'beta']
        result = _wc.flatten_patterns(patterns)
        assert result == ['alpha', 'beta']

    def test_dict_values_flattened(self):
        patterns = {
            'group_a': ['p1', 'p2'],
            'group_b': ['p3'],
        }
        result = _wc.flatten_patterns(patterns)
        assert set(result) == {'p1', 'p2', 'p3'}

    def test_empty_list(self):
        assert _wc.flatten_patterns([]) == []

    def test_empty_dict(self):
        assert _wc.flatten_patterns({}) == []

    def test_none_values_in_list_skipped(self):
        result = _wc.flatten_patterns(['a', None, '', 'b'])
        assert result == ['a', 'b']

    def test_none_values_in_dict_skipped(self):
        result = _wc.flatten_patterns({'g': ['a', None, '', 'b']})
        assert result == ['a', 'b']

    def test_dict_with_non_list_value_ignored(self):
        """Non-list dict values are silently ignored."""
        result = _wc.flatten_patterns({'g': 'not_a_list'})
        assert result == []


# ---------------------------------------------------------------------------
# ALWAYS_FIXABLE_TYPES detection
# ---------------------------------------------------------------------------


class TestAlwaysFixableTypes:
    """Warnings typed as ALWAYS_FIXABLE_TYPES go to fixable regardless of patterns."""

    def test_javadoc_warning_is_fixable(self):
        result = _wc.categorize_warnings(
            [_warn('some javadoc issue', wtype='javadoc_warning')],
            patterns=['some javadoc issue'],
            matcher='substring',
        )
        assert len(result['fixable']) == 1
        assert result['fixable'][0]['reason'] == "Type 'javadoc_warning' is always fixable"
        assert result['acceptable'] == []

    def test_all_always_fixable_types(self):
        for wtype in _wc.ALWAYS_FIXABLE_TYPES:
            result = _wc.categorize_warnings(
                [_warn('msg', wtype=wtype)],
                patterns=['msg'],
            )
            assert len(result['fixable']) == 1, f'{wtype} should be fixable'

    def test_compilation_error_routed_to_fixable(self):
        result = _wc.categorize_warnings(
            [_warn('cannot find symbol', wtype='compilation_error')],
        )
        assert len(result['fixable']) == 1


# ---------------------------------------------------------------------------
# Substring matcher (Maven style)
# ---------------------------------------------------------------------------


class TestSubstringMatcher:
    """categorize_warnings with matcher='substring'."""

    def test_exact_substring_match(self):
        result = _wc.categorize_warnings(
            [_warn('some deprecated API usage')],
            patterns=['deprecated API'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 1

    def test_case_insensitive_regex_fallback(self):
        result = _wc.categorize_warnings(
            [_warn('Found DEPRECATED method call')],
            patterns=['deprecated.*call'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 1

    def test_warning_prefix_stripped(self):
        """Patterns starting with [WARNING] have that prefix removed before matching."""
        result = _wc.categorize_warnings(
            [_warn('some build issue here')],
            patterns=['[WARNING] some build issue'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 1

    def test_no_match_goes_to_fixable_for_unknown_type(self):
        """Unmatched warnings with non-standard type go to fixable by default."""
        result = _wc.categorize_warnings(
            [_warn('something else', wtype='custom_type')],
            patterns=['no match here'],
            matcher='substring',
        )
        assert len(result['fixable']) == 1

    def test_invalid_regex_handled_gracefully(self):
        """Invalid regex in pattern does not raise — just fails to match."""
        result = _wc.categorize_warnings(
            [_warn('test message')],
            patterns=['[invalid regex'],
            matcher='substring',
        )
        # No crash; warning routes based on type
        assert len(result['fixable']) + len(result['unknown']) + len(result['acceptable']) == 1


# ---------------------------------------------------------------------------
# Wildcard matcher (Gradle style)
# ---------------------------------------------------------------------------


class TestWildcardMatcher:
    """categorize_warnings with matcher='wildcard'."""

    def test_exact_match(self):
        result = _wc.categorize_warnings(
            [_warn('exact pattern')],
            patterns=['exact pattern'],
            matcher='wildcard',
        )
        assert len(result['acceptable']) == 1

    def test_trailing_wildcard(self):
        result = _wc.categorize_warnings(
            [_warn('com.example.SomeClass is deprecated')],
            patterns=['com.example.*'],
            matcher='wildcard',
        )
        assert len(result['acceptable']) == 1

    def test_leading_wildcard(self):
        result = _wc.categorize_warnings(
            [_warn('something ending with .deprecated')],
            patterns=['*.deprecated'],
            matcher='wildcard',
        )
        assert len(result['acceptable']) == 1

    def test_both_wildcards_contains_match(self):
        result = _wc.categorize_warnings(
            [_warn('prefix middle suffix')],
            patterns=['*middle*'],
            matcher='wildcard',
        )
        assert len(result['acceptable']) == 1

    def test_caret_regex_pattern(self):
        result = _wc.categorize_warnings(
            [_warn('com.example.Foo has issues')],
            patterns=['^com\\.example\\.Foo'],
            matcher='wildcard',
        )
        assert len(result['acceptable']) == 1

    def test_caret_regex_no_match(self):
        result = _wc.categorize_warnings(
            [_warn('org.other.Bar has issues')],
            patterns=['^com\\.example\\.Foo'],
            matcher='wildcard',
        )
        assert result['acceptable'] == []

    def test_no_match(self):
        result = _wc.categorize_warnings(
            [_warn('totally different message')],
            patterns=['no match'],
            matcher='wildcard',
        )
        assert result['acceptable'] == []


# ---------------------------------------------------------------------------
# Regex matcher
# ---------------------------------------------------------------------------


class TestRegexMatcher:
    """categorize_warnings with matcher='regex'."""

    def test_simple_regex(self):
        result = _wc.categorize_warnings(
            [_warn('WARNING: found 3 issues')],
            patterns=[r'found \d+ issues'],
            matcher='regex',
        )
        assert len(result['acceptable']) == 1

    def test_complex_regex(self):
        result = _wc.categorize_warnings(
            [_warn('com.example.Foo:42 deprecation')],
            patterns=[r'^com\.example\.\w+:\d+'],
            matcher='regex',
        )
        assert len(result['acceptable']) == 1

    def test_invalid_regex_no_crash(self):
        result = _wc.categorize_warnings(
            [_warn('test')],
            patterns=['[invalid'],
            matcher='regex',
        )
        # Invalid regex returns False, does not match — no crash
        assert result['acceptable'] == []

    def test_no_match(self):
        result = _wc.categorize_warnings(
            [_warn('hello world')],
            patterns=[r'^goodbye'],
            matcher='regex',
        )
        assert result['acceptable'] == []


# ---------------------------------------------------------------------------
# Flat pattern list input
# ---------------------------------------------------------------------------


class TestFlatPatternInput:
    """categorize_warnings with patterns as flat list."""

    def test_flat_list_matches(self):
        result = _wc.categorize_warnings(
            [_warn('known issue ABC')],
            patterns=['known issue ABC'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 1
        # Flat list match does not add 'reason' key
        assert 'reason' not in result['acceptable'][0]

    def test_flat_list_multiple_patterns(self):
        warnings = [
            _warn('issue A here'),
            _warn('issue B here'),
            _warn('issue C unmatched'),
        ]
        result = _wc.categorize_warnings(
            warnings,
            patterns=['issue A', 'issue B'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 2
        assert len(result['fixable']) + len(result['unknown']) == 1


# ---------------------------------------------------------------------------
# Categorized dict input
# ---------------------------------------------------------------------------


class TestCategorizedDictInput:
    """categorize_warnings with patterns as categorized dict."""

    def test_dict_match_includes_category_in_reason(self):
        result = _wc.categorize_warnings(
            [_warn('known annotation issue')],
            patterns={'annotation_issues': ['annotation issue']},
            matcher='substring',
        )
        assert len(result['acceptable']) == 1
        assert 'annotation_issues' in result['acceptable'][0]['reason']

    def test_dict_multiple_categories(self):
        warnings = [
            _warn('foo annotation problem'),
            _warn('bar dependency thing'),
        ]
        result = _wc.categorize_warnings(
            warnings,
            patterns={
                'annotations': ['annotation problem'],
                'deps': ['dependency thing'],
            },
            matcher='substring',
        )
        assert len(result['acceptable']) == 2

    def test_dict_no_match_routes_by_type(self):
        result = _wc.categorize_warnings(
            [_warn('unmatched message', wtype='other')],
            patterns={'group': ['no match']},
            matcher='substring',
        )
        assert len(result['unknown']) == 1
        assert result['unknown'][0].get('requires_classification') is True


# ---------------------------------------------------------------------------
# Mixed acceptable and fixable warnings
# ---------------------------------------------------------------------------


class TestMixedWarnings:
    """Mixed warning sets with different types and pattern matches."""

    def test_mixed_routing(self):
        warnings = [
            _warn('known issue', wtype='other'),
            _warn('javadoc error', wtype='javadoc_warning'),
            _warn('unknown thing', wtype='other'),
            _warn('test fail', wtype='test_failure'),
            _warn('openrewrite note', wtype='openrewrite_info'),
        ]
        result = _wc.categorize_warnings(
            warnings,
            patterns=['known issue'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 2  # 'known issue' + openrewrite_info
        assert len(result['fixable']) == 2  # javadoc_warning + test_failure
        assert len(result['unknown']) == 1  # 'other' unmatched

    def test_extra_fixable_types_route_correctly(self):
        for wtype in _wc.EXTRA_FIXABLE_TYPES:
            result = _wc.categorize_warnings(
                [_warn('some message', wtype=wtype)],
            )
            assert len(result['fixable']) == 1, f'{wtype} should be fixable'

    def test_acceptable_types_route_correctly(self):
        for wtype in _wc.ACCEPTABLE_TYPES:
            result = _wc.categorize_warnings(
                [_warn('some message', wtype=wtype)],
            )
            assert len(result['acceptable']) == 1, f'{wtype} should be acceptable'

    def test_unknown_types_route_correctly(self):
        for wtype in _wc.UNKNOWN_TYPES:
            result = _wc.categorize_warnings(
                [_warn('some message', wtype=wtype)],
            )
            assert len(result['unknown']) == 1, f'{wtype} should be unknown'
            assert result['unknown'][0].get('requires_classification') is True


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    """Edge cases with empty warnings or patterns."""

    def test_empty_warnings_list(self):
        result = _wc.categorize_warnings([], patterns=['anything'])
        assert result == {'acceptable': [], 'fixable': [], 'unknown': []}

    def test_empty_patterns_list(self):
        result = _wc.categorize_warnings(
            [_warn('msg', wtype='other')],
            patterns=[],
        )
        assert len(result['unknown']) == 1

    def test_none_patterns(self):
        result = _wc.categorize_warnings(
            [_warn('msg', wtype='other')],
            patterns=None,
        )
        assert len(result['unknown']) == 1

    def test_both_empty(self):
        result = _wc.categorize_warnings([], patterns=[])
        assert result == {'acceptable': [], 'fixable': [], 'unknown': []}


# ---------------------------------------------------------------------------
# filter_severity parameter
# ---------------------------------------------------------------------------


class TestFilterSeverity:
    """categorize_warnings with filter_severity."""

    def test_filters_by_severity(self):
        warnings = [
            _warn('warn msg', severity='WARNING'),
            _warn('error msg', severity='ERROR'),
        ]
        result = _wc.categorize_warnings(
            warnings,
            patterns=['warn msg', 'error msg'],
            matcher='substring',
            filter_severity='WARNING',
        )
        assert len(result['acceptable']) == 1
        assert result['acceptable'][0]['message'] == 'warn msg'

    def test_no_matching_severity_returns_empty(self):
        result = _wc.categorize_warnings(
            [_warn('msg', severity='WARNING')],
            filter_severity='ERROR',
        )
        assert result == {'acceptable': [], 'fixable': [], 'unknown': []}


# ---------------------------------------------------------------------------
# Default matcher fallback
# ---------------------------------------------------------------------------


class TestDefaultMatcher:
    """categorize_warnings with unknown matcher falls back to substring."""

    def test_unknown_matcher_uses_substring(self):
        result = _wc.categorize_warnings(
            [_warn('has a substring here')],
            patterns=['a substring'],
            matcher='nonexistent_matcher',
        )
        assert len(result['acceptable']) == 1


# ---------------------------------------------------------------------------
# Unrecognized type routing
# ---------------------------------------------------------------------------


class TestUnrecognizedType:
    """Warnings with types not in any known list route to fixable."""

    def test_unrecognized_type_goes_to_fixable(self):
        result = _wc.categorize_warnings(
            [_warn('msg', wtype='completely_new_type')],
        )
        assert len(result['fixable']) == 1
