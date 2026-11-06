# Répartit les chapitres demandés en lots de taille équilibrée (pour la matrice GitHub Actions).
import json, sys, os
run = json.load(open("outils/bible-audio/run.json"))
idx = json.load(open("bible/index.json"))["books"]
books = run["books"] or list(range(1, 67))
items = []
for b in books:
    d = json.load(open(f"bible/{b:02d}.json"))["c"]
    for c, vs in enumerate(d, 1):
        items.append((b, c, sum(len(v) for v in vs)))
S = max(1, min(run["shards"], len(items)))
total = sum(i[2] for i in items); target = total / S
shards, cur, acc = [], [], 0
for it in items:
    cur.append(f"{it[0]}:{it[1]}"); acc += it[2]
    if acc >= target and len(shards) < S - 1: shards.append(" ".join(cur)); cur, acc = [], 0
if cur: shards.append(" ".join(cur))
matrix = {"include": [{"voice": v, "shard": i, "chapters": s} for v in run["voices"] for i, s in enumerate(shards)]}
with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as o:
    o.write("matrix=" + json.dumps(matrix) + "\n")
    o.write("release=" + ("true" if run.get("release") else "false") + "\n")
print(len(items), "chapitres,", total, "caractères,", len(shards), "lots par voix", file=sys.stderr)
