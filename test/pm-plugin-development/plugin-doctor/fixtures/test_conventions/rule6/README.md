# Rule 6-7 fixtures — the module-content rules

`test_test_conventions_rule6.py` covers the two warning-severity rules that
govern what a collected module contains: `test-module-preamble-boilerplate` and
`test-docstring-historical-prose`. The module-shape rules live in
`test_test_conventions_rule4.py` (see `../rule4/`).

The tests build their fixture trees dynamically via pytest's `tmp_path` rather
than checking in static fixture files, matching the convention of the sibling
rule directories.

Static fixtures would additionally be self-defeating here: a checked-in fixture
carrying a hand-rolled preamble or a historical citation would trip these rules
against the real `test/` tree during a whole-tree sweep and inflate every count
the standards measure.

Scenarios covered:

**`test-module-preamble-boilerplate`**

- `test_spec_from_file_location_is_flagged` — hand-rolled loader preamble.
- `test_deep_parent_chain_is_flagged` — a depth-3 `.parent` chain, with its
  depth in the finding details.
- `test_shallow_parent_chain_is_not_flagged` — a depth-2 hop is ordinary path
  work.
- `test_conftest_helpers_are_not_flagged` — the sanctioned helpers.
- `test_resolve_does_not_break_the_chain` — a `.resolve()` hop between
  `Path(__file__)` and the chain still counts.
- `test_parents_index_is_flagged` — `parents[N]` is the indexed spelling of an
  N-deep chain. Without this the rule's count would be gameable: respelling a
  flagged chain as `parents[N]` would clear the finding while changing nothing.
- `test_mixed_chain_and_index_compose` — a `.parent` chain feeding `parents[N]`
  counts as their sum, so the mixed spelling is not an escape from the count.
- `test_negative_and_non_constant_index_are_not_flagged` — a negative or
  computed index is not a directory count.
- `test_shallow_parents_index_is_not_flagged` — `parents[2]` is below threshold.
- `test_one_chain_yields_one_finding` — a depth-4 chain reports once, not once
  per suffix.

**`test-docstring-historical-prose`**

- `test_lesson_id_in_docstring_is_flagged` — lesson-id citation.
- `test_pr_reference_in_docstring_is_flagged` — PR citation.
- `test_plan_deliverable_id_in_comment_is_flagged` — comments are prose too.
- `test_unlettered_deliverable_ordinal_is_flagged` — `Deliverable 2` is the same
  citation as `deliverable D2`; a matcher carrying only the lettered form reports
  one half of a corpus that writes both.
- `test_bare_record_number_is_flagged` — a record number cited without a `PR`
  prefix.
- `test_prefixed_single_digit_record_is_still_flagged` — the two-digit bound is
  local to the BARE form, so an unambiguous `PR #7` still fires. Pinned beside the
  bound so a later "simplification" onto both alternatives cannot pass silently.
- `test_record_number_opening_a_docstring_is_flagged` — a citation at the very
  first character of a docstring. The bound that keeps a comment's own `#`
  delimiter from reading as a citation must not also silence this.
- `test_single_digit_bare_number_is_not_flagged` — a one-digit bare number is
  intra-document enumeration, not a record id.
- `test_number_inside_a_hyphenated_compound_is_not_flagged` — `pre-<n>` names a
  schema or code era the corpus asserts on, so the number is the test's own data.
- `test_comment_delimiter_does_not_read_as_a_record_number` — a comment's `#` is
  punctuation the tokenizer supplies, not the author's citation.
- `test_present_tense_docstring_is_not_flagged` — negative control.
- `test_citation_shape_as_string_data_is_not_flagged` — the rule's structural
  discriminator: the same shape as string-literal test data is not a citation.
- `test_finding_reports_the_citation_line_not_the_declaration` — the reported
  line is the citation's own line, since the finding exists to be navigated to.
- `test_backticked_id_named_as_a_value_is_not_flagged` and
  `test_quoted_id_named_as_a_value_is_not_flagged` — the inline-literal exemption:
  prose has to name values as well as cite records, and formatting is what tells
  them apart.
- `test_bare_id_beside_a_backticked_one_is_still_flagged` — the exemption is per
  occurrence, so backticking one identifier cannot launder the sentence.
- `test_double_backticked_lesson_citation_is_still_flagged` — a `lesson` prefix
  outside the span is a narrative citation whatever the span's spelling.
- `test_possessive_apostrophe_does_not_open_a_literal_span` and
  `test_two_apostrophes_on_one_line_do_not_open_a_literal_span` — English prose is
  full of apostrophes, and an apostrophe is not a quote delimiter. Both shapes were
  observed silently exempting real citations.
- `test_one_finding_per_prose_segment` — one finding per segment, not per
  matching pattern.

**Shared**

- `test_missing_test_root_is_a_noop` — both rules return no findings when the
  test root does not exist.
