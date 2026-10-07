import json, sys, os, re, glob
from datetime import datetime

ROOTS = sys.argv[1:]
notifs = []  # (ts, sess, status)

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
                txt = content if isinstance(content, str) else ''
                if '<task-notification>' in txt:
                    st = re.search(r'<status>([^<]*)</status>', txt)
                    notifs.append((ts, sess, st.group(1) if st else '?'))
        except Exception:
            pass

notifs = sorted(set(notifs))
from collections import Counter
print('notification status counts:', Counter(s for _, _, s in notifs))
print('total notifications:', len(notifs))
print()

def clusters_for(statuses, label):
    sel = [n for n in notifs if n[2] in statuses]
    if not sel:
        print(f'{label}: n=0  multi-session clusters(<=5s)=0  notifs_in_multi=0  rate=0.0%')
        return []
    cl = []
    cur = [sel[0]]
    for k in sel[1:]:
        if (parse(k[0]) - parse(cur[-1][0])).total_seconds() <= 5:
            cur.append(k)
        else:
            cl.append(cur)
            cur = [k]
    cl.append(cur)
    multi = [c for c in cl if len({x[1] for x in c}) > 1]
    n_in = sum(len(c) for c in multi)
    print(f'{label}: n={len(sel)}  multi-session clusters(<=5s)={len(multi)}  notifs_in_multi={n_in}  rate={n_in/len(sel)*100:.1f}%')
    return multi

clusters_for({'killed'}, 'KILLED')
clusters_for({'completed'}, 'COMPLETED')
