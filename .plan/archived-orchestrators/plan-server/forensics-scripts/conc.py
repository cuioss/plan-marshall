import json, sys, os, re, glob
from datetime import datetime

ROOTS = sys.argv[1:]
launches = {}
events = []  # (ts, sess, tuid, status)

def parse(ts):
    return datetime.strptime(ts[:23], '%Y-%m-%dT%H:%M:%S.%f')

for root in ROOTS:
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        sess = os.path.basename(path).replace('.jsonl', '')
        try:
            for line in open(path, errors='replace'):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ts = d.get('timestamp', '')
                msg = d.get('message') or {}
                content = msg.get('content')
                if isinstance(content, list):
                    for it in content:
                        if isinstance(it, dict) and it.get('type') == 'tool_use' and it.get('name') == 'Bash':
                            inp = it.get('input') or {}
                            if inp.get('run_in_background'):
                                launches[it['id']] = (ts, sess)
                txt = content if isinstance(content, str) else ''
                if '<task-notification>' in txt:
                    m = re.search(r'<tool-use-id>([^<]+)</tool-use-id>', txt)
                    st = re.search(r'<status>([^<]*)</status>', txt)
                    if m and st:
                        events.append((ts, sess, m.group(1), st.group(1)))
        except Exception:
            pass

events = sorted(set(events))
# build intervals
iv = []
for ts, sess, tuid, st in events:
    if tuid in launches:
        iv.append((parse(launches[tuid][0]), parse(ts), launches[tuid][1], st))

def inflight(t, exclude_sess):
    return len({s for a, b, s, _ in iv if a <= t <= b and s != exclude_sess})

from collections import Counter
for status in ('killed', 'completed'):
    c = Counter()
    for a, b, s, st in iv:
        if st != status:
            continue
        c[inflight(b, s)] += 1
    tot = sum(c.values())
    if not tot:
        print(f'{status:10} n=    0  mean_other_sessions_inflight=0.00  dist={{}}')
        continue
    dist = {k: f'{v} ({v/tot*100:.0f}%)' for k, v in sorted(c.items())}
    mean = sum(k * v for k, v in c.items()) / tot
    print(f'{status:10} n={tot:5}  mean_other_sessions_inflight={mean:.2f}  dist={dist}')
