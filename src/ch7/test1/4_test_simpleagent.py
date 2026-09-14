from myAgents.core.llm import HelloAgentsLLM
from myAgents.agents.simple_agent import SimpleAgent

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    llm = HelloAgentsLLM()
    agent = SimpleAgent(name="SimpleAgent", llm=llm, system_prompt="你是一个专业的助手")
    # print(agent.run("你好,你是哪个模型?"))
    # print(agent._history)

    # print(agent.run("我前面的问题是什么?"))

    for chunk in agent.stream_run("你好，你是哪个模型?   "):
        print(chunk, end="")