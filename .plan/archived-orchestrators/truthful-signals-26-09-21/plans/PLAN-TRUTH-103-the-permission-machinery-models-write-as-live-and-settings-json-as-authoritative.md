# PLAN-TRUTH-103: The permission machinery models `Write(...)` as live and `settings.json` as authoritative

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-103-the-permission-machinery-models-write-as-live-and-settings-json-as-authoritative.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-23 from the three **Open residuals** § 9.1–9.3 of the PR #1337 run report (foreign
machine, ad-hoc `NO_PLAN` lane, merged as `2cd1a19c8`). The report recorded them deliberately
un-actioned rather than silently widening its change — the correct call, and this spec is the owner it
named. **Every claim below was corroborated FIRST-PARTY at HEAD `2cd1a19c8`** by this orchestrator; the
report's own framing is sharpened in two places, both marked ⭐ and both attributable to the
corroboration rather than to the report.

## Objective

PR #1337 retired `Write(.plan/**)` on the premise — verified against the official permissions
documentation, and against Claude Code's own startup warning — that **Claude's file permission checks
consult `Edit(...)` rules only**, and that an `Edit` rule covers every file-editing tool, `Write` and
`NotebookEdit` included. A `Write(...)` allow rule therefore grants nothing.

That premise is now load-bearing in shipped code (`_RETIRED_DEFAULT_RULES` deletes an operator's rule
without asking, defensible **only** because the rule is inert). But the premise was applied to exactly
one rule. **Three other places in the same machinery still model `Write(...)` as a live grant, or model
`.claude/settings.json` as the file whose entries take effect — and both models are false.** Each is
small; together they are one subject, which is why they are one plan rather than three.

⛔ **This plan does not re-litigate the `Edit`-covers-`Write` premise.** It is settled, shipped, and
documented at `_RETIRED_DEFAULT_RULES`. This plan propagates it.

## Deliverables

Four deliverables, well under the epic's split guard of 12. D0 is a gate.

**D0 — GATE: derive the population of `Write(...)`-modelling sites before changing any of them.** The
three members below were each found by a *different* accident — one by a startup warning, two by an
adversarial review of the fix for that warning — which is evidence the machinery was never swept for
this premise. ⛔ **Do not treat the three as the population.** Sweep every site that renders, audits,
matches, or documents a permission rule for the `Write(`/`Edit(` distinction, and **publish the swept
population and its size** before D1–D3 act. A member found after D0 is folded here, not deferred.

⭐ This gate is the epic's own standing rule applied to itself: *every set-guarding detector must be
population-derived*, and a fix list assembled from three accidents is not a population.

**D1 — the suspicious-permission audit polices the grammar that grants nothing, and is silent on the one
that grants everything.** *(report § 9.2; the report ranks this the highest-value of its three residuals,
and the corroboration agrees)* `_claude_runtime_impl.py:1009–1013` carries five `suspicious_patterns`:

| Pattern | Severity | First-party verdict at `2cd1a19c8` |
|---|---|---|
| `Write\(/tmp/` | medium | **False positive** — inert by this codebase's own shipped premise |
| `Write\(/\*\*\)` | **high** | **False positive** — inert by the same premise |
| `Bash\(sudo:` | high | genuine |
| `Bash\(\*\)` | high | genuine |
| `Read\(/\*\*\)` | medium | genuine — `Read` rules ARE consulted |

⭐ **SHARPENING beyond the report: the write-side coverage is not merely incomplete, it is exactly
inverted.** The audit's only **high**-severity filesystem-wide-*write* detector fires on `Write(/**)`,
which grants nothing — while **`Edit(/**)`, which genuinely grants filesystem-wide write, matches no
pattern at all.** `Edit(/tmp/` likewise has none. A settings file carrying `Edit(/**)` passes this audit
clean. Correct the write-side patterns so severity tracks what is actually granted. ⚠ Keep `Read(/**)`
and both `Bash` patterns unchanged — they are correct and are not this plan's subject.

