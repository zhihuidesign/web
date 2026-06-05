import requests
import json
import os

# 1. 飞书核心配置（从 GitHub Actions 的 Secrets 环境变量自动读取）
APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
# 从你 data.js 中提取的表格唯一 Token
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def sync():
    if not APP_ID or not APP_SECRET:
        print("【错误】GitHub Actions 运行环境中缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET 配置！")
        return

    print("🚀 正在向飞书服务器申请临时通行证 (tenant_access_token)...")
    token_res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}
    )
    token_data = token_res.json()
    token = token_data.get("tenant_access_token")
    
    if not token:
        print("❌ 获取飞书通行证失败，请检查飞书后台的凭证是否正确！", token_data)
        return

    headers = {"Authorization": f"Bearer {token}"}

    def fetch_table(table_name):
        print(f"📦 正在全量同步飞书多维表格: {table_name}...")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_name}/records?page_size=100"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
        print(f"⚠️ 获取表格 {table_name} 失败，状态码: {res.status_code}")
        return []

    # 同步三大核心基础数据表
    settings_raw = fetch_table("Settings")
    banners_raw = fetch_table("Banners")
    cases_raw = fetch_table("Cases")

    # 2. 智能解析 Settings 表
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = fields.get("键名")
        val = fields.get("内容值")
        if key:
            settings[key] = val

    # 3. 智能解析 Banners 表
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        if fields.get("图片链接"):
            banners.append({
                "id": fields.get("编号", "b-default"),
                "title": fields.get("广告标题", ""),
                "image": fields.get("图片链接")
            })

    # 4. 智能解析 Cases 案例表
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        feishu_category = fields.get("栏目分类", "")
        
        # 兼容飞书可能存在的多选标签/单选文本格式
        if isinstance(feishu_category, list):
            category_str = feishu_category[0].get("text", "") if feishu_category else ""
        else:
            category_str = str(feishu_category)

        category_english = "spatial"
        if "品牌视觉" in category_str:
            category_english = "branding"
        elif "活动视觉" in category_str:
            category_english = "events"

        is_featured = fields.get("是否上首页") in [True, "true", "TRUE", "是"]

        cases.append({
            "id": fields.get("编号", "c-default"),
            "title": fields.get("项目标题", "未命名项目"),
            "category": category_english,
            "tag": fields.get("副标题", ""),
            "desc": fields.get("项目简述", ""),
            "images": fields.get("图片集合", ""),
            "featured": is_featured
        })

    # 打包组合
    master_data = {
        "settings": settings,
        "banners": banners,
        "cases": cases
    }

    # 5. 安全写入本地资产库
    os.makedirs('api', exist_ok=True)
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print("✨ 【大功告成】飞书最新云端数据已全量成功同步至静态资产 api/data.json！")

if __name__ == "__main__":
    sync()
