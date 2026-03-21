import { defineUserConfig } from "vuepress";

import theme from "./theme.js";

export default defineUserConfig({
  base: "/Blog_Vuepress/", // 如果你要部署到 GitHub Pages 的子目录，这里需要改，比如 "/my-blog/"
  lang: "zh-CN",
  title: "Avalache's Blog", // 浏览器标签页的名字
  description: "THU DEE", 
  theme,
});
