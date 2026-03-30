import os
import asyncio
from typing import Any, AsyncGenerator, List, Dict, Mapping, Optional, Sequence, Union

import anthropic
from dotenv import load_dotenv

from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
)
from autogen_core import CancellationToken

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Custom AutoGen model client — wraps anthropic.Anthropic directly
# ─────────────────────────────────────────────────────────────────────────────

class CustomAnthropicClient(ChatCompletionClient):
    """
    AutoGen-compatible model client built on top of the Anthropic SDK.
    Works with any Anthropic-protocol endpoint (official, MiniMax, One-API…)
    without depending on autogen-ext[openai].
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ):
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    async def close(self) -> None:
        """
        关闭客户端并清理资源。
        即使目前没有需要手动关闭的 session，也必须定义此方法。
        """
        pass
    # ── AutoGen required interface ────────────────────────────────────────────

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=False,
            json_output=False,
            family="unknown",
        )

    @property
    def capabilities(self):
        return self.model_info

    def count_tokens(self, messages: Sequence[LLMMessage], **kwargs) -> int:
        total = sum(len(str(m.content)) for m in messages)
        return total // 4

    def remaining_tokens(self, messages: Sequence[LLMMessage], **kwargs) -> int:
        return self._max_tokens - self.count_tokens(messages)

    @property
    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens,
        )

    @property
    def actual_usage(self) -> RequestUsage:
        return self.total_usage

    # ── Message format conversion ─────────────────────────────────────────────

    @staticmethod
    def _to_anthropic_messages(
        messages: Sequence[LLMMessage],
    ) -> tuple[str, list[dict]]:
        """Convert AutoGen LLMMessage list → (system_prompt, anthropic_messages)."""
        system_prompt = ""
        anthropic_messages: list[dict] = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content

            elif isinstance(msg, UserMessage):
                content = msg.content
                if isinstance(content, list):
                    parts = [
                        {"type": "text", "text": part.text}
                        for part in content
                        if hasattr(part, "text")
                    ]
                    content = parts or str(content)
                anthropic_messages.append({"role": "user", "content": content})

            elif isinstance(msg, AssistantMessage):
                anthropic_messages.append(
                    {"role": "assistant", "content": str(msg.content)}
                )

            elif isinstance(msg, FunctionExecutionResultMessage):
                results_text = "\n".join(
                    f"[Tool result for {r.call_id}]: {r.content}"
                    for r in msg.content
                )
                anthropic_messages.append({"role": "user", "content": results_text})

        return system_prompt, anthropic_messages

    # ── Core create (non-streaming) ───────────────────────────────────────────

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:

        system_prompt, anthropic_messages = self._to_anthropic_messages(messages)

        # ⚠️  Must use get_running_loop() inside an async context (Python ≥ 3.10)
        loop = asyncio.get_running_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system_prompt,
                    messages=anthropic_messages,
                    temperature=self._temperature,
                    **extra_create_args,
                ),
            )
        except Exception as exc:
            # Surface the error instead of swallowing it — agents will fail
            # loudly rather than silently producing empty messages.
            raise RuntimeError(f"[CustomAnthropicClient] API call failed: {exc}") from exc

        reply_text = ""
        for block in response.content:
            if block.type == "text":
                reply_text += block.text
            # thinking blocks are intentionally skipped in non-stream mode

        usage = RequestUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )
        self._total_prompt_tokens += usage.prompt_tokens
        self._total_completion_tokens += usage.completion_tokens

        return CreateResult(
            finish_reason="stop",
            content=reply_text,
            usage=usage,
            cached=False,
            logprobs=None,
        )

    # ── Streaming create ──────────────────────────────────────────────────────

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:

        system_prompt, anthropic_messages = self._to_anthropic_messages(messages)
        collected: list[str] = []

        # ⚠️  get_running_loop() — correct inside async context
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[str | Exception]] = asyncio.Queue()

        def _stream_worker():
            try:
                with self._client.messages.stream(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system_prompt,
                    messages=anthropic_messages,
                    temperature=self._temperature,
                    **extra_create_args,
                ) as stream:
                    for event in stream:
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                asyncio.run_coroutine_threadsafe(
                                    queue.put(event.delta.text), loop
                                )
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

        loop.run_in_executor(None, _stream_worker)

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise RuntimeError(f"[CustomAnthropicClient] Stream error: {item}") from item
            collected.append(item)
            yield item

        full_text = "".join(collected)
        yield CreateResult(
            finish_reason="stop",
            content=full_text,
            usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
            cached=False,
            logprobs=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_autogen_model_client(
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> CustomAnthropicClient:
    model    = model    or os.getenv("LLM_MODEL_ID")
    api_key  = api_key  or os.getenv("LLM_API_KEY")
    base_url = base_url or os.getenv("LLM_BASE_URL")

    if not all([model, api_key, base_url]):
        raise ValueError("模型ID、API密钥和服务地址不能为空（参数或环境变量）。")

    return CustomAnthropicClient(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        temperature=temperature,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Standalone LLM class（独立测试用，与 AutoGen 无关）
# ─────────────────────────────────────────────────────────────────────────────

class LLM:
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None):
        self.model = model or os.getenv("LLM_MODEL_ID")
        api_key    = apiKey   or os.getenv("LLM_API_KEY")
        base_url   = baseUrl  or os.getenv("LLM_BASE_URL")

        if not all([self.model, api_key, base_url]):
            raise ValueError("模型ID、API密钥和服务地址不能为空。")

        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        print(f"🧠 正在通过 Anthropic 协议调用 {self.model} 模型...")

        system_content = ""
        user_messages  = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)

        try:
            collected_text = []
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system_content,
                messages=user_messages,
                temperature=temperature,
            ) as stream:
                print("✅ 建立连接，输出内容：")
                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            print(f"\033[90m{event.delta.thinking}\033[0m", end="", flush=True)
                        elif event.delta.type == "text_delta":
                            print(event.delta.text, end="", flush=True)
                            collected_text.append(event.delta.text)
            print()
            return "".join(collected_text)

        except Exception as e:
            print(f"❌ 调用失败: {e}")
            return None


if __name__ == "__main__":
    llm_client = LLM()
    llm_client.think([
        {"role": "system", "content": "你是一个严谨的助手。"},
        {"role": "user",   "content": "1.11 和 1.9 哪个大？"},
    ])