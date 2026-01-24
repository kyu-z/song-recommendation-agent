from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import re
import json

# Import your MusicAgent
from music_ai_agent import MusicAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Music AI Agent API",
    description="AI-powered music recommendation service",
    version="1.0.0"
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MusicAgent instance (initialized once at startup)
music_agent: Optional[MusicAgent] = None

# Pydantic models
class RecommendationRequest(BaseModel):
    user_input: str

class Song(BaseModel):
    title: str
    artist: str
    reason: str
    link: Optional[str] = None
    platform: Optional[str] = None
    source: Optional[str] = None  # "web" or "local"

class RecommendationResponse(BaseModel):
    success: bool
    search_goal: Optional[str] = None
    songs: List[Song]
    message: Optional[str] = None
    total_found: int

def parse_recommendation_text(recommendation_text: str, found_songs: List[Dict[str, Any]] = None) -> List[Song]:
    """
    Parse the recommendation text and extract structured song information
    """
    songs = []
    
    # If we have found_songs from the context, use that as the primary source
    if found_songs:
        # Extract reasons from the recommendation text
        song_blocks = re.split(r'\*\*([^*]+)\*\*', recommendation_text)
        reasons = {}
        
        for i in range(1, len(song_blocks), 2):
            if i + 1 < len(song_blocks):
                song_title = song_blocks[i].strip()
                content = song_blocks[i + 1].strip()
                
                # Extract reason (text between title and link)
                reason_match = re.search(r'推荐理由[：:]\s*(.*?)播放链接', content, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
                    reasons[song_title] = reason
        
        # Create Song objects from found_songs
        for song_data in found_songs:
            song_title = song_data.get('song', '')
            artist_name = song_data.get('artist', '')
            
            # Try to match reason from parsed text
            title_key = f"{song_title} - {artist_name}"
            reason = reasons.get(title_key, song_data.get('context', '经典推荐'))
            
            songs.append(Song(
                title=song_title,
                artist=artist_name,
                reason=reason,
                link=song_data.get('official_link'),
                platform=song_data.get('platform'),
                source=song_data.get('source', 'web')
            ))
    
    else:
        # Fallback: parse from recommendation text directly
        # Split by song headers (bold text with ** **)
        song_blocks = re.split(r'\*\*([^*]+)\*\*', recommendation_text)
        
        for i in range(1, len(song_blocks), 2):
            if i + 1 < len(song_blocks):
                song_header = song_blocks[i].strip()
                song_content = song_blocks[i + 1].strip()
                
                # Parse title - artist
                if ' - ' in song_header:
                    title, artist = song_header.split(' - ', 1)
                else:
                    title = song_header
                    artist = "Unknown Artist"
                
                # Extract reason
                reason_match = re.search(r'推荐理由[：:]\s*(.*?)(?:播放链接|$)', song_content, re.DOTALL)
                reason = reason_match.group(1).strip() if reason_match else "AI推荐的优质音乐"
                
                # Extract link
                link_match = re.search(r'播放链接[：:]\s*(https?://[^\s]+)', song_content)
                link = link_match.group(1) if link_match else None
                
                # Determine platform from link
                platform = None
                if link:
                    if 'youtube.com' in link or 'youtu.be' in link:
                        platform = "YouTube"
                    elif 'spotify.com' in link:
                        platform = "Spotify"
                    elif 'bandcamp.com' in link:
                        platform = "Bandcamp"
                    else:
                        platform = "Web"
                
                songs.append(Song(
                    title=title.strip(),
                    artist=artist.strip(),
                    reason=reason,
                    link=link,
                    platform=platform,
                    source="web"
                ))
    
    return songs

@app.on_event("startup")
async def startup_event():
    """Initialize MusicAgent on startup"""
    global music_agent
    try:
        logger.info("🎵 Initializing MusicAgent...")
        music_agent = MusicAgent(use_local_model=False)
        logger.info("✅ MusicAgent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MusicAgent: {e}")
        raise e

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest):
    """Get music recommendation"""
    if not music_agent:
        raise HTTPException(status_code=503, detail="MusicAgent not initialized")
    
    try:
        logger.info(f"🎵 Processing recommendation request: {request.user_input}")
        
        # Get recommendation from agent
        recommendation_text = music_agent.get_recommendation(request.user_input)
        
        # Get the structured context data
        context = music_agent.get_last_context()
        found_songs = context.get('found_songs', [])
        search_goal = context.get('search_goal')
        
        # Parse the recommendation text into structured data
        songs = parse_recommendation_text(recommendation_text, found_songs)
        
        if not songs:
            return RecommendationResponse(
                success=False,
                search_goal=search_goal,
                songs=[],
                message="未找到合适的音乐推荐",
                total_found=0
            )
        
        return RecommendationResponse(
            success=True,
            search_goal=search_goal,
            songs=songs,
            message="推荐成功",
            total_found=len(songs)
        )
    
    except Exception as e:
        logger.error(f"❌ Error processing recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"推荐处理失败: {str(e)}")

# Add startup event to initialize agent
@app.on_event("startup")
async def startup_event():
    """Initialize MusicAgent on startup"""
    global music_agent
    try:
        logger.info("🎵 Initializing MusicAgent...")
        music_agent = MusicAgent(use_local_model=False)
        logger.info("✅ MusicAgent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MusicAgent: {e}")
        raise e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
