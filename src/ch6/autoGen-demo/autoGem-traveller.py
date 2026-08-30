# autoGem-traveller.py
import asyncio
import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from tavily import TavilyClient

load_dotenv()

# ============================================================
# 1. 本地记忆模块
# ============================================================
class Memory:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        self.records.append({"type": record_type, "content": content})
        print(f"📝 记忆已更新（{record_type}）")

    def get_trajectory(self) -> str:
        parts = []
        for r in self.records:
            if r['type'] == 'execution':
                parts.append(f"--- 执行 ---\n{r['content']}")
            elif r['type'] == 'reflection':
                parts.append(f"--- 反思 ---\n{r['content']}")
        return "\n\n".join(parts) if parts else "暂无历史记录"

    def get_last_execution(self) -> Optional[str]:
        for r in reversed(self.records):
            if r['type'] == 'execution':
                return r['content']
        return None

memory = Memory()

def remember(content: str) -> str:
    memory.add_record("execution", content)
    return "已记住"

def recall() -> str:
    return memory.get_trajectory()

def reflect(feedback: str) -> str:
    memory.add_record("reflection", feedback)
    return "反馈已记录"

MEMORY_TOOLS = [remember, recall, reflect]

# ============================================================
# 2. 模型客户端
# ============================================================
def create_model_client():
    return OpenAIChatCompletionClient(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
        },
    )

# ============================================================
# 3. 外部工具
# ============================================================
def get_weather(city: str) -> str:
    """通过 wttr.in 获取实时天气（免费，无需 Key）"""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data["current_condition"][0]
        desc = current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        return f"{city} 当前天气：{desc}，气温 {temp}°C"
    except Exception as e:
        return f"⚠️ 获取天气失败：{e}"

def get_attraction(city: str, weather_desc: str = "") -> str:
    """使用 Tavily 搜索景点推荐"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "❌ 未配置 TAVILY_API_KEY"
    tavily = TavilyClient(api_key=api_key)
    query = f"{city} {'天气' + weather_desc if weather_desc else ''} 必去景点 推荐"
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        if response.get("answer"):
            return response["answer"]
        results = [f"- {r['title']}: {r['content']}" for r in response.get("results", [])[:5]]
        return "根据搜索，为您推荐：\n" + "\n".join(results) if results else "未找到相关景点。"
    except Exception as e:
        return f"⚠️ Tavily 搜索失败：{e}"

EXTERNAL_TOOLS = [get_weather, get_attraction]

# ============================================================
# 4. 创建多智能体
# ============================================================
def create_agents(model_client):
    all_tools = MEMORY_TOOLS + EXTERNAL_TOOLS

    planner = AssistantAgent(
        name="TravelPlanner",
        model_client=model_client,
        system_message="""
你是一位资深旅行规划师，统筹全局。
工作流程：
1. 先让 Researcher 搜索景点，WeatherAgent 查询天气。
2. 综合信息，制定每日行程（景点、餐饮、交通）。
3. 最终输出完整的 5 天计划，包括穿衣建议和预算估算。
4. 你可以使用 remember() 存储重要信息，用 recall() 回忆历史，用 reflect() 记录反思。
当计划最终确定，回复 "TERMINATE" 结束。
""",
        tools=all_tools,
    )

    researcher = AssistantAgent(
        name="Researcher",
        model_client=model_client,
        system_message="你是旅行研究员，使用 get_attraction 搜索目的地热门景点、美食和活动。",
        tools=[get_attraction],
    )

    weather_agent = AssistantAgent(
        name="WeatherAgent",
        model_client=model_client,
        system_message="你是天气专家，使用 get_weather 获取实时天气预报，并分析天气对出行的影响。",
        tools=[get_weather],
    )

    user_proxy = UserProxyAgent(
        name="UserProxy",
        input_func=input,
        description="代表旅行者，可随时提出意见、修改需求或确认计划。",
    )

    return [planner, researcher, weather_agent, user_proxy]

# ============================================================
# 5. 主运行程序（已按你的要求修改）
# ============================================================
async def run_travel_assistant():
    print("🚀 启动智能旅行助手...")

    # ---- 收集用户旅行需求 ----
    print("\n👤 请告诉我您的旅行偏好：")
    city = input("📍 目的地: ").strip()
    days = input("📅 天数: ").strip()
    interest = input("🎯 兴趣（如历史、美食、购物）: ").strip()
    budget = input("💰 预算（日均，单位元）: ").strip()

    # 默认值
    if not city:
        city = "东京"
    if not days:
        days = "5"
    if not interest:
        interest = "历史、美食、购物"
    if not budget:
        budget = "1000"

    user_task = f"请为我在{city}规划一个{days}天的旅行计划，预算中等（日均{budget}元），兴趣是{interest}。"
    print(f"\n✅ 已收到您的需求：{user_task}")

    # ---- 初始化模型和代理 ----
    model_client = create_model_client()
    agents = create_agents(model_client)

    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat(
        participants=agents,
        termination_condition=termination,
        max_turns=30,
    )

    print("\n📋 任务已提交，开始协作...")
    print("=" * 60)
    result = await Console(team.run_stream(task=user_task))
    print("=" * 60)
    print("✅ 旅行计划生成完成！")
    await model_client.close()
    return result

# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(run_travel_assistant())
    except KeyboardInterrupt:
        print("\n👋 用户中断了对话")
    except Exception as e:
        print(f"❌ 发生错误：{e}")