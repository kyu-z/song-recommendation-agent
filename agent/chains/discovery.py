"""
Discovery Chain - Stage 2: Music discovery and extraction with two-stage processing
"""
import asyncio
import time
import re
import json
import unicodedata
import requests
from typing import Dict, Any, List, Set, Optional, Tuple
from ..prompts.clue_extraction import get_clue_extraction_prompt
from ..prompts.single_verification import get_single_clue_verification_prompt


class DiscoveryChain:
    """Handles music discovery through web search and extraction"""

    # Max distance (chars) between song and artist substrings in normalized evidence for relaxed tier
    _EVIDENCE_COOCCUR_WINDOW = 420
    
    def __init__(self, brave_search, model_manager):
        self.brave_search = brave_search
        self.model_manager = model_manager

    def _normalize_for_evidence_match(self, text: str) -> str:
        """Normalize text for substring / co-occurrence checks (NFKC, quotes, whitespace)."""
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", text)
        t = re.sub(r"[\u200b-\u200d\ufeff]", "", t)
        for a, b in (
            ("\u201c", '"'),
            ("\u201d", '"'),
            ("\u2018", "'"),
            ("\u2019", "'"),
            ("\u2013", "-"),
            ("\u2014", "-"),
        ):
            t = t.replace(a, b)
        t = t.lower()
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _co_occurs_within_window(self, haystack: str, a: str, b: str, window: int) -> bool:
        """Return True if some occurrence of `a` lies within `window` chars of some occurrence of `b`."""
        if not a or not b or len(a) < 2 or len(b) < 2:
            return False
        pos = 0
        while True:
            i = haystack.find(a, pos)
            if i == -1:
                break
            start = max(0, i - window)
            end = min(len(haystack), i + len(a) + window)
            if b in haystack[start:end]:
                return True
            pos = i + 1
        pos = 0
        while True:
            i = haystack.find(b, pos)
            if i == -1:
                break
            start = max(0, i - window)
            end = min(len(haystack), i + len(b) + window)
            if a in haystack[start:end]:
                return True
            pos = i + 1
        return False

    def _snippet_containing_both_in_source(
        self,
        combined_results: str,
        song: str,
        artist: str,
        window: int,
        max_len: int = 280,
    ) -> str:
        """Extract a slice from original evidence where song and artist co-occur within `window` (case-insensitive)."""
        cl = combined_results.lower()
        sl = song.strip().lower()
        al = artist.strip().lower()
        if not sl or not al:
            return ""
        pos = 0
        while True:
            i = cl.find(sl, pos)
            if i == -1:
                break
            start = max(0, i - window)
            end = min(len(cl), i + len(sl) + window)
            segment = cl[start:end]
            if al in segment:
                raw = combined_results[start:end].strip()
                if len(raw) > max_len:
                    raw = raw[: max_len - 3] + "..."
                return raw
            pos = i + 1
        return ""
    
    async def search(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Two-stage discovery: 1) Authority links, 2) Content parsing
        
        Args:
            context: Context from perception stage
            
        Returns:
            Updated context with found songs
        """
        if not self.brave_search:
            print("⚠️  Brave Search not available, skipping discovery phase")
            return context
        
        try:
            print("🔍 [Two-Stage Discovery] 开始两段式音乐发现...")
            
            # Stage 1: Find authority links (Wikipedia/Discogs/Reddit/etc.)
            authority_links = self._find_authority_links(context)
            
            # Stage 2: Evidence collection (Brave + WebReader) + candidate extraction
            all_search_results: List[str] = []
            
            # Keep a small number of Brave queries to bound latency
            general_queries = self._generate_discovery_queries(context)[:2]

            for i, query in enumerate(general_queries):
                try:
                    print(f"🔍 搜索 ({i+1}/{len(general_queries)}): {query}")
                    results = await asyncio.to_thread(self.brave_search.run, query, 5)
                    all_search_results.append(results)
                except Exception as e:
                    print(f"⚠️  Search failed for '{query}': {e}")

            # Fetch a capped number of authority pages via WebReader for stronger evidence
            if authority_links:
                web_content = self._fetch_authority_web_content(authority_links)
                if web_content:
                    all_search_results.extend(web_content)
                    print(f"🌐 [WebReader] 成功抓取 {len(web_content)} 个网页内容")
            
            print(f"🔍 [调试] 总共收集到 {len(all_search_results)} 个搜索结果")
            if not all_search_results:
                print("🔍 [调试] 没有任何搜索结果，提前返回")
                return context
            
            # Extract candidates from evidence sources (async)
            discovered_songs = await self._extract_songs_from_text(all_search_results, context)
            print(f"✅ [Discovery] 发现 {len(discovered_songs)} 首候选歌曲")
            
            context['found_songs'] = discovered_songs
            return context
            
        except Exception as e:
            print(f"❌ [Discovery Phase] 失败: {e}")
            return context

    def _discovery_search_query(self, context: Dict[str, Any]) -> str:
        """
        Normalize perception text for Brave/Wikipedia: 'gathering' matches wrong bands;
        'urban' matches Keith Urban. Optionally append vision cultural_tags (LGBTQ+, etc.).
        """
        refined_query = (context.get("refined_query") or "").strip()
        search_goal = (context.get("search_goal") or "").strip()
        native_name = context.get("native_name")
        search_strategy = context.get("search_strategy", "international")

        if search_strategy in ["localized", "hybrid"] and native_name:
            return (native_name or "").strip()

        base = refined_query or search_goal
        if not base:
            return ""

        s = base
        s = re.sub(r"\bgathering\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\burban\b", "city", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()

        tags = context.get("cultural_tags") or []
        if isinstance(tags, list):
            q_compact = re.sub(r"\s+", "", s.lower()).replace("+", "")
            for t in tags[:5]:
                if not isinstance(t, str):
                    continue
                t = t.strip()
                if not t:
                    continue
                tl = t.lower()
                if not any(
                    k in tl
                    for k in ("lgbt", "queer", "pride", "gay", "lesbian", "trans", "bisex")
                ):
                    continue
                t_compact = re.sub(r"\s+", "", tl).replace("+", "")
                if t_compact and t_compact in q_compact:
                    continue
                s = f"{s} {t}".strip()

        s = re.sub(r"\s+", " ", s).strip()
        if len(s) < 3:
            return base
        if s != base:
            print(f"🎯 [discovery_query] 检索词归一: {base!r} -> {s!r}")
        return s
    
    def _generate_discovery_queries(self, context: Dict[str, Any]) -> List[str]:
        """Generate region-aware discovery queries with native names"""
        refined_query = context.get('refined_query', '')
        search_goal = context.get('search_goal', '')
        native_name = context.get('native_name')
        origin_region = context.get('origin_region', 'unknown')
        search_strategy = context.get('search_strategy', 'international')
        is_specific = context.get('is_specific', False)
        vocal_type = context.get('vocal_type', 'unknown')
        music_type = context.get('music_type', 'unknown')
        
        # Choose primary search term based on strategy
        if search_strategy in ['localized', 'hybrid'] and native_name:
            primary_query = native_name
            secondary_query = refined_query
        else:
            primary_query = self._discovery_search_query(context) or refined_query or search_goal
            secondary_query = native_name
        
        if not primary_query:
            return ["atmospheric music recommendations reddit"]
        
        print(f"🎯 [智能搜索] 主查询: {primary_query}, 辅查询: {secondary_query}")
        print(f"🎯 [智能搜索] 地域: {origin_region}, 策略: {search_strategy}")
        
        queries = []
        
        # Region-specific search templates
        if origin_region == 'Japan':
            if is_specific and native_name:
                queries.extend([
                    f"{native_name} 人気曲",
                    f"{native_name} ベストアルバム",
                    f"{primary_query} essential jpop"
                ])
            else:
                queries.extend([
                    f"{primary_query} jpop おすすめ",
                    f"best {primary_query} japanese music",
                    f"{primary_query} 必听歌曲"
                ])
                
        elif origin_region == 'Korea':
            if is_specific and native_name:
                queries.extend([
                    f"{native_name} 인기곡",
                    f"{native_name} 베스트",
                    f"{primary_query} kpop hits"
                ])
            else:
                queries.extend([
                    f"{primary_query} kpop 추천",
                    f"best {primary_query} korean music",
                    f"{primary_query} must listen"
                ])
                
        elif origin_region == 'Greater China':
            if is_specific and native_name:
                queries.extend([
                    f"{native_name} 必听歌曲",
                    f"{native_name} 热门歌曲",
                    f"{primary_query} cpop songs"
                ])
            else:
                queries.extend([
                    f"{primary_query} 华语音乐推荐",
                    f"best {primary_query} chinese music",
                    f"{primary_query} 经典歌曲"
                ])
        else:
            # International/Western music - use original logic
            if is_specific:
                queries = [
                    primary_query,
                    f"{primary_query} playlist",
                    f"{primary_query} collection"
                ]
            else:
                if music_type == 'classical':
                    queries = [
                        f"best {primary_query} pieces",
                        f"{primary_query} masterpieces",
                        f"essential {primary_query} repertoire"
                    ]
                elif music_type == 'ambient':
                    queries = [
                        f"{primary_query} playlists",
                        f"atmospheric {primary_query}",
                        f"{primary_query} for relaxation"
                    ]
                elif vocal_type == 'instrumental':
                    queries = [
                        f"{primary_query} instrumental pieces",
                        f"best {primary_query} no vocals",
                        f"{primary_query} background music"
                    ]
                else:
                    queries = [
                        f"{primary_query} essential songs",
                        f"best {primary_query} tracks",
                        f"must hear {primary_query} playlist"
                    ]
        
        # Add hybrid query if we have both names
        if search_strategy == 'hybrid' and secondary_query and secondary_query != primary_query:
            queries.append(f"{secondary_query} {primary_query} best songs")
        
        # Special handling for year-based queries
        if self._contains_year(primary_query):
            year_enhanced_queries = self._generate_year_enhanced_queries(primary_query, origin_region)
            queries.extend(year_enhanced_queries)
        
        print(f"🎯 [地域化模板] 生成 {len(queries)} 个查询")
        return queries[:4]  # Increased limit for year queries
    
    def _contains_year(self, query: str) -> bool:
        """Check if query contains a year"""
        import re
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        return bool(re.search(year_pattern, query))
    
    def _generate_year_enhanced_queries(self, primary_query: str, origin_region: str) -> List[str]:
        """Generate enhanced queries for year-specific searches"""
        import re
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        year_match = re.search(year_pattern, primary_query)
        
        if not year_match:
            return []
            
        year = year_match.group(1)
        enhanced_queries = []
        
        if origin_region == 'Korea':
            enhanced_queries.extend([
                f"site:wikipedia.org K-pop {year} chart hits",
                f"site:billboard.com Korea {year} music chart",
                f"Melon chart {year} 연말결산 year-end"
            ])
        elif origin_region == 'Japan':
            enhanced_queries.extend([
                f"site:wikipedia.org J-pop {year} Oricon chart",
                f"site:oricon.co.jp {year} 年間ランキング",
                f"日本 {year} 人気曲 年末チャート"
            ])
        elif origin_region == 'Greater China':
            enhanced_queries.extend([
                f"site:wikipedia.org C-pop {year} chart Chinese music",
                f"{year} 年度華語歌曲排行榜",
                f"KKBOX {year} 年度百大單曲"
            ])
        else:
            enhanced_queries.extend([
                f"site:wikipedia.org {year} in music Billboard chart",
                f"site:billboard.com year-end {year} Hot 100",
                f"best songs {year} year-end chart hits"
            ])
        
        print(f"🎯 [年份增强] 为 {year} 年生成 {len(enhanced_queries)} 个专门查询")
        return enhanced_queries
    
    def _find_authority_links(self, context: Dict[str, Any]) -> List[str]:
        """Stage 1: Find diverse information sources (not limited to official platforms)"""
        refined_query = context.get('refined_query', '')
        search_goal = context.get('search_goal', '')
        native_name = context.get('native_name')
        origin_region = context.get('origin_region', 'unknown')
        search_strategy = context.get('search_strategy', 'international')
        
        print(f"🎯 [多源信息搜索] 地域: {origin_region}, 策略: {search_strategy}")
        
        # Build diverse information source queries
        authority_queries = []
        
        # Core query with native name if available; else same normalization as general discovery
        if native_name and search_strategy in ['localized', 'hybrid']:
            base_query = native_name
        else:
            base_query = self._discovery_search_query(context) or refined_query or search_goal
        
        # Check if this is a year-specific or genre-specific query
        contains_year = self._contains_year(base_query)
        
        if contains_year:
            # For year-specific queries, prioritize Wikipedia and community sources
            import re
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', base_query)
            year = year_match.group(1) if year_match else ""
            
            authority_queries.extend([
                f"site:wikipedia.org list of {year} hit songs {origin_region}",
                f"site:reddit.com best songs of {year} {base_query.replace(year, '').strip()}",
                f"list of {year} hit songs {base_query.replace(year, '').strip()}",
                f"best songs of {year} according to reddit"
            ])
        else:
            # For general queries, use diverse sources
            authority_queries.extend([
                f"site:wikipedia.org {base_query} discography",
                f"site:reddit.com {base_query} recommendation",
                f"list of {base_query} hit songs",
                f"best {base_query} according to reddit"
            ])
        
        # Region-specific community and information sites
        if origin_region == 'Japan':
            authority_queries.extend([
                f"site:reddit.com jpop {base_query}",
                f"site:natalie.mu {base_query}",
                f"日本 {base_query} 人気曲 まとめ"
            ])
        elif origin_region == 'Korea':
            authority_queries.extend([
                f"site:soompi.com {base_query}",
                f"site:allkpop.com {base_query}",
                f"site:reddit.com kpop {base_query}"
            ])
        elif origin_region == 'Greater China':
            authority_queries.extend([
                f"site:reddit.com cpop {base_query}",
                f"{base_query} 華語歌曲推薦",
                f"{base_query} 中文歌曲 排行"
            ])
        else:
            authority_queries.extend([
                f"site:reddit.com music {base_query}",
                f"site:pitchfork.com {base_query}",
                f"site:rollingstone.com {base_query}"
            ])
        
        print(f"🎯 [多源查询] {len(authority_queries)} 个信息源查询")
        
        # Execute diverse source searches
        authority_links = []
        # Keep this bounded for latency + rate-limit safety (Brave-only mode).
        for query in authority_queries[:2]:
            try:
                print(f"🔗 [信息搜索]: {query}")
                results = self.brave_search.run(query, count=5)
                # Skip if Brave returned error string (e.g. 429)
                if isinstance(results, str) and results.strip().lower().startswith("search failed"):
                    continue
                links = self._extract_authority_links(results)
                authority_links.extend(links)
            except Exception as e:
                print(f"⚠️  Information search failed: {e}")
        
        print(f"🔗 [信息链接] 找到 {len(authority_links)} 个信息源链接")
        
        # Apply diversity filtering before returning
        diversified_links = self._apply_domain_diversity_filter(authority_links, max_per_domain=2, max_total=8)
        print(f"🎯 [多样性过滤] 过滤后保留 {len(diversified_links)} 个多样化链接")
        
        return diversified_links
    
    def _apply_domain_diversity_filter(self, links: List[str], max_per_domain: int = 2, max_total: int = 8) -> List[str]:
        """Apply diversity filtering to ensure balanced domain representation"""
        from urllib.parse import urlparse
        
        # Group links by domain
        domain_groups = {}
        for link in links:
            try:
                domain = urlparse(link).netloc.lower()
                # Normalize domain (remove www, etc)
                domain = domain.replace('www.', '')
                
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(link)
            except Exception as e:
                print(f"⚠️  [域名解析] 无法解析链接: {link}, 错误: {e}")
                continue
        
        print(f"🎯 [域名统计] 发现 {len(domain_groups)} 个不同域名")
        for domain, links_list in domain_groups.items():
            print(f"   - {domain}: {len(links_list)} 个链接")
        
        # Apply diversity filtering
        diversified_links = []
        
        # Define domain priority for better selection
        priority_domains = [
            'wikipedia.org', 'en.wikipedia.org',  # Reference first
            'reddit.com',  # Community insights
            'billboard.com', 'rollingstone.com',  # Industry authority
            'music.apple.com', 'spotify.com',  # Platform data
            'soompi.com', 'allkpop.com',  # Specialized coverage
            'natalie.mu', 'oricon.co.jp',  # Regional authority
            'genius.com', 'pitchfork.com'  # Music analysis
        ]
        
        # First pass: prioritize important domains
        for priority_domain in priority_domains:
            if len(diversified_links) >= max_total:
                break
                
            for domain, links_list in domain_groups.items():
                if priority_domain in domain and links_list:
                    # Take up to max_per_domain links from this domain
                    selected_count = min(max_per_domain, len(links_list), max_total - len(diversified_links))
                    selected_links = links_list[:selected_count]
                    diversified_links.extend(selected_links)
                    
                    # Remove selected links to avoid duplicates
                    domain_groups[domain] = links_list[selected_count:]
                    
                    print(f"🎯 [优先选择] {domain}: 选择了 {selected_count} 个链接")
                    break
        
        # Second pass: fill remaining slots with other domains
        for domain, links_list in domain_groups.items():
            if len(diversified_links) >= max_total:
                break
                
            if links_list:  # Still has unselected links
                selected_count = min(max_per_domain, len(links_list), max_total - len(diversified_links))
                selected_links = links_list[:selected_count]
                diversified_links.extend(selected_links)
                
                print(f"🎯 [补充选择] {domain}: 选择了 {selected_count} 个链接")
        
        return diversified_links[:max_total]
    
    def _extract_authority_links(self, search_results: str) -> List[str]:
        """Extract diverse information source URLs from search results"""
        information_domains = [
            # Wikipedia & Reference
            'wikipedia.org', 'en.wikipedia.org', 'ko.wikipedia.org', 'ja.wikipedia.org',
            # Community & Fan Sites
            'reddit.com', 'soompi.com', 'allkpop.com', 'asianjunkie.com',
            # Music Industry & News
            'oricon.co.jp', 'natalie.mu', 'melon.com', 'genius.com',
            'musicmatch.com', 'last.fm', 'discogs.com', 'metacritic.com',
            # Music Platforms (for reference info)
            'kkbox.com', 'xiami.com', 'bandcamp.com',
            # Entertainment News
            'variety.com', 'billboard.com', 'rollingstone.com', 'pitchfork.com'
        ]
        
        links = []
        # Skip error responses (e.g. Brave 429 returns "Search failed: ..." with API URL in it)
        if isinstance(search_results, str) and search_results.strip().lower().startswith("search failed"):
            return []
        # Exclude API endpoints (Brave error URLs contain api.search.brave.com)
        excluded_domains = ('api.search.brave.com', 'api.brave.com')
        url_pattern = r'https?://[^\s<>"\']+(?:[^\s<>"\'.,;:])'
        urls = re.findall(url_pattern, search_results)
        
        for url in urls:
            if any(d in url for d in excluded_domains):
                continue
            if any(domain in url for domain in information_domains):
                links.append(url)
        
        return links
    
    def _parse_authority_links(self, authority_links: List[str]) -> List[str]:
        """Stage 2: Parse content from authority links"""
        print(f"🎵 [权威解析] 开始解析 {len(authority_links)} 个权威链接...")
        
        parsed_content = []
        for link in authority_links:
            try:
                # Note: In a real implementation, you'd use a web scraping tool
                # For now, we'll simulate by treating the link as searchable content
                print(f"🎵 [解析]: {link}")
                
                # Simulate authority content extraction
                if 'apple.com' in link:
                    content = f"Apple Music tracklist from {link}"
                elif 'spotify.com' in link:
                    content = f"Spotify playlist content from {link}"
                elif 'wikipedia.org' in link:
                    content = f"Wikipedia discography from {link}"
                else:
                    content = f"Authority content from {link}"
                
                parsed_content.append(content)
                
            except Exception as e:
                print(f"⚠️  Failed to parse {link}: {e}")
        
        print(f"🎵 [权威解析] 成功解析 {len(parsed_content)} 个链接内容")
        return parsed_content
    
    def _fetch_web_content(self, url: str) -> str:
        """Fetch web content using Jina Reader API"""
        try:
            reader_url = f"https://r.jina.ai/{url}"
            print(f"🌐 [WebReader] 抓取: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(reader_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            content = response.text
            print(f"🌐 [WebReader] 成功抓取 {len(content)} 字符")
            return content
            
        except Exception as e:
            print(f"⚠️  [WebReader] 抓取失败 {url}: {e}")
            return ""
    
    def _fetch_authority_web_content(self, authority_links: List[str]) -> List[str]:
        """Fetch web content from diverse information sources - try all authority links"""
        web_contents = []
        max_attempts = min(8, len(authority_links))  # Reasonable limit
        successful_reads = 0
        
        print(f"🌐 [WebReader] 开始从 {len(authority_links)} 个权威链接抓取内容")
        
        for i, link in enumerate(authority_links[:max_attempts]):
            if successful_reads >= 6:  # Stop after 6 successful reads
                break
                
            try:
                print(f"🔗 [{i+1}/{max_attempts}] 尝试抓取: {link}")
                content = self._fetch_web_content(link)
                
                if content and len(content.strip()) > 100:  # Only include substantial content
                    truncated_content = self._truncate_evidence_content(content)
                    web_contents.append(f"=== Web Content from {link} ===\n{truncated_content}")
                    successful_reads += 1
                    print(f"✅ [成功抓取] {len(content)} 字符 from {link}")
                else:
                    print(f"⚠️  [内容不足] 链接返回内容过少: {len(content) if content else 0} 字符")
                    
                # Rate limiting for web requests
                time.sleep(1.0)
                
            except Exception as e:
                print(f"❌ [抓取失败] {link}: {str(e)}")
                continue
        
        print(f"🎯 [抓取总结] 成功抓取 {successful_reads}/{max_attempts} 个链接")
        return web_contents

    def _truncate_evidence_content(self, content: str) -> str:
        """
        Cap per-page evidence size while preserving list-heavy tails (head + tail for long pages).
        """
        max_total = 24000
        head_n = 12000
        tail_n = 12000
        if len(content) <= max_total:
            return content
        head = content[:head_n]
        tail = content[-tail_n:]
        return (
            head
            + "\n\n=== ... [middle omitted for length] ... ===\n\n"
            + tail
        )
    
    def _clean_json_string(self, response: str) -> str:
        """Clean JSON string to remove common AI-generated formatting issues"""
        # Remove code block markers
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        
        # Remove comments and explanatory text
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        
        # Remove trailing commas before closing brackets
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned

    def _repair_clue_json_string(self, json_string: str) -> str:
        """
        Best-effort fixes before json.loads: Wikipedia/Jina often yields Markdown links in
        evidence lines; unescaped quotes in model output also break JSON.
        """
        s = json_string
        # [Label](https://...) -> Label (stops at first ); good enough for Wikipedia
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
        return s

    def _fallback_parse_clue_pairs(self, text: str) -> List[Dict[str, Any]]:
        """
        If the array is not valid JSON, extract song/artist pairs in order of appearance.
        evidence_quote left empty; _filter_by_evidence relaxed tier can still anchor.
        """
        pat = re.compile(
            r'"song"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"artist"\s*:\s*"((?:[^"\\]|\\.)*)"',
            re.DOTALL,
        )
        out: List[Dict[str, Any]] = []
        for m in pat.finditer(text):
            try:
                song = json.loads('"' + m.group(1) + '"')
                artist = json.loads('"' + m.group(2) + '"')
            except json.JSONDecodeError:
                continue
            song = (song or "").strip()
            artist = (artist or "").strip()
            if song and artist:
                out.append(
                    {
                        "song": song,
                        "artist": artist,
                        "source_url": "",
                        "evidence_quote": "",
                    }
                )
        return out
    
    def _aggressive_json_clean(self, json_string: str) -> str:
        """More aggressive JSON cleaning for malformed responses"""
        # Remove ellipsis and continuation marks
        cleaned = re.sub(r'\.\.\.+', '', json_string)
        cleaned = re.sub(r'…+', '', cleaned)
        
        # Remove incomplete objects at the end
        if cleaned.count('{') != cleaned.count('}'):
            # Find last complete object
            brace_count = 0
            last_valid_pos = 0
            for i, char in enumerate(cleaned):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_valid_pos = i + 1
            
            if last_valid_pos > 0:
                cleaned = cleaned[:last_valid_pos] + ']'
        
        # Fix common quote issues
        cleaned = re.sub(r'([{,]\s*\w+):', r'"\1":', cleaned)  # Add quotes to keys
        cleaned = re.sub(r':\s*([^",\[\]{}]+)([,}])', r': "\1"\2', cleaned)  # Add quotes to unquoted values
        
        return cleaned
    
    def _extract_json_manually(self, response: str) -> Optional[str]:
        """Manually extract JSON object from response using pattern matching"""
        # Look for JSON object pattern
        json_patterns = [
            r'\{[^{}]*"song"[^{}]*"artist"[^{}]*\}',  # Simple object with song and artist
            r'\{[^{}]*"artist"[^{}]*"song"[^{}]*\}',  # Reversed order
            r'\{.*?"song".*?"artist".*?\}',  # More permissive
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_candidate = match.group()
                # Basic cleanup
                json_candidate = re.sub(r'\n', ' ', json_candidate)
                json_candidate = re.sub(r'\s+', ' ', json_candidate)
                return json_candidate.strip()
        
        return None
    
    def _build_fallback_json(self, response: str, original_song: str, original_artist: str) -> Optional[Dict[str, Any]]:
        """Build fallback JSON when parsing fails but response seems valid"""
        response_lower = response.lower()
        
        # Check if response indicates the song exists
        if any(word in response_lower for word in ['song', 'track', 'music', 'artist', 'singer']):
            # Try to extract basic info or use original
            fallback = {
                'song': original_song,
                'artist': original_artist,
                'genre': 'Unknown',
                'year': 'Unknown',
                'youtube_link': '',
                'confidence': 0.5  # Lower confidence for fallback
            }
            
            # Try to extract year if present
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', response)
            if year_match:
                fallback['year'] = year_match.group(1)
            
            # Try to extract YouTube link if present
            youtube_match = re.search(r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+', response)
            if youtube_match:
                fallback['youtube_link'] = youtube_match.group()
            
            return fallback
        
        return None
    
    def _clean_search_goal(self, goal: str) -> str:
        """Clean search goal to extract core keywords"""
        unwanted_phrases = [
            ' or ', ' and ', ' music', ' songs', ' tracks',
            ' soundtrack', ' OST', ' theme song', ' opening', ' ending'
        ]
        
        cleaned = goal
        
        # Handle "A or B" cases, prefer the first more specific part
        if ' or ' in cleaned:
            parts = cleaned.split(' or ')
            cleaned = parts[0].strip()
        
        # Remove trailing generic words
        for phrase in unwanted_phrases:
            if cleaned.lower().endswith(phrase.lower()):
                cleaned = cleaned[:-len(phrase)].strip()
        
        # If cleaned too short, use original
        if len(cleaned.strip()) < 3:
            cleaned = goal
            
        return cleaned.strip()
    
    async def _extract_songs_from_text(self, search_results: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Candidate extraction from web search results.
        
        Note: Online path returns *candidates only* (song/artist). Source finding and
        verification are handled downstream in DecisionChain to avoid duplicate work.
        """
        if not search_results:
            return []
        
        # Stage 1: Extract song clues (maximum recall)
        song_clues = await self._extract_song_clues(search_results, context)
        if not song_clues:
            print("Stage 1: No song clues extracted")
            return []
        
        print(f"Stage 1: Extracted {len(song_clues)} song clues")
        # Return candidates only; DecisionChain will find sources and validate/rank.
        candidates: List[Dict[str, Any]] = []
        for clue in song_clues:
            candidates.append({
                "song": clue.get("song", ""),
                "artist": clue.get("artist", ""),
                # Use evidence quote as user-visible context; Decision will add richer explanations later.
                "context": clue.get("evidence_quote", "") or "",
                "source_url": clue.get("source_url", "") or "",
                "evidence_quote": clue.get("evidence_quote", "") or "",
                "source": "discovery"
            })
        return candidates
    
    async def _extract_song_clues(self, web_content: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stage 1: Extract evidence-backed song clues (precision-first)"""
        combined_results = "\n".join(web_content)
        goal = context.get('search_goal', '')
        
        print(f"Clue extraction from {len(combined_results)} characters")
        
        try:
            clue_prompt = get_clue_extraction_prompt(goal, combined_results, context)
            response = await asyncio.to_thread(self.model_manager.invoke_text, clue_prompt)
            
            # Parse clue response
            cleaned_response = self._clean_json_string(response)
            json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
            
            if json_match:
                json_string = json_match.group()
                # Repair truncated or overly long source_url (model sometimes outputs "source_url": "https:\n" breaking JSON)
                # Match "source_url": "https:..." (complete or truncated) and normalize to empty string
                json_string = re.sub(
                    r'"source_url"\s*:\s*"https:[^"]*"?,?\s*',
                    '"source_url": "", ',
                    json_string,
                    flags=re.DOTALL
                )
                json_string = self._repair_clue_json_string(json_string)
                raw_clues: Optional[List[Any]] = None
                try:
                    # Sanitize control characters that break JSON parsing (e.g., raw tabs/newlines in evidence_quote)
                    json_string_sanitized = re.sub(r'[\x00-\x1f\x7f]', ' ', json_string)
                    raw_clues = json.loads(json_string_sanitized)
                except json.JSONDecodeError as e:
                    # Retry with aggressive cleaning + link stripping again
                    try:
                        json_string_sanitized = re.sub(r'[\x00-\x1f\x7f]', ' ', json_string)
                        json_string_sanitized = self._repair_clue_json_string(json_string_sanitized)
                        aggressive = self._aggressive_json_clean(json_string_sanitized)
                        raw_clues = json.loads(aggressive)
                    except Exception:
                        print(f"Clue parsing failed: {e}")
                        print(f"📝 [clue_json_head] {json_string[:300]}...")
                        raw_clues = self._fallback_parse_clue_pairs(json_string)
                        if raw_clues:
                            print(
                                f"📝 [clue_parse] recovered {len(raw_clues)} pairs via regex fallback (empty evidence_quote)"
                            )
                        else:
                            return []
                if raw_clues is None:
                    return []
                
                # Basic validation and deduplication
                validated_clues = self._deduplicate_clues(raw_clues)
                # Post-validate evidence to reduce hallucination: quote must exist in combined_results
                validated_clues = self._filter_by_evidence(validated_clues, combined_results)
                return validated_clues[:10]
            
            print("No valid JSON found in clue response")
            return []
            
        except Exception as e:
            print(f"Clue extraction failed: {e}")
            return []
    
    def _deduplicate_clues(self, raw_clues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate clues based on (song, artist) pairs, preserving evidence fields."""
        seen_pairs: Set[Tuple[str, str]] = set()
        unique_clues = []
        
        for clue in raw_clues:
            if isinstance(clue, dict) and clue.get('song') and clue.get('artist'):
                song = clue['song'].strip().lower()
                artist = clue['artist'].strip().lower()
                pair = (song, artist)
                
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    unique_clues.append({
                        'song': clue['song'].strip(),
                        'artist': clue['artist'].strip(),
                        'source_url': clue.get('source_url', '') or '',
                        'evidence_quote': clue.get('evidence_quote', '') or ''
                    })
        
        print(f"Deduplication: {len(raw_clues)} -> {len(unique_clues)} unique clues")
        return unique_clues

    def _filter_by_evidence(self, clues: List[Dict[str, Any]], combined_results: str) -> List[Dict[str, Any]]:
        """
        Tiered validation: strict (normalized quote substring + song/artist in quote) or
        relaxed (both titles appear in evidence with window co-occurrence). DecisionChain
        still enforces YouTube + AI verification downstream.
        """
        kept: List[Dict[str, Any]] = []
        combined_norm = self._normalize_for_evidence_match(combined_results)
        strict_ok_n = 0
        relaxed_ok_n = 0
        drop_no_pair = 0
        drop_no_both_in_source = 0
        drop_no_cooccurrence = 0
        window = self._EVIDENCE_COOCCUR_WINDOW

        for clue in clues:
            quote = (clue.get("evidence_quote") or "").strip()
            song = (clue.get("song") or "").strip()
            artist = (clue.get("artist") or "").strip()
            if not song or not artist:
                drop_no_pair += 1
                continue

            song_norm = self._normalize_for_evidence_match(song)
            artist_norm = self._normalize_for_evidence_match(artist)
            if len(song_norm) < 2 or len(artist_norm) < 2:
                drop_no_pair += 1
                continue

            quote_norm = self._normalize_for_evidence_match(quote) if quote else ""

            strict_ok = bool(
                quote_norm
                and len(quote) >= 10
                and quote_norm in combined_norm
                and song_norm in quote_norm
                and artist_norm in quote_norm
            )

            if strict_ok:
                kept.append(dict(clue))
                strict_ok_n += 1
                continue

            both_in_source = song_norm in combined_norm and artist_norm in combined_norm
            if not both_in_source:
                drop_no_both_in_source += 1
                continue

            relaxed_ok = self._co_occurs_within_window(
                combined_norm, song_norm, artist_norm, window
            )
            if not relaxed_ok:
                drop_no_cooccurrence += 1
                continue

            out = dict(clue)
            need_snip = (
                not quote
                or len(quote) < 10
                or quote_norm not in combined_norm
                or song_norm not in quote_norm
                or artist_norm not in quote_norm
            )
            if need_snip:
                snip = self._snippet_containing_both_in_source(
                    combined_results, song, artist, window
                )
                if snip:
                    out["evidence_quote"] = snip
            kept.append(out)
            relaxed_ok_n += 1

        print(
            f"🧾 [evidence_filter] strict_ok={strict_ok_n} relaxed_ok={relaxed_ok_n} "
            f"drop_no_pair={drop_no_pair} drop_not_in_source={drop_no_both_in_source} "
            f"drop_no_cooccurrence={drop_no_cooccurrence}"
        )
        return kept
    
    async def _verify_clues_parallel(self, clues: List[Dict[str, str]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stage 2: Verify clues in parallel with early exit"""
        verified_songs = []
        target_count = 5  # Target 5 songs max
        
        print(f"Starting parallel verification of {len(clues)} clues...")
        
        # Add rate limiting delay between requests
        async def verify_with_delay(clue, delay):
            if delay > 0:
                await asyncio.sleep(delay)
            return await self._verify_single_clue(clue['song'], clue['artist'], context)
        
        # Create tasks with staggered delays to avoid rate limiting
        tasks = []
        for i, clue in enumerate(clues[:10]):
            delay = i * 1.5  # 1.5 second delay between requests
            task = verify_with_delay(clue, delay)
            tasks.append(task)
        
        try:
            # Wait for all tasks to complete (with timeout)
            for task in asyncio.as_completed(tasks, timeout=45):
                result = await task
                if isinstance(result, dict) and result.get('official_link'):
                    verified_songs.append(result)
                    print(f"✅ 已验证第 {len(verified_songs)} 首: {result['song']}")
                    
                    # 核心：够了就走
                    if len(verified_songs) >= target_count:
                        print(f"⚡ 已达到目标数量 {target_count}，正在停止其余任务并返回...")
                        return verified_songs
                    
        except asyncio.TimeoutError:
            print("Verification timeout - using partial results")
        except Exception as e:
            print(f"Parallel verification failed: {e}")
        
        return verified_songs
    
    async def _verify_single_clue(self, song: str, artist: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify a single clue and enrich with metadata"""
        try:
            # Search for YouTube link
            if self.brave_search:
                refined_goal = context.get('refined_query', context.get('search_goal', ''))
                search_query = f"site:youtube.com {song} {artist} {refined_goal} official music"
                search_query = search_query[:120] 
                print(f"🔍 [YouTube Search] Query: {search_query}") # 打印出来方便你调试
                search_results = await asyncio.to_thread(self.brave_search.run, search_query, 5)
            else:
                search_results = ""

            # AI verification
            verification_prompt = get_single_clue_verification_prompt(song, artist, search_results, context)
            response = await asyncio.to_thread(self.model_manager.invoke_text, verification_prompt)

            # Enhanced parsing with multiple fallback attempts
            if response and response.strip().lower() != 'null':
                # Attempt 1: Standard cleaning
                try:
                    cleaned_response = self._clean_json_string(response)
                    verified_data = json.loads(cleaned_response)
                    if verified_data.get('song') and verified_data.get('artist'):
                        if verified_data['artist'].strip().lower() != artist.strip().lower():
                            print(f"[AI Artist Correction] '{artist}' → '{verified_data['artist']}' for song '{song}'")
                        return verified_data
                except json.JSONDecodeError as e1:
                    # Attempt 2: Aggressive cleaning
                    try:
                        aggressively_cleaned = self._aggressive_json_clean(response)
                        verified_data = json.loads(aggressively_cleaned)
                        if verified_data.get('song') and verified_data.get('artist'):
                            if verified_data['artist'].strip().lower() != artist.strip().lower():
                                print(f"[AI Artist Correction] '{artist}' → '{verified_data['artist']}' for song '{song}' (aggressive)")
                            print(f"🔧 [Aggressive parsing] Succeeded for {song} by {artist}")
                            return verified_data
                    except json.JSONDecodeError as e2:
                        # Attempt 3: Extract JSON object manually
                        try:
                            manual_json = self._extract_json_manually(response)
                            if manual_json:
                                verified_data = json.loads(manual_json)
                                if verified_data.get('song') and verified_data.get('artist'):
                                    if verified_data['artist'].strip().lower() != artist.strip().lower():
                                        print(f"[AI Artist Correction] '{artist}' → '{verified_data['artist']}' for song '{song}' (manual)")
                                    print(f"🔧 [Manual extraction] Succeeded for {song} by {artist}")
                                    return verified_data
                        except json.JSONDecodeError as e3:
                            # Final attempt: Try to build JSON from key phrases
                            fallback_data = self._build_fallback_json(response, song, artist)
                            if fallback_data:
                                print(f"🔧 [Fallback construction] Used for {song} by {artist}")
                                return fallback_data
                            # All attempts failed - log for debugging
                            print(f"❌ [JSON Parse Failure] {song} by {artist}")
                            print(f"   Original response: {response[:200]}...")
                            print(f"   Standard clean error: {e1}")
                            print(f"   Aggressive clean error: {e2}")
                            print(f"   Manual extract error: {e3}")
            return None
        except Exception as e:
            print(f"Single clue verification failed for {song} by {artist}: {e}")
            return None
