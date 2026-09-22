envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-18T08:52:21Z

component=plan-marshall:manage-architecture
category=bug

# Three architecture-store writer defects are yours by subject — handed over with their text, and removed from the corpus after this write

⛔ **FORWARDED from `truthful-signals`, 2026-09-18, at the end of a corpus-wide sweep** (131 active lessons
classified by subject; 124 were ours; corpus 131 → 7 → 0). These three are **`manage-architecture` store
integrity — how the system persists what it knows** — which is `code-intelligence-substrate`'s column, not
ours. The operator directed that every remaining lesson become an inbox item for its owning epic and then
leave the corpus.

⛔ **After this message the corpus copies are GONE.** Their text survives at
`.plan/local/orchestrator/truthful-signals/lessons/forwarded-to-other-epics/{id}.md` and in the bodies
below. Decline any of them and we restore it; otherwise nothing else holds them.

⭐ **All three are already FIXED in PR #1489** (TASK-042/043, CodeRabbit findings `d82638`, `6bb8d2`,
`43da9d`). They are forwarded as **durable authoring rules and regression risk**, not as open work — each
names a shape that recurs. Check them against `PLAN-CIS-029` (architecture-store concept model) and
`PLAN-CIS-049` before deciding whether anything is owed at all.

---

## 1. `2026-09-15-08-041` — one live writer bypassed the index write-through the others had been given

`save_module_enriched` updates only `enriched.json`. `api_init` calls it DIRECTLY when it repairs or resets
documents, so the document gets a new generation header while `_project.json` keeps its old mirrored one.

**Fix shape (as recorded):** move the index write-through into a shared persistence operation, or route
`api_init` through the same synchronized operation the enrich path uses — **explicitly NOT** a second
parallel write path. The existing constraint is preserved: `discover --force` stages documents under a tmp
directory it later swaps, and must not be redirected through the live-path writer.

⭐ **The reusable half is the reviewer's framing:** *"When a change states that something is skipped,
disabled, guarded, validated, enforced or removed, verify that the mechanism exists in the file that would
have to implement it."*

## 2. `2026-09-15-08-052` — the JSON writer truncated the destination before the dump completed

`_architecture_core._write_json` opens the destination with mode `w`, truncating it before `json.dump`
finishes, so a concurrent reader of `_project.json` or `enriched.json` can observe a partial file and fail
to parse it.

**Fix shape:** follow the convention this repository ALREADY uses rather than inventing one — temp file in
the same directory, flush, `os.replace` onto the destination. That tmp-then-replace shape is already in
`swap_data_dir` **in this very module**, and in `_locks_core.py`, `_config_core.py` and
`generate_executor.py`. Coverage was extended so atomicity is asserted rather than assumed.

## 3. `2026-09-15-08-053` — a partial batch write stranded documents because the index sync was not in a `finally`

`api_init` builds the `initialised` list in a per-module loop over `save_module_enriched`, then calls
`sync_module_index(initialised, project_dir)` AFTER the loop with nothing guarding the exception path. A
raise at module *k* strands documents 0..*k-1* with a `_project.json` still describing the description and
generation header they no longer carry.

⭐ **The sibling already names the correct shape:** `_cmd_enrich._batched_index_sync` flushes its owed
entries on the way out even when the body raised, and its docstring states why. `api_init` was the one
live-path writer not following it.

---

## The pattern across all three, which is why they travel together

Each is a **writer that diverges from a convention its own module already contains** — a second write path,
a non-atomic write beside an atomic one, an unguarded flush beside a guarded one. If `code-intelligence-substrate`
wants one derivation out of this, it is: enumerate the store's write paths and assert they share one
persistence operation, rather than fixing the three that were caught.
