import asyncio

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console

from agents import (
    create_product_manager,
    create_engineer,
    create_code_reviewer,
    create_user_proxy,
)
from llm_cli import create_autogen_model_client


# ── 任务描述 ────────────────────────────────────────────────────────────────
TASK = """
我们需要开发一个标普500ETF价格显示应用，具体要求如下：

核心功能：
- 实时显示标普500ETF当前价格（USD）
- 显示24小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

请团队协作完成这个任务，从需求分析到最终实现。
当所有工作完成并且代码已通过审查时，请输出 TERMINATE。
""".strip()


async def run_software_development_team() -> None:
    # ── 1. 创建 AutoGen 兼容的模型客户端 ────────────────────────────────────
    model_client = create_autogen_model_client()

    # ── 2. 初始化各角色智能体 ────────────────────────────────────────────────
    product_manager = create_product_manager(model_client)
    engineer = create_engineer(model_client)
    code_reviewer = create_code_reviewer(model_client)
    user_proxy = create_user_proxy()          # 通常不需要 model_client

    # ── 3. 组建 RoundRobin 团队 ──────────────────────────────────────────────
    termination_condition = TextMentionTermination("TERMINATE")

    team_chat = RoundRobinGroupChat(
        participants=[
            product_manager,
            engineer,
            code_reviewer,
            user_proxy,
        ],
        termination_condition=termination_condition,
        max_turns=20,
    )

    # ── 4. 流式运行并打印对话过程 ────────────────────────────────────────────
    print("🚀 软件开发团队启动，开始协作...\n")
    result = await Console(team_chat.run_stream(task=TASK))

    # ── 5. 打印最终摘要 ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ 团队协作结束")
    print(f"共进行了 {len(result.messages)} 轮对话")
    print("=" * 60)

    return result


# ── 主程序入口 ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(run_software_development_team())