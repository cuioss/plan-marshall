# PLAN-10: Dispatch-entry capture gaps

> ✅ **UN-PARKED 2026-09-27 by explicit operator directive ("issues about current problems are to be fixed, not
> relayed to PM-MCP").** Staged and emittable as an operator-confirmed exception to the PM-MCP supersession
> (originally parked per inbox `review-apparatus-001`). Deliverable 2 is no longer a confirmation exercise: the
> reader mis-parse is CONFIRMED at HEAD (see the 2026-09-27 folds below) and is a live delivery defect.

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-10-entry-capture.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close the light-lane entry gaps that force exempt-and-continue overrides at plan start:
the 2-refine capture demanding a `pr_title` the collapsed envelope never produced, an
unverified mailbox-probe classification report (re-scoped 2026-09-22: cleanup traced the
classifier and it does NOT reproduce for any well-formed pointer — see deliverable 2), the
recipe-match/aspect-classify lane lacking file input for verbatim narrative, the
`phase_steps_complete` parser reading non-step bullets, and the missing phase-handshake
captures. Every gap below was absorbed as an explicit operator-approved exemption; this
plan makes the entry lane decidable so the exemption stops recurring.

## Deliverables

1. Capture-source matrix + fix: `pr_title` capture source for the light-lane collapsed
   envelope (refine-artifact vs required flag), so post-exempt capture stops refusing
   with `pr_title_missing`.
2. Mailbox-probe vocabulary confirmation (re-scoped 2026-09-22, cleanup re-grounding): the
   original incident's informal `not_orchestrated` label does not name a real token in
   `_orchestrator_inbox.py`'s `SourceIdClassification` vocabulary
   (`orchestrated`/`unsafe_slug`/`unrecognised_id`/`not_orchestrator_pointer`), and a
   regex trace against 5 realistic staged-spec pointer shapes found no misclassification
   for any well-formed pointer — reproduce the ORIGINAL incident's exact `source_id`
   string (from `plan-09-outline-sweep-002.md`, archived) at outline; if it turns out
   malformed (prose, or the retired `.plan/local/orchestrator/` address), close this
   deliverable with that finding and no code change; if a well-formed pointer genuinely
   misclassifies, fix the classifier.
3. Recipe-match/aspect-classify file input parity (`--content-file` or equivalent) for
   verbatim narrative ingestion — implementing surface is `phase-1-init/` (added to
   Expected Surface 2026-09-22, cleanup re-grounding; the spec previously named no file
   for this deliverable).
4. `phase_steps_complete` parser fix: reads step bullets only; post-archive state handled.
5. Phase-handshake capture backfill: the zero-capture runs across two completed phases
   get a contract (capture or recorded reason), not silence.

**Cleanup 2026-09-29 (duplication):** the silent same-sender inbox replacement claim (last claim below) has no deliverable here. Its mechanism is PLAN-26 D4 (the allocator reads a cwd-relative ledger copy from a plan worktree), which now owns it. The claim stays, as the audit record.

## Claim Labels

- OBSERVED: post-exempt 2-refine capture refuses `pr_title_missing` because the collapsed envelope never ran Step 13 — read at `.plan/orchestrator/process-compliance/inbox/ledger-joins-002.md` § body (filed, then `--override` under prior approval)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _invariants.py:1683-1713 _capture_pr_title_present raises PrTitleMissing, no light-lane carve-out; light-lane.md gained only the halt rule, no pr_title
- OBSERVED: an original incident report used the informal label `not_orchestrated` for a mailbox-probe misclassification on a valid spec pointer — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-002.md` § body (dispatched leaf gist; body auditable in archive after drain) — CONTRADICTED at HEAD, see verdict below
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py:118 MAILBOX_PROBE_NOT_ORCHESTRATED; :174-181 still returns not_orchestrated when source_id parses to ''
- OBSERVED: recipe-match/aspect-classify lack file input for verbatim narrative — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-001.md` § body (dispatched leaf gist)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: manage-config recipe-match / aspect-classify --help at HEAD: only --request-text + --threshold
- OBSERVED: main-dirt assertion fires on pre-existing dirt; light-lane entry demands refine-artifact `pr_title`; steps parser reads non-step bullets — cited at `plan-09-outline-sweep-003.md`, `plan-09-outline-sweep-004.md`, `plan-09-outline-sweep-005.md` § bodies (dispatched leaf gists)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: planning.md:169 and :443 porcelain, no baseline/exemption; _invariants.py:543-552 _parse_required_steps unchanged
- HYPOTHESIS: zero phase-handshake captures across two completed phases is a contract gap, not operator choice — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/` § handshake capture seam (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-003.md`)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: planning.md:199,:521 orchestrator capture calls; _cmd_lifecycle.py:795 cmd_transition verifies only at _BLOCKING_BOUNDARIES (6-finalize)
- HYPOTHESIS: light-lane routing on an 8-deliverable scope without a solution outline is undocumented entry, not sanctioned entry — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § light-lane entry (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-004.md`)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py:359-377 _has_outline_artifact unchanged; _cmd_planning_lane.py has no deliverable-count signal
- Verify-first clause: the consuming phase settles both HYPOTHESIS clauses against the implementing source before scoping — refutation loops back to re-scope
  - verdict: unverifiable | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural verify-first instruction; no source artifact
- OBSERVED: the mailbox probe mis-parses every production colon-format request.md — `_resolve_mailbox_checkpoint` reads `source_id` via key=value-only `parse_markdown_metadata`, which stops at the `# Request:` heading and returns `{}` — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py`:174 and `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`:1554-1593 (folded lead from `implement-opencode-enforcement-parity-002.md`; re-opens deliverable 2's settled premise, which tested the classifier regex but never the probe's reader path)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py:174 classify_source_id(parse_markdown_metadata(...)); file_ops.py:1648-1687 (moved by #1652) still key=value only, breaks at '#' (:1679)
- OBSERVED: the light-lane pr_title gap has a named root cause — `pr_title` is authored only in deep-lane refine Step 13 while the light lane folds refine away and the envelope authors nothing, and `_capture_pr_title_present` has no light-lane carve-out — cited at `.plan/orchestrator/process-compliance/inbox/implement-opencode-enforcement-parity-001.md` § Root cause (folded into deliverable 1 scope; mechanism not re-opened at source this pass)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _invariants.py:1686 pr_title only from refine Step 13; :1708-1713 no light-lane branch
- OBSERVED: a second same-sender inbox write silently replaced the first live message (sequence re-opened at allocation; sender-observed, mechanism not reproduced) — cited at `.plan/orchestrator/process-compliance/inbox/implement-opencode-enforcement-parity-003.md` § Evidence (folded; reproduction left to the consuming plan)
  - verdict: unverifiable | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _orchestrator_inbox.py unchanged; sender-observed replacement not reproducible from source

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — light-lane entry + capture pairing live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — mailbox probe (`cmd_inbox_detect`/`SourceIdClassification`) actually lives here, not in `orchestrator.py` directly (corrected 2026-09-22, cleanup re-grounding)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/` — entry-lane scripts and workflow docs
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/` — recipe-match/aspect-classify lane lives here (added 2026-09-22, cleanup re-grounding — understated surface, deliverable 3 named no implementing file before this correction)
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — probe regression tests live here
- OBSERVED: `test/plan-marshall/plan-marshall/` — entry-lane regression tests live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — mailbox probe reader path (added drain 2026-09-22, -002 fold; the mis-parse lives here, not in the classifier)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/` — `recipe-match` / `aspect-classify` argparse (`manage-config.py`, `_cmd_recipe_match.py`, `_cmd_aspect_classify.py`): deliverable 3 file input (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-plan-documents/scripts/` — request-document parser for `source_id` (deliverable 2) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` — key=value-only `parse_markdown_metadata` (deliverable 2) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md` — non-step `- ` bullets (deliverable 4) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — light-lane `pr_title` producer (deliverable 1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `test/plan-marshall/manage-config/` and `test/plan-marshall/manage-status/` — regression tests (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `test/plan-marshall/manage-plan-documents/` — request-document path (#1652 `test_request_body_file_ingestion.py`) that D2 reuses (added cleanup 2026-09-29 at 56add3f — understated surface)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 surfaces (shipped, no live collision); PLAN-08 (shared orchestator surface area — sequence, do not parallelize)
- Adjacent to: condensed-inline lane question (recorded defect; stays untouched — this plan fixes the documented lane, not the undocumented one)

## Folded inbox material (same act)

- `ledger-joins-002.md` (finding): pr_title capture gap — head of this spec
- `plan-09-outline-sweep-001.md` (finding): file-input parity — staged into this spec
- `plan-09-outline-sweep-002.md` (finding): mailbox probe — staged into this spec
- `plan-09-outline-sweep-003.md` (finding): dirt assertion — originally staged into this spec with no deliverable; MOVED to PLAN-17 deliverable 1 (2026-09-27)
- `plan-09-outline-sweep-005.md` (finding): steps parser — staged into this spec
- `plan-09-outline-sweep-004.md` (finding): pr_title capture recurrence — folded; expected surface unchanged by this fold (recurrence note, adds no file surface — recorded explicitly)
- `test-fidelity-rules-follow-up-003.md` (finding): handshake captures — staged into this spec
- `test-fidelity-rules-follow-up-004.md` (finding): light-lane routing — staged into this spec
- `implement-opencode-enforcement-parity-001.md` (finding): light-lane pr_title root cause — folded into deliverable 1 scope; expected surface unchanged by this fold (planning.md already declared — recorded explicitly)
- `implement-opencode-enforcement-parity-002.md` (finding): mailbox probe reader mis-parse, re-opens deliverable 2 premise — folded; expected surface updated in the same act (+1 entry: _cmd_lifecycle.py)
- `module-budget-campaign-completion-004.md` (finding): same reader mis-parse, independently verified (direct invocation + fixture shape) — folded into deliverable 2 mechanism note as recurrence; expected surface unchanged (recorded explicitly)
- `implement-opencode-enforcement-parity-003.md` (finding): inbox write sequence re-use — folded; expected surface unchanged by this fold (_orchestrator_inbox.py already declared — recorded explicitly)
- `module-budget-campaign-completion-001.md` issue 1 (finding): recipe-match/aspect-classify need `--body-file` for verbatim bodies — folded into deliverable 3 scope; expected surface unchanged by this fold (phase-1-init/ already declared — recorded explicitly)
- `truth-147-lane-reports-green-001.md` item 2 (finding): same `--body-file` gap, `--request-file`/`--stdin` request — folded into deliverable 3 scope as recurrence; expected surface unchanged (recorded explicitly)
- `truth-179-opencode-target-detection-landed-001.md` (finding): same gap, sharpest statement (three binding rules, no compliant spelling) — folded into deliverable 3 scope as recurrence; expected surface unchanged (recorded explicitly)
- `truth-147-lane-reports-green-003.md` + `truth-179-opencode-target-detection-landed-002.md` + `carried-defects-and-watches-closure-001.md` item 1 (findings): mailbox-probe vs detect disagreement recurrences — folded into deliverable 2 mechanism note; expected surface unchanged (recorded explicitly)
- `plan-12-tool-triage-001.md` (finding): mailbox probe reports `not_orchestrated` for every orchestrated plan — root cause CONFIRMED by the orchestrator at HEAD 2026-09-27: `_cmd_lifecycle.py` feeds raw request.md to `file_ops.parse_markdown_metadata`, which parses `key=value` and stops at the first heading; request.md opens with an HTML comment then `# Request:` then `key: value` lines, so the parse is always `{}` and `classify_source_id('')` returns `not_orchestrator_pointer`. Fix: read `source_id` through the request-document schema (`manage-plan-documents request read`'s parser) and add a transition regression test asserting `probe != not_orchestrated` for an orchestrator pointer. Folded into deliverable 2 (now a fix, not a confirmation); expected surface unchanged (`_cmd_lifecycle.py` already declared — recorded explicitly)
- `plan-13-finalize-mechanism-defects-001.md` item 1 (finding): same probe false negative, mis-attributed to the `PLAN-13-…` filename lacking a code segment — attribution REFUTED (`inbox detect` returns `orchestrated: true`; `PLAN-{DIGITS}` is an accepted form), symptom real, same root cause as above. Folded into deliverable 2 as recurrence; expected surface unchanged (recorded explicitly)
- `plan-12-tool-triage-002.md` + `plan-13-finalize-mechanism-defects-001.md` item 2 (findings): file-pointer rebind unsatisfiable — `recipe-match`/`aspect-classify` take only `--request-text`, forcing a lossy flattening of a multi-line spec. Folded into deliverable 3 as recurrence (preferred shape: `--plan-id`, reading the persisted request.md body); expected surface unchanged (`phase-1-init/` already declared — recorded explicitly)
- `plan-13-finalize-mechanism-defects-002.md` item 1 (finding): the run's own correction — filename theory withdrawn, transition probe and `inbox detect` disagree on the same input; must share one classifier path. Folded into deliverable 2 as recurrence; expected surface unchanged (recorded explicitly)
- `truth-168-sync-defaults-reverting-remove-001.md` items 1-2/4 (finding): direct `.plan` read before sanctioned read (recurrence, self-corrected); `--request-text` verbatim vs Bash newline rule forcing single-line title workaround with zero-match no-routing-impact (deliverable 3 recurrence); logical-vs-physical store path note (no action). Folded into deliverables 2/3 as recurrences; expected surface unchanged by this fold (phase-1-init/ and probe paths already declared — recorded explicitly)
- `truth-168-sync-defaults-reverting-remove-002.md` item 6 (finding): `inbox detect orchestrated:true` vs transition probe `not_orchestrated` on the same pointer (deliverable 2 recurrence, root cause already confirmed). Folded into deliverable 2 as recurrence; expected surface unchanged (`_cmd_lifecycle.py` already declared — recorded explicitly)
- `issue-1697-001.md` (finding): `--request-text` verbatim passing breaks on real issue bodies — backticks trigger shell substitution, embedded quotes break parsing. Sharpest restatement of the deliverable 3 gap, with a named argv-safe workaround (python `subprocess.run` with argv elements) and the preferred `--request-file` shape. Folded into deliverable 3 as recurrence; expected surface unchanged (`phase-1-init/` and `manage-config/scripts/` already declared — recorded explicitly)
- `issue-1697-002.md` (finding): light-lane pre-dispatch 2-refine closure refused by the `refine_bare_transition` guard — the light lane never runs the phase body that would write the demanded artifact, and the workflow authorizes no exemption at this site. Same exempt-or-stop shape as the deliverable 1 gap, at the transition guard rather than the capture. Folded into deliverable 1 scope as recurrence; expected surface unchanged (`planning.md` and `_cmd_lifecycle.py` already declared — recorded explicitly)
- `issue-1697-003.md` (finding): light-lane pre-dispatch `phase_handshake capture` fails `pr_title_missing` — Step 13 never runs on the light lane before the capture. Direct deliverable 1 recurrence, with the run stopping rather than inventing a title or overriding. Folded into deliverable 1 as recurrence; expected surface unchanged (light-lane `pr_title` producer path already declared — recorded explicitly)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-10-entry-capture.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
