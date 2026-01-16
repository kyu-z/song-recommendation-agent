"""
ChromaDB vector database wrapper class
Migrate existing numpy database to professional vector database
"""
import chromadb
import numpy as np
from typing import List, Dict, Any
import os

class MusicVectorStore:
    def __init__(self, collection_name: str = "music_embeddings", persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB vector storage
        
        Args:
            collection_name: Collection name
            persist_directory: Persistent storage directory
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(collection_name)
            print(f"Connected to existing collection: {collection_name}")
        except:
            # Create new collection
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Music embeddings from SE-ResNet V4 model"}
            )
            print(f"Created new collection: {collection_name}")
    
    def migrate_from_numpy(self, npz_path: str) -> bool:
        """
        Migrate data from numpy file to ChromaDB
        
        Args:
            npz_path: Numpy file path
            
        Returns:
            bool: Whether migration was successful
        """
        try:
            # Check if file exists
            if not os.path.exists(npz_path):
                print(f"Error: File {npz_path} does not exist")
                return False
            
            # Load numpy data
            print(f"Loading data: {npz_path}")
            data = np.load(npz_path)
            embeddings = data['embeddings']
            filenames = data['filenames']
            
            print(f"Found {len(embeddings)} song feature vectors")
            
            # Check if collection already has data
            existing_count = self.collection.count()
            if existing_count > 0:
                print(f"Warning: Collection already has {existing_count} records, skipping migration")
                return True
            
            # Prepare ChromaDB format data
            ids = [f"song_{i:04d}" for i in range(len(filenames))]
            
            # Extract filename as basic metadata
            metadatas = []
            for fname in filenames:
                basename = os.path.basename(fname)
                name_without_ext = os.path.splitext(basename)[0]
                metadatas.append({
                    "filename": basename,
                    "full_path": fname,
                    "title": name_without_ext
                })
            
            # Batch insert into ChromaDB
            print("Inserting data into ChromaDB...")
            self.collection.add(
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ Successfully migrated {len(embeddings)} songs to ChromaDB")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    def search_similar(self, query_embedding: np.ndarray, n_results: int = 5, include_self: bool = False) -> List[Dict]:
        """
        Search for similar music
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            
        Returns:
            List[Dict]: List of similar songs
        """
        try:
            # Ensure input is in correct format
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.flatten().tolist()
            
            actual_n = n_results if include_self else n_results + 1

            # Execute similarity search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_n
            )
            
            # Format return results
            similar_songs = []
            for i in range(len(results['ids'][0])):
                dist = results['distances'][0][i]
                
                # Filter logic: if distance is very small (almost 0) and set not to include self, skip
                if not include_self and dist < 1e-5:
                    continue

                similar_songs.append({
                    'id': results['ids'][0][i],
                    'filename': results['metadatas'][0][i]['filename'],
                    'full_path': results['metadatas'][0][i]['full_path'],
                    'title': results['metadatas'][0][i]['title'],
                    'distance': results['distances'][0][i]
                })
            
            return similar_songs
            
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    def song_exists(self, full_path: str) -> bool:
        """
        Check if a song with the given full path already exists
        
        Args:
            full_path: Full file path to check
            
        Returns:
            bool: True if song exists, False otherwise
        """
        try:
            # Check if collection is empty first
            count = self.collection.count()
            if count == 0:
                return False
                
            results = self.collection.query(
                query_embeddings=[[0.0] * 128],  # Dummy embedding
                n_results=count,
                where={"full_path": full_path}
            )
            return len(results['ids'][0]) > 0
        except Exception as e:
            print(f"Error checking song existence: {str(e)}")
            return False
    
    def add_song(self, embedding: np.ndarray, metadata: Dict[str, Any], song_id: str = None) -> bool:
        """
        Add a single song
        
        Args:
            embedding: Song feature vector
            metadata: Metadata
            song_id: Song ID, auto-generated if not provided
            
        Returns:
            bool: Whether addition was successful
        """
        try:
            if song_id is None:
                song_id = f"song_{self.collection.count():04d}"
            
            self.collection.add(
                embeddings=[embedding.flatten().tolist()],
                metadatas=[metadata],
                ids=[song_id]
            )
            return True
        except Exception as e:
            print(f"Failed to add song: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dict: Statistics information
        """
        count = self.collection.count()
        return {
            "total_songs": count,
            "collection_name": self.collection.name,
            "is_empty": count == 0
        }
    
    import numpy as np

    def get_gtzan_centroid(self, genre_name):
        """
        Calculates the mean vector (centroid) for a specific GTZAN genre 
        to use as an acoustic baseline.
        """
        try:
            # 1. Query the collection for tracks belonging to the specified GTZAN genre
            # Note: We filter by 'source' to ensure we only use original GTZAN data
            results = self.collection.get(
                where={
                    "$and": [
                        {"genre": genre_name},
                        {"source": "gtzan"} 
                    ]
                },
                include=["embeddings"]
            )

            # 2. Check if we found any matching vectors
            if results is None or 'embeddings' not in results or len(results['embeddings']) == 0:
                print(f"⚠️  No GTZAN reference data found for genre: {genre_name}")
                return None

            # 3. Convert list of embeddings to a numpy array for mathematical operations
            embeddings_array = np.array(results['embeddings'])
            
            # 4. Calculate the mean along the first axis (average of all vectors)
            # This creates a single 'representative' vector for the entire genre
            centroid = np.mean(embeddings_array, axis=0)
            
            return centroid

        except Exception as e:
            # Log error if the query or calculation fails
            print(f"Error calculating centroid: {e}")
            return None
        
    def get_all_songs(self) -> List[Dict]:
        """
        Get all songs in the collection
        
        Returns:
            List of all songs with their metadata
        """
        try:
                if self.collection is None:
                    return []
                
                # Get all results without filtering
                results = self.collection.get(
                    include=['metadatas', 'documents', 'embeddings']
                )
                
                if not results or not results.get('metadatas'):
                    return []
                
                songs = []
                metadatas = results['metadatas']
                ids = results['ids']
                
                for i, metadata in enumerate(metadatas):
                    song_info = {
                        'id': ids[i] if ids else f"song_{i}",
                        'metadata': metadata or {}
                    }
                    songs.append(song_info)
                
                return songs
                
        except Exception as e:
            print(f"Failed to get all songs: {e}")
            return []
    
    def delete_collection(self):
        """Delete entire collection (dangerous operation)"""
        try:
            self.client.delete_collection(self.collection.name)
            print("⚠️  Collection deleted")
        except Exception as e:
            print(f"Failed to delete collection: {str(e)}")


# Test script
if __name__ == "__main__":
    # Create vector store instance
    vector_store = MusicVectorStore()
    
    # Display current status
    stats = vector_store.get_stats()
    print(f"Database status: {stats}")
    
    # If database is empty, try to migrate data
    if stats["is_empty"]:
        print("\nStarting data migration...")
        success = vector_store.migrate_from_numpy("my_music_database.npz")
        if success:
            print("Data migration completed!")
            stats = vector_store.get_stats()
            print(f"New database status: {stats}")
    
    # Test search functionality
    if stats["total_songs"] > 0:
        print("\nTesting search functionality...")
        # Load a song vector for testing
        try:
            data = np.load("my_music_database.npz")
            test_embedding = data['embeddings'][0]  # Take the first song

            results = vector_store.search_similar(test_embedding, n_results=3, include_self=False)
            print("Search results:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']} (distance: {result['distance']:.4f})")
                
        except Exception as e:
            print(f"Test search failed: {str(e)}")
