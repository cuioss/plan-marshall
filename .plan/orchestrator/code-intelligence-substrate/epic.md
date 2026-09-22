# Epic: Code-Intelligence Substrate — how the system knows things about the codebase

slug: code-intelligence-substrate

> Ledger document for one epic under `.plan/local/orchestrator/code-intelligence-substrate/`. The
> layout and authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the machine
> authority; any statement here that conflicts with it is stale prose.
>
> **This document carries CURRENT STATE ONLY.** The historical record — every landing, every drained
> inbox message, every decision with its timestamp — lives in `landings/`, `inbox/archive/`, and
> `logs/decision.log`. Nothing here restates it.

## Cloud bridge

Plans from this epic may be executed in the standalone cloud lane instead of the plan-marshall
lifecycle. The mapping between this epic's plan specs and those cloud plans, and the rule for
creating, syncing, and collecting them, are in [`cloud-bridge.md`](cloud-bridge.md).

Read it before staging work for the cloud and before ingesting a landed cloud plan.

## Vision

Plan-marshall answers questions about its own codebase through a substrate it built itself: a files
inventory, a module graph, a build map, and a set of measurement counters. That substrate is
**thinner than its API surface implies** — verbs that return `status: success` over empty or
path-only answers, measurements that are structurally unobtainable at the moment they are read, and
a content-search capability that main context has and dispatched leaves do not.

**Done at the epic level** = a recorded, evidence-backed direction decision, plus the plans that
implement it and retire the gap-filling work the current approach would otherwise keep generating.

### ⛔⛔ 2026-08-09 — THE EPIC'S OWN INSTRUMENT SAYS THE EPIC IS AIMED AT THE SMALLER HALF

The first six-phase instrumented record (PR #1126) splits exploration into what a **code**
substrate could remove and what it could not. **n=1 plan**, all six phases, first-party recompute:

| bucket | share of exploration bytes |
|---|---:|
| index-answerable — what THIS EPIC addresses | **15.9%** |
| **doc-residency — the system reading its own skills, standards, workflow docs** | **65.2%** |
| unattributed | 18.9% |

Exploration is ~77% of tool-result bytes, so doc-residency alone is **≈50% of every tool-result
byte**. ⇒ ⛔ **Plan-marshall spends more context reading plan-marshall than on anything else, and
until 2026-08-09 no plan in a 30-row queue owned it.**

⭐ **The discipline already exists and is already written down** — `code-intelligence.adoc`
§ "Location and strength, never the lines" argues exactly this cost asymmetry. **It was applied
to the codebase and never to the corpus.** → **WS-06** and **PLAN-CIS-039**.

⚠ **This is a challenge, not a refutation, and the distinction is n=1.** `PLAN-CIS-036` D1 is the
verification; `PLAN-CIS-039` D4 is the deliverable permitted to conclude the epic has been aimed
at the smaller half. ⛔ **Neither the 15.9% nor the 65.2% may be quoted as settled until one of
them has run.**

⭐ **And a second factor the same record exposed**: the average byte is **re-read ~44.6 times**,
so a byte costs `1.25 + 0.1 × turns_remaining` — **~5.7× at the mean, ~13.4× entering early in a
122-turn envelope.** **When a byte enters dominates how big it is**, and envelope length was
likewise unowned. → **PLAN-CIS-040**.

## Direction — where the decision stands

| Direction | State |
|---|---|
| **A — own implementation, close the gaps** | **In progress.** WS-01/WS-02 are this direction, now seam-based rather than patch-based. |
| **B — graph backend (`libcgraph`-style store)** | ⛔ **REFUTED TWICE — closed 2026-08-01, do not re-propose.** *First ground (standing):* the edge-derivation path yielded zero rows, so a store sat underneath a derivation that produced nothing. **Storage was never the gap.** *Second ground (new, independent):* even granting the store, cgraph's **differentiator is layout** — not needed — and its **non-differentiator is traversal**, which is ~40 lines of stdlib BFS at our scale (**12 modules here**, order-10² in the largest consumer repos, against cgraph's 10⁵⁺ target). It has no persistence model we want and no query language at all. A native C dependency contradicts the subprocess-free-crawl discipline the whole substrate rests on. ⭐ **The one real offering is DOT rendering — and DOT is a text format**, so a ~20-line serializer plus `dot -Tsvg` gets it with zero dependency. |
| **C — LSP** | ✅ **ADOPTED 2026-08-01 (operator), split by tier.** LSP for working on code is **fixed, not in question**. The internal lookup API is **LSP-shaped** (PLAN-CIS-002, now decided as an additive facade). The settled open question — *server-as-lookup-backend vs graph library* — resolved to **neither, as posed**: see the tier split below. ⛔ **The former "LSP is per-language and would not index markdown/AsciiDoc" objection is WITHDRAWN as worded** — it applies to *reusing off-the-shelf servers*; we would **write** the server, so it indexes whatever we teach it, and `documentLink` is the natural fit for `xref:` integrity. The genuine per-language cost sits at **Tier 2 symbol intelligence** (one parser per language) — an argument against chasing Tier 2 broadly, **not** against the LSP shape at Tier 0/1. |
| **D — plain index / restore `Grep` to leaves** | **Open, and still the cheapest candidate** for the content-search gap specifically (F1/F3 → PLAN-CIS-001). ⭐ Unaffected by the C decision: LSP has no file-glob and no content-search method, so nothing in the LSP adoption closes this. |
| **E — a mixture** | ✅ **CONFIRMED as the operative answer.** The 2026-08-01 analysis settled it concretely rather than as an assumption — the gaps sit at different tiers and take different answers (below). |

### ⭐ The tier split — why "LSP server vs graph library" had no answer as posed

The two do not compete for the same queries, because they occupy different tiers of the ladder
`doc/concepts/code-intelligence.adoc` already commits to:

| Tier | Content | Can an LSP server supply it? | Owner |
|---|---|---|---|
| **Tier 0** — crawl | module set + metadata | ✗ no method | our crawl + the attribution seam (**PLAN-CIS-023**) |
| **Tier 1** — module edges | module→module + provenance | ✗ **no method — LSP has no module concept** | our persisted store + the resolver seam (PLAN-02, shipped) |
| **Tier 2** — symbols | definition, references, rename | ✓ **this is literally what LSP is** | a language server |

⛔ **Every navigation verb in use today — `path`, `impact`, `which-module`, `files`, `neighbors` —
is Tier 1, and an LSP server cannot answer a single one of them at any level of effort.**
Conversely Tier 2 is where building our own means reimplementing jdtls/pyright. Hence: both, split
by tier — not either/or, and no Graphviz on either side.

⭐ **The lifecycle mismatch, and its resolution.** LSP assumes a long-lived editor session
amortizing index cost over thousands of queries; our consumers are **one-shot subprocesses and
dispatched leaves**. Booting a server per query is not viable. The resolution is to make the
language server a **derivation resolver** (**PLAN-CIS-026**) rather than a query backend: it runs
once at derivation time, harvests real symbol references, lifts them file→module through the
attribution seam, and emits edges into the store PLAN-02 already ships — cold start paid once,
reads cheap and persistent, provenance stamped `lsp-{language}`. **This is what finally puts real
edges in the graph**, which F2's retirement explicitly did not do. Live pass-through for genuine
symbol queries (`definition` at a position, `rename`) is the recorded alternative, hosted in the
opt-in `marshalld` daemon, and is deliberately **out of scope** for PLAN-CIS-026.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug code-intelligence-substrate
     Paste the returned block verbatim between the markers. -->

> ⛔ **Superseded anchors are NOT here.** The ~40 KB frozen 2026-08-07 anchor was **relocated
> 2026-08-09** to [`superseded-anchors.md`](superseded-anchors.md), verbatim and complete. It is
> historical and authoritative for nothing — read it only when investigating *why* a past decision was
> made. ⭐ **Why it moved**: this document states it carries **current state only**, and an inert 40 KB
> block loaded by every reader of the epic's hottest file contradicted both that contract and the
> epic's own `WS-06` doc-residency finding. Preserving it was still required — the reason it was
> frozen in the first place was that the text existed nowhere else — so nothing was deleted, only
> moved. ⚠ The 2026-08-08 anchor was **replaced, never frozen**; its durable content had already been
> carried into §§ Structural Findings / Operating Rules / Open Defects. **Do not hunt for a frozen
> 08-08 block.**

<!-- REMOVED 2026-08-09: the verbatim 2026-08-07 anchor previously inlined here now lives, complete, in superseded-anchors.md. -->
-->

⚠ **Cleanup residue, recorded rather than hidden (2026-08-09).** The relocation above removed the
anchor's *head* from this file; its **tail remains inline directly above, inside an HTML comment** —
inert to a renderer, still costing bytes to a reader. It was left because deleting it required
matching a single ~40 KB line, and three partial matches had already produced worse damage than the
residue itself. ⛔ **Nothing is lost**: the complete anchor is in
[`superseded-anchors.md`](superseded-anchors.md), and the commented tail is superseded by it.
⭐ **The honest framing**: this is the *volume-read-as-coverage* archetype pointed at my own cleanup —
"relocated" would have over-claimed, so the residue is named. **A future pass may delete the comment
block wholesale; no reader should consult it.**

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: === 2026-09-15 ANCHOR (18) - PIN REPAIRED AND INDEPENDENTLY VERIFIED. ⛔ THE FULL RESTART IS NOW THE ONLY THING OWED. ===
*** SUPERSEDES ONLY anchor (17)'s pin section and its next-action item (1). EVERY OTHER STATEMENT IN (17) STANDS VERBATIM - the ceiling change to fourteen, the bounded A1 re-grounding and its three yields, the CIS-054 glob-instrument note, the phase results, D29, and the owed-but-unstaged list. ***
*** PIN GATE REPAIRED by the operator running .plan/temp/repair-plugin-pin.py --target 0.1.1670 --apply. Markers-first-then-registry, the proven order: cleared=10, added=10, errors=0, then 18 registry entries repointed. ***
*** ⭐ VERIFIED INDEPENDENTLY AND DOUBLE-SAMPLED BY TWO DIFFERENT METHODS, BOTH AGREEING - the script's own post-check was NOT taken as the verification. Sample 1 (python walk of installed_plugins.json + filesystem marker scan): 19 entries, 0 unresolvable installPaths, registry version AND installPath both 0.1.1670 on 18 entries (the 19th at 1.1.0 is a foreign plugin), executor MARSHALL_VERSION 0.1.1670, unmarked == ['0.1.1670'] on all 10 bundles. Sample 2 (shell walk, independent code path): 10 unmarked rows all 0.1.1670, 36 registry version tokens all 0.1.1670, executor line 0.1.1670, dist-manifest version 0.1.1670 with source_sha == HEAD exactly. BOTH GATES HOLD: executor == installPath, AND unmarked == [executor] on every bundle. ***
*** ⛔⛔ THE RESTART IS STILL OWED AND IS NOW THE ONLY THING OWED. /reload-plugins does NOT re-seat skill markdown bodies. This session is seated from the PRE-REPAIR state, so the next session must start COLD to pick up 0.1.1670. ***
*** ⛔ RE-CHECK THE PIN AT THE START OF THE NEXT SESSION ANYWAY, rather than trusting this record: the standing archetype is that the pin is LEFT BEHIND, not drifting, and EVERY /sync-plugin-cache re-opens the gap. A green reading here is a reading of 2026-09-15, not a property of the machine. ***
*** STATE UNCHANGED at HEAD 7a028157e, worktree CLEAN: 54 shipped / 3 staged (PLAN-CIS-052, PLAN-CIS-050, PLAN-CIS-054, in queue order) / 6 parked / 2 retired. N=1, R=0 - ONE FREE SLOT. Inbox EMPTY. No staged spec is prep-blocked. Corpus reconciles 65/65 both directions. ***
*** NEXT ACTION AFTER THE RESTART: (1) re-verify the pin (see above - re-check, do not trust); (2) re-run corpus surfaces + cross-check + verdicts at whatever HEAD the restart lands on; (3) emit into the free slot - CIS-052 heads the queue and is the most re-grounded of the three. Owed but unstaged, carried from (17): epic.md D22 (re-firing is where the spend is), D30 (two architecture enrich insight calls, recorded and NOT executed - they write git-tracked enriched.json), and the five self-seeding documentation sites from the CIS-049 landing that fold into CIS-054. ***

=== 2026-09-15 ANCHOR (17) - CLEANUP DONE, LEDGER CLEAN, RESTART-READY EXCEPT FOR THE PIN. ⛔⛔ THE PIN GATE IS FAILING AND MUST BE REPAIRED BEFORE THE RESTART. ===
*** SUPERSEDES anchor (16)'s next-action and the ceiling statements in (13)/(16). Everything else in (16) STANDS VERBATIM - the shipped landing, its two anomalies, the D4-D6 not-established note, and the drain record. ***
*** ⭐ OPERATOR DECISION 2026-09-15: TWELVE IS NOT A HARD LIMIT - UP TO FOURTEEN IS OK. It is guidance, not a gate, and it supersedes the ceiling character of the 2026-09-12 directive. Applied: PLAN-CIS-050's "nothing further folds in here" note is corrected in place - it was true at a ceiling of twelve and false now. ⛔ HEADROOM IS NOT A LICENCE: promoted lesson 2026-09-15-08-003 reports the twelve-deliverable PLAN-CIS-049 running 5.2x over its multi_module+bug_fix anchor (10.49M vs 2.0M; 874k tokens per deliverable). A 13th or 14th fold is a decision RECORDED WITH THAT TRADE NAMED, not a slot to fill. ***
*** STATE at HEAD 7a028157e (local == origin/main, worktree CLEAN): 54 shipped / 3 staged / 6 parked / 2 retired (65 rows). Staged, in queue order: PLAN-CIS-052, PLAN-CIS-050 (TWELVE deliverables), PLAN-CIS-054. N=1, R=0 - ONE FREE SLOT. Inbox EMPTY (0 queued, 319 archived, closed_senders empty, invalid 0). Corpus reconciles 65/65 both directions, 0 unreadable. restart-check READY, 5 of 6 scored. ***
*** ⛔⛔⛔ DO NOT RESTART BEFORE REPAIRING THE PIN, AND DO NOT READ PHASE D's READY AS COVERING IT - registry_parity reports not_available and is EXCLUDED FROM THE FLOOR, so a READY verdict is silent on the pin BY CONSTRUCTION. Measured 2026-09-15: executor MARSHALL_VERSION 0.1.1670 vs registry version AND installPath 0.1.1655 across 18 entries (a 15-version gap), unmarked == ['0.1.1655'] on all 10 bundles, 0 unresolvable installPaths. ⭐ 0.1.1670 IS PRESENT in every bundle but is ORPHAN-MARKED, its dist-manifest source_sha equals HEAD EXACTLY, and its content is identical to target/claude/plan-marshall (differing only by .orphaned_at and __pycache__). So the CONTENT is correct and current; the PIN is left behind and the correct build is marked orphan - the recorded archetype, the pin is LEFT BEHIND not drifting, and every /sync-plugin-cache re-opens it. ***
*** ⛔ BOTH PRIOR REPAIR HELPERS HAD BEEN SWEPT FROM .plan/temp/ - a temp cleanup removes them, so do not assume they are there. ONE REPLACEMENT WAS RE-AUTHORED at .plan/temp/repair-plugin-pin.py and DRY-RUN ONLY; repair is OPERATOR-ONLY and was NOT applied. It fixes the half the original could not (the original only ADDED .orphaned_at to non-target dirs and NEVER CLEARED it from the target, so against this state it would write the registry then fail its own post-check). It clears the target's marker first, collects per-directory OSErrors instead of aborting, REFUSES to touch the registry if any marker failed, and runs MARKERS-FIRST-THEN-REGISTRY - the proven order, because a failed registry step then leaves pin=old/unmarked=new and the loader still serves correct content, while the reverse has a live window in which a restart loses. Dry run: cleared=10 added=10 errors=0, 18 registry entries repointed. OPERATOR COMMAND: python3 .plan/temp/repair-plugin-pin.py --target 0.1.1670 --apply ⛔ --target is a VERSION, never a bundle name. ⛔ THEN RESTART FULLY - /reload-plugins does NOT re-seat skill markdown bodies. ***
*** A1 RE-GROUNDING WAS BOUNDED AND SAYS SO IN EVERY VERDICT: 334 files changed since 53ab7dd2e, intersected with each spec's declared surface (CIS-052 13/37, CIS-050 8/38, CIS-054 2/12); claims on untouched files retain their previous verdicts and were NOT re-executed. All three section verdicts re-stamped at 7a028157e by {slug}/cleanup, contradicted/rescoped:yes, so all three ADMIT. ***
*** ⭐⭐ THE PASS'S THREE YIELDS, none of them assumable: (1) CIS-052 ROW 17 RE-CONFIRMED LIVE ON A FILE THAT MOVED - phase-6-finalize/SKILL.md item 5c (:1096) still gates the boundary write on did-NOT-time-out while the cause table (:1105) still defines blocked_session_restart to INCLUDE the timeout firing, so a timed-out finalize step still writes no boundary row. (2) CIS-050 D1(e) CORROBORATED AFTER A NEAR-MISS - a new normative emission-contract docstring in generate_executor.py governs format_surface_stats_line (the stdout LINE), NOT the dry-run count, which still returns dict(_EMPTY_SURFACE_STATS) with scripts_registered 0 while the sibling OSError path sets len(mappings). ⛔⛔ A REFUTATION THAT NAMES A NEARBY MECHANISM IS NOT A REFUTATION OF THE CLAIM - twice in four days now, after the 09-12 D3(a) near-miss. (3) CIS-050 D5(a) POPULATION CORRECTED from an asserted four to a DERIVED eight-of-twenty-four CHECK_ERA entries carrying the literal plan-10 instead of a boundary. ***
*** ⛔ CIS-054's "2 of 12 entries touched" IS THE WRONG INSTRUMENT and the verdict records why: its surface is GLOB-dominated (skills/*/SKILL.md, standards/*.md, doc/user/, doc/concepts/, doc/adr/), so the count counts GLOBS not files, and dozens of documents under them moved. Reading 2/12 as low risk would be the count-without-its-population error that plan exists to correct. ***
*** PHASES: A2 no spec is already-fixed (none has the required POSITIVE account; two had defects re-confirmed live). A3 clean - all three declarative with admits_disjointness_check true. A4 source_origin_match_count 0 over 10 sibling epics. A5 NO REGROUPING, and that is a JUDGEMENT not a skip: regrouped 3 days ago, the raised ceiling adds headroom rather than a reason to re-cut, and churning would cost three freshly-stamped verdicts for nothing. B compact idempotent (epic_changed false, regenerated 0). C archive drain REFUSED per the permanent default - no epic-wide quiescence signal exists (PLAN-TRUTH-032 superseded), and closed_senders is per-sender only, so it cannot rule out a sender that has filed nothing yet. ***
*** ⛔ D29 STILL OPEN and governs the next emit: the literal disjointness gate cannot pass (its population still includes 53 shipped and 2 retired specs). The substitute test - collides iff it overlaps a LIVE plan, or a staged sibling that could run the same round - is what the next emit uses, named in the open again when it does. ⭐ plans_scanned is now 1: the live-plan set has nearly drained, so the next cross-check may be materially cleaner. ***
*** NEXT ACTION AFTER THE RESTART: (1) re-verify the pin gate FIRST - re-check, do not trust this line; (2) re-run corpus surfaces + cross-check + verdicts at whatever HEAD the restart lands on, since a restart-day HEAD will differ; (3) emit into the free slot - CIS-052 heads the queue and is the most re-grounded of the three. Owed but unstaged: epic.md D22 (re-firing is where the spend is), D30 (two architecture enrich insight calls, recorded and NOT executed), and the five self-seeding doc sites from the CIS-049 landing that fold into CIS-054. ***

