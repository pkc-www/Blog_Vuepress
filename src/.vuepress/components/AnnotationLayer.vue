<script setup lang="ts">
// 文章页批注层：划词工具条、正文右侧的旁注卡片（宽屏）/ 批注气泡（窄屏）、批注栏。挂在 rootComponents 上
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { RouteLink, onContentUpdated, usePageData, useRoute } from "vuepress/client";

import { alignMathBands, buildIndex, describeRange, locate, unwrapAll, wrapRange } from "../annotate/anchor.js";
import { hasMath, loadKatex, renderNote } from "../annotate/render.js";
import {
  COLORS,
  type AnnoColor,
  type Annotation,
  addAnno,
  connectGitHub,
  disconnectGitHub,
  exportJSON,
  importJSON,
  initStore,
  pageAnnos,
  removeAnno,
  setOwner,
  state,
  syncNow,
  updateAnno,
} from "../annotate/store.js";

const route = useRoute();
const page = usePageData();
const mounted = ref(false);

const pagePath = computed(() => decodeURI(route.path));
// 只在课程笔记页启用，博文大全页除外
const active = computed(
  () => mounted.value && pagePath.value.startsWith("/post/") && pagePath.value !== "/post/",
);
const annos = computed(() =>
  pageAnnos(pagePath.value).sort((a, b) => a.pos - b.pos),
);
const orphans = ref(new Set<string>());

// 宽屏时批注直接排在正文右侧；窄屏退回点击弹出气泡
const MARGIN_MIN_WIDTH = 1180;
const wide = ref(false);
const margin = computed(
  () => active.value && wide.value && (state.owner || annos.value.length > 0),
);
const mathReady = ref(false);

const contentRoot = (): HTMLElement | null =>
  document.querySelector<HTMLElement>("[vp-content]");

const colorName = (color: AnnoColor): string =>
  COLORS.find((item) => item.id === color)?.name ?? "";

// 公式库异步加载完后重新渲染
const note = (text: string): string => {
  void mathReady.value;
  return renderNote(text);
};

/* ---------- 把批注画到正文上 ---------- */

const apply = (): void => {
  const root = contentRoot();
  if (!root) return;
  unwrapAll(root);
  const missing = new Set<string>();
  if (active.value)
    for (const anno of annos.value) {
      const index = buildIndex(root);
      const at = locate(index, anno);
      if (at) wrapRange(index, at[0], at[1], anno);
      else missing.add(anno.id);
    }
  orphans.value = missing;
  alignMathBands(root);
  markActive();
  void nextTick(relayout);
  if (!mathReady.value && annos.value.some((anno) => hasMath(anno.note)))
    void loadKatex().then(() => (mathReady.value = true));
};

let applyTimer = 0;
const scheduleApply = (): void => {
  window.clearTimeout(applyTimer);
  applyTimer = window.setTimeout(() => {
    apply();
    focusFromHash();
  }, 60);
};

const marksOf = (id: string): HTMLElement[] =>
  [...document.querySelectorAll<HTMLElement>(`[data-anno-id="${id}"]`)];

const flash = (id: string, cls = "anno-flash"): void => {
  for (const mark of marksOf(id)) {
    mark.classList.remove(cls);
    void mark.offsetWidth;
    mark.classList.add(cls);
    window.setTimeout(() => mark.classList.remove(cls), 1400);
  }
};

const jumpTo = (id: string, open = true): void => {
  const first = marksOf(id)[0];
  if (!first) return;
  first.scrollIntoView({ behavior: "smooth", block: "center" });
  flash(id);
  if (open) window.setTimeout(() => openBubble(id, first), 380);
};

// 从复习页跳过来时地址带 #anno-<id>
const focusFromHash = (): void => {
  const match = /^#anno-(\w+)$/.exec(location.hash);
  if (match && marksOf(match[1]).length) jumpTo(match[1]);
};

/* ---------- 划词工具条 ---------- */

const coarse = ref(false);
const bar = reactive({
  show: false,
  x: 0,
  y: 0,
  below: false,
  desc: null as ReturnType<typeof describeRange>,
});
let hideTimer = 0;

