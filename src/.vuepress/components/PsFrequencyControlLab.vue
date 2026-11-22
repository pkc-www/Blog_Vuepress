<script setup lang="ts">
import { computed, ref } from "vue";

const SB = 1000; // MW
const fN = 50; // Hz
const Tg = 0.5; // s

const dPdMw = ref(100); // MW step at t = 5s
const inertiaH = ref(5.0); // s
const kgPu = ref(20); // K_G* (pu) -> K_G = kgPu * SB / fN = 400 MW/Hz at 20
const kdPu = ref(1.0); // D = K_D* (pu) -> K_D = 20 MW/Hz at 1.0
const enableAgc = ref(true);
const kiAgc = ref(2.0);

const applyPreset = (dp: number, h: number, kg: number, kd: number, agc: boolean): void => {
  dPdMw.value = dp;
  inertiaH.value = h;
  kgPu.value = kg;
  kdPu.value = kd;
  enableAgc.value = agc;
};

const runOde = (H: number, dpPu: number, kg: number, kd: number, agc: boolean, ki: number) => {
  const tEnd = 60;
  const steps = 600;
  const dt = tEnd / steps;
  let x = 0; // df / fN
  let pm = 0;
  let ps = 0;
  const ts: number[] = [];
  const fs: number[] = [];
  let fExtremum = fN;

  const deriv = (t: number, ax: number, apm: number, aps: number): [number, number, number] => {
    const pd = t >= 5 ? dpPu : 0;
    const dx = (apm - pd - kd * ax) / (2 * H);
    const dpm = (-apm - kg * ax + aps) / Tg;
    const dps = agc && t >= 25 ? -ki * ax : 0;
    return [dx, dpm, dps];
  };

  for (let i = 0; i <= steps; i++) {
    const t = i * dt;
    const f = fN * (1 + x);
    ts.push(t);
    fs.push(f);
    if (dpPu >= 0 ? f < fExtremum : f > fExtremum) fExtremum = f;

    const [k11, k12, k13] = deriv(t, x, pm, ps);
    const [k21, k22, k23] = deriv(t + 0.5 * dt, x + 0.5 * dt * k11, pm + 0.5 * dt * k12, ps + 0.5 * dt * k13);
    const [k31, k32, k33] = deriv(t + 0.5 * dt, x + 0.5 * dt * k21, pm + 0.5 * dt * k22, ps + 0.5 * dt * k23);
    const [k41, k42, k43] = deriv(t + dt, x + dt * k31, pm + dt * k32, ps + dt * k33);
    x += (dt / 6) * (k11 + 2 * k21 + 2 * k31 + k41);
    pm += (dt / 6) * (k12 + 2 * k22 + 2 * k32 + k42);
    ps += (dt / 6) * (k13 + 2 * k23 + 2 * k33 + k43);
  }
  return { ts, fs, fExtremum, fFinal: fs[fs.length - 1] };
};

const sim = computed(() => {
  const dpPu = dPdMw.value / SB;
  const KG = (kgPu.value * SB) / fN; // MW/Hz
  const KD = (kdPu.value * SB) / fN; // MW/Hz
  const df1 = -dPdMw.value / (KG + KD);
  const f1 = fN + df1;
  const dPG1 = -KG * df1;
  const dPDfSelf = KD * df1;
  const rocof = (-fN * dpPu) / (2 * inertiaH.value);

  const main = runOde(inertiaH.value, dpPu, kgPu.value, kdPu.value, enableAgc.value, kiAgc.value);
  const noAgc = runOde(inertiaH.value, dpPu, kgPu.value, kdPu.value, false, 0);

  return { KG, KD, df1, f1, dPG1, dPDfSelf, rocof, main, noAgc };
});

// Left panel: Static f-P droop diagram (P in [800, 1250] MW, f in [49.4, 50.6] Hz)
const SW = 290;
const SH = 215;
const sx = (p: number): number => 42 + ((p - 820) / 420) * (SW - 56);
const sy = (f: number): number => 16 + ((50.55 - f) / 1.1) * (SH - 42);

