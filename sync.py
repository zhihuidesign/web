import requests
import json
import os

# 1. 飞书多维表格开放平台安全凭证（直接从你原本的 data.js 中精准移植过来）
FEISHU_APP_ID = "cli_aaa8876d4fb95bd8"
FEISHU_APP_SECRET = "uaVTQdj59AXdtjMwng1aNf0nvUuBYzOc"
FEISHU_APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json().get("tenant_access_token")
    except Exception as e:
        print(f"请求飞书网络通行证失败: {e}")
    return None

def fetch_table_records(token, table_name):
    # 根据飞书规则，最高一次性同步 100 条记录
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_name}/records?page_size=100"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
    except Exception as e:
        print(f"拉取飞书表格【{table_name}】失败: {e}")
    return []

def sync():
    print("------------------------------------------")
    print("🤖 开启知汇文化飞书云同步数据引擎...")
    token = get_tenant_access_token()
    if not token:
        print("❌ 错误：无法获取飞书临时通信权，请检查安全凭证！")
        return
    
    print("✅ 成功：飞书云通道鉴权成功，正在抓取底层多维表格...")
    settings_raw = fetch_table_records(token, "Settings")
    banners_raw = fetch_table_records(token, "Banners")
    cases_raw = fetch_table_records(token, "Cases")
    
    # 解析 Settings 基础设置表格
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = fields.get("键名")
        val = fields.get("内容值")
        if key:
            # 统一转化为小写，防错
            settings[str(key).strip().lower()] = val
            
    # 解析 Banners 轮播广告表格
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        if fields.get("编号") or fields.get("广告标题"):
            banners.append({
                "id": str(fields.get("编号", "")),
                "title": str(fields.get("广告标题", "")),
                "image": str(fields.get("图片链接", ""))
            })
            
    # 解析 Cases 项目作品表格
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        feishu_cat = fields.get("栏目分类", "")
        
        # 处理可能的多选、单选或文本结构
        if isinstance(feishu_cat, list):
            cat_str = feishu_cat[0].get("text", "") if feishu_cat else ""
        elif isinstance(feishu_cat, dict):
            cat_str = feishu_cat.get("text", "")
        else:
            cat_str = str(feishu_cat)
            
        # 根据你的 data.js 汉字做智能分类重定向，确保网页导航栏分类流畅对应
        category_english = "spatial"
        if "品牌视觉" in cat_str:
            category_english = "branding"
        elif "活动视觉" in cat_str:
            category_english = "events"
            
        # 处理是否推荐到首页的布尔值判断
        is_featured = fields.get("是否上首页")
        if isinstance(is_featured, str):
            is_featured = is_featured.upper() == "TRUE"
        else:
            is_featured = bool(is_featured)
            
        cases.append({
            "id": str(fields.get("编号", "")),
            "title": str(fields.get("项目标题", "")),
            "category": category_english,
            "tag": str(fields.get("副标题", "")),
            "desc": str(fields.get("项目简述", "")),
            "images": str(fields.get("图片集合", "")),
            "featured": is_featured
        })
        
    # 合并输出
    final_output = {
        "settings": settings,
        "banners": banners,
        "cases": cases
    }
    
    # 3. 自动检查生成前端所需的 api 资源路径
    if not os.path.exists('api'):
        os.makedirs('api')
        
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
        
    print("------------------------------------------")
    print(f"🎉 动态数据同步成功！本地静态数据库 api/data.json 成功刷新。")
    print(f"📊 同步统计：全局配置({len(settings)}条), 推荐横幅({len(banners)}条), 项目案例({len(cases)}条)")

if __name__ == "__main__":
    sync()
