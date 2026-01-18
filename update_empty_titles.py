#!/usr/bin/env python3
"""
更新 Notion 中职位名称为空的记录
Update Notion records with empty job titles
"""

import json
import os
import sys
import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATABASE_NAME = "📋 招聘信息库"


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }


def find_database(headers):
    """Search for the database"""
    url = f"{NOTION_API_URL}/search"
    data = {
        "query": DATABASE_NAME,
        "filter": {"value": "database", "property": "object"}
    }
    response = requests.post(url, headers=headers, json=data, timeout=30)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return results[0]["id"]
    return None


def get_pages_with_empty_titles(headers, database_id):
    """Get all pages with empty titles"""
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        data = {"page_size": 100}
        if start_cursor:
            data["start_cursor"] = start_cursor
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code}")
            break
        
        result = response.json()
        for page in result.get("results", []):
            props = page.get("properties", {})
            title_prop = props.get("职位名称", {})
            title_arr = title_prop.get("title", [])
            title_text = "".join([t.get("plain_text", "") for t in title_arr])
            
            url_prop = props.get("原文链接", {})
            page_url = url_prop.get("url", "")
            
            if not title_text.strip() and page_url:
                pages.append({
                    "page_id": page["id"],
                    "url": page_url
                })
        
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")
    
    return pages


def update_page_title(headers, page_id, title):
    """Update a page's title"""
    url = f"{NOTION_API_URL}/pages/{page_id}"
    data = {
        "properties": {
            "职位名称": {
                "title": [{"text": {"content": title}}]
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data, timeout=30)
    return response.status_code == 200


def load_job_data(file_path):
    """Load job data and create URL -> title mapping"""
    with open(file_path, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    return {job.get("原文链接"): job.get("职位名称") for job in jobs if job.get("原文链接")}


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("❌ 请设置 NOTION_TOKEN 环境变量")
        sys.exit(1)
    
    # Load job data
    data_file = sys.argv[1] if len(sys.argv) > 1 else "data/gongkaoleida_20260115.json"
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        sys.exit(1)
    
    print(f"📂 加载数据: {data_file}")
    url_to_title = load_job_data(data_file)
    print(f"📊 共 {len(url_to_title)} 条记录")
    
    headers = get_headers(token)
    
    # Find database
    print("🔍 搜索 Notion 数据库...")
    database_id = find_database(headers)
    if not database_id:
        print("❌ 未找到数据库")
        sys.exit(1)
    print(f"✅ 找到数据库: {database_id}")
    
    # Get pages with empty titles
    print("🔍 查找空标题记录...")
    empty_pages = get_pages_with_empty_titles(headers, database_id)
    print(f"📊 找到 {len(empty_pages)} 条空标题记录")
    
    if not empty_pages:
        print("✅ 没有需要更新的记录")
        return
    
    # Update pages
    updated = 0
    failed = 0
    for page in empty_pages:
        page_url = page["url"]
        new_title = url_to_title.get(page_url, "")
        
        if not new_title:
            print(f"⚠️ 未找到标题: {page_url}")
            continue
        
        short_title = new_title[:40] + "..." if len(new_title) > 40 else new_title
        print(f"  更新: {short_title}")
        
        if update_page_title(headers, page["page_id"], new_title):
            updated += 1
        else:
            failed += 1
    
    print(f"\n✅ 更新完成: {updated} 条成功, {failed} 条失败")


if __name__ == "__main__":
    main()
