"""天气工具 - 原生天气实现"""

import os
from typing import Optional, Dict, Any, List

from ..base import Tool, ToolParameter
from ...core.exceptions import HelloAgentsException
import requests


class WeatherTool(Tool):
    """天气工具 - 原生天气实现"""

    def __init__(
        self,
        backend: str = "hybrid",
        tavily_key: Optional[str] = None,
        serpapi_key: Optional[str] = None,
    ):
        super().__init__(
            name="weatherTool",
            description="一个查询天气的工具，它根据用户输入的城市名称查询天气信息。",
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行天气查询

        从参数中提取城市名称，调用天气查询函数，返回天气信息。

        Args:
            parameters: 包含input参数的字典

        Returns:
            天气信息 包含input参数的字典
        """
        city = parameters.get("input", "").strip()
        if not city:
            return "错误：城市名称不能为空"
        return self._get_weather(city)

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="input",
                type="string",
                description="input是待要查询天气的城市名称，例如'长沙'。",
                required=True,
            )
        ]

    def _get_weather(self, city: str) -> str:
        """
        通过调用 wttr.in API 查询真实的天气信息。
        API格式: https://wttr.in/{city}?format=j1
        """
        url = f"https://wttr.in/{city}?format=j1"  # f格式化字符串   支持变量插值
        try:
            # 发起网络请求
            response = requests.get(url, timeout=10)
            # 检查响应状态码是否为200 (成功)
            response.raise_for_status()
            # 解析 JSON 响应
            weather_data = response.json()
            print("得到的天气数据:", weather_data)
            print(
                "================================================" * 2
            )  # *2代表将前面的字符串重复2次
            # 提取天气信息
            # weather_desc = weather_data['current_condition'][0]['weatherDesc'][0]['value']
            # return f"{city}的天气是: {weather}"

            # 提取当前天气状况
            current_condition = weather_data["current_condition"][0]
            weather_desc = current_condition["weatherDesc"][0]["value"]
            temp_c = current_condition["temp_C"]

            # 格式化成自然语言返回
            return f"{city}当前天气:{weather_desc}，气温{temp_c}摄氏度"
        except requests.exceptions.RequestException as e:
            # 处理网络错误
            return f"错误:查询天气时发出请求，遇到网络问题 - {e}"
        except (KeyError, IndexError) as e:
            # 处理数据解析错误
            return f"错误:解析天气数据失败，可能是城市名称无效 - {e}"