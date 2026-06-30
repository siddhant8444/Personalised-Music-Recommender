# Personalised Music Recommender

A personal music recommendation website powered by genre-based similarity matching with Spotify integration.

Share your favorite artists and songs with visitors, who get personalized "You Might Also Like" recommendations based on genre overlap.

## Features

- **Admin panel** — Add your favorite artists with songs via a hidden URL-based admin interface
- **Spotify autocomplete** — Search artists and tracks directly from Spotify when building your profile
- **Genre-based recommendations** — Visitors see similar artists grouped by genre
- **Persistent storage** — Your artist profile survives server restarts
- **Dark theme** — Clean, modern dark UI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Spotify credentials in .env
cp .env.example .env
# Add your SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET

# Run the server
python3 run.py
```

Open **http://localhost:8000** for the visitor view, or **http://localhost:8000/?admin=YOUR_KEY** for the admin panel.

## Tech Stack

- **Backend:** Python, FastAPI, Pandas
- **Frontend:** Vanilla HTML/CSS/JS
- **Recommendations:** Jaccard similarity on genre keywords
- **Data:** Spotify API (via Spotipy), JSON file storage

## Project Structure

```
├── run.py                  # Server entry point
├── app/
│   ├── main.py             # FastAPI app setup
│   ├── routes.py           # API endpoints
│   └── models.py           # Data models
├── data/
│   ├── sample_data.py      # Recommendation pool (30 artists)
│   └── spotify_source.py   # Spotify API client
├── recommender/
│   └── content_based.py    # Genre similarity engine
└── frontend/
    └── index.html          # The website
```

## License

MIT
