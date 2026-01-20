import os
import base64
import re
import random
import json
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
        Stage 1: Perception - Analyze input and extract genre, vocal_type, and keywords
        
        Args:
            user_input: User input (text or image path)
            
        Returns:
            Context dict with perception results including:
            - suggested_genre: Music genre
            - vocal_type: 'vocal' or 'instrumental' or None
            - keywords: Comma-separated keywords for mood/tags
        """
        context = {
            'original_input': user_input,
            'is_image': False,
            'image_analysis': '',
            'suggested_genre': '',
            'vocal_type': None,
            'keywords': None,
            'query_text': user_input
        }
        
        # Get available genres
        available_genres = self.music_search_tool.get_available_genres()
        genres_pool = ", ".join(available_genres)
        
        # Check if input is an image
        if os.path.isfile(user_input) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
            context['is_image'] = True
            
            # Enhanced vision prompt: extract genre, vocal preference, and mood keywords
            vision_prompt = f"""分析这张图片的意境，然后回答以下问题（用JSON格式）：
1. 流派：从以下流派中选出1个最匹配的：[{genres_pool}]
2. 人声偏好：判断这张图更适合"vocal"（有人声）还是"instrumental"（纯音乐），如果无法判断则返回null
3. 心情关键词：提取2-3个描述这张图心情/氛围的英文关键词（如：chill, night, calm, energetic），用逗号分隔

请以JSON格式输出，例如：{{"genre": "jazz", "vocal_type": "instrumental", "keywords": "night,calm"}}
如果无法判断某个字段，使用null。"""
            
            try:
                analysis_result = self.model_manager.invoke_vision(user_input, vision_prompt)
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response (handle markdown code blocks)
                    json_match = re.search(r'\{[^}]+\}', analysis_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        context['suggested_genre'] = parsed.get('genre', '').lower().strip()
                        context['vocal_type'] = parsed.get('vocal_type', None)
                        if context['vocal_type']:
                            context['vocal_type'] = context['vocal_type'].lower().strip()
                        context['keywords'] = parsed.get('keywords', None)
                    else:
                        # Fallback: extract genre only
                        context['suggested_genre'] = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                except:
                    # Fallback: extract genre only
                    context['suggested_genre'] = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                
                # Validate genre
                if context['suggested_genre'] not in available_genres:
                    context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                
                context['image_analysis'] = f"这张图散发着一种 {context['suggested_genre']} 的氛围。"
                context['query_text'] = "这张图片的视觉意境"
                
                print(f"🖼️  [视觉感知] 流派: {context['suggested_genre']}, 人声类型: {context['vocal_type']}, 关键词: {context['keywords']}")
                
            except Exception as e:
                print(f"⚠️  Vision analysis failed: {e}")
                context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                context['image_analysis'] = "图片分析失败，使用默认推荐。"
        
        else:
            # Text mode - enhanced analysis for genre, vocal_type, and keywords
            enhanced_prompt = f"""分析用户描述 '{user_input}'，然后回答以下问题（用JSON格式）：
1. 流派：从以下流派中选出1个最匹配的：[{genres_pool}]
2. 人声偏好：用户是否明确提到"纯音乐"、"无人声"、"instrumental"（返回"instrumental"），或提到"有人声"、"vocal"（返回"vocal"），如果未提及则返回null
3. 心情关键词：提取2-3个描述用户心情/氛围的英文关键词（如：chill, night, calm, energetic, trap, dark），用逗号分隔

