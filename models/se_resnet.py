import numpy as np 
import pandas as pd 
import os
import librosa
import torch
import torch.nn as nn
from torchvision.models.resnet import BasicBlock
from torchvision.models import ResNet
    
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class SEBasicBlock(BasicBlock):
    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, r=16):
        super(SEBasicBlock, self).__init__(inplanes, planes, stride, downsample, 
                                           groups, base_width, dilation, norm_layer)

        # insert SE module
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),    # compress the entire spectrogram into a single value per channel to capture global statistics
            nn.Conv2d(planes, planes // r, kernel_size=1, bias=False), # bottleneck: consider which is most important
            nn.ReLU(inplace=True),
            nn.Conv2d(planes // r, planes, kernel_size=1, bias=False), # expand: restore original dimensions and amplify important features
            nn.Sigmoid()                #scaling: generate attention weights between 0 and 1
        )

    def forward(self, x):
        identity = x            # save input for residual connection

        # step 1
        out = self.conv1(x)     # 3x3 Conv: extract initial features (eg. existing drum kick?)
        out = self.bn1(out)     # BatchNorm: stabilize learning, standardize activations so that the data distribution is more consistent
        out = self.relu(out)    # ReLU: introduce non-linearity (like filter, filter out unwanted noise)

        out = self.conv2(out)   # 3x3 Conv: extract more complex features (eg. rock snare or jazz snare?)
        out = self.bn2(out)     


        # step 2
        # reallocate channel weights
        b, c, _, _ = out.size()
        w = self.se(out).view(b, c, 1, 1) # calculate weights
        out = out * w.expand_as(out)      # multiply back

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity # residual add
        out = self.relu(out)
        return out
    
class MusicSEResNet(nn.Module):
    def __init__(self, embedding_dim=128):
        super(MusicSEResNet, self).__init__()
        # replace original BasicBlock with SEBasicBlock
        self.model = ResNet(SEBasicBlock, [2, 2, 2, 2], num_classes=embedding_dim)

        # Adapt to your audio input
        self.model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        
    def forward(self, x):
        embedded = self.model(x)
        return nn.functional.normalize(embedded, p=2, dim=1)
    
