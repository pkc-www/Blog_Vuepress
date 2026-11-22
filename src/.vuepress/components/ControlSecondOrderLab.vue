<script setup lang="ts">
import { computed, ref } from "vue";

const zeta = ref(0.4);
const wn = ref(3.0);
const enableZero = ref(false);
const zeroVal = ref(4.0); // transfer factor (1 + s / z), zero at s = -z
const enablePole = ref(false);
const poleVal = ref(8.0); // transfer factor 1 / (1 + s / p), pole at s = -p

interface Preset {
  label: string;
  zeta: number;
  wn: number;
  enableZero: boolean;
  zeroVal: number;
  enablePole: boolean;
  poleVal: number;
}

const presets: Preset[] = [
  { label: "典型欠阻尼 (ζ=0.4)", zeta: 0.4, wn: 3.0, enableZero: false, zeroVal: 4, enablePole: false, poleVal: 8 },
  { label: "最佳阻尼 (ζ=0.707)", zeta: 0.707, wn: 3.0, enableZero: false, zeroVal: 4, enablePole: false, poleVal: 8 },
  { label: "临界阻尼 (ζ=1.0)", zeta: 1.0, wn: 3.0, enableZero: false, zeroVal: 4, enablePole: false, poleVal: 8 },
  { label: "过阻尼 + LHP 零点超调", zeta: 1.2, wn: 2.5, enableZero: true, zeroVal: 1.2, enablePole: false, poleVal: 8 },
  { label: "非最小相位 (RHP 零点下冲)", zeta: 0.6, wn: 3.0, enableZero: true, zeroVal: -3.0, enablePole: false, poleVal: 8 },
  { label: "附加远/近极点对比", zeta: 0.5, wn: 3.0, enableZero: false, zeroVal: 4, enablePole: true, poleVal: 2.5 },
];

const applyPreset = (p: Preset): void => {
  zeta.value = p.zeta;
  wn.value = p.wn;
  enableZero.value = p.enableZero;
  zeroVal.value = p.zeroVal;
  enablePole.value = p.enablePole;
  poleVal.value = p.poleVal;
};

// Base 2nd-order poles
const basePoles = computed(() => {
  const z = zeta.value;
  const w = wn.value;
  if (z < 1) {
    const re = -z * w;
    const im = w * Math.sqrt(1 - z * z);
    return [
      { re, im },
      { re, im: -im },
    ];
  }
  const disc = w * Math.sqrt(z * z - 1);
  return [
    { re: -z * w + disc, im: 0 },
    { re: -z * w - disc, im: 0 },
  ];
});

const regimeLabel = computed(() => {
  const z = zeta.value;
  if (z < 0.005) return "无阻尼 (Undamped)";
  if (z < 0.995) return "欠阻尼 (Underdamped)";
  if (z <= 1.005) return "临界阻尼 (Critically Damped)";
  return "过阻尼 (Overdamped)";
});

