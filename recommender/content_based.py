import pandas as pd


class ContentBasedRecommender:
    def __init__(self, artist_info: pd.DataFrame):
        self.artist_info = artist_info
        self._similarity: dict[str, list[tuple[str, float]]] = {}

    def fit(self):
        artist_genres: dict[str, set[str]] = {}
        for _, row in self.artist_info.iterrows():
            raw = row["genre"].replace("/", " ").replace(",", " ")
            genres = set(g.strip().lower() for g in raw.split() if g.strip())
            artist_genres[row["artist"]] = genres

        all_artists = list(artist_genres.keys())
        for artist in all_artists:
            scores: dict[str, float] = {}
            my_genres = artist_genres[artist]
            for other in all_artists:
                if other == artist:
                    continue
                other_genres = artist_genres[other]
                if not my_genres or not other_genres:
                    continue
                overlap = len(my_genres & other_genres)
                union = len(my_genres | other_genres)
                jaccard = overlap / union if union > 0 else 0
                if jaccard > 0:
                    scores[other] = jaccard
            self._similarity[artist] = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def add_artist(self, name: str, genre: str, image_url: str = "", spotify_id: str = ""):
        if name in self.artist_info["artist"].values:
            return
        new = pd.DataFrame([{
            "artist": name, "genre": genre, "image_url": image_url, "spotify_id": spotify_id,
        }])
        self.artist_info = pd.concat([self.artist_info, new], ignore_index=True)
        for col in ["image_url", "spotify_id"]:
            if col in self.artist_info.columns:
                self.artist_info[col] = self.artist_info[col].fillna("")
        self.fit()

    def recommend_from_artists(self, artist_names: list[str], n: int = 10) -> list[dict]:
        matched = [a for a in artist_names if a in self._similarity]
        if not matched:
            return []

        candidate_scores: dict[str, float] = {}
        for seed in matched:
            for related, sim in self._similarity[seed]:
                if related in matched:
                    continue
                candidate_scores[related] = candidate_scores.get(related, 0) + sim

        ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:n]
        result = []
        for artist, score in ranked:
            info = self.artist_info[self.artist_info["artist"] == artist]
            row = info.iloc[0] if not info.empty else {}
            result.append({
                "artist": artist,
                "genre": row.get("genre", "Unknown"),
                "content_score": round(score, 4),
                "image_url": row.get("image_url", ""),
                "spotify_id": row.get("spotify_id", ""),
            })
        return result