**D2 — `apply-fixes --scope project` can never reach the file whose entries actually take effect.**
*(report § 9.1)* Corroborated first-party: `claude_runtime.py` carries two resolvers whose preferences
are **mirror images**, and each docstring says so plainly.

| Resolver | Line | Prefers | Its own docstring |
|---|---|---|---|
| `_claude_project_settings_path` (**write**) | 2389 | `.claude/settings.json` when it `is_file()` | *"the Claude project settings file path to write to"* |
| `_claude_project_settings_read_path` (**read**) | 2406 | `.claude/settings.local.json` when it `is_file()` | *"it is the file whose entries actually take effect for that operator"* |

⇒ On any project where **both** files exist, the pruning `apply-fixes` performs writes to
`settings.json` and **never reaches `settings.local.json`** — the file the read side itself names as
authoritative. Proven in the report's review: `defaults_removed: []`, `changes_made: False`, file
untouched. `~/.claude/settings.json` is likewise unreached unless `--scope global` is invoked by hand.

⭐ **SHARPENING beyond the report — the mechanism is live in THIS repository while the symptom is
absent, and the two must not be conflated.** First-party at `2cd1a19c8`: `.claude/settings.json` and
`.claude/settings.local.json` both exist here, `settings.local.json` carries live grants, and the write
resolver therefore targets `settings.json` and can never touch the local file. The retired rule happens
not to be present in our local file, so no symptom shows. ⛔ **An absent symptom is not an absent
defect** — this epic's own archetype. Do not let a clean local check close this deliverable.

⚠ **The asymmetry is PRE-EXISTING and is not itself the bug to fix.** The two resolvers are each
correct for their stated purpose and both docstrings defend the split. What is missing is that a
*mutating* operation resolves through the *write* preference while the operator's effective grants live
behind the *read* preference. Settle which files a pruning operation must reach, and make the answer
explicit in both docstrings — changing which files the command writes is a real behaviour change and
owes its own test surface, which is why it is a deliverable and not a drive-by.

**D3 — `deny` and `ask` are never pruned.** *(report § 9.3; low)* Pruning rebuilds `allow` only.
Corroborated first-party that this is reachable **only** from a hand-edited file: `_protect_path_deny_rules`
(`claude_runtime.py:2730`) emits `Read(...)` and `Bash(...)` rules exclusively — no plan-marshall path
emits a `Write(...)` deny rule. ⚠ Record that reachability finding in the shipped code or docs
regardless of the disposition chosen: *"unreachable from our own emitters"* is the fact that makes
either answer defensible, and it is exactly the kind of premise that rots silently.

