import requests
import json
import os
import re

APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
APP_TOKEN = "L3gAbHr0vaDklls2gfQcjdEmnjf"

def parse_text(field_val):
    if field_val is None: return ""
    if isinstance(field_val, list):
        return "".join([item.get("text", "") or item.get("name", "") if isinstance(item, dict) else str(item) for item in field_val])
    if isinstance(field_val, dict):
        return field_val.get("text", "") or field_val.get("name", "")
    return str(field_val)

def parse_images(field_val):
    """【增强版】适配飞书附件结构：支持列表和单对象"""
    if not field_val: return []
    
    # 强制将单对象转为列表处理
    items = field_val if isinstance(field_val, list) else [field_val]
    
    urls = []
    for item in items:
        if isinstance(item, dict):
            if "url" in item: urls.append(item["url"])
            elif "link" in item: urls.append(item["link"]) # 适配图片对象的 link 属性
            elif "text" in item: urls.extend(re.findall(r'https?://[^\s,;|]+', item["text"]))
        else:
            urls.extend(re.findall(r'https?://[^\s,;|]+', str(item)))
    return urls

def sync():
    # ... (前面的 Token 获取部分保持不变) ...
    # 为了节省空间，直接写核心逻辑部分，请确保保留完整代码
    
    # 获取 Token 和表格数据的逻辑保持不变
    # ... (省略中间部分) ...
    
    # ⭐【关键修改】这里改用“图片连接” (和你表格里那一列名字完全对齐)
    banners = []
    for item in banners_raw:
        fields = item.get("fields", {})
        
        # 使用你表格里真实存在的列名：“图片连接”
        img_urls = parse_images(fields.get("图片连接"))
        
        img_url = img_urls[0] if img_urls else ""
        
        if img_url:
            banners.append({
                "id": parse_text(fields.get("编号", "b-default")),
                "title": parse_text(fields.get("广告标题", "")),
                "image": img_url
            })
        else:
            # 如果还抓不到，这行日志会打印出具体的数据，方便我们二次排查
            print(f"DEBUG: 跳过该条记录，无法解析图片。原始字段内容: {fields.get('图片连接')}")

    # ... (Cases 解析逻辑保持不变) ...
    
    # 写入文件逻辑保持不变
    # ...
