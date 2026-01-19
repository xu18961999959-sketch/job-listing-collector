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
    patterns = [
        r'(年薪[：:]\s*\d+(?:-\d+)?万)',
        r'(月薪[：:]\s*\d+(?:-\d+)?[千元kK])',
        r'(\d+(?:-\d+)?万/年)',
        r'(\d+(?:-\d+)?[千kK]/月)',
        r'(工资[：:]\s*\d+(?:-\d+)?元)',
        r'(\d+(?:-\d+)?(?:k|K|万|元)(?:/月|/年)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "未公开"


def extract_count(text: str) -> str:
    """提取招聘人数"""
    patterns = [
        r'招聘[人数]*[：:\s]*(\d+)\s*[人名]',
        r'招录[人数]*[：:\s]*(\d+)\s*[人名]',
        r'拟招[聘录]*\s*(\d+)\s*[人名]',
        r'招聘岗位\s*(\d+)\s*个',
        r'名额[：:]\s*(\d+)',
        r'共[招聘录]*\s*(\d+)\s*[人名]',
        r'招\s*(\d+)\s*人',
        r'(\d+)\s*个岗位',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)}人"
    return "若干"


def extract_education(text: str) -> str:
    """提取学历要求"""
    patterns = [
        r'学历[要求：:]*\s*(高中|中专|大专|本科|硕士|博士|研究生)(?:及以上|以上|学历)?',
        r'(全日制本科|全日制硕士|全日制博士|全日制研究生)',
        r'(本科及以上|硕士及以上|博士及以上|大专及以上)',
        r'(本科|硕士|博士|研究生|大专|高中|中专)(?:及以上|以上|学历)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result = match.group(1) if match.lastindex else match.group(0)
            return result
    
    # 简单匹配
    if "博士" in text:
        return "博士"
    if "硕士" in text or "研究生" in text:
        return "硕士及以上"
    if "本科" in text:
        return "本科及以上"
    if "大专" in text:
        return "大专及以上"
    
    return "详见公告"


def extract_deadline(text: str) -> str:
    """提取报名截止日期"""
    patterns = [
        r'报名[时间截止]*[：:至到]*\s*(\d{4}年\d{1,2}月\d{1,2}日)',
        r'截止[时间日期]*[：:至到]*\s*(\d{4}年\d{1,2}月\d{1,2}日)',
        r'报名.*?至.*?(\d{4}年\d{1,2}月\d{1,2}日)',
        r'(\d{4}-\d{1,2}-\d{1,2}).*?(?:截止|结束)',
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "详见公告"


def extract_location(text: str, title: str = "") -> str:
    """提取工作地点"""
    combined = title + " " + text
    
    # 江苏省城市列表
    cities = {
        "南京": "南京市",
        "苏州": "苏州市", 
        "无锡": "无锡市",
        "常州": "常州市",
        "南通": "南通市",
        "扬州": "扬州市",
        "镇江": "镇江市",
        "泰州": "泰州市",
        "徐州": "徐州市",
        "盐城": "盐城市",
        "淮安": "淮安市",
        "连云港": "连云港市",
        "宿迁": "宿迁市",
        "昆山": "苏州市昆山",
        "张家港": "苏州市张家港",
        "常熟": "苏州市常熟",
        "江阴": "无锡市江阴",
        "宜兴": "无锡市宜兴",
    }
    
    for city, full_name in cities.items():
        if city in combined:
            return f"江苏省{full_name}"
    
    return "江苏省"


def extract_employer(text: str, title: str = "") -> str:
    """提取招聘单位"""
    patterns = [
        r'招聘单位[：:]\s*([^\n,，]{2,30})',
        r'用人单位[：:]\s*([^\n,，]{2,30})',
        r'主管单位[：:]\s*([^\n,，]{2,30})',
        r'主办[单位]*[：:]\s*([^\n,，]{2,30})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    # 从标题提取
    # 如 "2026年南京市XXX招聘公告" -> "南京市XXX"
    match = re.search(r'(\d{4}年)?(.{2,20}?)(公开)?招[聘录]', title)
    if match:
        employer = match.group(2).strip()
        if len(employer) >= 4:
            return employer
    
    return ""


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
        content = detail.get("content", "") or ""
        title = job.get("title", detail.get("title", ""))
        
        # 提取招聘单位
        employer = job.get("source", "") or extract_employer(content, title)
        
        processed = {
            "职位名称": title or "未知职位",
            "招聘单位": employer,
            "薪资范围": extract_salary(content),
            "工作地点": extract_location(content, title),
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
    
    # 打印示例
    if results:
        print(f"\n📊 示例数据:")
        sample = results[0]
        print(f"   职位: {sample['职位名称'][:40]}")
        print(f"   单位: {sample['招聘单位']}")
        print(f"   人数: {sample['招聘人数']}")
        print(f"   学历: {sample['学历要求']}")
        print(f"   截止: {sample['报名截止']}")
    
    # 清理临时文件
    if details_file.exists():
        details_file.unlink()
        print("🧹 已清理临时文件")


if __name__ == "__main__":
    main()
