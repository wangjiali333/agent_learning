"""消息规范类, 定义消息的格式和内容,这里要求满足OpenAI的API规范"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

# Literal是类型提示, 限制变量只能取指定的值集（相当于枚举类型）
MessageRole = Literal["user", "assistant", "system", "tool"]


class Message(BaseModel):
    """消息规范类"""

    content: str  # 消息内容
    role: MessageRole  # 消息角色
    # Optional可选参数
    timestamp: Optional[str] = None  # 消息时间戳
    metadata: Optional[Dict[str, Any]] = None  # 消息元数据,用于存储额外的信息

    #   **kwargs:    {"source":"baidu","accuracy":0.9 } =>
    #                拆包 => source="baidu", accuracy=0.9
    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get("timestamp", str(datetime.now())),
            metadata=kwargs.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（OpenAI API格式）"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """返回消息的字符串表示,相当于toString()"""
        return f"[{self.role}] {self.content} ({self.timestamp})"