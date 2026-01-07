# 🎼 音乐通感私人DJ - AI Agent开发计划

## 项目概述
将现有的音乐相似性搜索系统升级为一个具备"音乐通感"的私人DJ Agent，能够理解复杂情感需求如"我今晚想在雨天看书，但不要那种太丧的，最好带点80年代复古味"。

## 现有资产分析

### 你已经拥有的核心技术：
1. **SE-ResNet V4 音频特征提取模型** (`music_model_resnet_se_v4.pth`)
2. **向量相似性搜索系统** (`music_agent.py`, `openai_music_agent.py`)
3. **Mel频谱图处理管线** (`extract_features.py`, `audio_cnn.py`)
4. **小规模音乐库** (`my_songs/` - 4首歌，`Music Similarity Search/songs/` - 6首歌)

### 技术栈升级路线图

## 阶段1: 底层基础设施重构 (第1-7天)

### 目标：从numpy文件升级到专业向量数据库

#### 需要创建的文件：
```
database/
├── __init__.py
├── vector_store.py          # ChromaDB向量数据库封装
├── music_metadata.py        # 音乐元数据结构
└── data_ingestion.py        # 批量音频文件处理

tools/
├── __init__.py
├── audio_processor.py       # 增强版音频特征提取
├── music_expander.py        # 自动扩充音乐库(爬虫/API)
└── genre_classifier.py     # 流派分类工具

config/
├── agent_config.py         # Agent配置文件
└── model_paths.py          # 模型路径配置
```

#### Day 1-2: 向量数据库迁移
- **任务**: 将`my_music_database.npz`迁移到ChromaDB
- **新文件**: `database/vector_store.py`
```python
# 需要实现的核心类
class MusicVectorStore:
    def __init__(self, collection_name="music_embeddings")
    def add_songs(self, embeddings, metadata)  
    def search_similar(self, query_embedding, n_results=5)
    def get_by_genre(self, genre)
    def update_user_feedback(self, song_id, feedback)
```

#### Day 3-4: 音乐库扩充
- **任务**: 从10首歌扩充到100+首歌
- **新文件**: `tools/music_expander.py`
- **策略**: 
  - 使用Free Music Archive API
  - 爬取Creative Commons音乐
  - 接入YouTube Audio Library

#### Day 5-6: 增强音频处理
- **任务**: 提取更丰富的音频特征
- **新文件**: `tools/audio_processor.py`
- **新特征**:
  - BPM (节拍)
  - 音调/调性
  - 动态范围
  - 频谱质心

#### Day 7: 元数据管理
- **任务**: 构建音乐元数据系统
- **新文件**: `database/music_metadata.py`
```python
# 数据结构示例
@dataclass
class MusicMetadata:
    filename: str
    title: str
    artist: str
    genre: str
    bpm: float
    key: str
    energy_level: float
    mood_tags: List[str]
    audio_features: Dict
```

---

## 阶段2: Agent核心逻辑构建 (第8-15天)

### 目标：使用LangChain构建智能决策系统

#### 需要创建的文件：
```
agent/
├── __init__.py
├── music_agent.py           # 主Agent类
├── prompt_templates.py      # 提示词模板
├── tools_registry.py       # 工具注册中心
└── memory_manager.py       # 长期记忆管理

tools/
├── music_search_tool.py     # 向量搜索工具
├── spotify_tool.py          # Spotify API工具  
├── music_analysis_tool.py   # 音乐分析工具
├── mood_interpreter.py      # 情感解析工具
└── rag_tool.py             # 音乐知识检索工具

knowledge_base/
├── music_theory.json       # 乐理知识库
├── genre_descriptions.json # 流派特征描述
└── mood_mapping.json      # 情感-音乐映射
```

#### Day 8-9: LangChain Agent框架
- **任务**: 搭建基础Agent架构
- **新文件**: `agent/music_agent.py`
```python
class MusicAgent:
    def __init__(self):
        self.llm = ChatOpenAI()  # 或Ollama
        self.tools = self._load_tools()
        self.memory = ConversationBufferMemory()
        self.agent = initialize_agent(self.tools, self.llm)
    
    def process_request(self, user_input: str) -> str:
        # 主要对话逻辑
```

#### Day 10-11: 工具系统开发
- **任务**: 开发Agent调用的工具集
- **核心工具**:
  1. `MusicSearchTool` - 向量检索
  2. `MoodInterpreterTool` - 情感解析
  3. `SpotifySearchTool` - 外部搜索
  4. `MusicAnalysisTool` - 特征分析

