import json, sys, re, subprocess, os
import numpy as np, soundfile as sf
engine = sys.argv[1]; out = "out"; os.makedirs(out, exist_ok=True)
T = json.load(open("voix-test/textes.json", encoding="utf-8"))
def sentences(t): return [s for s in re.split(r'(?<=[.!?…»])\s+', t) if s.strip()]
def save(name, chunks, sr, gap=0.28):
    sil = np.zeros(int(sr*gap), dtype=np.float32); parts=[]
    for c in chunks: parts += [np.asarray(c, dtype=np.float32).reshape(-1), sil]
    sf.write(f"{out}/{name}.wav", np.concatenate(parts), sr)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"{out}/{name}.wav","-ac","1","-b:a","64k",f"{out}/{name}.mp3"], check=True)
    os.remove(f"{out}/{name}.wav")
if engine == "chatterbox":
    import torch
    _l = torch.load
    torch.load = lambda *a, **k: _l(*a, **{**k, "map_location": "cpu"})
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    for key, txt in T.items():
        save(f"chatterbox-{key}", [m.generate(s, language_id="fr", exaggeration=0.45, cfg_weight=0.5).squeeze(0).numpy() for s in sentences(txt)], m.sr)
elif engine == "kokoro":
    from kokoro import KPipeline
    p = KPipeline(lang_code="f")
    for key, txt in T.items():
        save(f"kokoro-{key}", [a.numpy() if hasattr(a,'numpy') else a for _,_,a in p(txt, voice="ff_siwis", speed=0.95)], 24000, gap=0.15)
elif engine == "piper":
    for v in ["fr_FR-siwis-medium", "fr_FR-tom-medium", "fr_FR-upmc-medium"]:
        for key, txt in T.items():
            subprocess.run(["piper","-m",f"voices/{v}.onnx","-f",f"{out}/piper-{v}-{key}.wav"], input=txt.encode(), check=True)
            subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"{out}/piper-{v}-{key}.wav","-ac","1","-b:a","64k",f"{out}/piper-{v.split('-')[1]}-{key}.mp3"], check=True)
            os.remove(f"{out}/piper-{v}-{key}.wav")
