# Check: cross-check-synthesis (facet-completeness critic, runs LAST)

The **facet-completeness critic** that operationalizes the SKILL.md **Step-4b**
review-completeness gate. Every other check reports signals over ONE facet of the
corpus — a token-trend regression, a heavy build, a finalize-heavy token share, a
CI re-run, an argparse-rejection spike. A real systemic problem usually shows up
not as a single loud row but as a **chatter of related single-check signals
across facets** that no single check's adjudication resolves. This check joins
the OTHER checks' **retained structured results** (the `rows` / `result` dicts
they computed, NOT their emitted TOON strings) and reports the cross-check
**couplings** those single rows individually miss.

The deterministic computation lives in `scripts/audit.py`
(`cross_check_synthesis` / `emit_cross_check_synthesis_block`); this sub-document
is the interpretation guide. It is a **cross-plan** check (one row per coupling,
not per plan) and it MUST run **last** — it consumes the other checks' results,
so it is the final entry in `CHECK_NAMES`.

## Why it consumes results, not strings

The other checks emit TOON for the orchestrator to read. Re-parsing that TOON to
recover the couplings would be brittle and would duplicate the parse the script
already did. Instead, `run_checks()` retains each upstream check's structured
result in an `all_results` dict at computation time and passes it to
`cross_check_synthesis(all_results)`. The synthesis reads the structured fields
directly (`flags` lists, `regression` string, `data_confidence` buckets,
`mismatch` cells) — the same values the upstream emitters render.

When the check is invoked alone via `--check cross-check-synthesis`,
`run_checks()` still **computes** every upstream result it depends on (without
emitting those upstream blocks) so the synthesis can fire. When synthesis is NOT
selected, the upstream computation/emit path is byte-for-byte unchanged.

## The five couplings

Each coupling carries a **qualifying caveat** — the condition under which the
fired coupling is a genuine cross-facet signal rather than a coincidence. A fired
coupling is a `genuine` signal (D1 `severity` column); a coupling that did not
fire is carried as `informational` so the read-out shows every coupling was
evaluated.

| Coupling | Fires when | Reads from | Qualifying caveat |
|----------|------------|------------|-------------------|
| `trend_empty_untrustworthy` | `token-efficiency-trend` `regression` is **empty** AND `input-integrity` reports ≥1 `data_confidence: blind` plan. | token-efficiency-trend, input-integrity | An empty regression over blind-execute plans is **floor, not truth** — the trend saw no rise because execute tokens were never recorded, not because spend is flat. The empty regression is NOT itself a finding; the coupling marks it untrustworthy. |
| `churn_explains_walltime` | A plan flagged sequence `non_minimal_build` / `build_churn` whose build wall-clock (`total_build_seconds`) sits in the corpus **upper half** (≥ median over build-running plans). | sequence-and-build-minimality | Build cost is correlated against **wall-clock** because the recorded token metric **cannot see it**. A build runs as a subprocess (zero model tokens during the run) and is one tool-call turn among many; its real token cost is a full-context `cache_read` round-trip — plus a `cache_creation` re-cache penalty when the build exceeds the ~5-min prompt-cache TTL — and **both are excluded from `total_tokens` (input+output only; see the token-economics measurement caveat)**. So build token cost is invisible to the metric, and correlating churn against it was noise. **Do NOT read a fired coupling as "builds are token-cheap"** — their cost is real but unrecorded. The *visible* token over-spend on these plans is generation volume (`long_session`) + execution-context fragmentation, not builds. |
| `qgate_gap_chain` | A plan flagged quality-chain `no_qgate6` / `auto_review_only` that ALSO carries sequence `ci_rerun` OR token-economics `finalize_heavy`. | quality-chain, sequence-and-build-minimality, token-economics | A missing self-review surface co-occurring with a CI re-run / heavy finalize is the **shift-right tax** — the PR round-trip paid for what an earlier gate could have caught. |
| `argparse_signature_cluster` | recurring-pattern argparse-shaped signatures correlate with global-log ERROR / argparse-rejection counts AND quality-verification unfiled signatures — **collapsed to ONE candidate**. | recurring-pattern-detector, global-log-analysis, quality-verification-report | The three facets are three views of **ONE** source-keyed argparse drift — file ONE source-keyed lesson, not one per facet (per the SKILL.md source-keyed argparse-rejection rule). |
| `scope_underestimate_cost` | A plan flagged scope-estimate-accuracy under-estimation (`mismatch`) that ALSO sits in the high tokens-per-file tail (≥ corpus-median `tokens_per_file`) OR carries a task-count outlier. | scope-estimate-accuracy, token-economics, task-count-efficiency | An under-estimated scope **predicts** the over-spend — the coupling names the predicted-vs-actual gap, not a fresh finding. |

