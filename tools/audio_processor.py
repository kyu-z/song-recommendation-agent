"""
Audio Feature Extractor - Object-oriented refactor of extract_features.py
Directly integrates with ChromaDB vector database
"""
import torch
import librosa
import numpy as np
import os
from typing import List, Dict, Optional, Union
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.se_resnet import MusicSEResNet
from database.vector_store import MusicVectorStore

class AudioFeatureExtractor:
    """
    Professional audio feature extractor using SE-ResNet V4 model
    Designed for AI Agent integration and batch processing
    """
    
    def __init__(self, 
                 model_path: str = "music_model_resnet_se_v4.pth",
                 device: str = 'auto',
                 sample_rate: int = 22050,
                 n_mels: int = 64,
                 duration: float = 15.0,
                 offset: float = 15.0):
        """
        Initialize the feature extractor
        
        Args:
            model_path: Path to the SE-ResNet model file
            device: Device to use ('cuda', 'cpu', or 'auto')
            sample_rate: Audio sample rate
            n_mels: Number of mel bands
            duration: Duration of audio to process (seconds)
            offset: Start offset for audio processing (seconds)
        """
        # Set device
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Audio processing parameters
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.duration = duration
        self.offset = offset
        
        # Load model
        self.model_path = model_path
        self._load_model()
        
        print(f"🎵 AudioFeatureExtractor initialized")
        print(f"   Device: {self.device}")
        print(f"   Model: {model_path}")
        print(f"   Audio params: {sample_rate}Hz, {n_mels} mels, {duration}s duration")
    
    def _load_model(self):
        """Load the SE-ResNet model"""
        try:
            self.model = MusicSEResNet(embedding_dim=128).to(self.device)
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.eval()
            print(f"✅ Model loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {str(e)}")
    
    def extract_single(self, audio_path: str) -> np.ndarray:
        """
        Extract feature vector from a single audio file
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            np.ndarray: 128-dimensional feature vector
        """
        try:
            # Load audio with specified parameters
            y, _ = librosa.load(audio_path, 
                              sr=self.sample_rate, 
                              offset=self.offset, 
                              duration=self.duration)
            
            # Extract mel spectrogram
            mel = librosa.feature.melspectrogram(y=y, 
                                               sr=self.sample_rate, 
                                               n_mels=self.n_mels)
            mel_db = librosa.power_to_db(mel, ref=np.max)
            
            # Normalize mel spectrogram
            mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-6)
            
            # Prepare tensor for model input [1, 1, 64, T]
            input_tensor = torch.FloatTensor(mel_db).unsqueeze(0).unsqueeze(0).to(self.device)
            
            # Extract features using the model
            with torch.no_grad():
                embedding = self.model(input_tensor)
            
            return embedding.cpu().numpy().flatten()
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract features from {audio_path}: {str(e)}")
    
    def extract_with_metadata(self, audio_path: str, source: str = "my_library") -> Dict:
        """
        Extract features along with metadata
        
        Args:
            audio_path: Path to the audio file
            source: Data source identifier (default: "my_library")
            
        Returns:
            Dict: Contains embedding and metadata
        """
        # Extract features
        embedding = self.extract_single(audio_path)
        
        # Extract metadata
        basename = os.path.basename(audio_path)
        name_without_ext = os.path.splitext(basename)[0]
        file_size = os.path.getsize(audio_path)
        file_ext = os.path.splitext(basename)[1].lower()
        
        # Get actual audio duration for metadata
        try:
            actual_duration = librosa.get_duration(path=audio_path)
        except:
            actual_duration = None
        
        metadata = {
            "filename": basename,
            "full_path": os.path.abspath(audio_path),
            "title": name_without_ext,
            "file_size": file_size,
            "format": file_ext,
            "sample_rate": self.sample_rate,
            "processed_duration": self.duration,
            "actual_duration": actual_duration,
            "source": source  # 🔧 添加source字段
        }
        
        return {
            "embedding": embedding,
            "metadata": metadata
        }
    
    def extract_and_save(self, audio_path: str, 
                        vector_store: Optional[MusicVectorStore] = None,
                        source: str = "my_library") -> bool:
        """
        Extract features and directly save to ChromaDB
        
        Args:
            audio_path: Path to the audio file
            vector_store: MusicVectorStore instance (creates new if None)
            source: Data source identifier (default: "my_library")
            
        Returns:
            bool: Success status
        """
        try:
            # Extract features with metadata
            result = self.extract_with_metadata(audio_path, source=source)
            
            # Use provided vector store or create new one
            if vector_store is None:
                vector_store = MusicVectorStore()
            
            # Check if song already exists (using full path to avoid filename conflicts)
            full_path = result['metadata']['full_path']
            if vector_store.song_exists(full_path):
                print(f"⚠️  Skipped (already exists): {result['metadata']['filename']}")
                return True  # Return True as it's not an error, just already exists
            
            # Save to ChromaDB
            success = vector_store.add_song(result["embedding"], result["metadata"])
            
            if success:
                print(f"✅ Saved: {result['metadata']['filename']} (source: {source})")
            else:
                print(f"❌ Failed to save: {result['metadata']['filename']}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error processing {audio_path}: {str(e)}")
            return False
    
    def extract_batch(self, audio_dir: str, 
                     supported_formats: tuple = ('.mp3', '.wav', '.m4a', '.flac'),
                     save_to_db: bool = True,
                     source: str = "my_library") -> List[Dict]:
        """
        Extract features from all audio files in a directory
        
        Args:
            audio_dir: Directory containing audio files
            supported_formats: Tuple of supported audio file extensions
            save_to_db: Whether to save to ChromaDB automatically
            source: Data source identifier (default: "my_library")
            
        Returns:
            List[Dict]: List of extraction results
        """
        print(f"🚀 Starting batch extraction from: {audio_dir}")
        print(f"📋 Source identifier: {source}")
        
        # Find all audio files
        audio_files = []
        for file in os.listdir(audio_dir):
            if file.lower().endswith(supported_formats):
                audio_files.append(file)
        
        if not audio_files:
            print(f"⚠️  No audio files found in {audio_dir}")
            print(f"   Supported formats: {supported_formats}")
            return []
        
        print(f"📁 Found {len(audio_files)} audio files")
        
        # Initialize vector store if saving to database
        vector_store = MusicVectorStore() if save_to_db else None
        
        results = []
        successful = 0
        failed = 0
        
        # Process each file
        for i, file in enumerate(audio_files, 1):
            file_path = os.path.join(audio_dir, file)
            print(f"🎵 [{i}/{len(audio_files)}] Processing: {file}")
            
            try:
                if save_to_db:
                    # Extract and save to database with source
                    success = self.extract_and_save(file_path, vector_store, source=source)
                    if success:
                        successful += 1
                        # Still get the result for return value
                        result = self.extract_with_metadata(file_path, source=source)
                        results.append(result)
                    else:
                        failed += 1
                else:
                    # Just extract features
                    result = self.extract_with_metadata(file_path, source=source)
                    results.append(result)
                    successful += 1
                    print(f"✅ Extracted: {file} (source: {source})")
                    
            except Exception as e:
                print(f"❌ Failed: {file} - {str(e)}")
                failed += 1
        
        # Summary
        print(f"\n🎉 Batch extraction completed!")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📋 Source: {source}")
        if save_to_db:
            print(f"   💾 Saved to ChromaDB: {successful}")
        
        return results


