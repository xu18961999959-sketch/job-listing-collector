#!/usr/bin/env python3
"""
Claude Agent SDK 驱动的公考雷达采集工作流

使用 Claude 作为"大脑"，自主调用工具脚本完成采集任务。

使用方法:
    python agent_workflow.py

环境变量:
    ANTHROPIC_API_KEY - Claude API 密钥
    NOTION_TOKEN - Notion Integration Token
"""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

# 尝试导入 Claude SDK
try:
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


def get_system_prompt() -> str:
    """读取 CLAUDE.md 作为系统指令"""
    claude_md = PROJECT_DIR / "CLAUDE.md"
    if claude_md.exists():
        return claude_md.read_text(encoding="utf-8")
    return """你是一个招聘信息采集助手。请执行以下步骤：
1. 运行 python scripts/scrape_list.py 获取职位列表
2. 对每个职位运行 python scripts/scrape_detail.py --url <URL>
3. 运行 python scripts/process_data.py 处理数据
4. 运行 python scripts/sync_notion.py 同步到 Notion
"""


def validate_environment() -> bool:
    """验证必要的环境变量"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ 未设置 ANTHROPIC_API_KEY")
        return False
    if not os.environ.get("NOTION_TOKEN"):
        print("❌ 未设置 NOTION_TOKEN")
        return False
    return True


async def run_with_claude():
    """使用 Claude Agent SDK 运行工作流"""
    print("🤖 启动 Claude Agent 模式...")
    
    options = ClaudeAgentOptions(
        system_prompt=get_system_prompt(),
        max_turns=30,  # 允许足够的交互轮次
        allowed_tools=["Bash", "Read", "Write"],
        permission_mode="acceptEdits",
        cwd=str(PROJECT_DIR),
    )
    
    client = ClaudeSDKClient(options)
    
    prompt = """请执行今日的公考雷达招聘信息采集任务。

按照 CLAUDE.md 中定义的步骤执行：
1. 首先运行 scripts/scrape_list.py 获取职位列表
2. 查看输出的 job_list 文件，获取职位 URL
3. 对每个职位运行 scripts/scrape_detail.py --url "<URL>" 获取详情
4. 运行 scripts/process_data.py 处理数据  
5. 运行 scripts/sync_notion.py 同步到 Notion
6. 输出采集统计报告

开始执行。"""
    
    try:
        async for message in client.query(prompt):
            if hasattr(message, 'text'):
                print(message.text)
            elif hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(block.text)
    except Exception as e:
        print(f"❌ Claude Agent 执行出错: {e}")
        return False
    finally:
        await client.close()
    
    return True


async def run_fallback():
    """回退到直接执行模式（不使用 Claude SDK）"""
    import subprocess
    
    print("📋 直接执行模式 (无 Claude SDK)...")
    
    scripts = [
        ("scrape_list.py", []),
        ("process_data.py", []),
        ("sync_notion.py", [])
    ]
    
    for script, args in scripts:
        script_path = PROJECT_DIR / "scripts" / script
        print(f"\n🔄 运行: {script}")
        
        cmd = [sys.executable, str(script_path)] + args
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            print(f"⚠️ {script} 执行失败")
    
    return True


async def main():
    """主入口"""
    print("🚀 公考雷达招聘信息采集工作流")
    print(f"⏰ 执行时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not validate_environment():
        sys.exit(1)
    
    # 优先使用 Claude SDK
    if CLAUDE_SDK_AVAILABLE:
        success = await run_with_claude()
    else:
        print("⚠️ Claude SDK 未安装，使用直接执行模式")
        success = await run_fallback()
    
    if success:
        print("\n🎉 采集工作流完成!")
    else:
        print("\n❌ 采集工作流失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
