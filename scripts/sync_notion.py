#!/usr/bin/env python3
"""
同步数据到 Notion

读取: data/gongkaoleida_YYYYMMDD.json
输出: 创建 Notion 数据库记录

环境变量: NOTION_TOKEN
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# 配置
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATABASE_NAME = "📋 招聘信息库"
DATA_DIR = Path(__file__).parent.parent / "data"


class NotionSync:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION
        }
        self.database_id = None
    
    def find_database(self) -> bool:
        """搜索数据库"""
        url = f"{NOTION_API_URL}/search"
        data = {"query": DATABASE_NAME, "filter": {"value": "database", "property": "object"}}
        
        resp = requests.post(url, headers=self.headers, json=data)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                self.database_id = results[0]["id"]
                print(f"✅ 找到数据库: {DATABASE_NAME}")
                return True
        
        print(f"❌ 未找到数据库: {DATABASE_NAME}")
        return False
    
    def get_existing_urls(self) -> set:
        """获取已存在的 URL 用于去重"""
        if not self.database_id:
            return set()
        
        urls = set()
        url = f"{NOTION_API_URL}/databases/{self.database_id}/query"
        has_more = True
        start_cursor = None
        
        while has_more:
            data = {"page_size": 100}
            if start_cursor:
                data["start_cursor"] = start_cursor
            
            resp = requests.post(url, headers=self.headers, json=data)
            if resp.status_code == 200:
                result = resp.json()
                for page in result.get("results", []):
                    url_prop = page.get("properties", {}).get("原文链接", {})
                    if url_prop.get("url"):
                        urls.add(url_prop["url"])
                has_more = result.get("has_more", False)
                start_cursor = result.get("next_cursor")
            else:
                break
        
        return urls
    
    def create_page(self, job: dict) -> bool:
        """创建一条记录"""
        url = f"{NOTION_API_URL}/pages"
        
        properties = {
            "职位名称": {"title": [{"text": {"content": job.get("职位名称", "未知")[:100]}}]},
            "招聘单位": {"rich_text": [{"text": {"content": job.get("招聘单位", "")[:200]}}]},
            "薪资范围": {"rich_text": [{"text": {"content": job.get("薪资范围", "")[:100]}}]},
            "工作地点": {"rich_text": [{"text": {"content": job.get("工作地点", "")[:100]}}]},
            "来源网站": {"rich_text": [{"text": {"content": job.get("来源网站", "")[:100]}}]},
            "职位描述": {"rich_text": [{"text": {"content": job.get("职位描述", "")[:2000]}}]},
            "招聘人数": {"rich_text": [{"text": {"content": job.get("招聘人数", "")[:50]}}]},
            "学历要求": {"rich_text": [{"text": {"content": job.get("学历要求", "")[:50]}}]},
            "报名截止": {"rich_text": [{"text": {"content": job.get("报名截止", "")[:50]}}]},
            "状态": {"select": {"name": "新增"}}
        }
        
        if job.get("原文链接"):
            properties["原文链接"] = {"url": job["原文链接"]}
        
        if job.get("发布日期"):
            try:
                date_str = job["发布日期"].split(" ")[0]
                properties["发布日期"] = {"date": {"start": date_str}}
            except:
                pass
        
        if job.get("采集时间"):
            try:
                dt_str = job["采集时间"].replace(" ", "T")
                properties["采集时间"] = {"date": {"start": dt_str}}
            except:
                pass
        
        payload = {"parent": {"database_id": self.database_id}, "properties": properties}
        resp = requests.post(url, headers=self.headers, json=payload)
        return resp.status_code == 200
    
    def sync(self, jobs: list) -> dict:
        """同步所有数据"""
        stats = {"success": 0, "skipped": 0, "failed": 0}
        
        existing = self.get_existing_urls()
        print(f"📊 数据库已有: {len(existing)} 条记录")
        
        for i, job in enumerate(jobs, 1):
            job_url = job.get("原文链接", "")
            job_title = job.get("职位名称", "未知")[:30]
            
            if job_url in existing:
                stats["skipped"] += 1
                print(f"   [{i}/{len(jobs)}] ⏭️ 跳过: {job_title}...")
                continue
            
            print(f"   [{i}/{len(jobs)}] 同步: {job_title}...")
            if self.create_page(job):
                stats["success"] += 1
                existing.add(job_url)
            else:
                stats["failed"] += 1
        
        return stats


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("❌ 未设置 NOTION_TOKEN 环境变量")
        sys.exit(1)
    
    # 查找最新的数据文件
    files = sorted(DATA_DIR.glob("gongkaoleida_*.json"), reverse=True)
    if not files:
        print("❌ 未找到数据文件")
        sys.exit(1)
    
    data_file = files[0]
    print(f"📂 数据文件: {data_file.name}")
    
    with open(data_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    
    print(f"📊 待同步: {len(jobs)} 条")
    
    sync = NotionSync(token)
    if not sync.find_database():
        sys.exit(1)
    
    stats = sync.sync(jobs)
    
    print(f"\n{'='*40}")
    print(f"✅ 成功: {stats['success']} 条")
    print(f"⏭️ 跳过: {stats['skipped']} 条 (已存在)")
    print(f"❌ 失败: {stats['failed']} 条")
    
    # 输出数据库链接
    if sync.database_id:
        db_id = sync.database_id.replace("-", "")
        print(f"\n📎 Notion: https://www.notion.so/{db_id}")


if __name__ == "__main__":
    main()
