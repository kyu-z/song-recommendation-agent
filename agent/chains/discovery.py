"""
Discovery Chain - Stage 2: Music discovery and extraction
"""
import time
import re
import json
import requests
from typing import Dict, Any, List
from ..prompts.extraction import get_extraction_prompt


class DiscoveryChain:
    """Handles music discovery through web search and extraction"""
    
    def __init__(self, brave_search, model_manager):
        self.brave_search = brave_search
        self.model_manager = model_manager
    
    def search(self, context: Dict[str, Any]) -> Dict[str, Any]:
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
            
            # Stage 1: Find authority links (Apple Music, Spotify, Wikipedia)
            authority_links = self._find_authority_links(context)
            
            # Stage 2: Parse authority content + general search
            all_search_results = []
            
            # Parse authority links first
            if authority_links:
                authority_content = self._parse_authority_links(authority_links)
                all_search_results.extend(authority_content)
                
                # Also try to fetch web content from authority links
                web_content = self._fetch_authority_web_content(authority_links)
                if web_content:
                    all_search_results.extend(web_content)
                    print(f"🌐 [WebReader] 成功抓取 {len(web_content)} 个网页内容")
            
            # Fallback to general discovery if no authority content
            if not all_search_results:
                print("🔍 [Fallback] 权威链接解析失败，使用通用搜索...")
                general_queries = self._generate_discovery_queries(context)
                
                for i, query in enumerate(general_queries):
                    if i > 0:
                        time.sleep(1.5)  # Rate limiting
                    try:
                        print(f"🔍 搜索 ({i+1}/{len(general_queries)}): {query}")
                        results = self.brave_search.run(query)
                        all_search_results.append(results)
                    except Exception as e:
                        print(f"⚠️  Search failed for '{query}': {e}")
            
            print(f"🔍 [调试] 总共收集到 {len(all_search_results)} 个搜索结果")
            if not all_search_results:
                print("🔍 [调试] 没有任何搜索结果，提前返回")
                return context
            
            # Extract songs from search results
            discovered_songs = self._extract_songs_from_text(all_search_results, context)
            print(f"✅ [Discovery] 发现 {len(discovered_songs)} 首候选歌曲")
            
            context['found_songs'] = discovered_songs
            return context
            
        except Exception as e:
            print(f"❌ [Discovery Phase] 失败: {e}")
            return context
    
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
            primary_query = refined_query or search_goal
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
        native_name = context.get('native_name')
        origin_region = context.get('origin_region', 'unknown')
        search_strategy = context.get('search_strategy', 'international')
        
        print(f"🎯 [多源信息搜索] 地域: {origin_region}, 策略: {search_strategy}")
        
        # Build diverse information source queries
        authority_queries = []
        
        # Core query with native name if available
        base_query = native_name if native_name and search_strategy in ['localized', 'hybrid'] else refined_query
        
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
        for query in authority_queries[:5]:  # Increased to 5 for better coverage
            try:
                print(f"🔗 [信息搜索]: {query}")
                results = self.brave_search.run(query)
                # Extract actual links from results
                links = self._extract_authority_links(results)
                authority_links.extend(links)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"⚠️  Information search failed: {e}")
        
        print(f"🔗 [信息链接] 找到 {len(authority_links)} 个信息源链接")
        return authority_links[:8]  # Increased limit for better coverage
    
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
        # Simple regex to find URLs (this is a basic implementation)
        url_pattern = r'https?://[^\s<>"\']+(?:[^\s<>"\'.,;:])'
        urls = re.findall(url_pattern, search_results)
        
        for url in urls:
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
        """Fetch web content from authority music platform links"""
        target_domains = ['music.apple.com', 'open.spotify.com', 'billboard.com']
        web_contents = []
        
        for link in authority_links:
            # Check if link is from target domains
            if any(domain in link for domain in target_domains):
                content = self._fetch_web_content(link)
                if content and len(content) > 100:  # Only include substantial content
                    web_contents.append(f"=== Web Content from {link} ===\n{content}")
                    
                # Rate limiting for web requests
                time.sleep(1)
        
        return web_contents
    
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
    
    def _extract_songs_from_text(self, search_results: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract specific songs from search results using AI"""
        combined_results = "\n".join(search_results)
        goal = context.get('search_goal', '')
        
        # Debug information
        print(f"🎯 [调试] 搜索结果总长度: {len(combined_results)} 字符")
        print(f"🎯 [调试] 搜索结果预览前500字符:")
        print(combined_results[:500])
        print("=" * 50)
        
        extraction_prompt = get_extraction_prompt(goal, combined_results, context)
        
        try:
            response = self.model_manager.invoke_text(extraction_prompt)
            print(f"🎯 [调试] AI提取响应长度: {len(response)} 字符")
            print(f"🎯 [调试] AI完整响应:")
            print(response)
            print("=" * 50)
            
            # Clean and parse JSON response with robustness
            cleaned_response = self._clean_json_string(response)
            print(f"🎯 [JSON清理] 清理后长度: {len(cleaned_response)}")
            
            # Parse JSON response
            json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
            if json_match:
                json_string = json_match.group()
                print(f"🎯 [调试] 找到JSON匹配: {json_string[:200]}...")
                
                try:
                    extracted_songs = json.loads(json_string)
                except json.JSONDecodeError as e:
                    print(f"⚠️  [JSON解析] 第一次解析失败: {e}")
                    # Try additional cleaning
                    json_string = self._aggressive_json_clean(json_string)
                    try:
                        extracted_songs = json.loads(json_string)
                        print(f"🎯 [JSON清理] 二次清理成功")
                    except json.JSONDecodeError as e2:
                        print(f"⚠️  [JSON解析] 二次解析也失败: {e2}")
                        return []
                
                # Filter and validate results with enhanced metadata
                valid_songs = []
                for song in extracted_songs:
                    if isinstance(song, dict) and song.get('song') and song.get('artist'):
                        enhanced_song = {
                            'song': song['song'].strip(),
                            'artist': song['artist'].strip(),
                            'context': song.get('context', '').strip(),
                            'is_official_release': song.get('is_official_release', True),
                            'artist_nationality': song.get('artist_nationality', 'unknown'),
                            'explanation': song.get('explanation', ''),
                            'source': 'discovery'
                        }
                        valid_songs.append(enhanced_song)
                        
                        # Log metadata for debugging
                        print(f"🎯 [提取歌曲] {enhanced_song['song']} by {enhanced_song['artist']}")
                        print(f"   📝 推荐理由: {enhanced_song['context']}")
                        if enhanced_song['explanation']:
                            print(f"   ⚠️  元数据说明: {enhanced_song['explanation']}")
                
                print(f"🎯 [调试] 解析出的歌曲数量: {len(extracted_songs)}")
                print(f"🎯 [调试] 验证通过的歌曲数量: {len(valid_songs)}")
                return valid_songs[:5]  # Return max 5 songs
            else:
                print("⚠️  [调试] 无法解析歌曲提取结果，未找到JSON数组")
                print(f"⚠️  [调试] 完整响应: {response}")
                return []
                
        except Exception as e:
            print(f"⚠️  歌曲提取失败: {e}")
            return []
