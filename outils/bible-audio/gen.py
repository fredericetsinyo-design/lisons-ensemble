# Génère l'audio d'une liste de chapitres : un MP3 par chapitre + minutage de chaque verset.
# Usage : python gen.py <f|h> "8:1 8:2 ..." <dossier_sortie>
import json, sys, os, re, time, subprocess
import numpy as np
voice, chapters, out = sys.argv[1], sys.argv[2].split(), sys.argv[3]
os.makedirs(out, exist_ok=True)
idx = json.load(open("bible/index.json"))["books"]

def clean(t):
    t = t.replace("’", "'").replace("‘", "'").replace("«", "").replace("»", "").replace("—", ", ").replace("–", ", ")
    t = re.sub(r"\[|\]", "", t)
    return re.sub(r"\s+", " ", t).strip()

if voice == "f":
    from kokoro import KPipeline
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
    pipe = KPipeline(lang_code="f")
    SR = 24000
    def synth(text):
        parts = [np.asarray(a, dtype=np.float32).reshape(-1) for _, _, a in pipe(text, voice="ff_siwis", speed=1.0) if a is not None]
        return np.concatenate(parts) if parts else np.zeros(1, np.float32)
else:
    from piper import PiperVoice
    pv = PiperVoice.load("voices/fr_FR-tom-medium.onnx")
    SR = pv.config.sample_rate
    def synth(text):
        parts = [c.audio_float_array for c in pv.synthesize(text)]
        return np.concatenate(parts).astype(np.float32) if parts else np.zeros(1, np.float32)

def trim(a, th=0.008):
    nz = np.where(np.abs(a) > th)[0]
    if not len(nz): return a
    return a[max(0, nz[0] - int(SR * .03)): nz[-1] + int(SR * .06)]

stats = []
for ch in chapters:
    b, c = map(int, ch.split(":"))
    name = f"{b:02d}-{c:03d}"
    if os.path.exists(f"{out}/{name}.mp3"): continue
    t0 = time.time()
    verses = json.load(open(f"bible/{b:02d}.json"))["c"][c - 1]
    bk = idx[b - 1]["n"]
    intro = f"Psaume {c}." if bk == "Psaumes" else (f"{bk}." if idx[b - 1]["c"] == 1 else f"{bk}, chapitre {c}.")
    pcm = [trim(synth(intro)), np.zeros(int(SR * .75), np.float32)]
    pos = sum(len(x) for x in pcm); starts = []
    for v in verses:
        a = trim(synth(clean(v)))
        starts.append(round(pos / SR, 2))
        gap = np.zeros(int(SR * (.55 if re.search(r"[.!?]$", v.strip()) else .4)), np.float32)
        pcm += [a, gap]; pos += len(a) + len(gap)
    audio = np.concatenate(pcm)
    peak = np.max(np.abs(audio)) or 1
    audio = (audio / peak * 0.89 * 32767).astype(np.int16)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-af", "highpass=f=60", "-c:a", "libmp3lame", "-b:a", "40k", "-ar", "22050",
                    "-metadata", f"title={intro.rstrip('.')}", "-metadata", "artist=Lisons Ensemble",
                    "-metadata", "album=Bible Louis Segond 1910", f"{out}/{name}.mp3"], input=audio.tobytes(), check=True)
    dur = round(len(audio) / SR, 2)
    json.dump({"d": dur, "v": starts}, open(f"{out}/{name}.json", "w"))
    el = time.time() - t0
    chars = sum(len(v) for v in verses)
    stats.append(f"{name} {chars} car. {dur}s audio en {el:.1f}s (x{dur/el:.1f} temps réel)")
    print(stats[-1], flush=True)
open(f"{out}/stats-{voice}-{os.getpid()}.txt", "w").write("\n".join(stats) + "\n")
