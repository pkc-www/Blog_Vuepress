import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const postsDir = path.join(__dirname, '../src/post');

// 需要处理的 SVG 文件名列表
const svgFiles = ['受控源.svg', '受控源实际.svg', '绘图1.svg'];

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let originalContent = content;

  svgFiles.forEach(svg => {
    // 匹配 Markdown 语法 ![alt](.../xxx.svg) 或 ![alt](xxx.svg)
    // 以及 HTML 语法 <img src=".../xxx.svg">
    const mdRegex = new RegExp(`!\\[(.*?)\\]\\(.*?${svg.replace('.', '\\.')}\\)`, 'g');
    const htmlRegex = new RegExp(`<img\\s+(.*?)src=["'].*?${svg.replace('.', '\\.')}["'](.*?)>`, 'g');

    content = content.replace(mdRegex, `![$1](/images/${svg})`);
    content = content.replace(htmlRegex, `<img $1src="/images/${svg}"$2>`);
  });

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
  console.log(`处理完成！共修改了 ${processedCount} 个文件的 SVG 引用路径。`);
} else {
  console.error(`目录不存在: ${postsDir}`);
}
