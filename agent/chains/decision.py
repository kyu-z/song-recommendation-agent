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
        # In-memory caches to reduce repeated network/LLM work within a server process
        # (artist,song) -> extracted youtube candidates
        self._youtube_candidate_cache: Dict[str, List[Dict[str, Any]]] = {}
        # youtube_url -> ai analysis result
        self._ai_analysis_cache: Dict[str, Dict[str, Any]] = {}
    
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
        songs_without_links = []
        allow_no_link = bool(context.get("allow_no_link", False))
        
        for candidate in candidates:
            # 如果没有YouTube链接：默认不返回（避免慢且不稳定的“无音源推荐”）
            if not candidate.get('youtube_url'):
                if allow_no_link:
                    candidate['quality_score'] = 25
                    candidate['preserved_without_link'] = True
                    candidate['context'] = candidate.get('context') or "歌曲信息已识别，但暂未找到可用的官方播放链接"
                    songs_without_links.append(candidate)
                    print(f"✅ [保留无链接] {candidate.get('song', 'N/A')} by {candidate.get('artist', 'N/A')}")
                continue
            
            # 有YouTube链接的进行正常硬过滤
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
                # 特殊处理：Love Live! 是作品名，不应该被过滤
                if 'love live' in full_text.lower():
                    # 跳过live关键词检测
                    pass
                else:
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
        
        # 合并有链接过滤后的和无链接保留的
        hard_filtered.extend(songs_without_links)
        
        print(f"🛡️ [硬过滤] 剩余 {len(hard_filtered)}/{len(candidates)} 个候选")
        print(f"   - 有链接通过过滤: {len(hard_filtered) - len(songs_without_links)}")
        print(f"   - 无链接直接保留: {len(songs_without_links)}")
        
        # 2. AI语义识别阶段 - 批量处理节约成本
        if not hard_filtered:
            return []
        
        ai_validated = self._ai_semantic_validation(hard_filtered, context)
        print(f"🤖 [AI验证] 最终通过 {len(ai_validated)} 个候选")
        
        return ai_validated
    
    def _ai_semantic_validation(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        批量校验 + 纠错闸门（严格模式优先真歌）：
        - 核心输出：exists_for_artist / confidence / canonical_song / canonical_artist / official_link
        - 严格策略：宁可少返回，也不输出错配/不存在歌曲
        """
        origin_region = context.get('origin_region', 'unknown')
        search_goal = context.get('search_goal', '')
        strict_true_only = bool(context.get("strict_true_only", True))
        min_confidence = float(context.get("min_confidence", 0.78))

        # 1) 先把无需验证/无链接的直接保留
        preserved: List[Dict[str, Any]] = []
        to_validate: List[Dict[str, Any]] = []

        for candidate in candidates:
            if candidate.get('preserved_without_link'):
                preserved.append(candidate)
                continue

            youtube_url = (candidate.get('youtube_url') or '').strip()
            if youtube_url and youtube_url in self._ai_analysis_cache:
                candidate['_cached_ai_analysis'] = self._ai_analysis_cache[youtube_url]
            to_validate.append(candidate)

        if not to_validate:
            for c in preserved:
                print(f"✅ [跳过AI验证] {c.get('song', 'N/A')} - 无链接歌曲直接保留")
            return preserved

        # 2) 组装 batch 任务（跳过已缓存的 URL）
        batch_items: List[Dict[str, Any]] = []
        item_map: List[Dict[str, Any]] = []  # keep references aligned by index

        for candidate in to_validate:
            youtube_url = (candidate.get('youtube_url') or '').strip()
            if candidate.get('_cached_ai_analysis'):
                continue
            batch_items.append({
                "song": candidate.get("song", ""),
                "artist": candidate.get("artist", ""),
                "youtube_title": candidate.get("youtube_title", ""),
                "youtube_url": youtube_url,
                "source_url": candidate.get("source_url", "") or "",
                "evidence_quote": candidate.get("evidence_quote", "") or candidate.get("context", "") or "",
            })
            item_map.append(candidate)

        batch_results: List[Optional[Dict[str, Any]]] = []
        if batch_items:
            batch_results = self._invoke_ai_verify_batch(
                batch_items=batch_items,
                origin_region=origin_region,
                search_goal=search_goal
            )
            # Write-through cache
            for item, analysis in zip(batch_items, batch_results):
                url = (item.get("youtube_url") or "").strip()
                if url and isinstance(analysis, dict):
                    self._ai_analysis_cache[url] = analysis

        # 3) 将分析结果合并回 candidates，并应用严格过滤策略
        validated_candidates: List[Dict[str, Any]] = []

        # Apply for items that came from batch call
        batch_iter_idx = 0
        for candidate in to_validate:
            try:
                youtube_url = (candidate.get('youtube_url') or '').strip()
                ai_analysis = candidate.pop('_cached_ai_analysis', None)

                if ai_analysis is None and batch_items:
                    # Candidate might be part of batch (in order). We locate by pointer list.
                    # Simpler and stable: if this candidate equals item_map[batch_iter_idx], consume one.
                    if batch_iter_idx < len(item_map) and candidate is item_map[batch_iter_idx]:
                        ai_analysis = batch_results[batch_iter_idx] if batch_iter_idx < len(batch_results) else None
                        batch_iter_idx += 1

                if isinstance(ai_analysis, dict):
                    # Strict verification gate
                    exists_for_artist = bool(ai_analysis.get("exists_for_artist", True))
                    confidence = ai_analysis.get("confidence", 0.0)
                    try:
                        confidence = float(confidence)
                    except Exception:
                        confidence = 0.0

                    canonical_song = (ai_analysis.get("canonical_song") or candidate.get("song") or "").strip()
                    canonical_artist = (ai_analysis.get("canonical_artist") or candidate.get("artist") or "").strip()

                    # Prefer verifier-provided official_link; otherwise keep current youtube_url
                    official_link = (ai_analysis.get("official_link") or ai_analysis.get("youtube_url") or candidate.get("youtube_url") or "").strip()

                    if strict_true_only:
                        if (not exists_for_artist) or (confidence < min_confidence) or (not official_link):
                            # Fail closed in strict mode
                            continue

                    enhanced_candidate = {
                        **candidate,
                        "song": canonical_song or candidate.get("song", ""),
                        "artist": canonical_artist or candidate.get("artist", ""),
                        "exists_for_artist": exists_for_artist,
                        "confidence": confidence,
                        "official_link": official_link or None,
                        'ai_verified': True,
                        'content_type': ai_analysis.get('content_type', 'unknown'),
                        'officialness_score': ai_analysis.get('officialness_score', 50),
                        'region_match': ai_analysis.get('region_match', True),
                        'channel_authority': ai_analysis.get('channel_authority', 'unknown'),
                        'ai_quality_score': ai_analysis.get('quality_score', 50),
                        # Optional: a short explanation to display as context
                        'explanation': ai_analysis.get('reject_reason') or ai_analysis.get('why_match') or candidate.get('explanation')
                    }

                    final_score = self._calculate_ai_enhanced_quality_score(enhanced_candidate)
                    enhanced_candidate['quality_score'] = final_score

                    # If we got a useful short explanation, use it as context shown to users
                    if enhanced_candidate.get('explanation') and not enhanced_candidate.get('context'):
                        enhanced_candidate['context'] = enhanced_candidate['explanation']

                    validated_candidates.append(enhanced_candidate)
                else:
                    base_score = self._calculate_basic_quality_score(candidate)
                    candidate['quality_score'] = base_score
                    candidate['ai_verified'] = False
                    if not strict_true_only:
                        validated_candidates.append(candidate)
            except Exception as e:
                print(f"❌ [AI验证] 验证失败: {e}")
                base_score = self._calculate_basic_quality_score(candidate)
                candidate['quality_score'] = base_score
                candidate['ai_verified'] = False
                if not strict_true_only:
                    validated_candidates.append(candidate)

        # Finally add preserved no-link candidates only in non-strict mode
        if not strict_true_only:
            for c in preserved:
                print(f"✅ [跳过AI验证] {c.get('song', 'N/A')} - 无链接歌曲直接保留")
            validated_candidates.extend(preserved)

        return validated_candidates

    def _parse_ai_json(self, response: str) -> Optional[Any]:
        """Parse JSON response, handling common markdown fences."""
        if not response or not response.strip():
            return None
        cleaned = response.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()
        elif cleaned.startswith('```'):
            cleaned = cleaned.replace('```', '').strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️  [AI分析] JSON解析失败: {str(e)}")
            print(f"📝 [原始响应] {response[:200]}...")
            return None

    def _invoke_ai_verify_batch(
        self,
        batch_items: List[Dict[str, Any]],
        origin_region: str,
        search_goal: str
    ) -> List[Optional[Dict[str, Any]]]:
        """调用AI进行批量“存在性+错配校验+纠错”（单次 LLM 往返）。"""
        try:
            prompt = self._build_batch_verify_prompt(
                batch_items=batch_items,
                origin_region=origin_region,
                search_goal=search_goal
            )
            response = self.model_manager.invoke_text(prompt)
            parsed = self._parse_ai_json(response)

            # Expected: list aligned with input order
            if isinstance(parsed, dict) and "results" in parsed:
                parsed = parsed["results"]

            if not isinstance(parsed, list):
                return [None] * len(batch_items)

            # Normalize length
            results: List[Optional[Dict[str, Any]]] = []
            for i in range(len(batch_items)):
                item = parsed[i] if i < len(parsed) else None
                results.append(item if isinstance(item, dict) else None)
            return results
        except Exception as e:
            print(f"❌ [AI分析] 批量调用失败: {e}")
            return [None] * len(batch_items)

    def _build_batch_verify_prompt(
        self,
        batch_items: List[Dict[str, Any]],
        origin_region: str,
        search_goal: str
    ) -> str:
        """构建批量校验提示词（要求严格 JSON 数组输出，顺序与输入一致）。"""
        items_json = json.dumps(batch_items, ensure_ascii=False)
        return f"""你是严格的音乐事实核查员。你只能使用我提供的证据文本与候选链接来判断，不允许凭空补全或“凭常识猜测”。

期望地域：{origin_region}
用户搜索目标：{search_goal}

候选列表（JSON数组，每个元素包含 song/artist/source_url/evidence_quote/youtube_title/youtube_url）：
{items_json}

任务（对每个候选逐条输出结果，顺序必须一致）：\n
1) **存在性与错配检查**：判断“song 是否确实存在、并且确实是该 artist 的作品”。\n
2) **证据一致性**：evidence_quote 必须能支撑 song+artist 配对；如果证据不足或冲突，判 false。\n
3) **纠错**：如果你能在证据中明确看到更正确的歌名/艺人（例如拼写/别名/括号副标题），输出 canonical_*；否则保持原样。\n
4) **链接严禁捏造**：official_link 只能从给定 youtube_url 原样复制，或设为 null。\n
\n
输出字段：\n
- exists_for_artist: true/false\n
- canonical_song: string\n
- canonical_artist: string\n
- confidence: 0.0-1.0（只基于证据一致性与链接匹配程度）\n
- official_link: string|null（只能等于输入 youtube_url 或 null）\n
- content_type: \"Official MV\"|\"Lyric Video\"|\"Audio Only\"|\"Live Performance\"|\"Topic Channel\"|\"Unknown\"\n
- channel_authority: \"Official Label\"|\"Topic Channel\"|\"Artist Official\"|\"Unofficial\"|\"Unknown\"\n
- officialness_score: 0-100\n
- quality_score: 0-100\n
- why_match: 一句话说明为什么匹配用户意图（具体到风格/年代/场景）\n
- reject_reason: 若 exists_for_artist=false，用一句话说明错误原因（例如“song-title 属于另一位艺人/证据不足/疑似不存在”）\n

