import os
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
import yt_dlp
from yt_dlp import YoutubeDL
from fastapi.responses import FileResponse, HTMLResponse
from typing import Annotated

ALLOWED_USER_AGENTS = [
    "PostmanRuntime/", 
    "MTA:SA Server"
]

DOWNLOAD_DIR = "downloads"
TTL_SECONDS = 24 * 60 * 60  # 24 godziny

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

async def cleanup_worker():
    while True:
        now = time.time()
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.getmtime(file_path) + TTL_SECONDS < now:
                os.remove(file_path)
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(cleanup_worker())
    yield
    cleanup_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/download/{url:path}")
async def get_music(url: str, user_agent: Annotated[str | None, Header()] = None):
    is_authorized = user_agent and any(user_agent.startswith(prefix) for prefix in ALLOWED_USER_AGENTS)

    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="Brak dostępu. Używasz nieautoryzowanej aplikacji lub przeglądarki."
        )
    ydl_opts_info = {'quiet': True, 'extract_flat': True} 
    
    try:
        with YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info or info.get('_type') == 'playlist':
                raise HTTPException(
                    status_code=400, 
                    detail="Podany link prowadzi do playlisty lub profilu. API obsługuje wyłącznie pojedyncze utwory."
                )
            
            track_id = info.get('id')
            if not track_id:
                raise HTTPException(
                    status_code=400, 
                    detail="Nie udało się odnaleźć ID utworu. Link może być niepoprawny."
                )
                
            ext = 'mp3'
            filename = f"{track_id}.{ext}"
            file_path = os.path.join(DOWNLOAD_DIR, filename)

    except yt_dlp.utils.DownloadError:
        raise HTTPException(
            status_code=400, 
            detail="Nieprawidłowy link SoundCloud lub utwór został usunięty/jest prywatny."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Wystąpił nieoczekiwany błąd serwera: {str(e)}"
        )

    if os.path.exists(file_path):
        os.utime(file_path, None)
        return FileResponse(
            path=file_path, 
            media_type="audio/mpeg", 
            content_disposition_type="inline",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": "inline"
            }
        )

    ydl_opts_download = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{track_id}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with YoutubeDL(ydl_opts_download) as ydl:
        ydl.download([url])

    return FileResponse(
        path=file_path, 
        media_type="audio/mpeg", 
        content_disposition_type="inline",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline"
        }
    )