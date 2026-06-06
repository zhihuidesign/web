import requests
import json
import os
import re

# 1. 飞书核心配置
APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def parse_text(field_val):
    """【万能文本清洗器】"""
    if field_val is None: return ""
    if isinstance(field_val, list):
        return "".join([item.get("text", "") or item.get("name", "") if isinstance(item, dict) else str(item) for item in field_val])
    if isinstance(field_val, dict):
        return field_val.get("text", "") or field_val.get("name", "")
    return str(field_val)

def parse_images(field_val):
    """【智能图片链接提取器】支持列表和单对象"""
    if not field_val: return []
    items = field_val if isinstance(field_val, list) else [field_val]
    urls = []
    for item in items:
        if isinstance(item, dict):
            if "url" in item: urls.append(item["url"])
            elif "link" in item: urls.append(item["link"])
            elif "text" in item: urls.extend(re.findall(r'https?://[^\s,;|]+', item["text"]))
        else:
            urls.extend(re.findall(r'https?://[^\s,;|]+', str(item)))
    return urls

def sync():
    print("=== 开始执行知汇文化数据同步 ===")
    
    # 1. 获取 Token
    token_res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}
    ).json()
    token = token_res.get("tenant_access_token")
    if not token:
        print(f"❌ 无法获取 Token，请检查 Secrets: {token_res}")
        return
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 动态扫描表格 (确保 ID 获取准确)
    tables_res = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables", headers=headers).json()
    name_to_id = {item.get("name"): item.get("table_id") for item in tables_res.get("data", {}).get("items", []) if item.get("name")}
    
    def fetch_records(t_name):
        t_id = name_to_id.get(t_name)
        if not t_id: return []
        res = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{t_id}/records?page_size=100", headers=headers).json()
        return res.get("data", {}).get("items", []) if res.get("code") == 0 else []

    settings_raw = fetch_records("Settings")
    banners_raw = fetch_records("Banners")
    cases_raw = fetch_records("Cases")

    # 3. 解析数据
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = parse_text(fields.get("键名")).strip()
        val = parse_text(fields.get("内容值")).strip()
        if key: settings[key] = val

    # ★ 重点更新：这里现在精准查找“图片链接”列
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        img_urls = parse_images(fields.get("图片链接"))
        if img_urls:
            banners.append({
                "id": parse_text(fields.get("编号", "b-default")),
                "title": parse_text(fields.get("广告标题", "")),
                "image": img_urls[0]
            })

    # 4. 解析 Cases
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        category_str = parse_text(fields.get("栏目分类"))
        category_english = "spatial"
        if "品牌视觉" in category_str: category_english = "branding"
        elif "活动视觉" in category_str: category_english = "events"

        is_feat = fields.get("是否上首页")
        featured = is_feat if isinstance(is_feat, bool) else parse_text(is_feat).strip().lower() in ["true", "1", "是", "yes"]
        images_str = ",".join(parse_images(fields.get("图片集合")))

        cases.append({
            "id": parse_text(fields.get("编号", "c-default")),
            "title": parse_text(fields.get("项目标题", "未命名项目")),
            "category": category_english,
            "tag": parse_text(fields.get("副标题", "")),
            "desc": parse_text(fields.get("项目简述", "")),
            "images": images_str,
            "featured": featured
        })

    # 5. 写入文件
    master_data = {"settings": settings, "banners": banners, "cases": cases}
    os.makedirs('api', exist_ok=True)
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"✨ 同步完成：配置 {len(settings)} 项，广告图 {len(banners)} 张，案例 {len(cases)} 个。")

if __name__ == "__main__":
    sync()
