<script setup lang="ts">
import { computed, ref } from "vue";

interface Cplx {
  re: number;
  im: number;
}

const cMul = (a: Cplx, b: Cplx): Cplx => ({
  re: a.re * b.re - a.im * b.im,
  im: a.re * b.im + a.im * b.re,
});
const cDiv = (a: Cplx, b: Cplx): Cplx => {
  const d = b.re * b.re + b.im * b.im || 1e-18;
  return { re: (a.re * b.re + a.im * b.im) / d, im: (a.im * b.re - a.re * b.im) / d };
};

type Mode = "nyq3" | "bodeEx" | "comp";
const mode = ref<Mode>("comp");
const gainK = ref(4.0);
const compAlpha = ref(1.0); // >1 lead, <1 lag, =1 uncompensated
const compT = ref(0.25);

const selectMode = (m: Mode): void => {
  mode.value = m;
  if (m === "nyq3") {
    gainK.value = 100;
  } else if (m === "bodeEx") {
    gainK.value = 5;
  } else {
    gainK.value = 4.0;
    compAlpha.value = 1.0;
    compT.value = 0.25;
  }
};

const applyCompPreset = (k: number, a: number, t: number): void => {
  mode.value = "comp";
  gainK.value = k;
  compAlpha.value = a;
  compT.value = t;
};

// Evaluate L(jw) and exact unwrapped phase (deg)
const evalL = (w: number): { val: Cplx; magDb: number; phaseDeg: number } => {
  const K = gainK.value;
  if (mode.value === "nyq3") {
    // K / [(jw+1)(0.5jw+1)(0.2jw+1)]
    const d1: Cplx = { re: 1, im: w };
    const d2: Cplx = { re: 1, im: 0.5 * w };
    const d3: Cplx = { re: 1, im: 0.2 * w };
    const den = cMul(cMul(d1, d2), d3);
    const val = cDiv({ re: K, im: 0 }, den);
    const mag = Math.hypot(val.re, val.im);
    const phaseDeg =
      -(Math.atan(w) + Math.atan(0.5 * w) + Math.atan(0.2 * w)) * (180 / Math.PI);
    return { val, magDb: 20 * Math.log10(Math.max(mag, 1e-9)), phaseDeg };
  }

  if (mode.value === "bodeEx") {
    // K(0.1jw+1) / [jw (0.5jw+1) (1 - w^2/2500 + j*0.6w/50)]
    const num: Cplx = { re: K, im: K * 0.1 * w };
    const d0: Cplx = { re: 0, im: w };
    const d1: Cplx = { re: 1, im: 0.5 * w };
    const d2: Cplx = { re: 1 - (w * w) / 2500, im: (0.6 / 50) * w };
    const den = cMul(cMul(d0, d1), d2);
    const val = cDiv(num, den);
    const mag = Math.hypot(val.re, val.im);
    const phaseDeg =
      -90 +
      (Math.atan(0.1 * w) -
        Math.atan(0.5 * w) -
        Math.atan2((0.6 / 50) * w, 1 - (w * w) / 2500)) *
        (180 / Math.PI);
    return { val, magDb: 20 * Math.log10(Math.max(mag, 1e-9)), phaseDeg };
  }

  // Compensated plant: K / [jw (0.5jw+1)(0.2jw+1)] * (alpha*T*jw + 1)/(T*jw + 1)
  const a = compAlpha.value;
  const T = compT.value;
  const num: Cplx = { re: K, im: K * a * T * w };
  const d0: Cplx = { re: 0, im: w };
  const d1: Cplx = { re: 1, im: 0.5 * w };
  const d2: Cplx = { re: 1, im: 0.2 * w };
  const d3: Cplx = { re: 1, im: T * w };
  const den = cMul(cMul(cMul(d0, d1), d2), d3);
  const val = cDiv(num, den);
  const mag = Math.hypot(val.re, val.im);
  const phaseDeg =
    -90 +
    (Math.atan(a * T * w) - Math.atan(0.5 * w) - Math.atan(0.2 * w) - Math.atan(T * w)) *
      (180 / Math.PI);
  return { val, magDb: 20 * Math.log10(Math.max(mag, 1e-9)), phaseDeg };
};

const freqRange = computed(() => {
  if (mode.value === "bodeEx") return { logMin: -1, logMax: 2.4 };
  return { logMin: -1, logMax: 2 };
});

