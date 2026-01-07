import torch
import torch.nn.functional as F

#load embeddings
data = torch.load("music_index.pt")
embeddings = data["embeddings"]      # (B, 128)
filenames = data["filenames"]

def search(query_idx, top_k=5):
    query = embeddings[query_idx]          # (128,)
    query = query.unsqueeze(0)              # (1, 128)

    # cosine similarity
    sims = F.cosine_similarity(query, embeddings)  # (B,)
    sims[query_idx] = -1.0  # 排除自己（cosine 最小值）

    values, indices = torch.topk(sims, top_k)

    return indices, values

# test
query_idx = 0

print(f"Query song: {filenames[query_idx]}\n")

idxs, scores = search(query_idx=query_idx)

print("Most similar songs:")
for idx, score in zip(idxs, scores):
    print(f"{filenames[idx]} | score={score:.4f}")