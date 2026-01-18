# 公考雷达招聘信息采集器

使用 **Claude Agent SDK** 作为工作流核心，自动采集公考雷达网站的招聘信息并同步到 Notion。

## 架构

```
GitHub Actions → agent_workflow.py → Claude Agent SDK
                                          ↓
                     Claude 自主调用工具脚本完成采集任务
```

## 功能特性

- 🤖 **Claude 智能驱动**: 使用 Claude Agent SDK 自主决策和执行
- 🌐 **Playwright 抓取**: 支持 JavaScript 渲染的动态页面
- 📊 **Notion 同步**: 自动去重，避免重复录入
- ⏰ **定时执行**: 每天北京时间 14:00 自动运行

## GitHub Actions 部署

### 1. 推送到 GitHub

```bash
cd job-listing-collector
git init
git add .
git commit -m "feat: Claude Agent SDK 采集工作流"
git remote add origin https://github.com/YOUR_USERNAME/job-listing-collector.git
git push -u origin main
```

### 2. 配置 GitHub Secrets

在仓库 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 说明 | 必需 |
|--------|------|:----:|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | ✅ |
| `NOTION_TOKEN` | Notion Integration Token | ✅ |

### 3. 获取密钥

#### ANTHROPIC_API_KEY
1. 访问 [console.anthropic.com](https://console.anthropic.com/)
2. 创建 API Key

#### NOTION_TOKEN
1. 访问 [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. 创建 Integration，复制 Token
3. 在 Notion 中将 Integration 添加到目标数据库

### 4. 手动触发测试

1. 进入仓库 → **Actions**
2. 选择 **公考雷达招聘信息采集**
3. 点击 **Run workflow**

## 本地运行

```bash
# 安装依赖
pip install claude-agent-sdk playwright beautifulsoup4 requests
playwright install chromium

# 配置环境变量
export ANTHROPIC_API_KEY='your_key'
export NOTION_TOKEN='your_token'

# 运行
python agent_workflow.py
```

## 文件说明

| 文件 | 功能 |
|------|------|
| `agent_workflow.py` | 主入口 (Claude SDK) |
| `CLAUDE.md` | Claude 系统指令 |
| `scripts/scrape_list.py` | 抓取职位列表 |
| `scripts/scrape_detail.py` | 抓取职位详情 |
| `scripts/process_data.py` | 数据处理合并 |
| `scripts/sync_notion.py` | Notion 同步 |
