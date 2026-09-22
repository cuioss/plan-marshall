# PLAN-CIS-025: The Project-Local Artifact Provider — pm-plugin-development owns `.claude/**`

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The project-local artifact tree is attributed inconsistently: `.claude/skills/**` resolves to the
`plan-marshall` module through core's hardcoded prefix map, while `.claude/commands/**` — the
sibling tree, same kind of artifact — resolves to `module: null`. One tree, two answers, and the
non-null one is produced by core holding domain knowledge it should not hold.

`pm-plugin-development` is the bundle that understands Claude Code plugin artifacts — it already
implements `discover_modules()` bundle-based and owns `plugin-doctor`, `tools-marketplace-inventory`,
and the plugin architecture standards. Give it the attribution claim for the whole project-local
artifact surface through PLAN-CIS-023's seam, and settle the ownership question the core comment
deferred.

## Deliverables

1. **Project-local artifact claim** through PLAN-CIS-023's seam, covering the surface uniformly:
   `.claude/skills/**`, `.claude/commands/**`, and `.claude/agents/**` if present. ⛔ **Derive the
   set of `.claude/` subtrees from the filesystem — do not enumerate it from this spec.** The three
   named here are what the orchestrator saw; the population is what exists.
2. **The ownership decision, made explicitly and recorded.** Core's comment calls
   `plan-marshall` "the operator-confirmed owner" of `.claude/skills/**`. This plan may move that
   to `pm-plugin-development`, but ⛔ **the move is a decision, not a refactor side effect** —
   record it, and surface it if the two readings conflict. ⚠ The distinction that matters: these
   artifacts are *authored in* the meta-project and *understood by* pm-plugin-development. Owner =
   who understands the content, consistent with why the seam exists at all.
3. **Consistency verification across the whole tree.** After the claim lands, every path under
   every `.claude/` subtree must resolve to the same module, and a path under none of them must
   report unclaimed rather than falling through to a stale prefix hit. ⭐ **Derive this check from
   the filesystem population, not from a fixed list of probe paths** — standing rule 4, and
   standing rule 5: N probes of a pure prefix function is one assertion repeated N times. The
   check that bites walks the actual tree.
4. **Documentation** — the ownership contract in `pm-plugin-development`, and the project-local
   attribution row in `doc/concepts/code-intelligence.adoc`.

## Claim Labels

- **OBSERVED** — `_PROJECT_LOCAL_PREFIX_MAP = (('.claude/skills', 'plan-marshall'),)` at
  `_architecture_core.py`:742. Its comment states the meta-project's `.claude/skills/**` tree
  "is owned by the `plan-marshall` module — the operator-confirmed owner", and the mapping is
  guarded by module existence at `:765` so consumer projects are unaffected.
- **OBSERVED (probed against HEAD 2026-08-01)** — `.claude/skills/sync-plugin-cache/SKILL.md` and
  `.claude/skills/build-fix-commit/SKILL.md` both → `module: plan-marshall`;
  `.claude/commands/marshall-steward.md` → `module: null`.
- **OBSERVED** — `_cmd_client_handlers.py`:754: project-local dotfile trees "are never inventoried
  at all", so the prefix map is the sole resolution path for them.
- **OBSERVED** — `pm-plugin-development` is listed as an existing `discover_modules()` implementor
  ("Bundle-based (marketplace bundles)") in `extension-api/standards/module-discovery.md`
  § Existing Implementations.
- **HYPOTHESIS (asserted absence — verify like a presence)** — `.claude/agents/**` exists in this
  repo. Confirm/refute by listing `.claude/` at outline. ⛔ An unverified absence produces either a
  dead claim or an uncovered tree; **this epic has recorded the absence-verification obligation as
  standing rule 4.**
- **HYPOTHESIS** — moving `.claude/skills/**` from `plan-marshall` to `pm-plugin-development`
  breaks no consumer. Confirm/refute by enumerating consumers that branch on the returned module
  name for a `.claude/` path (verify-at-outline). ⚠ The project-local skills' **tests live under
  `test/plan-marshall/**`** per the core comment — so a move may split an artifact from its tests
  across two modules. **Decide whether that is acceptable before moving; it may be the reason the
  original owner was chosen.**
