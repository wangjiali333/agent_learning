import os
import re
import requests
from openai import OpenAI
from tavily import TavilyClient
from dotenv import load_dotenv
import sys

load_dotenv()
# ---------- 工具函数 ----------
def get_weather(city: str) -> str:
    """通过 wttr.in API 查询真实天气"""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        current_condition = weather_data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        return f"{city}当前天气:{weather_desc}，气温{temp_c}摄氏度"
    except requests.exceptions.RequestException as e:
        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        return f"错误:解析天气数据失败，可能是城市名称无效 - {e}"

def get_attraction(city: str, weather: str) -> str:
    """根据城市和天气，使用 Tavily Search API 推荐景点"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误:未配置TAVILY_API_KEY环境变量。"
    tavily = TavilyClient(api_key=api_key)
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        if response.get("answer"):
            return response["answer"]
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")
        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"
        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题 - {e}"

available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}

# ---------- LLM 客户端 ----------
class OpenAICompatibleClient:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        print("正在调用大语言模型...")
        if not prompt:
            return "错误:请输入用户提示词。"
        try:
            # 正确构建 messages，避免 None 元素
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.1   # 降低随机性，更稳定
            )
            print("原始响应:", response)
            print("==" * 200)
            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误:调用语言模型服务时出错。"

# ---------- 系统提示 ----------
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手，你的任务是根据用户的需求，并使用可调用的工具来一步步解决问题。

可用的工具：
- get_weather(city: str) -> str: 查询指定城市的当前天气。
- get_attraction(city: str, weather: str) -> str: 根据城市和天气推荐旅游景点。

# 输出格式要求：
你的每次回答必须严格按照以下格式（两行）：
Thought: [你思考过程和下一步计划]  
Action: [你要执行的具体行动]。

Action的格式必须是以下之一：
1.调用工具：function_name(arg_name = "arg_value")
2.结束对话：Finish[最终答案]

# 语言强制要求（最高优先级）：
- **所有输出（包括 Thought 和 Action 中的所有文字）必须使用中文。**
- **无论用户的输入是什么语言，你都只能用中文回复。**
- **严禁输出任何英文句子或单词（工具函数名称和参数名除外，但参数值必须用中文）。**

# 重要提示：
- 每次只输出一对 Thought 和 Action。
- Action 必须在同一行，不能跨行。
- 当收集到足够的信息可以回答用户问题时，使用Action: Finish[最终答案]格式结束。
- 请开始吧！
"""

# ---------- 主循环 ----------
if __name__ == "__main__":
    # argv存的是数组，假设你的命令是 python 智能旅行推荐助手.py 北京
    # args[0] python 智能旅行推荐助手.py
    # args[1] 北京
    args = sys.argv[1:]
    if len(args) == 0:
        # 如果没有提供城市参数，默认使用北京
        city = "北京"
    else:
        city = args[0]

    API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL")
    MODEL_ID = os.getenv("OPENAI_MODEL_NAME")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    llm = OpenAICompatibleClient(
        model=MODEL_ID,
        api_key=API_KEY,
        base_url=BASE_URL
    )

    user_prompt = f"你好，请帮我查询一下今天{city}的天气，然后根据天气推荐一个合适的旅游景点。"
    prompt_history = [f"用户请求: {user_prompt}"]
    print(f"用户输入: {user_prompt}\n" + "="*40)

    for i in range(50):   # 最大循环次数
        print(f"--- 循环 {i+1} ---\n")

        # 构建完整提示
        full_prompt = "\n".join(prompt_history)

        # 调用 LLM
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)

        # 截断多余的 Thought-Action 对
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")

        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 解析 Action
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)
            continue

        action_str = action_match.group(1).strip()

        # 判断是否完成
        if action_str.startswith("Finish"):
            finish_match = re.search(r"Finish\[(.*)\]", action_str)
            if finish_match:
                final_answer = finish_match.group(1)
                print(f"任务完成，最终答案: {final_answer}")
                break
            else:
                observation = "错误: Finish 格式不正确，应为 Finish[答案]。"
                observation_str = f"Observation: {observation}"
                print(f"{observation_str}\n" + "="*40)
                prompt_history.append(observation_str)
                continue

        # 解析工具调用
        tool_match = re.search(r"(\w+)\(", action_str)
        args_match = re.search(r"\((.*)\)", action_str)
        if not tool_match or not args_match:
            observation = "错误: 工具调用格式无效，应为 function_name(arg1 = 'value1', arg2 = 'value2')"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)
            continue

        tool_name = tool_match.group(1)
        args_str = args_match.group(1)

        # 解析参数（兼容等号前后空格、双引号）
        kwargs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', args_str))

        if tool_name in available_tools:
            try:
                observation = available_tools[tool_name](**kwargs)
            except Exception as e:
                observation = f"错误:执行工具时发生异常 - {e}"
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)