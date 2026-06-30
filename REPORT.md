# Siddhant's Music — Complete Project Report

## 1. What Is This?

A **personal music recommendation website** where:
- **You** (Siddhant) manage your favorite artists and songs privately
- **Visitors** see your artists with their Spotify photos, songs, and personalized genre-based recommendations

---

## 2. How to Use It

### Starting the server
```bash
python3 run.py
```
This starts a web server at `http://localhost:8000`.

### Two modes

| URL | Who | What you see |
|-----|-----|--------------|
| `http://localhost:8000` | Visitors | Your artists + "You Might Also Like" recommendations |
| `http://localhost:8000/?admin=siddhant` | You (admin) | Your artists + admin panel to add/remove artists |

The admin key (`siddhant`) is set in `.env` as `ADMIN_KEY=siddhant`.

---

## 3. Project Architecture

```
project/
├── run.py                  # Launches the server
├── .env                    # Spotify API keys + admin password
├── requirements.txt        # Python packages needed
├── pyproject.toml          # Project metadata
├── .gitignore              # Files to not commit to git
│
├── app/                    # The web application
│   ├── main.py             # Server setup, middleware, startup
│   ├── routes.py           # All API endpoints
│   └── models.py           # Data structures (ArtistInfo, etc.)
│
├── data/                   # Data handling
│   ├── sample_data.py      # 30 hidden "pool" artists (for recommendations)
│   ├── spotify_source.py   # Talks to Spotify API, fetches images/IDs
│   ├── artist_cache.json   # Saved Spotify data (so we don't re-fetch)
│   └── profile.json        # Your saved artists (persists across restarts)
│
├── recommender/            # The brain
│   └── content_based.py    # Genre similarity engine
│
├── frontend/               # What users see
│   └── index.html          # The whole website (HTML + CSS + JavaScript)
│
└── tests/
    └── test_recommender.py # Automated tests
```

---

## 4. Every File Explained

### `run.py` (3 lines)
**Purpose:** Start the server.
```python
import uvicorn
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```
- `uvicorn` is a web server for Python
- `app.main:app` means "load the `app` variable from `app/main.py`"
- `reload=True` means the server auto-restarts when files change

### `requirements.txt`
**Purpose:** Lists all Python packages needed.
- **fastapi** — The web framework (handles HTTP requests)
- **uvicorn** — The server that runs FastAPI
- **pandas** — Data manipulation (stores artist info as a table)
- **spotipy** — Talks to Spotify's API
- **python-dotenv** — Reads `.env` file
- **pydantic** — Validates data structures

Install with: `pip install -r requirements.txt`

### `.env`
**Purpose:** Secret keys (never commit to git).
```
SPOTIPY_CLIENT_ID=84a8b...    # Spotify app ID
SPOTIPY_CLIENT_SECRET=0413... # Spotify app secret
ADMIN_KEY=siddhant            # Your admin password
```

To get Spotify keys: go to https://developer.spotify.com/dashboard → create an app → copy Client ID and Client Secret.

### `app/main.py`
**Purpose:** The server's entry point. Three jobs:

**1. Startup (`lifespan` function):**
When the server starts, it:
1. Tries to load artist data from Spotify (via cache)
2. If Spotify fails, falls back to `sample_data.py`
3. Creates the `ContentBasedRecommender` and trains it (`fit()`)
4. Loads your saved profile from `profile.json`
5. Registers any profile artists not already in the recommender (with their Spotify images)

**2. Middleware:**
- **CORS** — Allows the frontend (port 8000) to talk to the API (also port 8000)
- **NoCache** — Forces browsers to always get the latest HTML (not a cached old version)

**3. Static files:**
- Serves the `frontend/index.html` when someone visits `http://localhost:8000`

### `app/models.py`
**Purpose:** Defines data shapes used across the app.
- `ArtistInfo` — What an artist looks like in API responses (name, genre, score, image, Spotify ID)
- `RecommendationResponse` — A list of recommendations + the method used

### `app/routes.py`
**Purpose:** All the API endpoints. Think of these as the "buttons" the frontend presses.

**Data structures:**
- `AddArtistRequest` — What the frontend sends when adding an artist (name + genre)
- `ProfileEntry` — A saved artist with artist name, genre, song, track_id
- `ProfileUpdate` — A list of ProfileEntries (the full profile)

