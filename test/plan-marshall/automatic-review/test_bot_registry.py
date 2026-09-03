#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, the producer pre-filter, and the rate-limit detector DERIVE
what they need instead of hard-coding the shipped bot set across several code
files. Three bots ship today
(``coderabbit``, ``pr-agent``, ``sourcery``), and that count is asserted from
:data:`_SHIPPED_BOTS` rather than restated per test.

Coverage:

1. Shipped-standards contract — the real ``standards/*.md`` docs parse into the
   expected bot set, login map, triggers, skip-label flags, ignore patterns,
   contentless-review / actionable-content markers, rate-limit classes,
   rate-limit ETA patterns, and severity maps.
2. Derived ``BOT_KINDS`` — ``_findings_core.BOT_KINDS`` equals the registry's
   ``bot_kinds()`` (proving it is derived, not a literal).
3. Constrained-YAML reader units — the scalar/comment/block parsers over
   synthetic blocks, including quoted values carrying ``#`` and ``:``.
4. Robustness — a missing or empty standards directory yields an empty registry
   rather than raising; unknown bot kinds return empty defaults.

Module import resolves via the root conftest's marketplace PYTHONPATH setup
(``import bot_registry``).
"""

import re

import bot_registry

# The bots shipped as standards docs in this skill.
_SHIPPED_BOTS = ['coderabbit', 'pr-agent', 'sourcery']


# =============================================================================
# 1. Shipped-standards contract (the real standards/*.md docs)
# =============================================================================


def test_bot_kinds_equals_shipped_set_sorted():
    """``bot_kinds()`` returns the shipped bot set in deterministic sorted order."""
    assert bot_registry.bot_kinds() == sorted(_SHIPPED_BOTS)


def test_bot_kinds_is_deterministically_sorted():
    """Repeated calls return the same sorted list (load order is stable)."""
    first = bot_registry.bot_kinds()
    second = bot_registry.bot_kinds()
    assert first == second == sorted(first)


def test_login_to_bot_kind_maps_every_shipped_author():
    """Each shipped bot's ``author_login`` resolves to its ``bot_kind``."""
    mapping = bot_registry.login_to_bot_kind()
    assert mapping == {
        'coderabbitai': 'coderabbit',
        'cuioss-review-bot': 'pr-agent',
        'sourcery-ai': 'sourcery',
    }


def test_trigger_comment_per_bot():
    """Each bot's re-review trigger comment is read from its data block."""
    assert bot_registry.trigger_comment('coderabbit') == '@coderabbitai review'
    assert bot_registry.trigger_comment('sourcery') == '@sourcery-ai review'
    assert bot_registry.trigger_comment('pr-agent') == '/review'


def test_completion_check_name_per_bot():
    """CodeRabbit publishes an in-progress completion check-run; the others do not."""
    assert bot_registry.completion_check_name('coderabbit') == 'CodeRabbit'
    assert bot_registry.completion_check_name('sourcery') == ''
    assert bot_registry.completion_check_name('pr-agent') == ''


def test_honors_skip_label_per_bot():
    """CodeRabbit and PR-Agent honor the central skip label; Sourcery does not.

    The two ``True`` cases are honored by DIFFERENT mechanisms — CodeRabbit from its own
    central config, PR-Agent from the reusable workflow's ``if:`` guard, because its
    ``ignore_pr_labels`` setting is webhook-server-only and inert in GitHub Action mode.
    The registry records the observable behaviour, not the mechanism.
    """
    assert bot_registry.honors_skip_label('coderabbit') is True
    assert bot_registry.honors_skip_label('pr-agent') is True
    assert bot_registry.honors_skip_label('sourcery') is False


def test_ignore_patterns_are_nonempty_literal_markers():
    """Each bot exposes at least one literal whole-comment ignore marker."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '## Walkthrough' in coderabbit
    assert 'No actionable comments were generated' in coderabbit

    sourcery = bot_registry.ignore_patterns('sourcery')
    assert 'found 0 issues' in sourcery

    pr_agent = bot_registry.ignore_patterns('pr-agent')
    assert '## PR Agent Walkthrough' in pr_agent
    # The persistent-review update notice carries no review content, and is authored by the
    # reviewer identity, so without this marker it reaches triage as a candidate finding.
    # Markdown link syntax must survive the YAML round-trip verbatim.
    assert '**[Persistent review]' in pr_agent


def test_ignore_patterns_preserve_quoted_special_characters():
    """A quoted marker carrying ``:`` and HTML-comment syntax survives verbatim."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->' in coderabbit


def test_contentless_review_markers_only_declared_by_pr_agent():
    """PR-Agent declares the clean-Guide marker set; the other two declare none.

    The list is a CONJUNCTION target — every entry must be present for the
    producer's contentless layer to fire — so all three entries are asserted
    member-by-member rather than by one representative. An empty list for the
    other two bots is the fail-closed default that keeps their ingest behaviour
    byte-identical to before the field existed.

    The two assertion entries are BARE INNER TEXT, not the ``**bold**`` a human
    reads on GitHub: PR-Agent emits them inside an HTML ``<table>``, where no
    markdown is rendered, so the raw API body carries ``<strong>…</strong>``. The
    superseded ``**``-wrapped values matched no real body at all and left the
    conjunction permanently unsatisfiable, so this assertion is exact rather than
    a membership check — a re-wrapped value must turn it red here, at the data
    boundary, and not only in the producer's behavioural suite.
    """
    assert bot_registry.contentless_review_markers('pr-agent') == [
        '## PR Reviewer Guide',
        'No security concerns identified',
        'PR contains tests',
    ]
    assert bot_registry.contentless_review_markers('coderabbit') == []
    assert bot_registry.contentless_review_markers('sourcery') == []


def test_actionable_content_markers_only_declared_by_pr_agent():
    """``<details>`` is PR-Agent's disqualifying marker; the other two declare none."""
    assert bot_registry.actionable_content_markers('pr-agent') == ['<details>']
    assert bot_registry.actionable_content_markers('coderabbit') == []
    assert bot_registry.actionable_content_markers('sourcery') == []


def test_contentless_markers_survive_inline_comment_stripping():
    """Each marker's trailing ``# CONFIRMED …`` rationale is stripped, the value is not.

    Every entry in PR-Agent's block carries an inline grounding comment, and one
    of them (``## PR Reviewer Guide``) opens with the very ``#`` character that
    starts a YAML comment. A reader that stripped from the first ``#`` rather than
    from the first ``#`` OUTSIDE the quoted span would silently truncate the
    heading marker to the empty string — which the producer's fail-closed
    short-circuit would then read as "this bot declared nothing".
    """
    markers = bot_registry.contentless_review_markers('pr-agent')
    for marker in markers:
        assert marker
        assert 'CONFIRMED' not in marker
        assert marker == marker.strip()
    # The quoted-``#`` case specifically: the heading keeps its markdown prefix.
    assert '## PR Reviewer Guide' in markers
    assert bot_registry.actionable_content_markers('pr-agent') == ['<details>']


def test_severity_map_per_bot():
    """Each bot's marker->severity map is parsed as a nested mapping."""
    coderabbit = bot_registry.severity_map('coderabbit')
    assert coderabbit['nitpick'] == 'low'
    assert coderabbit['potential_issue_critical'] == 'critical'

    sourcery = bot_registry.severity_map('sourcery')
    assert sourcery['security'] == 'critical'

    # PR-Agent's map is an ASSIGNMENT map keyed on the review-table row a finding
    # came from — the observed review emits no severity vocabulary to parse. All
    # three keys are asserted so a dropped row is caught, not just the first.
    pr_agent = bot_registry.severity_map('pr-agent')
    assert pr_agent == {'security_concern': 'high', 'focus_area': 'medium', 'missing_tests': 'low'}


def test_rate_limit_class_per_bot():
    """Each bot's rate-limit class is read from its data block, per OBSERVED evidence.

    The class is what a caller branches on before deciding to wait out a refusal:
    an ``awaitable_window`` reopens on its own, a ``hard_quota`` does not reopen on
    a useful timescale, and ``unknown`` records that no refusal has ever been seen
    for that bot. The three shipped bots deliberately span all three values.
    """
    assert bot_registry.rate_limit_class('coderabbit') == 'awaitable_window'
    assert bot_registry.rate_limit_class('sourcery') == 'hard_quota'
    assert bot_registry.rate_limit_class('pr-agent') == 'unknown'


def test_rate_limit_class_fails_closed_for_absent_field(tmp_path):
    """A record that declares no class reads as ``unknown``, never as awaitable.

    ADR-009 fail-closed: assuming an undeclared refusal is waitable is the
    expensive failure — the caller burns its whole await budget and still times
    out. The default must therefore be the value that suppresses the await.
    """
    (tmp_path / 'demo.md').write_text(
        '```yaml\nbot_kind: demo\nauthor_login: demo-bot\n```\n', encoding='utf-8'
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.rate_limit_class('demo') == 'unknown'


def test_refusal_size_patterns_mark_the_diff_size_cause():
    """``refusal_size_patterns`` overlays the diff-SIZE cause onto ``refusal_patterns``.

    The orthogonal CAUSE axis to ``rate_limit_class`` (awaitability): which of a bot's
    refusals is caused by the diff being too big (remedy: a smaller diff) rather than a
    rate/budget quota (remedy: backoff). Sourcery is the only shipped bot with a
    size-caused refusal — its per-PR size ceiling — and that entry ALSO appears in
    ``refusal_patterns`` (detection stays that field's job). Both of its
    account-quota wordings are deliberately absent here, so both classify ``quota``.
    CodeRabbit and PR-Agent declare none, so every refusal they emit is a quota.
    """
    sourcery_size = bot_registry.refusal_size_patterns('sourcery')
    assert sourcery_size == ['your pull request is larger than the review limit of']
    # The size marker is a genuine subset overlay — it is also a detection pattern.
    assert sourcery_size[0] in bot_registry.refusal_patterns('sourcery')
    # Both account-quota wordings are refusals but NOT a size cause. The second is the
    # *used* phrasing (PR #1391), which the structural recogniser cannot see either.
    for quota_marker in ('reached your weekly rate limit of', 'used your own review budget of'):
        assert quota_marker in bot_registry.refusal_patterns('sourcery')
        assert quota_marker not in sourcery_size

    assert bot_registry.refusal_size_patterns('coderabbit') == []
    assert bot_registry.refusal_size_patterns('pr-agent') == []


def test_refusal_size_patterns_absent_is_empty():
    """A record that declares no size patterns reads as ``[]`` — every refusal is quota."""
    reg = bot_registry.BotRegistry(standards_dir=bot_registry.STANDARDS_DIR)
    assert reg.refusal_size_patterns('nonexistent-bot') == []


def test_refusal_size_patterns_is_a_subset_of_refusal_patterns_for_every_bot():
    """Every declared size marker is also a detection marker — the subset invariant.

    ``refusal_size_patterns`` is a CAUSE overlay on ``refusal_patterns``, never a
    second detection list: a marker that names a refusal's cause as size but is absent
    from ``refusal_patterns`` would attribute a cause to a refusal the detection layer
    never recognizes. Derived over the WHOLE live bot population so a future registry
    edit that adds a size marker outside the refusal set fails here rather than
    silently reclassifying a quota refusal as size.

    Non-vacuity: at least one shipped bot must declare a size marker, or the subset
    assertion is vacuously true and the guard proves nothing.
    """
    kinds = bot_registry.bot_kinds()
    assert kinds, 'the registry declares no bots — the sweep would be vacuous'

    total_size_markers = 0
    for kind in kinds:
        size = bot_registry.refusal_size_patterns(kind)
        refusal = bot_registry.refusal_patterns(kind)
        total_size_markers += len(size)
        assert set(size) <= set(refusal), (
            f'{kind}: refusal_size_patterns {size} is not a subset of refusal_patterns '
            f'{refusal} — a size marker must also be a detection marker'
        )

    assert total_size_markers > 0, (
        'no shipped bot declares a size marker — the subset assertion above is '
        'vacuously true; the population-derived guard needs at least one to bite'
    )


def test_rate_limit_eta_patterns_per_bot():
    """Only a bot whose notice states a reset time declares extraction patterns.

    CodeRabbit's window notice states when it reopens, so its patterns pull that
    ETA out. Sourcery declares one too: its diff-character budget notice states a
    reset days away — a concrete ETA, even though ``hard_quota`` makes it an
    unawaitable one, so extracting it is reporting rather than an invitation to
    wait. PR-Agent declares none because no refusal has been observed at all, and
    an empty list is the signal to report an absent ETA rather than invent one.
    """
    coderabbit = bot_registry.rate_limit_eta_patterns('coderabbit')
    assert coderabbit
    assert all(isinstance(pattern, str) and pattern for pattern in coderabbit)
    assert 'wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review' in coderabbit

    sourcery = bot_registry.rate_limit_eta_patterns('sourcery')
    assert sourcery
    assert all(isinstance(pattern, str) and pattern for pattern in sourcery)
    # The pattern must read the ETA out of the notice as actually observed (PR #1391) —
    # a declared-but-non-matching pattern degrades silently to "no ETA stated".
    observed = (
        "Sorry @SomeUser, you've used your own review budget of 250,000 diff characters "
        'for the last 7 days.  You can request another review in 3 days and 17 hours by '
        'commenting `@sourcery-ai review`.'
    )
    assert any(re.search(pattern, observed) for pattern in sourcery)
    assert next(
        m.group(1) for p in sourcery if (m := re.search(p, observed))
    ) == '3 days and 17 hours'

    assert bot_registry.rate_limit_eta_patterns('pr-agent') == []


def test_rate_limit_eta_patterns_are_valid_regexes():
    """Every declared ETA pattern compiles — a bad data edit is caught here, not at runtime.

    The consumer skips an uncompilable pattern rather than raising into the poll
    return path, so a malformed pattern would otherwise degrade silently to "no ETA
    stated" instead of surfacing as a defect.
    """
    for bot_kind in bot_registry.bot_kinds():
        for pattern in bot_registry.rate_limit_eta_patterns(bot_kind):
            re.compile(pattern)


def test_module_functions_match_registry_singleton():
    """The module-level functions delegate to the ``REGISTRY`` singleton."""
    assert bot_registry.bot_kinds() == bot_registry.REGISTRY.bot_kinds()
    assert bot_registry.login_to_bot_kind() == bot_registry.REGISTRY.login_to_bot_kind()
    for bot_kind in bot_registry.bot_kinds():
        assert bot_registry.trigger_comment(bot_kind) == bot_registry.REGISTRY.trigger_comment(bot_kind)
        assert bot_registry.completion_check_name(bot_kind) == bot_registry.REGISTRY.completion_check_name(bot_kind)
        assert bot_registry.ignore_patterns(bot_kind) == bot_registry.REGISTRY.ignore_patterns(bot_kind)
        assert bot_registry.contentless_review_markers(bot_kind) == (
            bot_registry.REGISTRY.contentless_review_markers(bot_kind)
        )
        assert bot_registry.actionable_content_markers(bot_kind) == (
            bot_registry.REGISTRY.actionable_content_markers(bot_kind)
        )
        assert bot_registry.rate_limit_class(bot_kind) == bot_registry.REGISTRY.rate_limit_class(bot_kind)
        assert bot_registry.rate_limit_eta_patterns(bot_kind) == bot_registry.REGISTRY.rate_limit_eta_patterns(
            bot_kind
        )


# =============================================================================
# 2. Derived BOT_KINDS (proves _findings_core.BOT_KINDS is data-derived)
# =============================================================================


def test_findings_core_bot_kinds_is_derived_from_registry():
    """``_findings_core.BOT_KINDS`` equals ``bot_registry.bot_kinds()`` — not a literal."""
    from _findings_core import BOT_KINDS

    assert list(BOT_KINDS) == bot_registry.bot_kinds()


def test_findings_core_bot_kinds_contains_every_shipped_bot():
    """The derived enum contains each shipped bot, and nothing beyond them.

    The negative half is the retirement guard: a bot whose ``standards/{bot_kind}.md``
    doc is deleted must disappear from the enum with no code change, so a stale
    ``bot_kind`` can never be stored as a finding.
    """
    from _findings_core import BOT_KINDS

    for bot_kind in _SHIPPED_BOTS:
        assert bot_kind in BOT_KINDS
    assert set(BOT_KINDS) == set(_SHIPPED_BOTS)


# =============================================================================
# 3. Constrained-YAML reader units (synthetic blocks)
# =============================================================================


def test_strip_inline_comment_outside_quotes():
    """A ``#`` preceded by whitespace outside quotes starts a comment and is dropped."""
    assert bot_registry._strip_inline_comment('true          # central config').rstrip() == 'true'


def test_strip_inline_comment_preserves_hash_inside_quotes():
    """A ``#`` inside a quoted span is NOT treated as a comment start."""
    text = '"a #hashtag value"  # real comment'
    assert bot_registry._strip_inline_comment(text).rstrip() == '"a #hashtag value"'


def test_scalar_unquotes_and_coerces_bool():
    """``_scalar`` unquotes strings and coerces ``true``/``false`` to bool."""
    assert bot_registry._scalar(' "@coderabbitai review"  # trigger') == '@coderabbitai review'
    assert bot_registry._scalar(' true  # flag') is True
    assert bot_registry._scalar(' false') is False
    assert bot_registry._scalar(' coderabbit') == 'coderabbit'


def test_extract_registry_block_selects_the_bot_kind_block():
    """The extractor returns the first ``yaml`` fence declaring ``bot_kind:``."""
    md = (
        '# Doc\n'
        '```bash\n'
        'echo not-this\n'
        '```\n'
        'prose\n'
        '```yaml\n'
        'bot_kind: example\n'
        'author_login: example-bot\n'
        '```\n'
    )
    block = bot_registry._extract_registry_block(md)
    assert block is not None
    assert 'bot_kind: example' in block
    assert 'echo not-this' not in block


def test_extract_registry_block_ignores_yaml_without_bot_kind():
    """A ``yaml`` fence with no ``bot_kind:`` line is not treated as a registry block."""
    md = '```yaml\nsome_key: value\n```\n'
    assert bot_registry._extract_registry_block(md) is None


def test_parse_block_scalars_list_and_map():
    """``_parse_block`` reads top-level scalars, a list, and a nested map."""
    block = (
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'trigger_comment: "@demo review"\n'
        'honors_skip_label: true\n'
        'ignore_patterns:\n'
        '  - "## Heading"\n'
        '  - "no-op line"   # a comment\n'
        'severity_map:\n'
        '  issue: high\n'
        '  nitpick: low\n'
    )
    data = bot_registry._parse_block(block)
    assert data['bot_kind'] == 'demo'
    assert data['author_login'] == 'demo-bot'
    assert data['trigger_comment'] == '@demo review'
    assert data['honors_skip_label'] is True
    assert data['ignore_patterns'] == ['## Heading', 'no-op line']
    assert data['severity_map'] == {'issue': 'high', 'nitpick': 'low'}


def test_registry_loads_from_synthetic_standards_dir(tmp_path):
    """A synthetic standards dir with one data block loads as one bot."""
    (tmp_path / 'demo.md').write_text(
        '# Demo\n'
        '```yaml\n'
        'bot_kind: demo\n'
        'author_login: demo-bot\n'
        'trigger_comment: "@demo review"\n'
        'honors_skip_label: false\n'
        'ignore_patterns:\n'
        '  - "drop me"\n'
        'severity_map:\n'
        '  issue: medium\n'
        '```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert reg.bot_kinds() == ['demo']
    assert reg.login_to_bot_kind() == {'demo-bot': 'demo'}
    assert reg.trigger_comment('demo') == '@demo review'
    assert reg.honors_skip_label('demo') is False
    assert reg.ignore_patterns('demo') == ['drop me']
    assert reg.severity_map('demo') == {'issue': 'medium'}


def test_registry_skips_docs_without_a_registry_block(tmp_path):
    """A standards doc with no bot_kind data block contributes no bot."""
    (tmp_path / 'prose-only.md').write_text('# Just prose\n\nNo data block here.\n', encoding='utf-8')
    (tmp_path / 'real.md').write_text(
        '```yaml\nbot_kind: real\nauthor_login: real-bot\n```\n', encoding='utf-8'
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)
    assert reg.bot_kinds() == ['real']


# =============================================================================
# 4. Robustness — missing dir and unknown keys never raise
# =============================================================================


def test_missing_standards_dir_yields_empty_registry(tmp_path):
    """A non-existent standards directory yields an empty registry, not an error."""
    reg = bot_registry.BotRegistry(standards_dir=tmp_path / 'does-not-exist')
    assert reg.bot_kinds() == []
    assert reg.login_to_bot_kind() == {}


def test_unknown_bot_kind_returns_empty_defaults():
    """Accessors return empty defaults (not raise) for an unregistered bot_kind."""
    assert bot_registry.trigger_comment('nope') == ''
    assert bot_registry.completion_check_name('nope') == ''
    assert bot_registry.honors_skip_label('nope') is False
    assert bot_registry.ignore_patterns('nope') == []
    assert bot_registry.severity_map('nope') == {}
    # The content-aware marker accessors fail closed for an unregistered kind too —
    # an empty required list is what stops the producer's layer 3 from ever firing.
    assert bot_registry.contentless_review_markers('nope') == []
    assert bot_registry.actionable_content_markers('nope') == []
    # The rate-limit accessors fail closed for an unregistered kind too.
    assert bot_registry.rate_limit_class('nope') == 'unknown'
    assert bot_registry.rate_limit_eta_patterns('nope') == []


def test_review_body_summary_patterns_are_registry_owned():
    """The status-summary signature is per-bot DATA, not a literal in a counter.

    A `review_body` can be either the bot's consolidated findings or its
    "Actionable comments posted: N" status line, and the counting rule
    (`bot-participation-contract.md` § "The counting rule") excludes the latter.
    Which literal marks it is a per-bot fact, so it belongs in the registry beside
    `ignore_patterns` and `refusal_patterns` — a counter that hard-codes the login
    or the bot_kind is the hard-coded-population archetype one directory away from
    the registry that exists to prevent it.
    """
    assert bot_registry.review_body_summary_patterns('coderabbit') == [
        'Actionable comments posted:',
    ]


def test_review_body_summary_patterns_default_empty_and_fail_closed():
    """A bot that declares none never has a review_body reclassified as a summary.

    Empty is the fail-closed default in the direction that matters HERE: for the
    gate-escape count, dropping a substantive review_body under-counts escapes and
    makes the gates look better than they are. A bot that has not opted in keeps
    every review_body counted.
    """
    assert bot_registry.review_body_summary_patterns('sourcery') == []
    assert bot_registry.review_body_summary_patterns('pr-agent') == []
    assert bot_registry.review_body_summary_patterns('no-such-bot') == []


def test_bot_kind_for_login_normalises_casing_and_the_bot_suffix():
    """The login→bot_kind lookup tolerates the two drifts real logins carry.

    `github_pr` stores `author` VERBATIM, and GraphQL author logins arrive both
    with a `[bot]` suffix and with non-canonical casing — the repo's own fixtures
    use `coderabbitai[bot]`. A raw exact-match lookup silently resolves those to
    nothing, which disables every per-bot rule keyed off the author for exactly the
    records that have no `bot_kind` to fall back on.

    The registry owns the login map, so the normalised lookup belongs here rather
    than being re-implemented by each consumer.
    """
    assert bot_registry.bot_kind_for_login('coderabbitai') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('coderabbitai[bot]') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('CodeRabbitAI') == 'coderabbit'
    assert bot_registry.bot_kind_for_login('CodeRabbitAI[bot]') == 'coderabbit'


def test_bot_kind_for_login_returns_empty_for_a_human_or_absent_login():
    """A non-bot author resolves to no bot_kind — never to a wrong one."""
    assert bot_registry.bot_kind_for_login('some-human') == ''
    assert bot_registry.bot_kind_for_login('') == ''
    assert bot_registry.bot_kind_for_login(None) == ''