// Generator line: f(P) = 50 - (P - 1000 - dPgs) / KG
// Load line: f(P) = 50 + (P - 1000 - dPd) / KD  (steeper positive slope)
const genLine = (shiftMw: number): string => {
  const fLo = 49.48;
  const fHi = 50.52;
  const pAtLo = 1000 + shiftMw - sim.value.KG * (fLo - 50);
  const pAtHi = 1000 + shiftMw - sim.value.KG * (fHi - 50);
  return `M${sx(pAtHi).toFixed(1)},${sy(fHi).toFixed(1)} L${sx(pAtLo).toFixed(1)},${sy(fLo).toFixed(1)}`;
};
const loadLine = (dpMw: number): string => {
  const fLo = 49.48;
  const fHi = 50.52;
  const pAtLo = 1000 + dpMw + sim.value.KD * (fLo - 50);
  const pAtHi = 1000 + dpMw + sim.value.KD * (fHi - 50);
  return `M${sx(pAtLo).toFixed(1)},${sy(fLo).toFixed(1)} L${sx(pAtHi).toFixed(1)},${sy(fHi).toFixed(1)}`;
};

// Right panel: Dynamic f(t)
const DW = 365;
const DH = 215;
const fBounds = computed(() => {
  const all = [...sim.value.main.fs, ...sim.value.noAgc.fs];
  const lo = Math.min(49.55, Math.min(...all) - 0.08);
  const hi = Math.max(50.35, Math.max(...all) + 0.08);
  return { lo, hi };
});
const dx = (t: number): number => 44 + (t / 60) * (DW - 56);
const dy = (f: number): number => 16 + ((fBounds.value.hi - f) / (fBounds.value.hi - fBounds.value.lo)) * (DH - 42);

const pathFrom = (ts: number[], fs: number[]): string =>
  ts
    .filter((_, i) => i % 2 === 0)
    .map((t, j) => `${j === 0 ? "M" : "L"}${dx(t).toFixed(1)},${dy(fs[j * 2]).toFixed(1)}`)
    .join(" ");

const mainPath = computed(() => pathFrom(sim.value.main.ts, sim.value.main.fs));
const noAgcPath = computed(() => pathFrom(sim.value.noAgc.ts, sim.value.noAgc.fs));
</script>

