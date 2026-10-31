<script setup lang="ts">
// 文章阅读页：左侧目录栏可收起；「此页内容」是右侧栏顶部的卡片，旁注排在它下方
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from "vue";
import { onContentUpdated, useRoute } from "vuepress/client";

interface Heading {
  level: number;
  title: string;
  slug: string;
}

const route = useRoute();
const mounted = ref(false);

const isPost = computed(() => {
  const path = decodeURI(route.path);
  return mounted.value && path.startsWith("/post/") && path !== "/post/";
});

const store = {
  get: (key: string): string | null => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set: (key: string, value: string): void => {
    try {
      localStorage.setItem(key, value);
    } catch {
      // 无痕模式下只在本次生效
    }
  },
};

const sidebarOff = ref(false);
const tocOpen = ref(false);

watchEffect(() => {
  if (!mounted.value) return;
  const root = document.documentElement.classList;
  root.toggle("rd-page", isPost.value);
  root.toggle("rd-nosb", isPost.value && sidebarOff.value);
});

// 版面左右移动后，通知旁注重新对齐
const nudgeLayout = (): void => {
  window.setTimeout(() => window.dispatchEvent(new Event("resize")), 380);
};

const toggleSidebar = (): void => {
  sidebarOff.value = !sidebarOff.value;
  store.set("read:sidebar", sidebarOff.value ? "off" : "on");
  nudgeLayout();
};

const toggleToc = (): void => {
  tocOpen.value = !tocOpen.value;
};

// 宽屏打开文章时默认展开；窄屏会盖住正文，默认收起
const WIDE = 1180;
const resetToc = (): void => {
  tocOpen.value = window.innerWidth >= WIDE;
};

// 目录卡片展开/收起的动画过程中，每一帧都通知旁注让位
const card = ref<HTMLElement | null>(null);
let cardResize: ResizeObserver | null = null;
watch(card, (el, old) => {
  if (old) cardResize?.unobserve(old);
  if (el) cardResize?.observe(el);
});

/* ---------- 此页内容 ---------- */

// 从正文里读 h2/h3（主题没有在页面数据里保留标题列表）
const headings = ref<Heading[]>([]);

const readHeadings = (): void => {
  headings.value = [...document.querySelectorAll<HTMLElement>("[vp-content] h2[id], [vp-content] h3[id]")].map(
    (el) => ({
      level: Number(el.tagName[1]),
      title: (el.textContent ?? "").replace(/^#\s*/, "").trim(),
      slug: el.id,
    }),
  );
};

// 「参考资料」一节在面板里和前面的章节隔开
const isRefs = (heading: Heading): boolean =>
  heading.level === 2 && /^参考(资料|文献)/.test(heading.title);

onContentUpdated((reason) => {
  if (reason !== "beforeUnmount") window.setTimeout(() => {
    readHeadings();
    spy();
  }, 50);
});

const current = ref("");

const navbarHeight = (): number =>
  document.querySelector<HTMLElement>(".vp-navbar")?.offsetHeight ?? 64;

const spy = (): void => {
  const line = navbarHeight() + 90;
  let found = "";
  for (const heading of headings.value) {
    const el = document.getElementById(heading.slug);
    if (!el) continue;
    if (el.getBoundingClientRect().top <= line) found = heading.slug;
    else break;
  }
  current.value = found;
};

let frame = 0;
const onScroll = (): void => {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(spy);
};

const go = (heading: Heading): void => {
  const el = document.getElementById(heading.slug);
  if (!el) return;
  window.scrollTo({
    top: el.getBoundingClientRect().top + window.scrollY - navbarHeight() - 16,
    behavior: "smooth",
  });
  history.replaceState(history.state, "", `#${heading.slug}`);
};

// 当前标题保持在面板可见范围内（只滚面板自己，不带动页面）
const panel = ref<HTMLElement | null>(null);
watch(current, (slug) => {
  const box = panel.value;
  const item = box?.querySelector<HTMLElement>(`[data-slug="${CSS.escape(slug)}"]`);
  if (!box || !item) return;
  const top = item.offsetTop - box.offsetTop;
  if (top < box.scrollTop) box.scrollTo({ top: top - 8, behavior: "smooth" });
  else if (top + item.offsetHeight > box.scrollTop + box.clientHeight)
    box.scrollTo({ top: top + item.offsetHeight - box.clientHeight + 8, behavior: "smooth" });
});

watch(() => route.path, resetToc);

onMounted(() => {
  sidebarOff.value = store.get("read:sidebar") === "off";
  resetToc();
  cardResize = new ResizeObserver(() => window.dispatchEvent(new Event("rd-toc-resize")));
  if (card.value) cardResize.observe(card.value);
  mounted.value = true;
  window.addEventListener("scroll", onScroll, { passive: true });
  window.setTimeout(() => {
    readHeadings();
    spy();
  }, 300);
});

onBeforeUnmount(() => {
  window.removeEventListener("scroll", onScroll);
  cardResize?.disconnect();
  document.documentElement.classList.remove("rd-page", "rd-nosb");
});
</script>

<template>
  <div v-if="isPost" class="rd-ui">
    <button
      class="rd-sb-toggle"
      :class="{ off: sidebarOff }"
      :title="sidebarOff ? '展开左侧目录栏' : '收起左侧目录栏'"
      @click="toggleSidebar"
    >
      <svg viewBox="0 0 24 24" width="18" height="18">
        <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.6" />
        <path d="M9 4.5v15" stroke="currentColor" stroke-width="1.6" />
        <path :d="sidebarOff ? 'M13 10l2 2-2 2' : 'M15 10l-2 2 2 2'" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <section v-if="headings.length" ref="card" class="rd-toc-card" :class="{ open: tocOpen }">
      <button class="rd-toc-head" :title="tocOpen ? '收起此页内容' : '展开此页内容'" @click="toggleToc">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path d="M4 6h16M4 12h10M4 18h13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <span>此页内容</span>
        <span class="rd-toc-count">{{ headings.length }}</span>
        <svg class="rd-chev" viewBox="0 0 24 24" width="16" height="16">
          <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <div class="rd-toc-body">
        <div class="rd-toc-clip">
          <nav ref="panel" class="rd-toc">
            <a
              v-for="h in headings"
              :key="h.slug"
              :href="`#${h.slug}`"
              :data-slug="h.slug"
              :class="[`lv${h.level}`, { active: h.slug === current, sep: isRefs(h) }]"
              @click.prevent="go(h)"
            ><span class="rd-toc-t">{{ h.title }}</span></a>
          </nav>
        </div>
      </div>
    </section>
  </div>
</template>

<style lang="scss">
@use "../annotate/reading.scss";
</style>
