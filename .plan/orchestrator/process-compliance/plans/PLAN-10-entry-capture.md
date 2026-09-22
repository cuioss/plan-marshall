# PLAN-10: Dispatch-entry capture gaps

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

## Claim Labels

- OBSERVED: post-exempt 2-refine capture refuses `pr_title_missing` because the collapsed envelope never ran Step 13 — read at `.plan/orchestrator/process-compliance/inbox/ledger-joins-002.md` § body (filed, then `--override` under prior approval)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (ledger-joins-002 inbox, archived) unchanged; run-behavior premise still needs outline
- OBSERVED: an original incident report used the informal label `not_orchestrated` for a mailbox-probe misclassification on a valid spec pointer — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-002.md` § body (dispatched leaf gist; body auditable in archive after drain) — CONTRADICTED at HEAD, see verdict below
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: yes | evidence: traced _orchestrator_inbox.py cmd_inbox_detect/SourceIdClassification (byte-unchanged since 93bda90): vocabulary is orchestrated/unsafe_slug/unrecognised_id/not_orchestrator_pointer, no 'not_orchestrated' token exists; regex-tested _SOURCE_ID_RE + PLAN_ID_SEGMENT against 5 realistic staged-spec pointer shapes (plain, PLAN-CIS-01, bare CIS-01, single-digit, dated-slug epic) — all classify correctly as orchestrated:true; no misclassification reproduces for a well-formed pointer. Deliverable 2 re-scoped from 'fix misclassification' to 'confirm probe vocabulary is documented/expected'; original incident likely involved a malformed source_id (prose or the retired .plan/local/orchestrator/ address), which correctly reads not_orchestrator_pointer/unrecognised_id
- OBSERVED: recipe-match/aspect-classify lack file input for verbatim narrative — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-001.md` § body (dispatched leaf gist)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatched leaf gist (plan-09-outline-sweep-001, archived) unchanged; CLI-flag check still deferred to outline
- OBSERVED: main-dirt assertion fires on pre-existing dirt; light-lane entry demands refine-artifact `pr_title`; steps parser reads non-step bullets — cited at `plan-09-outline-sweep-003.md`, `plan-09-outline-sweep-004.md`, `plan-09-outline-sweep-005.md` § bodies (dispatched leaf gists)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatched leaf gists (sweep-003/004/005, archived) unchanged; run-behavior premises still need outline
- HYPOTHESIS: zero phase-handshake captures across two completed phases is a contract gap, not operator choice — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/` § handshake capture seam (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-003.md`)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: phase-handshake.md unchanged since 93bda90; capture/verify registry still present at :273; re-confirmed
- HYPOTHESIS: light-lane routing on an 8-deliverable scope without a solution outline is undocumented entry, not sanctioned entry — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § light-lane entry (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-004.md`)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: planning.md unchanged since 93bda90; light-lane branch still present at :222-273; re-confirmed
- Verify-first clause: the consuming phase settles both HYPOTHESIS clauses against the implementing source before scoping — refutation loops back to re-scope
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies
- OBSERVED: the mailbox probe mis-parses every production colon-format request.md — `_resolve_mailbox_checkpoint` reads `source_id` via key=value-only `parse_markdown_metadata`, which stops at the `# Request:` heading and returns `{}` — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py`:174 and `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`:1554-1593 (folded lead from `implement-opencode-enforcement-parity-002.md`; re-opens deliverable 2's settled premise, which tested the classifier regex but never the probe's reader path)
  - verdict: corroborated | checked_at: 048221d3c98f6ca06925ee57c4077f36496009a9 | by: process-compliance/analyze | rescoped: n/a | evidence: lifecycle174 keyvalue reader plus fileops1554 stop-at-heading yields empty dict on colon request
- OBSERVED: the light-lane pr_title gap has a named root cause — `pr_title` is authored only in deep-lane refine Step 13 while the light lane folds refine away and the envelope authors nothing, and `_capture_pr_title_present` has no light-lane carve-out — cited at `.plan/orchestrator/process-compliance/inbox/implement-opencode-enforcement-parity-001.md` § Root cause (folded into deliverable 1 scope; mechanism not re-opened at source this pass)
  - verdict: unverifiable | checked_at: 048221d3c98f6ca06925ee57c4077f36496009a9 | by: process-compliance/analyze | rescoped: n/a | evidence: cited inbox root cause not re-opened at source this pass
- OBSERVED: a second same-sender inbox write silently replaced the first live message (sequence re-opened at allocation; sender-observed, mechanism not reproduced) — cited at `.plan/orchestrator/process-compliance/inbox/implement-opencode-enforcement-parity-003.md` § Evidence (folded; reproduction left to the consuming plan)
  - verdict: unverifiable | checked_at: 048221d3c98f6ca06925ee57c4077f36496009a9 | by: process-compliance/analyze | rescoped: n/a | evidence: sender-observed allocation anomaly mechanism not reproduced

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — light-lane entry + capture pairing live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — mailbox probe (`cmd_inbox_detect`/`SourceIdClassification`) actually lives here, not in `orchestrator.py` directly (corrected 2026-09-22, cleanup re-grounding)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/` — entry-lane scripts and workflow docs
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/` — recipe-match/aspect-classify lane lives here (added 2026-09-22, cleanup re-grounding — understated surface, deliverable 3 named no implementing file before this correction)
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — probe regression tests live here
- OBSERVED: `test/plan-marshall/plan-marshall/` — entry-lane regression tests live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — mailbox probe reader path (added drain 2026-09-22, -002 fold; the mis-parse lives here, not in the classifier)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 surfaces (shipped, no live collision); PLAN-08 (shared orchestator surface area — sequence, do not parallelize)
- Adjacent to: condensed-inline lane question (recorded defect; stays untouched — this plan fixes the documented lane, not the undocumented one)

## Folded inbox material (same act)

- `ledger-joins-002.md` (finding): pr_title capture gap — head of this spec
- `plan-09-outline-sweep-001.md` (finding): file-input parity — staged into this spec
- `plan-09-outline-sweep-002.md` (finding): mailbox probe — staged into this spec
- `plan-09-outline-sweep-003.md` (finding): dirt assertion — staged into this spec
- `plan-09-outline-sweep-005.md` (finding): steps parser — staged into this spec
- `plan-09-outline-sweep-004.md` (finding): pr_title capture recurrence — folded; expected surface unchanged by this fold (recurrence note, adds no file surface — recorded explicitly)
- `test-fidelity-rules-follow-up-003.md` (finding): handshake captures — staged into this spec
- `test-fidelity-rules-follow-up-004.md` (finding): light-lane routing — staged into this spec
- `implement-opencode-enforcement-parity-001.md` (finding): light-lane pr_title root cause — folded into deliverable 1 scope; expected surface unchanged by this fold (planning.md already declared — recorded explicitly)
- `implement-opencode-enforcement-parity-002.md` (finding): mailbox probe reader mis-parse, re-opens deliverable 2 premise — folded; expected surface updated in the same act (+1 entry: _cmd_lifecycle.py)
- `implement-opencode-enforcement-parity-003.md` (finding): inbox write sequence re-use — folded; expected surface unchanged by this fold (_orchestrator_inbox.py already declared — recorded explicitly)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-10-entry-capture.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
