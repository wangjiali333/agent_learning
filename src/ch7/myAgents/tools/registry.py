"""工具注册器, 用于注册和获取工具，执行工具"""

from typing import Any, Callable, Optional, List, Dict
from .base import Tool, ToolParameter, FunctionTool
import logging

logger = logging.getLogger(__name__)  # 日志记录器


class ToolRegistry:
    """
    HelloAgents工具注册表（容器)

    提供工具的注册、管理和执行功能。
    支持两种工具注册方式：
    1. Tool对象注册（推荐:因为我们定义Tool类中包含了工具的所有必要信息，所以推荐使用Tool对象注册）
    2. 函数直接注册（简便）
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        """
        注册Tool对象，即将tool添加到  self._tools字典中

        Args:
            tool: Tool实例
        """
        if tool.name in self._tools:
            logger.warning(f"⚠️ 警告：工具 '{tool.name}' 已存在，将被覆盖。")
        self._tools[tool.name] = tool
        logger.info(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: Optional[List[ToolParameter]] = None,
    ):
        """
        直接注册函数作为工具

        Args:
            name: 函数名称
            description: 函数描述
            func: 执行函数
            parameters: 函数参数定义
        """
        if name in self._tools:
            logger.warning(f"⚠️ 警告：函数式工具 '{name}' 已存在，将被覆盖。")
        tool = FunctionTool(
            name=name, description=description, func=func, parameters=parameters or []
        )
        self.register_tool(tool)

    def unregister(self, name: str):
        """注销工具或函数式工具

        Args:
            name: 待注销工具或函数式工具名称
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"🗑️ 工具 '{name}' 已注销。")
        else:
            logger.warning(f"⚠️ 工具或函数式工具: '{name}' 不存在。")

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取Tool对象"""
        return self._tools.get(name)

    def list_all_tools(self) -> list[str]:
        """列出所有工具和函数式工具的名称"""
        return list(self._tools.keys())

    def get_all_tools(self) -> list[Tool]:
        """获取所有Tool对象"""
        return list(self._tools.values())

    def clear(self):
        """清空所有工具"""
        self._tools.clear()
        # self._functions.clear()
        logger.info("🧹 所有工具及函数式工具已清空。")

    # TODO: 完善get_tools_description方法，添加函数式工具的描述,以备prompt-base agent使用
    def get_tools_description(self) -> str:
        """
        获取所有可用工具及函数式工具的格式化描述字符串

        实际上是为另一种 Agent 架构准备的。
        有两种类型的agent调用tool的架构:
         Prompt-base Agent: 该架构下，agent通过提示词调用工具，工具的执行结果会作为提示词的一部分返回。 ****
         Function-call Agent: 该架构下，agent通过函数调用工具，工具的执行结果会作为函数调用的结果返回。

        Returns:
            工具描述字符串，用于构建提示词
        """
        descriptions = []
        # Tool对象描述
        for tool in self._tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        执行工具

        Args:
            name: 工具或函数式工具名称
            input_text: 输入参数

        Returns:
            工具执行结果
        """
        if name in self._tools:
            tool = self._tools[name]
            try:
                if not tool.validate_parameters(arguments):
                    return f"错误：工具 '{name}' 缺少必要参数"
                # 简化参数传递，直接传入字符串
                # return tool.run(**arguments)
                return tool.run(arguments)
            except Exception as e:
                logger.exception(f"执行工具 '{name}' 时发生异常: {str(e)}")
                return f"错误：执行工具 '{name}' 时发生异常: {str(e)}"
        else:
            return f"错误：未找到名为 '{name}' 的工具。"

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling schema 格式
        schema格式如下:
        tools
        └── tool
            ├── type
            └── function
                ├── name
                ├── description
                └── parameters
                        ├── type
                        ├── properties
                        └── required

        用于 FunctionCallAgent，使工具能够被 OpenAI 原生 function calling 使用

        Returns:
            符合 OpenAI function calling 标准的 schema
        """
        schemas = []
        # ============================================================
        # 1. Tool对象
        # ============================================================
        for tool in self._tools.values():
            parameters = tool.get_parameters()
            properties = {}
            required = []
            for param in parameters:
                prop = {
                    "type": param.type,
                    "description": param.description,
                }
                # array类型需要items , 如果参数是array类型，需要指定items元素的类型
                if param.items is not None:
                    prop["items"] = param.items
                if param.default is not None:
                    prop["default"] = param.default
                properties[param.name] = prop
                if param.required:
                    required.append(param.name)
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
            )
        return schemas


# 创建全局工具注册器
global_registry = ToolRegistry()