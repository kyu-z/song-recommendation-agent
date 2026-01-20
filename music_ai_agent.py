import os
import base64
import re
import random
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database.vector_store import MusicVectorStore
from agent.models import ModelManager
from agent.tools import MusicSearchTool

load_dotenv(".env.local")

class MusicAgent:
    """
    Music AI Agent with Tool calling capabilities
    
    Refactored from MusicAIExplorer to support:
    - Multi-model switching (GPT-4o-mini / Ollama)
    - LangChain Tool integration
    - LCEL chain composition
    """
    
    def __init__(self, use_local_model: bool = False):
        """
        Initialize Music Agent
        
        Args:
            use_local_model: If True, use local Ollama models; otherwise use OpenAI
        """
        print(f"🎵 Initializing Music Agent (Local: {use_local_model})")
        
        # Core components
        self.model_manager = ModelManager(use_local_model)
        self.vector_store = MusicVectorStore()
        self.music_search_tool = MusicSearchTool(self.vector_store)
        
        # Build main processing chain
        self._build_main_chain()
        
        print("✅ Music Agent initialized successfully")
    
    def _build_main_chain(self):
        """Build the main processing chain using LCEL"""
        # Define processing stages as RunnableLambda functions
        self.perception_stage = RunnableLambda(self._perception_stage)
        self.retrieval_stage = RunnableLambda(self._retrieval_stage)
        self.decision_stage = RunnableLambda(self._decision_stage)
        self.generation_stage = RunnableLambda(self._generation_stage)
        
        # Compose main chain
        self.main_chain = (
            self.perception_stage |
            self.retrieval_stage |
            self.decision_stage |
            self.generation_stage
        )
    
    def _perception_stage(self, user_input: str) -> Dict[str, Any]:
        """
        Stage 1: Perception - Analyze input and determine genre
        
        Args:
            user_input: User input (text or image path)
            
        Returns:
            Context dict with perception results
        """
        context = {
            'original_input': user_input,
            'is_image': False,
            'image_analysis': '',
            'suggested_genre': '',
            'query_text': user_input
        }
        
        # Get available genres
        available_genres = self.music_search_tool.get_available_genres()
        genres_pool = ", ".join(available_genres)
        
        # Check if input is an image
        if os.path.isfile(user_input) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
            context['is_image'] = True
            
            # Use vision model for image analysis
            vision_prompt = f"分析这张图片的意境。然后从以下流派中选出1个最匹配的单词：[{genres_pool}]。注意：直接输出单词本身，不要带标点符号，不要解释。"
            
            try:
                suggested_genre = self.model_manager.invoke_vision(user_input, vision_prompt)
                context['suggested_genre'] = re.sub(r'[^\w\s]', '', suggested_genre).strip().lower()
                context['image_analysis'] = f"这张图散发着一种 {context['suggested_genre']} 的氛围。"
                context['query_text'] = "这张图片的视觉意境"
                
                print(f"🖼️  [视觉感知] 图片意境: {context['suggested_genre']}")
                
            except Exception as e:
                print(f"⚠️  Vision analysis failed: {e}")
                context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                context['image_analysis'] = "图片分析失败，使用默认推荐。"
        
        else:
            # Text mode - use text model for genre classification
            keyword_prompt = f"根据描述 '{user_input}'，从以下流派中选出一个最匹配的：[{genres_pool}]。仅输出单词，不要标点。"
            
            try:
                suggested_genre = self.model_manager.invoke_text(keyword_prompt)
                context['suggested_genre'] = re.sub(r'[^\w\s]', '', suggested_genre).strip().lower()
                context['image_analysis'] = f"听众想要这种感觉: {user_input}"
                
                print(f"🔍 [文本感知] 确定的流派: {context['suggested_genre']}")
                
            except Exception as e:
                print(f"⚠️  Text analysis failed: {e}")
                context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                context['image_analysis'] = "文本分析失败，使用默认推荐。"
        
        return context
    
    def _retrieval_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 2: Retrieval - Search music database using MusicSearchTool
        
        Args:
            context: Context from perception stage
            
        Returns:
            Context with search results
        """
        genre = context['suggested_genre']
        
        # Use MusicSearchTool for retrieval
        search_results = self.music_search_tool.search_by_genre(genre, limit=15)
        
        if not search_results:
            context['search_results'] = []
            context['candidates_text'] = ""
            print(f"❌ [检索] 没有找到 '{genre}' 类型的音乐")
        else:
            # Shuffle for variety
            random.shuffle(search_results)
            context['search_results'] = search_results
            
            # Format candidates for LLM
            candidates_text = ""
            for result in search_results:
                candidates_text += f"候选{result['index']}: 标题: {result['title']}, 描述: {result['model_tag']}\n"
            context['candidates_text'] = candidates_text
            
            print(f"✅ [检索] 找到 {len(search_results)} 首 '{genre}' 音乐")
        
        return context
    
    def _decision_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 3: Decision - Select best matching track from candidates
        
        Args:
            context: Context from retrieval stage
            
        Returns:
            Context with selected music
        """
        search_results = context['search_results']
        
        if not search_results:
            context['selected_music'] = None
            context['selection_error'] = "没有找到匹配的音乐"
            return context
        
        # If only one result, select it directly
        if len(search_results) == 1:
            context['selected_music'] = search_results[0]
            print(f"🎯 [决策] 唯一选择: {search_results[0]['title']}")
            return context
        
        # Use LLM to select best match
        selection_prompt = f"""
        你是一位感性的音乐主理人。
        图片/环境意境描述: {context['image_analysis']}
        
        曲库候选名单：
        {context['candidates_text']}
        
        请从中选出 1 首意境最贴合的歌。只需回复数字索引（如: 1）。
        """
        
        try:
            selection_response = self.model_manager.invoke_text(selection_prompt)
            
            # Extract number from response
            match = re.search(r'\d+', selection_response)
            if match:
                idx = int(match.group()) - 1
                # Ensure index is valid
                idx = max(0, min(idx, len(search_results) - 1))
                context['selected_music'] = search_results[idx]
                print(f"🎯 [智能决策] AI 选中了: {context['selected_music']['title']}")
            else:
                # Fallback to random selection
                context['selected_music'] = random.choice(search_results)
                print(f"🎲 [随机决策] 选中: {context['selected_music']['title']}")
                
        except Exception as e:
            print(f"⚠️  Decision failed, using random: {e}")
            context['selected_music'] = random.choice(search_results)
        
        return context
    
    def _generation_stage(self, context: Dict[str, Any]) -> str:
        """
        Stage 4: Generation - Generate personalized recommendation
        
        Args:
            context: Context from decision stage
            
        Returns:
            Final recommendation text
        """
        selected_music = context.get('selected_music')
        
        if not selected_music:
            return f"抱歉，关于 '{context['suggested_genre']}' 的音乐，我的收藏夹暂时还是空白。"
        
        # Generate recommendation using LLM
        prompt_template = ChatPromptTemplate.from_template("""
        你是一位感性、温柔的深夜电台音乐主理人。
        
        听众的需求/图片意境是: "{query}"
        
        你决定推荐这首歌:
        - 标题: {title}
        - 风格: {genre}
        - AI 捕捉到的隐藏韵律: {model_tag}
        
        请用自然、动人的语言告诉听众，为什么你觉得这首歌和此时此刻的氛围是最完美的搭配。
        """)
        
        try:
            recommendation_prompt = prompt_template.format(
                query=context['query_text'],
                title=selected_music['title'],
                genre=selected_music['genre'],
                model_tag=selected_music.get('model_tag', '未知韵律')
            )
            
            recommendation = self.model_manager.invoke_text(recommendation_prompt)
            print(f"✨ [生成] 推荐语生成完成")
            return recommendation
            
        except Exception as e:
            print(f"⚠️  Generation failed: {e}")
            return f"推荐: {selected_music['title']} - 一首很棒的 {selected_music['genre']} 音乐。"
    
    def get_recommendation(self, user_input: str) -> str:
        """
        Main interface - Generate music recommendation
        
        Args:
            user_input: User input (text description or image path)
            
        Returns:
            Personalized music recommendation
        """
        try:
            print(f"🎵 开始处理用户输入: {user_input}")
            
            # Execute main chain
            result = self.main_chain.invoke(user_input)
            return result
            
        except Exception as e:
            print(f"❌ 推荐过程出现错误: {e}")
            return "抱歉，音乐推荐过程中出现了问题，请稍后重试。"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration"""
        return {
            'model_info': self.model_manager.get_model_info(),
            'database_stats': self.music_search_tool.get_stats(),
            'available_genres': self.music_search_tool.get_available_genres()
        }


# Backward compatibility - alias for the old class name
MusicAIExplorer = MusicAgent


if __name__ == "__main__":
    # Test the refactored agent
    print("\n--- 🌙 深夜音乐馆：重构版Agent测试 ---")
    
    # Test with different model configurations
    print("\n=== Testing with OpenAI models ===")
    agent_openai = MusicAgent(use_local_model=False)
    print("Agent info:", agent_openai.get_agent_info())
    
    # Test text input
    test_input = "我想要一点迷幻且复古的音乐"
    print(f"\n用户输入: {test_input}")
    recommendation = agent_openai.get_recommendation(test_input)
    print(f"\n推荐结果:\n{recommendation}")
    
    # Test image input (if exists)
    test_image = "img/music_img.jpg"
    if os.path.exists(test_image):
        print(f"\n图片输入: {test_image}")
        recommendation = agent_openai.get_recommendation(test_image)
        print(f"\n推荐结果:\n{recommendation}")
    else:
        print(f"⚠️  测试图片不存在: {test_image}")
    
    # Test with local models (if available)
    print("\n=== Testing with local models ===")
    agent_local = MusicAgent(use_local_model=True)
    if agent_local.model_manager.use_local:
        recommendation = agent_local.get_recommendation(test_input)
        print(f"\n本地模型推荐:\n{recommendation}")
    else:
        print("本地模型不可用，已回退到OpenAI")