const readSelection = (): void => {
  if (!active.value || !state.owner) return;
  const selection = getSelection();
  const root = contentRoot();
  if (!selection || selection.isCollapsed || !selection.rangeCount || !root) {
    // 稍等再收起：点工具条按钮时选区会先被清掉
    window.clearTimeout(hideTimer);
    hideTimer = window.setTimeout(() => (bar.show = false), 300);
    return;
  }
  const range = selection.getRangeAt(0);
  const desc = describeRange(root, range);
  if (!desc || desc.quote.length > 3000) return;
  const rect = range.getBoundingClientRect();
  window.clearTimeout(hideTimer);
  // 手机上系统菜单在选区上方，工具条放到下方
  bar.below = coarse.value || rect.top < 120;
  bar.x = Math.min(
    Math.max(rect.left + rect.width / 2, 150),
    document.documentElement.clientWidth - 150,
  );
  bar.y = (bar.below ? rect.bottom + 10 : rect.top - 10) + window.scrollY;
  bar.desc = desc;
  bar.show = true;
};

let selTimer = 0;
const onSelectionChange = (): void => {
  window.clearTimeout(selTimer);
  selTimer = window.setTimeout(readSelection, coarse.value ? 350 : 120);
};

const create = (color: AnnoColor, withNote: boolean): void => {
  if (!bar.desc) return;
  const anno = addAnno({
    ...bar.desc,
    page: pagePath.value,
    pageTitle: page.value.title,
    color,
    note: "",
  });
  bar.show = false;
  getSelection()?.removeAllRanges();
  apply();
  flash(anno.id, "anno-new");
  if (withNote) {
    const first = marksOf(anno.id)[0];
    if (first) openBubble(anno.id, first, true);
  }
};

/* ---------- 批注气泡 ---------- */

const bubble = reactive({
  id: "",
  x: 0,
  y: 0,
  editing: false,
  draft: "",
});
const bubbleAnno = computed(() => state.list.find((item) => item.id === bubble.id));

const openBubble = (id: string, el: HTMLElement, edit = false): void => {
  const rect = el.getBoundingClientRect();
  const width = Math.min(340, document.documentElement.clientWidth - 24);
  bubble.id = id;
  bubble.x = Math.min(
    Math.max(rect.left, 12),
    document.documentElement.clientWidth - width - 12,
  );
  bubble.y = rect.bottom + window.scrollY + 8;
  const anno = state.list.find((item) => item.id === id);
  bubble.editing = edit || (state.owner && !anno?.note);
  bubble.draft = anno?.note ?? "";
  if (bubble.editing) void nextTick(() => focusEditor());
};

const focusEditor = (): void => {
  document.querySelector<HTMLTextAreaElement>(".anno-ui .anno-editor")?.focus({ preventScroll: true });
};

const startEdit = (anno: Annotation): void => {
  bubble.id = anno.id;
  bubble.editing = true;
  bubble.draft = anno.note;
  void nextTick(() => focusEditor());
};

const closeBubble = (): void => {
  bubble.id = "";
  bubble.editing = false;
};

/* ---------- 旁注栏（宽屏） ---------- */

// 右侧栏：和 reading.scss 里的 $edge / $column 一致
const EDGE = 24;
const COLUMN = 288;
const GAP = 10;

const gutter = reactive({ left: 0, width: COLUMN });
// 每张卡片的位置：fixed 表示被「此页内容」卡片顶住、停在它下方（视口坐标），否则随正文滚动（文档坐标）
const place = reactive<Record<string, { y: number; fixed: boolean }>>({});
const still = reactive(new Set<string>());
// 原文已经滚出导航栏的批注：卡片和连线原地淡出，不滑到目录后面
const gone = reactive(new Set<string>());
const cardEls = new Map<string, HTMLElement>();

const setCardEl = (id: string, el: unknown): void => {
  if (el instanceof HTMLElement) {
    if (cardEls.get(id) !== el) cardResize?.observe(el);
    cardEls.set(id, el);
  } else cardEls.delete(id);
};

const navbarBottom = (): number =>
  document.querySelector(".vp-navbar")?.getBoundingClientRect().bottom ?? 64;

