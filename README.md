# Music-Agent-RAG  
## Neural Music Similarity & AI Agent

A personal project exploring **Metric Learning** and **Vector Databases** in the context of **music recommendation**.  
This system uses a **custom-trained SE-ResNet model** to transform audio signals into **high-dimensional embeddings** for semantic search and explanation.

---

## Project Overview

The goal of this project is to build a **music-aware agent** that doesn’t rely on tags or metadata, but instead understands the actual acoustic **“vibe”** of a track.

By extracting features from **Mel-spectrograms**, the system retrieves musically similar tracks based on **timbre**, **rhythm**, and **spectral characteristics**.

---

## Core Technical Implementation

### Feature Extraction — SE-ResNet

- **Architecture**  
  ResNet-18 backbone enhanced with **Squeeze-and-Excitation (SE) blocks** to introduce channel-wise attention and improve timbral sensitivity.

- **Model Training**  
  Trained on the **GTZAN dataset (v4 iteration)** to produce **128-dimensional embedding vectors** optimized for similarity learning.

- **Signal Processing**  
  Raw audio is converted into **Mel-spectrograms** using Librosa:
  - Sample rate: `22050 Hz`
  - Mel bands: `64`

---

### Vector Search — ChromaDB

- Replaced traditional flat-file storage with **ChromaDB** for scalable and efficient vector indexing.
- Applied **L2 normalization** to all embeddings to ensure consistent **Euclidean distance** computations in vector space.
- Enables fast **nearest-neighbor search** for musically similar tracks.

---

### AI Agent — LangChain (RAG)

- Implemented a **Retrieval-Augmented Generation (RAG)** pipeline using **LangChain**.
- The agent:
  1. Retrieves acoustically similar tracks from the vector database
  2. Uses an LLM to **explain *why*** the tracks are stylistically related
- Bridges low-level audio embeddings with **human-readable musical reasoning**.

---

##  Tech Stack

- **Deep Learning**: PyTorch  
- **Audio Analysis**: Librosa, NumPy  
- **Vector Database**: ChromaDB  
- **AI Agent Framework**: LangChain