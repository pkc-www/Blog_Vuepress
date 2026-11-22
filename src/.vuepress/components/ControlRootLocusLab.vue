<script setup lang="ts">
import { computed, ref } from "vue";

interface Complex {
  re: number;
  im: number;
}

interface RLSystem {
  id: string;
  label: string;
  formula: string;
  note: string;
  poles: number[]; // real open-loop poles
  zeros: number[]; // real open-loop zeros
  kMin: number;
  kMax: number;
  kDefault: number;
  xRange: [number, number];
  yMax: number;
}

const systems: RLSystem[] = [
  {
    id: "2nd",
    label: "二阶基础",
    formula: "G₀(s) = K' / [s(s + 2)]",
    note: "分离点 s = −1，两条 90° 渐近线，全增益稳定。",
    poles: [0, -2],
    zeros: [],
    kMin: 0.05,
    kMax: 30,
    kDefault: 2.5,
    xRange: [-6, 2],
    yMax: 4.5,
  },
  {
    id: "add-pole",
    label: "附加极点 (右移失稳)",
    formula: "G₀(s) = K' / [s(s + 2)(s + 5)]",
    note: "增加极点 s = −5 后根轨迹向右弯曲，K' = 70 时穿虚轴 s = ±j√10，K' > 70 不稳定。",
    poles: [0, -2, -5],
    zeros: [],
    kMin: 0.2,
    kMax: 120,
    kDefault: 15,
    xRange: [-7.5, 2.5],
    yMax: 5.0,
  },
  {
    id: "add-zero",
    label: "附加 LHP 零点 (圆弧左弯)",
    formula: "G₀(s) = K'(s + 4) / [s(s + 2)]",
    note: "在 −4 处附加开环零点，根轨迹形成圆弧向 LHP 弯曲，显著改善阻尼并消除失稳风险。",
    poles: [0, -2],
    zeros: [-4],
    kMin: 0.1,
    kMax: 40,
    kDefault: 4.0,
    xRange: [-8.5, 1.5],
    yMax: 4.5,
  },
  {
    id: "lead-pair",
    label: "超前零极点对",
    formula: "G₀(s) = K'(s + 2.5) / [s(s + 2)(s + 6)]",
    note: "|z_c| < |p_c|，不改变渐近线条数 (n−m = 2)，但将渐近线重心左移，大幅提升稳定裕度。",
    poles: [0, -2, -6],
    zeros: [-2.5],
    kMin: 0.2,
    kMax: 60,
    kDefault: 10,
    xRange: [-8, 2],
    yMax: 5.0,
  },
  {
    id: "lag-dipole",
    label: "近原点滞后偶极子",
    formula: "G₀(s) = K'(s + 0.25) / [s(s + 2)(s + 5)(s + 0.05)]",
    note: "偶极子 (−0.05, −0.25) 紧贴原点，主导根轨迹几乎不变，而速度误差系数 K_v 提升 5 倍！",
    poles: [0, -2, -5, -0.05],
    zeros: [-0.25],
    kMin: 0.2,
    kMax: 100,
    kDefault: 15,
    xRange: [-7.5, 2.5],
    yMax: 5.0,
  },
];

const selectedId = ref("add-pole");
const currentSys = computed(() => systems.find((s) => s.id === selectedId.value) ?? systems[0]);

// Store log10(K') for smooth logarithmic slider
const logK = ref(Math.log10(15));
const selectSystem = (sys: RLSystem): void => {
  selectedId.value = sys.id;
  logK.value = Math.log10(sys.kDefault);
};

const kVal = computed(() => Math.pow(10, logK.value));

// Polynomial helpers: descending powers [a_n, ..., a_0]
const polyFromRoots = (roots: number[]): number[] => {
  let p = [1];
  for (const r of roots) {
    const next = new Array(p.length + 1).fill(0);
    for (let i = 0; i < p.length; i++) {
      next[i] += p[i];
      next[i + 1] -= p[i] * r;
    }
    p = next;
  }
  return p;
};

const addPoly = (d: number[], n: number[], k: number): number[] => {
  const len = Math.max(d.length, n.length);
  const res = new Array(len).fill(0);
  for (let i = 0; i < d.length; i++) res[len - d.length + i] += d[i];
  for (let i = 0; i < n.length; i++) res[len - n.length + i] += k * n[i];
  return res;
};

