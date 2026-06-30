from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path == "/" or request.url.path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

from app.routes import _ensure_profile_artists_in_recommender, _load_profile, set_recommender, router
from recommender.content_based import ContentBasedRecommender


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        from data.spotify_source import load_spotify_data
        artist_info = load_spotify_data()
        print(f"Spotify source loaded {len(artist_info)} artists")
    except Exception as e:
        print(f"Spotify API failed ({e}), using fallback data")
        from data.sample_data import ARTISTS, GENRES
        import pandas as pd
        rows = [
            {"artist": a, "genre": GENRES.get(a, "Unknown"), "image_url": "", "spotify_id": ""}
            for a in ARTISTS
        ]
        artist_info = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["artist", "genre", "image_url", "spotify_id"])
        print(f"Fallback loaded {len(artist_info)} artists")

    content = ContentBasedRecommender(artist_info)
    content.fit()
    set_recommender(content)
    _load_profile()
    _ensure_profile_artists_in_recommender()
    count = len(content.artist_info)
    print(f"Ready — {count} artist{'s' if count != 1 else ''} in recommender")
    yield


app = FastAPI(
    title="Music Recommender",
    description="Personal music recommendations based on artists you love.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(NoCacheMiddleware)

app.include_router(router, prefix="/api/v1")

frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
