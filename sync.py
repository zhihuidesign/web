import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

# ================================
# 知汇文化网站：飞书多维表格同步脚本
# 当前推荐部署方式：GitHub Pages 静态网站
# 你平时只需要维护飞书表格；这个脚本会自动生成 api/data.json
# ================================

FEISHU_API = "https://open.feishu.cn/open-apis"
APP_ID = os.getenv("FEISHU_APP_ID", "").strip()
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "").strip()
APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "").strip()

# 这 3 个 table_id 来自你当前的飞书多维表格网址。它们不是密码，固定在代码里可以降低后期维护成本。
TABLE_SETTINGS = os.getenv("FEISHU_TABLE_SETTINGS", "tbl4yj6yMn9b6TVB").strip()
TABLE_BANNERS = os.getenv("FEISHU_TABLE_BANNERS", "tbleKDTByw1PG3vB").strip()
TABLE_CASES = os.getenv("FEISHU_TABLE_CASES", "tblLbJOrvKnT2dHR").strip()
# CoCreate 没有拿到 table_id，所以默认按左侧表名 CoCreate 自动寻找；找不到也不影响网站打开。
TABLE_COCREATE = os.getenv("FEISHU_TABLE_COCREATE", "CoCreate").strip()

URL_RE = re.compile(r"https?://[^\s\"'<>，,;；|\)\]\}]+", re.IGNORECASE)
ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT_DIR / "api" / "data.json"


def natural_sort_key(value: Any) -> list[Any]:
    """让 01、02、10 这种编号按人类习惯排序，避免新增案例后顺序混乱。"""
    text = parse_text(value).strip()
    parts = re.split(r"(\d+)", text)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def fail(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)


def parse_text(value: Any) -> str:
    """把飞书各种字段格式清洗成普通文本。"""
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(parse_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "name", "value", "url", "link", "tmp_url", "file_url"):
            if value.get(key) is not None:
                return str(value.get(key))
        return ""
    return str(value)


def extract_urls(value: Any) -> list[str]:
    """从飞书文本、URL、附件对象、数组中提取图片或视频链接。"""
    urls: list[str] = []

    def push(raw: Any) -> None:
        text = parse_text(raw).strip()
        if not text:
            return
        found = URL_RE.findall(text)
        if found:
            urls.extend(item.strip() for item in found)
            return
        for part in re.split(r"[\n，,;；|]+", text):
            part = part.strip()
            if part.startswith("http://") or part.startswith("https://"):
                urls.append(part)

    def walk(input_value: Any) -> None:
        if not input_value:
            return
        if isinstance(input_value, list):
            for item in input_value:
                walk(item)
            return
        if isinstance(input_value, dict):
            for key in ("url", "link", "tmp_url", "file_url", "text", "name"):
                if input_value.get(key):
                    push(input_value.get(key))
            return
        push(input_value)

    walk(value)
    # 去重并保留原顺序
    result: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def parse_boolean(value: Any) -> bool:
    if value is True or value is False:
        return bool(value)
    text = parse_text(value).strip().lower()
    return text in {"true", "1", "是", "yes", "y", "首页", "推荐", "checked"}


def normalize_category(value: Any) -> str:
    """把飞书里的中文栏目分类转成网页内部分类。"""
    text = parse_text(value).strip()
    lower = text.lower()
    if lower == "branding" or "品牌视觉" in text or "品牌" in text:
        return "branding"
    if lower == "events" or "活动展览" in text or "活动视觉" in text or "会展" in text or "展览" in text or "活动" in text:
        return "events"
    if lower == "digital" or "数字触点" in text or "h5" in lower or "网页" in text or "网站" in text or "小程序" in text or "数字" in text:
        return "digital"
    if lower == "lab" or "实验室" in text or "短视频" in text or "ai" in lower or "漫剧" in text or "IP" in text or "内容孵化" in text:
        return "lab"
    return "spatial"


def get_token() -> str:
    if not APP_ID:
        fail("缺少 GitHub Secret：FEISHU_APP_ID")
    if not APP_SECRET:
        fail("缺少 GitHub Secret：FEISHU_APP_SECRET")
    if not APP_TOKEN:
        fail("缺少 GitHub Secret：FEISHU_APP_TOKEN")

    response = requests.post(
        f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=20,
    )
    data = response.json()
    token = data.get("tenant_access_token")
    if not token:
        fail(f"无法获取飞书 tenant_access_token，请检查 App ID / App Secret。飞书返回：{data}")
    return token


def get_table_map(headers: dict[str, str]) -> dict[str, str]:
    response = requests.get(
        f"{FEISHU_API}/bitable/v1/apps/{APP_TOKEN}/tables?page_size=100",
        headers=headers,
        timeout=20,
    )
    data = response.json()
    if data.get("code") != 0:
        print(f"⚠️ 获取表格列表失败：{data}")
        return {}
    return {
        item.get("name", ""): item.get("table_id", "")
        for item in data.get("data", {}).get("items", [])
        if item.get("name") and item.get("table_id")
    }


