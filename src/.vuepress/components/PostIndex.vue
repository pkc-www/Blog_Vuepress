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

// 每张卡片最多列出的章节数（4 条让各卡片高度整齐）
const PREVIEW = 4;

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
    // 日期写成 MM-DD，<time> 里保留完整日期
    { value: updated ? updated.slice(5) : "—", unit: "", label: "最近更新", datetime: updated },
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
      <p class="pi-eyebrow">
        <span class="pi-eyebrow-rule" aria-hidden="true" />
        <span class="pi-eyebrow-en" lang="en">Course Notes</span>
        <span class="pi-eyebrow-zh">课程笔记</span>
      </p>
      <h1 class="pi-title">博文大全</h1>
      <p class="pi-lead">电气工程专业课的学习笔记，按课程与章节整理。从信号与系统、电磁场到电力系统，持续更新中。</p>
      <dl class="pi-stats">
        <div v-for="item in stats" :key="item.label" class="pi-stat">
          <dt>{{ item.label }}</dt>
          <dd>
            <time v-if="item.datetime" :datetime="item.datetime">{{ item.value }}</time>
            <template v-else>{{ item.value }}</template>
            <small v-if="item.unit">{{ item.unit }}</small>
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
      >
        <span class="pi-bar" aria-hidden="true" />
        <div class="pi-card-head">
          <span class="pi-index" aria-hidden="true">{{ pad(index) }}</span>
          <span v-if="course.tag" class="pi-tag"><i class="pi-dot" aria-hidden="true" />{{ course.tag }}</span>
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
            <template v-if="course.updated"><i /><time :datetime="course.updated">{{ course.updated.slice(5) }}</time></template>
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

      <aside class="pi-card pi-card-recent" :style="{ '--i': list.length }" aria-labelledby="pi-latest">
        <div class="pi-recent-head">
          <span class="pi-index" lang="en" aria-hidden="true">LATEST</span>
          <h2 id="pi-latest" class="pi-recent-heading">最近更新</h2>
        </div>
        <ol class="pi-recent">
          <li
            v-for="item in recent"
            :key="item.path"
            class="course-hue"
            :style="{ '--h': item.hue }"
          >
            <RouteLink :to="item.path" :title="item.desc || item.title">
              <time :datetime="item.date!">{{ item.date!.slice(5) }}</time>
              <span class="pi-recent-title">{{ item.title }}</span>
              <span class="pi-recent-course"><i class="pi-dot" aria-hidden="true" />{{ item.course }}</span>
            </RouteLink>
          </li>
        </ol>
      </aside>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.post-index {
  --pi-accent: var(--vp-c-accent);
  --pi-line: var(--vp-c-divider);
  --pi-muted: var(--vp-c-text-mute);

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

/* ---------- 顶部：大留白，不再铺坐标纸网格 ---------- */
.pi-hero {
  position: relative;
  padding: 128px 0 112px;
  overflow: hidden;
  // 波形的 z-index: -1 依赖这里新建的层叠上下文
  isolation: isolate;
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

  // 目标方波：灰色虚线
  .pi-wave-square {
    animation: pi-fade 1s 1.2s both;
    stroke: var(--pi-muted);
    stroke-dasharray: 3 5;
    stroke-width: 1;
    opacity: 0.6;
  }

  // 1 项、3 项用中性灰，只有 9 项用主色
  .pi-wave-0 {
    stroke: var(--line-strong);
    stroke-width: 1;
  }

  .pi-wave-1 {
    stroke: var(--pi-muted);
    stroke-width: 1.2;
    opacity: 0.75;
  }

  .pi-wave-2 {
    stroke-width: 2;
  }
}

// 横线 + 英文等宽小标 + 中文
.pi-eyebrow {
  display: flex;
  flex-wrap: wrap;
  gap: 0 14px;
  align-items: center;
  margin: 0;
  color: var(--ink);
}

.pi-eyebrow-rule {
  display: inline-block;
  width: 40px;
  height: 1.5px;
  background: var(--ink);
}

.pi-eyebrow-en {
  font-family: var(--vp-font-mono);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.pi-eyebrow-zh {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.pi-title {
  margin: 18px 0 0;
  padding: 0;
  border: none;
  color: var(--ink);
  font-size: clamp(44px, 6vw, 80px);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: 0.08em;
}

.pi-lead {
  max-width: 30em;
  margin: 32px 0 0;
  color: var(--pi-muted);
  font-size: 17px;
  line-height: 1.8;
}

// 统计数字：细等宽字，tabular-nums 让 count-up 滚动时宽度不跳
.pi-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 20px 32px;
  margin: 64px 0 0;

  dt {
    color: var(--pi-muted);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
  }

  dd {
    margin: 8px 0 0;
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-size: clamp(30px, 3.4vw, 44px);
    font-weight: 300;
    font-variant-numeric: tabular-nums;
    line-height: 1;

    small {
      margin-inline-start: 6px;
      color: var(--pi-muted);
      font-family: var(--vp-font);
      font-size: 15px;
      font-weight: 400;
    }
  }
}

@media (min-width: 641px) {
  .pi-stats {
    gap: 20px 0;

    .pi-stat + .pi-stat {
      margin-inline-start: 32px;
      padding-inline-start: 32px;
      border-inline-start: 1px solid var(--pi-line);
    }
  }
}

/* ---------- 课程卡片：开放式，顶部一条细线 + 课程色短条 ---------- */
.pi-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 56px 64px;
  padding-bottom: 160px;
}

.pi-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 28px 0 0;
  border-top: 1px solid var(--pi-line);

  // 悬停不上浮，只让空心编号填成课程色
  &.course-hue:hover .pi-index {
    color: var(--cc);
    -webkit-text-stroke-color: var(--cc);
  }
}

