// 批注数据：内存中的响应式列表，缓存在本机，填了 token 后同步到 GitHub 仓库
import { reactive } from "vue";

export type AnnoColor = "yellow" | "green" | "blue" | "pink";

export const COLORS: { id: AnnoColor; name: string }[] = [
  { id: "yellow", name: "重点" },
  { id: "green", name: "理解" },
  { id: "blue", name: "公式" },
  { id: "pink", name: "疑问" },
];

export interface Annotation {
  id: string;
  /** 页面路径（已解码，不含 base），如 /post/电机学/第2章-变压器.html */
  page: string;
  pageTitle: string;
  /** 划选的原文，以及前后各一小段上下文，用来在页面里重新定位 */
  quote: string;
  prefix: string;
  suffix: string;
  /** 原文在正文中的字符位置，原文出现多次时用来挑最近的一处 */
  pos: number;
  color: AnnoColor;
  note: string;
  created: number;
  updated: number;
}

// 批注同步到 GitHub 仓库里的一个 JSON 文件；本机 localStorage 做缓存，离线也能用
const REPO = "pkc-www/Blog_Vuepress";
const BRANCH = "main";
const FILE = "annotations/annotations.json";
const API = `https://api.github.com/repos/${REPO}`;

const CACHE_KEY = "anno:v1";
const OWNER_KEY = "anno:owner";
const TOKEN_KEY = "anno:token";
// 删除记录保留 90 天，足够让其他设备同步到
const TOMBSTONE_TTL = 90 * 864e5;

interface Tombstone {
  id: string;
  at: number;
}

interface AnnoFile {
  version: 1;
  annotations: Annotation[];
  deleted: Tombstone[];
}

export const state = reactive({
  list: [] as Annotation[],
  ready: false,
  /** 只有作者模式下才显示划词工具条和编辑入口 */
  owner: false,
  /** 已填 GitHub token，批注会同步到仓库 */
  connected: false,
  saving: false,
  syncedAt: 0,
  error: "",
});

let deleted: Tombstone[] = [];
let remoteSha: string | null = null;
let loading: Promise<void> | null = null;

const storage = {
  get: (key: string): string | null => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set: (key: string, value: string | null): void => {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch {
      // 无痕模式等情况下写不进去，只在本次会话生效
    }
  },
};

const normalize = (data: unknown): AnnoFile => {
  // 兼容最早只存数组的格式
  if (Array.isArray(data)) return { version: 1, annotations: data as Annotation[], deleted: [] };
  const file = (data ?? {}) as Partial<AnnoFile>;
  return { version: 1, annotations: file.annotations ?? [], deleted: file.deleted ?? [] };
};

/** 合并两份数据：同一条取更新时间较新的，删除记录优先于删除之前的修改 */
const merge = (a: AnnoFile, b: AnnoFile): AnnoFile => {
  const now = Date.now();
  const gone = new Map<string, number>();
  for (const t of [...a.deleted, ...b.deleted])
    if (now - t.at < TOMBSTONE_TTL) gone.set(t.id, Math.max(gone.get(t.id) ?? 0, t.at));
  const byId = new Map<string, Annotation>();
  for (const item of [...a.annotations, ...b.annotations]) {
    if (!item?.id || (gone.get(item.id) ?? 0) >= item.updated) continue;
    const old = byId.get(item.id);
    if (!old || old.updated < item.updated) byId.set(item.id, item);
  }
  return {
    version: 1,
    annotations: [...byId.values()],
    deleted: [...gone].map(([id, at]) => ({ id, at })),
  };
};

const snapshot = (): AnnoFile => ({
  version: 1,
  annotations: JSON.parse(JSON.stringify(state.list)) as Annotation[],
  deleted,
});

const adopt = (file: AnnoFile): void => {
  state.list = file.annotations;
  deleted = file.deleted;
  storage.set(CACHE_KEY, JSON.stringify(snapshot()));
};

const sameContent = (a: AnnoFile, b: AnnoFile): boolean =>
  JSON.stringify([a.annotations, a.deleted]) === JSON.stringify([b.annotations, b.deleted]);

/* ---------- GitHub ---------- */

const toBase64 = (text: string): string => {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
};

const fromBase64 = (data: string): string =>
  new TextDecoder().decode(Uint8Array.from(atob(data.replace(/\s/g, "")), (ch) => ch.charCodeAt(0)));