// Compute unit step response y(t) via RK4 on state-space realization
// Base 2nd-order: G2(s) = wn^2 / (s^2 + 2*zeta*wn*s + wn^2)
// With optional extra pole 1/(1 + s/p) and optional zero (1 + s/z)
const simData = computed(() => {
  const z = zeta.value;
  const w = wn.value;
  const useZ = enableZero.value && Math.abs(zeroVal.value) > 0.05;
  const zv = zeroVal.value;
  const useP = enablePole.value && poleVal.value > 0.1;
  const pv = poleVal.value;

  const sigma = Math.max(z * w, 0.35);
  const tEnd = Math.min(20, Math.max(4.5, 8.5 / sigma));
  const steps = 420;
  const dt = tEnd / steps;

  // States: x1 = y_base, x2 = dy_base/dt, x3 = y_filtered (if extra pole)
  // For step u = 1:
  // dx1 = x2
  // dx2 = w^2 * (1 - x1) - 2*z*w*x2
  // If useP: dx3 = pv * (x1 - x3), y0 = x3, dy0 = pv * (x1 - x3)
  // Else: y0 = x1, dy0 = x2
  // If useZ: y = y0 + dy0 / zv
  let x1 = 0;
  let x2 = 0;
  let x3 = 0;

  const ts: number[] = [];
  const ys: number[] = [];

  const deriv = (a1: number, a2: number, a3: number): [number, number, number] => {
    const d1 = a2;
    const d2 = w * w * (1 - a1) - 2 * z * w * a2;
    const d3 = useP ? pv * (a1 - a3) : 0;
    return [d1, d2, d3];
  };

  for (let i = 0; i <= steps; i++) {
    const t = i * dt;
    const y0 = useP ? x3 : x1;
    const dy0 = useP ? pv * (x1 - x3) : x2;
    const y = useZ ? y0 + dy0 / zv : y0;
    ts.push(t);
    ys.push(y);

    const [k11, k12, k13] = deriv(x1, x2, x3);
    const [k21, k22, k23] = deriv(x1 + 0.5 * dt * k11, x2 + 0.5 * dt * k12, x3 + 0.5 * dt * k13);
    const [k31, k32, k33] = deriv(x1 + 0.5 * dt * k21, x2 + 0.5 * dt * k22, x3 + 0.5 * dt * k23);
    const [k41, k42, k43] = deriv(x1 + dt * k31, x2 + dt * k32, x3 + dt * k33);
    x1 += (dt / 6) * (k11 + 2 * k21 + 2 * k31 + k41);
    x2 += (dt / 6) * (k12 + 2 * k22 + 2 * k32 + k42);
    x3 += (dt / 6) * (k13 + 2 * k23 + 2 * k33 + k43);
  }

  // Extract metrics numerically
  let yMax = -Infinity;
  let yMin = Infinity;
  let tp = 0;
  for (let i = 0; i < ys.length; i++) {
    if (ys[i] > yMax) {
      yMax = ys[i];
      tp = ts[i];
    }
    if (ys[i] < yMin) yMin = ys[i];
  }

  const mp = yMax > 1.0005 ? (yMax - 1) * 100 : 0;

  // Rise time: 0->100% if underdamped/overshoots, else 10%->90%
  let tr: number | null = null;
  if (yMax >= 1.0) {
    const idx = ys.findIndex((v) => v >= 1.0);
    if (idx > 0) tr = ts[idx];
  } else {
    const i10 = ys.findIndex((v) => v >= 0.1);
    const i90 = ys.findIndex((v) => v >= 0.9);
    if (i10 >= 0 && i90 > i10) tr = ts[i90] - ts[i10];
  }

  // Settling time (±2%)
  let tsVal: number | null = null;
  if (z > 0.005) {
    let lastOut = -1;
    for (let i = 0; i < ys.length; i++) {
      if (Math.abs(ys[i] - 1.0) > 0.02) lastOut = i;
    }
    if (lastOut < ys.length - 1) tsVal = ts[Math.max(0, lastOut + 1)];
  }

  return { ts, ys, tEnd, yMax, yMin, tp, mp, tr, tsVal };
});

// SVG coordinates for s-plane
const SP_W = 290;
const SP_H = 240;
const spBounds = computed(() => {
  const maxR = Math.max(
    6,
    wn.value * 1.4,
    enablePole.value ? poleVal.value * 1.15 : 0,
    enableZero.value ? Math.abs(zeroVal.value) * 1.15 : 0
  );
  return { xMin: -maxR, xMax: maxR * 0.45, yMax: maxR * 0.78 };
});

const spX = (re: number): number => {
  const { xMin, xMax } = spBounds.value;
  return 26 + ((re - xMin) / (xMax - xMin)) * (SP_W - 40);
};
const spY = (im: number): number => {
  const { yMax } = spBounds.value;
  return SP_H / 2 - (im / yMax) * (SP_H / 2 - 22);
};

