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
        """Generate a summary report of found songs"""
        report_parts = [
            f"基于您的搜索「{search_goal}」，为您推荐以下音乐：\n"
        ]
        
        for i, song in enumerate(songs, 1):
            song_name = song.get('song', 'Unknown')
            artist_name = song.get('artist', 'Unknown')
            context_info = song.get('context', '')
            has_link = song.get('official_link') is not None
            
            report_parts.append(
                f"{i}. **{song_name}** - {artist_name}\n"
                f"   {context_info}\n"
                f"   {'🎵 可播放' if has_link else '📋 仅信息'}\n"
            )
        
        return "\n".join(report_parts)