## Emitted columns

```
couplings_evaluated: N
couplings_fired: F
genuine_signal_count: G
rows[N]{coupling,fired,caveat,detail,severity}
```

| Column | Meaning |
|--------|---------|
| `coupling` | The coupling name (one of the five above). |
| `fired` | `true` when the cross-facet correlation surfaced, else `false`. |
| `caveat` | The qualifying caveat — the condition under which a fired coupling is genuine. |
| `detail` | The cross-facet evidence: the plan ids and the per-facet counts the coupling joined. |
| `severity` | Uniform D1 severity column: `genuine` when the coupling `fired`, `informational` otherwise. |

`genuine_signal_count` equals `couplings_fired`: every fired coupling is a genuine
cross-check signal the per-check adjudication must resolve before dormation.

## How the orchestrator interprets the rows

The synthesis block is read AFTER the individual check blocks, as the Step-4b
completeness critic:

- **A fired coupling is a cross-check signal the per-row adjudication must
  resolve.** It is not a new finding on top of the underlying single-check rows —
  it asserts that those rows COUPLE, so they must be adjudicated together, not in
  isolation. Read the coupling's `caveat` first: it states the skepticism the
  underlying checks' own caveats already demand.
- **`trend_empty_untrustworthy`** — do NOT clear the token-trend "no regression"
  result as healthy. The blind execute plans named by input-integrity's
  `blind_plan_ids` floor the trend; the honest read is "no measurable regression
  among fully-recorded plans; the blind plans are floored". This coupling
  enforces the input-integrity no-false-healthy obligation across the trend facet.
- **`churn_explains_walltime`** — the named plans' build redundancy wasted
  **wall-clock**, corroborated by a build wall-clock (`total_build_seconds`) in the
  corpus upper half. Read against the three structural caveats in
  `checks/sequence-and-build-minimality.md`. The correlation is against wall-clock
  because the recorded token metric **cannot see** build cost: a build's real token
  cost — a full-context `cache_read` round-trip, plus a `cache_creation` re-cache
  penalty when the build exceeds the ~5-min cache TTL — is **excluded from
  `total_tokens`** (input+output only). **Do NOT read this as "builds are
  token-cheap"**; their cost is real but unrecorded. The *visible* token over-spend
  lives in generation volume (`long_session`) + execution-context fragmentation —
  separate axes the metric can partly see.
- **`qgate_gap_chain`** — the named plans paid the shift-right tax. Cross-read
  with the quality-chain shift-left tiers: a Tier-1 `auto_review_only` finding on
  a plan that also re-ran CI is the strongest avoidable-rework signal.
- **`argparse_signature_cluster`** — collapse to ONE source-keyed candidate. Do
  NOT file one lesson per facet (recurring-pattern, global-log, quality-verification
  each surface the same drift). Route the single candidate through the three-gate
  policy keyed to the **source notation** that argparse rejected, per SKILL.md
  Step 4's source-keyed argparse-rejection rule.
- **`scope_underestimate_cost`** — the under-estimated scope predicted the
  over-spend. The file-worthy signal is the scope-estimation gap recurring across
  plans, not each plan's individual over-spend (which the token-economics check
  already covers under its canonical lesson).

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; an `informational` (non-fired) coupling is dismissed
with the cited reason that its facets did not co-occur.

## Relationship to the Step-4b completeness gate

This block **operationalizes** the SKILL.md Step-4b review-completeness gate. The
gate requires that every genuine-signal row be adjudicated with verdict and
evidence and that no "all healthy" claim be reached over blind-input plans. The
synthesis block is the deterministic surface that makes a premature "no findings"
conclusion impossible: a fired coupling is a `genuine` row the gate's first
checkbox ("every genuine-signal row adjudicated") must account for, and
`trend_empty_untrustworthy` is the structural enforcement of the gate's
blind-plan checkbox across the trend facet. Dormation stays BLOCKED until each
fired coupling is resolved in the adjudication.

## Critical rules

- The script is the single source of truth for the coupling computation. Do not
  re-derive a coupling inline in chat — read the emitted `fired` / `detail` /
  `caveat` cells.
- The check reads the other checks' RETAINED RESULTS, never their emitted
  strings. If an upstream check's result shape changes, update the field reads in
  `cross_check_synthesis` rather than re-parsing TOON.
- The argparse-signature grammar (`_SYN_ARGPARSE_SIG_RE`) and the
  median-tokens-per-file tail are module-level deterministic predicates. If the
  recurring-pattern signature wording or the token-economics row shape changes,
  edit `scripts/audit.py`.
- This check is read-only; it never edits `.plan/` files.
- It MUST remain the last entry in `CHECK_NAMES` — it depends on every upstream
  result being computed first.