// SVG coordinates for step response
const ST_W = 390;
const ST_H = 240;
const stBounds = computed(() => {
  const yHi = Math.max(1.5, Math.min(2.6, Math.ceil((simData.value.yMax + 0.15) * 4) / 4));
  const yLo = Math.min(-0.1, Math.max(-1.0, Math.floor((simData.value.yMin - 0.1) * 4) / 4));
  return { yLo, yHi };
});

const stX = (t: number): number => 40 + (t / simData.value.tEnd) * (ST_W - 56);
const stY = (y: number): number => {
  const { yLo, yHi } = stBounds.value;
  return ST_H - 30 - ((y - yLo) / (yHi - yLo)) * (ST_H - 46);
};

const stepPath = computed(() => {
  const { ts, ys } = simData.value;
  return ts
    .map((t, i) => `${i === 0 ? "M" : "L"}${stX(t).toFixed(1)},${stY(ys[i]).toFixed(1)}`)
    .join(" ");
});

const poleText = computed(() => {
  const [p1, p2] = basePoles.value;
  if (Math.abs(p1.im) > 1e-4) {
    return `${p1.re.toFixed(2)} ± j${Math.abs(p1.im).toFixed(2)}`;
  }
  return `${p1.re.toFixed(2)}, ${p2.re.toFixed(2)}`;
});
</script>

