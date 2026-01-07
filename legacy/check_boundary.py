import numpy as np
from scipy.spatial.distance import cdist

# 加载数据库
data = np.load("my_music_database.npz")
embs = data['embeddings']
names = data['filenames']

# 假设 Let It Happen 是你库里的第 0 首歌
song_idx = 0 
print(f"🔍 正在分析: {names[song_idx]}")

# 计算它与 GTZAN 10 个流派中心点的距离（如果你有的话）
# 或者简单点，看它在你的库里离哪首歌最近
distances = cdist(embs[song_idx].reshape(1, -1), embs, metric='euclidean')[0]
# 排除掉自己，看第二近的
nearest = np.argsort(distances)[1]

print(f"🤖 Agent 观察结论：")
print(f"这首歌虽然你认为是电子，但在我看来，它最像：{names[nearest]}")
print(f"相似度距离为: {distances[nearest]:.4f}")