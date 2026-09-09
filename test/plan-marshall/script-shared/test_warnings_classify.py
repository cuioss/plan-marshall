# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _warnings_classify module — unified warning categorization with pluggable matching."""

# ``_warnings_classify`` lives in ``script-shared/scripts/build``, an immediate
# subdirectory the root conftest already puts on ``sys.path``, so it imports
# plainly with no bootstrap.
import _warnings_classify as _wc
import pytest


def _warn(message: str, wtype: str = 'other', severity: str = 'WARNING') -> dict:
    """Build a minimal warning dict."""
    return {'type': wtype, 'message': message, 'severity': severity}


#: ``(declared patterns, the flat list they reduce to)``. Both container shapes
#: are accepted — a flat list rides through, a categorised dict is flattened
#: across its groups — and the falsy / non-list entries are dropped from either.
_FLATTEN_CASES = [
    (['alpha', 'beta'], ['alpha', 'beta']),
    ({'group_a': ['p1', 'p2'], 'group_b': ['p3']}, ['p1', 'p2', 'p3']),
    ([], []),
    ({}, []),
    (['a', None, '', 'b'], ['a', 'b']),
    ({'g': ['a', None, '', 'b']}, ['a', 'b']),
    ({'g': 'not_a_list'}, []),
]

_FLATTEN_IDS = [
    'a-flat-list',
    'a-dict-of-groups',
    'an-empty-list',
    'an-empty-dict',
    'falsy-entries-in-a-list',
    'falsy-entries-in-a-group',
    'a-group-whose-value-is-not-a-list',
]


class TestFlattenPatterns:
    """Tests for flatten_patterns()."""

    @pytest.mark.parametrize('patterns,expected', _FLATTEN_CASES, ids=_FLATTEN_IDS)
    def test_flatten_patterns(self, patterns, expected: list[str]):
        assert _wc.flatten_patterns(patterns) == expected


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


#: ``(warning message, acceptance patterns)`` the substring matcher must accept.
#: The second row is the case-insensitive regex fallback the matcher applies when
#: the plain substring test misses; the third is the ``[WARNING]`` prefix a
#: pattern may carry, which is stripped before matching.
_SUBSTRING_ACCEPTED_CASES = [
    ('some deprecated API usage', ['deprecated API']),
    ('Found DEPRECATED method call', ['deprecated.*call']),
    ('some build issue here', ['[WARNING] some build issue']),
]

_SUBSTRING_ACCEPTED_IDS = [
    'a-plain-substring',
    'a-case-insensitive-regex-fallback',
    'a-pattern-carrying-the-warning-prefix',
]


class TestSubstringMatcher:
    """categorize_warnings with matcher='substring'."""

    @pytest.mark.parametrize('message,patterns', _SUBSTRING_ACCEPTED_CASES, ids=_SUBSTRING_ACCEPTED_IDS)
    def test_an_accepted_warning_lands_in_acceptable(self, message: str, patterns: list[str]):
        result = _wc.categorize_warnings([_warn(message)], patterns=patterns, matcher='substring')

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
        assert len(result['fixable']) + len(result['unknown']) + len(result['acceptable']) == 1


#: ``(warning message, patterns, accepted?)`` for the wildcard matcher. Each
#: wildcard position gets its own row, and a bare ``^`` pattern is handled as a
#: regex — with a matched negative so that arm is shown to discriminate rather
#: than accept everything.
_WILDCARD_CASES = [
    ('exact pattern', ['exact pattern'], 1),
    ('com.example.SomeClass is deprecated', ['com.example.*'], 1),
    ('something ending with .deprecated', ['*.deprecated'], 1),
    ('prefix middle suffix', ['*middle*'], 1),
    ('com.example.Foo has issues', ['^com\\.example\\.Foo'], 1),
    ('org.other.Bar has issues', ['^com\\.example\\.Foo'], 0),
    ('totally different message', ['no match'], 0),
]

_WILDCARD_IDS = [
    'an-exact-pattern',
    'a-trailing-wildcard',
    'a-leading-wildcard',
    'wildcards-on-both-ends',
    'a-caret-regex-that-matches',
    'a-caret-regex-that-does-not-match',
    'a-pattern-that-matches-nothing',
]


