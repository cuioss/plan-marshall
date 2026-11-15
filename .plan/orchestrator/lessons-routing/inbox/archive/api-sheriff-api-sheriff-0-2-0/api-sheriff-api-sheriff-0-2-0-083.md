envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-07T16:39:11Z

# Class: a mechanism reports a result it never computed (api-sheriff-0-2-0 close-out, 2026-11-07)

Final hand-off from the `api-sheriff-0-2-0` close-out (`epic-closeout` step 1 + step 2 ledger sweep). Three findings not yet in lessons-routing share one shape: a verb returns a clean, well-formed answer for something it never computed. Already-routed members of the same class, for context: `2026-08-09-07-006` (surfacer zero), `2026-08-09-07-007` (`verify-links`), `2026-08-09-18-006` (empty assessment store), `as-005`/`as-022` (module-tests DEGRADED with zero bundles), `as-055` (barrier fails open), `as-078` #2 (freshness passed on a 5-test row labelled whole-tree).

## 1. `manage-lessons list` renders a lesson whose header did not parse as a well-formed row with empty fields (`plan-marshall:manage-lessons`; writer side `lessons-capture`)

API-Sheriff lesson `2026-08-08-11-001` (written by api-sheriff-roadmap PLAN-51's own `lessons-capture` step with a markdown-bullet header `- **id**: …` instead of `key=value` frontmatter) was listed with empty component/category, and `remove` then reported it `not_found`. The `remove` half is fixed (three-state resolution, `remove --allow-unreadable`, `manage-lessons/SKILL.md` § resolution seam). The `list` half is still live: `manage-lessons/scripts/_lessons_query.py` `cmd_list` builds each row with `metadata.get('component', '')` / `metadata.get('category', '')` and never consults the resolver's `unreadable` state, so a triage that groups by component silently drops such a lesson. plan-marshall saw the same shape in its own lesson `2026-08-08-20-002`; PLAN-LR-06 (corpus integrity), which would have owned it, is retired, and `settled.md` only watches for headerless files. **Ask:** `list` reports an unparseable lesson as `unreadable` (or in an `unresolvable[]` bucket, as `aggregate` already does), and the `lessons-capture` writer and the corpus reader share one header format.

## 2. `inbox landing-check` reports `complete: true` over a surface delta it never computed (`plan-orchestrator` landing-check / emit-landing `landing-facts`)

Three landings in api-sheriff-0-2-0 carry it: PLAN-V02-11 (`surface_delta` `unmeasured`, no declared or realized path list supplied), PLAN-V02-53 and PLAN-V02-56 (`declared_not_supplied_and_realized_not_supplied`). The delta was measured only when the orchestrator passed `--declared-paths/--realized-paths` itself (PLAN-V02-49, PLAN-V02-55 — which found real expansions of 2 and 9 files). So the default landing path cannot detect a footprint expansion, and `complete: true` reads as a checked landing. plan-marshall records the same symptom on its own landings (live-blockers `epic.md`, PLAN-LB-106 note) but has not filed it. **Ask:** emit-landing carries the plan's declared and realized footprint (both derivable via `manage-references`), or `landing-check` reports a distinct `surface_unmeasured` state rather than an unqualified `complete: true`.

## 3. A finalize review closes on operator override over a partial read, and the override drops the review's facts (`phase-6-finalize` code-review / functional-review; landing-facts)

PLAN-V02-48: the finalize code review did not read 40 of the 50 rewritten ADRs, the final commit was not code-reviewed, and the step record says only `acceptance=operator_override` — the gap is visible only because the plan listed it in its PR body. PLAN-V02-56 and PLAN-V02-22: review closed on override at the final head, so verdict and count facts were not recorded as typed facts in the landing. Override closes occurred on six plans (V02-20, -27, -47, -48, -49, -56), so the override is now the usual exit. The causes of most overrides are already routed (`weakened_test` false positives, re-fire cost); the partial-coverage close and the lost facts are not. **Ask:** a review step records which part of the footprint it read (read/total) and keeps its last verdict/counts on an operator close, so a landing can tell "closed with nothing found" from "closed without looking".
