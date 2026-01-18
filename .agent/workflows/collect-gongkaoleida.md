---
description: 采集公考雷达招聘信息并同步到 Notion
---

# 公考雷达招聘信息采集工作流

当用户说"采集公考雷达招聘信息"、"采集今天的招聘岗位"或类似指令时，执行以下步骤：

## 配置信息

- **工作目录**: `/Users/xusheng/Desktop/视频素材/课程/智能体/00 skill/0106采集招聘信息/job-listing-collector`
- **数据存储**: `data/gongkaoleida_YYYYMMDD.json`
- **Notion Token**: 使用环境变量 `$NOTION_TOKEN`
- **Notion 数据库**: 📋 招聘信息库

## 执行步骤

### Step 1: 获取招聘列表

1. 使用浏览器访问公考雷达江苏省页面: `https://www.gongkaoleida.com/area/878-0-0-0-124`
2. 筛选当天发布的招聘信息（通过"X小时前"、"今天"等时间标识判断）
3. 提取每条招聘信息的：
   - 职位名称（公告标题）
   - 详情页URL
   - 发布时间
4. 滚动页面确保获取完整列表（通常30条左右）

### Step 2: 获取职位详情

对于重要岗位（如教师招聘、事业单位招聘等），访问详情页补充：
- 招聘单位
- 工作地点
- 招聘人数
- 报名截止日期
- 学历要求
- 职位描述（岗位条件、招聘要求等，100-300字摘要）

**重点关注岗位类型**:
- 教师招聘（编制内）
- 事业单位招聘
- 国企招聘
- 卫生医疗系统招聘
- 公益性岗位

### Step 3: 整理数据并保存 JSON

将采集的数据整理为 JSON 格式，保存到 `data/gongkaoleida_YYYYMMDD.json`

**JSON 格式规范**:
```json
[
    {
        "职位名称": "标题",
        "招聘单位": "单位名称",
        "工作地点": "城市/区县",
        "招聘人数": "X人/若干",
        "发布日期": "YYYY-MM-DD",
        "报名截止": "YYYY-MM-DD 或 见详情页",
        "学历要求": "学历要求",
        "来源网站": "gongkaoleida.com",
        "原文链接": "https://www.gongkaoleida.com/article/XXXXXX",
        "职位描述": "详细描述（100-300字）",
        "状态": "新增"
    }
]
```

**注意事项**:
- JSON 中的双引号必须转义或使用单引号替代
- 确保 JSON 格式正确，可用 `python3 -m json.tool filename.json` 验证

### Step 4: 同步到 Notion

// turbo
运行同步脚本将数据导入 Notion 数据库：

```bash
cd /Users/xusheng/Desktop/视频素材/课程/智能体/00\ skill/0106采集招聘信息/job-listing-collector
python3 sync_to_notion.py data/gongkaoleida_YYYYMMDD.json
```

**同步脚本功能**:
- 自动查找或创建 Notion 数据库
- 根据"原文链接"去重，跳过已存在的记录
- 逐条写入新记录到数据库

### Step 5: 输出执行摘要

同步完成后，输出执行摘要：
- 采集日期
- 采集条数
- 成功/跳过/失败数量
- Notion 数据库链接

## 数据库字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 职位名称 | Title | 招聘公告标题 |
| 招聘单位 | Rich Text | 招聘单位名称 |
| 薪资范围 | Rich Text | 薪资待遇（公考类通常"未公开"） |
| 工作地点 | Rich Text | 工作城市/区县 |
| 发布日期 | Date | 公告发布日期 |
| 来源网站 | Rich Text | gongkaoleida.com |
| 原文链接 | URL | 招聘详情页链接 |
| 职位描述 | Rich Text | 岗位要求、条件摘要 |
| 招聘人数 | Rich Text | 招聘人数 |
| 学历要求 | Rich Text | 学历条件 |
| 报名截止 | Rich Text | 报名截止日期 |
| 采集时间 | Date | 数据采集时间（自动填充） |
| 状态 | Select | 新增/已查看/已申请/已过期 |

## 常见问题

### Q: JSON 解析错误
检查职位描述中是否有未转义的双引号，将 `"XXX"` 改为 `'XXX'`

### Q: Notion 同步失败
检查 Token 是否正确，确保 Notion Integration 已添加到目标页面

### Q: 采集不完整
公考雷达非登录用户只能查看第一页（约30条），如需更多数据需登录
