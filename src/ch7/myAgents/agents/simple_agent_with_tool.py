from myAgents.agents.simple_agent import SimpleAgent
from myAgents.core.llm import HelloAgentsLLM
from typing import Optional, Dict, Any, Iterator
from myAgents.core.config import Config
from myAgents.tools.registry import ToolRegistry, global_registry
from myAgents.core.message import Message

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] \n       %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleAgentWithTool(SimpleAgent):
    """
    重写的简单对话Agent
    展示如何基于框架基类构建自定义Agent，支持工具调用
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling
        print(
            f"✅ {name} 初始化完成，工具调用: {'启用' if self.enable_tool_calling else '禁用'}"
        )

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """
        运行简单Agent，支持工具调用
        :param input_text: 输入的文本提示词
        :param max_tool_iterations: 最大工具调用次数
        :param kwargs: 其他LLM调用参数: 如 temperature, max_tokens, timeout 等
        :return: 生成的文本响应
        """
        print(f"🤖 {self.name} 正在处理输入提示词: {input_text}")
        # 构建消息列表
        messages = []
        # 添加系统消息（可能包含工具信息 <=  toolregistry.to_openai_schema()  ）
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})
        # 添加当前用户消息
        messages.append({"role": "user", "content": input_text})
        # 如果没有启用工具调用，使用简单对话逻辑
        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)  # 调用LLM生成响应

            # self.add_message(
            #     Message(input_text, "user")
            # )  # 添加用户消息  此处使用了Message类来包装消息，与上面 messages.append({"role": "user", "content": input_text})相同的
            self.add_message(Message(response, "assistant"))  # 添加助手消息
            print(f"✅ {self.name} 响应完成")
            return response
        # 支持多轮工具调用的逻辑
        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def _get_enhanced_system_prompt(self) -> str:
        """构建增强的系统提示词，其中还可以包含工具信息, 以便LLM调用时使用工具"""
        base_prompt = (
            self.system_prompt
            or "你是一个有用的AI助手,你具有调用工具，执行工具任务的能力。你会按照工具调用的规范进行。"
        )
        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt
        # 获取工具描述
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt
        # 构建工具描述部分
        tools_section = "\n\n## 可用工具列表\n"
        tools_section += "你可以使用以下工具来帮助回答问题:\n"
        tools_section += tools_description + "\n"
        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请严格使用以下格式输出需要调用的工具信息:\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "例如:`[TOOL_CALL:search:Python编程]` 或 `[TOOL_CALL:memory:recall=用户信息]`\n\n"
        tools_section += (
            "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。\n"
        )
        return base_prompt + tools_section

    def _run_with_tools(
        self, messages: list, input_text: str, max_tool_iterations: int, **kwargs
    ) -> str:
        """带工具调用的运行逻辑:
        :param messages: 已构建的消息列表，包含系统、用户和助手消息
        :param input_text: 输入的文本提示词
        :param max_tool_iterations: 最大工具调用次数
        :param kwargs: 其他LLM调用参数: 如 temperature, max_tokens, timeout 等
        :return: 生成的文本响应
        """
        current_iteration = 0
        final_response = ""
        # 最大迭代次数
        while current_iteration < max_tool_iterations:
            # 调用LLM, messages中是包含了工具信息
            response = self.llm.invoke(messages, **kwargs)
            logger.info(f"\n\n🔧 LLM输出的原始响应:\n         {response}")

            # 检查llm模型输出的response中是否有工具调用的要求:   格式为:   [TOOL_CALL:search:Python编程]
            tool_calls = self._parse_tool_calls(response)
            if tool_calls:
                logger.info(
                    f"\n\n🔧 检测到 {len(tool_calls)} 个工具调用，这些工具调用为:\n        {tool_calls}"
                )
                # 执行所有工具调用并收集结果
                tool_results = []
                clean_response = response  # 原始的响应
                # 循环工具
                for call in tool_calls:
                    result = self._execute_tool_call(
                        call["tool_name"], call["parameters"]
                    )
                    tool_results.append(result)
                    # 从响应中移除工具调用标记
                    clean_response = clean_response.replace(call["original"], "")

                # 构建包含工具结果的消息
                # TODO:　这样做，　clean_response 中正常情况下应该没有工具调用标记，会是''
                messages.append({"role": "assistant", "content": response})

                # 添加工具结果
                tool_results_text = "\n\n".join(tool_results)
                messages.append(
                    {
                        "role": "user",
                        "content": f"工具执行结果:\n{tool_results_text}\n\n请基于这些结果给出完整的回答。",
                    }
                )
                current_iteration += 1
                continue
            final_response = response
            break

            # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages, **kwargs)
        # 保存到历史记录
        # self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        print(f"✅ {self.name} 响应完成")
        return final_response

    def _parse_tool_calls(self, text: str) -> list:
        """解析文本中的工具调用
        :param text: 包含工具调用的文本   ,例 如:   [TOOL_CALL:search:Python编程]
        TODO: 参数此处只做了基本解析， 并没有考虑参数个数的情况(0, 1,n), 参数类型的情况( str, list, dict, object )
        """
        import re

        pattern = r"\[TOOL_CALL:([^:]+):([^\]]+)\]"
        matches = re.findall(pattern, text)
        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append(
                {
                    "tool_name": tool_name.strip(),
                    "parameters": parameters.strip(),
                    "original": f"[TOOL_CALL:{tool_name}:{parameters}]",
                }
            )
        return tool_calls

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:
        """智能解析工具参数
        :param tool_name: 工具名称
        :param parameters: 工具参数字符串     city=北京,limit=3,query=Python编程
        :return: 解析后的参数字典

        TODO: 后期需要对它进行更复杂的解析，考虑参数个数的情况(0, 1,n), 参数类型的情况( str, list, dict, object )
        """
        param_dict = {}
        if "=" in parameters:
            # 格式: key=value 或 action=search,query=Python
            if "," in parameters:
                # 多个参数:action=search,query=Python,limit=3
                pairs = parameters.split(",")
                for pair in pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        param_dict[key.strip()] = value.strip()
            else:
                # 单个参数:key=value
                key, value = parameters.split("=", 1)
                param_dict[key.strip()] = value.strip()
        else:
            # 直接传入参数，根据工具类型智能推断
            # 例 如:  情况1:  search:Python编程   情况2:  {"search":"python编程"}
            # TODO: 读取工具的参数定义，看那个参数是什么名字，根据名字来解析参数
            self.tool_registry.get_tool(tool_name)

            if tool_name == "search":
                param_dict = {"query": parameters}
            elif tool_name == "memory":
                # TODO: 后期加入记忆后对应的工具参数解析
                param_dict = {"action": "search", "query": parameters}
            else:
                param_dict = {"input": parameters}

        return param_dict

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用
        :param tool_name: 工具名称
        :param parameters: 工具参数字符串     city=北京,limit=3,query=Python编程
        :return: 工具执行结果
        """
        if not self.tool_registry:
            return f"❌ 错误:未配置工具注册表"
        try:
            # 智能参数解析
            # TODO: 应该是要根据工具的参数类型来判定是否需要解析参数:
            if tool_name == "calculator":
                # 计算器工具直接传入表达式
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                # 其他工具使用智能参数解析, 得到参数的字典.
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"❌ 错误:未找到工具 '{tool_name}'"
                result = tool.run(param_dict)
            return f"🔧 工具 {tool_name} 执行结果:\n{result}"
        except Exception as e:
            return f"❌ 工具调用失败:{str(e)}"

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """
        自定义的流式运行方法
        """
        print(f"🌊 {self.name} 开始流式处理: {input_text}")
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})
        # 流式调用LLM
        full_response = ""
        print("📝 实时响应: ", end="")
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            # print(chunk, end="", flush=True)
            yield chunk

        print()  # 换行

        # 保存完整对话到历史记录
        # self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))
        print(f"✅ {self.name} 流式响应完成")

    def add_tool(self, tool) -> None:
        """添加工具到Agent（便利方法）"""
        if not self.tool_registry:
            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True
        self.tool_registry.register_tool(tool)
        print(f"🔧 工具 '{tool.name}' 已添加")

    def has_tools(self) -> bool:
        """检查是否有可用工具"""
        return self.enable_tool_calling and self.tool_registry is not None

    def remove_tool(self, tool_name: str) -> bool:
        """移除工具（便利方法）"""
        if self.tool_registry:
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def list_tools(self) -> list:
        """列出所有可用工具"""
        if self.tool_registry:
            return self.tool_registry.list_all_tools()
        return []