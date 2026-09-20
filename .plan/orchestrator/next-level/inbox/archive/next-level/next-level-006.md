envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:38:11Z

## A cited format-sensitivity study bears directly on WS-02's calibration-axis decision

Source: *Spec-Driven Production Grade Development in the Age of Vibe Coding* (Lee Boonstra; Google/Kaggle,
May 2026) — Day 5 of the same course series, read in full from a local PDF.

### The claim, and its citation

Unlike most of the series, this one names a study: Ouyang et al., 2026, *SkCC: Portable and Secure Skill
Compilation for Cross-Framework LLM Agents* (endnote 3, `arxiv.org/abs/2605.03353`). As reported in the
whitepaper:

- LLM agents show "extreme sensitivity to how instructions are formatted", with **up to a 40% performance
  drop** from generic, unoptimized Markdown.
- The optimal format is **model-specific**. For Gemini the reported best strategy is hybrid Markdown +
  conditional YAML: Markdown headers to anchor attention, switching to YAML for structured data at nesting
  depth > 3, where the reported parsing accuracies are YAML **51.9%**, JSON **43.1%**, XML **33.8%**.
- Their remedy is a **compiler**: one single-source instruction file compiled to each model's optimal target
  format in under 10ms.

⛔ **Unverified.** The figures are as the whitepaper reports them; nobody here has read the study, and none
of them may be treated as measurements of our corpus. The endnote resolves to an arXiv id — verification is
cheap and should precede any use.

### Why this is the sharpest external input this epic has received

It is the same architecture as our multi-target generator, arriving at a conclusion our generator does not
implement. `./pw generate --target {name}` compiles one Markdown source to `claude`, `opencode`, and
`antigravity`. The standing position is that the generator translates **vocabulary, not calibration** —
emphasis and verification scaffolding ship byte-identical to every target. SkCC's claim is that **format
calibration is per-model, mechanical, and worth up to 40%**. If that holds, the byte-identical export is not
neutrality; it is a silent per-target regression on every target but the one the corpus was written against.

That is WS-02's question, and the resume anchor already flags WS-02 as the time-sensitive row because the
antigravity target is in flight and uncommitted. Antigravity is Gemini-backed — the exact model the study's
specific numbers describe.

### Two cautions that cut against over-reading it

- **A per-model format table is the calibration trap, not the escape from it.** The standing rule is that the
  corpus is never tuned for one model; a compiler that emits Gemini-optimal YAML is only safe if it emits a
  target-appropriate form for *every* runtime, including the ones nobody measures. A half-built compiler is
  worse than none — it makes one target better and leaves the rest silently behind.
- **We already own part of the answer.** TOON is our structured wire format, and the question of whether it
  is the right per-runtime form is now an empirical one rather than a settled one. That is a finding, not a
  defect claim: nothing here shows TOON is wrong anywhere.

### Status

The strongest outside input so far, and still unverified. The first action it warrants is reading the study,
not acting on the whitepaper's summary of it.
