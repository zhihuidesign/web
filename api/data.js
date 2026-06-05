export default async function handler(req, res) {
  // ⚠️ 核心配置区：在这里替换为你刚才在第二步拿到的飞书钥匙！
  const FEISHU_APP_ID = "cli_aaa8876d4fb95bd8";
  const FEISHU_APP_SECRET = "uaVTQdj59AXdtjMwng1aNf0nvUuBYzOc";
  const FEISHU_APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf";

  try {
    // 1. 获取飞书的临时通行证
    const tokenRes = await fetch("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ "app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET })
    });
    const tokenData = await tokenRes.json();
    const token = tokenData.tenant_access_token;

    // 2. 如果是有人提交表单（POST请求），自动写入纯中文表头的 CoCreate 表
    if (req.method === 'POST') {
      let body = req.body;
      if (typeof body === 'string') {
        body = Object.fromEntries(new URLSearchParams(body));
      }
      await fetch(`https://open.feishu.cn/open-apis/bitable/v1/apps/${FEISHU_APP_TOKEN}/tables/CoCreate/records`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ fields: { "称呼": body.name, "联系方式": body.contact, "共创想法": body.message } })
      });
      return res.status(200).send("SUCCESS");
    }

    // 3. 如果是打开网页（GET请求），读取纯中文表头并智能打包输出
    const fetchTable = async (tableName) => {
      const r = await fetch(`https://open.feishu.cn/open-apis/bitable/v1/apps/${FEISHU_APP_TOKEN}/tables/${tableName}/records?page_size=100`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const d = await r.json();
      return d.data?.items || [];
    };

    const [settingsRaw, bannersRaw, casesRaw] = await Promise.all([
      fetchTable("Settings"), fetchTable("Banners"), fetchTable("Cases")
    ]);

    // 智能解析 Settings (纯中文表头：键名、内容值)
    const settings = {};
    settingsRaw.forEach(item => { 
      const key = item.fields["键名"];
      const val = item.fields["内容值"];
      if(key) settings[key] = val; 
    });

    // 智能解析 Banners (纯中文表头：编号、广告标题、图片链接)
    const banners = bannersRaw.map(item => ({
      id: item.fields["编号"], 
      title: item.fields["广告标题"], 
      image: item.fields["图片链接"]
    }));

    // 智能解析 Cases (纯中文表头：编号、项目标题、栏目分类、副标题、项目简述、图片集合、是否上首页)
    const cases = casesRaw.map(item => {
      let categoryEnglish = "spatial";
      const feishuCategory = item.fields["栏目分类"] || "";
      const categoryStr = Array.isArray(feishuCategory) ? feishuCategory[0]?.text : String(feishuCategory);
      
      if (categoryStr.includes("品牌视觉")) categoryEnglish = "branding";
      if (categoryStr.includes("活动视觉")) categoryEnglish = "events";

      const isFeatured = item.fields["是否上首页"] === true || String(item.fields["是否上首页"]).toUpperCase() === "TRUE";

      return {
        id: item.fields["编号"],
        title: item.fields["项目标题"],
        category: categoryEnglish,
        tag: item.fields["副标题"],
        desc: item.fields["项目简述"],
        images: item.fields["图片集合"] || "",
        featured: isFeatured
      };
    });

    return res.status(200).json({ settings, banners, cases });

  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}