<template>
  <div class="ps-lab">
    <div class="ps-head">
      <div>
        <span class="ps-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ps-title">一次 / 二次调频静态交点与惯量动态响应实验室（S<sub>B</sub>=1000 MW, f<sub>N</sub>=50 Hz）</h4>
      </div>
      <span class="ps-status" :class="enableAgc ? 'is-ok' : 'is-warn'">
        {{ enableAgc ? "一次 + 二次 AGC（无差恢复 50 Hz）" : `仅一次调频（稳态 ${sim.f1.toFixed(3)} Hz）` }}
      </span>
    </div>

    <div class="ps-presets">
      <button type="button" class="ps-chip" @click="applyPreset(100, 5.0, 20, 1.0, true)">课件基准 (H=5s, +100 MW)</button>
      <button type="button" class="ps-chip" @click="applyPreset(100, 2.0, 20, 1.0, true)">低惯量新能源电网 (H=2s!)</button>
      <button type="button" class="ps-chip" @click="applyPreset(100, 5.0, 20, 1.0, false)">关闭二次调频 (有差平衡)</button>
      <button type="button" class="ps-chip" @click="applyPreset(100, 5.0, 35, 1.0, false)">水轮机强下垂 (K_G*=35)</button>
      <button type="button" class="ps-chip" @click="applyPreset(-100, 5.0, 20, 1.0, true)">切负荷甩载 (−100 MW)</button>
    </div>

    <div class="ps-controls">
      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>外部负荷阶跃 ΔP<sub>D0</sub>（t=5s 投入）</span>
          <strong>{{ dPdMw >= 0 ? "+" : "" }}{{ dPdMw }} MW</strong>
        </span>
        <input v-model.number="dPdMw" type="range" min="-150" max="180" step="10" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>系统惯性时间常数 H（不改变稳态频差！）</span>
          <strong>H = {{ inertiaH.toFixed(1) }} s</strong>
        </span>
        <input v-model.number="inertiaH" type="range" min="1.5" max="10.0" step="0.5" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>机组标幺调频系数 K<sub>G*</sub>（下垂率 R<sub>*</sub>={{ (100 / kgPu).toFixed(1) }}%）</span>
          <strong>K<sub>G*</sub> = {{ kgPu }} ({{ sim.KG.toFixed(0) }} MW/Hz)</strong>
        </span>
        <input v-model.number="kgPu" type="range" min="8" max="40" step="1" />
      </label>

      <div class="ps-agc-box">
        <label class="ps-check">
          <input v-model="enableAgc" type="checkbox" />
          <span>t = 25 s 启用二次调频 AGC 积分控制 (K<sub>i</sub> = {{ kiAgc.toFixed(1) }})</span>
        </label>
        <input v-model.number="kiAgc" type="range" min="0.5" max="5.0" step="0.5" :disabled="!enableAgc" />
      </div>
    </div>

    <div class="ps-grid">
      <!-- Static f-P intersection -->
      <div class="ps-panel">
        <div class="ps-panel-label">静态 f–P 平衡交点（蓝：一次 / 绿：二次平移）</div>
        <svg :viewBox="`0 0 ${SW} ${SH}`" class="ps-svg">
          <defs>
            <clipPath id="ps-freq-static-clip">
              <rect x="42" y="16" :width="SW - 56" :height="SH - 42" />
            </clipPath>
          </defs>
          <line x1="42" :y1="sy(50)" :x2="SW - 14" :y2="sy(50)" class="svg-ref" />
          <line x1="42" y1="16" x2="42" :y2="SH - 26" class="svg-axis" />
          <line x1="42" :y1="SH - 26" :x2="SW - 14" :y2="SH - 26" class="svg-axis" />

          <g clip-path="url(#ps-freq-static-clip)">
            <path :d="loadLine(0)" fill="none" class="svg-load-old" />
            <path :d="loadLine(dPdMw)" fill="none" class="svg-load-new" />
            <path :d="genLine(0)" fill="none" class="svg-gen-1" />
            <path v-if="enableAgc" :d="genLine(dPdMw)" fill="none" class="svg-gen-2" />
            <!-- Original eq -->
            <circle :cx="sx(1000)" :cy="sy(50)" r="3.5" class="svg-dot-0" />
            <!-- Primary eq -->
            <circle :cx="sx(1000 + sim.dPG1)" :cy="sy(sim.f1)" r="4.8" class="svg-dot-1" />
            <!-- Secondary eq -->
            <circle v-if="enableAgc" :cx="sx(1000 + dPdMw)" :cy="sy(50)" r="4.8" class="svg-dot-2" />
          </g>

          <text x="36" :y="sy(50.4) + 3" class="svg-tick" text-anchor="end">50.4</text>
          <text x="36" :y="sy(50.0) + 3" class="svg-tick" text-anchor="end">50.0</text>
          <text x="36" :y="sy(49.6) + 3" class="svg-tick" text-anchor="end">49.6</text>
          <text :x="sx(1000)" :y="SH - 9" class="svg-tick" text-anchor="middle">1000 MW</text>
          <text :x="SW - 14" :y="SH - 9" class="svg-tick" text-anchor="end">P</text>
        </svg>
      </div>

      <!-- Dynamic f(t) -->
      <div class="ps-panel">
        <div class="ps-panel-label">频率动态响应 f(t)（实线当前 / 虚线仅一次调频）</div>
        <svg :viewBox="`0 0 ${DW} ${DH}`" class="ps-svg">
          <line x1="44" :y1="dy(50)" :x2="DW - 12" :y2="dy(50)" class="svg-ref" />
          <line :x1="dx(5)" y1="16" :x2="dx(5)" :y2="DH - 26" class="svg-evt" />
          <line v-if="enableAgc" :x1="dx(25)" y1="16" :x2="dx(25)" :y2="DH - 26" class="svg-evt-agc" />
          <line x1="44" y1="16" x2="44" :y2="DH - 26" class="svg-axis" />
          <line x1="44" :y1="DH - 26" :x2="DW - 12" :y2="DH - 26" class="svg-axis" />

          <path v-if="enableAgc" :d="noAgcPath" fill="none" class="svg-noagc" />
          <path :d="mainPath" fill="none" class="svg-freq" />

          <text x="38" :y="dy(50) + 3" class="svg-tick" text-anchor="end">50.0</text>
          <text x="38" :y="dy(fBounds.lo + 0.05) + 3" class="svg-tick" text-anchor="end">{{ (fBounds.lo + 0.05).toFixed(2) }}</text>
          <text :x="dx(5)" y="26" class="svg-tick" text-anchor="start"> +ΔP</text>
          <text v-if="enableAgc" :x="dx(25)" y="26" class="svg-lbl-agc" text-anchor="start"> AGC</text>
          <text v-for="t in [0, 20, 40, 60]" :key="'t' + t" :x="dx(t)" :y="DH - 9" class="svg-tick" text-anchor="middle">{{ t }}s</text>
        </svg>
      </div>
    </div>

    <div class="ps-metrics">
      <div class="ps-metric">
        <span>初始变化率 RoCoF ḟ(5⁺)</span>
        <strong>{{ sim.rocof >= 0 ? "+" : "" }}{{ sim.rocof.toFixed(2) }} Hz/s</strong>
      </div>
      <div class="ps-metric">
        <span>动态极值频率 (Nadir)</span>
        <strong>{{ sim.main.fExtremum.toFixed(3) }} Hz</strong>
      </div>
      <div class="ps-metric">
        <span>一次调频稳态 f<sub>1</sub> (Δf<sub>1</sub>)</span>
        <strong>{{ sim.f1.toFixed(3) }} Hz ({{ sim.df1 >= 0 ? "+" : "" }}{{ sim.df1.toFixed(3) }})</strong>
      </div>
      <div class="ps-metric">
        <span>一次分担：ΔP<sub>G</sub> / 负荷自调</span>
        <strong>{{ sim.dPG1.toFixed(1) }} / {{ sim.dPDfSelf.toFixed(1) }} MW</strong>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ps-lab {
  margin: 1.4rem 0;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  font-size: 0.9rem;
  line-height: 1.5;
}

