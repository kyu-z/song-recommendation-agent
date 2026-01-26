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
        
        # Initialize context storage
        self._last_context = {}
        
        # Build main processing chain
        self._build_main_chain()
        
        print("✅ Music Agent initialized successfully")
    
    def _build_main_chain(self):
        """Build the main processing chain using LCEL"""
        # Define processing stages as RunnableLambda functions
        self.perception_stage = RunnableLambda(self._perception_stage)
        self.retrieval_stage = RunnableLambda(self._retrieval_stage)
        self.decision_stage = RunnableLambda(self._decision_stage)
        self.generation_stage = RunnableLambda(self._generation_stage_with_context_save)
        
        # Compose main chain
        self.main_chain = (
            self.perception_stage |
            self.retrieval_stage |
            self.decision_stage |
            self.generation_stage
        )
    
    def _perception_stage(self, user_input: str) -> Dict[str, Any]:
        """
        Stage 1: 意图感知 - 理解用户想要什么，不做分类
        
        Args:
            user_input: User input (text or image path)
            
        Returns:
            Context dict with search goal and vibe
        """
        context = {
            'raw_input': user_input,
            'search_goal': '',
            'found_songs': [],
            'final_report': ''
        }
        
        # Check if input is an image
        if os.path.isfile(user_input) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
            context['is_image'] = True
            
            # 图片意图理解
            vision_prompt = """You are a music curator with deep cultural knowledge and excellent visual recognition skills. Analyze this image and determine what type of music would best match.

FIRST: Try to identify specific elements:
- Is this from a specific anime, game, movie, or TV show? (Name it!)
- Are there recognizable characters? (Name them!)
- Is this a specific location, brand, or cultural reference?
- What specific activity or context is shown?

THEN: Determine appropriate music based on your identification:
- If you recognize a specific work (anime/game/movie), prioritize music FROM that work
- If you identify characters, consider their associated soundtracks/themes
- If it's a general scene, think about functional music needs

Examples of SPECIFIC thinking:
- Pokemon characters → "Pokemon soundtrack", "Pokemon theme songs"
- Love Live characters → "Love Live songs", "idol anime music"  
- Studio Ghibli scene → "Studio Ghibli soundtrack", "Ghibli music"
- Zelda imagery → "Legend of Zelda music", "game soundtrack"
- Beach with no specific references → "beach music", "summer hits"

Output format: {"identification": "What specific thing did you recognize, or general scene if nothing specific", "search_goal": "The most appropriate music search term based on your identification"}

Analyze the image with focus on SPECIFIC recognition first:"""
            try:
                analysis_result = self.model_manager.invoke_vision(user_input, vision_prompt)
                
                # 解析JSON响应
                json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
                if json_match:
                    print(f"🖼️  [调试] 找到JSON: {json_match.group()}")
                    parsed = json.loads(json_match.group())
                    raw_search_goal = parsed.get('search_goal', '').strip()
                    
                    # 清理搜索词：取逗号前的主要部分，去除冗余描述
                    if ',' in raw_search_goal:
                        # 如果有逗号，取第一部分（通常是最精确的）
                        context['search_goal'] = raw_search_goal.split(',')[0].strip()
                    else:
                        context['search_goal'] = raw_search_goal
                        
                    print(f"🖼️  [视觉感知] 原始: {raw_search_goal}")
                    print(f"🖼️  [视觉感知] 清理后: {context['search_goal']}")
                else:
                    print(f"🖼️  [调试] 未找到JSON，使用备用词汇")
                    # 备用：从响应中提取
                    context['search_goal'] = "atmospheric instrumental"
                
            except Exception as e:
                print(f"⚠️  Vision analysis failed: {e}")
                context['search_goal'] = "atmospheric music"
        
        else:
            # 文本意图理解 - 音乐术语翻译专家
            intent_prompt = f"""你是顶级音乐专家，专门将用户的口语化描述转化为精准的英文音乐搜索术语。

转换规则：
- 去掉形容词：'美妙的小提琴' → 'violin solo'
- 识别俚语：'钉鞋' → 'shoegaze'，'氛围' → 'ambient'，'迷幻' → 'psychedelic'
- 专业化：'那种复古感' → 'vintage'，'电子乐' → 'electronic'
- 乐器+风格：'爵士钢琴' → 'jazz piano'，'古典小提琴' → 'classical violin'
- 保持简洁：最多2-3个核心英文词

用户说："{user_input}"

输出格式：{{"search_goal": "精准英文搜索词"}}

不要解释，不要总结，只要最准确的英文术语！"""
            
            try:
                analysis_result = self.model_manager.invoke_text(intent_prompt)
                
                print(f"🔍 [AI理解] 原始响应: {analysis_result[:100]}...")
                
                # 解析JSON响应
                json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    context['search_goal'] = parsed.get('search_goal', '').strip()
                else:
                    # 备用：简单文本处理
                    context['search_goal'] = user_input.strip()
                
                print(f"🔍 [术语翻译] 搜索目标: {context['search_goal']}")
                
            except Exception as e:
                print(f"⚠️  Text analysis failed: {e}")
                context['search_goal'] = user_input.strip()
        
        print(f"🎯 [调试] 最终context: {context}")
        return context
    
    def _generate_discovery_queries(self, context: Dict[str, Any]) -> List[str]:
        """
        智能搜索词生成 - 根据精确度采用不同策略
        """
        goal = context.get('search_goal', '')
        
        if not goal:
            return ["atmospheric music recommendations reddit"]
        
        # 检测是否为精确搜索词（包含具体作品名）
        specific_indicators = ['Love Live', 'Pokemon', 'Ghibli', 'Zelda', 'anime', 'soundtrack', 'OST', 'theme']
        is_specific = any(indicator.lower() in goal.lower() for indicator in specific_indicators)
        
        if is_specific:
            # 精确搜索：直接使用原词汇和简单变体
            queries = [
                goal,  # 原搜索词
                f"{goal} playlist",  # 播放列表
                f"{goal} collection"  # 合集
            ]
        else:
            # 泛化搜索：使用传统的修饰词策略
            queries = [
                f"{goal} essential",
                f"best {goal}",
                f"must hear {goal} songs"
            ]
        
        print(f"🎯 [搜索词生成] 基于术语: {goal} ({'精确' if is_specific else '泛化'})")
        
        return queries
    
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
            
            # 执行搜索（添加延迟避免频率限制）
            for i, query in enumerate(discovery_queries):
                if i > 0:  # 第一次不需要等待
                    time.sleep(1.5)  # 1.5秒延迟确保符合免费版限制
                try:
                    print(f"🔍 搜索 ({i+1}/{len(discovery_queries)}): {query}")
                    results = self.brave_search.run(query)
                    all_search_results.append(results)
                except Exception as e:
                    print(f"⚠️  Search failed for '{query}': {e}")
            
            print(f"🔍 [调试] 总共收集到 {len(all_search_results)} 个搜索结果")
            if not all_search_results:
                print("🔍 [调试] 没有任何搜索结果，提前返回")
                return []
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
        从搜索到的文字内容中，AI提取具体的歌名和艺人名 - 加入事实校验
        """
        combined_results = "\n".join(search_results)
        goal = context.get('search_goal', '')
        
        extraction_prompt = f"""从这些英文音乐推荐中提取歌曲：

