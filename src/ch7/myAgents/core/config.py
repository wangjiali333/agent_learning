"""配置信息类: 支持自动从环境变量加载"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Config(BaseModel):
    """Agent中LLM及embedding模型的配置信息类"""

    # LLM配置
    default_model: str = "Qwen/Qwen3.5-35B-A3B"
    default_provider: str = "modelscope"  # 默认model提供方 ->简化配置
    temperature: float = 0.7  # 温度参数 ->控制输出的随机性
    max_tokens: Optional[int] = None  # 最大token数 ->根据model自动调整

    # 系统配置
    debug: bool = False  # 是否开启调试模式 ->用于开发和测试
    log_level: str = "INFO"  # 日志级别 ->控制日志输出的详细程度

    # 其他配置
    max_history_length: int = 100  # 最大消息历史长度 ->控制对话历史的长度

    @classmethod
    def from_env(cls) -> "Config":
        """类方法，它允许用户通过设置环境变量来覆盖默认配置，无需修改代码，这在部署到不同环境时尤其有用。"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_tokens=(
                int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式, 方便后续处理"""
        return self.dict()

    def __str__(self) -> str:
        """返回配置的字符串表示"""
        return str(self.to_dict())