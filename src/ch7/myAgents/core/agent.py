"""Agent基类:它用来定义agent的基本属性和方法"""

from abc import ABC, abstractmethod
from typing import Optional

from myAgents.core.config import Config
from myAgents.core.message import Message
from myAgents.core.llm import HelloAgentsLLM


class Agent(ABC):
    """Agent基类"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """初始化Agent

        args:
          name: agent的名称
          llm: 用于agent的LLM模型
          system_prompt: 系统提示词
          config: 配置参数

        """
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []  # 历史对话记录

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent"""
        pass

    def add_message(self, message: Message):
        """添加消息到历史记录"""
        self._history.append(message)

    def clear_history(self):
        """清空历史记录"""
        self._history.clear()

    def get_history(self) -> list[Message]:
        """获取历史记录"""
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"

    def __repr__(self) -> str:
        return self.__str__()