const cAdd = (a: Complex, b: Complex): Complex => ({ re: a.re + b.re, im: a.im + b.im });
const cSub = (a: Complex, b: Complex): Complex => ({ re: a.re - b.re, im: a.im - b.im });
const cMul = (a: Complex, b: Complex): Complex => ({
  re: a.re * b.re - a.im * b.im,
  im: a.re * b.im + a.im * b.re,
});
const cDiv = (a: Complex, b: Complex): Complex => {
  const den = b.re * b.re + b.im * b.im || 1e-18;
  return { re: (a.re * b.re + a.im * b.im) / den, im: (a.im * b.re - a.re * b.im) / den };
};

const evalPoly = (coeffs: number[], z: Complex): Complex => {
  let acc: Complex = { re: coeffs[0], im: 0 };
  for (let i = 1; i < coeffs.length; i++) {
    acc = cMul(acc, z);
    acc.re += coeffs[i];
  }
  return acc;
};

// Durand-Kerner complex root finder
const solveRoots = (rawCoeffs: number[], warmStart?: Complex[]): Complex[] => {
  const lead = rawCoeffs[0];
  const coeffs = rawCoeffs.map((c) => c / lead);
  const deg = coeffs.length - 1;
  if (deg <= 0) return [];
  if (deg === 1) return [{ re: -coeffs[1], im: 0 }];

  const roots: Complex[] = warmStart && warmStart.length === deg
    ? warmStart.map((r, i) => ({ re: r.re + (i + 1) * 1e-4, im: r.im + ((i % 2 ? 1 : -1) * 1e-4) }))
    : Array.from({ length: deg }, (_, k) => {
        const ang = (2 * Math.PI * k) / deg + 0.37;
        const rad = 1.4 + 0.25 * k;
        return { re: rad * Math.cos(ang), im: rad * Math.sin(ang) };
      });

  for (let iter = 0; iter < 90; iter++) {
    let maxStep = 0;
    for (let i = 0; i < deg; i++) {
      let denom: Complex = { re: 1, im: 0 };
      for (let j = 0; j < deg; j++) {
        if (i !== j) denom = cMul(denom, cSub(roots[i], roots[j]));
      }
      const delta = cDiv(evalPoly(coeffs, roots[i]), denom);
      roots[i] = cSub(roots[i], delta);
      const step = Math.hypot(delta.re, delta.im);
      if (step > maxStep) maxStep = step;
    }
    if (maxStep < 1e-9) break;
  }

  return roots.map((r) => ({ re: r.re, im: Math.abs(r.im) < 1e-6 ? 0 : r.im }));
};

// Greedy nearest-neighbor matching so branches stay continuous
const matchRoots = (prev: Complex[], next: Complex[]): Complex[] => {
  const used = new Array(next.length).fill(false);
  const ordered: Complex[] = new Array(prev.length);
  for (let i = 0; i < prev.length; i++) {
    let bestJ = -1;
    let bestD = Infinity;
    for (let j = 0; j < next.length; j++) {
      if (used[j]) continue;
      const d = Math.hypot(prev[i].re - next[j].re, prev[i].im - next[j].im);
      if (d < bestD) {
        bestD = d;
        bestJ = j;
      }
    }
    used[bestJ] = true;
    ordered[i] = next[bestJ];
  }
  return ordered;
};

const W = 540;
const H = 310;
const padL = 36;
const padR = 20;
const padT = 18;
const padB = 28;

const mapX = (re: number): number => {
  const [xMin, xMax] = currentSys.value.xRange;
  return padL + ((re - xMin) / (xMax - xMin)) * (W - padL - padR);
};
const mapY = (im: number): number => {
  const yMax = currentSys.value.yMax;
  return padT + ((yMax - im) / (2 * yMax)) * (H - padT - padB);
};

