"""
Music Expander Demo Script

This script demonstrates the music_expander functionality without requiring API keys.
It creates mock music files for testing purposes.

Usage: python demo_expander.py
"""

import os
import sys
import shutil
import random
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.audio_processor import AudioFeatureExtractor
from database.vector_store import MusicVectorStore


def create_mock_audio_file(filepath: str, duration: float = 3.0):
    """
    Create a mock audio file with generated data
    
    Args:
        filepath: Output file path
        duration: Duration in seconds
    """
    try:
        import librosa
        import soundfile as sf
        
        # Generate simple sine wave audio
        sr = 22050
        samples = int(duration * sr)
        t = np.linspace(0, duration, samples)
        
        # Create a simple melody (multiple sine waves)
        frequencies = [440, 523, 659, 784]  # A4, C5, E5, G5
        audio = np.zeros(samples)
        
        for freq in frequencies:
            audio += 0.25 * np.sin(2 * np.pi * freq * t)
        
        # Add some noise for realism
        noise = 0.05 * np.random.randn(samples)
        audio += noise
        
        # Normalize
        audio = audio / np.max(np.abs(audio))
        
        # Save as wav file
        sf.write(filepath, audio, sr)
        print(f"✅ Created mock audio: {filepath}")
        
    except ImportError:
        print("⚠️ Warning: librosa/soundfile not available, creating placeholder file")
        # Create a placeholder file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            f.write("Mock audio file for testing")


def create_demo_music_library():
    """Create a demo music library with diverse genres"""
    
    demo_songs = [
        ("Ambient_Ocean_Waves", "ambient", "Natural Sounds Artist"),
        ("Electronic_Synthwave_Night", "synthwave", "Retro Producer"),
        ("Indie_Folk_Morning", "indie", "Coffee Shop Band"),
        ("Lo_Fi_Study_Beats", "lo-fi", "Chill Hop Collective"),
        ("Instrumental_Piano_Rain", "instrumental", "Solo Pianist"),
        ("Cinematic_Epic_Journey", "cinematic", "Film Score Composer"),
        ("Downtempo_City_Lights", "downtempo", "Urban Sound Designer"),
        ("Post_Rock_Sunrise", "post-rock", "Atmospheric Rock Band"),
    ]
    
    demo_dir = Path("demo_expanded_music")
    demo_dir.mkdir(exist_ok=True)
    
    created_files = []
    
    for title, genre, artist in demo_songs:
        filename = f"{title}.wav"
        filepath = demo_dir / filename
        
        # Create mock audio file
        create_mock_audio_file(str(filepath))
        
        created_files.append({
            "filepath": str(filepath),
            "title": title.replace("_", " "),
            "artist": artist,
            "genre": genre
        })
    
    return created_files


def demo_music_expander():
    """Demonstrate the music expander functionality"""
    
    print("🎵 Music Expander Demo")
    print("=" * 50)
    
    # Create demo music library
    print("\n1. Creating demo music library...")
    demo_files = create_demo_music_library()
    
    # Initialize components
    print("\n2. Initializing audio processor and vector store...")
    vector_store = MusicVectorStore(collection_name="demo_music")
    audio_processor = AudioFeatureExtractor()
    
    # Get initial stats
    initial_stats = vector_store.get_stats()
    print(f"   Initial database size: {initial_stats['total_songs']} songs")
    
    # Process demo files
    print("\n3. Processing demo music files...")
    processed_count = 0
    
    for file_info in demo_files:
        filepath = file_info["filepath"]
        
        try:
            # Check if already exists
            if vector_store.song_exists(filepath):
                print(f"   ⚠️ Already exists: {file_info['title']}")
                continue
            
            # Extract features (this will create a mock embedding if actual audio processing fails)
            print(f"   🔄 Processing: {file_info['title']}")
            embedding = audio_processor.extract_single(filepath)
            
            if embedding is None:
                # Create mock embedding for demo
                print(f"   📝 Creating mock embedding for: {file_info['title']}")
                embedding = np.random.randn(128).astype(np.float32)
            
            # Add to database
            metadata = {
                "filename": os.path.basename(filepath),
                "full_path": filepath,
                "title": file_info["title"],
                "artist": file_info["artist"],
                "genre": file_info["genre"],
                "source": "demo_expander",
                "license": "Demo/Test",
                "added_by": "demo_script"
            }
            
            success = vector_store.add_song(embedding, metadata)
            if success:
                processed_count += 1
                print(f"   ✅ Added to database: {file_info['title']}")
            else:
                print(f"   ❌ Failed to add: {file_info['title']}")
                
        except Exception as e:
            print(f"   ❌ Error processing {file_info['title']}: {e}")
    
    # Final stats
    print(f"\n4. Results:")
    final_stats = vector_store.get_stats()
    print(f"   📊 Final database size: {final_stats['total_songs']} songs")
    print(f"   📈 Added: {processed_count} new songs")
    
    # Test similarity search
    if final_stats['total_songs'] > 1:
        print(f"\n5. Testing similarity search...")
        
        try:
            # Create a test embedding for search
            test_embedding = np.random.randn(128).astype(np.float32)
            print(f"   🔍 Searching with random test embedding...")
            
            results = vector_store.search_similar(test_embedding, n_results=3, include_self=False)
            
            print(f"   � Found {len(results)} similar songs:")
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Unknown Title')
                genre = result.get('genre', 'Unknown Genre')
                distance = result.get('distance', 0.0)
                print(f"      {i}. {title} ({genre}) - Distance: {distance:.4f}")
                
        except Exception as e:
            print(f"   ⚠️ Similarity search test failed: {e}")
            # Try alternative approach
            print(f"   🔄 Trying alternative search method...")
            try:
                # Just show that we have songs in the database
                all_songs = vector_store.get_all_songs()
                print(f"   📋 Database contains {len(all_songs)} songs:")
                for i, song in enumerate(all_songs[:3], 1):
                    title = song['metadata'].get('title', 'Unknown')
                    genre = song['metadata'].get('genre', 'Unknown')
                    print(f"      {i}. {title} ({genre})")
            except Exception as e2:
                print(f"   ❌ Could not list songs: {e2}")
    
    print(f"\n✅ Demo completed!")
    print(f"Demo files created in: {Path('demo_expanded_music').absolute()}")
    
    return {
        "demo_files_created": len(demo_files),
        "songs_processed": processed_count,
        "final_db_size": final_stats['total_songs']
    }


def cleanup_demo():
    """Clean up demo files"""
    demo_dir = Path("demo_expanded_music")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
        print("🧹 Cleaned up demo files")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Music Expander Demo")
    parser.add_argument("--cleanup", action="store_true", help="Clean up demo files")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio file generation")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_demo()
    else:
        try:
            results = demo_music_expander()
            print(f"\n📊 Demo Statistics:")
            for key, value in results.items():
                print(f"   {key}: {value}")
                
        except KeyboardInterrupt:
            print("\n⛔ Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