#### Day 12-13: RAG知识库
- **任务**: 构建音乐知识检索系统
- **新文件**: `tools/rag_tool.py`
- **知识源**:
  - 音乐理论百科
  - 流派特征描述
  - 经典专辑评论

#### Day 14-15: Spotify API集成
- **任务**: 增加外部音乐搜索能力
- **新文件**: `tools/spotify_tool.py`
- **功能**: 
  - 搜索新歌曲
  - 获取音轨特征
  - 生成试听链接

---

## 阶段3: 多模态与交互界面 (第16-20天)

### 目标：图片荐歌 + 可视化界面

#### 需要创建的文件：
```
multimodal/
├── __init__.py
├── image_analyzer.py        # 图像情感分析
├── visual_music_mapper.py   # 视觉-音乐映射
└── cross_modal_search.py    # 跨模态检索

frontend/
├── streamlit_app.py         # 主界面
├── components/
│   ├── audio_player.py     # 音频播放器
│   ├── similarity_viz.py   # 相似度可视化
│   └── chat_interface.py   # 对话界面
└── static/
    ├── style.css
    └── images/
```

#### Day 16-17: 图像情感分析
- **任务**: 实现图片到音乐的映射
- **新文件**: `multimodal/image_analyzer.py`
- **技术**: CLIP模型 + 情感分类
```python
class ImageMoodAnalyzer:
    def analyze_image(self, image_path) -> Dict:
        # 返回: {"mood": "melancholic", "energy": 0.3, "colors": ["blue", "grey"]}
    
    def map_to_music_features(self, image_mood) -> Dict:
        # 将视觉特征映射到音频特征空间
```

#### Day 18-19: Streamlit前端界面
- **任务**: 构建交互式Web界面
- **新文件**: `frontend/streamlit_app.py`
- **功能模块**:
  1. 文本输入对话框
  2. 图片上传分析
  3. 音频播放器
  4. 相似度雷达图
  5. 推荐结果展示

#### Day 20: 系统集成与测试
- **任务**: 端到端系统测试
- **测试场景**:
  - 复杂情感查询: "雨夜读书，不要太丧，要有80年代复古味"
  - 图片荐歌: 上传落日照片
  - 外部搜索: 本地库不满足时的Spotify搜索

---

## 核心Pipeline架构

### Agent决策流程:
```
用户输入 → 意图解析 → 工具选择 → 执行搜索 → 结果整合 → 自然语言回复
    ↓
[情感关键词提取] → [向量检索] → [结果筛选] → [外部补充] → [个性化排序]
```

### 多模态处理流程:
```
图片输入 → 视觉特征提取 → 情感映射 → 音乐特征转换 → 向量检索 → 结果返回
```

---

## 技术栈说明

### 必需安装的包:
```bash
# Agent框架
pip install langchain langchain-openai

# 向量数据库  
pip install chromadb

# 多模态
pip install transformers clip-by-openai pillow

# API集成
pip install spotipy requests

# 前端
pip install streamlit plotly

# 音频处理 (你已有)
# librosa torch numpy scipy
```

### 开发顺序建议:

1. **Week 1 (Day 1-7)**: 专注底层基础设施，别急着做Agent
2. **Week 2 (Day 8-14)**: 核心Agent逻辑，这是最复杂的部分
3. **Week 3 (Day 15-20)**: 多模态和界面，让项目变得酷炫

### 简历亮点包装:

完成后，你的项目将包含以下技术亮点:
- ✅ **RAG (检索增强生成)**: 音乐知识库检索
- ✅ **Tool Use/Function Calling**: 多工具协作Agent  
- ✅ **Multi-Modal**: 图片到音乐的跨模态检索
- ✅ **Vector Database**: ChromaDB高效语义检索
- ✅ **Long-term Memory**: 用户偏好学习系统
- ✅ **API Integration**: Spotify外部数据源
- ✅ **Deep Learning**: SE-ResNet音频特征提取

### 项目展示建议:

1. **Demo视频录制**: 展示从"雨夜读书"到具体歌曲推荐的完整流程
2. **技术博客**: 详细解释跨模态检索的实现原理  
3. **GitHub README**: 突出AI Agent + 多模态的技术难点

---

这个计划让你在20天内从现有的简单相似性搜索，升级为一个具备RAG、工具调用、多模态能力的完整AI Agent系统。每个阶段都有清晰的目标和可交付成果，确保你能在求职时展示完整的现代AI应用开发能力。
