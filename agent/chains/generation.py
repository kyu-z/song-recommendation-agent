"""
Generation Chain - Stage 4: Final output generation
"""
from typing import Dict, Any


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
            match_reason = song.get('match_reason', '')
            
            # Build song entry
            song_entry = f"{i}. **{song_name}** - *{artist_name}*\n"
            
            # Add enhanced context if available
            if context_info and context_info.strip():
                song_entry += f"   💭 {context_info}\n"
            
            # Add match reason if available
            if match_reason:
                song_entry += f"   🎯 {match_reason}\n"
            
            # Add clickable link if available
            if official_link and official_link.strip():
                song_entry += f"   🎶 [点击播放]({official_link})\n"
            else:
                song_entry += f"   📋 暂无播放链接\n"
            
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
        
        # If more than half need enhancement, do it for all
        return empty_or_placeholder_count > len(songs) // 2
    
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
        
        return f"""你是一位资深音乐评论人，请为以下歌曲生成简洁、专业、有吸引力的推荐语。

用户搜索：{search_goal}
歌曲列表：
{songs_text}

要求：
1. 每首歌一句推荐语（30字以内）
2. 突出歌曲的独特价值或流行背景
3. 避免空洞词汇如"经典作品"、"热门歌曲"
4. 可提及具体的成就、影响或特色

示例风格：
- "Billboard Hot 100 冠军单曲，定义了2023年流行音乐"
- "TikTok病毒传播，全球播放量突破10亿次"
- "获格莱美最佳流行歌曲提名的治愈系神曲"

请按顺序输出每首歌的推荐语，每行一句，不要编号："""
    
    def _parse_enhancement_response(self, response: str) -> list:
        """解析 LLM 的增强响应"""
        lines = response.strip().split('\n')
        contexts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove numbering if present
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')):
                line = line.split('.', 1)[1].strip()
            
            # Remove leading dashes
            if line.startswith('-'):
                line = line[1:].strip()
            
            if line and len(line) > 5:  # Valid context
                contexts.append(line)
        
        return contexts
