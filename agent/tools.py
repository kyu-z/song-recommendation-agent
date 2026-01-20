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
    vocal_type: Optional[str] = Field(default=None, description="Filter by vocal type: 'vocal' or 'instrumental'")
    keywords: Optional[str] = Field(default=None, description="Keywords to search in tags (comma-separated)")


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
    
    def search_by_genre(self, genre: str, limit: int = 15, 
                       vocal_type: Optional[str] = None, 
                       keywords: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search music by genre with enhanced filtering and Jamendo metadata support
        
        Args:
            genre: Target genre to search for
            limit: Maximum number of results
            vocal_type: Filter by vocal type ('vocal' or 'instrumental')
            keywords: Keywords to search in tags (comma-separated)
            
        Returns:
            List of music tracks with metadata including source_tags and vocal_type
        """
        try:
            # Build complex where query
            where_conditions = [
                {"genre": genre},
                {"source": {"$ne": "gtzan"}}  # Exclude GTZAN training data
            ]
            
            # Add vocal_type filter if provided
            if vocal_type:
                # Normalize vocal_type values
                vocal_type_normalized = vocal_type.lower().strip()
                if vocal_type_normalized in ['vocal', 'instrumental']:
                    where_conditions.append({"vocalinstrumental": vocal_type_normalized})
            
            # Construct final where query
            where_query = {"$and": where_conditions}
            
            # Execute search
            results = self.vector_store.collection.get(
                where=where_query,
                include=['metadatas'],
                limit=limit * 2  # Get more results for keyword filtering
            )
            
            music_list = results.get('metadatas', [])
            ids_list = results.get('ids', [])
            
            if not music_list:
                return []
            
            # Filter by keywords if provided
            filtered_results = []
            if keywords:
                keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
                
                for i, metadata in enumerate(music_list):
                    tags_str = metadata.get('tags', '').lower()
                    # Check if any keyword matches tags
                    if any(keyword in tags_str for keyword in keyword_list):
                        filtered_results.append((ids_list[i] if i < len(ids_list) else None, metadata))
            else:
                # No keyword filtering, use all results
                for i, metadata in enumerate(music_list):
                    filtered_results.append((ids_list[i] if i < len(ids_list) else None, metadata))
            
            # Limit results
            filtered_results = filtered_results[:limit]
            
            # Format results with source_tags and vocal_type
            formatted_results = []
            for idx, (song_id, metadata) in enumerate(filtered_results):
                # Extract tags (source_tags)
                tags_str = metadata.get('tags', '')
                source_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
                
                # Extract vocal_type
                vocal_type_value = metadata.get('vocalinstrumental', 'unknown')
                
                formatted_results.append({
                    'index': idx + 1,
                    'id': song_id,
                    'title': metadata.get('title', 'Unknown'),
                    'artist': metadata.get('artist', 'Unknown Artist'),
                    'genre': metadata.get('genre', genre),
                    'model_tag': metadata.get('model_tag', 'Unknown'),
                    'source': metadata.get('source', 'Unknown'),
                    'duration': metadata.get('duration', 0),
                    'source_tags': source_tags,  # List of tags
                    'vocal_type': vocal_type_value,  # vocal/instrumental/unknown
                    'speed': metadata.get('speed', 'unknown'),
                    'album_name': metadata.get('album_name', ''),
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
        def _search_music(genre: str, limit: int = 15, 
                         vocal_type: Optional[str] = None, 
                         keywords: Optional[str] = None) -> str:
            """Search for music by genre with optional vocal type and keyword filters"""
            results = self.search_by_genre(genre, limit, vocal_type, keywords)
            
            if not results:
                filter_info = []
                if vocal_type:
                    filter_info.append(f"vocal_type={vocal_type}")
                if keywords:
                    filter_info.append(f"keywords={keywords}")
                filter_str = f" with filters: {', '.join(filter_info)}" if filter_info else ""
                return f"No music found for genre: {genre}{filter_str}"
            
            # Format results as string for LLM consumption with source_tags and vocal_type
            formatted = f"Found {len(results)} tracks for genre '{genre}'"
            if vocal_type:
                formatted += f" (vocal_type: {vocal_type})"
            if keywords:
                formatted += f" (keywords: {keywords})"
            formatted += ":\n\n"
            
            for result in results[:5]:  # Limit to top 5 for context
                # Format tags
                tags_display = ", ".join(result['source_tags']) if result['source_tags'] else "无标签"
                
                # Format vocal type
                vocal_display = result['vocal_type'] if result['vocal_type'] != 'unknown' else "未知"
                
                formatted += f"- {result['title']} by {result['artist']}\n"
                formatted += f"  标签：[{tags_display}] | 类型：[{vocal_display}]\n"
                formatted += f"  流派：{result['genre']} | 模型标签：{result['model_tag']}\n\n"
            
            return formatted
        
        return StructuredTool(
            name="music_search",
            description="Search for music tracks by genre in the vector database. Supports filtering by vocal_type (vocal/instrumental) and keywords in tags.",
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
            print(f"  标签：{result.get('source_tags', [])} | 类型：{result.get('vocal_type', 'unknown')}")
        
        # Test with vocal_type filter
        print(f"\nTesting search with vocal_type filter: instrumental")
        results_instrumental = search_tool.search_by_genre(test_genre, limit=3, vocal_type="instrumental")
        print(f"Found {len(results_instrumental)} instrumental results")
        
        # Test with keywords
        print(f"\nTesting search with keywords: 'electronic'")
        results_keywords = search_tool.search_by_genre(test_genre, limit=3, keywords="electronic")
        print(f"Found {len(results_keywords)} results with keywords")
    
    # Test LangChain tool conversion
    lc_tool = search_tool.as_langchain_tool()
    print(f"\nLangChain tool created: {lc_tool.name}")
    
    # Get stats
    stats = search_tool.get_stats()
    print(f"\nDatabase stats: {stats}")
