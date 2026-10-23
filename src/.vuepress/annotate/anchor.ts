// 文本定位：把划选范围记成「原文 + 上下文」，页面重新渲染后再找回来并包上 <mark>
import type { AnnoColor, Annotation } from "./store.js";

interface Piece {
  node: Text;
  start: number;
  end: number;
}

export interface TextIndex {
  text: string;
  pieces: Piece[];
}

const CONTEXT = 32;

// KaTeX 的 MathML 部分和可见部分文字重复，只取可见部分；批注界面自身也跳过
const SKIP = ".katex-mathml, .anno-ui, script, style, .header-anchor";

export const buildIndex = (root: Element): TextIndex => {
  const pieces: Piece[] = [];
  let text = "";
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) =>
      node.parentElement?.closest(SKIP)
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT,
  });
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const value = (node as Text).data;
    pieces.push({ node: node as Text, start: text.length, end: text.length + value.length });
    text += value;
  }
  return { text, pieces };
};

const pointToOffset = (index: TextIndex, container: Node, offset: number): number => {
  if (container.nodeType === Node.TEXT_NODE) {
    const piece = index.pieces.find((item) => item.node === container);
    if (piece) return piece.start + offset;
  }
  // 落在元素上（或被跳过的文字里）：取该点之后的第一段文字
  const point = document.createRange();
  point.setStart(container, offset);
  for (const piece of index.pieces)
    if (point.comparePoint(piece.node, piece.node.length) > 0) {
      return point.comparePoint(piece.node, 0) >= 0 ? piece.start : piece.end;
    }
  return index.text.length;
};

/** 把当前选区描述成可保存的定位信息；选区不在正文里时返回 null */
export const describeRange = (
  root: Element,
  range: Range,
): Pick<Annotation, "quote" | "prefix" | "suffix" | "pos"> | null => {
  if (!root.contains(range.commonAncestorContainer)) return null;
  const index = buildIndex(root);
  let start = pointToOffset(index, range.startContainer, range.startOffset);
  let end = pointToOffset(index, range.endContainer, range.endOffset);
  // 去掉首尾空白
  while (start < end && /\s/.test(index.text[start])) start++;
  while (end > start && /\s/.test(index.text[end - 1])) end--;
  if (end <= start) return null;
  return {
    quote: index.text.slice(start, end),
    prefix: index.text.slice(Math.max(0, start - CONTEXT), start),
    suffix: index.text.slice(end, end + CONTEXT),
    pos: start,
  };
};

const commonTail = (a: string, b: string): number => {
  let n = 0;
  while (n < a.length && n < b.length && a[a.length - 1 - n] === b[b.length - 1 - n]) n++;
  return n;
};

const commonHead = (a: string, b: string): number => {
  let n = 0;
  while (n < a.length && n < b.length && a[n] === b[n]) n++;
  return n;
};

/** 在正文中找回批注对应的位置：原文多次出现时，按上下文吻合度和原位置挑一处 */
export const locate = (index: TextIndex, anno: Annotation): [number, number] | null => {
  let best = -1;
  let bestScore = -Infinity;
  for (let at = index.text.indexOf(anno.quote); at !== -1; at = index.text.indexOf(anno.quote, at + 1)) {
    const before = index.text.slice(Math.max(0, at - CONTEXT), at);
    const after = index.text.slice(at + anno.quote.length, at + anno.quote.length + CONTEXT);
    const score =
      commonTail(before, anno.prefix) + commonHead(after, anno.suffix) - Math.abs(at - anno.pos) / 1000;
    if (score > bestScore) {
      bestScore = score;
      best = at;
    }
  }
  return best === -1 ? null : [best, best + anno.quote.length];
};

/** 给 [start, end) 范围内的文字包上高亮；公式整体加类名，不拆 KaTeX 内部结构 */
export const wrapRange = (
  index: TextIndex,
  start: number,
  end: number,
  anno: { id: string; color: AnnoColor; note: string },
): HTMLElement[] => {
  const marks: HTMLElement[] = [];
  const cls = `anno-hl anno-c-${anno.color}${anno.note.trim() ? " has-note" : ""}`;
  for (const piece of index.pieces) {
    if (piece.end <= start || piece.start >= end) continue;
    // 行内公式整体加类名；独立公式块只标可见部分，避免整行色带
    const math = piece.node.parentElement?.closest<HTMLElement>(".katex-display .katex-html, .katex");
    if (math) {
      if (!math.classList.contains("anno-hl")) {
        math.className += ` ${cls} anno-math`;
        math.dataset.annoId = anno.id;
        marks.push(math);
      }
      continue;
    }
    let node = piece.node;
    const from = Math.max(start, piece.start) - piece.start;
    const to = Math.min(end, piece.end) - piece.start;
    if (!node.data.slice(from, to).trim()) continue;
    if (from > 0) node = node.splitText(from);
    if (to - from < node.length) node.splitText(to - from);
    const mark = document.createElement("mark");
    mark.className = cls;
    mark.dataset.annoId = anno.id;
    node.parentNode!.insertBefore(mark, node);
    mark.appendChild(node);
    marks.push(mark);
  }
  // 最后一段打上标记，用来显示「有批注」的小圆点
  marks.at(-1)?.classList.add("anno-tail");
  return marks;
};

/** 去掉所有高亮，恢复原来的文字节点 */
export const unwrapAll = (root: Element): void => {
  root.querySelectorAll<HTMLElement>("mark.anno-hl").forEach((mark) => {
    const parent = mark.parentNode!;
    while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
    parent.removeChild(mark);
    parent.normalize();
  });
  root.querySelectorAll<HTMLElement>(".anno-hl:not(mark)").forEach((math) => {
    math.className = math.className.replace(/\s*(anno-[\w-]+|has-note)/g, "");
    for (const name of MATH_VARS) math.style.removeProperty(name);
    delete math.dataset.annoId;
  });
};

const MATH_VARS = ["--hl-y", "--hl-h", "--hl-fy", "--hl-fh"];

/**
 * 行内公式的盒子比文字高（分式、上下标），按百分比画色带会和同一行文字对不齐。
 * 在公式前临时插一个空的 <mark> 量出这一行文字的位置，让公式的色带用同样的高度和位置。
 */
export const alignMathBands = (root: Element): void => {
  root.querySelectorAll<HTMLElement>(".katex.anno-hl").forEach((math) => {
    if (math.closest(".katex-display")) return;
    const box = math.getBoundingClientRect();
    const middle = (box.top + box.bottom) / 2;
    // 公式前后各放一个探针：公式刚好在行首时，前面的探针会落在上一行，取和公式同一行的那个
    let text: DOMRect | null = null;
    for (const after of [false, true]) {
      const probe = document.createElement("mark");
      probe.className = "anno-probe";
      probe.textContent = "\u200b";
      math.parentNode!.insertBefore(probe, after ? math.nextSibling : math);
      const rect = probe.getBoundingClientRect();
      probe.remove();
      if (rect.height && rect.top <= middle && rect.bottom >= middle) {
        text = rect;
        break;
      }
    }
    if (!text) return;
    const top = text.top - box.top;
    // 与文字高亮一致：background-size 52%、background-position 92%
    math.style.setProperty("--hl-y", `${top + text.height * 0.48 * 0.92}px`);
    math.style.setProperty("--hl-h", `${text.height * 0.52}px`);
    math.style.setProperty("--hl-fy", `${top}px`);
    math.style.setProperty("--hl-fh", `${text.height}px`);
  });
};
