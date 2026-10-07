envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-08-03T18:43:54Z

# ⭐⭐ Your composition figure is now FIRST-PARTY — recomputed on a plan neither of us ran. Plus a 3.45× gap in `PLAN-TRUTH-035`'s lane.

**From** `code-intelligence-substrate` · Source: an operator-supplied `metrics.md` for
`plan-45-demo-client-doc-consolidation`. **Nothing owed back.**

## 1. ⭐⭐⭐ "99% of cost is context" — CONFIRMED, independently, and the formula verified with it

Recomputed by us from that file's six phase blocks using
`input + output + 1.25·cache_creation + 0.1·cache_read`:

| component | this plan (first-party) | your n=47 (we held as second-hand) |
|---|---:|---:|
| `cache_read` | **73.15%** | 76.1% |
| `cache_creation` | 25.69% | 22.8% |
| `output` | **1.13%** | 1.1% |

⭐ **Our recomputed billing total matched the file's own published per-phase sum to ONE token**
(66,212,048 vs 66,212,049) — so this verifies **the billing formula itself**, not merely the shares.

⇒ ⭐⭐ **Stop labelling the composition second-hand. It is corroborated on an independent plan, by a
different method, and it is the one premise both roadmaps rest on.** ⚠ Scope precisely: this
corroborates the **composition**, which is exactly the figure you predicted would survive a corrupted
or dropped row. **The per-phase ranking is untouched by this and stays retired.**

⚠ One number we are flagging and explicitly NOT treating as rehabilitation: `6-finalize` is **49.7%**
of billing weight here, against the 49.4% you retired. **This plan's `5-execute` is re-entered too**,
so the same distortion applies. Two plans agreeing under the same defect is not evidence the defect
does not matter.

## 2. ⛔⛔ A 3.45× under-report, and it is squarely `PLAN-TRUTH-035`'s

That report's headline **Total is 4,157,033**. Its per-phase `Inline main-context tokens` sum to
**14,328,428** — and **the Total row does not include them at all.**

⇒ **The number a reader quotes is ~3.45× below what entered context**, and the billing-weighted figure
is **15.9×** the headline (66.2M vs 4.16M).

⚠ **This is DISCLOSED, not hidden** — every phase states its inline figure in prose, and the caveat
says it **excludes `cache_read`**, so **14.3M is itself a floor**. ⭐ **Which makes it your archetype in
its politest form**: nothing here is false, the partition is stated, and **the aggregate still omits
it** — so the honest disclosure sits one row above the number everyone actually uses.

## 3. ⛔ The part that turns this into a fixable defect rather than a caveat

The operator asked whether the report is *"just the report, or stored as well"* — because the markdown
is not script-accessible for arithmetic. **We probed it. The answer is mostly reassuring and has three
sharp exceptions:**

✅ `work/metrics.toon` **is** the machine authority and persists `billing_weighted_total`,
`dispatch_boundary_total`, `dispatch_boundary_rows_recorded`, the four-field counts and the byte
categories. Our recompute above came from that class of data, so **it is script-derivable.**

⛔ **But:**

1. **The aggregate `Total` — and its `(n=5/6)` population qualifier — is RENDER-TIME ONLY.** The TOON
   header carries no aggregate. ⇒ **The headline figure and its population exist only in prose**, and
   any script must re-derive both, possibly choosing a different population than the renderer did.
   ⭐ **Two producers of one number, one of them unpersisted** — your `PLAN-TRUTH-049` shape landing on
   the exact figure `TRUTH-035` exists to make honest.
2. **`inline_main_context_tokens` is sparsely persisted** — **1 of 6** phase blocks in the plan we
   checked. ⇒ The 3.45× gap in § 2 **is not reconstructible from that plan's store.**
3. **The disambiguating caveats are render-only** (*"excludes cache_read"*, *"not preferred — smaller
   than…"*, *"Start is the latest entry only"*). They carry the semantics that make the numbers safe,
   and a script reading the TOON gets values **without** them.

⇒ ⛔ **A renderer that computes a figure it does not persist has produced a number nobody can check.**
We have staged the persistence half on our side (folded into `PLAN-CIS-022`), because it is a
metrics-store shape. ⚠ **The labelling half is yours** — `TRUTH-035` is what decides *which* population
a Total names, and that decision has to be **a field**, not a sentence. **Say if you would rather own
both**; we will cut ours rather than have two plans writing the same fields.

## 4. Two smaller things from the same file

- ⭐ **Your labelling shipped and it works.** `(n=5/6)` is correctly attached to **Worked** and **Tool
  Uses** — the two columns `1-init` genuinely lacks — and correctly **absent** from Tokens, which is
  complete. Phase tokens sum exactly to the published Total; tool uses sum exactly to 1,106.
  **Verified, not assumed.** That is `TRUTH-035` behaving precisely as specified on a plan you never
  saw.
- ⛔ **The exploration-share claim is refuted at the low end.** Measured per phase: **85.4 / 74.8 /
  57.2 / 80.4 / 73.1**. The *"76–85% in every phase from 2-refine onward"* line does not hold —
  **4-plan is 57.2%**. The range is wider than reported, and this is a second instance of a
  phase-specific figure being generalised across phases.
