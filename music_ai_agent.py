import os
import base64
import re
import random
import json
import sys
import requests
import time
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

class BraveSearchTool:
    """Brave Search API wrapper for music discovery"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
    
    def run(self, query: str, count: int = 10) -> str:
        """Execute search query and return formatted results"""
        try:
            params = {
                "q": query,
                "count": count,
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate",
                "freshness": "py",  # Past year
                "text_decorations": False
            }
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("web", {}).get("results", [])
            
            # Format results for LLM consumption
            formatted_results = []
            for result in results:
                title = result.get("title", "")
                url = result.get("url", "")
                description = result.get("description", "")
                
                formatted_results.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n")
            
            return "\n".join(formatted_results)
            
        except requests.RequestException as e:
            print(f"Brave Search API error: {e}")
            return f"Search failed: {e}"
        except Exception as e:
            print(f"Brave Search processing error: {e}")
            return f"Search processing failed: {e}"


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
        
        # Initialize Brave Search for web discovery
        brave_api_key = os.getenv('Brave_Search_API_KEY')
        if brave_api_key:
            try:
                self.brave_search = BraveSearchTool(brave_api_key)
                print("✅ Brave Search initialized")
            except Exception as e:
                print(f"⚠️  Brave Search initialization failed: {e}")
                self.brave_search = None
        else:
            print("⚠️  Brave_Search_API_KEY not found in environment")
            self.brave_search = None
        
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
            'original_genre_request': '',  # 新增：保存用户原始流派需求
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
                        original_genre = parsed.get('genre', '').lower().strip()
                        context['original_genre_request'] = original_genre  # 保存原始需求
                        context['suggested_genre'] = original_genre
                        context['vocal_type'] = parsed.get('vocal_type', None)
                        if context['vocal_type']:
                            context['vocal_type'] = context['vocal_type'].lower().strip()
                        context['keywords'] = parsed.get('keywords', None)
                    else:
                        # Fallback: extract genre only
                        original_genre = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                        context['original_genre_request'] = original_genre
                        context['suggested_genre'] = original_genre
                except:
                    # Fallback: extract genre only
                    original_genre = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                    context['original_genre_request'] = original_genre
                    context['suggested_genre'] = original_genre
                
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

用户输入: "{user_input}"
可用流派: [{genres_pool}]

请分析：
1. 用户想要的流派（即使不在可用列表中，也要提取用户真实意图）
2. 人声偏好：用户是否明确提到"纯音乐"、"无人声"、"instrumental"（返回"instrumental"），或提到"有人声"、"vocal"（返回"vocal"），如果未提及则返回null
3. 心情关键词：提取2-3个描述用户心情/氛围的英文关键词（如：chill, night, calm, energetic, classical, jazz, blues），用逗号分隔

输出格式（必须是有效的JSON）：
{{"genre": "用户真实想要的流派", "vocal_type": "vocal或instrumental或null", "keywords": "关键词1,关键词2"}}

注意：即使用户想要的流派不在可用列表中，也要如实记录用户的真实需求。"""
            
            try:
                analysis_result = self.model_manager.invoke_text(enhanced_prompt)
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response
                    json_match = re.search(r'\{[^}]+\}', analysis_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        original_genre = parsed.get('genre', '').lower().strip()
                        context['original_genre_request'] = original_genre  # 保存原始需求
                        context['suggested_genre'] = original_genre
                        context['vocal_type'] = parsed.get('vocal_type', None)
                        if context['vocal_type']:
                            context['vocal_type'] = context['vocal_type'].lower().strip()
                        context['keywords'] = parsed.get('keywords', None)
                    else:
                        # Fallback: extract genre only
                        original_genre = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                    context['original_genre_request'] = original_genre
                    context['suggested_genre'] = original_genre
                except:
                    # Fallback: extract genre only
                    original_genre = re.sub(r'[^\w\s]', '', analysis_result).strip().lower()
                    context['original_genre_request'] = original_genre
                    context['suggested_genre'] = original_genre
                
                # 确保原始流派需求被正确设置
                if not context.get('original_genre_request'):
                    # 从用户输入中直接提取流派关键词
                    user_lower = user_input.lower()
                    genre_keywords = ['jazz', '爵士', 'classical', '古典', 'blues', '蓝调', 'rock', '摇滚', 'pop', '流行']
                    for keyword in genre_keywords:
                        if keyword in user_lower:
                            if keyword in ['爵士']:
                                context['original_genre_request'] = 'jazz'
                            elif keyword in ['古典']:
                                context['original_genre_request'] = 'classical'
                            elif keyword in ['蓝调']:
                                context['original_genre_request'] = 'blues'
                            elif keyword in ['摇滚']:
                                context['original_genre_request'] = 'rock'
                            elif keyword in ['流行']:
                                context['original_genre_request'] = 'pop'
                            else:
                                context['original_genre_request'] = keyword
                            break
                
                # Validate genre for local search (but keep original request intact)
                if context['suggested_genre'] not in available_genres:
                    context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                
                context['image_analysis'] = f"听众想要这种感觉: {user_input}"
                
                print(f"🔍 [文本感知] 流派: {context['suggested_genre']}, 人声类型: {context['vocal_type']}, 关键词: {context['keywords']}")
                
            except Exception as e:
                print(f"⚠️  Text analysis failed: {e}")
                context['suggested_genre'] = available_genres[0] if available_genres else "electronic"
                context['image_analysis'] = "文本分析失败，使用默认推荐。"
        
        return context
    
    def _generate_discovery_queries(self, context: Dict[str, Any]) -> List[str]:
        """
        生成发现阶段的搜索词，专门针对音乐推荐内容
        优先使用用户原始流派需求，避免流派偏见
        """
        # 优先使用用户原始需求，而非数据库匹配的流派
        original_genre = context.get('original_genre_request', '')
        fallback_genre = context.get('suggested_genre', '')
        genre = original_genre if original_genre else fallback_genre
        
        keywords = context.get('keywords', '')
        cultural_context = self._extract_cultural_context(context)
        mood_description = self._extract_mood_description(context)
        
        queries = []
        
        # 基于用户原始流派需求的推荐搜索
        if genre and keywords:
            queries.append(f"best {genre} songs for {keywords} mood reddit -site:youtube.com")
        elif genre:
            queries.append(f"best {genre} songs recommendations reddit -site:youtube.com")
        
        # 文化背景相关搜索
        if cultural_context:
            queries.append(f"{cultural_context} {genre if genre else 'music'} recommendations blog -site:youtube.com -site:spotify.com")
        
        # 氛围场景搜索
        if mood_description:
            queries.append(f"songs for {mood_description} playlist curator -site:youtube.com")
        
        # 如果没有生成任何搜索词，使用通用搜索
        if not queries:
            queries.append(f"atmospheric music recommendations reddit -site:youtube.com")
        
        print(f"🎯 [搜索词生成] 原始流派需求: {original_genre}, 本地匹配流派: {fallback_genre}")
        
        return queries[:3]  # 最多返回3个搜索词
    
    def _extract_cultural_context(self, context: Dict[str, Any]) -> str:
        """从上下文中提取文化背景信息"""
        image_analysis = context.get('image_analysis', '').lower()
        
        if '日本' in image_analysis or 'japanese' in image_analysis or '日式' in image_analysis:
            return 'japanese'
        elif '韩国' in image_analysis or 'korean' in image_analysis or '韩式' in image_analysis:
            return 'korean'
        elif '中国' in image_analysis or 'chinese' in image_analysis or '中式' in image_analysis:
            return 'chinese'
        elif '西方' in image_analysis or 'western' in image_analysis:
            return 'western'
        
        return ''
    
    def _extract_mood_description(self, context: Dict[str, Any]) -> str:
        """从上下文中提取心情描述"""
        keywords = context.get('keywords', '')
        image_analysis = context.get('image_analysis', '').lower()
        
        if keywords:
            return keywords.replace(',', ' ')
        elif '夜' in image_analysis or 'night' in image_analysis:
            return 'night ambient'
        elif '雨' in image_analysis or 'rain' in image_analysis:
            return 'rainy day'
        elif '安静' in image_analysis or 'quiet' in image_analysis or 'calm' in image_analysis:
            return 'calm peaceful'
        
        return 'atmospheric ambient'
    
    def _discovery_phase(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        第一阶段：从音乐社区、博客、杂志中发现真实曲目
        """
        if not self.brave_search:
            print("⚠️  Brave Search not available, skipping discovery phase")
            return []
        
        try:
            print("🔍 [Discovery Phase] 开始全网音乐发现...")
            
            # 生成发现性搜索词
            discovery_queries = self._generate_discovery_queries(context)
            print(f"🔍 Discovery queries: {discovery_queries}")
            
            all_search_results = []
            
            # 执行搜索
            for query in discovery_queries:
                try:
                    results = self.brave_search.run(query)
                    all_search_results.append(results)
                except Exception as e:
                    print(f"⚠️  Search failed for '{query}': {e}")
            
            if not all_search_results:
                return []
            
            # AI从文字中提取歌曲信息
            discovered_songs = self._extract_songs_from_text(all_search_results, context)
            print(f"✅ [Discovery] 发现 {len(discovered_songs)} 首候选歌曲")
            
            return discovered_songs
            
        except Exception as e:
            print(f"❌ [Discovery Phase] 失败: {e}")
            return []
    
    def _extract_songs_from_text(self, search_results: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从搜索到的文字内容中，AI提取具体的歌名和艺人名
        """
        combined_results = "\n".join(search_results)
        
        extraction_prompt = f"""从这些音乐推荐讨论中提取具体的歌曲信息：

搜索内容：
{combined_results[:2000]}  

用户场景：{context.get('image_analysis', '')}
偏好流派：{context.get('suggested_genre', '')}
关键词：{context.get('keywords', '')}

请提取3-5首最符合用户场景的真实歌曲，要求：
1. 必须是具体的歌名和艺人名（不是专辑名或泛泛描述）
2. 优先选择被多次推荐或评价较高的歌曲
3. 符合用户的流派和心情偏好
4. 如果提到背景信息（电影原声、经典地位等），请一并记录

输出格式（JSON数组）：
[
  {{"song": "具体歌名", "artist": "艺人名", "context": "推荐理由或背景信息"}},
  {{"song": "另一首歌", "artist": "艺人名", "context": "背景信息"}}
]

只返回JSON，不要其他文字。如果没有找到合适的歌曲，返回空数组[]。"""
        
        try:
            response = self.model_manager.invoke_text(extraction_prompt)
            
            # 尝试解析JSON
            import json
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                extracted_songs = json.loads(json_match.group())
                
                # 过滤和验证结果
                valid_songs = []
                for song in extracted_songs:
                    if isinstance(song, dict) and song.get('song') and song.get('artist'):
                        valid_songs.append({
                            'song': song['song'].strip(),
                            'artist': song['artist'].strip(),
                            'context': song.get('context', '').strip(),
                            'source': 'discovery'
                        })
                
                return valid_songs[:5]  # 最多返回5首
            else:
                print("⚠️  无法解析歌曲提取结果")
                return []
                
        except Exception as e:
            print(f"⚠️  歌曲提取失败: {e}")
            return []
    
    def _source_finding_phase(self, discovered_songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        第二阶段：为确定的歌曲找到官方音源链接
        """
        if not self.brave_search or not discovered_songs:
            return []
        
        print("🎵 [Source Finding Phase] 开始精准音源匹配...")
        
        final_results = []
        
        for i, song_info in enumerate(discovered_songs):
            try:
                # 优化搜索词格式，不使用强制引号
                artist = song_info["artist"].strip()
                song = song_info["song"].strip()
                
                # 尝试多种搜索格式，从简单到复杂
                search_formats = [
                    f"site:youtube.com {artist} {song}",
                    f"{artist} {song} official audio",
                    f'"{artist}" - "{song}" official'
                ]
                
                validated_info = None
                
                for search_format in search_formats:
                    print(f"🔍 搜索音源 ({i+1}/{len(discovered_songs)}): {search_format}")
                    
                    # 添加延迟以符合API频率限制
                    if i > 0:  # 第一次不需要等待
                        time.sleep(1.5)  # 1.5秒延迟确保符合免费版限制
                    
                    try:
                        # 搜索官方音源
                        source_results = self.brave_search.run(search_format, count=5)
                        
                        # 记录搜索结果用于调试
                        print(f"📝 [调试日志] 搜索词: {search_format}")
                        print(f"📝 [调试日志] 返回结果前200字符: {source_results[:200]}...")
                        
                        # AI校验：确保是标准单曲
                        validated_info = self._validate_music_source(source_results, song_info)
                        
                        if validated_info:
                            break  # 找到有效链接，跳出搜索格式循环
                            
                    except Exception as search_error:
                        print(f"⚠️  搜索格式 '{search_format}' 失败: {search_error}")
                        continue
                
                if validated_info:
                    final_results.append(validated_info)
                    print(f"✅ 找到音源: {song_info['song']} - {song_info['artist']}")
                else:
                    print(f"❌ 未找到可靠音源: {song_info['song']} - {song_info['artist']}")
                    print(f"📝 [调试日志] 尝试的所有搜索格式都未成功")
                    
            except Exception as e:
                print(f"⚠️  音源搜索失败 '{song_info['song']}': {e}")
        
        print(f"✅ [Source Finding] 成功匹配 {len(final_results)} 首歌曲")
        return final_results
    
    def _validate_music_source(self, search_results: str, song_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        校验搜索到的链接是否为标准单曲（放宽匹配标准）
        """
        validation_prompt = f"""检查这些搜索结果，为歌曲 "{song_info['song']}" by {song_info['artist']} 找出最可靠的官方音源：

搜索结果：
{search_results[:1500]}

放宽的验证标准：
1. 优先YouTube、Spotify、Apple Music等知名平台
2. 标题包含歌曲名或艺人名的核心关键词即可（不需要完全匹配）
3. 来自YouTube且标题相关的视频都视为有效
4. 不是明显的合集、播放列表标题（避免"playlist"、"mix"、"compilation"等词）
5. 不要过度严格要求官方版本

请返回最符合要求的一个链接，格式：
{{"link": "URL地址", "platform": "平台名", "title": "视频/音频标题", "match_reason": "匹配理由"}}

如果没有找到任何相关结果，返回null。只返回JSON格式，不要其他文字。"""
        
        try:
            response = self.model_manager.invoke_text(validation_prompt)
            
            # 尝试解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                validated = json.loads(json_match.group())
                
                if validated and validated.get('link'):
                    match_reason = validated.get('match_reason', 'AI验证通过')
                    print(f"🎯 [音源验证] 匹配理由: {match_reason}")
                    
                    return {
                        **song_info,
                        'official_link': validated['link'],
                        'platform': validated.get('platform', 'Unknown'),
                        'source_title': validated.get('title', ''),
                        'match_reason': match_reason,
                        'source': 'web',
                        'duration_validated': True
                    }
            
            print(f"📝 [调试日志] AI验证响应: {response[:200]}...")
            return None
            
        except Exception as e:
            print(f"⚠️  音源验证失败: {e}")
            print(f"📝 [调试日志] 验证过程出错，原始搜索结果: {search_results[:300]}...")
            return None

    def _retrieval_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 2: 双引擎检索 - 全网搜索优先 + 本地数据库兜底
        
        Args:
            context: Context from perception stage (includes genre, vocal_type, keywords)
            
        Returns:
            Context with search results from web or local database
        """
        print("🎵 [检索阶段] 开始双引擎音乐检索...")
        
        # 第一优先级：全网搜索
        web_results = []
        if self.brave_search:
            try:
                # Discovery Phase: 发现真实歌曲
                discovered_songs = self._discovery_phase(context)
                
                if discovered_songs:
                    # Source Finding Phase: 精准音源匹配
                    web_results = self._source_finding_phase(discovered_songs)
                
            except Exception as e:
                print(f"⚠️  全网搜索失败: {e}")
        
        # 判断全网搜索结果质量
        if web_results and len(web_results) >= 2:
            # 全网搜索成功，使用联网结果
            context['search_results'] = web_results
            context['result_source'] = 'web'
            context['candidates_text'] = self._format_web_candidates(web_results)
            print(f"✅ [全网检索] 成功找到 {len(web_results)} 首歌曲")
            
        else:
            # 第二优先级：本地搜索（兜底）
            print("🏠 [本地兜底] 全网搜索结果不足，切换到本地数据库...")
            local_results = self._local_search_engine(context)
            
            if local_results:
                context['search_results'] = local_results
                context['result_source'] = 'local'
                context['candidates_text'] = self._format_local_candidates(local_results)
                print(f"✅ [本地检索] 找到 {len(local_results)} 首本地收藏")
            else:
                # 完全没有结果
                context['search_results'] = []
                context['result_source'] = 'none'
                context['candidates_text'] = ""
                print("❌ [检索失败] 全网和本地都没有找到合适的音乐")
        
        return context
    
    def _local_search_engine(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        本地搜索引擎（原有逻辑保持不变）
        """
        genre = context['suggested_genre']
        vocal_type = context.get('vocal_type')
        keywords = context.get('keywords')
        
        # 使用现有的本地搜索逻辑
        search_results = self.music_search_tool.search_by_genre(
            genre=genre,
            vocal_type=vocal_type,
            keywords=keywords,
            limit=15
        )
        
        # 如果没有结果，尝试放宽条件
        if not search_results and vocal_type:
            print(f"⚠️  [本地检索] 使用 vocal_type={vocal_type} 无结果，尝试放宽过滤条件...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                vocal_type=None,
                keywords=keywords,
                limit=15
            )
        
        if not search_results and keywords:
            print(f"⚠️  [本地检索] 使用关键词过滤无结果，尝试仅使用流派...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                vocal_type=vocal_type if vocal_type else None,
                keywords=None,
                limit=15
            )
        
        # 最终回退：仅流派搜索
        if not search_results:
            print(f"⚠️  [本地检索] 使用所有过滤条件无结果，回退到仅流派搜索...")
            search_results = self.music_search_tool.search_by_genre(
                genre=genre,
                vocal_type=None,
                keywords=None,
                limit=15
            )
        
        if search_results:
            # 打乱顺序增加多样性
            random.shuffle(search_results)
            # 标记为本地来源
            for result in search_results:
                result['source'] = 'local'
        
        return search_results
    
    def _format_web_candidates(self, web_results: List[Dict[str, Any]]) -> str:
        """
        格式化全网搜索结果供LLM决策使用
        """
        candidates_text = ""
        for i, result in enumerate(web_results, 1):
            candidates_text += (
                f"候选{i}: "
                f"标题: {result['song']} | "
                f"艺术家: {result['artist']} | "
                f"平台: {result.get('platform', 'Unknown')} | "
                f"背景: {result.get('context', '无')} | "
                f"来源: 全网搜索\n"
            )
        return candidates_text
    
    def _format_local_candidates(self, local_results: List[Dict[str, Any]]) -> str:
        """
        格式化本地搜索结果供LLM决策使用
        """
        candidates_text = ""
        for result in local_results:
            source_tags = result.get('source_tags', '')
            if isinstance(source_tags, list):
                tags_str = ", ".join(source_tags)
            else:
                tags_str = str(source_tags) if source_tags else "无标签"
            
            vocal_display = result.get('vocal_type', 'unknown')
            speed_display = result.get('speed', 'unknown')
            
            candidates_text += (
                f"候选{result['index']}: "
                f"标题: {result['title']} | "
                f"艺术家: {result['artist']} | "
                f"标签: [{tags_str}] | "
                f"类型: [{vocal_display}] | "
                f"速度: [{speed_display}] | "
                f"来源: 本地收藏\n"
            )
        return candidates_text

    def _decision_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 3: 智能决策 - 根据来源和元数据选择最佳歌曲
        
        Args:
            context: Context from retrieval stage (includes candidates and source info)
            
        Returns:
            Context with selected music and source information
        """
        search_results = context['search_results']
        result_source = context.get('result_source', 'none')
        
        if not search_results:
            context['selected_music'] = None
            context['selection_error'] = "没有找到匹配的音乐"
            return context
        
        # 对于全网搜索结果，选择多首歌曲（3-5首）
        if result_source == 'web':
            # 全网搜索通常返回高质量结果，选择前3首
            selected_count = min(3, len(search_results))
            context['selected_music'] = search_results[:selected_count]
            print(f"🌐 [全网决策] 选择了 {selected_count} 首联网歌曲")
            
        else:
            # 本地搜索结果，使用AI智能选择单首
            if len(search_results) == 1:
                context['selected_music'] = [search_results[0]]
                song_info = search_results[0]
                print(f"🎯 [本地决策] 唯一选择: {song_info.get('title', song_info.get('song', 'Unknown'))}")
                
            else:
                # 多首本地结果，AI智能选择
                selected_song = self._ai_select_best_match(context)
                context['selected_music'] = [selected_song] if selected_song else []
                
        return context
    
    def _ai_select_best_match(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        AI智能选择最匹配的本地歌曲
        """
        search_results = context['search_results']
        
        user_preferences = []
        if context.get('vocal_type'):
            user_preferences.append(f"人声偏好: {context['vocal_type']}")
        if context.get('keywords'):
            user_preferences.append(f"心情关键词: {context['keywords']}")
        preferences_text = "\n".join(user_preferences) if user_preferences else "无特定偏好"
        
        selection_prompt = f"""你是一位感性的音乐策展人，需要从本地收藏中选择最合适的歌曲。

用户需求/图片意境: {context['image_analysis']}
用户偏好: {preferences_text}

本地收藏候选歌曲：
{context['candidates_text']}

请仔细分析每首歌的标签、类型、速度等信息，选择1首最贴合用户需求的歌曲。
你的选择应该基于：
1. 标签匹配度（关键词相关性）
2. 人声类型匹配度
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
                selected = search_results[idx]
                
                # Log selection reasoning
                source_tags = selected.get('source_tags', '')
                if isinstance(source_tags, list):
                    tags_str = ", ".join(source_tags)
                else:
                    tags_str = str(source_tags) if source_tags else "无标签"
                
                song_title = selected.get('title', selected.get('song', 'Unknown'))
                artist_name = selected.get('artist', 'Unknown Artist')
                
                print(f"🎯 [AI智能决策] 选中了: {song_title} - {artist_name}")
                print(f"   标签: [{tags_str}], 类型: [{selected.get('vocal_type', 'unknown')}]")
                
                return selected
            else:
                # Fallback to random selection
                selected = random.choice(search_results)
                song_title = selected.get('title', selected.get('song', 'Unknown'))
                print(f"🎲 [随机决策] 选中: {song_title}")
                return selected
                
        except Exception as e:
            print(f"⚠️  AI决策失败: {e}")
            # Fallback to first result
            return search_results[0] if search_results else None

    def _generation_stage(self, context: Dict[str, Any]) -> str:
        """
        Stage 4: 深度推荐生成 - 根据来源生成专业且感性的推荐理由
        
        Args:
            context: Context from decision stage
            
        Returns:
            Final recommendation text with deep reasoning
        """
        selected_music = context.get('selected_music')
        result_source = context.get('result_source', 'none')
        
        if not selected_music:
            return f"抱歉，关于 '{context.get('suggested_genre', '这种意境')}' 的音乐，我暂时没有找到合适的推荐。"
        
        # 处理不同来源的推荐生成
        if result_source == 'web' and isinstance(selected_music, list):
            # 全网搜索结果：多首歌曲的深度推荐
            return self._generate_web_recommendations(selected_music, context)
        elif isinstance(selected_music, list) and len(selected_music) > 0:
            # 单首本地歌曲推荐
            return self._generate_local_recommendation(selected_music[0], context)
        else:
            # 兼容旧格式
            return self._generate_local_recommendation(selected_music, context)
    
    def _generate_web_recommendations(self, songs: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        生成全网搜索结果的深度推荐
        """
        generation_prompt = f"""你是一位有深度的音乐策展人，需要为这些全网搜索到的歌曲写推荐理由。

用户场景：{context['image_analysis']}
用户偏好：{context.get('keywords', '')}

搜索到的歌曲：
{chr(10).join([f"- {song['song']} by {song['artist']} | 背景：{song.get('context', '无')}" for song in songs])}

为每首歌写一段2-3句的推荐理由，要求：
1. 结合图片的视觉细节和氛围
2. 融入歌曲的背景信息（如电影原声、时代经典等）
3. 建立情感共鸣连接
4. 语言专业、感性且直接，避免陈旧的电台式开场白

输出格式：
🎵 基于你的意境，我从全网为你找到了这些歌曲：

**歌曲标题 - 艺人**
推荐理由：[感性且有深度的2-3句解释]
播放链接：[从搜索中获得的链接]

[重复上述格式为每首歌生成推荐]"""
        
        try:
            recommendation = self.model_manager.invoke_text(generation_prompt)
            
            # 后处理：添加实际的播放链接
            final_recommendation = recommendation
            for i, song in enumerate(songs):
                if song.get('official_link'):
                    link_placeholder = f"播放链接：[从搜索中获得的链接]"
                    actual_link = f"播放链接：{song['official_link']}"
                    final_recommendation = final_recommendation.replace(link_placeholder, actual_link, 1)
            
            return final_recommendation
            
        except Exception as e:
            print(f"⚠️  全网推荐生成失败: {e}")
            return self._generate_fallback_web_recommendation(songs, context)
    
    def _generate_local_recommendation(self, song: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        生成本地数据库歌曲的推荐
        """
        # 提取歌曲信息（兼容不同格式）
        song_title = song.get('title', song.get('song', 'Unknown'))
        artist_name = song.get('artist', 'Unknown Artist')
        source_tags = song.get('source_tags', '')
        vocal_type = song.get('vocal_type', 'unknown')
        speed = song.get('speed', 'unknown')
        
        # 处理标签格式
        if isinstance(source_tags, list):
            tags_display = ", ".join(source_tags)
        else:
            tags_display = str(source_tags) if source_tags else "无标签"
        
        generation_prompt = f"""你是一位专业的音乐策展人，需要为这首本地收藏写推荐理由。

用户场景：{context['image_analysis']}
用户偏好：{context.get('keywords', '')}

选中的歌曲：
- 标题：{song_title}
- 艺人：{artist_name}
- 标签：{tags_display}
- 类型：{vocal_type}
- 速度：{speed}

写一段2-3句的推荐理由，要求：
1. 结合图片的视觉细节和情感氛围
2. 引用歌曲的标签来增强说服力
3. 建立情感共鸣连接
4. 开头提到：'全网搜索未果，但我从私房库中找到了这首同样契合的珍藏'
5. 语言专业、温柔且直接

输出格式：
🏠 全网搜索未果，但我从私房库中找到了这首同样契合的珍藏：

**{song_title} - {artist_name}**
推荐理由：[感性且有深度的2-3句解释，必须引用标签]
播放链接：本地收藏"""
        
        try:
            recommendation = self.model_manager.invoke_text(generation_prompt)
            return recommendation
            
        except Exception as e:
            print(f"⚠️  本地推荐生成失败: {e}")
            return f"""🏠 全网搜索未果，但我从私房库中找到了这首同样契合的珍藏：

**{song_title} - {artist_name}**
推荐理由：这首歌的标签 [{tags_display}] 与你现在的氛围非常契合。它的{vocal_type}特质正好符合此刻的意境。
播放链接：本地收藏"""
    
    def _generate_fallback_web_recommendation(self, songs: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        全网推荐生成失败时的兜底方案
        """
        result = "🎵 基于你的意境，我从全网为你找到了这些歌曲：\n\n"
        
        for song in songs:
            song_title = song.get('song', 'Unknown')
            artist_name = song.get('artist', 'Unknown Artist')
            context_info = song.get('context', '经典之作')
            official_link = song.get('official_link', '链接暂时不可用')
            
            result += f"**{song_title} - {artist_name}**\n"
            result += f"推荐理由：{context_info}，与你的意境完美契合。\n"
            result += f"播放链接：{official_link}\n\n"
        
        return result

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