#!/usr/bin/env python3
"""
抓取公考雷达职位列表

输出: data/job_list_YYYYMMDD.json

使用方法:
    python scripts/scrape_list.py [--date YYYY-MM-DD]
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置
BASE_URL = "https://www.gongkaoleida.com"
LIST_URL = f"{BASE_URL}/area/878-0-0-0-124"  # 江苏省
DATA_DIR = Path(__file__).parent.parent / "data"

# 筛选规则
EXCLUDE_KEYWORDS = ["成绩", "名单", "面试", "体检", "领取", "资格审查", "公示", "录用", "通知"]
INCLUDE_KEYWORDS = ["招聘", "招募", "选聘", "招考", "遴选", "选调"]


def is_recruitment_post(title: str) -> bool:
    """判断是否为招聘公告"""
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in title:
            return False
    for keyword in INCLUDE_KEYWORDS:
        if keyword in title:
            return True
    return False


async def fetch_list(target_date: str) -> list:
    """使用 Playwright 抓取职位列表"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 请安装 playwright: pip install playwright && playwright install chromium")
        sys.exit(1)
    
    jobs = []
    print(f"📋 开始抓取 {target_date} 的招聘信息...")
    print(f"🌐 URL: {LIST_URL}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(LIST_URL, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # 获取所有链接
            links = await page.query_selector_all("a")
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    title = await link.inner_text()
                    
                    if not title or len(title.strip()) < 10:
                        continue
                    if not href or href.startswith("#"):
                        continue
                    
                    title = title.strip()
                    
                    if not is_recruitment_post(title):
                        continue
                    
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    
                    jobs.append({
                        "title": title,
                        "url": full_url,
                        "date": target_date,
                        "source": ""
                    })
                except:
                    continue
            
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
        finally:
            await browser.close()
    
    # 去重
    seen = set()
    unique_jobs = []
    for job in jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)
    
    print(f"✅ 找到 {len(unique_jobs)} 条招聘公告")
    return unique_jobs


def main():
    parser = argparse.ArgumentParser(description="抓取公考雷达职位列表")
    parser.add_argument("--date", help="采集日期 YYYY-MM-DD", 
                        default=os.environ.get("COLLECT_DATE", datetime.now().strftime("%Y-%m-%d")))
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    jobs = asyncio.run(fetch_list(args.date))
    
    if not jobs:
        print("⚠️ 没有找到符合条件的招聘公告")
        return
    
    # 保存
    date_str = args.date.replace("-", "")
    output_file = DATA_DIR / f"job_list_{date_str}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 已保存到: {output_file}")
    print(f"📊 职位列表:")
    for i, job in enumerate(jobs[:10], 1):
        print(f"   {i}. {job['title'][:50]}...")
    if len(jobs) > 10:
        print(f"   ... 共 {len(jobs)} 条")


if __name__ == "__main__":
    main()