const sweep = computed(() => {
  const { logMin, logMax } = freqRange.value;
  const N = 320;
  const ws: number[] = [];
  const mags: number[] = [];
  const phases: number[] = [];
  const nyq: Cplx[] = [];

  for (let i = 0; i <= N; i++) {
    const w = Math.pow(10, logMin + ((logMax - logMin) * i) / N);
    const r = evalL(w);
    ws.push(w);
    mags.push(r.magDb);
    phases.push(r.phaseDeg);
    nyq.push(r.val);
  }

  // Find gain crossover (magDb crosses 0 downward)
  let wg: number | null = null;
  let pm: number | null = null;
  for (let i = 1; i < mags.length; i++) {
    if ((mags[i - 1] >= 0 && mags[i] <= 0) || (mags[i - 1] <= 0 && mags[i] >= 0)) {
      const frac = (0 - mags[i - 1]) / (mags[i] - mags[i - 1] || 1e-9);
      wg = ws[i - 1] * Math.pow(ws[i] / ws[i - 1], frac);
      const r = evalL(wg);
      pm = 180 + r.phaseDeg;
      break;
    }
  }

  // Find phase crossover (phaseDeg crosses -180 downward)
  let wp: number | null = null;
  let gm: number | null = null;
  for (let i = 1; i < phases.length; i++) {
    if (phases[i - 1] >= -180 && phases[i] <= -180) {
      const frac = (-180 - phases[i - 1]) / (phases[i] - phases[i - 1] || 1e-9);
      wp = ws[i - 1] * Math.pow(ws[i] / ws[i - 1], frac);
      const r = evalL(wp);
      gm = -r.magDb;
      break;
    }
  }

  const stable =
    (gm === null || gm > 0.05) && (pm === null || pm > 0.2) && (wg === null || wp === null || wg < wp);

  return { ws, mags, phases, nyq, wg, wp, gm, pm, stable };
});

// Bode SVG geometry
const BW = 360;
const BH = 148;
const bPadL = 42;
const bPadR = 14;
const bPadT = 12;
const bPadB = 22;

const bx = (w: number): number => {
  const { logMin, logMax } = freqRange.value;
  return bPadL + ((Math.log10(w) - logMin) / (logMax - logMin)) * (BW - bPadL - bPadR);
};
const bMagY = (db: number): number => {
  const clamped = Math.max(-60, Math.min(50, db));
  return bPadT + ((50 - clamped) / 110) * (BH - bPadT - bPadB);
};
const bPhY = (deg: number): number => {
  const clamped = Math.max(-280, Math.min(0, deg));
  return bPadT + ((0 - clamped) / 280) * (BH - bPadT - bPadB);
};

const magPath = computed(() =>
  sweep.value.ws
    .map((w, i) => `${i === 0 ? "M" : "L"}${bx(w).toFixed(1)},${bMagY(sweep.value.mags[i]).toFixed(1)}`)
    .join(" ")
);

const phasePath = computed(() =>
  sweep.value.ws
    .map((w, i) => `${i === 0 ? "M" : "L"}${bx(w).toFixed(1)},${bPhY(sweep.value.phases[i]).toFixed(1)}`)
    .join(" ")
);

// Nyquist SVG geometry (zoomed cleanly around (-1, j0) and unit circle)
const NW = 290;
const NH = 304;
const nyqLim = computed(() => (mode.value === "nyq3" && gainK.value > 25 ? 2.6 : 1.9));
const nx = (re: number): number => 24 + ((re + nyqLim.value) / (nyqLim.value * 1.55)) * (NW - 36);
const ny = (im: number): number => NH / 2 - (im / (nyqLim.value * 0.95)) * (NH / 2 - 22);

const nyqPath = computed(() => {
  const lim = nyqLim.value * 3.5;
  const segs: string[] = [];
  let penDown = false;
  for (const pt of sweep.value.nyq) {
    if (Math.abs(pt.re) <= lim && Math.abs(pt.im) <= lim) {
      segs.push(`${penDown ? "L" : "M"}${nx(pt.re).toFixed(1)},${ny(pt.im).toFixed(1)}`);
      penDown = true;
    } else {
      penDown = false;
    }
  }
  return segs.join(" ");
});

const unitCirclePath = computed(() => {
  const pts: string[] = [];
  for (let i = 0; i <= 72; i++) {
    const th = (2 * Math.PI * i) / 72;
    pts.push(`${i === 0 ? "M" : "L"}${nx(Math.cos(th)).toFixed(1)},${ny(Math.sin(th)).toFixed(1)}`);
  }
  return pts.join(" ");
});

