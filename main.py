from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import logging
import re
import json
import os
import tempfile
import shutil

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
    is_official_release: Optional[bool] = None
    artist_nationality: Optional[str] = None
    explanation: Optional[str] = None

class RecommendationResponse(BaseModel):
    success: bool
    search_goal: Optional[str] = None
    songs: List[Song]
    message: Optional[str] = None
    total_found: int
    original_input: Optional[str] = None


def sanitize_display_text(text: str) -> str:
    """Strip wiki/markdown noise from fallback reason lines (does not affect retrieval)."""
    if not text or not text.strip():
        return text
    s = text
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[\[(\d+)\]\](?:\([^)]*\))?", "", s)
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_recommendation_text(recommendation_text: str, found_songs: List[Dict[str, Any]] = None) -> List[Song]:
    """
    Parse the recommendation text and extract structured song information
    """
    songs = []
    
    # If we have found_songs from the context, use that as the primary source
    if found_songs:
        # Extract reasons from the recommendation text (aligned with generation._generate_summary_report)
        song_blocks = re.split(r'\*\*([^*]+)\*\*', recommendation_text)
        reasons = {}
        
        for i in range(1, len(song_blocks), 2):
            if i + 1 < len(song_blocks):
                song_title = song_blocks[i].strip()
                if ' - ' not in song_title:
                    continue
                content = song_blocks[i + 1].strip()
                
                reason_match = re.search(r'推荐理由[：:]\s*(.*?)播放链接', content, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
                    reasons[song_title] = reason
        
        # Create Song objects from found_songs
        for song_data in found_songs:
            song_title = song_data.get('song', '')
            artist_name = song_data.get('artist', '')
            
            title_key = f"{song_title} - {artist_name}"
            parsed = reasons.get(title_key)
            if parsed:
                reason = sanitize_display_text(parsed)
            else:
                reason = (song_data.get('explanation') or '').strip()
                if not reason:
                    reason = song_data.get('context', '经典推荐')
                reason = sanitize_display_text(reason)
            
            songs.append(Song(
                title=song_title,
                artist=artist_name,
                reason=reason,
                link=song_data.get('official_link'),
                platform=song_data.get('platform'),
                source=song_data.get('source', 'web'),
                is_official_release=song_data.get('is_official_release'),
                artist_nationality=song_data.get('artist_nationality'),
                explanation=song_data.get('explanation')
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
    """Get music recommendation from text input"""
    if not music_agent:
        raise HTTPException(status_code=503, detail="MusicAgent not initialized")
    
    try:
        logger.info(f"🎵 Processing recommendation request: {request.user_input}")
        
        # Get recommendation from agent
        result = await music_agent.recommend(request.user_input)
        
        # Get the structured context data from result
        found_songs = result.get('found_songs', [])
        search_goal = result.get('search_goal')
        recommendation_text = result.get('final_report', '')
        
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
            message=f"成功推荐 {len(songs)} 首歌曲",
            total_found=len(songs),
            original_input=request.user_input
        )
    
    except Exception as e:
        logger.error(f"❌ Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend/image", response_model=RecommendationResponse)
async def get_recommendation_from_image(image: UploadFile = File(...)):
    """Get music recommendation from image input"""
    if not music_agent:
        raise HTTPException(status_code=503, detail="MusicAgent not initialized")
    
    # Validate image file
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    if image.content_type not in ['image/jpeg', 'image/jpg', 'image/png']:
        raise HTTPException(status_code=400, detail="仅支持 JPG, JPEG, PNG 格式")
    
    # Create temporary file for the image
    temp_dir = tempfile.mkdtemp()
    temp_file_path = None
    
    try:
        # Save uploaded image to temporary file
        file_extension = os.path.splitext(image.filename or 'image.jpg')[1]
        temp_file_path = os.path.join(temp_dir, f"uploaded_image{file_extension}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        logger.info(f"🖼️ Processing image recommendation: {image.filename}")
        
        # Get recommendation from agent using image path
        result = await music_agent.recommend(temp_file_path)
        
        # Get the structured context data from result
        found_songs = result.get('found_songs', [])
        search_goal = result.get('search_goal')
        image_analysis = result.get('image_analysis')
        recommendation_text = result.get('final_report', '')
        
        # Parse the recommendation text into structured data
        songs = parse_recommendation_text(recommendation_text, found_songs)
        
        if not songs:
            return RecommendationResponse(
                success=False,
                search_goal=search_goal,
                songs=[],
                message="未找到匹配图片意境的音乐",
                total_found=0
            )
        
        return RecommendationResponse(
            success=True,
            search_goal=search_goal,
            songs=songs,
            message=f"根据图片意境推荐 {len(songs)} 首歌曲",
            total_found=len(songs),
            original_input=f"图片分析: {image_analysis}" if image_analysis else f"图片文件: {image.filename}"
        )
    
    except Exception as e:
        logger.error(f"❌ Image recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary file
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to cleanup temp file: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
