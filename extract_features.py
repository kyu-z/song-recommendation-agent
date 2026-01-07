import torch
import librosa
import numpy as np
import os
from audio_cnn import MusicSEResNet # 确保你的模型类定义在 audio_cnn.py 里，或者直接贴在这里

# --- 配置 ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
MODEL_PATH = "music_model_resnet_se_v4.pth"
SONGS_DIR = "my_songs"
SAVE_PATH = "my_music_database.npz"

# --- 1. 加载模型 ---
model = MusicSEResNet(embedding_dim=128).to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval()

def get_embedding(path):
    # 统一使用 15s 时长，与训练保持一致
    y, _ = librosa.load(path, sr=22050, offset=15.0, duration=15.0)
    mel = librosa.feature.melspectrogram(y=y, sr=22050, n_mels=64)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-6)
    
    # 确保维度是 [1, 1, 64, 646]
    input_tensor = torch.FloatTensor(mel_db).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model(input_tensor)
    return embedding.cpu().numpy().flatten()

# --- 2. 批量处理 ---
embeddings = []
filenames = []

print("🚀 开始扫描文件夹并提取特征...")
for file in os.listdir(SONGS_DIR):
    if file.lower().endswith(('.mp3', '.wav', '.m4a')):
        print(f"正在处理: {file}")
        path = os.path.join(SONGS_DIR, file)
        try:
            emb = get_embedding(path)
            embeddings.append(emb)
            filenames.append(file)
        except Exception as e:
            print(f"❌ 错误: {file} 无法处理. {e}")

# --- 3. 保存数据库 ---
if len(embeddings) > 0:
    np.savez(SAVE_PATH, embeddings=embeddings, filenames=filenames)
    print(f"\n✨ 大功告成！共处理 {len(embeddings)} 首歌，特征库已更新: {SAVE_PATH}")
else:
    print("\n⚠️ 警告：没有找到任何音频文件，特征库未更新。请检查 my_songs 文件夹。")