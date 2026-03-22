"""
Generation Chain - Stage 4: Final output generation
"""
from typing import Dict, Any, List, Optional
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
            context['final_report'] = self._generate_summary_report(
                found_songs, search_goal, pipeline_context=context
            )
            print(f"🎯 [生成阶段] 生成了包含 {len(found_songs)} 首歌曲的推荐报告")
        else:
            context['final_report'] = f"抱歉，没有找到与'{search_goal}'相关的音乐推荐。"
            print("🎯 [生成阶段] 生成了无结果的回复")
        
        return context

    def _reason_line_for_report(self, song: Dict[str, Any], search_goal: str) -> str:
        """User-facing reason line: prefer AI explanation; use context only if not raw wiki/markdown."""
        ex = (song.get("explanation") or "").strip()
        if ex:
            return ex
        ctx = (song.get("context") or "").strip()
        if ctx and len(ctx) < 1200 and "](http" not in ctx and "[[" not in ctx:
            return ctx
        return f"与您的搜索「{search_goal}」相关的优质选曲，值得聆听。"
    
    def _generate_summary_report(
        self,
        songs: list,
        search_goal: str,
        pipeline_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a summary report of found songs with enhanced context"""
        if not songs:
            return f"抱歉，没有找到与'{search_goal}'相关的音乐推荐。"
        
        # Final-list only: always run professional blurbs (does not affect retrieval)
        print("🎯 [文案增强] 正在为已确定的歌单生成专栏式推荐语...")
        songs = self._enhance_song_contexts(songs, search_goal, pipeline_context or {})
        
        # No **bold** in header — main.parse_recommendation_text splits on **Title - Artist**
        report_parts = [
            f"🎵 基于您的搜索「{search_goal}」，为您推荐以下音乐：\n"
        ]
        
        for i, song in enumerate(songs, 1):
            song_name = song.get('song', 'Unknown')
            artist_name = song.get('artist', 'Unknown')
            reason_line = self._reason_line_for_report(song, search_goal)
            official_link = song.get('official_link', '')
            source_type = song.get('source', 'unknown')
            
            song_entry = f"{i}. **{song_name} - {artist_name}**\n"
            song_entry += f"推荐理由：{reason_line}\n"
            if official_link:
                song_entry += f"播放链接：{official_link}\n"
                song_entry += f"   🔗 [在 YouTube 上播放]({official_link})\n\n"
            else:
                song_entry += f"播放链接：\n"
                if source_type == 'no_link':
                    song_entry += f"   💡 *经典曲目，建议在您的主音乐 App 中搜索听取*\n\n"
                elif source_type == 'verified':
                    song_entry += f"   ⚠️ *已验证歌曲信息，播放链接暂不可用*\n\n"
                else:
                    song_entry += f"   💡 *已收录该单曲，建议在您的主音乐 App 中搜索听取*\n\n"
            
            report_parts.append(song_entry)
        
        linked_count = sum(1 for song in songs if song.get('official_link'))
        total_count = len(songs)
        
        report_parts.append(f"\n📊 推荐汇总: {total_count} 首歌曲，其中 {linked_count} 首有播放链接")
        
        return "\n".join(report_parts)
    
    def _enhance_song_contexts(
        self,
        songs: list,
        search_goal: str,
        pipeline_context: Optional[Dict[str, Any]] = None,
    ) -> list:
        """使用 LLM 为歌曲生成专业推荐语（仅改写展示用 context，不影响检索结果）"""
        pipeline_context = pipeline_context or {}
        try:
            song_list = []
            for song in songs:
                song_info = f"{song.get('artist', '')} - {song.get('song', '')}"
                song_list.append(song_info)
            
            enhancement_prompt = self._create_context_enhancement_prompt(
                song_list, search_goal, pipeline_context
            )
            
            response = self.model_manager.invoke_text(enhancement_prompt)
            print(f"🎯 [LLM增强] 响应: {response[:500]}...")
            
            enhanced_contexts = self._parse_enhancement_response(response)
            
            if enhanced_contexts:
                n = min(len(enhanced_contexts), len(songs))
                for i in range(n):
                    text = (enhanced_contexts[i] or "").strip()
                    if text:
                        songs[i]["context"] = text
                        print(
                            f"✨ [增强完成] {songs[i].get('artist')} - {songs[i].get('song')}: {text[:80]}..."
                        )
                if len(enhanced_contexts) < len(songs):
                    print(
                        f"⚠️ [文案增强] 仅返回 {len(enhanced_contexts)}/{len(songs)} 条，其余沿用原字段或兜底"
                    )
            
        except Exception as e:
            print(f"⚠️  [文案增强失败] {e}")
            for song in songs:
                if not song.get("context", "").strip():
                    song["context"] = f"{song.get('artist', 'Unknown')} 的经典作品"
        
        return songs
    
    def _create_context_enhancement_prompt(
        self,
        song_list: List[str],
        search_goal: str,
        pipeline_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """专栏式推荐语：与检索无关，仅服务前端展示。"""
        pipeline_context = pipeline_context or {}
        songs_text = "\n".join([f"{i+1}. {song}" for i, song in enumerate(song_list)])

        scene_lines: List[str] = []
        tags = pipeline_context.get("cultural_tags")
        if isinstance(tags, list) and tags:
            scene_lines.append(
                "氛围/文化线索（可自然呼应一两句，勿堆砌标签、勿复述用户原句）："
                + ", ".join(str(t).strip() for t in tags[:8] if t)
            )
        if pipeline_context.get("is_image"):
            scene_lines.append(
                "用户通过图片进入：可用一两句轻点氛围与情绪的呼应，避免套话如「根据图片」「与您搜索相关」。"
            )

        scene_block = ("\n" + "\n".join(scene_lines) + "\n") if scene_lines else ""

        return f"""你是一位资深音乐专栏编辑。请为下面每一首歌各写一段「推荐语」（面向普通乐迷），用于 App 内展示。

用户检索/意图（写作时勿照抄成标题腔）：{search_goal}
{scene_block}
歌曲列表（顺序与输出一一对应）：
{songs_text}

写作要求：
1. 每一段约 90–140 字，以这首歌为主：风格、听感、作品或艺人的一点背景，读起来像人在推荐，而不是百科摘要。
2. 语气专业但不僵硬；避免排比模板句、避免「综上所述」「总而言之」。
3. 可以轻轻点一下与上面氛围/意图的契合点，但不要写成 SEO 或「与您搜索相关的优质选曲」这类空话。
4. 不要输出 Markdown 链接、脚注、URL、[[数字]]。

请务必只返回 JSON（不要其它文字）：
{{"recommendations": ["第1首推荐语...", "第2首推荐语...", ...]}}
列表长度必须等于歌曲数量 {len(song_list)}。
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