// 安全占位文件：GitHub Pages 稳定版不依赖 /api/data 动态接口。
// 网站实际读取：./api/data.json
export default function handler(req, res) {
  res.status(200).json({ ok: true, mode: 'github-pages-static', dataFile: './api/data.json' });
}