// 卡片和高亮对齐；被目录挡住的排到目录下方；挤在一起时依次往下排
const relayout = (): void => {
  if (!margin.value) return;
  gutter.width = COLUMN;
  gutter.left = document.documentElement.clientWidth - EDGE - COLUMN;
  const sy = window.scrollY;
  const nav = navbarBottom();
  const toc = document.querySelector(".rd-toc-card");
  const floorView = (toc ? toc.getBoundingClientRect().bottom : nav) + 14;
  const items = annos.value
    .filter((anno) => !orphans.value.has(anno.id))
    .flatMap((anno) => {
      const rect = marksOf(anno.id)[0]?.getClientRects()[0];
      if (!rect) return [];
      return [{
        id: anno.id,
        want: sy + rect.top - 6,
        floor: sy + floorView,
        out: rect.bottom < nav,
        h: cardEls.get(anno.id)?.offsetHeight ?? 60,
      }];
    })
    .sort((a, b) => a.want - b.want);

  const moves: [string, { y: number; fixed: boolean }][] = [];
  let prev: { y: number; h: number; fixed: boolean } | null = null;
  for (const item of items) {
    const el = cardEls.get(item.id);
    if (item.out) {
      // 定在当前所在位置淡出；不参与排布，也不挤占后面的卡片
      if (!gone.has(item.id)) {
        gone.add(item.id);
        const top = el?.getBoundingClientRect().top;
        if (top !== undefined) {
          place[item.id] = { y: top, fixed: true };
          still.add(item.id);
          moves.push([item.id, place[item.id]]);
        }
      }
      continue;
    }
    const wasGone = gone.delete(item.id);
    let y = item.want;
    let fixed = false;
    if (item.floor > y) {
      y = item.floor;
      fixed = true;
    }
    if (prev && prev.y + prev.h + GAP > y) {
      y = prev.y + prev.h + GAP;
      fixed = prev.fixed;
    }
    prev = { y, h: item.h, fixed };
    const target = { y: fixed ? y - sy : y, fixed };
    const old = place[item.id];
    if (wasGone) {
      // 原文重新回到屏幕里：直接出现在目标位置，靠淡入显示
      place[item.id] = target;
      still.add(item.id);
      moves.push([item.id, target]);
    } else if (old && el && old.fixed !== fixed) {
      // 换定位方式时先原地切换（不动画），下一帧再滑到目标位置
      const top = el.getBoundingClientRect().top;
      place[item.id] = { y: fixed ? top : top + sy, fixed };
      still.add(item.id);
      moves.push([item.id, target]);
    } else place[item.id] = target;
  }
  if (moves.length)
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        still.clear();
        for (const [id, target] of moves) place[id] = target;
        animateLinks();
      }),
    );
  drawLinks();
};

let frame = 0;
const scheduleRelayout = (): void => {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    relayout();
    animateLinks();
  });
};

/* ---------- 连线：从正文右缘指向批注卡片 ---------- */

const links = ref<{ id: string; d: string; x: number; y: number; color: AnnoColor }[]>([]);
const linkBox = reactive({ w: 0, h: 0 });

const drawLinks = (): void => {
  const root = contentRoot();
  if (!margin.value || !root) {
    links.value = [];
    return;
  }
  const sy = window.scrollY;
  const x0 = root.getBoundingClientRect().right + 12;
  linkBox.w = document.documentElement.clientWidth;
  linkBox.h = document.documentElement.scrollHeight;
  const out: typeof links.value = [];
  for (const anno of annos.value) {
    const card = cardEls.get(anno.id);
    const rect = marksOf(anno.id)[0]?.getClientRects()[0];
    if (!card || !rect || orphans.value.has(anno.id) || gone.has(anno.id)) continue;
    const box = card.getBoundingClientRect();
    const y0 = rect.top + rect.height / 2 + sy;
    const x1 = box.left - 1;
    const y1 = box.top + Math.min(20, box.height / 2) + sy;
    const dx = Math.max(12, (x1 - x0) * 0.55);
    out.push({
      id: anno.id,
      d: `M${x0},${y0} C${x0 + dx},${y0} ${x1 - dx},${y1} ${x1},${y1}`,
      x: x0,
      y: y0,
      color: anno.color,
    });
  }
  links.value = out;
};

// 卡片在做过渡动画时连续重画连线
let linkUntil = 0;
let linkFrame = 0;
const animateLinks = (ms = 560): void => {
  linkUntil = Math.max(linkUntil, performance.now() + ms);
  if (linkFrame) return;
  const tick = (): void => {
    drawLinks();
    linkFrame = performance.now() < linkUntil ? requestAnimationFrame(tick) : 0;
  };
  linkFrame = requestAnimationFrame(tick);
};

