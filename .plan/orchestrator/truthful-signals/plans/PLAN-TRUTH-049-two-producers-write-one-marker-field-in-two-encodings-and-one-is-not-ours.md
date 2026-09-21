# PLAN-TRUTH-049: two producers write one marker field in two encodings, and one of them is not ours

epic: truthful-signals
workstream: WS-01

## ⛔⛔ READ THIS FIRST — the observation is CONFIRMED, the reported IMPACT is REFUTED

`code-intelligence-substrate` filed this (`-017`) with the impact stated as: *the documented 7-day
`.orphaned_at` retention is silently false for whichever half the consumer cannot decode.*

**I verified both halves first-party. The observation holds exactly. The impact chain does not exist.**
⭐ **The sender labelled the impact as NOT ESTABLISHED and explicitly wrote "do not report any of them
as the impact until the consumer is read."** ⇒ **This spec is what reading the consumer produced.** The
discipline worked; the finding is smaller and stranger than it looked.

## OBSERVED — re-derived first-party, whole population

✅ **The split reproduces to the file**: 400 markers under `~/.claude/plugins/cache/`, **180 ISO-8601 /
220 raw epoch-ms / 0 other**. Ranges **overlap** — ISO `2026-07-27T23:35:57Z … 2026-08-03T07:09:44Z`
strictly contains epoch-ms `2026-07-28T08:50:54Z … 2026-08-02T07:08:47Z`. ⇒ **Not a format migration.
Both writers were live across the same six-day window.**

### ⛔ Refutation 1 — nothing anywhere parses the marker's CONTENT

Every consumer in this repo tests **`.exists()`**:

- `script-shared/scripts/marketplace_bundles.py:39` — *"The ONE place the `.orphaned_at` marker is
  read"*: `live = [d for d in eligible if d == pinned or not (d / '.orphaned_at').exists()]`
- `tools-script-executor/scripts/generate_executor.py:530` — the same predicate, mirrored

**No `read_text`, no `strptime`, no `int()`, no comparison against a cutoff — at any site.**

⇒ ⛔ **The reported failure modes cannot occur.** *"decode-as-ISO ⇒ 220 fail to parse"*,
*"decode-as-epoch ⇒ 180 fail to parse"*, and the *"epoch-seconds ⇒ year 58561, never collectable"*
scenario **all require a decoder, and there is none.**

### ⛔ Refutation 2 — the 7-day retention contract the impact rests on is not the contract

`manage-config/standards/data-model.md:477` and `marshall-steward/scripts/cache_retention.py:31` both
state it plainly:

> The `.orphaned_at` marker is **advisory** and is **NEVER consulted as a keep-or-delete oracle**.

Retention is a **keep-UNION** over `plugin_cache_keep_versions` / `plugin_cache_keep_days`, newest-on-disk,
`system.provisioned_version`, the `dist-manifest.json` dir, and the dir the sweep executes from.
**The knobs only ever WIDEN the keep-set; neither can force a delete.**

⇒ **There is no timestamp-driven 7-day expiry to be silently false about.**

⭐⭐ **And this refutes MY OWN ledger, not only the sender's.** Our memory recorded *"7-day
`.orphaned_at`; keep-oracle = no marker"*. **The first half is wrong** (retention is the union, not the
marker) and **the second half is right but for liveness, not retention** — the marker IS the
liveness/selector oracle, which is a different question from collection. ⇒ **Two epics carried the same
wrong model of this field**, which is a better explanation for why the finding looked alarming than
anything in the cache.

### ⭐⭐ What genuinely survives, and it is the interesting part

**Our source contains exactly ONE writer, and it is ISO**:
`generate_executor.py:1812` → `marker_ts = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')`, written at
`:1825`. A whole-repo sweep for `orphaned_at` returns 12 files — 5 tests, 4 docs, 3 scripts — and **no
second writer.**

⇒ ⛔ **The 220 epoch-ms markers — 55% of the corpus — are written by a producer that is not in this
repository.** The overlapping live ranges make "a legacy remnant of ours" untenable. **The remaining
candidate is the Claude Code plugin system itself.**

> **We share a filesystem field with a producer we do not own, in an encoding we did not agree, and we
> only survive it because we never look at the value.**

⇒ **The defect is a latent one with a precise trigger**: *the first consumer that reads the value
breaks*, and it breaks on 55% of the corpus. ⭐ This is the epic's theme in an unusual direction — **not
a confident signal hiding a caveat, but an UNDEFENDED contract whose safety is accidental.**

## ⛔⛔ AND THEN MY OWN RECORD REVIVED THE IMPACT — in the OPPOSITE direction

