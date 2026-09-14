from myAgents.core.llm import HelloAgentsLLM

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # llm = HelloAgentsLLM()
    llm = HelloAgentsLLM(
        provider="ollama",
        model="deepseek-r1:1.5b",  # 需与服务启动时指定的模型一致
        base_url="http://localhost:11434/v1",
        api_key="",  # 本地服务通常不需要真实API Key，可填任意非空字符串
    )
    print(llm)

    # print(llm.think("你好,你是哪个模型?"))  # <generator object HelloAgentsLLM.think at 0x000001310A7CEF00>
    # generator 是一个迭代器, 可以通过 next() 函数获取下一个值
    for chunk in llm.think(
        [{"role": "user", "content": "你好,你是哪个模型?你是参数规模是多少"}]
    ):
        print(chunk, end="", flush=True)

    # 非流式调用
    # result = llm.invoke([{"role": "user", "content": "你好,你是哪个模型?"}])
    # print(result)