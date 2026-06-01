import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
import yt_dlp
from yt_dlp import YoutubeDL
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Logging setup
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "7583"))
DOWNLOAD_DIR = "downloads"
TTL_SECONDS = int(os.getenv("TTL_SECONDS", 24 * 60 * 60))
CLEANUP_INTERVAL_MINUTES = int(os.getenv("CLEANUP_INTERVAL_MINUTES", 60))
CLEANUP_INTERVAL_SECONDS = CLEANUP_INTERVAL_MINUTES * 60

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    logger.info(f"Created downloads directory: {DOWNLOAD_DIR}")

async def cleanup_worker():
    while True:
        try:
            now = time.time()
            deleted_count = 0
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) + TTL_SECONDS < now:
                    os.remove(file_path)
                    deleted_count += 1
            if deleted_count > 0:
                logger.info(f"Cleanup: Deleted {deleted_count} expired files")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up - creating cleanup task")
    cleanup_task = asyncio.create_task(cleanup_worker())
    yield
    logger.info("Shutting down - cancelling cleanup task")
    cleanup_task.cancel()

app = FastAPI(
    title="SoundCloud MP3 API",
    description="Stream SoundCloud tracks as MP3 files",
    version="1.0.0",
    lifespan=lifespan
)

# Simple rate limiting storage
rate_limit_store = {}
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_SECONDS = 60

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    
    # Remove old requests (older than 60 seconds)
    rate_limit_store[client_ip] = [ts for ts in rate_limit_store[client_ip] if now - ts < RATE_LIMIT_SECONDS]
    
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    rate_limit_store[client_ip].append(now)
    return True

def create_file_response(file_path: str) -> FileResponse:
    """Helper to create consistent FileResponse"""
    return FileResponse(
        path=file_path, 
        media_type="audio/mpeg", 
        content_disposition_type="inline",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline"
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "ok", "service": "soundcloud-mp3-api"}

@app.get("/download/{url:path}")
async def get_music(url: str, request: Request):
    # Rate limiting
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Maximum 10 requests per minute."
        )
    
    logger.info(f"Download request for: {url[:50]}...")
    ydl_opts_info = {'quiet': True, 'extract_flat': True} 
    
    try:
        with YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info or info.get('_type') == 'playlist':
                logger.warning(f"Playlist attempt: {url}")
                raise HTTPException(
                    status_code=400, 
                    detail="The provided link is a playlist or profile. This API supports only single tracks."
                )
            
            track_id = info.get('id')
            if not track_id:
                logger.warning(f"Could not extract track ID from: {url}")
                raise HTTPException(
                    status_code=400, 
                    detail="Could not find track ID. The link may be invalid."
                )
                
            ext = 'mp3'
            filename = f"{track_id}.{ext}"
            file_path = os.path.join(DOWNLOAD_DIR, filename)

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error for {url}: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid SoundCloud link or the track has been deleted/is private."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected server error occurred: {str(e)}"
        )

    if os.path.exists(file_path):
        logger.info(f"File exists, serving from cache: {filename}")
        os.utime(file_path, None)
        return create_file_response(file_path)

    ydl_opts_download = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{track_id}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    logger.info(f"Downloading: {track_id}")
    with YoutubeDL(ydl_opts_download) as ydl:
        ydl.download([url])
    
    logger.info(f"Download complete: {filename}")
    return create_file_response(file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)