# Regroupe les minutages des chapitres par livre : bible/audio/<voix>/<livre>.json = {"<chap>": {"d":..,"v":[..]}}
import json, glob, os, sys
for f in sorted(glob.glob("dl/**/*.json", recursive=True)):
    voice = f.split("bible-")[1].split("-")[0]
    b, c = os.path.basename(f)[:-5].split("-")
    p = f"bible/audio/{voice}/{b}.json"; os.makedirs(os.path.dirname(p), exist_ok=True)
    d = json.load(open(p)) if os.path.exists(p) else {}
    d[str(int(c))] = json.load(open(f))
    json.dump(dict(sorted(d.items(), key=lambda kv: int(kv[0]))), open(p, "w"), separators=(",", ":"))
