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
            # Find sources for songs
            candidate_results = self._source_finding_phase(discovered_songs, context)
            print(f"🎯 [Source Finding] 找到 {len(candidate_results)} 个候选结果")
            
            # Apply hard filtering
            filtered_results = self._apply_hard_filters(candidate_results, context)
            print(f"🛡️ [Hard Filter] 过滤后剩余 {len(filtered_results)} 个结果")
            
            # Rank by officialness and quality
            final_results = self._rank_by_officialness(filtered_results, context)
            print(f"⭐ [Ranking] 最终排序 {len(final_results)} 个结果")
            
            context['found_songs'] = final_results
            
            if final_results:
                print(f"✅ [决策] 选择了 {len(final_results)} 首高质量歌曲")
            else:
                print("❌ [决策] 硬过滤后没有符合要求的歌曲")
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
