// 全站动效：阅读进度条、导航栏滚动态、页面切换入场、内容滚动渐显
// 样式在 styles/motion.scss；系统开启“减弱动态效果”时只保留进度条

const reduceMotion = (): boolean =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// 滚动到视口时渐显的元素（博文大全页的卡片有自己的入场动画，不在此列）
const REVEAL_SELECTOR = [
  ".vp-article-item",
  "[vp-content] > h2",
  "[vp-content] > h3",
  "[vp-content] img",
  "[vp-content] .katex-display",
  "[vp-content] > div[class*='language-']",
  "[vp-content] > .hint-container",
  "[vp-content] > table",
].join(",");

let observer: IntersectionObserver | null = null;

const setupReveal = (): void => {
  observer?.disconnect();
  if (reduceMotion() || !("IntersectionObserver" in window)) return;

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("mo-in");
        observer!.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -8% 0px" },
  );

  // 只处理首屏以下的元素，首屏内容直接显示，避免闪烁
  for (const el of document.querySelectorAll(REVEAL_SELECTOR)) {
    if (el.classList.contains("mo-in")) continue;
    if (!el.classList.contains("mo-reveal")) {
      if (el.getBoundingClientRect().top < window.innerHeight) continue;
      el.classList.add("mo-reveal");
    }
    observer.observe(el);
  }
};

const playPageEnter = (): void => {
  if (reduceMotion()) return;
  const page = document.querySelector(".vp-page");
  if (!page) return;
  page.classList.remove("mo-page-enter");
  // 触发重排，让动画可以重新播放
  void (page as HTMLElement).offsetWidth;
  page.classList.add("mo-page-enter");
};

let bar: HTMLElement | null = null;
let ticking = false;

const onScroll = (): void => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    ticking = false;
    const doc = document.documentElement;
    const max = doc.scrollHeight - window.innerHeight;
    const progress = max > 0 ? Math.min(window.scrollY / max, 1) : 0;
    if (bar) bar.style.transform = `scaleX(${progress})`;
    document.querySelector(".vp-navbar")?.classList.toggle("mo-scrolled", window.scrollY > 8);
  });
};

export const initMotion = (): void => {
  bar = document.createElement("div");
  bar.className = "mo-progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();
  setTimeout(setupReveal, 100);
};

// 路由切换后调用（hash 变化不算换页）
export const onRouteChange = (pathChanged: boolean): void => {
  setTimeout(() => {
    if (pathChanged) playPageEnter();
    setupReveal();
    onScroll();
  }, 50);
};