**In-memory storage:**
- `_content` — The recommender (all artists + similarity data)
- `_profile_artists` — Your saved profile artists

**API endpoints:**
- `GET /api/v1/artists` — List ALL artists in the recommender (both pool + profile)
- `GET /api/v1/recommend/from-artists?artists=X&n=Y` — Get recommendations for specific artists
- `GET /api/v1/recommend/by-genre?n=Y` — Returns your profile artists + recommendations grouped by genre
- `GET /api/v1/artists/search?q=X` — Search Spotify for artists (for autocomplete)
- `GET /api/v1/songs/search?q=X` — Search Spotify for tracks (for autocomplete)
- `POST /api/v1/artists` — Register a new artist in the recommender
- `GET /api/v1/profile` — Get your saved artists
- `POST /api/v1/profile` — Save your artists
- `DELETE /api/v1/profile` — Clear your saved artists

**Key functions:**
- `_save_profile()` / `_load_profile()` — Read/write your artists to `profile.json`
- `_ensure_profile_artists_in_recommender()` — On startup, makes sure your profile artists exist in the recommender (with Spotify images from cache)

### `data/sample_data.py`
**Purpose:** A hidden pool of 30 artists across many genres. These act as the "world" of music. Visitors never see them directly — they only show up as "You Might Also Like" suggestions.

The genres are organized like:
- **Synthwave** — The Midnight, Gunship, FM-84
- **Electronic/French Touch** — Daft Punk, Justice
- **Electronic/Shoegaze** — M83
- **Ambient/Post-Rock** — Tycho
- **House/Electronic** — Bicep
- **Progressive House** — Deadmau5
- And many more

### `data/spotify_source.py`
**Purpose:** The bridge to Spotify's API. Three main jobs:

**1. Fetch artist data (`fetch_artist_data`):**
- Searches Spotify for an artist by name
- Gets their official name, profile image URL, and Spotify ID
- Returns `None` if rate-limited

**2. Cache system (`_load_cache` / `_save_cache`):**
- Stores fetched data in `artist_cache.json`
- On restart, reads from cache instead of calling Spotify again
- If cached entry has no image (rate-limited), retries when not rate-limited
- This way, once images are fetched, they survive restarts forever

**3. Search functions:**
- `search_artist(q)` — Searches artists on Spotify (for admin autocomplete)
- `search_track(q)` — Searches tracks on Spotify (for song autocomplete)

**Rate limit handling:**
- Spotify allows ~20 requests per 30 seconds for free-tier apps
- When rate-limited (HTTP 429), sets `_rate_limited = True` and stops all Spotify calls
- All searches return empty, all fetches return None
- System works fully offline from cache during this time

### `data/artist_cache.json`
**Purpose:** Persistent storage for Spotify data. Contains all 30 pool artists + your profile artists with:
- `name` — Official Spotify name
- `image_url` — Profile photo URL (300×300)
- `spotify_id` — Unique Spotify identifier

This file should NOT be committed to git (listed in `.gitignore`).

### `data/profile.json`
**Purpose:** Your saved artists. Persists across server restarts. Schema:
```json
[
  {
    "artist": "Calvin Harris",
    "genre": "Electronic Dance Music",
    "song": "Blame",
    "track_id": ""
  }
]
```
- `track_id` is filled when you add a song via the autocomplete (Spotify search)
- Empty `track_id` = falls back to searching the song on Spotify

### `recommender/content_based.py`
**Purpose:** The recommendation engine. Two phases:

**Phase 1: Training (`fit()`):**
1. Takes every artist's genre string (e.g., "Electronic/French Touch")
2. Splits it into individual words: `"Electronic/French Touch"` → `{electronic, french, touch}`
3. `"Electronic Dance Music"` → `{electronic, dance, music}`
4. `"House Music"` → `{house, music}`
5. For each artist, compares their genre words against every other artist's genre words
6. Uses **Jaccard similarity**: size of overlap ÷ size of union
   - Example: `{electronic, french, touch}` vs `{electronic, dance, music}`
   - Overlap: `{electronic}` = 1
   - Union: `{electronic, french, touch, dance, music}` = 5
   - Score: 1/5 = 0.2 (20% match)
7. Stores the top similar artists for each artist

**Phase 2: Recommending (`recommend_from_artists`):**
1. Takes your artists (e.g., Calvin Harris, Avicii)
2. For each, looks up their pre-computed similar artists
3. Aggregates scores (similar artists get points from both Calvin Harris AND Avicii)
4. Returns the top N matches, excluding your own artists

