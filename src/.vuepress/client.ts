import { defineClientConfig } from "vuepress/client";

import AnnotationLayer from "./components/AnnotationLayer.vue";
import AnnotationReview from "./components/AnnotationReview.vue";
import ControlBodeNyquistLab from "./components/ControlBodeNyquistLab.vue";
import ControlRootLocusLab from "./components/ControlRootLocusLab.vue";
import ControlSecondOrderLab from "./components/ControlSecondOrderLab.vue";
import EmInductionMotorLab from "./components/EmInductionMotorLab.vue";
import EmRotatingFieldLab from "./components/EmRotatingFieldLab.vue";
import EmSyncMachineLab from "./components/EmSyncMachineLab.vue";
import EmTransformerLab from "./components/EmTransformerLab.vue";
import PageLead from "./components/PageLead.vue";
import PeDcDcLab from "./components/PeDcDcLab.vue";
import PePwmBridgeLab from "./components/PePwmBridgeLab.vue";
import PeRectifierLab from "./components/PeRectifierLab.vue";
import PostIndex from "./components/PostIndex.vue";
import PsEconomicDispatchLab from "./components/PsEconomicDispatchLab.vue";
import PsFrequencyControlLab from "./components/PsFrequencyControlLab.vue";
import PsPowerFlowLab from "./components/PsPowerFlowLab.vue";
import PsVoltageDropLab from "./components/PsVoltageDropLab.vue";
import PsVoltageReactiveLab from "./components/PsVoltageReactiveLab.vue";
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
import "@fontsource/jetbrains-mono/200.css";
import "@fontsource/jetbrains-mono/300.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/700.css";
// 展示字体：只用于站点名（Playfair Display，仅 latin 700 / 900）
// 和首页大标题、博主名（Noto Serif Display 可变字体，带 wdth 轴，可以压窄到 62.5%）
import "@fontsource/playfair-display/latin-700.css";
import "@fontsource/playfair-display/latin-900.css";
import "@fontsource-variable/noto-serif-display/wdth.css";
import "@fontsource-variable/noto-serif-display/wdth-italic.css";

import "./styles/home.scss";
import "./styles/motion.scss";

export default defineClientConfig({
  enhance({ app, router }) {
    // 博文大全页使用的课程卡片总览
    app.component("PostIndex", PostIndex);
    // 批注复习页（src/review/README.md）
    app.component("AnnotationReview", AnnotationReview);
    // 自动控制原理交互实验组件
    app.component("ControlSecondOrderLab", ControlSecondOrderLab);
    app.component("ControlRootLocusLab", ControlRootLocusLab);
    app.component("ControlBodeNyquistLab", ControlBodeNyquistLab);
    // 电力电子基础交互实验组件
    app.component("PeRectifierLab", PeRectifierLab);
    app.component("PeDcDcLab", PeDcDcLab);
    app.component("PePwmBridgeLab", PePwmBridgeLab);
    // 电力系统分析交互实验组件
    app.component("PsVoltageDropLab", PsVoltageDropLab);
    app.component("PsPowerFlowLab", PsPowerFlowLab);
    app.component("PsVoltageReactiveLab", PsVoltageReactiveLab);
    app.component("PsFrequencyControlLab", PsFrequencyControlLab);
    app.component("PsEconomicDispatchLab", PsEconomicDispatchLab);
    // 电机学交互实验组件
    app.component("EmTransformerLab", EmTransformerLab);
    app.component("EmRotatingFieldLab", EmRotatingFieldLab);
    app.component("EmSyncMachineLab", EmSyncMachineLab);
    app.component("EmInductionMotorLab", EmInductionMotorLab);

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

  // 文章页：批注层（划词高亮、旁注、批注栏）、阅读控件（左侧栏收放、此页内容面板）和标题下的摘要
  rootComponents: [AnnotationLayer, ReadingControls, PageLead],
});