const github = async (token: string, path: string, init: RequestInit = {}): Promise<Response> =>
  fetch(`${API}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  });

const httpError = (res: Response): Error =>
  new Error(
    res.status === 401
      ? "token 无效或已过期"
      : res.status === 403 || res.status === 404
        ? "token 没有这个仓库的读写权限"
        : `GitHub 返回 ${res.status}`,
  );

const pull = async (token: string): Promise<AnnoFile> => {
  const res = await github(token, `/contents/${FILE}?ref=${BRANCH}`);
  if (res.status === 404) {
    remoteSha = null;
    return normalize(null);
  }
  if (!res.ok) throw httpError(res);
  const meta = (await res.json()) as { sha: string; content?: string; encoding?: string };
  remoteSha = meta.sha;
  // 超过 1MB 的文件接口不带内容，改走 raw
  const text =
    meta.encoding === "base64" && meta.content
      ? fromBase64(meta.content)
      : await (
          await github(token, `/contents/${FILE}?ref=${BRANCH}`, {
            headers: { Accept: "application/vnd.github.raw+json" },
          })
        ).text();
  return normalize(JSON.parse(text));
};

const push = async (token: string, file: AnnoFile): Promise<Response> =>
  github(token, `/contents/${FILE}`, {
    method: "PUT",
    body: JSON.stringify({
      // [skip ci]：批注改动不触发博客重新部署
      message: `批注：同步 ${file.annotations.length} 条 [skip ci]`,
      content: toBase64(`${JSON.stringify(file, null, 2)}\n`),
      branch: BRANCH,
      ...(remoteSha ? { sha: remoteSha } : {}),
    }),
  });

/** 拉取远端、与本机合并，有差异就写回仓库；远端被别的设备改过时重试 */
const sync = async (): Promise<void> => {
  const token = storage.get(TOKEN_KEY);
  if (!token) return;
  state.saving = true;
  state.error = "";
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      const remote = await pull(token);
      const merged = merge(snapshot(), remote);
      adopt(merged);
      if (sameContent(merged, remote)) break;
      const res = await push(token, merged);
      if (res.ok) {
        remoteSha = ((await res.json()) as { content: { sha: string } }).content.sha;
        break;
      }
      if (res.status !== 409 && res.status !== 422) throw httpError(res);
    }
    state.syncedAt = Date.now();
  } catch (err) {
    state.error = `同步失败：${(err as Error).message}`;
  } finally {
    state.saving = false;
  }
};

let syncTimer = 0;
const persist = (): void => {
  storage.set(CACHE_KEY, JSON.stringify(snapshot()));
  if (!state.connected) return;
  // 连续操作合并成一次提交
  window.clearTimeout(syncTimer);
  state.saving = true;
  syncTimer = window.setTimeout(() => void sync(), 1500);
};

/** 填入 token：先确认对仓库有写权限，再把本机已有的批注合并上去 */
export const connectGitHub = async (token: string): Promise<void> => {
  const res = await github(token.trim(), "");
  if (!res.ok) throw httpError(res);
  const repo = (await res.json()) as { permissions?: { push?: boolean } };
  if (!repo.permissions?.push) throw new Error("token 没有这个仓库的写入权限");
  storage.set(TOKEN_KEY, token.trim());
  state.connected = true;
  state.owner = true;
  storage.set(OWNER_KEY, "1");
  await sync();
};

export const disconnectGitHub = (): void => {
  storage.set(TOKEN_KEY, null);
  state.connected = false;
};

export const syncNow = (): Promise<void> => sync();

const readOwner = (): boolean => {
  try {
    // 地址栏带 ?anno=on 开启作者模式，?anno=off 关闭，之后记在本机
    const flag = new URLSearchParams(location.search).get("anno");
    if (flag === "on") storage.set(OWNER_KEY, "1");
    if (flag === "off") storage.set(OWNER_KEY, null);
  } catch {
    // 忽略
  }
  return storage.get(OWNER_KEY) === "1";
};

export const initStore = (): Promise<void> => {
  loading ??= (async () => {
    state.connected = Boolean(storage.get(TOKEN_KEY));
    state.owner = readOwner() || state.connected;
    try {
      adopt(normalize(JSON.parse(storage.get(CACHE_KEY) ?? "null")));
    } catch {
      adopt(normalize(null));
    }
    state.ready = true;
    // 先用缓存把页面画出来，再在后台同步
    if (state.connected) void sync();
    // 切回这个标签页时拉一次，拿到其他设备的改动
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && state.connected && !state.saving) void sync();
    });
  })();
  return loading;
};

export const setOwner = (on: boolean): void => {
  state.owner = on;
  storage.set(OWNER_KEY, on ? "1" : null);
};

const newId = (): string =>
  Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

export const addAnno = (
  data: Omit<Annotation, "id" | "created" | "updated">,
): Annotation => {
  const now = Date.now();
  const anno: Annotation = { ...data, id: newId(), created: now, updated: now };
  state.list.push(anno);
  persist();
  return state.list[state.list.length - 1];
};

export const updateAnno = (
  id: string,
  patch: Partial<Pick<Annotation, "note" | "color">>,
): void => {
  const anno = state.list.find((item) => item.id === id);
  if (!anno) return;
  Object.assign(anno, patch, { updated: Date.now() });
  persist();
};

export const removeAnno = (id: string): void => {
  state.list = state.list.filter((item) => item.id !== id);
  deleted = [...deleted, { id, at: Date.now() }];
  persist();
};

export const pageAnnos = (page: string): Annotation[] =>
  state.list.filter((item) => item.page === page);

/** 导出为 JSON 文件（换设备时手动搬运） */
export const exportJSON = (): void => {
  const blob = new Blob([JSON.stringify(state.list, null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `批注-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
};

/** 导入 JSON：和现有批注合并，同一条取更新时间较新的 */
export const importJSON = async (file: File): Promise<number> => {
  const incoming = normalize(JSON.parse(await file.text()));
  const before = new Set(state.list.map((item) => item.id));
  adopt(merge(snapshot(), incoming));
  persist();
  return state.list.filter((item) => !before.has(item.id)).length;
};
