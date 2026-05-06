"""
Web Search Tool for LLM Function Calling

Provides web search capability using DuckDuckGo (no API key required)
or other search engines. Returns search results that the LLM can use
to answer questions about current events, facts, or web content.

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("web-search-tool")


# Tool definition in Anthropic format
web_search_tool = {
    "name": "web_search",
    "description": (
        "Search the web for current information, news, facts, or any content "
        "not in your training data. Use this when you need up-to-date information, "
        "current events, or to verify facts. Returns a list of search results with "
        "titles, snippets, and URLs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. Be specific and use keywords that will return relevant results.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


def execute_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Execute a web search using DuckDuckGo (no API key required).

    Args:
        query: The search query string
        max_results: Maximum number of results to return (1-10)

    Returns:
        Dictionary containing search results:
        {
            "success": bool,
            "query": str,
            "results": List[Dict],
            "error": Optional[str]
        }

    Example:
        >>> result = execute_web_search("latest Python releases")
        >>> print(result["results"][0]["title"])
    """
    try:
        # Validate query
        if not query or not query.strip():
            return {
                "success": False,
                "query": query,
                "results": [],
                "error": "Search query cannot be empty",
            }

        # Limit results
        max_results = max(1, min(max_results, 10))

        # Try to import ddgs
        try:
            from ddgs import DDGS
        except ImportError:
            return {
                "success": False,
                "query": query,
                "results": [],
                "error": (
                    "ddgs not installed. "
                    "Install with: pip install ddgs"
                ),
            }

        # Perform search
        logger.info(f"Executing web search: '{query}' (max_results={max_results})")

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        # Format results
        formatted_results = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]

        logger.info(f"Web search returned {len(formatted_results)} results")

        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Web search failed: {e}", exc_info=True)
        return {
            "success": False,
            "query": query,
            "results": [],
            "error": str(e),
        }


def format_search_results_for_llm(search_result: Dict[str, Any]) -> str:
    """
    Format search results into a readable string for the LLM.

    Args:
        search_result: Result from execute_web_search()

    Returns:
        Formatted string with search results

    Example:
        >>> result = execute_web_search("Python 3.13")
        >>> print(format_search_results_for_llm(result))
    """
    if not search_result["success"]:
        return f"Search failed: {search_result.get('error', 'Unknown error')}"

    results = search_result["results"]
    if not results:
        return f"No results found for query: {search_result['query']}"

    # Format results
    formatted = f"Search results for '{search_result['query']}':\n\n"

    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result['title']}\n"
        formatted += f"   {result['snippet']}\n"
        formatted += f"   URL: {result['url']}\n\n"

    return formatted.strip()
