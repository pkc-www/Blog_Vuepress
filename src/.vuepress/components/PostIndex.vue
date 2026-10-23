<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouteLink } from "vuepress/client";
// 由 plugins/post-index.ts 在构建时生成
import courses from "@temp/post-index.js";

interface Chapter {
  no: string | null;
  name: string;
  title: string;
  path: string;
  desc: string;
  date: string | null;
  words: number;
}

interface Course {
  title: string;
  path: string;
  desc: string;
  tag: string | null;
  hue: number;
  words: number;
  updated: string | null;
  chapters: Chapter[];
}

// 每张卡片最多列出的章节数
const PREVIEW = 5;

const list = courses as Course[];

const formatWords = (words: number): string =>
  words >= 10000 ? `${(words / 10000).toFixed(1)} 万字` : `${words} 字`;

const pad = (index: number): string => String(index + 1).padStart(2, "0");

// 章节序号：有“第N章”的用 N；同一课程里其他章节有编号而它没有时（如“场论”）用 ·
const chapterNo = (course: Course, chapter: Chapter, index: number): string =>
  chapter.no ?? (course.chapters.some((c) => c.no) ? "·" : String(index + 1));

// 顶部装饰：方波的傅里叶级数逼近（1、3、5 项）
const WAVE_W = 520;
const WAVE_H = 200;
const wavePath = (terms: number): string => {
  const points: string[] = [];
  for (let x = 0; x <= WAVE_W; x += 2) {
    const t = (x / WAVE_W) * 4 * Math.PI;
    let y = 0;
    for (let k = 0; k < terms; k++) y += Math.sin((2 * k + 1) * t) / (2 * k + 1);
    points.push(`${x},${(WAVE_H / 2 - y * 70).toFixed(1)}`);
  }
  return `M${points.join("L")}`;
};
const waves = [1, 3, 9].map(wavePath);
const squarePath = (() => {
  const half = WAVE_W / 4;
  const hi = WAVE_H / 2 - 55;
  const lo = WAVE_H / 2 + 55;
  let d = `M0,${WAVE_H / 2}V${hi}`;
  for (let i = 0; i < 4; i++) d += `H${half * (i + 1)}V${i % 2 ? hi : lo}`;
  return d;
})();

// 最近更新的笔记
const recent = computed(() =>
  list
    .flatMap((course) =>
      course.chapters.map((chapter) => ({ ...chapter, course: course.title, hue: course.hue })),
    )
    .filter((chapter) => chapter.date)
    .sort((a, b) => b.date!.localeCompare(a.date!) || a.title.localeCompare(b.title, "zh"))
    .slice(0, 5),
);

// 统计数字从 0 滚动到实际值（服务端渲染时直接是最终值）
const progress = ref(1);

onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const start = performance.now();
  const duration = 1100;
  progress.value = 0;
  const step = (now: number): void => {
    const x = Math.min((now - start) / duration, 1);
    progress.value = 1 - Math.pow(1 - x, 3);
    if (x < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
});

// 卡片上跟随鼠标的光斑
const onPointerMove = (event: PointerEvent): void => {
  const card = event.currentTarget as HTMLElement;
  const rect = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
  card.style.setProperty("--my", `${event.clientY - rect.top}px`);
};

const stats = computed(() => {
  const notes = list.reduce((sum, c) => sum + c.chapters.length, 0);
  const words = list.reduce((sum, c) => sum + c.words, 0);
  const updated = list
    .map((c) => c.updated)
    .filter(Boolean)
    .sort()
    .pop();
  const t = progress.value;
  return [
    { value: Math.round(list.length * t), unit: "门", label: "课程" },
    { value: Math.round(notes * t), unit: "篇", label: "笔记" },
    { value: ((words / 10000) * t).toFixed(1), unit: "万", label: "字数" },
    { value: updated ? updated.slice(5).replace("-", "/") : "—", unit: "", label: "最近更新" },
  ];
});
</script>

