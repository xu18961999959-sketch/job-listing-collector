
import json
import glob
import re
import os
from datetime import datetime

def extract_salary(text):
    # Match patterns like "3000-5000元", "10-15万", "5k-8k"
    match = re.search(r'(\d+(?:-\d+)?(?:k|K|万|元|kw|KW)(?:/月|/年|/days)?)', text)
    if match:
        return match.group(1)
    return "面议"

def extract_count(text):
    match = re.search(r'(?:招聘|招|人数[：:])\s*(\d+)\s*人?', text)
    if match:
        return f"{match.group(1)}人"
    return "若干"

def extract_education(text):
    match = re.search(r'(高中|中专|大专|本科|硕士|博士|研究生)', text)
    if match:
        return match.group(1)
    return "不限"

def extract_deadline(text):
    # Match dates like 2026年1月20日 or 2026-01-20
    match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', text)
    if match:
        return match.group(1)
    return "详见公告"

def extract_location(text, title, source):
    # Simple heuristic checks
    cities = ["南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", "泰州", "徐州", "盐城", "淮安", "连云港", "宿迁"]
    
    # Check title/source first
    for city in cities:
        if city in title or city in source:
            return f"江苏省{city}市"
            
    # Check text
    for city in cities:
        if city in text:
            return f"江苏省{city}市"
            
    return "江苏省"

def process_batches():
    data_dir = "/Users/xusheng/Desktop/视频素材/课程/智能体/00 skill/0106采集招聘信息/job-listing-collector/data"
    today_str = datetime.now().strftime("%Y%m%d")
    output_file = f"{data_dir}/gongkaoleida_{today_str}.json"
    
    all_jobs = []
    
    # Read all temp batch files
    batch_files = glob.glob(f"{data_dir}/temp_batch_*.json")
    print(f"Found {len(batch_files)} batch files.")
    
    # Load metadata from job_list_*.json
    metadata_map = {}
    job_list_files = glob.glob(f"{data_dir}/job_list_*.json")
    for jf in job_list_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
                for j in jobs:
                    if j.get("url"):
                        metadata_map[j["url"]] = j
        except Exception as e:
            print(f"Error loading {jf}: {e}")

    for fpath in batch_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
            for item in batch_data:
                content = item.get("content", "")
                url = item.get("url", "")
                meta = metadata_map.get(url, {})
                
                title = item.get("title") or meta.get("title", "")
                source = item.get("source") or meta.get("source", "")
                date_val = item.get("date") or meta.get("date", datetime.now().strftime("%Y-%m-%d"))

                job = {
                    "职位名称": title,
                    "招聘单位": source,
                    "薪资范围": extract_salary(content),
                    "工作地点": extract_location(content, title, source),
                    "发布日期": date_val,
                    "来源网站": "公考雷达",
                    "原文链接": item.get("url", ""),
                    "职位描述": content[:2000], # Truncate if too long for Notion text block, though rich_text can handle more, keeping it safe
                    "招聘人数": extract_count(content),
                    "学历要求": extract_education(content),
                    "报名截止": extract_deadline(content),
                    "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                all_jobs.append(job)
    
    # Save combined file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully processed {len(all_jobs)} jobs and saved to {output_file}")
    return output_file

if __name__ == "__main__":
    process_batches()