let scrollFrame = 0;
const onScroll = (): void => {
  if (!margin.value) return;
  cancelAnimationFrame(scrollFrame);
  scrollFrame = requestAnimationFrame(relayout);
};

let contentResize: ResizeObserver | null = null;
let cardResize: ResizeObserver | null = null;

// 选中的批注：正文高亮涂满，对应卡片突出
const markActive = (): void => {
  document
    .querySelectorAll(".anno-hl.anno-active")
    .forEach((el) => el.classList.remove("anno-active"));
  if (bubble.id) marksOf(bubble.id).forEach((el) => el.classList.add("anno-active"));
};

const onCardClick = (anno: Annotation): void => {
  if (bubble.id === anno.id) return;
  bubble.id = anno.id;
  bubble.editing = false;
  flash(anno.id);
};

const saveNote = (): void => {
  if (!bubble.id) return;
  updateAnno(bubble.id, { note: bubble.draft.trim() });
  bubble.editing = false;
  apply();
};

const recolor = (color: AnnoColor): void => {
  updateAnno(bubble.id, { color });
  apply();
};

const remove = (id: string): void => {
  removeAnno(id);
  if (bubble.id === id) closeBubble();
  apply();
};

const onEditorKey = (event: KeyboardEvent): void => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) saveNote();
  if (event.key === "Escape") bubble.editing = false;
};

const onDocClick = (event: MouseEvent): void => {
  const target = event.target as HTMLElement;
  if (target.closest(".anno-ui")) return;
  const mark = target.closest<HTMLElement>("[data-anno-id]");
  if (mark && active.value && !getSelection()?.toString()) {
    openBubble(mark.dataset.annoId!, mark);
    return;
  }
  closeBubble();
};

/* ---------- 批注栏 ---------- */

const drawer = ref(false);
const filter = ref<AnnoColor | "all">("all");
const shown = computed(() =>
  filter.value === "all" ? annos.value : annos.value.filter((a) => a.color === filter.value),
);
const fileInput = ref<HTMLInputElement | null>(null);
const toast = ref("");

const say = (text: string): void => {
  toast.value = text;
  window.setTimeout(() => (toast.value = ""), 2400);
};

const onImport = async (event: Event): Promise<void> => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  try {
    const added = await importJSON(file);
    say(`导入完成，新增 ${added} 条`);
    apply();
  } catch (err) {
    say(`导入失败：${(err as Error).message}`);
  }
  (event.target as HTMLInputElement).value = "";
};

/* ---------- GitHub 同步 ---------- */

const linkForm = reactive({ open: false, token: "", busy: false, error: "" });

const connect = async (): Promise<void> => {
  if (!linkForm.token.trim()) return;
  linkForm.busy = true;
  linkForm.error = "";
  try {
    await connectGitHub(linkForm.token);
    linkForm.open = false;
    linkForm.token = "";
    say(state.error || "已连接，批注会同步到仓库");
  } catch (err) {
    linkForm.error = (err as Error).message;
  } finally {
    linkForm.busy = false;
  }
};

const syncText = computed(() => {
  if (state.saving) return "正在同步…";
  if (state.error) return state.error;
  if (!state.connected) return "批注目前只存在这台设备的浏览器里";
  if (!state.syncedAt) return "已连接 GitHub";
  const minutes = Math.round((Date.now() - state.syncedAt) / 60000);
  return `已同步到 GitHub · ${minutes < 1 ? "刚刚" : `${minutes} 分钟前`}`;
});

const timeText = (anno: Annotation): string => {
  const date = new Date(anno.updated);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
};

// 窄屏上批注栏盖住正文，跳转前先收起
const onCard = (id: string): void => {
  if (document.documentElement.clientWidth < 960) drawer.value = false;
  jumpTo(id);
};

const onKey = (event: KeyboardEvent): void => {
  if (event.key === "Escape") {
    closeBubble();
    drawer.value = false;
  }
};

/* ---------- 生命周期 ---------- */

onContentUpdated((reason) => {
  if (reason !== "beforeUnmount") scheduleApply();
});

