"""搜索工具"""
from langchain_core.tools import tool

@tool
def search_arxiv(query: str) -> str:
    """在arXiv上搜索学术论文
    当需要查找学术论文时，可以使用此工具进行搜索。
    query: 搜索关键词
    """
    try:
        import httpx
        url = f"https://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 5,
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
        # 解析简单的XML结果，提取标题和链接
        entries = resp.text.split("<entry>")[1:]  # 跳过第一个<entry>前的内容
        results = []
        for entry in entries:
            title = entry.split("<title>")[1].split("</title>")[0].strip()
            # 提取摘要
            summary = entry.split("<summary>")[1].split("</summary>")[0].strip()
            results.append(f"- {title}\n摘要: {summary[:200]}")
        return "\n\n".join(results) if results else "未找到相关论文"
    except Exception as e:
        return f"搜索arXiv失败: {str(e)}"

if __name__ == "__main__":
    result = search_arxiv.invoke({"query": "transformer"})
    print(result)