返回 **仅** 一个 JSON 数组，数组长度必须与输入候选列表一致，顺序必须一致。不要返回其他文字。"""
    
    def _invoke_ai_content_analysis(self, validation_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用AI进行内容分析"""
        try:
            analysis_prompt = self._build_content_analysis_prompt(validation_context)
            response = self.model_manager.invoke_text(analysis_prompt)

            parsed = self._parse_ai_json(response)
            return parsed if isinstance(parsed, dict) else None
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
        
        # Hard cap to keep latency bounded
        discovered_songs = discovered_songs[:10]
        max_linked_candidates = 8

        for song_info in discovered_songs:
            # Early stop once we already have enough linked candidates
            linked_count = sum(1 for r in results if r.get("youtube_url"))
            if linked_count >= max_linked_candidates:
                break

            artist = song_info.get('artist', '')
            song = song_info.get('song', '')
            
            if not artist or not song:
                continue
                
            print(f"🎵 [自动音源] 搜索: {artist} - {song}")
            
            # Generate official audio search query
            search_query = f"{artist} {song} official"
            cache_key = f"{artist.strip().lower()}|||{song.strip().lower()}"
            
            try:
                # Use Brave Search to find YouTube links
                if self.brave_search:
                    # Cache hit: reuse validated candidates to avoid repeated Brave calls
                    if cache_key in self._youtube_candidate_cache:
                        validated_candidates = self._youtube_candidate_cache[cache_key]
                    else:
                        # Prefer structured results to avoid brittle regex title extraction
                        structured = None
                        if hasattr(self.brave_search, "run_structured"):
                            structured = self.brave_search.run_structured(f"site:youtube.com {search_query}", count=5)
                            if isinstance(structured, str) and ("Too Many Requests" in structured or "429" in structured):
                                print("⚠️  [自动音源] Brave 触发限流(429)，等待后重试一次...")
                                time.sleep(1.5)
                                structured = self.brave_search.run_structured(f"site:youtube.com {search_query}", count=3)

                        if isinstance(structured, list):
                            youtube_candidates = [
                                {"url": r.get("url", ""), "title": r.get("title", ""), "video_id": ""}
                                for r in structured
                                if isinstance(r, dict) and "youtube.com/watch" in (r.get("url", "") or "")
                            ]
                        else:
                            search_results = self.brave_search.run(f"site:youtube.com {search_query}", count=5)
                            # Simple retry on rate limiting
                            if "Too Many Requests" in search_results or "429" in search_results:
                                print("⚠️  [自动音源] Brave 触发限流(429)，等待后重试一次...")
                                time.sleep(1.5)
                                search_results = self.brave_search.run(f"site:youtube.com {search_query}", count=3)
                            youtube_candidates = self._extract_youtube_links(search_results)
                        validated_candidates = self._validate_youtube_sources(youtube_candidates, artist, song)
                        # Cache even empty results to avoid repeated misses
                        self._youtube_candidate_cache[cache_key] = validated_candidates
                    
                    if validated_candidates:
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
                        # No YouTube links found, but preserve the discovered song
                        print(f"⚠️  [自动音源] {artist} - {song}: 未找到YouTube链接，保留歌曲信息")
                        results.append({
                            **song_info,
                            'youtube_url': None,
                            'youtube_title': '',
                            'source_type': 'no_youtube_found',
                            'validation_score': 0
                        })
                else:
                    print("⚠️  Brave Search not available for source finding")
                    # Add song without YouTube link
                    results.append({
                        **song_info,
                        'youtube_url': None,
                        'youtube_title': '',
                        'source_type': 'no_source',
                        'validation_score': 0
                    })
                
            except Exception as e:
                print(f"⚠️  [自动音源] 搜索失败 {artist} - {song}: {e}")
                results.append({
                    **song_info,
                    'youtube_url': None,
                    'youtube_title': '',
                    'source_type': 'search_failed',
                    'validation_score': 0
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
            
            # Prefer AI-enhanced quality score, fall back to validation score
            candidates.sort(
                key=lambda x: (x.get('quality_score', 0), x.get('validation_score', 0)),
                reverse=True
            )
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
    
    def _extract_official_link(self, candidate: Dict[str, Any]) -> Optional[str]:
        """提取官方链接"""
        # Check various possible link fields
        possible_fields = ['youtube_url', 'official_link', 'url', 'link']
        
        for field in possible_fields:
            link = candidate.get(field)
            if link and isinstance(link, str) and link.strip():
                return link.strip()
        
        return None  # 返回None而不是空字符串
    
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
