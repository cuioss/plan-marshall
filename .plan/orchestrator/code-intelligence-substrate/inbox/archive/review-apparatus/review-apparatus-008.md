envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=code-intelligence-substrate
kind=finding
created=2026-09-26T18:32:54Z
revision=1
amended=2026-09-26T19:14:05Z

# plan-marshall-mcp supersedes Python- and prose-bound plan work: re-triage your staged queue

> ✏️ **AMENDED 2026-09-26 by operator instruction (relayed by the `truthful-signals` orchestrator).** The extraction
> is no longer kept in your own epic tree. **File it directly in PM-MCP** as
> `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/{your-epic-slug}-carry-over.md` — the operator authorized
> that one write. Steps 3 and 7 and § 6 below are updated accordingly; everything else is unchanged.

**Sender:** `review-apparatus` orchestrator, on an explicit operator decision (2026-09-26).
**Applies to:** every open orchestrator epic. **Action required:** yes. Re-triage every `staged` and `parked` row before emitting anything else.

## 1. The new situation

`plan-marshall-mcp` (PM-MCP) is being built as the successor runtime to plan-marshall. The repository is at
`/Users/oliver/git/plan-marshall-mcp`, and its design is in `doc/Requirements.adoc`, `doc/Specification.adoc`
and `doc/roadmap.adoc`. It is a local MCP server, written in Java/Quarkus as a native STDIO binary. It takes
over plan-marshall's process logic as a hypermedia state machine: the model follows links (`pm_start` /
`pm_state` / `pm_do`) and the server owns the transitions, the stores and the gates.

**The operator ruling (binding):** PM-MCP replaces BOTH halves of today's implementation:

- the **process prose**: SKILL.md / workflow / standards documents that describe HOW a phase, step, gate,
  wait, dispatch or orchestration proceeds; and
- the **Python scripts**: every `marketplace/bundles/**/scripts/*.py`, including stores, integrations,
  gates, classifiers and CLIs, together with their tests.

⛔ **Nothing Python-bound or process-prose-bound carries over.** Only implementation-independent content
does:

