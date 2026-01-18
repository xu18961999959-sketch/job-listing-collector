#!/usr/bin/env python3
"""
招聘信息同步到 Notion 数据库
Sync Job Listings to Notion Database

使用方法:
1. 设置环境变量 NOTION_TOKEN (Notion Integration Token)
2. 运行: python sync_to_notion.py [json_file]

如果未指定 json_file，将自动查找当前目录下最新的 采集结果_*.json 文件
"""

import json
import os
import sys
import glob
from datetime import datetime
from typing import Optional
import requests
import time

# Notion API 配置
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATABASE_NAME = "📋 招聘信息库"

# 数据库属性定义
DATABASE_PROPERTIES = {
    "职位名称": {"title": {}},
    "招聘单位": {"rich_text": {}},
    "薪资范围": {"rich_text": {}},
    "工作地点": {"rich_text": {}},
    "发布日期": {"date": {}},
    "来源网站": {"rich_text": {}},
    "原文链接": {"url": {}},
    "职位描述": {"rich_text": {}},
    "招聘人数": {"rich_text": {}},
    "学历要求": {"rich_text": {}},
    "报名截止": {"rich_text": {}},
    "采集时间": {"date": {}},
    "状态": {
        "select": {
            "options": [
                {"name": "新增", "color": "blue"},
                {"name": "已查看", "color": "yellow"},
                {"name": "已申请", "color": "green"},
                {"name": "已过期", "color": "gray"},
                {"name": "公示中", "color": "purple"}
            ]
        }
    }
}


