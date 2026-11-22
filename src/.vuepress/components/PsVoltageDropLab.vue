<script setup lang="ts">
import { computed, ref } from "vue";

const p2 = ref(0.8); // Receiving-end active power (pu)
const q2 = ref(0.5); // Receiving-end reactive power (pu), negative = capacitive
const xLine = ref(0.15); // Line reactance X (pu)
const rxRatio = ref(0.05); // R / X ratio
const u2 = 1.0; // Reference receiving-end voltage magnitude (pu)

const applyPreset = (p: number, q: number, x: number, rx: number): void => {
  p2.value = p;
  q2.value = q;
  xLine.value = x;
  rxRatio.value = rx;
};

const sim = computed(() => {
  const P = p2.value;
  const Q = q2.value;
  const X = xLine.value;
  const R = rxRatio.value * X;

  // Longitudinal & transverse voltage drop components referenced to U2_dot = U2 ∠ 0°
  const dU_Q = (Q * X) / u2;
  const dU_P = (P * R) / u2;
  const dU = dU_Q + dU_P;

  const deltaU_P = (P * X) / u2;
  const deltaU_Q = -(Q * R) / u2;
  const deltaU = deltaU_P + deltaU_Q;

  const u1Re = u2 + dU;
  const u1Im = deltaU;
  const u1Mag = Math.hypot(u1Re, u1Im);
  const delta1Rad = Math.atan2(u1Im, u1Re);
  const delta1Deg = (delta1Rad * 180) / Math.PI;

  const exactLoss = u1Mag - u2; // Voltage loss U1 - U2
  const approxErr = exactLoss - dU; // Difference between exact loss and longitudinal approx

  const s2Sq = P * P + Q * Q;
  const dPs = (s2Sq / (u2 * u2)) * R;
  const dQs = (s2Sq / (u2 * u2)) * X;
  const p1 = P + dPs;
  const q1 = Q + dQs;

  const isRise = u1Mag < u2 - 1e-4;
  const isDecoupled = rxRatio.value <= 0.15;

  // --- SVG 1: 1:1 Phasor Diagram (viewBox 0 0 360 220) ---
  const w1 = 360;
  const h1 = 220;
  const padL = 28;
  const padR = 26;
  const padT = 22;
  const padB = 26;

  const xMaxPu = Math.max(1.26, u1Re + 0.16, u2 + 0.2);
  const yPosPu = Math.max(0.42, u1Im + 0.16, 0.25);
  const yNegPu = Math.max(0.18, -u1Im + 0.14);

  const scaleX = (w1 - padL - padR) / (xMaxPu + 0.08);
  const scaleY = (h1 - padT - padB) / (yPosPu + yNegPu);
  const scale = Math.min(scaleX, scaleY);

  const ox = padL + 0.06 * scale;
  const oy = padT + yPosPu * scale;

  const sx = (re: number) => ox + re * scale;
  const sy = (im: number) => oy - im * scale;

  const u2X = sx(u2);
  const u2Y = sy(0);
  const dUX = sx(u1Re);
  const u1X = sx(u1Re);
  const u1Y = sy(u1Im);

  // Reference arc of radius U2 = 1.0 centered at O from -22° to +35°
  const arcPts: string[] = [];
  const aMin = Math.min(-0.32, delta1Rad - 0.14);
  const aMax = Math.max(0.55, delta1Rad + 0.14);
  for (let i = 0; i <= 40; i++) {
    const a = aMin + (i / 40) * (aMax - aMin);
    arcPts.push(`${i === 0 ? "M" : "L"}${sx(u2 * Math.cos(a)).toFixed(1)},${sy(u2 * Math.sin(a)).toFixed(1)}`);
  }

  // Angle arc for delta1 near origin (radius 0.34 pu)
  const rAng = 0.34;
  const angPts: string[] = [];
  if (Math.abs(delta1Rad) > 0.015) {
    for (let i = 0; i <= 20; i++) {
      const a = (i / 20) * delta1Rad;
      angPts.push(`${i === 0 ? "M" : "L"}${sx(rAng * Math.cos(a)).toFixed(1)},${sy(rAng * Math.sin(a)).toFixed(1)}`);
    }
  }
  const angLblX = sx((rAng + 0.12) * Math.cos(delta1Rad * 0.5));
  const angLblY = sy((rAng + 0.12) * Math.sin(delta1Rad * 0.5));

  // --- SVG 2: Coupling Breakdown Bar Chart (viewBox 0 0 340 220) ---
  const maxComp = Math.max(
    0.25,
    Math.abs(dU_Q),
    Math.abs(dU_P),
    Math.abs(dU),
    Math.abs(deltaU_P),
    Math.abs(deltaU_Q),
    Math.abs(deltaU),
  );
  const barCenter = 196;
  const barHalfW = 86;
  const mapBar = (v: number) => {
    const len = (Math.abs(v) / maxComp) * barHalfW;
    return {
      x: v >= 0 ? barCenter : barCenter - len,
      w: Math.max(1.5, len),
    };
  };

  const bars = [
    { label: "Q₂X / U₂", sub: "无功→纵分量", val: dU_Q, y: 34, cls: "bar-q", ...mapBar(dU_Q) },
    { label: "P₂R / U₂", sub: "有功→纵分量", val: dU_P, y: 60, cls: "bar-p", ...mapBar(dU_P) },
    { label: "合计 ΔU₂", sub: "纵分量总和", val: dU, y: 86, cls: "bar-sum", ...mapBar(dU) },
    { label: "P₂X / U₂", sub: "有功→横分量", val: deltaU_P, y: 132, cls: "bar-p", ...mapBar(deltaU_P) },
    { label: "−Q₂R / U₂", sub: "无功→横分量", val: deltaU_Q, y: 158, cls: "bar-q", ...mapBar(deltaU_Q) },
    { label: "合计 δU₂", sub: "横分量总和", val: deltaU, y: 184, cls: "bar-sum2", ...mapBar(deltaU) },
  ];

  // Coupling share percentages
  const dUDen = Math.abs(dU_Q) + Math.abs(dU_P);
  const qShareInDU = dUDen > 1e-6 ? (Math.abs(dU_Q) / dUDen) * 100 : 0;
  const deltaUDen = Math.abs(deltaU_P) + Math.abs(deltaU_Q);
  const pShareInDeltaU = deltaUDen > 1e-6 ? (Math.abs(deltaU_P) / deltaUDen) * 100 : 0;

  return {
    R,
    dU_Q,
    dU_P,
    dU,
    deltaU_P,
    deltaU_Q,
    deltaU,
    u1Mag,
    delta1Deg,
    exactLoss,
    approxErr,
    dPs,
    dQs,
    p1,
    q1,
    isRise,
    isDecoupled,
    ox,
    oy,
    u2X,
    u2Y,
    dUX,
    u1X,
    u1Y,
    refArcPath: arcPts.join(" "),
    angArcPath: angPts.join(" "),
    angLblX,
    angLblY,
    barCenter,
    bars,
    qShareInDU,
    pShareInDeltaU,
    maxComp,
  };
});

