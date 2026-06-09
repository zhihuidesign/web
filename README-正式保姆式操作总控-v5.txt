知汇文化网站 GitHub Pages 低维护最终版 v5

本版总策略：
1. 当前网站按 GitHub Pages 静态网站维护，不要求配置 Vercel。
2. 平时你只维护飞书多维表格，网站通过 GitHub Actions 自动同步 api/data.json。
3. 顶部案例菜单确定为 4 个：空间场景、品牌视觉、活动展览、数字内容。
4. 飞书 Cases 表可以设置 5 个栏目分类：空间场景、品牌视觉、活动展览、数字触点、实验室。
5. 数字触点 + 实验室 会统一显示在前端“数字内容”菜单里，避免导航过长，也避免把未大力推广的实验业务放得太重。
6. 工作首页底部新增“提交项目需求”按钮，默认打开飞书表单。可在 Settings 表里通过 lead_form_url 修改。

文件放置位置：
index.html                              放仓库根目录
sync.py                                 放仓库根目录
data.js                                 放仓库根目录，用安全占位文件覆盖旧文件
api/data.json                           放 api 文件夹
api/data.js                             放 api 文件夹，用安全占位文件覆盖旧文件
.github/workflows/feishu_sync.yml       放 .github/workflows 文件夹

必须先做的安全动作：
1. 撤销旧 GitHub Token。
2. 重置飞书 App Secret。
3. GitHub Secrets 添加 FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_APP_TOKEN。
4. 以后不要把 token、secret、App Secret 发给任何人，也不要放进代码文件。

GitHub Secrets 路径：
GitHub 仓库 zhihuidesign/web
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret

需要新增 3 个：
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_APP_TOKEN

飞书 Cases 表建议修改：
1. 栏目分类设置为单选，选项为：
   空间场景
   品牌视觉
   活动展览
   数字触点
   实验室

2. 新增字段：
   字段名：媒体集合
   字段类型：多行文本 / 长文本 / 文本
   填写方式：一个链接一行

3. 不删除旧字段“图片集合”。
   新代码读取顺序：封面链接 → 媒体集合 → 图片集合 → 图片链接。

飞书 Settings 表建议新增：
键名：lead_form_url
内容值：你的飞书项目需求表单链接

如果 lead_form_url 不填，首页“提交项目需求”按钮会自动使用 cocreate_form_url。

飞书表单建议字段：
姓名 / 称呼
手机 / 电话
微信
公司 / 品牌名称
项目类型：空间场景、品牌视觉、活动展览、数字触点、实验室、其他
项目背景
需要服务的具体内容
预算区间
期望启动时间
是否已有资料或链接

第一次上线步骤：
1. 下载 v5 ZIP 并解压。
2. 上传覆盖 GitHub 仓库根目录：index.html、sync.py、data.js。
3. 上传覆盖 GitHub 仓库 api 文件夹：data.json、data.js。
4. 上传覆盖 .github/workflows/feishu_sync.yml。
5. GitHub → Settings → Pages → Source 选择 GitHub Actions。
6. GitHub → Actions → Sync Feishu Data and Deploy GitHub Pages → Run workflow。
7. 等待 2-5 分钟，看到绿色成功。
8. 打开 https://zhihuidesign.github.io/web/api/data.json 检查数据。
9. 打开 https://zhihuidesign.github.io/web/ 检查电脑端和手机端。

以后日常上传案例：
1. 打开飞书 Cases 表。
2. 新增一行。
3. 编号填 03、04、05……不要重复。
4. 项目标题填客户能看懂的案例名。
5. 栏目分类从五个选项里选。
6. 副标题填短标签。
7. 项目简述填 1-3 句话。
8. 媒体集合：一个链接一行，第一行是封面图或封面视频。
9. 想上首页就勾选“是否上首页”。
10. 等 GitHub Actions 每小时自动同步；着急就手动 Run workflow。
