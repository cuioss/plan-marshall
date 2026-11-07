#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the ``analyze`` three-layer landing analysis.

The three-layer analysis makes ``analyze`` read every full-ship landing on three
layers — **specified**, **implemented** and **correct** — by reading alone, through
one read-only leaf per landing. Two contract files are read here and neither is
written:

- ``plan-orchestrator/workflow/analyze.md`` — Step 4's analysis step (the layer
  definitions, the read-only limit, the ``not shown by reading`` tag, the full
  dispatch contract), Step 2's dispatch index entry (the resolve form and the
  one-leaf-per-landing rule), and the per-layer routing rule.
- ``plan-orchestrator/templates/landing-analysis.md`` — the
  ``## Three-Layer Analysis`` section: one block per layer, the conformance list
  for the project's own rules, and the verdict line.

The third carrier — the Dispatch Decision Rule's numbered index in
``orchestration-model.md`` — is pinned by
``test_orchestrator_dispatch_workflow_pin.py``, which also pins this dispatch's
concrete ``--workflow`` doc and surface.

Every assertion below derives its population from the document text it names, and
each helper that locates a block publishes the marker it could not find rather
than returning an empty string — a green over a renamed heading would otherwise
claim the contract was verified when nothing was read.

The "no size qualifier" absence assertion is scoped to the three-layer blocks
only — Step 4's analysis block and the Step 2 index bullet — never document-wide:
Step 2's corroboration dispatch keeps its own "when the read burden is large"
gate, and a document-wide absence check would either fail on that legitimate
wording or force it out of the doc. The three-layer read, stated in Step 4, is
the one that is unconditional.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

#: The corpus verdict vocabulary, derived from the emitter's own constant rather
#: than re-listed: `corpus set-verdict` accepts exactly these values, and a literal
#: copy here would drift the moment that set changes.
_orch = load_script_module('plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script')
CORPUS_VERDICTS: tuple[str, ...] = tuple(f'`{value}`' for value in _orch.VERDICT_VALUES)

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_PLAN_ORCHESTRATOR = _PLAN_MARSHALL / 'plan-orchestrator'
_ANALYZE_MD = _PLAN_ORCHESTRATOR / 'workflow' / 'analyze.md'
_LANDING_TEMPLATE = _PLAN_ORCHESTRATOR / 'templates' / 'landing-analysis.md'
_THREE_LAYER_DOC = _PLAN_ORCHESTRATOR / 'standards' / 'three-layer-analysis.md'

#: Markers the helpers below anchor on. Literal rather than regex because each one
#: is a contract phrase the documents are expected to carry verbatim.
_ANALYSIS_HEADING = '#### The three-layer analysis'
_ROUTING_HEADING = '#### Routing what the three-layer analysis finds'
_BEFORE_THE_REPORT = '1. Write the landing report'
_DISPATCH_MARKER = '- **Dispatchable** — the Step 4 three-layer landing analysis'
_DISPATCH_END = '\n- **Inline-only**'
_LAYERS: tuple[tuple[int, str], ...] = ((1, 'specified'), (2, 'implemented'), (3, 'correct'))

#: The three-layer dispatch's own level resolution, as it must appear in the Step 2
#: index. The exact ``--workflow`` value is what pins the doc the leaf loads.
_DISPATCH_WORKFLOW_DOC = 'plan-marshall:plan-orchestrator/standards/three-layer-analysis.md'

#: The one-line summary verdict the template carries, naming every layer.
_VERDICT_LINE_RE = re.compile(r'(?im)^- \*\*Verdict:\*\*.*layer 1.*layer 2.*layer 3')

#: The three columns of the Step 4 mapping table this file derives from. A table
#: that renames or drops one of them fails the helper rather than parsing half.
_VERDICT_COLUMN = 'Leaf `verdict`'
_POLARITY_COLUMN = 'Leaf `polarity`'
_PERSISTED_COLUMN = 'Persisted corpus verdict'


def _ticked_values(cell: str) -> list[str]:
    """The backticked tokens of one table cell, in order."""
    return [f'`{value}`' for value in re.findall(r'`([^`]+)`', cell)]


