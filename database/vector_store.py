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
    
    def search_similar(self, query_embedding: np.ndarray, n_results: int = 5, 
                      include_self: bool = False, where_metadata: Dict = None) -> List[Dict]:
        """
        Search for similar music with optional metadata filtering
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            include_self: Whether to include the query song itself
            where_metadata: Optional metadata filters (e.g., {"vocal_type": "instrumental"})
            
        Returns:
            List[Dict]: List of similar songs matching criteria
        """
        try:
            # Ensure input is in correct format
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.flatten().tolist()
            
            actual_n = n_results if include_self else n_results + 1

            # Prepare query parameters
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": actual_n
            }
            
            # Add metadata filtering if provided
            if where_metadata:
                # Ensure we exclude GTZAN data by default
                if "source" not in where_metadata:
                    where_metadata = {"$and": [where_metadata, {"source": {"$ne": "gtzan"}}]}
                query_params["where"] = where_metadata

            # Execute similarity search
            results = self.collection.query(**query_params)
            
            # Format return results
            similar_songs = []
            for i in range(len(results['ids'][0])):
                dist = results['distances'][0][i]
                
                # Filter logic: if distance is very small (almost 0) and set not to include self, skip
                if not include_self and dist < 1e-5:
                    continue

                similar_songs.append({
                    'id': results['ids'][0][i],
                    'filename': results['metadatas'][0][i].get('filename', 'Unknown'),
                    'full_path': results['metadatas'][0][i].get('full_path', ''),
                    'title': results['metadatas'][0][i].get('title', 'Unknown'),
                    'artist': results['metadatas'][0][i].get('artist', 'Unknown'),
                    'genre': results['metadatas'][0][i].get('genre', 'Unknown'),
                    'vocal_type': results['metadatas'][0][i].get('vocalinstrumental', 'unknown'),
                    'tags': results['metadatas'][0][i].get('tags', ''),
                    'speed': results['metadatas'][0][i].get('speed', 'unknown'),
                    'distance': results['distances'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
            
            return similar_songs
            
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    def search_by_metadata(self, criteria: Dict[str, Any], limit: int = 15) -> List[Dict]:
        """
        Pure semantic search based on metadata only (no vector similarity)
        
        Args:
            criteria: Search criteria dict, e.g., {"vocal_type": "instrumental", "speed": "medium"}
            limit: Maximum number of results
            
        Returns:
            List of songs matching metadata criteria (excludes GTZAN by default)
        """
        try:
            # Always exclude GTZAN training data unless explicitly included
            if "source" not in criteria:
                where_filter = {"$and": [criteria, {"source": {"$ne": "gtzan"}}]}
            else:
                where_filter = criteria
            
            results = self.collection.get(
                where=where_filter,
                include=['metadatas'],
                limit=limit
            )
            
            if not results or not results.get('metadatas'):
                return []
            
            formatted_results = []
            for i, metadata in enumerate(results['metadatas']):
                formatted_results.append({
                    'id': results['ids'][i],
                    'title': metadata.get('title', 'Unknown'),
                    'artist': metadata.get('artist', 'Unknown'),
                    'genre': metadata.get('genre', 'Unknown'),
                    'vocal_type': metadata.get('vocalinstrumental', 'unknown'),
                    'tags': metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                    'speed': metadata.get('speed', 'unknown'),
                    'source': metadata.get('source', 'unknown'),
                    'album_name': metadata.get('album_name', 'Unknown'),
                    'metadata': metadata
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Metadata search failed: {e}")
            return []

    def search_by_tags(self, tag_query: str, limit: int = 15) -> List[Dict]:
        """
        Search songs by tags using partial string matching
        
        Args:
            tag_query: Tag to search for (e.g., "chill", "beach", "electronic")
            limit: Maximum number of results
            
        Returns:
            List of songs with matching tags (excludes GTZAN by default)
        """
        try:
            # Get all non-GTZAN songs
            results = self.collection.get(
                where={"source": {"$ne": "gtzan"}},
                include=['metadatas'],
                limit=1000  # Get more to filter properly
            )
            
            if not results or not results.get('metadatas'):
                return []
            
            # Filter by tag content
            matched_songs = []
            tag_query_lower = tag_query.lower()
            
            for i, metadata in enumerate(results['metadatas']):
                tags_str = metadata.get('tags', '').lower()
                if tag_query_lower in tags_str:
                    matched_songs.append({
                        'id': results['ids'][i],
                        'title': metadata.get('title', 'Unknown'),
                        'artist': metadata.get('artist', 'Unknown'),
                        'genre': metadata.get('genre', 'Unknown'),
                        'vocal_type': metadata.get('vocalinstrumental', 'unknown'),
                        'tags': metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                        'speed': metadata.get('speed', 'unknown'),
                        'source': metadata.get('source', 'unknown'),
                        'metadata': metadata
                    })
                    
                    if len(matched_songs) >= limit:
                        break
            
            return matched_songs
            
        except Exception as e:
            print(f"Tag search failed: {e}")
            return []

    def hybrid_search(self, query_embedding: np.ndarray = None, metadata_criteria: Dict = None, 
                     tag_query: str = None, limit: int = 15, balance_ratio: float = 0.5) -> List[Dict]:
        """
        Hybrid search combining semantic (metadata) and acoustic (vector) similarity
        
        Args:
            query_embedding: Optional vector for acoustic similarity
            metadata_criteria: Optional metadata filters
            tag_query: Optional tag search string
            limit: Maximum number of results
            balance_ratio: How to balance results (0.5 = equal weight)
            
        Returns:
            List of songs combining semantic and acoustic matches
        """
        try:
            all_results = []
            
            # 1. Acoustic similarity search (if embedding provided)
            if query_embedding is not None:
                acoustic_results = self.search_similar(
                    query_embedding, 
                    n_results=max(1, int(limit * balance_ratio * 2)),
                    where_metadata=metadata_criteria
                )
                for result in acoustic_results:
                    result['match_type'] = 'acoustic'
                    result['score'] = 1.0 - result['distance']  # Convert distance to similarity
                all_results.extend(acoustic_results)
            
            # 2. Semantic metadata search
            if metadata_criteria:
                semantic_results = self.search_by_metadata(
                    metadata_criteria, 
                    limit=max(1, int(limit * (1 - balance_ratio) * 2))
                )
                for result in semantic_results:
                    result['match_type'] = 'semantic'
                    result['score'] = 1.0  # Full semantic match
                all_results.extend(semantic_results)
            
            # 3. Tag-based search
            if tag_query:
                tag_results = self.search_by_tags(
                    tag_query,
                    limit=max(1, int(limit * (1 - balance_ratio)))
                )
                for result in tag_results:
                    result['match_type'] = 'tags'
                    result['score'] = 0.8  # High but not perfect score
                all_results.extend(tag_results)
            
            # 4. Deduplicate and rank results
            seen_ids = set()
            unique_results = []
            
            for result in all_results:
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    unique_results.append(result)
            
            # Sort by score (highest first)
            unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return unique_results[:limit]
            
        except Exception as e:
            print(f"Hybrid search failed: {e}")
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
        Add a single song with enhanced metadata support
        
        Args:
            embedding: Song feature vector
            metadata: Enhanced metadata including Jamendo fields
            song_id: Song ID, auto-generated if not provided
            
        Returns:
            bool: Whether addition was successful
        """
        try:
            if song_id is None:
                song_id = f"song_{self.collection.count():04d}"
            
            # Ensure all metadata values are compatible with ChromaDB
            processed_metadata = {}
            for key, value in metadata.items():
                if value is None:
                    processed_metadata[key] = ""
                elif isinstance(value, (list, tuple)):
                    # Convert lists to comma-separated strings
                    processed_metadata[key] = ",".join(str(v) for v in value if v)
                else:
                    processed_metadata[key] = str(value)
            
            self.collection.add(
                embeddings=[embedding.flatten().tolist()],
                metadatas=[processed_metadata],
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
    
    def get_genres_pool(self) -> List[str]:
        """
        Get all unique genres available in the database (excluding GTZAN training data)
        
        Returns:
            List of unique genres from user library only
        """
        try:
            # Only get genres from non-GTZAN sources
            results = self.collection.get(
                where={"source": {"$ne": "gtzan"}},  # Exclude GTZAN data
                include=['metadatas']
            )
            if not results or not results.get('metadatas'):
                return []
            
            genres = set()
            for metadata in results['metadatas']:
                genre = metadata.get('genre')
                if genre:
                    genres.add(genre.lower().strip())
            
            return sorted(list(genres))
            
        except Exception as e:
            print(f"Failed to get genres pool: {e}")
            return []
    
    def search_by_genre_enhanced(self, genre: str, limit: int = 15, 
                               include_similar: bool = False) -> List[Dict]:
        """
        Enhanced genre-based search with optional similarity expansion (excluding GTZAN training data)
        
        Args:
            genre: Target genre
            limit: Maximum results
            include_similar: Whether to include similar genres if exact matches are low
            
        Returns:
            List of matching songs from user library only
        """
        try:
            # First try exact genre match, excluding GTZAN data
            results = self.collection.get(
                where={
                    "$and": [
                        {"genre": genre.lower()},
                        {"source": {"$ne": "gtzan"}}  # Exclude GTZAN training data
                    ]
                },
                include=['metadatas', 'embeddings'],
                limit=limit
            )
            
            songs = []
            if results and results.get('metadatas'):
                for i, metadata in enumerate(results['metadatas']):
                    songs.append({
                        'metadata': metadata,
                        'embedding': results['embeddings'][i] if results.get('embeddings') else None,
                        'match_type': 'exact'
                    })
            
            # If we don't have enough results and include_similar is True
            if len(songs) < limit // 2 and include_similar:
                # Look for partial matches or related genres, still excluding GTZAN
                all_results = self.collection.get(
                    where={"source": {"$ne": "gtzan"}},  # Exclude GTZAN data
                    include=['metadatas']
                )
                for metadata in all_results.get('metadatas', []):
                    song_genre = metadata.get('genre', '').lower()
                    if genre.lower() in song_genre or song_genre in genre.lower():
                        if len(songs) >= limit:
                            break
                        songs.append({
                            'metadata': metadata,
                            'embedding': None,
                            'match_type': 'similar'
                        })
            
            return songs[:limit]
            
        except Exception as e:
            print(f"Enhanced genre search failed: {e}")
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
