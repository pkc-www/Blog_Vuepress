import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const postsDir = path.join(__dirname, '../src/post');

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function processDirectory(dir) {
  let count = 0;
  const files = fs.readdirSync(dir);

  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stats = fs.statSync(filePath);

    if (stats.isDirectory()) {
      count += processDirectory(filePath);
    } else if (file.endsWith('.md')) {
      const content = fs.readFileSync(filePath, 'utf8');
      
      // Check for existing frontmatter
      if (!content.trim().startsWith('---')) {
        const title = path.basename(file, '.md');
        const date = formatDate(stats.birthtime);
        
        // Determine category: parent folder name
        const parentDirName = path.basename(dir);
        const category = parentDirName === 'post' ? '随笔' : parentDirName;

        const frontmatter = `---
title: ${title}
date: ${date}
category: ${category}
---

`;
        fs.writeFileSync(filePath, frontmatter + content);
        count++;
      }
    }
  });

  return count;
}

if (fs.existsSync(postsDir)) {
  const totalProcessed = processDirectory(postsDir);
  console.log(`处理完成！共为 ${totalProcessed} 个文件添加了 frontmatter。`);
} else {
  console.error(`目录不存在: ${postsDir}`);
}
