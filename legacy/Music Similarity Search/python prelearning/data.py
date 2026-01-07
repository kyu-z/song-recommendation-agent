import librosa
import librosa.display
import matplotlib.pyplot as plt
import torch
import numpy as np
import os
import glob

def audio_to_mel(path, sr=22050):
    y, sr = librosa.load(path, sr=sr, duration=15.0)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=64)
    S_dB = librosa.power_to_db(S, ref=np.max)
    return torch.tensor(S_dB, dtype=torch.float32)

def load_all_mels(audio_dir):
    mel_list = []
    filenames = []

    audio_files = glob.glob(
        os.path.join(audio_dir, "**", "*.wav"),
        recursive=True
    )
    print(f"Found {len(audio_files)} audio files")

    for path in sorted(audio_files):
        try:
            mel = audio_to_mel(path)
            mel_list.append(mel)
            filenames.append(path)
        except Exception as e:
            print(f"Failed to process {path}: {e}")

    if len(mel_list) == 0:
        raise RuntimeError("No valid audio files found in the specified directory.")

    # 合并成 batch tensor
    mel_batch = torch.stack([m for m in mel_list])  # shape = (B, 64, T)
    return mel_batch, filenames

# test code
if __name__ == "__main__":
    mel_batch, filenames = load_all_mels()
    print(mel_batch.shape)
    print(len(filenames))