- **Verify-first clause**: D2's ownership move is reversible only at the cost of a second landing.
  Settle the artifact-vs-test-module split against the implementing source before scoping.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/` — extension manifest and `extension.py`
- **OBSERVED**: `doc/concepts/code-intelligence.adoc` — project-local attribution row
- **OBSERVED**: `test/pm-plugin-development/` — tests
- ~~**HYPOTHESIS**: `_architecture_core.py` — only if PLAN-CIS-023 left the retired prefix map's last entry in place.~~ ✅ **SETTLED 2026-08-08 — ANSWER: PLAN-CIS-023 (#1072) ALREADY RETIRED IT. THIS PLAN TOUCHES NO CORE FILE.** Verified first-party: `_architecture_core.py` carries no `.claude/skills` literal and no prefix-map constant. ⇒ **The open question this spec asked outline to settle is settled here** — do not re-derive it, and **do not budget a core edit.** ⛔ **The spec's own escape clause now binds harder, not softer**: *if this plan finds itself editing core for any reason, loop back — the seam was incomplete.* With the map confirmed gone, a core edit is no longer an expected contingency but a **signal that CIS-023's seam did not cover this case.**
- ⚠ **Coordination added 2026-08-08 — `PLAN-CIS-019`**: `.claude/` is one of two literals in `_BOOKKEEPING_PREFIXES`, which exists at **two** sites (`check-manifest-consistency.py:49`, `check-routing-decisions.py:65`) and which CIS-019 is replacing with a `build_map` lookup. Different map, different files — **not a duplicate** — but that plan changes how `.claude/**` paths are classified downstream. **Re-check the interaction at outline.**

## Dependencies and Sequencing

- **Depends on**: **PLAN-CIS-023** (the attribution seam). ⛔ Hard gate.
- **Overlaps with**: **PLAN-CIS-003** (marketplace-dependency-resolver), **PLAN-CIS-006**
  (validate-precision), **PLAN-CIS-021** (self-review duplicate-claimable-key) — all on
  `pm-plugin-development`. ⛔ **Never pair with any of them.** ⚠ PLAN-CIS-003 and PLAN-CIS-006
  touch `tools-marketplace-inventory` and `_dep_detection.py`; PLAN-CIS-021 touches
  `ext-self-review-plan-marshall`. This plan touches `plan-marshall-plugin`. **Re-verify the file
  sets at emit time** — the bundle-level collision may be avoidable at file level, but the epic
  has recorded that pairing within `pm-plugin-development` needs the file-set check first.
- **Adjacent to**: `manage-architecture` core — claimed through the seam, not edited here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-025-project-local-artifact-provider.md"
```

## ⭐⭐ MEASURED CONSEQUENCE — "structured queries first" SILENTLY degrades to a whole-tree fallback (folded 2026-08-03 from `…-009`, PR #1086)

**The structured index cannot answer for `.claude/skills/`** — the very artifacts this plan exists to
claim. ⇒ A caller obeying the standing *"structured queries first"* rule asks the index, gets nothing,
and **falls back to a whole-tree scan** — which is the expensive path the rule exists to avoid.

⛔ **The word that matters is SILENTLY.** The caller cannot distinguish *"the index looked and there
is nothing there"* from *"the index does not cover this path"*, so the fallback reads as a correct
answer to a completed query rather than as a coverage gap. ⭐ **This epic's flagship archetype landing
on the epic's own flagship rule.**

⇒ ⭐ **This raises the plan's priority and sharpens its value case, which was previously stated as
consistency**: an unclaimed path is not merely untidy, it is a **measured token cost** under the
Priority-1 directive — every query against it pays whole-tree prices, on every plan, forever. **Note
the direction: this is the good kind of saving** (bytes that buy nothing), not an examination cut.

⛔ **Deliverable implication**: claiming the path is necessary but not sufficient. The resolver must
be able to say **"not covered"** distinctly from **"covered, no matches"**, or the next uncovered
path reproduces this silently. ⚠ **`PLAN-CIS-001` shipped exactly this discipline** — `search
--content` returns `files_scanned` / `unreadable` / `truncated` / `elided` — **reuse that contract
rather than inventing a second one.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
