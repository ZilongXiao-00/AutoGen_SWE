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
| **User Proxy** | 任务发起、代码执行、结果验证、终止信号 |

## Agent 技术能力

### 多智能体协作
- **角色扮演**：每个智能体有明确的职责和专业知识
- **轮转机制**：使用 `RoundRobinGroupChat` 实现有序协作
- **终止控制**：通过 `TextMentionTermination` 自动检测任务完成

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

1. **任务发起**：User Proxy 提交开发需求
2. **需求分析**：Product Manager 分析需求，制定实现计划
3. **编码实现**：Engineer 根据计划编写代码
4. **代码审查**：Code Reviewer 检查代码质量，提出改进意见
5. **验证执行**：如需调整，返回 Engineer 重写；如通过，User Proxy 执行测试
6. **任务终止**：Code Reviewer 确认通过后输出 `TERMINATE`

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

### 多智能体协作的优势

**专业化分工**

每个智能体专注于自己的领域（如产品规划、代码编写、代码审查），模拟真实团队的专业分工，提高输出质量。

**流程自动化**

传统软件开发需要人工协调各环节，而多智能体系统可以自动完成产品分析→开发→审查的完整流程。

**可扩展的工作流**

通过调整智能体组合和工作流程，可以适应不同类型的软件开发任务。

### 技术挑战

**协作一致性**

多个智能体需要协调一致地工作，避免输出冲突或循环依赖。

**质量控制**

需要有效的审查机制（如 Code Reviewer）确保最终代码质量。

**成本与效率**

多智能体意味着多次 LLM 调用，需要在质量和效率间找到平衡。
