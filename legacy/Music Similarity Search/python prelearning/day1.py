import torch
import torch.nn as nn

# fake data
x = torch.randn(32, 10)   # 32 samples, 10 features
y = torch.randint(0, 2, (32,))  # binary labels

model = nn.Linear(10, 2)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

# forward
out = model(x)
loss = criterion(out, y)

# backward
optimizer.zero_grad()
loss.backward()
optimizer.step()

print(loss.item())