def _mapping_rows(routing: str) -> list[dict[str, str]]:
    """The Step 4 mapping table as row dicts keyed by its own header cells."""
    lines = [line for line in routing.splitlines() if line.strip().startswith('|')]
    assert len(lines) >= 3, 'the routing rule carries no mapping table (a header, a separator and at least one row)'
    header = [cell.strip() for cell in lines[0].strip().strip('|').split('|')]
    for column in (_VERDICT_COLUMN, _POLARITY_COLUMN, _PERSISTED_COLUMN):
        assert column in header, f'the mapping table has no {column!r} column — header read: {header}'
    rows = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        rows.append(dict(zip(header, cells, strict=False)))
    assert rows, 'the mapping table carries no data row'
    return rows


def _leaf_vocabulary(field: str) -> tuple[str, ...]:
    """The values the leaf document declares for one return field, as backticked tokens."""
    match = re.search(rf'`{field}` is one of (.+?);', _read(_THREE_LAYER_DOC))
    assert match, f'the leaf document declares no closed vocabulary for {field!r}'
    return tuple(_ticked_values(match.group(1)))


def _read(path: Path) -> str:
    assert path.is_file(), f'the contract source is missing: {path}'
    return path.read_text(encoding='utf-8')


def _between(text: str, start_marker: str, end_marker: str, source: str) -> str:
    """The text from ``start_marker`` up to the next ``end_marker``."""
    start = text.find(start_marker)
    assert start != -1, f'{source}: the contract block {start_marker!r} was not found'
    tail = text[start:]
    end = tail.find(end_marker)
    assert end != -1, f'{source}: the contract block {start_marker!r} has no closing marker {end_marker!r}'
    return tail[:end]


def _step4(text: str) -> str:
    return _between(text, '### Step 4:', '### Step 5:', 'analyze.md')


def _analysis_block(text: str) -> str:
    return _between(_step4(text), _ANALYSIS_HEADING, _ROUTING_HEADING, 'analyze.md Step 4')


def _routing_block(text: str) -> str:
    return _between(_step4(text), _ROUTING_HEADING, _BEFORE_THE_REPORT, 'analyze.md Step 4')


def _dispatch_bullet(text: str) -> str:
    step2 = _between(text, '### Step 2: Verify against ground truth', '#### Step 2b:', 'analyze.md')
    return _between(step2, _DISPATCH_MARKER, _DISPATCH_END, 'analyze.md Step 2')


def _layer_block(analysis: str, number: int) -> str:
    """The definition bullet of one layer, up to the next layer's bullet.

    Layer 3 has no following bullet, so its block ends at the limit paragraph
    that closes the definitions. Without that bound the helper would return the
    rest of the analysis block, and a keyword moved out of the layer-3 definition
    into the limit or dispatch paragraph would keep the definition assertion green.
    """
    marker = f'**Layer {number} — {dict(_LAYERS)[number]}.**'
    start = analysis.find(marker)
    assert start != -1, f'analyze.md Step 4: the layer definition {marker!r} was not found'
    tail = analysis[start + len(marker) :]
    following = [f'**Layer {n} — {name}.**' for n, name in _LAYERS if n > number]
    stops = [tail.find(m) for m in following if tail.find(m) != -1]
    if number == max(n for n, _ in _LAYERS):
        stops.append(tail.find('The limit is absolute:'))
    stops = [stop for stop in stops if stop != -1]
    assert stops, f'analyze.md Step 4: the layer {number} block has no closing marker'
    return tail[: min(stops)]


# =============================================================================
# (D1) Step 4 carries the three-layer analysis; the template carries its section
# =============================================================================


