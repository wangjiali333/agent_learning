"""ReAct Agent实现 - 推理与行动结合的智能体
reasoning -> action -> observation
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] \n       %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# 默认ReAct提示词模板
DEFAULT_REACT_PROMPT = """
你是一个具备推理和行动能力的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，且每次只能执行一个步骤：

Thought:  分析当前问题，思考需要什么信息或采取什么行动。
Action:  选择一个行动，格式必须是以下之一：
- {{tool_name}}[{{tool_input}}] - 调用指定工具
- Finish[最终答案] - 当你有足够信息给出最终答案时

## 重要提醒
1. 每次回应必须包含Thought和Action两部分
2. 工具调用的格式必须严格遵循：工具名[参数]
3. 只有当你确信有足够信息回答问题时，才使用Finish, Finish的格式必须遵循：Finish[最终答案]
4. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数
5. 语言必须是中文

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始你的推理和行动："""


from ..core.agent import Agent
from ..core.config import Config
from ..core.llm import HelloAgentsLLM
from ..tools.registry import ToolRegistry
from typing import Optional, Dict, List, Tuple
from ..core.message import Message
import re


class ReActAgent(Agent):
    """
    ReAct (Reasoning and Acting) Agent

    结合推理和行动的智能体，能够：
    1. 分析问题并制定行动计划
    2. 调用外部工具获取信息
    3. 基于观察结果进行推理
    4. 迭代执行直到得出最终答案

    这是一个经典的Agent范式，特别适合需要外部信息的任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 10,
        custom_prompt: Optional[str] = None,
    ):
        """
        初始化ReActAgent

        Args:
            name: Agent名称
            llm: LLM实例
            tool_registry: 工具注册表
            system_prompt: 系统提示词
            config: 配置对象
            max_steps: 最大执行步数
            custom_prompt: 自定义提示词模板
        """
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []

        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_REACT_PROMPT

    def run(self, input_text: str, **kwargs: Dict[str, any]) -> str:
        """
        运行ReAct Agent

        Args:
            input_text: 用户问题
            **kwargs: 其他LLM参数

        Returns:
            最终答案
        """
        self.current_history = []  # 清空历史记录
        current_step = 0  # 初始化当前步骤数

        logger.info(f"\n🤖 {self.name} 开始处理问题: {input_text}")
        while current_step < self.max_steps:
            current_step += 1
            logger.info(f"\n--- 第 {current_step} 步 ---")
            # 构建提示词模板中各个参数
            # 1. 工具描述
            tools_desc = self.tool_registry.get_tools_description()
            # 2. 执行历史
            history_str = (
                "\n".join(self.current_history)
                if self.current_history
                else "暂无执行历史"
            )
            # 3. 格式化模板
            prompt = self.prompt_template.format(
                tools=tools_desc, question=input_text, history=history_str
            )
            # 4. 调用LLM生成回复
            # 构造messages
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm.invoke(messages, **kwargs)
            if not response_text:
                logger.info("❌ 错误：LLM未能返回有效响应。")
                break
            # 解析输出 :     Thought, Action( 有两种可能: 调用工具或 调用Finish )
            thought, action = self._parse_output(response_text)
            if thought:
                logger.info(f"🤔 思考: {thought}")

            if not action:
                logger.warning("⚠️ 警告：未能解析出有效的Action，流程终止。")
                break
            # 检查是否完成
            if action.startswith("Finish["):
                final_answer = self._parse_action_input_finish(action)
                logger.info(f"🎉 最终答案: {final_answer}")
                # 保存到历史记录
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))
                return final_answer
            # 解析工具： {{tool_name}}[{{tool_input}}]
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                self.current_history.append(
                    "Observation: 无效的Action格式，请重新检查。"
                )
                continue
            logger.info(f"🎬 解析到行动执行的工具信息: {tool_name}[{tool_input}]")
            # 调用工具
            # execute_tool(工具名,    参数字典  )
            paramDict = self._parse_tool_parameters(tool_input)
            observation = self.tool_registry.execute_tool(tool_name, paramDict)
            logger.info(f"👀 观察: {observation}")
            # 更新历史
            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

        logger.info("⏰ 已达到最大步数，流程终止。")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        return final_answer

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析LLM输出，提取思考和行动
        params:
            text: LLM原始输出
        return:
            thought: 思考内容
            action: 行动内容
        """
        thought_match = re.search(r"Thought: (.*)", text)
        action_match = re.search(r"Action: (.*)", text)
        # thought_match = re.search(r"\*\*?Thought:?\*\*?:? (.*)", text)   # 匹配可选的星号和冒号
        # action_match = re.search(r"\*\*?Action:?\*\*?:? (.*)", text)
        # 提取思考和行动
        # group(1) 1表示匹配到的子字符串
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析行动文本，提取工具名称和输入"""
        match = re.match(r"(\w+)\[(.*)\]", action_text)  # 匹配的格式为 tool_name[input]
        if match:
            return match.group(1), match.group(2)  # 提取工具名称和输入
        return None, None  # 如果匹配失败，返回None

    def _parse_action_input_finish(self, action_text: str) -> str:
        """解析 Finish 中的最终结果"""
        match = re.match(
            r"\w+\[(.*)\]", action_text, re.DOTALL
        )  # 匹配的格式为 Finish[final_answer]
        return match.group(1) if match else ""

    def _parse_tool_parameters(self, parameters: str) -> dict:
        """智能解析工具参数
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
            param_dict = {"input": parameters}
        return param_dict