**Important insight:** Your profile artists get added to the similarity matrix alongside the 30 pool artists. So Calvin Harris (Electronic Dance Music) matches M83 (Electronic/Shoegaze) on the word "electronic" — 50% match.

### `frontend/index.html`
**Purpose:** The entire user interface. A single HTML file containing:

**HTML structure:**
- Hero section (title, search bar, share button)
- Main content area (rendered by JavaScript)
- Admin panel (hidden unless `?admin=siddhant`)
- Toast notification container

**CSS (custom dark theme):**
- Dark background (#0a0a0f) with gradient hero
- Cards with hover effects (lift + glow)
- Autocomplete dropdowns matching the theme
- Toast notifications (slide-in animation)
- Responsive grid layout

**JavaScript (the brain of the UI):**

*Autocomplete system (`setupAutocomplete`):*
- Generic function reused for artist, genre, and song inputs
- On keystroke: debounces 250ms, fetches suggestions from API
- Renders dropdown with keyboard navigation (arrow keys + Enter)
- Click outside closes dropdown

*Artist autocomplete:* Fetches from `/api/v1/artists/search?q=...`
*Genre autocomplete:* Filters a hardcoded list of 37 genres
*Song autocomplete:* Fetches from `/api/v1/songs/search?q=...` (includes artist name for better results)

*Save flow (`saveFavorites`):*
1. POSTs the full favorites list to `/api/v1/profile`
2. For each artist with a genre, registers them in the recommender via `/api/v1/artists`
3. Shows a toast notification
4. Reloads the page

*Page rendering (`renderPage`):*
1. Renders "My Artists" grid (with images, songs, click-to-play)
2. For visitors only: renders "You Might Also Like" sections grouped by genre
3. Supports filtering (searches by artist name or genre)

*Click behavior (`spotifyUrl`):*
1. If artist has a `track_id` → opens exact track on Spotify
2. If artist has a song name → searches Spotify for "song artist"
3. If artist has a `spotify_id` → opens their artist page
4. Otherwise → searches artist name

---

## 5. Complete Data Flow

### When a visitor opens the page:

```
Browser → GET http://localhost:8000/
  │
  ├── Server serves frontend/index.html (with no-cache headers)
  │
  └── JavaScript runs:
       │
       ├── init() checks: is this admin? (No → skip profile loading)
       │
       └── loadPage():
            │
            └── fetch /api/v1/recommend/by-genre?n=8
                 │
                 └── Server:
                      ├── Reads _profile_artists (your 4 saved artists)
                      ├── For each, looks up genre/image/spotify_id from recommender
                      ├── Groups your artists by genre
                      ├── For each genre, calls recommend_from_artists()
                      │   └── Looks up similar artists from similarity matrix
                      │   └── Returns matches (e.g., M83, Bonobo for Calvin Harris)
                      └── Returns JSON:
                          {
                            "profile_artists": [
                              {"artist": "Calvin Harris", "song": "Blame", ...}
                            ],
                            "recommendations": {
                              "Electronic Dance Music": [
                                {"artist": "M83", "content_score": 0.5, ...}
                              ]
                            }
                          }
 │
 └── renderPage(data):
      ├── "My Artists" section (Calvin Harris, Avicii, etc.)
      └── "You Might Also Like" sections (grouped by genre)
```

### When you add an artist via admin:

```
Admin panel → Type "Calvin" in artist field
  │
  ├── Debounce 250ms
  ├── fetch /api/v1/artists/search?q=Calvin
  │   └── Server calls Spotify search → returns [Calvin Harris, Calum Scott, ...]
  └── Dropdown shows results → You click "Calvin Harris"
       │
       ├── Name fills in → cursor jumps to Genre field
       │
       ├── Type genre → autocomplete filters from 37 genres → click one
       │   → Cursor jumps to Song field
       │
       ├── Type "Blame" → autocomplete searches Spotify tracks → click "Blame (feat. John Newman)"
       │   → Song fills in, track_id stored in dataset
       │
       └── Click "+" button
            │
            ├── Added to local favorites array
            ├── Render tag (green badge showing the artist)
            └── saveFavorites() runs:
                 ├── POST /api/v1/profile → saves to profile.json
                 ├── POST /api/v1/artists → registers in recommender (name + genre)
                 └── loadPage() → refreshes page
```

---

## 6. The Recommendation System Explained Simply

Think of it as **word matching for genres**.

Every artist has a genre string. The system:
1. **Breaks it into individual words** (ignoring `/` and spaces)
2. **Compares** your artists' words against every other artist's words
3. **Counts how many words they share** ÷ **how many total unique words they have**
4. Higher score = more genre overlap = better recommendation

### Example:

```
Your artist:  Calvin Harris ("Electronic Dance Music")
              → words: {electronic, dance, music}

Pool artist:  M83 ("Electronic/Shoegaze")
              → words: {electronic, shoegaze}

Overlap:      {electronic} = 1 word
Union:        {electronic, dance, music, shoegaze} = 4 words
Score:        1/4 = 0.25 = 25% match
```

The more genre words two artists share, the higher their match percentage.

### Why 30 pool artists?
Without them, there's nothing to recommend FROM. They're the "music universe." Your artists' genres are matched against them to find what visitors might also like.

---

## 7. Spotify Integration

### What Spotify is used for:
1. **Artist images** — Profile photos for the artist cards
2. **Spotify IDs** — Direct links to artist/track pages
3. **Autocomplete** — Searching artists and songs when adding via admin
4. **Track links** — Opening the exact song when you click a card

### Rate limits:
- Free Spotify API keys: ~20 requests per 30 seconds
- When exceeded: HTTP 429 error, then all Spotify calls stop
- System works fully offline: images come from cache, searches return empty
- Rate limit auto-resets after ~22 hours

### How images persist:
1. First successful fetch → saved to `artist_cache.json`
2. On next restart → loaded from cache (no Spotify call needed)
3. If rate-limited → uses cached images
4. If no cached image → shows a colored square with the artist's first letter

---

## 8. Key Design Decisions

**Why a hidden pool of 30 artists?**
Without them, recommendations would always be empty (nothing to compare against).

**Why no database?**
The data is small (30 + your artists). A JSON file is simpler than installing PostgreSQL/MySQL.

**Why one HTML file?**
Simplest deployment. No build tools, no npm, no React. Just open and edit.

**Why `track_id`?**
When you add a song through autocomplete, Spotify returns its track ID. This lets us link directly to the exact track instead of searching.

**Why no-cache headers?**
Browsers aggressively cache HTML. Without this, old versions of the page would show after you update artists.

---

## 9. What Could Be Added Next

### Highest Impact

**1. Reorder artists via drag-and-drop**
- Let you drag artists to rearrange them in "My Artists"
- Save the order to profile.json

**2. Album art on cards**
- When displaying a song, also fetch the album cover from Spotify
- Show it as a secondary image on the card

**3. Multiple songs per artist**
- Currently: one song per artist
- Could support an array of songs with their track IDs
- Clicking the card cycles through songs or shows all

**4. Genre graph / visualization**
- Show a bubble chart of your genres
- Each bubble size = how many artists in that genre
- Color-coded by genre family

**5. "Listen on Spotify" inline player**
- Embed Spotify's Web Playback SDK
- Let visitors preview 30-second clips without leaving the page

### Medium Impact

**6. Export / Import profile**
- Download your profile as JSON
- Share it with others or back it up

**7. Dark/light mode toggle**
- Currently only dark mode
- Light mode with CSS variables

**8. Stats page**
- Total artists count
- Genre distribution pie chart
- Most similar artist pairs
- "Your music mood" summary

**9. Auto-fetch top tracks**
- When adding an artist, automatically fetch their top 5 tracks from Spotify
- Let you pick which one to feature

### Nice Polish

**10. Loading skeletons**
- Instead of "Loading..." text, show gray card outlines that shimmer

**11. Animated page transitions**
- Cards fade in one by one
- Smooth genre section transitions

**12. Keyboard shortcuts**
- `Cmd/Ctrl + K` to focus search
- `Escape` to close admin panel

---

## 10. Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Server | FastAPI + Uvicorn | Handles HTTP requests |
| Data | Pandas DataFrame + JSON | Stores artists and similarity |
| Spotify | Spotipy library | Fetches images, IDs, searches |
| Recommender | Custom Jaccard similarity | Finds genre-similar artists |
| Frontend | Vanilla HTML/CSS/JS | What users see and interact with |
| Persistence | JSON files (cache + profile) | Survives server restarts |
