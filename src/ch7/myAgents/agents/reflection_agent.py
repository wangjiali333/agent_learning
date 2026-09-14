# 默认提示词模板
DEFAULT_PROMPTS = {
    "initial": """
请根据以下要求完成任务：

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间：

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答：

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
""",
}

from typing import List, Dict, Any, Optional
from myAgents.core.agent import Agent
from myAgents.core.llm import HelloAgentsLLM
from myAgents.tools.registry import ToolRegistry
from myAgents.core.config import Config


class Memory:
    """
    简单的短期记忆模块，用于存储智能体的行动与反思轨迹。
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        """向记忆中添加一条新记录"""
        self.records.append({"type": record_type, "content": content})
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为一个连贯的字符串文本"""
        trajectory = ""
        for record in self.records:
            if record["type"] == "execution":
                trajectory += f"--- 上一轮尝试 (代码) ---\n{record['content']}\n\n"
            elif record["type"] == "reflection":
                trajectory += f"--- 评审员反馈 ---\n{record['content']}\n\n"
        return trajectory.strip()

    def get_last_execution(self) -> str:
        """获取最近一次的执行execution结果"""
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return ""


# 反思智能体
class ReflectionAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 10,
        custom_prompt: Optional[
            Dict[str, str]
        ] = None,  # 这里要与上面的DEFAULT_PROMPTS的结构匹配
    ):
        """
        初始化ReflectionAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            max_iterations: 最大迭代次数
            custom_prompts: 自定义提示词模板 {"initial": "", "reflect": "", "refine": ""}
        """
        super().__init__(name, llm, system_prompt, config)
        self.max_iterations = max_iterations
        self.prompts = custom_prompt if custom_prompt else DEFAULT_PROMPTS
        self.memory = Memory()

    def run(self, input_text: str, **kwargs) -> str:
        print(f"\n---{self.name} 开始处理任务 ---\n任务: {input_text}")

        # --- 1. 初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = self.prompts["initial"].format(task=input_text)
        initial_code = self._get_llm_response(
            initial_prompt, **kwargs
        )  # 调用llm获取初始代码

        self.memory.add_record("execution", initial_code)  # 记录初始执行结果

        # --- 2. 迭代循环:反思与优化 ---
        for i in range(self.max_iterations):
            print(f"\n--- 第 {i+1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            last_code = (
                self.memory.get_last_execution()
            )  # 取最近一次的执行 execution结果

            reflect_prompt = self.prompts["reflect"].format(
                task=input_text, content=initial_code
            )  # 格式化反思提示
            feedback = self._get_llm_response(
                reflect_prompt, **kwargs
            )  # 调用llm获取反思反馈
            self.memory.add_record("reflection", feedback)  # 记录反思反馈

            # b. 检查是否需要停止
            if "无需改进" in feedback:
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            # c. 优化
            print("\n-> 正在进行优化...")
            # 格式化优化提示
            refine_prompt = self.prompts["refine"].format(
                task=input_text, last_attempt=last_code, feedback=feedback
            )
            refined_code = self._get_llm_response(refine_prompt, **kwargs)
            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()  # 跳出循环后，获取最终的执行结果
        print(f"\n--- 任务完成 ---\n最终生成的代码:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str, **kwargs) -> str:
        """一个辅助方法，用于调用LLM并获取完整的流式响应。"""
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm.invoke(messages=messages, **kwargs) or ""
        return response_text