<template>
  <div class="ctrl-lab">
    <div class="ctrl-lab-head">
      <div>
        <span class="ctrl-lab-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ctrl-lab-title">二阶系统极零点与阶跃响应实验室</h4>
      </div>
      <span class="ctrl-lab-regime">{{ regimeLabel }}</span>
    </div>

    <div class="ctrl-presets">
      <button
        v-for="p in presets"
        :key="p.label"
        type="button"
        class="ctrl-chip"
        @click="applyPreset(p)"
      >
        {{ p.label }}
      </button>
    </div>

    <div class="ctrl-controls">
      <label class="ctrl-slider">
        <span class="ctrl-slider-row">
          <span>阻尼比 ζ</span>
          <strong>{{ zeta.toFixed(2) }}</strong>
        </span>
        <input v-model.number="zeta" type="range" min="0" max="2" step="0.01" />
      </label>

      <label class="ctrl-slider">
        <span class="ctrl-slider-row">
          <span>自然频率 ω<sub>n</sub> (rad/s)</span>
          <strong>{{ wn.toFixed(1) }}</strong>
        </span>
        <input v-model.number="wn" type="range" min="0.5" max="8" step="0.1" />
      </label>

      <div class="ctrl-toggle-group">
        <label class="ctrl-check">
          <input v-model="enableZero" type="checkbox" />
          <span>附加闭环零点 (1 + s/z)</span>
        </label>
        <div v-if="enableZero" class="ctrl-subslider">
          <span>z = {{ zeroVal.toFixed(1) }}（零点位于 {{ (-zeroVal).toFixed(1) }}）</span>
          <input v-model.number="zeroVal" type="range" min="-8" max="10" step="0.2" />
        </div>
      </div>

      <div class="ctrl-toggle-group">
        <label class="ctrl-check">
          <input v-model="enablePole" type="checkbox" />
          <span>附加闭环极点 1/(1 + s/p)</span>
        </label>
        <div v-if="enablePole" class="ctrl-subslider">
          <span>p = {{ poleVal.toFixed(1) }}（极点位于 -{{ poleVal.toFixed(1) }}）</span>
          <input v-model.number="poleVal" type="range" min="0.5" max="15" step="0.5" />
        </div>
      </div>
    </div>

    <div class="ctrl-charts">
      <!-- s-plane -->
      <div class="ctrl-panel">
        <div class="ctrl-panel-label">s 平面闭环极零点分布</div>
        <svg :viewBox="`0 0 ${SP_W} ${SP_H}`" class="ctrl-svg">
          <!-- LHP subtle tint -->
          <rect
            x="26"
            y="14"
            :width="Math.max(0, spX(0) - 26)"
            :height="SP_H - 28"
            class="svg-lhp"
          />
          <!-- Axes -->
          <line x1="20" :y1="spY(0)" :x2="SP_W - 10" :y2="spY(0)" class="svg-axis" />
          <line :x1="spX(0)" y1="12" :x2="spX(0)" :y2="SP_H - 12" class="svg-axis" />
          <text :x="SP_W - 14" :y="spY(0) - 6" class="svg-ax-lbl" text-anchor="end">σ</text>
          <text :x="spX(0) + 6" y="22" class="svg-ax-lbl">jω</text>

          <!-- Damping ray for underdamped -->
          <template v-if="zeta > 0 && zeta < 1">
            <line
              :x1="spX(0)"
              :y1="spY(0)"
              :x2="spX(basePoles[0].re)"
              :y2="spY(basePoles[0].im)"
              class="svg-ray"
            />
            <line
              :x1="spX(basePoles[0].re)"
              :y1="spY(0)"
              :x2="spX(basePoles[0].re)"
              :y2="spY(basePoles[0].im)"
              class="svg-guide"
            />
          </template>

          <!-- Base 2nd-order poles -->
          <g v-for="(p, idx) in basePoles" :key="'p' + idx" :transform="`translate(${spX(p.re)},${spY(p.im)})`">
            <line x1="-5" y1="-5" x2="5" y2="5" class="svg-pole" />
            <line x1="-5" y1="5" x2="5" y2="-5" class="svg-pole" />
          </g>

          <!-- Extra pole -->
          <g v-if="enablePole" :transform="`translate(${spX(-poleVal)},${spY(0)})`">
            <line x1="-5" y1="-5" x2="5" y2="5" class="svg-pole-extra" />
            <line x1="-5" y1="5" x2="5" y2="-5" class="svg-pole-extra" />
            <text y="-9" class="svg-tag-extra" text-anchor="middle">-p</text>
          </g>

          <!-- Extra zero -->
          <g v-if="enableZero && Math.abs(zeroVal) > 0.05" :transform="`translate(${spX(-zeroVal)},${spY(0)})`">
            <circle r="5.2" class="svg-zero" />
            <text y="-9" class="svg-tag-zero" text-anchor="middle">{{ zeroVal > 0 ? "-z" : "+|z|" }}</text>
          </g>
        </svg>
      </div>

      <!-- Step Response -->
      <div class="ctrl-panel">
        <div class="ctrl-panel-label">单位阶跃响应 y(t)（含 ±2% 误差带）</div>
        <svg :viewBox="`0 0 ${ST_W} ${ST_H}`" class="ctrl-svg">
          <!-- ±2% band -->
          <rect
            x="40"
            :y="stY(1.02)"
            :width="ST_W - 56"
            :height="Math.max(2, stY(0.98) - stY(1.02))"
            class="svg-band"
          />
          <!-- Unity line -->
          <line x1="40" :y1="stY(1)" :x2="ST_W - 16" :y2="stY(1)" class="svg-ref" />
          <!-- Axes -->
          <line x1="40" :y1="stY(0)" :x2="ST_W - 12" :y2="stY(0)" class="svg-axis" />
          <line x1="40" y1="14" x2="40" :y2="ST_H - 28" class="svg-axis" />

          <!-- Y ticks -->
          <text x="34" :y="stY(1) + 4" class="svg-tick" text-anchor="end">1.0</text>
          <text x="34" :y="stY(0) + 4" class="svg-tick" text-anchor="end">0</text>
          <text x="34" :y="stY(stBounds.yHi) + 8" class="svg-tick" text-anchor="end">{{ stBounds.yHi.toFixed(1) }}</text>
          <text :x="ST_W - 14" :y="ST_H - 10" class="svg-tick" text-anchor="end">t ({{ simData.tEnd.toFixed(1) }}s)</text>

          <!-- Settling marker -->
          <g v-if="simData.tsVal !== null">
            <line
              :x1="stX(simData.tsVal)"
              y1="16"
              :x2="stX(simData.tsVal)"
              :y2="ST_H - 28"
              class="svg-ts-line"
            />
            <text :x="Math.min(ST_W - 22, stX(simData.tsVal) + 4)" y="26" class="svg-ts-lbl">t_s</text>
          </g>

          <!-- Response Curve -->
          <path :d="stepPath" class="svg-curve" fill="none" />

          <!-- Peak marker -->
          <g v-if="simData.mp > 0.5">
            <circle :cx="stX(simData.tp)" :cy="stY(simData.yMax)" r="4" class="svg-peak" />
          </g>
        </svg>
      </div>
    </div>

    <div class="ctrl-metrics">
      <div class="ctrl-metric">
        <span>主导极点 s<sub>1,2</sub></span>
        <strong>{{ poleText }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>超调量 σ%</span>
        <strong>{{ simData.mp.toFixed(1) }}%</strong>
      </div>
      <div class="ctrl-metric">
        <span>上升时间 t<sub>r</sub></span>
        <strong>{{ simData.tr !== null ? simData.tr.toFixed(2) + " s" : "—" }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>峰值时间 t<sub>p</sub></span>
        <strong>{{ simData.mp > 0.5 ? simData.tp.toFixed(2) + " s" : "无峰值" }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>调节时间 t<sub>s</sub> (±2%)</span>
        <strong>{{ simData.tsVal !== null ? simData.tsVal.toFixed(2) + " s" : "不收敛" }}</strong>
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
  margin-bottom: 0.8rem;
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

.ctrl-lab-regime {
  padding: 0.2rem 0.6rem;
  border: 1px solid var(--vp-c-accent);
  border-radius: var(--r, 2px);
  background: var(--vp-c-accent-soft);
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.78rem;
  font-weight: 600;
}

.ctrl-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.9rem;
}

.ctrl-chip {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background-color 0.18s;

  &:hover {
    border-color: var(--vp-c-accent);
    color: var(--vp-c-accent);
  }
}

.ctrl-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1.2rem;
  margin-bottom: 0.95rem;
}

.ctrl-slider,
.ctrl-toggle-group {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}

.ctrl-slider-row {
  display: flex;
  justify-content: space-between;
  color: var(--vp-c-text);
  font-size: 0.85rem;

  strong {
    color: var(--vp-c-accent);
    font-family: var(--vp-font-mono);
    font-variant-numeric: tabular-nums;
  }
}

.ctrl-check {
  display: inline-flex;
  gap: 0.45rem;
  align-items: center;
  color: var(--vp-c-text);
  font-size: 0.84rem;
  cursor: pointer;
}

.ctrl-subslider {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-left: 0.2rem;
  color: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 0.76rem;
}

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;
}

