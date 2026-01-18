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
    
    def get_existing_records(self) -> tuple[set, set]:
        """获取数据库中已存在的原文链接和职位名称，用于去重"""
        if not self.database_id:
            return set(), set()
        
        urls = set()
        titles = set()
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
                        
                        # 获取 URL
                        url_prop = props.get("原文链接", {})
                        if url_prop.get("url"):
                            urls.add(url_prop["url"])
                            
                        # 获取 Title
                        title_prop = props.get("职位名称", {})
                        if title_prop.get("title"):
                            title_text = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])])
                            if title_text:
                                titles.add(title_text)
                                
                    has_more = result.get("has_more", False)
                    start_cursor = result.get("next_cursor")
                else:
                    print(f"⚠️ 查询数据库失败: {response.status_code}")
                    break
            except Exception as e:
                print(f"⚠️ 查询数据库出错: {e}")
                break
        
        print(f"📊 已有记录: {len(urls)} 个链接, {len(titles)} 个标题")
        return urls, titles
    
    def ensure_database(self) -> bool:
        """检查数据库是否可访问，如果不知道ID则尝试搜索"""
        if self.database_id:
            return True
            
        print("🔍 正在搜索 Notion 数据库...")
        url = f"{NOTION_API_URL}/search"
        data = {
            "query": DATABASE_NAME,
            "filter": {
                "value": "database",
                "property": "object"
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    self.database_id = results[0]["id"]
                    print(f"✅ 找到数据库: {DATABASE_NAME} ({self.database_id})")
                    return True
                else:
                    print(f"❌ 未找到名为 '{DATABASE_NAME}' 的数据库")
                    print("💡 请确保已在 Notion 中创建数据库，并将 Integration 分享给定该数据库")
                    return False
            else:
                print(f"❌ 搜索数据库失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 连接 Notion 失败: {e}")
            return False

    def create_page(self, job_data: dict) -> bool:
        """创建一条新的招聘记录"""
        if not self.database_id:
            return False
            
        url = f"{NOTION_API_URL}/pages"
        
        # 构建属性
        properties = {}
        
        # 职位名称 (Title)
        properties["职位名称"] = {
            "title": [{"text": {"content": job_data.get("职位名称", "未知")}}]
        }
        
        # 文本字段 mappings
        text_fields = {
            "招聘单位": "招聘单位",
            "薪资范围": "薪资范围",
            "工作地点": "工作地点",
            "来源网站": "来源网站",
            "职位描述": "职位描述",
            "招聘人数": "招聘人数",
            "学历要求": "学历要求",
            "报名截止": "报名截止"
        }
        
        for notion_field, data_field in text_fields.items():
            content = str(job_data.get(data_field, "") or "")
            # Notion rich_text limit is 2000 chars
            if len(content) > 2000:
                content = content[:1997] + "..."
            properties[notion_field] = {
                "rich_text": [{"text": {"content": content}}]
            }
            
        # URL
        if job_data.get("原文链接"):
            properties["原文链接"] = {"url": job_data.get("原文链接")}
            
        # 日期
        if job_data.get("发布日期"):
            try:
                # 尝试解析日期格式，确保是 YYYY-MM-DD
                # 这里假设输入已经是比较规范的格式，或者简单处理
                date_str = job_data.get("发布日期")
                # 如果包含时间，只取日期部分
                if " " in date_str:
                    date_str = date_str.split(" ")[0]
                properties["发布日期"] = {"date": {"start": date_str}}
            except:
                pass

        if job_data.get("采集时间"):
             try:
                # 采集时间带时分秒
                date_str = job_data.get("采集时间")
                # Notion date accepts ISO 8601
                # If space separated, replace with T
                if " " in date_str:
                    date_str = date_str.replace(" ", "T")
                properties["采集时间"] = {"date": {"start": date_str}}
             except:
                pass
        
        # 状态 (Select)
        properties["状态"] = {"select": {"name": "新增"}}
        
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                return True
            else:
                print(f"❌ 创建页面失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return False

    def sync_jobs(self, jobs: list, skip_duplicates: bool = True) -> dict:
        """同步所有招聘信息，支持去重"""
        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
        
        # 获取已存在的记录用于去重
        existing_urls = set()
        existing_titles = set()
        
        if skip_duplicates:
            existing_urls, existing_titles = self.get_existing_records()
        
        for i, job in enumerate(jobs, 1):
            job_name = job.get("职位名称", "未知职位")
            job_url = job.get("原文链接", "")
            
            # 检查是否重复 (链接重复 或 标题重复)
            is_duplicate = False
            duplicate_reason = ""
            
            if skip_duplicates:
                if job_url and job_url in existing_urls:
                    is_duplicate = True
                    duplicate_reason = "链接已存在"
                elif job_name and job_name in existing_titles:
                    is_duplicate = True
                    duplicate_reason = "标题已存在"
            
            if is_duplicate:
                results["skipped"] += 1
                short_name = job_name[:30] + "..." if len(job_name) > 30 else job_name
                results["details"].append(f"⏭️ {short_name} ({duplicate_reason})")
                print(f"  [{i}/{len(jobs)}] 跳过: {short_name} ({duplicate_reason})")
                continue
            
            print(f"  [{i}/{len(jobs)}] 同步: {job_name[:30]}...")
            
            if self.create_page(job):
                results["success"] += 1
                results["details"].append(f"✅ {job_name[:30]}")
                # 更新本地缓存
                if job_url:
                    existing_urls.add(job_url)
                if job_name:
                    existing_titles.add(job_name)
            else:
                results["failed"] += 1
                results["details"].append(f"❌ {job_name[:30]}")
        
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
