"""工具基类"""

from pydantic import BaseModel
from typing import Any, List, Dict, Callable, Optional
from abc import ABC, abstractmethod


class ToolParameter(BaseModel):
    """工具参数定义"""

    name: str  # 工具参数名称
    type: str  # 工具参数类型
    description: str  # 工具参数描述
    required: bool = True  # 是否必填参数
    default: Any = None  # 工具参数默认值
    # 工具参数:数组元素的 Schema 定义（仅对数组类型有效）, 取值为:   items={"type": "integer"}
    items: Optional[Dict[str, Any]] = None


class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """工具执行函数"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义，因为一个工具可能有多个参数，所以返回一个列表。"""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证工具参数是否符合定义"""
        required_params = [
            p.name for p in self.get_parameters() if p.required
        ]  # 必填参数列表
        # 验证传入的参数 parameters是否包含所有必填参数
        return all(param in parameters for param in required_params)

    def to_dict(self) -> Dict[str, Any]:
        """将工具的参数定义转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.model_dump() for p in self.get_parameters()],
        }

    def __str__(self) -> str:
        return f"Tool(name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()


class FunctionTool(Tool):
    """函数式工具:
    比如定义一个函数   def add( x: int, y:int)
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,  # 工具执行函数， 对比，原生的Tool是run()方法, 而函数是 Callable
        parameters: List[ToolParameter],
    ):
        super().__init__(name, description)
        self.func = func
        self.parameters = parameters

    def run(self, **kwargs) -> Any:
        return self.func(**kwargs)  # 实际上是调用了 Callable函数=>   add( x,y )

    def get_parameters(self) -> List[ToolParameter]:
        return self.parameters