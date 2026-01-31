"""
Brave Search API wrapper for music discovery
"""
import requests
from typing import Optional


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
            
            # Format results for LLM consumption
            formatted_results = []
            for result in results:
                title = result.get("title", "")
                url = result.get("url", "")
                description = result.get("description", "")
                
                formatted_results.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n")
            
            return "\n".join(formatted_results)
            
        except requests.RequestException as e:
            print(f"Brave Search API error: {e}")
            return f"Search failed: {e}"
        except Exception as e:
            print(f"Brave Search processing error: {e}")
            return f"Search processing failed: {e}"
