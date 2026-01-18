#!/usr/bin/env python3
"""
删除 Notion 数据库中指定日期的记录
"""
import os
import sys
import json
import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATABASE_ID = "2e07d626c84e81a5b57fea92a936e2cd"

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("❌ 请设置 NOTION_TOKEN 环境变量")
        return
    
    # 从JSON文件读取要删除的URL列表
    json_file = sys.argv[1] if len(sys.argv) > 1 else "data/gongkaoleida_20260112.json"
    
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        urls_to_delete = [job["原文链接"] for job in jobs]
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    print(f"🔍 准备删除 {len(urls_to_delete)} 条记录...")
    
    deleted_count = 0
    for i, url in enumerate(urls_to_delete, 1):
        # 查询包含该URL的页面
        query_url = f"{NOTION_API_URL}/databases/{DATABASE_ID}/query"
        query_data = {
            "filter": {
                "property": "原文链接",
                "url": {"equals": url}
            }
        }
        
        try:
            response = requests.post(query_url, headers=headers, json=query_data)
            if response.status_code == 200:
                results = response.json().get("results", [])
                for page in results:
                    page_id = page["id"]
                    title_list = page.get("properties", {}).get("职位名称", {}).get("title", [])
                    title = title_list[0].get("plain_text", "未知") if title_list else "未知"
                    
                    # 删除（归档）页面
                    archive_url = f"{NOTION_API_URL}/pages/{page_id}"
                    archive_data = {"archived": True}
                    del_response = requests.patch(archive_url, headers=headers, json=archive_data)
                    
                    if del_response.status_code == 200:
                        print(f"  [{i}/{len(urls_to_delete)}] ✅ 已删除: {title[:35]}...")
                        deleted_count += 1
                    else:
                        print(f"  [{i}/{len(urls_to_delete)}] ❌ 删除失败: {title[:35]}...")
            else:
                print(f"  [{i}/{len(urls_to_delete)}] ❌ 查询失败")
        except Exception as e:
            print(f"  [{i}/{len(urls_to_delete)}] ❌ 错误: {e}")
    
    print(f"\n🎉 删除完成! 共删除 {deleted_count} 条记录")

if __name__ == "__main__":
    main()