const formulaText = computed(() => {
  if (mode.value === "nyq3") {
    return `L(s) = ${gainK.value.toFixed(1)} / [(s + 1)(0.5s + 1)(0.2s + 1)]`;
  }
  if (mode.value === "bodeEx") {
    return `L(s) = ${gainK.value.toFixed(1)}(0.1s + 1) / [s(0.5s + 1)(s²/2500 + 0.6s/50 + 1)]`;
  }
  const tag = compAlpha.value > 1.05 ? "超前" : compAlpha.value < 0.95 ? "滞后" : "无校正";
  return `L(s) = ${gainK.value.toFixed(1)} / [s(0.5s+1)(0.2s+1)] · (${(compAlpha.value * compT.value).toFixed(2)}s+1)/(${compT.value.toFixed(2)}s+1) [${tag}]`;
});

const compMaxPhase = computed(() => {
  const a = compAlpha.value;
  return (Math.asin((a - 1) / (a + 1)) * 180) / Math.PI;
});
</script>

<template>
  <div class="ctrl-lab">
    <div class="ctrl-lab-head">
      <div>
        <span class="ctrl-lab-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ctrl-lab-title">伯德图、奈奎斯特图与超前/滞后校正实验室</h4>
      </div>
      <span class="ctrl-status" :class="sweep.stable ? 'is-ok' : 'is-bad'">
        {{ sweep.stable ? "闭环稳定 (GM > 0, PM > 0)" : "闭环不稳定 (包围 −1 点)" }}
      </span>
    </div>

    <div class="ctrl-presets">
      <button type="button" class="ctrl-chip" :class="{ 'is-active': mode === 'comp' }" @click="selectMode('comp')">
        超前 / 滞后校正实验
      </button>
      <button type="button" class="ctrl-chip" :class="{ 'is-active': mode === 'nyq3' }" @click="selectMode('nyq3')">
        笔记例题：三阶奈奎斯特 (K=100)
      </button>
      <button type="button" class="ctrl-chip" :class="{ 'is-active': mode === 'bodeEx' }" @click="selectMode('bodeEx')">
        笔记例题：综合伯德图 (K=5)
      </button>
      <button type="button" class="ctrl-chip" @click="applyCompPreset(8, 5, 0.14)">
        一键演示：超前校正挽救不稳定
      </button>
      <button type="button" class="ctrl-chip" @click="applyCompPreset(8, 0.2, 5.0)">
        一键演示：滞后校正提裕度
      </button>
    </div>

    <div class="bn-formula">
      <code>{{ formulaText }}</code>
    </div>

    <div class="ctrl-controls">
      <label class="ctrl-slider">
        <span class="ctrl-slider-row">
          <span>开环增益 K</span>
          <strong>K = {{ gainK.toFixed(1) }}</strong>
        </span>
        <input
          v-model.number="gainK"
          type="range"
          :min="mode === 'nyq3' ? 1 : 0.5"
          :max="mode === 'nyq3' ? 120 : 25"
          :step="mode === 'nyq3' ? 0.5 : 0.2"
        />
      </label>

      <template v-if="mode === 'comp'">
        <label class="ctrl-slider">
          <span class="ctrl-slider-row">
            <span>校正系数 α（&gt;1 超前 / &lt;1 滞后）</span>
            <strong>α = {{ compAlpha.toFixed(2) }}（φ<sub>m</sub> = {{ compMaxPhase >= 0 ? "+" : "" }}{{ compMaxPhase.toFixed(1) }}°）</strong>
          </span>
          <input v-model.number="compAlpha" type="range" min="0.1" max="10" step="0.05" />
        </label>

        <label class="ctrl-slider bn-span2">
          <span class="ctrl-slider-row">
            <span>校正时间常数 T（ω<sub>m</sub> = 1 / (T√α) = {{ (1 / (compT * Math.sqrt(compAlpha))).toFixed(2) }} rad/s）</span>
            <strong>T = {{ compT.toFixed(2) }} s</strong>
          </span>
          <input v-model.number="compT" type="range" min="0.04" max="6.0" step="0.02" />
        </label>
      </template>
    </div>

    <div class="bn-grid">
      <div class="bn-bode-col">
        <!-- Bode Magnitude -->
        <div class="ctrl-panel">
          <div class="ctrl-panel-label">对数幅频特性 L(ω) / dB</div>
          <svg :viewBox="`0 0 ${BW} ${BH}`" class="ctrl-svg">
            <line :x1="bPadL" :y1="bMagY(0)" :x2="BW - bPadR" :y2="bMagY(0)" class="svg-zero-line" />
            <line :x1="bPadL" :y1="bPadT" :x2="bPadL" :y2="BH - bPadB" class="svg-axis" />
            <line :x1="bPadL" :y1="BH - bPadB" :x2="BW - bPadR" :y2="BH - bPadB" class="svg-axis" />
            <text v-for="db in [40, 20, 0, -20, -40]" :key="db" :x="bPadL - 5" :y="bMagY(db) + 3" class="svg-tick" text-anchor="end">
              {{ db }}
            </text>
            <line v-if="sweep.wg" :x1="bx(sweep.wg)" :y1="bPadT" :x2="bx(sweep.wg)" :y2="BH - bPadB" class="svg-wg" />
            <line v-if="sweep.wp" :x1="bx(sweep.wp)" :y1="bPadT" :x2="bx(sweep.wp)" :y2="BH - bPadB" class="svg-wp" />
            <path :d="magPath" fill="none" class="svg-curve" />
            <circle v-if="sweep.wg" :cx="bx(sweep.wg)" :cy="bMagY(0)" r="3.6" class="svg-dot-g" />
          </svg>
        </div>

        <!-- Bode Phase -->
        <div class="ctrl-panel">
          <div class="ctrl-panel-label">对数相频特性 φ(ω) / deg</div>
          <svg :viewBox="`0 0 ${BW} ${BH}`" class="ctrl-svg">
            <line :x1="bPadL" :y1="bPhY(-180)" :x2="BW - bPadR" :y2="bPhY(-180)" class="svg-crit-line" />
            <line :x1="bPadL" :y1="bPadT" :x2="bPadL" :y2="BH - bPadB" class="svg-axis" />
            <line :x1="bPadL" :y1="BH - bPadB" :x2="BW - bPadR" :y2="BH - bPadB" class="svg-axis" />
            <text v-for="deg in [0, -90, -180, -270]" :key="deg" :x="bPadL - 5" :y="bPhY(deg) + 3" class="svg-tick" text-anchor="end">
              {{ deg }}°
            </text>
            <text v-for="exp in [-1, 0, 1, 2]" :key="exp" :x="bx(Math.pow(10, exp))" :y="BH - 6" class="svg-tick" text-anchor="middle">
              10{{ exp === -1 ? "⁻¹" : exp === 0 ? "⁰" : exp === 1 ? "¹" : "²" }}
            </text>
            <line v-if="sweep.wg" :x1="bx(sweep.wg)" :y1="bPadT" :x2="bx(sweep.wg)" :y2="BH - bPadB" class="svg-wg" />
            <line v-if="sweep.wp" :x1="bx(sweep.wp)" :y1="bPadT" :x2="bx(sweep.wp)" :y2="BH - bPadB" class="svg-wp" />
            <path :d="phasePath" fill="none" class="svg-curve-ph" />
            <circle v-if="sweep.wp" :cx="bx(sweep.wp)" :cy="bPhY(-180)" r="3.6" class="svg-dot-p" />
          </svg>
        </div>
      </div>

      <!-- Nyquist Plot -->
      <div class="ctrl-panel">
        <div class="ctrl-panel-label">奈奎斯特图 L(jω)（正频率局部放大，含单位圆与 −1 点）</div>
        <svg :viewBox="`0 0 ${NW} ${NH}`" class="ctrl-svg">
          <defs>
            <clipPath id="nyq-clip">
              <rect x="16" y="14" :width="NW - 28" :height="NH - 32" />
            </clipPath>
          </defs>
          <line x1="16" :y1="ny(0)" :x2="NW - 12" :y2="ny(0)" class="svg-axis" />
          <line :x1="nx(0)" y1="14" :x2="nx(0)" :y2="NH - 18" class="svg-axis" />
          <g clip-path="url(#nyq-clip)">
            <path :d="unitCirclePath" fill="none" class="svg-unit-circle" />
            <path :d="nyqPath" fill="none" class="svg-curve" />
            <!-- (-1, j0) critical point -->
            <g :transform="`translate(${nx(-1)},${ny(0)})`">
              <line x1="-5" y1="-5" x2="5" y2="5" class="svg-crit-x" />
              <line x1="-5" y1="5" x2="5" y2="-5" class="svg-crit-x" />
              <text x="-6" y="-8" class="svg-crit-lbl" text-anchor="end">(−1, j0)</text>
            </g>
          </g>
          <rect x="16" y="14" :width="NW - 28" :height="NH - 32" fill="none" class="svg-frame" />
          <text :x="NW - 16" :y="ny(0) - 5" class="svg-tick" text-anchor="end">Re</text>
          <text :x="nx(0) + 5" y="25" class="svg-tick">Im</text>
        </svg>
      </div>
    </div>

    <div class="ctrl-metrics">
      <div class="ctrl-metric">
        <span>截止频率 ω<sub>g</sub></span>
        <strong>{{ sweep.wg !== null ? sweep.wg.toFixed(2) + " rad/s" : "无穿越" }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>相位穿越 ω<sub>p</sub></span>
        <strong>{{ sweep.wp !== null ? sweep.wp.toFixed(2) + " rad/s" : "无穿越" }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>幅值裕度 GM</span>
        <strong>{{ sweep.gm !== null ? (sweep.gm >= 0 ? "+" : "") + sweep.gm.toFixed(1) + " dB" : "∞ dB" }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>相角裕度 PM</span>
        <strong>{{ sweep.pm !== null ? (sweep.pm >= 0 ? "+" : "") + sweep.pm.toFixed(1) + "°" : "—" }}</strong>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ctrl-lab {
  margin: 1.5rem 0;
  padding: 1.15rem 1.25rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  font-size: 0.92rem;
  line-height: 1.5;
}

.ctrl-lab-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.ctrl-lab-badge {
  display: inline-block;
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.ctrl-lab-title {
  margin: 0.15rem 0 0 !important;
  color: var(--ink);
  font-size: 1.05rem;
  font-weight: 700;
}

.ctrl-status {
  padding: 0.2rem 0.65rem;
  border-radius: var(--r, 2px);
  font-family: var(--vp-font-mono);
  font-size: 0.78rem;
  font-weight: 600;

  &.is-ok {
    border: 1px solid #1e7a56;
    background: rgb(30 122 86 / 12%);
    color: #1e7a56;
  }

  &.is-bad {
    border: 1px solid #c83e37;
    background: rgb(200 62 55 / 12%);
    color: #c83e37;
  }
}

.ctrl-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.7rem;
}

.ctrl-chip {
  padding: 0.26rem 0.62rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.8rem;
  cursor: pointer;

  &.is-active,
  &:hover {
    border-color: var(--vp-c-accent);
    background: var(--vp-c-accent-soft);
    color: var(--vp-c-accent);
    font-weight: 600;
  }
}

.bn-formula {
  margin-bottom: 0.75rem;

  code {
    display: inline-block;
    padding: 0.22rem 0.55rem;
    border: 1px solid var(--vp-c-border);
    border-radius: var(--r, 2px);
    background: var(--vp-c-bg);
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-size: 0.82rem;
  }
}

.ctrl-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1.15rem;
  margin-bottom: 0.85rem;
}

.bn-span2 {
  grid-column: 1 / -1;
}

.ctrl-slider {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
}

.ctrl-slider-row {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.83rem;

  strong {
    color: var(--vp-c-accent);
    font-family: var(--vp-font-mono);
    font-variant-numeric: tabular-nums;
  }
}

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;
}

.bn-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 0.75rem;
  margin-bottom: 0.8rem;
}