**D4 — tests, each pinning the side that drifted.** ⭐ The report's own L2 is the design rule here: *the
absent test is the drift mechanism* — `normalize`'s default set had no pin, which is precisely why it
diverged from the renderer. Pin D1's corrected pattern set against a **matched negative control** (a
settings file carrying `Edit(/**)` must be FLAGGED; one carrying `Write(/**)` must not be flagged as a
filesystem-write grant), and pin D2's file-reach decision on a fixture where **both** settings files
exist — the shape under which the defect is live and a single-file fixture is vacuous.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`
- `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py`
- `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py`
- `test/plan-marshall/platform-runtime/test_claude_runtime.py`
- `test/plan-marshall/platform-runtime/test_permission_rendering_defaults.py`
- `test/plan-marshall/tools-permission-fix/test_permission_fix.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md`
  — the health-check invocation at `:48-50` that names the wrong artifact — added 2026-09-05 by the
  consumer-project data-point fold (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/SKILL.md` — the
  `ensure-wildcards` canonical block and its `--marketplace-json` contract (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/tools-permission-fix/test_permission_fix_behavior.py` — the
  shape-mismatch control (verify-at-outline)

## Dependencies and Sequencing

✅ **MACHINE-DERIVED at staging (`corpus cross-check`, 2026-08-23 — 152 specs / 7 sibling epics / 7
live plans).** ⭐ **The hand-written version of this section named TWO collisions and MISSED TWO** —
`-086` and the cross-epic `PLAN-CIS-052`. R39 records the identical failure when `-102` was staged; it
recurred here, one section after the spec that warns about it. ⛔ Re-derive again at emit time — a
running plan's real surface can be wider than its spec.

- ⛔ **`PLAN-TRUTH-102` — SERIALIZE, never pair.** **Three-file overlap**: `claude_runtime.py`,
  `_claude_runtime_impl.py`, `test_claude_runtime.py`. Both plans act on the settings-file resolution
  story — `-102` reports a dual-homed *hook install*; this plan settles which settings file a *mutating
  permission operation* reaches. Landing them concurrently would produce two answers to one question.
  ⚠ `-102` is the natural PREDECESSOR: it settles the three-state reporting vocabulary for a cross-file
  settings condition, which D2 here can then reuse instead of inventing a second one.
- ⛔ **`PLAN-TRUTH-086` — SERIALIZE.** Two-file overlap: `_claude_runtime_impl.py`,
  `test_claude_runtime.py`. Both `staged`. *(Missed by the hand-written map.)*
- ⚠ **`code-intelligence-substrate/PLAN-CIS-052` — cross-epic, one file (`claude_runtime.py`).**
  *(Missed by the hand-written map.)* CIS-052 is `staged` and is that epic's **recommended first pair**,
  and CIS is under a standing 2026-08-09 operator hold. ⛔ **Check the SUBJECT, not only the file
  count** — R14 records that a 3-file overlap with CIS-052 understated a direct contract conflict for
  `-100`. CIS-052's declared intent in `claude_runtime.py` is read-mostly (finalize dispatch
  observability), so no conflict is expected, but confirm against their live queue before pairing.
- ✅ **`PLAN-TRUTH-013` — NOT a constraint.** One-file overlap on `claude_runtime.py`, but `-013` is
  **shipped** (#1131). Recorded so nobody re-flags it as live.
- **Depends on:** nothing. The premise it propagates already landed (#1337 / `2cd1a19c8`).

## Claim Labels

Every claim below was read first-party at HEAD `2cd1a19c8` on 2026-08-23.

- OBSERVED: the `suspicious` check carries exactly five patterns — `Write(/tmp/`, `Write(/**)`, `Bash(sudo:`, `Bash(*)`, `Read(/**)` — and NO `Edit(` pattern of any kind — read at `platform-runtime/scripts/_claude_runtime_impl.py` § `suspicious_patterns`, `:1009-1013`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _claude_runtime_impl.py:1084-1090 still exactly 5 patterns (Write(/tmp/, Bash(sudo:, Bash(*), Write(/**), Read(/**)); zero Edit( patterns
- OBSERVED: `_claude_project_settings_path` (write) prefers `.claude/settings.json` while `_claude_project_settings_read_path` (read) prefers `.claude/settings.local.json`, whose docstring calls it *"the file whose entries actually take effect for that operator"* — read at `platform-runtime/scripts/claude_runtime.py` § `:2389` and `:2406`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: claude_runtime.py:2464 write path prefers settings.json; :2482-2483 read path prefers settings.local.json entries actually take effect
- OBSERVED: `_protect_path_deny_rules` emits only `Read(...)` and `Bash(...)` rules — read at `claude_runtime.py` § `:2730`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: claude_runtime.py:2802-2843 _protect_path_deny_rules emits only Read( and Bash( rules; zero Write/Edit
- OBSERVED: both settings files exist in this repository and the retired rule is absent from the local one, so the MECHANISM is live here while the SYMPTOM is not — read at `.claude/settings.json` and `.claude/settings.local.json` § `permissions.allow`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Both .claude/settings.json and .claude/settings.local.json exist at HEAD; the local file allow[] carries no Write( rule
- HYPOTHESIS: no other site in the tree models `Write(...)` as a live grant — confirm/refute at D0's sweep over every renderer, auditor, matcher and doc naming a permission rule (verify-at-outline). ⛔ **The three known members were each found by a different accident; treating them as the population is the error D0 exists to prevent.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0 tree-wide sweep; population not enumerated this pass
- Verify-first clause: any replacement pattern set must be exercised against a settings file carrying `Edit(/**)` — that fixture is the matched control, and without it the suite passes against the defect.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on an unimplemented D1 test fixture

## ⛔⛔⛔ FOLDED 2026-09-05 (d) — consumer-project data-point. THE SUBJECT WIDENS, AND THE WIDENING IS DELIBERATE.

- **The plugin-wildcard health check reports `success` over a population of ZERO, and it does so in THIS
  repository too.**

  ⛔⛔ **Scope note, stated because it changes D0:** this spec was scoped to the machinery modelling
  `Write(...)` as a live grant and `.claude/settings.json` as authoritative — **one false premise, three
  sites.** This member is a *different* false premise at the same machinery: **an input-SHAPE premise.**
  ⇒ **D0's population is therefore "false premises the permission machinery holds", not "Write-modelling
  sites"**, and a sweep scoped to the narrower phrase would not have found this.

  **The mechanism, verified first-party at `permission_fix.py:477-498` and `:531`:**
  `generate_required_wildcards()` reads `marketplace.get('bundles', {})` — **a dict, and its own docstring
  says so**: *"Expects 'bundles' as a dict … (from scan-marketplace-inventory JSON output)."*
  `cmd_ensure_wildcards` derives `bundles_analyzed` from the same key.

  ⛔ **But the artifact it is documented to be pointed at is a `marketplace.json` DESCRIPTOR, which carries
  a `plugins` ARRAY.** Two different artifacts sharing a name in the docs.
  `menu-healthcheck.md:48-50` prescribes `--marketplace-json marketplace/.claude-plugin/marketplace.json`.

  ⭐⭐⭐ **REPRODUCED HERE, IN ONE COMMAND, USING THE DOCUMENTED INVOCATION AND THE DOCUMENTED PATH:**

  ```text
  added[0]
  already_present: 0
  total: 0
  bundles_analyzed: 0
  status: success
  ```

  Both descriptors carry `plugins` (a 10-element list) and neither carries `bundles` — **the installed
  one at `~/.claude/plugins/marketplaces/plan-marshall/.claude-plugin/marketplace.json` AND this
  repository's own `marketplace/.claude-plugin/marketplace.json`.**

  ⛔⛔ **So the reporter's framing is TOO NARROW and must not be inherited.** They diagnosed it as a
  consumer-project problem (*"the documented path points at a file that doesn't exist in a consumer
  project"*). **The path exists here and the check is equally blind.** The defect is universal; the
  missing file is a second, lesser symptom.

  ⭐⭐⭐ **The decisive evidence is a MATCHED PAIR, and it is what makes this unarguable.** In the
  reporting consumer project **no `Skill(...)` wildcard exists in either settings file**. In this
  repository **17 exist globally**, including `Skill(plan-marshall:*)`. ⇒ **The check emits the IDENTICAL
  `added: []` / `status: success` over OPPOSITE ground truths.** It cannot distinguish *"every wildcard
  is present"* from *"none is, and I did not look."*

  ⭐ **The discriminator is already published and no consumer branches on it**: `bundles_analyzed: 0` IS
  in the payload. **This is the shipped shape of the archetype — the SCRIPT complies, the CONSUMER
  discards.** ⇒ **A fix that only adds a population field would change nothing here.** Two things are
  owed: the caller must be pointed at the artifact whose shape the function declares (or the function
  must accept the descriptor), **and `bundles_analyzed: 0` must not be reachable with `status: success`.**

  ⚠ **The cost is masked by auto-mode and will surface without it**: with permissions auto-approved a
  missing `Skill(...)` wildcard is invisible; without it, every skill invocation prompts. **A consumer
  who runs the health check, sees `success`, and turns auto-mode off gets a prompt storm the check
  certified against.**

  ⚠ **Expected Surface widened in this same act** — see the three entries added above.