# Backward compatibility function for old script usage
def main():
    """
    Backward compatibility main function
    Replicates the behavior of the original extract_features.py
    """
    extractor = AudioFeatureExtractor()
    results = extractor.extract_batch("my_songs", save_to_db=True)
    
    if results:
        print(f"\n🎯 Legacy compatibility: Processed {len(results)} songs")
        print("   Note: Data saved to ChromaDB instead of numpy file")
    else:
        print("\n⚠️  No audio files processed. Please check the my_songs folder.")


# Test and demo functionality
if __name__ == "__main__":
    # For backward compatibility, run the main function
    main()
    
    # Demonstrate new object-oriented usage
    print("\n" + "="*50)
    print("🧪 DEMO: New Object-Oriented Usage")
    print("="*50)
    
    try:
        # Create extractor instance
        extractor = AudioFeatureExtractor()
        
        # Demo single file extraction (if files exist)
        song_dir = "my_songs"
        if os.path.exists(song_dir):
            files = [f for f in os.listdir(song_dir) if f.lower().endswith(('.mp3', '.wav', '.m4a'))]
            if files:
                demo_file = os.path.join(song_dir, files[0])
                print(f"\n🎵 Demo single extraction: {files[0]}")
                
                # Extract single file
                embedding = extractor.extract_single(demo_file)
                print(f"   Embedding shape: {embedding.shape}")
                print(f"   Embedding type: {type(embedding)}")
                
                # Extract with metadata
                result = extractor.extract_with_metadata(demo_file, source="demo")
                print(f"   Metadata keys: {list(result['metadata'].keys())}")
        
        print(f"\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
