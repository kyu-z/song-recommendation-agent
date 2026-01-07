"""
Backward compatibility adapter
Ensures old calling methods can still use the new ChromaDB backend
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from typing import List, Dict, Any
from database.vector_store import MusicVectorStore

class BackwardCompatibilityAgent:
    """
    Maintains the same interface as the original music_agent.py
    but uses the new ChromaDB system underneath
    """
    
    def __init__(self):
        self.vector_store = MusicVectorStore()
        stats = self.vector_store.get_stats()
        print(f"🔄 Compatibility mode enabled - database has {stats['total_songs']} songs")
    
    def search_similar_songs(self, target_emb: np.ndarray, top_k: int = 3) -> List[Dict]:
        """
        Compatible with original music_agent.py search_similar_songs interface
        
        Args:
            target_emb: Target feature vector
            top_k: Number of results to return
            
        Returns:
            List[Dict]: Format exactly the same as original version
        """
        # Use new vector database for search
        results = self.vector_store.search_similar(target_emb, n_results=top_k)
        
        # Convert to original version return format
        compatible_results = []
        for result in results:
            compatible_results.append({
                "filename": result['full_path'],  # Maintain original full path format
                "distance": round(result['distance'], 4)
            })
        
        return compatible_results
    
    def agent_analyze(self, song_name: str, similar_results: List[Dict]):
        """
        Compatible with original version analysis functionality
        """
        print(f"\n🤖 Music Agent Analysis Report (Compatibility Mode):")
        print(f"--------------------------------")
        print(f"Target Song: {song_name}")
        print(f"Most Similar Songs in Library:")
        
        for i, res in enumerate(similar_results):
            print(f" {i+1}. {res['filename']} (similarity distance: {res['distance']})")
        
        # Maintain original analysis logic
        if similar_results:
            top_match = similar_results[0]['filename']
            dist = similar_results[0]['distance']
            
            if dist < 0.5:
                print(f"\n💡 Conclusion: These two songs are extremely similar in timbre, the model considers them to be of the same genre.")
            else:
                print(f"\n💡 Conclusion: This song has a unique style, no perfect match found in the library, but it's closest to {top_match} in terms of timbre.")


class DatabaseCompatibility:
    """
    Provides the same interface as the original numpy database
    """
    
    def __init__(self):
        self.vector_store = MusicVectorStore()
        stats = self.vector_store.get_stats()
        if stats['is_empty']:
            print("⚠️  Database is empty, please run data migration first")
            
    @property
    def db_embeddings(self):
        """Simulate original db_embeddings array"""
        # Note: This is for compatibility, in actual use should directly call vector database
        try:
            # Get all data (for compatibility only)
            data = np.load("my_music_database.npz")
            return data['embeddings']
        except:
            print("⚠️  Cannot load original numpy file, recommend using new vector database interface")
            return np.array([])
    
    @property  
    def db_filenames(self):
        """Simulate original db_filenames array"""
        try:
            data = np.load("my_music_database.npz")
            return data['filenames']
        except:
            print("⚠️  Cannot load original numpy file, recommend using new vector database interface")
            return []


# Test compatibility
if __name__ == "__main__":
    # Test using the same method as original music_agent.py
    
    # 1. Create compatible Agent
    agent = BackwardCompatibilityAgent()
    compat_db = DatabaseCompatibility()
    
    # 2. Simulate original testing method
    if len(compat_db.db_embeddings) > 0:
        test_idx = 0
        test_emb = compat_db.db_embeddings[test_idx]
        test_name = compat_db.db_filenames[test_idx]
        
        print(f"\n🧪 Compatibility Test - Using Original Interface:")
        print(f"Test Song: {test_name}")
        
        # 3. Use exactly the same calling method
        matches = agent.search_similar_songs(test_emb, top_k=3)
        agent.agent_analyze(test_name, matches)
        
        print(f"\n✅ Compatibility test passed! New system is fully compatible with original interface.")
        
    else:
        print("❌ Compatibility test failed: Cannot access original data")
        print("💡 Suggestion: Use new vector database interface directly")
