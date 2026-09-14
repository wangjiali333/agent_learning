from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.simple_agent import SimpleAgent
from myAgents.tools.registry import ToolRegistry, global_registry
from myAgents.tools.base import Tool, ToolParameter, FunctionTool
from myAgents.tools.builtin.calculator import CalculatorTool, calculate

from dotenv import load_dotenv

load_dotenv()


def add(x: int, y: int) -> int:
    return x + y


def sub(x: int, y: int) -> int:
    return x - y


# 定义更通用的数学运算工具函数
def math_operation(expression: str) -> float:
    return eval(expression)  # eval(   字符串表达式)   => 表达式的计算结果


# eval()缺点: 1. 安全风险，执行任意代码；2. 仅支持简单的表达式，不支持复杂的逻辑

# 对于生成数学运算表达式解析这种需求，我们需要引入 AST 解析器 => 解析表达式. ->语法树
# 语法树: 一种用于表示程序源代码的树状结构，每个节点表示程序中的一个语法元素，如变量、函数调用、运算符等。


if __name__ == "__main__":
    # ============================函数测试 ===============================
    # 注册函数到ToolRegistry
    global_registry.register_tool(
        FunctionTool(
            "加",
            "对两个整数进行加法操作",
            add,
            [
                ToolParameter(name="x", type="integer", description="第一个整数"),
                ToolParameter(name="y", type="integer", description="第二个整数"),
            ],
        )
    )
    global_registry.register_tool(
        FunctionTool(
            "减",
            "对两个整数进行减法操作",
            sub,
            [
                ToolParameter(name="x", type="integer", description="第一个整数"),
                ToolParameter(name="y", type="integer", description="第二个整数"),
            ],
        )
    )
    # 输出所有工具的工具名称
    print(global_registry.list_all_tools())
    # 输出满足open AI 的function call的schema
    print(global_registry.to_openai_schema())
    # 输出满足 prompt-base agent的 schema 格式
    print(global_registry.get_tools_description())

    # ==============================工具测试 : 1.计算器工具============================
    # 1. 直接调用工具
    calculatorTool = CalculatorTool()
    print(calculatorTool.run({"input": "2 + 3"}))
    print(calculatorTool.run({"input": "2 + 3 * 4"}))
    print(calculatorTool.run({"input": "sqrt(16)"}))
    print(calculatorTool.run({"input": "sin(pi / 2)"}))
    # 2. 便捷调用 工具方式
    print(calculate("2*2+3"))

    # 3. 测试工具注册表
    global_registry.register_tool(CalculatorTool())
    # # 获取所有工具
    print(global_registry.list_all_tools())
    # # 获取所有工具的基于prompt-base agent  的schema参数
    print(global_registry.get_tools_description())
    # # 获取所有工具的基于function calling agent  的schema参数
    print(global_registry.to_openai_schema())
    # # 测试工具调用
    print(global_registry.execute_tool("python_calculator", {"input": "2 + 3"}))