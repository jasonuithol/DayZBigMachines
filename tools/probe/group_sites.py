import sys, re, glob, math
S = sys.argv[1]
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a","b","v","g","d","e","yo","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","y","","e","yu","ya"]))
def tr(s):
    out = "".join((TR.get(c.lower(), c) if c.lower() in TR else c) for c in s)
    return out[:1].upper() + out[1:] if any(c.lower() in TR for c in s) else s
KIND = [("Bulldozer", r"wreck_bulldozer"), ("Excavator", r"wreck_digger\.p3d"),
 ("Mining excavator", r"Wreck_Mining_Excavator"), ("Haul truck", r"Wreck_Mining_HaulTruck"),
 ("Crawler crane", r"wreck_crawlercrane_cabin"), ("Tower crane", r"\|Land_Construction_Crane\|"),
 ("Concrete mixer", r"concrete_mixer")]
for m in ["chernarusplus","enoch","sakhal","nasdara"]:
    lines = open(glob.glob(f"{S}/prof_{m}/script_*.log")[0], errors="replace").read().splitlines()
    towns, locs = [], []
    for l in lines:
        if "[BM] name|" in l:
            t, n, x, z = l.split("[BM] name|")[1].split("|")
            (towns if t in ("Capital","City","Village") else locs if t in ("Local","Camp","Ruin") else []).append((tr(n), float(x), float(z)))
    pts = []
    for l in lines:
        if "[BM] obj|" not in l: continue
        for label, rx in KIND:
            if re.search(rx, l, re.I):
                f = l.split("[BM] obj|")[1].split("|"); pts.append((label, float(f[2]), float(f[4]))); break
    # cluster all machines within 400 m
    clusters = []
    for p in pts:
        for c in clusters:
            if any(math.hypot(q[1]-p[1], q[2]-p[2]) < 400 for q in c): c.append(p); break
        else: clusters.append([p])
    # merge pass
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i+1, len(clusters)):
                if any(math.hypot(a[1]-b[1], a[2]-b[2]) < 400 for a in clusters[i] for b in clusters[j]):
                    clusters[i] += clusters.pop(j); merged = True; break
            if merged: break
    print(f"=== {m}  totals: " + ", ".join(f"{k} {sum(1 for p in pts if p[0]==k)}" for k,_ in KIND if any(p[0]==k for p in pts)))
    rows = []
    for c in clusters:
        cx = sum(p[1] for p in c)/len(c); cz = sum(p[2] for p in c)/len(c)
        t = min(towns, key=lambda n: math.hypot(n[1]-cx, n[2]-cz)); dt = math.hypot(t[1]-cx, t[2]-cz)
        lo = min(locs, key=lambda n: math.hypot(n[1]-cx, n[2]-cz)) if locs else None
        dl = math.hypot(lo[1]-cx, lo[2]-cz) if lo else 1e9
        where = f"{t[0]} ({dt/1000:.1f} km)" + (f" / {lo[0]}" if dl < 700 else "")
        counts = {}
        for p in c: counts[p[0]] = counts.get(p[0], 0) + 1
        rows.append((len(c), f"{cx:6.0f} {cz:6.0f}  {where}: " + ", ".join(f"{v} {k}" for k,v in counts.items())))
    for _, r in sorted(rows, reverse=True): print("  " + r)
