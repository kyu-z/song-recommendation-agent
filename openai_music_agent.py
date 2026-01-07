import numpy as np
import os
from scipy.spatial.distance import cdist
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. 初始化配置 ---
client = OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama"  # 本地模型不需要真 key，填这个占位即可
)

data = np.load("my_music_database.npz")
db_embs = data['embeddings']
db_names = data['filenames']

def get_musical_analysis(target_song, match_song, distance):
    system_prompt = "你是一个精通乐坛的资深乐评人，你必须且只能使用【中文】进行回答。"
    
    user_prompt = f"""
    目标歌曲：'{target_song}'
    相似歌曲：'{match_song}'
    欧氏距离：{distance}

    任务：
    1. 分析为什么模型会觉得它们相似（从吉他音色、频率分布、混响等物理特征入手）。
    2. 用幽默且毒舌的语气吐槽这种“跨界撞脸”。
    3. 请务必使用【中文】回答，严禁输出英文。
    4. 200字以内。
    """
    response = client.chat.completions.create(
        model="llama3",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}]
    )
    return response.choices[0].message.content

# --- 2. 运行 Agent ---
test_idx = 0 # 对应 ASAYAKE
target_name = db_names[test_idx]
target_emb = db_embs[test_idx]

# 计算距离并找第2近的（排除自己）
distances = cdist(target_emb.reshape(1, -1), db_embs, metric='euclidean')[0]
nearest_idx = np.argsort(distances)[1] 
match_name = db_names[nearest_idx]
match_dist = round(float(distances[nearest_idx]), 4)

print(f"🤖 Agent 正在深思熟虑中...\n")
analysis = get_musical_analysis(target_name, match_name, match_dist)

print(f"【AI 乐评人分析报告】")
print(f"目标：{target_name}  <-->  相似：{match_name} (距离: {match_dist})")
print("-" * 50)
print(analysis)