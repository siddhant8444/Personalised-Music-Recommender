import json
import os
import time
from pathlib import Path

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

from data.sample_data import ARTISTS, GENRES

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

CACHE_PATH = Path(__file__).parent / "artist_cache.json"

_client: spotipy.Spotify | None = None
_last_request = 0.0
_rate_limited = False


def get_client() -> spotipy.Spotify:
    global _client
    if _client is None:
        auth = SpotifyClientCredentials(
            client_id=os.environ["SPOTIPY_CLIENT_ID"],
            client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        )
        _client = spotipy.Spotify(auth_manager=auth)
    return _client


def _rate_limit():
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)
    _last_request = time.time()


def fetch_artist_data(artist_name: str) -> dict | None:
    global _rate_limited
    if _rate_limited:
        return None
    _rate_limit()
    try:
        sp = get_client()
        results = sp.search(q=artist_name, type="artist", limit=1)
        items = results.get("artists", {}).get("items", [])
        if not items:
            return None
        a = items[0]
        full = sp.artist(a["id"])
        return {
            "name": full["name"],
            "image_url": full["images"][0]["url"] if full.get("images") else None,
            "spotify_id": full["id"],
        }
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            _rate_limited = True
            print(f"  Rate limited! Using cache/fallback.")
        return None


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(data: dict):
    CACHE_PATH.write_text(json.dumps(data, indent=2))


def get_artist_info() -> pd.DataFrame:
    cache = _load_cache()
    changed = False
    rows = []

    for artist in ARTISTS:
        if artist in cache:
            c = cache[artist]
            # Retry fetching if cached entry is incomplete and not rate limited
            if not c.get("image_url") and not c.get("spotify_id") and not _rate_limited:
                data = fetch_artist_data(artist)
                if data:
                    c["name"] = data["name"]
                    c["image_url"] = data.get("image_url", "")
                    c["spotify_id"] = data.get("spotify_id", "")
                    changed = True
            rows.append({
                "artist": c.get("name", artist),
                "genre": GENRES.get(artist, "Unknown"),
                "image_url": c.get("image_url", ""),
                "spotify_id": c.get("spotify_id", ""),
            })
            print(f"  (cached) {artist}")
        else:
            print(f"  Fetching: {artist}")
            data = fetch_artist_data(artist)
            if data:
                cache[artist] = {
                    "name": data["name"],
                    "image_url": data.get("image_url", ""),
                    "spotify_id": data.get("spotify_id", ""),
                }
                changed = True
                rows.append({
                    "artist": data["name"],
                    "genre": GENRES.get(artist, "Unknown"),
                    "image_url": data.get("image_url", ""),
                    "spotify_id": data.get("spotify_id", ""),
                })
            else:
                rows.append({
                    "artist": artist,
                    "genre": GENRES.get(artist, "Unknown"),
                    "image_url": "",
                    "spotify_id": "",
                })

    if changed:
        _save_cache(cache)

    df = pd.DataFrame(rows)
    for col in ["artist", "genre", "image_url", "spotify_id"]:
        if col not in df.columns:
            df[col] = ""
    return df


def search_artist(query: str) -> list[dict]:
    global _rate_limited
    if _rate_limited:
        return []
    _rate_limit()
    try:
        sp = get_client()
        results = sp.search(q=query, type="artist", limit=10)
        items = results.get("artists", {}).get("items", [])
        out = []
        for a in items:
            out.append({
                "name": a["name"],
                "image_url": a["images"][0]["url"] if a.get("images") else "",
                "spotify_id": a["id"],
            })
        return out
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            _rate_limited = True
            print("Search rate limited.")
        return []


def search_track(query: str, limit: int = 5) -> list[dict]:
    global _rate_limited
    if _rate_limited:
        return []
    _rate_limit()
    try:
        sp = get_client()
        results = sp.search(q=query, type="track", limit=limit)
        items = results.get("tracks", {}).get("items", [])
        out = []
        for t in items:
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            out.append({
                "name": t["name"],
                "artist": artists,
                "spotify_id": t["id"],
            })
        return out
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            _rate_limited = True
            print("Track search rate limited.")
        return []


def load_spotify_data() -> pd.DataFrame:
    print("Loading artist data (cache + Spotify)...")
    return get_artist_info()