class TestThreeLayerStepFourContract:
    def test_the_analysis_sits_before_the_report_is_written(self):
        step4 = _step4(_read(_ANALYZE_MD))

        analysis_at = step4.find(_ANALYSIS_HEADING)
        report_at = step4.find(_BEFORE_THE_REPORT)

        assert analysis_at != -1, (
            f'analyze.md Step 4 carries no {_ANALYSIS_HEADING!r} block — a landing can still '
            'pass the fidelity check while resting on a wrong spec premise, an unexplained '
            'file, or a defect in the merged code'
        )
        assert report_at != -1, 'analyze.md Step 4 no longer carries the item 1 report write'
        assert analysis_at < report_at, (
            'the three-layer analysis is placed after item 1 writes the report — its findings '
            'must reach the report, so it has to run before that Write'
        )

    def test_each_layer_carries_its_definition(self):
        analysis = _analysis_block(_read(_ANALYZE_MD))

        expectations = {
            1: ('premises', 'Done-when', '`main`'),
            2: ('traces to code', 'test that can fail', 'no deliverable explains', 'does not bear out'),
            3: ('defects', 'invariants', 'boundaries', 'error paths', 'concurrency', 'resource handling'),
        }
        for number, keywords in expectations.items():
            block = _layer_block(analysis, number)
            for keyword in keywords:
                assert keyword in block, (
                    f'layer {number} ({dict(_LAYERS)[number]}) does not name {keyword!r} — its '
                    f'definition has drifted from the contract. Block read: {block!r}'
                )

    def test_the_read_only_limit_and_the_not_shown_tag_are_stated(self):
        analysis = _analysis_block(_read(_ANALYZE_MD)).lower()

        assert 'by reading, no build, no test run, no write' in analysis, (
            'the three-layer analysis does not state the "by reading, no build, no test run, '
            'no write" limit — a reading step without it invites a build or a write'
        )
        assert '`not shown by reading`' in analysis, (
            'the three-layer analysis does not carry the `not shown by reading` tag — what only '
            'a run could show would be reported as clean'
        )

    def test_the_analysis_applies_to_a_full_ship_only(self):
        analysis = _analysis_block(_read(_ANALYZE_MD))

        assert re.search(r'(?i)full ship only', analysis), (
            'the three-layer analysis is not scoped to a full ship — a mid-flight observation '
            'has no merged code to read'
        )
        assert re.search(r'(?i)mid-flight observation \(Step 5\) is unchanged', analysis), (
            'the three-layer analysis does not state that Step 5 is unchanged'
        )

    def test_the_template_carries_the_three_layer_section(self):
        template = _read(_LANDING_TEMPLATE)
        section = _between(template, '## Three-Layer Analysis', '## Metrics and Anomalies', 'landing-analysis.md')

        for number, name in _LAYERS:
            assert f'### Layer {number} — {name.title()}' in section, (
                f'the landing template carries no block for layer {number} ({name})'
            )
            assert f'**Layer {number} verdict:**' in section, (
                f'the landing template carries no verdict for layer {number} ({name})'
            )
        assert 'Conformance' in section, 'the landing template carries no conformance list'
        assert '`CLAUDE.md`' in section and 'code rules' in section, (
            "the conformance list does not name the project's own rules — `CLAUDE.md` and the code rules it names"
        )
        assert '{conforms \\| deviates \\| not_shown_by_reading}' in section, (
            'the conformance table renders a verdict outside the return vocabulary — it must use the '
            '`not_shown_by_reading` token the dispatch contract declares'
        )
        assert _VERDICT_LINE_RE.search(section), (
            'the landing template carries no summary verdict line naming layer 1, layer 2 and '
            'layer 3 — a layer-3 defect must be visible without reading the section'
        )


# =============================================================================
# (D2 doc half) always-dispatched, one read-only leaf per landing
# =============================================================================