Refutation 2 above is correct **about our retention code and only about it**. Our own memory
(`project_plugin_cache_orphan_gc`, researched 2026-07-13, **GC verified working 2026-07-14**) records
the other half:

> **Claude Code's automatic GC is ACTIVE**: superseded version dirs get a `.orphaned_at` marker
> **(epoch-ms)** and are auto-deleted **~7 days later**.
> *Verified 07-14: the cache shrank **428MB → 99MB** and every marker dated 07-07..12 was GONE.*

⇒ ⭐⭐ **There IS a 7-day timestamp-parsing consumer. It is not ours — it is the field's OWNER.** And it
**expects epoch-ms**, which is the format WE do not write.

> ⛔ **The exposure inverts.** The sender feared *our* consumer choking on *their* 220 epoch-ms markers.
> The live risk is **Claude Code's GC choking on OUR 180 ISO markers** — dirs we mark as orphaned that
> **may never be collected**, silently regrowing the cache we shrank by 329MB.

⭐ **This also promotes the elimination argument to near-certainty**: the memory independently names
Claude Code as the epoch-ms writer, from research done three weeks before this finding. Two independent
routes to the same producer.

### ⭐ A DECISIVE, CHEAP TEST — and today the data is genuinely INCONCLUSIVE

Oldest markers at the 2026-08-03 ~07:10Z read: **ISO `2026-07-27T23:35:57Z` (6d 7h)**, **epoch-ms
`2026-07-28T08:50:54Z` (5d 22h)**.

⛔ **Neither format has yet reached 7 days**, so the absence of aged ISO markers proves **nothing** —
it is equally explained by "ISO is collected normally" and by "ISO is never collected but nothing has
aged out yet." ⚠ **Do not read the current corpus as evidence either way.**

✅ **The discriminator arrives on its own**: re-read after **2026-08-04 ~00:00Z**, when the oldest ISO
marker crosses 7 days.

| Observation then | Conclusion |
|---|---|
| The `2026-07-27T23:35:57Z` dir is **gone** | Claude Code parses both formats ⇒ **finding is cosmetic**, close D0–D2 as a docs item |
| It **survives** while epoch-ms dirs of similar age are collected | ⛔ **Our ISO markers are un-collectable** — a real, quantified leak, and D0 becomes urgent |

⛔ **D0 MUST run this test before scoping anything else.** It costs one directory listing and it decides
whether this plan is a docs correction or a cache-growth defect.

⚠ **Note what nearly happened**: I had already written *"there is no timestamp-driven expiry to be
silently false about"* — **true of our code, false of the system.** ⇒ *A refutation scoped to the
repository is not a refutation scoped to the behaviour.* The sender's caution about unread consumers
applied to **me**, one layer out, and I had to be caught by my own three-week-old research rather than
by the sweep I had just run.

## Deliverables — deliberately small. This is a contract item, not a repair.

0. **D-1 — GATE, AND IT RUNS FIRST: the aged-ISO-marker test above (after 2026-08-04 ~00:00Z).**
   ⛔ **Everything below is scoped by its outcome** — a docs correction or a cache-growth defect. **Do
   not size the rest of this plan before it.**
1. **D0 — GATE: identify the second writer, or establish that it is external.** ⛔ **Both outcomes are
   acceptable results; an unidentified writer is not.** ⭐ **The expected answer is Claude Code's plugin
   GC**, now supported by two independent routes (the exhaustive repo sweep, and our own 2026-07-13
   research naming it as the epoch-ms writer). Record it as a **shared-field dependency** — the fix is
   then a *contract*, not a code change. ⚠ **Do not "normalise the corpus"** before this: rewriting 220
   markers a foreign producer owns would be undone by that producer and would look like a fix.
   ⛔ **If D-1 shows our ISO markers are un-collectable, the remedy inverts** — we must write **epoch-ms
   to match the owning consumer**, not document that the content is unread.
2. **D1 — state the encoding, or state that we do not depend on it.** ⭐ **The honest answer is probably
   the second**, and saying so is the deliverable: *"`.orphaned_at` is an EXISTENCE marker; its content
   is never read and MUST NOT be relied on."* That converts today's accidental safety into a stated
   invariant. ⛔ Put it where the liveness contract already lives (`marketplace_bundles.py` module
   docstring + `data-model.md`), not in a new document.
3. **D2 — a test that FAILS if a consumer starts parsing it.** The invariant D1 states must be
   enforceable, or it decays into the same undocumented convention it replaces. ⛔ **Verify it fails
   against a deliberately-added parsing consumer** — a guard never observed to fire is not a guard
   (archetype n≥5).
