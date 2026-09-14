from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.simple_agent import SimpleAgent
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

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # ============================快捷工具函数测试 ===============================
    # print(search_tavily("什么是transformer?"))
    # print("===================================")
    # print(search_serpapi("什么是transformer?"))
    # print("===================================")
    # print(search_hybrid("什么是transformer?"))
    # print("===================================")
    # print(search("什么是transformer?", backend="tavily"))

    # ============================工具注册测试 ===============================
    global_registry.register_tool(SearchTool())
    print(global_registry.get_all_tools())
    print(global_registry.to_openai_schema())
    print("===================================")
    print(global_registry.execute_tool("search", {"input": "什么是transformer?"}))