// Precompute root locus branches & asymptotes
const locusData = computed(() => {
  const sys = currentSys.value;
  const D = polyFromRoots(sys.poles);
  const N = polyFromRoots(sys.zeros);
  const n = sys.poles.length;
  const m = sys.zeros.length;

  // Sweep K' from 0 to kMax*2.5
  const kGrid: number[] = [0];
  const steps = 110;
  const logLo = Math.log10(Math.max(1e-3, sys.kMin * 0.05));
  const logHi = Math.log10(sys.kMax * 2.5);
  for (let i = 0; i <= steps; i++) {
    kGrid.push(Math.pow(10, logLo + ((logHi - logLo) * i) / steps));
  }

  const branches: Complex[][] = Array.from({ length: n }, () => []);
  let prev: Complex[] = sys.poles.map((p) => ({ re: p, im: 0 }));
  for (let i = 0; i < n; i++) branches[i].push(prev[i]);

  for (let idx = 1; idx < kGrid.length; idx++) {
    const poly = addPoly(D, N, kGrid[idx]);
    const raw = solveRoots(poly, prev);
    const matched = matchRoots(prev, raw);
    for (let b = 0; b < n; b++) branches[b].push(matched[b]);
    prev = matched;
  }

  // Asymptotes
  const asymLines: { x1: number; y1: number; x2: number; y2: number }[] = [];
  let sigmaA: number | null = null;
  if (n > m) {
    const sumP = sys.poles.reduce((a, b) => a + b, 0);
    const sumZ = sys.zeros.reduce((a, b) => a + b, 0);
    sigmaA = (sumP - sumZ) / (n - m);
    const len = 18;
    for (let k = 0; k < n - m; k++) {
      const ang = ((2 * k + 1) * Math.PI) / (n - m);
      asymLines.push({
        x1: sigmaA,
        y1: 0,
        x2: sigmaA + len * Math.cos(ang),
        y2: len * Math.sin(ang),
      });
    }
  }

  const branchPaths = branches.map((pts) =>
    pts
      .map((p, i) => `${i === 0 ? "M" : "L"}${mapX(p.re).toFixed(1)},${mapY(p.im).toFixed(1)}`)
      .join(" ")
  );

  return { D, N, branchPaths, asymLines, sigmaA };
});

// Active closed-loop poles at current K'
const activePoles = computed(() => {
  const { D, N } = locusData.value;
  const roots = solveRoots(addPoly(D, N, kVal.value));
  return roots.sort((a, b) => b.re - a.re || b.im - a.im);
});

const stabilityStatus = computed(() => {
  const maxRe = Math.max(...activePoles.value.map((p) => p.re));
  if (maxRe > 0.015) return { text: "不稳定 (RHP 存在闭环极点)", cls: "is-bad" };
  if (maxRe > -0.015) return { text: "临界稳定 (虚轴极点)", cls: "is-warn" };
  return { text: "闭环渐近稳定 (全部极点位于 LHP)", cls: "is-ok" };
});

const dominantZeta = computed(() => {
  const complexPole = activePoles.value.find((p) => p.im > 1e-3);
  if (!complexPole) return "过阻尼 (实极点)";
  const wn = Math.hypot(complexPole.re, complexPole.im);
  const z = -complexPole.re / wn;
  return z.toFixed(3);
});

const formatPole = (p: Complex): string => {
  if (Math.abs(p.im) < 1e-3) return p.re.toFixed(2);
  return `${p.re.toFixed(2)} ${p.im >= 0 ? "+" : "−"} j${Math.abs(p.im).toFixed(2)}`;
};
</script>

