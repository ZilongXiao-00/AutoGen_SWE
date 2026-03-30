import asyncio

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console

from agents import (
    create_product_manager,
    create_engineer,
    create_code_reviewer,
    create_user_proxy,
)
from llm_cli import create_autogen_model_client


# ── 任务描述 ─────────────────────────────────────────────────────────────────
# ⚠️ 任务描述中不要包含 "TERMINATE"，否则 TextMentionTermination 会立即触发
TASK = """
我们需要开发一个标普500 ETF 价格显示应用，具体要求如下：

核心功能：
- 实时显示标普500 ETF（代码：SPY）当前价格（USD）
- 显示24小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格手动刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 使用 yfinance 库获取价格数据
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

请团队协作完成这个任务，按照以下流程：
1. ProductManager 先输出需求文档
2. Engineer 根据需求文档编写完整代码
3. CodeReviewer 审查代码并给出意见
4. Engineer 根据审查意见修改代码（若有问题）
5. ProductManager 确认所有需求已满足后结束任务
""".strip()


async def run_software_development_team() -> None:
    print("🔧 初始化模型客户端...")
    model_client = create_autogen_model_client()
    print(f"✅ 模型客户端就绪：{model_client._model}")

    print("🤖 初始化智能体...")
    product_manager = create_product_manager(model_client)
    engineer        = create_engineer(model_client)
    code_reviewer   = create_code_reviewer(model_client)
    user_proxy      = create_user_proxy()
    print("✅ 4 个智能体已就绪\n")

    # 双重终止条件：
    #   1. TextMentionTermination  — 正常完成时由 ProductManager 发出 TERMINATE
    #   2. MaxMessageTermination   — 保底，防止无限循环（20 条消息）
    termination = (
        TextMentionTermination("TERMINATE")
        | MaxMessageTermination(max_messages=20)
    )

    team_chat = RoundRobinGroupChat(
        participants=[
            product_manager,   # 轮次 1：需求分析
            engineer,          # 轮次 2：编写代码
            code_reviewer,     # 轮次 3：代码审查
            user_proxy,        # 轮次 4：用户验收（静默代理，不调用 LLM）
        ],
        termination_condition=termination,
        max_turns=20,
    )

    print("🚀 软件开发团队启动，开始协作...\n")
    result = await Console(team_chat.run_stream(task=TASK))

    # ── 结果摘要 ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ 团队协作结束")
    msg_count = len(result.messages) if hasattr(result, "messages") else "N/A"
    print(f"共进行了 {msg_count} 轮对话")
    stop_reason = getattr(result, "stop_reason", "未知")
    print(f"终止原因：{stop_reason}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(run_software_development_team())