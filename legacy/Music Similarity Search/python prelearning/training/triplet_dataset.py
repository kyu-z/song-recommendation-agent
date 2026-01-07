import torch
from torch.utils.data import Dataset
import random
import os

class TripletDataset(Dataset):
    def __init__(self, mel_batch, filenames):
        """
        mel_batch: Tensor (B, 64, T)
        """
        self.mels = mel_batch
        self.filenames = filenames
        self.B = mel_batch.shape[0]

        # get genres from the file path
        self.genres = [
            os.path.basename(os.path.dirname(p))
            for p in filenames
        ]

        # genres to index mapping
        self.genre_to_indices = {}
        for i, genre in enumerate(set(self.genres)):
            self.genre_to_indices.setdefault(genre, []).append(i)

    def __len__(self):
        return self.B

    def __getitem__(self, idx):
        anchor = self.mels[idx]
        anchor_genre = self.genres[idx]

        # positive: 同 genre，不同歌曲
        pos_idx = idx
        while pos_idx == idx:
            pos_idx = random.choice(self.genre_to_indices[anchor_genre])
        positive = self.mels[pos_idx]

        # negative: 不同 genre
        neg_genre = anchor_genre
        while neg_genre == anchor_genre:
            neg_genre = random.choice(list(self.genre_to_indices.keys()))
        neg_idx = random.choice(self.genre_to_indices[neg_genre])
        negative = self.mels[neg_idx]

        return anchor, positive, negative