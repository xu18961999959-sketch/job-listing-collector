#!/usr/bin/env python3
"""
抓取公考雷达职位列表

支持分页抓取

使用方法:
    python scripts/scrape_list.py [--pages N]
    
示例:
    python scripts/scrape_list.py --pages 10
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 配置
BASE_URL = "https://www.gongkaoleida.com"
LIST_URL_TEMPLATE = BASE_URL + "/area/878-0-0-0-124?page={page}"
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


async def fetch_page(page_num: int, playwright) -> list:
    """抓取单页职位列表"""
    url = LIST_URL_TEMPLATE.format(page=page_num)
    jobs = []
    
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = await context.new_page()
    
    try:
        print(f"   📄 加载第 {page_num} 页...")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 获取所有职位链接
        items = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a');
                
                links.forEach(link => {
                    const href = link.href;
                    const title = link.innerText.trim();
                    
                    if (href && title && title.length > 10 && 
                        (href.includes('/article/') || href.includes('/info/'))) {
                        results.push({
                            title: title.substring(0, 200),
                            url: href
                        });
                    }
                });
                
                return results;
            }
        """)
        
        for item in items:
            title = item.get("title", "")
            full_url = item.get("url", "")
            
            if not is_recruitment_post(title):
                continue
            
            jobs.append({
                "title": title,
                "url": full_url,
                "date": "",  # 日期将从详情页提取
                "source": ""
            })
        
        print(f"      找到 {len(jobs)} 条招聘公告")
        
    except Exception as e:
        print(f"   ⚠️ 第 {page_num} 页抓取失败: {e}")
    finally:
        await browser.close()
    
    return jobs


async def fetch_list(max_pages: int) -> list:
    """使用 Playwright 抓取职位列表（支持分页）"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 请安装 playwright")
        sys.exit(1)
    
    all_jobs = []
    print(f"📋 开始抓取招聘信息...")
    print(f"🔢 最大页数: {max_pages}")
    
    async with async_playwright() as p:
        empty_pages = 0
        for page_num in range(1, max_pages + 1):
            page_jobs = await fetch_page(page_num, p)
            
            if not page_jobs:
                empty_pages += 1
                if empty_pages >= 2:
                    print(f"   连续 {empty_pages} 页无内容，停止翻页")
                    break
            else:
                empty_pages = 0
                all_jobs.extend(page_jobs)
            
            await asyncio.sleep(1)
    
    # 去重
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)
    
    print(f"✅ 共找到 {len(unique_jobs)} 条招聘公告")
    return unique_jobs


def main():
    parser = argparse.ArgumentParser(description="抓取公考雷达职位列表")
    parser.add_argument("--pages", help="最大页数", type=int,
                        default=int(os.environ.get("MAX_PAGES", "5")))
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    jobs = asyncio.run(fetch_list(args.pages))
    
    if not jobs:
        print("⚠️ 没有找到符合条件的招聘公告")
        return
    
    # 保存
    today_str = datetime.now().strftime("%Y%m%d")
    output_file = DATA_DIR / f"job_list_{today_str}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 已保存到: {output_file}")
    print(f"📊 共 {len(jobs)} 条职位")
    for i, job in enumerate(jobs[:5], 1):
        print(f"   {i}. {job['title'][:50]}...")


if __name__ == "__main__":
    main()
