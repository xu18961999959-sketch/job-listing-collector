#!/usr/bin/env python3
"""
抓取单个职位详情

使用方法:
    python scripts/scrape_detail.py --url "https://..."

输出: 追加到 data/temp_details.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


async def fetch_detail(url: str) -> dict:
    """使用 Playwright 抓取职位详情"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 请安装 playwright")
        return {"url": url, "content": "", "error": "playwright not installed"}
    
    result = {"url": url, "content": "", "title": ""}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(3)  # 等待 JS 渲染
            
            # 获取标题
            title = await page.title()
            result["title"] = title
            
            # 尝试多种选择器获取正文内容
            content = await page.evaluate("""
                () => {
                    // 公考雷达特定选择器
                    const selectors = [
                        '.article-content',
                        '.detail-content', 
                        '.content-wrap',
                        '.post-content',
                        '.news-content',
                        '.main-content',
                        '#article-content',
                        '#content',
                        'article',
                        '.content',
                        '.main',
                        '[class*="content"]',
                        '[class*="article"]',
                        '[class*="detail"]'
                    ];
                    
                    for (const sel of selectors) {
                        try {
                            const el = document.querySelector(sel);
                            if (el && el.innerText && el.innerText.length > 100) {
                                return el.innerText.trim();
                            }
                        } catch(e) {}
                    }
                    
                    // 如果没找到，获取 body 内容但排除导航等
                    const body = document.body.cloneNode(true);
                    const removeSelectors = ['nav', 'header', 'footer', '.nav', '.header', '.footer', '.sidebar', 'script', 'style'];
                    removeSelectors.forEach(sel => {
                        body.querySelectorAll(sel).forEach(el => el.remove());
                    });
                    
                    return body.innerText.trim();
                }
            """)
            
            result["content"] = content[:8000] if content else ""
            
            # 额外提取日期信息
            date_text = await page.evaluate("""
                () => {
                    const dateSelectors = ['.date', '.time', '.publish-time', '.post-date', '[class*="date"]', '[class*="time"]'];
                    for (const sel of dateSelectors) {
                        try {
                            const el = document.querySelector(sel);
                            if (el) return el.innerText.trim();
                        } catch(e) {}
                    }
                    return '';
                }
            """)
            if date_text:
                result["date_text"] = date_text
            
        except Exception as e:
            result["error"] = str(e)
            print(f"⚠️ 抓取失败: {e}")
        finally:
            await browser.close()
    
    return result


def main():
    parser = argparse.ArgumentParser(description="抓取职位详情")
    parser.add_argument("--url", required=True, help="职位详情URL")
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 正在抓取: {args.url[:60]}...")
    result = asyncio.run(fetch_detail(args.url))
    
    # 追加到临时文件
    temp_file = DATA_DIR / "temp_details.json"
    
    details = []
    if temp_file.exists():
        with open(temp_file, "r", encoding="utf-8") as f:
            try:
                details = json.load(f)
            except:
                details = []
    
    # 检查是否已存在
    existing_urls = {d.get("url") for d in details}
    if args.url not in existing_urls:
        details.append(result)
    
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)
    
    if result.get("error"):
        print(f"❌ 失败: {result['error']}")
    else:
        content_len = len(result.get('content', ''))
        print(f"✅ 成功: {result.get('title', 'N/A')[:40]}...")
        print(f"   内容长度: {content_len} 字符")
        if content_len < 100:
            print(f"   ⚠️ 内容可能提取不完整")


if __name__ == "__main__":
    main()
