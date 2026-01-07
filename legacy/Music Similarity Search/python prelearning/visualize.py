import torch
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

# load embeddings
data = torch.load("music_index.pt")         # return dict
embeddings = data["embeddings"].numpy()
filenames = data["filenames"]

#TSNE，t-Distributed Stochastic Neighbor Embedding，降维到2D
tsne = TSNE(n_components=2, perplexity=2, random_state=42)
X_2d = tsne.fit_transform(embeddings)

# Plot
plt.figure(figsize=(8,6))
plt.scatter(X_2d[:, 0], X_2d[:, 1])

# Add labels
for i, name in enumerate(filenames):
    plt.text(X_2d[i, 0]+0.5, X_2d[i, 1]+0.5, name, fontsize=9)

plt.title("Song Embedding Space")
plt.xlabel("TSNE-1")
plt.ylabel("TSNE-2")
plt.show()
