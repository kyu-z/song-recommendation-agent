import numpy as np
from scipy.spatial.distance import cdist

# --- 1. 加载数据库 ---
data = np.load("my_music_database.npz")
db_embeddings = data['embeddings']
db_filenames = data['filenames']

def search_similar_songs(target_emb, top_k=3):
    """
    在数据库中搜索最相似的歌曲
    """
    # 计算目标特征与数据库中所有特征的欧式距离
    distances = cdist(target_emb.reshape(1, -1), db_embeddings, metric='euclidean')[0]
    
    # 获取距离最近的前 K 个索引
    nearest_indices = np.argsort(distances)[:top_k]
    
    results = []
    for idx in nearest_indices:
        results.append({
            "filename": db_filenames[idx],
            "distance": round(float(distances[idx]), 4)
        })
    return results

# --- 2. 模拟 Agent 对话逻辑 ---
def agent_analyze(song_name, similar_results):
    print(f"\n🤖 Music Agent 分析报告:")
    print(f"--------------------------------")
    print(f"分析曲目: {song_name}")
    print(f"最相似的库内曲目:")
    
    for i, res in enumerate(similar_results):
        print(f" {i+1}. {res['filename']} (相似度距离: {res['distance']})")
    
    # 这里我们模拟一段 AI 的解释逻辑
    top_match = similar_results[0]['filename']
    dist = similar_results[0]['distance']
    
    if dist < 0.5:
        print(f"\n💡 结论：这两首歌音色极度接近，模型认为它们属于同一流派。")
    else:
        print(f"\n💡 结论：这首歌风格比较独特，在库中没有发现完全一致的，但它在音色上最靠近 {top_match}。")

if __name__ == "__main__":
    # 假设我们拿库里的第一首歌来做测试
    test_idx = 0
    test_emb = db_embeddings[test_idx]
    test_name = db_filenames[test_idx]
    
    matches = search_similar_songs(test_emb)
    agent_analyze(test_name, matches)