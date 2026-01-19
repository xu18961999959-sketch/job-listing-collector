#!/usr/bin/env python3
"""
抓取公考雷达职位列表

支持分页和日期筛选

使用方法:
    python scripts/scrape_list.py [--date YYYY-MM] [--pages N]
    
示例:
    python scripts/scrape_list.py --date 2025-12 --pages 10
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


def matches_date(text: str, target_yearmonth: str) -> bool:
    """检查文本是否包含目标年月"""
    # target_yearmonth 格式: "2025-12"
    if not target_yearmonth:
        return True
    
    year, month = target_yearmonth.split("-")
    
    # 检查是否包含年月
    patterns = [
        f"{year}年{int(month)}月",
        f"{year}-{month}",
        f"{year}-{int(month):02d}",
        f"{year}/{month}",
    ]
    
    for pattern in patterns:
        if pattern in text:
            return True
    
    return False


async def fetch_page(page, playwright, target_date: str = None) -> list:
    """抓取单页职位列表"""
    url = LIST_URL_TEMPLATE.format(page=page)
    jobs = []
    
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page_obj = await context.new_page()
    
    try:
        print(f"   📄 加载第 {page} 页...")
        await page_obj.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 获取所有链接和发布时间
        items = await page_obj.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a');
                
                links.forEach(link => {
                    const href = link.href;
                    const title = link.innerText.trim();
                    
                    // 尝试获取日期信息（从附近元素）
                    let dateText = '';
                    const parent = link.parentElement;
                    if (parent) {
                        const dateEl = parent.querySelector('.date, .time, [class*="date"], [class*="time"]');
                        if (dateEl) dateText = dateEl.innerText;
                    }
                    
                    // 获取所有文本用于日期匹配
                    const fullText = link.closest('li, .item, [class*="item"]')?.innerText || '';
                    
                    if (href && title && title.length > 10 && (href.includes('/article/') || href.includes('/info/'))) {
                        results.push({
                            title: title.substring(0, 200),
                            url: href,
                            dateText: dateText,
                            context: fullText.substring(0, 500)
                        });
                    }
                });
                
                return results;
            }
        """)
        
        for item in items:
            title = item.get("title", "")
            full_url = item.get("url", "")
            context_text = item.get("context", "") + " " + title
            
            # 日期筛选
            if target_date and not matches_date(context_text, target_date):
                continue
            
            if not is_recruitment_post(title):
                continue
            
            jobs.append({
                "title": title,
                "url": full_url,
                "date": target_date or datetime.now().strftime("%Y-%m-%d"),
                "source": "",
                "date_text": item.get("dateText", "")
            })
        
    except Exception as e:
        print(f"   ⚠️ 第 {page} 页抓取失败: {e}")
    finally:
        await browser.close()
    
    return jobs


async def fetch_list(target_date: str, max_pages: int) -> list:
    """使用 Playwright 抓取职位列表（支持分页）"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 请安装 playwright: pip install playwright && playwright install chromium")
        sys.exit(1)
    
    all_jobs = []
    print(f"📋 开始抓取 {target_date or '最新'} 的招聘信息...")
    print(f"🔢 最大页数: {max_pages}")
    
    async with async_playwright() as p:
        for page_num in range(1, max_pages + 1):
            page_jobs = await fetch_page(page_num, p, target_date)
            
            if not page_jobs and page_num > 1:
                print(f"   📄 第 {page_num} 页无匹配职位，停止")
                break
            
            all_jobs.extend(page_jobs)
            print(f"      找到 {len(page_jobs)} 条匹配职位")
            
            if len(page_jobs) == 0 and page_num >= 3:
                print(f"   连续无匹配，停止翻页")
                break
            
            # 休息一下避免过快请求
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
    parser.add_argument("--date", help="目标年月 YYYY-MM (如 2025-12)", 
                        default=os.environ.get("COLLECT_DATE", ""))
    parser.add_argument("--pages", help="最大页数", type=int,
                        default=int(os.environ.get("MAX_PAGES", "5")))
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    target_date = args.date
    if target_date:
        print(f"🎯 目标日期: {target_date}")
    else:
        print("🎯 目标日期: 最新职位")
    
    jobs = asyncio.run(fetch_list(target_date, args.pages))
    
    if not jobs:
        print("⚠️ 没有找到符合条件的招聘公告")
        return
    
    # 保存
    date_str = target_date.replace("-", "") if target_date else datetime.now().strftime("%Y%m%d")
    output_file = DATA_DIR / f"job_list_{date_str}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 已保存到: {output_file}")
    print(f"📊 共 {len(jobs)} 条职位")
    for i, job in enumerate(jobs[:5], 1):
        print(f"   {i}. {job['title'][:50]}...")


if __name__ == "__main__":
    main()
