"""
Song extraction prompts for processing search results
"""
from typing import Dict, Any
import re

def get_extraction_prompt(goal: str, search_results: str, context: Dict[str, Any] = None) -> str:
    # 保持原有的逻辑计算不变
    origin_region = context.get('origin_region', 'unknown') if context else 'unknown'
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    year_matches = re.findall(year_pattern, goal)
    
    year_instr = "提取最符合要求的歌曲。"
    if year_matches:
        target_year = year_matches[0]
        y_start, y_end = max(int(target_year)-2, 1990), min(int(target_year)+2, 2025)
        year_instr = f"若无确切匹配，可提取 {y_start}-{y_end} 年间的经典代表作。"

    return f"""你已获得网页内容，请执行歌曲提取任务。

搜索术语：{goal}
网页内容：{search_results[:3000]}

**强制要求**：
1. ✅ **地域限定**：确保艺人主要来自 {origin_region}。
2. ✅ **信息丰满**：context 需详细记录网页中的背景事实，为后续 150 字文案提供素材。
3. ✅ **格式严谨**：仅输出 JSON 数组。

**输出格式说明**：
- **song**: 歌名
- **artist**: 艺人名（含母语名）
- **context**: 背景事实（榜单、成就、曲风等）
- **is_official_release**: 布尔值。若网页显示为 Cover/Remix/Live 则为 false，否则默认为 true。
- **artist_nationality**: 艺人国籍（如 Japan, Korea, China, US 等）。
- **explanation**: 仅在艺人国籍与目标地域 {origin_region} 不符时填写原因，否则留空。

**JSON 输出**（最多 10 首）：
[
  {{
    "song": "歌名", 
    "artist": "艺人名", 
    "context": "详细素材",
    "is_official_release": true,
    "artist_nationality": "国籍",
    "explanation": ""
  }}
]
"""