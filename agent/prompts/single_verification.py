"""
Single clue verification prompts for stage 2 processing
"""

def get_single_clue_verification_prompt(song: str, artist: str, search_results: str, context: dict = None) -> str:
    """
    Generate verification prompt for a single song clue
    
    Args:
        song: Song name to verify
        artist: Artist name to verify  
        search_results: YouTube search results for this specific song
        context: Additional context
        
    Returns:
        Formatted verification prompt for single clue
    """
    origin_region = context.get('origin_region', 'unknown') if context else 'unknown'
    
    return f"""Verify and enhance this single song clue using YouTube search results.

**Target Song**: "{song}" by {artist}
**Provided Artist**: "{artist}" (Note: This might be incorrect, use your knowledge to verify)
**Expected Region**: {origin_region}

**YouTube Search Results**:
{search_results[:2000]}

**VERIFICATION TASK**:
1. Find the BEST official YouTube link for this exact song
2. Gather context information about the song (chart performance, significance, style)
3. Determine if this is an official release (not cover/remix/fan-made)
4. **Identity Correction**: Based on your internal knowledge, who is the ACTUAL artist of the song "{song}"? 
   - If the provided artist "{artist}" is a voice actor, a franchise name, or just wrong, REPLACE it with the correct original artist (e.g., Change "Miyamoto Yoshiko" to "7!!" if it's the Naruto theme).
5. **YouTube Alignment**: Look at the search results below. Find the link that matches the REAL artist you identified in step 4.
6. **Data Enrichment**: Fill in the nationality and background for the CORRECT artist.


**QUALITY STANDARDS**:
- Prefer Official MVs > Topic Channels > Audio Only > Live Performances  
- Avoid covers, remixes, reaction videos, tutorials
- Trust major music channels (VEVO, official artist channels, major labels)

**OUTPUT FORMAT** (JSON only):
{{
  "song": "{song}",
  "artist": "CORRECT_ARTIST_NAME",
  "context": "Detailed background about this song (chart success, cultural impact, musical style, etc.)",
  "official_link": "https://youtube.com/watch?v=...",
  "platform": "YouTube",
  "is_official_release": true,
  "artist_nationality": "Japan/Korea/China/US/UK/Other",
  "explanation": "",
  "source": "verified"
}}

If NO suitable YouTube link found, return:
{{
  "song": "{song}",
  "artist": "{artist}",
  "context": "Classic track - recommend manual search on your preferred music platform",
  "official_link": null,
  "platform": null,
  "is_official_release": true,
  "artist_nationality": "Japan/Korea/China/US/UK/Other",
  "explanation": "",
  "source": "no_link"
}}

If the song doesn't exist or verification fails completely, return: null

**CRITICAL**: 
- Return ONLY valid JSON object, nothing else
- No explanatory text before or after JSON
- Use double quotes for all strings
- End with proper closing brace
- Do not include trailing commas
- If uncertain, use "Unknown" for missing fields

Only return JSON, no explanatory text."""