class TestThreeLayerAlwaysDispatched:
    def test_the_step_two_index_names_the_three_layer_sub_step(self):
        step2 = _between(_read(_ANALYZE_MD), '### Step 2: Verify against ground truth', '#### Step 2b:', 'analyze.md')

        assert re.search(r'\*\*Six\*\* sub-steps', step2), (
            'Step 2 still declares five dispatchable sub-steps — the three-layer landing analysis '
            'is not in the complete index, so a reader would not find the dispatch'
        )
        assert 'three-layer landing analysis' in step2, (
            "Step 2's dispatchable index does not name the three-layer landing analysis"
        )

    def test_step_four_states_the_dispatch_contract_as_written(self):
        """D2's done-when names Step 4, so the contract is pinned THERE as well.

        Pinning only the Step 2 index bullet would leave a size qualifier added to
        Step 4's own paragraph unobserved: the absence check would be looking at a
        different block than the one that tells the orchestrator when to dispatch.
        """
        analysis = _analysis_block(_read(_ANALYZE_MD))
        lowered = analysis.lower()

        assert 'every time, with no size qualifier' in lowered, (
            'Step 4 does not state that the analysis is dispatched every time, with no size qualifier'
        )
        for qualifier in ('when large', 'when the read burden is large'):
            assert qualifier not in lowered, (
                f'Step 4 carries the optional-dispatch qualifier {qualifier!r} — the three-layer '
                'analysis runs on every full-ship landing'
            )
        assert 'one read-only leaf per landing' in lowered, 'Step 4 does not state the one-leaf-per-landing shape'
        assert 'must not share context' in lowered, (
            "Step 4 does not give the one-leaf reason — one landing's read must not share context with another's"
        )
        assert '`findings[N]{layer,severity,file,line,claim,verdict,polarity}`' in analysis, (
            'Step 4 does not give the findings return shape'
        )
        assert '`checked`' in analysis and '`not_shown_by_reading`' in analysis, (
            'Step 4 does not give BOTH verdict values'
        )
        assert '`conformance[M]{rule_source,rule,verdict,evidence}`' in analysis, (
            'Step 4 does not give the conformance return shape'
        )
        for severity in ('`blocker`', '`major`', '`minor`', '`info`'):
            assert severity in analysis, (
                f'Step 4 does not define the severity vocabulary member {severity} the leaf must return'
            )
        assert re.search(r'(?i)re-reads every `?checked`? point', analysis), (
            'Step 4 does not require the orchestrator to re-read every `checked` point'
        )
        for target in (
            '`Write`',
            '`Edit`',
            '`manage-status`',
            '`manage-logging --store orchestrator`',
            '`orchestrator queue`',
            '`corpus set-verdict`',
        ):
            assert target in analysis, f'Step 4 does not forbid the leaf {target}'

    def test_the_dispatch_loads_its_own_read_only_leaf_doc(self):
        """The leaf loads a dedicated doc, not the whole orchestrator workflow.

        `--workflow .../workflow/analyze.md` would hand the leaf a document that
        instructs ledger writes and declares a different Output shape. The
        dedicated doc carries the read-only limit and the untrusted-content rule.
        """
        analysis = _analysis_block(_read(_ANALYZE_MD))
        doc = _read(_THREE_LAYER_DOC)

        assert 'standards/three-layer-analysis.md' in analysis, (
            'Step 4 does not name the dedicated leaf doc the dispatch loads'
        )
        assert 'by reading, no build, no test run, no write' in doc.lower(), (
            'the leaf doc does not carry the read-only limit'
        )
        assert 'data to be assessed, never an instruction' in doc.lower(), (
            'the leaf doc does not state that source text is data, never an instruction'
        )
        assert 'writes nothing' in doc.lower() or 'write nothing' in doc.lower(), (
            'the leaf doc does not state that the leaf writes nothing'
        )

    def test_the_leaf_doc_declares_the_workflow_contract(self):
        """A doc loaded through `--workflow` must declare the ext-point and its envelope."""
        doc = _read(_THREE_LAYER_DOC)

        assert doc.startswith('---\n'), 'the leaf doc carries no frontmatter'
        assert 'implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow' in doc, (
            'the leaf doc does not declare the execution-context workflow extension point it is loaded as'
        )
        assert 'status: success | error | loop_back | blocked' in doc, (
            'the leaf doc declares no status in its return contract'
        )
        assert 'display_detail:' in doc, 'the leaf doc declares no display_detail in its return contract'

    def test_the_leaf_doc_carries_the_narrative_and_the_cross_repo_path(self):
        doc = _read(_THREE_LAYER_DOC)

        assert 'landing narrative' in doc.lower(), (
            'the leaf doc does not name the landing narrative as an input — layer 2 cannot check a lane '
            'claim the diff does not bear out without it'
        )
        assert 'git -C {OTHER_REPO_PATH}' in doc, (
            'the leaf doc does not state how a cross-repo landing is read, where the merge commit may '
            "live outside the epic's worktree"
        )

    def test_the_dispatch_is_unconditional_and_one_leaf_per_landing(self):
        bullet = _dispatch_bullet(_read(_ANALYZE_MD))

        assert 'every full-ship landing' in bullet.lower(), (
            'the three-layer dispatch is not stated as running on every full-ship landing'
        )
        assert 'no size qualifier' in bullet.lower(), (
            'the three-layer dispatch does not say it runs without a size qualifier'
        )
        for qualifier in ('when large', 'when the read burden is large'):
            assert qualifier not in bullet.lower(), (
                f'the three-layer dispatch still carries the optional-dispatch qualifier {qualifier!r} '
                '— the analysis runs on every full-ship landing, not only on large reads'
            )

        assert 'one leaf per landing' in bullet.lower(), 'the dispatch does not state the one-leaf-per-landing shape'
        assert 'one envelope' in bullet.lower() and 'does not apply' in bullet.lower(), (
            'the dispatch does not record why the one-envelope-per-message drafting rule does not '
            'apply to the per-landing read'
        )
        assert 'must not share context' in bullet.lower(), (
            "the dispatch does not state the reason for one leaf per landing — one landing's "
            "read must not share context with another's"
        )

    def test_the_dispatch_states_the_return_shape_and_both_verdicts(self):
        bullet = _dispatch_bullet(_read(_ANALYZE_MD))

        assert '`findings[N]{layer,severity,file,line,claim,verdict,polarity}`' in bullet, (
            'the dispatch does not state the return shape `findings[N]{layer,severity,file,line,claim,verdict,polarity}`'
        )
        assert '`checked`' in bullet and '`not_shown_by_reading`' in bullet, (
            'the dispatch does not give BOTH `verdict` values (`checked` and `not_shown_by_reading`)'
        )
        assert '`conformance[M]{rule_source,rule,verdict,evidence}`' in bullet, (
            "the dispatch does not declare the conformance return shape for the project's own rules"
        )

    def test_the_dispatch_carries_the_resolved_level_and_its_workflow_doc(self):
        bullet = _dispatch_bullet(_read(_ANALYZE_MD))

        assert 'effort resolve-target --role orchestrator.analyze' in bullet, (
            'the dispatch does not resolve its level on the `orchestrator.analyze` surface'
        )
        for fact in (
            '--plan-id none',
            '--caller plan-marshall:persona-plan-orchestrator',
            f'--workflow {_DISPATCH_WORKFLOW_DOC}',
        ):
            assert fact in bullet, (
                f'the dispatch resolve omits {fact!r} — the four facts are what make the resolve '
                'seam emit the [DISPATCH] record'
            )
        assert '`execution-context-{level}`' in bullet and 'S1' in bullet, (
            'the dispatch does not name its vehicle and the S1 read-only instruction'
        )

    def test_the_orchestrator_re_reads_what_it_records_as_checked(self):
        bullet = _dispatch_bullet(_read(_ANALYZE_MD))

        assert re.search(r'(?i)re-reads every `?checked`? point', bullet), (
            'the dispatch does not require the orchestrator to re-read every `checked` point'
        )
        assert re.search(r'(?i)records which points it re-read', bullet), (
            'the dispatch does not require the orchestrator to record which points it re-read'
        )
        assert 'unverified lead' in bullet, (
            'a point the orchestrator cannot re-read is not recorded as an unverified lead'
        )

    def test_the_leaf_is_forbidden_every_ledger_write(self):
        bullet = _dispatch_bullet(_read(_ANALYZE_MD))

        assert 'writes nothing' in bullet.lower(), 'the dispatch does not state that the leaf writes nothing'
        for target in (
            '`Write`',
            '`Edit`',
            '`manage-status`',
            '`manage-logging --store orchestrator`',
            '`orchestrator queue`',
            '`corpus set-verdict`',
        ):
            assert target in bullet, (
                f'the dispatch does not forbid the leaf {target} — the draft crosses the dispatch '
                'edge as data, and every ledger write stays with the orchestrator'
            )


