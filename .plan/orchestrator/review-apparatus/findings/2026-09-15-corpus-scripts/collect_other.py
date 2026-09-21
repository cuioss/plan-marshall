import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect
collect.RAW = os.path.join(collect.BASE, "raw_other")
d = json.load(open("org_search.json"))
main6 = set(collect.REPOS)
jobs = []
for x in d:
    r = x["repository"]["name"]
    if r in main6: continue
    if any(l["name"] == "skip-bot-review" for l in x["labels"]): continue
    if x["createdAt"] < collect.LOWER: continue
    jobs.append((r, {"number": x["number"], "title": x["title"], "createdAt": x["createdAt"], "author": x["author"]}))
print(len(jobs))
with ThreadPoolExecutor(max_workers=6) as ex:
    list(ex.map(lambda j: collect.dump_pr(*j), jobs))
