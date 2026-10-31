<script setup lang="ts">
import { computed } from "vue";
import { RouteLink, useFrontmatter, withBase } from "vuepress/client";
import { Blog } from "vuepress-theme-hope/blog";
// 由 plugins/post-index.ts 在构建时生成
import courses from "@temp/post-index.js";

// 首页（Blog 布局）：自定义 Hero 文案区、“按课程浏览”条和文章信息行，其余沿用主题

const frontmatter = useFrontmatter<Record<string, any>>();

// tagline 形如“正文——出处”，拆成引文和署名两行
const quote = computed(() => {
  const tagline: string = frontmatter.value.tagline ?? "";
  const [text, author] = tagline.split(/\s*——\s*/);
  return { text, author: author ?? "" };
});

// heroText 形如“Notes for EE”：首词占一行，末词用主色，中间的词做成斜体小字
// 不足三个词（或没写 heroText）时返回 null，模板里按主题给的 info.text 原样显示
const heroTitle = computed(() => {
  const words = String(frontmatter.value.heroText ?? "").trim().split(/\s+/);
  if (words.length < 3) return null;
  return { first: words[0], middle: words.slice(1, -1).join(" "), last: words[words.length - 1] };
});

const avatar = computed(() =>
  frontmatter.value.heroImage ? withBase(frontmatter.value.heroImage) : null,
);

const list = courses as { title: string; path: string; hue: number; chapters: unknown[] }[];
const total = list.reduce((sum, c) => sum + c.chapters.length, 0);

// 文章信息行：分类名就是课程名，按名字查课程色；查不到时 .course-hue 用默认色相
const hueOf = (name: string): number | undefined => list.find((c) => c.title === name)?.hue;
// 与 post-index.ts 一致，日期统一写成 YYYY-MM-DD
const isoDate = (date: Date): string => date.toISOString().slice(0, 10);

const scrollToArticles = (): void => {
  document.querySelector(".blog-page-wrapper")?.scrollIntoView({ behavior: "smooth" });
};
</script>

<template>
  <Blog>
    <template #heroLogo>
      <span />
    </template>

    <template #heroInfo="info">
      <div class="hb-hero">
        <!-- 文字列：最宽 440px，靠左；逐个元素依次上升入场 -->
        <div class="hb-col">
          <img v-if="avatar" class="hb-avatar" :src="avatar" alt="" />
          <p class="hb-eyebrow" lang="en">
            <span class="hb-eyebrow-rule" aria-hidden="true" />
            <span>Electrical Engineering · Tsinghua</span>
          </p>
          <h1 class="hb-title" lang="en">
            <template v-if="heroTitle">
              <span class="hb-t1">{{ heroTitle.first }}</span>
              <span class="hb-t2"><i>{{ heroTitle.middle }}</i><span class="hb-t-acc">{{ heroTitle.last }}</span></span>
            </template>
            <template v-else>{{ info.text }}</template>
          </h1>
          <blockquote v-if="quote.text" class="hb-quote">
            <p>{{ quote.text }}</p>
            <cite v-if="quote.author">—— {{ quote.author }}</cite>
          </blockquote>
          <div class="hb-actions">
            <RouteLink to="/post/" class="hb-btn hb-btn-primary">
              浏览笔记
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9.5M8.5 4l4 4-4 4" /></svg>
            </RouteLink>
            <button type="button" class="hb-btn hb-btn-ghost" @click="scrollToArticles">
              最新文章
            </button>
          </div>
        </div>
      </div>
    </template>

    <template #articlesBefore>
      <section id="courses" class="hb-courses" aria-label="按课程浏览">
        <header class="hb-section-head">
          <span class="hb-sec-no" lang="en">§01</span>
          <h2>按课程浏览</h2>
          <RouteLink to="/post/" class="hb-more">{{ list.length }} 门课程 · {{ total }} 篇笔记 →</RouteLink>
        </header>
        <div class="hb-course-row">
          <RouteLink
            v-for="(course, index) in list"
            :key="course.path"
            :to="course.path"
            class="hb-course course-hue"
            :style="{ '--h': course.hue }"
          >
            <span class="hb-course-no" aria-hidden="true">{{ String(index + 1).padStart(2, "0") }}</span>
            <span class="hb-course-name">{{ course.title }}</span>
            <span class="hb-course-count">{{ course.chapters.length }} 篇</span>
          </RouteLink>
        </div>
        <header id="latest" class="hb-section-head hb-section-latest">
          <span class="hb-sec-no" lang="en">§02</span>
          <h2>最新文章</h2>
        </header>
      </section>
    </template>

    <!-- 首页文章信息行只留“日期 · 课程”；分类 / 标签 / 时间轴页面没有 home，仍用主题的 PageInfo -->
    <template v-if="frontmatter.home" #articleInfo="{ date, category }">
      <!-- 和主题的 PageInfo 一样阻止冒泡：点课程链接只去分类页，不触发整卡跳转 -->
      <div class="hb-article-meta" @click.stop>
        <span v-if="date" class="hb-article-date">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="1" /><path d="M3.5 10h17M8 3v4M16 3v4" /></svg>
          <time :datetime="isoDate(date)">{{ isoDate(date) }}</time>
        </span>
        <RouteLink
          v-for="item in category"
          :key="item.path"
          :to="item.path"
          class="hb-article-course course-hue"
          :style="{ '--h': hueOf(item.name) }"
        >
          <span class="hb-dot" aria-hidden="true" />{{ item.name }}
        </RouteLink>
      </div>
    </template>
  </Blog>
</template>
