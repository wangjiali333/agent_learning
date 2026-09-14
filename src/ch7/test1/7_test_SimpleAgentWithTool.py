import sys
import os

# 获取当前文件的父目录的父目录（即项目根目录）, 并添加到sys.path, 以后上线需要将myAgents模块发布，这里就不要了
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.simple_agent import SimpleAgent
from myAgents.agents.simple_agent_with_tool import SimpleAgentWithTool
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
from myAgents.tools.builtin.calculator import CalculatorTool
from myAgents.tools.builtin.weatherTool import WeatherTool

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    llm = HelloAgentsLLM()
    agent = SimpleAgentWithTool(
        name="SimpleAgentWithTool",
        llm=llm,
        system_prompt="你是一个专业的智能助手,你可以使用工具来完成任务",
    )

    agent.add_tool(CalculatorTool())
    agent.add_tool(SearchTool())
    agent.add_tool(WeatherTool())

    

    print(agent.has_tools())
    print(agent.list_tools())

    print("*" * 50)

    # print(agent.run("请计算1+2*3-5+9"))
    print(agent.run("请查询长沙的天气，根据这个天气给我推荐一个旅游景点"))