.ctrl-charts {
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}

.ctrl-panel {
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.ctrl-panel-label {
  margin-bottom: 0.35rem;
  color: var(--vp-c-text-mute);
  font-size: 0.78rem;
  font-weight: 600;
}

.ctrl-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-lhp {
  fill: var(--vp-c-accent-soft);
  opacity: 0.4;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.1;
}

.svg-ax-lbl,
.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 10px;
}

.svg-ray {
  stroke: var(--vp-c-accent);
  stroke-width: 1.3;
  stroke-dasharray: 4 3;
}

.svg-guide {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}

.svg-pole {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
  stroke-linecap: round;
}

.svg-pole-extra {
  stroke: #c27803;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.svg-zero {
  fill: var(--vp-c-bg);
  stroke: #c83e37;
  stroke-width: 2.2;
}

.svg-tag-extra {
  fill: #c27803;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 600;
}

.svg-tag-zero {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 600;
}

.svg-band {
  fill: #1e7a56;
  opacity: 0.14;
}

.svg-ref {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  stroke-dasharray: 4 3;
}

.svg-ts-line {
  stroke: #1e7a56;
  stroke-width: 1.2;
  stroke-dasharray: 3 3;
}

.svg-ts-lbl {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 600;
}

.svg-curve {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
  stroke-linejoin: round;
}

.svg-peak {
  fill: #c83e37;
}

.ctrl-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
  .ctrl-charts {
    grid-template-columns: 1fr;
  }

  .ctrl-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
