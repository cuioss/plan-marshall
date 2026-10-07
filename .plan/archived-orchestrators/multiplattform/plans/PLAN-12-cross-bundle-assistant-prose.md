# PLAN-12: No bundle outside plan-marshall names Claude as the assistant

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to close inventory rows that are **structurally unreachable** by any
> staged plan. Source evidence: `../reference/coupling-inventory.md` §C rows 2, 3, 4.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim; the hit list is the work list.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

Three inventory rows are unclaimed for a **structural** reason, not an oversight: PLAN-07's Expected
Surface is `marketplace/bundles/plan-marshall/**` only, so it cannot reach the sibling bundles;
PLAN-07's D5 covers `/marshall-steward` and `/sync-plugin-cache` emission but not `/plan-marshall`;
and the metrics *scripts* were normalized while the metrics *documentation* still teaches a Claude
billing envelope as the format. The result is that a reader of `pm-requirements`, `pm-documents`,
`pm-dev-frontend`, `manage-lessons`, or `manage-metrics` still learns that Claude is the assistant and
`message.usage` is the shape. Close all three.

## Deliverables

1. **D1 — Cross-bundle assistant prose (NARROWED 2026-09-09 — see below; the site list the spec was staged with is largely stale).** The sibling bundles should state what the reader gets, not which product provides it. **The one site still open** is `pm-requirements/README.md` ("provides Claude Code with expert knowledge" — re-measured at `a83389fdb`, exactly 1 occurrence). Also fold in the one in-bundle site the §M clusters never named: `phase-5-execute/standards/operations.md`'s `mcp__sonarqube__` tool name (re-measured, exactly 1 hit).
   *Done when:* both sites are reworded to name the capability or the owning rule; a sweep of the touched files finds no remaining assertion that Claude *is* the assistant. ⛔ Legitimate Claude-target material stays and is **declared as such** — this is a rewording plan, not a deletion plan.

   ⚙️ **NARROWED at the 2026-09-09 drain, on measurement at `a83389fdb`.** Three of the five sites the spec was staged with are no longer D1 work, and each disposition is recorded rather than silently dropped:

   | Staged site | Disposition | Account |
   |---|---|---|
   | `pm-documents`'s `content-review.md` second Claude mention | ⛔ **ALREADY CLOSED — do not re-open** | Measures **0** Claude hits. Positive account per the A2 rule: closed by **`30cd8aaf8`** — *fix(targets,bundles): register read_directive and name acts, not host tools* (**PLAN-05**, #1379), a landed plan in this epic. ⚠️ The spec also cites it at `references/content-review.md`; the file is at **`workflow/content-review.md`** — a phantom path, corrected here. |
   | `pm-documents/skills/ref-svg-diagrams/SKILL.md` | ⛔ **ALREADY CLOSED — do not re-open** | Measures **0** Claude hits. Same positive account: `30cd8aaf8` / PLAN-05 (#1379) closed both sites in one commit. |
   | `pm-dev-frontend` README / `css` / `javascript` mentions | ⛔ **DELIBERATE NON-MIGRATION — rewording would make them FALSE** | The three hits are an *attribution*, not an assistant-coupling: *"Anthropic ships an official `frontend-design` skill…"*. Anthropic genuinely ships it. A target-neutral rewording would state something untrue, which is strictly worse than the coupling. Leave them; declare them as Claude/Anthropic-factual if a declaration surface applies. |

   ⭐ **The declared surface is COMPLETE, and that is measured rather than assumed.** The five bundles this spec does not declare — `pm-dev-java`, `pm-dev-java-cui`, `pm-dev-python`, `pm-dev-oci`, `pm-dev-frontend-cui` — carry **zero** occurrences of the bare string `Claude` at `a83389fdb`, checked with a bare pattern rather than a compound one so the zero is not an artefact of the probe. Their absence from the surface is a **checked negative**, not an unchecked one.

   ⚠️ **The two bundle globs stay declared even though D1 now edits neither.** `pm-documents/skills/**` and `pm-dev-frontend/**` remain in the Expected Surface because D1 must still **sweep** them to confirm the closure and the non-migration hold at execution time — the surface declares where the plan LOOKS, and the deliverable states what it CHANGES. ⛔ Do not read the narrowing as licence to skip the sweep: `pm-documents` retains one live Claude mention (`recipe-doc-verify/SKILL.md`), and it is already in the correct target-aware form (`CLAUDE.md` on Claude / `AGENTS.md` on OpenCode). **Rewording that site would REGRESS it.**

   ⛔ **Why this narrowing was needed at all, recorded so the class is visible:** PLAN-05 closed two of this spec's D1 sites while this spec sat staged, and nothing noticed. No mechanism reconciles a LANDED plan's realized footprint against OTHER staged specs' site lists, so a spec's work list decays silently as its siblings land. Re-derive D1's live set at outline regardless of this table — it was accurate at `a83389fdb` and the same decay applies to it.

2. **D2 — The `/plan-marshall` emission sites consume one command-form lookup.** `manage-lessons` emits `/plan-marshall …` launch strings as remediation text. PLAN-07's D5 builds a command-form lookup for `/marshall-steward` and `/sync-plugin-cache`; consume **that** lookup rather than building a second one.
   *Done when:* no `manage-lessons` script carries a literal slash-command form; the lookup is the one PLAN-07 established, verified by reading its definition site.
3. **D3 — `manage-metrics` documentation stops teaching a Claude wire format.** `manage-metrics/SKILL.md` and `standards/data-format.md` carry `message.usage` / `<usage>` / billing vocabulary as the format, while the scripts already consume the normalized `{input, output, cache_read, cache_creation, total}` shape at the runtime boundary. Bring the documentation to what the code actually does, and state the Claude transcript vocabulary as the Claude runtime's own concern.
   *Done when:* neither document states a transcript or billing envelope as the metrics format; both name the normalized shape and point at the runtime for the per-target transcript detail.

## Out of Scope

- **`marketplace/bundles/plan-marshall/**` generally** — PLAN-07's surface. ⛔ D1's single in-bundle site (`phase-5-execute/standards/operations.md`) is carved in **because no §M cluster names it**, so PLAN-07 will not reach it. Touch that one file and nothing else under the plan-marshall bundle except the two `manage-metrics` documents D3 names and the `manage-lessons` scripts D2 names.
- **`manage-metrics`'s scripts** — already normalized by prior work. This is a documentation deliverable.
- **`pm-plugin-development`** — PLAN-06's surface.
- **The `persona-plan-marshall-agent` tool-usage surfaces** (inventory §C row 1) — deliberately gated on WS-05's live validation, and correctly unclaimed. ⛔ Do not fold it in: whether a rewrite is needed at all is a question the protocol answers.

## Claim Labels

- OBSERVED: `pm-requirements/README.md` still reads "provides Claude Code with expert knowledge" — re-derived at HEAD `2cd1a19c`.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e: pm-requirements/README.md still carries exactly ONE occurrence of 'provides Claude Code with expert knowledge'. The file is unchanged since 1c4e6febb. Holds as written, measured not assumed.
- OBSERVED: `phase-5-execute/standards/operations.md` still carries the `mcp__sonarqube__` tool name — **1** hit at HEAD. It sits inside the plan-marshall bundle but is named by no §M cluster, which is why PLAN-07 does not reach it.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e: phase-5-execute/standards/operations.md still carries exactly ONE mcp__sonarqube__ hit, the figure the claim states. The file is unchanged since 1c4e6febb. ⭐ Its in-bundle carve-out also held in practice: PLAN-07 has not run, and PLAN-10 and PLAN-22 both landed inside plan-marshall/** without touching this file - so the claim's premise that no section-M cluster reaches it is now supported by three landings rather than by reading alone.
- OBSERVED: `manage-metrics/SKILL.md` carries **4** hits and `standards/data-format.md` carries **24** hits of the Claude billing/transcript vocabulary. Counts are leads — re-derive before D3.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNCHANGED from the 1c4e6febb reading, and that stability is itself the new information. PRESENCE corroborated, COUNTS still unverifiable for the same reason: the claim's figures (4 in SKILL.md, 24 in data-format.md) were derived with a pattern the claim does not state. The probe over message.usage / <usage> / cache_creation_input_tokens / cache_read_input_tokens returns 35 and 75 at 8fc353b6e - IDENTICAL to the 1c4e6febb reading. ⚠️ data-format.md is one of the files that CHANGED in the interval, so the identical result means the edit did not touch the vocabulary. The divergence is therefore stable rather than drifting, which strengthens the diagnosis: a count published without its method is unreproducible by construction, not merely stale. ⛔ Do not treat 4/24 or 35/75 as the work list - the plan states its own pattern and derives its own set.
- OBSERVED: PLAN-07's D5 covers `/marshall-steward` and `/sync-plugin-cache` emission only; `/plan-marshall` is named nowhere in its deliverables — read at `plans/PLAN-07-runtime-fact-prose-and-single-sources.md` § Deliverables.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e by reading PLAN-07's spec directly rather than from prose. Its Deliverables still name /marshall-steward and /sync-plugin-cache emission and never name /plan-marshall; its Expected Surface still resolves to marketplace/bundles/plan-marshall/** plus named siblings, which structurally cannot reach pm-requirements, pm-documents or pm-dev-frontend. ⭐ Both halves are now confirmed by the PARSER, not by reading: corpus surfaces reports PLAN-07's 10 claimed entries and none lies outside the plan-marshall bundle. The structural gap this claim asserts is real and unchanged.
- OBSERVED: PLAN-07's Expected Surface is `marketplace/bundles/plan-marshall/**`, so the `pm-requirements` / `pm-documents` / `pm-dev-frontend` sites are structurally outside its reach — read at the same file § Expected Surface. This is the evidence that D1 is a real gap rather than a duplicate.
  - verdict: corroborated | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 8fc353b6e by reading PLAN-07's spec directly rather than from prose. Its Deliverables still name /marshall-steward and /sync-plugin-cache emission and never name /plan-marshall; its Expected Surface still resolves to marketplace/bundles/plan-marshall/** plus named siblings, which structurally cannot reach pm-requirements, pm-documents or pm-dev-frontend. ⭐ Both halves are now confirmed by the PARSER, not by reading: corpus surfaces reports PLAN-07's 10 claimed entries and none lies outside the plan-marshall bundle. The structural gap this claim asserts is real and unchanged.
- HYPOTHESIS: the `manage-lessons` half of inventory §C row 3 is the only unclaimed half — the `pm-plugin-development` half (the `/plugin-update-*` strings in `_cmd_apply.py` / `cmd_validate.py`) is absorbed by PLAN-06's D1 "live payloads become target-keyed". Confirm/refute by reading PLAN-06's D1 against those files (verify-at-outline). If PLAN-06 does **not** reach them, fold them into D2 and report the widening.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: OPEN BY DESIGN, verify-at-outline, left open. Both remaining claims are completeness assertions over a set the plan must sweep for itself - the unclaimed half of inventory section C row 3, and the D1 site list across all bundles except plan-marshall and pm-plugin-development. Settling a completeness claim is the LAUNCHED plan's job per the verify-first contract; cleanup can corroborate a named site but cannot establish that a set is complete without performing the plan's own sweep. ⚠️ One input HAS moved since staging and the plan should know it: PLAN-06 landed 45 files across pm-plugin-development, so the exclusion of that bundle from the D1 sweep is now a decision about already-target-aware code rather than about untouched code. Recorded as unverifiable, which does not block emission.
- HYPOTHESIS: the D1 site list is complete — confirm/refute by sweeping all bundles except `plan-marshall` and `pm-plugin-development` for Claude-as-assistant prose (verify-at-outline). Extra hits are folded in and reported.
  - verdict: corroborated | checked_at: a83389fdb | by: multiplattform/analyze | rescoped: n/a | evidence: MEASURED, not inferred, at a83389fdb - and the declared surface is COMPLETE. The claim asserts the D1 site list is complete and instructs a sweep of all bundles except plan-marshall and pm-plugin-development. PLAN-12 declares only three of the eight non-excluded bundles (pm-requirements, pm-documents, pm-dev-frontend), which looked like a gap. It is not: the five UNDECLARED bundles - pm-dev-java, pm-dev-java-cui, pm-dev-python, pm-dev-oci, pm-dev-frontend-cui - carry ZERO occurrences of the bare string 'Claude', verified with a bare pattern rather than a compound one to avoid a false zero. Their absence from the surface is therefore a CHECKED NEGATIVE, not an unchecked one. ⚠️ But the same sweep found the site list itself is now largely STALE - see the epic decision recorded alongside this stamp: two of the three named pm-documents/pm-requirements sites are already closed, and the three pm-dev-frontend hits are an Anthropic-ships ATTRIBUTION whose target-neutral rewording would make it FALSE. D1 must re-derive its live set before scoping; the completeness of the SURFACE is settled, the contents of the WORK LIST are not.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-requirements/README.md` — D1, **the one site D1 still EDITS** (1 occurrence re-measured at `a83389fdb`)
- OBSERVED: `marketplace/bundles/pm-documents/skills/**` — **SWEEP-ONLY as of the 2026-09-09 narrowing.** Both originally-named sites (`ref-documentation/workflow/content-review.md` — note: `workflow/`, not the `references/` this spec first cited — and `ref-svg-diagrams/SKILL.md`) measure **0** Claude hits at `a83389fdb`, closed by `30cd8aaf8` / PLAN-05 (#1379). Declared so D1 can CONFIRM the closure. ⛔ `recipe-doc-verify/SKILL.md` retains one mention already in the correct per-target form — rewording it would REGRESS it.
- OBSERVED: `marketplace/bundles/pm-dev-frontend/**` — **SWEEP-ONLY as of the 2026-09-09 narrowing.** The three hits (README, `css/SKILL.md`, `javascript/SKILL.md`) are the *Anthropic ships an official `frontend-design` skill* attribution — a DELIBERATE NON-MIGRATION, because a target-neutral rewording would make them false. Declared so D1 can confirm the disposition, not to edit them.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` — D1, **this file only**
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**` — D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md`, `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — D3
- OBSERVED: the corresponding `test/` subtrees for every touched script

## Dependencies and Sequencing

- Depends on: **PLAN-05**. ⛔ Run after it. PLAN-05's D4 edits `pm-documents`, `pm-dev-frontend` and `pm-requirements` files for a *different* reason (normative tool-invocation prose); this plan edits the same bundles for assistant-naming prose. Running second means re-deriving what PLAN-05 left.
- Depends on: **PLAN-07** for D2's command-form lookup. ⛔ D2 is unbuildable before PLAN-07 lands — there is no lookup to consume. If PLAN-07 has not landed, **report D2 as blocked and ship D1 and D3**, rather than building a second lookup.
- Overlaps with: **PLAN-07** on the plan-marshall bundle (three narrowly carved files). ⛔ Not concurrent.
- Overlaps with: **PLAN-06** conditionally, if the `/plugin-update-*` half turns out unclaimed.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- The D1 sweep re-run at verification time over the changed tree.
- **A cold read of the rewritten `manage-metrics/standards/data-format.md`:** a reviewer reads it without the plan in context and answers "what shape does `manage-metrics` consume, and where does a transcript get parsed?" An answer naming `message.usage` or a transcript envelope means D3's wording failed.
- D2's lookup consumption verified by reading PLAN-07's definition site, not by asserting the literal is gone — a literal can be gone and a second lookup still built, which is the failure this check catches.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-12-cross-bundle-assistant-prose.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write, including every coupling-inventory row retirement.
