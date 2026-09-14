import sys
import os

# 获取当前文件的父目录的父目录（即项目根目录）, 并添加到sys.path, 以后上线需要将myAgents模块发布，这里就不要了
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.reflection_agent import ReflectionAgent

# 加载环境变量
load_dotenv()

# 创建LLM实例
llm = HelloAgentsLLM()

# 创建自定义ReflectionAgent
# agent = ReflectionAgent(name="我的反思助手", llm=llm)
# result = agent.run("写一篇关于人工智能发展历程的简短文章")
# print("\n\n\n", result)


#  测试二:使用自定义代码生成提示词（类似第四章）
code_prompts = {
    "initial": "你是Python专家，请编写函数:{task}",
    "reflect": "请审查代码的算法效率:\n任务:{task}\n代码:{content}",
    "refine": "请根据反馈优化代码:\n任务:{task}\n反馈:{feedback}",
}
code_agent = ReflectionAgent(
    name="我的代码生成助手", llm=llm, custom_prompt=code_prompts
)

# 测试使用
result = code_agent.run(
    "请编写一个快排的Python函数，输入是一个整数列表，输出是一个排序后的整数列表。"
)

print(f"最终结果: {result}")