class NotionSync:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION
        }
        self.database_id = None
        self.existing_urls = set()  # 用于去重
    
    def get_existing_urls(self) -> set:
        """获取数据库中已存在的原文链接，用于去重"""
        if not self.database_id:
            return set()
        
        urls = set()
        url = f"{NOTION_API_URL}/databases/{self.database_id}/query"
        has_more = True
        start_cursor = None
        
        print("🔍 检查数据库中已有记录...")
        while has_more:
            data = {"page_size": 100}
            if start_cursor:
                data["start_cursor"] = start_cursor
            
            try:
                response = requests.post(url, headers=self.headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    for page in result.get("results", []):
                        props = page.get("properties", {})
                        url_prop = props.get("原文链接", {})
                        if url_prop.get("url"):
                            urls.add(url_prop["url"])
                    has_more = result.get("has_more", False)
                    start_cursor = result.get("next_cursor")
                else:
                    break
            except Exception:
                break
        
        print(f"📊 已有记录: {len(urls)} 条")
        return urls
    
    def search_database(self) -> Optional[str]:
        """搜索已存在的招聘信息库"""
        url = f"{NOTION_API_URL}/search"
        data = {
            "query": DATABASE_NAME,
            "filter": {"property": "object", "value": "database"}
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 200:
            results = response.json().get("results", [])
            for result in results:
                title = result.get("title", [])
                if title and title[0].get("plain_text") == DATABASE_NAME:
                    return result["id"]
        return None
    
    def get_parent_page(self) -> Optional[str]:
        """获取用于创建数据库的父页面"""
        url = f"{NOTION_API_URL}/search"
        data = {
            "filter": {"property": "object", "value": "page"},
            "page_size": 1
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
        return None
    
    def create_database(self, parent_page_id: str) -> Optional[str]:
        """创建新的招聘信息库数据库"""
        url = f"{NOTION_API_URL}/databases"
        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": DATABASE_NAME}}],
            "properties": DATABASE_PROPERTIES
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 200:
            return response.json()["id"]
        else:
            print(f"❌ 创建数据库失败: {response.status_code}")
            print(response.text)
            return None
    
    def ensure_database(self) -> bool:
        """确保数据库存在，不存在则创建"""
        print("🔍 搜索 Notion 数据库...")
        self.database_id = self.search_database()
        
        if self.database_id:
            print(f"✅ 找到数据库: {DATABASE_NAME}")
            return True
        
        print(f"⚠️ 数据库不存在，正在创建...")
        parent_page_id = self.get_parent_page()
        
        if not parent_page_id:
            print("❌ 找不到可用的父页面来创建数据库")
            print("💡 提示: 请确保 Notion Integration 有访问至少一个页面的权限")
            return False
        
        self.database_id = self.create_database(parent_page_id)
        if self.database_id:
            print(f"✅ 数据库创建成功!")
            return True
        
        return False
    
    def format_rich_text(self, text: str) -> list:
        """格式化为 Notion rich_text 格式"""
        if not text or text == "N/A":
            return []
        # 截断过长的文本 (Notion 限制 2000 字符)
        if len(text) > 2000:
            text = text[:1997] + "..."
        return [{"type": "text", "text": {"content": text}}]
    
    def format_date(self, date_str: str) -> Optional[dict]:
        """格式化日期"""
        if not date_str or date_str in ["N/A", "未公开", "已截止"]:
            return None
        
        # 尝试解析各种日期格式
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y-%m-%dT%H:%M:%S%z"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return {"start": dt.strftime("%Y-%m-%d")}
            except ValueError:
                continue
        
        return None
    
    def create_page(self, job: dict, max_retries: int = 3) -> bool:
        """创建单条招聘信息页面，支持重试"""
        url = f"{NOTION_API_URL}/pages"
        
        properties = {
            "职位名称": {
                "title": self.format_rich_text(job.get("职位名称", "未知职位")) or 
                         [{"type": "text", "text": {"content": "未知职位"}}]
            },
            "招聘单位": {"rich_text": self.format_rich_text(job.get("招聘单位", ""))},
            "薪资范围": {"rich_text": self.format_rich_text(job.get("薪资范围", "未公开"))},
            "工作地点": {"rich_text": self.format_rich_text(job.get("工作地点", ""))},
            "来源网站": {"rich_text": self.format_rich_text(job.get("来源网站", ""))},
            "职位描述": {"rich_text": self.format_rich_text(job.get("职位描述", ""))},
            "招聘人数": {"rich_text": self.format_rich_text(job.get("招聘人数", ""))},
            "学历要求": {"rich_text": self.format_rich_text(job.get("学历要求", ""))},
            "报名截止": {"rich_text": self.format_rich_text(str(job.get("报名截止", "")))},
        }
        
        # 添加 URL
        if job.get("原文链接"):
            properties["原文链接"] = {"url": job["原文链接"]}
        
        # 添加发布日期
        pub_date = self.format_date(job.get("发布日期"))
        if pub_date:
            properties["发布日期"] = {"date": pub_date}
        
        # 添加采集时间
        properties["采集时间"] = {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
        
        # 添加状态
        status = job.get("状态", "新增")
        if status in ["新增", "已查看", "已申请", "已过期", "公示中"]:
            properties["状态"] = {"select": {"name": status}}
        
        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
                return response.status_code == 200
            except (requests.exceptions.SSLError, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待: 2s, 4s, 6s
                    print(f"    ⚠️ 网络错误，{wait_time}秒后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"    ❌ 重试{max_retries}次后仍失败: {str(e)[:50]}")
                    return False
            except Exception as e:
                print(f"    ❌ 未知错误: {str(e)[:50]}")
                return False
        
        return False
    
    def sync_jobs(self, jobs: list, skip_duplicates: bool = True) -> dict:
        """同步所有招聘信息，支持去重"""
        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
        
        # 获取已存在的记录用于去重
        if skip_duplicates:
            self.existing_urls = self.get_existing_urls()
        else:
            self.existing_urls = set()
        
        for i, job in enumerate(jobs, 1):
            job_name = job.get("职位名称", "未知职位")[:30]
            job_url = job.get("原文链接", "")
            
            # 检查是否重复
            if skip_duplicates and job_url and job_url in self.existing_urls:
                results["skipped"] += 1
                results["details"].append(f"⏭️ {job_name} (已存在)")
                print(f"  [{i}/{len(jobs)}] 跳过: {job_name} (已存在)")
                continue
            
            print(f"  [{i}/{len(jobs)}] 同步: {job_name}...")
            
            if self.create_page(job):
                results["success"] += 1
                results["details"].append(f"✅ {job_name}")
                self.existing_urls.add(job_url)  # 添加到已存在集合
            else:
                results["failed"] += 1
                results["details"].append(f"❌ {job_name}")
        
        return results


def find_latest_json() -> Optional[str]:
    """查找最新的采集结果 JSON 文件"""
    pattern = os.path.join(os.path.dirname(__file__), "采集结果_*.json")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    return max(files, key=os.path.getmtime)


def load_jobs(file_path: str) -> list:
    """加载招聘信息"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 支持多种格式: 直接数组 或 包含 "招聘信息"/"招聘信息列表" 字段的对象
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "招聘信息" in data:
        return data["招聘信息"]
    elif isinstance(data, dict) and "招聘信息列表" in data:
        return data["招聘信息列表"]
    else:
        return [data]


def main():
    print("=" * 50)
    print("📋 招聘信息同步到 Notion")
    print("=" * 50)
    
    # 获取 Notion Token
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("\n❌ 错误: 未设置 NOTION_TOKEN 环境变量")
        print("\n💡 设置方法:")
        print("   export NOTION_TOKEN='your_integration_token'")
        print("\n📖 获取 Token:")
        print("   1. 访问 https://www.notion.so/my-integrations")
        print("   2. 创建新的 Integration")
        print("   3. 复制 Internal Integration Token")
        print("   4. 在 Notion 中将 Integration 添加到目标页面")
        sys.exit(1)
    
    # 确定要同步的文件
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = find_latest_json()
        if not json_file:
            print("\n❌ 错误: 未找到采集结果文件")
            print("💡 请提供 JSON 文件路径作为参数")
            sys.exit(1)
    
    if not os.path.exists(json_file):
        print(f"\n❌ 错误: 文件不存在 - {json_file}")
        sys.exit(1)
    
    print(f"\n📂 数据文件: {os.path.basename(json_file)}")
    
    # 加载数据
    try:
        jobs = load_jobs(json_file)
        print(f"📊 待同步: {len(jobs)} 条招聘信息")
    except Exception as e:
        print(f"\n❌ 加载数据失败: {e}")
        sys.exit(1)
    
    # 初始化 Notion 同步器
    sync = NotionSync(token)
    
    # 确保数据库存在
    if not sync.ensure_database():
        print("\n❌ 无法访问或创建 Notion 数据库")
        sys.exit(1)
    
    # 同步数据
    print(f"\n🔄 开始同步到 Notion...")
    results = sync.sync_jobs(jobs)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("📊 同步结果")
    print("=" * 50)
    print(f"✅ 成功: {results['success']} 条")
    print(f"⏭️ 跳过: {results.get('skipped', 0)} 条 (已存在)")
    print(f"❌ 失败: {results['failed']} 条")
    
    if results['details']:
        print("\n详情:")
        for detail in results['details']:
            print(f"  {detail}")
    
    print("\n🎉 同步完成!")
    
    # 输出数据库链接
    if sync.database_id:
        db_id = sync.database_id.replace("-", "")
        print(f"\n📎 Notion 数据库: https://www.notion.so/{db_id}")


if __name__ == "__main__":
    main()
