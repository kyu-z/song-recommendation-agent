import torch
import torch.nn as nn
import torch.nn.functional as F
from data import load_all_mels
from models.audio_cnn import AudioCNNEncoder

mel_batch = load_all_mels("songs/")
print("Mel batch shape:", mel_batch.shape)

model = AudioCNNEncoder(embedding_dim=128)
embeddings = model(mel_batch)
print("Final embeddings shape:", embeddings.shape)