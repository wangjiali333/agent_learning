from typing import Dict, Any
# 从search.py导入search函数，用于执行搜索操作
from search import search 

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        #           Dict[工具名称, Dict[工具描述, 工具执行函数]]
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])

if __name__ == "__main__":
    # 1.初始化工具执行器
    tool_executor = ToolExecutor()
    # 2.注册我们的实战搜索工具
    search_description = "一个网页的搜索引擎。当你需要回答关于事实、时事以及你的数据库中的信息时，应使用此工具。"
    #                          工具名称      工具描述      工具函数
    tool_executor.registerTool("Search", search_description, search)
    # 3.打印所有可用工具
    print(tool_executor.getAvailableTools())
    # 4.智能体的Action调用，这次我们问一个实时性的问题
    print("\n\n\n--- 执行Action: Search['英伟达最新的CPU型号是什么...']")
    tool_name = "Search"
    tool_input = "英伟达最新的CPU型号是什么？"
    tool_function = tool_executor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input) # 执行搜索工具
        print("-----观察(observation)-------")
        print(observation)
    else:
        print(f"错误:未找到工具 '{tool_name}'。请检查工具名称是否正确。")
