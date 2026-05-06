"""Web 搜索工具 —— 容错设计，搜索失败不影响病历生成。"""


def web_search(query: str, max_results: int = 5) -> str:
    """搜索互联网获取病历书写规范、临床诊疗指南等参考信息。

    如果搜索不可用（网络限制等），优雅降级返回提示信息，
    不会阻塞病历生成流程。

    Args:
        query: 搜索关键词
        max_results: 最大结果数
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return "搜索功能未安装，跳过网络检索。（可执行 pip install ddgs 启用）"

    queries = [
        f"{query} 病历书写规范 SOAP格式 site:zhihu.com OR site:dxy.cn",
        f"{query} 临床诊疗指南 site:msdmanuals.cn",
        f"{query} 门诊病历模板",
    ]

    all_snippets = []
    seen_links = set()

    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=3))
                    for r in results:
                        link = r.get("href", "")
                        if link and link not in seen_links:
                            seen_links.add(link)
                            all_snippets.append(
                                f"[{r.get('title', '')}]\n{r.get('body', '')}\n{link}"
                            )
                except Exception:
                    continue
    except Exception as e:
        # 网络不可达等，静默降级
        return f"网络搜索暂不可用（{str(e)[:100]}），将基于模型内置医学知识生成病历。"

    if not all_snippets:
        return "未搜索到额外参考资料，将基于模型内置医学知识生成病历。"

    return "\n\n---\n\n".join(all_snippets[:max_results])
