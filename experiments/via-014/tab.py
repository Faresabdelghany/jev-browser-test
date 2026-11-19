import json, collections, sys, statistics as st
for path in sys.argv[1:]:
    r = json.load(open(path)); specs = r["specs"]; print(path, f'elapsed {r["elapsed_ms"]/1000:.0f}s')
    for name, s in specs.items():
        if name.endswith("-via") and name[:-4] in specs: continue
        def row(n):
            runs = specs[n]["runs"]
            d = collections.Counter(x.get("outcome") for x in runs)
            return dict(d), int(st.median(x["wall_ms"] for x in runs)), int(st.median(x.get("requests") or 0 for x in runs))
        a = row(name)
        b = row(name + "-via") if name + "-via" in specs else None
        print(f"  {name:34} {a}" + (f"  | via {b}  {'SAME' if b and a[0]==b[0] else 'MOVED'}" if b else ""))
