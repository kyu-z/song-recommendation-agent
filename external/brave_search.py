"""
Brave Search API wrapper for music discovery.

Note: Free-tier quotas return HTTP 429 often; callers should expect occasional
empty or error-string results and keep query counts modest.
"""
import requests
from typing import Optional, List, Dict, Any, Union


class BraveSearchTool:
    """Brave Search API wrapper for music discovery"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
    
    def run(self, query: str, count: int = 10) -> str:
        """Execute search query and return formatted results"""
        results = self.run_structured(query=query, count=count)
        if isinstance(results, str):
            return results

        formatted_results = []
        for result in results:
            title = result.get("title", "")
            url = result.get("url", "")
            description = result.get("description", "")
            formatted_results.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n")
        return "\n".join(formatted_results)

    def run_structured(self, query: str, count: int = 10) -> Union[List[Dict[str, Any]], str]:
        """Execute search query and return structured results (title/url/description)."""
        try:
            params = {
                "q": query,
                "count": count,
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate",
                "freshness": "py",  # Past year
                "text_decorations": False
            }
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("web", {}).get("results", [])
            structured: List[Dict[str, Any]] = []
            for result in results:
                structured.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                })
            return structured
            
        except requests.RequestException as e:
            print(f"Brave Search API error: {e}")
            return f"Search failed: {e}"
        except Exception as e:
            print(f"Brave Search processing error: {e}")
            return f"Search processing failed: {e}"
