---
description: 采集江苏省人社厅和公考雷达招聘信息并同步到 Notion
---

# 江苏省招聘信息采集工作流

## 全局配置

### Notion 配置
- **Token**: 使用环境变量 `$NOTION_TOKEN`
- **数据库名称**: 📋 招聘信息库
- **数据库链接**: https://www.notion.so/2e07d626c84e81a5b57fea92a936e2cd

### 同步命令
// turbo
```bash
cd /Users/xusheng/Desktop/视频素材/课程/智能体/00\ skill/采集招聘信息/job-listing-collector && python3 sync_to_notion.py
```

---

# ⚠️ 采集规则（必须遵守）

## 1. 必须访问详情页
- ❌ 不能只从列表页采集标题和链接
- ✅ 必须点击进入每个详情页获取完整内容

## 2. 附件提取规则
- ❌ 不能捏造假的附件 URL
- ✅ 只提取页面上存在的真实文件链接
- ✅ 匹配文件扩展名: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`
- ✅ 真实附件通常来自: `static.gongkaoleida.com`

附件提取 JavaScript:
```javascript
const attachments = [];
document.querySelectorAll('a').forEach(a => {
  const href = a.href;
  const text = a.innerText.trim();
  if (href.match(/\.(pdf|doc|docx|xls|xlsx)(\?|$)/i)) {
    attachments.push({name: text || href.split('/').pop(), url: href});
  }
});
```

## 3. 去重处理
- 同步前会自动检查 Notion 数据库中已有的 URL
- 重复记录会被跳过，避免数据冗余

## 4. 分页采集
- 网站有多页时，需要逐页采集
- 分页格式: `?page=1`, `?page=2`, ...

---

# 数据源 1: 江苏省人社厅

## 配置信息
- **网站**: 江苏省人力资源和社会保障厅
- **栏目**: 省属事业单位招聘
- **URL**: https://jshrss.jiangsu.gov.cn/col/col78506/index.html

## 采集步骤
1. 打开列表页获取所有公告链接
2. 逐个访问详情页提取完整信息
3. 保存到 `data/jiangsu_jobs_YYYYMM.json`
4. 运行同步命令

---

# 数据源 2: 公考雷达

## 配置信息
- **网站**: 公考雷达
- **栏目**: 江苏省招聘公告
- **URL**: https://www.gongkaoleida.com/area/878
- **分页**: `?page=1` 到 `?page=334`

## 详情页提取脚本
```javascript
(() => {
  const result = {};
  
  // 标题
  result.职位名称 = document.querySelector('h1, h2.detail-title')?.innerText
    .replace(/查看相关职位|关注|分享/g, '').trim();
  
  // 日期
  const dateMatch = document.body.innerText.match(/(\d{4}-\d{2}-\d{2})/);
  result.发布日期 = dateMatch ? dateMatch[1] : '';
  
  // 内容
  const contentEl = document.querySelector('.article-content, .detail-content');
  if (contentEl) {
    result.职位描述 = contentEl.innerText.trim().substring(0, 2000);
  }
  
  // 真实附件
  result.附件列表 = [];
  document.querySelectorAll('a').forEach(a => {
    if (a.href.match(/\.(pdf|doc|docx|xls|xlsx)(\?|$)/i)) {
      result.附件列表.push({
        name: a.innerText.trim() || a.href.split('/').pop(),
        url: a.href
      });
    }
  });
  
  // 来源
  const sourceEl = document.querySelector('.article-info a');
  if (sourceEl) {
    result.原始来源 = sourceEl.href;
    result.来源名称 = sourceEl.innerText.trim();
  }
  
  result.原文链接 = window.location.href;
  result.工作地点 = '江苏省';
  result.来源网站 = 'gongkaoleida.com';
  
  return JSON.stringify(result, null, 2);
})()
```

---

# 数据字段说明

| 字段 | 说明 | 必填 |
|------|------|------|
| 职位名称 | 公告标题 | ✅ |
| 发布日期 | 格式 YYYY-MM-DD | ✅ |
| 原文链接 | 详情页 URL | ✅ |
| 职位描述 | 完整内容（最多2000字） | ✅ |
| 附件列表 | 真实文件下载链接 | 如有 |
| 原始来源 | 官方网站链接 | 如有 |
| 来源名称 | 发布机构名称 | 如有 |
| 工作地点 | 默认"江苏省" | ✅ |
| 招聘人数 | 从内容提取 | 如有 |
| 报名截止 | 从内容提取 | 如有 |

---

# 常见错误提醒

1. **不要只采集列表页** - 必须访问每个详情页
2. **不要编造附件链接** - 只使用页面上真实存在的 URL
3. **注意分页** - 网站可能有几百页数据
4. **保存中间结果** - 采集过程中保存到 JSON 文件
5. **测试去重** - 同步前确认已存在的记录会被跳过
