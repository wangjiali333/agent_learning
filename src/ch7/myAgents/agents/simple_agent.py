"""简单Agent实现 - 基于OpenAI原生API"""

from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message

from typing import Optional, Iterator


class SimpleAgent(Agent):
    """简单的对话Agent"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        # 调用父类初始化方法即可.
        super().__init__(name, llm, system_prompt, config)

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行简单Agent

        Args:
            input_text: 用户输入问题
            **kwargs: 其他参数

        Returns:
            Agent响应
        """
        # 构建消息列表
        messages = []
        # 添加系统消息(系统提示词), 每条消息的格式: {"role": "角色名", "content": "系统提示词"}
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        # 添加历史消息（ _history是在父类Agent定义的，它是一个列表，用于存储所有消息，内存）
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        # 添加当前用户消息
        messages.append({"role": "user", "content": input_text})
        # 调用LLM
        response = self.llm.invoke(messages, **kwargs)
        # 将当前用户的提问   保存到历史记录
        self.add_message(Message(input_text, "user"))  # 用户的问题
        self.add_message(Message(response, "assistant"))  # llm的回复
        return response

    def stream_run(self, input_text: str, **kwargs):
        """
        流式运行Agent

        Args:
            input_text: 用户输入
            **kwargs: 其他参数

        Yields:
            Agent响应片段
        """
        # 构建消息列表
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})
        # 流式调用LLM
        full_response = ""
        for chunk in self.llm.stream_invoke(
            messages, **kwargs
        ):  # 是一个generator生成器
            full_response += chunk  # 拼装响应片段
            yield chunk

        # 保存完整对话到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))