const fmtSigned = (v: number, digits = 3): string =>
  `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(digits)}`;
</script>

<template>
  <div class="ps-lab">
    <div class="ps-lab-head">
      <div>
        <div class="ps-lab-title">电压降落相量与 P-Q 耦合交互实验</div>
        <div class="ps-lab-sub">
          末端参考 U̇₂ = 1.0∠0° · ΔU₂ = (P₂R + Q₂X)/U₂ · δU₂ = (P₂X − Q₂R)/U₂
        </div>
      </div>
      <div class="ps-presets">
        <button type="button" class="ps-btn" @click="applyPreset(0.8, 0.5, 0.15, 0.05)">
          高压感性负荷
        </button>
        <button type="button" class="ps-btn" @click="applyPreset(0.25, -0.6, 0.2, 0.05)">
          轻载容性升压
        </button>
        <button type="button" class="ps-btn" @click="applyPreset(0.8, 0.3, 0.15, 0.8)">
          低压配网 R≈X
        </button>
        <button type="button" class="ps-btn" @click="applyPreset(1.2, 0.0, 0.2, 0.05)">
          纯有功大相角
        </button>
      </div>
    </div>

    <div class="ps-controls">
      <label class="ps-slider">
        <div class="ps-slider-row">
          <span>末端有功 P₂</span>
          <strong>{{ p2.toFixed(2) }} pu</strong>
        </div>
        <input v-model.number="p2" type="range" min="0" max="1.5" step="0.05" />
      </label>

      <label class="ps-slider">
        <div class="ps-slider-row">
          <span>末端无功 Q₂（负为容性）</span>
          <strong>{{ fmtSigned(q2, 2) }} pu</strong>
        </div>
        <input v-model.number="q2" type="range" min="-0.8" max="1.0" step="0.05" />
      </label>

      <label class="ps-slider">
        <div class="ps-slider-row">
          <span>线路电抗 X</span>
          <strong>{{ xLine.toFixed(2) }} pu</strong>
        </div>
        <input v-model.number="xLine" type="range" min="0.05" max="0.25" step="0.01" />
      </label>

      <label class="ps-slider">
        <div class="ps-slider-row">
          <span>阻抗比 R/X（R = {{ sim.R.toFixed(3) }}）</span>
          <strong>{{ rxRatio.toFixed(2) }}</strong>
        </div>
        <input v-model.number="rxRatio" type="range" min="0.02" max="1.0" step="0.02" />
      </label>
    </div>

    <div class="ps-grid">
      <!-- Left SVG: Voltage Drop Phasor Diagram -->
      <div class="ps-panel">
        <div class="ps-panel-label">
          电压降落相量图（虚弧为 |U̇| = U₂ 等幅值圆）
          <span v-if="sim.isRise" class="ps-badge rise">末端容性升压 U₂ &gt; U₁</span>
        </div>
        <svg viewBox="0 0 360 220" class="ps-svg" role="img" aria-label="电压降落相量图">
          <defs>
            <clipPath id="ps-vdrop-phasor-clip">
              <rect x="6" y="6" width="348" height="208" />
            </clipPath>
            <marker
              id="ps-vdrop-arr-u2"
              viewBox="0 0 10 10"
              refX="8.5"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,1.5 L9,5 L0,8.5 z" fill="var(--ink)" />
            </marker>
            <marker
              id="ps-vdrop-arr-u1"
              viewBox="0 0 10 10"
              refX="8.5"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,1.5 L9,5 L0,8.5 z" fill="var(--vp-c-accent)" />
            </marker>
          </defs>

          <g clip-path="url(#ps-vdrop-phasor-clip)">
            <!-- Axes -->
            <line x1="16" :y1="sim.oy" x2="348" :y2="sim.oy" class="svg-axis" />
            <line :x1="sim.ox" y1="14" :x2="sim.ox" y2="206" class="svg-axis" />

            <!-- Constant magnitude arc |U| = U2 -->
            <path :d="sim.refArcPath" fill="none" class="svg-ref" />

            <!-- Longitudinal component Delta U2 -->
            <line
              :x1="sim.u2X"
              :y1="sim.u2Y"
              :x2="sim.dUX"
              :y2="sim.u2Y"
              class="svg-du"
            />

            <!-- Transverse component j delta U2 -->
            <line
              :x1="sim.dUX"
              :y1="sim.u2Y"
              :x2="sim.u1X"
              :y2="sim.u1Y"
              class="svg-deltau"
            />

            <!-- Right-angle marker at (dUX, oy) -->
            <rect
              v-if="Math.abs(sim.dU) > 0.025 && Math.abs(sim.deltaU) > 0.025"
              :x="sim.dU >= 0 ? sim.dUX - 6 : sim.dUX"
              :y="sim.deltaU >= 0 ? sim.oy - 6 : sim.oy"
              width="6"
              height="6"
              fill="none"
              class="svg-axis"
            />

            <!-- Angle arc delta1 -->
            <path v-if="sim.angArcPath" :d="sim.angArcPath" fill="none" class="svg-ang" />
            <text
              v-if="sim.angArcPath"
              :x="sim.angLblX"
              :y="sim.angLblY + 3"
              class="svg-lbl-ang"
            >
              δ₁={{ sim.delta1Deg.toFixed(1) }}°
            </text>

            <!-- Phasor U2 -->
            <line
              :x1="sim.ox"
              :y1="sim.oy"
              :x2="sim.u2X"
              :y2="sim.u2Y"
              class="svg-u2"
              marker-end="url(#ps-vdrop-arr-u2)"
            />

            <!-- Phasor U1 -->
            <line
              :x1="sim.ox"
              :y1="sim.oy"
              :x2="sim.u1X"
              :y2="sim.u1Y"
              class="svg-u1"
              marker-end="url(#ps-vdrop-arr-u1)"
            />

            <!-- Origin dot -->
            <circle :cx="sim.ox" :cy="sim.oy" r="2.6" fill="var(--ink)" />

            <!-- Labels -->
            <text :x="(sim.ox + sim.u2X) * 0.52" :y="sim.oy + 14" class="svg-lbl-u2">
              U̇₂ = 1.00∠0°
            </text>
            <text
              :x="(sim.ox + sim.u1X) * 0.46"
              :y="Math.min(sim.oy - 10, (sim.oy + sim.u1Y) * 0.5 - 8)"
              class="svg-lbl-u1"
            >
              U̇₁ = {{ sim.u1Mag.toFixed(3) }}
            </text>
            <text
              v-if="Math.abs(sim.dU) > 0.01"
              :x="(sim.u2X + sim.dUX) * 0.5"
              :y="sim.deltaU >= 0 ? sim.oy + 14 : sim.oy - 7"
              text-anchor="middle"
              class="svg-lbl-du"
            >
              ΔU₂
            </text>
            <text
              v-if="Math.abs(sim.deltaU) > 0.01"
              :x="sim.u1X + 6"
              :y="(sim.oy + sim.u1Y) * 0.5 + 3"
              class="svg-lbl-deltau"
            >
              jδU₂
            </text>
          </g>
        </svg>
      </div>

      <!-- Right SVG: P/Q Coupling Breakdown -->
      <div class="ps-panel">
        <div class="ps-panel-label">
          纵/横分量构成（检验 V–Q 与 δ–P 解耦程度）
          <span class="ps-badge" :class="sim.isDecoupled ? 'ok' : 'warn'">
            {{ sim.isDecoupled ? "高压近似解耦" : "R/X 偏大·强耦合" }}
          </span>
        </div>
        <svg viewBox="0 0 340 220" class="ps-svg" role="img" aria-label="纵横分量P与Q贡献分解图">
          <!-- Group headers -->
          <text x="10" y="20" class="svg-group">纵分量 ΔU₂（影响幅值）</text>
          <text x="10" y="118" class="svg-group">横分量 δU₂（影响相角）</text>

          <!-- Zero reference vertical line -->
          <line :x1="sim.barCenter" y1="24" :x2="sim.barCenter" y2="204" class="svg-axis" />
          <line x1="10" y1="104" x2="330" y2="104" class="svg-ref" />

          <!-- Bars -->
          <g v-for="b in sim.bars" :key="b.label">
            <text x="10" :y="b.y + 11" class="svg-bar-lbl">{{ b.label }}</text>
            <rect :x="b.x" :y="b.y" :width="b.w" height="14" rx="2" :class="b.cls" />
            <text
              :x="b.val >= 0 ? Math.min(336, b.x + b.w + 4) : b.x - 4"
              :y="b.y + 11"
              :text-anchor="b.val >= 0 ? 'start' : 'end'"
              class="svg-tick"
            >
              {{ fmtSigned(b.val, 3) }}
            </text>
          </g>

          <!-- Footer note -->
          <text x="10" y="214" class="svg-tick">
            Q 占 |ΔU₂| {{ sim.qShareInDU.toFixed(0) }}% · P 占 |δU₂| {{ sim.pShareInDeltaU.toFixed(0) }}%
          </text>
        </svg>
      </div>
    </div>

    <div class="ps-metrics">
      <div class="ps-metric">
        <span>首端电压 U₁ ∠ δ₁</span>
        <strong>{{ sim.u1Mag.toFixed(4) }} ∠ {{ fmtSigned(sim.delta1Deg, 2) }}°</strong>
      </div>
      <div class="ps-metric">
        <span>电压损耗 U₁−U₂（近似 ΔU₂）</span>
        <strong>
          {{ fmtSigned(sim.exactLoss, 4) }}
          <em>({{ fmtSigned(sim.dU, 4) }})</em>
        </strong>
      </div>
      <div class="ps-metric">
        <span>纵分量误差 (U₁−U₂)−ΔU₂</span>
        <strong>{{ fmtSigned(sim.approxErr, 4) }} pu</strong>
      </div>
      <div class="ps-metric">
        <span>串联损耗 ΔP_S + jΔQ_S</span>
        <strong>{{ sim.dPs.toFixed(4) }} + j{{ sim.dQs.toFixed(4) }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.ps-lab {
  margin: 1.25rem 0;
  padding: 1rem 1.05rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
}

.ps-lab-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.78rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.ps-lab-title {
  color: var(--ink);
  font-size: 0.96rem;
  font-weight: 700;
}

.ps-lab-sub {
  margin-top: 0.14rem;
  color: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 0.74rem;
}

.ps-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.ps-btn {
  padding: 0.25rem 0.56rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.73rem;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;

  &:hover {
    border-color: var(--vp-c-accent);
    color: var(--vp-c-accent);
  }
}

.ps-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem 0.9rem;
  margin-bottom: 0.78rem;
}

