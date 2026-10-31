import { hopeTheme } from "vuepress-theme-hope";
import navbar from "./navbar.js";
import sidebar from "./sidebar.js";

export default hopeTheme({
  hostname: "https://pkc-www.github.io", // 只写域名，子路径由 config.ts 的 base 决定
  author: {
    name: "Avalanche",
    url: "https://github.com/pkc-www",
  },
  // iconAssets: "fontawesome-with-brands", // 默认使用 FontAwesome 图标
  repo: "pkc-www/Blog_Vuepress", // 填了之后导航栏会自动出 GitHub 图标

  // 这里引入了导航栏和侧边栏文件
  navbar,
  sidebar,

  navbarLayout: {
    start: ["Brand", "Links"], // 导航链接紧跟站点名，中间栏留空
    center: [],
    end: ["Repo", "Outlook", "Search"], // 👈 删掉了 Language，保留 Search
  },

  // 博客相关的配置
  blog: {
    avatar: "/assets/images/ava.jpg",
    description: "THU DEE", // 侧边栏个人简介
    medias: {
      GitHub: "https://github.com/pkc-www",
      // 这里可以配置微信、知乎、B站等图标和链接
    },
  },

  plugins: {
    // 关闭自动摘要，文章卡片改为显示 frontmatter 里的 description
    blog: {
      excerptLength: 0,
    },

    photoSwipe: {
      selector: "[vp-content] img:not([no-view])",
    },

    slimsearch: {
      indexContent: true,
      suggestion: true,
      hotKeys: [
        { key: "k", ctrl: true },
        { key: "/", ctrl: false },
      ],
    },

    icon: {
      assets: "fontawesome-with-brands",
    },
  },

  markdown: {
    math: {
      type: "katex",
    },
    // 代码高亮：浅色 one-light，深色 one-dark-pro，显示行号
    highlighter: {
      type: "shiki",
      themes: {
        light: "one-light",
        dark: "one-dark-pro",
      },
      lineNumbers: true,
    },
    alert: true,
    imgSize: true,
    mark: true,
    sup: true,
    sub: true,
    footnote: true,
    tasklist: true,
    mermaid: true,
  },
});