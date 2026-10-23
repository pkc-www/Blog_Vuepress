import type { App, Page, Plugin } from "vuepress/core";

// 构建时汇总 src/post/<课程>/ 下的笔记，生成 @temp/post-index.js 供总览页 <PostIndex /> 使用

// 这些标签太泛，不作为课程分类显示
const GENERIC_TAGS = ["课程笔记", "习题", "中英双语", "英文"];

// 课程辅助色的色相（oklch 的 h），按课程顺序依次分配；README frontmatter 里写 hue 可单独指定
const HUES = [250, 185, 300, 65, 25, 150, 340, 275, 210];

const toDate = (value: unknown): string | null => {
  if (!value) return null;
  const date = new Date(value as string);
  return Number.isNaN(date.getTime()) ? null : date.toISOString().slice(0, 10);
};

// README 正文第一段作为课程简介
const firstParagraph = (content: string): string =>
  content
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !/^[#<\-*>|!\[]/.test(line)) ?? "";

// “第2章 连续时间系统的时域分析” → { no: "2", name: "连续时间系统的时域分析" }
const splitTitle = (title: string): { no: string | null; name: string } => {
  const match = title.match(/^第\s*([\d\-–]+)\s*[章讲节]\s*/);
  const name = match ? title.slice(match[0].length) : title;
  // 中英并列的标题只保留中文部分，如“变压器 Transformers” → “变压器”
  const short = name.match(/^(.*[\u4e00-\u9fa5）)])\s+[A-Za-z][\w\s,&-]*$/)?.[1] ?? name;
  return { no: match ? match[1] : null, name: short };
};

const buildIndex = (pages: Page[]) => {
  const courses = new Map<string, any>();
  const getCourse = (dir: string) => {
    if (!courses.has(dir))
      courses.set(dir, { title: dir, path: `/post/${dir}/`, desc: "", order: 99, chapters: [] });
    return courses.get(dir);
  };

  for (const page of pages) {
    const match = decodeURI(page.path).match(/^\/post\/([^/]+)\/(.*)$/);
    if (!match) continue;
    const [, dir, rest] = match;
    const course = getCourse(dir);
    const fm = page.frontmatter as Record<string, any>;

    if (rest === "") {
      course.title = page.title || dir;
      course.path = page.path;
      course.order = fm.dir?.order ?? 99;
      course.desc = firstParagraph(page.content) || fm.description || "";
      course.hue = fm.hue ?? null;
    } else {
      course.chapters.push({
        ...splitTitle(page.title),
        title: page.title,
        path: page.path,
        desc: fm.description ?? "",
        order: fm.order ?? 99,
        date: toDate(fm.date),
        tags: fm.tag ?? [],
        words: (page.data as any).readingTime?.words ?? 0,
      });
    }
  }

  return [...courses.values()]
    .map((course) => {
      const chapters = course.chapters.sort(
        (a: any, b: any) => a.order - b.order || a.title.localeCompare(b.title, "zh"),
      );
      const tags = chapters.flatMap((c: any) => c.tags);
      return {
        ...course,
        chapters: chapters.map(({ tags: _, ...c }: any) => c),
        tag: tags.find((t: string) => !GENERIC_TAGS.includes(t)) ?? null,
        words: chapters.reduce((sum: number, c: any) => sum + c.words, 0),
        updated: chapters.map((c: any) => c.date).filter(Boolean).sort().pop() ?? null,
      };
    })
    .sort((a, b) => a.order - b.order)
    .map((course, index) => ({ ...course, hue: course.hue ?? HUES[index % HUES.length] }));
};

export const postIndexPlugin = (): Plugin => ({
  name: "post-index",
  onPrepared: async (app: App) => {
    await app.writeTemp(
      "post-index.js",
      `export default ${JSON.stringify(buildIndex(app.pages))};\n`,
    );
  },
});
