# PLAN-LB-84: The landing says what the refresh could not read, the refresh measures the plan's own tree, and the stamp tests can fail

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-84-lb-81-completion.md` and is queued as one row file, `queue/PLAN-LB-84.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-81 (#1832, `d7e351419`),
> `landings/PLAN-LB-81.md` § Code defects. Priority is **medium**: PLAN-LB-81 made the runtime stamp carry the
> measured variant and refresh at landing, and its core tests fail at the base, but the provenance it records
> never reaches the landing, the refresh measures the landing process's session rather than the plan's tree,
> the new root-manifest read stamps a placeholder version on one harness, and about a third of the new tests
> cannot fail for the reason they name. **Each deliverable is its own outline deliverable, and each Done-when is
> its own success criterion. Do not merge them.** A Done-when says "fails at `d7e351419`" only where the
> behaviour is new at that sha; a clause that already holds says "holds at `d7e351419`". A Done-when is never
> labelled "holds at" while a claim it rests on is still a HYPOTHESIS below.

## Objective

A cross-model comparison needs each landing to say which model, at which variant, with which effort, produced
the run, and to say so loudly when it could not read one of them. PLAN-LB-81 stamps the measured variant and
re-reads at landing, but a value kept from plan start is marked `measured_at_start` only in `status.json` and
the landing copies the bare value; the refresh reads the landing process's own session and replaces the stamp
wholesale; on a non-OpenCode harness it lets an environment model overwrite the model the run reported; an
Antigravity install now stamps `0.1.0` as the bundle version; and several tests check only that a word exists
in a markdown file or already pass at the base. This plan closes those, in the order of their consequence.

## Deliverables

1. **The landing carries the provenance the refresh recorded.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `emit-landing.md` Step 1 item 5 and `landing-payload-spec.md` state how a value kept from plan start
     (`model_source` / `effort_source` = `measured_at_start`) is marked in the landing itself, not only in
     `status.json`; the payload gains a field or a suffix for it (decide at outline and record why, keeping the
     `landing-check` required-key set unchanged).
   - `refresh-runtime-stamp` reports the real reason when an environment model was read but rejected: it
     returns a reason that names the rejected fallback, not `model_unknown` (`orchestrator.py` L6915-6937).
   - A refresh that changes the harness (a plan started under OpenCode and landed under another harness) clears
     `model_origin` together with the keys it replaces, so a Claude model never sits beside a stale
     `model_origin: session_tree`.

   *Done when:* each of these fails at `d7e351419`:
   - a refresh whose database is unreachable yields a landing fact that marks the model as start-time (a test
     that reads the landing payload, not `status.json`);
   - an env model rejected by the session-tree guard returns a reason that names it, not `model_unknown`;
   - a plan stamped `model_origin: session_tree` and refreshed under a non-OpenCode harness ends with no
     `model_origin`.

2. **The refresh measures the plan's own session tree and keeps the precedence preflight set.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The refresh no longer replaces the model with whatever the LANDING process's `OPENCODE_SESSION_ID` tree
     reports: it unions the tree it can measure with the models already stamped (a plan that started in root
     session A on model X and finishes in a new root B on model Y lands `mixed` with both labels), or it
     measures every root session bound to the plan; decide at outline which, and record why.
   - On a harness that does not measure, the refresh keeps the model and effort the run reported at preflight
     and does not let an environment model replace a flagged self-report (`orchestrator.py` L6866-6873,
     `runtime_info.py` L469-473).

   - A tree whose sessions ran more than one variant stamps an `effort` that names them, in the list form the
     `model` fact already uses, and not `unknown`: `unknown` is rejected at every landing key, so a mixed tree
     can otherwise never land `complete: true` (`runtime_info.py` L675-680 adds no effort when variants differ).
     A model or variant switch INSIDE one session is measured from the messages, not from the session row's one
     model cell (`runtime_info.py` L308-338; the PLAN-LB-78 run's main row said `flash/high` while 376 of its
     621 assistant messages ran `free/max`). Decide at outline whether a mixed effort is the list or the weakest
     measured value, and record why (folded from `landings/PLAN-LB-78.md` defect D3).

   *Done when:* each of these fails at `d7e351419`:
   - a plan stamped on model X whose landing runs in a second root session on model Y lands with both labels;
   - a Claude plan preflighted with `--model claude-opus-5-5` and refreshed with `ANTHROPIC_MODEL` set to
     another model keeps `claude-opus-5-5` and its `self_reported` tag;
   - a session tree whose children ran a different variant than the root yields an `effort` that is not `unknown`,
     and `inbox landing-check` on a landing carrying it reports no `effort` missing;
   - a single session whose messages ran two models yields both labels, not the session row's one cell.

3. **The bundle version is read from a real manifest only.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The root `plugin.json` read (`runtime_info.py` L511) does not stamp Antigravity's hard-coded aggregate
     manifest version `0.1.0` as the bundle version: either the reader refuses an aggregate manifest that is
     not a bundle's, or the Antigravity emitter stops writing a placeholder; decide at outline and record why.
   - The flat-layout fixture models a layout a real install produces (OpenCode installs write no root
     `plugin.json`), and the docstring that says it does is corrected.
   - A source tree's unstamped manifest (`marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:3`, `0.1`)
     is not stamped as `plugin_version` beside a measured `executor_version`: a runbook-lane run whose executor
     maps to a source tree (the meta-project or its base clone) lands `plugin_version=0.1` next to
     `executor_version=0.1.1977` with nothing marking the first as a placeholder. The reader reports it as
     unstamped, or the landing marks it; decide at outline and record why (folded from `landings/PLAN-LB-78.md`
     defect D5).

   *Done when:* each of these fails at `d7e351419`:
   - an Antigravity-shaped install tree (aggregate manifest `0.1.0`) yields no `bundle_version` rather than
     `0.1.0`;
   - the flat-layout test uses a layout an emitter actually writes;
   - a source-tree executor mapping (manifest `0.1`, `executor_version` `0.1.1977`) yields a `plugin_version` that
     is marked unstamped or absent, not a bare `0.1`.

4. **A failed clear or a lost race is reported, not swallowed.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `cmd_preflight` uses the result of `_clear_runtime_metadata` (L6740): a clear that failed followed by a
     failed collector returns a degraded result that says the old stamp may survive.
   - `refresh-runtime-stamp` reads and writes the status document inside one guarded section (or through the
     seam that carries protected and unrelated keys), so a concurrent non-protected write between the read
     (L6890) and the write is not clobbered; decide at outline whether the existing stamper (L6461-6474) takes
     the same fix.
   - The "exactly one refresh rule" partition assert (L6435) checks that the three field sets are disjoint and
     is a real check under `python -O`.

   *Done when:* each of these fails at `d7e351419`:
   - a clear whose write fails, then a failing collector, returns a degraded result naming the stale-stamp risk;
   - a status write that lands between the refresh's read and its write is still present afterwards;
   - two refresh field sets that share a key fail the partition check.

5. **The tests that guard the stamp can fail for the reason they name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-module-tester
   - `test_preflight_stamps_the_mixed_model_labels` and `TestEmitLandingRuntimeStamp::test_emit_landing_writes_the_mixed_list`
     pass at the base through a canned payload and a sentence already in the doc: replace them with a test that
     drives a real mixed fixture tree through the router and the refresh, or remove them and say so.
   - The keyword-only doc tests (`test_emit_landing_writes_the_variant_form`, `test_emit_landing_refreshes_the_stamp_first`,
     the two `TestPhase1InitRuntimeStampBranch` tests) assert behaviour: the emit-landing instruction is
     exercised through the landing payload builder the lane and the lifecycle share, or the test states that it
     is a doc-contract test and searches only the section it names (`test_warning_names_the_reason` searches the
     rest of the file).
   - `test_failed_collector_clears_a_previous_runtime_stamp`'s `_failed` fallback does not call the function it
     replaced (it recurses on any other subprocess call).
   - The duplicate `test_unstamped_metadata_without_degradation_is_reported` (passes at the base) is removed or
     made to fail at the base; `test_refresh_over_an_unchanged_tree_keeps_the_value` fails on a refresh that
     reports `refreshed: true` without reading; `test_the_executor_version_stays_optional` and
     `test_measurement_is_bounded_to_the_session_tree` assert behaviour, not a constant.
   - The landing's test name `TestPhase1InitRuntimeStampBranch::test_unstamped_metadata_without_degradation_is_reported`
     does not exist; the progress file and the landing cite names the audit can resolve.

   *Done when:* each replaced or reduced test fails when its named behaviour is mutated, run and recorded
   (`order=mutation-after` acceptable and labelled), and none of the listed tests passes at `d7e351419` for a
   reason other than the one it names.

6. **A landing whose facts fence has a space after the backticks is still read.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The facts-fence parser (`_LANDING_FENCE_RE`, `_orchestrator_inbox.py` L1494-1497) requires the info string
     to follow the backticks directly; CommonMark allows spaces between them. The PLAN-LB-49 landing wrote
     "``` landing-facts" and `landing-check` reported all thirteen required keys missing for a block that
     carried them. The parser accepts optional spaces or tabs between the fence and the info string, and still
     refuses a different info string.
   - `emit-landing.md` Step 2 item 2 (L275) says the block must open with "a ` landing-facts ` info-string
     fence", with padded backticks, which a model reads as spaces; it states the exact opening line instead.
     Decide at outline whether the lane's § 8 (`runbook-lane/SKILL.md`) needs the same sentence, and record why.

   *Done when:* each of these fails at `3baf825e4`: `landing-check` on a landing whose fence is "``` landing-facts"
   reports `complete: true` for a block that carries every required key; a fence with another info string is
   still not read; and the emit-landing text states the opening line verbatim.

Split guard: six deliverables, all in the landing and runtime-stamp family (`orchestrator.py`, `runtime_info.py`,
`_orchestrator_inbox.py`, their docs and tests). Proceeding unsplit: D5 changes tests only, D3 is one reader line
and D6 is one regular expression and one sentence.

## Claim Labels

- OBSERVED: `emit-landing.md` Step 1 item 5 copies `metadata.model`, `metadata.effort` and the other values into the landing and carries no `model_source` / `effort_source`, so `measured_at_start` is written only to `status.json` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` L227-228 (read by the orchestrator).
- OBSERVED: `refresh-runtime-stamp` runs `runtime-info` with the landing process's environment and no `--model` / `--effort`, then overwrites the model fields from that one read with no union — `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` L6866-6873, L6941-6950 (read by the orchestrator).
- OBSERVED: when the refresh's read is rejected by the session-tree guard the returned reason is `model_unknown` unless the collector gave a reason — `orchestrator.py` L6933-6938 (read by the orchestrator).
- OBSERVED: the refresh reads the status document with `read_status` and writes the whole document with `write_status` in two steps — `orchestrator.py` L6886-6890, L6964-6967 (read by the orchestrator).
- OBSERVED: PLAN-LB-81's third D1 Done-when ("a `mixed` tree writes the distinct labels", labelled "fails at `137986c61`") already held at the base — an authoring error of the orchestrator's spec, recorded in `landings/PLAN-LB-81.md`; the run reported it "not met as written".
- OBSERVED: the PLAN-LB-78 runbook-lane landing reported `effort=unknown` because the OpenCode tree ran two variants (`free/max` root and round-1 child, `flash/high` later), and `inbox landing-check` returned `complete: false` with `effort` missing; the session row of the main session carried one model cell (`flash/high`) for 641 messages of which 376 ran `free/max` (landing analysis of `landings/PLAN-LB-78.md`, from the OpenCode session store read by the corroboration; `landing-check` itself run by the orchestrator).
- OBSERVED: the landing stamped `plugin_version=0.1` beside `executor_version=0.1.1977`; `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` L3 is `0.1` (corroboration, not re-read).
- HYPOTHESIS: the preflight clears the runtime keys at L6740 and discards the result of `_clear_runtime_metadata` — confirm at `orchestrator.py` L6740 (verify-at-outline).
- HYPOTHESIS: on a non-OpenCode harness the refresh lets an environment model replace a flagged self-report and tags it `measured` — confirm at `runtime_info.py` L469-473 and `orchestrator.py` L6866-6871 (verify-at-outline).
- HYPOTHESIS: the root `plugin.json` read picks up Antigravity's aggregate manifest `0.1.0` — confirm at `runtime_info.py` L511 and `marketplace/targets/antigravity/emitter.py` L393 (verify-at-outline).
- HYPOTHESIS: OpenCode installs write no root `plugin.json` — confirm at `marketplace/targets/opencode/templates/install.sh` (verify-at-outline).
- HYPOTHESIS: the "exactly one refresh rule" assert checks set equality only and is stripped under `python -O` — confirm at `orchestrator.py` L6435 (verify-at-outline).
- OBSERVED: PLAN-LB-49 (#1833, `3baf825e4`) deleted the recursive tree query from `runtime_info.py` (net −76 lines) and routed the session-tree read through `_opencode_sessions.py`, whose `_session_rows` reads `session_v2` unconditionally (L339); every `runtime_info.py` line reference in this spec (L308-338, L327-335, L469-473, L511, L675-680) and the former recursive-query hypothesis are therefore stale — by the corroboration of the PLAN-LB-49 landing; re-read each at outline.
- OBSERVED: the PLAN-LB-49 landing wrote its facts fence as "``` landing-facts" (a space after the backticks); `_LANDING_FENCE_RE` is `^```landing-facts[ \t]*\n…` (`_orchestrator_inbox.py` L1494-1497) and `inbox landing-check` reported all thirteen required keys missing — read by the orchestrator at `3baf825e4`.
- OBSERVED: `emit-landing.md` L275 describes the opening as "a ` landing-facts ` info-string fence" (padded backticks), while L277 shows the unpadded block — read by the orchestrator.
- OBSERVED: the named tests are weak, vacuous at the base or keyword-only as listed in deliverable 5 (reported by the corroboration of the landing, not re-read by the orchestrator).
- Verify-first clause (deliverable 2): decide whether the refresh unions the measurable tree with the stamped models or measures every root session bound to the plan, before scoping; record why. A session binding that does not exist for a plan started in a different root session loops back to re-scope.
- Verify-first clause (deliverable 3): decide whether the reader or the Antigravity emitter owns the placeholder; if the emitter, the Expected Surface gains `marketplace/targets/antigravity/emitter.py` and its tests.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `refresh-runtime-stamp`, `cmd_preflight`, the clear, the partition assert (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py` — the session-tree read, the effort and model precedence, the root-manifest read (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — the stamp read and its provenance (D1); the opening-fence sentence (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `_LANDING_FENCE_RE` (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the `model` and `effort` rows (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/preflight.md` — the landing-time refresh section (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/runtime-info.md` — the field semantics (D1, D2, D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_preflight_client_toon.py` (D1, D2, D4, D5)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` (D1, D5, D6)
- OBSERVED: `test/plan-marshall/platform-runtime/test_runtime_info.py` (D2, D3, D5)
- OBSERVED: `test/plan-marshall/phase-1-init/test_phase_1_init.py` (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — only if the refresh verb's invocation text changes (verify-at-outline) (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — only if the session id the refresh reads moves (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/targets/antigravity/emitter.py` — only if the Antigravity emitter owns the placeholder (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-81 (shipped, `d7e351419`) and PLAN-LB-78 (shipped, `9a23d41e9`). PLAN-LB-78 D3 gave the runbook lane the four stamp keys, but its landing-time re-read calls `platform-runtime runtime-info` directly and NOT `refresh-runtime-stamp` (the lane has no `status.json`): deliverables 1 and 2 of this plan are therefore still not exercised end to end by a runbook-lane landing, only by the plan lifecycle's. Decide at outline whether the lane should call the refresh or the two readers should share one path (landing analysis of PLAN-LB-78, from `_resolve_runtime_stamp`; read by the corroboration).
- Overlaps with: PLAN-LB-78 (shipped) on `landing-payload-spec.md` (one file); PLAN-LB-69 on `orchestrator.py` and `landing-payload-spec.md`; PLAN-LB-83 on `opencode_runtime.py` only if deliverable 2 moves the session id read; PLAN-LB-86 (OpenCode measurement truth) on the session-tree reader `_opencode_sessions.py`, which PLAN-LB-49 (shipped, `3baf825e4`) made the single place the tree is read — deliverable 2's mixed-variant and per-message model read goes through that reader, so sequence PLAN-LB-86 first or state in the outline which plan owns the per-message read. PLAN-LB-85 on `landing-payload-spec.md`. The gate will ask.
- Adjacent to: `runbook-lane/SKILL.md` § 8 (PLAN-LB-78 D3 owns the lane's landing keys) and the OpenCode token reader (PLAN-LB-49), neither edited here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-84-lb-81-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
