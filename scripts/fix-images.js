import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const postsDir = path.join(__dirname, '../src/post');

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let originalContent = content;

  // 1. 处理 Markdown 语法图片: ![alt](url)
  // 正则解析：查找非空行前后的图片语句，确保前后都有空行
  // 这里采用更通用的正则匹配 ![...] (...)
  const mdImageRegex = /([^\n])\s*(!\[.*?\]\(.*?\))/g;
  content = content.replace(mdImageRegex, '$1\n\n$2');
  
  const mdImageAfterRegex = /(!\[.*?\]\(.*?\))\s*([^\n\s])/g;
  content = content.replace(mdImageAfterRegex, '$1\n\n$2');

  // 2. 处理 HTML 语法图片: <img ...>
  const htmlImageRegex = /([^\n])\s*(<img\s+.*?>)/g;
  content = content.replace(htmlImageRegex, '$1\n\n$2');
  
  const htmlImageAfterRegex = /(<img\s+.*?>)\s*([^\n\s])/g;
  content = content.replace(htmlImageAfterRegex, '$1\n\n$2');

  // 3. 清理可能产生的多余空行（将 3 个或更多换行符缩减为 2 个）
  content = content.replace(/\n{3,}/g, '\n\n');

  if (content !== originalContent) {
    fs.writeFileSync(filePath, content);
    return true;
  }
  return false;
}

function walkDir(dir) {
  let count = 0;
  const files = fs.readdirSync(dir);
  files.forEach(file => {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      count += walkDir(filePath);
    } else if (file.endsWith('.md')) {
      if (processFile(filePath)) {
        count++;
      }
    }
  });
  return count;
}

if (fs.existsSync(postsDir)) {
  const processedCount = walkDir(postsDir);
  console.log(`处理完成！共修复了 ${processedCount} 个文件的图片换行问题。`);
} else {
  console.error(`目录不存在: ${postsDir}`);
}