.bn-bode-col {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.ctrl-panel {
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.ctrl-panel-label {
  margin-bottom: 0.3rem;
  color: var(--vp-c-text-mute);
  font-size: 0.76rem;
  font-weight: 600;
}

.ctrl-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-frame {
  stroke: var(--vp-c-border);
  stroke-width: 1;
}

.svg-zero-line {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-crit-line {
  stroke: #c83e37;
  stroke-width: 1.1;
  stroke-dasharray: 4 3;
}

.svg-wg {
  stroke: #1e7a56;
  stroke-width: 1.1;
  stroke-dasharray: 3 3;
}

.svg-wp {
  stroke: #8552a1;
  stroke-width: 1.1;
  stroke-dasharray: 3 3;
}

.svg-unit-circle {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  stroke-dasharray: 4 3;
  opacity: 0.65;
}

.svg-curve {
  stroke: var(--vp-c-accent);
  stroke-width: 2.2;
}

.svg-curve-ph {
  stroke: #1e7a56;
  stroke-width: 2.2;
}

.svg-dot-g {
  fill: #1e7a56;
}

.svg-dot-p {
  fill: #8552a1;
}

.svg-crit-x {
  stroke: #c83e37;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.svg-crit-lbl {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
}

.ctrl-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}

.ctrl-metric {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);

  span {
    display: block;
    color: var(--vp-c-text-mute);
    font-size: 0.72rem;
  }

  strong {
    display: block;
    margin-top: 0.15rem;
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-size: 0.84rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .ctrl-controls,
  .bn-grid {
    grid-template-columns: 1fr;
  }

  .ctrl-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