class TestWildcardMatcher:
    """categorize_warnings with matcher='wildcard'."""

    @pytest.mark.parametrize('message,patterns,accepted', _WILDCARD_CASES, ids=_WILDCARD_IDS)
    def test_wildcard_acceptance(self, message: str, patterns: list[str], accepted: int):
        result = _wc.categorize_warnings([_warn(message)], patterns=patterns, matcher='wildcard')

        assert len(result['acceptable']) == accepted


#: ``(warning message, patterns, accepted?)`` for the regex matcher. The
#: unparseable-pattern row is the one that must not raise: an operator's typo in
#: a config file cannot be allowed to abort the whole classification.
_REGEX_CASES = [
    ('WARNING: found 3 issues', [r'found \d+ issues'], 1),
    ('com.example.Foo:42 deprecation', [r'^com\.example\.\w+:\d+'], 1),
    ('test', ['[invalid'], 0),
    ('hello world', [r'^goodbye'], 0),
]

_REGEX_IDS = [
    'an-unanchored-regex-matching-mid-message',
    'an-anchored-regex-of-character-classes',
    'an-unparseable-regex',
    'an-anchored-regex-that-matches-nothing',
]


class TestRegexMatcher:
    """categorize_warnings with matcher='regex'."""

    @pytest.mark.parametrize('message,patterns,accepted', _REGEX_CASES, ids=_REGEX_IDS)
    def test_regex_acceptance(self, message: str, patterns: list[str], accepted: int):
        result = _wc.categorize_warnings([_warn(message)], patterns=patterns, matcher='regex')

        assert len(result['acceptable']) == accepted


class TestFlatPatternInput:
    """categorize_warnings with patterns as flat list."""

    def test_flat_list_matches(self):
        result = _wc.categorize_warnings(
            [_warn('known issue ABC')],
            patterns=['known issue ABC'],
            matcher='substring',
        )
        assert len(result['acceptable']) == 1
        # A flat-list match carries no 'reason' key (only categorized-dict matches do).
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


#: ``(warnings, patterns, the (acceptable, fixable, unknown) bucket sizes)``. No
#: warnings means no output whatever the patterns say; an untyped warning with
#: nothing to match it against is UNKNOWN rather than fixable, and an absent
#: pattern set is the same answer as an empty one.
_EMPTY_INPUT_CASES = [
    ([], ['anything'], (0, 0, 0)),
    ([], [], (0, 0, 0)),
    ([_warn('msg', wtype='other')], [], (0, 0, 1)),
    ([_warn('msg', wtype='other')], None, (0, 0, 1)),
]

_EMPTY_INPUT_IDS = [
    'no-warnings-with-patterns',
    'no-warnings-and-no-patterns',
    'a-warning-with-an-empty-pattern-list',
    'a-warning-with-no-pattern-list-at-all',
]


class TestEmptyInputs:
    """Edge cases with empty warnings or patterns."""

    @pytest.mark.parametrize('warnings,patterns,expected', _EMPTY_INPUT_CASES, ids=_EMPTY_INPUT_IDS)
    def test_bucket_sizes(self, warnings: list[dict], patterns, expected: tuple[int, int, int]):
        result = _wc.categorize_warnings(warnings, patterns=patterns)

        assert (
            len(result['acceptable']),
            len(result['fixable']),
            len(result['unknown']),
        ) == expected


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


class TestDefaultMatcher:
    """categorize_warnings with unknown matcher falls back to substring."""

    def test_unknown_matcher_uses_substring(self):
        result = _wc.categorize_warnings(
            [_warn('has a substring here')],
            patterns=['a substring'],
            matcher='nonexistent_matcher',
        )
        assert len(result['acceptable']) == 1


class TestUnrecognizedType:
    """Warnings with types not in any known list route to fixable."""

    def test_unrecognized_type_goes_to_fixable(self):
        result = _wc.categorize_warnings(
            [_warn('msg', wtype='completely_new_type')],
        )
        assert len(result['fixable']) == 1
