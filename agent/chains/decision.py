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
        """Apply hard code-level filtering to remove unwanted content"""
        origin_region = context.get('origin_region', 'unknown')
        vocal_type = context.get('vocal_type', 'unknown')
        is_specific = context.get('is_specific', False)
        
        # Define filter keywords
        EXCLUDE_KEYWORDS = [
            'cover', 'reaction', 'tutorial', 'how to', 'lesson',
            'remix', 'mashup', 'nightcore', 'slowed', 'reverb',
            'live performance', 'concert', 'stage', 'fancam',
            'karaoke', 'instrumental version', 'backing track'
        ]
        
        # Live performance is only excluded if not specifically requested
        LIVE_KEYWORDS = ['live', 'concert', 'performance', '演唱会', 'ライブ', '콘서트']
        
        # Language validation keywords by region
        REGION_LANGUAGES = {
            'Japan': ['japanese', 'jpop', 'j-pop', '日本', 'japan', 'ジャニ'],
            'Korea': ['korean', 'kpop', 'k-pop', '韩国', 'korea', '한국'],
            'Greater China': ['chinese', 'cpop', 'c-pop', 'mandarin', 'cantonese', '中文', '华语', '粤语']
        }
        
        filtered = []
        for candidate in candidates:
            title = candidate.get('song', '').lower()
            artist = candidate.get('artist', '').lower()
            context_text = candidate.get('context', '').lower()
            full_text = f"{title} {artist} {context_text}"
            
            # Track filtering reasons
            filter_reasons = []
            
            # 1. Hard exclude keywords (unless specifically requested)
            excluded = False
            for keyword in EXCLUDE_KEYWORDS:
                if keyword in full_text:
                    if keyword in LIVE_KEYWORDS and vocal_type == 'live':
                        continue  # Allow live if specifically requested
                    filter_reasons.append(f"contains_{keyword}")
                    excluded = True
                    break
            
            if excluded:
                print(f"🛡️ [过滤] {title} by {artist} - 原因: {filter_reasons}")
                continue
            
            # 2. Language/Region validation
            if origin_region in REGION_LANGUAGES and is_specific:
                expected_langs = REGION_LANGUAGES[origin_region]
                has_correct_lang = any(lang in full_text for lang in expected_langs)
                
                # Check for wrong region indicators
                wrong_regions = []
                for region, langs in REGION_LANGUAGES.items():
                    if region != origin_region:
                        if any(lang in full_text for lang in langs):
                            wrong_regions.append(region)
                
                if wrong_regions and not has_correct_lang:
                    filter_reasons.append(f"wrong_region_{wrong_regions[0]}")
                    print(f"🛡️ [地域过滤] {title} - 期望: {origin_region}, 检测到: {wrong_regions}")
                    continue
            
            # 3. Quality scoring
            quality_score = self._calculate_quality_score(candidate, full_text)
            candidate['quality_score'] = quality_score
            candidate['filter_reasons'] = filter_reasons
            
            filtered.append(candidate)
        
        return filtered
    
    def _calculate_quality_score(self, candidate: Dict[str, Any], full_text: str) -> float:
        """Calculate quality score for ranking"""
        score = 50.0  # Base score
        
        # Official channel indicators (high priority)
        OFFICIAL_INDICATORS = ['official', 'vevo', 'topic', 'records', 'music', 'entertainment']
        for indicator in OFFICIAL_INDICATORS:
            if indicator in full_text:
                score += 30
                break
        
        # High-quality source indicators
        QUALITY_INDICATORS = ['hd', 'hq', 'high quality', 'official mv', 'music video']
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
            search_query = f"{artist} {song} official audio"
            
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
        """Validate music source using AI"""
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
            print(f"📝 [调试日志] AI验证响应: {response[:200]}...")
            
            # Parse validation result
            if response.strip().lower() in ['null', '{}', '[]', 'none']:
                return None
            
            # Try to parse JSON response
            try:
                validated = json.loads(response.strip())
                if validated and validated.get('link'):
                    match_reason = validated.get('match_reason', '找到匹配的音源')
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
            except json.JSONDecodeError:
                print(f"📝 [调试日志] JSON解析失败，响应: {response[:100]}...")
                return None
            
            return None
            
        except Exception as e:
            print(f"⚠️  音源验证失败: {e}")
            print(f"📝 [调试日志] 验证过程出错，原始搜索结果: {search_results[:300]}...")
            return None
