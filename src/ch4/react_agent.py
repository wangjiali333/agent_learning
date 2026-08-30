from llm import HelloAgentsLLM
from executor import ToolExecutor
from search import search
from typing import Optional
import re

# ReAct 提示词模板
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

class ReActAgent:
    def __init__(self, llm_client: "HelloAgentsLLM", tool_executor: "ToolExecutor", max_steps: int = 5):
        self.llm_client = llm_client # 初始化大语言模型客户端
        self.tool_executor = tool_executor # 初始化工具执行器
        self.max_steps = max_steps  # 最大迭代次数
        self.history = []  # 初始化空历史记录列表

    def run(self, question: str) -> Optional[str]:
        """
        运行 ReAct 智能体回答用户问题，返回最终答案字符串，若失败返回 None。
        """
        self.history = []  # 重置
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()  # 假设返回字符串描述
            history_str = self._format_history()  # 自定义历史格式化
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用 LLM
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("❌ LLM 未返回有效响应，终止。")
                break

            # 3. 解析 Thought 和 Action
            thought, action = self._parse_output(response_text)
            if thought:
                print(f"🧠 思考: {thought}")
            else:
                print("⚠️ 未能解析出 Thought，继续...")

            # 记录历史（包含思考，便于上下文）
            self.history.append({"role": "thought", "content": thought or "无思考"})

            if not action:
                # 若没有 Action，尝试引导模型重新生成
                observation = "错误：没有提供有效的 Action。请重新输出正确的 Thought 和 Action。"
                self.history.append({"role": "observation", "content": observation})
                print(f"👀 观察: {observation}")
                continue  # 继续下一轮，让模型重试

            # 4. 处理 Finish
            if action.startswith("Finish"):
                # 提取最终答案
                finish_match = re.match(r"Finish\[(.*)\]", action, re.DOTALL)
                if finish_match:
                    final_answer = finish_match.group(1).strip()
                    print(f"🎉 最终答案: {final_answer}")
                    return final_answer
                else:
                    # 格式错误，给予反馈
                    observation = "错误：Finish 格式应为 Finish[答案]，请修正。"
                    self.history.append({"role": "observation", "content": observation})
                    print(f"👀 观察: {observation}")
                    continue

            # 5. 解析工具名称和输入
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                observation = f"错误：无法解析 Action 格式，期望 '工具名[输入]'，得到 '{action}'"
                self.history.append({"role": "observation", "content": observation})
                print(f"👀 观察: {observation}")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            # 6. 执行工具
            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误：未找到名为 '{tool_name}' 的工具。"
            else:
                try:
                    observation = tool_function(tool_input)
                except Exception as e:
                    observation = f"执行工具时出错: {e}"

            print(f"👀 观察: {observation}")

            # 7. 记录本轮 Action 和 Observation
            self.history.append({"role": "action", "content": action})
            self.history.append({"role": "observation", "content": observation})

        # 超出最大步数
        print(f"⚠️ 已达到最大步数 {self.max_steps}，流程终止。")
        return None

    # ----- 辅助方法 -----

    def _format_history(self) -> str:
        """将历史记录格式化为字符串，供提示词使用"""
        lines = []
        for entry in self.history:
            role = entry.get("role")
            content = entry.get("content", "")
            if role == "thought":
                lines.append(f"Thought: {content}")
            elif role == "action":
                lines.append(f"Action: {content}")
            elif role == "observation":
                lines.append(f"Observation: {content}")
        return "\n".join(lines)

    def _parse_output(self, text: str):
        """
        从 LLM 输出中提取 Thought 和 Action。
        返回 (thought, action) 元组，若未找到则为 (None, None)。
        """
        # Thought: 匹配到 Action: 或文本末尾
        # \s* 匹配零个或多个空格字符
        # .*? 匹配任意字符（非贪婪模式），直到遇到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        action = action_match.group(1).strip() if action_match else None

        return thought, action

    def _parse_action(self, action_text: str):
        """
        解析 Action 字符串，返回 (tool_name, tool_input)。
        格式: tool_name[tool_input]
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

if __name__ == "__main__":
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页的搜索引擎。当你需要回答关于事实、时事以及你的数据库中的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)

    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)

    # 给一个问题
    question = "马克斯的optimus机器人目前产量状态?它的中国供应链公司有哪些?"
    agent.run(question)