<template>
  <div class="ctrl-lab">
    <div class="ctrl-lab-head">
      <div>
        <span class="ctrl-lab-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ctrl-lab-title">根轨迹实时求解与零极点效应实验室</h4>
      </div>
      <span class="ctrl-status" :class="stabilityStatus.cls">{{ stabilityStatus.text }}</span>
    </div>

    <div class="ctrl-presets">
      <button
        v-for="s in systems"
        :key="s.id"
        type="button"
        class="ctrl-chip"
        :class="{ 'is-active': s.id === currentSys.id }"
        @click="selectSystem(s)"
      >
        {{ s.label }}
      </button>
    </div>

    <div class="rl-info">
      <code class="rl-formula">{{ currentSys.formula }}</code>
      <span class="rl-note">{{ currentSys.note }}</span>
    </div>

    <label class="ctrl-slider rl-slider">
      <span class="ctrl-slider-row">
        <span>开环根轨迹增益 K'（对数调节）</span>
        <strong>K' = {{ kVal.toFixed(2) }}</strong>
      </span>
      <input
        v-model.number="logK"
        type="range"
        :min="Math.log10(currentSys.kMin)"
        :max="Math.log10(currentSys.kMax)"
        step="0.01"
      />
    </label>

    <div class="ctrl-panel rl-panel">
      <svg :viewBox="`0 0 ${W} ${H}`" class="ctrl-svg">
        <defs>
          <clipPath id="rl-clip">
            <rect :x="padL" :y="padT" :width="W - padL - padR" :height="H - padT - padB" />
          </clipPath>
        </defs>

        <!-- RHP warning tint -->
        <rect
          :x="mapX(0)"
          :y="padT"
          :width="Math.max(0, W - padR - mapX(0))"
          :height="H - padT - padB"
          class="svg-rhp"
        />

        <!-- Axes -->
        <line :x1="padL" :y1="mapY(0)" :x2="W - padR" :y2="mapY(0)" class="svg-axis" />
        <line :x1="mapX(0)" :y1="padT" :x2="mapX(0)" :y2="H - padB" class="svg-axis" />
        <text :x="W - padR - 4" :y="mapY(0) - 6" class="svg-ax-lbl" text-anchor="end">σ (Re)</text>
        <text :x="mapX(0) + 6" :y="padT + 12" class="svg-ax-lbl">jω (Im)</text>
        <text :x="mapX(0) + 6" :y="H - padB - 6" class="svg-rhp-lbl">不稳定区 (RHP)</text>

        <!-- Asymptotes & Branches (clipped) -->
        <g clip-path="url(#rl-clip)">
          <line
            v-for="(a, idx) in locusData.asymLines"
            :key="'a' + idx"
            :x1="mapX(a.x1)"
            :y1="mapY(a.y1)"
            :x2="mapX(a.x2)"
            :y2="mapY(a.y2)"
            class="svg-asym"
          />
          <path
            v-for="(d, idx) in locusData.branchPaths"
            :key="'b' + idx"
            :d="d"
            fill="none"
            class="svg-branch"
          />

          <!-- Open-loop poles -->
          <g v-for="(p, idx) in currentSys.poles" :key="'op' + idx" :transform="`translate(${mapX(p)},${mapY(0)})`">
            <line x1="-5" y1="-5" x2="5" y2="5" class="svg-ol-pole" />
            <line x1="-5" y1="5" x2="5" y2="-5" class="svg-ol-pole" />
          </g>

          <!-- Open-loop zeros -->
          <circle
            v-for="(z, idx) in currentSys.zeros"
            :key="'oz' + idx"
            :cx="mapX(z)"
            :cy="mapY(0)"
            r="5.2"
            class="svg-ol-zero"
          />

          <!-- Active closed-loop poles -->
          <circle
            v-for="(p, idx) in activePoles"
            :key="'cl' + idx"
            :cx="mapX(p.re)"
            :cy="mapY(p.im)"
            r="5.5"
            class="svg-cl-pole"
            :class="{ 'is-unstable': p.re > 0.01 }"
          />
        </g>

        <!-- Border -->
        <rect :x="padL" :y="padT" :width="W - padL - padR" :height="H - padT - padB" fill="none" class="svg-frame" />
      </svg>
    </div>

    <div class="rl-footer">
      <div class="ctrl-metric">
        <span>当前闭环极点</span>
        <strong>{{ activePoles.map(formatPole).join(" ， ") }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>主导极点阻尼比 ζ</span>
        <strong>{{ dominantZeta }}</strong>
      </div>
      <div class="ctrl-metric">
        <span>渐近线重心 σ<sub>a</sub></span>
        <strong>{{ locusData.sigmaA !== null ? locusData.sigmaA.toFixed(2) : "无" }}</strong>
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

  &.is-warn {
    border: 1px solid #c27803;
    background: rgb(194 120 3 / 12%);
    color: #c27803;
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
  margin-bottom: 0.75rem;
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

.rl-info {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.9rem;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.rl-formula {
  padding: 0.18rem 0.48rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--ink);
  font-family: var(--vp-font-mono);
  font-size: 0.84rem;
}

.rl-note {
  color: var(--vp-c-text-mute);
  font-size: 0.82rem;
}

.rl-slider {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.85rem;
}

.ctrl-slider-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;

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

.ctrl-panel {
  margin-bottom: 0.8rem;
  padding: 0.65rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.ctrl-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-rhp {
  fill: #c83e37;
  opacity: 0.06;
}

.svg-rhp-lbl {
  fill: #c83e37;
  font-size: 10px;
  opacity: 0.75;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.1;
}

.svg-frame {
  stroke: var(--vp-c-border);
  stroke-width: 1;
}

.svg-ax-lbl {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 10.5px;
}

.svg-asym {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  stroke-dasharray: 4 4;
  opacity: 0.65;
}

.svg-branch {
  stroke: var(--vp-c-accent);
  stroke-width: 2.1;
  opacity: 0.82;
}

.svg-ol-pole {
  stroke: var(--ink);
  stroke-width: 2.1;
  stroke-linecap: round;
}

.svg-ol-zero {
  fill: var(--vp-c-bg);
  stroke: #1e7a56;
  stroke-width: 2.2;
}

.svg-cl-pole {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;

  &.is-unstable {
    fill: #c83e37;
  }
}

.rl-footer {
  display: grid;
  grid-template-columns: 2fr 1fr 0.8fr;
  gap: 0.5rem;
}

.ctrl-metric {
  padding: 0.45rem 0.65rem;
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
    font-size: 0.82rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .rl-footer {
    grid-template-columns: 1fr;
  }
}
</style>
