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
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # 获取标题
            title = await page.title()
            result["title"] = title
            
            # 获取正文内容
            content = await page.evaluate("""
                () => {
                    const selectors = [
                        '.article-content', '.content', '.post-content',
                        '.detail-content', '#content', 'article', '.main'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            return el.innerText;
                        }
                    }
                    return document.body.innerText;
                }
            """)
            
            result["content"] = content[:5000] if content else ""
            
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
    
    details.append(result)
    
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)
    
    if result.get("error"):
        print(f"❌ 失败: {result['error']}")
    else:
        print(f"✅ 成功: {result['title'][:50]}...")
        print(f"   内容长度: {len(result['content'])} 字符")


if __name__ == "__main__":
    main()
