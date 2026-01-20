"""
Music Library Expander

This module automatically expands the music library by downloading songs from various sources
while avoiding overlap with GTZAN dataset used for model training.

"""

import os
import sys
import json
import requests
import torch.nn.functional as F
import torch
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import time
import random
from dataclasses import dataclass
from urllib.parse import urljoin
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.audio_processor import AudioFeatureExtractor
from database.vector_store import MusicVectorStore

# Load environment variables
load_dotenv()  # Load .env first
load_dotenv('.env.local')  # Load .env.local to override


@dataclass
class MusicSource:
    """Represents a music source with metadata"""
    title: str
    artist: str
    url: str
    source: str  # 'jamendo'
    genre: Optional[str] = None
    duration: Optional[int] = None
    license_info: Optional[str] = None
    # New Jamendo-specific fields
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    speed: Optional[str] = None
    vocalinstrumental: Optional[str] = None
    downloads_total: Optional[int] = None
    release_date: Optional[str] = None
    album_name: Optional[str] = None


class MusicExpander:
    """
    Automatic music library expansion tool
    
    Downloads music from various free/open sources while avoiding GTZAN overlap
    """
    
    def __init__(self, 
                 download_dir: str = "expanded_music",
                 vector_store: Optional[MusicVectorStore] = None,
                 audio_processor: Optional[AudioFeatureExtractor] = None):
        """
        Initialize the Music Expander
        
        Args:
            download_dir: Directory to store downloaded music
            vector_store: Vector database instance
            audio_processor: Audio feature extractor instance
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.vector_store = vector_store or MusicVectorStore()
        self.audio_processor = audio_processor or AudioFeatureExtractor()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # GTZAN genres to avoid (since our model was trained on GTZAN)
        self.gtzan_genres = {
            'blues', 'classical', 'country', 'disco', 'hiphop',
            'jazz', 'metal', 'pop', 'reggae', 'rock'
        }
        
        # Load configuration
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration for music sources"""
        config_path = Path(__file__).parent.parent / "config" / "music_sources.json"
        
        default_config = {
            "jamendo": {
                "enabled": True,
                "api_key": "ENV:JAMENDO_CLIENT_ID",
                "max_downloads": 20,
                "genres": ["electronic", "instrumental", "ambient", "synthwave", "lofi", "citypop", "shoegaze"]
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Process environment variable references
                    config = self._resolve_env_vars(config)
                    return config
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}, using defaults")
        
        return self._resolve_env_vars(default_config)
    
    def _resolve_env_vars(self, config: Dict) -> Dict:
        """Resolve environment variable references in config"""
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("ENV:"):
                env_var = value[4:]  # Remove "ENV:" prefix
                return os.getenv(env_var)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            return value
        
        return resolve_value(config)
    
    def is_too_similar_to_legacy(self, embedding, source_genre):
        """
        Scans the downloaded audio against all legacy GTZAN genre centroids.
        Returns True if the audio is too acoustically similar to ANY legacy genre 
        """
        legacy_labels = [
            "blues", "classical", "country", "disco", "hiphop", 
            "jazz", "metal", "pop", "reggae", "rock"
        ]

        threshold = 0.95
        if source_genre.lower() not in legacy_labels:
            self.logger.info(f"✨ 发现新潮流派 [{source_genre}]，自动调高过滤阈值至 0.99")
            threshold = 0.99
        try:
            # Convert to torch tensor for high-performance similarity calculation
            new_vec = torch.tensor(embedding).flatten().unsqueeze(0)

            # 2. Iterate through all genres we want to protect (GTZAN standard set)
            for genre in self.gtzan_genres:
                # Retrieve the average vector (centroid) for this specific legacy genre
                legacy_centroid = self.vector_store.get_gtzan_centroid(genre)
                
                if legacy_centroid is None:
                    continue
                    
                legacy_vec = torch.tensor(legacy_centroid).flatten().unsqueeze(0)
                
                # 3. Calculate similarity score between new song and legacy genre DNA
                similarity = F.cosine_similarity(new_vec, legacy_vec).item()
                
                # 4. If similarity is too high for ANY genre, trigger the rejection
                self.logger.info(f"Checking similarity with legacy {genre}: {similarity:.4f}")
        
                if similarity > threshold:
                    return True
            
            # If the loop finishes without exceeding threshold, the song is safe/modern
            return False

        except Exception as e:
            print(f"Acoustic validation failed: {e}")
            return False


    def get_jamendo_tracks(self, genre: str = "electronic", max_tracks: int = 10) -> List[MusicSource]:
        """
        Get tracks from Jamendo (Creative Commons music)
        
        Requires API key from https://developer.jamendo.com/
        """
        api_key = self.config.get("jamendo", {}).get("api_key")
        if not api_key:
            self.logger.warning("Jamendo API key not provided, skipping...")
            return []
        
        base_url = "https://api.jamendo.com/v3.0/tracks/"
        
        # Try different search approaches with enhanced metadata
        search_params_list = [
            # Method 1: Search by tags
            {
                'client_id': api_key,
                'format': 'json',
                'limit': min(max_tracks, 50),
                'tags': genre,
                'audioformat': 'mp32',
                'include': 'musicinfo'
            },
            # Method 2: Search by text in name/artist
            {
                'client_id': api_key,
                'format': 'json',
                'limit': min(max_tracks, 50),
                'search': genre,
                'audioformat': 'mp32',
                'include': 'musicinfo'
            },
            # Method 3: General search with order by popularity
            {
                'client_id': api_key,
                'format': 'json',
                'limit': min(max_tracks, 50),
                'order': 'popularity_total',
                'audioformat': 'mp32',
                'include': 'musicinfo'
            }
        ]
        
        all_sources = []
        
        for params in search_params_list:
            try:
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'headers' in data and data['headers'].get('status') == 'failed':
                    error_msg = data['headers'].get('error_message', 'Unknown error')
                    self.logger.error(f"Jamendo API error: {error_msg}")
                    if 'not authorized' in error_msg.lower():
                        self.logger.warning("Jamendo API key may be invalid or needs activation. Please check your credentials at https://developer.jamendo.com/")
                    continue
                
                tracks = data.get('results', [])
                
                for track in tracks:
                    # Filter tracks that might match our genre
                    track_name = track.get('name', '').lower()
                    artist_name = track.get('artist_name', '').lower()
                    
                    # If we're searching for a specific genre, check if it appears in title or artist
                    if params.get('search') or params.get('tags'):
                        if genre.lower() in track_name or genre.lower() in artist_name:
                            genre_match = True
                        else:
                            genre_match = False
                    else:
                        genre_match = True  # Accept all for general popularity search
                    
                    if genre_match or len(all_sources) < max_tracks//3:  # Allow some general tracks
                        # Extract enhanced metadata from Jamendo API
                        musicinfo = track.get('musicinfo', {})
                        
                        # Parse tags if available - Jamendo tags structure
                        tags = []
                        tag_data = musicinfo.get('tags', {})
                        if isinstance(tag_data, dict):
                            # Get genres and instruments
                            genres = tag_data.get('genres', [])
                            instruments = tag_data.get('instruments', [])
                            vartags = tag_data.get('vartags', [])
                            tags = genres + instruments + vartags
                        
                        source = MusicSource(
                            title=track.get('name', 'Unknown'),
                            artist=track.get('artist_name', 'Unknown Artist'),
                            url=track.get('audio', ''),
                            source="jamendo",
                            genre=genre,
                            duration=int(track.get('duration', 0)),
                            license_info="Creative Commons",
                            # Enhanced Jamendo metadata
                            tags=tags,
                            description=track.get('shorturl', ''),  # Use shorturl as description for now
                            speed=musicinfo.get('speed', 'unknown'),
                            vocalinstrumental=musicinfo.get('vocalinstrumental', 'unknown'),
                            downloads_total=0,  # Not available in this API response
                            release_date=track.get('releasedate', ''),
                            album_name=track.get('album_name', '')
                        )
                        all_sources.append(source)
                        
                        if len(all_sources) >= max_tracks:
                            break
                
                if len(all_sources) >= max_tracks:
                    break
                    
            except Exception as e:
                self.logger.warning(f"Jamendo search method failed: {e}")
                continue
        
        return all_sources[:max_tracks]
    
    def download_track(self, source: MusicSource) -> Optional[str]:
        """
        Download a single track
        
        Args:
            source: MusicSource object with download information
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            if source.source in ["jamendo"]:
                return self._download_direct_url(source)
            else:
                self.logger.warning(f"Unsupported source type: {source.source}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to download {source.title}: {e}")
            return None
    
    def _download_direct_url(self, source: MusicSource) -> Optional[str]:
        """Download track from direct URL"""
        try:
            response = requests.get(source.url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Generate filename
            safe_title = "".join(c for c in source.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = self.download_dir / f"{safe_title}_{source.source}.mp3"
            
            # Check if already exists
            if filename.exists():
                self.logger.info(f"File already exists: {filename}")
                return str(filename)
            
            # Download
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"Downloaded: {filename}")
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"Direct download failed for {source.title}: {e}")
            return None
    
    def expand_library(self, 
                      target_count: int = 50,
                      genres: Optional[List[str]] = None,
                      process_immediately: bool = True) -> Dict[str, int]:
        """
        Main method to expand the music library
        
        Args:
            target_count: Target number of new songs to add
            genres: List of genres to focus on (None for default)
            process_immediately: Whether to extract features immediately
            
        Returns:
            Dictionary with statistics about the expansion
        """
        if genres is None:
            genres = ["ambient", "electronic", "indie", "lo-fi", "synthwave", "instrumental"]
        
        num_genres = len(genres)
        target_per_genre = target_count // num_genres
        self.logger.info(f"Each genre will aim for approx {target_per_genre} songs")
        
        stats = {
            "attempted_downloads": 0,
            "successful_downloads": 0,
            "processed_to_db": 0,
            "skipped_gtzan_like": 0,
            "failed_downloads": 0
        }
        
        self.logger.info(f"🚀 Starting library expansion (target: {target_count} songs)")
        
        # Get current library size
        results = self.vector_store.get_all_songs()
        if isinstance(results, dict) and 'ids' in results:
            current_count = len(results['ids'])
        else:
            current_count = len(results) if results else 0
        
        total_downloaded_count = 0
        
        for i, genre in enumerate(genres):
            if total_downloaded_count >= target_count:
                break

            if i == num_genres - 1:
                current_genre_limit = target_count - total_downloaded_count
            else:
                current_genre_limit = target_per_genre
                
            genre_downloaded_count = 0  # 这个流派特有的计数器
            
            self.logger.info(f"🎵 Processing genre: {genre} (Target for this genre: {current_genre_limit})")
            
            # Get sources from Jamendo
            all_sources = []
            search_limit = max(5, current_genre_limit * 3)
            
            # Jamendo
            jamendo_sources = self.get_jamendo_tracks(genre, search_limit)
            all_sources.extend(jamendo_sources)
            
            # Shuffle for variety
            random.shuffle(all_sources)
            
            # Download and process
            for source in all_sources:
                if genre_downloaded_count >= current_genre_limit:
                    self.logger.info(f"✅ Reached quota for {genre}, moving to next genre.")
                    break
                
                if total_downloaded_count >= target_count:
                    break

                # check for existing song
                safe_title = "".join(c for c in source.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                potential_file_path = str(self.download_dir / f"{safe_title}_{source.source}.mp3")

                if self.vector_store.song_exists(potential_file_path): 
                    self.logger.info(f"⏩ Skipping existing song: {source.title}")
                    continue

                if total_downloaded_count >= target_count:
                    break
                
                stats["attempted_downloads"] += 1
                
                # Download
                self.logger.info(f"⬇️ Downloading: {source.title} by {source.artist}")
                file_path = self.download_track(source)
                
                if file_path:
                    self.logger.info(f"🧬 Extracting features for similarity check...")
                    current_embedding = self.audio_processor.extract_single(file_path)
                    
                    if current_embedding is None:
                        self.logger.error(f"❌ Could not extract features, skipping...")
                        os.remove(file_path)
                        continue

                    if self.is_too_similar_to_legacy(current_embedding, source.genre):
                        self.logger.info(f"🗑️ Deleting legacy-sounding track: {source.title}")
                        if os.path.exists(file_path):
                            os.remove(file_path) # Delete to save space and keep library clean
                        stats["skipped_gtzan_like"] += 1
                        continue

                    stats["successful_downloads"] += 1
                    genre_downloaded_count += 1
                    total_downloaded_count += 1
                    
                    # Process immediately if requested
                    if process_immediately:
                        success = self._process_to_database(file_path, source, embedding=current_embedding)
                        if success:
                            stats["processed_to_db"] += 1
                            self.logger.info(f"✅ Processed to database: {source.title}")
                    
                    # Rate limiting
                    time.sleep(random.uniform(1, 3))
                else:
                    stats["failed_downloads"] += 1
        
        # Summary
        self.logger.info(f"🎉 Library expansion completed!")
        self.logger.info(f"📈 Downloaded: {stats['successful_downloads']} songs")
        self.logger.info(f"💾 Processed to DB: {stats['processed_to_db']} songs")
        self.logger.info(f"⚠️ Skipped (GTZAN-like): {stats['skipped_gtzan_like']} songs")
        self.logger.info(f"❌ Failed: {stats['failed_downloads']} songs")
        
        return stats
    
    def get_model_prediction(self, embedding):
        best_genre = "unknown"
        max_sim = -1.0
        
        new_vec = torch.tensor(embedding).flatten().unsqueeze(0)
        
        # 遍历 GTZAN 的 10 个经典流派中心点
        for genre in self.gtzan_genres:
            centroid = self.vector_store.get_gtzan_centroid(genre)
            if centroid is None: continue
            
            legacy_vec = torch.tensor(centroid).flatten().unsqueeze(0)
            sim = F.cosine_similarity(new_vec, legacy_vec).item()
            
            if sim > max_sim:
                max_sim = sim
                best_genre = genre
                
        return best_genre, max_sim
    
    def _process_to_database(self, file_path: str, source: MusicSource, embedding = None) -> bool:
        """
        Process downloaded file and add to vector database
        
        Args:
            file_path: Path to the downloaded audio file
            source: Original source metadata
            
        Returns:
            True if successfully processed and added to database
        """
        try:
            # Check if already exists in database
            if self.vector_store.song_exists(file_path):
                self.logger.info(f"🔄 Song already in database: {file_path}")
                return True
            
            # Check if already extracted features
            if embedding is None:
                self.logger.info(f"🧬 No embedding provided, extracting now...")
                embedding = self.audio_processor.extract_single(file_path)
            else:
                self.logger.info(f"⚡ Using pre-computed embedding")
                
            if embedding is None:
                self.logger.error(f"Failed to extract features from: {file_path}")
                return False
            
            model_suggested_genre, confidence = self.get_model_prediction(embedding)
            self.logger.info(f"🔍 模型预测该音频最接近: {model_suggested_genre} (相似度: {confidence:.4f})")

            final_genre = source.genre if source.genre else model_suggested_genre

            # Prepare metadata with enhanced Jamendo information
            metadata = {
                "filename": os.path.basename(file_path),
                "full_path": file_path,
                "title": source.title or "unknown",
                "artist": source.artist or "unknown",
                "genre": final_genre or "unknown",
                "model_tag": model_suggested_genre or "unknown",
                "source": source.source or "unknown",
                "duration": source.duration or 0,
                "license": source.license_info or "unknown",
                "added_by": "music_expander",
                "timestamp": int(time.time()),
                # Enhanced Jamendo metadata for text-based search (convert list to string)
                "tags": ",".join(source.tags) if source.tags else "",
                "description": source.description or "",
                "speed": source.speed or "unknown",
                "vocalinstrumental": source.vocalinstrumental or "unknown",
                "downloads_total": source.downloads_total or 0,
                "release_date": source.release_date or "",
                "album_name": source.album_name or ""
            }
            
            # Add to vector database
            success = self.vector_store.add_song(embedding, metadata)
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            return False
    
    def batch_process_existing(self, directory: Optional[str] = None) -> int:
        """
        Process existing downloaded files in the directory
        
        Args:
            directory: Directory to process (uses download_dir if None)
            source: Original source metadata
        Returns:
            Number of files successfully processed
        """
        process_dir = Path(directory) if directory else self.download_dir
        
        if not process_dir.exists():
            self.logger.warning(f"Directory does not exist: {process_dir}")
            return 0
        
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
        audio_files = [
            f for f in process_dir.rglob('*')
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]
        
        processed_count = 0
        
        for file_path in audio_files:
            # Create mock source for existing files
            mock_source = MusicSource(
                title=file_path.stem,
                artist="Unknown",
                url=str(file_path),
                source="existing_file"
            )
            
            if self._process_to_database(str(file_path), mock_source):
                processed_count += 1
        
        self.logger.info(f"🔄 Batch processed {processed_count} existing files")
        return processed_count


def main():
    """Command-line interface for music expansion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Expand music library automatically")
    parser.add_argument("--target", type=int, default=3, help="Target number of songs to download")
    parser.add_argument("--genres", nargs="+", help="Genres to focus on")
    parser.add_argument("--download-dir", default="expanded_music", help="Download directory")
    parser.add_argument("--no-process", action="store_true", help="Don't process to database immediately")
    parser.add_argument("--batch-process", action="store_true", help="Process existing files in directory")
    
    args = parser.parse_args()
    
    # Initialize expander
    expander = MusicExpander(download_dir=args.download_dir)
    
    if args.batch_process:
        # Process existing files
        count = expander.batch_process_existing()
        print(f"Processed {count} existing files")
    else:
        # Expand library
        stats = expander.expand_library(
            target_count=args.target,
            genres=args.genres,
            process_immediately=not args.no_process
        )
        
        print(f"Expansion completed: {stats}")


if __name__ == "__main__":
    main()
