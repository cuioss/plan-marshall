envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-08-03T06:49:57Z

## Finding — the plugin-cache orphan marker has TWO concurrent producers writing TWO incompatible timestamp formats

Surfaced 2026-08-03 during the pre-launch pin check for `PLAN-CIS-030`, not by a plan under execution.
Routed here because it carries no PR/review surface (so it fails the `review-apparatus` test) and it is a
measurement/representation defect rather than a `code-intelligence-substrate` substrate concern.

### The observation (first-party, whole-population)

`.orphaned_at` markers under `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/` are written in two
mutually unparseable formats:

| Format | n | Example | Decoded range |
|---|---:|---|---|
| ISO-8601 | **180** | `plan-marshall/0.1.1286` = `2026-08-03T06:42:24Z` | 2026-07-27 23:35:57Z .. 2026-08-03 06:42:24Z |
| raw epoch-ms integer | **220** | `plan-marshall/0.1.1288` = `1785739333150` | 2026-07-28 08:50:54Z .. 2026-08-02 07:08:47Z |

Population: **all 400 markers present in the cache** (every bundle, every version dir) — not a sample.
55% of the corpus is epoch-ms. Neither format is rare, and neither is a legacy remnant.

### ⭐ The two ranges OVERLAP — this is not a format migration

The natural reading of a two-format field is "old writer superseded by new writer". **That reading is
refuted here**: the ISO range (07-27 → 08-03) strictly contains the epoch-ms range (07-28 → 08-02). Both
writers were live across the same six-day window, and both wrote as recently as this week. Two producers
are concurrently authoritative over one field, and nothing reconciles them.

The pin repair on 08-03 makes this concrete at one-version granularity: `0.1.1286` carried an ISO marker
stamped `06:42:24Z` while `0.1.1288` — same bundle, same directory tree, marked in the same era — carried
`1785739333150`.

### Why it belongs to this epic

The cache's documented contract is a **7-day `.orphaned_at` retention** with keep-oracle "no marker"
(see `project_plugin_cache_orphan_gc`). That retention is a confident, stated claim over a field whose
encoding is ambiguous. Any consumer that decodes the marker to apply the 7-day rule must pick one format:

- decode-as-ISO ⇒ the 220 epoch-ms markers fail to parse
- decode-as-epoch ⇒ the 180 ISO markers fail to parse
- decode-as-epoch-**seconds** (a plausible mis-read of a bare integer) ⇒ `1785739333150` resolves to year
  **58561**, i.e. an orphan that is never eligible for collection and never reported as unparseable

⇒ **The retention claim is silently false for whichever half the consumer cannot decode**, and the failure
direction (never-collect vs collect-immediately) is not derivable from the field itself. That is this
epic's theme exactly: a confidently-stated number resting on an unlabelled representation.

### ⛔ Claim labels — what is established and what is NOT

- **OBSERVED (first-party, whole population)**: the 180/220 split, the example values, and the overlapping
  decoded ranges above. Re-derivable by reading the 400 marker files.
- **⛔ NOT ESTABLISHED — deliberately not claimed**: *which* code paths write each format. I did not read
  the GC/sync source, and I am not naming a producer on inference from timing alone. Identifying the two
  writers is the first thing this finding needs and is not done here.
- **⛔ NOT ESTABLISHED**: what the consumer actually does on a parse failure (raise / skip / silently
  treat as never-expired). The three consequences enumerated above are the *possible* behaviours, not an
  observed one. **Do not report any of them as the impact until the consumer is read.**
- **OBSERVED**: the marker corpus is currently in the fully-inverted state — before the 08-03 repair, all
  41 `plan-marshall` version dirs carried a marker, including the registry pin and the newest build.

### Adjacent, already-tracked — NOT part of this finding

The registry-pin / orphan-GC inversion itself (`project_plugin_registry_pin_orphan_inversion`) is a
separate, known, ~daily-recurring defect with residue (a) owed at the tool layer. It explains *which* dirs
get marked. It does **not** explain why two writers disagree on the encoding, and the format split would
survive a complete fix of the inversion. Filed separately on purpose — please do not fold them.

Also decayed and worth knowing if you touch this surface: `.in_use` is no longer an oracle. It has
accumulated on 1194, 1222, 1240, 1279, 1282, 1286 and now 1288 — every version any past manual repair
touched, because the stale-delete raises `PermissionError` on macOS and is skipped. It is a repair-residue
trail; `installed_plugins.json` is the only honest read of the pin.

### Suggested first step

Enumerate the writers of `.orphaned_at` across the marketplace source and settle whether the encoding is
specified anywhere. If it is specified, this is two implementations of one contract; if it is not, the
contract itself is the gap — and the fix is to state the encoding before normalising the corpus, so the
normalisation is verifiable rather than another undocumented convention.
