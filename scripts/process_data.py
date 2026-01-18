#!/usr/bin/env python3
"""
处理并合并采集数据

读取: data/job_list_*.json, data/temp_details.json
输出: data/gongkaoleida_YYYYMMDD.json
"""

import glob
import json
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def extract_salary(text: str) -> str:
    """提取薪资信息"""
    match = re.search(r'(\d+(?:-\d+)?(?:k|K|万|元)(?:/月|/年)?)', text)
    return match.group(1) if match else "面议"


def extract_count(text: str) -> str:
    """提取招聘人数"""
    match = re.search(r'(?:招聘|招|人数[：:])?\s*(\d+)\s*人', text)
    return f"{match.group(1)}人" if match else "若干"


def extract_education(text: str) -> str:
    """提取学历要求"""
    match = re.search(r'(高中|中专|大专|本科|硕士|博士|研究生)(?:及以上|以上)?', text)
    return match.group(0) if match else "不限"


def extract_deadline(text: str) -> str:
    """提取报名截止日期"""
    match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', text)
    return match.group(1) if match else "详见公告"


def extract_location(text: str) -> str:
    """提取工作地点"""
    cities = ["南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", 
              "泰州", "徐州", "盐城", "淮安", "连云港", "宿迁"]
    for city in cities:
        if city in text:
            return f"江苏省{city}市"
    return "江苏省"


def main():
    today_str = datetime.now().strftime("%Y%m%d")
    
    # 加载职位列表
    list_files = sorted(DATA_DIR.glob("job_list_*.json"), reverse=True)
    if not list_files:
        print("❌ 未找到职位列表文件")
        return
    
    job_list = []
    for f in list_files[:1]:  # 只取最新的
        with open(f, "r", encoding="utf-8") as fp:
            job_list = json.load(fp)
    
    print(f"📋 加载职位列表: {len(job_list)} 条")
    
    # 加载详情
    details_file = DATA_DIR / "temp_details.json"
    details = []
    if details_file.exists():
        with open(details_file, "r", encoding="utf-8") as f:
            details = json.load(f)
    
    print(f"📄 加载详情: {len(details)} 条")
    
    # 建立 URL -> 详情 映射
    detail_map = {d["url"]: d for d in details}
    
    # 合并处理
    results = []
    for job in job_list:
        url = job.get("url", "")
        detail = detail_map.get(url, {})
        content = detail.get("content", "")
        
        processed = {
            "职位名称": job.get("title", detail.get("title", "未知职位")),
            "招聘单位": job.get("source", ""),
            "薪资范围": extract_salary(content),
            "工作地点": extract_location(content + job.get("title", "")),
            "发布日期": job.get("date", datetime.now().strftime("%Y-%m-%d")),
            "来源网站": "公考雷达",
            "原文链接": url,
            "职位描述": content[:2000] if content else "",
            "招聘人数": extract_count(content),
            "学历要求": extract_education(content),
            "报名截止": extract_deadline(content),
            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(processed)
    
    # 保存
    output_file = DATA_DIR / f"gongkaoleida_{today_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 处理完成: {len(results)} 条")
    print(f"💾 输出文件: {output_file}")
    
    # 清理临时文件
    if details_file.exists():
        details_file.unlink()
        print("🧹 已清理临时文件")


if __name__ == "__main__":
    main()