请以JSON格式输出，例如：{{"genre": "hiphop", "vocal_type": "instrumental", "keywords": "trap,chill"}}
如果无法判断某个字段，使用null。"""
            
            try:
                analysis_result = self.model_manager.invoke_text(enhanced_prompt)
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response
                    json_match = re.search(r'\{[^}]+\}', analysis_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        context['suggested_genre'] = parsed.get('genre', '').lower().strip()
                        context['vocal_type'] = parsed.get('vocal_type', None)
                        if context['vocal_type']:
                            context['vocal_type'] = context['vocal_type'].lower().strip()
                        context['keywords'] = parsed.get('keywords', None)
                    else:
                        # Fallback: extract genre only
                        context['suggested_genre'] = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                except:
                    # Fallback: extract genre only
                    context['suggested_genre'] = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                
                # Validate genre
                if context['suggested_genre'] not in available_genres:
                    context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                
                context['image_analysis'] = f"听众想要这种感觉: {user_input}"
                
                print(f"🔍 [文本感知] 流派: {context['suggested_genre']}, 人声类型: {context['vocal_type']}, 关键词: {context['keywords']}")
                
            except Exception as e:
                print(f"⚠️  Text analysis failed: {e}")
                context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                context['image_analysis'] = "文本分析失败，使用默认推荐。"
        
        return context
    
    def _retrieval_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 2: Retrieval - Search music database with enhanced filters
        
        Args:
            context: Context from perception stage (includes genre, vocal_type, keywords)
            
        Returns:
            Context with search results including full metadata
        """
        genre = context['suggested_genre']
        vocal_type = context.get('vocal_type')
        keywords = context.get('keywords')
        
        # Try search with all filters first
        search_results = self.music_search_tool.search_by_genre(
            genre=genre,
            limit=15,
            vocal_type=vocal_type,
            keywords=keywords
        )
        
        # If no results with vocal_type filter, try without it (but keep keywords)
        if not search_results and vocal_type:
            print(f"⚠️  [检索] 使用 vocal_type={vocal_type} 无结果，尝试放宽过滤条件...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                limit=15,
                vocal_type=None,  # Remove vocal_type filter
                keywords=keywords
            )
        
        # If still no results with keywords, try without keywords (but keep vocal_type if it worked)
        if not search_results and keywords:
            print(f"⚠️  [检索] 使用关键词过滤无结果，尝试仅使用流派...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                limit=15,
                vocal_type=vocal_type if vocal_type else None,
                keywords=None  # Remove keywords filter
            )
        
        # Final fallback: genre only
        if not search_results:
            print(f"⚠️  [检索] 使用所有过滤条件无结果，回退到仅流派搜索...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                limit=15,
                vocal_type=None,
                keywords=None
            )
        
        if not search_results:
            context['search_results'] = []
            context['candidates_text'] = ""
            filter_info = []
            if vocal_type:
                filter_info.append(f"人声类型={vocal_type}")
            if keywords:
                filter_info.append(f"关键词={keywords}")
            filter_str = f" (过滤条件: {', '.join(filter_info)})" if filter_info else ""
            print(f"❌ [检索] 没有找到 '{genre}' 类型的音乐{filter_str}")
        else:
            # Shuffle for variety
            random.shuffle(search_results)
            context['search_results'] = search_results
            
            # Format candidates for LLM with full metadata (source_tags, vocal_type, speed)
            candidates_text = ""
            for result in search_results:
                tags_str = ", ".join(result.get('source_tags', [])) if result.get('source_tags') else "无标签"
                vocal_display = result.get('vocal_type', 'unknown')
                speed_display = result.get('speed', 'unknown')
                
                candidates_text += (
                    f"候选{result['index']}: "
                    f"标题: {result['title']} | "
                    f"艺术家: {result['artist']} | "
                    f"标签: [{tags_str}] | "
                    f"类型: [{vocal_display}] | "
                    f"速度: [{speed_display}] | "
                    f"模型标签: {result.get('model_tag', 'unknown')}\n"
                )
            context['candidates_text'] = candidates_text
            
            filter_info = []
            if vocal_type:
                filter_info.append(f"人声类型={vocal_type}")
            if keywords:
                filter_info.append(f"关键词={keywords}")
            filter_str = f" (过滤条件: {', '.join(filter_info)})" if filter_info else ""
            print(f"✅ [检索] 找到 {len(search_results)} 首 '{genre}' 音乐{filter_str}")
        
        return context
    
    def _decision_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 3: Decision - Select best matching track based on tags and metadata
        
        Args:
            context: Context from retrieval stage (includes candidates with full metadata)
            
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
        
        # Enhanced LLM selection prompt with tag-based reasoning
        user_preferences = []
        if context.get('vocal_type'):
            user_preferences.append(f"人声偏好: {context['vocal_type']}")
        if context.get('keywords'):
            user_preferences.append(f"心情关键词: {context['keywords']}")
        preferences_text = "\n".join(user_preferences) if user_preferences else "无特定偏好"
        
        selection_prompt = f"""你是一位感性的音乐主理人，需要根据标签证据来选择最合适的歌曲。

用户需求/图片意境: {context['image_analysis']}
用户偏好: {preferences_text}

候选歌曲列表（每首歌都包含标签、类型、速度等元数据）：
{context['candidates_text']}

请仔细分析每首歌的标签（tags）、类型（vocal/instrumental）、速度等信息，选择1首最贴合用户需求的歌曲。
你的选择应该基于：
1. 标签匹配度（如果用户提到关键词，优先选择标签中包含这些关键词的歌曲）
2. 人声类型匹配度（如果用户有偏好，优先匹配）
3. 整体氛围契合度

请只回复数字索引（如: 1），不要有其他文字。"""
        
        try:
            selection_response = self.model_manager.invoke_text(selection_prompt)
            
            # Extract number from response
            match = re.search(r'\d+', selection_response)
            if match:
                idx = int(match.group()) - 1
                # Ensure index is valid
                idx = max(0, min(idx, len(search_results) - 1))
                context['selected_music'] = search_results[idx]
                
                # Log selection reasoning
                selected = context['selected_music']
                tags_str = ", ".join(selected.get('source_tags', [])) if selected.get('source_tags') else "无标签"
                print(f"🎯 [智能决策] AI 选中了: {selected['title']}")
                print(f"   标签: [{tags_str}], 类型: [{selected.get('vocal_type', 'unknown')}], 速度: [{selected.get('speed', 'unknown')}]")
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
        Stage 4: Generation - Generate personalized recommendation with tag references
        
        Args:
            context: Context from decision stage
            
        Returns:
            Final recommendation text that references source_tags for persuasion
        """
        selected_music = context.get('selected_music')
        
        if not selected_music:
            return f"抱歉，关于 '{context['suggested_genre']}' 的音乐，我的收藏夹暂时还是空白。"
        
        # Extract tags for reference
        source_tags = selected_music.get('source_tags', [])
        tags_display = ", ".join(source_tags) if source_tags else "无标签"
        vocal_type = selected_music.get('vocal_type', 'unknown')
        speed = selected_music.get('speed', 'unknown')
        
        # Generate recommendation using LLM with tag references
        prompt_template = ChatPromptTemplate.from_template("""
        你是一位感性、温柔的深夜电台音乐主理人。
        
        听众的需求/图片意境是: "{query}"
        
        你决定推荐这首歌:
        - 标题: {title}
        - 艺术家: {artist}
        - 风格: {genre}
        - 标签: [{tags}]
        - 类型: [{vocal_type}]
        - 速度: [{speed}]
        - AI 捕捉到的隐藏韵律: {model_tag}
        
        请用自然、动人的语言告诉听众，为什么你觉得这首歌和此时此刻的氛围是最完美的搭配。
        
        重要要求：
        1. 必须引用歌曲的标签（tags）来增强推荐的说服力
        2. 例如："我注意到这首歌带有'chill'和'night'标签，非常适合你现在的状态"
        3. 如果标签中有与用户需求相关的关键词，一定要提到
        4. 语言要感性、温暖，像深夜电台DJ一样
        
        请开始你的推荐：
        """)
        
        try:
            recommendation_prompt = prompt_template.format(
                query=context['query_text'],
                title=selected_music['title'],
                artist=selected_music.get('artist', 'Unknown Artist'),
                genre=selected_music['genre'],
                tags=tags_display,
                vocal_type=vocal_type,
                speed=speed,
                model_tag=selected_music.get('model_tag', '未知韵律')
            )
            
            recommendation = self.model_manager.invoke_text(recommendation_prompt)
            print(f"✨ [生成] 推荐语生成完成（已引用标签: {tags_display}）")
            return recommendation
            
        except Exception as e:
            print(f"⚠️  Generation failed: {e}")
            # Fallback with tag reference
            tags_mention = f"（标签: {tags_display}）" if source_tags else ""
            return f"推荐: {selected_music['title']} by {selected_music.get('artist', 'Unknown')} - 一首很棒的 {selected_music['genre']} 音乐{tags_mention}。"
    
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
    test_image = "img/smtm.jpg"
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