# =============================================================================
# (D3) Routing by layer, nothing fixed inline
# =============================================================================


class TestThreeLayerRouting:
    def test_a_layer_three_defect_goes_to_the_operator_at_once(self):
        routing = _routing_block(_read(_ANALYZE_MD))

        assert 'reported to the operator' in routing and 'at once' in routing, (
            'the routing rule does not report a layer-3 defect to the operator at once'
        )
        assert 'never fixed inline' in routing, 'the routing rule does not forbid fixing a layer-3 defect inline'
        assert "only on the operator's word" in routing, (
            'the routing rule does not reserve the staged fix-plan decision to the operator'
        )

    def test_a_layer_one_or_two_finding_names_the_spec_to_correct(self):
        routing = _routing_block(_read(_ANALYZE_MD))

        assert 'name the spec' in routing, (
            'the routing rule does not require a layer-1/2 finding to name the spec to correct'
        )
        assert 'same-act rule' in routing, (
            'the routing rule does not point a corpus-naming finding at the same-act fold rule'
        )
        assert 'Step 2b' in routing and 'corpus set-verdict' in routing, (
            "the routing rule does not state that a corroborated claim persists through Step 2b's `corpus set-verdict`"
        )
        assert 'Step 4 runs after Step 2b' in routing, (
            'the routing rule does not resolve the ordering: Step 2b has already run when Step 4 '
            'settles the claim, so the `corpus set-verdict` call is made at Step 4'
        )
        assert CORPUS_VERDICTS, 'the corpus verdict vocabulary resolved empty — the routing check would be vacuous'
        for corpus_verdict in CORPUS_VERDICTS:
            assert corpus_verdict in routing, (
                f'the routing rule does not name the corpus verdict {corpus_verdict} the call accepts — '
                "passing the analysis's own `checked` / `not_shown_by_reading` value would be refused"
            )

    def test_the_template_verdict_line_names_the_layers_with_findings(self):
        template = _read(_LANDING_TEMPLATE)
        section = _between(template, '## Three-Layer Analysis', '## Metrics and Anomalies', 'landing-analysis.md')

        assert re.search(r'(?i)every layer that carried a finding', section), (
            "the template's verdict line does not say it names every layer that carried a finding"
        )