搜索术语：{goal}
搜索内容：
{combined_results[:2000]}

**经典优先 + 严格事实校验要求**：
1. **优先选择该类型的经典代表作** - 知名度高、影响力大的标志性歌曲
2. 用户要"{goal}"类型的音乐，你提取的歌曲必须真的是这种类型
3. 必须提取完整正确的歌名和艺人名，不要省略或猜测
4. 如果看到不完整的信息（如只有歌名没有艺人），跳过该条目
5. 确保艺人名和歌名的拼写完全准确
6. 如果搜索结果里没有明确匹配{goal}的歌，返回空数组[]
7. **在同等质量下，优先选择更著名、更具代表性的艺术家和作品**
8. 宁可不推荐，也不要推荐错误类型或错误信息的歌曲

输出格式（JSON数组）：
[
  {{"song": "完整准确的歌名", "artist": "完整准确的艺人名", "context": "推荐理由或背景信息"}},
  {{"song": "另一首歌的完整歌名", "artist": "另一个艺人的完整名称", "context": "背景信息"}}
]

只提取信息完整且真实匹配{goal}的**经典代表作**！如果信息不完整或不匹配，返回[]。"""
        
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
                print("⚠️  [调试] 无法解析歌曲提取结果，未找到JSON数组")
                print(f"⚠️  [调试] 完整响应: {response}")
                return []
                
        except Exception as e:
            print(f"⚠️  歌曲提取失败: {e}")
            return []
    
    def _source_finding_phase(self, discovered_songs: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                        
                        # AI校验：确保是标准单曲（传入context用于乐器识别）
                        validated_info = self._validate_music_source(source_results, song_info, context)
                        
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
    
    def _validate_music_source(self, search_results: str, song_info: Dict[str, Any], context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        校验搜索到的链接是否为标准单曲（针对乐器音乐采用不同标准）
        """
        # 检查是否为乐器音乐
        instruments = context.get('instruments', '') if context else ''
        is_instrumental = instruments or any(word in song_info.get('song', '').lower() + ' ' + song_info.get('artist', '').lower() 
                                           for word in ['piano', 'violin', 'guitar', 'saxophone', 'trumpet', 'cello', 'flute', 'drums'])
        
        if is_instrumental:
            # 乐器音乐的验证标准
            validation_prompt = f"""检查这些搜索结果，为乐器演奏 "{song_info['song']}" by {song_info['artist']} 找出最高质量的音源：

搜索结果：
{search_results[:1500]}

乐器音乐专用验证标准：
1. **播放量优先**: 高播放量通常代表演奏质量被认可
2. **演奏完整性**: 完整的乐器演奏（避免片段或教学）
3. **音质清晰**: 优先选择音质清晰的录音
4. **不限制官方**: 个人演奏者、音乐学院学生、独立音乐家的优秀演奏都是有效的
5. **平台可靠**: YouTube、SoundCloud等知名平台

优先选择标准：
1. 高播放量的完整演奏版本
2. 标题包含乐器名称和曲目名称
3. 音质清晰的现场或录音室版本
4. 时长合理（通常2-15分钟）

需要避免的内容：
1. 明显的教学视频 ('Tutorial', 'How to play', 'Lesson', 'Learn')
2. 反应视频 ('Reaction', 'Review')
3. 过短的片段（少于1分钟）
4. 明显的翻唱或改编（除非演奏质量很高）

请返回播放量最高且质量最好的一个链接，格式：
{{"link": "URL地址", "platform": "平台名", "title": "视频/音频标题", "match_reason": "选择理由（包含播放量信息）"}}

如果没有找到合适结果，返回null。只返回JSON格式，不要其他文字。"""
        else:
            # 传统流行音乐的验证标准
            validation_prompt = f"""检查这些搜索结果，为歌曲 "{song_info['song']}" by {song_info['artist']} 找出最可靠的官方音源：

搜索结果：
{search_results[:1500]}

流行音乐验证标准：
1. 优先YouTube、Spotify、Apple Music等知名平台
2. 标题包含歌曲名或艺人名的核心关键词即可（不需要完全匹配）
3. 来自YouTube且标题相关的视频都视为有效
4. 不是明显的合集、播放列表标题（避免"playlist"、"mix"、"compilation"等词）
5. 优先官方版本，但不过度严格要求

注意过滤以下内容：
1. 标题包含 'Cover', 'Remix' (除非用户要求), 'Tutorial', 'How to play', 'Lesson'
2. 时长过短（少于2分钟）的片段或预览
3. 包含 'reaction', 'review', 'analysis' 的评论视频
4. 'karaoke', 'instrumental version' (除非用户明确要求)

优先选择：
1. 官方频道或知名音乐平台上传的内容
2. 完整版歌曲（通常3-6分钟正常时长）
3. 标题简洁直接，包含歌曲名和艺人名
4. 高播放量或来源可靠的版本

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
        Stage 2: 音乐搜索 - 基于搜索目标找音乐
        
        Args:
            context: Context from perception stage (includes search_goal and vibe)
            
        Returns:
            Context with found songs
        """
        print("🎵 [检索阶段] 开始全网音乐搜索...")
        
        # 全网搜索
        web_results = []
        if self.brave_search:
            try:
                # Discovery Phase: 发现真实歌曲
                discovered_songs = self._discovery_phase(context)
                
                if discovered_songs:
                    # Source Finding Phase: 精准音源匹配
                    web_results = self._source_finding_phase(discovered_songs, context)
                
            except Exception as e:
                print(f"⚠️  全网搜索失败: {e}")
        
        # 将找到的歌曲放入context
        if web_results:
            context['found_songs'] = web_results
            print(f"✅ [全网检索] 成功找到 {len(web_results)} 首歌曲")
        else:
            context['found_songs'] = []
            print("❌ [检索失败] 全网搜索未找到合适的音乐")
        
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
        Stage 3: 决策 - 简单选择找到的音乐
        
        Args:
            context: Context from retrieval stage
            
        Returns:
            Context with selected music (就是found_songs)
        """
        found_songs = context.get('found_songs', [])
        
        if found_songs:
            # 简单决策：使用所有找到的歌曲
            print(f"� [决策] 选择了 {len(found_songs)} 首歌曲")
        else:
            print("❌ [决策] 没有歌曲可选择")
            
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
        Stage 4: 基于找到的音乐生成推荐 - AI自由分析和推荐
        
        Args:
            context: Context from decision stage
            
        Returns:
            Final recommendation text
        """
        found_songs = context.get('found_songs', [])
        search_goal = context.get('search_goal', '')
        raw_input = context.get('raw_input', '')
        
        if not found_songs:
            return f"抱歉，没能为你找到匹配'{search_goal}'的音乐。请尝试用不同的描述方式。"
        
        # 让AI基于找到的音乐进行分析和推荐
        recommendation_prompt = f"""用户说："{raw_input}"

我理解用户想要：{search_goal}

我为用户找到了这些音乐：
{chr(10).join([f"- {song['song']} by {song['artist']}" for song in found_songs])}

请写一段推荐语，要求：
1. 解释为什么这些音乐符合用户对'{search_goal}'的需求
2. 基于你的音乐知识，补充这些歌曲的流派、背景、特色等信息
3. 语言感性、专业，让用户感受到被理解
4. 不要说"我找到了"，直接开始推荐理由

格式：
**歌曲名 - 艺人名**
推荐理由：[详细的推荐理由]
播放链接：[PLACEHOLDER_LINK]

[为每首歌重复上述格式]"""
        
        try:
            recommendation = self.model_manager.invoke_text(recommendation_prompt)
            
            # 后处理：添加实际的播放链接
            final_recommendation = recommendation
            for i, song in enumerate(found_songs):
                if song.get('official_link'):
                    # 按顺序替换占位符
                    final_recommendation = final_recommendation.replace(
                        "[PLACEHOLDER_LINK]", 
                        song['official_link'], 
                        1  # 只替换第一个匹配的
                    )
                    
                    # 备用替换模式
                    link_patterns = [
                        "播放链接：[链接]",
                        "播放链接：[从搜索中获得的链接]",
                        "[链接]"
                    ]
                    for pattern in link_patterns:
                        if pattern in final_recommendation:
                            final_recommendation = final_recommendation.replace(pattern, song['official_link'], 1)
                            break
            
            # 保存到context中
            context['final_report'] = final_recommendation
            return final_recommendation
            
        except Exception as e:
            print(f"⚠️  推荐生成失败: {e}")
            # 兜底推荐
            result = f"基于你对'{search_goal}'的需求，我为你找到了以下音乐：\n\n"
            
            for song in found_songs:
                song_title = song.get('song', 'Unknown')
                artist_name = song.get('artist', 'Unknown Artist')
                official_link = song.get('official_link', '链接暂时不可用')
                
                result += f"**{song_title} - {artist_name}**\n"
                result += f"这首音乐完美契合你对{search_goal}的需求。\n"
                result += f"播放链接：{official_link}\n\n"
            
            context['final_report'] = result
            return result
    
    def _generation_stage_with_context_save(self, context: Dict[str, Any]) -> str:
        """
        Wrapper for generation stage that saves context for API access
        """
        result = self._generation_stage(context)
        # Save the context for API access
        self._last_context = context.copy()
        return result
    
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
            
            # 后处理：添加实际的播放链接（改进替换逻辑）
            final_recommendation = recommendation
            for i, song in enumerate(songs):
                if song.get('official_link'):
                    # 使用正则表达式进行精确替换
                    placeholder_pattern = r'播放链接：\[从搜索中获得的链接\]'
                    actual_link = f"播放链接：{song['official_link']}"
                    final_recommendation = re.sub(placeholder_pattern, actual_link, final_recommendation, count=1)
            
            # 如果还有占位符没有替换，使用简单替换作为备份
            for i, song in enumerate(songs):
                if song.get('official_link'):
                    final_recommendation = final_recommendation.replace(
                        "[从搜索中获得的链接]", 
                        song['official_link'], 
                        1
                    )
            
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
            
            # Store the last context for API access
            self._last_context = getattr(self.main_chain, '_last_context', {})
            
            return result
            
        except Exception as e:
            print(f"❌ 推荐过程出现错误: {e}")
            return "抱歉，音乐推荐过程中出现了问题，请稍后重试。"
    
    def get_last_context(self) -> Dict[str, Any]:
        """
        Get the context from the last recommendation request
        For API use to access structured data
        """
        return getattr(self, '_last_context', {})
    
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
    print("\n--- 🎵 双引擎音乐推荐系统测试 ---")
    
    # Test with different model configurations
    print("\n=== 使用 OpenAI 模型测试 ===")
    agent_openai = MusicAgent(use_local_model=False)
    print("Agent info:", agent_openai.get_agent_info())
    
    # Test text input
    test_input = "我想要听迷幻摇滚"
    print(f"\n用户输入: {test_input}")
    recommendation = agent_openai.get_recommendation(test_input)
    print(f"\n推荐结果:\n{recommendation}")
    """
    # Test image input (if exists)
    test_image = "img/smtm.jpg"
    if os.path.exists(test_image):
        print(f"\n图片输入: {test_image}")
        recommendation = agent_openai.get_recommendation(test_image)
        print(f"\n推荐结果:\n{recommendation}")
    else:
        print(f"⚠️  测试图片不存在: {test_image}")
    """
    # Test with local models (已禁用)
    print("\n=== 本地模型已禁用 ===")
    print("所有请求都将使用 OpenAI GPT-4o-mini 模型")