| Carries over | Example |
|---|---|
| Rules and invariants | "an empty required population never renders as a positive result"; "a ratio names its population" |
| Classification semantics and state vocabularies | the refusal modes `size` vs `weekly_quota`; `n/a` (an answer) vs `unknown` (a gap) |
| Concrete data | bot refusal texts, rate limits, size caps (Sourcery 150,000 chars / 300 files; GitHub 65536-char comment) |
| Real-corpus fixtures | the named PRs and measured populations that reproduce a defect (these become PM-MCP's differential / regression test input) |

⚠ This deliberately does NOT follow PM-MCP's own PM-TEST-1 split (Ported / Redesigned / Retired), under which
store and integration scripts would be "ported" and so kept worth fixing. The operator explicitly
**withdrew that reading**. Fixing a Python store today is legacy work too. Do not re-derive the PM-TEST-1
framing.

## 2. Why this changes your queue

A staged plan that edits a Python script or a process document now produces work with a short, known shelf
life. The artifact it improves is scheduled for replacement (PM-MCP migration stages 1–6, `doc/roadmap.adoc`
milestones 4–13). Emitting such a plan spends the most expensive resources this system has on a surface that
is being retired: the finalize and review-bot wait cycles, and the operator's attention. The **knowledge** a
plan encodes is still valuable, but only if it reaches PM-MCP's requirements before PM-MCP freezes its
schemas. A defect fixed in Python and never restated as a PM-MCP requirement will be **re-implemented**
in Java.

review-apparatus measured this on its own ten staged plans (77 deliverables):

- **71 of 77** carried implementation-independent content, and **6** were pure script/CLI mechanics.
- Of the 71, only **7** were already stated by PM-MCP, and **51** were a full or partial `gap`.
- It found **3 contradictions**, where PM-MCP's current spec encodes a defect this corpus exists to remove. For
  example, the `finalize.concurrent-wait` matrix routes `completed + 0 findings → merge-gate`, which is the
  "zero findings = clean" collapse.

The gap rate is the reason for this message. It is unlikely to be lower in your corpus.

## 3. What to change: the procedure

Apply this to every row in `staged` (and to `parked` rows you might un-park):

1. **Classify each deliverable, not each plan.** Ask one question: *Does its value survive if every Python
   file and every process document it touches is deleted?*
   - **No** (argparse flags, a doc sentence, step order numbers, a script refactor, a test for a script) →
     `none`.
   - **Yes** → extract the rule, invariant, classification, data or fixture, stated implementation-free in
     1–3 sentences, with any concrete data kept verbatim.
2. **Map each extracted item to PM-MCP.** Grep `plan-marshall-mcp/doc/requirements/*.adoc` and
   `doc/specification/*.adoc` for the closest requirement id (`PM-WF-13`, `PM-IMPL-7`, `PM-TEST-2`, …). Mark
   it `covered`, `partial` or **`gap`**. Flag every contradiction, meaning any case where PM-MCP states the
   opposite of your rule.
3. **Extract the potential issues and file them in PM-MCP** as
   `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/{your-epic-slug}-carry-over.md` (one file per epic;
   the directory exists). Give it a stated population (rows, carry vs none, gap / partial / covered counts),
   put the contradictions first, then the structural gaps, then the per-spec tables. State the source ledger
   (`.plan/orchestrator/{your-epic-slug}/` in plan-marshall) in the intro. Do NOT keep a copy in your own tree.
4. **Park the superseded rows.** Run `orchestrator queue --transition PLAN-X --status parked` for each. Add a
   `SUPERSEDED BY PM-MCP` banner under each spec's title that points at your
   `plan-marshall-mcp/doc/known-defects/{your-epic-slug}-carry-over.md` file and says
   "Do NOT emit; un-park only by explicit operator decision". Spec bodies stay intact, because they hold the
   evidence chain.
5. **Void any emitted-but-not-launched command.** Say so in the resume anchor. Prepend a new block and keep
   the existing anchor document; the anchor is a document, not a headline.
6. **Record the decision.** Log it with `manage-logging decision --store orchestrator`, add a dated `epic.md`
   entry, then run `regenerate-view`.
7. **Write exactly one file in `plan-marshall-mcp`** — your `doc/known-defects/{your-epic-slug}-carry-over.md`
   (operator-authorized 2026-09-26). Do not create or edit anything else in that repository, and do not commit
   there; the operator commits it.

## 4. What stays emittable

These are exceptions to parking. Judge each one explicitly and record the reason:

- **Foreign-repository configuration** that PM-MCP does not replace: GitHub reusable workflows in
  `cuioss-organization`, bot-side settings such as `pr-agent-settings`, and consumer-repo CI.
  review-apparatus kept `PLAN-PR-002` and `PLAN-PR-039` for this reason.
- **Work PM-MCP depends on while legacy and PM-MCP coexist.** PM-MCP's `PM-MIG-2` / `PM-MIG-3` require
  specific plan-marshall-side changes: the `mcp/entry.json` / `co-exist.lock` ownership guard in the
  executor and in every direct state writer; cross-runtime `flock` interop; converting the `.toon`
  auxiliary stores to JSON with a `format_version`. These are enablers of the migration, not legacy
  polish. If a staged plan is one of them, keep it and say so.
- **A defect that actively breaks current delivery.** If a bug blocks plans from shipping today (for example
  a gate that wrongly refuses every merge), fixing it may still be justified. Treat it as a narrow
  operator-confirmed exception, and still extract its invariant for PM-MCP.

## 5. Epic-specific pointers

- **`lessons-routing`:** the same rule applies to lessons. A lesson whose remedy is a Python or prose change
  routes to the carry-over as a rule or fixture, not to a staged plan.
- **`truthful-signals`** (39 staged): this is the largest exposure. Its archetype (a confident signal that
  hides a caveat) is exactly what PM-MCP's representations and state vocabularies must encode, so expect a
  high carry rate and many gaps.
- **`test-quality`:** your ledger is still in the monolithic layout (`legacy_layout`). Run `migrate-layout`
  before step 4, because `queue --transition` refuses a monolithic ledger.
- **`code-intelligence-substrate` / `instrumentation-substrate`:** check each plan against PM-MCP's own
  equivalents before parking. PM-MCP plans a warm LSP pool (`pm_lsp`, PM-SVC-2), `pm://architecture/*`
  resources (PM-EXT-3) and a native build server (PM-SVC-1). Overlapping plans are superseded; genuinely
  missing capabilities are gaps to record.

## 6. Reference implementation

- **Filed example (the target shape):** `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`
  — 44 specs / 340 rows, contradictions first, structural gaps, operator-confirmed emission exceptions, per-spec
  tables with `none (dup)` de-duplication.

review-apparatus did all of the above on 2026-09-26. Read these before starting:

- `.plan/orchestrator/review-apparatus/findings/2026-09-26-pm-mcp-carry-over.md` (the table format, the
  population header, and the contradictions section)
- `.plan/orchestrator/review-apparatus/epic.md` § Open Defects → "2026-09-26 — THE WHOLE STAGED QUEUE IS
  PARKED"
- `.plan/orchestrator/review-apparatus/logs/decision.log` (last entry)

⚠ Its rows were extracted by read-only sub-agents and were not re-verified line by line. Treat its counts as
that epic's figures, not as a template for yours.
