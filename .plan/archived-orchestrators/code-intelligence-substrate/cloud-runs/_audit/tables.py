"""Emit the AsciiDoc tables for the report. Generated, never hand-typed (README Step 10)."""
import json
import pathlib
import re
from collections import Counter

S = pathlib.Path(__file__).resolve().parent
A = json.load(open(S / "analysis.json"))
CR = {r["pr"]: r for r in json.load(open(S / "reviewer_cloud.json"))}
LOC = {r["pr"]: r for r in json.load(open(S / "reviewer_local.json"))}

rows = {r["plan"]: r for r in A["rows"]}
data = sorted(A["data"], key=lambda d: d["plan"])

print("// ---------- per-plan ledger ----------")
for d in data:
    r = rows[d["plan"]]
    pr = int(r["pr"])
    cr = CR.get(pr, {})
    st = cr.get("state")
    f = "-" if st != "reviewed" else str(cr["findings"])
    fx = "-" if st != "reviewed" else str(cr["resolved"])
    hi = sum(1 for s in d["sevs"] if s == "high")
    num = d["plan"].split("-")[0]
    ovr = d["overall"].replace("**", "").strip()
    ovr = {"CONFIRMED WITH GAPS": "confirmed-with-gaps",
           "PARTIALLY REFUTED": "partially-refuted",
           "PARTIAL": "partial"}.get(ovr, ovr.lower())
    print(f"| `{num}` | #{pr} | {ovr} | {d['n_del']} | {d['d_fail']} | "
          f"{len(d['gap_ids'])} | {hi} | {f} | {fx}")

n_del = sum(d["n_del"] for d in data)
d_fail = sum(d["d_fail"] for d in data)
n_gap = sum(len(d["gap_ids"]) for d in data)
hi = sum(1 for d in data for s in d["sevs"] if s == "high")
print(f"| **total** | | | **{n_del}** | **{d_fail}** | **{n_gap}** | **{hi}** | | ")

print()
print("// ---------- taxonomy ----------")
kc = Counter()
for d in data:
    for k in d["kinds"]:
        kc[re.split(r"[ (/,]", k.strip().lower().strip("`*"))[0]] += 1
REAL = {"bug", "test-gap", "missing-detector"}
SWEEP = {"incomplete"}
DOC = {"doc-defect", "omission", "report-defect"}
for k, v in kc.most_common():
    cls = "real defect" if k in REAL else "incomplete sweep" if k in SWEEP else "documentation / prose" if k in DOC else "UNMAPPED"
    print(f"| `{k}` | {v} | {100*v/n_gap:.1f}% | {cls}")
print(f"| **total** | **{n_gap}** | **100%** | ")

print()
real = sum(v for k, v in kc.items() if k in REAL)
sweep = sum(v for k, v in kc.items() if k in SWEEP)
doc = sum(v for k, v in kc.items() if k in DOC)
print(f"// partition: real={real} ({100*real/n_gap:.1f}%) sweep={sweep} ({100*sweep/n_gap:.1f}%) doc={doc} ({100*doc/n_gap:.1f}%)")
print(f"// report-defect kind alone: {kc['report-defect']} = {100*kc['report-defect']/n_gap:.1f}%")
rep_w = sum(1 for d in data for w in d["wheres"] if "report-0" in w.lower())
allw = sum(len(d["wheres"]) for d in data)
print(f"// where-field points at the run's own report: {rep_w}/{allw} = {100*rep_w/allw:.1f}%")

print()
print("// ---------- severity ----------")
sev = Counter(s for d in data for s in d["sevs"])
for k in ("high", "medium", "low"):
    print(f"| {k} | {sev[k]} | {100*sev[k]/n_gap:.1f}%")

print()
print("// ---------- reviewer ----------")
for lane, m, tot in (("cloud", CR, 37), ("local", LOC, 11)):
    rev = [r for r in m.values() if r["state"] == "reviewed"]
    dec = [r for r in m.values() if r["state"] == "declined"]
    f = sum(r["findings"] for r in rev)
    x = sum(r["resolved"] for r in rev)
    zero = [r for r in rev if r["findings"] == 0]
    print(f"// {lane}: PRs={len(m)} reviewed={len(rev)} declined={len(dec)} "
          f"reviewed-but-zero={len(zero)} findings={f} resolved={x} "
          f"resolution={100*x/f if f else 0:.1f}% coverage={100*len(rev)/len(m):.1f}%")
