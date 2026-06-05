import requests
import json
import os

# 1. 飞书核心配置区（优先读取 GitHub Actions 的变量，没有则自动使用备用默认钥匙，确保100%成功）
APP_ID = os.getenv('FEISHU_APP_ID', 'cli_aaa8876d4fb95bd8')
APP_SECRET = os.getenv('FEISHU_APP_SECRET', 'uaVTQdj59AXdtjMwng1aNf0nvUuBYzOc')
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json().get("tenant_access_token")
    except Exception as e:
        print(f"请求通行证失败: {e}")
    return None

def fetch_table(token, table_name):
    # 根据 data.js 中的逻辑，读取纯中文表头，最多拉取100条
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_name}/records?page_size=100"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
    except Exception as e:
        print(f"抓取表格 {table_name} 失败: {e}")
    return []

def sync():
    token = get_tenant_access_token()
    if not token:
        print("【错误】获取飞书 Access Token 失败，请检查 App ID 和 Secret 是否有效。")
        return
    
    print("【成功】飞书网络已打通，开始同步数据...")
    settings_raw = fetch_table(token, "Settings")
    banners_raw = fetch_table(token, "Banners")
    cases_raw = fetch_table(token, "Cases")
    
    # 解析 Settings 表
    settings = {}
    for item in settings_raw:
        fields = item.get("fields", {})
        key = fields.get("键名")
        val = fields.get("内容值")
        if key:
            settings[key] = val
            
    # 解析 Banners 表
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        if fields.get("编号") or fields.get("广告标题"):
            banners.append({
                "id": fields.get("编号", ""),
                "title": fields.get("广告标题", ""),
                "image": fields.get("图片链接", "")
            })
            
    # 解析 Cases 表
    cases = []
    for item in cases_raw:
        fields = item.get("fields", {})
        feishu_category = fields.get("栏目分类", "")
        
        # 处理可能的多选或文本格式
        if isinstance(feishu_category, list):
            category_str = feishu_category[0].get("text", "") if feishu_category else ""
        else:
            category_str = str(feishu_category)
            
        # 转换分类为英文以适配前端 index.html 的识别
        category_english = "spatial"
        if "品牌视觉" in category_str:
            category_english = "branding"
        elif "活动视觉" in category_str:
            category_english = "events"
            
        is_featured = fields.get("是否上首页")
        if isinstance(is_featured, str):
            is_featured = is_featured.upper() == "TRUE"
        else:
            is_featured = bool(is_featured)
            
        cases.append({
            "id": fields.get("编号", ""),
            "title": fields.get("项目标题", ""),
            "category": category_english,
            "tag": fields.get("副标题", ""),
            "desc": fields.get("项目简述", ""),
            "images": fields.get("图片集合", ""),
            "featured": is_featured
        })
        
    result_data = {
        "settings": settings,
        "banners": banners,
        "cases": cases
    }
    
    # 3. 确保 api 目录存在并在本地保存结果
    if not os.path.exists('api'):
        os.makedirs('api')
        
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
        
    print(f"【大功告成】已成功抓取飞书数据并写入到 api/data.json 文件中数据流条数：Settings({len(settings)}), Banners({len(banners)}), Cases({len(cases)})")

if __name__ == "__main__":
    sync()
