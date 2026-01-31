import os
from database.vector_store import MusicVectorStore

def inspect_database():
    vs = MusicVectorStore()
    
    # 1. 统计基本信息
    count = vs.collection.count()
    print(f"\n{'='*40}")
    print(f"📊 数据库概览")
    print(f"{'='*40}")
    print(f"总计记录数: {count}")
    
    if count == 0:
        print("⚠️ 数据库当前为空，请运行 init_db.py 导入基准数据。")
        return

    # 2. 按流派和来源查看分布
    all_data = vs.collection.get(include=["metadatas"])
    metas = all_data['metadatas']
    
    sources = {}
    genres = {}
    
    for m in metas:
        src = m.get('source', 'unknown')
        gnr = m.get('genre', 'unknown')
        sources[src] = sources.get(src, 0) + 1
        genres[gnr] = genres.get(gnr, 0) + 1
        
    print(f"\n📍 数据来源分布:")
    for src, num in sources.items():
        print(f" - {src}: {num}")

    """   
    print(f"\n🎵 流派分布 (Top 10):")
    sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
    for gnr, num in sorted_genres[:10]:
        print(f" - {gnr}: {num}")
    """

    print(f"\n✨ 检查最新扩容的现代音乐 (非 GTZAN):")
    # 使用 $ne (not equal) 过滤掉 gtzan 数据
    modern_music = vs.collection.get(
        where={"source": {"$ne": "gtzan"}}, 
        limit=10, # 看多一点，确保涵盖 synthwave 等
        include=["metadatas"]
    )
    
    if not modern_music['ids']:
        print(" 🔍 未发现现代扩容数据。")
    else:
        for i in range(len(modern_music['ids'])):
            m = modern_music['metadatas'][i]
            print(f" [{i+1}] Title: {m.get('title')}")
            print(f"     Genre (Target): {m.get('genre')}")
            print(f"     Model Predicted: {m.get('model_tag')}")
            print(f"     Similarity Check: {m.get('source')}")
    print(f"{'='*40}\n")

if __name__ == "__main__":
    inspect_database()