# Landing — PLAN-PR-044: a misconfigured reviewer name reads as a missing review

**PR** [#1392](https://github.com/cuioss/plan-marshall/pull/1392) · **merged** via merge queue at `cc5ea40a1` · **WS-01**
**Plan** `misconfigured-reviewer-name-reads-missing-review` · 6/6 deliverables · 7,926,426 tokens / 64.2M billing-weighted · 32h22m wall, 9h12m worked
**Landing message** `inbox/misconfigured-reviewer-name-reads-missing-review-004.md` — `landing-check: complete: true`, `missing_keys[0]`

## Deliverable fidelity vs spec

| # | Deliverable | Verdict |
|---|---|---|
| D0 | Record the observed proximate cause and the workaround | ✅ shipped |
| D1 | Add an `unregistered_kind` completeness state that refines `absent` | ✅ shipped |
| D2 | Report unknown bot-kind tokens when the reviewer config is read | ✅ shipped |
| D3 | Name the token, kind set, and login mapping in the escalation | ✅ shipped |
| D4 | Collapse the PR-Agent `bot_kind` onto its author login | ✅ shipped — `standards/pr-agent.md` → `standards/cuioss-review-bot.md`, `bot_kind: cuioss-review-bot` |
| D5 | Propagate the renamed token to all four CUI checkouts | ⛔ **NOT SHIPPED AS CLAIMED** — see below |

⛔ **D0's spec asked for exactly one mechanism to be named and the other two rejected. That was met** — mechanism (1), the login placed in the kind slot, corroborated first-party across three repos before the plan ran.

## ⛔⛔ Open Defect 1 — D5's foreign propagation did not happen, and its corroboration was false-green

The landing narrative states: *"all three foreign PRs (#249, #192, #693) are MERGED, corroborated at the foreign PR."* Those three PR numbers **are the original defective sweep PRs**, merged 2026-09-02, *before this plan existed*. They are not this plan's deliverables. Re-derived per repo — the last commit to touch each `.plan/marshal.json`:

| Repo | Last `marshal.json` commit | Current `required_bots` | Changed by this plan? |
|---|---|---|---|
| plan-marshall | `cc5ea40a1` (#1392) | `cuioss-review-bot` | ✅ yes |
| API-Sheriff | `1f4fc24` (#252, steward sync) | `coderabbit,cuioss-review-bot` | ❌ no — value dates from the sweep |
| cui-http | `c7862d0` (#192, the sweep) | `coderabbit,cuioss-review-bot` | ❌ no — untouched since the sweep |
| TokenSheriff | `6c1bd849` (#699) | `coderabbit,pr-agent` | ❌ no — and now **wrong** |

⇒ The plan changed **one** checkout, not four. API-Sheriff and cui-http happen to hold the post-rename-correct value **by accident of the defective sweep**, not by propagation. This is the *"corroborate a foreign landing against the FOREIGN PR"* failure in its exact recorded form: a merged-state read against a PR that was already merged for an unrelated reason returns green and proves nothing about this plan's work.

## ⛔⛔ Open Defect 2 — the rename newly broke TokenSheriff, and the timing is decisive

`bot_kind: pr-agent` was retired by this PR, so the registry kind set is now `{coderabbit, cuioss-review-bot, sourcery}` and **`pr-agent` is no longer a registered kind**.

| Event | UTC |
|---|---|
| #1392 merges — `pr-agent` stops being a kind | **2026-09-03 22:32:44** |
| TokenSheriff #699 *"correct required_bots"* sets `coderabbit,pr-agent` | **2026-09-04 00:13:27** |

**1h41m apart.** TokenSheriff was "corrected" to a token the registry had already stopped recognising. It is now permanently merge-blocked by the very mechanism this plan set out to make legible — `classified` iterates the configured tokens verbatim, evidence keys on `bot_kind`, and `absent` is the fail-closed default, so the required quorum can never be satisfied.

⭐ **The shipped fix is what makes this diagnosable**: D1's `unregistered_kind` state now NAMES the token instead of reporting a silent `absent`. The defect is real; the instrument works.

⛔ **The generalisation, and it is the durable one:** renaming a `bot_kind` invalidates every consumer configuration in the fleet, and **no propagation mechanism exists**. The denominator is unknown — ~21 org repos, 9 local checkouts, 4 configuring the key.

## ⛔ Open Defect 3 — the shipped fix does not close its own defect (plan's own finding, corroborated)

`unregistered_kind` fires only for **unregistered** tokens. plan-marshall's own config now reads `required_bots: "cuioss-review-bot"`, `optional_bots: "coderabbit,sourcery"` — `coderabbit` is a correctly-registered kind sitting in the **optional** list, so the new state never applies to it. A well-named required reviewer in the wrong list still buys `participation_complete: true` with zero diff-readers. Lesson `2026-09-03-23-003`.

## ⛔ Open Defect 4 — the durable config fix is still owed

The correction landed in the **plan-local manifest only**; tracked `.plan/marshal.json` still lists `coderabbit` as optional. Every future plan inherits it until `/marshall-steward` is run.

## ⛔ Open Defect 5 — orchestration context mis-asserted, six lessons mis-routed

`orchestrated: false` was passed to `plan-retrospective` without resolving it, though the plan is orchestrated under this epic. **Six lessons went to the global store instead of the epic inbox** (three reached the inbox as `-001`…`-003`). The mechanism the run then found is a real ordering defect: the manifest runs `plan-retrospective` (995) **before** `lessons-capture` (991), and the verdict is resolved inside the latter — **producer after consumer**. Indexed in the epic inbox as do-not-re-file.

## ⛔ Open Defect 6 — the pre-archive foreign gate cannot ever pass (filed `8fe5be`)

The gate classifies the **checked-out branch**, and a merged PR's head is never `main` — so it can never return `merged` for a completed foreign deliverable. The run archived on evidence rather than bypass, which was the right call. ⚠ Note this gate's false positive is *also* what let Open Defect 1 through unexamined.

## Reconciliation actions

- Queue row `PLAN-PR-044` → `shipped`; `pr` = `1392`; `landing` = `landings/PLAN-PR-044.md`.
- Six Open Defects recorded above; Defects 1 and 2 are **new work candidates** and are not owned by any staged spec.