watch(() => route.path, () => {
  closeBubble();
  bar.show = false;
  filter.value = "all";
});
watch(() => state.owner, scheduleApply);
// 从仓库同步下来新数据时重画
watch(() => state.list, scheduleApply);
watch(() => bubble.id, () => {
  markActive();
  scheduleRelayout();
});
watch(() => bubble.editing, scheduleRelayout);
watch(margin, (on) => {
  document.documentElement.classList.toggle("anno-margin", on);
  // 版心宽度变化后重新对齐
  void nextTick(() => window.setTimeout(relayout, 50));
});

onMounted(async () => {
  coarse.value = matchMedia("(pointer: coarse)").matches;
  const wideQuery = matchMedia(`(min-width: ${MARGIN_MIN_WIDTH}px)`);
  wide.value = wideQuery.matches;
  wideQuery.addEventListener("change", (event) => (wide.value = event.matches));
  cardResize = new ResizeObserver(scheduleRelayout);
  // 图片加载、侧边栏开合都会让正文位置变化
  contentResize = new ResizeObserver(scheduleRelayout);
  contentResize.observe(document.body);
  window.addEventListener("resize", scheduleRelayout);
  window.addEventListener("rd-toc-resize", scheduleRelayout);
  window.addEventListener("scroll", onScroll, { passive: true });
  await initStore();
  mounted.value = true;
  document.addEventListener("selectionchange", onSelectionChange);
  document.addEventListener("click", onDocClick);
  document.addEventListener("keydown", onKey);
  scheduleApply();
});

onBeforeUnmount(() => {
  contentResize?.disconnect();
  cardResize?.disconnect();
  window.removeEventListener("resize", scheduleRelayout);
  window.removeEventListener("rd-toc-resize", scheduleRelayout);
  window.removeEventListener("scroll", onScroll);
  document.documentElement.classList.remove("anno-margin");
  document.removeEventListener("selectionchange", onSelectionChange);
  document.removeEventListener("click", onDocClick);
  document.removeEventListener("keydown", onKey);
});
</script>

