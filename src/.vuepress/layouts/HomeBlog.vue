<script setup lang="ts">
import { computed } from "vue";
import { RouteLink, useFrontmatter, withBase } from "vuepress/client";
import { Blog } from "vuepress-theme-hope/blog";
// 由 plugins/post-index.ts 在构建时生成
import courses from "@temp/post-index.js";

// 首页（Blog 布局）：自定义 Hero 文案区和“按课程浏览”条，其余沿用主题

const frontmatter = useFrontmatter<Record<string, any>>();

// tagline 形如“正文——出处”，拆成引文和署名两行
const quote = computed(() => {
  const tagline: string = frontmatter.value.tagline ?? "";
  const [text, author] = tagline.split(/\s*——\s*/);
  return { text, author: author ?? "" };
});

const avatar = computed(() =>
  frontmatter.value.heroImage ? withBase(frontmatter.value.heroImage) : null,
);

const list = courses as { title: string; path: string; hue: number; chapters: unknown[] }[];
const total = list.reduce((sum, c) => sum + c.chapters.length, 0);

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
        <img v-if="avatar" class="hb-avatar" :src="avatar" alt="" />
        <p class="hb-eyebrow">Electrical Engineering · Tsinghua</p>
        <h1 class="hb-title">{{ info.text }}</h1>
        <blockquote v-if="quote.text" class="hb-quote">
          <p>{{ quote.text }}</p>
          <cite v-if="quote.author">— {{ quote.author }}</cite>
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
    </template>

    <template #articlesBefore>
      <section class="hb-courses" aria-label="按课程浏览">
        <header class="hb-section-head">
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
            <span class="hb-course-no">{{ String(index + 1).padStart(2, "0") }}</span>
            <span class="hb-course-name">{{ course.title }}</span>
            <span class="hb-course-count">{{ course.chapters.length }} 篇</span>
          </RouteLink>
        </div>
        <header class="hb-section-head hb-section-latest">
          <h2>最新文章</h2>
        </header>
      </section>
    </template>
  </Blog>
</template>
