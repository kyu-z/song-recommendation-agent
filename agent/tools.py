"""
Tools for Music AI Agent
Focus on capability extension rather than process decomposition
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.vector_store import MusicVectorStore


class MusicSearchInput(BaseModel):
    """Input schema for music search tool"""
    genre: str = Field(description="Genre to search for")
    limit: int = Field(default=15, description="Maximum number of results to return")


class MusicSearchTool:
    """
    Music Search Tool - Core capability extension for vector database queries
    
    This tool handles the retrieval stage by searching the ChromaDB collection
    for music tracks matching specified criteria.
    """
    
    def __init__(self, vector_store: Optional[MusicVectorStore] = None):
        """
        Initialize music search tool
        
        Args:
            vector_store: ChromaDB vector store instance
        """
        self.vector_store = vector_store or MusicVectorStore()
    
    def search_by_genre(self, genre: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Search music by genre with enhanced filtering (excluding GTZAN training data)
        
        Args:
            genre: Target genre to search for
            limit: Maximum number of results
            
        Returns:
            List of music tracks with metadata from user library only
        """
        try:
            # Execute genre-based search, excluding GTZAN training data
            results = self.vector_store.collection.get(
                where={
                    "$and": [
                        {"genre": genre},
                        {"source": {"$ne": "gtzan"}}  # Exclude GTZAN training data
                    ]
                },
                include=['metadatas'],
                limit=limit
            )
            
            music_list = results.get('metadatas', [])
            
            if not music_list:
                return []
            
            # Return formatted results
            formatted_results = []
            for i, metadata in enumerate(music_list):
                formatted_results.append({
                    'index': i + 1,
                    'title': metadata.get('title', 'Unknown'),
                    'artist': metadata.get('artist', 'Unknown Artist'),
                    'genre': metadata.get('genre', genre),
                    'model_tag': metadata.get('model_tag', 'Unknown'),
                    'source': metadata.get('source', 'Unknown'),
                    'duration': metadata.get('duration', 0),
                    'metadata': metadata
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Music search failed: {e}")
            return []
    
    def get_available_genres(self) -> List[str]:
        """
        Get list of all available genres in the database (excluding GTZAN training data)
        
        Returns:
            List of unique genres from user library only
        """
        try:
            existing_genres = self.vector_store.collection.get(
                where={"source": {"$ne": "gtzan"}},  # Exclude GTZAN training data
                include=['metadatas']
            )['metadatas']
            unique_genres = list(set([m.get('genre') for m in existing_genres if m.get('genre')]))
            return sorted(unique_genres)
        except Exception as e:
            print(f"Failed to get genres: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.vector_store.get_stats()
    
    def as_langchain_tool(self) -> StructuredTool:
        """
        Convert to LangChain StructuredTool for agent integration
        
        Returns:
            StructuredTool instance
        """
        def _search_music(genre: str, limit: int = 15) -> str:
            """Search for music by genre"""
            results = self.search_by_genre(genre, limit)
            
            if not results:
                return f"No music found for genre: {genre}"
            
            # Format results as string for LLM consumption
            formatted = f"Found {len(results)} tracks for genre '{genre}':\n"
            for result in results[:5]:  # Limit to top 5 for context
                formatted += f"- {result['title']} by {result['artist']} ({result['model_tag']})\n"
            
            return formatted
        
        return StructuredTool(
            name="music_search",
            description="Search for music tracks by genre in the vector database",
            func=_search_music,
            args_schema=MusicSearchInput
        )


# Future expansion tools (placeholders)
class JamendoDownloadTool:
    """
    Future tool for downloading music from Jamendo
    This will be implemented in later phases for capability extension
    """
    
    def __init__(self):
        self.enabled = False
        print("🚧 JamendoDownloadTool - Coming in future phases")
    
    def download_track(self, track_id: str) -> Optional[str]:
        """Download track from Jamendo"""
        # TODO: Implement in future phases
        return None


class SpotifyAnalysisTool:
    """
    Future tool for analyzing Spotify playlists/tracks
    This will be implemented in later phases for capability extension
    """
    
    def __init__(self):
        self.enabled = False
        print("🚧 SpotifyAnalysisTool - Coming in future phases")
    
    def analyze_playlist(self, playlist_url: str) -> Optional[Dict]:
        """Analyze Spotify playlist"""
        # TODO: Implement in future phases
        return None


# Tool factory function
def create_music_tools(vector_store: Optional[MusicVectorStore] = None) -> Dict[str, Any]:
    """
    Factory function to create all available tools
    
    Args:
        vector_store: Vector store instance
        
    Returns:
        Dictionary of available tools
    """
    music_search = MusicSearchTool(vector_store)
    
    return {
        'music_search': music_search,
        'music_search_langchain': music_search.as_langchain_tool(),
        # Future tools
        'jamendo_download': JamendoDownloadTool(),
        'spotify_analysis': SpotifyAnalysisTool(),
    }


# Test script
if __name__ == "__main__":
    print("Testing Music Search Tool...")
    
    # Initialize tool
    search_tool = MusicSearchTool()
    
    # Test genre availability
    genres = search_tool.get_available_genres()
    print(f"Available genres: {genres}")
    
    # Test search functionality
    if genres:
        test_genre = genres[0]
        print(f"\nTesting search for genre: {test_genre}")
        results = search_tool.search_by_genre(test_genre, limit=3)
        
        print(f"Found {len(results)} results:")
        for result in results:
            print(f"- {result['title']} by {result['artist']}")
    
    # Test LangChain tool conversion
    lc_tool = search_tool.as_langchain_tool()
    print(f"\nLangChain tool created: {lc_tool.name}")
    
    # Get stats
    stats = search_tool.get_stats()
    print(f"\nDatabase stats: {stats}")