4. **D3 — correct the two wrong records this exposed.** (a) The *"7-day `.orphaned_at` retention with
   keep-oracle = no marker"* model, carried in BOTH epics' memory. (b) `.in_use` as a pin oracle —
   see below. ⚠ **Correct them at the source, not by adding a note next to them.**

⭐ **Four deliverables, well under the bloat threshold, and that is deliberate**: after the refutations
there is very little to build. ⛔ **Resist re-inflating it** — the value here is the corrected model,
not a normalisation project.

## ⭐ Adjacent, folded because it corrects a record we act on

**`.in_use` is no longer a pin oracle.** ✅ **Verified**: it is present on **7** versions —
`0.1.1194, 1222, 1240, 1279, 1282, 1286, 1288` — i.e. **every version any past manual repair touched**,
because the stale-delete raises `PermissionError` on macOS and is skipped. It is a **repair-residue
trail**, not a currency signal.

⛔ **This contradicts our standing note that `.in_use` is "the second marker that identifies the pin".**
**`installed_plugins.json` is the only honest read.** Folded into D3(b).

✅ **Also verified while here — the pin state is currently CORRECT**: `installed_plugins.json` pins
`0.1.1288`, and `0.1.1288` is the **only** unmarked dir of 41. `unmarked == [pinned_version]` holds, so
the ~daily inversion is **repaired as of 2026-08-03**. ⚠ It has recurred daily; this is a snapshot, not
a resolution.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, whole population)**: 180/220/400, the overlapping ranges,
  the single ISO writer at `generate_executor.py:1812`, the `.exists()`-only reads at
  `marketplace_bundles.py:39` and `generate_executor.py:530`, the advisory-only contract text, the 7
  `.in_use` dirs, and the pin/unmarked identity.
- ⚠ **A DISCREPANCY I could not resolve and am not papering over**: the sender cited
  `plan-marshall/0.1.1288 = 1785739333150` as an epoch-ms example. **At my read, `0.1.1288` is UNMARKED
  and is the pin.** The 180/220/400 split matched theirs **exactly** while the named example moved, and
  the ISO max advanced from `06:42:24Z` to `07:09:44Z` — so **the corpus churned between the two reads
  in a way that preserved the split.** ⛔ Either the example was mis-transcribed or a marker was removed
  and another added within ~27 minutes. **Settle this at D0** — it bears directly on how fast the
  foreign producer writes.
- **INFERENCE, explicitly labelled**: that the epoch-ms writer is the Claude Code plugin system.
  ⛔ **Not established — it is the only remaining candidate after an exhaustive repo sweep, which is an
  elimination argument, not an observation.** D0 must confirm it.
- ⛔ **REFUTED (both by me, first-party)**: the parse-failure impact chain; the 7-day timestamp expiry.

## Expected Surface

- **OBSERVED**: `script-shared/scripts/marketplace_bundles.py`, `tools-script-executor/scripts/generate_executor.py`
- **OBSERVED**: `manage-config/standards/data-model.md` (retention semantics), `marshall-steward/scripts/cache_retention.py`
- **HYPOTHESIS**: `tools-script-executor/SKILL.md:305` — the marker's documented semantics

## Dependencies and Sequencing

- ⛔ **NOT the registry-pin / orphan-GC inversion** — the sender asked explicitly that the two not be
  folded, and they are right: **the format split would survive a complete fix of the inversion.**
- ✅ Disjoint from both running plans (`manage-metrics`; `ref-code-quality` + lessons corpus).
- ⚠ Low priority against the token-reduction levers. **Real, latent, cheap — not urgent.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-049-two-producers-write-one-marker-field-in-two-encodings-and-one-is-not-ours.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message, and
⛔ **writes nothing under `~/.claude/plugins/cache/`** — see D0's warning against normalising a foreign
producer's markers. Qualifiers are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⛔⛔ RE-GROUNDED 2026-08-08 — D-1's DISCRIMINATOR MAY BE UNREACHABLE AS DESIGNED. READ BEFORE SCOPING.

The plan says: *"the discriminator arrives on its own — re-read after 2026-08-04 ~00:00Z, when the
oldest ISO marker crosses 7 days."* **It did not arrive.** Whole-population survey at
`2026-08-08T19:05Z` (9 dirs under the plugin cache), ages computed from the marker contents:

| dir | encoding | marked | age |
|---|---|---|---|
| `0.1.1240` | ISO | `2026-08-08T19:01:17Z` | **0.00 d** |
| `0.1.1288` | ISO | `2026-08-07T20:27:07Z` | 0.94 d |
| `0.1.1289` | epoch-ms | `2026-08-03T12:17:19Z` | **5.28 d** ← oldest overall |
| `0.1.1291` | ISO | `2026-08-03T16:42:39Z` | 5.10 d |
| `0.1.1292` / `0.1.1293` | epoch-ms | `2026-08-06T07:51:24Z` | 2.47 d |
| `0.1.1324` | ISO | `2026-08-08T18:12:48Z` | 0.04 d |
| `0.1.1325` | epoch-ms | `2026-08-08T18:53:21Z` | 0.01 d |
| `0.1.1304` | **UNMARKED** | — | — (and it IS the registry pin: invariant holds) |

**Nothing in either encoding has reached 7 days**, five days after the date the plan expected the
answer. The `2026-07-27T23:35:57Z` dir the test hinged on is simply **absent** — and absence is not
the evidence the table assumes, because it is equally explained by collection, by a sync replacing
the tree, or by a re-mark.

⭐ **THE MECHANISM THAT BREAKS THE TEST — HYPOTHESIS, and D-1's real job now.** `0.1.1240` carried
`2026-08-08T17:26:55Z` earlier in this same session and carries `2026-08-08T19:01:17Z` now. **Its
marker was rewritten, resetting its age.** If ISO markers are refreshed on every sweep/regeneration,
the 7-day threshold is **never reached by construction** — a dir would leak forever while looking
freshly marked, and no amount of waiting produces the discriminator D-1 waits for.
⛔ **Confirm/refute by watching one dir's marker across two consecutive executor regenerations** —
not by waiting longer. **Do not re-run the wait; it is the thing that failed.**

⚠ **Consequence for the deliverable order.** D-1 as written ("wait, then read") cannot conclude. Its
question must be re-asked as *"do our markers age monotonically at all?"* — which is answerable today
and is a strictly better gate. The remedy branch it guards is unchanged: if our ISO markers never age
out, we write **epoch-ms to match the owning consumer**.

## ⭐ NEW, AND IT MAKES THIS PLAN OPERATIONALLY URGENT RATHER THAN A CONTRACT ITEM

`.plan/execute-script.py` currently resolves to **`0.1.1325`** — and `0.1.1325` is **orphan-marked, in
epoch-ms**, i.e. the encoding the plan's own research names as the one Claude Code's GC actually
parses. ⇒ **The executor is running out of a directory that is genuinely collectable**, while the
loader follows unmarked `0.1.1304`. That is the `ModuleNotFoundError` failure mode with a live fuse.

⛔ This is a **LEAD for D-1 to settle, not a finding to act on**: it is one observation of one machine
at one instant, and a pin/marker state is a snapshot, never a status. But it means the plan's outcome
decides whether a live executor pointer is safe — so **D-1 runs before anything else touches the
cache**, and no "normalise the corpus" step may run ahead of it.

## ⛔⛔ RE-SURVEYED at the PR #1115 landing analysis — THE PIN/MARKER INVARIANT NOW FAILS

The section above records `unmarked == ['0.1.1304']` with the registry pin at `0.1.1304`, i.e. the
invariant holding. **That is no longer the state.** Re-derived first-party over the whole population
at this analysis (9 version dirs enumerated, not sampled):

- **`unmarked == ['0.1.1240', '0.1.1304']`** — **two** unmarked dirs. The invariant is
  `unmarked == [pin]`; the actual shape is `[stale, pin]`. Both `[]` and `[stale, pin]` fail it.
- The registry pin is still `0.1.1304`, so **the pin is not the problem — the unmarked stale `1240`
  is.** `0.1.1240` unmarked alongside the pin is the exact configuration recorded as having seated a
  session **48 versions backward** on 2026-08-07, because the loader follows the unmarked directory
  rather than the pin.
- `.plan/execute-script.py` still pins **`0.1.1325`**, still orphan-marked
  (`.orphaned_at = 1786215201115`, epoch-ms), still absent from the registry.

⭐ **The re-arming agent is now named: PR #1115's own `sync-plugin-cache` finalize step.** It reported
*"10 bundles synced; executor regenerated"* — regenerating the executor to `1325` — and, per the
already-recorded mechanism, `sync-plugin-cache` updates the cache and the executor and **never the
registry**. So the finalize that *reported* the condition is the finalize that *created* it. This is
the tenth-plus recurrence and the first with the producing step identified inside the same run.

⛔ **Nothing was repaired.** Registry repair is operator-only, and this plan owns the mechanism.
D-1's re-asked question ("do our markers age monotonically at all?") is now directly answerable from
this very observation: `0.1.1240`'s marker was rewritten twice within one session and it is **now
unmarked again** — a third state the aging model does not contain. **A dir that goes marked →
re-marked → UNMARKED is not aging; it is being reset by a producer.** Settle D-1 against that.
