import requests
import json
import os

# 1. 飞书配置（从 GitHub Actions 的环境变量读取）
APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')

# 2. 这里的 URL 需要填入你的飞书表格 API 地址
# 你可以在飞书开放平台-API调试台获取
URL = "https://open.feishu.cn/open-apis/bitable/v1/..." 

def sync():
    # 简单的鉴权逻辑（示例）
    # 实际开发中你需要根据飞书文档获取 access_token
    # 这里我们模拟生成一个 data.json，你可以根据你的实际需求修改
    
    data = {
        "settings": {"core_values": "知汇文化，深度操盘。"},
        "cases": []
    }
    
    # 3. 确保 api 文件夹存在
    if not os.path.exists('api'):
        os.makedirs('api')
        
    # 4. 写入 data.json，供 index.html[cite: 3] 读取
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("同步成功！")

if __name__ == "__main__":
    sync()