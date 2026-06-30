import pandas as pd
from recommender.content_based import ContentBasedRecommender

TEST_ARTISTS = [
    {"artist": "The Midnight", "genre": "Synthwave"},
    {"artist": "Gunship", "genre": "Synthwave"},
    {"artist": "FM-84", "genre": "Synthwave"},
    {"artist": "Daft Punk", "genre": "Electronic/French Touch"},
    {"artist": "Justice", "genre": "Electronic/French Touch"},
    {"artist": "M83", "genre": "Electronic/Shoegaze"},
    {"artist": "The Chemical Brothers", "genre": "Electronic/Big Beat"},
    {"artist": "Tycho", "genre": "Ambient/Post-Rock"},
    {"artist": "Bonobo", "genre": "Downtempo/Electronic"},
    {"artist": "ODESZA", "genre": "Folktronica/Indie Electronic"},
]

def make_artist_info():
    return pd.DataFrame(TEST_ARTISTS)


def test_artist_count():
    assert len(TEST_ARTISTS) == 10


def test_content_based_from_artists():
    artist_info = make_artist_info()
    rec = ContentBasedRecommender(artist_info)
    rec.fit()
    results = rec.recommend_from_artists(["Daft Punk", "The Midnight"], n=5)
    assert len(results) == 5
    for r in results:
        assert "artist" in r
        assert "content_score" in r
        assert r["content_score"] > 0


def test_content_based_empty_input():
    artist_info = make_artist_info()
    rec = ContentBasedRecommender(artist_info)
    rec.fit()
    results = rec.recommend_from_artists([], n=5)
    assert results == []


def test_content_based_unknown_artist():
    artist_info = make_artist_info()
    rec = ContentBasedRecommender(artist_info)
    rec.fit()
    results = rec.recommend_from_artists(["Nonexistent Artist XYZ"], n=5)
    assert results == []
