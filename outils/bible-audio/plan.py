# Répartit les chapitres demandés en lots de taille équilibrée (pour la matrice GitHub Actions).
import json, sys, os
run = json.load(open("outils/bible-audio/run.json"))
idx = json.load(open("bible/index.json"))["books"]
books = run["books"] or [b for b in range(1, 67) if b not in run.get("skip", [])]
items = []
for b in books:
    d = json.load(open(f"bible/{b:02d}.json"))["c"]
    for c, vs in enumerate(d, 1):
        items.append((b, c, sum(len(v) for v in vs)))
def split(S):
    S = max(1, min(S, len(items))); total = sum(i[2] for i in items); target = total / S
    shards, cur, acc = [], [], 0
    for it in items:
        cur.append(f"{it[0]}:{it[1]}"); acc += it[2]
        if acc >= target and len(shards) < S - 1: shards.append(" ".join(cur)); cur, acc = [], 0
    if cur: shards.append(" ".join(cur))
    return shards
sh = run["shards"]
per = {v: split(sh[v] if isinstance(sh, dict) else sh) for v in run["voices"]}
matrix = {"include": [{"voice": v, "shard": i, "chapters": c} for v in run["voices"] for i, c in enumerate(per[v])]}
with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as o:
    o.write("matrix=" + json.dumps(matrix) + "\n")
    o.write("release=" + ("true" if run.get("release") else "false") + "\n")
print(len(items), "chapitres,", {v: len(x) for v, x in per.items()}, "lots", file=sys.stderr)