# =============================================================================
# (D1 corrections) not-shown-by-reading at every layer, one report write,
# the corpus mapping, the Dispatch choice, the conformance spelling, and the
# leaf's cross-repo field and no-fetch rule
# =============================================================================

#: The one spelling of the conformance return shape. `[M]` — one row per rule
#: checked, not one per finding — is the leaf document's spelling, and Step 4
#: must not drift back to `[N]`, which reads as one row per finding.
_CONFORMANCE_SHAPE = 'conformance[M]{rule_source,rule,verdict,evidence}'


def _template_section() -> str:
    return _between(
        _read(_LANDING_TEMPLATE), '## Three-Layer Analysis', '## Metrics and Anomalies', 'landing-analysis.md'
    )


class TestThreeLayerCorrections:
    def test_the_layer_one_and_two_summary_slots_offer_not_shown_by_reading(self):
        verdict_line = next(
            (line for line in _template_section().splitlines() if line.startswith('- **Verdict:**')),
            '',
        )

        assert verdict_line, 'the template carries no summary Verdict line'
        for layer in (1, 2):
            assert re.search(rf'(?i)layer {layer} \{{clean \| findings \| not shown by reading\}}', verdict_line), (
                f'the layer-{layer} summary slot offers no "not shown by reading" value, so a point only a '
                'run could show is forced to `clean`'
            )

    def test_the_layer_one_and_two_verdict_slots_offer_not_shown_by_reading(self):
        section = _template_section()

        for layer in (1, 2):
            expected = f'**Layer {layer} verdict:** {{clean | findings — N | not shown by reading — N}}'
            assert expected in section, (
                f'the layer-{layer} verdict slot cannot record a point only a run could show — it must offer '
                'the same third value layer 3 has'
            )

    def test_the_dispatch_line_offers_the_inline_fallback(self):
        section = _template_section()
        dispatch_line = next(
            (line for line in section.splitlines() if line.startswith('- **Dispatch:**')),
            '',
        )

        assert dispatch_line, 'the template carries no Dispatch line'
        assert (
            '{one read-only leaf per landing | the orchestrator inline, because the dispatch did not return}'
        ) in dispatch_line, (
            "the template's Dispatch line does not carry the same choice the section preamble does, so a "
            'dispatch that did not return has no legal value to record'
        )
        assert 'why this landing got its own leaf, or why the dispatch did not return' in dispatch_line, (
            'the Dispatch reason clause does not cover the inline arm'
        )

    def test_step_four_hands_the_analysis_to_the_single_report_write(self):
        analysis = _analysis_block(_read(_ANALYZE_MD))

        assert "as data for item 1's single `Write`" in analysis, (
            "Step 4 does not say the analysis block returns its result as data for item 1's single Write"
        )
        assert 'write the result into' not in analysis.lower(), (
            'Step 4 still tells the analysis block to write the landing report itself, so the report is written twice'
        )
        assert 'landings/PLAN-NN.md' not in analysis, (
            'the analysis block still names the landing report file as a write target, so the report is written twice'
        )

    def test_the_inline_only_index_names_only_the_item_one_write(self):
        """Guard: the Inline-only APPLY index stays at exactly one `Write`.

        This is a guard, not a red-first test: the index is untouched by the change
        that introduced the single report write, so it holds at the parent too. It
        stays to catch a second landing-report write slipping into the index.
        """
        text = _read(_ANALYZE_MD)
        inline_only = _between(text, _DISPATCH_END, '#### Step 2b:', 'analyze.md Step 2')

        assert inline_only.count('`Write`') == 1, (
            'the Inline-only APPLY index names more than one `Write` — a second landing-report write slipped in'
        )
        assert 'the Step 4 item 1 `Write` of `{epic_dir}/landings/PLAN-NN.md`' in inline_only, (
            "the Inline-only APPLY index does not name item 1's Write of the landing report"
        )

    def test_the_routing_maps_the_leaf_vocabulary_to_the_corpus_vocabulary(self):
        """The mapping is derived from the routing table, not from a hard-coded list.

        The table's own persisted-verdict column is the population, so a table
        whose rows were swapped, dropped or pointed at a value the script refuses
        fails here — a phrase-presence check over the same text would pass on any
        arrangement of the words.
        """
        routing = _routing_block(_read(_ANALYZE_MD))
        rows = _mapping_rows(routing)
        persisted = {
            value for row in rows for value in _ticked_values(row[_PERSISTED_COLUMN]) if value in CORPUS_VERDICTS
        }

        assert CORPUS_VERDICTS, 'the corpus verdict vocabulary resolved empty — the mapping check would be vacuous'
        assert persisted == set(CORPUS_VERDICTS), (
            f'the mapping table does not reach every corpus verdict the script accepts: table={sorted(persisted)} '
            f'vocabulary={sorted(CORPUS_VERDICTS)}'
        )
        assert re.search(r'(?i)two orchestrator runs persist the same value', routing), (
            'the routing rule does not state that the mapping is deterministic'
        )
        assert re.search(r'(?i)layer-2 or layer-3 finding persists none', routing), (
            'the routing rule does not state which layers persist a verdict'
        )

    def test_the_mapping_covers_a_checked_finding_that_confirms_a_premise(self):
        """A confirming `checked` finding must have its own row, never a contradiction.

        At the parent the table had no polarity at all, so a `checked` finding that
        confirms a premise fell through to `contradicted` (or to no row). A wrong
        `contradicted` on a staged spec's claim blocks that spec at the prep-ready
        test, which is why the confirming row is asserted directly.
        """
        routing = _routing_block(_read(_ANALYZE_MD))
        rows = _mapping_rows(routing)
        confirming = [
            row
            for row in rows
            if '`checked`' in row[_VERDICT_COLUMN]
            and 'confirms' in row[_POLARITY_COLUMN]
            and _ticked_values(row[_PERSISTED_COLUMN])
        ]

        assert confirming, (
            'the mapping has no row for a `checked` finding whose polarity confirms a premise — a confirming '
            'finding would be read as a contradiction'
        )
        assert any('`corroborated`' in _ticked_values(row[_PERSISTED_COLUMN]) for row in confirming), (
            'a `checked`/`confirms` layer-1 finding maps to no corpus verdict, so its row is not total'
        )

    def test_the_mapping_is_total_over_the_leaf_verdict_values(self):
        """Every leaf verdict value maps to exactly one corpus verdict or to none."""
        routing = _routing_block(_read(_ANALYZE_MD))
        rows = _mapping_rows(routing)
        leaf_verdicts = _leaf_vocabulary('verdict')

        assert leaf_verdicts, 'the leaf verdict vocabulary resolved empty — the totality check would be vacuous'
        for verdict in leaf_verdicts:
            assert any(verdict in row[_VERDICT_COLUMN] for row in rows), (
                f'the leaf verdict {verdict!r} has no row in the mapping — the mapping is not total'
            )
        for row in rows:
            cell = row[_PERSISTED_COLUMN]
            corpus = [value for value in CORPUS_VERDICTS if value in cell]
            assert len(corpus) <= 1, (
                f'the row {row} names more than one corpus verdict, so one finding could persist two values'
            )
            assert corpus or 'none' in cell, (
                f'the row {row} maps to neither a corpus verdict nor `none`'
            )

    def test_the_two_corroboration_statements_agree(self):
        """One rule states which verdicts a layer persists; the contradiction is gone."""
        routing = _routing_block(_read(_ANALYZE_MD))

        assert 'a layer-1 finding never yields' not in routing, (
            'the routing rule still says a layer-1 finding never yields `corroborated`, which contradicts the '
            '`corpus set-verdict` bullet beside it'
        )
        assert re.search(r'(?i)one rule states which verdicts a layer persists', routing), (
            'the routing rule does not state the single persistence rule the two former statements collapse into'
        )
        assert re.search(r'(?i)layer-1 finding persists', routing), (
            'the routing rule does not say which verdicts a layer-1 finding persists'
        )

    def test_the_never_downgrade_rule_covers_every_settled_verdict(self):
        """A `not_shown_by_reading` finding never overwrites a settled `contradicted`."""
        routing = _routing_block(_read(_ANALYZE_MD))
        settle = re.search(r'(?is)never downgrade a settled verdict(.{0,900})', routing)

        assert settle, 'the routing rule carries no never-downgrade rule'
        body = settle.group(1)
        for settled in ('`contradicted`', '`corroborated`', '`unverifiable`'):
            assert settled in body, (
                f'the never-downgrade rule does not name the settled verdict {settled}, so a '
                f'`not_shown_by_reading` finding could overwrite a claim settled as {settled}'
            )
        assert re.search(r'(?i)precedence between two findings on one claim', routing), (
            'two findings on one claim with different verdicts have no stated precedence'
        )

    def test_the_conformance_shape_is_spelled_once_across_the_contract(self):
        for source, text in (
            ('analyze.md', _read(_ANALYZE_MD)),
            ('three-layer-analysis.md', _read(_THREE_LAYER_DOC)),
        ):
            assert _CONFORMANCE_SHAPE in text, (
                f'{source} does not spell the conformance return shape as `conformance[M]`'
            )
            assert 'conformance[N]' not in text, (
                f'{source} still spells the conformance shape `conformance[N]`, which reads as one row per finding'
            )

    def test_the_leaf_doc_gives_a_cross_repo_prompt_field_besides_worktree(self):
        doc = _read(_THREE_LAYER_DOC)

        assert 'OTHER_REPO_PATH' in doc, (
            "the leaf doc names no prompt field for another repository's path, so a cross-repo landing has "
            'no legal field to carry it'
        )
        assert 'git -C {OTHER_REPO_PATH}' in doc, 'the leaf doc does not say how the cross-repo path is used'
        assert 'stays repo-relative' in doc, (
            'the leaf doc does not keep `WORKTREE` repo-relative while the other repository travels in its own field'
        )

    def test_the_leaf_doc_forbids_fetching_third_party_text(self):
        doc = _read(_THREE_LAYER_DOC)

        assert re.search(r'(?i)does not fetch', doc), 'the leaf doc does not forbid fetching third-party text itself'
        assert 'PR bodies' in doc and 'comment' in doc, (
            'the no-fetch rule does not name the third-party text it excludes'
        )
        assert 'validate_struct' in doc, (
            'the leaf doc does not point third-party text at the reader and `validate_struct` boundary'
        )
