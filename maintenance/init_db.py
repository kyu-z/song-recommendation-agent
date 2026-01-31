import os
from pathlib import Path
from tools.music_expander import MusicExpander # This should work if run from root

def run_init():
    # 1. Initialize expander (which connects to your ChromaDB)
    expander = MusicExpander()
    
    # 2. Define where your GTZAN files are
    # Make sure this points to the folder containing 'pop', 'rock', etc.
    gtzan_base_path = "/Users/kyzheng/Downloads/datasets/gtzan" 
    
    # 3. Import 
    for genre in expander.gtzan_genres:
        genre_path = Path(gtzan_base_path) / genre
        if not genre_path.exists():
            print(f"Skipping {genre}, path not found.")
            continue
            
        print(f"Processing {genre}...")
        files = list(genre_path.glob("*.wav"))
        
        for f in files:
            # Check if already exists to avoid duplicates
            if expander.vector_store.song_exists(str(f)):
                continue
                
            try:
                embedding = expander.audio_processor.extract_single(str(f))
                metadata = {
                    "source": "gtzan",
                    "genre": genre,
                    "title": f.name,
                    "full_path": str(f)
                }
                expander.vector_store.add_song(embedding, metadata)
                
            except Exception as e:
                print(f"⚠️ 跳过损坏文件 {f.name}: 格式无法识别")
                continue
    print("Done! Your 'Acoustic Baseline' is now ready.")

if __name__ == "__main__":
    run_init()