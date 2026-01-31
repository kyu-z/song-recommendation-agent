"""
Decision Chain - Stage 3: Source finding and result selection
"""
import time
import re
import json
from typing import Dict, Any, List, Optional
from ..prompts.validation import get_instrumental_validation_prompt, get_popular_music_validation_prompt


class DecisionChain:
    """Handles source finding and result selection"""
    
    def __init__(self, brave_search, model_manager):
        self.brave_search = brave_search
        self.model_manager = model_manager
    
    def select(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find sources and apply hard filtering for quality control
        
        Args:
            context: Context with discovered songs
            
        Returns:
            Updated context with filtered and ranked song selection
        """
        discovered_songs = context.get('found_songs', [])
        
        if discovered_songs:
            # Find sources for songs with automatic YouTube search
            candidate_results = self._automatic_source_finding(discovered_songs, context)
            print(f"🎯 [Auto Source Finding] 找到 {len(candidate_results)} 个候选结果")
            
            # Apply hard filtering
            filtered_results = self._apply_hard_filters(candidate_results, context)
            print(f"🛡️ [Hard Filter] 过滤后剩余 {len(filtered_results)} 个结果")
            
            # Rank by officialness and quality
            final_results = self._rank_by_officialness(filtered_results, context)
            print(f"⭐ [Ranking] 最终排序 {len(final_results)} 个结果")
            
            # Apply deduplication and selection
            deduplicated_results = self._deduplicate_and_select_best(final_results)
            print(f"🎯 [去重精选] 最终输出 {len(deduplicated_results)} 首歌曲")
            
            context['found_songs'] = deduplicated_results
            
            if deduplicated_results:
                print(f"✅ [决策] 最终选择了 {len(deduplicated_results)} 首高质量歌曲")
                
                # Debug: log final song structure
                for i, song in enumerate(deduplicated_results[:3], 1):  # Show first 3
                    print(f"🎯 [最终歌曲 {i}] {song.get('artist', 'N/A')} - {song.get('song', 'N/A')}")
                    print(f"   🔗 官方链接: {song.get('official_link', 'None')}")
                    print(f"   📝 匹配原因: {song.get('match_reason', 'None')}")
            else:
                print("❌ [决策] 去重后没有符合要求的歌曲")
        else:
            print("❌ [检索失败] 全网搜索未找到合适的音乐")
            print("❌ [决策] 没有歌曲可选择")
        
        return context
    
    def _apply_hard_filters(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        硬核垃圾过滤 + AI语义识别混合模式
        - 硬过滤：全球通用噪音词（cover, remix, reaction等）
        - AI识别：地域身份、官方性质、视频类型等复杂判断
        """
        vocal_type = context.get('vocal_type', 'unknown')
        
        # 1. 硬核垃圾过滤 - 全球通用噪音关键词
        UNIVERSAL_EXCLUDE_KEYWORDS = [
            'cover', 'reaction', 'tutorial', 'how to', 'lesson', 'guide',
            'remix', 'mashup', 'nightcore', 'slowed', 'reverb', '8d audio',
            'karaoke', 'instrumental version', 'backing track', 'acapella',
            'color coded', 'lyrics with', 'pronunciation guide', 'romanization',
            'fan made', 'amateur', 'bootleg', 'pirated', 'compilation mix'
        ]
        
        # Live performance关键词 - 仅在未特别请求时过滤
        LIVE_KEYWORDS = ['live', 'concert', 'performance', '演唱会', 'ライブ', '콘서트']
        
        print(f"🛡️ [硬核过滤] 开始处理 {len(candidates)} 个候选")
        
        hard_filtered = []
        for candidate in candidates:
            title = candidate.get('song', '').lower()
            artist = candidate.get('artist', '').lower()
            context_text = candidate.get('context', '').lower()
            youtube_title = candidate.get('youtube_title', '').lower()
            full_text = f"{title} {artist} {context_text} {youtube_title}"
            
            # 硬核垃圾过滤
            excluded = False
            exclude_reason = ""
            
            for keyword in UNIVERSAL_EXCLUDE_KEYWORDS:
                if keyword in full_text:
                    excluded = True
                    exclude_reason = keyword
                    break
            
            # Live performance特殊处理
            if not excluded:
                for keyword in LIVE_KEYWORDS:
                    if keyword in full_text and vocal_type != 'live':
                        excluded = True
                        exclude_reason = f"live_performance_{keyword}"
                        break
            
            if excluded:
                print(f"🛡️ [硬过滤] {title} by {artist} - 垃圾词: {exclude_reason}")
                continue
            
            # 通过硬过滤的候选进入下一阶段
            hard_filtered.append(candidate)
        
        print(f"🛡️ [硬过滤] 剩余 {len(hard_filtered)}/{len(candidates)} 个候选")
        
        # 2. AI语义识别阶段 - 批量处理节约成本
        if not hard_filtered:
            return []
        
        ai_validated = self._ai_semantic_validation(hard_filtered, context)
        print(f"🤖 [AI验证] 最终通过 {len(ai_validated)} 个候选")
        
        return ai_validated
    
    def _ai_semantic_validation(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用AI进行语义验证：地域身份、官方性质、视频类型判定"""
        origin_region = context.get('origin_region', 'unknown')
        search_goal = context.get('search_goal', '')
        
        validated_candidates = []
        
        # 批量处理以节约成本
        for candidate in candidates:
            try:
                # 构造AI验证的上下文信息
                validation_context = {
                    'song': candidate.get('song', ''),
                    'artist': candidate.get('artist', ''),
                    'youtube_title': candidate.get('youtube_title', ''),
                    'youtube_url': candidate.get('youtube_url', ''),
                    'context': candidate.get('context', ''),
                    'origin_region': origin_region,
                    'search_goal': search_goal
                }
                
                # 使用AI进行智能验证
                ai_analysis = self._invoke_ai_content_analysis(validation_context)
                
                if ai_analysis:
                    # 将AI分析结果合并到候选中
                    enhanced_candidate = {
                        **candidate,
                        'ai_verified': True,
                        'content_type': ai_analysis.get('content_type', 'unknown'),
                        'officialness_score': ai_analysis.get('officialness_score', 50),
                        'region_match': ai_analysis.get('region_match', True),
                        'channel_authority': ai_analysis.get('channel_authority', 'unknown'),
                        'ai_quality_score': ai_analysis.get('quality_score', 50)
                    }
                    
                    # 基于AI分析结果计算最终质量分数
                    final_score = self._calculate_ai_enhanced_quality_score(enhanced_candidate)
                    enhanced_candidate['quality_score'] = final_score
                    
                    validated_candidates.append(enhanced_candidate)
                    
                    print(f"🤖 [AI验证] {candidate.get('song', 'N/A')} - "
                          f"类型: {ai_analysis.get('content_type', 'unknown')}, "
                          f"官方度: {ai_analysis.get('officialness_score', 50)}, "
                          f"最终分数: {final_score:.1f}")
                else:
                    # AI验证失败，使用基础评分
                    base_score = self._calculate_basic_quality_score(candidate)
                    candidate['quality_score'] = base_score
                    candidate['ai_verified'] = False
                    validated_candidates.append(candidate)
                    print(f"⚠️  [AI验证] {candidate.get('song', 'N/A')} - AI验证失败，使用基础评分: {base_score:.1f}")
                
            except Exception as e:
                print(f"❌ [AI验证] 验证失败: {e}")
                # 出错时使用基础评分
                base_score = self._calculate_basic_quality_score(candidate)
                candidate['quality_score'] = base_score
                candidate['ai_verified'] = False
                validated_candidates.append(candidate)
        
        return validated_candidates
    
    def _invoke_ai_content_analysis(self, validation_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用AI进行内容分析"""
        try:
            analysis_prompt = self._build_content_analysis_prompt(validation_context)
            response = self.model_manager.invoke_text(analysis_prompt)
            
            # 解析AI响应 - 清理格式问题
            if response and response.strip():
                try:
                    # 清理常见的JSON格式问题
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
                    elif cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response.replace('```', '').strip()
                    
                    analysis = json.loads(cleaned_response)
                    return analysis
                except json.JSONDecodeError as e:
                    print(f"⚠️  [AI分析] JSON解析失败: {str(e)}")
                    print(f"📝 [原始响应] {response[:200]}...")
                    return None
            else:
                return None
        except Exception as e:
            print(f"❌ [AI分析] 调用失败: {e}")
            return None
    
    def _build_content_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """构建内容分析提示词"""
        return f"""你是专业的音乐内容分析师。请分析以下音乐内容的真实性和质量：

**目标歌曲信息：**
- 歌曲：{context['song']}
- 艺人：{context['artist']}
- 期望地域：{context['origin_region']}
- 搜索目标：{context['search_goal']}

**YouTube视频信息：**
- 视频标题：{context['youtube_title']}
- 视频链接：{context['youtube_url']}
- 相关描述：{context['context']}

**分析要求：**
1. **地域匹配性**：利用你的音乐知识判断这个艺人/歌曲是否来自目标地域
2. **频道权威性**：分析YouTube频道名称，识别官方频道（如SMTOWN、JYPE、Avex等）
3. **内容类型识别**：判断是Official MV、Lyric Video、Audio Only、Live Performance等
4. **官方程度评估**：基于频道名、视频标题、描述判断官方程度

**特别注意：**
- 即使标题是全英文，也要根据艺人背景判断地域匹配
- 官方发行的K-Pop、J-Pop经常使用全英文标题
- Topic频道（如"Artist - Topic"）是官方的音频频道
- VEVO、官方唱片公司频道都是高权威来源

请返回JSON格式分析结果：
```json
{{
    "region_match": true/false,
    "content_type": "Official MV/Lyric Video/Audio Only/Live Performance/Topic Channel/Unknown",
    "channel_authority": "Official Label/Topic Channel/Artist Official/Unofficial/Unknown", 
    "officialness_score": 0-100,
    "quality_score": 0-100,
    "analysis_notes": "分析说明"
}}
```

只返回JSON，不要其他文字。"""

    def _calculate_ai_enhanced_quality_score(self, candidate: Dict[str, Any]) -> float:
        """基于AI分析结果计算增强质量分数"""
        base_score = 30.0
        
        # AI官方度评分权重 (40%)
        officialness = candidate.get('officialness_score', 50)
        base_score += officialness * 0.4
        
        # AI质量评分权重 (30%)
        ai_quality = candidate.get('ai_quality_score', 50)
        base_score += ai_quality * 0.3
        
        # 内容类型加分 (20%)
        content_type = candidate.get('content_type', 'unknown')
        content_type_scores = {
            'Official MV': 25,
            'Topic Channel': 23,
            'Audio Only': 20,
            'Lyric Video': 18,
            'Live Performance': 15,
            'Unknown': 10
        }
        base_score += content_type_scores.get(content_type, 10)
        
        # 频道权威性加分 (10%)
        authority = candidate.get('channel_authority', 'unknown')
        authority_scores = {
            'Official Label': 10,
            'Topic Channel': 9,
            'Artist Official': 8,
            'Unofficial': 3,
            'Unknown': 5
        }
        base_score += authority_scores.get(authority, 5)
        
        # 地域匹配性加分/减分
        if not candidate.get('region_match', True):
            base_score -= 20  # 地域不匹配重度减分
        
        return max(0.0, min(100.0, base_score))
    
    def _calculate_basic_quality_score(self, candidate: Dict[str, Any]) -> float:
        """计算基础质量分数（AI验证失败时使用）"""
        score = 40.0  # 基础分数降低，因为未通过AI验证
        
        # 基于关键词的简单评分
        title = candidate.get('song', '').lower()
        artist = candidate.get('artist', '').lower()
        youtube_title = candidate.get('youtube_title', '').lower()
        full_text = f"{title} {artist} {youtube_title}"
        
        # 官方指示词加分
        if any(word in full_text for word in ['official', 'vevo', 'topic']):
            score += 25
        
        # 高质量指示词加分
        if any(word in full_text for word in ['hd', 'hq', 'music video']):
            score += 10
        
        # 负面指示词减分
        if any(word in full_text for word in ['amateur', 'fan made', 'unofficial']):
            score -= 15
        
        return max(0.0, min(100.0, score))
    
    def _calculate_quality_score(self, candidate: Dict[str, Any], full_text: str = None) -> float:
        """
        保持向后兼容的质量评分方法
        注意：新的AI增强过滤流程使用 _calculate_ai_enhanced_quality_score
        """
        if full_text is None:
            title = candidate.get('song', '').lower()
            artist = candidate.get('artist', '').lower()
            context_text = candidate.get('context', '').lower()
            youtube_title = candidate.get('youtube_title', '').lower()
            full_text = f"{title} {artist} {context_text} {youtube_title}"
        
        score = 50.0  # Base score
        
        # Official channel indicators (high priority)
        OFFICIAL_INDICATORS = ['official', 'vevo', 'topic', 'records', 'music', 'entertainment']
        for indicator in OFFICIAL_INDICATORS:
            if indicator in full_text:
                score += 30
                break
        
        # High-quality source indicators
        QUALITY_INDICATORS = ['hd', 'hq', 'high quality', 'official', 'music video']
        for indicator in QUALITY_INDICATORS:
            if indicator in full_text:
                score += 10
        
        # Negative indicators
        NEGATIVE_INDICATORS = ['amateur', 'fan made', 'unofficial', 'bootleg', 'pirated']
        for indicator in NEGATIVE_INDICATORS:
            if indicator in full_text:
                score -= 20
        
        return max(0.0, min(100.0, score))
    
    def _rank_by_officialness(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank candidates by officialness and quality"""
        if not candidates:
            return []
        
        # Sort by quality score (descending)
        ranked = sorted(candidates, key=lambda x: x.get('quality_score', 0), reverse=True)
        
        # Log ranking results
        print("⭐ [排序结果]:")
        for i, candidate in enumerate(ranked[:5]):  # Show top 5
            score = candidate.get('quality_score', 0)
            print(f"  {i+1}. {candidate.get('song', 'N/A')} - Score: {score:.1f}")
        
        return ranked[:10]  # Return top 10
    
    def _automatic_source_finding(self, discovered_songs: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Automatically find official YouTube sources for discovered songs"""
        results = []
        
        for song_info in discovered_songs:
            artist = song_info.get('artist', '')
            song = song_info.get('song', '')
            
            if not artist or not song:
                continue
                
            print(f"🎵 [自动音源] 搜索: {artist} - {song}")
            
            # Generate official audio search query
            search_query = f"{artist} {song} official"
            
            try:
                # Use Brave Search to find YouTube links
                if self.brave_search:
                    search_results = self.brave_search.run(f"site:youtube.com {search_query}")
                    
                    # Extract YouTube links and validate them
                    youtube_candidates = self._extract_youtube_links(search_results)
                    validated_candidates = self._validate_youtube_sources(youtube_candidates, artist, song)
                    
                    # Add validated candidates to results
                    for candidate in validated_candidates:
                        result = {
                            **song_info,  # Preserve original metadata
                            'youtube_url': candidate['url'],  # Keep original field for processing
                            'youtube_title': candidate['title'],
                            'duration': candidate.get('duration', 'unknown'),
                            'validation_score': candidate.get('score', 50),
                            'source_type': 'youtube_auto'
                        }
                        results.append(result)
                        
                    print(f"🎵 [自动音源] {artist} - {song}: 找到 {len(validated_candidates)} 个候选")
                else:
                    print("⚠️  Brave Search not available for source finding")
                    # Add song without YouTube link
                    results.append({
                        **song_info,
                        'youtube_url': None,
                        'source_type': 'no_source'
                    })
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️  [自动音源] 搜索失败 {artist} - {song}: {e}")
                results.append({
                    **song_info,
                    'youtube_url': None,
                    'source_type': 'search_failed'
                })
        
        return results
    
    def _extract_youtube_links(self, search_results: str) -> List[Dict[str, Any]]:
        """Extract YouTube video information from search results"""
        candidates = []
        
        # Simple regex to find YouTube URLs and titles
        # This is a basic implementation - in production you'd want more robust parsing
        youtube_pattern = r'https://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        urls = re.findall(youtube_pattern, search_results)
        
        for video_id in urls[:5]:  # Limit to top 5 results
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Try to extract title from surrounding text
            title_pattern = rf'.*?(.*?){re.escape(url)}.*?'
            title_match = re.search(title_pattern, search_results, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else f"Video {video_id}"
            
            candidates.append({
                'url': url,
                'title': title,
                'video_id': video_id
            })
        
        return candidates
    
    def _validate_youtube_sources(self, candidates: List[Dict[str, Any]], artist: str, song: str) -> List[Dict[str, Any]]:
        """Validate YouTube sources using title analysis and blacklist filtering"""
        if not candidates:
            return []
        
        # Blacklist keywords for filtering
        BLACKLIST_KEYWORDS = [
            'cover', 'reaction', 'remix', 'nightcore', 'slowed',
            'reverb', 'tutorial', 'how to', 'karaoke', 'instrumental version',
            'fan made', 'amateur', 'bootleg', 'live stream', 'compilation'
        ]
        
        # Official indicators for scoring
        OFFICIAL_KEYWORDS = [
            'official', 'vevo', 'topic', 'records', 'music', 'entertainment',
            'official audio', 'official video', 'official mv'
        ]
        
        validated = []
        
        for candidate in candidates:
            title = candidate['title'].lower()
            url = candidate['url']
            score = 50  # Base score
            
            # Check for blacklist keywords
            is_blacklisted = any(keyword in title for keyword in BLACKLIST_KEYWORDS)
            if is_blacklisted:
                print(f"🛡️ [黑名单过滤] {title[:50]}...")
                continue
            
            # Check for official indicators
            official_bonus = 0
            for keyword in OFFICIAL_KEYWORDS:
                if keyword in title:
                    official_bonus += 20
                    break
            
            # Check if title contains both artist and song name
            artist_match = artist.lower() in title
            song_match = song.lower() in title
            
            if artist_match and song_match:
                score += 30
            elif artist_match or song_match:
                score += 15
            
            score += official_bonus
            
            # Duration validation would go here in a full implementation
            # For now, we'll use a placeholder
            candidate['score'] = min(100, max(0, score))
            candidate['duration'] = 'unknown'  # Would extract from API
            
            validated.append(candidate)
            print(f"✅ [验证通过] {title[:50]}... (Score: {candidate['score']})")
        
        # Sort by score (highest first)
        validated.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return validated[:2]  # Return top 2 candidates per song
    
    def _deduplicate_and_select_best(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重并为每首歌选择最佳链接"""
        if not results:
            return []
        
        # Group by song identity (artist + song name)
        song_groups = {}
        
        for result in results:
            artist = result.get('artist', '').strip().lower()
            song = result.get('song', '').strip().lower()
            
            # Create unique key for the song
            song_key = f"{artist}|||{song}"
            
            if song_key not in song_groups:
                song_groups[song_key] = []
            
            song_groups[song_key].append(result)
        
        print(f"🎯 [去重分组] 发现 {len(song_groups)} 个独特歌曲组")
        
        # Select best version for each song
        final_songs = []
        
        for song_key, candidates in song_groups.items():
            print(f"🎯 [处理组] {song_key}: {len(candidates)} 个候选")
            
            # Sort candidates by validation score (highest first)
            candidates.sort(key=lambda x: x.get('validation_score', 0), reverse=True)
            best_candidate = candidates[0]
            
            # Standardize the output structure
            standardized_song = {
                'song': best_candidate.get('song', '').strip(),
                'artist': best_candidate.get('artist', '').strip(),
                'official_link': self._extract_official_link(best_candidate),
                'match_reason': self._generate_match_reason(best_candidate),
                'context': best_candidate.get('context', ''),
                'is_official_release': best_candidate.get('is_official_release', True),
                'artist_nationality': best_candidate.get('artist_nationality', 'unknown'),
                'validation_score': best_candidate.get('validation_score', 0)
            }
            
            final_songs.append(standardized_song)
            
            print(f"✅ [最佳选择] {standardized_song['artist']} - {standardized_song['song']}")
            print(f"   📝 推荐理由: {standardized_song['context']}")
            if standardized_song['official_link']:
                print(f"   🔗 链接: {standardized_song['official_link']}")
            print(f"   ⭐ 评分: {standardized_song['validation_score']}")
        
        # Sort final results by validation score and limit to reasonable number
        final_songs.sort(key=lambda x: x.get('validation_score', 0), reverse=True)
        
        return final_songs[:8]  # Return top 8 unique songs
    
    def _extract_official_link(self, candidate: Dict[str, Any]) -> str:
        """提取官方链接"""
        # Check various possible link fields
        possible_fields = ['youtube_url', 'official_link', 'url', 'link']
        
        for field in possible_fields:
            link = candidate.get(field)
            if link and isinstance(link, str) and link.strip():
                return link.strip()
        
        return ""
    
    def _generate_match_reason(self, candidate: Dict[str, Any]) -> str:
        """生成匹配原因"""
        reasons = []
        
        # Check source type
        source_type = candidate.get('source_type', '')
        if source_type == 'youtube_auto':
            reasons.append("自动音源匹配")
        elif source_type == 'discovery':
            reasons.append("发现阶段提取")
        
        # Check official status
        if candidate.get('is_official_release', False):
            reasons.append("官方发行")
        
        # Check validation score
        score = candidate.get('validation_score', 0)
        if score >= 80:
            reasons.append("高质量匹配")
        elif score >= 60:
            reasons.append("良好匹配")
        
        # Check if has official link
        if self._extract_official_link(candidate):
            reasons.append("包含播放链接")
        
        return " | ".join(reasons) if reasons else "基础匹配"
    
    def _source_finding_phase(self, discovered_songs: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find official sources for discovered songs"""
        if not self.brave_search or not discovered_songs:
            return []
        
        print("🎵 [Source Finding Phase] 开始精准音源匹配...")
        
        final_results = []
        
        for i, song_info in enumerate(discovered_songs):
            try:
                # Optimize search format
                artist = song_info["artist"].strip()
                song = song_info["song"].strip()
                
                # Try multiple search formats
                search_formats = [
                    f"site:youtube.com {artist} {song}",
                    f"{artist} {song} official audio",
                    f'"{artist}" - "{song}" official'
                ]
                
                validated_info = None
                
                for search_format in search_formats:
                    print(f"🔍 搜索音源 ({i+1}/{len(discovered_songs)}): {search_format}")
                    
                    # Add delay for API rate limiting
                    if i > 0:
                        time.sleep(1.5)
                    
                    try:
                        # Search for official sources
                        source_results = self.brave_search.run(search_format, count=5)
                        
                        # Debug logging
                        print(f"📝 [调试日志] 搜索词: {search_format}")
                        print(f"📝 [调试日志] 返回结果前200字符: {source_results[:200]}...")
                        
                        # AI validation
                        validated_info = self._validate_music_source(source_results, song_info, context)
                        
                        if validated_info:
                            break  # Found valid link, break from search format loop
                            
                    except Exception as search_error:
                        print(f"⚠️  搜索格式 '{search_format}' 失败: {search_error}")
                        continue
                
                if validated_info:
                    final_results.append(validated_info)
                    print(f"✅ 找到音源: {song_info['song']} - {song_info['artist']}")
                else:
                    # Add song info even without source link for frontend display
                    final_results.append({
                        **song_info,
                        'official_link': None,
                        'platform': 'Unknown',
                        'source_title': '',
                        'match_reason': '找到歌曲信息但无可用音源链接',
                        'source': 'discovery',
                        'duration_validated': False
                    })
                    print(f"⚠️  添加无音源歌曲: {song_info['song']} - {song_info['artist']}")
                    print(f"📝 [调试日志] 尝试的所有搜索格式都未成功")
                    
            except Exception as e:
                print(f"⚠️  音源搜索失败 '{song_info['song']}': {e}")
        
        return final_results
    
    def _validate_music_source(self, search_results: str, song_info: Dict[str, Any], context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Validate music source using enhanced AI with regional and content analysis"""
        # Check if it's instrumental music
        instruments = context.get('instruments', '') if context else ''
        is_instrumental = instruments or any(word in song_info.get('song', '').lower() + ' ' + song_info.get('artist', '').lower() 
                                           for word in ['piano', 'violin', 'guitar', 'saxophone', 'trumpet', 'cello', 'flute', 'drums'])
        
        try:
            if is_instrumental:
                validation_prompt = get_instrumental_validation_prompt(song_info, search_results)
            else:
                validation_prompt = get_popular_music_validation_prompt(song_info, search_results)
            
            response = self.model_manager.invoke_text(validation_prompt)
            print(f"📝 [AI验证] 增强响应: {response[:200]}...")
            
            # Parse validation result
            if response.strip().lower() in ['null', '{}', '[]', 'none']:
                return None
            
            # Try to parse enhanced JSON response
            try:
                validated = json.loads(response.strip())
                if validated and validated.get('link'):
                    match_reason = validated.get('match_reason', '找到匹配的音源')
                    
                    # 增强的返回结构，包含AI分析结果
                    enhanced_result = {
                        **song_info,
                        'official_link': validated['link'],
                        'platform': validated.get('platform', 'Unknown'),
                        'source_title': validated.get('title', ''),
                        'match_reason': match_reason,
                        'source': 'web',
                        'duration_validated': True,
                        # 新增AI分析字段
                        'content_type': validated.get('content_type', 'Unknown'),
                        'channel_authority': validated.get('channel_authority', 'Unknown'),
                        'region_match': validated.get('region_match', True),
                        'officialness_score': validated.get('officialness_score', 50),
                        'ai_enhanced': True
                    }
                    
                    print(f"🎯 [增强验证] 内容类型: {validated.get('content_type', 'Unknown')}")
                    print(f"🎯 [增强验证] 频道权威: {validated.get('channel_authority', 'Unknown')}")
                    print(f"🎯 [增强验证] 地域匹配: {validated.get('region_match', True)}")
                    print(f"🎯 [增强验证] 官方度: {validated.get('officialness_score', 50)}")
                    
                    return enhanced_result
                    
            except json.JSONDecodeError:
                print(f"📝 [AI验证] JSON解析失败，响应: {response[:100]}...")
                return None
            
            return None
            
        except Exception as e:
            print(f"⚠️  [AI验证] 增强验证失败: {e}")
            print(f"📝 [调试日志] 验证过程出错，原始搜索结果: {search_results[:300]}...")
            return None
