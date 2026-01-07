import torch
from models.audio_cnn import AudioCNNEncoder
from data import load_all_mels

DATA_ROOT = "/Users/kyzheng/Downloads/datasets/gtzan"
#load mel
mel_batch, filenames = load_all_mels(DATA_ROOT)

#load model
model = AudioCNNEncoder(embedding_dim=128)      #AudioCNNEncoder：convert mel spectrogram to embedding
model.eval()        # just extract features, no training

with torch.no_grad():                       # since no training, we dont need gradients
    embeddings = model(mel_batch)           # (batch_size, 128)

print("Extracted embeddings shape:", embeddings.shape)

#save data
torch.save(
    {
        "embeddings": embeddings,
        "filenames": filenames
    },
    "music_index.pt"
    
)