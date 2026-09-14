import sys
import os

# 获取当前文件的父目录的父目录（即项目根目录）, 并添加到sys.path, 以后上线需要将myAgents模块发布，这里就不要了
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.plan_solve_agent import PlanAndSolveAgent

# 加载环境变量
load_dotenv()

# 创建LLM实例
llm = HelloAgentsLLM()

# 创建自定义PlanAndSolveAgent
agent = PlanAndSolveAgent(name="我的规划执行助手", llm=llm)

# 测试复杂问题
question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"

result = agent.run(question)
print(f"\n最终结果: {result}")