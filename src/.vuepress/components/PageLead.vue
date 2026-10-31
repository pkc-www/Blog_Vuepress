<script setup lang="ts">
// 文章摘要：把 frontmatter.description 显示在标题和信息行下面
// 必须放在 [vp-content] 外面：正文里的文字会进入批注索引（已保存批注的 pos 会整体偏移、开头的前文上下文失效），
// 也会被搜索再索引一遍。主题在标题和正文之间没有插槽，所以在标题区里挂一个节点，用 Teleport 渲染进去
import { onMounted, ref } from "vue";
import { onContentUpdated, useFrontmatter, useRoute } from "vuepress/client";

const frontmatter = useFrontmatter<{ description?: string }>();
const route = useRoute();

const host = ref<HTMLElement | null>(null);
const text = ref("");

// 只在文章页显示（和批注、阅读控件的范围一致），博文大全页除外
const readText = (): string => {
  const path = decodeURI(route.path);
  if (!path.startsWith("/post/") || path === "/post/") return "";
  return String(frontmatter.value.description ?? "").trim();
};

// 挂载点放在标题区的分隔线前面（标题、信息行之后）
// 换页时主题会整块重建标题区，这里跟着重新找；摘要在挂载时取一次，旧页面淡出时不会先换成新摘要
const attach = (): void => {
  const title = document.querySelector<HTMLElement>(".vp-page-title");
  if (!title) {
    host.value = null;
    return;
  }
  let el = title.querySelector<HTMLElement>(":scope > .vp-page-lead-host");
  if (!el) {
    el = document.createElement("div");
    el.className = "vp-page-lead-host";
    title.insertBefore(el, title.querySelector(":scope > hr"));
  }
  text.value = readText();
  host.value = el;
};

onContentUpdated((reason) => {
  if (reason === "beforeUnmount") host.value = null;
  else attach();
});

onMounted(attach);
</script>

<template>
  <Teleport v-if="host && text" :to="host">
    <p class="vp-page-lead">{{ text }}</p>
  </Teleport>
</template>
