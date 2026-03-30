# AutoGen SWE

基于 **Microsoft AutoGen** 框架的多智能体软件开发团队，模拟真实开发流程进行协作式代码生成。

## 核心思想

通过多智能体协作，模拟真实软件团队的开发流程。每个智能体扮演特定角色，分工明确，协作完成复杂任务。

```
User Proxy → Product Manager → Engineer → Code Reviewer → User Proxy → ...
                    (Round Robin 轮转协作)
```

## 智能体角色

| 角色 | 职责 |
|------|------|
| **Product Manager** | 需求分析、功能规划、技术选型、风险评估 |
| **Engineer** | 代码编写、技术实现、错误处理 |
| **Code Reviewer** | 代码质量审查、安全检查、最佳实践验证 |
| **User Proxy** | 用户验收、功能测试、反馈收集 |

## Agent 技术能力

### 多智能体协作
- **角色扮演**：每个智能体有明确的职责和专业知识
- **轮转机制**：使用 `RoundRobinGroupChat` 实现有序协作
- **终止控制**：双重终止条件 `TextMentionTermination` + `MaxMessageTermination`，防止无限循环

### AutoGen 框架特性
- **流式输出**：实时展示智能体思考和对话过程
- **异步执行**：基于 asyncio 的高效并发处理
- **可扩展性**：易于添加新角色、调整工作流程

### 自定义模型支持
- **CustomAnthropicClient**：兼容 AutoGen 的 Anthropic SDK 封装
- **多后端支持**：兼容 MiniMax 等 Anthropic 兼容端点
- **流式响应**：支持思考过程（thinking）和文本输出的分离展示

## 项目结构

```
AutoGen_SWE/
├── RoundRobinGroupChat.py   # 团队主入口，配置多智能体协作
├── agents.py                # 智能体工厂，定义各角色
├── llm_cli.py               # 模型客户端封装
└── README.md
```

## 工作流程

1. **需求分析**：Product Manager 分析需求，输出需求文档
2. **编码实现**：Engineer 根据需求文档编写完整代码
3. **代码审查**：Code Reviewer 审查代码质量，给出改进意见
4. **迭代优化**：如有问题，Engineer 根据审查意见修改代码
5. **任务终止**：Product Manager 确认所有需求已满足后输出 `TERMINATE`

## 快速运行

```bash
pip install autogen-agentchat autogen-core anthropic dotenv
export LLM_API_KEY=your_key
export LLM_MODEL_ID=your_model
export LLM_BASE_URL=https://api.minimaxi.com/anthropic
python RoundRobinGroupChat.py
```

## 可扩展性

- **添加新角色**：在 `agents.py` 中定义新智能体类型
- **调整协作流程**：修改 `RoundRobinGroupChat` 的参与者列表和顺序
- **自定义终止条件**：实现 `TerminationCondition` 接口
- **集成工具**：为智能体添加代码执行、搜索等工具能力

## 思考

### 1. 优势

**简化流程控制**

无需为智能体团队设计复杂的状态机或控制流逻辑，只需将软件开发流程自然地映射为角色之间的对话。这种方式更贴近人类协作模式，降低了复杂任务建模的门槛。开发者只需关注”谁（角色）”和”做什么（职责）”，而非”如何做（流程控制）”。

**角色专业化与复用**

通过系统消息（System Message）为每个智能体赋予高度专业化的角色。精心设计的智能体可以在不同项目中被复用，易于维护和扩展。

**清晰的协作流程**

`RoundRobinGroupChat` 提供了可预测的顺序化协作机制。同时，`UserProxyAgent` 为”人类在环”（Human-in-the-loop）提供了天然接口，既可以作为任务发起者，也可以是监督者和最终验收者，确保自动化系统始终处于人类监督之下。

### 2. 局限性

**对话不确定性**

虽然 `RoundRobinGroupChat` 提供了顺序化的流程，但基于 LLM 的对话本质上具有不确定性。智能体可能产生偏离预期的回复，导致对话走向意外分支，甚至陷入循环。

**调试困难**

当智能体团队的工作结果未达预期时，调试过程可能非常棘手。与传统程序不同，我们得到的不是清晰的错误堆栈，而是一长串的对话历史，这被称为”对话式调试”的难题。
## AutoGen 框架深度解析

### 1. 分层架构

AutoGen 采用清晰的分层设计：

- `autogen-core`：底层基础，封装语言模型交互、消息传递等核心功能，保证框架的稳定性和扩展性
- `autogen-agentchat`：构建于 core 之上，提供对话式智能体应用的高级接口，简化多智能体开发流程

这种分层策略使各组件职责明确，降低系统耦合度。

### 2. 异步优先

框架全面采用异步编程 (async/await)。在多智能体协作中，网络请求是主要耗时操作。异步模式允许系统在等待一个智能体响应时处理其他任务，避免线程阻塞，显著提升并发处理能力。

### 3. 核心智能体

**AssistantAgent（助理智能体）**

任务的主要解决者，封装了大型语言模型（LLM）。根据对话历史生成回复，通过系统消息（System Message）赋予不同的"专家"角色。

**UserProxyAgent（用户代理智能体）**

功能独特的组件，扮演双重角色：
- 人类用户的"代言人"，负责发起任务和传达意图
- 可靠的"执行器"，可配置执行代码或调用工具

这种设计清晰区分了"思考"（AssistantAgent）与"行动"。

### 4. 群聊协作机制

`RoundRobinGroupChat` 是一种顺序化的对话协调机制，让智能体按预定义顺序依次发言。

**工作流程**

1. 创建 `RoundRobinGroupChat` 实例，添加参与协作的智能体
2. 群聊按预设顺序依次激活智能体
3. 被选中的智能体根据当前对话上下文进行响应
4. 新回复加入对话历史，激活下一个智能体
5. 持续进行，直到达到最大轮次或满足终止条件

AutoGen 将复杂的协作关系简化为清晰的自动化"圆桌会议"。开发者只需定义角色和发言顺序，协作流程由群聊机制自主驱动。