// 压在顶部细线上的 40px 课程色短条
.pi-bar {
  position: absolute;
  top: -1px;
  left: 0;
  width: 40px;
  height: 2px;
  background: var(--cc);
}

.pi-card-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

// 空心大编号（深色模式的描边色见 index.scss 第 9 节）
.pi-index {
  color: transparent;
  font-family: var(--vp-font-mono);
  font-size: clamp(44px, 4.4vw, 56px);
  font-weight: 200;
  font-variant-numeric: tabular-nums;
  line-height: 0.8;
  letter-spacing: -0.04em;
  -webkit-text-stroke: 1.25px var(--ink);
  transition:
    color 0.25s ease,
    -webkit-text-stroke-color 0.25s ease;
}

// 课程分类：透明底描边胶囊 + 课程色圆点
.pi-tag {
  display: inline-flex;
  flex: none;
  gap: 6px;
  align-items: center;
  box-sizing: border-box;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--pi-line);
  border-radius: 999px;
  color: var(--vp-c-text);
  font-size: 13px;
  white-space: nowrap;
}

.pi-dot {
  display: inline-block;
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--cc);
}

.pi-card-title {
  margin: 28px 0 0;
  padding: 0;
  border: none;
  font-size: clamp(22px, 2.2vw, 26px);
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 0.03em;
}

// 只有标题（和章节链接）可点；多一层 .post-index 压过 motion.scss 去掉下划线的规则
.post-index .pi-card-title a {
  color: var(--ink);
  border: none !important;
  text-decoration: none;
  transition: color 0.2s ease;

  &:hover {
    color: var(--vp-c-accent);
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 6px;
  }
}

.pi-card-desc {
  display: -webkit-box;
  margin: 12px 0 0;
  overflow: hidden;
  color: var(--pi-muted);
  font-size: 14.5px;
  line-height: 1.85;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.pi-chapters {
  margin: 24px 0 20px;
  padding: 0;
  list-style: none;

  li {
    margin: 0;
  }

  a {
    display: flex;
    align-items: baseline;
    box-sizing: border-box;
    min-height: 44px;
    margin: 0 -8px;
    padding: 10px 8px;
    border: none !important;
    border-radius: var(--r);
    color: var(--vp-c-text);
    font-size: 15px;
    line-height: 1.55;
    transition: background-color 0.2s ease;

    &:hover {
      background: var(--vp-c-bg-alt);

      .pi-ch-name {
        color: var(--vp-c-accent);
      }
    }
  }
}

// 章节号右对齐，一直用课程色
.pi-ch-no {
  flex: 0 0 2.2em;
  padding-inline-end: 0.6em;
  box-sizing: border-box;
  color: var(--cc);
  font-family: var(--vp-font-mono);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

// 名称单行省略，卡片高度整齐
.pi-ch-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s ease;
}

.pi-card-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
}

.pi-meta {
  color: var(--pi-muted);
  font-size: 13px;
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

  time {
    font-family: var(--vp-font-mono);
  }
}

.post-index .pi-more {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  min-height: 44px;
  border: none !important;
  color: var(--vp-c-accent);
  font-size: 14px;
  text-decoration: none;

  svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentcolor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
    transition: transform 0.25s ease;
  }

  &:hover {
    text-decoration: underline;

    svg {
      transform: translateX(3px);
    }
  }
}

@media (min-width: 720px) {
  .pi-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 88px 64px;
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

/* ---------- 最近更新：bg-alt 底块，条目分两行 ---------- */
.pi-card-recent {
  padding: 40px 40px 32px;
  border-top: none;
  background: var(--vp-c-bg-alt);

  .pi-index {
    font-size: clamp(48px, 5vw, 72px);
  }
}

.pi-recent-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: baseline;
}

// 重置主题给正文 h2 加的上边距、下划线和内边距
.pi-recent-heading {
  margin: 0;
  padding: 0;
  border: none;
  color: var(--ink);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 0.03em;
}

.pi-recent {
  margin: 18px 0 0;
  padding: 0;
  list-style: none;

  li {
    margin: 0;
    border-top: 1px solid var(--pi-line);
  }

  a {
    display: grid;
    grid-template-columns: 4.2em 1fr;
    gap: 2px 12px;
    align-items: baseline;
    box-sizing: border-box;
    min-height: 44px;
    margin: 0 -8px;
    padding: 10px 8px;
    border: none !important;
    border-radius: var(--r);
    color: var(--vp-c-text);
    transition: background-color 0.2s ease;

    // 底块是 bg-alt，悬停改用页面底色
    &:hover {
      background: var(--vp-c-bg);

      .pi-recent-title {
        color: var(--vp-c-accent);
      }
    }
  }

  time {
    color: var(--pi-muted);
    font-family: var(--vp-font-mono);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }
}

// 标题可以换行
.pi-recent-title {
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
  transition: color 0.2s ease;
}

// 课程名 + 色点放在第二行
.pi-recent-course {
  display: flex;
  grid-column: 2;
  gap: 6px;
  align-items: center;
  color: var(--pi-muted);
  font-size: 13px;
}

@media (max-width: 959px) {
  .pi-wave {
    display: none;
  }
}

@media (max-width: 719px) {
  .pi-hero {
    padding: 56px 0 48px;
  }

  .pi-card-recent {
    padding: 24px 20px;
  }
}
</style>