<template>
  <div v-if="active" class="anno-ui">
    <!-- 划词工具条 -->
    <Transition name="anno-pop">
      <div
        v-if="bar.show && state.owner"
        class="anno-bar"
        :class="{ below: bar.below }"
        :style="{ left: `${bar.x}px`, top: `${bar.y}px` }"
        @mousedown.prevent
      >
        <button
          v-for="c in COLORS"
          :key="c.id"
          class="anno-dot"
          :class="`anno-c-${c.id}`"
          :title="`高亮：${c.name}`"
          @click="create(c.id, false)"
        >
          <span>{{ c.name }}</span>
        </button>
        <span class="anno-sep" />
        <button class="anno-btn" title="高亮并写批注" @click="create('yellow', true)">
          <svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /></svg>
          批注
        </button>
      </div>
    </Transition>

    <!-- 批注气泡 -->
    <Transition name="anno-pop">
      <div
        v-if="bubbleAnno && !margin"
        :key="bubble.id"
        class="anno-bubble"
        :class="`anno-c-${bubbleAnno.color}`"
        :style="{ left: `${bubble.x}px`, top: `${bubble.y}px` }"
      >
        <div class="anno-bubble-head">
          <template v-if="state.owner">
            <button
              v-for="c in COLORS"
              :key="c.id"
              class="anno-dot small"
              :class="[`anno-c-${c.id}`, { on: c.id === bubbleAnno.color }]"
              :title="c.name"
              @click="recolor(c.id)"
            />
          </template>
          <span class="anno-tag">{{ colorName(bubbleAnno.color) }}</span>
          <span class="anno-grow" />
          <button v-if="state.owner && !bubble.editing" class="anno-link" @click="bubble.editing = true; bubble.draft = bubbleAnno.note">编辑</button>
          <button v-if="state.owner" class="anno-link danger" @click="remove(bubbleAnno.id)">删除</button>
          <button class="anno-x" title="关闭" @click="closeBubble">×</button>
        </div>
        <template v-if="bubble.editing">
          <textarea
            v-model="bubble.draft"
            class="anno-editor"
            rows="4"
            placeholder="写点什么……支持 $公式$，Ctrl+Enter 保存"
            @keydown="onEditorKey"
          />
          <div class="anno-actions">
            <span class="anno-hint">Ctrl+Enter 保存</span>
            <button class="anno-btn ghost" @click="bubble.editing = false">取消</button>
            <button class="anno-btn primary" @click="saveNote">保存</button>
          </div>
        </template>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-else-if="bubbleAnno.note" class="anno-note" v-html="note(bubbleAnno.note)" />
        <div v-else class="anno-note empty">只有高亮，没有写批注</div>
      </div>
    </Transition>

    <!-- 旁注：宽屏时批注卡片排在正文右侧，和高亮对齐，用细线连到原文 -->
    <svg
      v-if="margin && links.length"
      class="anno-links"
      :width="linkBox.w"
      :height="linkBox.h"
      :viewBox="`0 0 ${linkBox.w} ${linkBox.h}`"
      aria-hidden="true"
    >
      <g
        v-for="link in links"
        :key="link.id"
        :class="[`anno-c-${link.color}`, { active: bubble.id === link.id }]"
      >
        <path :d="link.d" />
        <circle :cx="link.x" :cy="link.y" r="2.6" />
      </g>
    </svg>
    <div v-if="margin" class="anno-margin-col">
      <TransitionGroup name="anno-side">
        <article
          v-for="anno in annos"
          v-show="!orphans.has(anno.id)"
          :key="anno.id"
          :ref="(el) => setCardEl(anno.id, el)"
          class="anno-side"
          :class="[`anno-c-${anno.color}`, { active: bubble.id === anno.id, still: still.has(anno.id), gone: gone.has(anno.id), bare: !anno.note && !(bubble.editing && bubble.id === anno.id) }]"
          :style="{
            position: place[anno.id]?.fixed ? 'fixed' : 'absolute',
            top: `${place[anno.id]?.y ?? 0}px`,
            left: `${gutter.left}px`,
            width: `${gutter.width}px`,
          }"
          @click="onCardClick(anno)"
          @mouseenter="marksOf(anno.id).forEach((el) => el.classList.add('anno-hover'))"
          @mouseleave="marksOf(anno.id).forEach((el) => el.classList.remove('anno-hover'))"
        >
          <template v-if="bubble.editing && bubble.id === anno.id">
            <div class="anno-side-head">
              <button
                v-for="c in COLORS"
                :key="c.id"
                class="anno-dot small"
                :class="[`anno-c-${c.id}`, { on: c.id === anno.color }]"
                :title="c.name"
                @click.stop="recolor(c.id)"
              />
              <span class="anno-tag">{{ colorName(anno.color) }}</span>
            </div>
            <textarea
              v-model="bubble.draft"
              class="anno-editor"
              rows="3"
              placeholder="写点什么……支持 $公式$"
              @keydown="onEditorKey"
            />
            <div class="anno-actions">
              <span class="anno-hint">Ctrl+Enter 保存</span>
              <button class="anno-btn ghost" @click.stop="bubble.editing = false">取消</button>
              <button class="anno-btn primary" @click.stop="saveNote">保存</button>
            </div>
          </template>
          <template v-else>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-if="anno.note" class="anno-note" v-html="note(anno.note)" />
            <div class="anno-side-meta">
              <span class="anno-tag">{{ colorName(anno.color) }}</span>
              <span class="anno-grow" />
              <span class="anno-side-tools">
                <span class="anno-time">{{ timeText(anno) }}</span>
                <template v-if="state.owner">
                  <button class="anno-link" @click.stop="startEdit(anno)">{{ anno.note ? "编辑" : "写批注" }}</button>
                  <button class="anno-link danger" @click.stop="remove(anno.id)">删除</button>
                </template>
              </span>
            </div>
          </template>
        </article>
      </TransitionGroup>
    </div>

    <!-- 批注栏开关 -->
    <button
      v-if="state.owner || annos.length"
      class="anno-fab"
      :class="{ open: drawer }"
      :title="drawer ? '收起批注栏' : '打开批注栏'"
      @click="drawer = !drawer"
    >
      <svg viewBox="0 0 24 24" width="20" height="20"><path d="M5 4h14a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-7l-4 3v-3H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 9h8M8 12.5h5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
      <span v-if="annos.length" class="anno-count">{{ annos.length }}</span>
    </button>

    <!-- 批注栏 -->
    <Transition name="anno-fade">
      <div v-if="drawer" class="anno-scrim" @click="drawer = false" />
    </Transition>
    <Transition name="anno-slide">
      <aside v-if="drawer" class="anno-drawer">
        <header class="anno-drawer-head">
          <div>
            <div class="anno-drawer-title">本页批注</div>
            <div class="anno-drawer-sub">{{ page.title }}</div>
          </div>
          <button class="anno-x" title="收起" @click="drawer = false">×</button>
        </header>

        <div class="anno-filters">
          <button :class="{ on: filter === 'all' }" @click="filter = 'all'">全部 {{ annos.length }}</button>
          <button
            v-for="c in COLORS"
            :key="c.id"
            :class="[`anno-c-${c.id}`, { on: filter === c.id }]"
            @click="filter = c.id"
          >
            <i class="anno-swatch" />{{ c.name }}
          </button>
        </div>

        <TransitionGroup tag="ol" name="anno-list" class="anno-list">
          <li
            v-for="(anno, i) in shown"
            :key="anno.id"
            class="anno-card"
            :class="[`anno-c-${anno.color}`, { orphan: orphans.has(anno.id) }]"
            :style="{ '--i': i }"
            @click="onCard(anno.id)"
          >
            <blockquote class="anno-quote">{{ anno.quote }}</blockquote>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-if="anno.note" class="anno-note" v-html="note(anno.note)" />
            <div class="anno-meta">
              <span class="anno-tag">{{ colorName(anno.color) }}</span>
              <span v-if="orphans.has(anno.id)" class="anno-warn">原文已改动，找不到位置</span>
              <span class="anno-grow" />
              <span>{{ timeText(anno) }}</span>
              <button v-if="state.owner" class="anno-link danger" title="删除" @click.stop="remove(anno.id)">删除</button>
            </div>
          </li>
        </TransitionGroup>

        <div v-if="!shown.length" class="anno-empty">
          <template v-if="annos.length">这个颜色下还没有批注。</template>
          <template v-else>
            <svg viewBox="0 0 120 60" width="120" height="60"><path d="M6 44 Q30 8 60 30 T114 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="4 6" /></svg>
            <p>在正文里选中一段文字，<br>就能高亮或写批注。</p>
          </template>
        </div>

        <footer class="anno-drawer-foot">
          <RouteLink to="/review/" class="anno-review-link">全部批注 · 复习 →</RouteLink>
          <div v-if="state.owner" class="anno-tools">
            <button class="anno-link" @click="exportJSON">导出</button>
            <button class="anno-link" @click="fileInput?.click()">导入</button>
            <button class="anno-link" title="关闭后本机不再显示划词工具条" @click="setOwner(false)">退出批注模式</button>
            <input ref="fileInput" type="file" accept="application/json" hidden @change="onImport" />
          </div>
          <div class="anno-store" :class="{ err: state.error }">
            <i class="anno-sync-dot" :class="{ on: state.connected, busy: state.saving }" />
            <span>{{ syncText }}</span>
            <span class="anno-grow" />
            <template v-if="state.owner">
              <button v-if="state.connected" class="anno-link" @click="syncNow">立即同步</button>
              <button v-if="state.connected" class="anno-link" title="只在这台设备上忘掉 token" @click="disconnectGitHub">断开</button>
              <button v-else class="anno-link" @click="linkForm.open = !linkForm.open">连接 GitHub</button>
            </template>
          </div>
          <form v-if="linkForm.open && !state.connected" class="anno-connect" @submit.prevent="connect">
            <p>
              在 GitHub 新建一个
              <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">Fine-grained token</a>：
              仓库只选 Blog_Vuepress，权限 Contents 选 Read and write。token 只保存在这台设备的浏览器里。
            </p>
            <input v-model="linkForm.token" type="password" placeholder="github_pat_…" autocomplete="off" />
            <div class="anno-actions">
              <span class="anno-hint err">{{ linkForm.error }}</span>
              <button type="submit" class="anno-btn primary" :disabled="linkForm.busy">
                {{ linkForm.busy ? "验证中…" : "连接" }}
              </button>
            </div>
          </form>
        </footer>
      </aside>
    </Transition>

    <Transition name="anno-fade">
      <div v-if="toast" class="anno-toast">{{ toast }}</div>
    </Transition>
  </div>
</template>

<style lang="scss">
@use "../annotate/anno.scss";
</style>
