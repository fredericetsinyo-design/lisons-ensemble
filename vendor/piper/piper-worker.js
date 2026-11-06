/* Lisons Ensemble — Piper neural voice running on the phone (Web Worker).
   Phonemes: espeak-ng compiled to WebAssembly (piper_phonemize). Voice: Piper VITS model run by ONNX Runtime Web.
   Everything is downloaded once into Cache Storage, then works offline. Licences: Piper (MIT), espeak-ng (GPL-3.0),
   ONNX Runtime (MIT), voices Siwis (CC BY 4.0) and Tom (AGPL-3.0), see voices/. */
importScripts('ort.wasm.min.js', 'piper_phonemize.js');
const BASE = new URL('./', self.location.href).href;
const ROOT = new URL('../../', self.location.href).href;
ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = BASE;
const CACHE = 'le-piper-v1';
const voices = {};               // voiceId -> {session, cfg}
let phon = null;                 // {wasm, data}
let chain = Promise.resolve();   // one job at a time

async function getFile(url, onProgress){
  const c = await caches.open(CACHE);
  const hit = await c.match(url); if (hit) return hit.arrayBuffer();
  const r = await fetch(url); if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url);
  const total = +(r.headers.get('Content-Length') || 0); let loaded = 0; const parts = [];
  const rd = r.body.getReader();
  for (;;) { const {done, value} = await rd.read(); if (done) break; parts.push(value); loaded += value.length; if (onProgress) onProgress(loaded, total); }
  const blob = new Blob(parts); await c.put(url, new Response(blob, {headers:{'Content-Type':'application/octet-stream'}}));
  return blob.arrayBuffer();
}
async function phonemizer(){
  if (!phon) phon = {wasm: await getFile(BASE + 'piper_phonemize.wasm'), data: await getFile(BASE + 'piper_phonemize.data')};
  return phon;
}
async function loadVoice(id, onProgress){
  if (voices[id]) return voices[id];
  const sizes = {model: 63e6, rest: 30e6}; let a = 0, b = 0;
  const report = () => onProgress && onProgress(a + b, sizes.model + sizes.rest);
  await phonemizer();
  await getFile(BASE + 'ort-wasm-simd.wasm', l => { b = l; report(); });
  const cfg = JSON.parse(new TextDecoder().decode(await getFile(ROOT + 'voices/' + id + '.onnx.json')));
  const model = await getFile(ROOT + 'voices/' + id + '.onnx', (l, t) => { a = l; if (t) sizes.model = t; report(); });
  const session = await ort.InferenceSession.create(model, {executionProviders:['wasm']});
  return voices[id] = {session, cfg};
}
async function phonemeIds(text, voice){
  const {wasm, data} = await phonemizer();
  return new Promise((resolve, reject) => {
    let out = null;
    createPiperPhonemize({
      wasmBinary: wasm,
      getPreloadedPackage: () => data.slice(0),
      locateFile: u => BASE + u,
      print: line => { try { out = JSON.parse(line).phoneme_ids; } catch(e){} },
      printErr: () => {},
    }).then(m => {
      try { m.callMain(['-l', voice, '--input', JSON.stringify([{text}]), '--espeak_data', '/espeak-ng-data']); } catch(e){ if (!out) return reject(e); }
      out ? resolve(out) : reject(new Error('phonemes'));
    }, reject);
  });
}
function wav(pcm, rate){
  const n = pcm.length, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true);
  let peak = 0; for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(pcm[i]));
  const g = peak > 0 ? Math.min(1 / peak, 3) * 0.9 : 1;
  for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, pcm[i] * g)) * 32767, true);
  return buf;
}
async function speak(id, text){
  const {session, cfg} = await loadVoice(id);
  const ids = await phonemeIds(text, cfg.espeak.voice);
  const inf = cfg.inference || {};
  const feeds = {
    input: new ort.Tensor('int64', BigInt64Array.from(ids.map(BigInt)), [1, ids.length]),
    input_lengths: new ort.Tensor('int64', BigInt64Array.from([BigInt(ids.length)]), [1]),
    scales: new ort.Tensor('float32', Float32Array.from([inf.noise_scale ?? 0.667, inf.length_scale ?? 1, inf.noise_w ?? 0.8]), [3]),
  };
  if (cfg.num_speakers > 1) feeds.sid = new ort.Tensor('int64', BigInt64Array.from([0n]), [1]);
  const res = await session.run(feeds);
  const pcm = res.output.data;
  // a short silence at the end so sentences breathe
  const rate = cfg.audio.sample_rate, tail = Math.round(rate * 0.12), all = new Float32Array(pcm.length + tail); all.set(pcm);
  return wav(all, rate);
}
self.onmessage = e => {
  const m = e.data;
  chain = chain.then(async () => {
    try {
      if (m.type === 'load') { await loadVoice(m.voice, (loaded, total) => self.postMessage({id:m.id, type:'progress', loaded, total})); self.postMessage({id:m.id, ok:true}); }
      else if (m.type === 'speak') { const w = await speak(m.voice, m.text); self.postMessage({id:m.id, ok:true, wav:w}, [w]); }
    } catch(err){ self.postMessage({id:m.id, error:String(err && err.message || err)}); }
  });
};