def resolve_table_id(table_ref: str, table_map: dict[str, str]) -> str:
    """table_ref 可以是 table_id，也可以是左侧表名。"""
    if table_ref.startswith("tbl"):
        return table_ref
    return table_map.get(table_ref, "")


def fetch_records(table_ref: str, headers: dict[str, str], table_map: dict[str, str]) -> list[dict[str, Any]]:
    table_id = resolve_table_id(table_ref, table_map)
    if not table_id:
        print(f"⚠️ 找不到表：{table_ref}，跳过。")
        return []

    records: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        response = requests.get(
            f"{FEISHU_API}/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
            headers=headers,
            params=params,
            timeout=30,
        )
        data = response.json()
        if data.get("code") != 0:
            print(f"⚠️ 读取表 {table_ref} 失败：{data}")
            return records
        payload = data.get("data", {})
        records.extend(payload.get("items", []))
        if not payload.get("has_more"):
            break
        page_token = payload.get("page_token", "")
        if not page_token:
            break
    return records


def parse_settings(records: list[dict[str, Any]]) -> dict[str, str]:
    settings: dict[str, str] = {}
    for item in records:
        fields = item.get("fields", {})
        key = parse_text(fields.get("键名")).strip()
        value = parse_text(fields.get("内容值")).strip()
        if key:
            settings[key] = value
    return settings


def parse_banners(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    banners: list[dict[str, Any]] = []
    for index, item in enumerate(records, start=1):
        fields = item.get("fields", {})
        image_urls = extract_urls(fields.get("图片链接")) or extract_urls(fields.get("图片集合"))
        if not image_urls:
            continue
        banners.append({
            "id": parse_text(fields.get("编号")).strip() or f"banner-{index}",
            "title": parse_text(fields.get("广告标题")).strip(),
            "image": image_urls[0],
        })
    return sorted(banners, key=lambda item: natural_sort_key(item.get("id", "")))


def parse_cases(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, item in enumerate(records, start=1):
        fields = item.get("fields", {})

        media_urls: list[str] = []
        # 可选：如果以后你想单独控制封面，可新增“封面链接”；不新增也完全没问题。
        media_urls.extend(extract_urls(fields.get("封面链接")))
        # 可选：如果你以后新增“媒体集合”（多行文本），代码会优先读取。
        media_urls.extend(extract_urls(fields.get("媒体集合")))
        # 当前推荐保留“图片集合”：一行一个链接，第一行自动做封面，后面做详情图/视频。
        media_urls.extend(extract_urls(fields.get("图片集合")))
        # 兼容：如果你以后误填到“图片链接”，代码也能识别。
        media_urls.extend(extract_urls(fields.get("图片链接")))

        # 去重保序
        seen: set[str] = set()
        media_urls = [url for url in media_urls if not (url in seen or seen.add(url))]

        title = parse_text(fields.get("项目标题")).strip()
        if not title and not media_urls:
            # 空行直接跳过
            continue

        raw_category = parse_text(fields.get("栏目分类")).strip()
        cases.append({
            "id": parse_text(fields.get("编号")).strip() or f"case-{index}",
            "title": title or "未命名项目",
            "category": normalize_category(raw_category),
            "raw_category": raw_category,
            "tag": parse_text(fields.get("副标题")).strip(),
            "desc": parse_text(fields.get("项目简述")).strip(),
            "images": "\n".join(media_urls),
            "featured": parse_boolean(fields.get("是否上首页")),
        })
    return sorted(cases, key=lambda item: natural_sort_key(item.get("id", "")))


def parse_cocreate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    default_icons = ["📦", "🧸", "⚡", "✨", "🤝", "🚀"]
    for index, item in enumerate(records, start=1):
        fields = item.get("fields", {})
        title = parse_text(fields.get("标题")).strip()
        desc = parse_text(fields.get("描述")).strip()
        if not title and not desc:
            continue
        items.append({
            "id": parse_text(fields.get("编号ID")).strip() or parse_text(fields.get("编号")).strip() or str(index),
            "icon": parse_text(fields.get("图标")).strip() or default_icons[(index - 1) % len(default_icons)],
            "title": title,
            "desc": desc,
        })
    return sorted(items, key=lambda item: natural_sort_key(item.get("id", "")))


def sync() -> None:
    print("=== 知汇文化网站：开始同步飞书数据 ===")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    table_map = get_table_map(headers)

    settings_raw = fetch_records(TABLE_SETTINGS, headers, table_map)
    banners_raw = fetch_records(TABLE_BANNERS, headers, table_map)
    cases_raw = fetch_records(TABLE_CASES, headers, table_map)
    cocreate_raw = fetch_records(TABLE_COCREATE, headers, table_map)

    master_data = {
        "settings": parse_settings(settings_raw),
        "banners": parse_banners(banners_raw),
        "cases": parse_cases(cases_raw),
        "cocreate": parse_cocreate(cocreate_raw),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "✨ 同步完成："
        f"Settings {len(master_data['settings'])} 项，"
        f"Banners {len(master_data['banners'])} 条，"
        f"Cases {len(master_data['cases'])} 个，"
        f"CoCreate {len(master_data['cocreate'])} 个。"
    )


if __name__ == "__main__":
    sync()
