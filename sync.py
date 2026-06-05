import requests
import json
import os
import re

# 1. 飞书核心配置（从 GitHub Actions 的 Secrets 环境变量自动读取）
APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
# 从你 data.js 中提取的表格唯一 Token
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def parse_text(field_val):
    """【万能文本清洗器】确保无论飞书返回什么奇葩格式都能安全转成纯文本"""
    if field_val is None:
        return ""
    if isinstance(field_val, list):
        parts = []
        for item in field_val:
            if isinstance(item, dict):
                parts.append(item.get("text", "") or item.get("name", ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    if isinstance(field_val, dict):
        return field_val.get("text", "") or field_val.get("name", "")
    return str(field_val)

def parse_images(field_val):
    """【智能图片链接提取器】完美兼容直接上传的飞书附件文件与手贴的网址文本"""
    if not field_val:
        return []
    # 情况 A：如果直接在表格里上传了“图片附件”
    if isinstance(field_val, list):
        urls = []
        for item in field_val:
            if isinstance(item, dict):
                if "url" in item:
                    urls.append(item["url"])
                elif "text" in item:
                    found = re.findall(r'https?://[^\s,;|]+', item["text"])
                    urls.extend(found)
            else:
                found = re.findall(r'https?://[^\s,;|]+', str(item))
                urls.extend(found)
        return urls
    
    # 情况 B：如果是手贴的纯文本网址
    text = parse_text(field_val)
    return re.findall(r'https?://[^\s,;|]+', text)

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

    # ⭐【核心升级】全量获取飞书多维表格的子表名册，自动翻译出内部真正的 tbl... ID
    print("📋 正在全量获取飞书多维表格的子表名册...")
    tables_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
    tables_res = requests.get(tables_url, headers=headers)
    
    if tables_res.status_code != 200:
        print(f"❌ 无法连接飞书子表接口，状态码: {tables_res.status_code}")
        return
        
    tables_data = tables_res.json()
    if tables_data.get("code") != 0:
        print(f"❌ 飞书接口返回错误: {tables_data.get('msg')}")
        return
        
    items = tables_data.get("data", {}).get("items", [])
    name_to_id = {item.get("name"): item.get("table_id") for item in items if item.get("name")}
    print(f"🔍 成功识别到飞书云端子表映射: {name_to_id}")

    # 智能不区分大小写的容错匹配器
    def find_table_id(target_name):
        for name, tid in name_to_id.items():
            if name.strip().lower() == target_name.lower():
                return tid
        return None

    settings_id = find_table_id("Settings")
    banners_id = find_table_id("Banners")
    cases_id = find_table_id("Cases")

    # 根据翻译出来的真实 ID 抓取数据
    def fetch_table_records(table_id, table_display_name):
        if not table_id:
            print(f"⚠️ 【警告】在飞书里未找到名为 '{table_display_name}' 的子表，请检查子表名字是否一致！")
            return []
        print(f"📦 正在通过真实内部 ID [{table_id}] 抓取子表 [{table_display_name}] 的数据...")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records?page_size=100"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            if res_json.get("code") == 0:
                return res_json.get("data", {}).get("items", [])
            else:
                print(f"⚠️ 飞书返回数据错误 ({table_display_name}): {res_json.get('msg')}")
        print(f"⚠️ 获取表格 {table_display_name} 失败，状态码: {res.status_code}")
        return []

    # 全量拉取三大表格数据
    settings_raw = fetch_table_records(settings_id, "Settings")
    banners_raw = fetch_table_records(banners_id, "Banners")
    cases_raw = fetch_table_records(cases_id, "Cases")

    # 2. 智能解析 Settings 表
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = parse_text(fields.get("键名")).strip()
        val = parse_text(fields.get("内容值")).strip()
        if key:
            settings[key] = val

    # 3. 智能解析 Banners 表
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        img_urls = parse_images(fields.get("图片链接"))
        img_url = img_urls[0] if img_urls else ""
        if img_url:
            banners.append({
                "id": parse_text(fields.get("编号", "b-default")),
                "title": parse_text(fields.get("广告标题", "")),
                "image": img_url
            })

    # 4. 智能解析 Cases 案例表
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        
        # 栏目分类英文转换
        category_str = parse_text(fields.get("栏目分类"))
        category_english = "spatial"
        if "品牌视觉" in category_str:
            category_english = "branding"
        elif "活动视觉" in category_str:
            category_english = "events"

        # 是否上首页判断
        is_featured_raw = fields.get("是否上首页")
        if is_featured_raw is None:
            is_featured = False
        elif isinstance(is_featured_raw, bool):
            is_featured = is_featured_raw
        else:
            is_featured = parse_text(is_featured_raw).strip().lower() in ["true", "1", "是", "yes"]

        # 提取图片集合里的所有图片链接
        case_images = parse_images(fields.get("图片集合"))

        cases.append({
            "id": parse_text(fields.get("编号", "c-default")),
            "title": parse_text(fields.get("项目标题", "未命名项目")),
            "category": category_english,
            "tag": parse_text(fields.get("副标题", "")),
            "desc": parse_text(fields.get("项目简述", "")),
            "images": case_images,
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
        
    print(f"✨ 【大功告成】更新成功！当前共抓取到：配置 {len(settings)} 项，广告图 {len(banners)} 张，案例 {len(cases)} 个。")

if __name__ == "__main__":
    sync()