.ps-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.ps-badge {
  display: inline-block;
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.ps-title {
  margin: 0.15rem 0 0 !important;
  color: var(--ink);
  font-size: 1.02rem;
  font-weight: 700;
}

.ps-status {
  padding: 0.2rem 0.62rem;
  border-radius: var(--r, 2px);
  font-family: var(--vp-font-mono);
  font-size: 0.76rem;
  font-weight: 600;

  &.is-ok {
    border: 1px solid #1e7a56;
    background: rgb(30 122 86 / 12%);
    color: #1e7a56;
  }

  &.is-warn {
    border: 1px solid #c27803;
    background: rgb(194 120 3 / 12%);
    color: #c27803;
  }
}

.ps-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-bottom: 0.75rem;
}

.ps-chip {
  padding: 0.24rem 0.58rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.79rem;
  cursor: pointer;

  &:hover {
    border-color: var(--vp-c-accent);
    color: var(--vp-c-accent);
  }
}

.ps-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.62rem 1.1rem;
  margin-bottom: 0.85rem;
}

.ps-slider,
.ps-agc-box {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
}

.ps-slider-row {
  display: flex;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.81rem;

  strong {
    color: var(--vp-c-accent);
    font-family: var(--vp-font-mono);
    font-variant-numeric: tabular-nums;
  }
}

.ps-check {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  font-size: 0.81rem;
  cursor: pointer;
}

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;

  &:disabled {
    opacity: 0.35;
  }
}

.ps-grid {
  display: grid;
  grid-template-columns: 0.92fr 1.18fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.ps-panel {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.ps-panel-label {
  margin-bottom: 0.28rem;
  color: var(--vp-c-text-mute);
  font-size: 0.75rem;
  font-weight: 600;
}

.ps-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-ref {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 4 3;
}

.svg-evt {
  stroke: #c83e37;
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-evt-agc {
  stroke: #1e7a56;
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-load-old {
  stroke: var(--vp-c-border);
  stroke-width: 1.4;
  stroke-dasharray: 3 3;
}

.svg-load-new {
  stroke: #c83e37;
  stroke-width: 1.9;
}

.svg-gen-1 {
  stroke: var(--vp-c-accent);
  stroke-width: 2;
}

.svg-gen-2 {
  stroke: #1e7a56;
  stroke-width: 2;
  stroke-dasharray: 5 3;
}

.svg-dot-0 {
  fill: var(--vp-c-text-mute);
}

.svg-dot-1 {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.5;
}

.svg-dot-2 {
  fill: #1e7a56;
  stroke: var(--vp-c-bg);
  stroke-width: 1.5;
}

.svg-noagc {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-freq {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-lbl-agc {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
}

.ps-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.48rem;
}

.ps-metric {
  padding: 0.42rem 0.56rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);

  span {
    display: block;
    color: var(--vp-c-text-mute);
    font-size: 0.7rem;
  }

  strong {
    display: block;
    margin-top: 0.14rem;
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .ps-controls,
  .ps-grid {
    grid-template-columns: 1fr;
  }

  .ps-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
