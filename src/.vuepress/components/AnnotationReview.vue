<script setup lang="ts">
// 批注复习页：按课程汇总所有批注，可以遮住批注内容先自己回想
import { computed, onMounted, reactive, ref } from "vue";
import { RouteLink } from "vuepress/client";

import { hasMath, loadKatex, renderNote } from "../annotate/render.js";
import { COLORS, type AnnoColor, type Annotation, initStore, state } from "../annotate/store.js";

const mounted = ref(false);
const mathReady = ref(false);
const filter = ref<AnnoColor | "all">("all");
const onlyNotes = ref(false);
const keyword = ref("");
// 遮挡模式：只露出原文，点一下才显示自己的批注
const quiz = ref(false);
const revealed = reactive(new Set<string>());

const courseOf = (anno: Annotation): string => anno.page.split("/")[2] ?? "其他";

const matched = computed(() => {
  const word = keyword.value.trim().toLowerCase();
  return state.list.filter(
    (anno) =>
      (filter.value === "all" || anno.color === filter.value) &&
      (!onlyNotes.value || anno.note.trim()) &&
      (!word || `${anno.quote}\n${anno.note}`.toLowerCase().includes(word)),
  );
});

// 课程 → 页面 → 批注（页面内按正文顺序）
const groups = computed(() => {
  const courses = new Map<string, Map<string, Annotation[]>>();
  for (const anno of matched.value) {
    const course = courseOf(anno);
    if (!courses.has(course)) courses.set(course, new Map());
    const pages = courses.get(course)!;
    if (!pages.has(anno.page)) pages.set(anno.page, []);
    pages.get(anno.page)!.push(anno);
  }
  return [...courses].map(([course, pages]) => ({
    course,
    count: [...pages.values()].reduce((sum, list) => sum + list.length, 0),
    pages: [...pages]
      .map(([path, list]) => ({
        path,
        title: list[0].pageTitle,
        list: list.sort((a, b) => a.pos - b.pos),
      }))
      .sort((a, b) => a.path.localeCompare(b.path, "zh-CN", { numeric: true })),
  }));
});

const stats = computed(() => ({
  total: state.list.length,
  notes: state.list.filter((anno) => anno.note.trim()).length,
  pages: new Set(state.list.map((anno) => anno.page)).size,
}));

const note = (text: string): string => {
  void mathReady.value;
  return renderNote(text);
};

const toggle = (id: string): void => {
  if (revealed.has(id)) revealed.delete(id);
  else revealed.add(id);
};

const setQuiz = (on: boolean): void => {
  quiz.value = on;
  revealed.clear();
};

onMounted(async () => {
  await initStore();
  mounted.value = true;
  if (state.list.some((anno) => hasMath(anno.note))) {
    await loadKatex();
    mathReady.value = true;
  }
});
</script>

<template>
  <div class="anno-review anno-ui">
    <header class="ar-hero">
      <p class="ar-kicker">REVIEW</p>
      <h1>批注复习</h1>
      <p class="ar-lead">把读笔记时划下的重点和写下的想法集中在一起，按课程过一遍。</p>
      <div v-if="mounted" class="ar-stats">
        <div><b>{{ stats.total }}</b><span>条高亮</span></div>
        <div><b>{{ stats.notes }}</b><span>条批注</span></div>
        <div><b>{{ stats.pages }}</b><span>篇笔记</span></div>
      </div>
    </header>

    <template v-if="mounted">
      <div v-if="!stats.total" class="ar-empty">
        <p v-if="state.owner">还没有批注。打开任意一篇课程笔记，选中文字就能高亮或写批注。</p>
        <p v-else>这里是作者自己的复习页，需要登录作者的 GitHub 才能看到批注。</p>
        <RouteLink to="/post/" class="ar-go">去博文大全 →</RouteLink>
      </div>

      <template v-else>
        <div class="ar-toolbar">
          <div class="ar-chips">
            <button :class="{ on: filter === 'all' }" @click="filter = 'all'">全部</button>
            <button
              v-for="c in COLORS"
              :key="c.id"
              :class="[`anno-c-${c.id}`, { on: filter === c.id }]"
              @click="filter = c.id"
            >
              <i class="anno-swatch" />{{ c.name }}
            </button>
          </div>
          <label class="ar-check"><input v-model="onlyNotes" type="checkbox" />只看写了批注的</label>
          <label class="ar-check"><input :checked="quiz" type="checkbox" @change="setQuiz(($event.target as HTMLInputElement).checked)" />遮住批注自测</label>
          <input v-model="keyword" class="ar-search" type="search" placeholder="搜索原文或批注" />
        </div>

        <section v-for="(group, gi) in groups" :key="group.course" class="ar-course" :style="{ '--i': gi }">
          <h2>
            {{ group.course }}
            <small>{{ group.count }}</small>
          </h2>
          <div v-for="pg in group.pages" :key="pg.path" class="ar-page">
            <RouteLink :to="pg.path" class="ar-page-title">{{ pg.title }}</RouteLink>
            <ul>
              <li
                v-for="anno in pg.list"
                :key="anno.id"
                class="ar-item"
                :class="`anno-c-${anno.color}`"
              >
                <RouteLink class="ar-quote" :to="`${anno.page}#anno-${anno.id}`" title="回到原文">
                  <mark>{{ anno.quote }}</mark>
                </RouteLink>
                <template v-if="anno.note">
                  <button
                    v-if="quiz && !revealed.has(anno.id)"
                    class="ar-cover"
                    @click="toggle(anno.id)"
                  >
                    想一想，再点开看批注
                  </button>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-else class="anno-note ar-note" v-html="note(anno.note)" @click="quiz && toggle(anno.id)" />
                </template>
              </li>
            </ul>
          </div>
        </section>

        <p v-if="!groups.length" class="ar-empty">没有符合条件的批注。</p>
      </template>
    </template>
  </div>
</template>

<style lang="scss">
@use "../annotate/review.scss";
</style>