<template>
  <div class="post-index">
    <header class="pi-hero">
      <svg class="pi-wave" :viewBox="`0 0 ${WAVE_W} ${WAVE_H}`" aria-hidden="true">
        <path class="pi-wave-square" :d="squarePath" />
        <path
          v-for="(d, i) in waves"
          :key="i"
          :d="d"
          :class="`pi-wave-${i}`"
          pathLength="1"
        />
      </svg>
      <p class="pi-eyebrow">Course Notes · 课程笔记</p>
      <h1 class="pi-title">博文大全</h1>
      <p class="pi-lead">电气工程专业课的学习笔记，按课程与章节整理。从信号与系统、电磁场到电力系统，持续更新中。</p>
      <dl class="pi-stats">
        <div v-for="item in stats" :key="item.label" class="pi-stat">
          <dt>{{ item.label }}</dt>
          <dd>
            {{ item.value }}<small v-if="item.unit">{{ item.unit }}</small>
          </dd>
        </div>
      </dl>
    </header>

    <div class="pi-grid">
      <article
        v-for="(course, index) in list"
        :key="course.path"
        class="pi-card course-hue"
        :style="{ '--i': index, '--h': course.hue }"
        @pointermove="onPointerMove"
      >
        <div class="pi-card-head">
          <span class="pi-index">{{ pad(index) }}</span>
          <span v-if="course.tag" class="pi-tag">{{ course.tag }}</span>
        </div>

        <h2 class="pi-card-title">
          <RouteLink :to="course.path">{{ course.title }}</RouteLink>
        </h2>
        <p class="pi-card-desc">{{ course.desc }}</p>

        <ol class="pi-chapters">
          <li v-for="(chapter, i) in course.chapters.slice(0, PREVIEW)" :key="chapter.path">
            <RouteLink :to="chapter.path" :title="chapter.desc || chapter.title">
              <span class="pi-ch-no">{{ chapterNo(course, chapter, i) }}</span>
              <span class="pi-ch-name">{{ chapter.name }}</span>
            </RouteLink>
          </li>
        </ol>

        <footer class="pi-card-foot">
          <span class="pi-meta">
            {{ course.chapters.length }} 篇<i />{{ formatWords(course.words) }}
            <template v-if="course.updated"><i />{{ course.updated }}</template>
          </span>
          <RouteLink :to="course.path" class="pi-more">
            {{
              course.chapters.length > PREVIEW
                ? `全部 ${course.chapters.length} 篇`
                : "进入课程"
            }}
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 8h9.5M8.5 4l4 4-4 4" />
            </svg>
          </RouteLink>
        </footer>
      </article>

      <aside class="pi-card pi-card-recent" :style="{ '--i': list.length }">
        <div class="pi-card-head">
          <span class="pi-index">LATEST</span>
          <span class="pi-tag">最近更新</span>
        </div>
        <ol class="pi-recent">
          <li
            v-for="item in recent"
            :key="item.path"
            class="course-hue"
            :style="{ '--h': item.hue }"
          >
            <RouteLink :to="item.path" :title="item.desc || item.title">
              <time>{{ item.date!.slice(5) }}</time>
              <span class="pi-recent-title">{{ item.title }}</span>
              <span class="pi-recent-course"><i />{{ item.course }}</span>
            </RouteLink>
          </li>
        </ol>
        <p class="pi-recent-hint">按 <kbd>Ctrl</kbd> <kbd>K</kbd> 可搜索全部笔记内容</p>
      </aside>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.post-index {
  --pi-accent: var(--vp-c-accent);
  --pi-line: var(--vp-c-divider);
  --pi-muted: var(--vp-c-text-mute);
  --pi-card: var(--vp-c-bg-elv);
  --pi-radius: 16px;

  margin-top: 0.5rem;
}

/* ---------- 入场动画 ---------- */
@keyframes pi-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes pi-draw {
  from {
    stroke-dashoffset: 1;
  }

  to {
    stroke-dashoffset: 0;
  }
}

@keyframes pi-fade {
  from {
    opacity: 0;
  }
}

.pi-eyebrow,
.pi-title,
.pi-lead,
.pi-stats {
  animation: pi-rise 0.7s cubic-bezier(0.2, 0.7, 0.3, 1) both;
}

.pi-title {
  animation-delay: 0.06s;
}

.pi-lead {
  animation-delay: 0.12s;
}

.pi-stats {
  animation-delay: 0.18s;
}

.pi-grid > .pi-card {
  animation: pi-rise 0.7s cubic-bezier(0.2, 0.7, 0.3, 1) both;
  animation-delay: calc(0.25s + var(--i, 0) * 0.07s);
}

