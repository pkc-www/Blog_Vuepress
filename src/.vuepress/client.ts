import { defineClientConfig } from "vuepress/client";

import AnnotationLayer from "./components/AnnotationLayer.vue";
import AnnotationReview from "./components/AnnotationReview.vue";
import PostIndex from "./components/PostIndex.vue";
import ReadingControls from "./components/ReadingControls.vue";
import HomeBlog from "./layouts/HomeBlog.vue";
import { initMotion, onRouteChange } from "./motion.js";

// 字体：自托管，按 unicode-range 分片，浏览器只下载页面用到的字
import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/400-italic.css";
import "@fontsource/source-serif-4/600.css";
import "@fontsource/source-serif-4/700.css";
import "@fontsource/noto-serif-sc/400.css";
import "@fontsource/noto-serif-sc/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/700.css";

import "./styles/home.scss";
import "./styles/motion.scss";

export default defineClientConfig({
  enhance({ app, router }) {
    // 博文大全页使用的课程卡片总览
    app.component("PostIndex", PostIndex);
    // 批注复习页（src/review/README.md）
    app.component("AnnotationReview", AnnotationReview);

    if (__VUEPRESS_SSR__) return;

    router.afterEach((to, from) => {
      onRouteChange(to.path !== from.path);
    });
  },

  setup() {
    if (__VUEPRESS_SSR__) return;
    // 等首屏渲染完成再挂载
    if (document.readyState === "complete") initMotion();
    else window.addEventListener("load", initMotion, { once: true });
  },

  // 首页：自定义 Hero 和课程条（其余沿用主题的 Blog 布局）
  layouts: { Blog: HomeBlog },

  // 文章页：批注层（划词高亮、旁注、批注栏）和阅读控件（左侧栏收放、此页内容面板）
  rootComponents: [AnnotationLayer, ReadingControls],
});
