import { defineUserConfig } from "vuepress";

import { postIndexPlugin } from "./plugins/post-index.js";
import theme from "./theme.js";

export default defineUserConfig({
  base: "/Blog_Vuepress/", // 与 GitHub 仓库名 pkc-www/Blog_Vuepress 一致
  lang: "zh-CN",
  title: "Avalache's Blog", // 浏览器标签页的名字
  description: "THU DEE", 
  theme,
  plugins: [postIndexPlugin()],
});