/* ---------- 顶部 ---------- */
.pi-hero {
  position: relative;
  padding: 3.5rem 0 2.75rem;
  isolation: isolate;

  // 坐标纸网格，四周渐隐
  &::before {
    content: "";
    position: absolute;
    inset: 0 -2rem;
    z-index: -1;
    background-image:
      linear-gradient(var(--pi-line) 1px, transparent 1px),
      linear-gradient(90deg, var(--pi-line) 1px, transparent 1px);
    background-size: 28px 28px;
    mask-image: radial-gradient(ellipse 70% 90% at 15% 30%, #000 10%, transparent 70%);
    opacity: 0.7;
  }
}

.pi-wave {
  position: absolute;
  top: 50%;
  right: 0;
  z-index: -1;
  width: min(46%, 520px);
  transform: translateY(-58%);
  fill: none;
  mask-image: linear-gradient(90deg, transparent, #000 18%, #000 82%, transparent);
  stroke-linecap: round;
  stroke-linejoin: round;

  path {
    stroke: var(--pi-accent);
  }

  path:not(.pi-wave-square) {
    stroke-dasharray: 1;
    animation: pi-draw 1.8s 0.3s cubic-bezier(0.45, 0, 0.2, 1) both;
  }

  .pi-wave-1 {
    animation-delay: 0.45s !important;
  }

  .pi-wave-2 {
    animation-delay: 0.6s !important;
  }

  .pi-wave-square {
    animation: pi-fade 1s 1.2s both;
    stroke: var(--pi-muted);
    stroke-dasharray: 3 5;
    stroke-width: 1;
    opacity: 0.5;
  }

  .pi-wave-0 {
    stroke: oklch(0.68 0.1 185);
    stroke-width: 1;
    opacity: 0.25;
  }

  .pi-wave-1 {
    stroke: oklch(0.65 0.12 300);
    stroke-width: 1.2;
    opacity: 0.45;
  }

  .pi-wave-2 {
    stroke-width: 1.8;
    opacity: 0.9;
  }
}

.pi-eyebrow {
  margin: 0 0 0.9rem;
  color: var(--pi-accent);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.pi-title {
  margin: 0;
  padding: 0;
  border: none;
  font-size: clamp(2.2rem, 5vw, 3.2rem);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: 0.04em;
}

.pi-lead {
  max-width: 34em;
  margin: 1.1rem 0 0;
  color: var(--pi-muted);
  font-size: 1.05rem;
  line-height: 1.8;
}

.pi-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 2.2rem 0 0;

  .pi-stat {
    padding: 0 2rem;
    border-inline-start: 1px solid var(--pi-line);

    &:first-child {
      padding-inline-start: 0;
      border: none;
    }
  }

  dt {
    color: var(--pi-muted);
    font-size: 0.8rem;
    letter-spacing: 0.08em;
  }

  dd {
    margin: 0.2rem 0 0;
    font-size: 1.7rem;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;

    small {
      margin-inline-start: 0.2em;
      color: var(--pi-muted);
      font-size: 0.85rem;
      font-weight: 500;
    }
  }
}

/* ---------- 课程卡片 ---------- */
.pi-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
  padding-bottom: 2rem;
}

.pi-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 1.6rem 1.75rem 1.25rem;
  border: 1px solid var(--pi-line);
  border-radius: var(--pi-radius);
  background: var(--pi-card);
  overflow: hidden;
  isolation: isolate;
  transition:
    transform 0.3s cubic-bezier(0.2, 0.7, 0.3, 1),
    box-shadow 0.3s ease,
    border-color 0.3s ease;

  // 悬停时顶部出现一道主色细线
  &::before {
    content: "";
    position: absolute;
    inset: 0 0 auto;
    height: 3px;
    background: linear-gradient(90deg, var(--pi-accent), transparent);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.45s ease;
  }

  // 跟随鼠标的柔光
  &::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    background: radial-gradient(
      320px circle at var(--mx, 50%) var(--my, 0),
      color-mix(in srgb, var(--pi-accent) 12%, transparent),
      transparent 70%
    );
    opacity: 0;
    transition: opacity 0.35s ease;
    pointer-events: none;
  }

  &:hover::after {
    opacity: 1;
  }

  &:hover {
    transform: translateY(-4px);
    border-color: color-mix(in srgb, var(--pi-accent) 35%, var(--pi-line));
    box-shadow: 0 14px 36px -12px rgb(20 40 70 / 22%);

    &::before {
      transform: scaleX(1);
    }
  }
}

.pi-card.course-hue {
  --pi-accent: var(--cc);

  background:
    radial-gradient(120% 70% at 0% 0%, color-mix(in srgb, var(--cc) 7%, transparent), transparent 60%),
    var(--pi-card);
}

.pi-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.9rem;
}

.pi-index {
  color: var(--pi-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  opacity: 0.85;
}

.pi-tag {
  padding: 0.15rem 0.65rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--pi-accent) 10%, transparent);
  color: var(--pi-accent);
  font-size: 0.75rem;
  letter-spacing: 0.04em;
}