=== 2026-09-15 ANCHOR (16) - PLAN-CIS-049 SHIPPED (#1489). INBOX DRAINED 71/71. NOTHING RUNNING, SLOT FREE. ===
*** SUPERSEDES anchor (15) entirely and anchor (14)'s emit-state. The re-cut record in (13), the D29 substitute-test record, and the D3(a) narrowing all STAND VERBATIM. ***
*** STATE: 54 shipped / 3 staged / 6 parked / 2 retired (65 rows). Staged, in queue order: PLAN-CIS-052, PLAN-CIS-050 (now TWELVE deliverables), PLAN-CIS-054. N=1, R=0 - ONE FREE SLOT. Inbox EMPTY (0 queued, 319 archived, closed_senders empty, invalid 0). ***
*** SHIPPED: PLAN-CIS-049 as PR #1489, merge commit 7a028157e, archived to .plan/local/archived-plans/2026-09-15-architecture-store-query-truthfulness. CORROBORATED before any ledger write: ci pr view state merged, merge_commit_sha matches, git merge-base --is-ancestor against origin/main YES, archive dir listed. Landing record at landings/PLAN-CIS-049.md. landing-check complete:true, missing_keys[0] - the epic's SECOND complete landing. ***
*** ⚠ origin/main HAS ADVANCED PAST THE LANDING (ab86d7cbf/#1494 and others sit above 7a028157e). Every staged spec's section verdict is stamped at 53ab7dd2e and is now several landings stale. RE-GROUND BEFORE THE NEXT EMIT. ***
*** ⛔⛔ TWO ANOMALIES IN THE LANDING ITSELF, both recorded in landings/PLAN-CIS-049.md rather than smoothed over. (1) The landing-facts block says deliverables_total=12 while the PR body AND the spec both say TEN. Both halves report complete, so nothing is outstanding on either reading, but the two counts are not the same number and neither derives from the other - do not carry either forward without re-deriving from the archived task set. (2) TWO COST FIGURES THAT MUST NEVER BE CONFLATED: landing-facts total_tokens=5,299,565 for the whole plan, while plan-retrospective flagged 10.5M against a 2.0M anchor for the finalize+execute stretch ALONE. A stretch cannot cost twice the whole, so they measure different populations (almost certainly dispatched vs billing-weighted). Neither is publishable without naming which it is. ***
*** ⛔ THE LANDING ANALYSIS RECORDS D4, D5 and D6 AS **NOT ESTABLISHED**, not as shipped. The PR body was read in excerpt and those three fell outside it. The plan reports 12/12 done so they are almost certainly shipped - but almost certainly is not corroboration, and this epic does not record inferred completion as observed completion. Re-read the archived plan if the distinction matters. ***
*** DRAIN 71/71, 0 invalid, 0 staged: 1 landing reconciled; 64 candidate-lessons PROMOTED to the global corpus (129 -> 193); 1 folded as a RECURRENCE onto lesson 2026-09-04-08-007 (third instance, 44 tasks done / 40 [OUTCOME] lines); 2 insight hints recorded as OWED and NOT EXECUTED (epic.md D30 - architecture enrich insight writes git-tracked enriched.json, so it is a repository change outside this identity); 1 finding routed to parked PLAN-CIS-039; 1 absorbed as Watch W-049; 1 folded into PLAN-CIS-050 D12. ⭐ Dedup was DERIVED - 65 titles x 129 corpus titles by normalized similarity, exactly one crossed threshold - not eyeballed over 8,385 pairs. ***
*** ⛔⛔ THE ONE THING THIS DRAIN MUST NOT BURY, AND IT IS ABOUT THIS EPIC'S OWN OPERATING RULE: promoted lesson 2026-09-15-08-003 (phase-4-plan, improvement) is titled "Split a 12-deliverable, 44-task multi_module plan before executing it". Figures: 10,488,689 tokens against a multi_module+bug_fix ERROR anchor of 2.0M - 5.2x - and 380 min worked against a 150-min error anchor; 5-execute alone 6,330,694 (60%) over 18 dispatches and 3 re-entries; 6-finalize 2,412,805 over 12 dispatches with 4 loop-backs; 874,057 tokens per deliverable. Its remedy: teach phase-4-plan to read the SAME (scope_estimate, change_type) anchor table the retrospective scores against (plan-efficiency.md section 2 - an existing calibration, not a new one) and surface a split proposal BEFORE execute. ⚠ THIS IS EVIDENCE ABOUT THE 2026-09-12 RE-CUT, NOT A REFUTATION OF IT: the re-cut's shared-target rationale bought real things this landing demonstrates (the CIS-058 merge dissolved an emission exclusivity; D7 shipped as COMPLETE-the-rule rather than build-it). What the lesson adds is that a twelve-deliverable plan is scored against an anchor calibrated on plans an order of magnitude smaller, and the mismatch is only found after the spend. BOTH STAND. The operator was shown this at the drain rather than having it filed silently into a 193-lesson corpus. ***
*** PLAN-CIS-050 IS NOW AT TWELVE DELIVERABLES - THE CEILING EXACTLY. D12 (the execution-context level ladder as an unmeasured cost lever) folded in from next-level-001, with +5 surface entries declared in the same edit and verified through corpus surfaces (42 -> 47 claimed paths). ⛔ NOTHING FURTHER FOLDS INTO CIS-050; a thirteenth signal on that subject is staged as its own spec or routed to another epic. ⛔ D12 MEASURES ONLY - re-pinning a level is a behavioural change downstream of next-level WS-01, which is unbuilt, and no saving may be estimated because the source paper supplies none. ***
*** ⛔ W-049 (grounded evidence pinning, openwiki prior art) IS UNDER A STANDING OPERATOR INSTRUCTION NOT TO STAGE OR VALIDATE EARLY: validate only after the substrate is implemented AND several plans have executed against it, because the real failure modes are population statistics (false-stale rate, unresolved rate, coverage, realized token delta) that no test suite or single plan can show. Do not open a workstream. Do not adopt the tool - the mechanic is the asset. Its completeness-over-count guidance does NOT transfer: a pinning layer buys no-false-positives, not no-false-negatives. ***
*** RESIDUE OWED FROM THE LANDING: six out-of-footprint self-review findings became lessons 2026-09-14-21-001/-002/-003, and FIVE OF THEM ARE DOCUMENTATION SITES RESTATING A SUPERSEDED module_edges/content_search STATUS VOCABULARY - which is PLAN-CIS-054's subject exactly, now with their locations named. ⭐⭐ That five-site shape is the SELF-SEEDING archetype (PLAN-TRUTH-089: 27% of finalize findings); the terminating move is REPLACE THE RESTATEMENT WITH A POINTER AT ITS SOURCE, not correct five copies into five new copies. Fold into CIS-054 when it is next touched. ***
*** ⛔ D29 STILL OPEN and still governs the next selection: the literal disjointness gate cannot pass (4295 overlap rows over a population including 53 shipped and 2 retired specs). The substitute test - collides iff it overlaps a LIVE plan, or a staged sibling that could run the same round - is what the next emit uses, named in the open again when it does. ***
*** NEXT ACTION: a slot is free. Re-run corpus surfaces + corpus cross-check + corpus verdicts at current HEAD (they are stale at 53ab7dd2e), re-ground the selected survivor, then emit. CIS-052 heads the queue; check whether plan-truth-127's 11-file collision has cleared, since plan-truth-103 already left the live set and plan-truth-139 LOOPED BACK to 5-execute rather than landing. ⚠ Before emitting, consider the operator question the drain raised: whether the twelve-deliverable ceiling stands as-is, given CIS-050 now sits at exactly twelve. ***

=== 2026-09-13 ANCHOR (15) - PLAN-CIS-049 IS RUNNING. ZERO SLOTS FREE. ===
*** SUPERSEDES anchor (14)'s emit-state and next-action statements, and CORRECTS one factual line in it (see the plan-truth-139 note below). Every other statement in (14) and (13) STANDS VERBATIM - the D29 substitute-test record, the re-cut record, the D3(a) narrowing, and the parked-not-retired note. ***
*** STATE: 53 shipped / 3 staged / 1 RUNNING / 6 parked / 2 retired. Staged, in queue order: PLAN-CIS-052, PLAN-CIS-050, PLAN-CIS-054. N=1, R=1 ⇒ NO FREE SLOT. Do not emit again until CIS-049 lands. Inbox EMPTY (0 queued, 248 archived). ***
*** RUNNING: PLAN-CIS-049 (architecture-store-and-drift-detector truthfulness, 10 deliverables), lifecycle plan id architecture-store-query-truthfulness, stamped on the row. Operator confirmed launch AND start in one message, so the row went staged -> running directly; no launched state was ever observed and none was written. CORROBORATED at the time of the write, not taken on the report: manage-status list showed it at 4-plan, in_progress, location current. ***
*** ⛔ CORRECTION TO ANCHOR (14): it said all four colliding live plans were at 6-finalize and the collisions may clear within hours. TWO of them have moved and neither moved the way that sentence assumed. plan-truth-103 has LEFT the live set entirely (CIS-052's claude_runtime.py collision is CLEARED). plan-truth-139 moved BACKWARD, 6-finalize -> 5-execute - a LOOP-BACK - so its audit.py collision with CIS-050 and CIS-054 is live and is now longer-lived, not shorter. ⭐ A plan at 6-finalize is NOT a plan about to land; read the phase again rather than extrapolating from it. ***
*** WHAT THE NEXT EMIT MUST RE-DERIVE, not inherit: CIS-049's own surface moves under the other three while it runs, and the live-plan set has already changed twice in one day. When CIS-049 lands, re-run corpus surfaces AND corpus cross-check before selecting - and re-ground the survivor. The 2026-09-12 re-cut left CIS-050 x CIS-052 contending on four files and CIS-050 D8 / CIS-054 D7 sharing one population gate; both constraints are recorded in the specs themselves. ***
*** ⛔ D29 STILL OPEN and still governs the next selection: the literal disjointness gate cannot pass (4295 overlap rows over a population that includes 53 shipped and 2 retired specs), so the substitute test - collides iff it overlaps a LIVE plan, or a staged sibling that could run the same round - is what the next emit uses, named in the open again when it does. It retires when corpus cross-check filters by queue status and publishes both the filtered population and what it excluded. ***
*** NEXT ACTION: none until CIS-049 lands. On its landing, run analyze (the drain will also pick up whatever the plan wrote to the inbox), reconcile the row to shipped with its PR and landing record, then re-select from the three remaining staged specs on freshly derived reads. ***

=== 2026-09-13 ANCHOR (14) - EMIT ROUND: PLAN-CIS-049 EMITTED, AWAITING OPERATOR-CONFIRMED LAUNCH. ===
*** SUPERSEDES anchor (13)'s emit-state and next-action statements ONLY - in particular (13)'s "NOTHING IS EMITTABLE" line, which was true under the literal gate and is superseded by the substitute test recorded as epic.md D29. Every other statement in (13) STANDS VERBATIM, including the whole re-cut record, the D3(a) narrowing, and the parked-not-retired note. ***
*** STATE at HEAD 38af136ed (moved from 53ab7dd2e; 7 commits, incl. #1472 containment-aware overlap and #1473 the foreign-gate landing): 53 shipped / 4 staged / 6 parked / 2 retired. N=1, R=0. Nothing running. Inbox EMPTY (0 queued, 248 archived). ***
*** EMITTED: PLAN-CIS-049 (architecture-store-and-drift-detector truthfulness, 10 deliverables). auto_emit is FALSE, so NO launched transition is recorded - the operator confirms the launch, and only then does the row move staged -> launched. EMIT IS NOT RUNNING. ***
*** PREP: all four staged specs ADMIT. All four section verdicts are STALE (stamped at 53ab7dd2e, HEAD is 38af136ed) - staleness is REPORTED, NEVER PROMOTED, so no admission outcome moved. blocking_count 7, every one on a parked or retired spec. ***
*** ⛔⛔ WHY CIS-049 AND NOT CIS-052, WHICH HEADS THE QUEUE: the literal disjointness gate refuses ALL FOUR and is DEGENERATE - file_overlap_match_count 4295 over a population that still includes 53 SHIPPED and 2 RETIRED specs, so its negative is unreachable and its silence is not a clean reading. Recorded as epic.md D29 with the substitute test stated in the open: a candidate collides iff it overlaps a LIVE plan, or a staged sibling that could run the same round (vacuous at N=1). Live-plan overlap: CIS-052 13 files (plan-truth-127 alone contributes 11, squarely its own D2 surface - manage-status/SKILL.md, _status_query.py, phase-5-execute); CIS-054 4 (audit.py + three doc/user pages, plan-truth-139); CIS-050 3 (audit.py, a CORE D5 surface, plan-truth-139); CIS-049 4 but ALL PERIPHERAL - _cmd_lifecycle.py (one D5 sub-item plus a D6 test-only reference) and three test files, none of them in its manage-architecture core. ⭐ Least-conflicted on SUBSTANCE, not on count - CIS-050 has fewer overlapping files and a worse one. ***
*** ⚠ ALL FOUR COLLIDING LIVE PLANS ARE AT 6-FINALIZE (plan-pr-046, plan-truth-103, plan-truth-127, plan-truth-139), so these collisions may clear within hours. IF THE LAUNCH IS DEFERRED, RE-RUN corpus surfaces + corpus cross-check BEFORE CONFIRMING - a cleared collision may make CIS-052 emittable in its own queue position, and CIS-049's own overlap may vanish. ***
*** ⛔ THE SUBSTITUTE TEST IS A RECORDED ORCHESTRATOR JUDGEMENT, NOT A NEW RULE. It retires the day corpus cross-check filters its corpus_spec candidates by queue status and publishes both the filtered population and what it excluded. Do not let it harden. ***
*** NEXT ACTION: operator confirms or refuses the CIS-049 launch. On confirm: queue --transition PLAN-CIS-049 --status launched, then the plan lifecycle owns it. On refusal or deferral: re-run the two corpus reads after the finalize-stage plans land and re-select. ***

=== 2026-09-12 ANCHOR (13) - INBOX DRAINED (1/1) AND THE STAGED CORPUS RE-CUT 8 SPECS -> 4. NO STAGED SPEC IS PREP-BLOCKED ANY MORE. ===
*** SUPERSEDES anchor (12)'s STATE, inbox, emit-candidate and next-action statements. Anchor (12)'s PIN section is superseded by the reading below; every other statement in (12), (11) and (10) STANDS VERBATIM. ***
*** STATE: 53 shipped / 4 staged / 6 parked / 2 retired (65 rows). Staged, in queue order: PLAN-CIS-052, PLAN-CIS-049, PLAN-CIS-050, PLAN-CIS-054. Worktree CLEAN at 53ab7dd2e. ***
*** INBOX DRAIN: 1 of 1 consumed and archived (truthful-signals-059.md, 2 forwarded consumer-repo items). Both FOLDED, neither staged. Item 1 -> CIS-050 D7 (stale-base-ref footprint inflation, now n=3) as epic.md D26; Item 2 -> CIS-049 D10 (diff-modules reports an INDETERMINATE comparison as changed) as epic.md D27. Neither fold added a file surface, and both said so in the decision line. Post-drain the inbox is the EMPTY zero. ***
*** ⭐⭐ ITEM 2 WAS FILED AS A HYPOTHESIS AND IS NOW CONFIRMED FIRST-PARTY, which is why it became a deliverable rather than a watch: cmd_diff_modules (_cmd_client_handlers.py:1359-1372) treats snap_sha is None as `changed` while its own comment concedes the sha surface cannot certify equality, and `git ls-files .plan/` returns 14 paths - marshal.json, _project.json, 12 x enriched.json - with ZERO derived.json. So against any git-archive baseline of committed descriptors, changed == every module BY CONSTRUCTION, on every run, in every repo that commits its descriptors. Token-Sheriff's 18-of-18 and a 12-of-12 here are one defect. ***
*** ⭐⭐⭐ RE-CUT (operator directive: larger plans, ceiling TWELVE deliverables, group same targets). This SUPERSEDES persona identity attribute 8's ~6 presumptive split for this corpus. 41 deliverables in, 41 out, nothing dropped: CIS-049 absorbed CIS-058 (6->10), CIS-050 absorbed CIS-057 (7->11), CIS-052 absorbed CIS-061 (6->10), CIS-054 absorbed CIS-056 (6->11). Each absorbed spec keeps its file with a RETIREMENT HEADER naming its deliverables' new addresses one-for-one. Full record at epic.md § 2026-09-12 Spec re-cut. ***
*** ⛔ THE FOUR ABSORBED ROWS READ `parked`, NOT `retired`, AND THIS IS A TOOLING GAP NOT A JUDGEMENT (epic.md D28): `queue --transition` refuses `retired` - accept-set is landed/launched/parked/running/shipped/staged - even though PLAN-CIS-008 and PLAN-CIS-055 already CARRY that status from the pre-verb whole-array rewrite. `parked` was chosen because it removes the row from the staged emit walk. READ THE SPEC HEADER, NOT THE STATUS: these are ABSORBED and must never be resumed. ⛔ Do NOT repair this with a whole-array manage-status update-field --field plans rewrite - that is the D15 hazard. ***
*** ⭐⭐⭐ blocking_count 11 -> 7, and ALL 7 SURVIVORS SIT ON PARKED OR RETIRED SPECS. No staged spec carries a blocking verdict. All four section verdicts re-stamped contradicted/rescoped:yes at 53ab7dd2e by code-intelligence-substrate/analyze, each naming what it absorbed. ***
*** ⛔⛔ THE MOST IMPORTANT SINGLE FINDING OF THIS SESSION - A REFUTATION THAT NAMES A NEARBY MECHANISM IS NOT A REFUTATION OF THE CLAIM. The 09-05 re-grounding reported CIS-050 D3(a) closed by #1268 because _resolve_declared_footprint now catches WorktreeResolutionError and returns None instead of Path.cwd(). TRUE of the exception path, FALSE of the claim's own mechanism: PlanContext._resolve_worktree_face (file_ops.py:1199-1216) deliberately returns the MAIN CHECKOUT for a `pending` worktree WITHOUT raising - its docstring says so - and verify_failure_scope still does not gate on has_worktree. So a clean foreign checkout still yields a measured-empty footprint and exclusively_out_of_scope on no evidence. D3(a) is NARROWED, NOT STRUCK. Taking that refutation at face value would have struck a live defect. ***
*** OTHER ABSORPTIONS, all re-verified first-party at HEAD, none taken on the pass's word: CIS-052 D1(a)-(d) STRUCK - the dispatch-seam migration landed and the deliverable's OWN skill-wide exit condition (no --message [DISPATCH] anywhere under skills/phase-6-finalize/) is met; D1 survives as (e) alone. CIS-050 D5(f) STRUCK (#1339; _DESTROYS_MARKER at test_finalize_edge_ordering.py:81). CIS-049's _project.json staleness claim RETRACTED (tracked, but description and modules key set both correct) - only the no-derived.json coverage fact survives, and it is handed to D10. CIS-054's "That directory IS absent entirely" DELETED as false - cloud-runs/ holds 46 directories, 37 with a gaps.md - so D6's corrected gating derivation is MANDATORY, not precautionary. CIS-061's merged D8 re-scoped from the PREDICATE to the THRESHOLD: the emit site already consults tasks_remaining (execution.md:199, B7 at phase-5-execute/SKILL.md:1173-1181, machinery dating to #349/#714/#730/#842). ***
*** ⛔ WHAT THE RE-CUT DID NOT DISSOLVE, and each is recorded in the surviving spec rather than left to be rediscovered: (1) the four-file contention between CIS-050 and CIS-052 (manage-metrics.py, data-format.md, analyze-logs.py, phase-5-execute/SKILL.md) - CIS-061 overlapped CIS-050 more heavily but CIS-050 was already at ELEVEN and taking it would have breached the ceiling; (2) CIS-054 inherits CIS-056's collision with live PR #1398 on audit.py; (3) CIS-050 D8 and CIS-054 D7 ARE THE SAME POPULATION GATE over .plan/local/archived-plans/ - both specs now carry a must-not-diverge rule, whichever runs second cites the first's published population and reports any difference as a finding. ***
*** ⛔⛔ NOTHING IS EMITTABLE RIGHT NOW, AND THE BLOCKER IS DISJOINTNESS, NOT PREP. All four staged specs are declarative with admits_disjointness_check true (claimed counts 38/42/41/24), so the gate can SEE them - and every one of them carries file_overlap_matches rows. SIX live plans are in flight (plan-pr-046 6-finalize, plan-truth-103 5-execute, plan-truth-127 5-execute, plan-truth-139 6-finalize, the-foreign-gate-population-and-branch-f-recovery 6-finalize, NO_PLAN) and they collide with all four: CIS-052 x plan-truth-127 on 4 files, CIS-050 and CIS-054 x plan-truth-139 on audit.py, CIS-049 x plan-truth-127 and x the-foreign-gate plan, CIS-052 x plan-pr-046 and x plan-truth-103. The four ALSO mutually overlap (CIS-050 x CIS-052 on 8 files, CIS-050 x CIS-054 on 8, CIS-052 x CIS-054 on 5), which under parallelization_scope = 1 is sequencing, not a concurrency block. ⇒ RE-RUN corpus cross-check AFTER those live plans land; the survivor is re-grounded before emit. ***
*** PIN GATE READ 2026-09-12 AND IT IS TRUE: executor MARSHALL_VERSION 0.1.1644; installed_plugins.json carries 18 plan-marshall entries at version AND installPath 0.1.1644 (a 19th entry at 1.1.0 is a foreign plugin), 0 unresolvable installPaths; unmarked == ['0.1.1644'] on all 10 bundles. GATE executor == installPath HOLDS. ⚠ Anchor (12)'s 1622 repair narrative is HISTORY - a sync has happened since. ⛔ The restart anchor (12) declared owed was against 1622; the cache is now 1644, so RE-CHECK THE PIN AT THE START OF THE NEXT SESSION rather than trusting this line. ***
*** NEXT ACTION: (a) wait for the live plans to land, then re-run corpus surfaces + corpus cross-check and emit whichever of the four clears - CIS-052 is the natural head of the queue but carries the heaviest live collision (plan-truth-127, 4 files); or (b) stage epic.md D22 (re-firing is where the spend is), still UN-OWNED after three anchors; or (c) settle epic.md D28 (the retired-status tooling gap) so the four absorbed rows can carry their true status. ***
*** STANDING, unchanged from (12): corroborate against origin/main AND PR state before any shipped transition; every set-guarding detector must be POPULATION-DERIVED; a STEP-marker count is a FLOOR; LOWERING EFFORT LEVELS IS NOT A SANCTIONED SAVING; read queue counts and order from status.json plans array order, never from prose; the pin detector is truthful-signals PLAN-TRUTH-059, do NOT stage a CIS-side one; CHECK THE PLUGIN REGISTRY PIN BEFORE EVERY PLAN LAUNCH; NEVER accept a clean first-pass audit in this epic without the adversarial pass. ***
*** ⛔ ANCHOR HYGIENE: the defect ids D16-D20 are used TWICE in epic.md § Open Defects (top-level bullets and the 2026-09-08 drain's #### sub-blocks). D26/D27/D28 are allocated above both ranges. Resolve at the next cleanup, not by renumbering mid-flight. ***

=== 2026-09-08 ANCHOR (12) - CLEANUP DONE, PIN REPAIRED, RESTART-READY. ⛔ A FULL SESSION RESTART IS OWED BEFORE ANY LAUNCH. === *** SUPERSEDES anchor (11)'s inbox and pin statements; every other statement in (11) and (10) STANDS VERBATIM. *** RESUME HERE AFTER THE RESTART: the epic is idle and consistent - nothing is running, nothing is queued, and the next action is a decision, not a repair. *** STATE: 53 shipped / 8 staged / 2 parked / 2 retired. Inbox is the EMPTY zero (0 queued, 247 archived, closed_senders empty, invalid 0) - a later message from any sender is still possible. Worktree CLEAN at 33c8140f3. restart-check verdict READY, 5 of 6 signals scored. *** INBOX DRAIN COMPLETED THIS SESSION: 5 of 5 truthful-signals findings consumed and archived, 0 staged, yielding Open Defects D20-D25 recorded under ## Open Defects. Folds owed AT SPEC LEVEL: D20 to CIS-049, D21/D23/D25 to CIS-050, D24 to CIS-061 - all three specs are already prep-blocked and need corrections anyway, so the folds ride with those corrections. D22 (re-firing is where the spend is) is UN-OWNED and NOT STAGED. *** ⛔⛔ PIN GATE WAS FAILING AND HAS BEEN REPAIRED - AND THE restart-check READY VERDICT DOES NOT COVER IT. registry_parity reports not_available and is excluded from the floor, so a READY verdict is silent on the pin by construction. Observed: installPath 0.1.1592 vs executor 0.1.1622, a 30-version gap, with unmarked == [] on all 10 bundles - the ZERO-UNMARKED shape, where neither the pin nor the executor's own target is live to the loader and the foreign GC has scheduled both. Double-sampled seconds apart by two different methods, both agreeing, so the reading was not torn. *** ⛔ THE EXISTING REPAIR SCRIPT COULD NOT FIX THIS STATE, and this is worth keeping: .plan/temp/repair-plugin-pin.py only ADDS .orphaned_at to non-target dirs and NEVER CLEARS it from the target. That handles the two-dirs-unmarked state its docstring describes but NOT the unmarked == [] state the SAME docstring names as equally a failure. Run as-is against our state it would have written the registry and then failed its own post-check, leaving pin 1622 with nothing unmarked. ⇒ Wrote .plan/temp/repair-markers-only.py for the missing half: never touches .in_use, wraps every marker mutation in try/except OSError and collects rather than aborting, and stays SPLIT from the registry write. *** REPAIR APPLIED MARKERS-FIRST-THEN-REGISTRY, the proven order - a failed registry step then leaves pin=old / unmarked=new and the loader follows the unmarked dir, so it still serves correct content; the reverse order has a live window in which a restart loses. 10 markers cleared, 0 added, 0 OSErrors. VERIFIED ON ALL FOUR TERMS: registry version AND installPath both 0.1.1622 across 18 entries / 10 keys, 0 installPaths failing to resolve, executor MARSHALL_VERSION 0.1.1622 single-version, unmarked == ['0.1.1622'] per bundle double-sampled. GATE executor==installPath is now TRUE. Cache 0.1.1622 was confirmed byte-identical to target/claude/plan-marshall BEFORE repointing, and dist-manifest source_sha equals HEAD exactly. ⚠ 18 entries across 10 keys - a survey that counts keys reports 10 and is wrong; iterate ENTRIES. *** ⛔ RESTART IS OWED, NOT OPTIONAL: /reload-plugins does NOT re-seat skill markdown bodies. This session is seated from target/claude/ so its own reads were never at risk, but the next session must start cold to pick up 1622. *** CLEANUP PHASES: A1 re-grounding was done at 28b578f1e; all 50 verdict rows now read stale true because HEAD advanced to 33c8140f3, and blocking_count is UNCHANGED at 11 - staleness is REPORTED, NEVER PROMOTED, exactly as specified, so no admission outcome moved. A3 ambiguity is CLEAN OVER THE LIVE SET: all 8 staged specs are declarative with admits_disjointness_check true; the 11 indeterminate surfaces (8 prose + 3 absent) are all shipped or retired specs. A4 duplication: two candidates, CIS-052 row 20 vs CIS-057 claim 1 (the same reconcile-ledgers zero-call-sites fact) and CIS-061 vs truthful-signals PLAN-TRUTH-107 (cross-epic, same defect - see D24). Phase B compact: all three invariants ok, unreachable_count 0. Phase C archive drain: REFUSED per contract, no epic-wide quiescence signal exists and closed_senders is per-sender only. *** NEXT ACTION IS A CHOICE, not a repair: (a) emit PLAN-CIS-057, the sole staged spec passing BOTH gate halves - re-run corpus surfaces and corpus cross-check first, since HEAD moved; or (b) do the spec-correction pass on the six prep-blocked specs (052, 049, 050, 054, 058, 061), which is the critical path for everything except 057 and carries the D20/D21/D23/D24/D25 folds with it; or (c) stage D22. CIS-056 admits on prep but still collides with live PR #1398 on audit.py. === 2026-09-08 ANCHOR (11) - PLAN-CIS-053 SHIPPED (#1443, merged 33c8140f3) AND FULLY RECONCILED. NEXT EMIT CANDIDATE IS PLAN-CIS-057. === *** SUPERSEDES anchor (10) and every emit/queue statement below it; the anchor-(10) re-grounding findings all STAND VERBATIM. *** LANDING CORROBORATED BEFORE ANY WRITE: ci pr view 1443 returns state merged, merge_commit_sha 33c8140f3c6bad10343d5016b12ed0283fa3e83a, equal to main HEAD. Row is shipped with all three result fields stamped by their own set-row calls (pr 1443 / landings/PLAN-CIS-053.md / test-suite-anti-vacuity); landing record written; landing message archived. Tally is now 53 shipped / 8 staged / 2 parked / 2 retired. *** ⛔ TWO OPEN DEFECTS FROM THIS LANDING. D-L1: inbox landing-check returns complete false with missing_keys = the WHOLE required set of 8 - the landing carries no machine-readable facts block at all, so every fact in the landing record was recovered BY HAND from the PR and git rather than drained. A later paste from this plan may still surface what the inbox did not. D-L2: the run's own routed-defect counts disagree three ways - PR body 7 defects, landing message 9 defects / 4 writes, operator report 10 defects / 5 writes. DERIVED by enumerating every message from sender test-suite-anti-vacuity across ALL epics: FIVE finding messages exist (review-apparatus 001 archived + 002 + 003 queued; truthful-signals 001 + 002 both archived). The operator's 5 is CORRECT; the landing message's 4 UNDER-RECORDS. ⛔⛔ THE TRAP THIS NEARLY CAUSED, WORTH MORE THAN THE FINDING: truthful-signals inbox list reports count 0 because THAT VERB DOES NOT ENUMERATE ARCHIVED MESSAGES. Reading that zero as nothing-was-written would have manufactured a false under-recording finding. Enumerate the archive before calling any inbox zero an absence. *** CARRY-OUTS FROM THE RUN, ALL WORTH KEEPING. (1) Lesson 2026-09-07-21-001, TWO-SIDED BRACKETING: an arm placed INSIDE an accepted region proves the region is at least that wide and is SILENT on it being too wide. Four such arms look thorough and are a ONE-SIDED PROOF - every one of the five archetype recurrences entered through the side no arm watched (disjointness to sentence co-occurrence to destination preposition to target noun to aggregate-count-vs-identity-multiset). Proven by PROBE, not argued: widening the heading terminator's {0,3} to any indent left all four ADMIT arms, the level-4 control AND the live-document assertion green. Rule: for a BOUND, require one arm that reddens on widening and one on narrowing, and state in the fix record which direction each arm pins. (2) 93 PERCENT OF THE HEAD-DEPENDENT RE-FIRE CYCLE PRODUCED NOTHING - 5 of 6 head-bound steps fired 38 times with zero findings across the whole run; only pre-submission-self-review ever went red; pyproject_build owns 50.3 percent of all script time driven by steps that never turned red. The entire detection surface was TWO gates. This is a measured, UN-OWNED cost defect belonging to WS-04/WS-06 - ⛔ NOT YET STAGED, stage it before the next cost plan. (3) EIGHT INSTRUCTIONS PASSED DOWN WERE REFUTED BY MEASUREMENT - three in task descriptions, five premises supplied to dispatches, including 'no further CodeRabbit round is obtainable' and calling a fix 'structurally immune' when it was not. Each is recorded at the commit or decision-log entry carrying it rather than quietly corrected. Same discipline the re-grounding pass applies to staged specs, now observed applying to IN-FLIGHT INSTRUCTIONS. (4) ONLY 1 OF 3 REVIEWERS WAS MEASURABLE - cuioss-review-bot participated repeatedly with EVERY ARTIFACT EMPTY, sourcery refused structurally on every pass (7848-line diff against a 150000-character cap). Filed as 1b0984. CodeRabbit itself: 25 actionable findings over 5 rounds, 19 fixed, 72 percent resolved-as-fixed, and FOUR of its rounds each found a defect in the fixes for the round before. (5) Cost 17.2M tokens / 376M billing-weighted against a 2.5M anchor - 6.5x, and the landing calls it a FLOOR. *** ⛔ EPIC INBOX NOW CARRIES 5 QUEUED FINDINGS from truthful-signals (054-058, all live and valid). A DRAIN IS OWED and is separate work from emission. *** NEXT EMIT: the anchor-(10) gate state is unchanged except that CIS-053 has left the pool. Six of the eight remaining staged specs are still PREP-BLOCKED on refutations (052, 049, 050, 054, 058, 061) and need spec corrections before they re-enter the pool; CIS-056 admits on prep but still collides with live PR #1398 on audit.py. ⇒ PLAN-CIS-057 is the sole qualifier on BOTH halves and is the next candidate at N=1. Re-run the two corpus reads before emitting - HEAD has moved from 28b578f1e to 33c8140f3, so every verdict stamped in the anchor-(10) pass is now STALE (reported, never promoted). *** ⛔ PIN GAP: sync-plugin-cache in this run moved the cache to 0.1.1622 and regenerated the executor. RE-CHECK executor == installPath before launching anything. === 2026-09-05 ANCHOR (10) - FULL GROUND-TRUTH RE-GROUNDING DONE AT HEAD 28b578f1e. PLAN-CIS-053 STILL THE SOLE EMITTABLE CANDIDATE, NOW ON A RE-GROUNDED BASIS. === *** SUPERSEDES anchor (9) and every verdict/queue statement below it; all other statements stand verbatim. *** SCOPE OF THE PASS: 46 commits had landed since the prior re-grounding sha 91a07aaa4. 11 specs (9 staged + 2 parked) were re-derived from the tree by dispatched read-only execution-context-level-3 leaves, 149 claim rows examined, every verdict persisted through corpus set-verdict with producer code-intelligence-substrate/cleanup. NOTHING was taken from a spec's own narrative or its existing verdict. *** LEDGER GROUND TRUTH, all derived: 65 rows / 65 specs bidirectional with 0 rows_without_spec, 0 specs_without_row, 0 unreadable; all 52 shipped rows' PR numbers confirmed present in main's history over 2230 commits scanned, 0 rows unstamped; every landing file present on disk; both parked PRs (1149, 1178) in main; inbox is the EMPTY zero (count 0 / live 0 / closed_senders [] / invalid 0); source_origin_match_count 0 over plans_scanned 5, so NO staged row is secretly running. *** ⛔⛔ THE HEADLINE: blocking_count went 1 to 11, and SIX OF NINE STAGED SPECS ARE NOW PREP-BLOCKED ON REFUTATIONS. CIS-052 - D1a-D1d are DEAD, the dispatch-seam migration has ALREADY LANDED (finalize-step-simplify.md and pre-submission-self-review.md both call effort resolve-target with --workflow/--plan-id/--caller; lessons-capture.md and adr-propose.md both already defer to the seam); 19 of its 22 rows still stand. CIS-058 - D1 is DEAD, commit 7845a4b9a (#1370) shipped _analyze_documented_verb_set_drift.py with rule_id documented_verb_set_drift, and it already publishes population_size; claim 4's consume-the-argparse-seam hypothesis is not merely unrealised but CONTRAINDICATED (that seam's own docstring records a static AST walk abandoned after 1323 false positives). CIS-050 - 2 of its 3 refutations were ALREADY TRUE AT 91a07aaa4 (#1268 removed the cwd-fallback, #1339 closed the destroys-blind canary and is the very commit its own D7 cites), so the prior blanket unverifiable PAPERED OVER STALE CLAIMS. CIS-049 - _project.json is not stale on the axis its claim anchors on; 30 of 34 rows still stand, including a live-execution proof that find and which-module name DIFFERENT owners for README.md. CIS-054 - its § D6 body premise 'That directory IS absent entirely' is FALSE; three cloud-runs gaps.md files were read directly and are present, so D6 would take the discharged-by-collection fallback it exists to disarm. CIS-061 - the voluntary_checkpoint emit site DOES consult tasks_remaining (execution.md:199, plus B7's no-progress reclassification), and git log -S dates that machinery to #349/#714/#730/#842, older than the plan it was inferred from. *** ADMITTING ON PREP-READINESS: CIS-053, CIS-056, CIS-057 - and each carries a discharged verify-first clause rather than an unchecked one. *** TWO EXPECTED-SURFACE CORRECTIONS APPLIED AND VERIFIED BY MEMBERSHIP, NOT BY COUNT: CIS-053 declared test/pm-plugin-development/test_resolve_dependencies.py, which does not exist - the real path carries a tools-marketplace-inventory/ segment (2 occurrences fixed); CIS-050 still named _chat_provenance.py and _chat_gate_decisions.py under plan-retrospective/scripts after #1376 moved BOTH to platform-runtime/scripts (claimed_count 35 to 36). ⛔ A declared path that resolves to nothing can never collide, so the disjointness gate was comparing phantoms for both specs. *** EMIT: UNCHANGED - PLAN-CIS-053 at N=1, R=0, auto_emit=false, NOT transitioned to launched. It is the first candidate in queue order passing BOTH halves. Derived gate state per staged spec (prep-ready / live-plan-disjoint): 052 no/no, 049 no/no, 050 no/no, 053 YES/YES, 054 no/YES, 056 YES/no, 057 YES/YES, 058 no/YES, 061 no/no. CIS-057 also passes both and is the next slot's candidate. *** LIVE-PLAN COLLISIONS ARE REAL AND CURRENT: PR #1399 (planning-lane-change-type-scope-execution-manifest, 6-finalize) and PR #1398 (preference-admissibility-prose-vs-auditor-code, 5-execute) are both OPEN. *** PARKED PAIR - both parks STILL JUSTIFIED, and both carry a refutation: CIS-039's cited byte counts are stale (SKILL.md 15874 not 14835; standards/ 6 files / 114977 not 5 / 101897 - argument-naming.md was added), and CIS-036's TITLE PREMISE is refuted - recomputed at HEAD, 2-refine doc-residency is 90.7 percent and 3-outline 73.0 percent, both above 6-finalize's 64.5 percent, so 6-finalize is NOT the worst case. *** ⛔ THREE SPECS CITE THE SAME STALE POPULATION: the archived-plan corpus cited as 13 is 35 of 36 at HEAD (CIS-039, CIS-056, CIS-057). Do not carry 13 forward. *** DUPLICATION CANDIDATE FOR THE NEXT A4 PASS: CIS-052 row 20 and CIS-057 claim 1 assert the SAME fact (reconcile-ledgers has zero workflow call sites). *** RESTART-CHECK: not_ready, and the ONLY not_ready signal is 1 uncommitted path - `uv.lock`, which was already dirty at session start and is NOT this pass's doing. Every other scored signal is ready; registry_parity is not_available and excluded from the floor. *** ⛔ PIN GAP STILL OPEN: registry installPath 0.1.1592 vs executor 0.1.1602, so executor==installPath FAILS. This orchestrator session seats skill bodies from target/claude/ directly and is unaffected; RE-CHECK THE GATE in whatever session runs the emitted command. === 2026-09-05 ANCHOR (9) - EMIT ROUND: PLAN-CIS-053 EMITTED, AWAITING OPERATOR-CONFIRMED LAUNCH. === *** SUPERSEDES the emit/queue state of every block below; all other statements stand verbatim. *** N=1, R=0 (no launched row), 1 slot, auto_emit=false, so NOTHING was transitioned to launched - the emit is stage-and-wait and the launched transition is owed only when the operator confirms. EMITTED: PLAN-CIS-053-test-suite-anti-vacuity.md. *** THE ZERO SHORTFALL IS NOT A CLEAN BILL: the slot filled at the 4th candidate in queue order. Five staged candidates are blocked by LIVE-PLAN surface collisions, not by their own readiness - CIS-052 overlaps live plan planning-lane-change-type-scope-execution-manifest on manage-status/SKILL.md and phase-6-finalize/SKILL.md; CIS-049 overlaps the same plan on manage-execution-manifest.py; CIS-050 overlaps it on 4 paths AND preference-admissibility-prose-vs-auditor-code on audit.py; CIS-056 overlaps preference-admissibility on audit.py; CIS-061 overlaps planning-lane on manage-status/SKILL.md and phase-5-execute/SKILL.md. All five unblock when those two live plans land - re-run next then, do not re-triage them as unready. *** THE ANCHOR (8) STATEMENT 'PLAN-CIS-052 RE-EMITTED' IS SUPERSEDED: 052 is NOT emittable at this HEAD. *** CLEAN OF LIVE-PLAN OVERLAP THIS ROUND: CIS-053, CIS-054, CIS-057, CIS-058. *** GATE POPULATIONS (both halves derived, neither asserted): corpus surfaces 65/65 scanned, 54 declarative/admitting, 11 indeterminate (8 prose + 3 absent), 0 unreadable - all 9 staged candidates are declarative and admit the disjointness check, so no candidate's clean reading was silence. corpus verdicts 65/65 scanned, 296 claims, 34 verdict rows, blocking_count 1 - and that ONE blocking row is PLAN-CIS-055 (contradicted, not rescoped), which is RETIRED and not a candidate, so every staged candidate is prep-ready. claim_section_states: 49 parsed / 9 absent / 7 unreadable / 0 empty. corpus cross-check: 561 file overlap rows across 9 sibling epics and 5 live plans, of which only 9 name a live_plan. *** PIN GAP OBSERVED AT THIS EMIT: registry installPath 0.1.1592 vs executor 0.1.1602 - the gate executor==installPath FAILS. This orchestrator session seats its skill bodies from target/claude/ directly so its own loading is unaffected, but a plan launched from a differently-seated session is exposed; re-check the gate at launch. === 2026-08-31 ANCHOR (8) - INBOX DRAINED 19 OF 19, ZERO LEFT. PLAN-CIS-061 STAGED. PLAN-CIS-052 RE-EMITTED. === *** SUPERSEDES the inbox state and queue counts of every block below; all other statements stand verbatim. *** DRAIN RESULT: 19 enumerated, 19 archived, 0 invalid, 0 archive-failed. Dispositions: 13 folded, 1 staged, 1 promoted, 1 reconciled, 1 observed, 1 stream_end_noted, 1 (=-007) deduped into another fold. Folds by target: CIS-050 nine signals (F-004 re-entry accounting, F-005 unread discriminator, F-006 label-not-size probe, F-008 ledger union, F-009 dark context channel, F-010 build oracle, F-012 A+B, F-013 admissibility, F-LH-001, F-LH-002), CIS-052 three, CIS-054 three, CIS-049 two, CIS-053 one. *** ⛔ WHICH ZERO THIS IS: inbox list now reads live_count 0, closed_senders EMPTY, invalid_count 0 = the EMPTY state, not FINISHED. The lessons-handling-26-08-26-01 stream-end marker WAS filed and WAS noted, but closed_senders scans inbox/ only, so archiving the marker removed the closure from the payload. Do NOT read this zero as 'every sender has declared closure' - a later message from any sender is still possible. *** ⛔⛔ D20 IS THE SHARPEST THING THIS DRAIN PRODUCED AND IT WAS SELF-CAUGHT: A `###` SUB-HEADING INSIDE `## Expected Surface` SILENTLY TRUNCATES THE SECTION FOR epic_spec_parser. The first fold pass put all 17 added surface entries under such a sub-heading and EVERY ONE parsed as absent - CIS-052 stayed at 24 resolved, CIS-050 at 29. Demoting five sub-headings to bold text, the only change, took CIS-052 to 32, CIS-050 to 35, CIS-053 to 27, CIS-054 to 16 and resolved every added path. ⭐⭐ The same-act obligation was HONOURED and would still have left the gate reading the old surface: a declaration the parser cannot read is not a declaration. ⭐ ONLY corpus surfaces caught it - the narrative and the file both said the surface was updated. NEVER conclude a fold discharged its obligation without running corpus surfaces. Owner not yet decided: epic_spec_parser lives in script-shared, and CIS-049 owns query truthfulness but not this reader. *** STAGED: PLAN-CIS-061-voluntary-checkpoint-is-a-stall (WS-04), queue row added, 9 surface entries all resolving, 0 unresolved. From candidate-lesson -011: voluntary_checkpoint was 10 of 14 phase-5 terminations while SIX OF NINE operator turns existed only to restart a halted run - corroborated from two independent sources (boundary ledger + session transcript). ⛔ Must not run concurrently with CIS-050 (four shared files). Queue is now 52 shipped / 9 staged / 2 parked / 2 retired, 65 rows. *** PROMOTED: lesson 2026-08-31-09-001 (plan-marshall:plan-retrospective, improvement, 2615-byte body) - a producerless SECTION_SPEC row is an operator proposal, not an in-plan decision. *** ABSORBED AS WATCH W-048 (truthful-signals-052): PLAN-TRUTH-098 / #1359 measured 9.2M dispatched against 185.4M billing, phase 6 alone 52% of billing, resident context per tool-call 209K -> 771K. A measurement OFFERED, not a transfer. ⛔ Its per-phase caveat is now STRONGER than the sender knew: that run had 3 loop-backs, and D19 shows the producer-side corruption, so the phase label and the population it covers actively disagree. *** EMIT: PLAN-CIS-052 RE-EMITTED (queue head, prep-ready, auto_emit false so the row stays staged). It gained 8 surface entries in this drain, so re-derive its claims at HEAD before implementing. *** STILL OWED, unchanged by this drain: the D17 delegating message to review-apparatus is UNFILED (an offer is not a transfer), and the truthful-signals denominator correction (161 heading-carrying specs, not 124) is UNSENT. *** THIS ANCHOR IS A DOCUMENT, NOT A HEADLINE - never overwrite it with a summary; PREPEND. Its settled blocks are overdue for relocation into settled.md at the next cleanup. === 2026-08-31 ANCHOR (7) - PLAN-CIS-052 EMITTED INTO THE OPEN SLOT, AWAITING LAUNCH. === *** SUPERSEDES the emit state of ANCHOR (6) below; everything else in (6) and earlier stands verbatim. *** N=1, R=0 - CIS-051 shipped, no CIS plan launched or running. PLAN-CIS-052 finalize-dispatch-and-blocking-boundary-observability EMITTED 2026-08-31, row still staged because auto_emit is false. It is queue head and carries D1 (the Bucket-B plan-id injection whitelist, 4 of 8 entries inert - a LIVE production bug and the single most urgent item in the corpus) and D2 (the merge-with-pending-findings hole CIS-044 did not close). *** ⭐⭐ A 5-FILE COLLISION WAS CHECKED AND DISSOLVED - RECORD THE REASONING, IT GENERALISES. CIS-052 overlaps the live plan git-artifact-scanning-and-destructive-recovery on FIVE files (phase-6-finalize/SKILL.md, finalize-step-simplify.md, adr-propose.md, lessons-capture.md, workflow-integration-git/git-workflow.py). That plan shows in manage-status list as in_progress at 6-finalize, which LOOKS slot-occupying. It is not: its PR #1371 is ALREADY MERGED (8bc4a68f6, an ancestor of current HEAD 7845a4b9a), so it is running POST-MERGE finalize steps and its writes are DONE. ⭐ A plan at 6-finalize whose PR has merged is not surface-occupying - check the PR state, never the phase alone. Overlap with the other staged specs was measured at the same time: CIS-049 and CIS-050 one file each, CIS-053/054/056/057/058 zero. *** ⛔ STALENESS REPORTED, NOT PROMOTED: CIS-052 declares five files that #1370 and #1371 have just rewritten. Its section verdict is unverifiable (which ADMITS), so it emits - but re-derive its claims against HEAD before implementing, exactly as CIS-051's D2(a) needed. *** PREP-READY AT HEAD 7845a4b9a: specs_scanned 64, claims_scanned 290, count 34, blocking_count 1, and that one row is CIS-055 (retired). All EIGHT staged specs admit. === 2026-08-31 ANCHOR (6) - PLAN-CIS-051 SHIPPED (#1370). LANDING RECONCILED FROM AN OPERATOR PASTE. INBOX NOW HOLDS 18 LIVE MESSAGES AND A DRAIN IS OWED. === *** SUPERSEDES the emit state and queue counts of every block below; all other statements below stand and are preserved verbatim. *** LANDED: PLAN-CIS-051 detector-and-auditor-integrity SHIPPED as PR #1370, merge_commit 7845a4b9a, merged 2026-08-31T07:47:15Z. Row transitioned to shipped and all three result fields stamped. Landing report at landings/PLAN-CIS-051.md. 9 deliverables reported against a spec declaring D0-D7 (eight) - the ninth, the 42/42 mutation proof, is ADDED-UNPLANNED. Queue tally is now 52 shipped / 8 staged / 2 parked / 2 retired. *** ⛔ THIS WAS A PASTE-MODE ANALYZE, NOT A DRAIN. Mode=paste classifies once over the one item, so Step 4 ran and the inbox drain loop did NOT. inbox list reports count 19 / live_count 18 / invalid_count 0, closed_senders [lessons-handling-26-08-26-01]. The 14 messages PLAN-CIS-051 filed (001-014) are queued alongside the 4 pre-existing ones. ⭐ RUN /plan-orchestrator analyze slug=code-intelligence-substrate WITH NO PASTE to drain them. Message -014 is the kind=landing message and landing-check reports complete: true with missing_keys empty, so re-draining it is a dedup fold onto this landing, not a second reconciliation. *** ⛔⛔ D17 IS THE SHARPEST THING THIS LANDING PRODUCED AND IT IS NOT OURS TO FIX: THE REQUIRED-BOT QUORUM CLEARS ON A REVIEWER THAT DID NOT PARTICIPATE. marshal.json sets required_bots=pr-agent; on PR #1370 pr-agent left NO observable trace - ci pr reviews returns 47 reviews across exactly three users (coderabbitai 24, cuioss-oliver 22, sourcery-ai 1) and ci pr comments returns 81 comments with ZERO pr-agent occurrences - yet automatic-review reported the quorum satisfied in three rounds. The landing narrated it as a bot that answered weakly; the record says it did not participate at all. ⛔ NOT the known in-place-edit behaviour: an in-place edit leaves the comment PRESENT, and there is no comment. ROUTED OUT to review-apparatus under the three-way rule. ⚠⚠ THE DELEGATING MESSAGE HAS NOT BEEN FILED - AN OFFER IS NOT A TRANSFER. File it, or the routing is fiction. *** ⛔ D19: TWO REPORT FIGURES ARE NOT WHAT THEY LOOK LIKE, both corroborated first-hand. (a) the 6-finalize cell absorbs both loop-back execute passes - work/metrics.toon has close_count 1 and value_scope single_close for 5-execute and an EMPTY re_entered_phases, while status metadata records loop_back_iteration 2 and a 6-finalize->5-execute re-entry. ⭐⭐ This is the retired-per-phase-figure archetype in a SHARPER form: PLAN-TRUTH-055 made re-entered phases REPRESENTABLE, and here the representation exists and THE PRODUCER NEVER WRITES IT. Representable-but-never-written is a DIFFERENT defect from unrepresentable - do not collapse them. (b) 4.46M tokens are named by no record-step row, so the execution-log total covers ~37% of the spend it summarises. Both owed a fold into PLAN-CIS-050. *** ⛔ D18: PLAN-CIS-051's realized surface exceeded its declared one at FOUR paths (script-shared/argparse_surface.py, manage-execution-manifest/_manifest_core.py and _decision_line_shapes.py, plan-retrospective/references/logging-gap-analysis.md). The merge commit changes 63 files while the landing's own files_modified fact says 54. The spec is shipped, so no live declaration remains to correct. *** ⭐ CORROBORATION OUTCOMES WORTH KEEPING: the Executive-Summary-unwritable claim is CONFIRMED IN SUBSTANCE (no production writer exists; retro_sections.py:205 makes underscore keys unregisterable) but its published ratio 15-of-18 DOES NOT REPRODUCE - the corpus-wide population at HEAD is 24, of which 16 are under test/. A count published without its population, inside a plan whose subject is counts published without their population. Sourcery posted exactly ONE review, not one per round. *** THE MERGE-MUTEX OVERRIDE COST WHAT IT WAS MEANT TO PREVENT: first enqueue EJECTED when four upstream PRs landed during the queue wait (sync-baseline action=rebased, upstream_commit_count=4), forcing rebase, re-derived constant, full re-verify, force-push and re-review. No step records this; it is operator narrative preserved in the landing. *** RE-GROUNDING BY EXECUTION IS STILL OWED on 049/050/052/053/054 - CIS-051 has now shipped, so the six specs that debt covered are five. unverifiable ADMITS, it does not mean CHECKED. *** THE CROSS-EPIC OBLIGATION TO truthful-signals (numerator 19 confirmed, denominator REFUTED - 161 heading-carrying specs, not 124) IS STILL UNSENT. *** THIS ANCHOR IS A DOCUMENT, NOT A HEADLINE - never overwrite it with a summary; PREPEND. It is well past 30K characters and its settled blocks are overdue for relocation into settled.md at the next cleanup. === 2026-08-29 ANCHOR (5) - NEXT RE-RUN. SLOT OPEN, PLAN-CIS-051 RE-EMITTED AND STILL AWAITING LAUNCH. PIN INVERSION DOES NOT REPRODUCE. CIS-051 SURFACE HAS MOVED UNDER IT. === *** SUPERSEDES the emit state, the slot arithmetic and the pin-inversion warning of every block below; all other statements below stand and are preserved verbatim. *** SLOT ARITHMETIC AT 2026-08-29: N=1, R=0. No CIS plan is launched OR running, so the safe reading (R = launched + running) and the doc reading agree here and the single slot is open. The two live plans in the whole checkout are PLAN-TRUTH-113 disjointness-gate-reads-declared-surface-wrong and PLAN-TRUTH-109 findings-read-absent-plan-dir-returns-clean-zero - BOTH truthful-signals, BOTH at 3-outline, NEITHER ours. *** EMIT STATE: PLAN-CIS-051 detector-and-auditor-integrity was RE-EMITTED 2026-08-29 into that slot and is AWAITING OPERATOR-CONFIRMED LAUNCH; its row is still staged because auto_emit is false. Nothing was launched between the 2026-08-26 emit and this one - this is the SAME candidate, re-emitted, not a second plan. *** PREP-READY: corpus verdicts at HEAD 5f972ac15 reports specs_scanned 64, claims_scanned 290, count 34, blocking_count 1 - and that one blocking row is PLAN-CIS-055, which is RETIRED and out of the live queue. ALL NINE staged specs therefore admit. claim_section_states: absent 9 / empty 0 / unreadable 7 / parsed 48. *** THE 2026-08-26 CONCURRENCY CONCERN ON CIS-051 IS DISCHARGED - AND REPLACED BY A STALENESS FACT. The sibling plan plan-footprint-is-unknowable-to-its-own-graders is PLAN-TRUTH-098 and it SHIPPED as PR #1359 (841f90939). It is no longer a concurrent collision; it is a LANDED change sitting on CIS-051's declared surface. ⛔ #1359 touched FIVE of CIS-051's declared files, ONE MORE than the 4 the 2026-08-26 cross-check counted: plan-retrospective/SKILL.md, plan-retrospective/references/report-structure.md, plan-retrospective/scripts/analyze-logs.py, plan-retrospective/scripts/compile-report.py, and plan-retrospective/scripts/retro_sections.py. ⛔⛔ D2(a) is a divergence-paragraph DELETION in report-structure.md, and #1359 REWROTE that file (+53 lines) - re-derive D2(a) against HEAD before implementing it; it may be already done, or aimed at text that has moved. D1(d) and D3 likewise read compile-report.py and analyze-logs.py at their NEW state. #1359 also ADDED check-outline-vs-shipped.py and reworked _footprint_resolver.py inside plan-retrospective - files CIS-051's Expected Surface does not name. Per the standard, staleness is REPORTED, NEVER PROMOTED: this did not block the emit and must not be retro-fitted into a block. *** ⛔ COVERAGE CAVEAT - THE CROSS-CHECK'S LIVE-PLAN ARM RETURNED A VACUOUS ZERO. corpus cross-check reports plans_scanned: 3, yet every one of its 292 overlap rows is corpus_spec or sibling_epic_spec and not one is a live plan. Cause verified, not guessed: a plan at 3-outline has NO affected_files in references.json (manage-references get returned field_not_found for BOTH live plans). A live-plan zero out of cross-check means NO SURFACE RECORDED, not DISJOINT. The sibling judgement above was therefore made BY HAND from the two plans' subjects (plan-orchestrator disjointness gate; manage-findings absent-dir read) against CIS-051's surface (plan-retrospective, audit-archived-plan-retrospectives, tools-marketplace-inventory, plugin-doctor, ext-self-review-plan-marshall, manage-solution-outline) - no intersection. *** ⭐⭐ THE PLUGIN REGISTRY PIN INVERSION DOES NOT REPRODUCE ON 2026-08-29. Seated skill bodies in this session are served from /Users/oliver/git/plan-marshall/target/claude/ - the REPO BUILD OUTPUT, not a cache version directory at all - while the executor resolves scripts from ~/.claude/plugins/cache/plan-marshall, whose plan-marshall bundle now carries versions up to 0.1.1562. BEHAVIOURAL PROOF the script layer is current, which beats any version comparison: corpus verdicts returned the POST-1355 payload (scope, synthesised, claim_section_states, unreadable_claim_sections) and the seated SKILL.md documents corpus set-verdict --section-scope. ANCHOR (4)'s '0.1.1556 against a served 1544, TWELVE versions behind' is NOT the state observed today. ⛔ DO NOT RE-RUN THE OPERATOR-ONLY PIN REPAIR ON THE STRENGTH OF THAT SENTENCE without re-observing the gate first. *** RE-GROUNDING BY EXECUTION IS STILL OWED on 049/050/051/052/053/054 - unverifiable ADMITS, it does not mean CHECKED. That debt is unchanged by this run. *** THE CROSS-EPIC OBLIGATION TO truthful-signals (numerator 19 confirmed, denominator REFUTED - 161 heading-carrying specs, not 124) IS STILL UNSENT. *** THIS ANCHOR IS A DOCUMENT, NOT A HEADLINE - never overwrite it with a summary; PREPEND. It is well past 30K characters and its settled blocks are overdue for relocation into settled.md at the next cleanup. === 2026-08-26 ANCHOR (4) - RESTART PREP. doc/plans REFERENCES REMOVED FROM THE LEDGER; CIS-055 RETIRED; CLEANUP DONE; PLAN-CIS-051 EMITTED AND AWAITING LAUNCH. === *** SUPERSEDES the queue counts and blocking arithmetic of every block below; all other statements below stand and are preserved verbatim. *** ⛔⛔ START HERE ON RESTART. THE CLOUD PLAN LANE IS RETIRED (operator, 2026-08-26) and its function is incorporated into the orchestrators. doc/plans/ DOES NOT EXIST. *** ⛔ THE REMOVAL WAS SCOPED TO THIS LEDGER ONLY - THE REPOSITORY SOURCE WAS DELIBERATELY NOT TOUCHED, operator-confirmed: the cloud-plan-lane and author-cloud-plan skills STILL NEED their doc/plans references. A repository sweep was measured but NOT acted on - 74 references across 25 tracked files including two whole skills and a 17-reference test module - because that is a multi-file source mutation, i.e. plan work the prime directive forbids the orchestrator. DO NOT LATER MISTAKE THAT MEASUREMENT FOR OWED WORK. *** LEDGER REMOVAL DONE: 47 export-tree evidence paths mechanically re-pointed to the cloud-runs archive; the provenance header rewritten in all 6 live wave specs; 10 residual body-prose sites neutralized (conditional hedges about the tree becoming the settled fact). ⭐ THE FOUR LIVE TRANSLATION ROWS WERE PRESERVED ON PURPOSE - run report, merge gate, ./pw, sub-agent - because the spec BODIES STILL USE THOSE TERMS and deleting the table would strand them. Each of the 6 live specs now carries EXACTLY ONE doc/plans mention: the statement that the tree no longer exists. That mention is CORRECT AND MUST SURVIVE - it names the retired thing in order to say it is retired. ⛔ A future pass that strips it to reach zero will have destroyed the record. *** ⛔ SELF-CAUGHT DEFECT WORTH REMEMBERING: the mechanical re-point pass over-applied and rewrote doc/plans paths INSIDE the provenance header too, making the EVIDENCE row map a path to ITSELF and making a historical sentence claim the ingest deleted cloud-runs rather than the export tree. The residual REPORT is what exposed it. A mechanical sweep must always publish what it did NOT handle. *** PLAN-CIS-055 RETIRED (was staged). Its proposals targeted a lane contract that no longer exists; its section verdict came back contradicted at 91a07aaa4. Spec file KEPT per never-delete-a-spec. This REVERSES D12's RE-SCOPED not retired disposition, and D12 now carries a dated correction saying so rather than being rewritten. *** CLEANUP RESULTS: corpus enumerate reconciles 64/64 BOTH DIRECTIONS, 0 unreadable. Tally 51 shipped / 9 staged / 2 parked / 2 retired. compact regenerated both blocks, invariants 3/3 ok, 12 sections preserved verbatim, unreachable_count 0. blocking_count 1 and that one is CIS-055, now RETIRED, so it is out of the live queue and gates nothing. *** ⛔⛔ THE CLEANUP'S SHARPEST FINDING - READ BEFORE EMITTING CIS-050: the LIVE sibling plan plan-footprint-is-unknowable-to-its-own-graders overlaps FIVE staged specs (CIS-050 on 5 files, CIS-051 on 4, CIS-052/056/057 on 1 each) AND ITS NAME MATCHES THE SUBJECT of the two items the 2026-08-26 drain just folded into CIS-050 - D3.i (merge-commit tier structurally dead under squash landings) and D3.ii (nothing persists the realized footprint before branch-cleanup destroys the worktree). POSSIBLE DUPLICATE WORK. A ledger structurally CANNOT see a duplicate held in another ledger, so CHECK THAT PLAN'S LIVE STATE AND ITS ACTUAL DELIVERABLES against CIS-050 D3.i/D3.ii before emitting CIS-050. Surface overlap alone is not duplicate work (D14 ruled that way) - but surface overlap PLUS a matching subject is the shape a real duplicate takes. Second live plan a-failing-ci-call-reports-success overlaps CIS-052 (2), CIS-050 (1), CIS-053 (1) with no apparent subject collision - ordinary sequencing. *** EMIT STATE: PLAN-CIS-051 detector-and-auditor-integrity was EMITTED 2026-08-26 and is AWAITING OPERATOR-CONFIRMED LAUNCH - its row is still staged because auto_emit is false. ⛔ ITS EMIT PREDATES THE CROSS-CHECK ABOVE and it carries the SECOND-LARGEST overlap with plan-footprint-is-unknowable-to-its-own-graders (4 files). Re-check before it starts. If it has not started, N=1 R=0 and the slot is open. *** ⛔ RE-GROUNDING BY EXECUTION IS STILL OWED on six specs. The 2026-08-26 repair stamped 049/050/051/052/053/054 unverifiable, NOT corroborated, precisely because this pass did not re-execute their confirm/refute artifacts across roughly forty claims. unverifiable ADMITS, so they emit - but the debt is real and ON THE RECORD. Do not read admits as checked. *** ⛔⛔ PLUGIN REGISTRY PIN IS INVERTED: executor resolves 0.1.1556 against a served skill base dir of 0.1.1544 - TWELVE versions behind. REPAIR IS OPERATOR-ONLY and is the FIRST THING TO DO ON RESTART. Live consequence already hit this session: corpus set-verdict --section-scope did not exist in the seated 1544 body and had to be read from live --help. UNTIL REPAIRED, READ NEW SCRIPT SURFACES FROM --help, NEVER FROM THE SEATED SKILL BODY. *** D16 STILL UNROUTED: next's R counts only launched, so a RUNNING plan is invisible to the slot arithmetic and the verb would emit onto an occupied slot. The safe reading (R = launched plus running) is applied throughout this ledger and must NOT be corrected away on the strength of the doc wording. *** ⛔ CROSS-EPIC OBLIGATION STILL OWED TO truthful-signals: their numerator of 19 is CONFIRMED and twice-observed, their DENOMINATOR is REFUTED - 161 heading-carrying specs, not 124. TELL THEM. *** THIS ANCHOR IS NOW OVER 30K CHARACTERS. It is a DOCUMENT, not a headline - never overwrite it with a summary; prepend. But it is a candidate for relocating its settled blocks into settled.md at the next cleanup. *** === 2026-08-26 ANCHOR (3) - PLAN-CIS-060 SHIPPED (#1355); D13 RESOLVED; INBOX DRAINED 9 OF 9; 7 BLOCKED SPECS REPAIRED TO 1; PLAN-CIS-051 EMITTED. === *** SUPERSEDES the emit state, queue counts and blocking arithmetic of every block below; all other statements below stand and are preserved verbatim. *** PLAN-CIS-060 SHIPPED as PR #1355, merge commit 91a07aaa4 (= origin/main HEAD), row fully stamped. Corroborated first-party via ci pr view: state merged. ⭐ ITS LANDING MESSAGE IS THE EPIC'S FIRST complete:true - landing-check reports missing_keys[0]; every prior landing was a prose paste, so the drain could not previously establish that the required facts had drained. ⚠ Its steps fact records archive-plan:pending because emit-landing runs BEFORE archive-plan - a truthful snapshot of a step order, not a stale claim. Parsed with a LAST-colon split per the payload spec. *** ⛔⛔ D13 IS RESOLVED, and the proof is in this ledger: corpus verdicts went blocking_count 0 to 7 the moment #1355 landed. Both arms discharged - the READ side makes an unreadable claim section a distinguishable parse state contributing a BLOCKING row instead of a vacuous pass, and the WRITE side gives it an address via corpus set-verdict --section-scope, repairing a blocked spec in ONE call without re-authoring its claim prose. *** THE 7 BLOCKED SPECS WERE THE FIRST SEVEN ROWS IN STAGED ORDER (051, 052, 049, 050, 053, 055, 054) - the fix working, NOT a regression: work whose premises were never checked became visibly unemittable instead of invisibly admitted. Operator directed a repair pass rather than emitting past them. *** REPAIR DONE 2026-08-26: blocking_count 7 to 1. SIX stamped unverifiable (049, 050, 051, 052, 053, 054) - each section was READ IN FULL at 91a07aaa4 and found SUBSTANTIVELY INTACT, carrying a labelled claim table with OBSERVED/HYPOTHESIS discipline and a named git-reachable artifact per row; the block was a PARSER-READABILITY artifact (claims as a TABLE or a PROSE paragraph, not top-level bullets) and NOT a refutation. ⛔ unverifiable and NOT corroborated is deliberate and must not be upgraded without doing the work: this pass did NOT re-execute the confirm/refute artifacts across roughly forty claims, and stamping corroborated without executing them is precisely the vacuous-authority archetype this epic tracks. RE-GROUNDING BY EXECUTION REMAINS OWED - it belongs to a cleanup pass. unverifiable ADMITS by contract because an unreached population is not a refutation, so the six are unblocked with the debt ON THE RECORD rather than hidden. *** ⛔⛔ ONE SPEC CAME BACK CONTRADICTED AND STAYS BLOCKED: PLAN-CIS-055. doc/plans/ DOES NOT EXIST at 91a07aaa4 - ls returns No such file or directory - so three of its four declared Expected Surface entries (doc/plans/README.md, cloud-bridge.md, cloud-lane-contract-proposals.md) are GONE, refuting its two HYPOTHESIS claims and every OBSERVED claim whose artifact is cloud-bridge.md. ONE ARM SURVIVES, re-run exactly as the spec demands: grep -c prerequisite over .claude/skills/cloud-plan-lane/SKILL.md returns 0 and that file exists. rescoped=no, so it correctly BLOCKS. ⇒ CIS-055 MUST BE RE-SCOPED against the surviving lane skill alone, or RETIRED, before it is emittable. This is the repair pass earning its keep - it caught a spec whose world moved. *** INBOX DRAINED 9 OF 9 (8 candidate-lesson + 1 landing), ALL FOLDED, ZERO STAGED. Post-drain: count 0, live_count 0, closed_senders EMPTY, invalid_count 0 - the EMPTY zero. Dispositions: 001 to CIS-052 N2, 002 to CIS-051 N1, 003 to CIS-052 N6, 004 to CIS-052 N3, 005 to CIS-050 D4.i, 006 to CIS-050 D5.ii, 007 to CIS-052 N4, 008 to CIS-052 N5, 009 reconciled as the landing. All folded as SUB-ITEMS of existing deliverables - no spec gained a deliverable, no scope-bloat rationale changed. *** ⛔ THE SHARPEST FINDING is 002 composed with 001: check-dispatch-audit graded the finalize dispatch channel ratio 1.0 confidence nominal over a 892890-token hole (36 percent of the phase) in that SAME channel, because it divides an ALL-PHASE dispatch count by FINALIZE-ONLY completions; the finalize-scoped ratio is 12/22 = 0.545, barely above the 0.5 sparse floor. A VACUOUS GREEN IN THE INSTRUMENT THAT MEASURES THE INSTRUMENTS - this epic's subject one level up. Root shape of 001: all THREE nominally-independent channels hang off STEP ENTRY, so they share one blind spot. *** ⛔ CROSS-EPIC OBLIGATION OWED TO truthful-signals: their numerator of 19 is CONFIRMED and twice-observed, but their DENOMINATOR is REFUTED - 161 heading-carrying specs, not the 124 their spec states. Ratio changes, finding survives. TELL THEM. Blast radius was population-derived, not sampled: 331 specs over 9 epics, partition absent 104 / empty 0 / unreadable 26 / parsed 201 summing EXACTLY to 331; our own expectation of 7 CONFIRMED; template-placeholder 0 and fenced-only-body 0 both derived from a content sweep over 5246 files. *** ⚠ DO NOT TRUST THIS RUN'S WORKED-TIME FIGURE without checking the clamp (CIS-050 D2.i) - it reports no loop-back so the 059 clamp defect may not apply, but the clamp is still unreported when it fires. Tokens 5132687 and wall 50448s are fine. *** QUEUE IS 64 ROWS: 51 shipped, 9 staged, 2 parked, 1 retired, 1 running. Staged order: 051, 052, 049, 050, 053, 055, 054, 056, 057, 058 (055 blocked). *** EMITTED PLAN-CIS-051 detector-and-auditor-integrity - N=1, R=0, one slot, queue-order first and now admitting. It owns the 002 fold, so it will fix the auditor that graded its own blind spot nominal. auto_emit false so launched was NOT recorded. *** ⛔⛔ PIN GATE WIDENED AGAIN: bootstrap_plugin resolve returns 0.1.1556 against a served skill base dir of 0.1.1544 - TWELVE versions behind, widened by this landing's sync-plugin-cache exactly as the per-landing leak predicts. Repair is OPERATOR-ONLY. Note the live consequence THIS session hit: corpus set-verdict --section-scope did not exist in the 1544 skill body and had to be read from live --help. READ NEW SURFACES FROM --help, NOT FROM THE SEATED SKILL BODY, until the pin is repaired. *** D16 STILL UNROUTED - next's R counts only launched, so a running plan is invisible to the slot arithmetic. *** TWO TOOLING DEFECTS LOCATED IN SOURCE by 060 and folded: worktree-remove's rc-124 timeout wearing the dirty-tree hint (CIS-052 N6) and round-scoped cohort_size (CIS-052 N4). ONE OPEN QUESTION deliberately not asserted as a defect: the merge mutex released as not held despite no explicit release, 51m10s inside a 3600s budget - artifacts do not evidence the mechanism. *** === 2026-08-26 ANCHOR (2) - PLAN-CIS-060 IS RUNNING; ZERO SLOTS FREE. === *** SUPERSEDES the emit state of the block below; every other statement below stands and is preserved verbatim. *** PLAN-CIS-060 verdict-field-read-and-write-integrity is RUNNING - operator-confirmed 2026-08-26, row transitioned staged to running (launched was never recorded, auto_emit being false; that is the emit-not-running invariant working as intended, not a missing stamp). R=1, N=1, ZERO SLOTS FREE. Nothing is emittable until 060 lands. Next staged after it: 051, 052, 049, 050, 053, 055, 054, 056, 057, 058. *** ⛔ THE PIN GATE IS STILL INVERTED AND WAS NOT REPAIRED BEFORE THIS LAUNCH: re-checked at launch time, bootstrap_plugin resolve returns 0.1.1550 while the orchestrator session's served skill base dir is 0.1.1544 - six versions behind. 060 is therefore running under a script layer newer than the skill bodies this orchestrator session reads. Repair is OPERATOR-ONLY. This is recorded as fact, not as a blocker: the scripts resolve numerically-newest regardless, and no step taken so far depended on a 1545-to-1550 change. *** ⛔ D16 IS NOW LIVE AGAIN, and this is exactly the state it bites in: with 060 at RUNNING and next's R counting ONLY the launched status, a literal reading of orchestrate.md Step 4 computes R=0 and would emit a SECOND plan on top of the running one. The safe reading is applied here - R counts launched plus running, so R=1 and zero slots. A future session must NOT correct that to R=0 on the strength of the doc wording. D16 remains UNROUTED; decide its owner before the next emit. *** WHAT TO EXPECT AT 060'S LANDING: re-ground CIS-051, CIS-049 and CIS-050 before emitting any of them - all three were given new surface in the 2026-08-26 drain (git-workflow.py is claimed by CIS-050, CIS-049 AND CIS-052; _status_query.py by CIS-049 and CIS-052; manage-execution-manifest.py by CIS-050, CIS-051 and CIS-049), and under scope=1 those are sequencing constraints that only matter at the moment one of them lands. *** === 2026-08-26 ANCHOR - PLAN-CIS-059 SHIPPED (#1348); INBOX DRAINED 8 OF 8, ALL FOLDED; PLAN-CIS-060 EMITTED. === *** SUPERSEDES the emit-state, queue counts and slot arithmetic of every block below; all other statements below stand and are preserved verbatim. *** PLAN-CIS-059 SHIPPED as PR #1348, merge commit 9aaf22d8f, row fully stamped (pr 1348, landing landings/PLAN-CIS-059.md, plan_marshall_plan_id fold-pm-code-intelligence-into-core). CORROBORATED FIRST-PARTY via ci pr view: state merged. ⛔ THE LANDING NARRATIVE'S main up-to-date 8025b2210 IS ABOUT MAIN, NOT ABOUT THIS PLAN'S MERGE - 8025b2210 is PR #1349; 059 merged one commit earlier as 9aaf22d8f. Both true; the landing record stamps the plan's OWN merge commit. *** DELIVERABLE CLAIMS RE-DERIVED, NOT ACCEPTED: bundles 10 (git ls-files over plugin.json), pm-code-intelligence has ZERO tracked files and a clean status so the retirement is real; the lsp resolver IS on core's Extension (LSP_DEP_TYPE lsp at extension.py:41, provenance id lsp at :262). ⭐ SKILL FILES ARE 156 against the landing's 154 REGISTERED - the gap of exactly 2 independently reproduces the run's own a1e704 finding (lsp-client and recipe-surgical-fix live but unregistered). Derivation and self-report AGREE, which is stronger than either alone. ⚠ marketplace/bundles/pm-code-intelligence/ still exists ON DISK holding only gitignored __pycache__ pyc files - inert local litter (PEP 3147 will not import it), NOT an incomplete retirement. *** ⛔ DO NOT ENTER THIS RUN'S WORKED TIME INTO ANY EPIC-LEVEL EFFICIENCY FIGURE. The 3h50m worked / 9h43m wall pair is the DEFECTIVE shape the run's own inbox 003 reports: one loop-back left 6-finalize half-stamped and CLAMPED agent_duration_ms to the wall span, rendering a confident fully-worked row. Token (4.7M) and billing-weighted (88.4M) figures are unaffected. 6-finalize alone was about 50 percent of tokens, consistent with the standing finalize-dominates observation but still a per-run observation, not a reproduction. *** INBOX DRAINED 8 OF 8 on 2026-08-26, all from sender fold-pm-code-intelligence-into-core, all candidate-lesson, all valid. ALL EIGHT FOLDED into existing specs or an existing structural finding - ZERO staged, so D15's hand-rewrite cost was NOT incurred. Post-drain: count 0, live_count 0, closed_senders EMPTY, invalid_count 0, inbox_state present - the EMPTY zero, NOT finished and NOT blocked. DISPOSITIONS: 001 to CIS-050 D3.ii (nothing persists the realized footprint before branch-cleanup destroys the worktree); 002 to CIS-050 D3.i (footprint resolver merge-commit tier STRUCTURALLY DEAD under squash landings); 003 to CIS-050 D2.i (finalize loop-back half-stamps and clamps); 004 to CIS-049 N2 (merge FIFO queue has NO read surface); 005 to CIS-049 N1 (manage-status read/list blind to a sibling-worktree plan); 006 to CIS-050 D5.i (8 of 9 tasks emitted no ARTIFACT line); 007 to CIS-052 N1 (error finding filed after the metrics close stays pending past merge); 008 to epic.md F11 as a RECURRENCE (three count claims, each wrong, in a run that WAS a counting exercise). *** THE TWO MOST CONSEQUENTIAL ARE 002 AND 005, FOR OPPOSITE REASONS. 002 is a POPULATION defect - a tier matching two-parent commits can NEVER fire in a squash-merging repository, so it is dead for EVERY plan this project lands, not merely unreliable; PR #1348 landed as a one-parent squash (parent a2be2691c) and the datum a working tier needs (create-pr facts.pr_number) is ALREADY persisted. 005 is this epic's own theme biting hardest: TWO INDEPENDENT READS BOTH RETURNED ABSENCE AND BOTH WERE STRUCTURALLY INCAPABLE OF RETURNING PRESENCE (ADR-002 moves a phase-5+ plan into its own worktree), and the inference DESTROYED LIVE STATE - a sibling plan's merge-queue slot. Two blind checks agreeing is not corroboration. In 005 the read defect is OBSERVED but the list mechanism is HYPOTHESIS with a named confirm/refute artifact - the reporting run did NOT establish it. *** THREE SPECS GAINED SURFACE in this drain, each declared IN THE SAME PASS as its fold: git-workflow.py is now declared by CIS-050, CIS-049 AND CIS-052; _status_query.py by CIS-049 and CIS-052; manage-execution-manifest.py by CIS-050, CIS-051 and CIS-049. Under scope=1 these are SEQUENCING constraints, not concurrency ones - RE-GROUND THE SURVIVORS after whichever lands first. *** QUEUE IS 64 ROWS: 50 shipped, 10 staged, 2 parked, 1 retired. Staged order: 060, 051, 052, 049, 050, 053, 055, 054, 056, 057, 058. *** EMITTED PLAN-CIS-060 verdict-field-read-and-write-integrity - N=1, R=0, one slot. Prep-ready is NON-VACUOUS (9 parsed claims; claims_scanned rose 281 to 290 when it was staged) and its verdict field is ABSENT, which ADMITS by contract. auto_emit is false so launched was NOT recorded. *** ⛔⛔ PLUGIN REGISTRY PIN IS INVERTED RIGHT NOW: bootstrap_plugin resolve returns 0.1.1550 while this session's served skill base dir is 0.1.1544 - executor != installPath, the pin left behind by SIX versions, widened by 059's cache sync. REPAIR IS OPERATOR-ONLY. Graded against the steps ahead rather than the version delta, this session proceeded because the drain, the queue writes and the emit all ride stable script surfaces. RE-CHECK BEFORE LAUNCHING CIS-060. *** D16 STANDS AND IS STILL UNROUTED: next's R counts only launched, so a RUNNING plan is invisible to the slot arithmetic. It did not bite this time because 059 reached shipped, but it will the moment a plan sits at running. Decide its owner. *** === 2026-08-25 ANCHOR (2) - PLAN-CIS-059 IS RUNNING; INBOX DRAINED 2 OF 2; PLAN-CIS-060 STAGED AND HEADS THE QUEUE; ZERO SLOTS FREE. === *** SUPERSEDES the emit-state and slot arithmetic of BOTH blocks below; every other statement below stands and is preserved verbatim. *** PLAN-CIS-059 IS RUNNING - operator-confirmed 2026-08-25, row transitioned staged to running. R=1, N=1, ZERO SLOTS FREE: nothing is emittable until 059 lands. This drain's proactive emit therefore emitted NOTHING, by design and not by shortfall. *** INBOX DRAINED 2 OF 2 on 2026-08-25, both from truthful-signals, both filed AFTER the 08-24 drain (so the 08-24 line THE INBOX IS EMPTY was true when written and became false). Post-drain state: count 0, live_count 0, closed_senders EMPTY, invalid_count 0, inbox_state present - the EMPTY zero, NOT finished and NOT blocked; a later message is still possible. Archive 204 to 205. *** DISPOSITIONS. 050 (candidate-lesson, DELEGATION): FOLDED into CIS-050 as D1 sub-item (n) - the two-ledger token reconciliation. It is a RECURRENCE of our OWN CIS-022 residue, not new work: landings/PLAN-CIS-022.md records reconcile-ledgers shipped with ZERO workflow call sites (G4) and the arithmetic left unverifiable for want of a corpus that is now on this machine, and that landing already routes follow-ups to CIS-050. CORROBORATED FIRST-PARTY: execution_log[] declares 5-execute,6-finalize at 2518734 while metrics-dispatch-boundaries reports 2497910 plus 2761584 = 5259494; the ratio is 2.088, matching the claimed 2.09. The steps-vs-firings explanation is HYPOTHESIS, explicitly NOT established by the source. Surface declared IN THE SAME PASS as the fold: manage-execution-manifest.py, check-routing-decisions.py, test/plan-marshall/manage-execution-manifest/ - which creates a NEW overlap with CIS-051 and CIS-049; under scope=1 that gates nothing concurrently but is a SEQUENCING constraint. NOT taken: per-dispatch attribution, which truthful-signals owns and withheld. 051 (finding, REPLY to our 026): STAGED as PLAN-CIS-060 verdict-field-read-and-write-integrity (WS-07) by OPERATOR DECISION, and folded as D13 UPDATE 2. *** WHY 060 IS A NEW SPEC AND NOT A FOLD INTO CIS-051: CIS-051 contained ZERO mention of orchestrator.py, CLAIM_LABELS, claims_total or set-verdict - the standing claim that D13 was Routed to CIS-051 was recorded in the DEFECT LIST but NEVER WRITTEN INTO THE SPEC, so a fold would have been first authorship; CIS-051 already carries 8 deliverables under a recorded bloat rationale; and the verdict machinery is plan-orchestrator, a different subsystem from CIS-051's plan-retrospective plus audit.py subject. Surfaced to the operator per D15 rather than performed silently. DO NOT RE-FOLD 060 INTO CIS-051. *** THE D13 VACUITY IS BIDIRECTIONAL - CORROBORATED FIRST-PARTY at HEAD 1169fb5bf, not carried from the paste: set-verdict --plan PLAN-CIS-051 --claim-index 9999 returns claim_index_out_of_range with claims_total 0, so on a zero-claim spec EVERY index is out of range and the verdict field is structurally UNWRITABLE. A refusal-only remedy would turn a silent vacuous pass into a PERMANENT DEADLOCK. Read directly in orchestrator.py: _parse_claims :1214 does if start < 0 return []; only a TOP-LEVEL dash bullet counts (if not indent, :1244) so a TABLE and a PROSE paragraph each yield zero; and CLAIM_LABELS_HEADING_RE :394 AND EXPECTED_SURFACE_HEADING_RE :395 BOTH carry re.IGNORECASE, CONFIRMING their correction that #1338 was one line wider than D13 quotes. NOT re-derived and recorded as a LEAD: their 19-of-124 figure and the PROSE-ONLY form, which our own seven (all table-form) could not have revealed. *** D13's cross-epic obligation OWED is DISCHARGED - they were told, re-probed, and confirm our framing. ADOPTED their standing rule for our seven: a prep-ready PASS on a zero-claim spec is treated as INDETERMINATE, never READY, and the emit that follows says so out loud. *** NEW DEFECT D16: next's in-flight count R reads ONLY the launched status, so a RUNNING plan is invisible to the slot arithmetic and the verb would emit into an occupied slot. At N=1 that is the difference between zero free slots and one. Applied the SAFE reading here (R counts launched plus running, so R=1); a future session must NOT correct that to R=0 on the strength of the doc wording. NOT yet routed to a spec - adjacent to CIS-060 but NOT in its scope. *** QUEUE IS NOW 64 ROWS: 49 shipped, 11 staged, 2 parked, 1 retired, 1 running. corpus enumerate reconciles 64/64 BOTH DIRECTIONS, 0 unreadable. Staged order: 060, 051, 052, 049, 050, 053, 055, 054, 056, 057, 058 - 060 deliberately HEADS the staged run because it is a PREREQUISITE for 049 through 055, whose prep-ready is vacuous until it lands. CIS-060's own claim section parses claims_total 9, so it is NOT an instance of the defect it fixes. *** NEXT ACTION: await PLAN-CIS-059, then analyze its landing and emit PLAN-CIS-060. *** === 2026-08-25 ANCHOR - N LOWERED TO 1 (OPERATOR); PLAN-CIS-059 EMITTED, AWAITING OPERATOR-CONFIRMED LAUNCH. === *** THIS BLOCK SUPERSEDES THE EMIT STATE AND THE N=2 SLOT ARITHMETIC IN THE 2026-08-24 ANCHOR BELOW; every other statement below stands unchanged and is preserved verbatim. *** parallelization_scope is now 1 (was 2), set on operator instruction: STRICTLY SEQUENTIAL, and parallel-run reviews are retired for this epic - a single full slot is steady state, never a shortfall to fix. R=0, N=1, ONE slot. The RECOMMENDED FIRST PAIR wording below is therefore superseded: CIS-059 alone is the emit, CIS-052 is NOT emitted alongside it and becomes the next candidate after 059 lands. *** THE 2026-08-09 OPERATOR HOLD IS LIFTED - the operator invoked next with an explicit emit instruction on 2026-08-25. *** EMITTED: /plan-marshall task=implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-059-fold-pm-code-intelligence-into-core.md . auto_emit is false, so the launched transition was NOT recorded and the queue row is still staged; record launched only on operator-confirmed launch. *** DISJOINTNESS CORROBORATED FIRST-PARTY, not carried from the prior anchor: corpus cross-check (epics_scanned 8, plans_scanned 2, candidates_scanned 269) returns for CIS-059 exactly five overlap rows, ALL against SHIPPED specs - 023/024/025 on doc/concepts/code-intelligence.adoc, 026 on that file plus marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md, 027 on that standard. ZERO staged-spec overlap and ZERO live_plan overlap. The live_plan arm is NON-VACUOUS (it returns 3 rows for other specs), so that zero is a real negative and not an unreachable population. *** PREP-READY IS NON-VACUOUS FOR CIS-059 - it is NOT one of the seven D13 zero-claim specs. corpus verdicts parses 8 real rows for it: claims 0-5 and 7 corroborated, claim 6 contradicted with rescoped=yes; blocking_count 0 corpus-wide across 281 claims scanned. *** ALL 8 CIS-059 VERDICTS ARE STALE: checked_at b95d78437 vs HEAD 1169fb5bf. Reported, NOT promoted - staleness never changes admission. Five commits landed since the re-grounding (1169fb5bf, dfabe3d8e, 91bbe7470, 77db1a0d3, 9999f4d87); none was inspected against the CIS-059 surface, so treat the verdicts as unre-run rather than as re-confirmed. *** NEW SEQUENCING FINDING from the same cross-check: the LIVE sibling plan build-gates-test-suite-confidence-ci-workflow-lint (phase 6-finalize, worktree) overlaps CIS-049 on marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py and CIS-053 on test/conftest.py. Neither is emitted now, but RE-GROUND 049 and 053 after that plan lands - the same treatment D14 already prescribes for 050 and 056. *** PLUGIN REGISTRY PIN GATE PASSES as of this emit: bootstrap_plugin resolve returns 0.1.1544 for plan-marshall, equal to the served skill base dir, so executor == installPath. Re-check before the NEXT launch - the gate re-opens by one version on every sync. *** === 2026-08-24 ANCHOR - post cleanup + re-grounding + full inbox drain. THE LEDGER IS CLEAN AND THE INBOX IS EMPTY. === *** READ epic.md TOP TO BOTTOM; it is the brief. This anchor is short by design - the narrative lives in properly-structured sections (Open Defects D12-D15, Watches W-047, Structural Findings F9-F12, 2026-08-22 Landed-Corpus Ingest) and 831 lines of settled narrative sit VERBATIM in settled.md. *** QUEUE UNCHANGED at 63 rows: 49 shipped, 11 staged, 2 parked, 1 retired. corpus enumerate reconciles 63/63 BOTH DIRECTIONS, 0 unreadable. Staged order: 059, 051, 052, 049, 050, 053, 055, 054, 056, 057, 058. R=0, N=2, two slots open. *** CORRECTION TO THE PRIOR ANCHOR: PR #1331 is MERGED, not open-and-enqueued. Verified from PR state via ci pr view. The prior anchor's claim was true when written and is now false. *** INBOX FULLY DRAINED 2026-08-24: 7 of 7 messages (truthful-signals 043-049) consumed and archived. live_count 0, closed_senders EMPTY, invalid_count 0 - this is the EMPTY zero, NOT finished and NOT blocked; a later message is still possible. Archive 196 to 203. Dispositions: 043 folded into CIS-050 as D7 (footprint base resolves against the LOCAL ref - CORROBORATED FIRST-PARTY, resolve_base_ref returns a bare branch name and _references_core.py has ZERO origin/ occurrences); 044 folded into CIS-052 D6d/D6e (cross-epic ordering vs PLAN-TRUTH-100 - NOTHING BLOCKS CIS-052, and D6d MUST be worded as the OBLIGATION not the CONSEQUENCE); 045 discarded on its own instruction (settled, truthful-signals owns both arms via PLAN-TRUTH-098); 046 folded into CIS-056 Objective; 047 absorbed as Watch W-047; 048 folded into D13; 049 folded into CIS-051 as D7. *** THE HEADLINE FIGURES ARE NO LONGER n=1. Inbox 046 supplied a SECOND independent measurement from a different plan on a different machine: doc-residency 65.2 percent AGREEING TO THE DECIMAL, index-answerable 20.5 vs 15.9 DISAGREEING. Three caveats ride it and are in CIS-056: 45.3 percent of that finalize cache_read is UNATTRIBUTED, the buckets are a share of exploration result bytes NOT of billing, and NOTHING was reproduced - it is a second data point, not a confirmation. n is now 2 and 2 is still small. *** RE-GROUNDING: 27 of 27 claims of the four locally-authored staged specs corroborated at HEAD b95d78437 and PERSISTED - 22 corroborated, 2 contradicted, 3 unverifiable, blocking_count 0. Both refutations were stamped rescoped=yes AND the re-scopes were APPLIED, which is why nothing blocks. CIS-059 claim 6 refuted: doc/concepts/code-intelligence.adoc needs NO correction, its surface entry is STRUCK. CIS-057 claim 4 refuted: CIS-050 has NOT landed, so its pre-authorised branch fired and D1/D2 report AROUND the defects. CIS-059's central risk SETTLES FAVOURABLY - activation keys on the resolver id and producers stamp ids, so the fold is behaviour-neutral while derivation_resolver_id returns lsp. *** MOST URGENT: epic.md D13. corpus set-verdict parses claims_total 0 for ALL SEVEN staged wave specs (049-055, probed 7/7) against 154 tabulated claims, so their re-grounding CANNOT BE PERSISTED - and worse, next admits a candidate iff no row carries admits:false, so ZERO ROWS PASSES PREP-READY VACUOUSLY. All seven currently read as prepared while nothing about them is checked. GRAMMAR NOW PINNED first-party: TWO sequential gates - orchestrator.py:389 CLAIM_LABELS_HEADING_RE is case-exact with _parse_claims returning [] on a miss, AND _parse_claims:1209 requires a TOP-LEVEL dash bullet, so a TABLE parses to zero even when the heading matches. The seven fail BOTH, which is why normalizing the heading changed nothing. Routed to CIS-051 alongside D10/D11. Independently found the same day by truthful-signals on its own corpus. *** D12 CLOSED: the 5xx wave specs were only partially transformed out of the cloud lane and are now NORMALIZED - a normative lane-translation table heads all 7, every write-side doc/plans Expected Surface entry is gone, cloud-runs is declared READ-ONLY, CIS-055 was RE-SCOPED not retired, and a VACUOUS-PASS TRAP in CIS-054 D6 was disarmed (its gate would have closed 40-plus unexamined defects as a clean discharge). *** D14: six LIVE plans are at or near finalize on surfaces the staged queue declares; CIS-056 and CIS-050 share an IDENTICAL 4-file set with metrics-ledger-readers-and-timestamp-provenance. NOT superseded - surface overlap is not duplicate work. RE-GROUND CIS-050 and CIS-056 AFTER those land; CIS-056 claim 6 and CIS-057 claim 5 are HEAD-scoped and owe a re-check then. *** D15: there is NO add-a-row queue verb, so a Stage disposition costs a hand-rewrite of the whole 64-row plans array. It bent 043 from Stage to Fold. Surface a Stage to the operator rather than performing it silently. *** TWO SPECS NOW CARRY SEVEN DELIVERABLES (CIS-050, CIS-051) with scope-bloat rationales recorded; both lift out cleanly. *** EMIT STATE: the 2026-08-09 OPERATOR HOLD HAS NOT BEEN LIFTED. Preparation is complete. RECOMMENDED FIRST PAIR = CIS-059 + CIS-052 (059 operator-directed as the very next plan, overlaps no staged spec; 052 owns D1 and D2, the two most urgent live defects). CIS-049 pairs next. DO NOT PAIR 050/051/053/056 - they all contend on audit.py; 049/053/058 on client-api.md; 056/057 on manage-metrics plus analyze-logs. CIS-052 overlaps 8 live sibling-epic specs - CHECK THE SIBLING LEDGERS LIVE STATE BEFORE THE EMIT. *** RESTART VERDICT was not_ready ONLY on the inbox signal, which this drain cleared - re-run cleanup restart-check to confirm ready. *** STANDING, unchanged: corroborate against origin/main AND PR state before any shipped transition; every set-guarding detector must be POPULATION-DERIVED; a STEP-marker count is a FLOOR; LOWERING EFFORT LEVELS IS NOT A SANCTIONED SAVING; read queue counts and order from status.json plans array order, never from prose; the pin detector is truthful-signals PLAN-TRUTH-059, do NOT stage a CIS-side one; CHECK THE PLUGIN REGISTRY PIN BEFORE EVERY PLAN LAUNCH (a LIVE inversion was diagnosed 2026-08-23 and is recorded in Operator-Owed, unrepaired, repair is operator-only); NEVER accept a clean first-pass audit in this epic without the adversarial pass.
**Phase**: orchestrating
**Inbox (derived)**: 2 queued, 319 archived
**Parked**:
- PLAN-CIS-039 (WS-06) — PR 1149 — landing=landings/PLAN-CIS-039.md
- PLAN-CIS-036 (WS-04) — PR 1178 — landing=landings/PLAN-CIS-036.md
- PLAN-CIS-056 (WS-06)
- PLAN-CIS-057 (WS-04)
- PLAN-CIS-058 (WS-05)
- PLAN-CIS-061 (WS-04)
**Queue** (staged, in order):
1. PLAN-CIS-052 (WS-07)
2. PLAN-CIS-050 (WS-07)
3. PLAN-CIS-054 (WS-07)
<!-- END GENERATED: resume-summary -->

## Operating Rules

### ~~Parallelization and serialization classes~~ — ⛔ SUPERSEDED 2026-08-09

⛔⛔ **THE TABLE IN THIS SUBSECTION IS NO LONGER AUTHORITATIVE.** It derived disjointness from
**workstreams**, which pooled four unrelated surfaces into one class and capped the epic at a
15-deep serial path. **Read the next subsection instead** — § "Serialization classes are derived
from surfaces, not from workstreams". The `parallelization_scope = 2` / `auto_emit = false`
settings and the *pair by surface disjointness, never by count* principle below remain correct and
are restated there.

`parallelization_scope = 2`, `auto_emit = false`. Plans pair by **surface disjointness**, never by
count. A slot is left empty rather than filled with a colliding plan.

| Class | Members |
|---|---|
| `manage-architecture` | PLAN-02, PLAN-CIS-001, PLAN-CIS-002, **PLAN-CIS-023** — ⛔ **now FOUR-way** |
| `tools-marketplace-inventory` | PLAN-CIS-003, PLAN-CIS-006 |
| ⭐ **attribution-seam consumers** | **PLAN-CIS-024**, **PLAN-CIS-025**, **PLAN-CIS-026** (D2) — ✅ **mutually disjoint by bundle, so they MAY pair with each other**, but ⛔ **all three are gated on PLAN-CIS-023** and none may pair with it |
| ⭐ **derivation resolvers** (adjacent-by-contract) | PLAN-CIS-003, PLAN-CIS-004, **PLAN-CIS-026** — different bundles, same seam and union semantics. Pairing permissible; **re-verify at emit that none is editing the seam itself** |
| `plan-retrospective` | PLAN-CIS-008, PLAN-CIS-009, PLAN-CIS-012, PLAN-CIS-013, PLAN-CIS-019, PLAN-CIS-020, **PLAN-CIS-022** (+PLAN-CIS-016 partially) — ⛔ **now EIGHT-way, no two may pair** |
| `phase-6-finalize` | PLAN-CIS-010, PLAN-CIS-011 — ⛔ **cross-epic**, see below |
| project auditor (`audit.py`) | PLAN-CIS-016 (PLAN-11 shipped #1063) |
| `pm-plugin-development` | PLAN-CIS-003 + PLAN-CIS-006 (`tools-marketplace-inventory` — never pair) · **PLAN-CIS-021** (`ext-self-review-plan-marshall` — different skill, pairing permissible but re-verify file sets first) |
| phase-handshake records | PLAN-CIS-018 — ⚠ re-check against PLAN-CIS-015 at emit time |
| test tree / conftest | PLAN-CIS-017 — pairs badly with almost anything |
| ⭐ **`ext-self-review-plan-marshall`** | **PLAN-CIS-043** (+ PLAN-CIS-021, shipped) — ⛔ re-verify CIS-043's D2 against CIS-021's landing before scoping; it may already carry part of it |
| ⭐ **WS-06 context economics** | **PLAN-CIS-039**, **PLAN-CIS-040** — ✅ **mutually disjoint, MAY pair**; ⚠ both touch the `execution-context` agent body, so **re-verify the file set at emit**. ⛔ Neither pairs with a WS-04 plan editing `manage-metrics` emission |
| ⭐ **live language-server surface** | **PLAN-CIS-041**, PLAN-CIS-026, PLAN-CIS-007 — ⛔ **never pair**; shared server binary and config surface. ⚠ CIS-041 and CIS-026 are **two incompatible lifecycles** (warm interactive vs batch harvest) and must not be merged into one plan |
| ⭐ **`phase-6-finalize` blocking boundary** | **PLAN-CIS-044** — ⛔ never pair with CIS-010, CIS-011, or CIS-043 (D3 shares `pre-submission-self-review.md`); ⚠ coordinate with CIS-018 (same handshake record) |

### ⭐⭐ CORRECTED 2026-08-09 — SERIALIZATION CLASSES ARE DERIVED FROM SURFACES, NOT FROM WORKSTREAMS

⛔ **The former rule "WS-04 is a serialization class; any emit is at most one WS-04 plus one other"
is RETIRED.** It pooled four unrelated surfaces under one charter and capped the epic at a 15-deep
serial path. See § Queue Reconciliation 2026-08-09 finding **R2**. The classes below are the
authority; **a plan's workstream says nothing about whether it may pair.**

| Surface class | Members — no two may pair |
|---|---|
| `plan-retrospective` | CIS-012, CIS-013, CIS-016 (partial), CIS-019, CIS-020, CIS-022 |
| `phase-6-finalize` | CIS-010, CIS-011, CIS-034, CIS-044 |
| `manage-metrics` | CIS-042, CIS-037, CIS-035 (+ CIS-022's render side — coordinate) |
| `manage-execution-manifest` | CIS-038 (+ CIS-012 secondary) |
| `manage-architecture` | PLAN-02†, CIS-001†, CIS-002, CIS-023† († shipped) |
| `ext-self-review-plan-marshall` | CIS-043, CIS-045 (fixture corpus) — ⛔ never pair |
| live language-server | CIS-041, CIS-026, CIS-007 — ⛔ never pair |
| WS-06 context economics | CIS-039, CIS-040 — ✅ **may pair with each other**; ⚠ both touch `execution-context` |
| `tools-marketplace-inventory` | CIS-003†, CIS-006 |
| attribution-seam consumers | CIS-024, CIS-025, CIS-026 (D2) — ✅ mutually disjoint by bundle |
| derivation resolvers | CIS-003†, CIS-004, CIS-026 — pairing permissible; re-verify the seam at emit |
| project auditor (`audit.py`) | CIS-016 |
| test tree / conftest | CIS-017 — pairs badly with almost anything |

⭐ **FREED BY THIS CORRECTION — these three collide with NOTHING else in the queue and are the
highest-value second-slot fillers:**

| Plan | Surface | Why it is disjoint |
|---|---|---|
| **CIS-014** | `platform-runtime` + the hook layer | no other staged plan touches it |
| **CIS-018** | phase-handshake capture / `_invariants.py` | ⚠ re-check vs CIS-015 only |
| **CIS-036** | `work/metrics.toon` read-only + one audit check | ⭐ **mutates nothing** |

⚠ **The `plan-retrospective` class remains the largest single bottleneck at six members** — that is
real and unchanged. What changed is that it is no longer the whole of WS-04. Fill the second slot
from any class the running plan is not in
or from PLAN-CIS-021, never from a second WS-04 measurement plan.

⛔ **This rule is LIVE and it has already bitten — 2026-08-02.** With `parallelization_scope` raised to
2, the intended second-slot pick was **PLAN-CIS-030** (to get the L3 instrument in before the levers).
**That is a second WS-04 measurement plan beside a running CIS-028 that touches `plan-retrospective`,
so this rule forbids it**, and PLAN-CIS-001 (WS-01) was emitted instead. ⭐ **The instrument-first
concern dissolves on inspection and must not be re-litigated**: CIS-030's D1 re-derives its baseline
from `.plan/local/archived-plans`, which is **immutable** and whose plans all pre-date CIS-001, so
landing the lever first delays *sizing* the saving — it does not destroy the ability to size it.

✅ **BAR LIFTED 2026-08-03 — CIS-028 shipped as #1080, so the `plan-retrospective` class is free and
CIS-030 is emittable.** The paragraph above is kept as the record of *why it was held*, not as a live
constraint. ⛔ **The rule itself is unchanged and still binds**: with CIS-030 running, the second slot
must again come from WS-01/02/03 — **PLAN-CIS-031 is WS-04 and touches the same self-review /
`mark-step-done` neighbourhood, so it is NOT the pairing partner** despite sitting at queue position
2. The first admissible partner is **PLAN-CIS-032** (WS-01, executor generator), which is disjoint
from everything CIS-030 touches.

⭐ **The 08-01 additions improve pairing materially.** PLAN-CIS-024 (`pm-documents`) is disjoint from
every existing plan in the queue, and once PLAN-CIS-023 lands, 024/025/026 are mutually disjoint —
the first genuinely parallel cluster this epic has had outside a single lucky pairing.

⛔ **`phase-6-finalize` is a CROSS-EPIC class.** `truthful-signals` PLAN-TRUTH-001 must land **before**
PLAN-CIS-011's detector work — PLAN-TRUTH-001 corrects the roster the detector asserts against. Per-epic
disjointness does not see across the boundary; check both queues before pairing into that surface.

### Cross-epic routing — THREE-WAY (operator rule, 2026-07-30)

⛔ **We keep only what is ours. Every other finding is delegated, and delegation is mandatory, not
discretionary.** The operator set this rule directly: PR/review findings go to `review-apparatus`,
and everything else outside our goals goes to `truthful-signals`.

| Destination | Owns |
|---|---|
| **HERE** — `code-intelligence-substrate` | How the system **KNOWS things** — navigation, index, graph, content search — **and MEASUREMENT** of the codebase or of our own runs: footprint derivation, cost/token accounting, evidence emission, detector population and derivation |
| ➜ **`review-apparatus`** | **Anything touching PRs or review** — review-bot participation and contracts, PR comment/thread handling, review barriers and gates, merge-queue and post-merge revisit behaviour, and feeding PR findings back into local review |
| ➜ **`truthful-signals`** | **Everything else that is not ours** — the default sink. Behaviour/contract signals that read confident while hiding a caveat: config, lessons, daemon, docs contracts, test isolation, merge/landing truthfulness |

**Rule of thumb, in precedence order:**

1. Does it touch a **PR or a review**? → `review-apparatus`. This test runs FIRST and wins outright,
   even when the finding also smells like measurement — a participation *detector* is still review.
2. Otherwise, does fixing it change **what the system can find out, or how it counts**? → ours.
3. Otherwise → `truthful-signals`.

- ⭐ **SHARPENING ADOPTED 2026-08-09, proposed by `review-apparatus` (`-007`) and accepted here:
  the deciding question is WHOSE BEHAVIOUR IS BEING MEASURED, not which artifact carries it.**
  Self-review is ours (our own run's measurement, no PR surface); bot participation is theirs (a
  third party's behaviour on a PR). ⭐ It resolves every case the two epics have hit so far and it
  explains *why* test 1 below wins outright rather than restating that it does. ⚠ Either epic may
  propose better wording if it stops working — recorded as adopted, not as settled forever.
- ⚠ **Ambiguity between the two siblings defaults to `truthful-signals`** (the general sink); ambiguity
  between *us* and a sibling resolves by test 1 then test 2. **Do not ping-pong** — forward once; if it
  returns, keep it and record the disagreement.
- ⛔ **Forward, never copy — one owner per item.** A signal held in two epics produces two independent
  plans against one defect. When a finding is delegated it is **removed from our ledger**, not left
  behind as a courtesy note.
- ⛔ **Delegate through the INBOX, never by editing a sibling's tree.** `orchestrator inbox write
  --slug {sibling} --sender-type orchestrator --sender-id code-intelligence-substrate`. Another epic's
  tree is outside our write boundary.
- **A forwarded message is a LEAD, not a fact.** Re-verify against ground truth before it influences a
  ledger write here — in both directions.
- ⚠ **A deferral conditioned on a sibling's PR must NAME that PR**, so retiring it is a check rather
  than a memory. A cross-epic constraint recorded on one side only has no reader on the other side to
  notice when it expires.

### Plan-ID naming — code-slug scoped, band retired for new plans

⭐ **All new plans in this epic are named `PLAN-CIS-{NNN}-{slug}.md`.** `CIS` is this epic's code
slug; `{NNN}` is a zero-padded three-digit ordinal that IS the launch position. The full old→new
mapping for the 17 renamed staged specs lives in [`plan-id-rename-map.md`](plan-id-rename-map.md) —
consult it when reading any `logs/`, `inbox/archive/`, or cross-epic document written before the
rename, because those append-only records still carry the old ids by design.

⛔ **The numeric band is now legacy-only.** Because `CIS` scopes every new id to this epic, a
cross-epic numeric collision is structurally impossible for `PLAN-CIS-*` and the band no longer needs
to be negotiated for new work. The band still governs the four surviving unprefixed ids here —
`PLAN-01`, `PLAN-02` (running), `PLAN-10`, `PLAN-11` (running) — which were deliberately NOT renamed,
and it remains live in `truthful-signals`' mirror:

| Epic | Legacy numeric range |
|---|---|
| `code-intelligence-substrate` (this epic) | **1–49** and **120–199** — only `01`, `02`, `10`, `11` still in use |
| `truthful-signals` | **50–119** and **200–299** — still fully live there, **plus the carve-out below** |

⛔ **CARVE-OUT: `27` and `41–49` are `truthful-signals`', permanently.** Ten ids inside our nominal
`1–49` block are held by them — `PLAN-27` and `PLAN-41`–`PLAN-48` shipped (PRs #995, #991, #988, #989,
#990, #993, #994, #997, #996) and `PLAN-49` staged. They are inherited from the predecessor epic
`plan-optimization` and **predate the band invariant, which was written as though it had always
held**. The nine shipped ids are immovable: renumbering them would break citations across nine landing
reports and the merged PR record.

⭐ **Costs us nothing to concede, so it was conceded outright.** Since the `PLAN-CIS-*` rename we do
not allocate in `1–49` at all, so `PLAN-49` did **not** need renumbering — they were offered the
choice and told to keep it (`code-intelligence-substrate-007.md`, 2026-07-30).

✅ **RESOLVED the same day — the carve-out is now historical, not a live constraint.**
`truthful-signals` has since run its own code-slug rename (`PLAN-TRUTH-{NNN}`, 18 staged + 1 new), and
`PLAN-49` — the one movable member — is now `PLAN-TRUTH-015`. `review-apparatus` already used
`PLAN-PR-{NNN}`. ⭐ **All three epics are epic-scoped, so a cross-epic numeric collision is now
structurally impossible rather than convention-enforced, and the band no longer has to be mirrored in
three ledgers to work.** The nine shipped ids remain permanently theirs; this section is kept as the
resolver for pre-rename citations, not as a rule anyone still has to obey.

⭐ **The generalisable lesson, adopted here as a standing obligation:** *a numbering invariant written
after the fact describes the future, not the past.* Theirs was already false for ten rows at the
moment of writing, and went unnoticed for a session because it read as a description of reality rather
than an aspiration. **Audit the existing population against a new invariant at the moment you write
it, and record the exceptions as an explicit carve-out.** An invariant with a documented carve-out is
usable; a silently false one is worse than none, because it is trusted. This is standing rule 4
("a reported instance is a SAMPLE") applied to our own ledger rules rather than to findings.

⚠ **Never rename a launched or shipped plan.** `PLAN-02` and `PLAN-11` are running and their
`request.md` `source_id` points at their spec path on disk; `PLAN-01` and `PLAN-10` are shipped with
`landings/PLAN-01.md` / `landings/PLAN-10.md` and archived plan dirs pointing at them. Renaming any of
the four would dangle a persisted pointer that nothing re-derives.

⚠ **The next free ordinal is `PLAN-CIS-027`.** Allocate strictly by incrementing past the highest
existing `PLAN-CIS-*` — never by counting staged rows, which under-counts once plans ship.
⭐ **The ordinal is no longer the launch position.** `PLAN-CIS-018`/`-019`/`-020` were staged from a
landing rather than from `decompose`, so they sit at the queue TAIL while their subject matter belongs
with the WS-04 measurement cluster. The `#` column still equals the `plans[]` array position; it no
longer implies priority.

⛔ **The detector's grammar is case-sensitive.** `orchestrator inbox detect` accepts the code slug as
`[A-Z0-9]{2,8}` — UPPERCASE only. A lowercase `plan-cis-018-x.md` is classified
`unrecognised_id`, and the plan then writes NO inbox message at finalize. The accepted forms are
`PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, and `{SLUG}-{DIGITS}` (shipped in #1057).

### Standing verification rules

1. ⛔ **A `kind=landing` message is a LEAD.** Corroborate against `origin/main` and PR state **before**
   any `queue --transition --status shipped`. Two messages across the two epics have claimed a merge
   that had not happened; both were envelope-valid and richly detailed, and wrong on the only claim
   that mattered. An unverifiable landing message stays in `inbox/` un-archived and is reused intact
   once the merge is real.
2. ⛔ **A plan's own retraction outranks its earlier finding.** Fold the corrected version, and record
   the retraction so the withdrawn claim is not re-scoped later.
3. ⛔ **Verify a moved spec's HEADER and HAND-OFF LINE, not just its queue row.** The emitted command
   is a one-line pointer and the spec file *is* the brief, so a stale `epic:` header or hand-off path
   is a live emit-blocker that a correct queue row will not reveal.
4. ⛔ **A reported instance is a SAMPLE.** Every detector this epic ships must derive its population;
   a count of sightings is not a population, and an asserted absence needs the same derivation as an
   asserted presence.
5. ⛔ **N passing checks of a PURE function is ONE assertion repeated N times.** Before quoting a
   verification count as evidence, ask what the check actually touches. `inbox detect` is a pure
   function of the id *grammar* — it never opens the file — so "17/17 pointers return
   `detection: orchestrated`" establishes that 17 strings are well-formed, **not** that 17 files
   exist, are correctly named, or match `plans[]`. The check that bites is the one that can come back
   negative for a *different* reason than the others: here, enumerating the `plans/` directory
   against `plans[]` in **both** directions plus a row-slug-to-filename-tail comparison.
   ⭐ Raised by `truthful-signals` (`truthful-signals-018.md`) against our own rename note, accepted,
   and the real check then run — 21 rows ↔ 21 files, 1:1, zero orphans, zero slug mismatches. **A
   verification note that reads as stronger evidence than it is belongs to this epic's own theme**;
   we shipped one, and a sibling caught it rather than our own review.

## Ordered Queue

⛔ **Live count, live status and live order are `status.json` `plans[]` — this table restates none of
them.** The `#` column is a reading aid for queue order and is authoritative for nothing.

The table below is a GENERATED surface. Before the 2026-08-22 ingest this section carried **no
`BEGIN/END GENERATED` marker pair at all**, so `orchestrator compact` could not reach it and
reported it as a blind spot (`markers_absent`) rather than as an abstention. The markers are seated
now; the table is regenerated from `status.json` and must never be hand-edited. Per-plan narrative
goes in § Queue annotations below, **outside** the markers, where a regeneration preserves it
verbatim.

The pre-ingest annotated table — with its per-plan notes for the shipped plans — is relocated to
[`settled.md`](settled.md) § "Relocated: the pre-ingest Ordered Queue (annotated)". Those notes are superseded by
`landings/PLAN-CIS-*.md`, which carry the same facts **checked against the tree** rather than
against each plan's own account of itself.

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-CIS-052 | WS-07 | staged | .claude/skills/finalize-step-lessons-housekeeping/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_decision_line_shapes.py; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/scripts/_freshness_crosscheck.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/scripts/manage-tasks.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/references/report-structure.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/scripts/retro_sections.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/execute-task/test_inject_project_dir.py; test/plan-marshall/manage-metrics/; test/plan-marshall/manage-status/; test/plan-marshall/manage-status/test_manage_status_metadata.py; test/plan-marshall/manage-status/test_mark_step_completion_emission.py; test/plan-marshall/plan-marshall/; test/plan-marshall/plan-retrospective/; test/plan-marshall/workflow-integration-git/test_worktree_rebase_executor_refresh.py |
| 2 | PLAN-CIS-050 | WS-07 | staged | .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; .claude/skills/audit-archived-plan-retrospectives/scripts/checks/; .plan/local/archived-plans/**; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-dynamic-level-executor.md; marketplace/bundles/plan-marshall/skills/manage-config/; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-logging/scripts/plan_logging.py; marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage-references.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md; marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-variants.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/plan-efficiency.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-outline-vs-shipped.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/references/outline-vs-shipped.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/references/script-failure-analysis.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/script-failure-analysis.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_gate_decisions.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_provenance.py; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-walkthrough.md; marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py; test/plan-marshall/audit-archived-plan-retrospectives/; test/plan-marshall/manage-execution-manifest/; test/plan-marshall/manage-metrics/; test/plan-marshall/manage-references/; test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py; test/plan-marshall/plan-retrospective/; test/pm-plugin-development/tools-marketplace-inventory/ |
| 3 | PLAN-CIS-054 | WS-07 | staged | .claude/skills/audit-archived-plan-retrospectives/SKILL.md; .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; .claude/skills/audit-archived-plan-retrospectives/scripts/checks/; .plan/local/archived-plans/**; CLAUDE.md; doc/adr/; doc/concepts/; doc/developer/corpus-language-server-protocol.adoc; doc/resources/diagrams/context-isolation.svg; doc/user/; marketplace/bundles/plan-marshall/.claude-plugin/plugin.json; marketplace/bundles/plan-marshall/skills/*/*/references/*.md; marketplace/bundles/plan-marshall/skills/*/*/standards/*.md; marketplace/bundles/plan-marshall/skills/*/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/report-structure.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py; marketplace/bundles/pm-documents/skills/plan-marshall-plugin/; marketplace/bundles/pm-plugin-development/skills/*; marketplace/targets/claude/plugin_json_gen.py; test/plan-marshall/manage-metrics/; test/plan-marshall/plan-retrospective/; test/plan-marshall/tools-script-executor/test_generate_executor.py |
| 4 | PLAN-CIS-039 | WS-06 | parked | doc/concepts/token-management.adoc; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/skill-loading.md |
| 5 | PLAN-CIS-036 | WS-04 | parked | (prose) |
| 6 | PLAN-CIS-056 | WS-06 | parked | .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; doc/concepts/token-management.adoc; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py |
| 7 | PLAN-CIS-057 | WS-04 | parked | .plan/; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py |
| 8 | PLAN-CIS-058 | WS-05 | parked | marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/ |
| 9 | PLAN-CIS-061 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py; test/plan-marshall/manage-metrics/; test/plan-marshall/plan-retrospective/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

⭐ **The live queue is 13 rows: 10 staged, 2 parked, 1 retired.** Everything else has shipped.

**The `5xx` remediation wave (WS-07, 7 staged).** Emission order and the constraints that bound it
are in [`workstreams/WS-07-landed-corpus-remediation.md`](workstreams/WS-07-landed-corpus-remediation.md).
The two that matter: `PLAN-CIS-052` **preferably** before `PLAN-CIS-053` (a preference, not a
prerequisite — `053` is order-independent by construction, so **do not hold it**), and
`PLAN-CIS-054` **last**, because it corrects descriptions of behaviour the other seven change.

**The three orchestrator-authored plans (`056`, `057`, `058`).** Staged on 2026-08-22 because the
`5xx` wave does not cover them: it discharges the audit's gaps against the substrate's correctness,
and these three discharge (a) the measurement the epic was created to make, (b) the deliverables the
cloud lane structurally could not reach, and (c) two structural checks the epic specified and never
built. Each spec's § Provenance states why it exists.

**The two parked rows.** `PLAN-CIS-039` and `PLAN-CIS-036` both halted at their D0 gate because no
corpus is reachable in a cloud clone. Both halts were correct. ⛔ **Neither may be re-emitted as
written** — see § Open Defects D3 and D4.

**Pointer specs.** `PLAN-CIS-046`, `047` and `048` carry pointer specs, not briefs: they shipped
before ever being staged here. They exist so `corpus enumerate` reconciles in both directions, and
they carry no hand-off command.

### Emission readiness — prepared 2026-08-22, NOT emitted

⛔ **The 2026-08-09 operator hold has not been lifted.** The 2026-08-22 instruction was to *prepare*
to emit, which is preparation and not authorisation. `R=0`, `N=2`, two slots open. **Nothing was
emitted and no `launched` transition was recorded.**

**Preparation is complete and the queue is emit-ready**: 10 staged rows, every spec seated, every
surface now parseable (see § Open Defects D11 — it was not, until this pass fixed it), and the
corpus reconciling 62/62 in both directions.

**Recommended first pair — `PLAN-CIS-052` + `PLAN-CIS-049`.** Chosen on evidence, not on order:

- **They are genuinely disjoint.** `corpus cross-check` returns no overlap row between them, verified
  after the D11 fix made the check real.
- **`PLAN-CIS-052` owns the two most urgent live defects in the corpus** — D1 (the live
  wrong-checkout risk) and D2 (the merge-with-pending-findings hole) — and it is the plan the
  audit's own sequencing wants before `PLAN-CIS-053`.
- **`PLAN-CIS-049` is the largest untouched surface** (59 gaps) and contends with nothing `052`
  touches.

⛔ **Pairs that must NOT be emitted together**, from the cross-check over the staged set:

| Do not pair | Contended on |
|---|---|
| `050` / `051` / `053` / `056` | `audit.py` and the retrospective scripts — the audit's own stated constraint |
| `049` / `053` / `058` | `client-api.md` |
| `049` / `058` | `argparse_surface.py` |
| `056` / `057` | `manage-metrics.py`, `analyze-logs.py` (also both contend with `050`) |

⚠ **`PLAN-CIS-052` is the most cross-epic-contended spec in the corpus** — it overlaps **eight live
sibling-epic specs** (`truthful-signals` `-089`/`-090`/`-091`/`-096`/`-097`, `review-apparatus`
`PLAN-PR-010`/`-014`, `plan-optimization` `PLAN-28`). Those are staged, not running, so this is a
**sequencing caution, not a block** — but throughput is spent across epics, and emitting `052` here
while a sibling emits one of those eight would collide. **Check the sibling ledgers' live state
before the emit, not after.**

⛔ **Re-grounding coverage, stated so it is not over-read.** The `5xx` specs were authored against a
tree that has since taken commits up to `31211a99b`, and **no spec in this corpus has had its
verify-first clauses corroborated against HEAD by this pass** — `corpus verdicts` returns no admitted
verdict for any of them. Per the standing per-emit obligation, **each candidate owes that
corroboration at outline**, and an absent clause does not block an emit but an unabsorbed refutation
does.

## 2026-08-22 Landed-Corpus Ingest

The 36 specs exported to `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/` in the 2026-08 cloud wave have all
landed and are ingested. **The export directory is now empty and removed from git**; every artifact
it held is archived under `cloud-runs/`.

✅ **CORRECTION, 2026-08-24 (`status` pass) — the ingest PR HAS LANDED.** The resume anchor still says
*"PR #1331 is OPEN … and ENQUEUED in the merge queue"*, which was true when it was written and is now
false: `ci pr view --pr-number 1331` reports **`state: merged`** (branch `chore/ingest-cis-landed-corpus`
→ `main`). The anchor is rendered verbatim by design and is not silently rewritten, so the correction is
recorded here instead; the next mutating verb folds it into a fresh anchor. ⭐ **The standing rule held** —
the landing was verified from PR state, never from the enqueue message.

### What came back

| | |
|---|---|
| Plans executed | **37** — the 36 export directories `010`–`350` (which already include the mid-flight `135` and the split-off `350`), plus the fix plan `500` |
| Landed | **37 of 37** — no plan failed to land |
| Halted at a D0/D1 gate | **2** (`020`, `080`) — both correctly, both on an unreachable corpus |
| Recorded gaps | **480** — **48 high**, 219 medium, 213 low |
| Fix plans derived | **8** (`500`–`570`); `500` ran, seven are staged here |

⭐ **Every one of the 37 audited plans returned *sound after correction*. Not one returned sound as
written.** That is the ingest's most reusable result, and it held on the 37th: `PLAN-CIS-048`'s
first-pass audit reported *6 of 6 confirmed, zero high gaps, no false claims, no vacuous guards*,
and the adversarial pass overturned it with two high-severity findings — one of which was **disproved
by a sentence in the audited document itself**. ⛔ **Never accept a clean first-pass audit in this
epic without the adversarial pass.**

### Gap counts, re-derived first-party

⛔ **The audit's own roll-up is off, and so was the aggregate of the analysis pass.** Counted
directly from the `Severity` field of every `## G*` entry across the whole corpus:

| Source | Total | High | Medium | Low |
|---|---:|---:|---:|---:|
| The audit's own summary prose | 472 | 46 | 216 | 210 |
| Aggregate of the six analysis batches | 473 | 47 | 215 | 211 |
| **Counted first-party from the entries** | **473** | **46** | **217** | **210** |
| plus `PLAN-CIS-048`, audited during this ingest | 7 | 2 | 2 | 3 |
| **Corpus total** | **480** | **48** | **219** | **213** |

The entry population is exact: **473 `## G*` headings, and 473 `Severity` lines** — every entry
carries one and only one. The three figures disagree because **15 entries carry a severity followed
by prose** (`medium — raised from low…`, `low (contained today by G4…)`), and a strict line match
misses them while a loose word match over-counts. ⭐ The audit's summary anticipated exactly this
and told readers to re-derive rather than trust it. **It was right to, and its own total was still
one short.**

⚠ **A self-correction, recorded because it is this epic's own archetype (F11).** The first draft
of this section, of the commit message, and of the resume anchor all said **39** — counting `135` and
`350` as additions to the `010`–`350` range when they are **inside** it. Caught by reconciling
against the archive (37 directories carrying a `plan.md`) rather than against the prose. **A count
carried forward is wrong by the time it is published**, including this ledger's own.

### Two ledger premises this ingest CORRECTED

- **C1 — `PLAN-CIS-037` never halted.** The prior anchor recorded it as halted at a D1 gate, citing
  commit `c586d2cbe` / PR #1150. **That commit belongs to a different epic** — `truthful-signals`'
  plan `060-invented-plan-scoping-flags-are-an-overgeneralized-convention`. It is a **cross-epic
  collision on the bare numeral `060`.** This plan completed and merged as PR #1173.
  ⛔ **STANDING RULE: a bare `NNN-` export number is NOT unique across epics. Corroborate a commit
  against the epic named in its message before attributing it.**
- **C2 — `PLAN-CIS-016`'s item-B diagnosis was refuted as to cause.** The anchor recorded the
  `[LOCK]` marker as having *zero production emitters, so the detector AND its green test suite are
  both vacuous*. **Production does emit it** — `log_lock_event`, 10 call sites — and the tests were
  real. The actual defect was a **scan-root path mismatch** (`.plan/logs/` written vs
  `.plan/local/logs/` scanned), and **it is closed**: both roots are scanned, and an absent substrate
  now reports `unmeasured` rather than a fabricated zero.

### Two ledger premises this ingest CONFIRMED

- **`PLAN-CIS-018`: mechanism refuted, symptom confirmed** — and the run established that
  first-party at its own D1 rather than taking it from the ledger. It fixed the real defect (root
  resolution walking up from a worktree-resolved base) and **correctly avoided the no-op the ledger
  had forbidden**.
- **`PLAN-CIS-017`'s G1 withdrawal holds.** The claim was withdrawn because the evidence was CPU
  contention from concurrent agents sharing one working tree — nine fresh measurements all landed
  inside the shipped range. ✅ **No fix run was sent to rewrite correct documentation.** ⭐ This is
  the clearest evidence in the corpus that the adversarial pass does real work.

## Structural Findings — the standing evidence base

Verify against HEAD before scoping on any of these.

**F0 — ⛔⛔ A STAGED SPEC DECAYS AGAINST A MOVING TREE, AND NOTHING RE-GROUNDS IT. Established
2026-08-08 by the full-queue reconciliation; n=4 in ONE pass.** This is the finding the epic should act
on first, because it silently corrupts every other finding it carries.

| Instance | What was found | Verified against |
|---|---|---|
| `PLAN-CIS-008` | **Obsolete in FULL** — all four deliverables shipped. The `multi_module` rows exist; the closure test exists and is *stronger* than the spec asked (exact cross-product, both directions, with two negative controls). **RETIRED.** | `plan-efficiency.md:103-109`; `test_plan_efficiency_anchors.py` |
| `PLAN-CIS-020` | **Half shipped** — D3 done, D2's render path done, D4's mechanism done; 7 deliverables → 4. Its D1 premise (*"cannot be registered at all"*) is **REFUTED**. | `compile-report.py:164-189, 192, 313-341`; `retro_sections.py:30,85` |
| `PLAN-CIS-015` D5 | Carried a deliverable for **already-closed** calibration-anchors work. **STRUCK.** | lesson `2026-07-21-15-001` § "Closed sibling concern" |
| `PLAN-CIS-025` | An open verify-at-outline question **answered**: CIS-023 already retired the core prefix map ⇒ this plan touches **no** core file. | `_architecture_core.py` (no `.claude/skills` literal, no prefix-map constant) |

⇒ **Two plans were ONE EMIT away from re-shipping finished work.** ⛔ **A spec's AGE is a correctness
risk**, and the risk is invisible: an obsolete spec looks exactly like a valid one, and its D1 gate is
the *only* thing standing between it and wasted work — a gate the plan pays full lifecycle cost to
reach. ⭐ **Three independent arrivals of this finding in one day**: this reconciliation, lesson
`2026-07-29-19-001` (*a staged spec premise EXPIRES; re-measure at outline, never inherit it*, folded
into CIS-015), and CIS-011's own D5 note (*"re-ground against #1076 before scoping"*).

⛔ **STANDING RULE, binding on the `next` verb**: **re-ground a spec against the implementing source
before emitting it**, and prefer emitting *recently-touched* specs over long-dormant ones when both
qualify. **The ledger's oldest staged plans are its least trustworthy.**

**F0b — ⭐ The queue also carried THREE cross-plan DUPLICATE deliverables**, each in a different
workstream from its twin, all found in the same pass: footprint capture (`CIS-012` D3 vs `CIS-034` D4 —
**two writers for one key**), `[ARTIFACT]` emission (`CIS-010` D3 vs `CIS-015` D4), and the
pending-row partition (`CIS-016` D4 vs a fold the orchestrator itself added hours earlier). ⇒ **Folding
a message into a plan without reading that plan's deliverables reproduces the duplication the fold is
meant to prevent** — the orchestrator committed exactly that and recorded it in `CIS-016`.

**F1 — `architecture find` is a path glob, not a content search.** It cannot answer "which files
contain string S", and works as designed. → PLAN-CIS-001.

✅ **F2 and F4 are RETIRED by PLAN-02 (#1067, `c6b501e6a`)** — the seam they described now exists:
edge derivation is an N-resolver extension point, resolver-attributed, with the Maven coordinate join
re-homed as one resolver among others. ⚠ **Retired ≠ populated.** The seam makes a non-Maven resolver
*possible*; PLAN-CIS-003 and PLAN-CIS-004 are what actually put edges in the graph. ⛔ **Do not read
"F2 retired" as "the graph has edges"** — until a marketplace resolver ships, a zero-edge answer is
still the normal answer, the difference being that it now carries provenance and distinguishes
*no resolver ran* from *resolvers ran and found nothing*. Both findings are kept below as the standing
evidence base for the plans that consume them.

⛔ **F2 IS STILL OPEN AFTER PLAN-CIS-003 (#1074) — the landing claimed closure and the claim was
REFUTED at HEAD (2026-08-02).** Probed live after the merge: `architecture graph` returns
`edge_count: 0` / `edges[0]`, `impact` is empty for both `plan-marshall` and `pm-documents`,
`neighbors --module plan-marshall` returns only itself, and all 12 modules are listed as **both
roots and leaves**. Meanwhile `resolvers[3]` report `markdown, 24` · `maven, 0` · `python, 5`.
⭐ **29 resolver-derived edges exist and the merged graph has zero.**

**Stale data is ruled out**: `derived-module --module pm-documents` shows `component_refs[8]` with
**five RESOLVED cross-bundle refs** (4× `plan-marshall`, 1× `pm-plugin-development`) — inputs
present, fresh, resolved; output empty. Not a stale plugin cache either: the three new resolvers
execute, so #1074's code is the code running.

⛔ **The standing warning fired a second time, one tier down.** PLAN-02's landing said *"do not read
F2 retired as the graph has edges"*. The successor is **"resolvers wired" ≠ "the graph has edges"** —
and this time it was reported as closure. ⚠ The mechanism is a **HYPOTHESIS, not established** —
derive it, do not assume it. Candidates: the merge dropping pairs whose endpoints are not both known
module names; the 24 markdown edges collapsing to self-edges after module-granular mapping; or
`graph` reading a persisted edge set the live resolvers never write.

⭐ **The highest-value question is how D4's "end-to-end proof" passed while the live system returns
empty** — a proof that passes in-plan and fails on main is fixture-scoped or asserts the
resolver-level count rather than the merged graph. **Audit the evidence, not only the code.**

→ **PLAN-CIS-027 owed.** ⚠ **PLAN-CIS-004 and PLAN-CIS-026 are now SUSPECT** — both add resolvers
through this same merge path, and a fourth and fifth producer feeding a merge that drops its inputs
adds nothing. **Sequence PLAN-CIS-027 ahead of both.**

**F2 (original statement) — the dependency graph is empty while its API reports success.** The
originally-identified mechanism:
`_cmd_client_query.py` derives an internal edge **only** by joining a Maven `groupId:artifactId`
pair against a map built from module metadata. Bundle modules carry no such coordinates, so the
`internal` edge set can never populate. ⇒ **Edge derivation is build-system-shaped for Maven while
this repo is a marketplace-bundle project.** `graph`, `path`, `neighbors` and `impact` are
structurally vacuous here. ⭐ Raw material exists and is unused: `derived-module` already carries a
`packages` map at skill granularity. → PLAN-02 (seam), PLAN-CIS-003, PLAN-CIS-004.

**F3 — dispatched leaves have no sanctioned content-search path.** The `Grep` tool is revoked at
runtime while the bare-`grep` prohibition stays enforced, so leaves improvise with whatever survives
the hook. ⛔ The remedy is a first-class verb — **not** documenting the improvisation, which would
entrench a rule whose only basis is which binary gets invoked. → PLAN-CIS-001.

**F4 — the empty graph silently disarms a gate that reads as active.** `phase-2-refine`'s Feasibility
Check validates dependency direction from `architecture graph` and flags reverse flows as
`FEASIBILITY: CONCERN`; with zero edges the predicate can never fire. `architecture-refresh` reads
the same source. → PLAN-02 deliverable 5, PLAN-CIS-002.

**F5 — `impact` has no consumer** outside `manage-architecture`'s own SKILL.md. The concern that
blast-radius reasoning runs on an always-empty closure is **refuted** — that half is lower severity
than the rest of F2.

**F6 — ⛔⛔ THE ADDRESSABLE SHARE IS THE SMALLER HALF, AND THE LARGER HALF IS THE CORPUS.
Established 2026-08-09 from PR #1126's six-phase `metrics.toon` (first-party recompute, n=1).**

| | index-answerable | doc-residency | unattributed |
|---|---:|---:|---:|
| 2-refine | **3.3%** | **90.7%** | 6.0% |
| 3-outline | 16.8% | 73.0% | 10.2% |
| 4-plan | **0.0%** | 43.9% | 56.1% |
| 5-execute ⚠ | **33.6%** | 59.5% | 6.9% |
| 6-finalize | 13.8% | 64.5% | 21.6% |
| **whole plan** | **15.9%** | **65.2%** | 18.9% |

⇒ **`PLAN-CIS-036`'s central hypothesis is half-confirmed and half-refuted.** ✅ `5-execute` is
the substrate's best case at 33.6%, as predicted. ⛔ **`2-refine` is the WORST phase in the plan,
not a good one**, and `6-finalize` is not the worst case at all — two phases are worse. The spec
assumed refine was a codebase-orientation phase; **it is a documentation-reading phase.**

⛔ **STANDING RULE**: neither 15.9% nor 65.2% may be quoted as settled until `PLAN-CIS-036` D1 or
`PLAN-CIS-039` D1 has run the population. **n=1 is a lead, and this epic's own founding concern
is a phase-specific figure read as a whole-corpus one.**

**F7 — ⭐⭐ COST IS `resident_context × turns`, AND THE TURN FACTOR WAS UNOWNED.** The average
byte is re-read **44.6 times** (842.6M `cache_read` / 18.9M `cache_creation`), so
`cost(byte) = 1.25 + 0.1 × turns_remaining` — **~5.7× at the mean, ~13.4× entering early in
`5-execute`'s ~122-turn envelope.** ⇒ **When a byte enters dominates how big it is.** Both
factors are derivable today (`cache_read / tool_uses`) and neither is emitted. → `PLAN-CIS-042`
D3 emits them; `PLAN-CIS-040` consumes them.

**F8 — ⛔ A MID-RUN INBOX MESSAGE HAS NO READER, AND IT COST A DELIVERABLE.** The drain is an
orchestrator-tier act that runs **between** plans. `review-apparatus-006.md` was created
`2026-08-08T20:56Z`, **23 minutes after PLAN-CIS-031's `1-init` began**, carrying a hard
requirement — *every residual/absence claim must publish `scope_searched` + `files_scanned`* —
whose author stated it *"converts your scoping change from a risk into a safe one"*. It was
drained 2026-08-09, a day after the plan merged. **Verified first-party at HEAD: neither token
exists in `self_review.py` or `pre-submission-self-review.md`.** ⇒ **A message aimed at a running
plan is architecturally undeliverable and nothing says so.** → `PLAN-CIS-043` D4 makes the
undeliverability reported at write time; ⛔ **building a mid-run delivery channel is deliberately
out of scope** — it is a much larger design question.

### F9 — The cloud lane has one structural blind spot, and it is the git-ignored corpus

⭐ **Six plans deferred a measurement deliverable, every one of them on the same cause**: the
archived-plan corpus is git-ignored, so a fresh cloud clone cannot see it. Every deferral was
correct and every one was disclosed. **This is a LANE property, not six plan-level failures**, and
it is predictable in advance: any plan whose deliverable reads `.plan/local/archived-plans/` will
halt in the cloud and can only run locally.

⛔ **Two of the six then mis-stated what the halt implied.** `PLAN-CIS-036` reported, in four
places, *nothing needs building, only the corpus needs to be present* — and its own audit proved
that false: the instrument the measurement is defined over **does not exist**, is git-derivable, and
could have been built in the cloud clone with no corpus at all. `PLAN-CIS-039` similarly asserted an
absence that two shipped `--section` read verbs refute.

⭐ **`PLAN-CIS-040` is the correct model**: it separated the git-derivable half, shipped it, and left
the corpus-blocked half explicitly blocked. **That difference is the generalisable lesson** — a
corpus-blocked run should split, not halt wholesale — and it is what `PLAN-CIS-056` and
`PLAN-CIS-057` are built on.

### F10 — A fix for the vacuous-guard archetype keeps reproducing it, and now we can count it

The epic already knew this shape recurred. The ingest measured it: **it recurred in at least eight
of the 37 audited plans, and every time it did, it was in the deliverable specifically built to
detect that archetype.**

The clearest instances, all first-party and all reproduced by execution:

- `PLAN-CIS-016`'s census — built to catch unfireable detectors fleet-wide — ships a documented
  precedence rule that **cannot fire on any of the 12 live emissions**.
- `PLAN-CIS-017`'s anti-vacuity control — added as the remedy for exactly this — **fires red alone
  and green (25/25) in the real collection order**, which is the order that gates a merge.
- `PLAN-CIS-034`'s coverage canary went blind **one day after landing**, when a sibling plan added
  the very vocabulary the canary exists to notice.
- `PLAN-CIS-044`'s gate is real and mutation-proven internally, and **its refusal is invisible at
  its one production caller**.
- `PLAN-CIS-033`'s escape hatch can launder a populated profile to zero skills — **strictly worse
  than the defect it replaced, because it now looks deliberate.**

⛔ **The generalisable rule**: a guard's non-vacuity must be demonstrated **in the configuration
that consumes it**, not in isolation. Four of the five above are non-vacuous when run alone. This is
the whole charter of `PLAN-CIS-053`.

### F11 — A count carried forward is wrong by the time it is published

Present in nearly every one of the 37 reports, and named by three of them as their own most-repeated
error. Test counts, commit counts, file counts, gate-pass counts, corpus measurements — recorded
once at a verification round and never re-derived after the review round that changed them.

⭐ **The sharpest instances are self-referential**: `PLAN-CIS-004` and `PLAN-CIS-007` each ship the
stale-figure defect **inside the report proposing a fix for stale figures**, and `PLAN-CIS-019`'s
report warns its own readers to re-derive any count in it — and carries a count that warning would
have caught.

⛔ **Consequence for this ledger**: no figure enters `epic.md` without the command that produced it
and the moment it was taken. The § 2026-08-22 gap table above is written that way deliberately.

⭐⭐ **RECURRENCE 2026-08-25 — `PLAN-CIS-059`, folded from inbox `-008`, and it is the strongest
instance yet because the plan WAS a counting exercise.** Retiring one of eleven bundles and correcting
every count claim naming the old total, the run made **three** count assertions of its own and **each
was wrong**:

1. `CLAUDE.md` claimed **153** skills; re-derivation against the post-deletion tree found **154**. The
   outline had pre-empted exactly this, requiring counts be *"re-derived against the post-deletion
   tree, not decremented by guess."*
2. The clarified request said **"eight surfaces"** and then enumerated **nine**. ⛔⛔ **The outline
   CAUGHT it** — *"The D4 count is wrong, the enumeration is right"* — **and the operator gate that
   widened D4 then restated the same wrong figure** (*"Should D4 widen to cover all 8 surfaces"*), so
   the miscount survived into the decision record **after** being identified. ⭐ **This is the
   instructive one: identifying a miscount does not stop it propagating, because the gate was authored
   from the NARRATIVE rather than from the enumeration the outline had just derived.**
3. `phase-5-execute` claimed the deleted manifest had an empty `skills[]`; it had one entry.

⭐ **What worked, and is worth copying**: the outline's own *Coverage derivation* — a union of three
independent sweeps with a stated closure argument — produced the RIGHT surface set exactly where the
narrative count was wrong.
⛔ **Sharpened rule**: where a gate question or a document states a set size, derive it at authoring
time from the enumeration it summarizes — and **prefer stating the enumeration instead of its
cardinality** when the list is short enough to name. A cardinality is a claim; an enumeration is
evidence.
⭐ **Independently corroborated by this drain**: `git ls-files 'marketplace/bundles/*/skills/*/SKILL.md'`
returns **156** against the landing's **154 registered** — a gap of exactly 2, matching the run's own
`a1e704` finding (`lsp-client` and `recipe-surgical-fix` live but unregistered). The derivation and the
self-report agree, which is stronger than either alone.

### F12 — An automated reviewer repeatedly caught what every internal round missed

In at least three plans, a PR review bot or CI found a real defect that **four internal verification
rounds and the audit's own re-derivation all missed** — including a start-up crash reachable in every
installed project, which 3 rounds and 75 passing tests never saw because none of them tested outside
the flat source tree.

⭐ This is direct, repeated corroboration of the standing rule that **N passing checks of a pure
function is one assertion repeated N times**. The rounds were not lazy; they were *homogeneous*. The
check that bites fails for a **different reason** than the checks already written.

## Open Decisions — the epic must decide, not each plan

⛔ Two decisions closed on 2026-08-09 — the `in_total` direction and the cache-prefix rejection —
are relocated **with their reasoning** to [`settled.md`](settled.md) § "Relocated: settled Open Decisions", so neither is re-derived as an open option.

- ⭐ **Should the phase-5 chain tail be re-ordered to verify ONCE, after the Step 10a commit?**
  Today the tail is verify → commit → verify-again, and the second verify is **structurally
  unavoidable**: the Step 10a commit changes the `worktree_sha`, so `pre-commit-verify-freshness`
  correctly reports stale every time. Re-ordering to commit-then-verify would remove **one full
  verify per chain tail**. ⛔ It is a design question about step ordering, **not** a defect — the
  freshness gate is behaving correctly and must not be weakened. Cost impact belongs with
  `PLAN-CIS-057`.

- ⛔⛔ **NEW 2026-08-22 — `PLAN-CIS-007`'s D3 deferral rests on an INVERTED premise and should be
  re-taken, not merely re-documented.** Live diagnostics were withheld from the corpus LSP server
  because the validator's false-positive share was ~97%, making diagnostics unusable as a signal.
  **Its hard gate (`PLAN-CIS-006`) landed on main 74 minutes before `PLAN-CIS-007` merged**, taking
  the validator from 380 unresolved to 61 — **the false-positive share has inverted to ~41%.** Nine
  of that plan's 28 gaps are doc sites citing the stale figure. ⛔ **Fixing those nine numbers
  without re-taking the decision would harden a conclusion whose premise no longer holds.** The
  decision is the epic's, not a plan's.

- ⚠ **NEW 2026-08-22 — does `PLAN-CIS-055` (the lane-contract proposals register) belong to this
  epic at all?** It records proposals about the **cloud-plan-lane contract**, which is not this
  epic's surface. It is staged here because the audit derived it from this epic's runs and because
  the lane contract forbids a run from self-approving a change to the contract governing it. Under
  the standing three-way routing rule it is arguably `truthful-signals`' work. ⛔ **Not moved
  unilaterally** — a cross-epic move keeps its id and goes through the INBOX, and an offer is not a
  transfer. Recorded for the operator.

- ⚠ **NEW 2026-08-22 — is `PLAN-CIS-054` (156 gaps, 3 high) one plan or a wave?** It is by far the
  largest spec in the corpus and its charter is *shipped prose describes the code that shipped*.
  The scope-bloat guard applies at ~6 deliverables and it declares 6, so it passes as written — but
  156 gap entries behind 6 deliverables is a deliverable-to-work ratio nothing else in the corpus
  approaches. ⛔ **Its outline owes a split verdict before it is emitted**, and that verdict is the
  plan's to make against the tree, not this ledger's to guess.

## Open Defects — unowned or routed

The pre-ingest section is relocated verbatim to [`settled.md`](settled.md) § "Relocated: Open Defects as they stood before the ingest". This section is re-authored against the ingest's evidence. **Resolved items are named as
resolved rather than silently dropped.**

### Resolved by the wave

- ✅ **D-a (generator fail-open) is CLOSED** by `PLAN-CIS-045` — the guard exists and is
  mutation-proven. ⚠ **But it exits 0**, not the non-zero the plan and four shipped statements
  claim, so `test/conftest.py`'s `check=True` bootstrap is still blind to the refusal. The repo's
  own `manage-contract.md` forbids a non-zero here, so **the plan was wrong, not the run** — the
  residue is a doc-correction, routed to `PLAN-CIS-054`.
- ✅ **D-c (`4-plan` spends 65.4% of its billing weight on cache creation)** — the mechanism was
  read and documented by `PLAN-CIS-042`. ⚠ Its **magnitude remains corpus-blocked**; it moves to
  `PLAN-CIS-057`.
- ⛔ **D-b (the merge gate's required-reviewer predicate) stays ROUTED to `review-apparatus` as
  `-011`. Not ours. Do not stage a CIS-side plan for it.**

### Live and unowned

- ⛔⛔ **D1 — `PLAN-CIS-006` surfaced a LIVE PRODUCTION BUG that is still live.** `execute-task`'s
  Bucket-B plan-id injection whitelist has **4 of 8 entries inert** (two misspelled, and further
  gated by a run-only subcommand check), so **silent-wrong-checkout risk exists today** for `ci` /
  `sonar` / `pr_doctor` calls made without `--plan-id`. This is not a measurement gap; it is a
  defect that can corrupt a running plan's state. **Routed to `PLAN-CIS-052`, and it is the single
  most urgent item in the corpus.**
- ⛔⛔ **D2 — `PLAN-CIS-044` did NOT close the merge-with-pending-findings hole.** The gate is now
  state-armed **only at completion** (`order: 1100`), long after the merge (`order: 70`), and its
  refusal is invisible at its one production caller. **A skipped or mis-parsed pre-merge findings
  check still lets a plan merge with pending findings.** Routed to `PLAN-CIS-052`.
- ⛔ **D3 — `PLAN-CIS-039` must be RE-SCOPED before it is re-emitted.** Its D1 rests on
  `exploration_doc_residency_bytes`, a one-integer-per-phase proxy that **cannot answer a
  per-document question**. Re-running it as written would measure the wrong thing with a clean
  conscience. Owned by `PLAN-CIS-056` D2.
- ⛔ **D4 — `PLAN-CIS-036` must NOT be resumed on its own residue text.** Its report says *nothing
  needs building*; the instrument does not exist. Owned by `PLAN-CIS-056` D1.
- ⛔ **D5 — F8 is NOT closed.** A mid-run inbox message still has no reader. `PLAN-CIS-043`'s D4
  shipped the guard **opt-in**, and the one stream that can carry plan-directed content is never
  told to use it. **Routed to `PLAN-CIS-052`, which must scope it explicitly** — it is not implied
  by that plan's other deliverables.
- ⛔ **D6 — two false-clean paths are live in the LSP edit verb** (`PLAN-CIS-048`): a CRLF rollback
  reports `rolled_back: true` while the restored bytes differ, and a malformed `documentChanges`
  entry is silently dropped so the whole-refusal gate never trips. Both routed to `PLAN-CIS-053`.
- ⛔ **D7 — the npm discoverer aborts whole-project discovery** on a malformed `package.json` at the
  root **or at any single workspace member** — the same blast radius as the Python defect
  `PLAN-CIS-048` rated high and fixed. Routed to `PLAN-CIS-049`, in one window with `PLAN-CIS-004`'s
  Poetry/setuptools gap, which is the same class.
- ⛔ **D8 — `PLAN-CIS-020`'s false `warning` fires on every ordinary clean run.** Three conditional
  rows report a content-loss warning on plans that lost no content. **A signal that fires on every
  run stops being read**, which degrades the instrument for everything else it reports. Routed to
  `PLAN-CIS-051`.
- ⛔ **D10 — NEW 2026-08-22, found by this ingest doing its own relocation: `compact`'s
  `relocated_pointer_reachable` invariant CANNOT FIRE on the failure it exists to catch.** The
  detector counts pointers matching `settled\.md[^"\n]*§\s*"(heading)"` — the heading must be in
  **double quotes** — and when that population is empty it returns `verdict: ok` with the evidence
  *"no settled-narrative relocation pointer to resolve"*. ⇒ **A relocation performed with
  non-conforming pointer syntax is silently unverified and reports as passing.** Reproduced here:
  831 lines were relocated to `settled.md` with unquoted pointers, and the invariant reported `ok`
  over a population of **0**. The pointers were then rewritten into the recognised grammar and the
  invariant now resolves 4 of 4.
  ⭐ **This is the epic's own signature archetype inside the orchestrator's own compaction stage** —
  a confident verdict over a population the instrument never examined — and it is the third recorded
  instance of a zero that does not say which zero it is. **The fix is the same one this epic keeps
  prescribing**: the empty-population branch must be `indeterminate`, not `ok`, whenever the
  `epic_changed` half of the same run shows narrative left the file. Routed to **PLAN-CIS-051**
  (`530`, detector-and-auditor integrity) — it is that plan's exact charter, and the surface
  (`plan-orchestrator/scripts/orchestrator.py`) is uncontended by the rest of the wave.

- ⛔⛔ **D11 — NEW 2026-08-22, and it silently disarmed the emission gate: the Expected-Surface
  parser is CASE-SENSITIVE, and a spec that misses the spelling contributes NO SURFACE AT ALL.**
  `EXPECTED_SURFACE_HEADING_RE` matches `^##[ \t]+Expected Surface$` exactly. **12 of 62 specs in
  this corpus — every one of the `5xx` wave and all three orchestrator-authored plans — used
  `## Expected surface`.** For those 12, `_expected_surface_paths` returned an empty set, so:
  `corpus cross-check` reported **zero overlaps** for all of them (a false clean over a population it
  never read), the Ordered Queue's Surface column rendered `(no expected surface)`, and — the part
  that matters — **`next`'s disjointness test would have admitted a colliding pair**, because two
  empty surfaces are trivially disjoint.
  ⭐ **Caught only because the zero was implausible**: `PLAN-CIS-050`, `051` and `053` all name
  `audit.py`, and the audit's own charter says they must not run concurrently against it — yet
  cross-check reported no overlap between them. After normalising the 12 headings the same command
  returns **69 overlap rows across the staged set**, including the `audit.py` contention the zero had
  hidden.
  ✅ **The corpus is fixed** (all 62 specs now use the parsed spelling). ⛔ **The parser is not.** A
  heading the tool cannot read must not resolve to *no surface* — it must resolve to
  `indeterminate`, and a spec with an unreadable surface must be **refused for emission**, never
  treated as disjoint. Routed to **PLAN-CIS-051** (`530`), which owns the detector-integrity
  charter, alongside D10.

- ✅ **D12 — RAISED AND NORMALIZED 2026-08-24; SUPERSEDED IN PART 2026-08-26. Read this correction
  before the record below.**

  ⚠⚠ **THE CLOUD PLAN LANE IS RETIRED (operator, 2026-08-26) and its function is incorporated into the
  orchestrators.** The `doc/plans/` tree no longer exists at all — `ls doc/plans/` returns *No such
  file or directory*. Two consequences for the record below, which is otherwise preserved verbatim as
  the account of what the 08-24 normalization did:
  - ⛔ **The bullet below claiming `.claude/skills/cloud-plan-lane/SKILL.md` and
    `doc/plans/cloud-bridge.md` are "both alive and git-tracked" is now HALF FALSE.** The skill file
    survives; `cloud-bridge.md` does not. **`PLAN-CIS-055` was therefore RETIRED on 2026-08-26**,
    reversing the "RE-SCOPED, not retired" disposition recorded below: its proposals targeted a lane
    contract that no longer exists, and its section verdict came back `contradicted` against HEAD
    `91a07aaa4`. The spec file is kept, per never-delete-a-spec.
  - ✅ **The lane-translation tables were re-normalized the same day.** Every `doc/plans/` path
    reference is removed from the six live wave specs; each now carries exactly ONE mention — the
    statement that the export tree no longer exists. The four *term* rows (run report, merge gate,
    `./pw`, sub-agent) are PRESERVED, because the bodies still use those terms and deleting the table
    would strand them.
  - ⛔ **The repository source was deliberately NOT touched** (operator-confirmed): the
    `cloud-plan-lane` and `author-cloud-plan` skills still need their `doc/plans` references. This
    removal was scoped to the orchestrator ledger alone.

  **The 2026-08-24 record, preserved:** All seven staged wave specs are repaired; the emission block
  this defect created is LIFTED. What was done, and what each run must still honour:
  - **A NORMATIVE lane-translation table now heads all 7 specs**, replacing the ingest's false blanket
    claim. It maps every surviving cloud-lane term to its plan-marshall meaning: run report → the
    plan's verification record + PR body; merge gate → phase-6-finalize's pre-merge barrier; `./pw` →
    the resolved `pyproject_build` executor call; `cloud-plan-lane § Step N` sub-agent →
    `execution-context-{level}`; `doc/plans/…` cited as evidence → the read-only archive at
    `cloud-runs/{plan}/`; "stage a successor plan" → file an epic inbox `finding`, because the
    ORCHESTRATOR stages plans.
  - **Every write-side `doc/plans/` Expected-Surface entry is gone.** Verified: no
    `- \`doc/plans/code-intelligence-substrate` bullet survives anywhere in `plans/`. The record
    corrections they encoded now route to the epic inbox and the PR body instead.
  - ⛔ **`cloud-runs/` is READ-ONLY and that is now stated in every affected spec.** It is the evidence
    the corrections are *about*; editing it destroys what is being corrected.
  - **`PLAN-CIS-055` was RE-SCOPED, not retired** — its substance survives because proposals P1–P8
    target `.claude/skills/cloud-plan-lane/SKILL.md` and `doc/plans/cloud-bridge.md`, **both alive and
    git-tracked** (verified). Its one repository deliverable is now
    `doc/plans/cloud-lane-contract-proposals.md`; `record-corrections.md`, `{this-plan}/plan.md` and
    `report-NN.md` are struck.
  - ⛔⛔ **A VACUOUS-PASS TRAP WAS FOUND AND DISARMED IN `PLAN-CIS-054` D6.** Its gating derivation said
    *"if the epic directory is absent entirely, D6 is closed as not-applicable on that evidence
    alone"* — and the ingest had made it absent. As written, D6 would have closed over forty-odd
    unexamined defects and reported a clean discharge. The derivation now lists `cloud-runs/` instead,
    so `discharged-by-collection` is reachable only for a plan genuinely missing from the archive.
    ⭐ **This is F10 recurring in the deliverable built to correct records** — the archetype found by
    normalizing, not by running.
  - **Four direct `./pw` invocations replaced** (049, 050×2, 052) with the resolved executor command
    plus the ⛔ read-the-TOON-status warning; **two `cloud-plan-lane § Step 6` dispatches** (049, 054)
    became `execution-context-{level}`, with the cold-read property restated because that is what made
    those verifications worth anything.
  - **`PLAN-CIS-053`'s gap-citation note carried a claim that had become false in BOTH directions** —
    it said the cited files were "git-tracked and on `main` today" and might be "gone by the time this
    runs". Neither holds: they are not on `main`, and they are not gone. Corrected to name the archive,
    and a failed citation is now a reportable anomaly rather than the expected outcome.
  - ✅ **Verified after the edits**: `corpus enumerate` 63/63 both directions, 0 unreadable;
    `cross-check` parses all 63 specs and all 7 normalized specs still contribute surface rows
    (049:18, 050:24, 051:13, 052:30, 053:13, 054:2, 055:8 of 273) — so no spec was silently emptied,
    which would have re-armed D11's false-clean. ⚠ A first count of `0` here was **my own grep
    pattern error** (the field is `file_overlap_match_count`; rows are keyed by spec FILENAME, not
    plan id), not a real zero — recorded because that is precisely the mistake D11 punishes.
  - ⚠ **Scope, per operator**: staged/open plans only. The two PARKED specs (`036`, `039`) carry no
    cloud-lane markers, and the only other corpus hit (`046`) is shipped — neither was touched.

  ⛔ **Residual, deliberately NOT mechanized**: ~89 descriptive "run report" mentions remain in the
  bodies. They are governed by the header table rather than rewritten one by one, because most are
  citations of what a past run said rather than obligations on this one. **Each run must read the
  table before its `Done when` clauses.**

  <details><summary>Original D12 finding, as raised (retained — it is the evidence the repair answers)</summary>

  **The 5xx wave specs were only PARTIALLY transformed out of the cloud lane, and four of them declare
  an Expected Surface that no longer exists.** The ingest
  removed the `Skill: cloud-plan-lane` FIRST INSTRUCTION block from all seven wave specs and stated so
  in a uniform `ORCHESTRATOR PROVENANCE` header — that part is done, uniformly, and verified present on
  all 7. ⛔ **But the header then declares the body kept "verbatim as exported", asserting that its
  references to a run report, a merge gate, or `cloud-bridge.md` are "lane-relative and satisfied by the
  corresponding plan-marshall phase artifacts". That assertion is UNTESTED, and for one class of
  reference it is FALSE.**
  - **The `doc/plans/` targets are not lane-relative — they are gone.** This same ingest deleted
    `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/` from git (163 deletions, PR #1331, now merged). Verified
    2026-08-24: `git ls-files doc/plans/code-intelligence-substrate` returns empty and the directory is
    absent from the worktree. Four specs still declare it as **Expected Surface**, i.e. as files they
    will write: `PLAN-CIS-050` (`.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/**` — "the record corrections and
    the new successor plan file"), `PLAN-CIS-053` (four `report-01.md` coverage claims),
    `PLAN-CIS-054` (D6), and `PLAN-CIS-049` (one `plan.md`, hedged "if present"). No plan-marshall phase
    artifact satisfies a write to a deleted path.
  - **`PLAN-CIS-055` is the worst case and may not be emittable at all.** Its ENTIRE deliverable set
    (D1–D4 plus the run report) writes into `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/{this-plan}/`,
    including a literal `report-NN.md`. It is a plan *about* the cloud-lane contract whose every output
    is a cloud-lane artifact. Re-scope or retire — do not emit as written.
  - **89 `run report` references across the 7 specs** (049:9, 050:16, 051:6, 052:6, 053:16, 054:21,
    055:15), many inside `*Done when:*` clauses of the form *"the run report carries …"*. The
    plan-marshall lane has no `report-NN.md`; the nearest equivalents are the retrospective artifact,
    the PR body, and the findings ledger. ⛔ A `Done when` clause naming a non-existent artifact is
    **unverifiable as written** — it will either be silently reinterpreted at verification or pass
    vacuously, which is this epic's own signature archetype.
  - **Four direct `./pw` invocations survive** (049:1, 050:2, 052:1), one of them explicitly *"per
    `cloud-plan-lane`'s conditional gate"*. The local hard rule requires resolving build commands via
    `architecture resolve`. Two specs also instruct dispatch *"per `cloud-plan-lane` § Step 6"*.
  - ✅ **Not affected**: `PLAN-CIS-056`, `-057`, `-058`, `-059` (authored locally 2026-08-22). Their only
    cloud-lane mentions are descriptive or explicit out-of-scope declarations.

  ⇒ **This is an emission precondition, not a post-hoc cleanup.** The four `doc/plans/` Expected-Surface
  declarations also feed `next`'s disjointness test and `corpus cross-check`, so they contaminate the
  surface algebra as well as the deliverables. ⛔ **Do not emit `PLAN-CIS-050`, `-053`, `-054` or `-055`
  until their surfaces and `Done when` clauses are re-expressed in plan-marshall terms.** `PLAN-CIS-049`
  needs the same treatment but its one hedged reference is lower risk. **`PLAN-CIS-052` and `-051` are
  the least affected of the wave** — neither declares a `doc/plans/` surface — which leaves the
  recommended first pair (`059` + `052`) intact.

  ✅ **This emission block was DISCHARGED the same day by the normalization recorded above.** All
  eleven staged rows are emittable on this axis.

  </details>

- ✅ **D13 — RESOLVED 2026-08-26 by `PLAN-CIS-060` (PR #1355). Read this closure first; the history
  below is kept because its refuted hypotheses are the record of what NOT to re-derive.**

  ⭐⭐ **Both arms are discharged, and this ledger is the evidence.** Re-derived first-party at HEAD
  `91a07aaa4`: `corpus verdicts --slug code-intelligence-substrate` now reports
  `unreadable_claim_section_count: 7` and **`blocking_count: 7`**, against `blocking_count: 0` on the
  same corpus one day earlier. The READ arm blocks (an unreadable section is a distinguishable parse
  state contributing a blocking row, not a vacuous pass); the WRITE arm has an address
  (`corpus set-verdict --section-scope` repairs a blocked spec **in one call without re-authoring its
  claim prose**), which is the recovery path UPDATE 2 established was missing.
  ⛔⛔ **CONSEQUENCE, AND IT IS LARGE: the seven blocked specs are the first SEVEN rows in staged
  order** — CIS-051, 052, 049, 050, 053, 055, 054. The prep-ready gate now correctly refuses all of
  them, so the emittable head of the queue jumps to **CIS-056**. **This is the fix working, not a
  regression**: work whose premises were never checked is now visibly unemittable instead of invisibly
  admitted. ⛔ **None was repaired — deliberately.** Repair is re-grounding work; it belongs to a
  `cleanup` pass or an operator decision, never to a landing analysis.
  ⭐ Authoring forms of our seven: **prose-only 6** (CIS-049/050/051/052/053/054), **table-form 1**
  (CIS-055). The prose-only form was invisible to this ledger until `truthful-signals` named it.
  ⭐⭐ **The blast-radius sweep is population-derived, not sampled**: 331 specs across all 9 epic
  slugs, partition `absent 104 / empty 0 / unreadable 26 / parsed 201` **summing exactly to 331**.
  This epic's stated expectation of 7 is **CONFIRMED**. Corpus-wide forms: table-form 7, prose-only 19,
  template-placeholder **0**, fenced-only-body **0** — ⭐ both zeros derived from a content sweep over
  5 246 files, not merely unobserved.
  ⛔ **CROSS-EPIC OBLIGATION, NOW OWED THE OTHER WAY**: `truthful-signals`' numerator of **19 is
  CONFIRMED and twice-observed**, but its **DENOMINATOR is REFUTED — 161 heading-carrying specs, not
  the 124 its spec states.** Their ratio changes; their finding survives. Tell them.

  **The history, kept for its refuted hypotheses:**

- ⛔⛔ **D13 — RAISED 2026-08-24, HALF-FIXED UPSTREAM THE SAME DAY. Read the updates
  newest-first, before the original.**

  ⚠⚠⚠ **UPDATE 2, 2026-08-25 (inbox drain of `truthful-signals-051.md`) — THE VACUITY IS
  BIDIRECTIONAL, AND THIS ENTRY'S REMEDY WAS ONE ARM SHORT.**

  ⭐⭐ **`corpus set-verdict` addresses claims BY INDEX, so on a spec the parser reads as zero-claim,
  EVERY index is out of range and the re-grounding verdict field is structurally UNWRITABLE.**
  ⭐ **CORROBORATED FIRST-PARTY at HEAD `1169fb5bf`**, not carried from the paste — the non-writing
  probe on our own corpus returns:
  ```text
  corpus set-verdict --plan PLAN-CIS-051 --claim-index 9999 …
    → error: claim_index_out_of_range   claims_total: 0
  ```
  ⛔ **Consequence for the remedy this entry already records.** Resolving an unreadable claim section to
  `indeterminate` fixes the READ side and, alone, makes the seven **permanently unemittable** rather
  than correctly blocked: a spec that can never be *stamped* can never be re-grounded **out of**
  `indeterminate`. ⇒ **`PLAN-CIS-051` needs a RECOVERY path, not only a refusal path.** A detector that
  fails closed on an input no producer can repair converts a silent-pass into a permanent deadlock —
  a different defect, not the absence of one.
  ⭐ **A THIRD failure form this entry never named: PROSE-ONLY.** `truthful-signals` measured their own
  159-spec corpus at `91bbe7470`: **19 of the 124 specs carrying a `Claim Labels` heading parse to
  zero — 13 table-form and 6 prose-only** (a blanket "everything is HYPOTHESIS unless marked"
  paragraph with no bullets at all). Our seven are all table-form, so prose-only is a form our own
  population could not have revealed. ⚠ Their 19/124 figure is **their** first-party measurement and is
  NOT re-derived here — a lead. The bidirectional-unwritability claim above IS re-derived here.
  ⭐ **Correction to UPDATE 1 below**: `#1338` applied `re.IGNORECASE` to **BOTH** addressed headings —
  `CLAIM_LABELS_HEADING_RE` *and* `EXPECTED_SURFACE_HEADING_RE`, in the same hunk. The diff quoted below
  shows one line and the fix is one line wider. The conclusion is unaffected.
  ✅ **The "Cross-epic obligation, OWED" recorded in UPDATE 1 is DISCHARGED.** They were told, they
  re-probed, and they confirm our framing that `#1338` closed the gate that was not binding. ⛔ They
  are deliberately **not** normalizing their claim tables into bullets — they call that a treadmill
  that would make their gate report green while staying blind to the next authoring shape. Their
  standing rule until `-051` lands: **a prep-ready PASS on any of the nineteen is treated as
  `indeterminate`, never as READY**, and the emit that follows says so out loud. ⭐ Adopt the same rule
  here for our seven.

  ⚠⚠ **UPDATE 1, 2026-08-24 second `cleanup` pass: `#1338` FIXED GATE 1 AND LEFT GATE 2 UNTOUCHED — so
  this defect reads as resolved and is not.** `orchestrator-inbox-and-landing-residue` landed as
  `77db1a0d3` / PR **#1338** carrying exactly one line of the fix:
  ```diff
  -CLAIM_LABELS_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Claim Labels(?:[ \t]+#+)?[ \t]*$')
  +CLAIM_LABELS_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Claim Labels(?:[ \t]+#+)?[ \t]*$', re.IGNORECASE)
  ```
  ⛔ **Re-probed at the new HEAD: `PLAN-CIS-049` still returns `claims_total: 0`.** The heading gate is
  now case-insensitive and it changes NOTHING here — because the seven had already been heading-normalized
  by the first pass, and **their binding blocker was always gate 2: claims expressed as a TABLE.**
  ⭐⭐ **The upstream fix addressed the gate that was NOT binding for this corpus.** That is exactly why
  the two-gate model was worth pinning rather than accepting the single-cause framing inbox `-048`
  arrived with: a reader who takes `#1338` as closing D13 will conclude seven specs are re-groundable
  when none of them is. **The vacuous prep-ready pass is UNCHANGED.**
  ⇒ **`PLAN-CIS-051` still owns this**, and its scope narrows to the real remedy: a claim section the
  parser cannot read as claims must resolve to `indeterminate`, never to *zero claims* — whether the
  cause is the heading, the bullet form, or anything later.
  ⇒ **Cross-epic obligation, OWED**: `truthful-signals` reported this as a heading defect (`-048`) and
  the landed fix matches that framing. They should be told gate 2 exists, or their side will believe a
  half-fix is whole.

  **The original finding, as raised — its gate-2 half is unchanged and still governs:**

  **THE RE-GROUNDING VERDICT FIELD CANNOT BE WRITTEN
  ON ANY OF THE SEVEN STAGED WAVE SPECS, AND `next`'s PREP-READY TEST PASSES THEM VACUOUSLY.**
  `corpus set-verdict` parses **`claims_total: 0`** for all seven — verified one probe per spec, 7/7,
  population-derived rather than sampled — while those specs carry **154 tabulated claims**
  (049:34, 050:26, 051:35, 052:22, 053:10, 054:14, 055:13).
  - **Matched control**: `PLAN-CIS-002` → `claims_total: 7`; `PLAN-CIS-049` → `0`. The four
    locally-authored staged specs parse fine (056:7, 057:6, 058:6, 059:8), so the parser is not
    globally broken — it is blind to exactly one authoring form.
  - **The discriminator is claim FORM, not heading and not section.** The seven express claims as a
    markdown **table** (`| Claim | Label | Confirm/refute artifact |`); every spec the parser can read
    uses **bullets**. ⛔ Two hypotheses were tested and BOTH FAILED, recorded so nobody re-derives
    them: (a) *heading case alone* — the seven used `## Claim labels` against the template's
    `## Claim Labels`; **normalizing all seven changed `claims_scanned` not at all (281 → 281)** and
    left every one of them at `claims_total: 0`, so the case was a real template divergence but NOT
    sufficient on its own; (b) *"the parser is not section-scoped"* — ⛔ **THIS SUB-CLAIM WAS WRONG
    AND IS RETRACTED 2026-08-24, same session.** It rested on "`PLAN-CIS-059` has no
    `## Claim Labels` section at all", which is FALSE — 059 carries one at line 87. The inventory that
    produced that reading searched for the LOWERCASE `## Claim labels` and so missed the correctly-cased
    heading. ⭐ **The refutation was itself an instance of the defect it was investigating** — a
    case-sensitive scan reporting a real section as absent. Recorded rather than quietly fixed,
    because a retracted premise left standing is how the next reader re-derives the wrong model.
  - ⭐ **The model that survives all four probes**, stated as the current best reading and not as a
    pinned grammar: the parser locates `## Claim Labels` (**exact case**) and counts **bullet-form**
    claims inside it. `049` after the heading fix → section found, contents are a TABLE, **0 bullets
    → 0 claims**; `059` → 8 bullets → 8; `002` → 7. It also explains why `claims_scanned` held at 281
    across the heading normalization: the seven contribute zero under either spelling, because the
    blocker is the table, not the heading.
  - ✅ **GRAMMAR NOW PINNED — 2026-08-24, first-party, superseding this entry's earlier "not pinned"
    statement.** Independently reported by `truthful-signals` (inbox `-048`, drained same day) and
    then read directly in `orchestrator.py`. **There are TWO sequential gates, and the seven fail
    BOTH** — which is exactly why normalizing the heading changed nothing:
    1. **`orchestrator.py:389`** — `CLAIM_LABELS_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Claim Labels(?:[ \t]+#+)?[ \t]*$')`.
       Case-exact. `_parse_claims` then does **`if start < 0: return []`** — an absent or
       differently-cased section yields zero claims **silently, with no error and no warning**.
    2. **`_parse_claims` (`:1209`)** — *"A claim is a TOP-LEVEL `- ` bullet inside the section."*
       So a section whose claims are a markdown **TABLE** parses to zero even when gate 1 passes.
    ⇒ The seven had `## Claim labels` (gate 1) **and** table-form claims (gate 2). This pass fixed
    gate 1 only, so they still read zero — the fix and the non-fix are now both explained.
    ⭐ The earlier bullet-count reconciliation failure (287 / 246 vs 281) is also explained: the rule
    is TOP-LEVEL bullets with fenced regions masked, narrower than either count.
  - ⭐⭐ **INDEPENDENTLY CONFIRMED, and the convergence is the point.** `truthful-signals` found the
    identical defect on its own corpus the same day, by its own `cleanup` Step 5 — *"we found it
    because HALF OUR OWN live corpus had it, including every spec we authored that day."* Two epics,
    two independent discovery paths, one root cause. Their message names the same seven CIS specs and
    the same consequence — **the admission gate returns READY for a spec it could not read.**
    ⭐ Their added observation, worth keeping: the asymmetry is why it survived so long — **`corpus
    enumerate`, `compact` and `corpus cross-check` are all green because NONE of them reads Claim
    Labels.** The surface arm is healthy; only the claim arm is blind.
  - ⇒ **Two consequences, and the second is the dangerous one.** (1) `cleanup`'s A1 persistence half
    is structurally impossible for the seven, so their re-grounding cannot be recorded even when
    performed. (2) **`next` admits a candidate *iff no row carries `admits: false`* — and a spec with
    zero parsed claims has NO rows, so it passes prep-ready vacuously.** All seven currently read as
    prepared while nothing about them has been checked. This is D11's archetype a THIRD time, on the
    admission gate, in the orchestrator's own instruments.
  - **Routed to `PLAN-CIS-051`** (detector-and-auditor-integrity), which already owns D10 and D11 —
    same charter, and D11's own remedy language applies verbatim: a claim form the tool cannot read
    must resolve to `indeterminate`, never to *no claims*, and a spec whose claims are unreadable must
    be **refused for emission**, never treated as prepared.
  - ✅ **Applied this pass**: the seven headings normalized to the template's `## Claim Labels`. That
    is template conformance and nothing more — ⛔ **it did NOT fix the parse**, and recording it as a
    fix would be the false-green this defect is about.
  - ✅ **RE-GROUNDING CAMPAIGN RUN 2026-08-24 (operator-directed) over the addressable half.** All
    **27** claims of the four locally-authored staged specs are corroborated against HEAD
    `b95d78437` and persisted: **22 corroborated, 2 contradicted, 3 unverifiable**, `count: 27`,
    `blocking_count: 0`, `unreadable_count: 0`.
    | Spec | Claims | corroborated | contradicted | unverifiable |
    |---|---|---|---|---|
    | `PLAN-CIS-056` | 7 | 7 | 0 | 0 |
    | `PLAN-CIS-057` | 6 | 4 | 1 | 1 |
    | `PLAN-CIS-058` | 6 | 3 | 0 | 3 |
    | `PLAN-CIS-059` | 8 | 7 | 1 | 0 |
    ⭐ **`blocking_count: 0` with two refutations present is the CORRECT reading, not a miss**: both
    were stamped `rescoped: yes` and both re-scopes were APPLIED, so the refutations are absorbed.
    An unabsorbed one would block.
    - **`CIS-059` claim 6 → contradicted, re-scope applied**: `doc/concepts/code-intelligence.adoc`
      does NOT need correction — its resolver section argues lifecycle and never names the owning
      bundle. The Expected Surface entry is **struck, not re-edited**, per the spec's own clause.
    - **`CIS-057` claim 4 → contradicted, re-scope applied**: `PLAN-CIS-050` has NOT landed (staged,
      no PR), so the spec's pre-authorised branch fires and D1/D2 report AROUND the fabricated-zero
      and rounding defects. Recorded in its Deliverables preamble so outline does not re-decide it.
    - ⭐ **`CIS-059`'s central risk is settled FAVOURABLY**: activation keys on the resolver **id**
      (`_cmd_client_query.py:1006-1010`) and `producers[]` stamps ids (`:880-883`), so the fold is
      behaviour-neutral provided `derivation_resolver_id()` keeps returning `'lsp'`.
    - ⭐ **Both gating population risks clear**: 13 archived plans carry the exploration field set,
      so `CIS-056` and `CIS-057` are materially off n=1 on *existence*. ⛔ Sufficiency for any given
      figure stays each plan's D0 call — the verdicts say so explicitly.
    - ⛔ **Three `unverifiable` are honest abstentions, not failures** — two asserted absences and
      one August-2026 count that would need re-measuring, not reading. `unverifiable` never blocks.
    - ⛔ **HEAD-SCOPED, and D14 is the trigger**: `CIS-056` claim 6 and `CIS-057` claim 5 both assert
      *nothing has been built/closed since 2026-08-22*, verified against `main` only. Four live plans
      sit at `6-finalize` in worktrees on adjacent surfaces. **Re-check those two claims after they
      land** — the verdicts carry `checked_at` for exactly that comparison.

- ⚠ **D14 — NEW 2026-08-24 (`cleanup` Phase A4): six LIVE plans are at or near finalize on surfaces
  the staged queue declares, so staged premises are about to go stale.** `manage-status list` shows
  `metrics-ledger-readers-and-timestamp-provenance`, `orchestrator-inbox-and-landing-residue`,
  `build-gates-test-suite-confidence-ci-workflow-lint` and `plugin-doctor-detector-coverage-residue`
  at **`6-finalize` in worktrees**, `finalize-step-contract-guard-residue` at `6-finalize`, and
  `a-refusal-nobody-recognises-is-filed-as-a-finding` at `4-plan`.
  ⭐ **The sharpest pair**: `PLAN-CIS-056` declares the **identical four-file set** as the live
  `metrics-ledger-readers-and-timestamp-provenance` (`audit.py`, `manage-metrics.py`,
  `data-format.md`, `analyze-logs.py`). `PLAN-CIS-050` declares the same four.
  ⛔ **NOT superseded, and the reason is not caution but evidence**: a shared surface is not duplicate
  work, and nothing checked whether that live plan covers CIS-056's actual deliverable (the
  exploration-split aggregator) or merely edits the same files. Superseding on surface overlap alone
  would retire a spec against an unread plan. **Re-ground CIS-050 and CIS-056 against HEAD *after*
  those plans land** — this is the concrete trigger for the A1 pass that D13 currently blocks.

- ⚠ **D15 — NEW 2026-08-24, found by the inbox drain doing its own work: the orchestrator has NO
  add-a-row verb, so a `Stage` disposition costs a hand-rewrite of the whole queue.** `orchestrator.py
  queue` offers `--transition` (status only) and `--set-row` (one whitelisted result field of an
  existing row). Adding a row requires
  `manage-status update-field --field plans --value {entire 64-row JSON array}`, per
  `decompose.md` Step 5 — the only documented path.
  ⇒ **The drain's `Stage` disposition is therefore the most expensive and the most dangerous of the
  four**, because composing that array by hand means retyping 63 correct rows to add one, against a
  ledger whose own standing rule is that queue order and counts are read from `plans[]` and never from
  prose. ⭐ **This is not hypothetical — it changed a disposition on this very drain**: inbox `-043`
  was folded into `PLAN-CIS-050` as a 7th deliverable (with a recorded scope-bloat rationale) partly
  because staging it as `PLAN-CIS-060` would have required that rewrite. **A tooling gap that bends
  dispositions is worth more than the one message it bent.**
  *Wanted:* a `queue --add-row` verb taking `--plan/--slug/--workstream`, appending at a named position
  inside the same read-modify-write critical section `--set-row` already uses. Until then, a `Stage`
  disposition should be surfaced to the operator rather than performed silently.

- ⛔ **D16 — NEW 2026-08-25, found by this drain doing its own slot arithmetic: `next`'s in-flight
  count `R` reads ONLY the `launched` status, so a plan at `running` is INVISIBLE to it and the verb
  will emit into an occupied slot.**
  `orchestrate.md` § Step 4 says verbatim: *"Count `R`, the plans currently in `launched` status, and
  select up to `N − R` candidates."* But `launched` and `running` are **distinct** statuses — the
  emit≠running invariant exists precisely to keep them apart, and `queue --transition … --status
  running` is the operator-confirmed started state. A plan that has actually STARTED therefore leaves
  the `launched` population, and a literal reading of Step 4 computes `R = 0` while a plan is running.
  ⛔ **At `parallelization_scope = 1` this is not cosmetic: it takes the epic from zero free slots to
  one, and emits a second plan on top of a running one.** The bug is masked whenever a row is left at
  `launched` and only bites once the `running` transition is actually recorded — which this epic began
  doing on 2026-08-25, so it is live now rather than latent.
  ⭐ **Applied here as the safe reading, not the literal one**: `R` was counted as **1** (PLAN-CIS-059,
  `running`) and this drain's proactive emit reported **zero slots and emitted nothing**. A future
  session must not "correct" that to `R = 0` on the strength of the doc's wording.
  *Wanted:* Step 4's `R` defined over the in-flight set (`launched` ∪ `running`), not over `launched`
  alone — and a test that pins a `running` row as slot-occupying. ⚠ **NOT yet routed to a spec.** It is
  orchestrator-workflow surface, so it is adjacent to `PLAN-CIS-060` but is NOT in its scope; decide
  the owner before the next emit.

- ⚠ **D9 — `PLAN-CIS-026` is shipped but non-functional for its primary target.** The lsp derivation
  resolver derives **zero module edges** on the marketplace corpus, for a ~60-85 s crawl, because
  pyright cannot follow the executor's synthesized `sys.path` for cross-bundle imports. The ledger
  records this explicitly because `PARTIALLY REFUTED` alone under-states it for planning.

- ⛔⛔ **D17 — NEW 2026-08-31, from the PLAN-CIS-051 / PR #1370 landing: THE REQUIRED-BOT QUORUM
  CLEARS ON A REVIEWER THAT DID NOT PARTICIPATE.** `.plan/marshal.json` sets
  `required_bots = "pr-agent"`, `optional_bots = "coderabbit,sourcery"`. On PR #1370 `pr-agent`
  left **no observable trace at all** — `ci pr reviews --pr-number 1370` returns 47 reviews from
  exactly three distinct users (`coderabbitai` 24, `cuioss-oliver` 22, `sourcery-ai` 1) and
  `ci pr comments` returns 81 comments with **zero** `pr-agent` occurrences. The plan's
  `automatic-review` step nonetheless reported the required-bot quorum satisfied in three
  successive rounds.
  ⭐ **The landing narrated this as a bot that "satisfied the quorum every time while corroborating
  nothing". The record supports something sharper: it did not respond weakly, it did not
  participate, and the gate passed anyway.** A quorum clearing on zero observable participation is
  measuring its own configuration rather than any review — this epic's theme, sitting in the gate
  that admits a PR to merge.
  ⛔ **This is NOT the known in-place-edit behaviour.** An in-place re-review edit leaves the comment
  PRESENT with a later `updated_at`; here there is no comment to edit. Absence, not staleness.
  ⚠ Two readings remain open and only one has been excluded: (a) `pr-agent` posts under a handle
  neither verb surfaces — not excluded, though both verbs agree; (b) it posted nothing and the
  step's completion signal came from somewhere other than PR participation. Memory's standing rule
  — *only `ci pr comments` is evidence of participation* — makes (b) the operative reading.
  **ROUTED OUT to the `review-apparatus` epic** under the standing three-way rule (the PR/review
  test runs first and wins outright). ⚠ **The delegating message has NOT yet been filed** — this
  entry is the measurement, not the transfer; an offer is not a transfer.

- ⛔ **D18 — NEW 2026-08-31: PLAN-CIS-051's REALIZED surface exceeded its DECLARED surface at four
  paths.** `## Expected Surface` declared none of
  `plan-marshall/skills/script-shared/scripts/argparse_surface.py` (+63),
  `manage-execution-manifest/scripts/_manifest_core.py` (+35),
  `manage-execution-manifest/scripts/_decision_line_shapes.py` (+23), or
  `plan-retrospective/references/logging-gap-analysis.md` (+64) — the spec named
  `manage-execution-manifest.py` **"emitter only"**. The merge commit changes **63** files while the
  landing's own `files_modified` fact reads **54**, a nine-file under-count consistent with the
  plan's self-reported `references.affected_files` under-recording (it names at least seven
  occasions, and three consecutive deliverables under-declared: D3 7→11, D4 10→13, D5 8→12).
  ⭐ **Recorded as evidence for the next disjointness pairing, per `analyze.md` Step 4 item 5**: a
  declaration this far behind its realized footprint is what makes the gate mis-predict. The spec is
  shipped, so there is no live declaration left to correct — the correction belongs to whatever
  spec inherits the surface.

- ⛔ **D19 — NEW 2026-08-31: two figures in the PLAN-CIS-051 report are not what they look like, and
  BOTH are corroborated first-hand.**
  **(a) The 6-finalize token cell absorbs both loop-back execute passes.** `work/metrics.toon`
  carries `close_count: 1` and `value_scope=single_close` for 5-execute, and `re_entered_phases` is
  EMPTY, while status metadata records `loop_back_iteration=2` and a 6-finalize→5-execute re-entry
  at `2026-08-30T20:44:38Z`. So `3,804,957` is **not** finalize cost.
  ⭐⭐ **This is the retired-per-phase-figure archetype in a SHARPER form.** Previously such figures
  were *unrepresentable*; PLAN-TRUTH-055 made re-entered phases representable — and here the
  representation EXISTS and **the producer never writes it**. Representable-but-never-written is a
  different defect from unrepresentable, and the ledger must not collapse them.
  **(b) 4.46M tokens are named by no record-step row**, so the execution-log total covers ~37% of
  the spend it summarises; inbox `-008.md` reports the two ledgers' union exceeds either by 12 rows.
  ⚠ Both ride inbox messages `-004.md` and `-008.md` and are **owed a fold into
  `PLAN-CIS-050-measurement-and-cost-integrity` at the next drain** — not yet folded.

- ⛔⛔ **D20 — NEW 2026-08-31, SELF-CAUGHT DURING THE DRAIN THAT CAUSED IT: a `###` sub-heading
  inside `## Expected Surface` SILENTLY TRUNCATES the section for `epic_spec_parser`.** This drain's
  first fold pass appended each spec's new surface under a
  `### Added by the 2026-08-31 inbox drain` sub-heading placed inside the section. Every one of the
  17 added entries parsed as **absent**: `corpus surfaces` reported CIS-052 at 24 resolved entries
  and CIS-050 at 29, with none of the added paths present. Demoting the five sub-headings to bold
  text — the only change — took CIS-052 to **32**, CIS-050 to **35**, CIS-053 to **27** and CIS-054
  to **16**, and every added path then resolved.
  ⭐⭐ **This is the same-act obligation defeating itself.** The fold DID update the declaration in the
  same edit, exactly as `analyze.md` § "A fold that adds scope updates the declared surface in the
  same act" requires — and the disjointness gate would still have read the OLD surface, because the
  parser could not see the new entries. A declaration the parser cannot read is not a declaration.
  ⭐ **Only `corpus surfaces` caught it.** The narrative said the surface was updated; the file said
  so too; the parser disagreed. This is the concrete case for `analyze.md`'s *"Verify rather than
  assume — the spec's new declaration is readable from the parser, not from the edit"*, and it is now
  a first-party instance rather than a precaution.
  *Wanted:* either the parser reads through sub-headings inside the section, or authoring rejects one.
  ⚠ **NOT yet routed to a spec.** `epic_spec_parser` lives in `plan-marshall:script-shared`;
  `PLAN-CIS-049` owns query truthfulness but not this reader. Decide the owner before the next fold.

### 2026-09-15 Cleanup — Phases A–D, and the pin gate the verdict cannot see

Run after the `PLAN-CIS-049` landing and its 71-message drain, on the operator's instruction to clean
up and prepare a restart.

**Operator decision carried into this pass: the twelve-deliverable figure is NOT a hard limit — up to
fourteen is acceptable.** It is guidance, not a gate, and it supersedes the ceiling character of the
2026-09-12 directive. One consequence was applied immediately: `PLAN-CIS-050`'s D12 note reading
*"nothing further folds in here"* was true of a ceiling of twelve and is false of the new rule; it is
corrected in place to state the headroom **and** the counter-evidence, because promoted lesson
`2026-09-15-08-003` reports the twelve-deliverable `PLAN-CIS-049` running **5.2× over its anchor**.
⛔ Headroom is not a licence: a thirteenth or fourteenth fold is a decision recorded with that trade
named, not a slot to be filled.

**Phase A.** `corpus enumerate`: 65 rows / 65 specs, **0 rows without a spec, 0 specs without a row, 0
unreadable** — the corpus reconciles in both directions.

**A1 re-grounding — done against a DERIVED exposure set, not spec by spec.** 334 files changed between
the previous stamp `53ab7dd2e` and HEAD `7a028157e`. Each staged spec's declared surface was intersected
with that set, and the re-derivation targeted the intersection. The scope is stated in each verdict:
claims on untouched files retain their previous verdicts and were **not** re-executed. This is a bounded
pass and says so.

| Spec | Declared entries touched | Outcome |
|---|---|---|
| `PLAN-CIS-052` | **13 of 37** — the heaviest, incl. `pre-submission-self-review.md` and `phase-6-finalize/SKILL.md`, both moved by #1488 | Row 17 **re-confirmed live on a file that moved** |
| `PLAN-CIS-050` | **8 of 38** — `audit.py` (twice), `generate_executor.py`, `manage-execution-manifest.py`, two SKILL.mds, and D12's two new standards | D1(e) corroborated; D5(a) **corrected**; the rounding split re-framed |
| `PLAN-CIS-054` | **2 of 12** — and the low number is *misleading*, see below | No claim moved; new work arrives from the landing instead |

⭐ **`PLAN-CIS-052` row 17 is the pass's clearest yield.** `phase-6-finalize/SKILL.md` item 5c (`:1096`)
still gates the boundary-row write on the step having *did NOT time out*, while the cause table at
`:1105` still defines `blocked_session_restart` to **include** the per-agent timeout budget firing. So a
timed-out finalize step still writes no boundary row at all, and the two statements still contradict
each other inside one document — re-derived on a file that actually moved, which is what makes this a
re-grounding rather than a re-read.

⛔ **`PLAN-CIS-050` D1(e) was nearly mis-refuted, and the near-miss is the lesson.** `generate_executor.py`
gained a normative emission-contract docstring in this window, and reading it as the fix would have
struck a live defect: that contract governs `format_surface_stats_line` — the greppable stdout **line** —
while the dry-run early return still hands back `dict(_EMPTY_SURFACE_STATS)` verbatim with
`scripts_registered: 0`, where the sibling OSError path sets it to `len(mappings)`. ⭐ Same shape as the
2026-09-12 D3(a) near-miss: **a refutation that names a NEARBY mechanism is not a refutation of the
claim.** Twice in four days.

⛔ **`PLAN-CIS-050` D5(a)'s population was UNDERSTATED and is corrected in place.** The item said *"bump
four `CHECK_ERA` stamps"*. Derived from the dict rather than re-asserted: **24 entries, of which EIGHT
carry the literal `plan-10`** instead of a commit or PR boundary. A stamp reading `plan-10` is not a
boundary a cross-run diff can order against. The item now covers that set plus the Plan-290 four, and
forbids carrying 4, 8 or 24 forward without re-derivation.

⛔ **`PLAN-CIS-054`'s "2 of 12" is the wrong instrument and the verdict says so.** Its surface is
dominated by **globs** (`skills/*/SKILL.md`, `.../standards/*.md`, `doc/user/`, `doc/concepts/`,
`doc/adr/`), so a per-entry exposure count counts globs, not files — dozens of documents under those
globs moved. Reading 2/12 as low risk would be the count-without-its-population error this very plan
exists to correct.

**A2 applicability** — no staged spec qualifies as already-fixed. The rule requires a **positive
account** (the commit, PR, or symbol that now carries the behaviour), and none of the three has one;
two had their defects re-confirmed live this pass. **A3 ambiguity** — all three carry an Objective, an
Expected Surface and a claim section; all three parse `declarative` with `admits_disjointness_check:
true`. **A4 duplication** — `corpus cross-check` over 10 sibling epics and the live plan set:
`source_origin_match_count: 0`. **A5 distribution** — no regrouping applied, and that is a judgement
rather than a skip: the corpus was regrouped by component three days ago, the raised ceiling adds
headroom rather than a reason to re-cut, and churning three specs again days later would cost their
freshly-stamped verdicts for nothing.

**Phase B compaction** — `epic_changed: false`, `regenerated_count: 0`. Idempotent: the derivable blocks
were already current from the drain. **Phase C archive drain — REFUSED, per the permanent documented
default**, and the refusal is reported rather than skipped: no epic-wide emission-quiescence signal
exists (`PLAN-TRUTH-032` is `superseded`), and `closed_senders` is per-sender only — it cannot rule out
a sender that has filed nothing yet. **Phase D restart-readiness — `ready`, 5 of 6 signals scored.**

#### ⛔⛔ D31 — THE PIN GATE IS FAILING RIGHT NOW, AND PHASE D's `ready` VERDICT IS SILENT ON IT BY CONSTRUCTION

`registry_parity` reports `not_available` and is **excluded from the floor** (it belongs to
`PLAN-TRUTH-059`), so a `ready` verdict says nothing about the pin. Checked manually, as the standing
rule requires before any restart:

| Term | Reading |
|---|---|
| executor `MARSHALL_VERSION` | **0.1.1670** |
| registry `version` / `installPath` (18 entries) | **0.1.1655** — a 15-version gap |
| unmarked (live to the loader), all 10 bundles | **`['0.1.1655']`** |
| `0.1.1670` in cache | present in all 10 bundles, **orphan-MARKED** |
| `dist-manifest.json` | `version: 0.1.1670`, `source_sha` = `7a028157e` = **HEAD exactly** |
| cache `0.1.1670` vs `target/claude/plan-marshall` | content-identical (differs only by `.orphaned_at` and `__pycache__`) |

⇒ **The content is correct and current; the pin is left behind and the correct build is marked orphan.**
The loader serves 1655 while the executor targets 1670. This is the recorded archetype: *the pin is left
behind, not drifting* — every `/sync-plugin-cache` re-opens the gap.

⛔ **Both prior repair helpers had been swept from `.plan/temp/`.** A single replacement was re-authored
at `.plan/temp/repair-plugin-pin.py` and **dry-run only** — repair is operator-only and was not applied.
It handles the half the original could not: the original only ADDED `.orphaned_at` to non-target
directories and never CLEARED it from the target, so against this state it would have written the
registry and then failed its own post-check. The new one clears the target's marker first, collects
per-directory `OSError`s instead of aborting, refuses to touch the registry if any marker failed, and
runs **markers-first-then-registry** — the proven order, because a failed registry step then leaves
pin=old / unmarked=new and the loader still serves correct content, where the reverse order has a live
window in which a restart loses.

**✅ REPAIRED 2026-09-15 — the operator ran it, and the result was verified independently rather than
accepted on the script's own post-check.** Applied: `cleared=10 added=10 errors=0`, then 18 registry
entries repointed. **Double-sampled by two different methods, both agreeing**, so the reading is not
torn: a python walk of `installed_plugins.json` plus a filesystem marker scan (19 entries, 0
unresolvable, registry version *and* installPath both `0.1.1670` on 18 entries, executor `0.1.1670`,
`unmarked == ['0.1.1670']` on all 10 bundles), and an independent shell walk (10 unmarked rows all
`0.1.1670`, 36 registry version tokens all `0.1.1670`, `dist-manifest` `source_sha` == HEAD). **Both
gates hold: `executor == installPath`, and `unmarked == [executor]` on every bundle.**

⛔ **The full restart is still owed and is now the only thing owed** — `/reload-plugins` does not
re-seat skill markdown bodies, and the session that ran the repair is seated from the pre-repair state.
⛔ **Re-check the pin at the start of the next session anyway**: the archetype is that the pin is *left
behind*, and every `/sync-plugin-cache` re-opens the gap, so a green reading here is a reading of one
day, not a property of the machine.

The command that repaired it, retained as the record:

```bash
python3 .plan/temp/repair-plugin-pin.py --target 0.1.1670 --apply
```

⛔ `--target` is a **VERSION**, never a bundle name. ⛔ Then **restart fully** — `/reload-plugins` does
not re-seat skill markdown bodies.

### 2026-09-15 Inbox drain — 71 of 71 consumed, 0 staged, 0 invalid

The `PLAN-CIS-049` landing drain. One `landing`, three `finding`s, sixty-seven `candidate-lesson`s,
from three senders (`architecture-store-query-truthfulness` 69, `grounded-evidence-pinning` 1,
`next-level` 1). All valid, all `live`. Post-drain the inbox is the **EMPTY** zero.

| Kind | n | Disposition |
|---|---|---|
| `landing` | 1 | reconciled → `landings/PLAN-CIS-049.md`, row `shipped`, PR 1489 stamped. `landing-check` → **`complete: true`, `missing_keys[0]`** — the epic's second complete landing |
| `candidate-lesson` | 64 | **Promoted** to the global lessons corpus (129 → 193). Each was already in corpus body shape (`component=`/`category=`/`bundle=` headers) |
| `candidate-lesson` | 1 | **Folded as a recurrence** onto lesson `2026-09-04-08-007` — near-duplicate, caught by a title similarity sweep over all 129 existing lessons, not by eye |
| `candidate-lesson` | 2 | **Recorded as owed architecture hints** (below). Category `insight` is outside `manage-lessons`' four-value set, so neither is promotable as a lesson |
| `finding` | 1 | **Absorbed as Watch W-049** (`grounded-evidence-pinning-001`) — the operator's own instruction forbids staging it now |
| `finding` | 1 | **Folded → `PLAN-CIS-050` D12** (`next-level-001`), with its new surface declared in the same edit |
| `finding` | 1 | **Routed to `PLAN-CIS-039`** (`architecture-store-query-truthfulness-001`) — a precedent that plan's D2 must decide against |

⭐ **Dedup was DERIVED, not eyeballed.** All 65 promotable titles were compared against all 129 corpus
titles by normalized similarity; exactly one crossed the threshold. Scanning 67 titles by hand and
declaring them distinct would have been an asserted completeness claim over a population of 8,385
pairs.

#### The three non-lesson dispositions

**W-049 — grounded evidence pinning, external prior art (`langchain-ai/openwiki`, MIT).** Claim →
Evidence → resolver-owned content-hash version, with anchor relocation and a three-state
`current`/`stale`/`unresolved` vocabulary; **sparse reconciliation** retains issue-free claims by
omission so the model's working set is the *delta*, not the corpus. ⭐ That last element is the token
lever this epic exists for — `resident_context × turns`, average byte re-read 44.6× — arrived at
independently by a shipping tool. ⭐ We already own the hashing half (ADR-006,
`compute_source_tree_fingerprint`, `.emit-marker.json` `file_hashes`, `sync._staleness_guard`); what we
have never hashed is **prose ↔ source**, which is the machine-checkable form of the only move that
terminates restatement drift.

⛔⛔ **NOT STAGED, AND THE REASON IS AN OPERATOR INSTRUCTION, NOT CAUTION:** validate only *after* every
step of the substrate is implemented AND several plans have actually executed against it. An evidence-
pinning layer's real failure modes are **population statistics** — false-stale rate, unresolved rate,
coverage, realized token delta — and none is visible from a test suite or one plan. A validation run
before a corpus of pins has aged under real edits would report a clean signal that means nothing,
which is the failure the sibling epic is named after. ⛔ Do not open a workstream for this.
⚠ Do not adopt the tool: it rewrites managed `CLAUDE.md`/`AGENTS.md` blocks (collides with
`tools-sync-agents-file`), `--init` destructively replaces an existing wiki, 0.x with no cost cap, and
it would stand up a second documentation substrate beside `manage-architecture`. **The mechanic is the
asset.** ⛔ And its `CLAIMS_SUBSTANCE_GUIDANCE` does NOT transfer — "completeness takes priority over
minimizing claim count" is an exhortation with no derivation: every claim is falsifiable, the SET is
not, so a pinning layer buys **no-false-positives, not no-false-negatives**, and a `verified:` stamp
hides the difference.

**D30 — two owed `architecture enrich insight` calls, UNEXECUTED and deliberately so.** Messages
`-067` and `-068` carry ready-to-run calls adding the insight *"the project treats bug findings as a
standing consideration"* to modules `plan-marshall` and `documentation`, each derived from a
within-plan recurrence (count 2, threshold 2) of `taken_into_account` dispositions on `bug` findings.
⛔ **The orchestrator did NOT run them.** `architecture enrich insight` writes
`.plan/project-architecture/{module}/enriched.json`, which is **git-tracked** — a repository change,
and the prime directive puts repository state outside this identity. The calls are recorded verbatim
in the archived messages; a plan touching `manage-architecture` executes them, or an operator does.
⚠ ⭐ Note the interaction with `PLAN-CIS-049` D10, just shipped: the enrich writes `enriched.json`,
and the committed descriptor tree carries **no `derived.json`** — so these writes land on exactly the
surface whose absence made `diff-modules` report every module changed. Run them *after* reading D10's
shipped behaviour, not before.

#### ⛔⛔ The lesson this drain must not bury: the 12-deliverable ceiling has its first cost reading

Candidate lesson `-005` (promoted as **`2026-09-15-08-003`**, `plan-marshall:phase-4-plan`,
`improvement`) is titled *"Split a 12-deliverable, 44-task multi_module plan before executing it"*, and
it is about **this epic's own operating rule**, set by the operator three days earlier.

Its figures: **10,488,689 tokens against a `multi_module + bug_fix` error anchor of 2.0M — 5.2× — and
380 minutes worked against a 150-minute error anchor**, for 12 deliverables / 44 tasks. 5-execute alone
took 6,330,694 (60 % of the plan) over 18 dispatches and 3 re-entries; 6-finalize a further 2,412,805
over 12 dispatches with 4 loop-backs. `total_tokens_per_deliverable = 874,057`.

Its proposed remedy is that **phase-4-plan read the same `(scope_estimate, change_type)` anchor table
the retrospective scores against, and surface a split proposal BEFORE execute** — a read of an existing
calibration (`plan-retrospective/references/plan-efficiency.md` § 2), not a new one.

⚠ **This is evidence about the re-cut, not a refutation of it, and the distinction is load-bearing.**
The re-cut's rationale was *shared target*, and it bought real things this landing demonstrates: the
`PLAN-CIS-058` merge dissolved an emission exclusivity, and D7 shipped as *complete the rule* rather
than *build it*. What the lesson adds is that **a twelve-deliverable plan is scored against an anchor
calibrated on plans an order of magnitude smaller, and the mismatch is only discovered after the
spend.** ⛔ Both facts stand; neither cancels the other. **Surfaced to the operator at this drain
rather than filed silently into a 193-lesson corpus**, because it bears on a standing directive.

#### D29 — the disjointness gate's literal form can no longer pass, because its comparison population includes 53 SHIPPED specs ⇒ TOOLING GAP, un-owned

`orchestrate.md` Step 4 states a candidate is disjoint **iff** `corpus cross-check` reports **no**
`file_overlap_matches[]` row naming its spec. At HEAD `38af136ed` that test cannot be satisfied by any
spec in this epic, and the reason is structural rather than a property of the specs:

- `file_overlap_match_count` is **4295** (it was 734 on 2026-09-12, before `#1472`
  *containment-aware overlap* made a declared directory match the files under it — a correctness fix
  that multiplied the population by ~6).
- The matcher compares each spec against **the whole corpus**: `specs_total: 65`, of which **53 are
  `shipped` and 2 `retired`**. A shipped spec's files were changed and merged; it cannot collide with
  anything. Yet for `PLAN-CIS-049` alone, 21 of its 116 rows name shipped specs and 1 more names a
  retired one.
- Add 68–114 `sibling_epic_spec` rows per candidate, the large majority of them likewise against
  siblings' shipped or parked specs, and the signal that remains — an overlap with something that can
  actually run concurrently — is **2 to 3 rows out of 116**.

⇒ **A gate whose negative can never be reached tells the operator nothing, and its silence is not a
clean reading.** ⛔ This is the epic's own signature archetype pointed at the epic's own tooling: a
verdict computed over a population that was never filtered to the things the verdict is about.

*Wanted:* `corpus cross-check` filters its `corpus_spec` candidates by queue status (a `shipped`,
`retired` or `parked` counterpart cannot be a concurrency collision) and reports the filtered
population **and what it excluded**, so the count stays derivable rather than merely smaller. Until
then the operative test is stated here and used in its place: **a candidate collides iff it overlaps a
LIVE plan, or a STAGED sibling that could run in the same round.** Under `parallelization_scope = 1`
the second clause is vacuous — nothing runs concurrently — so the live-plan overlap is the whole test.

⚠ **This substitution is an orchestrator judgement recorded in the open, not a silent override.** Every
emit made under it names the live-plan overlap it accepted, and the operator can refuse the launch on
that evidence. ⛔ Do not let it harden into the rule: the fix is the filtered population, and the
substitution retires the day `cross-check` publishes one.

### 2026-09-12 Spec re-cut — 8 staged specs (41 deliverables) consolidated to 4 (41 deliverables)

**Operator directive, and it SUPERSEDES a persona rule for this corpus:** *"create larger plans (up to
12 deliverables) … especially group same items/targets."* The `persona-plan-orchestrator` identity
attribute 8 presumptive split at ~6 deliverables no longer governs this epic's staged corpus; the
ceiling is **twelve**, and the recorded rationale is the operator's own directive of 2026-09-12.

⛔ **Nothing was dropped. 41 deliverables in, 41 out.** Four specs absorbed four others; every absorbed
spec keeps its file with a retirement header naming its deliverables' new addresses one-for-one.

| Survivor | Absorbed | Deliverables | Grouping basis |
|---|---|---|---|
| `PLAN-CIS-049` | `PLAN-CIS-058` (+ inbox fold `-059` I2) | 6 → **10** | `manage-architecture` + `standards/client-api.md`. The two specs were **declared mutually exclusive for emission** over exactly this contention; merging dissolves it |
| `PLAN-CIS-050` | `PLAN-CIS-057` | 7 → **11** | The absorbed spec's D1/D2 were written to *report AROUND* two defects that are this plan's own D1/D2. Merged, an unpredictable landing order becomes a within-plan ordering: fix instruments, then measure through them |
| `PLAN-CIS-052` | `PLAN-CIS-061` | 6 → **10** | One dispatch loop, one boundary ledger, one termination vocabulary. D1–D6 record *what the dispatch did*; D7–D10 record *why it stopped* |
| `PLAN-CIS-054` | `PLAN-CIS-056` | 6 → **11** | Causal, not filing: D1–D6 correct documents that state figures, D7–D11 settle those figures. Split apart, every figure moved leaves a stale sentence in a document the other plan owns |

**Refutations absorbed in the same act — this is what unblocked the corpus.** `blocking_count` fell
from **11 to 7**, and all 7 survivors sit on parked or retired specs: **no staged spec carries a
blocking verdict.** All four section verdicts were re-stamped `contradicted / rescoped: yes` at HEAD
`53ab7dd2e`, per claim.

- **CIS-049** — the `_project.json` staleness claim is RETRACTED (tracked, but the description's *10
  production bundles* is correct and the 12-entry `modules` set is byte-identical to live output). The
  merged build-a-drift-rule premise is replaced by *complete the shipped rule* (`7845a4b9a`/#1370,
  which already publishes `population_size`), and the consume-`argparse_surface.py` hypothesis is
  recorded as **contraindicated** (that seam's own docstring records a static AST walk abandoned after
  1323 false positives).
- **CIS-050** — D5(f) STRUCK (closed by #1339, confirmed at HEAD). ⛔⛔ **D3(a)'s refutation was itself
  only half right, and taking it at face value would have struck a LIVE defect.** #1268 removed the
  `Path.cwd()` fallback, but the claim anchored on the `pending`-worktree path, and
  `PlanContext._resolve_worktree_face` still returns the **main checkout** for `pending` without
  raising, while `verify_failure_scope` still does not gate on `has_worktree`. D3(a) is **narrowed,
  not struck**. ⭐⭐ **A refutation that names a NEARBY mechanism is not a refutation of the claim** —
  worth carrying as a rule, not just as this instance.
- **CIS-052** — D1(a)–(d) STRUCK: the dispatch-seam migration landed, and the deliverable's own
  skill-wide exit condition (no `--message "[DISPATCH]"` anywhere under `skills/phase-6-finalize/`) is
  met at HEAD. D1 survives as (e) alone. The merged D8 is re-scoped from the **predicate** to the
  **threshold** — the emit site already consults `tasks_remaining` (machinery dating to #349/#714/
  #730/#842), which the retired spec's own verify-first clause pre-authorised.
- **CIS-054** — D6's *"That directory IS absent entirely"* is FALSE and deleted: `cloud-runs/` holds
  **46 directories, 37 with a `gaps.md`**. The not-applicable arm was never reachable, so the corrected
  gating derivation is now mandatory rather than precautionary.

**What the re-cut did NOT dissolve, recorded so it is visible rather than inferred:**

- ⛔ **The four-file contention between `PLAN-CIS-050` and `PLAN-CIS-052`** (`manage-metrics.py`,
  `data-format.md`, `analyze-logs.py`, `phase-5-execute/SKILL.md`). `PLAN-CIS-061` overlapped
  `PLAN-CIS-050` more heavily than `PLAN-CIS-052`, but `PLAN-CIS-050` was already at eleven and taking
  it would have breached the twelve ceiling. A sequencing constraint under `parallelization_scope = 1`,
  not a concurrency block.
- ⛔ **`PLAN-CIS-054` inherits `PLAN-CIS-056`'s surface collision with live PR #1398 on `audit.py`.**
- ⛔ **`PLAN-CIS-050` D8 and `PLAN-CIS-054` D7 are the SAME population gate** over the git-ignored
  `.plan/local/archived-plans/` tree. Both specs now carry a must-not-diverge rule: whichever runs
  second cites the first's published population and reports any difference as a finding. Two
  independent counts over one corpus is the disagreement-between-instruments archetype these plans
  exist to remove.
- ⛔ **Cost the operator was told and accepted:** `PLAN-CIS-057` was the epic's SOLE emittable
  candidate and is now absorbed. Emittability now depends on the disjointness read, not on prep.

#### D28 — `queue --transition` cannot write the `retired` status the queue already contains ⇒ TOOLING GAP, un-owned

The four absorbed specs should read `retired`, matching `PLAN-CIS-008` and `PLAN-CIS-055`. The verb
refuses it: `--status must be one of ['landed', 'launched', 'parked', 'running', 'shipped',
'staged']`. So a status **already present in `plans[]`** cannot be written by the only sanctioned
writer of that field — the two existing `retired` rows predate the verb and were set by the
whole-array rewrite the `--add-row`/`--transition` surface was built to replace.

⇒ **The four rows are `parked`**, which is the closest legal value that removes them from the staged
emit walk, and their spec files carry the authoritative retirement headers. ⚠ `parked` normally means
*paused, resumable in place*; these are **absorbed and must never be resumed**. Read the header, not
the status. ⛔ Do **not** repair this with a whole-array `manage-status update-field --field plans`
rewrite — that is the hazard **D15** records, and it is how 109 items were destroyed once already.
*Wanted:* `retired` added to the transition accept-set, or a documented ruling that `parked` is the
terminal absorbed state and the two legacy `retired` rows are migrated.

### 2026-09-12 Inbox drain — 1 of 1 consumed, 0 staged, both items FOLDED

One `finding` message from the `truthful-signals` orchestrator (`truthful-signals-059.md`, created
2026-09-11T15:52Z), valid, `live`, carrying two forwarded consumer-repo items. Both are **notifications
and hand-offs, not transfers** — nothing is staged in `truthful-signals` for either, and this drain
stages nothing new. Post-drain the inbox is the **EMPTY** zero (`live_count 0`, `closed_senders []`,
`invalid_count 0`) — a later message from any sender is still possible.

| Msg | Signal | Disposition |
|---|---|---|
| `-059` I1 | `compute-footprint` against a stale LOCAL `main` reported 183 files for a 4-file change (API-Sheriff PR #243) | **D26 below** → folded into **CIS-050 D7** as a sighting; adds no file surface |
| `-059` I2 | `diff-modules --pre` reports every module `changed` over a byte-identical baseline (Token-Sheriff) | **D27 below** → folded into **CIS-049 D3**; adds no file surface |

#### D26 — the stale-base-ref footprint inflation, now n=3, with a direction fact ⇒ folded into CIS-050 D7

A second consumer repo hit the resolver D7 already owns. The sender's 183-files-for-4 figure is a
**LEAD from another machine's archive and is NOT re-derived** — do not publish it as measured. What IS
corroborated first-party at HEAD `53ab7dd2e`: `_references_core.py` `resolve_base_ref()` (`:157-176`)
returns a bare branch name, falling back to the literal `'main'`, and nothing in the module consults
the remote-tracking ref or reports staleness — unchanged from the `b95d78437` reading D7 recorded.

⭐ **The direction is the part that changes D7's control, and it is why this is not merely a recurrence
tally.** A stale base ref **never under-reports**; it over-reports, and it does so with
legitimate-looking paths. Both observed instances were caught by *magnitude implausibility* — a ref
behind by 3 files instead of 179 yields a wrong footprint that looks entirely ordinary and is consumed
without question. **D7's control must therefore prove the small-divergence case**, not only the large
one; the all-or-nothing test is the vacuous half.

Three independent sightings of one resolver now: this epic's original (`truthful-signals-043`/`-045`),
API-Sheriff `macos-loopback-hang-investigation` (PR #243), and local lesson `2026-09-03-05-002`
(self-review `--base-branch` overstating `files_in_scope`). *Owner:* **CIS-050**, D7, no new surface.

#### D27 — an INDETERMINATE comparison published as `changed`, on every run, by construction ⇒ folded into CIS-049

⛔ **The sender filed a hypothesis; it is CONFIRMED first-party here at HEAD `53ab7dd2e`, and more
strongly than the sender could show.** `_cmd_client_handlers.py` `cmd_diff_modules` (`:1359-1372`)
hashes `snapshot_dir / name / derived.json` and treats `snap_sha is None` as **`changed`**, its own
comment conceding *"the sha surface cannot certify equality"* — an explicitly indeterminate branch
reported under the label that means evaluated-and-wanting. And `git ls-files .plan/` returns **14
paths — `marshal.json`, `_project.json`, and 12 × `{module}/enriched.json`, with ZERO `derived.json`**.
⇒ Against any `git archive` baseline of the committed descriptor tree, every module falls into that
branch, so `changed` is the full module set and `unchanged` is empty **by construction, on every run,
in every repository that commits its descriptors**. Token-Sheriff's 18-of-18 and a 12-of-12 here are
one defect, not two.

`changed[]` feeds Tier 1, so the false "all changed" proposes a whole-project LLM re-enrichment for a
plan that moved no descriptor — a large, silent, recurring cost — and a verb that says everything
changed on every run teaches operators to stop reading it. ⭐ This is **ADR-019 on a fourth verb**, the
same subject CIS-049's D2/D3 already make honest for `count: 0`: report `indeterminate[]` with a
per-module reason, separately from `changed[]`. *Owner:* **CIS-049**, folded into D3's vocabulary work,
no new file surface (`_cmd_client_handlers.py`, `client-api.md` and `test/plan-marshall/manage-architecture/`
are already declared). ⚠ `PLAN-CIS-002` also named `diff-modules` — check it before planning the item.

⚠ **Ledger hygiene noticed during this drain, not caused by it: the defect ids `D16`–`D20` are used
TWICE in this section** — once as top-level bullets (`D20` = the `###`-truncates-Expected-Surface
parser defect) and again as `####` sub-blocks under the 2026-09-08 drain (`D20` = the coverage-clean
zero routed to CIS-049). Two different defects answer to `D20`. Nothing is lost, but a reference to
"D20" is ambiguous without its section. `D26`/`D27` above are allocated above BOTH ranges so they add
no third collision. Resolve the collision at the next `cleanup`, not by renumbering mid-drain.

### 2026-09-08 Inbox drain — 5 of 5 consumed, 0 staged, 1 fold owed at spec level

Five `finding` messages, all from the `truthful-signals` orchestrator, all valid, all `live`.
Every one is a **notification and hand-off, not a transfer** — that epic staged nothing for us, and
this drain stages nothing new either. Post-drain the inbox is the **EMPTY** zero (`live_count 0`,
`closed_senders []`, `invalid_count 0`) — a later message from any sender is still possible.

| Msg | Signal | Disposition |
|---|---|---|
| `-054` I1 | `architecture search`/`find` return a COVERAGE-CLEAN zero against a deleted worktree root | **D20 below** → CIS-049 |
| `-054` I2 | All four token-decomposition columns unmeasured, 41 of 41 rows | **D21 below** → CIS-050 |
| `-055` I1 | Same, independently, on a second unrelated plan ⇒ n=2 | folded onto D21 — recurrence is the information |
| `-055` I2 | Finalize 81% of a 13.9M plan; 124 firings for 22 steps | **D22 below** → un-owned, WS-04/WS-06 |
| `-055` I3 | Dispatch-audit `0 / 73` clean at `0.058` channel completeness | **D23 below** → CIS-050 |
| `-056` I1 | `PLAN-CIS-060` "appears already shipped" | **no action — it IS shipped** (PR #1355). Their premise was that it is staged; our queue says otherwise. The three properties they found in the tree are there *because* CIS-060 landed them. |
| `-056` I2 | CIS-061's D1 is the instruction channel, measured 0/3 | **D24 below** → CIS-061, second independent block |
| `-057` a | Participation quorum passes when every reviewer yields nothing | **not ours** — addressed to `review-apparatus` in the same message. Not re-routed. |
| `-057` b | `blocked_user_review` spend falls into NO published class | **D25 below** → CIS-050, distinct from D21 |
| `-058` | The 41-of-41 omission has a NAMED CALL SITE | folded onto D21 as its actionable half |

#### D20 — a coverage-clean zero over a tree that was never opened ⇒ CIS-049

⛔⛔ **This falsifies a trust rule published in CLAUDE.md, and it is the sharpest item in the drain.**
After `branch-cleanup` removed a plan's worktree, `architecture --plan-id P search --content` returned
`success` / `count: 0` / **`files_scanned: 0`** with `unreadable[0]`, `truncated: false`, `elided[0]`
— a *fully populated and entirely clean* coverage block. The same call without `--plan-id` returned
`count: 2` over `files_scanned: 5361`, and `info` on the **same root** fails loudly with
`data_not_found`. One resolver, three verbs, two behaviours.

⛔ **The complete-coverage rule as written is insufficient**: it teaches readers to trust a `count: 0`
when `unreadable`/`truncated`/`elided` are clean, and **`files_scanned: 0` is not in that list**, so a
zero-population scan passes the published test. `find` publishes no `files_scanned` at all.

⭐ **It was found by searching for a literal known to exist, not by inspecting the response** — no
amount of inspection would have caught it. That is the transferable part: a positive control is the
only reader-side defence until the resolver fails closed.

*Blast radius is ours too:* every finalize step ordered after `branch-cleanup` runs against a removed
worktree; that plan ran six. Any of them passing `--plan-id` received a confident clean negative.
⇒ **Re-read any past finding of ours that rests on a `--plan-id` search taken after a `branch-cleanup`.**

*Owner:* **CIS-049** (architecture store-query truthfulness) — this is its thesis with a live,
reproducible instance. Fold owed at spec level; not yet folded.

#### D21 — the four token-decomposition columns are never filled, and the call site is now named ⇒ CIS-050

All four columns (`input_tokens`, `output_tokens`, `cache_read_input_tokens`,
`cache_creation_input_tokens`) ride `unmeasured_columns` on **41 of 41** dispatch-boundary rows, on
**two unrelated plans** (`PLAN-TRUTH-093`, `PLAN-TRUTH-089`). ⛔ **`position_multiple` has therefore
never once been computable** — not a coverage gap, a metric that has never run. `total_tokens` and
`tool_uses` DO record, so the rows are being written; it is specifically the four-way split that never
lands.

⭐⭐ **`-058` supplies the half the other two lacked: the columns are absent because the CALLER does
not pass them, at every `record-dispatch-boundary` call site in `phase-6-finalize`.** That rules out a
store-side remedy — `manage-metrics` is recording faithfully what it is handed.

⚠ The store labels the gap honestly (a zero with its population stated as `0`) and it still reads as a
cost of nothing to any consumer that takes the total without the denominator.

*Owner:* **CIS-050**. Fold owed at spec level.

#### D22 — re-firing, not implementation, is where the spend is ⇒ UN-OWNED, and now n≥2

`PLAN-TRUTH-089`: `6-finalize` **11.27M tokens / 2245 tool uses** against implementation's **507K /
194**, on a 13.9M plan (~7× anchor). **124 firings to complete 22 steps — a 5.6× multiplier**;
`plugin-doctor` 19×, `pre-submission-self-review` 19× (ceiling `17/17` fully consumed),
`pre-push-quality-gate` 18×, `lessons-housekeeping` 17×.

⛔ **The 11.27M is a FLOOR** — that phase never recorded an end time, so it is open in the metrics.
⭐ Publishing an open phase as a floor rather than closing it silently is correct; do not let a fix
stamp an end time after the fact.

⭐⭐ **Fourth landing in their series where a `23/23`-style headline under-reported the firing count**
— by 7, 44, 52 and now 102. **A cost model that reads step rosters is reading a number wrong by up to
5.6× on exactly the phase that dominates.**

⇒ **This corroborates PLAN-CIS-053's own landing finding** (93% of the head-dependent re-fire cycle
produced nothing; 5 of 6 head-bound steps fired 38× with zero findings; `pyproject_build` at 50.3% of
script time). Two independent measurements, same conclusion. ⛔ **Still un-owned and NOT STAGED** —
belongs with WS-04/WS-06 cost work. Stage before the next cost plan.

#### D23 — a clean audit verdict over a 5.8% sample ⇒ CIS-050

Dispatch-audit reports `0 / 73` clean at **`0.058` channel completeness** — it compared the channel
against itself over a population it could see 5.8% of. ⭐ Well-behaved: the confidence figure IS
published, so the verdict is qualified rather than bare. ⚠ **The risk is entirely at the consuming
end** — a reader taking `0 / 73` without the completeness number gets a clean bill of health over a
5.8% sample. *Owner:* **CIS-050** (the dispatch-audit channel is our measurement surface).

#### D24 — CIS-061's D1 remedy is a channel this epic measured at ZERO ⇒ second, independent block

`truthful-signals`' `PLAN-TRUTH-107` is the **same defect** as CIS-061. Their ask is specific and
cheap, and it is not a precedence claim:

⛔⛔ CIS-061's D1 — *"persist the standing completion instruction into plan state that each dispatch
reads"* — **is the instruction channel, measured at zero across four independent strengths**:
doc-instructed `[ARTIFACT]` emission survived **0 of 3** while script-emitted `[OUTCOME]` survived
**3 of 3** in the same run on the same tasks; a persona Hard Rule was violated in-session; an
in-session operator instruction failed twice in one run; two explicit do-not-stop directives both
failed. ⭐⭐ **CIS-061's own evidence is a fifth instance read the other way**: the operator's opening
run-to-completion instruction was already given, and six turns were still spent restarting. Persisting
it changes its *durability*, not its *channel* — and the channel is what measured zero.

⛔ **A coupling that will bite whoever ships first:** the stop/re-entry cycle has been *accidentally*
supplying head-dependent gate re-fires. A run that drove straight through recorded
`delta_verdict: excluded`, `gates_did_not_cover_reviewed_tree`, and mypy/ruff/plugin-doctor never
re-ran against the merged tree. ⇒ **Shipping the continuation mechanism alone is a NET REGRESSION, and
it scales with exactly the stopping frequency CIS-061 measured.**

⚠ **Note the tension with D22 and hold both**: D22 says the re-fires are 93% uninformative; this says
the re-fire mechanism is nonetheless load-bearing for merged-tree coverage. Both are true, and a fix
that removes stalls without replacing that coverage trades a cost defect for a correctness one.

*Two asks accepted:* (1) do not ship a persisted-instruction remedy as D1's primary mechanism without
recording that this class measured 0/3 and why a different result is expected; (2) **whichever epic
lands first sets the yield vocabulary** — two vocabularies for one question is the defect
`PLAN-TRUTH-124` exists to end.

⇒ CIS-061 is now blocked for **two independent reasons**: its claim 3 was refuted at HEAD by our own
re-grounding (the emit site DOES consult `tasks_remaining`), and its D1 remedy is a measured-dead
channel. Fold owed at spec level.

#### D25 — an unbucketed dispatch outcome ⇒ CIS-050, and it does NOT fold into D21

A dispatch ending `blocked_user_review` spends real tokens, and that spend is **accounted to no
published class**, so the run's spend decomposition is short by an unstated amount.

⛔ **D21 and D25 are separate defects: D21 is a COLUMN that is never filled, D25 is a ROW that is
never bucketed. A fix for either leaves the other, and a decomposition that closes only one still
fails to sum.** *Owner:* **CIS-050**.

### 2026-08-26 Inbox drain — PLAN-CIS-060 / PR #1355, 9 of 9 routed, 0 staged

One `landing` (`-009`, the epic's **first `complete: true` landing** — `landing-check` reports
`missing_keys[0]`) and eight `candidate-lesson` messages, all from
`verdict-field-read-and-write-integrity`, all valid. Every one folded into an existing staged spec;
none required a new spec. Post-drain the inbox is the **EMPTY** zero.

| Msg | Signal | Disposition |
|---|---|---|
| `-001` | Finalize dispatch ledger blind to re-dispatch inside an entered step (~36% of the phase) | folded → **CIS-052 N2** |
| `-002` | `channel_completeness` divides all-phase dispatches by finalize-only completions | folded → **CIS-051 N1** |
| `-003` | `worktree-remove` reports a 60 s timeout with the dirty-tree hint | folded → **CIS-052 N6** |
| `-004` | Self-review reports `clean` over defects the round actually saw and suppressed | folded → **CIS-052 N3** |
| `-005` | Billing/composition persist a measured-looking `0` over an empty population | folded → **CIS-050 D4.i** |
| `-006` | `planning-lane` routes on pre-settlement inputs, never re-evaluated | folded → **CIS-050 D5.ii** |
| `-007` | `cohort_size` round-scoped ⇒ a recurring class reads as closed every round | folded → **CIS-052 N4** |
| `-008` | Clause-deletion fixes re-flag the same line round after round | folded → **CIS-052 N5** |
| `-009` | Landing (complete) | reconciled → `landings/PLAN-CIS-060.md` |

⛔⛔ **The sharpest is `-002` composed with `-001`: the auditor graded the dispatch channel `nominal`
over a ~893 K-token hole in that same channel, because its ratio compared two unrelated populations.
A vacuous green in the instrument that measures the instruments** — this epic's own subject, one level
up. ⭐ Four of the eight are the SAME instrument (`pre-submission-self-review`) seen from four angles;
they are folded together into CIS-052 for that reason.

⭐ **The in-house gate found the substance, the bots found lint** — 7 self-review rounds found 10 real
defects pre-push (every one a doc claiming what the code does not provide), the 3 bots one
markdownlint nit. ⛔ **Confound kept, not dropped**: self-review runs at orders 5–7, so the bots
reviewed a tree those 10 defects had already been removed from. This run does **not** measure whether
they would have caught them.

### 2026-08-25 Inbox drain — PLAN-CIS-059 / PR #1348, 8 of 8 routed, 0 staged

All eight messages were `kind: candidate-lesson`, `lifecycle: live`, `valid: true`, from sender
`fold-pm-code-intelligence-into-core`. **Every one folded into an existing staged spec or an existing
structural finding — none required a new spec**, so no `Stage` was performed and D15's hand-rewrite
cost was not incurred. Post-drain: `live_count 0`, `closed_senders` empty, `invalid_count 0`,
`inbox_state present` — the **EMPTY** zero, not *finished* and not *blocked*.

| Msg | Signal | Disposition |
|---|---|---|
| `-001` | Nothing persists the realized footprint before `branch-cleanup` destroys the worktree | folded → **CIS-050 D3.ii** |
| `-002` | Footprint resolver's merge-commit tier is structurally dead under squash landings | folded → **CIS-050 D3.i** |
| `-003` | Finalize loop-back half-stamps `6-finalize` and clamps worked time into a confident row | folded → **CIS-050 D2.i** |
| `-004` | Merge FIFO queue has no read surface; the hand-read pruned a live plan's slot | folded → **CIS-049 N2** |
| `-005` | `manage-status read`/`list` blind to a sibling-worktree plan; two blind reads agreed | folded → **CIS-049 N1** |
| `-006` | 8 of 9 completed tasks emitted no `[ARTIFACT]` line; the floor could not grade it | folded → **CIS-050 D5.i** |
| `-007` | `error` finding filed after the metrics close stays pending past merge | folded → **CIS-052 N1** |
| `-008` | Three count claims in one run, each wrong — in a run that WAS a counting exercise | folded → **F11 recurrence** |

⛔ **The two most consequential are `-002` and `-005`, for opposite reasons.** `-002` is a **population**
defect — a tier matching two-parent commits can never fire in a squash-merging repository, so it is
dead for *every* plan this project lands, not merely unreliable. `-005` is this epic's own theme
biting hardest: **two independent reads both returned absence and both were structurally incapable of
returning presence, and the resulting inference destroyed live state** (a sibling plan's merge-queue
slot). Two blind checks agreeing is not corroboration.

⚠ **Three specs gained surface in this drain**, each declared in the same pass as its fold rather than
afterwards. `git-workflow.py` is now declared by CIS-050, CIS-049 and CIS-052; `_status_query.py` by
CIS-049 and CIS-052. Under `parallelization_scope = 1` these are **sequencing** constraints, not
concurrency ones — re-ground the survivors after whichever lands first.

### 2026-08-26 cleanup — cross-check finding: TWO live sibling plans overlap five staged specs

⛔⛔ **`plan-footprint-is-unknowable-to-its-own-graders` may be DUPLICATE WORK against `PLAN-CIS-050`,
and this ledger structurally cannot tell on its own.** `corpus cross-check` (epics_scanned 8,
plans_scanned 4, candidates_scanned 273) reports it overlapping **five** staged specs:

| Staged spec | Overlap | Files |
|---|---|---|
| `PLAN-CIS-050` | **5** | `manage-references.py`, `phase-6-finalize/SKILL.md`, `plan-retrospective/SKILL.md`, `analyze-logs.py`, `compile-report.py` |
| `PLAN-CIS-051` | **4** | `plan-retrospective/SKILL.md`, `references/report-structure.md`, `compile-report.py`, `retro_sections.py` |
| `PLAN-CIS-052` | 1 | `phase-6-finalize/SKILL.md` |
| `PLAN-CIS-056` | 1 | `analyze-logs.py` |
| `PLAN-CIS-057` | 1 | `analyze-logs.py` |

⛔ **The name is the alarm**: *footprint unknowable to its own graders* is, on its face, the SAME
subject as the two items the 2026-08-26 drain just folded into CIS-050 — **D3.i** (the merge-commit
tier is structurally dead under squash landings) and **D3.ii** (nothing persists the realized
footprint before `branch-cleanup` destroys the worktree). A surface overlap is not by itself duplicate
work — this epic has ruled that way before (D14) — but a surface overlap **plus a matching subject**
is the shape a real duplicate takes.
⛔ **Per the standing rule, a ledger cannot see a duplicate held in another ledger.** Check that plan's
live state and its actual deliverables against CIS-050 D3.i/D3.ii **before emitting CIS-050**, and
before CIS-051 starts if it has not.

⚠ **`a-failing-ci-call-reports-success`** overlaps `PLAN-CIS-052` (2: `automatic-review/SKILL.md`,
`phase-6-finalize/SKILL.md`), `PLAN-CIS-050` (1) and `PLAN-CIS-053` (1: `test/conftest.py`). No
subject collision is apparent, so this reads as ordinary sequencing — under
`parallelization_scope = 1` it gates nothing concurrently. Re-ground the survivors after it lands.

⛔ **`PLAN-CIS-051` IS ALREADY EMITTED** (2026-08-26, awaiting operator-confirmed launch) and carries
the second-largest overlap in the table. Its emit predates this cross-check.

## Watches

The pre-ingest section is relocated verbatim to [`settled.md`](settled.md) § "Relocated: Watches as they stood before the ingest".

- ⭐⭐ **W-048 — NEW 2026-08-31, absorbed from inbox `truthful-signals-052`: a FOURTH data point,
  and the first one carrying a measured per-tool-call context climb.** `PLAN-TRUTH-098` landed as
  PR #1359 / `841f9093` on 2026-08-27: **9,203,064 dispatched** against **185,422,539
  billing-weighted** (~20×), of which **phase 6 alone was 4,996,549 dispatched and 96,178,416
  billing-weighted — 52% of the run**, more than every other phase combined. Wall 8h12m worked /
  23h38m elapsed, 3 loop-back iterations of a ceiling of 5.
  - ⭐ **The mechanism is measured here rather than inferred: resident context per tool-call climbed
    209K → 771K across finalize** — a near-4× growth in what every subsequent call re-reads. That is
    the first direct observation of the climb this epic has been attributing cost to.
  - ⛔ **The sender states the caveat rather than burying it, and it must survive**: their own ledger
    has retired every per-phase figure drawn from a re-entered row as arithmetically impossible, and
    **this run had 3 loop-backs**, so the 52% is NOT directly comparable to this epic's earlier
    per-phase figures. ⛔⛔ **And PLAN-CIS-051's own landing has now shown the same corruption from the
    producer side** (D19: `re_entered_phases` empty, `close_count: 1` against two recorded
    loop-backs), so a re-entered per-phase figure is not merely incomparable — **the phase label and
    the population it covers actively disagree**. Read the 52% as "phase 6 plus whatever re-entered
    under it", never as finalize cost.
  - **Why a watch and not a plan**: it is a measurement offered, not owned — *"NOT a transfer,
    nothing leaves our ledger"*. It corroborates the standing finding and is folded nowhere; the
    owning work is `PLAN-CIS-050`, which already carries the producer-side defect that makes figures
    of this shape untrustworthy.

- ⭐⭐ **W-047 — NEW 2026-08-24, absorbed from inbox `truthful-signals-047`: a THIRD data point that
  spend does not track diff, and the instrument that would explain it did not run.** `PLAN-TRUTH-075`
  landed as PR #1336 / `77c9dc70a` — **3 files, +745/−2** — for **71.4M billing-weighted** against
  3.04M dispatched, of which **`6-finalize` was 45.3M, i.e. 63% of the plan**, over 342 tool uses and
  13h 2m wall clock at **80% idle**. The landing and diff are corroborated first-party by the sender
  (`git show --stat`, `ci pr view`); ⛔ **the cost figures are that plan's own retrospective output and
  are NOT re-derived** — a lead, not a fact.
  - ⭐ **Why it is a watch and not a plan**: it corroborates the epic's standing finding that billing
    tracks *context residency*, not diff size. This anchor already records a doc-only plan at ≥14.3M
    context / 66.2M billing behind a 4.16M headline; `-046` supplied #1332's split; this one is
    **smaller in diff and comparable in billing**. Three independent points, same direction.
  - ⛔⛔ **The 63% CANNOT currently be explained, and that is the substantive part.** Per the source
    plan's own inbox `-006`: `6-finalize` recorded **2 dispatch-boundary rows totalling 238,455 tokens
    against a phase accumulator of 1,233,654 — 19.3%** — with **7 finalize steps token-proven to have
    dispatched**. All four context-load columns (`input`, `output`, `cache_read`, `cache_creation`) are
    **unmeasured on every row across all three dispatching phases** (`total_rows: 4`,
    `measured_rows: 0`, `position_multiple: unmeasured`). ⇒ **45.3M of billing has no per-dispatch
    attribution behind it.**
  - ⛔ **DO NOT STAGE the `position_multiple` half.** It is **owned** — `PLAN-TRUTH-097` F2 on the
    sibling epic, now at n=2. It is named here only because it bounds what the 63% can be explained
    with. ⭐ This is the standing three-way routing working correctly: the cost *observation* is this
    epic's column, the *instrument* is theirs.
  - ⚠ **Caveats carried, not dropped**: 80% idle wall time makes wall-clock useless here and would
    distort any per-hour or per-phase rate; and the retrospective's own total is a **floor**, so "past
    the error anchor" understates rather than overstates.
  - ⭐ **Reconciliation left open, deliberately**: the sender notes the 63% whole-phase share sits near
    a 26.2% settle-band re-fire share recorded from #1332 — **but those measure different things** and
    neither side has reconciled them. Do not treat the proximity as agreement.

- ⭐ **`PLAN-CIS-038`'s D2 has never executed end-to-end, and the next ordinary local plan will
  exercise it for free.** The reconcile verb has exactly one call site and no run has reached it —
  that plan's own finalize ran under the OLD frozen manifest, and the cloud lane never executes
  phase-6-finalize at all. **The first local plan to reach phase-6-finalize Step 1.5 is its real
  test.** Watch that run's output; do not stage a plan to manufacture the test.
- ⚠ **`PLAN-CIS-024` created a new crawled module** (`documentation`, 12 → 13 here) **whose full
  consumer population was never derived.** Only the *docs-only change derives zero builds*
  consequence was checked; phase-4 planning, task-profile resolution and module-tests scoping were
  not. Watch for a scoping anomaly on a docs-touching plan.
- ⚠ **`PLAN-CIS-029` shipped with two refuted Done-when clauses that three other plans sit on top
  of.** Its freshness read **fails open** — reporting `fresh` for both a diverged-tree document and
  a missing one. ⛔ **When `PLAN-CIS-049` fixes it, re-check whether `PLAN-CIS-033`'s
  `skills_by_profile` freshness inherits the same document-vs-index divergence. No plan tested that
  interaction.**
- ⚠ **A second `cache_read_per_tool_use` emitter exists over a DIFFERENT population**, added by a
  later plan, violating `PLAN-CIS-042`'s own one-writer rule. Neither document cross-references the
  other. **The two are not comparable and the name collision will eventually produce a false
  comparison.** Routed to `PLAN-CIS-050`.
- ⚠ **`PLAN-CIS-002`'s leaf-verification obligation is unmet epic-wide** — verify a capability claim
  inside a dispatched leaf with `Grep`/`Glob` revoked. It now has an owner (`PLAN-CIS-058` D3), whose
  mandate is to discharge it **or retire it with a stated replacement**.
- ⚠ **`PLAN-CIS-016`'s C5 claim was never located** — *a warning that fires at every boundary*. Two
  independent searches came back empty. It carries **neither a verdict nor a mode**, and is recorded
  as an open question rather than as a closed one. Either the claim is wrong or the site is outside
  the swept surface.
- ⚠ **Eight of `PLAN-CIS-048`'s twelve disclosed survivors have been re-verified by nobody.** The
  first audit checked two, the adversarial pass checked two more. This is a **known coverage hole**,
  not a clean result.

## Close Obligations — discharged at `close`, not before

- ⭐⭐ **A `doc/analysis/` document on context-admission economics, written at epic CLOSE.**
  **Operator instruction, 2026-08-09**: the reasoning behind WS-06 — the byte-turn cost model,
  the doc-residency-vs-index-answerable split, the per-dispatch isolation currency correction,
  and the comparison against the eager-hydration / just-in-time-search / vector-index positions
  other coding harnesses take — is to be written up as a **git-controlled document**, and
  **deliberately NOT now**: the findings it would record are `n=1` and are the explicit subject
  of `PLAN-CIS-036` D1, `PLAN-CIS-039` D1, `PLAN-CIS-040` D1 and `PLAN-CIS-042` D1. **Writing it
  before those run would publish exactly the phase-specific-figure-read-as-general claim this
  epic exists to detect.**
  - **Home**: `doc/analysis/` — the sanctioned place for a measurement-and-decision report
    (`uncompressed-output-measurement.md` is the shape to match: methodology first, populations
    named, estimation band stated).
  - ⛔ **External tools may NOT be named in it.** `doc/concepts/design-influences.adoc` is the
    single sanctioned place for prior-art attribution, so the comparative framing lands there and
    the analysis document describes plan-marshall in its own vocabulary.
  - ⛔ **Every figure carries its population and its phase**, and every claim carries the plan id
    it was measured on. **A figure whose gating plan has not run is stated as a lead, not a result.**
  - **Source material** — all first-party, all recomputed by the orchestrator rather than quoted:
    `landings/PLAN-CIS-031.md` §§ Metrics and Anomalies, and § Vision's 2026-08-09 block above.

## Operator-Owed

- ⛔ **Post-merge PR revisit owed on the whole 2026-08 wave.** 39 PRs landed (#1140 … #1321) and the
  standing rule is that every landed plan gets a post-merge revisit. ⚠ Two are named by their own
  runs as having had effectively no earned external review (#1056, #1059 from the prior wave; #1126
  and #1127 likewise). ⭐ **The ingest's audit is not a substitute** — it checked the tree against
  the plan, not the PR conversation against the diff.
- ⚠ **`PLAN-CIS-016` merged with merge-gate condition 2 unestablished** (two unreadable PR-comment
  surfaces), on an explicit operator override. Recorded so the override is visible rather than
  buried in the run report.
- ⛔ **The plugin registry pin inversion recurs ~daily and a session restart does NOT fix it.**
  **Check the pin before every plan launch.** The executor's own bootstrap self-heal for a dangling
  pin is inert. Repair is operator-only.
- ⛔⛔ **LIVE PIN INVERSION, diagnosed 2026-08-23T08:26Z during a cleanup pass. Repair is
  operator-only, so it is recorded rather than fixed.**
  - Registry `installPath` pins **`0.1.1526`** for every bundle (double-sampled, both samples agree).
  - **The generated executor points at `0.1.1527`** — for `plan-marshall`, `pm-dev-frontend`,
    `pm-dev-java`, `pm-dev-java-cui`, `pm-documents` and `pm-plugin-development` alike.
  - **`0.1.1527` carries an `.orphaned_at` marker**, written `2026-08-22T16:04:17Z`. Its content is
    an epoch-ms value (`1787407457548`), which is **Claude Code's own GC marker format**, not ours.
  - `0.1.1526` and `0.1.1240` are unmarked.

  ⇒ **The executor is pinned to a directory that has been marked for garbage collection.** It works
  today only because the marked directory still exists. When the foreign 7-day GC collects it, every
  `.plan/execute-script.py` call fails with `ModuleNotFoundError`. The gate that catches this is
  **`executor == installPath`**, and it currently **FAILS**.

  ⭐ **Nothing automated would have caught it.** `cleanup restart-check` returns `verdict: ready`
  with `registry_parity` as `not_available` — *"this component observes no parity surface; it is
  owned by `PLAN-TRUTH-059`"*. The row is honestly abstaining rather than falsely passing, but the
  consequence is that readiness reports `ready` over an executor pinned to a condemned directory.

  ⛔ **Do NOT stage a CIS-side detector** — that surface is `truthful-signals`' (`PLAN-TRUTH-059`).
  ⛔ **Do not `/sync-plugin-cache` or regenerate before deciding**: every regen moves the cache and
  the executor and **never the registry**, so it re-arms the inversion. The documented recovery is
  to run `generate_executor.py generate` **directly by path**, never through the proxy.

- ⚠ **`/marshall-steward`** — `marshal.json` provisioning stamp is behind the installed bundle
  version.

---

## Relocated narrative

[`settled.md`](settled.md) holds the pre-ingest Ordered Queue, the 2026-08-09 full-queue
reconciliation, the pre-ingest Open Defects and Watches, the two decisions closed on 2026-08-09, and
the stale-inline anchor tail — **all verbatim**. It is a record, not a brief: nothing is read from it
to decide anything, and every claim in it that still binds has been restated in the live sections
above.

[`superseded-anchors.md`](superseded-anchors.md) holds the frozen 2026-08-07 resume anchor.
