import torch
import torch.nn as nn
import torch.nn.functional as F

class AudioCNNEncoder(nn.Module):
    def __init__(self, embedding_dim=128):
        super().__init__()

        # 输入: (B, 1, 64, T)
        self.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=16,
            kernel_size=3,
            stride=1,
            padding=1
        )

        self.conv2 = nn.Conv2d(
            in_channels=16,
            out_channels=32,
            kernel_size=3,
            stride=1,
            padding=1
        )

        self.conv3 = nn.Conv2d(
            in_channels=32,
            out_channels=64,
            kernel_size=3,
            stride=1,
            padding=1
        )

        # 把任意 (H, W) -> (1, 1)
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))

        # 最终映射到 128-d embedding
        self.fc = nn.Linear(64, embedding_dim)

    def forward(self, x):
        #print("Input:", x.shape)

        # (B, 1, 64, T)
        x = x.unsqueeze(1)
        #print("After unsqueeze:", x.shape)

        x = F.relu(self.conv1(x))           #F.relu: 非线性变换，把负值置 0，正值保持不变
        #print("After conv1:", x.shape)

        x = F.relu(self.conv2(x))
        #print("After conv2:", x.shape)

        x = F.relu(self.conv3(x))
        #print("After conv3:", x.shape)

        x = self.global_pool(x)
        #print("After global pooling:", x.shape)

        x = x.squeeze(-1).squeeze(-1)
        #print("After squeeze:", x.shape)

        x = self.fc(x)
        #print("Output embedding:", x.shape)

        return x
