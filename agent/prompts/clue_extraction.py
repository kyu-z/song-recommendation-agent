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
    
    return f"""You are an evidence-first music extractor. Your goal is HIGH PRECISION: only output song–artist pairs that are explicitly supported by the provided text evidence.

Search Term: {goal}
Web Content (evidence only; do not use external knowledge): {search_results}
Target Region: {origin_region}
{year_context}

**STRICT RULES (NO HALLUCINATION)**:
1. ONLY extract pairs where BOTH the song title AND the artist name are present in the evidence text.
2. DO NOT guess, infer, “suggest”, or use internal/external knowledge. If uncertain, omit the item.
3. Each output item MUST include an evidence_quote: a **short plain-text** line that contains BOTH the song title and the artist name as they appear in the evidence (do not paraphrase).
   - **JSON safety (mandatory)**: evidence_quote MUST be valid inside a JSON string. Do NOT paste Markdown links like [Artist](https://...); use the visible artist name only. Do NOT put raw double-quote characters (") inside evidence_quote — if the source uses quotes around the title, use single quotes '...' or omit them. No line breaks inside evidence_quote.
   - **SINGLE LINE** only; keep it SHORT: 80–200 characters when possible.
   - Do NOT include unescaped control characters.
4. Always use empty string "" for source_url (avoids JSON truncation); evidence_quote is required.
5. Output AT MOST 10 items.

**OUTPUT FORMAT** (JSON array only):
[
  {{
    "song": "Song Title",
    "artist": "Artist Name",
    "source_url": "",
    "evidence_quote": "Exact text snippet that contains both the song and the artist"
  }}
]

IMPORTANT: Always use empty string "" for source_url. Output MUST be parseable JSON: escape any double quote inside strings as backslash-doublequote (\\"). The evidence comes from the provided web content.
Return ONLY the JSON array. No markdown fences, no commentary."""
