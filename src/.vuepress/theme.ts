import { hopeTheme } from "vuepress-theme-hope";
import navbar from "./navbar.js";
import sidebar from "./sidebar.js";

export default hopeTheme({
  hostname: "https://pkc-www.github.io/my_study_blog", // 如果没有域名先随便填或留空
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
    start: ["Brand"],
    center: ["Links"],
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
    blog: true,
    
    slimsearch: {
      // 是否索引正文内容（全文搜索核心）
      indexContent: true,
      // 开启搜索建议
      suggestion: true,
      // 这里的热键配置
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
  },
});