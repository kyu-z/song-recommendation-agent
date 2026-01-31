"""
Clue extraction prompts for initial song discovery
"""
from typing import Dict, Any
import re

def get_clue_extraction_prompt(goal: str, search_results: str, context: Dict[str, Any] = None) -> str:
    """
    Generate clue extraction prompt focused on maximum recall
    
    Args:
        goal: User's search goal/term
        search_results: Combined search results text
        context: Additional context for validation
    
    Returns:
        Formatted clue extraction prompt optimized for recall
    """
    origin_region = context.get('origin_region', 'unknown') if context else 'unknown'
    
    # Extract year information for flexible matching
    year_context = ""
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    year_matches = re.findall(year_pattern, goal)
    
    if year_matches:
        target_year = year_matches[0]
        year_context = f"\n**Year Context**: User is searching for {target_year} music. Prioritize songs from that era."
    
    return f"""You are a music detective extracting song clues from web content. Your goal is MAXIMUM RECALL - find every possible song mentioned.

Search Term: {goal}
Web Content: {search_results[:4000]}
Target Region: {origin_region}
{year_context}

**EXTRACTION STRATEGY**:
1. **Direct Extraction**: Find any song titles and artists explicitly mentioned
2. **Franchise Association**: If the page mentions legendary franchises (e.g., Naruto, Dragon Ball, Studio Ghibli), suggest the top 3 most famous theme songs using your internal knowledge
3. **Liberal Interpretation**: When in doubt, include it - verification happens later
4. **Regional Focus**: Prioritize artists from {origin_region} region when applicable

**RULES**:
- Extract UP TO 12 song clues (we'll filter later)
- Include songs even if context is unclear - better safe than sorry
- For anime/game franchises, suggest opening/ending themes from your knowledge
- Don't worry about metadata - just get the song names and artists
- If artist name is unclear, make your best guess or use "Various Artists"

**OUTPUT FORMAT** (JSON array only):
[
  {{"song": "Song Title", "artist": "Artist Name"}},
  {{"song": "Another Song", "artist": "Another Artist"}}
]

Extract aggressively - verification will filter out false positives later."""
