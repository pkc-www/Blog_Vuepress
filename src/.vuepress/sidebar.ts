import { sidebar } from "vuepress-theme-hope";

export default sidebar({
  "/": [
    "",
    {
      text: "所有文章",
      icon: "book",
      prefix: "post/",
      link: "post/",
      children: "structure",
    },
  ],
});
