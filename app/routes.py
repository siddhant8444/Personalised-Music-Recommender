import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.models import ArtistInfo, RecommendationResponse
from data.spotify_source import search_artist, search_track
from recommender.content_based import ContentBasedRecommender

load_dotenv()

router = APIRouter()
PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "profile.json"
ADMIN_KEY = os.getenv("ADMIN_KEY", "siddhant")


class AddArtistRequest(BaseModel):
    name: str
    genre: str = "Unknown"


class ProfileEntry(BaseModel):
    artist: str
    genre: str = ""
    song: str = ""
    track_id: str = ""


class ProfileUpdate(BaseModel):
    artists: list[ProfileEntry]


_content: ContentBasedRecommender | None = None
_profile_artists: list[ProfileEntry] = []


def _save_profile():
    PROFILE_PATH.write_text(json.dumps([a.model_dump() for a in _profile_artists], indent=2))


def _load_profile():
    global _profile_artists
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text())
            _profile_artists = [ProfileEntry(**a) for a in data]
        except (json.JSONDecodeError, Exception):
            _profile_artists = []


def set_recommender(content: ContentBasedRecommender):
    global _content
    _content = content


def _ensure_profile_artists_in_recommender():
    if _content is None or not _profile_artists:
        return
    from data.spotify_source import _load_cache, _save_cache
    cache = _load_cache()
    changed = False
    for entry in _profile_artists:
        if entry.artist not in _content.artist_info["artist"].values:
            genre = entry.genre or "Unknown"
            image_url = ""
            spotify_id = ""
            if entry.artist in cache:
                c = cache[entry.artist]
                image_url = c.get("image_url", "")
                spotify_id = c.get("spotify_id", "")
            else:
                try:
                    results = search_artist(entry.artist)
                    if results:
                        image_url = results[0].get("image_url", "")
                        spotify_id = results[0].get("spotify_id", "")
                        cache[entry.artist] = {"name": entry.artist, "image_url": image_url, "spotify_id": spotify_id}
                        changed = True
                except Exception:
                    pass
            _content.add_artist(entry.artist, genre, image_url, spotify_id)
            print(f"  Registered profile artist: {entry.artist}")
    if changed:
        _save_cache(cache)


@router.get("/artists", tags=["Artists"])
def list_artists():
    if _content is None:
        return {"artists": []}
    return {
        "artists": [
            {
                "artist": row["artist"],
                "genre": row["genre"],
                "image_url": row.get("image_url", ""),
                "spotify_id": row.get("spotify_id", ""),
            }
            for _, row in _content.artist_info.iterrows()
        ]
    }


@router.get("/recommend/from-artists", response_model=RecommendationResponse, tags=["Recommendations"])
def recommend_from_artists(
    artists: str = Query(..., description="Comma-separated list of artists you like"),
    n: int = Query(10, ge=1, le=50),
):
    names = [a.strip() for a in artists.split(",") if a.strip()]
    if not names or _content is None:
        return RecommendationResponse(recommendations=[], method="from_artists")
    recs = _content.recommend_from_artists(names, n=n)
    return RecommendationResponse(recommendations=[ArtistInfo(**r) for r in recs], method="from_artists")


@router.get("/recommend/by-genre", tags=["Recommendations"])
def recommend_by_genre(n: int = Query(6, ge=1, le=20)):
    if _content is None or not _profile_artists:
        return {"profile_artists": [], "recommendations": {}}

    profile_with_genre = []
    for entry in _profile_artists:
        info = _content.artist_info[_content.artist_info["artist"] == entry.artist]
        if not info.empty:
            row = info.iloc[0]
            genre = row["genre"]
            image_url = row.get("image_url", "")
            spotify_id = row.get("spotify_id", "")
        else:
            genre = "Unknown"
            image_url = ""
            spotify_id = ""
        profile_with_genre.append({
            "artist": entry.artist,
            "genre": genre,
            "image_url": image_url,
            "spotify_id": spotify_id,
            "song": entry.song,
            "track_id": entry.track_id,
        })

    artist_genres: dict[str, list[str]] = defaultdict(list)
    for entry in _profile_artists:
        info = _content.artist_info[_content.artist_info["artist"] == entry.artist]
        genre = info.iloc[0]["genre"] if not info.empty else "Unknown"
        artist_genres[genre].append(entry.artist)

    genres = {}
    for genre, artists in artist_genres.items():
        recs = _content.recommend_from_artists(artists, n=n)
        if recs:
            genres[genre] = recs

    return {"profile_artists": profile_with_genre, "recommendations": genres}


@router.get("/artists/search", tags=["Artists"])
def search_artists_on_spotify(q: str = Query(..., description="Search query")):
    results = search_artist(q)
    return {"results": results}


@router.get("/songs/search", tags=["Songs"])
def search_songs_on_spotify(q: str = Query(..., description="Search query")):
    results = search_track(q)
    return {"results": results}


@router.post("/artists", tags=["Artists"])
def add_artist(req: AddArtistRequest):
    if _content is None:
        return {"status": "error", "message": "Recommender not ready"}
    from data.spotify_source import _load_cache, _save_cache
    cache = _load_cache()
    image_url = ""
    spotify_id = ""
    if req.name in cache:
        c = cache[req.name]
        image_url = c.get("image_url", "")
        spotify_id = c.get("spotify_id", "")
    else:
        try:
            results = search_artist(req.name)
            if results:
                image_url = results[0].get("image_url", "")
                spotify_id = results[0].get("spotify_id", "")
                cache[req.name] = {"name": req.name, "image_url": image_url, "spotify_id": spotify_id}
                _save_cache(cache)
        except Exception:
            pass
    _content.add_artist(req.name, req.genre, image_url, spotify_id)
    return {
        "status": "added",
        "artist": req.name,
        "genre": req.genre,
        "image_url": image_url,
        "spotify_id": spotify_id,
    }


@router.get("/profile", tags=["Profile"])
def get_profile():
    enriched = []
    for entry in _profile_artists:
        genre = entry.genre
        if not genre and _content is not None:
            info = _content.artist_info[_content.artist_info["artist"] == entry.artist]
            if not info.empty:
                genre = info.iloc[0]["genre"]
        enriched.append(ProfileEntry(artist=entry.artist, genre=genre, song=entry.song))
    return {"artists": enriched}


@router.post("/profile", tags=["Profile"])
def update_profile(profile: ProfileUpdate):
    global _profile_artists
    _profile_artists = profile.artists
    _save_profile()
    return {"artists": _profile_artists, "status": "saved"}


@router.delete("/profile", tags=["Profile"])
def clear_profile():
    global _profile_artists
    _profile_artists = []
    _save_profile()
    return {"status": "cleared"}
