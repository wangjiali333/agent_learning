import sys
import os

# 获取当前文件的父目录的父目录（即项目根目录）, 并添加到sys.path, 以后上线需要将myAgents模块发布，这里就不要了
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.simple_agent import SimpleAgent
from myAgents.agents.simple_agent_with_tool import SimpleAgentWithTool
from myAgents.agents.react_agent import ReActAgent
from myAgents.tools.registry import ToolRegistry, global_registry
from myAgents.tools.base import Tool, ToolParameter, FunctionTool
from myAgents.tools.builtin.search import (
    SearchTool,
    search,
    search_tavily,
    search_hybrid,
    search_serpapi,
    search_arxiv,
)

#                                             工具            快捷函数
from myAgents.tools.builtin.calculator import CalculatorTool, calculate
from myAgents.tools.builtin.weatherTool import WeatherTool

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    llm = HelloAgentsLLM()

    # 创建工具注册表. 这个注册表中可以存工具，也可以存快捷函数
    tool_registry = ToolRegistry()
    # 注册工具
    tool_registry.register_tool(CalculatorTool())
    tool_registry.register_tool(SearchTool())
    tool_registry.register_tool(WeatherTool())
    # 注册工具对应的快捷函数
    tool_registry.register_function("calculateFunction", "执行数学计算.", calculate)

    agent = ReActAgent(
        name="ReactAgent",
        llm=llm,
        system_prompt="你是一个专业的智能助手,你可以使用工具来完成任务",
        tool_registry=tool_registry,
    )
    print("\n" + "=" * 60)
    print("开始测试 ReActAgent")
    print("=" * 60)

    # 测试1：数学计算问题
    # print("\n📊 测试1：数学计算问题")
    # math_question = "请帮我计算：(25 + 15) * 3 - 8 的结果是多少？"
    args = {"temperature": 0.7, "max_tokens": 1024}
    # result1 = agent.run(math_question, **args)
    # print(f"\n🎯 测试1结果: {result1}")

    # # 测试2：需要搜索的问题
    print("\n🔍 测试2：信息搜索问题")
    search_question = "Python编程语言是什么时候发布的？请告诉我具体的年份。"
    result2 = agent.run(search_question, **args)
    print(f"\n🎯 测试2结果: {result2}")

    # # 测试3：复合问题（需要多步推理）
    # print("\n🧠 测试3：复合推理问题")
    # complex_question = "请查询长沙的天气后给我推荐几个合适的旅游景点。"
    # result3 = agent.run(complex_question, **args)
    # print(f"\n🎯 测试3结果: {result3}")