.ps-slider {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;

  input[type="range"] {
    width: 100%;
    margin: 0;
    accent-color: var(--vp-c-accent);
  }
}

.ps-slider-row {
  display: flex;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--vp-c-text-mute);

  strong {
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-variant-numeric: tabular-nums;
  }
}

.ps-grid {
  display: grid;
  grid-template-columns: 1.06fr 1fr;
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-bottom: 0.28rem;
  color: var(--vp-c-text-mute);
  font-size: 0.75rem;
  font-weight: 600;
}

.ps-badge {
  padding: 0.08rem 0.42rem;
  border-radius: var(--r, 2px);
  font-size: 0.68rem;
  font-weight: 600;

  &.ok {
    background: rgba(30, 122, 86, 0.13);
    color: #1e7a56;
  }

  &.warn {
    background: rgba(200, 62, 55, 0.13);
    color: #c83e37;
  }

  &.rise {
    background: rgba(45, 114, 210, 0.14);
    color: var(--vp-c-accent);
  }
}

.ps-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  opacity: 0.55;
}

.svg-ref {
  stroke: var(--vp-c-border);
  stroke-width: 1.1;
  stroke-dasharray: 4 3;
}

.svg-u2 {
  stroke: var(--ink);
  stroke-width: 2.3;
}

.svg-u1 {
  stroke: var(--vp-c-accent);
  stroke-width: 2.4;
}

.svg-du {
  stroke: #c83e37;
  stroke-width: 2.2;
}

.svg-deltau {
  stroke: #1e7a56;
  stroke-width: 2.2;
}

.svg-ang {
  stroke: var(--vp-c-accent);
  stroke-width: 1.3;
}

.svg-lbl-u2 {
  fill: var(--ink);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-lbl-u1 {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 700;
}

.svg-lbl-du {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-lbl-deltau {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-lbl-ang {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 9px;
}

.svg-group {
  fill: var(--ink);
  font-size: 9.5px;
  font-weight: 700;
}

.svg-bar-lbl {
  fill: var(--vp-c-text);
  font-family: var(--vp-font-mono);
  font-size: 9.2px;
}

.bar-q {
  fill: var(--vp-c-accent);
  opacity: 0.85;
}

.bar-p {
  fill: #1e7a56;
  opacity: 0.85;
}

.bar-sum {
  fill: #c83e37;
}

.bar-sum2 {
  fill: #145c40;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9px;
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
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;

    em {
      color: var(--vp-c-text-mute);
      font-style: normal;
      font-weight: 400;
    }
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
