import json, sys, os, re, glob
from datetime import datetime

ROOTS = sys.argv[1:]
launches = {}
kills = []

def parse(ts):
    return datetime.strptime(ts[:23], '%Y-%m-%dT%H:%M:%S.%f')

for root in ROOTS:
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        sess = os.path.basename(path).replace('.jsonl', '')
        repo = root.split('-')[-1]
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
                                launches[it['id']] = (ts, sess, inp.get('command', ''))
                txt = content if isinstance(content, str) else ''
                if '<status>killed</status>' in txt:
                    m = re.search(r'<tool-use-id>([^<]+)</tool-use-id>', txt)
                    if m:
                        kills.append((ts, sess, repo, m.group(1)))
        except Exception:
            pass

kills = sorted(set(kills))
if not kills:
    print('total kills=0  clusters=0  multi-session clusters(<=5s)=0')
    print('kills inside multi-session clusters = 0')
    sys.exit(0)
# cluster kills within 5s across DIFFERENT sessions
clusters = []
cur = [kills[0]]
for k in kills[1:]:
    if (parse(k[0]) - parse(cur[-1][0])).total_seconds() <= 5:
        cur.append(k)
    else:
        clusters.append(cur)
        cur = [k]
clusters.append(cur)

multi = [c for c in clusters if len({x[1] for x in c}) > 1]
print(f'total kills={len(kills)}  clusters={len(clusters)}  multi-session clusters(<=5s)={len(multi)}')
print(f'kills inside multi-session clusters = {sum(len(c) for c in multi)}')
print()
for c in multi:
    span = (parse(c[-1][0]) - parse(c[0][0])).total_seconds()
    print(f'--- cluster {c[0][0]}  n={len(c)}  span={span:.2f}s  sessions={sorted({x[1][:8] for x in c})} repos={sorted({x[2] for x in c})}')
    for ts, sess, repo, tuid in c:
        if tuid in launches:
            lts, lsess, cmd = launches[tuid]
            el = (parse(ts) - parse(lts)).total_seconds()
            print(f'    {ts[11:23]} {sess[:8]} elapsed={el:7.0f}s  {cmd[:85]}')
        else:
            print(f'    {ts[11:23]} {sess[:8]} elapsed=      ?  [launch not found]')
