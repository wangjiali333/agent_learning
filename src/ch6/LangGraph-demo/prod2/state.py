from typing import TypedDict, Annotated
# 用于添加消息到状态中的装饰器
from langgraph.graph.message import add_messages

class ResearchState(TypedDict):
    """研究助手的全局状态"""
    # 对话
    messages: Annotated[list, add_messages] # 消息历史
    # 探究状态
    question: str            # 原始问题
    question_type: str       # 问题类型:simple/search/complex
    search_results: str     # 搜索结果
    knowledge_results: str          # 知识库检索结果
    analysis: str            # 分析结果
    report: str              # 报告结果

    # 控制
    iteration: int           # 当前迭代次数
    review_passed: bool      # 质量是否通过了审核
    review_feedback: str        # 质量审核的反馈意见
    next_agent: str           # 下一步要执行的agent