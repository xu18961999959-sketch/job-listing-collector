#!/usr/bin/env python3
"""
公考雷达招聘信息采集工作流

直接执行模式 - 不依赖 Claude API

使用方法:
    python agent_workflow.py

环境变量:
    NOTION_TOKEN - Notion Integration Token (必需)
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DATA_DIR = PROJECT_DIR / "data"


def validate_environment() -> bool:
    """验证必要的环境变量"""
    if not os.environ.get("NOTION_TOKEN"):
        print("❌ 未设置 NOTION_TOKEN")
        print("💡 请在 GitHub Secrets 中配置 NOTION_TOKEN")
        return False
    return True


def run_script(script_name: str, args: list = None) -> tuple[bool, str]:
    """运行 Python 脚本"""
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    return result.returncode == 0, output


def main():
    """主工作流"""
    print("🚀 公考雷达招聘信息采集工作流")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 模式: 直接执行 (无需 Claude API)")
    
    if not validate_environment():
        sys.exit(1)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    stats = {"scraped": 0, "synced": 0, "skipped": 0, "failed": 0}
    
    # Step 1: 抓取职位列表
    print("\n" + "="*50)
    print("🌐 Step 1: 抓取公考雷达职位列表")
    print("="*50)
    
    success, output = run_script("scrape_list.py")
    print(output)
    
    if not success:
        print("❌ 抓取列表失败")
        # 继续执行，可能有之前的数据
    
    # 读取职位列表获取 URL
    today = datetime.now().strftime("%Y%m%d")
    job_list_file = DATA_DIR / f"job_list_{today}.json"
    
    job_urls = []
    if job_list_file.exists():
        with open(job_list_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)
            job_urls = [job.get("url") for job in jobs if job.get("url")]
            stats["scraped"] = len(job_urls)
            print(f"📊 找到 {len(job_urls)} 个职位")
    
    # Step 2: 抓取职位详情 (限制数量避免超时)
    if job_urls:
        print("\n" + "="*50)
        print("📄 Step 2: 抓取职位详情")
        print("="*50)
        
        max_jobs = int(os.environ.get("MAX_JOBS", "15"))
        job_urls = job_urls[:max_jobs]
        
        for i, url in enumerate(job_urls, 1):
            print(f"   [{i}/{len(job_urls)}] 获取详情...")
            success, output = run_script("scrape_detail.py", ["--url", url])
            if not success:
                print(f"      ⚠️ 失败")
    
    # Step 3: 处理数据
    print("\n" + "="*50)
    print("🔄 Step 3: 处理合并数据")
    print("="*50)
    
    success, output = run_script("process_data.py")
    print(output)
    
    # Step 4: 同步到 Notion
    print("\n" + "="*50)
    print("☁️ Step 4: 同步到 Notion")
    print("="*50)
    
    success, output = run_script("sync_notion.py")
    print(output)
    
    # 解析同步结果
    import re
    match = re.search(r"成功:\s*(\d+)", output)
    if match:
        stats["synced"] = int(match.group(1))
    match = re.search(r"跳过:\s*(\d+)", output)
    if match:
        stats["skipped"] = int(match.group(1))
    match = re.search(r"失败:\s*(\d+)", output)
    if match:
        stats["failed"] = int(match.group(1))
    
    # Step 5: 生成报告
    print("\n" + "="*50)
    print("📊 采集完成统计")
    print("="*50)
    print(f"📥 抓取职位: {stats['scraped']} 条")
    print(f"✅ 新增同步: {stats['synced']} 条")
    print(f"⏭️ 跳过重复: {stats['skipped']} 条")
    print(f"❌ 处理失败: {stats['failed']} 条")
    
    # 保存摘要
    summary_file = DATA_DIR / "collect_summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"- 抓取职位: {stats['scraped']} 条\n")
        f.write(f"- 新增同步: {stats['synced']} 条\n")
        f.write(f"- 跳过重复: {stats['skipped']} 条\n")
    
    print("\n🎉 采集工作流完成!")


if __name__ == "__main__":
    main()
