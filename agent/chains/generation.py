"""
Generation Chain - Stage 4: Final output generation
"""
from typing import Dict, Any
import json

class GenerationChain:
    """Handles final response generation"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final response based on processed context
        
        Args:
            context: Complete context from previous stages
            
        Returns:
            Final response context
        """
        found_songs = context.get('found_songs', [])
        search_goal = context.get('search_goal', '')
        
        if found_songs:
            # Generate summary report
            context['final_report'] = self._generate_summary_report(found_songs, search_goal)
            print(f"🎯 [生成阶段] 生成了包含 {len(found_songs)} 首歌曲的推荐报告")
        else:
            context['final_report'] = f"抱歉，没有找到与'{search_goal}'相关的音乐推荐。"
            print("🎯 [生成阶段] 生成了无结果的回复")
        
        return context
    
    def _generate_summary_report(self, songs: list, search_goal: str) -> str:
        """Generate a summary report of found songs with enhanced context"""
        if not songs:
            return f"抱歉，没有找到与'{search_goal}'相关的音乐推荐。"
        
        # Check if we need to enhance contexts
        needs_enhancement = self._check_contexts_need_enhancement(songs)
        if needs_enhancement:
            print("🎯 [文案增强] 检测到空洞推荐理由，正在生成专业推荐语...")
            songs = self._enhance_song_contexts(songs, search_goal)
        
        report_parts = [
            f"🎵 **基于您的搜索「{search_goal}」，为您推荐以下音乐：**\n"
        ]
        
        for i, song in enumerate(songs, 1):
            song_name = song.get('song', 'Unknown')
            artist_name = song.get('artist', 'Unknown') 
            context_info = song.get('context', '')
            official_link = song.get('official_link', '')
            source_type = song.get('source', 'unknown')
            
            # Build song entry
            song_entry = f"{i}. **{song_name}** - *{artist_name}*\n"
            if context_info:
                song_entry += f"   > {context_info}\n"
            
            # Dynamic link handling based on verification status
            if official_link:
                song_entry += f"   🔗 [在 YouTube 上播放]({official_link})\n\n"
            elif source_type == 'no_link':
                song_entry += f"   💡 *经典曲目，建议在您的主音乐 App 中搜索听取*\n\n"
            elif source_type == 'verified':
                song_entry += f"   ⚠️ *已验证歌曲信息，播放链接暂不可用*\n\n"
            else:
                song_entry += f"   💡 *已收录该单曲，建议在您的主音乐 App 中搜索听取*\n\n"
            
            report_parts.append(song_entry)
        
        # Add summary footer
        linked_count = sum(1 for song in songs if song.get('official_link'))
        total_count = len(songs)
        
        report_parts.append(f"\n📊 **推荐汇总**: {total_count} 首歌曲，其中 {linked_count} 首有播放链接")
        
        return "\n".join(report_parts)
    
    def _check_contexts_need_enhancement(self, songs: list) -> bool:
        """检查是否需要增强推荐理由"""
        placeholder_keywords = ['推荐理由', '热门歌曲', '经典作品', '代表作', '必听']
        
        empty_or_placeholder_count = 0
        
        for song in songs:
            context = song.get('context', '').strip()
            if not context or len(context) < 10:
                empty_or_placeholder_count += 1
            elif any(keyword in context for keyword in placeholder_keywords):
                empty_or_placeholder_count += 1
        
        # Latency-sensitive default: only enhance when *all* contexts are unusable.
        # (Otherwise the additional LLM call can dominate end-to-end latency.)
        return empty_or_placeholder_count == len(songs)
    
    def _enhance_song_contexts(self, songs: list, search_goal: str) -> list:
        """使用 LLM 为歌曲生成专业推荐语"""
        try:
            # Prepare song list for LLM
            song_list = []
            for song in songs:
                song_info = f"{song.get('artist', '')} - {song.get('song', '')}"
                song_list.append(song_info)
            
            enhancement_prompt = self._create_context_enhancement_prompt(song_list, search_goal)
            
            # Call LLM
            response = self.model_manager.invoke_text(enhancement_prompt)
            print(f"🎯 [LLM增强] 响应: {response}")
            
            # Parse LLM response
            enhanced_contexts = self._parse_enhancement_response(response)
            
            # Apply enhanced contexts to songs
            if enhanced_contexts and len(enhanced_contexts) == len(songs):
                for i, song in enumerate(songs):
                    if i < len(enhanced_contexts):
                        song['context'] = enhanced_contexts[i]
                        print(f"✨ [增强完成] {song.get('artist')} - {song.get('song')}: {enhanced_contexts[i]}")
            
        except Exception as e:
            print(f"⚠️  [文案增强失败] {e}")
            # Fallback to basic context generation
            for song in songs:
                if not song.get('context', '').strip():
                    song['context'] = f"{song.get('artist', 'Unknown')} 的经典作品"
        
        return songs
    
    def _create_context_enhancement_prompt(self, song_list: list, search_goal: str) -> str:
        """创建文案增强的 Prompt"""
        songs_text = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(song_list)])
        
        return f"""你是一位资深音乐专栏作家。请为以下歌曲撰写一段深度、富有感染力且专业的推荐语。

用户搜索需求：{search_goal}
歌曲列表：
{songs_text}

要求：
1. 每首歌撰写一段 100-150 字左右的深度评析。
2. 评价维度：包含歌曲的风格流派、艺人的创作背景、歌曲的情感共鸣点、或者在乐坛的地位/成就。
3. 语气：专业、感性且吸引人，像是在为顶级音乐杂志撰稿。
4. 避免空洞词汇，尽量描述听感（如：编曲的层次感、人声的质感等）。

请务必返回以下 JSON 格式：
{{"recommendations": ["文案1...", "文案2..."]}}
"""
    
    def _parse_enhancement_response(self, response: str) -> list:
        """解析 LLM 的增强响应，支持 JSON 格式"""
        try:
            # 1. 尝试清理 Markdown 的代码块标签
            cleaned_response = response.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()

            # 2. 使用 json 模块解析
            data = json.loads(cleaned_response)
            
            # 3. 提取推荐语列表
            if isinstance(data, dict) and "recommendations" in data:
                return data["recommendations"]
            elif isinstance(data, list):
                return data
            return []

        except Exception as e:
            print(f"⚠️ [解析失败] 正在尝试行切分兜底: {e}")
            # 兜底方案：如果 AI 没按 JSON 返回，按行切分并过滤掉短句
            return [line.strip() for line in response.split('\n') if len(line.strip()) > 20]