#!/usr/bin/env python3
"""
删除 Notion 数据库中的非招聘信息记录
"""
import os
import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATABASE_ID = "2e07d626c84e81a5b57fea92a936e2cd"

# 需要删除的URL列表（非招聘信息）
URLS_TO_DELETE = [
    "https://www.gongkaoleida.com/article/2754870",  # 成绩公告
    "https://www.gongkaoleida.com/article/2754861",  # 成绩公示
    "https://www.gongkaoleida.com/article/2754804",  # 面试名单
    "https://www.gongkaoleida.com/article/2754800",  # 成绩公告
    "https://www.gongkaoleida.com/article/2754781",  # 名单公示
    "https://www.gongkaoleida.com/article/2754771",  # 成绩公示
    "https://www.gongkaoleida.com/article/2754699",  # 面试通知
]

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("❌ 请设置 NOTION_TOKEN 环境变量")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    print("🔍 搜索需要删除的记录...")
    
    for url in URLS_TO_DELETE:
        # 查询包含该URL的页面
        query_url = f"{NOTION_API_URL}/databases/{DATABASE_ID}/query"
        query_data = {
            "filter": {
                "property": "原文链接",
                "url": {"equals": url}
            }
        }
        
        response = requests.post(query_url, headers=headers, json=query_data)
        if response.status_code == 200:
            results = response.json().get("results", [])
            for page in results:
                page_id = page["id"]
                title = page.get("properties", {}).get("职位名称", {}).get("title", [{}])[0].get("plain_text", "未知")
                
                # 删除（归档）页面
                archive_url = f"{NOTION_API_URL}/pages/{page_id}"
                archive_data = {"archived": True}
                del_response = requests.patch(archive_url, headers=headers, json=archive_data)
                
                if del_response.status_code == 200:
                    print(f"  ✅ 已删除: {title[:40]}...")
                else:
                    print(f"  ❌ 删除失败: {title[:40]}... - {del_response.text}")
        else:
            print(f"  ❌ 查询失败: {url} - {response.text}")
    
    print("\n🎉 清理完成!")

if __name__ == "__main__":
    main()