.pi-card-title {
  margin: 0;
  padding: 0;
  border: none;
  font-size: 1.4rem;
  font-weight: 650;
  line-height: 1.35;
  letter-spacing: 0.03em;

  a {
    color: var(--vp-c-text);
    border: none !important;

    // 整个标题区域可点
    &::after {
      content: "";
      position: absolute;
      inset: 0;
      z-index: 0;
    }
  }
}

.pi-card-desc {
  display: -webkit-box;
  margin: 0.55rem 0 1.1rem;
  overflow: hidden;
  color: var(--pi-muted);
  font-size: 0.92rem;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.pi-chapters {
  position: relative;
  z-index: 1;
  flex: 1;
  margin: 0 0 1rem;
  padding: 0.35rem 0 0;
  border-top: 1px dashed var(--pi-line);
  list-style: none;

  li {
    margin: 0;
  }

  a {
    display: flex;
    gap: 0.8rem;
    align-items: baseline;
    margin: 0 -0.6rem;
    padding: 0.42rem 0.6rem;
    border: none !important;
    border-radius: 8px;
    color: var(--vp-c-text);
    font-size: 0.93rem;
    line-height: 1.5;
    transition: background 0.2s ease, color 0.2s ease;

    &:hover {
      background: color-mix(in srgb, var(--pi-accent) 8%, transparent);
      color: var(--pi-accent);

      .pi-ch-no {
        color: var(--pi-accent);
        transform: translateX(2px);
      }
    }
  }
}

.pi-ch-no {
  flex: none;
  transition: color 0.2s ease, transform 0.25s ease;
  min-width: 2.2em;
  color: var(--pi-muted);
  font-family: var(--vp-font-mono);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}

.pi-ch-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pi-card-foot {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  padding-top: 0.9rem;
  border-top: 1px solid var(--pi-line);
  font-size: 0.8rem;
}

.pi-meta {
  color: var(--pi-muted);
  font-variant-numeric: tabular-nums;

  i {
    display: inline-block;
    width: 3px;
    height: 3px;
    margin: 0 0.55em;
    border-radius: 50%;
    background: currentcolor;
    vertical-align: middle;
    opacity: 0.6;
  }
}

.pi-more {
  display: inline-flex;
  gap: 0.3em;
  align-items: center;
  border: none !important;
  color: var(--pi-accent);
  font-weight: 600;

  svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentcolor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.6;
    transition: transform 0.25s ease;
  }

  &:hover svg {
    transform: translateX(3px);
  }
}

@media (min-width: 720px) {
  .pi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1200px) {
  .pi-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  // 7 门课 + 最近更新：后者在三栏时横跨两格，补齐最后一行
  .pi-card-recent {
    grid-column: span 2;
  }
}

.pi-card-recent {
  background: transparent;
  border-style: dashed;

  &:hover {
    transform: none;
    box-shadow: none;
  }

  &::before {
    display: none;
  }

  .pi-index {
    font-size: 0.75rem;
  }

  kbd {
    padding: 0.05em 0.4em;
    border: 1px solid var(--pi-line);
    border-radius: 4px;
    font-family: var(--vp-font-mono);
    font-size: 0.8em;
  }
}

.pi-recent {
  flex: 1;
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    margin: 0;
    border-bottom: 1px solid var(--pi-line);

    &:last-child {
      border-bottom: none;
    }
  }

  a {
    display: flex;
    gap: 1rem;
    align-items: baseline;
    padding: 0.7rem 0;
    border: none !important;
    color: var(--vp-c-text);
    font-size: 0.95rem;
    transition: color 0.2s ease;

    &:hover {
      color: var(--pi-accent);
    }
  }

  time {
    flex: none;
    color: var(--pi-accent);
    font-family: var(--vp-font-mono);
    font-size: 0.8rem;
  }
}

.pi-recent-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pi-recent-course {
  flex: none;
  color: var(--pi-muted);
  font-size: 0.8rem;

  i {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-inline-end: 0.45em;
    border-radius: 50%;
    background: var(--cc);
    vertical-align: middle;
  }
}

.pi-recent .course-hue time {
  color: var(--cc);
}

.pi-recent-hint {
  margin: 0.8rem 0 0;
  color: var(--pi-muted);
  font-size: 0.8rem;
}

@media (max-width: 959px) {
  .pi-wave {
    display: none;
  }
}

@media (max-width: 719px) {
  .pi-hero {
    padding: 2rem 0 2rem;
  }

  .pi-stats .pi-stat {
    padding: 0 1.1rem;
  }

  .pi-stats dd {
    font-size: 1.35rem;
  }

  .pi-card {
    padding: 1.3rem 1.25rem 1.1rem;
  }
}
</style>
