import requests
import json
import os

# 1. 飞书核心配置（从 GitHub Actions 的 Secrets 环境变量自动读取）
APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
# 多维表格的 App Token
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

# ==================== 🛑 小白配置核心区 🛑 ====================
# 💡 请看下方的【配置指南】，换成你飞书里每一张子表真正以 tbl 开头的 ID！
SETTINGS_TABLE_ID = "换成你Settings表的tbl开头的ID" 
BANNERS_TABLE_ID = "换成你Banners表的tbl开头的ID"
CASES_TABLE_ID = "换成你Cases表的tbl开头的ID"
# =============================================================

def parse_text_field(field_val):
    """【万能文本清洗器】自动兼容飞书的普通文本、单选/多选标签、富文本"""
    if field_val is None:
        return ""
    if isinstance(field_val, dict):
        return str(field_val.get("text") or field_val.get("name") or "")
    if isinstance(field_val, list):
        texts = []
        for item in field_val:
            if isinstance(item, dict):
                texts.append(str(item.get("text") or item.get("name") or ""))
            else:
                texts.append(str(item))
        return ",".join(texts)
    return str(field_val)

def parse_image_field(field_val, single=False):
    """【万能图片清洗器】自动兼容文本链接与直接上传的飞书附件图片"""
    if not field_val:
        return ""
    if isinstance(field_val, list):
        urls = []
        for item in field_val:
            if isinstance(item, dict) and "url" in item:
                urls.append(item["url"])
            elif isinstance(item, str):
                urls.append(item)
        if single:
            return urls[0] if urls else ""
        return ",".join(urls)
    return str(field_val)

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

    def fetch_table(table_id, table_name_debug):
        if "换成你" in table_id or not table_id.startswith("tbl"):
            print(f"❌ 【配置错误】你还没有把 {table_name_debug} 表的 ID 换成以 tbl 开头的真实ID！")
            return []
            
        print(f"📦 正在全量同步飞书多维表格: {table_name_debug} (ID: {table_id})...")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records?page_size=100"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
        
        print(f"⚠️ 获取表格 {table_name_debug} 失败，状态码: {res.status_code}")
        if res.status_code in [400, 404]:
            print(f"👉 提示：很可能是因为你填写的 Table ID '{table_id}' 在飞书云端不存在，请重新核对浏览器地址栏！")
        return []

    # 同步三大核心基础数据表
    settings_raw = fetch_table(SETTINGS_TABLE_ID, "Settings")
    banners_raw = fetch_table(BANNERS_TABLE_ID, "Banners")
    cases_raw = fetch_table(CASES_TABLE_ID, "Cases")

    if not settings_raw and not banners_raw and not cases_raw:
        print("🛑 【严重警告】未成功拉取到任何有效数据，放弃写入，防止意外覆盖本地资产！")
        return

    # 2. 智能解析 Settings 表
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = parse_text_field(fields.get("键名"))
        val = parse_text_field(fields.get("内容值"))
        if key:
            settings[key] = val

    # 3. 智能解析 Banners 表
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        # 兼容列名：既可以叫“图片链接”，也可以直接叫“图片”
        img_val = fields.get("图片链接") or fields.get("图片")
        img_url = parse_image_field(img_val, single=True)
        
        if img_url:
            banners.append({
                "id": parse_text_field(fields.get("编号", "b-default")),
                "title": parse_text_field(fields.get("广告标题", "")),
                "image": img_url
            })

    # 4. 智能解析 Cases 案例表
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        category_str = parse_text_field(fields.get("栏目分类", ""))
        
        # 英文路由映射归类
        category_english = "spatial"
        if "品牌视觉" in category_str:
            category_english = "branding"
        elif "活动视觉" in category_str:
            category_english = "events"

        # 兼容各种花式输入的“是否上首页”
        is_featured_raw = fields.get("是否上首页")
        is_featured_str = parse_text_field(is_featured_raw).strip().lower()
        is_featured = is_featured_str in ["true", "1", "是", "yes", "checked"] or is_featured_raw is True

        cases.append({
            "id": parse_text_field(fields.get("编号", "c-default")),
            "title": parse_text_field(fields.get("项目标题", "未命名项目")),
            "category": category_english,
            "tag": parse_text_field(fields.get("副标题", "")),
            "desc": parse_text_field(fields.get("项目简述", "")),
            "images": parse_image_field(fields.get("图片集合") or fields.get("图片")),
            "featured": is_featured
        })

    # 打包组合
    master_data = {
        "settings": settings,
        "banners": banners,
        "cases": cases
    }

    # 5. 安全写入本地静态文件
    os.makedirs('api', exist_ok=True)
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"✨ 【大功告成】飞书云端数据（成功同步了 {len(banners)} 个广告图，{len(cases)} 个案例）已全量写入静态资产 api/data.json！")

if __name__ == "__main__":
    sync()
