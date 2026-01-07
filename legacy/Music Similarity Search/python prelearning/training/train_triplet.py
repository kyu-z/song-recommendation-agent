import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from models.audio_cnn import AudioCNNEncoder
from training.triplet_dataset import TripletDataset
from data import load_all_mels

# load data
mel_batch, filenames = load_all_mels("/Users/kyzheng/Downloads/datasets/gtzan")   # (B, 64, T)
dataset = TripletDataset(mel_batch, filenames)
loader = DataLoader(dataset, batch_size=2, shuffle=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# load model
model = AudioCNNEncoder(embedding_dim=128).to(device)
criterion = nn.TripletMarginLoss(margin=1.0)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

# load precomputed embeddings
#data = torch.load("music_index.pt")
#embeddings_all = data["embeddings"]  # (B, 128)

# train
model.train()

for epoch in range(5):          # epoch：完整遍历一次训练数据的次数，这里训练 5 次。

    for anchor, positive, negative in loader:
        optimizer.zero_grad()  # PyTorch 会累加梯度，每次更新前必须先清零，否则梯度会叠加。

        # anchor embedding
        emb_a = model(anchor)
        emb_p = model(positive)
        emb_n = model(negative)

        # calculate triplet loss
        loss = criterion(emb_a, emb_p, emb_n)
        loss.backward()
        optimizer.step()

    #print(f"Epoch {epoch} | Loss: {total_loss:.4f}")

print(f"Epoch {epoch} | Loss: {loss.item():.4f}")