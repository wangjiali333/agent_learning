"""
智能搜索助手-基于LangGraph + Tavily API的真实搜索系统
1.理解用户的需求
2.使用Tavily API进行真实搜索
3.生成基于搜索结果的最终答案
"""
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import asyncio

# 加载环境变量
load_dotenv()

# ---------- 状态定义 ----------
class SearchState(TypedDict):
    messages: Annotated[list, add_messages]   # 对话历史（LangGraph 标准）
    user_query: str                           # 用户原始问题
    search_query: str                         # 优化后的搜索关键词
    search_results: str                       # 搜索结果的格式化文本
    final_answer: str                         # 最终答案
    step: str                                 # 当前步骤状态（用于流程控制）

# 初始化 LLM 和 Tavily 客户端
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    temperature=0.7,
)
# 初始化 Tavily 客户端
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ---------- 节点函数 ----------
def understand_query_node(state: SearchState) -> SearchState:
    """步骤1：理解用户查询并生成搜索关键词"""
    # 获取最新的用户消息
    user_message = ""
    # reverse()从最后(最新)消息开始遍历
    for msg in reversed(state["messages"]): 
        # 判断是否是用户消息，如果是则提取内容
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    understand_prompt = f"""分析用户的查询："{user_message}"
        请完成两个任务：
            1. 简洁总结用户想要了解什么
            2. 生成最适合搜索引擎的关键词（中英文均可，要精准）

        格式：
            理解：[用户需求总结]
            搜索词：[最佳搜索关键词]"""

    response = llm.invoke([SystemMessage(content=understand_prompt)])
    # 提取搜索关键词
    response_text = response.content
    
    # 解析LLM的输出，提取搜索关键词
    search_query = user_message # 默认使用原始查询
    if "搜索词：" in response_text:
        search_query = response_text.split("搜索词：")[1].strip()
    elif "搜索关键词：" in response_text:
        search_query = response_text.split("搜索关键词：")[1].strip()
    return {
        "user_query": response_text, # 系统提示词
        "search_query": search_query, # 优化后的搜索关键词
        "step": "understood", # 当前步骤状态是"understood"，表示已经理解用户需求
        "messages": [AIMessage(content=f"我将为您搜索：{search_query}")]
    }

def tavily_search_node(state: SearchState) -> SearchState:
    """
    步骤2：使用 Tavily 执行真实搜索，并格式化结果。
    若失败则记录错误信息。
    """
    search_query = state["search_query"]
    try:
        print(f"🔍 正在使用的搜索词: {search_query}")
        response = tavily_client.search(
            query=search_query,
            search_depth="basic",
            max_results=5, # 最多返回5个结果
            include_answer=True, # 包含综合答案
            include_raw_content=False # 不包含原始内容
        )

        # 处理Tavily API返回的搜索结果
        search_results = ""
        # 优先使用Tavily提供的综合答案
        if response.get("answer"):
            search_results = f"📌 综合答案：\n{response['answer']}\n\n"
        # 添加具体的搜索结果详情
        if response.get("results"):
            search_results += "📄 相关信息：\n"

            for i, result in enumerate(response["results"][:3], 1):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                search_results += f"{i}.{title}\n{content}\n来源: {url}\n\n"
        if not search_results:
            search_results = "抱歉,未找到相关信息。"
        return {
            "search_results": search_results,
            "step": "searched",
            "messages": [AIMessage(content="✅ 搜索完成!找到了相关信息，正在为您整理答案...")]
        }
    except Exception as e:
        error_msg = f"搜索时发生错误：{str(e)}"
        print(f"❌ {error_msg}")
        return {
            "search_results": f"搜索失败: {error_msg}",
            "step": "search_failed",
            "messages": [AIMessage(content="⚠️ 搜索服务暂时不可用，我将基于自身知识回答。")]
        }

def generate_answer_node(state: SearchState) -> dict:
    """
    步骤3：根据搜索结果（或回退到自身知识）生成最终答案。
    """
    # 检查是否有搜索结果
    if state["step"] == "search_failed":
        # 如果搜索失败，回退到仅依赖 LLM 内部知识
        fallback_prompt = f"""搜索服务暂时不可用，请基于你的知识回答用户的问题。
                            用户问题：{state["user_query"]}
                            请提供清晰、有用的回答。"""
        response = llm.invoke([SystemMessage(content=fallback_prompt)])
        return {
            "final_answer": response.content,
            "step": "completed",
            "messages": [AIMessage(content=response.content)]
        }
    # 基于tavily搜索结果生成最终答案
    answer_prompt = f"""基于以下搜索结果回答用户的问题。
                    用户问题：{state["user_query"]}
                    搜索结果：
                    {state["search_results"]}
                    请综合上述信息，提供准确、完整、有条理的回答。如果搜索结果信息不足，可以适当补充常识。"""
    response = llm.invoke([SystemMessage(content=answer_prompt)])

    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }

# ---------- 构建图 ----------
def create_search_assistant():
    workflow = StateGraph(SearchState)

    # 添加节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("answer", generate_answer_node)

    # 线性执行流程:以下是普通边，没有条件判断
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    # 编译（带内存检查点）
    memory = InMemorySaver() #内存保存器，用于存储状态
    app = workflow.compile(checkpointer=memory) #编译工作流，指定状态保存器
    return app

async def main():
    """主函数：运行智能体搜索助手"""
    #检查API密钥
    if not os.getenv("TAVILY_API_KEY"):
        print("错误: 请在环境变量中设置TAVILY_API_KEY")
        return
    app = create_search_assistant()
    print("智能搜索助手已启动...")
    print("我会使用Tavily API为您搜索最新、最准确的信息。")
    print("支持各种问题：新闻、科技、体育等知识问答")
    print("输入'quit'退出程序。\n")
    #会话计数器
    session_count = 0
    while True:
        user_input = input("请输入您的问题: ").strip()
        if user_input.lower() in ["quit", "exit", "q", "退出"]:
            print("感谢使用智能搜索助手，再见！")
            break
        if not user_input:
            print("⚠️ 输入不能为空，请重新输入。\n")
            continue
        session_count += 1
        config = {"configurable": {"thread_id": f"search_session_{session_count}"}}
        inital_state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": "",
            "search_query": "",
            "search_results": "",
            "final_answer": "",
            "step": "start"
        }
        try:
            print("\n" + "="*50)
            # 执行工作流并流式输出结果
            async for output in app.astream(inital_state, config=config):
                #print("DEBUG: output =", output)   # 打印每次收到的完整输出
                for node_name, node_output in output.items():
                    if "messages" in node_output and node_output["messages"]:
                        # 取最后一个消息(最新消息)
                        latest_message = node_output["messages"][-1]
                        if isinstance(latest_message, AIMessage):
                            if node_name == "understand":
                                print(f"🤖 理解用户需求: {latest_message.content}")
                            elif node_name == "search":
                                print(f"🔍 搜索结果: {latest_message.content}")
                            elif node_name == "answer":
                                print(f"📝 最终答案: {latest_message.content}")
            print("\n" + "="*50 + "\n")
        except Exception as e:
            print(f"搜索助手运行时出错: {e}")
            print("请重新输入您的问题。\n")
# ---------- 使用示例 ----------
if __name__ == "__main__":
    # 以异步方式运行主函数
    asyncio.run(main())