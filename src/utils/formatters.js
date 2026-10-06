export function rand(min, max) {
  return (min + max) / 2;
}

export function buildSeries(len, base, vol, opts = {}) {
  const arr = [];
  let v = base;
  const spikeAt = opts.spikeAt;
  const spikeMag = opts.spikeMag || 0;
  const recoverAt = opts.recoverAt;
  for (let i = 0; i < len; i++) {
    // Deterministic progression for mock data fallback
    const wave = Math.sin((i / len) * Math.PI * 2) * (vol * 0.4);
    v = base + wave;
    if (spikeAt !== undefined && i >= spikeAt && (recoverAt === undefined || i < recoverAt)) {
      v += spikeMag * Math.min(1, (i - spikeAt + 1) / 4);
    }
    if (recoverAt !== undefined && i >= recoverAt) {
      const decay = Math.max(0, 1 - (i - recoverAt) / 5);
      v = base + (v - base) * decay;
    }
    v = Math.max(opts.min ?? 0, Math.min(opts.max ?? 100, v));
    const hour = 12 + Math.floor(i / 12);
    const min = (i % 12) * 5;
    arr.push({ t: `${String(hour).padStart(2, "0")}:${String(min).padStart(2, "0")}`, value: Math.round(v * 10) / 10 });
  }
  return arr;
}

export function fmtBig(n) {
  return n.toLocaleString("en-US");
}
