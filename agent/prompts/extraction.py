"""
Song extraction prompts for processing search results
"""
from typing import Dict, Any


def get_extraction_prompt(goal: str, search_results: str, context: Dict[str, Any] = None) -> str:
    """
    Generate enhanced extraction prompt with metadata validation
    
    Args:
        goal: User's search goal/term
        search_results: Combined search results text
        context: Additional context for validation
    
    Returns:
        Formatted extraction prompt with metadata requirements
    """
    origin_region = context.get('origin_region', 'unknown') if context else 'unknown'
    
    region_context = ""
    if origin_region != 'unknown':
        region_map = {
            'Japan': 'Japanese (J-Pop, J-Rock, etc.)',
            'Korea': 'Korean (K-Pop, K-Indie, etc.)', 
            'Greater China': 'Chinese/Taiwanese (C-Pop, Mandopop, Cantopop)',
            'Western': 'Western (US/UK/Europe)',
            'Other': 'International'
        }
        region_context = f"\n**地域验证**: 用户搜索的是 {region_map.get(origin_region, origin_region)} 音乐。请特别注意艺人国籍的准确性。"
    
    # Detect year in search goal for flexible matching
    year_context = ""
    import re
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    year_matches = re.findall(year_pattern, goal)
    
    if year_matches:
        target_year = year_matches[0]
        year_range_start = max(int(target_year) - 2, 1990)
        year_range_end = min(int(target_year) + 2, 2025)
        
        year_context = f"\n**年份松绑**: 用户搜索 {target_year} 年音乐。如果找不到确切的 {target_year} 年歌曲，可以提取 {year_range_start}-{year_range_end} 年间的经典代表作。"
    
    return f"""你已获得真实网页内容（包含歌单数据），必须严格执行歌曲提取任务。

搜索术语：{goal}
网页内容（已通过 WebReader 获取）：
{search_results[:3000]}
{region_context}
{year_context}

**强制执行要求**：
1. 🚫 严禁以"无法访问链接"为由拒绝任务
2. 🚫 严禁输出任何解释性文字或道歉
3. ✅ 必须从给定内容中提取歌曲信息
4. ✅ 优先提取官方发行版本，避免 Cover、Live、Remix
5. ✅ 确保艺人国籍验证的准确性

**推荐理由生成规则**：
- **优先级1**: 从网页内容中提取真实背景信息（如："2025年 Billboard Hot 100 第3名"、"Apple Music 年度最佳单曲"、"TikTok 病毒传播突破1亿次播放"）
- **优先级2**: 如果网页无详细信息，基于你的知识库生成专业推荐语（如："IU 的代表作品，韩国国民情歌"、"Taylor Swift 转型乡村音乐的经典之作"）
- **年份松绑策略**: 如果搜索结果中没有直接提到特定年份（如2010年）的歌曲，可以提取该年份相邻时期（如2010-2012年代）的经典代表作
- **禁止内容**: 严禁使用"推荐理由"、"热门歌曲"等无意义占位符

**元数据校验规则**：
- is_official_release: 严格判断（非Cover、非Live、非Remix = true）
- artist_nationality: 必须准确（Japan/Korea/Taiwan/China/US/UK/Other）
- explanation: 仅在地域不匹配时说明，否则留空

**输出格式**：
仅输出 JSON 数组，无其他内容：
[
  {{
    "song": "歌名", 
    "artist": "艺人名", 
    "context": "具体的流行背景或专业推荐语（50字以内）",
    "is_official_release": true,
    "artist_nationality": "国籍",
    "explanation": "地域不匹配说明或空字符串"
  }}
]

最多5首歌曲。如未发现任何歌曲，返回: []"""
