// 批注正文渲染：纯文本 + 换行 + $公式$，KaTeX 只在批注里有公式时才加载

// 转义并把换行变成 <br>（只处理普通文字，KaTeX 输出里的换行不能动）
const escape = (text: string): string =>
  text.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`).replace(/\n/g, "<br>");

type Katex = typeof import("katex").default;
let katex: Katex | null = null;

const MATH = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;

export const hasMath = (text: string): boolean => /\$[^$]+\$/.test(text);

export const loadKatex = async (): Promise<void> => {
  katex ??= (await import("katex")).default;
};

export const renderNote = (text: string): string => {
  let html = "";
  let last = 0;
  for (const match of text.matchAll(MATH)) {
    html += escape(text.slice(last, match.index));
    const tex = match[1] ?? match[2];
    html += katex
      ? katex.renderToString(tex, { displayMode: Boolean(match[1]), throwOnError: false })
      : `<code>${escape(match[0])}</code>`;
    last = match.index! + match[0].length;
  }
  html += escape(text.slice(last));
  return html;
};
