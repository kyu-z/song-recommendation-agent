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
    
    return f"""从音乐推荐内容中提取歌曲，并进行严格的元数据校验：

搜索术语：{goal}
搜索内容：
{search_results[:2000]}
{region_context}

**提取要求**：
1. 从搜索结果中提取与"{goal}"相关的高质量歌曲信息
2. 优先选择知名度高、代表性强的**官方发行版本**
3. 必须同时有歌名和艺人名才能提取
4. 严格验证艺人国籍与搜索目标的匹配度
5. 识别并标注官方发行状态

**元数据校验规则**：
- is_official_release: 判断是否为官方发行版本（非Cover、非Live、非Remix）
- artist_nationality: 艺人主要国籍/地区（Japan/Korea/Taiwan/China/US/UK等）
- explanation: 如果艺人国籍与搜索地域不匹配，必须说明原因（如：韩国艺人的日语作品）

输出格式（JSON数组）：
[
  {{
    "song": "完整准确的歌名", 
    "artist": "完整准确的艺人名", 
    "context": "推荐理由",
    "is_official_release": true/false,
    "artist_nationality": "Japan/Korea/Taiwan/China/US/UK/Other",
    "explanation": "如有地域不匹配则说明原因，否则为空字符串"
  }}
]

请提取最多5首高质量的相关歌曲。确保每首歌都有完整的元数据。如果确实没有找到任何完整的歌曲信息，返回[]。"""
